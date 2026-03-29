import traceback
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "Todoリストアプリ"
WORKSHEET_NAME = "todos"

# 1列目: ID / 2列目: タイトル / 3列目: 内容 / 4列目: 期日（見出し行に合わせて調整してください）
NEW_TITLE = "テストTodo"
NEW_BODY = "これは追加テストです"
NEW_DUE = "2026-03-28"


def compute_next_id(all_values: list[list[str]]) -> int:
    """1行目は見出し。2行目以降の先頭列を ID として最大値+1。データなしなら 1。"""
    if len(all_values) <= 1:
        return 1

    ids: list[int] = []
    for row in all_values[1:]:
        if not row or not str(row[0]).strip():
            continue
        try:
            ids.append(int(str(row[0]).strip()))
        except ValueError:
            continue

    return max(ids) + 1 if ids else 1


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    creds_path = base_dir / "credentials.json"

    print("【1】処理開始")
    print(f"    credentials パス: {creds_path}")

    try:
        print("【2】認証開始（Service Account）")
        creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        print("【3】認証情報の読み込み成功")

        print("【4】gspread クライアント作成開始")
        client = gspread.authorize(creds)
        print("【5】gspread クライアント作成成功")

        print(f"【6】スプレッドシート接続開始（名前: {SPREADSHEET_NAME}）")
        spreadsheet = client.open(SPREADSHEET_NAME)
        print("【7】スプレッドシート接続成功")

        print(f"【8】ワークシート取得開始（シート名: {WORKSHEET_NAME}）")
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        print("【9】ワークシート取得成功")

        print("【10】既存データ取得開始（get_all_values）")
        all_values = worksheet.get_all_values()
        print(f"【11】取得完了（全行数: {len(all_values)}、データ行は見出し除く {max(0, len(all_values) - 1)} 行）")

        print("【12】次の ID を算出（2行目以降の先頭列の最大 + 1、なければ 1）")
        next_id = compute_next_id(all_values)
        print(f"【13】次の ID: {next_id}")

        new_row = [str(next_id), NEW_TITLE, NEW_BODY, NEW_DUE]
        print("【14】1行追加開始（append_row）")
        print(f"    追加内容: {new_row}")
        worksheet.append_row(new_row, value_input_option="USER_ENTERED")
        print("【15】追加成功")

        print("【16】追加した行の内容（このスクリプトで書き込んだ値）")
        print("-" * 40)
        print(f"  ID: {new_row[0]}")
        print(f"  タイトル: {new_row[1]}")
        print(f"  内容: {new_row[2]}")
        print(f"  期日: {new_row[3]}")
        print(f"  行全体: {new_row}")
        print("-" * 40)
        print("【完了】すべて正常に終了しました")

    except FileNotFoundError as e:
        print("【エラー】credentials.json が見つかりません")
        print(f"    例外: {e!r}")
        traceback.print_exc()

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"【エラー】スプレッドシートが見つかりません: {SPREADSHEET_NAME!r}")
        print("    サービスアカウントのメールをスプレッドシートの共有に追加したか確認してください。")
        traceback.print_exc()

    except gspread.exceptions.WorksheetNotFound:
        print(f"【エラー】シートが見つかりません: {WORKSHEET_NAME!r}")
        traceback.print_exc()

    except Exception as e:
        print(f"【エラー】予期しない例外: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
