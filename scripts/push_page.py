import os
import json
import argparse
import difflib
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUPS_DIR = ROOT_DIR / "backups"
MANIFEST_PATH = ROOT_DIR / "manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    if not BASE_URL or not TOKEN or not COURSE_ID:
        raise RuntimeError(
            "Missing .env values. Required: CANVAS_BASE_URL, CANVAS_TOKEN, COURSE_ID"
        )


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("manifest.json not found. Run pull_pages.py first.")

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_canvas_page(page_url):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{page_url}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def update_canvas_page(page_url, html_body):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{page_url}"

    payload = {
        "wiki_page[body]": html_body
    }

    response = requests.put(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def show_diff(canvas_html, local_html):
    diff = difflib.unified_diff(
        canvas_html.splitlines(keepends=True),
        local_html.splitlines(keepends=True),
        fromfile="Canvas current",
        tofile="Local edited file"
    )

    print("".join(diff))


def main():
    check_env()

    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="HTML filename from pages/")
    parser.add_argument("--apply", action="store_true", help="Actually push to Canvas")
    parser.add_argument("--no-diff", action="store_true", help="Skip diff output")

    args = parser.parse_args()

    manifest = load_manifest()

    if args.filename not in manifest["pages"]:
        raise ValueError(
            f"File not found in manifest.json: {args.filename}"
        )

    page_info = manifest["pages"][args.filename]
    page_url = page_info["canvas_url"]
    local_path = ROOT_DIR / page_info["html_file"]

    local_html = local_path.read_text(encoding="utf-8")

    canvas_page = get_canvas_page(page_url)
    canvas_html = canvas_page.get("body") or ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS_DIR / f"pre_push_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_file = backup_dir / args.filename
    backup_file.write_text(canvas_html, encoding="utf-8")

    print(f"Page title: {canvas_page.get('title')}")
    print(f"Canvas URL key: {page_url}")
    print(f"Local file: {local_path}")
    print(f"Backup saved: {backup_file}")

    if not args.no_diff:
        print("\nDiff preview:\n")
        show_diff(canvas_html, local_html)

    if not args.apply:
        print("\nDRY RUN ONLY. Nothing was pushed.")
        print("To push for real:")
        print(f'python scripts/push_page.py "{args.filename}" --apply')
        return

    updated_page = update_canvas_page(page_url, local_html)

    print("\nPushed successfully.")
    print(f"Updated page: {updated_page.get('title')}")
    print(f"Updated at: {updated_page.get('updated_at')}")


if __name__ == "__main__":
    main()