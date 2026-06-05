import os
import json
import re
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT_DIR / "pages"
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


def safe_filename(text):
    """
    Converts a Canvas page title/url into a safe local filename.

    Example:
    'M01: AI Hidden in Plain Sight — Module Overview'
    becomes:
    'm01-ai-hidden-in-plain-sight-module-overview'
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "untitled"


def get_all_pages():
    """
    Lists all Canvas pages in the course.

    Canvas may return results in chunks.
    That is called pagination.

    We follow the 'next' link until there are no more pages.
    """
    all_pages = []

    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages"
    params = {"per_page": 100}

    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()

        all_pages.extend(response.json())

        next_link = response.links.get("next", {}).get("url")
        url = next_link

        # After the first request, the next URL already contains its own params.
        params = None

    return all_pages


def get_page_details(page_url):
    """
    Gets one full Canvas page, including its HTML body.

    The list endpoint gives title/url.
    This endpoint gives the actual editable page body.
    """
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{page_url}"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    return response.json()


def main():
    check_env()

    PAGES_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_run_dir = BACKUPS_DIR / f"pull_{timestamp}"
    backup_run_dir.mkdir(exist_ok=True)

    pages = get_all_pages()

    print(f"Found {len(pages)} Canvas pages.")

    manifest = {
        "course_id": COURSE_ID,
        "base_url": BASE_URL,
        "pulled_at": timestamp,
        "pages": {}
    }

    for index, page in enumerate(pages, start=1):
        page_url = page["url"]
        page_details = get_page_details(page_url)

        title = page_details.get("title", "Untitled Page")
        body = page_details.get("body") or ""

        filename = f"{safe_filename(title)}__{page_url}.html"

        local_path = PAGES_DIR / filename
        backup_path = backup_run_dir / filename

        local_path.write_text(body, encoding="utf-8")
        backup_path.write_text(body, encoding="utf-8")

        manifest["pages"][filename] = {
            "title": title,
            "canvas_url": page_url,
            "page_id": page_details.get("page_id"),
            "html_file": f"pages/{filename}",
            "last_canvas_update": page_details.get("updated_at")
        }

        print(f"[{index}/{len(pages)}] Pulled: {title}")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print("\nPull complete.")
    print(f"Local pages saved in: {PAGES_DIR}")
    print(f"Backup copy saved in: {backup_run_dir}")
    print(f"Manifest saved to: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()