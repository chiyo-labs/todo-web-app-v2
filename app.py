import os
import traceback
from pathlib import Path
from datetime import datetime, date

import gspread
from flask import Flask, redirect, render_template, request, url_for
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# スプレッドシートID（URL の /d/ と /edit の間の文字列）。リポジトリに直書きせず環境変数で渡す。
SPREADSHEET_KEY = os.getenv("GOOGLE_SPREADSHEET_ID", "").strip()
WORKSHEET_NAME = "todos"

HEADER_FALLBACK = ["ID", "タイトル", "内容", "期日", "優先度", "完了"]

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))


def _normalize_headers(row: list[str] | None) -> list[str]:
    """スプレッドシート1行目を6列の見出しにそろえる（空セルはデフォルト文言）。"""
    if not row:
        return list(HEADER_FALLBACK)
    out: list[str] = []
    for i in range(6):
        if i < len(row) and str(row[i]).strip():
            out.append(str(row[i]).strip())
        else:
            out.append(HEADER_FALLBACK[i])
    return out


def _get_worksheet():
    if not SPREADSHEET_KEY:
        raise ValueError(
            "環境変数 GOOGLE_SPREADSHEET_ID が未設定です。"
            "対象スプレッドシートのURLからIDをコピーし、起動前に設定してください（README参照）。"
        )
    creds_path = BASE_DIR / "credentials.json"
    print(f"[DEBUG] credentials パス: {creds_path}")
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    print(f"[DEBUG] スプレッドシートを開く（ID）: {SPREADSHEET_KEY}")
    spreadsheet = client.open_by_key(SPREADSHEET_KEY)
    print(f"[DEBUG] ワークシート取得: {WORKSHEET_NAME}")
    return spreadsheet.worksheet(WORKSHEET_NAME)


def _rows_to_todos(data_rows: list[list[str]]) -> list[dict[str, str]]:
    """データ行を ID / タイトル / 内容 / 期日 / 優先度 / 完了 の dict にそろえる。"""
    todos: list[dict[str, str]] = []
    for row in data_rows:
        cells = list(row) + [""] * max(0, 6 - len(row))
        todos.append(
            {
                "id": cells[0],
                "title": cells[1],
                "content": cells[2],
                "due": cells[3],
                "priority": cells[4],
                "done": cells[5],
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


def _row_cells_for_edit(row: list[str]) -> tuple[str, str, str, str]:
    """データ行から タイトル・内容・期日・優先度 を取り出す（列不足は空文字）。"""
    cells = list(row) + [""] * max(0, 6 - len(row))
    return (
        cells[1] if len(cells) > 1 else "",
        cells[2] if len(cells) > 2 else "",
        cells[3] if len(cells) > 3 else "",
        cells[4] if len(cells) > 4 else "中",
    )


@app.route("/edit/<todo_id>", methods=["GET", "POST"])
def edit(todo_id: str):
    error: str | None = None
    title = ""
    content = ""
    due = ""
    priority = "中"

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
                    priority=priority,
                ), 404

            print(f"[DEBUG] 対象行番号（シート）: {row_num}")
            row = all_values[row_num - 1]
            title, content, due, priority = _row_cells_for_edit(row)
            print(f"[DEBUG] 既存値: title={title!r}, content={content!r}, due={due!r}, priority={priority!r}")

            return render_template(
                "edit.html",
                error=None,
                todo_id=todo_id,
                title=title,
                content=content,
                due=due,
                priority=priority,
            )

        except FileNotFoundError as e:
            error = f"credentials.json が見つかりません: {e}"
            print(f"[ERROR] {error}")
            traceback.print_exc()
        except gspread.exceptions.SpreadsheetNotFound:
            error = (
                f"スプレッドシートが見つかりません（ID）: {SPREADSHEET_KEY}。"
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
            priority=priority,
        )

    print(f"[DEBUG] POST /edit/{todo_id!r} 保存")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    due = request.form.get("due", "").strip()
    priority = request.form.get("priority", "").strip() or "中"
    print(f"[DEBUG] 入力: title={title!r}, content={content!r}, due={due!r}, priority={priority!r}")

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
            priority=priority,
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
                priority=priority,
            )

        row_existing = all_values[row_num - 1]
        cells_ex = list(row_existing) + [""] * max(0, 6 - len(row_existing))
        done_cell = cells_ex[5] if len(cells_ex) > 5 else ""

        new_row = [str(todo_id).strip(), title, content, due, priority, done_cell]
        range_a1 = f"A{row_num}:F{row_num}"
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
            f"スプレッドシートが見つかりません（ID）: {SPREADSHEET_KEY}。"
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
        priority=priority,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    error: str | None = None
    title = ""
    content = ""
    due = ""
    priority = "中"

    if request.method == "GET":
        print("[DEBUG] GET /add フォーム表示")
        return render_template(
            "add.html",
            error=None,
            title=title,
            content=content,
            due=due,
            priority=priority,
        )

    print("[DEBUG] POST /add 受信（フォーム送信）")
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    due = request.form.get("due", "").strip()
    priority = request.form.get("priority", "").strip() or "中"
    print(f"[DEBUG] 入力: title={title!r}, content={content!r}, due={due!r}, priority={priority!r}")

    if not title:
        error = "タイトルは必須です。"
        print(f"[ERROR] バリデーション: {error}")
        return render_template(
            "add.html",
            error=error,
            title=title,
            content=content,
            due=due,
            priority=priority,
        )

    try:
        print("[DEBUG] シート接続・行追加開始")
        worksheet = _get_worksheet()
        all_values = worksheet.get_all_values()
        print(f"[DEBUG] get_all_values 完了: {len(all_values)} 行（見出し除くデータ行 {max(0, len(all_values) - 1)}）")

        next_id = _compute_next_id(all_values)
        print(f"[DEBUG] 自動採番 ID: {next_id}")

        new_row = [str(next_id), title, content, due, priority, ""]
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
            f"スプレッドシートが見つかりません（ID）: {SPREADSHEET_KEY}。"
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
        priority=priority,
    )


@app.route("/toggle/<todo_id>", methods=["POST"])
def toggle_done(todo_id: str):
    print(f"[DEBUG] POST /toggle/{todo_id!r} 完了トグル")
    try:
        worksheet = _get_worksheet()
        all_values = worksheet.get_all_values()
        row_num = _find_row_number_by_todo_id(all_values, todo_id)
        if row_num is None:
            print(f"[ERROR] ID {todo_id!r} の行が見つかりません（toggle）")
            return redirect(url_for("index"))

        row = all_values[row_num - 1]
        cells = list(row) + [""] * max(0, 6 - len(row))
        current = str(cells[5]).strip() if len(cells) > 5 else ""
        new_done = "" if current == "完了" else "完了"
        new_row = [
            str(todo_id).strip(),
            cells[1] if len(cells) > 1 else "",
            cells[2] if len(cells) > 2 else "",
            cells[3] if len(cells) > 3 else "",
            cells[4] if len(cells) > 4 else "",
            new_done,
        ]
        worksheet.update(
            f"A{row_num}:F{row_num}",
            [new_row],
            value_input_option="USER_ENTERED",
        )
        print(f"[DEBUG] 完了列を更新: {new_done!r}")
    except Exception as e:
        print(f"[ERROR] toggle_done: {type(e).__name__}: {e}")
        traceback.print_exc()
    return redirect(url_for("index"))


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
            # 未完了を上・完了を下にし、各グループ内は期日が近い順（期日なし/不正はグループ末尾）。
            def _due_sort_key(todo: dict[str, str]) -> tuple[bool, date]:
                due_text = (todo.get("due") or "").strip()
                if not due_text:
                    return (True, date.max)
                try:
                    parsed = datetime.strptime(due_text, "%Y-%m-%d").date()
                    return (False, parsed)
                except Exception:
                    return (True, date.max)

            def _list_sort_key(todo: dict[str, str]) -> tuple[int, tuple[bool, date]]:
                is_done = (todo.get("done") or "").strip() == "完了"
                completion_rank = 1 if is_done else 0
                return (completion_rank, _due_sort_key(todo))

            todos.sort(key=_list_sort_key)
            print(f"[DEBUG] 見出し1行 + データ {len(todos)} 件（未完了→完了、期日順）")

        print("[DEBUG] テンプレート描画")
    except FileNotFoundError as e:
        error = f"credentials.json が見つかりません: {e}"
        print(f"[ERROR] {error}")
        traceback.print_exc()
    except gspread.exceptions.SpreadsheetNotFound:
        error = (
            f"スプレッドシートが見つかりません（ID）: {SPREADSHEET_KEY}。"
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
