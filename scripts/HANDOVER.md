# MLB Player Viewer - 引き継ぎドキュメント

## プロジェクト概要
Statcast データから MLB 投手/打者のパフォーマンスを可視化する Streamlit アプリ。

- メインファイル: `mlb_player_viewer.py`
- 旧ファイル (残置): `pitcher_movement_app.py`, `ohtani_pitch_movement.py`

## 起動
```bash
python -m streamlit run mlb_player_viewer.py
```
ブラウザで http://localhost:8501 を開く。

## 依存パッケージ
```bash
pip install streamlit pandas numpy plotly requests pybaseball cloudscraper
```

- **cloudscraper**: FanGraphs の Cloudflare ガード突破用（Stuff+/Location+/Pitching+/xFIP/WAR 取得に必須）。未インストールでも FIP 等はローカル計算で動作。

## データソース
| 用途 | ソース |
|------|--------|
| Statcast 生データ | pybaseball → Baseball Savant |
| 選手プロフィール (チーム/身長体重/画像) | MLB Stats API (`statsapi.mlb.com`) |
| ヘッドショット画像 | `img.mlbstatic.com` |
| 注目選手リーダーボード | MLB Stats API `/stats/leaders` (OPS/ERA) |
| 投手高度指標 (Stuff+ 等) | FanGraphs JSON API (cloudscraper 経由) |

## 主な機能
1. **TOP ページ**: MLB Stats API から OPS トップ打者 + ERA トップ投手を自動キュレーション（12h キャッシュ、🔄 更新ボタン付き）
2. **選手検索**: 日本語/英語/チーム略称でインクリメンタル検索（全アクティブ選手 ~1400 名を 24h キャッシュ）
3. **プロフィールカード**: 画像・チーム・身長体重・打投・出身地等
4. **投手 FanGraphs 指標**: Stuff+ / Location+ / Pitching+ / FIP / xFIP / ERA / WAR
5. **投手タブ**: Movement Map / Pitch Locations (打者シルエット付き) / Arm Angle (背面視点シルエット) / Active Spin / Movement Profile / Pitch Frequency
6. **打者タブ**: Batted Ball (EV×LA) / Zone Heatmap / Spray Chart / vs Pitch Type / 時系列推移
7. **TOP へ戻るボタン**: ヘッダー右上 / プロフィール上 / サイドバー / 最下部 の 4 箇所

## カスタマイズポイント
| 項目 | 場所 |
|------|------|
| 日本語エイリアス追加 | `JP_ALIASES` 辞書 |
| フォールバック用注目選手 | `FALLBACK_CURATED_PLAYERS` リスト |
| シーズン日付範囲 | `SEASON_DATES` 辞書 |
| 球種最低投球数 | ソース内 `min_pitches = 10` (固定) |
| FIP 定数 | `compute_fip_from_statcast` 内 `fip_const = 3.10` |

## 既知の挙動 / 注意点
- **FanGraphs**: Cloudflare ガードで通常 requests は 403。`cloudscraper` で突破。それでも失敗する場合は API が返す診断メッセージをカード下に表示。
- **Spray Chart 座標**: Statcast `hc_x/hc_y` はレガシーピクセル座標。home plate = (125.42, 198.27)、2.5 倍でフィート換算。
- **プレート座標**: plate_x は catcher's view で右側が正。RHB は 3B 側 (plate_x < 0)、LHB は 1B 側 (plate_x > 0)。
- **Arm Angle**: 0° = サイドアーム、+90° = オーバーハンド、負値 = サブマリン。`p_throws` で左右投手判定し背面シルエットの向きを反転。
- **キュレーション**: 早期シーズンで当該年データが空の場合、前年シーズンにフォールバック。
- **Barrel 推定**: 正確な Savant 定義ではなく簡易推定 (EV≥98 mph かつ LA 8°〜50°)。

## セッション状態キー
`ss_lookup_df`, `ss_raw_df`, `ss_base_key`, `ss_full_key`, `ss_player_name`, `ss_player_id`, `ss_chosen_label`, `ss_player_type`, `ss_season`, `ss_pending_label`

TOP ボタンは `_reset_to_top()` で上記を全て pop する。

## 開発ログ (主な変更履歴)
1. 元は大谷投手専用スクリプト (matplotlib) → Streamlit + plotly へ刷新
2. 投手/打者切替対応、MLB Stats API でプロフィール追加
3. 自動キュレーション TOP ページ
4. 日本語検索・予測変換 (selectbox)
5. FanGraphs 指標対応 (Cloudflare 回避)
6. Pitch Locations に打者シルエット、Arm Angle を背面視点図へ
