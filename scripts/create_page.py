from canvas_runtime import add_write_flags, authorize
import os
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT_DIR / "pages"
MANIFEST_PATH = ROOT_DIR / "manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def safe_filename(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "untitled"


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {"course_id": COURSE_ID, "base_url": BASE_URL, "pages": {}}

    from canvas_runtime import bound
    return bound(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")), BASE_URL, COURSE_ID)


def save_manifest(manifest):
    from canvas_runtime import save_json
    save_json(MANIFEST_PATH, manifest)


def create_canvas_page(title, body, published=False):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages"

    payload = {
        "wiki_page[title]": title,
        "wiki_page[body]": body,
        "wiki_page[published]": str(published).lower()
    }

    response = requests.post(url, headers=HEADERS, data=payload)

    if response.status_code == 409:
        raise RuntimeError(
            "A Canvas page with this title/url may already exist. "
            "Try a more unique title."
        )

    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Create a new Canvas page safely.")
    parser.add_argument("title", help="New Canvas page title")
    parser.add_argument(
        "--body-file",
        help="Optional local HTML file to use as the page body"
    )
    parser.add_argument(
        "--published",
        action="store_true",
        help="Publish the page immediately"
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.exists():
            raise FileNotFoundError(f"Body file not found: {body_path}")
        body = body_path.read_text(encoding="utf-8")
    else:
        from html import escape
        body = f"<h2>{escape(args.title)}</h2>\n<p>New page created by CanvasDaemon.</p>"

    manifest = load_manifest()

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    created_page = create_canvas_page(
        title=args.title,
        body=body,
        published=args.published
    )

    page_url = created_page["url"]
    title = created_page["title"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{safe_filename(title)}__{safe_filename(page_url)}.html"
    local_path = PAGES_DIR / filename
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    local_path.write_text(created_page.get("body") or body, encoding="utf-8")

    from canvas_runtime import body_hash
    manifest["pages"][filename] = {
        "body_sha256": body_hash(created_page.get("body") or body),
        "title": title,
        "canvas_url": page_url,
        "page_id": created_page.get("page_id"),
        "html_file": f"pages/{filename}",
        "last_canvas_update": created_page.get("updated_at"),
        "created_locally_at": timestamp
    }

    save_manifest(manifest)

    print("\nCreated Canvas page successfully.")
    print(f"Title: {title}")
    print(f"Canvas URL key: {page_url}")
    print(f"Published: {created_page.get('published')}")
    print(f"Local file: pages/{filename}")
    print("\nNext:")
    print(f'code "pages/{filename}"')
    print(f'python scripts/push_page.py "{filename}"')


if __name__ == "__main__":
    main()
