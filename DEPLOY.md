# Streamlit Community Cloud へのデプロイ手順

## 前提
- GitHub アカウント
- https://share.streamlit.io/ (Streamlit Community Cloud) のアカウント(GitHub連携で無料)

## 1. GitHubリポジトリを用意

ローカル(PowerShell)で:

```powershell
cd "C:\path\to\MLB ANALYSIS"
git init
git add .
git commit -m "Initial commit: MLB Player Viewer"
```

GitHubで新規リポジトリを作成(例: `mlb-player-viewer`)し、push:

```powershell
git branch -M main
git remote add origin https://github.com/<あなたのユーザー名>/mlb-player-viewer.git
git push -u origin main
```

**リポジトリは Public で問題なし**(Streamlit Community Cloud は Public リポジトリ向けが無料枠)。
Private リポジトリでも可だがワークスペース招待が必要。

## 2. Streamlit Community Cloud でデプロイ

1. https://share.streamlit.io/ にアクセスし GitHub でサインイン
2. **New app** をクリック
3. 設定:
   - **Repository**: `<あなたのユーザー名>/mlb-player-viewer`
   - **Branch**: `main`
   - **Main file path**: `scripts/mlb_player_viewer.py`
   - **Python version**: 3.11 推奨(Advanced settings から指定)
4. **Deploy** をクリック

初回ビルドは依存インストールで5〜10分かかる(特に pybaseball 周り)。

## 3. 公開URL

デプロイ成功後、`https://<app-name>.streamlit.app` が発行される。
これがそのまま公開サイトのURL。

## 4. 更新フロー

ローカルで編集 → `git push` すると Streamlit Cloud が自動で再デプロイする。

```powershell
git add .
git commit -m "update: 機能説明"
git push
```

## トラブルシューティング

### `ModuleNotFoundError: cloudscraper`
- `requirements.txt` にちゃんと書かれているか確認(リポジトリルートのもの)

### FanGraphs 指標が取れない
- Streamlit Cloud の出口IPが FanGraphs 側で弾かれる可能性あり。`cloudscraper` で突破できないケースは、カード下の診断メッセージが表示されるのでそれを確認。
- 恒久対策としては、バッチでローカル取得→CSVキャッシュを同梱する方式に切り替え(将来的な改修ポイント)。

### pybaseball のキャッシュ
- Streamlit Cloud のファイルシステムは永続化されないので、`@st.cache_data` によるオンメモリキャッシュが主。
- リクエスト頻度が高すぎると Baseball Savant 側でレート制限を受けるので、TOP ページの 12h キャッシュは維持推奨。

### シークレットが必要な場合
- Streamlit Cloud の **Settings → Secrets** に TOML 形式で記述すれば、`st.secrets["KEY"]` で読める。
- ローカルは `.streamlit/secrets.toml` に同じ形式で書く(このファイルは `.gitignore` 済)。

## カスタムドメイン

Streamlit Community Cloud の無料枠は `<app>.streamlit.app` のサブドメインのみ。
カスタムドメインが必要なら Hugging Face Spaces や Render.com、自前VPS(Docker)等への移行を検討。
