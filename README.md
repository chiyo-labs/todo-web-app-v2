# Todo Web App（Flask + Google スプレッドシート）

## アプリ概要

Google スプレッドシートをデータストアとして使う、シンプルな Todo 管理 Web アプリです。ブラウザから一覧表示・新規登録・編集ができます。

## 使用技術

- **Python 3**（3.10 以降を推奨）
- **Flask**（Web フレームワーク）
- **gspread**（Google スプレッドシート操作用）
- **google-auth**（サービスアカウント認証）
- **Google Sheets API / Google Drive API**（スプレッドシートの読み書き）

## 主な機能

| 機能 | 説明 |
|------|------|
| Todo 一覧表示 | トップページ（`/`）でスプレッドシートの Todo を表形式で表示 |
| Todo 新規登録 | `/add` からタイトル・内容・期日を入力し、行を追加（ID は自動採番） |
| Todo 編集 | 一覧の「編集」から `/edit/<id>` に遷移し、既存行を更新 |

## スプレッドシート側の前提

- **ブック名（スプレッドシート名）:** `Todoリストアプリ`
- **シート名:** `todos`
- **1 行目:** 見出し行（例: ID / タイトル / 内容 / 期日）
- **データ列:** A 列=ID、B 列=タイトル、C 列=内容、D 列=期日
- サービスアカウントのメールアドレスに、このスプレッドシートの**共有（編集可）**を付与してください。

## セットアップ手順

### 1. リポジトリの取得と仮想環境（任意）

```bash
cd todo_web_app
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
```

### 2. 必要ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 3. Google サービスアカウントと `credentials.json`

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成し、**Google Sheets API** と **Google Drive API** を有効にします。
2. サービスアカウントを作成し、**JSON キー**をダウンロードします。
3. ダウンロードした JSON を、このプロジェクトの **`app.py` と同じフォルダ**に `credentials.json` という名前で配置します。

> **重要:** `credentials.json` は機密情報です。**Git にコミットしないでください。** 本リポジトリの `.gitignore` に含まれています。

### 4. 接続テスト用スクリプト（任意）

同梱の `test_sheet.py` や `add_test.py` で、スプレッドシート接続・行追加のテストができます（事前に `pip install -r requirements.txt`）。

## 起動方法

`app.py` があるディレクトリで次を実行します。

```bash
python app.py
```

ブラウザで **http://127.0.0.1:5000** を開いてください。

開発用に `debug=True` で起動しています。本番公開時は適切な WSGI サーバと `debug=False` の利用を検討してください。

## プロジェクト構成（主要ファイル）

| パス | 説明 |
|------|------|
| `app.py` | Flask アプリ本体 |
| `templates/` | HTML テンプレート（一覧・新規・編集） |
| `requirements.txt` | Python 依存パッケージ |
| `test_sheet.py` / `add_test.py` | スプレッドシート接続・追加のテスト用 |

## ライセンス

学習・個人利用を想定しています。必要に応じてご自身でライセンスを追記してください。
