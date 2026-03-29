import traceback
from pathlib import Path

import gspread
from flask import Flask, redirect, render_template, request, url_for
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "Todoリストアプリ"
WORKSHEET_NAME = "todos"

HEADER_FALLBACK = ["ID", "タイトル", "内容", "期日"]

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))


def _normalize_headers(row: list[str] | None) -> list[str]:
    """スプレッドシート1行目を4列の見出しにそろえる（空セルはデフォルト文言）。"""
    if not row:
        return list(HEADER_FALLBACK)
    out: list[str] = []
    for i in range(4):
        if i < len(row) and str(row[i]).strip():
            out.append(str(row[i]).strip())
        else:
            out.append(HEADER_FALLBACK[i])
    return out


def _get_worksheet():
    creds_path = BASE_DIR / "credentials.json"
    print(f"[DEBUG] credentials パス: {creds_path}")
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    print(f"[DEBUG] スプレッドシートを開く: {SPREADSHEET_NAME}")
    spreadsheet = client.open(SPREADSHEET_NAME)
    print(f"[DEBUG] ワークシート取得: {WORKSHEET_NAME}")
    return spreadsheet.worksheet(WORKSHEET_NAME)


def _rows_to_todos(data_rows: list[list[str]]) -> list[dict[str, str]]:
    """データ行を ID / タイトル / 内容 / 期日 の dict にそろえる（列不足は空文字）。"""
    todos: list[dict[str, str]] = []
    for row in data_rows:
        cells = list(row) + [""] * max(0, 4 - len(row))
        todos.append(
            {
                "id": cells[0] if len(cells) > 0 else "",
                "title": cells[1] if len(cells) > 1 else "",
                "content": cells[2] if len(cells) > 2 else "",
                "due": cells[3] if len(cells) > 3 else "",
            }
        )
    return todos


def _compute_next_id(all_values: list[list[str]]) -> int:
    """1行目は見出し。2行目以降の先頭列を ID とし最大+1。データなしなら 1。"""
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


def _find_row_number_by_todo_id(all_values: list[list[str]], todo_id: str) -> int | None:
    """先頭列の ID が一致する行の、シート上の行番号（1始まり）を返す。見出し行は除外。"""
    target = str(todo_id).strip()
    if not target:
        return None
    for i in range(1, len(all_values)):
        row = all_values[i]
        if not row:
            continue
        cell = str(row[0]).strip()
        if cell == target:
            return i + 1
        try:
            if int(cell) == int(target):
                return i + 1
        except ValueError:
            continue
    return None


def _row_cells_for_edit(row: list[str]) -> tuple[str, str, str]:
    """データ行から タイトル・内容・期日 を取り出す（列不足は空文字）。"""
    cells = list(row) + [""] * max(0, 4 - len(row))
    return (
        cells[1] if len(cells) > 1 else "",
        cells[2] if len(cells) > 2 else "",
        cells[3] if len(cells) > 3 else "",
    )


@app.route("/edit/<todo_id>", methods=["GET", "POST"])
def edit(todo_id: str):
    error: str | None = None
    title = ""
    content = ""
    due = ""

    if request.method == "GET":
        print(f"[DEBUG] GET /edit/{todo_id!r} フォーム表示")
        try:
            worksheet = _get_worksheet()
            all_values = worksheet.get_all_values()
            print(f"[DEBUG] get_all_values 完了: {len(all_values)} 行")

            row_num = _find_row_number_by_todo_id(all_values, todo_id)
            if row_num is None:
                err = f"ID {todo_id!r} の Todo が見つかりません。"
                print(f"[ERROR] {err}")
                return render_template(
                    "edit.html",
                    error=err,
                    todo_id=todo_id,
                    title=title,
                    content=content,
                    due=due,
                ), 404

            print(f"[DEBUG] 対象行番号（シート）: {row_num}")
            row = all_values[row_num - 1]
            title, content, due = _row_cells_for_edit(row)
            print(f"[DEBUG] 既存値: title={title!r}, content={content!r}, due={due!r}")

            return render_template(
                "edit.html",
                error=None,
                todo_id=todo_id,
                title=title,
                content=content,
                due=due,
            )

        except FileNotFoundError as e:
            error = f"credentials.json が見つかりません: {e}"
            print(f"[ERROR] {error}")
            traceback.print_exc()
        except gspread.exceptions.SpreadsheetNotFound:
            error = (
                f"スプレッドシートが見つかりません: {SPREADSHEET_NAME}。"
                "サービスアカウントを共有に追加したか確認してください。"
            )
            print(f"[ERROR] {error}")
            traceback.print_exc()
        except gspread.exceptions.WorksheetNotFound:
            error = f"シートが見つかりません: {WORKSHEET_NAME}"
            print(f"[ERROR] {error}")
            traceback.print_exc()
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            print(f"[ERROR] {error}")
            traceback.print_exc()

        return render_template(
            "edit.html",
            error=error,
            todo_id=todo_id,
            title=title,
            content=content,
            due=due,
        )

    print(f"[DEBUG] POST /edit/{todo_id!r} 保存")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    due = request.form.get("due", "").strip()
    print(f"[DEBUG] 入力: title={title!r}, content={content!r}, due={due!r}")

    if not title:
        error = "タイトルは必須です。"
        print(f"[ERROR] バリデーション: {error}")
        return render_template(
            "edit.html",
            error=error,
            todo_id=todo_id,
            title=title,
            content=content,
            due=due,
        )

    try:
        print("[DEBUG] シート接続・行更新開始")
        worksheet = _get_worksheet()
        all_values = worksheet.get_all_values()
        print(f"[DEBUG] get_all_values 完了: {len(all_values)} 行")

        row_num = _find_row_number_by_todo_id(all_values, todo_id)
        if row_num is None:
            error = f"ID {todo_id!r} の Todo が見つかりません（削除された可能性があります）。"
            print(f"[ERROR] {error}")
            return render_template(
                "edit.html",
                error=error,
                todo_id=todo_id,
                title=title,
                content=content,
                due=due,
            )

        new_row = [str(todo_id).strip(), title, content, due]
        range_a1 = f"A{row_num}:D{row_num}"
        print(f"[DEBUG] update 範囲: {range_a1} 値: {new_row}")
        worksheet.update(
            range_a1,
            [new_row],
            value_input_option="USER_ENTERED",
        )
        print("[DEBUG] 更新成功 → / へリダイレクト")
        return redirect(url_for("index"))

    except FileNotFoundError as e:
        error = f"credentials.json が見つかりません: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.SpreadsheetNotFound:
        error = (
            f"スプレッドシートが見つかりません: {SPREADSHEET_NAME}。"
            "サービスアカウントを共有に追加したか確認してください。"
        )
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.WorksheetNotFound:
        error = f"シートが見つかりません: {WORKSHEET_NAME}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()

    return render_template(
        "edit.html",
        error=error,
        todo_id=todo_id,
        title=title,
        content=content,
        due=due,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    error: str | None = None
    title = ""
    content = ""
    due = ""

    if request.method == "GET":
        print("[DEBUG] GET /add フォーム表示")
        return render_template(
            "add.html",
            error=None,
            title=title,
            content=content,
            due=due,
        )

    print("[DEBUG] POST /add 受信（フォーム送信）")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    due = request.form.get("due", "").strip()
    print(f"[DEBUG] 入力: title={title!r}, content={content!r}, due={due!r}")

    if not title:
        error = "タイトルは必須です。"
        print(f"[ERROR] バリデーション: {error}")
        return render_template(
            "add.html",
            error=error,
            title=title,
            content=content,
            due=due,
        )

    try:
        print("[DEBUG] シート接続・行追加開始")
        worksheet = _get_worksheet()
        all_values = worksheet.get_all_values()
        print(f"[DEBUG] get_all_values 完了: {len(all_values)} 行（見出し除くデータ行 {max(0, len(all_values) - 1)}）")

        next_id = _compute_next_id(all_values)
        print(f"[DEBUG] 自動採番 ID: {next_id}")

        new_row = [str(next_id), title, content, due]
        print(f"[DEBUG] append_row 実行: {new_row}")
        worksheet.append_row(new_row, value_input_option="USER_ENTERED")
        print("[DEBUG] 保存成功 → / へリダイレクト")
        return redirect(url_for("index"))

    except FileNotFoundError as e:
        error = f"credentials.json が見つかりません: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.SpreadsheetNotFound:
        error = (
            f"スプレッドシートが見つかりません: {SPREADSHEET_NAME}。"
            "サービスアカウントを共有に追加したか確認してください。"
        )
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.WorksheetNotFound:
        error = f"シートが見つかりません: {WORKSHEET_NAME}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()

    return render_template(
        "add.html",
        error=error,
        title=title,
        content=content,
        due=due,
    )


@app.route("/")
def index():
    print("[DEBUG] GET / リクエスト受信")
    headers: list[str] = []
    todos: list[dict[str, str]] = []
    error: str | None = None

    try:
        print("[DEBUG] シート接続・データ取得開始")
        worksheet = _get_worksheet()
        all_values = worksheet.get_all_values()
        print(f"[DEBUG] get_all_values 完了: {len(all_values)} 行")

        if not all_values:
            print("[DEBUG] データなし（空シート）")
            headers = _normalize_headers(None)
        else:
            headers = _normalize_headers(all_values[0])
            data_rows = all_values[1:]
            todos = _rows_to_todos(data_rows)
            print(f"[DEBUG] 見出し1行 + データ {len(todos)} 件")

        print("[DEBUG] テンプレート描画")
    except FileNotFoundError as e:
        error = f"credentials.json が見つかりません: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.SpreadsheetNotFound:
        error = (
            f"スプレッドシートが見つかりません: {SPREADSHEET_NAME}。"
            "サービスアカウントを共有に追加したか確認してください。"
        )
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.WorksheetNotFound:
        error = f"シートが見つかりません: {WORKSHEET_NAME}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()

    return render_template(
        "index.html",
        headers=headers,
        todos=todos,
        error=error,
    )


if __name__ == "__main__":
    print("[DEBUG] Flask 起動（http://127.0.0.1:5000）")
    app.run(debug=True, host="127.0.0.1", port=5000)
