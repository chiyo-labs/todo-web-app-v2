import traceback
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

# Google Sheets API の認証範囲
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "Todoリストアプリ"
WORKSHEET_NAME = "todos"


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

        print("【10】全データ取得開始（get_all_values）")
        data = worksheet.get_all_values()
        print(f"【11】全データ取得成功（行数: {len(data)}）")

        print("【12】シート内容を表示します")
        print("-" * 40)
        for i, row in enumerate(data, start=1):
            print(f"  行{i}: {row}")
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
