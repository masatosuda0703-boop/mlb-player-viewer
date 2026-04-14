# MLB Statcast データ取得スクリプト(Phase 1-A)

## セットアップ(初回のみ)

```bash
# このフォルダに移動
cd "MLB ANALYSIS/scripts"

# 仮想環境を作成(推奨)
python -m venv venv
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 依存ライブラリをインストール
pip install -r requirements.txt
```

## 使い方

### 1. 打者のStatcastデータを取得

```bash
# 大谷翔平の直近30日
python fetch_data.py --player "Shohei Ohtani" --type batter

# 期間指定
python fetch_data.py --player "Shohei Ohtani" --start 2026-03-27 --end 2026-04-15
```

### 2. 投手のStatcastデータを取得

```bash
python fetch_data.py --player "Yoshinobu Yamamoto" --type pitcher --start 2026-03-27 --end 2026-04-15
```

### 3. リーグ全体のリーダーボード取得

```bash
# 打撃リーダー(HR順、上位20人)
python fetch_data.py --leaderboard batting --season 2026 --top 20

# 投手リーダー(IP順、Stuff+ 含む)
python fetch_data.py --leaderboard pitching --season 2026 --top 20
```

## 出力されるファイル

`../data/` フォルダに以下が保存されます:

- `{player}_{type}_{start}_{end}.csv` — Statcastの全投球データ(生データ)
- `{player}_{type}_{start}_{end}_summary.txt` — 集計済みサマリー(Claudeに貼り付ける用)
- `leaderboard_{kind}_{season}_top{N}.csv` — リーダーボード

## Claudeへの渡し方

1. `_summary.txt` の中身を全コピーしてClaudeに貼る
2. 必要に応じて `.csv` もアップロード
3. Claudeに「このデータで記事を書いて」と依頼

## 計算している指標

**打者:**
- ホームラン数、Barrel数/率(Statcast公式定義 `launch_speed_angle == 6`)
- Hard-Hit% (95mph以上の打球)
- 平均/最大打球速度、平均打球角度
- xwOBA(打球発生時の期待値平均)
- Whiff率(スイング中の空振り率)
- 全本塁打のEV/LA/飛距離/球種

**投手:**
- 球数、4シーム球速、K/BB/被HR
- Whiff率、被xwOBA
- 球種構成(球種別投球数・平均球速)

## 注意事項

- Baseball Savantへのアクセスがレート制限されるので、取得の合間は数秒空けましょう(pybaseball内部で調整済み)
- 初回実行時はplayerid lookupテーブルをダウンロードするため時間がかかります
- キャッシュは `~/.pybaseball/` に保存されます
