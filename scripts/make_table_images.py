"""
記事用の表画像生成スクリプト
note投稿時に貼り付ける .png 画像を出力する。

使い方:
    python make_table_images.py --article soriano
    python make_table_images.py --article yamamoto
    python make_table_images.py --article ohtani

出力:
    ../images/{article}_table{N}.png
"""
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager

# Windows向け日本語フォント設定
for font in ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans CJK JP"]:
    try:
        font_manager.findfont(font, fallback_to_default=False)
        plt.rcParams["font.family"] = font
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

IMG_DIR = Path(__file__).parent.parent / "images"
IMG_DIR.mkdir(exist_ok=True)


def render_table(title: str, headers: list, rows: list, col_aligns: list, highlight_rows: list, out_path: Path):
    """
    表画像を生成する。
    headers: 列見出しのリスト
    rows: [[cell, cell, ...], ...]
    col_aligns: 各列の揃え('left' / 'right' / 'center')
    highlight_rows: 強調したい行のindex(0-based)
    """
    n_rows = len(rows)
    n_cols = len(headers)

    fig_width = max(7.0, 1.6 * n_cols)
    fig_height = 0.55 * (n_rows + 2) + 0.8
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=180)
    ax.axis("off")

    # タイトル
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98, color="#1a1a1a")

    # テーブル
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        colLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.65)

    # ヘッダのスタイル
    for j in range(n_cols):
        cell = table[(0, j)]
        cell.set_facecolor("#1e3a5f")
        cell.set_text_props(color="white", fontweight="bold")
        cell.set_edgecolor("#ffffff")

    # 行ごとのスタイル
    for i in range(1, n_rows + 1):
        for j in range(n_cols):
            cell = table[(i, j)]
            # 縞模様
            if i % 2 == 0:
                cell.set_facecolor("#f5f8fc")
            else:
                cell.set_facecolor("#ffffff")
            cell.set_edgecolor("#d0d7de")
            # 列の揃え
            align = col_aligns[j] if j < len(col_aligns) else "center"
            cell.get_text().set_horizontalalignment(align)
            # 強調行
            if (i - 1) in highlight_rows:
                cell.set_facecolor("#fff4e5")
                cell.set_text_props(fontweight="bold", color="#c0392b")

    plt.savefig(out_path, bbox_inches="tight", dpi=180, facecolor="white")
    plt.close(fig)
    print(f"[OK] {out_path}")


def soriano_tables():
    # 表1: 球種構成
    render_table(
        title="表1:ホセ・ソリアーノ 球種構成の変化(2025フル vs 2026序盤)",
        headers=["球種", "2025年(2,784球)", "2026年(293球)", "変化(pt)"],
        rows=[
            ["Sinker(シンカー)", "49.1%", "29.4%", "▼19.7"],
            ["Knuckle Curve", "26.7%", "26.3%", "▼0.4"],
            ["4-Seam Fastball", "8.6%", "22.9%", "▲14.3"],
            ["Split-Finger", "9.2%", "14.7%", "▲5.5"],
            ["Slider", "6.0%", "6.8%", "▲0.8"],
            ["Changeup", "0.4%", "0.0%", "▼0.4"],
        ],
        col_aligns=["left", "right", "right", "right"],
        highlight_rows=[0, 2, 3],
        out_path=IMG_DIR / "soriano_table1_pitch_mix.png",
    )

    # 表2: Statcast指標
    render_table(
        title="表2:ホセ・ソリアーノ Statcast成績比較",
        headers=["指標", "2025年フル", "2026年序盤", "変化"],
        rows=[
            ["奪三振", "152", "24", "年換算180相当"],
            ["与四球", "78", "5", "年換算38相当(▼51%)"],
            ["K/BB比", "1.95", "4.80", "▲2.46倍"],
            ["被本塁打", "12", "1", "やや改善"],
            ["被xwOBA", ".312", ".276", "▼.036(改善)"],
            ["Whiff率", "25.3%", "24.6%", "ほぼ横ばい"],
            ["平均4シーム球速", "97.9 mph", "97.9 mph", "±0"],
            ["平均シンカー球速", "97.2 mph", "96.6 mph", "▼0.6"],
        ],
        col_aligns=["left", "right", "right", "right"],
        highlight_rows=[2, 4],
        out_path=IMG_DIR / "soriano_table2_stats.png",
    )


def yamamoto_tables():
    render_table(
        title="表1:山本由伸 球種構成の変化(2025フル vs 2026序盤)",
        headers=["球種", "2025年(2,719球)", "2026年(184球)", "変化(pt)"],
        rows=[
            ["4-Seam Fastball", "35.1%", "23.4%", "▼11.7"],
            ["Split-Finger", "25.0%", "26.6%", "▲1.6"],
            ["Cutter", "11.4%", "20.1%", "▲8.7"],
            ["Curveball", "17.7%", "12.5%", "▼5.2"],
            ["Sinker", "7.8%", "10.3%", "▲2.5"],
            ["Slider", "2.8%", "7.1%", "▲4.3"],
        ],
        col_aligns=["left", "right", "right", "right"],
        highlight_rows=[0, 2, 5],
        out_path=IMG_DIR / "yamamoto_table1_pitch_mix.png",
    )
    render_table(
        title="表2:山本由伸 Statcast先進指標比較",
        headers=["指標", "2025年フル", "2026年序盤", "変化"],
        rows=[
            ["平均4シーム球速", "95.3 mph", "95.5 mph", "▲0.2"],
            ["Whiff率", "27.2%", "23.1%", "▼4.1pt"],
            ["被xwOBA", ".260", ".316", "▲.056(悪化)"],
            ["K/BB", "3.38", "4.00", "▲(改善)"],
            ["被HR率", "0.51/9IP相当", "1試合で1本", "やや悪化"],
        ],
        col_aligns=["left", "right", "right", "right"],
        highlight_rows=[1, 2],
        out_path=IMG_DIR / "yamamoto_table2_stats.png",
    )


def ohtani_tables():
    render_table(
        title="表1:2026年ホームラン王候補 Statcast先進指標",
        headers=["選手", "HR", "Barrel%", "平均EV", "xwOBA", "Whiff%"],
        rows=[
            ["アーロン・ジャッジ", "6", "30.8%", "90.5", ".471", "30.6%"],
            ["大谷 翔平", "5", "22.5%", "93.2", ".410", "26.8%"],
            ["カイル・シュワーバー", "5", "28.6%", "94.7", ".437", "30.2%"],
            ["カル・ローリー", "2", "9.5%", "83.9", ".301", "30.4%"],
        ],
        col_aligns=["left", "right", "right", "right", "right", "right"],
        highlight_rows=[0, 1],
        out_path=IMG_DIR / "ohtani_table1_hr_race.png",
    )
    render_table(
        title="表2:2026年本塁打王予想確率",
        headers=["選手", "MLB全体王", "NL王", "予想本数"],
        rows=[
            ["ジャッジ", "38%", "―", "52〜58"],
            ["大谷", "22%", "60%", "48〜54"],
            ["シュワーバー", "12%", "28%", "44〜50"],
            ["ローリー", "8%", "―", "38〜44"],
        ],
        col_aligns=["left", "right", "right", "center"],
        highlight_rows=[0, 1],
        out_path=IMG_DIR / "ohtani_table2_probability.png",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--article", choices=["soriano", "yamamoto", "ohtani", "all"], default="soriano")
    a = p.parse_args()
    if a.article == "soriano" or a.article == "all":
        soriano_tables()
    if a.article == "yamamoto" or a.article == "all":
        yamamoto_tables()
    if a.article == "ohtani" or a.article == "all":
        ohtani_tables()


if __name__ == "__main__":
    main()
