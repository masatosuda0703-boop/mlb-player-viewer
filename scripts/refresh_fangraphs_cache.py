"""FanGraphs 投手リーダーボードを CSV にスナップショット保存するローカル用スクリプト。

Streamlit Cloud の出口 IP が FanGraphs に弾かれることがあるので、
ローカル(自宅 PC)からこのスクリプトで CSV を生成 → git push で本番に同梱する運用。

Usage:
    python scripts/refresh_fangraphs_cache.py            # 当年シーズン
    python scripts/refresh_fangraphs_cache.py 2025       # シーズン指定
    python scripts/refresh_fangraphs_cache.py 2024 2025  # 複数シーズン

実行後は data/fangraphs_pitchers_{season}.csv が更新される。
git add data/ && git commit -m "refresh FG cache" && git push でデプロイ。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

FG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fangraphs.com/leaders/major-league",
}


def fetch_live(season: int) -> pd.DataFrame:
    """まず pybaseball、ダメなら cloudscraper の二段構え。"""
    print(f"[{season}] fetching via pybaseball.pitching_stats ...", flush=True)
    try:
        from pybaseball import pitching_stats
        df = pitching_stats(season, qual=0)
        if df is not None and not df.empty:
            print(f"[{season}] pybaseball OK ({len(df)} rows)", flush=True)
            return df
        print(f"[{season}] pybaseball returned empty, trying API ...", flush=True)
    except Exception as e:
        print(f"[{season}] pybaseball failed ({type(e).__name__}: {e}), trying API ...", flush=True)

    import cloudscraper
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    url = "https://www.fangraphs.com/api/leaders/major-league/data"
    params = {
        "pos": "all", "stats": "pit", "lg": "all",
        "qual": 0, "season": season, "season1": season,
        "ind": 0, "team": 0, "rost": 0,
        "pageitems": 3000, "pagenum": 1,
    }
    r = scraper.get(url, params=params, headers=FG_HEADERS, timeout=60)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data") if isinstance(payload, dict) else payload
    df = pd.DataFrame(rows or [])
    print(f"[{season}] cloudscraper OK ({len(df)} rows)", flush=True)
    return df


def save(df: pd.DataFrame, season: int) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"fangraphs_pitchers_{season}.csv"
    df.to_csv(out, index=False)
    print(f"[{season}] saved -> {out.relative_to(REPO_ROOT)} ({out.stat().st_size:,} bytes)")
    return out


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        seasons = [datetime.now().year]
    else:
        try:
            seasons = [int(a) for a in argv[1:]]
        except ValueError:
            print("usage: python scripts/refresh_fangraphs_cache.py [season ...]")
            return 2

    for s in seasons:
        try:
            df = fetch_live(s)
            if df.empty:
                print(f"[{s}] WARNING: empty response, skipping save")
                continue
            save(df, s)
        except Exception as e:
            print(f"[{s}] FAILED: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
