"""MLBリーダーボード取得(MLB Stats API + Baseball Savant)"""
import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MLB_API = "https://statsapi.mlb.com/api/v1/stats"


def fetch_mlb_leaders(group, season, sort_stat, top_n=50):
    """MLB公式APIから打撃/投手リーダーを取得"""
    params = {
        "stats": "season",
        "group": group,          # "hitting" or "pitching"
        "season": season,
        "sportIds": 1,           # MLB
        "limit": top_n,
        "sortStat": sort_stat,
        "order": "desc",
    }
    print(f"[INFO] MLB Stats API 取得中: {group} / sort={sort_stat}", file=sys.stderr)
    r = requests.get(MLB_API, params=params, timeout=30)
    r.raise_for_status()
    splits = r.json().get("stats", [{}])[0].get("splits", [])
    rows = []
    for s in splits:
        player = s.get("player", {})
        team = s.get("team", {})
        stat = s.get("stat", {})
        row = {
            "Name": player.get("fullName"),
            "PlayerID": player.get("id"),
            "Team": team.get("abbreviation") or team.get("name"),
            **stat,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_savant_advanced(season):
    """Baseball Savant先進指標(xwOBA, Barrel%, EV)"""
    try:
        from pybaseball import statcast_batter_expected_stats, statcast_batter_exitvelo_barrels
        print(f"[INFO] Baseball Savant 先進指標取得中...", file=sys.stderr)
        exp = statcast_batter_expected_stats(season, minPA=1)
        evb = statcast_batter_exitvelo_barrels(season, minBBE=1)
        for d in (exp, evb):
            if "last_name, first_name" in d.columns:
                d["Name"] = d["last_name, first_name"].apply(
                    lambda x: " ".join(reversed(str(x).split(", ")))
                )
        exp_cols = [c for c in ["Name", "xba", "xslg", "xwoba"] if c in exp.columns]
        evb_cols = [c for c in ["Name", "avg_hit_speed", "brl_percent", "ev95percent"] if c in evb.columns]
        return exp[exp_cols].merge(evb[evb_cols], on="Name", how="outer")
    except Exception as e:
        print(f"[WARN] Savant取得スキップ: {e}", file=sys.stderr)
        return pd.DataFrame()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["batting", "pitching"], default="batting")
    p.add_argument("--season", type=int, default=date.today().year)
    p.add_argument("--sort", default=None,
                   help="打撃: homeRuns/battingAverage/onBasePlusSlugging等 / 投手: earnedRunAverage/strikeOuts/wins等")
    p.add_argument("--top", type=int, default=20)
    a = p.parse_args()

    group = "hitting" if a.kind == "batting" else "pitching"
    sort_stat = a.sort or ("homeRuns" if a.kind == "batting" else "strikeOuts")

    df = fetch_mlb_leaders(group, a.season, sort_stat, top_n=a.top)
    if df.empty:
        print("[ERR] データが空です。シーズン/ソート指標を確認してください。")
        return

    # 打撃の場合はSavant指標をマージ
    if a.kind == "batting":
        savant = fetch_savant_advanced(a.season)
        if not savant.empty:
            df = df.merge(savant, on="Name", how="left")

    # 主要列を前に出す
    if a.kind == "batting":
        priority = ["Name", "Team", "gamesPlayed", "plateAppearances", "atBats",
                    "homeRuns", "rbi", "avg", "obp", "slg", "ops",
                    "xba", "xslg", "xwoba", "avg_hit_speed", "brl_percent"]
    else:
        priority = ["Name", "Team", "gamesPlayed", "gamesStarted", "wins", "losses",
                    "era", "inningsPitched", "strikeOuts", "baseOnBalls", "homeRuns", "whip"]
    cols = [c for c in priority if c in df.columns] + [c for c in df.columns if c not in priority and c != "PlayerID"]
    df = df[cols].head(a.top)

    path = DATA_DIR / f"leaderboard_{a.kind}_{a.season}_sortBy_{sort_stat}_top{a.top}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] {path}\n")
    # 主要列のみ表示
    display_cols = cols[:12]
    print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
