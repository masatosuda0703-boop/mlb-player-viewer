"""
note記事用サムネイル画像生成スクリプト
1280x670 px、濃紺背景+3行テキスト(選手名/核心数字/煽り文)

使い方:
    python make_thumbnails.py --article soriano
    python make_thumbnails.py --article yamamoto
    python make_thumbnails.py --article ohtani
    python make_thumbnails.py --article all
"""
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager, patches

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

# note推奨サムネサイズ 1280x670
W, H = 1280, 670
DPI = 160


def render_thumb(line1: str, line2: str, line3: str, out_path: Path,
                 bg_color="#0b1e3a", accent="#ffcc33", line2_color="#ffffff"):
    """
    line1: 選手名(大きめ、白)
    line2: 核心数字(最大、黄色)
    line3: 煽り文(中、白)
    """
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # 背景
    ax.add_patch(patches.Rectangle((0, 0), 1, 1, color=bg_color, zorder=0))

    # 左側のアクセントバー
    ax.add_patch(patches.Rectangle((0, 0), 0.015, 1, color=accent, zorder=1))

    # 上部ブランドライン
    ax.text(0.05, 0.88, "データが暴く真実", color=accent,
            fontsize=20, fontweight="bold", ha="left", va="center")
    ax.add_patch(patches.Rectangle((0.05, 0.83), 0.9, 0.003, color=accent, zorder=1))

    # メイン3行
    ax.text(0.05, 0.68, line1, color="white",
            fontsize=38, fontweight="bold", ha="left", va="center")
    ax.text(0.05, 0.45, line2, color=accent,
            fontsize=64, fontweight="bold", ha="left", va="center")
    ax.text(0.05, 0.22, line3, color=line2_color,
            fontsize=26, fontweight="bold", ha="left", va="center")

    # フッターブランド
    ax.text(0.95, 0.06, "MLB Data Analysis", color="#88a0c0",
            fontsize=14, ha="right", va="center", style="italic")

    plt.savefig(out_path, dpi=DPI, facecolor=bg_color)
    plt.close(fig)
    print(f"[OK] {out_path}")


def soriano_thumb():
    render_thumb(
        line1="ホセ・ソリアーノ",
        line2="ERA 0.33 の真実",
        line3="シンカー投手が4シーム投手へ",
        out_path=IMG_DIR / "soriano_thumbnail.png",
    )


def yamamoto_thumb():
    render_thumb(
        line1="山本由伸",
        line2="4シーム ▼11.7pt",
        line3="球種革命の代償と成果",
        out_path=IMG_DIR / "yamamoto_thumbnail.png",
    )


def ohtani_thumb():
    render_thumb(
        line1="大谷翔平 vs ジャッジ",
        line2="HR王の確率分布",
        line3="xwOBA .410 は何を意味する?",
        out_path=IMG_DIR / "ohtani_thumbnail.png",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--article",
                   choices=["soriano", "yamamoto", "ohtani", "all"],
                   default="soriano")
    a = p.parse_args()
    if a.article in ("soriano", "all"):
        soriano_thumb()
    if a.article in ("yamamoto", "all"):
        yamamoto_thumb()
    if a.article in ("ohtani", "all"):
        ohtani_thumb()


if __name__ == "__main__":
    main()
