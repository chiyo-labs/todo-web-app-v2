# Todo Web App v2（Flask + Google Spreadsheet）

## アプリ概要

Google スプレッドシートをデータベースとして使う Todo 管理 Web アプリです。ブラウザから一覧・追加・編集・完了の切り替えができます。

## 使用技術

- **Python 3**（3.10 以降を推奨）
- **Flask** … Web フレームワーク
- **gspread** … スプレッドシート操作
- **google-auth** … サービスアカウント認証
- **Google Sheets API / Google Drive API** … 読み書き（Cloud Console で有効化）

## 主な機能

| 機能 | 説明 |
|------|------|
| Todo 一覧表示 | `/` で一覧表示 |
| 新規登録 | `/add` でタイトル・内容・期日・優先度を登録（ID は自動採番） |
| 編集 | `/edit/<id>` で更新（完了の有無は保持） |
| 優先度 | 高 / 中 / 低 |
| 期日順ソート | 未完了・完了それぞれのグループ内で期日が近い順（未入力や不正な日付はグループの後ろ） |
| 完了チェック | 一覧のチェックで「完了」列を `完了` と空でトグル。完了行は一覧の下にまとまり表示 |

## スプレッドシートの列構成

1 行目は見出し。**A〜F 列**を想定しています。

| 列 | 内容 |
|----|------|
| A | ID |
| B | タイトル |
| C | 内容 |
| D | 期日（`YYYY-MM-DD` 推奨） |
| E | 優先度（高・中・低） |
| F | 完了（未完了は空、完了は `完了` という文字列） |

- **シート名（タブ名）:** `todos`（`app.py` の `WORKSHEET_NAME` で変更可）
- **ブックの特定:** スプレッドシートの URL にある **ID** を使います（後述の環境変数）

サービスアカウント用のクライアントメールを、対象スプレッドシートに **編集者として共有** してください。

## セットアップ手順

### 1. 仮想環境（任意）

```bash
cd todo_web_app_v2
python -m venv .venv
```

Windows（PowerShell で `Activate.ps1` が使えない場合は、`activate` なしで次のように実行しても構いません）:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### 2. ライブラリのインストール

```bash
pip install -r requirements.txt
```

依存内容は **Flask / gspread / google-auth** のみです。

### 3. `credentials.json` を配置

1. [Google Cloud Console](https://console.cloud.google.com/) で **Google Sheets API** と **Google Drive API** を有効化する  
2. サービスアカウントを作成し、**JSON キー**をダウンロードする  
3. ダウンロードした JSON を **`app.py` と同じフォルダ**に `credentials.json` という名前で置く  

**`credentials.json` は秘密情報です。GitHub にコミットしないでください。**（`.gitignore` に含めています）

### 4. スプレッドシート ID の設定

スプレッドシートを開いたときの URL は次のような形です。

`https://docs.google.com/spreadsheets/d/【ここがスプレッドシートID】/edit`

**環境変数 `GOOGLE_SPREADSHEET_ID`** に、その ID だけを設定してからアプリを起動します。

**Windows（PowerShell・そのセッションだけ）:**

```powershell
$env:GOOGLE_SPREADSHEET_ID = "あなたのスプレッドシートID"
python app.py
```

**macOS / Linux:**

```bash
export GOOGLE_SPREADSHEET_ID="あなたのスプレッドシートID"
python app.py
```

ID をコードに直書きしない運用にしてあります（クローンした人が各自のシート ID を設定する想定です）。

## 起動方法

`todo_web_app_v2` ディレクトリで:

```bash
python app.py
```

ブラウザで **http://127.0.0.1:5000** を開きます。

`debug=True` で起動しています。本番では適切な WSGI サーバと `debug=False` の利用を検討してください。

## 補足ファイル

| ファイル | 説明 |
|----------|------|
| `test_sheet.py` / `add_test.py` | スプレッドシート接続テスト用（設定はスクリプト内。本アプリの `open_by_key` とは別の書き方の場合があります） |

## ライセンス

学習・個人利用を想定しています。必要に応じてご自身でライセンスを追記してください。
