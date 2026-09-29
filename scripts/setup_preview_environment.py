import os
import json
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
PREVIEW_CONFIG_PATH = ROOT_DIR / "preview_config.json"
PAGES_DIR = ROOT_DIR / "pages"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

PREVIEW_PAGE_TITLE = "CanvasDaemon Preview Page"
PREVIEW_PAGE_URL = "canvasdaemon-preview-page"


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def get_page(page_url):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{page_url}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def create_page():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages"

    body = """
<div style="padding: 24px; border: 2px dashed #A32638; border-radius: 12px;">
  <h1>CanvasDaemon Preview Page</h1>
  <p>This page is used only for CanvasDaemon previews.</p>
  <p>Preview scripts may overwrite this content.</p>
</div>
""".strip()

    payload = {
        "wiki_page[title]": PREVIEW_PAGE_TITLE,
        "wiki_page[body]": body,
        "wiki_page[published]": "false"
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def update_local_preview_file(page):
    PAGES_DIR.mkdir(exist_ok=True)

    filename = f"{PREVIEW_PAGE_URL}__{PREVIEW_PAGE_URL}.html"
    local_path = PAGES_DIR / filename

    local_path.write_text(page.get("body") or "", encoding="utf-8")

    return filename, local_path


def save_config(page, local_filename):
    config = {
        "course_id": COURSE_ID,
        "base_url": BASE_URL,
        "preview_page_title": PREVIEW_PAGE_TITLE,
        "preview_page_url": page.get("url") or PREVIEW_PAGE_URL,
        "preview_page_id": page.get("page_id") or page.get("id"),
        "preview_page_html_url": page.get("html_url"),
        "local_preview_file": f"pages/{local_filename}",
        "preview_asset_folder": "CanvasDaemon Preview Assets"
    }

    PREVIEW_CONFIG_PATH.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8"
    )

    return config


def main():
    import argparse
    from canvas_runtime import add_write_flags, authorize
    parser = argparse.ArgumentParser(description="Set up an unpublished Canvas preview page")
    add_write_flags(parser)
    args = parser.parse_args()
    check_env()
    if not authorize(args, BASE_URL, COURSE_ID):
        return

    page = get_page(PREVIEW_PAGE_URL)

    if page and page.get("published"):
        raise ValueError("The preview page is published. Unpublish it in Canvas before reuse.")
    if page:
        print("Preview page already exists.")
    else:
        print("Creating preview page...")
        page = create_page()

    local_filename, local_path = update_local_preview_file(page)
    config = save_config(page, local_filename)

    print()
    print("CanvasDaemon preview environment ready.")
    print(f"Preview page title: {config['preview_page_title']}")
    print(f"Canvas URL key: {config['preview_page_url']}")
    print(f"Canvas page URL: {config['preview_page_html_url']}")
    print(f"Local preview file: {local_path}")
    print(f"Config saved: {PREVIEW_CONFIG_PATH}")


if __name__ == "__main__":
    main()
