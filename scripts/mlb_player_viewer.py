"""
MLB Player Viewer  (Pitcher + Batter)
pybaseball + plotly + Streamlit
"""

import warnings
warnings.filterwarnings("ignore")

import math
import re
import datetime
import requests
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pybaseball import (statcast_pitcher, statcast_batter, playerid_lookup,
                        pitching_stats, playerid_reverse_lookup)

# ============================================================
# Page Config & Global Styling
# ============================================================
st.set_page_config(
    page_title="MLB Player Viewer",
    page_icon="⚾",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 700; }
[data-testid="stMetricLabel"] { font-size: 0.78rem; color: #8b949e; }

.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    height: 40px;
    padding: 0 18px;
    border-radius: 6px 6px 0 0;
    background-color: #161b22;
    color: #8b949e;
    font-size: 0.9rem;
}
.stTabs [aria-selected="true"] {
    background-color: #21262d;
    color: #e6edf3;
    font-weight: 600;
    border-bottom: 2px solid #58a6ff;
}

div[data-testid="stSidebarContent"] .stButton button { width: 100%; }

.player-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 14px;
    margin-top: 4px;
}

.profile-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2430 100%);
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 8px 0 18px 0;
    display: flex;
    align-items: center;
    gap: 20px;
}
.profile-card .avatar {
    flex: 0 0 auto;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 2px solid #30363d;
    background: #0d1117;
    object-fit: cover;
}
.profile-card .info { flex: 1 1 auto; min-width: 0; }
.profile-card h3 { margin: 0 0 4px 0; color: #e6edf3; }
.profile-card .team { color: #58a6ff; font-size: 0.95rem; font-weight: 600; }
.profile-card .meta { color: #8b949e; font-size: 0.85rem; margin-top: 8px; }
.profile-card .meta b { color: #c9d1d9; }

/* ヒーローストリップ(TOPページ冒頭の「今日の見どころ」) */
.hero-strip {
    background: linear-gradient(135deg, #10202f 0%, #1a0f22 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px 22px;
    margin: 8px 0 18px 0;
}
.hero-strip .label {
    color: #8b949e;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.hero-strip .leader-name {
    color: #e6edf3;
    font-weight: 700;
    font-size: 1.05rem;
    margin: 0;
}
.hero-strip .leader-stat {
    color: #58a6ff;
    font-weight: 700;
    font-size: 1.6rem;
    margin: 2px 0 0 0;
}
.hero-strip .leader-sub {
    color: #8b949e;
    font-size: 0.78rem;
    margin-top: 2px;
}

/* フッター */
.mlb-footer {
    margin-top: 36px;
    padding: 22px 0 12px 0;
    border-top: 1px solid #30363d;
    color: #8b949e;
    font-size: 0.82rem;
}
.mlb-footer a { color: #58a6ff; text-decoration: none; }
.mlb-footer a:hover { text-decoration: underline; }
.mlb-footer .foot-row {
    display: flex;
    flex-wrap: wrap;
    gap: 14px 26px;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
}
.mlb-footer .note-cta {
    display: inline-block;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    color: #e6edf3 !important;
    font-weight: 600;
}
.mlb-footer .note-cta:hover { background: #2d333b; }
.mlb-footer .copyright { text-align: center; color: #6e7681; font-size: 0.75rem; margin-top: 6px; }

/* 注目選手カードのスタッツ表示 */
.curated-stat {
    color: #58a6ff;
    font-weight: 700;
    font-size: 0.95rem;
    margin-top: 6px;
}
.curated-stat-label {
    color: #8b949e;
    font-size: 0.68rem;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 定数
# ============================================================
PITCH_LABEL = {
    "FF": "Four-Seam (FF)", "SI": "Sinker (SI)", "SL": "Slider (SL)",
    "ST": "Sweeper (ST)", "CU": "Curveball (CU)", "KC": "Knuckle-Curve (KC)",
    "CH": "Changeup (CH)", "FS": "Split-Finger (FS)", "FC": "Cutter (FC)",
    "EP": "Eephus (EP)", "KN": "Knuckleball (KN)", "FO": "Forkball (FO)",
    "SC": "Screwball (SC)", "CS": "Slow Curve (CS)", "PO": "Pitchout (PO)",
}

COLORS = [
    "#E63946", "#457B9D", "#2A9D8F", "#E9C46A",
    "#F4A261", "#264653", "#A8DADC", "#6D6875",
    "#B5838D", "#FFAFCC", "#BDE0FE", "#CDB4DB",
]

_today = datetime.date.today().strftime("%Y-%m-%d")

# フォールバック用ハードコード (API 障害時)
FALLBACK_CURATED_PLAYERS = [
    # 打者
    {"id": 660271, "first": "shohei",   "last": "ohtani",   "type": "打者 (Batter)",  "note": "史上初 50-50"},
    {"id": 592450, "first": "aaron",    "last": "judge",    "type": "打者 (Batter)",  "note": "AL MVP級スラッガー"},
    {"id": 665742, "first": "juan",     "last": "soto",     "type": "打者 (Batter)",  "note": "出塁率の怪物"},
    {"id": 677951, "first": "bobby",    "last": "witt",     "type": "打者 (Batter)",  "note": "5ツールSS"},
    {"id": 660670, "first": "ronald",   "last": "acuna",    "type": "打者 (Batter)",  "note": "前年MVP"},
    {"id": 608070, "first": "jose",     "last": "ramirez",  "type": "打者 (Batter)",  "note": "安定のCLE主砲"},
    # 投手
    {"id": 694973, "first": "paul",     "last": "skenes",   "type": "投手 (Pitcher)", "note": "新人NLサイ・ヤング候補"},
    {"id": 669373, "first": "tarik",    "last": "skubal",   "type": "投手 (Pitcher)", "note": "AL サイ・ヤング"},
    {"id": 543037, "first": "gerrit",   "last": "cole",     "type": "投手 (Pitcher)", "note": "NYY エース"},
    {"id": 554430, "first": "zack",     "last": "wheeler",  "type": "投手 (Pitcher)", "note": "PHI のNo.1"},
    {"id": 657277, "first": "logan",    "last": "webb",     "type": "投手 (Pitcher)", "note": "ゴロ王"},
    {"id": 669203, "first": "corbin",   "last": "burnes",   "type": "投手 (Pitcher)", "note": "元サイ・ヤング"},
]

SEASON_DATES = {
    2017: ("2017-04-02", "2017-10-01"),
    2018: ("2018-03-29", "2018-10-01"),
    2019: ("2019-03-28", "2019-09-29"),
    2020: ("2020-07-23", "2020-09-27"),
    2021: ("2021-04-01", "2021-10-03"),
    2022: ("2022-04-07", "2022-10-05"),
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-20", "2024-09-29"),
    2025: ("2025-03-27", "2025-09-28"),
    2026: ("2026-03-26", _today),
}

BG  = "#0d1117"
PBG = "#161b22"
GC  = "#30363d"
TC  = "#e6edf3"

SWING_DESC = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
              "hit_into_play", "hit_into_play_no_out", "hit_into_play_score"}
WHIFF_DESC = {"swinging_strike", "swinging_strike_blocked"}
CSW_DESC   = {"swinging_strike", "swinging_strike_blocked", "called_strike"}
HIT_EVENTS = {"single", "double", "triple", "home_run"}
AB_EVENTS  = HIT_EVENTS | {"strikeout", "field_out", "grounded_into_double_play",
                           "double_play", "triple_play", "force_out", "fielders_choice",
                           "fielders_choice_out", "field_error"}


def hex_to_rgba(hex_color: str, alpha: float = 0.6) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def dark_layout(fig: go.Figure, title: str = "", height: int = 480) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=PBG,
        font=dict(color=TC, size=11),
        title=dict(text=title, x=0.5, font=dict(size=14, color=TC)) if title else {},
        xaxis=dict(gridcolor=GC, zerolinecolor=GC, tickfont=dict(color=TC)),
        yaxis=dict(gridcolor=GC, zerolinecolor=GC, tickfont=dict(color=TC)),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GC, borderwidth=1,
                    font=dict(color=TC)),
        height=height,
        margin=dict(l=50, r=30, t=60, b=50),
    )
    return fig


def inches_to_ft_in(inches) -> str:
    if inches is None or (isinstance(inches, float) and math.isnan(inches)):
        return "—"
    try:
        inches = int(inches)
    except Exception:
        return str(inches)
    return f"{inches // 12}′{inches % 12}″"


# ============================================================
# キャッシュ付き関数
# ============================================================
@st.cache_data(show_spinner="選手情報を検索中...")
def lookup_player(last_name: str, first_name: str):
    return playerid_lookup(last_name.strip(), first_name.strip() or None)


# 主要選手の日本語エイリアス (漢字 / カタカナ)
JP_ALIASES = {
    # 日本人 MLB 選手
    "shohei ohtani":       "大谷翔平 / オオタニショウヘイ / オオタニ",
    "yoshinobu yamamoto":  "山本由伸 / ヤママトヨシノブ",
    "seiya suzuki":        "鈴木誠也 / スズキセイヤ",
    "masataka yoshida":    "吉田正尚 / ヨシダマサタカ",
    "kodai senga":         "千賀滉大 / センガコウダイ",
    "shota imanaga":       "今永昇太 / イマナガショウタ",
    "yusei kikuchi":       "菊池雄星 / キクチユウセイ",
    "roki sasaki":         "佐々木朗希 / ササキロウキ",
    "shugo maki":          "牧秀悟 / マキシュウゴ",
    "munetaka murakami":   "村上宗隆 / ムラカミムネタカ",
    # 主要スター (カタカナ読み)
    "aaron judge":   "アーロンジャッジ / ジャッジ",
    "juan soto":     "フアンソト / ソト",
    "mookie betts":  "ムーキーベッツ / ベッツ",
    "freddie freeman":"フレディフリーマン / フリーマン",
    "ronald acuna jr.": "ロナルドアクーニャ / アクーニャ",
    "bobby witt jr.":   "ボビーウィット / ウィット",
    "jose ramirez":  "ホセラミレス / ラミレス",
    "gerrit cole":   "ゲリットコール / コール",
    "paul skenes":   "ポールスキーンズ / スキーンズ",
    "tarik skubal":  "タリクスクーバル / スクーバル",
    "zack wheeler":  "ザックウィーラー / ウィーラー",
    "logan webb":    "ローガンウェブ / ウェブ",
    "corbin burnes": "コービンバーンズ / バーンズ",
    "clayton kershaw": "クレイトンカーショー / カーショー",
    "max scherzer":  "マックスシャーザー / シャーザー",
    "jacob degrom":  "ジェイコブデグロム / デグロム",
    "vladimir guerrero jr.": "ブラディミールゲレーロ / ゲレーロ",
}


@st.cache_data(ttl=60 * 60 * 24, show_spinner="選手リストを取得中...")
def fetch_all_active_players():
    """MLB Stats API から全アクティブ選手を取得 (24h キャッシュ)"""
    year = datetime.date.today().year
    url = "https://statsapi.mlb.com/api/v1/sports/1/players"
    try:
        r = requests.get(url, params={"season": year}, timeout=20)
        if r.status_code != 200:
            # 前年にフォールバック
            r = requests.get(url, params={"season": year - 1}, timeout=20)
        people = r.json().get("people", []) if r.status_code == 200 else []
    except Exception:
        people = []
    out = []
    for p in people:
        out.append({
            "id":        p.get("id"),
            "full_name": p.get("fullName") or "",
            "team":      (p.get("currentTeam") or {}).get("abbreviation")
                         or (p.get("currentTeam") or {}).get("name") or "",
            "position":  (p.get("primaryPosition") or {}).get("abbreviation") or "",
        })
    return [p for p in out if p["id"] and p["full_name"]]


def build_player_options(players):
    """selectbox 用 option リストを構築: (label, id, full_name)"""
    opts = []
    for p in players:
        jp = JP_ALIASES.get(p["full_name"].lower(), "")
        parts = [p["full_name"]]
        if jp:
            parts.append(jp)
        meta_bits = [x for x in [p["team"], p["position"]] if x]
        if meta_bits:
            parts.append(" ".join(meta_bits))
        label = "  ·  ".join(parts)
        opts.append((label, p["id"], p["full_name"]))
    opts.sort(key=lambda x: x[2].lower())
    return opts


@st.cache_data(show_spinner="Statcast (投手) データを取得中...")
def fetch_statcast_pitcher(player_id: int, start: str, end: str) -> pd.DataFrame:
    return statcast_pitcher(start, end, player_id=player_id)


@st.cache_data(show_spinner="Statcast (打者) データを取得中...")
def fetch_statcast_batter(player_id: int, start: str, end: str) -> pd.DataFrame:
    return statcast_batter(start, end, player_id=player_id)


FG_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.fangraphs.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

# 1 PA あたりのアウトカウント (FIP/IP 計算用)
_EVENT_OUTS = {
    "strikeout": 1, "strikeout_double_play": 2,
    "field_out": 1, "force_out": 1, "fielders_choice_out": 1,
    "grounded_into_double_play": 2, "double_play": 2, "triple_play": 3,
    "sac_fly": 1, "sac_fly_double_play": 2, "sac_bunt": 1,
    "sac_bunt_double_play": 2, "other_out": 1,
    "caught_stealing_2b": 1, "caught_stealing_3b": 1,
    "caught_stealing_home": 1, "pickoff_caught_stealing_2b": 1,
    "pickoff_caught_stealing_3b": 1, "pickoff_caught_stealing_home": 1,
    "pickoff_1b": 1, "pickoff_2b": 1, "pickoff_3b": 1,
}


def compute_fip_from_statcast(raw_df: pd.DataFrame) -> dict:
    """Statcast 生データから FIP/K/9/BB/9/IP を近似計算"""
    if raw_df is None or raw_df.empty or "events" not in raw_df.columns:
        return {}
    ev = raw_df["events"].dropna()
    if ev.empty:
        return {}
    k   = int((ev == "strikeout").sum() + (ev == "strikeout_double_play").sum())
    bb  = int((ev == "walk").sum())
    hbp = int((ev == "hit_by_pitch").sum())
    hr  = int((ev == "home_run").sum())
    outs = int(sum(_EVENT_OUTS.get(e, 0) for e in ev))
    ip   = outs / 3.0
    if ip <= 0:
        return {}
    # FIP 定数は年度により変動するが近年は ~3.10 で近似
    fip_const = 3.10
    fip = ((13 * hr + 3 * (bb + hbp) - 2 * k) / ip) + fip_const
    return {
        "FIP":  round(fip, 2),
        "K/9":  round(k * 9 / ip, 2),
        "BB/9": round(bb * 9 / ip, 2),
        "IP":   round(ip, 1),
    }


@st.cache_data(ttl=60 * 60 * 6, show_spinner="FanGraphs リーダーボード取得中...")
def fetch_fangraphs_pitchers(season: int) -> pd.DataFrame:
    """FanGraphs JSON API から投手リーダーボードを取得 (cloudscraper 必須)"""
    try:
        import cloudscraper
    except ImportError:
        raise RuntimeError(
            "cloudscraper 未インストール — `pip install cloudscraper` で "
            "FanGraphs の Cloudflare ガードを突破できます"
        )
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
    r = scraper.get(url, params=params, headers=FG_HEADERS, timeout=45)
    if r.status_code != 200:
        snippet = r.text[:120].replace("\n", " ")
        raise RuntimeError(f"HTTP {r.status_code}  body={snippet}")
    payload = r.json()
    rows = payload.get("data") if isinstance(payload, dict) else payload
    return pd.DataFrame(rows or [])


def fetch_pitcher_advanced(player_id: int, season: int,
                           raw_df: pd.DataFrame | None = None) -> dict:
    """Stuff+/Location+/Pitching+/FIP 等を取得
    - FIP/K/9/BB/9/IP は Statcast からローカル計算（常時）
    - Stuff+/Location+/Pitching+/xFIP/WAR は FanGraphs から取得（要 cloudscraper）
    """
    local = compute_fip_from_statcast(raw_df) if raw_df is not None else {}
    fg_stats = {}
    fg_diag = ""

    try:
        df = fetch_fangraphs_pitchers(season)
        if df is None or df.empty:
            fg_diag = f"FG データ空 ({season})"
        else:
            id_col = next(
                (c for c in ["xMLBAMID", "MLBAMID", "mlbamid", "mlbam_id"]
                 if c in df.columns),
                None,
            )
            if id_col is None:
                fg_diag = "FG 応答に MLBAM 列なし"
            else:
                df["_mlbam"] = pd.to_numeric(df[id_col], errors="coerce")
                row = df[df["_mlbam"] == player_id]
                if row.empty:
                    fg_diag = f"{season} FG に該当選手なし"
                else:
                    r = row.iloc[0]

                    def _get(*keys):
                        for k in keys:
                            if k in r.index and pd.notna(r[k]):
                                return r[k]
                        return None

                    fg_stats = {
                        "Stuff+":    _get("Stuff+", "sp_stuff"),
                        "Location+": _get("Location+", "sp_location"),
                        "Pitching+": _get("Pitching+", "sp_pitching"),
                        "xFIP":      _get("xFIP"),
                        "WAR":       _get("WAR"),
                        "ERA":       _get("ERA"),
                    }
                    fg_diag = "FG OK"
    except Exception as e:
        fg_diag = f"{type(e).__name__}: {e}"

    combined = dict(local)
    for k, v in fg_stats.items():
        if v is not None:
            combined[k] = v

    diag_parts = []
    if local:
        diag_parts.append(f"ローカル FIP={local.get('FIP')} (IP={local.get('IP')})")
    else:
        diag_parts.append("ローカル計算不可")
    diag_parts.append(f"FG: {fg_diag}")

    return {"stats": combined, "diag": "  ·  ".join(diag_parts)}


@st.cache_data(ttl=60 * 60 * 12, show_spinner="最新リーダーボード取得中...")
def fetch_curated_players(season: int, n_batters: int = 6, n_pitchers: int = 6):
    """MLB Stats API のリーダーボードから注目選手を自動生成 (12h キャッシュ)"""

    def _fetch(group: str, cat: str, yr: int):
        url = "https://statsapi.mlb.com/api/v1/stats/leaders"
        params = {
            "leaderCategories": cat,
            "season":           yr,
            "sportId":          1,
            "limit":            25,
            "statGroup":        group,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                return []
            data = r.json().get("leagueLeaders", [])
            return data[0].get("leaders", []) if data else []
        except Exception:
            return []

    def _to_card(ld: dict, role: str, label: str, stat_name: str):
        p = ld.get("person", {}) or {}
        fn = (p.get("fullName") or "").strip()
        val = ld.get("value")
        parts = fn.split(" ", 1)
        first = parts[0].lower() if parts else ""
        last  = parts[1].lower() if len(parts) > 1 else first
        team  = ld.get("team") or {}
        team_abbr = team.get("abbreviation") if isinstance(team, dict) else ""
        note_parts = []
        if team_abbr:
            note_parts.append(team_abbr)
        note_parts.append(f"{label} {val}")
        return {
            "id":    p.get("id"),
            "first": first,
            "last":  last,
            "type":  role,
            "note":  "  ".join(note_parts),
            "stat_name": stat_name,
            "stat_val":  val,
        }

    # 当該シーズンにデータがなければ前年にフォールバック
    batters_raw = _fetch("hitting", "onBasePlusSlugging", season) or \
                  _fetch("hitting", "onBasePlusSlugging", season - 1)
    pitchers_raw = _fetch("pitching", "earnedRunAverage", season) or \
                   _fetch("pitching", "earnedRunAverage", season - 1)

    batters = [
        _to_card(ld, "打者 (Batter)", "OPS", "onBasePlusSlugging")
        for ld in batters_raw[:n_batters]
        if ld.get("person", {}).get("id")
    ]
    pitchers = [
        _to_card(ld, "投手 (Pitcher)", "ERA", "earnedRunAverage")
        for ld in pitchers_raw[:n_pitchers]
        if ld.get("person", {}).get("id")
    ]
    return batters + pitchers


def get_curated_players(season: int):
    live = fetch_curated_players(season)
    if not live:
        return FALLBACK_CURATED_PLAYERS, False
    return live, True


@st.cache_data(show_spinner="選手プロフィールを取得中...")
def fetch_player_profile(player_id: int) -> dict:
    """MLB Stats API からプロフィール情報を取得"""
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=currentTeam"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json().get("people", [])
        if not data:
            return {}
        p = data[0]
        team = p.get("currentTeam", {}) or {}
        pos  = p.get("primaryPosition", {}) or {}
        bat  = p.get("batSide", {}) or {}
        throw = p.get("pitchHand", {}) or {}
        return {
            "full_name":    p.get("fullName"),
            "team":         team.get("name"),
            "team_abbr":    team.get("abbreviation"),
            "position":     pos.get("abbreviation"),
            "position_name": pos.get("name"),
            "jersey":       p.get("primaryNumber"),
            "bats":         bat.get("code"),
            "throws":       throw.get("code"),
            "height":       p.get("height"),  # 例: "6' 4\""
            "weight":       p.get("weight"),
            "birth_date":   p.get("birthDate"),
            "age":          p.get("currentAge"),
            "birth_city":   p.get("birthCity"),
            "birth_country": p.get("birthCountry"),
            "mlb_debut":    p.get("mlbDebutDate"),
            "active":       p.get("active"),
        }
    except Exception:
        return {}


def player_headshot_url(player_id: int) -> str:
    return (
        "https://img.mlbstatic.com/mlb-photos/image/upload/"
        "d_people:generic:headshot:67:current.png/w_240,q_auto:best/"
        f"v1/people/{player_id}/headshot/67/current"
    )


def render_profile_card(profile: dict, player_name: str, player_id: int):
    img_url = player_headshot_url(player_id)
    if not profile:
        st.markdown(
            f'<div class="profile-card">'
            f'<img class="avatar" src="{img_url}" alt="headshot" '
            f'onerror="this.style.display=\'none\'"/>'
            f'<div class="info"><h3>🏟️ {player_name}</h3>'
            f'<div class="meta">MLBAM ID: <b>{player_id}</b></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    name = profile.get("full_name") or player_name
    team = profile.get("team") or "—"
    pos  = profile.get("position_name") or "—"
    pos_short = profile.get("position") or ""
    jersey = profile.get("jersey")
    bats = profile.get("bats") or "—"
    throws = profile.get("throws") or "—"
    height = profile.get("height") or "—"
    weight = profile.get("weight")
    weight_s = f"{weight} lbs" if weight else "—"
    age = profile.get("age")
    bdate = profile.get("birth_date") or "—"
    bcity = profile.get("birth_city") or ""
    bcountry = profile.get("birth_country") or ""
    birth_place = ", ".join(x for x in [bcity, bcountry] if x) or "—"
    debut = profile.get("mlb_debut") or "—"
    jersey_s = f"#{jersey}  " if jersey else ""

    st.markdown(
        f'''
        <div class="profile-card">
            <img class="avatar" src="{img_url}" alt="headshot"
                 onerror="this.style.display='none'"/>
            <div class="info">
                <h3>🏟️ {jersey_s}{name} <span style="color:#8b949e;font-size:0.8em;">({pos_short})</span></h3>
                <div class="team">{team}</div>
                <div class="meta">
                    <b>ポジション:</b> {pos} &nbsp;·&nbsp;
                    <b>打/投:</b> {bats}/{throws} &nbsp;·&nbsp;
                    <b>身長:</b> {height} &nbsp;·&nbsp;
                    <b>体重:</b> {weight_s} &nbsp;·&nbsp;
                    <b>年齢:</b> {age if age is not None else "—"}
                </div>
                <div class="meta">
                    <b>生年月日:</b> {bdate} &nbsp;·&nbsp;
                    <b>出身:</b> {birth_place} &nbsp;·&nbsp;
                    <b>MLB デビュー:</b> {debut} &nbsp;·&nbsp;
                    <b>MLBAM ID:</b> {player_id}
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


# ============================================================
# セッションリセット
# ============================================================
def _reset_to_top():
    """TOPページに戻る: 検索結果関連のセッション状態をクリア"""
    for k in ["ss_lookup_df", "ss_raw_df", "ss_base_key", "ss_full_key",
              "ss_player_name", "ss_player_id", "ss_chosen_label",
              "ss_player_type", "ss_season"]:
        st.session_state.pop(k, None)


# ============================================================
# UI ヘルパー: ヒーロー / フッター
# ============================================================
# note ユーザー名(プロフィールURL末尾)。空文字にするとフッターのnoteブロックを非表示
NOTE_USER = "mlb_analysis"      # https://note.com/mlb_analysis
GITHUB_URL = "https://github.com/masatosuda0703-boop/mlb-player-viewer"


def render_hero_strip(curated_list: list):
    """TOPページ冒頭に表示する「今日の見どころ」バナー。OPS/ERAリーダーを強調表示。"""
    top_batter  = next((p for p in curated_list if p.get("type", "").startswith("打者")), None)
    top_pitcher = next((p for p in curated_list if p.get("type", "").startswith("投手")), None)
    if not top_batter and not top_pitcher:
        return

    def _block(p, role_label, stat_label):
        if not p:
            return ""
        name = f"{p.get('first','').title()} {p.get('last','').title()}".strip()
        val  = p.get("stat_val", "")
        img  = player_headshot_url(p["id"])
        note = p.get("note", "")
        return (
            f'<div style="display:flex;align-items:center;gap:14px;flex:1;min-width:220px;">'
            f'<img src="{img}" style="width:68px;height:68px;border-radius:50%;'
            f'border:2px solid #30363d;object-fit:cover;background:#0d1117;" '
            f'onerror="this.style.visibility=\'hidden\'"/>'
            f'<div style="min-width:0;">'
            f'<div class="label">{role_label}リーダー</div>'
            f'<p class="leader-name">{name}</p>'
            f'<p class="leader-stat">{stat_label} {val}</p>'
            f'<div class="leader-sub">{note}</div>'
            f'</div></div>'
        )

    html = (
        '<div class="hero-strip" style="display:flex;gap:22px;flex-wrap:wrap;">'
        + _block(top_batter,  "打者",  "OPS")
        + _block(top_pitcher, "投手",  "ERA")
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_footer():
    """ページ下部の共通フッター。note誘導枠 + クレジット。"""
    note_block = ""
    if NOTE_USER:
        note_block = (
            f'<a class="note-cta" href="https://note.com/{NOTE_USER}" target="_blank" '
            f'rel="noopener">📝 note で詳しい解説を読む</a>'
        )
    html = f"""
<div class="mlb-footer">
    <div class="foot-row">
        {note_block}
        <span>データ: <a href="https://baseballsavant.mlb.com/" target="_blank" rel="noopener">Baseball Savant</a> / <a href="https://statsapi.mlb.com/" target="_blank" rel="noopener">MLB Stats API</a> / <a href="https://www.fangraphs.com/" target="_blank" rel="noopener">FanGraphs</a></span>
        <span><a href="{GITHUB_URL}" target="_blank" rel="noopener">⚙️ ソース (GitHub)</a></span>
    </div>
    <div class="copyright">© 2026 MLB Player Viewer — 非公式・学習目的のツールです</div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# note 記事連携 (RSS から最新記事を取得し、選手名でマッチング)
# ============================================================
_NOTE_RSS_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_note_articles(user: str) -> list:
    """note.com の公開RSS (最新20件程度) を取得してパース。1時間キャッシュ。"""
    if not user:
        return []
    url = f"https://note.com/{user}/rss"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
    except Exception:
        return []
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        enc = item.find("content:encoded", _NOTE_RSS_NS)
        html_body = ((enc.text or "") if enc is not None else "") + " " + desc
        thumb = ""
        m = re.search(r'<img[^>]+src="([^"]+)"', html_body)
        if m:
            thumb = m.group(1)
        text = re.sub(r"<[^>]+>", "", desc)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 120:
            text = text[:120] + "…"
        # pubDate を 'YYYY-MM-DD' 形式に正規化 (失敗したら先頭16文字)
        pub_short = pub[:16]
        try:
            dt = datetime.datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S")
            pub_short = dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        items.append({"title": title, "link": link, "pub": pub_short,
                      "desc": text, "thumb": thumb})
    return items


def _player_keywords(player_name_en: str) -> list:
    """マッチング用キーワード: 英語フル名 + ラストネーム + 日本語エイリアス。"""
    keys = []
    if player_name_en:
        keys.append(player_name_en.lower())
        parts = player_name_en.lower().split()
        if len(parts) >= 2:
            keys.append(parts[-1])
    alias = JP_ALIASES.get(player_name_en.lower(), "")
    for a in alias.split("/"):
        a = a.strip()
        if a:
            keys.append(a.lower())
    # 3文字未満は誤マッチが多いので除外
    return list({k for k in keys if len(k) >= 3})


def match_articles_for_player(articles: list, player_name_en: str, max_n: int = 5) -> list:
    keys = _player_keywords(player_name_en)
    if not keys:
        return []
    out = []
    for a in articles:
        hay = (a["title"] + " " + a["desc"]).lower()
        if any(k in hay for k in keys):
            out.append(a)
            if len(out) >= max_n:
                break
    return out


def render_latest_notes(max_n: int = 6):
    """TOPページ用: note の最新記事をサムネ付きで一覧表示。"""
    if not NOTE_USER:
        return
    articles = fetch_note_articles(NOTE_USER)
    profile_url = f"https://note.com/{NOTE_USER}"
    st.markdown("---")
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.subheader("📝 note 最新記事")
    with header_cols[1]:
        st.markdown(
            f'<div style="text-align:right;padding-top:10px;">'
            f'<a href="{profile_url}" target="_blank" rel="noopener" '
            f'style="color:#58a6ff;text-decoration:none;font-size:0.9em;">'
            f'すべて見る →</a></div>',
            unsafe_allow_html=True,
        )
    if not articles:
        st.caption("noteの記事を取得できませんでした。後でもう一度お試しください。")
        return
    st.caption(f"note.com/{NOTE_USER} の最新公開記事(1時間キャッシュ)")
    latest = articles[:max_n]
    cards = ['<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-top:4px;">']
    for a in latest:
        thumb_html = (
            f'<img src="{a["thumb"]}" style="width:100%;height:130px;object-fit:cover;" '
            f'onerror="this.style.display=\'none\'"/>'
            if a["thumb"] else
            '<div style="width:100%;height:130px;background:#0d1117;display:flex;'
            'align-items:center;justify-content:center;color:#30363d;font-size:2em;">📝</div>'
        )
        cards.append(
            f'<a href="{a["link"]}" target="_blank" rel="noopener" '
            f'style="display:block;background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'text-decoration:none;color:#c9d1d9;overflow:hidden;transition:border-color .15s;" '
            f'onmouseover="this.style.borderColor=\'#58a6ff\'" '
            f'onmouseout="this.style.borderColor=\'#30363d\'">'
            f'{thumb_html}'
            f'<div style="padding:10px 12px;">'
            f'<div style="font-weight:600;font-size:0.92em;line-height:1.35;margin-bottom:6px;'
            f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{a["title"]}</div>'
            f'<div style="color:#8b949e;font-size:0.75em;">{a["pub"]}</div>'
            f'</div></a>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def render_related_notes(player_name_en: str):
    """選手ページ下部に、この選手に関連する note 記事を表示。"""
    if not NOTE_USER:
        return
    articles = fetch_note_articles(NOTE_USER)
    profile_url = f"https://note.com/{NOTE_USER}"
    st.markdown("---")
    st.markdown(f"### 📝 {player_name_en} に関連する note 記事")
    if not articles:
        st.markdown(
            f'<div style="color:#8b949e;font-size:0.9em;">'
            f'note記事の取得に失敗しました。'
            f'<a href="{profile_url}" target="_blank" rel="noopener" style="color:#58a6ff;">'
            f'noteプロフィールを開く →</a></div>',
            unsafe_allow_html=True,
        )
        return
    matched = match_articles_for_player(articles, player_name_en)
    if not matched:
        st.markdown(
            f'<div style="color:#8b949e;font-size:0.9em;margin-bottom:8px;">'
            f'最新{len(articles)}件のnote記事には関連記事が見当たりませんでした。</div>'
            f'<a href="{profile_url}" target="_blank" rel="noopener" '
            f'style="color:#58a6ff;font-size:0.9em;">📒 noteで他の記事を読む →</a>',
            unsafe_allow_html=True,
        )
        return
    cards = ['<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-top:8px;">']
    for a in matched:
        thumb_html = (
            f'<img src="{a["thumb"]}" style="width:100%;height:120px;object-fit:cover;" '
            f'onerror="this.style.display=\'none\'"/>'
            if a["thumb"] else ""
        )
        cards.append(
            f'<a href="{a["link"]}" target="_blank" rel="noopener" '
            f'style="display:block;background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'text-decoration:none;color:#c9d1d9;overflow:hidden;transition:border-color .15s;" '
            f'onmouseover="this.style.borderColor=\'#58a6ff\'" '
            f'onmouseout="this.style.borderColor=\'#30363d\'">'
            f'{thumb_html}'
            f'<div style="padding:10px 12px;">'
            f'<div style="font-weight:600;font-size:0.92em;line-height:1.35;margin-bottom:6px;">{a["title"]}</div>'
            f'<div style="color:#8b949e;font-size:0.75em;">{a["pub"]}</div>'
            f'</div></a>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin-top:10px;font-size:0.85em;">'
        f'<a href="{profile_url}" target="_blank" rel="noopener" style="color:#58a6ff;">'
        f'📒 noteで他の記事も読む →</a></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# サイドバー：検索フォーム
# ============================================================
with st.sidebar:
    st.header("🔍 選手検索")

    player_type = st.radio(
        "選手タイプ", ["投手 (Pitcher)", "打者 (Batter)"],
        horizontal=True, key="player_type_radio",
    )
    is_pitcher = player_type.startswith("投手")

    _all_players = fetch_all_active_players()
    _options     = build_player_options(_all_players)
    _id_to_label = {pid: lbl for lbl, pid, _ in _options}
    _label_to_opt = {lbl: (pid, fn) for lbl, pid, fn in _options}

    PLACEHOLDER_LABEL = "— 選手を選択（英名・漢字・カタカナ・チーム略称で検索可）—"

    # 外部(キュレーション等)からの選択を反映
    _default_idx = 0
    _pending = st.session_state.get("ss_pending_label")
    if _pending and _pending in _label_to_opt:
        _default_idx = 1 + list(_label_to_opt.keys()).index(_pending)
        st.session_state["ss_pending_label"] = None

    selected_label = st.selectbox(
        "選手",
        options=[PLACEHOLDER_LABEL] + list(_label_to_opt.keys()),
        index=_default_idx,
        key="player_select",
        help="名前の一部・チーム略称 (例: LAD)・日本語表記でも絞り込めます",
    )

    season = st.selectbox(
        "シーズン",
        options=list(reversed(SEASON_DATES.keys())),
        index=0,
    )
    min_pitches = 10  # 球種別集計の最低ピッチ数 (UI から非表示)
    search_btn  = st.button("検索する", type="primary", use_container_width=True)

    if st.session_state.get("ss_player_name"):
        st.divider()
        st.button("🏠 TOPページへ戻る", on_click=_reset_to_top,
                  use_container_width=True, key="reset_top_side")
        _pn   = st.session_state["ss_player_name"]
        _pid  = st.session_state.get("ss_player_id", "")
        _psea = st.session_state.get("ss_season", "")
        _ptype = st.session_state.get("ss_player_type", "")
        st.markdown(
            f'<div class="player-card">'
            f'<b>📋 表示中の選手</b><br><br>'
            f'🏟️ <b>{_pn}</b><br>'
            f'🎯 タイプ: <b>{_ptype}</b><br>'
            f'🆔 MLBAM ID: <code>{_pid}</code><br>'
            f'📅 シーズン: <b>{_psea}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption("データソース: Baseball Savant (Statcast) via pybaseball / MLB Stats API")

# ============================================================
# ページヘッダー
# ============================================================
_title_cols = st.columns([4, 1])
with _title_cols[0]:
    st.title("⚾ MLB Player Viewer")
    st.caption("Statcast データをもとに投手/打者のパフォーマンスを可視化します")
with _title_cols[1]:
    if st.session_state.get("ss_raw_df") is not None:
        st.write("")  # 垂直揃え用スペーサー
        st.button("🏠 TOPへ戻る", on_click=_reset_to_top,
                  use_container_width=True, type="secondary")

# ============================================================
# メイン処理
# ============================================================
ss = st.session_state
has_cached = ss.get("ss_raw_df") is not None


def _trigger_curated_pick(p: dict, season_val: int):
    """on_click コールバック: 疑似 lookup_df をセットして再実行させる"""
    st.session_state["ss_lookup_df"] = pd.DataFrame([{
        "name_first":       p["first"],
        "name_last":        p["last"],
        "key_mlbam":        p["id"],
        "mlb_played_first": np.nan,
        "mlb_played_last":  np.nan,
    }])
    st.session_state["ss_base_key"]     = f"{p['type']}|{p['last']}|{p['first']}|{season_val}|curated"
    st.session_state["ss_player_type"]  = p["type"]
    st.session_state["ss_raw_df"]       = None
    st.session_state["ss_full_key"]     = ""
    st.session_state["ss_chosen_label"] = None
    # コールバック内ではウィジェットkeyの変更も許可される
    st.session_state["player_type_radio"] = p["type"]


if not search_btn and not has_cached and ss.get("ss_lookup_df") is None:
    curated_list, is_live = get_curated_players(season)

    # 1) ヒーローストリップ: OPS/ERAリーダー
    render_hero_strip(curated_list)

    # 2) モバイル向け補助案内(PCではサイドバーがデフォルト表示)
    st.info(
        "👈 左のサイドバー(モバイルの方は画面左上の **≫** アイコンをタップ)から"
        "選手タイプ・選手名を入力して「検索する」を押してください。"
    )

    # 3) 注目選手セクション
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.subheader("⭐ 注目選手 (クリックで即ロード)")
    with header_cols[1]:
        if st.button("🔄 リストを更新", use_container_width=True):
            fetch_curated_players.clear()
            st.rerun()

    source_label = "MLB Stats API リーダーボードから自動生成" if is_live \
                   else "⚠️ API 取得失敗 — フォールバック表示"
    st.caption(
        f"{season} シーズン · OPS上位打者 + ERA上位投手 · {source_label}"
        f"  (12時間キャッシュ)"
    )

    N_COLS = 4
    for row_start in range(0, len(curated_list), N_COLS):
        cols = st.columns(N_COLS)
        for col, p in zip(cols, curated_list[row_start:row_start + N_COLS]):
            with col:
                img_url = player_headshot_url(p["id"])
                role_color = "#E63946" if p["type"].startswith("投手") else "#2A9D8F"
                stat_name = p.get("stat_name", "") or ""
                stat_val  = p.get("stat_val", "")
                stat_label_disp = (
                    "OPS" if stat_name == "onBasePlusSlugging"
                    else "ERA" if stat_name == "earnedRunAverage"
                    else (stat_name or "").upper()
                )
                stat_block = ""
                if stat_val != "" and stat_val is not None and stat_label_disp:
                    stat_block = (
                        f'<div class="curated-stat-label">{stat_label_disp}</div>'
                        f'<div class="curated-stat">{stat_val}</div>'
                    )
                st.markdown(
                    f"""
                    <div style="background:#161b22;border:1px solid #30363d;
                                border-radius:10px;padding:12px;text-align:center;
                                margin-bottom:6px;">
                        <img src="{img_url}" style="width:96px;height:96px;
                             border-radius:50%;border:2px solid #30363d;
                             object-fit:cover;background:#0d1117;"
                             onerror="this.style.visibility='hidden'"/>
                        <div style="color:#e6edf3;font-weight:700;margin-top:8px;">
                            {p['first'].title()} {p['last'].title()}
                        </div>
                        <div style="color:{role_color};font-size:0.78rem;font-weight:600;
                                    margin-top:2px;">
                            {p['type']}
                        </div>
                        {stat_block}
                        <div style="color:#8b949e;font-size:0.72rem;margin-top:4px;
                                    min-height:1.2em;">
                            {p['note']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button("📊 このデータを見る",
                          key=f"pick_{p['id']}",
                          on_click=_trigger_curated_pick,
                          args=(p, season),
                          use_container_width=True)

    # 4) note 最新記事セクション
    render_latest_notes(max_n=6)

    render_footer()
    st.stop()

if search_btn:
    if selected_label == PLACEHOLDER_LABEL:
        st.error("選手を選択してください。")
        st.stop()
    _opt = _label_to_opt.get(selected_label)
    if not _opt:
        st.error("選択が無効です。")
        st.stop()
    _pid, _fn = _opt
    _parts = _fn.strip().split(" ", 1)
    _first = _parts[0] if _parts else ""
    _last  = _parts[1] if len(_parts) > 1 else _first

    _base_key = f"{player_type}|{_pid}|{season}"
    if ss.get("ss_base_key") != _base_key or not has_cached:
        ss.ss_lookup_df = pd.DataFrame([{
            "name_first":       _first,
            "name_last":        _last,
            "key_mlbam":        _pid,
            "mlb_played_first": np.nan,
            "mlb_played_last":  np.nan,
        }])
        ss.ss_base_key    = _base_key
        ss.ss_raw_df      = None
        ss.ss_full_key    = ""
        ss.ss_player_type = player_type

lookup_df = ss.get("ss_lookup_df")
if lookup_df is None or lookup_df.empty:
    st.info("← サイドバーに選手名を入力して「検索する」を押してください。")
    st.stop()

if len(lookup_df) > 1:
    options = {
        f"{row['name_first'].title()} {row['name_last'].title()} "
        f"(MLB: {int(row['mlb_played_first']) if pd.notna(row['mlb_played_first']) else '?'}"
        f"–{int(row['mlb_played_last']) if pd.notna(row['mlb_played_last']) else '?'})": idx
        for idx, row in lookup_df.iterrows()
    }
    saved_label  = ss.get("ss_chosen_label", list(options.keys())[0])
    default_idx  = list(options.keys()).index(saved_label) if saved_label in options else 0
    chosen_label = st.selectbox("複数の候補が見つかりました。選手を選んでください:",
                                list(options.keys()), index=default_idx)
    chosen_row   = lookup_df.loc[options[chosen_label]]
else:
    chosen_label = None
    chosen_row   = lookup_df.iloc[0]

player_id   = int(chosen_row["key_mlbam"])
player_name = f"{chosen_row['name_first'].title()} {chosen_row['name_last'].title()}"
full_key    = f"{ss.get('ss_base_key', '')}|{player_id}"

if ss.get("ss_full_key") != full_key or ss.get("ss_raw_df") is None:
    start_date, end_date = SEASON_DATES[season]
    with st.spinner(
        f"🔄 {player_name} の {season} シーズン Statcast データを取得中... "
        "(初回は10〜20秒ほどかかります)"
    ):
        if is_pitcher:
            raw_df = fetch_statcast_pitcher(player_id, start_date, end_date)
        else:
            raw_df = fetch_statcast_batter(player_id, start_date, end_date)
    ss.ss_raw_df       = raw_df
    ss.ss_player_name  = player_name
    ss.ss_player_id    = player_id
    ss.ss_full_key     = full_key
    ss.ss_chosen_label = chosen_label
    ss.ss_season       = season
    ss.ss_player_type  = player_type
else:
    raw_df      = ss.ss_raw_df
    player_name = ss.ss_player_name
    season      = ss.ss_season
    player_type = ss.ss_player_type
    is_pitcher  = player_type.startswith("投手")

if raw_df is None or raw_df.empty:
    st.warning(
        f"{player_name} の {ss.ss_season} シーズンの{'投手' if is_pitcher else '打者'}データが見つかりませんでした。\n\n"
        "考えられる原因:\n"
        "- その年は該当タイプとして出場していない\n"
        "- Statcast 収録対象外のシーズン（2014 以前）\n"
        "- 名前のスペルが異なる"
    )
    st.stop()

# ============================================================
# プロフィールヘッダー
# ============================================================
profile = fetch_player_profile(player_id)
render_profile_card(profile, player_name, player_id)

# --- 投手専用 FanGraphs 高度指標 ---
if is_pitcher:
    _adv_result = fetch_pitcher_advanced(player_id, int(season), raw_df)
    adv = _adv_result.get("stats", {}) if isinstance(_adv_result, dict) else {}
    adv_diag = _adv_result.get("diag", "") if isinstance(_adv_result, dict) else ""
    if adv and any(v is not None for v in adv.values()):
        def _fmt(v, spec):
            return f"{v:{spec}}" if v is not None and not pd.isna(v) else "—"

        def _delta_plus(v):
            """100 を基準に +N / -N を表示 (Stuff+ 系用)"""
            if v is None or pd.isna(v):
                return None
            diff = v - 100
            return f"{diff:+.0f} vs 平均"

        ac1, ac2, ac3, ac4, ac5, ac6 = st.columns(6)
        ac1.metric("Stuff+",    _fmt(adv.get("Stuff+"), ".0f"),
                   _delta_plus(adv.get("Stuff+")),
                   help="球質指標 (FanGraphs)。100=平均、高いほど優秀")
        ac2.metric("Location+", _fmt(adv.get("Location+"), ".0f"),
                   _delta_plus(adv.get("Location+")),
                   help="制球指標。100=平均、高いほど優秀")
        ac3.metric("Pitching+", _fmt(adv.get("Pitching+"), ".0f"),
                   _delta_plus(adv.get("Pitching+")),
                   help="Stuff+ と Location+ の合成指標")
        ac4.metric("FIP",       _fmt(adv.get("FIP"), ".2f"),
                   help="Fielding Independent Pitching (低いほど優秀)")
        ac5.metric("xFIP",      _fmt(adv.get("xFIP"), ".2f"),
                   help="本塁打率を平均化した FIP (低いほど優秀)")
        ac6.metric("ERA / WAR",
                   f"{_fmt(adv.get('ERA'), '.2f')} / {_fmt(adv.get('WAR'), '.1f')}",
                   help=f"IP: {_fmt(adv.get('IP'), '.1f')}  ·  "
                        f"K/9: {_fmt(adv.get('K/9'), '.1f')}  ·  "
                        f"BB/9: {_fmt(adv.get('BB/9'), '.1f')}")
        st.caption(f"📈 FanGraphs 高度指標 ({season} シーズン) — "
                   f"Stuff+/Location+/Pitching+ は 2020+ のみ利用可能")
    else:
        st.caption(f"⚠️ FanGraphs 高度指標を取得できませんでした — 詳細: {adv_diag}")

# ============================================================
# データ整形
# ============================================================
COLS = [
    "pitch_type", "pfx_x", "pfx_z", "release_speed", "plate_x", "plate_z",
    "sz_top", "sz_bot", "release_spin_rate", "type", "description",
    "estimated_woba_using_speedangle", "launch_speed", "launch_angle",
    "game_date", "game_pk", "home_team", "away_team", "inning",
    "arm_angle", "release_pos_x", "release_pos_y", "release_pos_z",
    "release_extension", "spin_axis", "stand", "p_throws", "events",
    "hc_x", "hc_y", "bb_type", "zone", "balls", "strikes",
]
available = [c for c in COLS if c in raw_df.columns]
df_all = raw_df[available].dropna(
    subset=["pitch_type", "pfx_x", "pfx_z", "release_speed", "plate_x", "plate_z"]
).copy()
df_all["pfx_x_in"] = df_all["pfx_x"] * 12
df_all["pfx_z_in"] = df_all["pfx_z"] * 12
if "game_date" in df_all.columns:
    df_all["game_date"] = pd.to_datetime(df_all["game_date"]).dt.date

# ============================================================
# 試合ログ & 試合フィルタ
# ============================================================
if "game_date" in df_all.columns and "home_team" in df_all.columns:
    game_log = (
        df_all.groupby(["game_date", "game_pk", "home_team", "away_team"])
        .agg(
            pitches=("pitch_type", "size"),
            avg_velo=("release_speed", "mean"),
            innings=("inning", "max") if "inning" in df_all.columns else ("pitch_type", "size"),
        )
        .reset_index()
        .sort_values("game_date")
    )
    game_log["対戦"]  = game_log["away_team"] + "  @  " + game_log["home_team"]
    game_log["試合日"] = game_log["game_date"].astype(str)

    log_label = "登板" if is_pitcher else "出場"
    with st.expander(f"📅 試合ログ（全 {len(game_log)} {log_label}）", expanded=False):
        log_disp = game_log[["試合日", "対戦", "pitches", "avg_velo", "innings"]].copy()
        pitch_col_name = "投球数" if is_pitcher else "被投球数"
        log_disp.columns = ["試合日", "対戦カード", pitch_col_name, "平均球速 (mph)", "最終イニング"]
        log_disp["平均球速 (mph)"] = log_disp["平均球速 (mph)"].round(1)
        st.dataframe(log_disp.set_index("試合日"), use_container_width=True)

    game_options = [f"全試合（{season} シーズン合算）"] + [
        f"{row['試合日']}  {row['対戦']}  ({int(row['pitches'])} 球)"
        for _, row in game_log.iterrows()
    ]
    selected_game = st.selectbox("🎮 表示する試合を選択", game_options)

    if selected_game.startswith("全試合"):
        df         = df_all.copy()
        game_label = f"{ss.ss_season} シーズン合算"
    else:
        idx        = game_options.index(selected_game) - 1
        gk         = game_log.iloc[idx]["game_pk"]
        df         = df_all[df_all["game_pk"] == gk].copy()
        gd         = game_log.iloc[idx]["試合日"]
        opp        = game_log.iloc[idx]["対戦"]
        game_label = f"{gd}  {opp}"
else:
    df         = df_all.copy()
    game_label = f"{ss.ss_season} シーズン合算"

# ============================================================
# 対戦相手フィルタ
# ============================================================
hand_filter = None  # デフォルト: フィルタなし
if is_pitcher:
    if "stand" in df.columns and df["stand"].notna().any():
        hand_options = {"全打者": None, "vs 右打者 (RHB)": "R", "vs 左打者 (LHB)": "L"}
        hand_sel     = st.radio("⚾ 対戦打者", list(hand_options.keys()), horizontal=True)
        hand_filter  = hand_options[hand_sel]
        if hand_filter:
            df = df[df["stand"] == hand_filter].copy()
else:
    if "p_throws" in df.columns and df["p_throws"].notna().any():
        hand_options = {"全投手": None, "vs 右投手 (RHP)": "R", "vs 左投手 (LHP)": "L"}
        hand_sel     = st.radio("⚾ 対戦投手", list(hand_options.keys()), horizontal=True)
        hand_filter  = hand_options[hand_sel]
        if hand_filter:
            df = df[df["p_throws"] == hand_filter].copy()


# ============================================================
# 投手ブランチ
# ============================================================
def pitcher_summary_stats(group):
    total   = len(group)
    swings  = group["description"].isin(SWING_DESC).sum() if "description" in group else 0
    whiffs  = group["description"].isin(WHIFF_DESC).sum() if "description" in group else 0
    csw     = group["description"].isin(CSW_DESC).sum()   if "description" in group else 0
    strikes = (group["type"] == "S").sum() + (group["type"] == "X").sum() \
              if "type" in group else 0

    # Zone%: ゾーン内 (zone 1-9) 割合
    zone_pct = np.nan
    if "zone" in group:
        z = group["zone"].dropna()
        if len(z):
            zone_pct = (z.between(1, 9)).sum() / len(z) * 100

    # Chase%: ゾーン外のピッチに対するスイング割合
    chase_pct = np.nan
    if "zone" in group and "description" in group:
        out_zone = group[(group["zone"] > 9) | (group["zone"].isna() == False) & ~group["zone"].between(1, 9)]
        out_zone = group[~group["zone"].between(1, 9)] if "zone" in group else None
        if out_zone is not None and len(out_zone):
            chase_pct = out_zone["description"].isin(SWING_DESC).sum() / len(out_zone) * 100

    stats = {
        "count":      total,
        "avg_speed":  group["release_speed"].mean(),
        "avg_pfx_x":  group["pfx_x_in"].mean(),
        "avg_pfx_z":  group["pfx_z_in"].mean(),
        "strike_pct": strikes / total  * 100 if total  else 0,
        "whiff_pct":  whiffs  / swings * 100 if swings else 0,
        "csw_pct":    csw     / total  * 100 if total  else 0,
        "zone_pct":   zone_pct,
        "chase_pct":  chase_pct,
    }
    if "release_spin_rate" in group:
        stats["avg_spin"] = group["release_spin_rate"].mean()
    if "estimated_woba_using_speedangle" in group:
        in_play = group["estimated_woba_using_speedangle"].dropna()
        stats["xwoba"] = in_play.mean() if len(in_play) else float("nan")
    return pd.Series(stats)


def batter_pitch_stats(group):
    total    = len(group)
    swings   = group["description"].isin(SWING_DESC).sum() if "description" in group else 0
    whiffs   = group["description"].isin(WHIFF_DESC).sum() if "description" in group else 0

    # 打率系
    ab_mask = group["events"].isin(AB_EVENTS) if "events" in group else pd.Series([], dtype=bool)
    hits    = group["events"].isin(HIT_EVENTS).sum() if "events" in group else 0
    ab      = ab_mask.sum() if len(ab_mask) else 0
    ba      = hits / ab if ab else np.nan

    stats = {
        "count":     total,
        "avg_speed": group["release_speed"].mean(),
        "whiff_pct": whiffs / swings * 100 if swings else 0,
        "swing_pct": swings / total * 100 if total else 0,
        "ba":        ba,
        "ab":        ab,
        "hits":      hits,
    }
    if "estimated_woba_using_speedangle" in group:
        ip = group["estimated_woba_using_speedangle"].dropna()
        stats["xwoba"] = ip.mean() if len(ip) else float("nan")
    if "launch_speed" in group:
        stats["avg_ev"] = group["launch_speed"].mean()
    return pd.Series(stats)


# ============================================================
# 集計
# ============================================================
if is_pitcher:
    summary = (
        df.groupby("pitch_type")
        .apply(pitcher_summary_stats, include_groups=False)
        .reset_index()
    )
else:
    summary = (
        df.groupby("pitch_type")
        .apply(batter_pitch_stats, include_groups=False)
        .reset_index()
    )
summary = summary[summary["count"] >= min_pitches].copy()

if summary.empty:
    st.warning(f"最低{min_pitches}球以上の球種データがありません。スライダーを下げてください。")
    st.stop()

total_pitches        = summary["count"].sum()
summary["usage_pct"] = summary["count"] / total_pitches * 100
summary["label"]     = summary["pitch_type"].map(lambda c: PITCH_LABEL.get(c, c))
summary = summary.sort_values("count", ascending=False).reset_index(drop=True)

pitch_colors = {
    row["pitch_type"]: COLORS[i % len(COLORS)]
    for i, row in summary.iterrows()
}

# ============================================================
# サブヘッダー
# ============================================================
st.divider()
role_label = "投手" if is_pitcher else "打者"
st.subheader(f"📊 {role_label} 成績 — {ss.ss_season} シーズン")
st.caption(game_label)

# ============================================================
# メトリクスカード
# ============================================================
if is_pitcher:
    top_pitch  = summary.iloc[0]
    best_whiff = summary.loc[summary["whiff_pct"].idxmax()]
    best_csw   = summary.loc[summary["csw_pct"].idxmax()]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("総投球数",     f"{int(total_pitches):,}")
    c2.metric("球種数",       f"{len(summary)}")
    c3.metric("主球種",       f"{top_pitch['label'].split(' ')[0]}  {top_pitch['avg_speed']:.1f} mph")
    c4.metric("最高空振り率", f"{best_whiff['whiff_pct']:.1f}%",
              help=f"球種: {best_whiff['label']}")
    c5.metric("最高 CSW%",    f"{best_csw['csw_pct']:.1f}%",
              help=f"球種: {best_csw['label']}")
else:
    # 打者サマリー全体
    all_ab    = df["events"].isin(AB_EVENTS).sum() if "events" in df.columns else 0
    all_hits  = df["events"].isin(HIT_EVENTS).sum() if "events" in df.columns else 0
    all_hr    = (df["events"] == "home_run").sum() if "events" in df.columns else 0
    ba_all    = all_hits / all_ab if all_ab else np.nan
    xwoba_all = df["estimated_woba_using_speedangle"].dropna().mean() \
                if "estimated_woba_using_speedangle" in df.columns else np.nan
    ev_all    = df["launch_speed"].dropna().mean() if "launch_speed" in df.columns else np.nan
    la_all    = df["launch_angle"].dropna().mean() if "launch_angle" in df.columns else np.nan
    swings    = df["description"].isin(SWING_DESC).sum() if "description" in df.columns else 0
    whiffs    = df["description"].isin(WHIFF_DESC).sum() if "description" in df.columns else 0
    whiff_all = whiffs / swings * 100 if swings else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("打数 (AB)", f"{int(all_ab):,}")
    c2.metric("安打 / 本塁打", f"{int(all_hits)} / {int(all_hr)}")
    c3.metric("打率 (BA)", f"{ba_all:.3f}" if not pd.isna(ba_all) else "—")
    c4.metric("xwOBA", f"{xwoba_all:.3f}" if not pd.isna(xwoba_all) else "—")
    c5.metric("平均打球速度", f"{ev_all:.1f} mph" if not pd.isna(ev_all) else "—",
              help=f"平均打球角度: {la_all:.1f}°" if not pd.isna(la_all) else None)
    c6.metric("空振り率", f"{whiff_all:.1f}%")

# ============================================================
# Pitch Summary テーブル
# ============================================================
st.subheader("📊 Pitch Summary")

if is_pitcher:
    tbl_cols = ["label", "count", "usage_pct", "avg_speed", "avg_pfx_x",
                "avg_pfx_z", "strike_pct", "whiff_pct", "csw_pct", "zone_pct", "chase_pct"]
    tbl_cols = [c for c in tbl_cols if c in summary.columns]
    tbl = summary[tbl_cols].copy()
    if "avg_spin" in summary.columns:
        tbl["avg_spin"] = summary["avg_spin"]
    if "xwoba" in summary.columns:
        tbl["xwoba"] = summary["xwoba"]

    col_rename = {
        "label": "球種", "count": "投球数", "usage_pct": "使用率 %",
        "avg_speed": "平均球速 (mph)", "avg_pfx_x": "横変化 (in)", "avg_pfx_z": "縦変化 (in)",
        "strike_pct": "ストライク %", "whiff_pct": "空振り %", "csw_pct": "CSW %",
        "zone_pct": "Zone %", "chase_pct": "Chase %",
        "avg_spin": "回転数 (rpm)", "xwoba": "xwOBA",
    }
    fmt = {
        "投球数": "{:.0f}", "使用率 %": "{:.1f}", "平均球速 (mph)": "{:.1f}",
        "横変化 (in)": "{:.1f}", "縦変化 (in)": "{:.1f}",
        "ストライク %": "{:.1f}", "空振り %": "{:.1f}", "CSW %": "{:.1f}",
        "Zone %": "{:.1f}", "Chase %": "{:.1f}",
        "回転数 (rpm)": "{:.0f}", "xwOBA": "{:.3f}",
    }
    tbl = tbl.rename(columns=col_rename).set_index("球種")
    styled = tbl.style.format({k: v for k, v in fmt.items() if k in tbl.columns})
    for col in ["空振り %", "CSW %"]:
        if col in tbl.columns:
            styled = styled.background_gradient(cmap="RdYlGn", subset=[col], vmin=0, vmax=40)
    if "xwOBA" in tbl.columns:
        styled = styled.background_gradient(cmap="RdYlGn_r", subset=["xwOBA"], vmin=0.2, vmax=0.5)
    st.dataframe(styled, use_container_width=True)

    with st.expander("📌 指標の説明"):
        st.markdown("""
| 指標 | 説明 |
|------|------|
| 使用率 % | 全投球に占めるその球種の割合 |
| ストライク % | ストライク判定+インプレーの割合 |
| 空振り % | スイングのうち空振りになった割合 (Whiff Rate) |
| CSW % | Called Strike + Whiff の合計割合 |
| Zone % | ストライクゾーン (1-9) に投じた割合 |
| Chase % | ゾーン外へのスイング誘発率 |
| 回転数 | リリース時の平均スピン (rpm) |
| xwOBA | インプレー時の推定加重出塁率 (低いほど投手有利) |
""")
else:
    tbl_cols = ["label", "count", "usage_pct", "avg_speed", "ab", "hits",
                "ba", "xwoba", "swing_pct", "whiff_pct", "avg_ev"]
    tbl_cols = [c for c in tbl_cols if c in summary.columns]
    tbl = summary[tbl_cols].copy()
    col_rename = {
        "label": "球種", "count": "被投球数", "usage_pct": "配球率 %",
        "avg_speed": "平均球速 (mph)", "ab": "打数", "hits": "安打",
        "ba": "打率", "xwoba": "xwOBA",
        "swing_pct": "スイング %", "whiff_pct": "空振り %", "avg_ev": "平均EV (mph)",
    }
    fmt = {
        "被投球数": "{:.0f}", "配球率 %": "{:.1f}", "平均球速 (mph)": "{:.1f}",
        "打数": "{:.0f}", "安打": "{:.0f}",
        "打率": "{:.3f}", "xwOBA": "{:.3f}",
        "スイング %": "{:.1f}", "空振り %": "{:.1f}", "平均EV (mph)": "{:.1f}",
    }
    tbl = tbl.rename(columns=col_rename).set_index("球種")
    styled = tbl.style.format({k: v for k, v in fmt.items() if k in tbl.columns})
    if "xwOBA" in tbl.columns:
        styled = styled.background_gradient(cmap="RdYlGn", subset=["xwOBA"], vmin=0.2, vmax=0.5)
    if "打率" in tbl.columns:
        styled = styled.background_gradient(cmap="RdYlGn", subset=["打率"], vmin=0.15, vmax=0.35)
    if "空振り %" in tbl.columns:
        styled = styled.background_gradient(cmap="RdYlGn_r", subset=["空振り %"], vmin=10, vmax=40)
    st.dataframe(styled, use_container_width=True)

    with st.expander("📌 指標の説明"):
        st.markdown("""
| 指標 | 説明 |
|------|------|
| 配球率 % | 対戦中にその球種を投じられた割合 |
| 打数 | その球種で結果が確定した打席数 |
| 打率 | 安打 / 打数 |
| xwOBA | インプレー時の推定加重出塁率 (高いほど打者有利) |
| スイング % | 球種別スイング率 |
| 空振り % | スイング中の空振り率 |
| 平均EV | 打球速度の平均 (Exit Velocity) |
""")

# ============================================================
# ダウンロードボタン
# ============================================================
dl1, dl2 = st.columns(2)
role_slug = "pitcher" if is_pitcher else "batter"
with dl1:
    st.download_button(
        "📥 ピッチデータ CSV",
        df.to_csv(index=False).encode("utf-8"),
        f"{player_name.replace(' ', '_')}_{season}_{role_slug}_pitches.csv",
        "text/csv",
        use_container_width=True,
    )
with dl2:
    st.download_button(
        "📥 サマリー CSV",
        summary.to_csv(index=False).encode("utf-8"),
        f"{player_name.replace(' ', '_')}_{season}_{role_slug}_summary.csv",
        "text/csv",
        use_container_width=True,
    )

# ============================================================
# タブ (投手 / 打者で分岐)
# ============================================================
if is_pitcher:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Movement Map", "📍 Pitch Locations", "💪 Arm & Release",
        "🔄 Active Spin", "📐 Movement Profile", "📈 Pitch Frequency",
    ])

    # ---- Tab 1: Movement Map ----
    with tab1:
        fig1 = go.Figure()
        for _, row in summary.iterrows():
            c    = pitch_colors[row["pitch_type"]]
            mask = df["pitch_type"] == row["pitch_type"]
            sub  = df.loc[mask]
            if len(sub) >= 20:
                fig1.add_trace(go.Histogram2dContour(
                    x=sub["pfx_x_in"], y=sub["pfx_z_in"],
                    colorscale=[[0, "rgba(0,0,0,0)"], [1, hex_to_rgba(c, 0.55)]],
                    showscale=False, ncontours=5, name=row["label"],
                    legendgroup=row["pitch_type"], showlegend=False,
                    hoverinfo="skip", line=dict(width=0),
                ))
            fig1.add_trace(go.Scatter(
                x=sub["pfx_x_in"], y=sub["pfx_z_in"], mode="markers",
                marker=dict(color=c, size=4, opacity=0.18),
                name=row["label"], legendgroup=row["pitch_type"], showlegend=True,
                hovertemplate=(f"<b>{row['label']}</b><br>H-Break: %{{x:.1f}} in<br>"
                               "V-Break: %{y:.1f} in<extra></extra>"),
            ))
            fig1.add_trace(go.Scatter(
                x=[row["avg_pfx_x"]], y=[row["avg_pfx_z"]],
                mode="markers+text",
                marker=dict(color=c, size=15, line=dict(color="white", width=1.5)),
                text=[row["pitch_type"]], textposition="top right",
                textfont=dict(color=c, size=11, family="Arial Black"),
                legendgroup=row["pitch_type"], showlegend=False,
                hovertemplate=(f"<b>{row['label']}</b><br>"
                               f"Avg H-Break: {row['avg_pfx_x']:.1f} in<br>"
                               f"Avg V-Break: {row['avg_pfx_z']:.1f} in<br>"
                               f"n = {int(row['count']):,}<extra></extra>"),
            ))
        fig1.add_hline(y=0, line_color="#556270", line_width=1)
        fig1.add_vline(x=0, line_color="#556270", line_width=1)
        dark_layout(fig1, f"Pitch Movement Map — {game_label}", height=560)
        fig1.update_layout(
            xaxis_title="Horizontal Break (in)  ←  Glove Side  |  Arm Side  →",
            yaxis_title="Vertical Break (in)  ↑ Rise  |  Drop ↓",
        )
        st.plotly_chart(fig1, use_container_width=True)

    # ---- Tab 2: Pitch Locations ----
    with tab2:
        sz_top     = df["sz_top"].mean() if "sz_top" in df.columns and df["sz_top"].notna().any() else 3.5
        sz_bot     = df["sz_bot"].mean() if "sz_bot" in df.columns and df["sz_bot"].notna().any() else 1.5
        PLATE_HALF = 17 / 24

        pitch_types = summary["pitch_type"].tolist()
        n           = len(pitch_types)
        MAX_COLS    = 4
        n_cols      = min(n, MAX_COLS)
        n_rows_loc  = (n + n_cols - 1) // n_cols

        subtitles = []
        for p in pitch_types:
            r_ = summary.loc[summary["pitch_type"] == p].iloc[0]
            subtitles.append(
                f"{r_['label']}<br>"
                f"<span style='font-size:10px'>n={int(r_['count']):,}  {r_['avg_speed']:.1f} mph</span>"
            )

        fig2 = make_subplots(
            rows=n_rows_loc, cols=n_cols, subplot_titles=subtitles,
            horizontal_spacing=0.06, vertical_spacing=0.14,
        )
        for i, ptype in enumerate(pitch_types):
            r_idx = i // n_cols + 1
            c_idx = i % n_cols + 1
            c     = pitch_colors[ptype]
            mask  = df["pitch_type"] == ptype
            sub   = df.loc[mask]
            fig2.add_trace(go.Scatter(
                x=sub["plate_x"], y=sub["plate_z"], mode="markers",
                marker=dict(color=c, size=5, opacity=0.28), showlegend=False,
                hovertemplate="plate_x: %{x:.2f} ft<br>plate_z: %{y:.2f} ft<extra></extra>",
            ), row=r_idx, col=c_idx)
            fig2.add_shape(type="rect",
                x0=-PLATE_HALF, x1=PLATE_HALF, y0=sz_bot, y1=sz_top,
                line=dict(color="white", width=1.5), row=r_idx, col=c_idx)
            for xv in [-PLATE_HALF / 3, PLATE_HALF / 3]:
                fig2.add_shape(type="line", x0=xv, x1=xv, y0=sz_bot, y1=sz_top,
                    line=dict(color="#666", width=0.8), row=r_idx, col=c_idx)
            for zv in [sz_bot + (sz_top - sz_bot) / 3,
                       sz_bot + 2 * (sz_top - sz_bot) / 3]:
                fig2.add_shape(type="line", x0=-PLATE_HALF, x1=PLATE_HALF, y0=zv, y1=zv,
                    line=dict(color="#666", width=0.8), row=r_idx, col=c_idx)
            axis_n = "" if i == 0 else str(i + 1)
            fig2.update_layout(**{
                f"xaxis{axis_n}": dict(range=[-2.5, 2.5], gridcolor=GC,
                                       zeroline=False, tickfont=dict(size=8, color=TC)),
                f"yaxis{axis_n}": dict(range=[0.5, 5.5], gridcolor=GC,
                                       zeroline=False, tickfont=dict(size=8, color=TC),
                                       scaleanchor=f"x{axis_n}", scaleratio=1),
            })
        # 各サブプロットに打者シルエット + ラベル
        # Catcher's view: RHB は 3B 側(左, plate_x<0) / LHB は 1B 側(右, plate_x>0)
        def _draw_batter(fig, r, c, side_x, hand_label):
            """簡易打者シルエット (頭+胴+バット) を描画"""
            col = "rgba(139,148,158,0.35)"
            fill = "rgba(139,148,158,0.12)"
            # 頭
            fig.add_shape(type="circle",
                x0=side_x - 0.18, x1=side_x + 0.18,
                y0=4.40, y1=4.78,
                line=dict(color=col, width=1.2), fillcolor=fill,
                row=r, col=c)
            # 胴体
            fig.add_shape(type="rect",
                x0=side_x - 0.22, x1=side_x + 0.22,
                y0=2.20, y1=4.35,
                line=dict(color=col, width=1.2), fillcolor=fill,
                row=r, col=c)
            # 脚
            fig.add_shape(type="rect",
                x0=side_x - 0.22, x1=side_x + 0.22,
                y0=0.55, y1=2.20,
                line=dict(color=col, width=1.2), fillcolor=fill,
                row=r, col=c)
            # バット (打席に構えた斜め線, ホームプレート側に伸ばす)
            bat_dir = -1 if side_x > 0 else 1  # ホーム方向
            fig.add_shape(type="line",
                x0=side_x + bat_dir * 0.15, y0=3.5,
                x1=side_x + bat_dir * 0.85, y1=4.8,
                line=dict(color=col, width=1.5),
                row=r, col=c)

        # 打者フィルタに応じて描画側を決定
        _show_rhb = hand_filter in (None, "R")
        _show_lhb = hand_filter in (None, "L")
        _show_labels = hand_filter is None  # 全打者時のみ L/R ラベルを表示

        for i in range(n):
            r_idx = i // n_cols + 1
            c_idx = i % n_cols + 1
            axis_n = "" if i == 0 else str(i + 1)

            if _show_rhb:
                _draw_batter(fig2, r_idx, c_idx, -1.85, "RHB")
                if _show_labels:
                    fig2.add_annotation(
                        xref=f"x{axis_n}", yref=f"y{axis_n}",
                        x=-1.85, y=0.25, text="RHB<br>(3B側)",
                        showarrow=False,
                        font=dict(color="#8b949e", size=8),
                        xanchor="center",
                    )
            if _show_lhb:
                _draw_batter(fig2, r_idx, c_idx,  1.85, "LHB")
                if _show_labels:
                    fig2.add_annotation(
                        xref=f"x{axis_n}", yref=f"y{axis_n}",
                        x=1.85, y=0.25, text="LHB<br>(1B側)",
                        showarrow=False,
                        font=dict(color="#8b949e", size=8),
                        xanchor="center",
                    )

        fig2.update_layout(
            paper_bgcolor=BG, plot_bgcolor=PBG, font=dict(color=TC),
            height=max(420, 330 * n_rows_loc), showlegend=False,
            margin=dict(t=70, b=40),
            title=dict(text=f"Pitch Locations — {game_label}<br>"
                            f"<sub>Catcher's view  "
                            f"(左=3B側/RHB, 右=1B側/LHB)</sub>",
                       x=0.5, font=dict(size=14, color=TC)),
        )
        for ann in fig2.layout.annotations:
            ann.font.color = TC
            ann.font.size  = 10
        st.plotly_chart(fig2, use_container_width=True)

    # ---- Tab 3: Arm Angle & Release Point ----
    with tab3:
        has_arm    = "arm_angle"         in df.columns and df["arm_angle"].notna().any()
        has_relpos = "release_pos_x"     in df.columns and df["release_pos_x"].notna().any()
        has_ext    = "release_extension" in df.columns and df["release_extension"].notna().any()

        if not has_arm and not has_relpos:
            st.info("このシーズンには Arm Angle / Release Point データがありません（2020 年以降で利用可能）。")
        else:
            if has_arm:
                arm_summary = (
                    df.groupby("pitch_type")["arm_angle"].mean()
                    .reindex(summary["pitch_type"]).dropna()
                )
                # 左右投手判定
                throws = "R"
                if "p_throws" in df.columns and df["p_throws"].notna().any():
                    throws = df["p_throws"].mode().iloc[0]
                is_lhp = throws == "L"
                sgn = -1 if is_lhp else 1
                shoulder_x = sgn * 0.8
                shoulder_y = 2.2

                fig_arm = go.Figure()

                # --- 背面視点の投手シルエット ---
                # 頭
                fig_arm.add_shape(type="circle",
                    x0=-0.45, x1=0.45, y0=2.75, y1=3.65,
                    line=dict(color="#8b949e", width=2),
                    fillcolor="rgba(139,148,158,0.12)")
                # 首
                fig_arm.add_shape(type="rect",
                    x0=-0.18, x1=0.18, y0=2.55, y1=2.78,
                    line=dict(color="#8b949e", width=1.5),
                    fillcolor="rgba(139,148,158,0.12)")
                # 胴体 (台形)
                fig_arm.add_shape(type="path",
                    path="M -0.85,2.35 L 0.85,2.35 L 0.70,-0.10 L -0.70,-0.10 Z",
                    line=dict(color="#8b949e", width=2),
                    fillcolor="rgba(139,148,158,0.10)")
                # 非投球側の腕 (下に垂直)
                non_throw_x = -shoulder_x
                fig_arm.add_trace(go.Scatter(
                    x=[non_throw_x, non_throw_x * 1.05],
                    y=[shoulder_y, 0.4],
                    mode="lines",
                    line=dict(color="#6D6875", width=10),
                    showlegend=False, hoverinfo="skip"))
                # 地面
                fig_arm.add_shape(type="line",
                    x0=-3.2, x1=3.2, y0=-0.25, y1=-0.25,
                    line=dict(color="#30363d", width=1))

                # --- 角度参照ライン (0° / 45° / 90°) ---
                ARM_LEN = 2.1
                for ref_angle, lbl in [(0, "0°\nサイド"),
                                       (45, "45°\n3/4"),
                                       (90, "90°\nオーバー"),
                                       (-30, "-30°\nサブマリン")]:
                    rad = math.radians(ref_angle)
                    dx  = sgn * math.cos(rad) * (ARM_LEN + 0.2)
                    dy  = math.sin(rad) * (ARM_LEN + 0.2)
                    fig_arm.add_shape(type="line",
                        x0=shoulder_x, x1=shoulder_x + dx,
                        y0=shoulder_y, y1=shoulder_y + dy,
                        line=dict(color="#30363d", width=1, dash="dot"))
                    fig_arm.add_annotation(
                        x=shoulder_x + dx * 1.08,
                        y=shoulder_y + dy * 1.08,
                        text=lbl.replace("\n", "<br>"),
                        showarrow=False,
                        font=dict(color="#6b7280", size=8),
                        xanchor="left" if not is_lhp else "right")

                # --- 肩マーカー ---
                fig_arm.add_trace(go.Scatter(
                    x=[shoulder_x], y=[shoulder_y],
                    mode="markers",
                    marker=dict(color="#e6edf3", size=12,
                                line=dict(color="#0d1117", width=1.5)),
                    showlegend=False, hoverinfo="skip"))

                # --- 球種別アームアングル ---
                # ラベル衝突を避けるため angle でソート
                arm_sorted = arm_summary.sort_values()
                for pt, ang in arm_sorted.items():
                    c = pitch_colors[pt]
                    lbl = summary.loc[summary["pitch_type"] == pt,
                                      "label"].values[0]
                    rad = math.radians(ang)
                    dx = sgn * math.cos(rad) * ARM_LEN
                    dy = math.sin(rad) * ARM_LEN
                    end_x, end_y = shoulder_x + dx, shoulder_y + dy
                    fig_arm.add_trace(go.Scatter(
                        x=[shoulder_x, end_x],
                        y=[shoulder_y, end_y],
                        mode="lines",
                        line=dict(color=c, width=5),
                        name=f"{lbl}  {ang:.1f}°",
                        legendgroup=pt,
                        hovertemplate=(f"<b>{lbl}</b><br>"
                                       f"Arm Angle: {ang:.1f}°<extra></extra>"),
                    ))
                    # 先端マーカー + ラベル
                    fig_arm.add_trace(go.Scatter(
                        x=[end_x], y=[end_y],
                        mode="markers+text",
                        marker=dict(color=c, size=14,
                                    line=dict(color="white", width=1.5)),
                        text=[pt],
                        textposition=("middle right" if not is_lhp
                                      else "middle left"),
                        textfont=dict(color=c, size=11,
                                      family="Arial Black"),
                        legendgroup=pt,
                        showlegend=False,
                        hovertemplate=(f"<b>{lbl}</b><br>"
                                       f"Arm Angle: {ang:.1f}°<extra></extra>"),
                    ))

                hand_label = "左投手 (LHP)" if is_lhp else "右投手 (RHP)"
                fig_arm.update_layout(
                    title=dict(
                        text=(f"Arm Angle by Pitch Type<br>"
                              f"<sub>{hand_label} · 背面視点  ·  "
                              f"0°=サイドアーム / +90°=オーバーハンド / "
                              f"−°=サブマリン</sub>"),
                        x=0.5, font=dict(size=14, color=TC),
                    ),
                    paper_bgcolor=BG, plot_bgcolor=PBG,
                    font=dict(color=TC),
                    xaxis=dict(range=[-3.4, 3.4], showgrid=False,
                               zeroline=False, showticklabels=False),
                    yaxis=dict(range=[-0.7, 4.6], showgrid=False,
                               zeroline=False, showticklabels=False,
                               scaleanchor="x", scaleratio=1),
                    height=560,
                    legend=dict(bgcolor="rgba(0,0,0,0)",
                                bordercolor=GC, borderwidth=1,
                                font=dict(color=TC, size=10),
                                orientation="v"),
                    margin=dict(l=30, r=30, t=80, b=30),
                )
                st.plotly_chart(fig_arm, use_container_width=True)

            if has_relpos:
                fig_rel = go.Figure()
                for _, row in summary.iterrows():
                    c    = pitch_colors[row["pitch_type"]]
                    mask = df["pitch_type"] == row["pitch_type"]
                    sub  = df.loc[mask]
                    mx   = sub["release_pos_x"].mean()
                    mz   = sub["release_pos_z"].mean()
                    fig_rel.add_trace(go.Scatter(
                        x=sub["release_pos_x"], y=sub["release_pos_z"], mode="markers",
                        marker=dict(color=c, size=4, opacity=0.15),
                        name=row["label"], legendgroup=row["pitch_type"],
                        showlegend=True, hoverinfo="skip",
                    ))
                    fig_rel.add_trace(go.Scatter(
                        x=[mx], y=[mz], mode="markers+text",
                        marker=dict(color=c, size=14, line=dict(color="white", width=1.5)),
                        text=[row["pitch_type"]], textposition="top right",
                        textfont=dict(color=c, size=10, family="Arial Black"),
                        legendgroup=row["pitch_type"], showlegend=False,
                        hovertemplate=(f"<b>{row['label']}</b><br>"
                                       "x: %{x:.2f} ft<br>z: %{y:.2f} ft<extra></extra>"),
                    ))
                dark_layout(fig_rel, "Release Point (Catcher's View)", height=450)
                fig_rel.update_layout(
                    xaxis_title="release_pos_x  (ft,  ← 3B side | 1B side →)",
                    yaxis_title="release_pos_z  (ft, height)",
                )
                st.plotly_chart(fig_rel, use_container_width=True)

            if has_ext:
                ext_summary = (
                    df.groupby("pitch_type")["release_extension"].mean()
                    .reindex(summary["pitch_type"]).dropna()
                )
                ext_labels = [summary.loc[summary["pitch_type"] == p, "label"].values[0]
                              for p in ext_summary.index]
                ext_colors = [pitch_colors[p] for p in ext_summary.index]
                fig_ext = go.Figure(go.Bar(
                    x=ext_summary.values, y=ext_labels, orientation="h",
                    marker_color=ext_colors,
                    text=[f"{v:.2f} ft" for v in ext_summary.values],
                    textposition="outside", textfont=dict(color=TC, size=10),
                    hovertemplate="%{y}: %{x:.2f} ft<extra></extra>",
                ))
                dark_layout(fig_ext, "Release Extension (distance past rubber)",
                            height=max(300, 55 * len(ext_summary) + 120))
                fig_ext.update_layout(
                    xaxis_title="Extension (ft)",
                    yaxis=dict(autorange="reversed", gridcolor=GC, tickfont=dict(color=TC)),
                )
                st.plotly_chart(fig_ext, use_container_width=True)

    # ---- Tab 4: Active Spin ----
    with tab4:
        has_spin = "release_spin_rate" in df.columns and df["release_spin_rate"].notna().any()
        has_axis = "spin_axis"         in df.columns and df["spin_axis"].notna().any()
        if not has_spin:
            st.info("このシーズンにはスピンデータがありません。")
        else:
            spin_summary = (
                df.groupby("pitch_type")
                .agg(avg_spin=("release_spin_rate", "mean"),
                     avg_axis=("spin_axis", "mean") if has_axis
                              else ("release_spin_rate", "count"))
                .reindex(summary["pitch_type"]).dropna(subset=["avg_spin"]).reset_index()
            )
            spin_summary["label"] = spin_summary["pitch_type"].map(
                lambda c: PITCH_LABEL.get(c, c))
            if has_axis:
                col_sp1, col_sp2 = st.columns(2)
            else:
                col_sp1 = st.container()
            with col_sp1:
                spin_colors = [pitch_colors[p] for p in spin_summary["pitch_type"]]
                fig_sr = go.Figure(go.Bar(
                    x=spin_summary["avg_spin"], y=spin_summary["label"],
                    orientation="h", marker_color=spin_colors,
                    text=[f"{v:.0f}" for v in spin_summary["avg_spin"]],
                    textposition="outside", textfont=dict(color=TC, size=10),
                    hovertemplate="%{y}: %{x:.0f} rpm<extra></extra>",
                ))
                dark_layout(fig_sr, "Spin Rate by Pitch Type",
                            height=max(300, 55 * len(spin_summary) + 120))
                fig_sr.update_layout(
                    xaxis_title="Avg Spin Rate (rpm)",
                    yaxis=dict(autorange="reversed", gridcolor=GC, tickfont=dict(color=TC)),
                )
                st.plotly_chart(fig_sr, use_container_width=True)
            if has_axis:
                with col_sp2:
                    fig_sa = go.Figure()
                    for _, row in spin_summary.iterrows():
                        if pd.isna(row.get("avg_axis")):
                            continue
                        angle_deg = float(row["avg_axis"])
                        c         = pitch_colors[row["pitch_type"]]
                        fig_sa.add_trace(go.Scatterpolar(
                            r=[0, 0.88], theta=[angle_deg, angle_deg],
                            mode="lines+markers+text",
                            line=dict(color=c, width=3),
                            marker=dict(size=[0, 13], color=c,
                                        line=dict(color="white", width=1.5)),
                            text=["", row["pitch_type"]],
                            textposition="top center",
                            textfont=dict(color=c, size=10, family="Arial Black"),
                            name=row["label"],
                            hovertemplate=(f"<b>{row['label']}</b><br>"
                                           f"Axis: {angle_deg:.1f}°<extra></extra>"),
                        ))
                    fig_sa.update_layout(
                        title=dict(text="Spin Axis (Clock Face)<br>"
                                        "<sup>0° = 12時(Backspin)  180° = 6時(Topspin)</sup>",
                                   x=0.5, font=dict(size=13, color=TC)),
                        polar=dict(
                            bgcolor=PBG,
                            angularaxis=dict(
                                tickmode="array",
                                tickvals=list(range(0, 360, 30)),
                                ticktext=["12","1","2","3","4","5","6","7","8","9","10","11"],
                                direction="clockwise", rotation=90,
                                gridcolor=GC, linecolor=GC,
                                tickfont=dict(color=TC, size=9),
                            ),
                            radialaxis=dict(visible=False, range=[0, 1.15]),
                        ),
                        paper_bgcolor=BG, font=dict(color=TC),
                        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TC)),
                        height=420, margin=dict(l=40, r=40, t=70, b=40),
                    )
                    st.plotly_chart(fig_sa, use_container_width=True)

    # ---- Tab 5: Movement Profile ----
    with tab5:
        col_mp1, col_mp2 = st.columns(2)
        with col_mp1:
            fig_mp1 = go.Figure()
            for _, row in summary.iterrows():
                c           = pitch_colors[row["pitch_type"]]
                total_break = math.sqrt(row["avg_pfx_x"] ** 2 + row["avg_pfx_z"] ** 2)
                fig_mp1.add_trace(go.Scatter(
                    x=[row["avg_speed"]], y=[total_break],
                    mode="markers+text",
                    marker=dict(color=c, size=16, line=dict(color="white", width=1.5)),
                    text=[f"{row['pitch_type']}<br>{row['avg_speed']:.1f}"],
                    textposition="top right", textfont=dict(color=c, size=9),
                    name=row["label"],
                    hovertemplate=(f"<b>{row['label']}</b><br>"
                                   f"Velocity: {row['avg_speed']:.1f} mph<br>"
                                   f"Total Break: {total_break:.1f} in<br>"
                                   f"n = {int(row['count']):,}<extra></extra>"),
                ))
            dark_layout(fig_mp1, "Velocity vs Total Break", height=420)
            fig_mp1.update_layout(
                xaxis_title="Avg Velocity (mph)",
                yaxis_title="Total Break — √(pfx_x² + pfx_z²)  (in)",
                showlegend=False,
            )
            st.plotly_chart(fig_mp1, use_container_width=True)

        with col_mp2:
            fig_mp2 = go.Figure()
            fig_mp2.add_hline(y=0, line_color="#556270", line_width=1)
            fig_mp2.add_vline(x=0, line_color="#556270", line_width=1)
            for _, row in summary.iterrows():
                c = pitch_colors[row["pitch_type"]]
                fig_mp2.add_annotation(
                    x=row["avg_pfx_x"], y=row["avg_pfx_z"], ax=0, ay=0,
                    xref="x", yref="y", axref="x", ayref="y",
                    arrowhead=3, arrowsize=1.2, arrowwidth=2.5,
                    arrowcolor=c, showarrow=True,
                )
                fig_mp2.add_trace(go.Scatter(
                    x=[row["avg_pfx_x"]], y=[row["avg_pfx_z"]],
                    mode="markers+text",
                    marker=dict(color=c, size=14, line=dict(color="white", width=1.5)),
                    text=[row["pitch_type"]], textposition="top right",
                    textfont=dict(color=c, size=10, family="Arial Black"),
                    name=row["label"],
                    hovertemplate=(f"<b>{row['label']}</b><br>"
                                   f"H-Break: {row['avg_pfx_x']:.1f} in<br>"
                                   f"V-Break: {row['avg_pfx_z']:.1f} in<extra></extra>"),
                ))
            dark_layout(fig_mp2,
                        "Movement Profile<br><sup>Arrow = direction & magnitude from gravity baseline</sup>",
                        height=420)
            fig_mp2.update_layout(
                xaxis_title="Horizontal Break (in)  ← Glove | Arm →",
                yaxis_title="Vertical Break (in)  ↑ Rise | Drop ↓",
                showlegend=False,
            )
            st.plotly_chart(fig_mp2, use_container_width=True)

    # ---- Tab 6: Pitch Frequency ----
    with tab6:
        if "game_date" not in df_all.columns:
            st.info("試合日データがないため Pitch Frequency を表示できません。")
        else:
            freq_df = df_all[df_all["pitch_type"].isin(summary["pitch_type"])].copy()
            freq_df["game_date"] = pd.to_datetime(freq_df["game_date"])
            game_pitch_cnt = (
                freq_df.groupby(["game_date", "pitch_type"]).size().reset_index(name="cnt")
            )
            game_total = freq_df.groupby("game_date").size().reset_index(name="total")
            game_pitch_cnt = game_pitch_cnt.merge(game_total, on="game_date")
            game_pitch_cnt["pct"] = game_pitch_cnt["cnt"] / game_pitch_cnt["total"] * 100
            pivot = (
                game_pitch_cnt.pivot(index="game_date", columns="pitch_type", values="pct")
                .fillna(0)
            )
            pivot       = pivot[[p for p in summary["pitch_type"] if p in pivot.columns]]
            pitch_order = list(pivot.columns)
            dates       = pivot.index

            fig_f1 = go.Figure()
            for ptype in pitch_order:
                c   = pitch_colors[ptype]
                lbl = PITCH_LABEL.get(ptype, ptype)
                fig_f1.add_trace(go.Scatter(
                    x=dates, y=pivot[ptype].values, mode="lines",
                    stackgroup="one", fillcolor=hex_to_rgba(c, 0.65),
                    line=dict(color=c, width=0.8), name=lbl,
                    hovertemplate=f"<b>{lbl}</b><br>%{{x|%Y-%m-%d}}: %{{y:.1f}}%<extra></extra>",
                ))
            dark_layout(fig_f1, "Pitch Usage % per Game (Stacked Area)", height=400)
            fig_f1.update_layout(
                xaxis_title="Game Date",
                yaxis=dict(range=[0, 100], title="Usage %", gridcolor=GC, tickfont=dict(color=TC)),
            )
            st.plotly_chart(fig_f1, use_container_width=True)

            fig_f2 = go.Figure()
            for ptype in pitch_order:
                c   = pitch_colors[ptype]
                lbl = PITCH_LABEL.get(ptype, ptype)
                fig_f2.add_trace(go.Scatter(
                    x=dates, y=pivot[ptype].values, mode="lines+markers",
                    line=dict(color=c, width=2), marker=dict(size=5, color=c), name=lbl,
                    hovertemplate=f"<b>{lbl}</b><br>%{{x|%Y-%m-%d}}: %{{y:.1f}}%<extra></extra>",
                ))
            dark_layout(fig_f2, "Pitch Usage % per Game (Line)", height=400)
            fig_f2.update_layout(xaxis_title="Game Date", yaxis_title="Usage %")
            st.plotly_chart(fig_f2, use_container_width=True)

else:
    # ============================================================
    # 打者タブ
    # ============================================================
    btab1, btab2, btab3, btab4, btab5 = st.tabs([
        "💥 Batted Ball", "📍 Zone Heatmap", "🎯 Spray Chart",
        "⚾ vs Pitch Type", "📈 時系列推移",
    ])

    # ---- Batter Tab 1: Batted Ball (EV × LA) ----
    with btab1:
        bb = df.dropna(subset=["launch_speed", "launch_angle"]).copy() \
            if {"launch_speed", "launch_angle"}.issubset(df.columns) else pd.DataFrame()
        if bb.empty:
            st.info("打球データ (launch_speed / launch_angle) がありません。")
        else:
            if "events" in bb.columns:
                bb["outcome"] = bb["events"].fillna("in_play")
            else:
                bb["outcome"] = "in_play"
            hit_map = {
                "single": ("安打", "#2A9D8F"),
                "double": ("二塁打", "#457B9D"),
                "triple": ("三塁打", "#F4A261"),
                "home_run": ("本塁打", "#E63946"),
            }
            bb["outcome_label"] = bb["outcome"].map(lambda e: hit_map.get(e, ("アウト/その他", "#6D6875"))[0])
            bb["outcome_color"] = bb["outcome"].map(lambda e: hit_map.get(e, ("その他", "#6D6875"))[1])

            fig_bb = go.Figure()
            for lbl, color in [("アウト/その他", "#6D6875"),
                               ("安打", "#2A9D8F"),
                               ("二塁打", "#457B9D"),
                               ("三塁打", "#F4A261"),
                               ("本塁打", "#E63946")]:
                sub = bb[bb["outcome_label"] == lbl]
                if sub.empty:
                    continue
                fig_bb.add_trace(go.Scatter(
                    x=sub["launch_angle"], y=sub["launch_speed"],
                    mode="markers",
                    marker=dict(color=color, size=8,
                                opacity=0.75 if lbl != "アウト/その他" else 0.35,
                                line=dict(color="white", width=0.3)),
                    name=f"{lbl} ({len(sub)})",
                    hovertemplate=(f"<b>{lbl}</b><br>"
                                   "LA: %{x:.1f}°<br>EV: %{y:.1f} mph<extra></extra>"),
                ))

            # Barrel zone の目安線 (EV>=98 & 8°-50° 近辺)
            fig_bb.add_shape(type="rect", x0=8, x1=50, y0=98, y1=120,
                             line=dict(color="#E63946", width=1, dash="dot"),
                             fillcolor="rgba(230,57,70,0.06)")
            fig_bb.add_annotation(x=29, y=118, text="Barrel Zone",
                                  showarrow=False, font=dict(color="#E63946", size=10))

            dark_layout(fig_bb, "打球分布 (Launch Angle × Exit Velocity)", height=520)
            fig_bb.update_layout(
                xaxis=dict(title="Launch Angle (°)", range=[-40, 80], gridcolor=GC),
                yaxis=dict(title="Exit Velocity (mph)", range=[30, 120], gridcolor=GC),
            )
            st.plotly_chart(fig_bb, use_container_width=True)

            # サマリー
            cA, cB, cC, cD = st.columns(4)
            cA.metric("打球数", f"{len(bb):,}")
            cB.metric("平均 EV", f"{bb['launch_speed'].mean():.1f} mph")
            cC.metric("ハードヒット%",
                      f"{(bb['launch_speed'] >= 95).mean() * 100:.1f}%",
                      help="EV ≥ 95 mph の打球の割合")
            barrel_mask = (bb["launch_speed"] >= 98) & bb["launch_angle"].between(8, 50)
            cD.metric("Barrel 推定%",
                      f"{barrel_mask.mean() * 100:.1f}%",
                      help="簡易推定: EV≥98 mph かつ LA 8°〜50°")

    # ---- Batter Tab 2: Zone Heatmap ----
    with btab2:
        if not {"plate_x", "plate_z"}.issubset(df.columns):
            st.info("投球位置データがありません。")
        else:
            metric_choice = st.radio(
                "ヒートマップ指標",
                ["Swing %", "Whiff %", "xwOBA", "被投球数"],
                horizontal=True,
            )
            xbins = np.linspace(-1.6, 1.6, 9)
            zbins = np.linspace(1.0, 4.2, 9)
            dfh = df.dropna(subset=["plate_x", "plate_z"]).copy()
            dfh["xbin"] = np.digitize(dfh["plate_x"], xbins) - 1
            dfh["zbin"] = np.digitize(dfh["plate_z"], zbins) - 1
            dfh = dfh[(dfh["xbin"] >= 0) & (dfh["xbin"] < len(xbins) - 1) &
                      (dfh["zbin"] >= 0) & (dfh["zbin"] < len(zbins) - 1)]

            if dfh.empty:
                st.info("データなし")
            else:
                if metric_choice == "Swing %":
                    dfh["val"] = dfh["description"].isin(SWING_DESC).astype(float) * 100
                    cell = dfh.groupby(["zbin", "xbin"])["val"].mean().unstack(fill_value=np.nan)
                    cmin, cmax, fmt_s, cs = 0, 100, ".0f", "Reds"
                elif metric_choice == "Whiff %":
                    swing_df = dfh[dfh["description"].isin(SWING_DESC)]
                    swing_df = swing_df.copy()
                    swing_df["val"] = swing_df["description"].isin(WHIFF_DESC).astype(float) * 100
                    cell = swing_df.groupby(["zbin", "xbin"])["val"].mean().unstack(fill_value=np.nan)
                    cmin, cmax, fmt_s, cs = 0, 60, ".0f", "Reds"
                elif metric_choice == "xwOBA":
                    cell = (dfh.groupby(["zbin", "xbin"])["estimated_woba_using_speedangle"]
                            .mean().unstack(fill_value=np.nan))
                    cmin, cmax, fmt_s, cs = 0.1, 0.7, ".3f", "RdYlGn"
                else:
                    cell = dfh.groupby(["zbin", "xbin"]).size().unstack(fill_value=0)
                    cmin, cmax, fmt_s, cs = 0, None, ".0f", "Blues"

                # reindex to full grid
                cell = cell.reindex(index=range(len(zbins) - 1),
                                    columns=range(len(xbins) - 1))
                xc = (xbins[:-1] + xbins[1:]) / 2
                zc = (zbins[:-1] + zbins[1:]) / 2

                text_vals = [[f"{v:{fmt_s}}" if pd.notna(v) else "" for v in row]
                             for row in cell.values]

                fig_hm = go.Figure(go.Heatmap(
                    z=cell.values, x=xc, y=zc,
                    colorscale=cs, zmin=cmin, zmax=cmax,
                    text=text_vals, texttemplate="%{text}",
                    textfont=dict(color="black", size=11),
                    hovertemplate="x: %{x:.2f} ft<br>z: %{y:.2f} ft<br>"
                                  f"{metric_choice}: %{{z:{fmt_s}}}<extra></extra>",
                ))
                # strike zone outline
                sz_top = df["sz_top"].mean() if df["sz_top"].notna().any() else 3.5
                sz_bot = df["sz_bot"].mean() if df["sz_bot"].notna().any() else 1.5
                PLATE_HALF = 17 / 24
                fig_hm.add_shape(type="rect",
                                 x0=-PLATE_HALF, x1=PLATE_HALF, y0=sz_bot, y1=sz_top,
                                 line=dict(color="white", width=2))
                dark_layout(fig_hm, f"{metric_choice} ヒートマップ (Catcher's View)", height=560)
                fig_hm.update_layout(
                    xaxis=dict(title="plate_x (ft)", range=[-2, 2]),
                    yaxis=dict(title="plate_z (ft)", range=[0.5, 4.8],
                               scaleanchor="x", scaleratio=1),
                )
                st.plotly_chart(fig_hm, use_container_width=True)

    # ---- Batter Tab 3: Spray Chart ----
    with btab3:
        if not {"hc_x", "hc_y"}.issubset(df.columns):
            st.info("打球位置データ (hc_x / hc_y) がありません。")
        else:
            sp = df.dropna(subset=["hc_x", "hc_y"]).copy()
            if sp.empty:
                st.info("打球位置データなし")
            else:
                # Statcast hc_x/hc_y は legacy ピクセル座標
                # home plate ≈ (125.42, 198.27)、y 軸は下向き、1 unit ≈ 2.5 ft
                # → home plate を (0,0)、外野方向 +y、フィート単位に変換
                SCALE_FT = 2.5
                sp["spray_x"] = (sp["hc_x"] - 125.42) * SCALE_FT
                sp["spray_y"] = (198.27 - sp["hc_y"]) * SCALE_FT
                # 球場内に収まらない明らかな外れ値を除外
                sp = sp[(sp["spray_y"] >= -20) & (sp["spray_y"] <= 500) &
                        (sp["spray_x"].abs() <= 400)].copy()

                event_map = {
                    "single":   ("単打",   "#2A9D8F"),
                    "double":   ("二塁打", "#457B9D"),
                    "triple":   ("三塁打", "#F4A261"),
                    "home_run": ("本塁打", "#E63946"),
                }
                fig_sp = go.Figure()

                # --- フィールド輪郭 (フィート) ---
                # 外野フェンス (ホームから約 330 ft、センター 400 ft の楕円近似)
                theta = np.linspace(-np.pi / 4, np.pi / 4, 120)
                left_line_ft  = 330
                center_ft     = 400
                # 楕円: 左右=330、中央=400 を通るよう補間
                fence_r = np.where(
                    np.abs(theta) < 1e-9,
                    center_ft,
                    np.sqrt(1.0 / ((np.sin(theta) / left_line_ft) ** 2 +
                                   (np.cos(theta) / center_ft) ** 2)),
                )
                fig_sp.add_trace(go.Scatter(
                    x=fence_r * np.sin(theta), y=fence_r * np.cos(theta),
                    mode="lines", line=dict(color="#4a5d7a", width=1.2),
                    showlegend=False, hoverinfo="skip",
                ))
                # 内野ダイヤモンド (90 ft の菱形、ホームから各ベースまで 90 ft)
                base = 90 / math.sqrt(2)
                diamond_x = [0,  base, 0, -base, 0]
                diamond_y = [0,  base, 2 * base, base, 0]
                fig_sp.add_trace(go.Scatter(
                    x=diamond_x, y=diamond_y, mode="lines",
                    line=dict(color="#8b949e", width=1.2),
                    showlegend=False, hoverinfo="skip",
                ))
                # ファウルライン
                for angle in [-np.pi / 4, np.pi / 4]:
                    fig_sp.add_trace(go.Scatter(
                        x=[0, left_line_ft * np.sin(angle)],
                        y=[0, left_line_ft * np.cos(angle)],
                        mode="lines", line=dict(color="#4a5d7a", width=1),
                        showlegend=False, hoverinfo="skip",
                    ))
                # 距離リング (200/300 ft)
                for r in [200, 300]:
                    fig_sp.add_trace(go.Scatter(
                        x=r * np.sin(theta), y=r * np.cos(theta),
                        mode="lines",
                        line=dict(color="#30363d", width=0.8, dash="dot"),
                        showlegend=False, hoverinfo="skip",
                    ))

                for ev_code, (lbl, color) in event_map.items():
                    sub = sp[sp["events"] == ev_code] if "events" in sp.columns else pd.DataFrame()
                    if sub.empty:
                        continue
                    fig_sp.add_trace(go.Scatter(
                        x=sub["spray_x"], y=sub["spray_y"],
                        mode="markers",
                        marker=dict(color=color, size=9,
                                    line=dict(color="white", width=0.5)),
                        name=f"{lbl} ({len(sub)})",
                        hovertemplate=f"<b>{lbl}</b><br>"
                                      "EV: %{customdata[0]:.1f} mph<br>"
                                      "LA: %{customdata[1]:.1f}°<extra></extra>",
                        customdata=sub[["launch_speed", "launch_angle"]].values
                                    if {"launch_speed","launch_angle"}.issubset(sub.columns)
                                    else None,
                    ))

                # アウトその他
                others = sp[~sp["events"].isin(event_map.keys())] if "events" in sp.columns else sp
                if not others.empty:
                    fig_sp.add_trace(go.Scatter(
                        x=others["spray_x"], y=others["spray_y"],
                        mode="markers",
                        marker=dict(color="#6D6875", size=6, opacity=0.45),
                        name=f"アウト/その他 ({len(others)})",
                        hoverinfo="skip",
                    ))

                dark_layout(fig_sp, "Spray Chart (打球方向・フィート)", height=640)
                fig_sp.update_layout(
                    xaxis=dict(range=[-380, 380], showgrid=False, zeroline=False,
                               showticklabels=False),
                    yaxis=dict(range=[-30, 450], showgrid=False, zeroline=False,
                               showticklabels=False, scaleanchor="x", scaleratio=1),
                )
                st.plotly_chart(fig_sp, use_container_width=True)

    # ---- Batter Tab 4: vs Pitch Type ----
    with btab4:
        st.caption("球種別 Swing% / Whiff% / xwOBA のレーダー的比較")
        col_v1, col_v2 = st.columns(2)

        with col_v1:
            fig_v1 = go.Figure()
            if "xwoba" in summary.columns:
                fig_v1.add_trace(go.Bar(
                    x=summary["label"], y=summary["xwoba"],
                    marker_color=[pitch_colors[p] for p in summary["pitch_type"]],
                    text=[f"{v:.3f}" if pd.notna(v) else "" for v in summary["xwoba"]],
                    textposition="outside", textfont=dict(color=TC, size=10),
                    hovertemplate="%{x}: xwOBA %{y:.3f}<extra></extra>",
                ))
                dark_layout(fig_v1, "球種別 xwOBA", height=400)
                fig_v1.update_layout(yaxis_title="xwOBA", showlegend=False)
                st.plotly_chart(fig_v1, use_container_width=True)

        with col_v2:
            fig_v2 = go.Figure()
            fig_v2.add_trace(go.Bar(
                name="Swing %", x=summary["label"], y=summary["swing_pct"],
                marker_color="#457B9D",
            ))
            fig_v2.add_trace(go.Bar(
                name="Whiff %", x=summary["label"], y=summary["whiff_pct"],
                marker_color="#E63946",
            ))
            dark_layout(fig_v2, "球種別 Swing% / Whiff%", height=400)
            fig_v2.update_layout(barmode="group", yaxis_title="%")
            st.plotly_chart(fig_v2, use_container_width=True)

    # ---- Batter Tab 5: 時系列推移 ----
    with btab5:
        if "game_date" not in df_all.columns or "events" not in df_all.columns:
            st.info("時系列推移を表示するデータが不足しています。")
        else:
            ts = df_all.dropna(subset=["game_date"]).copy()
            ts["game_date"] = pd.to_datetime(ts["game_date"])
            grp = ts.groupby("game_date").agg(
                ab=("events", lambda s: s.isin(AB_EVENTS).sum()),
                hits=("events", lambda s: s.isin(HIT_EVENTS).sum()),
                xwoba=("estimated_woba_using_speedangle", "mean")
                       if "estimated_woba_using_speedangle" in ts.columns else ("events", "size"),
                avg_ev=("launch_speed", "mean") if "launch_speed" in ts.columns else ("events", "size"),
            ).reset_index()
            grp["ba"] = grp["hits"] / grp["ab"].replace(0, np.nan)
            # 累積打率
            grp["cum_ab"]   = grp["ab"].cumsum()
            grp["cum_hits"] = grp["hits"].cumsum()
            grp["cum_ba"]   = grp["cum_hits"] / grp["cum_ab"].replace(0, np.nan)

            fig_ts = go.Figure()
            fig_ts.add_trace(go.Scatter(
                x=grp["game_date"], y=grp["cum_ba"],
                mode="lines+markers", name="累積打率",
                line=dict(color="#E63946", width=2.5),
                marker=dict(size=5),
                hovertemplate="%{x|%Y-%m-%d}<br>累積打率: %{y:.3f}<extra></extra>",
            ))
            if "estimated_woba_using_speedangle" in ts.columns:
                fig_ts.add_trace(go.Scatter(
                    x=grp["game_date"], y=grp["xwoba"],
                    mode="lines+markers", name="試合別 xwOBA",
                    line=dict(color="#2A9D8F", width=1.5, dash="dot"),
                    marker=dict(size=4),
                    hovertemplate="%{x|%Y-%m-%d}<br>xwOBA: %{y:.3f}<extra></extra>",
                ))
            dark_layout(fig_ts, "打率 / xwOBA の時系列推移", height=420)
            fig_ts.update_layout(xaxis_title="試合日", yaxis_title="値")
            st.plotly_chart(fig_ts, use_container_width=True)

            if "launch_speed" in ts.columns:
                fig_ev = go.Figure(go.Scatter(
                    x=grp["game_date"], y=grp["avg_ev"],
                    mode="lines+markers",
                    line=dict(color="#F4A261", width=2),
                    marker=dict(size=5),
                    hovertemplate="%{x|%Y-%m-%d}<br>Avg EV: %{y:.1f} mph<extra></extra>",
                ))
                dark_layout(fig_ev, "試合別 平均 Exit Velocity", height=320)
                fig_ev.update_layout(xaxis_title="試合日", yaxis_title="Avg EV (mph)")
                st.plotly_chart(fig_ev, use_container_width=True)

# ============================================================
# 関連 note 記事 + 下部フッター
# ============================================================
render_related_notes(player_name)
render_footer()
