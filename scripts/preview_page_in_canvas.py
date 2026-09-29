from canvas_runtime import add_write_flags, authorize
import os
import json
import argparse
import webbrowser
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT_DIR / "pages"
PREVIEW_CONFIG_PATH = ROOT_DIR / "preview_config.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def load_preview_config():
    if not PREVIEW_CONFIG_PATH.exists():
        raise FileNotFoundError(
            "preview_config.json not found.\n"
            "Run: python scripts/setup_preview_environment.py"
        )

    from canvas_runtime import bound
    return bound(json.loads(PREVIEW_CONFIG_PATH.read_text(encoding="utf-8")), BASE_URL, COURSE_ID)


def resolve_page_path(filename):
    page_path = Path(filename)

    if page_path.exists():
        return page_path

    page_path = PAGES_DIR / filename

    if page_path.exists():
        return page_path

    raise FileNotFoundError(f"Page file not found: {filename}")


def update_preview_page(preview_page_url, html_body):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{preview_page_url}"

    current = requests.get(url, headers=HEADERS)
    current.raise_for_status()
    if current.json().get("published"):
        raise ValueError("Refusing to overwrite a published preview page.")

    payload = {
        "wiki_page[body]": html_body,
        "wiki_page[published]": "false"
    }

    response = requests.put(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def wrap_preview_html(source_file, html_body):
    from html import escape
    source_file = escape(source_file)
    return f"""
<div style="border: 2px dashed #A32638; border-radius: 12px; padding: 16px; margin-bottom: 24px; background: #fff7f8;">
  <h2 style="margin-top: 0;">CanvasDaemon Page Preview</h2>
  <p><strong>Source file:</strong> {source_file}</p>
  <p style="margin-bottom: 0;">This is a Canvas-rendered preview. The content below has been inserted into the dedicated CanvasDaemon preview page.</p>
</div>

{html_body}
""".strip()


def main():
    parser = argparse.ArgumentParser(
        description="Preview a local Canvas page inside the real Canvas editor/render environment."
    )

    parser.add_argument(
        "filename",
        help="Page HTML filename from pages/ or full local path"
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the preview page in the browser"
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    config = load_preview_config()
    preview_page_url = config["preview_page_url"]
    preview_html_url = config["preview_page_html_url"]

    page_path = resolve_page_path(args.filename)
    html_body = page_path.read_text(encoding="utf-8", errors="replace")

    preview_body = wrap_preview_html(page_path.name, html_body)

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    updated = update_preview_page(preview_page_url, preview_body)

    print("\nCanvas preview page updated.")
    print(f"Source file: {page_path}")
    print(f"Preview page: {updated.get('title')}")
    print(f"Canvas URL: {preview_html_url}")

    if not args.no_open:
        webbrowser.open(preview_html_url)
        print("Opened preview page in browser.")


if __name__ == "__main__":
    main()
