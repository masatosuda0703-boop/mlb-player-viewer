"""
MLB Statcast データ取得スクリプト(Phase 1 - Option A)

使い方:
    python fetch_data.py --player "Shohei Ohtani" --start 2026-03-27 --end 2026-04-15
    python fetch_data.py --player "Yoshinobu Yamamoto" --type pitcher
    python fetch_data.py --leaderboard batting --season 2026

出力:
    ../data/ にCSVで保存される。
    Claudeに貼り付ける用のサマリー(.txt)も同時に出力。
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from pybaseball import (
    playerid_lookup,
    statcast_batter,
    statcast_pitcher,
    batting_stats,
    pitching_stats,
    cache,
)

# キャッシュを有効化(同じクエリを繰り返すときに速い)
cache.enable()

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def get_player_id(full_name: str) -> int:
    """選手名 → MLBAM ID"""
    parts = full_name.strip().split()
    if len(parts) < 2:
        raise ValueError(f"フルネームで指定してください(例: 'Shohei Ohtani'): {full_name}")
    first, last = parts[0], " ".join(parts[1:])
    df = playerid_lookup(last, first)
    if df.empty:
        raise ValueError(f"選手が見つかりません: {full_name}")
    # 現役選手優先(mlb_played_lastが最新のもの)
    df = df.sort_values("mlb_played_last", ascending=False, na_position="last")
    pid = int(df.iloc[0]["key_mlbam"])
    print(f"[INFO] {full_name} → MLBAM ID: {pid}", file=sys.stderr)
    return pid


def summarize_batter(df: pd.DataFrame, name: str) -> str:
    """打者のStatcast pitch-by-pitchデータからサマリー指標を算出"""
    if df.empty:
        return f"{name}: データなし\n"

    # バレル判定: launch_speed_angle == 6 がBarrel(Statcast定義)
    batted = df[df["type"] == "X"].copy()  # 打球が発生したピッチのみ
    total_pitches = len(df)
    batted_balls = len(batted)
    swings = df[df["description"].isin([
        "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
        "hit_into_play", "foul_bunt", "missed_bunt",
    ])]
    whiffs = df[df["description"].isin([
        "swinging_strike", "swinging_strike_blocked", "missed_bunt",
    ])]

    hr = len(df[df["events"] == "home_run"])
    barrels = len(batted[batted["launch_speed_angle"] == 6]) if "launch_speed_angle" in batted.columns else 0
    hard_hit = len(batted[batted["launch_speed"] >= 95]) if "launch_speed" in batted.columns else 0

    avg_ev = batted["launch_speed"].mean() if not batted.empty else float("nan")
    max_ev = batted["launch_speed"].max() if not batted.empty else float("nan")
    avg_la = batted["launch_angle"].mean() if not batted.empty else float("nan")

    xwoba = df["estimated_woba_using_speedangle"].mean() if "estimated_woba_using_speedangle" in df.columns else float("nan")

    lines = [
        f"=== {name} Statcast サマリー ===",
        f"期間内の投球数: {total_pitches}",
        f"打球数(打席内で打球発生): {batted_balls}",
        f"ホームラン: {hr}",
        f"バレル: {barrels} ({barrels/batted_balls*100:.1f}% of batted balls)" if batted_balls else "バレル: 0",
        f"Hard-Hit(95mph+): {hard_hit} ({hard_hit/batted_balls*100:.1f}%)" if batted_balls else "Hard-Hit: 0",
        f"平均打球速度: {avg_ev:.1f} mph",
        f"最大打球速度: {max_ev:.1f} mph",
        f"平均打球角度: {avg_la:.1f} 度",
        f"xwOBA(打球のみ): {xwoba:.3f}",
        f"Whiff率: {len(whiffs)/len(swings)*100:.1f}% ({len(whiffs)}/{len(swings)} swings)" if len(swings) else "Whiff率: N/A",
        "",
        "--- 本塁打一覧(打球速度・角度・飛距離) ---",
    ]

    hrs = df[df["events"] == "home_run"][["game_date", "launch_speed", "launch_angle", "hit_distance_sc", "pitcher", "pitch_name"]]
    for _, r in hrs.iterrows():
        lines.append(
            f"{r['game_date']} | EV {r.get('launch_speed', 'N/A')} mph | "
            f"LA {r.get('launch_angle', 'N/A')}° | 飛距離 {r.get('hit_distance_sc', 'N/A')} ft | "
            f"球種 {r.get('pitch_name', 'N/A')}"
        )

    return "\n".join(lines) + "\n"


def summarize_pitcher(df: pd.DataFrame, name: str) -> str:
    """投手のStatcast pitch-by-pitchデータからサマリー指標を算出"""
    if df.empty:
        return f"{name}: データなし\n"

    total = len(df)
    swings = df[df["description"].isin([
        "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
        "hit_into_play", "foul_bunt", "missed_bunt",
    ])]
    whiffs = df[df["description"].isin(["swinging_strike", "swinging_strike_blocked"])]
    strikeouts = len(df[df["events"] == "strikeout"])
    walks = len(df[df["events"] == "walk"])
    hr_allowed = len(df[df["events"] == "home_run"])

    avg_velo = df[df["pitch_type"] == "FF"]["release_speed"].mean() if "release_speed" in df.columns else float("nan")
    xwoba_against = df["estimated_woba_using_speedangle"].mean() if "estimated_woba_using_speedangle" in df.columns else float("nan")

    # 球種ごとのWhiff率
    pitch_mix = df.groupby("pitch_name").agg(
        count=("pitch_name", "size"),
        avg_velo=("release_speed", "mean"),
    ).sort_values("count", ascending=False)

    lines = [
        f"=== {name} Statcast 投手サマリー ===",
        f"総投球数: {total}",
        f"平均4シーム球速: {avg_velo:.1f} mph",
        f"奪三振: {strikeouts} / 与四球: {walks} / 被本塁打: {hr_allowed}",
        f"Whiff率: {len(whiffs)/len(swings)*100:.1f}%" if len(swings) else "Whiff率: N/A",
        f"被xwOBA: {xwoba_against:.3f}",
        "",
        "--- 球種構成 ---",
        pitch_mix.to_string(),
    ]
    return "\n".join(lines) + "\n"


def fetch_player(full_name: str, player_type: str, start: str, end: str):
    pid = get_player_id(full_name)
    if player_type == "batter":
        df = statcast_batter(start, end, pid)
        summary = summarize_batter(df, full_name)
    else:
        df = statcast_pitcher(start, end, pid)
        summary = summarize_pitcher(df, full_name)

    slug = full_name.lower().replace(" ", "_")
    csv_path = DATA_DIR / f"{slug}_{player_type}_{start}_{end}.csv"
    txt_path = DATA_DIR / f"{slug}_{player_type}_{start}_{end}_summary.txt"
    df.to_csv(csv_path, index=False)
    txt_path.write_text(summary, encoding="utf-8")

    print(f"[OK] CSV: {csv_path}")
    print(f"[OK] サマリー: {txt_path}")
    print()
    print(summary)


def fetch_leaderboard(kind: str, season: int, top_n: int = 20):
    """リーグ全体のリーダーボード取得(シーズン集計)"""
    if kind == "batting":
        df = batting_stats(season, qual=1)
        cols = ["Name", "Team", "G", "PA", "HR", "AVG", "OBP", "SLG", "OPS", "wRC+", "Barrel%", "HardHit%", "xwOBA"]
        cols = [c for c in cols if c in df.columns]
        df = df[cols].sort_values("HR", ascending=False).head(top_n)
    else:
        df = pitching_stats(season, qual=1)
        cols = ["Name", "Team", "G", "IP", "ERA", "FIP", "K/9", "BB/9", "Stuff+", "Location+", "Pitching+"]
        cols = [c for c in cols if c in df.columns]
        df = df[cols].sort_values("IP", ascending=False).head(top_n)

    path = DATA_DIR / f"leaderboard_{kind}_{season}_top{top_n}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] リーダーボード: {path}")
    print(df.to_string(index=False))


def main():
    p = argparse.ArgumentParser(description="MLB Statcast データ取得")
    p.add_argument("--player", help="選手名(例: 'Shohei Ohtani')")
    p.add_argument("--type", choices=["batter", "pitcher"], default="batter", help="打者/投手")
    p.add_argument("--start", default=str(date.today() - timedelta(days=30)), help="開始日 YYYY-MM-DD")
    p.add_argument("--end", default=str(date.today()), help="終了日 YYYY-MM-DD")
    p.add_argument("--leaderboard", choices=["batting", "pitching"], help="リーダーボード取得モード")
    p.add_argument("--season", type=int, default=date.today().year, help="シーズン年")
    p.add_argument("--top", type=int, default=20, help="リーダーボード表示件数")
    args = p.parse_args()

    if args.leaderboard:
        fetch_leaderboard(args.leaderboard, args.season, args.top)
    elif args.player:
        fetch_player(args.player, args.type, args.start, args.end)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
