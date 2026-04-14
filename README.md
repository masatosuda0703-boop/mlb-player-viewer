# MLB Player Viewer

Statcast データから MLB 投手/打者のパフォーマンスを可視化する Streamlit アプリ。

- エントリーポイント: [`scripts/mlb_player_viewer.py`](scripts/mlb_player_viewer.py)
- 詳細仕様: [`scripts/HANDOVER.md`](scripts/HANDOVER.md)

## ローカル起動

```bash
pip install -r requirements.txt
python -m streamlit run scripts/mlb_player_viewer.py
```

ブラウザで http://localhost:8501 を開く。

## 主要機能

- TOPページ自動キュレーション (OPS/ERAリーダー)
- 日本語/英語/チーム略称での選手検索
- 投手: Movement Map / Pitch Locations / Arm Angle / Active Spin / Pitch Frequency
- 打者: Batted Ball / Zone Heatmap / Spray Chart / vs Pitch Type
- FanGraphs 高度指標 (Stuff+ / Location+ / xFIP / WAR)

## データソース

| 用途 | ソース |
|------|--------|
| Statcast 生データ | pybaseball → Baseball Savant |
| 選手プロフィール | MLB Stats API |
| 投手高度指標 | FanGraphs (cloudscraper経由) |

## 公開 (Streamlit Community Cloud)

手順は [`DEPLOY.md`](DEPLOY.md) を参照。
