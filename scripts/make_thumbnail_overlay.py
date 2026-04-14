"""
Gemini生成のベース画像にデータオーバーレイを重ねてnote用サムネを完成させる

前提:
    images/soriano_base.png   (Gemini生成, 1280x670 推奨)
出力:
    images/soriano_thumbnail.png

使い方:
    python make_thumbnail_overlay.py --article soriano
"""
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import font_manager, patches

for font in ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans CJK JP"]:
    try:
        font_manager.findfont(font, fallback_to_default=False)
        plt.rcParams["font.family"] = font
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).parent.parent
IMG_DIR = ROOT / "images"

W, H = 1280, 670
DPI = 160


def overlay(base_name: str, out_name: str,
            player: str, tagline: str,
            kpi_label1: str, kpi_value1: str,
            kpi_label2: str, kpi_value2: str,
            kpi_label3: str, kpi_value3: str,
            accent="#ffcc33", neon="#00e5ff"):
    base_path = IMG_DIR / base_name
    if not base_path.exists():
        raise FileNotFoundError(
            f"ベース画像が見つかりません: {base_path}\n"
            f"Geminiで生成した画像を {base_path} として保存してください。"
        )

    img = mpimg.imread(base_path)

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ベース画像
    ax.imshow(img, extent=(0, 1, 0, 1), aspect="auto", zorder=0)

    # 左側を暗くするグラデーション(左=濃い, 右=透明)
    # 左端 alpha=0.75 から x=0.55 で alpha=0 までフェード
    grad = np.linspace(0.75, 0.0, 512).reshape(1, -1)
    ax.imshow(grad, extent=(0, 0.55, 0, 1), aspect="auto",
              cmap="Greys", zorder=1, vmin=0, vmax=1)

    # 左エッジのアクセントバー
    ax.add_patch(patches.Rectangle((0, 0), 0.012, 1,
                                    color=accent, zorder=2))

    # 上部ブランド
    ax.text(0.04, 0.90, "データが暴く真実", color=accent,
            fontsize=18, fontweight="bold", ha="left", va="center", zorder=3)
    ax.add_patch(patches.Rectangle((0.04, 0.865), 0.50, 0.003,
                                    color=accent, zorder=3))

    # 選手名
    ax.text(0.04, 0.77, player, color="white",
            fontsize=34, fontweight="bold", ha="left", va="center", zorder=3)

    # KPIブロック(3列)
    kpi_y = 0.52
    kpi_box_h = 0.20
    cols = [
        (0.04, kpi_label1, kpi_value1, accent),
        (0.22, kpi_label2, kpi_value2, neon),
        (0.40, kpi_label3, kpi_value3, "#ff2d95"),
    ]
    for x, label, value, col in cols:
        # 枠
        ax.add_patch(patches.Rectangle((x, kpi_y), 0.16, kpi_box_h,
                                        fill=False, edgecolor=col,
                                        linewidth=1.5, zorder=3))
        ax.text(x + 0.005, kpi_y + kpi_box_h - 0.035, label,
                color=col, fontsize=11, fontweight="bold",
                ha="left", va="center", zorder=4)
        ax.text(x + 0.08, kpi_y + 0.07, value,
                color="white", fontsize=24, fontweight="bold",
                ha="center", va="center", zorder=4)

    # 煽り文
    ax.text(0.04, 0.35, tagline, color="white",
            fontsize=22, fontweight="bold", ha="left", va="center", zorder=3)

    # フッターブランド
    ax.text(0.04, 0.08, "note / MLB Data Analysis", color="#88a0c0",
            fontsize=12, ha="left", va="center", style="italic", zorder=3)

    out_path = IMG_DIR / out_name
    plt.savefig(out_path, dpi=DPI, facecolor="black")
    plt.close(fig)
    print(f"[OK] {out_path}")


def soriano():
    overlay(
        base_name="soriano_base.png",
        out_name="soriano_thumbnail.png",
        player="ホセ・ソリアーノ",
        tagline="シンカー投手が4シーム投手へ",
        kpi_label1="ERA",    kpi_value1="0.33",
        kpi_label2="K/BB",   kpi_value2="4.80",
        kpi_label3="xwOBA",  kpi_value3=".276",
    )


def yamamoto():
    overlay(
        base_name="yamamoto_base.png",
        out_name="yamamoto_thumbnail.png",
        player="山本由伸",
        tagline="球種革命の代償と成果",
        kpi_label1="4-SEAM", kpi_value1="▼11.7",
        kpi_label2="SPLIT",  kpi_value2="▲8.2",
        kpi_label3="xERA",   kpi_value3="2.45",
    )


def ohtani():
    overlay(
        base_name="ohtani_base.png",
        out_name="ohtani_thumbnail.png",
        player="大谷翔平 vs ジャッジ",
        tagline="HR王の確率分布を読み解く",
        kpi_label1="xwOBA",  kpi_value1=".410",
        kpi_label2="Barrel%", kpi_value2="18.2",
        kpi_label3="HR pace", kpi_value3="54",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--article",
                   choices=["soriano", "yamamoto", "ohtani", "all"],
                   default="soriano")
    a = p.parse_args()
    if a.article in ("soriano", "all"):
        soriano()
    if a.article in ("yamamoto", "all"):
        yamamoto()
    if a.article in ("ohtani", "all"):
        ohtani()


if __name__ == "__main__":
    main()
