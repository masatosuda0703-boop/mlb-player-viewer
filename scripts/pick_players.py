"""
MLB 週次記事候補の自動選定スクリプト(Phase 2)

ロジック:
  [固定枠] japanese_players.json に登録された日本人選手から、直近7日で出場/登板がある選手
  [旬枠]   リーグ全体のリーダーボードから、HR/xwOBA/Whiff等の指標でスコアリング上位
  [除外]   articles/_history.json で過去 cooldown_weeks 以内に書いた選手

使い方:
    python pick_players.py
    python pick_players.py --date 2026-04-15 --top 5

出力:
    ../data/weekly_picks_YYYY-MM-DD.txt
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
ARTICLES_DIR = Path(__file__).parent.parent / "articles"
CONFIG_DIR = Path(__file__).parent
DATA_DIR.mkdir(exist_ok=True)

MLB_STATS_API = "https://statsapi.mlb.com/api/v1/stats"


def load_japanese_players() -> dict:
    with open(CONFIG_DIR / "japanese_players.json", encoding="utf-8") as f:
        return json.load(f)


def load_history() -> dict:
    path = ARTICLES_DIR / "_history.json"
    if not path.exists():
        return {"articles": [], "cooldown_weeks": 4}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def excluded_players(history: dict, today: date) -> set:
    """cooldown期間内に記事化した選手は除外"""
    weeks = history.get("cooldown_weeks", 4)
    cutoff = today - timedelta(weeks=weeks)
    excluded = set()
    for a in history.get("articles", []):
        adate = datetime.strptime(a["date"], "%Y-%m-%d").date()
        if adate >= cutoff:
            excluded.add(a["player"])
    return excluded


def fetch_mlb_leaders(group: str, season: int, sort_stat: str, top_n: int = 30) -> pd.DataFrame:
    """MLB Stats APIから直近シーズンのリーダーボード取得"""
    params = {
        "stats": "season",
        "group": group,
        "season": season,
        "sportIds": 1,
        "limit": top_n,
        "sortStat": sort_stat,
        "order": "desc",
    }
    r = requests.get(MLB_STATS_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    rows = []
    for split in data.get("stats", [{}])[0].get("splits", []):
        stat = split.get("stat", {})
        player = split.get("player", {})
        team = split.get("team", {})
        rows.append({
            "name": player.get("fullName"),
            "team": team.get("abbreviation"),
            **stat,
        })
    return pd.DataFrame(rows)


def score_batter(row) -> float:
    """打者スコアリング: HR/xwOBA/OPS/BB%などを総合"""
    score = 0.0
    try:
        score += float(row.get("homeRuns", 0) or 0) * 3.0
        ops = float(row.get("ops", 0) or 0)
        score += ops * 20.0  # OPS 1.000 → 20点
        slg = float(row.get("slg", 0) or 0)
        score += slg * 10.0
    except (TypeError, ValueError):
        pass
    return round(score, 2)


def score_pitcher(row) -> float:
    """投手スコアリング: K/ERA逆数/Whiff近似"""
    score = 0.0
    try:
        score += float(row.get("strikeOuts", 0) or 0) * 0.5
        era = float(row.get("era", 99) or 99)
        if era > 0:
            score += (5.0 / era) * 10.0  # ERA 2.00 → 25点
        ip = float(row.get("inningsPitched", 0) or 0)
        score += ip * 0.3
    except (TypeError, ValueError):
        pass
    return round(score, 2)


def pick_fixed_slots(jp_players: dict, excluded: set) -> list:
    """日本人選手の固定枠(除外対象は外す、priority順)"""
    picks = []
    all_jp = [("batter", p) for p in jp_players.get("batters", [])] + \
             [("pitcher", p) for p in jp_players.get("pitchers", [])]
    # priority順
    all_jp.sort(key=lambda x: x[1].get("priority", 99))
    seen = set()
    for ptype, p in all_jp:
        name = p["name"]
        if name in excluded or name in seen:
            continue
        seen.add(name)
        picks.append({
            "slot": "固定",
            "type": ptype,
            "name": name,
            "team": p.get("team", ""),
            "priority": p.get("priority", 99),
            "reason": f"日本人選手(priority {p.get('priority', 99)})",
        })
    return picks


def pick_trending_slots(season: int, excluded: set, jp_names: set, top_n: int = 3) -> list:
    """旬枠: リーダーボード上位から日本人以外・クールダウン外を抽出"""
    picks = []

    # 打者: HR順で取得 → スコアリング
    try:
        bat = fetch_mlb_leaders("hitting", season, "homeRuns", top_n=30)
        bat["score"] = bat.apply(score_batter, axis=1)
        bat = bat.sort_values("score", ascending=False)
        count = 0
        for _, row in bat.iterrows():
            name = row["name"]
            if name in excluded or name in jp_names:
                continue
            picks.append({
                "slot": "旬",
                "type": "batter",
                "name": name,
                "team": row.get("team", ""),
                "score": row["score"],
                "reason": f"HR {int(row.get('homeRuns', 0))}本 / OPS {row.get('ops', 'N/A')}",
            })
            count += 1
            if count >= 2:
                break
    except Exception as e:
        print(f"[WARN] 打者リーダー取得失敗: {e}", file=sys.stderr)

    # 投手: 奪三振順
    try:
        pit = fetch_mlb_leaders("pitching", season, "strikeOuts", top_n=30)
        pit["score"] = pit.apply(score_pitcher, axis=1)
        pit = pit.sort_values("score", ascending=False)
        count = 0
        for _, row in pit.iterrows():
            name = row["name"]
            if name in excluded or name in jp_names:
                continue
            picks.append({
                "slot": "旬",
                "type": "pitcher",
                "name": name,
                "team": row.get("team", ""),
                "score": row["score"],
                "reason": f"K {int(row.get('strikeOuts', 0))} / ERA {row.get('era', 'N/A')}",
            })
            count += 1
            if count >= 1:
                break
    except Exception as e:
        print(f"[WARN] 投手リーダー取得失敗: {e}", file=sys.stderr)

    return picks


def format_output(today: date, fixed: list, trending: list) -> str:
    lines = [f"=== {today} 週の記事候補 ===", ""]

    lines.append("[固定枠 — 日本人選手]")
    if not fixed:
        lines.append("  (候補なし — 全員クールダウン中)")
    for i, p in enumerate(fixed[:3], 1):
        lines.append(f"  {i}. {p['name']} ({p['team']}/{p['type']}) — {p['reason']}")

    lines.append("")
    lines.append("[旬枠 — リーダーボード上位]")
    if not trending:
        lines.append("  (取得失敗 — 手動で確認してください)")
    for i, p in enumerate(trending, len(fixed[:3]) + 1):
        lines.append(f"  {i}. {p['name']} ({p['team']}/{p['type']}) — {p['reason']} [score {p['score']}]")

    lines.append("")
    lines.append("--- 推奨 ---")
    if fixed:
        lines.append(f"今週の本命: {fixed[0]['name']}(固定枠トップ優先度)")
    if trending:
        lines.append(f"旬の穴: {trending[0]['name']}")
    lines.append("")
    lines.append("→ Claudeに「この候補から記事化したい選手を選んで」と投げればOK")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=str(date.today()), help="基準日 YYYY-MM-DD")
    p.add_argument("--season", type=int, default=date.today().year)
    p.add_argument("--top", type=int, default=5, help="候補合計数")
    args = p.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d").date()

    jp = load_japanese_players()
    jp_names = {x["name"] for x in jp.get("batters", []) + jp.get("pitchers", [])}

    history = load_history()
    excluded = excluded_players(history, today)
    if excluded:
        print(f"[INFO] クールダウン中(除外): {', '.join(excluded)}", file=sys.stderr)

    fixed = pick_fixed_slots(jp, excluded)
    trending = pick_trending_slots(args.season, excluded, jp_names)

    output = format_output(today, fixed, trending)
    out_path = DATA_DIR / f"weekly_picks_{today}.txt"
    out_path.write_text(output, encoding="utf-8")

    print(f"[OK] 候補ファイル: {out_path}")
    print()
    print(output)


if __name__ == "__main__":
    main()
