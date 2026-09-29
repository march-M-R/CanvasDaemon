import os
import json
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
BACKUPS_DIR = ROOT_DIR / "backups"
MANIFEST_PATH = ROOT_DIR / "manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}
TIMEOUT = (10, 25)


def request_with_retry(method, url, **kwargs):
    # The caller can rerun a failed read; never silently retry a write.
    response = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    return response


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def safe_filename(text):
    """
    Converts a Canvas page title/url into a safe local filename.

    Example:
    'M01: AI Hidden in Plain Sight - Module Overview'
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

    seen_urls = set()
    while url:
        if url in seen_urls:
            raise RuntimeError("Canvas repeated a pagination URL.")
        seen_urls.add(url)
        response = request_with_retry("GET", url, headers=HEADERS, params=params)

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

    response = request_with_retry("GET", url, headers=HEADERS)
    return response.json()


def main():
    import argparse
    from canvas_runtime import bound, body_hash, save_json
    parser = argparse.ArgumentParser(description="Pull Canvas pages, preserving unpushed local work.")
    parser.add_argument("--overwrite-local", action="store_true", help="Explicitly replace edited local pages after backing them up")
    args = parser.parse_args()
    check_env()
    previous = bound(json.loads(MANIFEST_PATH.read_text()), BASE_URL, COURSE_ID) if MANIFEST_PATH.exists() else {"pages": {}}
    incoming = []
    by_url = {v["canvas_url"]: (k, v) for k, v in previous["pages"].items()}
    for page in get_all_pages():
        details = get_page_details(page["url"])
        title, body = details.get("title", "Untitled Page"), details.get("body") or ""
        default_name = f"{safe_filename(title)}__{safe_filename(page['url'])}.html"
        filename, old = by_url.get(page["url"], (default_name, {}))
        if Path(filename).name != filename:
            raise ValueError("Manifest filenames must be plain filenames.")
        path = PAGES_DIR / filename
        if path.exists() and not args.overwrite_local:
            baseline = old.get("body_sha256")
            local_body = path.read_text(encoding="utf-8")
            if (baseline and body_hash(local_body) != baseline) or (not baseline and local_body != body):
                raise ValueError(f"Local edits in {filename}. Preserve/merge them, or use --overwrite-local for a backed-up replacement.")
        incoming.append((filename, details, body))
    # All downloads and conflict checks succeed before replacing any local content.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = BACKUPS_DIR / f"pre_pull_{timestamp}"
    backup_dir.mkdir(parents=True)
    if MANIFEST_PATH.exists():
        (backup_dir / "manifest.json").write_bytes(MANIFEST_PATH.read_bytes())
    PAGES_DIR.mkdir(exist_ok=True)
    manifest = {"course_id": COURSE_ID, "base_url": BASE_URL, "pulled_at": timestamp, "pages": {}}
    for filename, details, body in incoming:
        path = PAGES_DIR / filename
        if path.exists():
            (backup_dir / filename).write_bytes(path.read_bytes())
        path.write_text(body, encoding="utf-8")
        manifest["pages"][filename] = {"title": details["title"], "canvas_url": details["url"],
            "page_id": details.get("page_id"), "html_file": "pages/" + filename,
            "last_canvas_update": details.get("updated_at"), "body_sha256": body_hash(body)}
    save_json(MANIFEST_PATH, manifest)
    print(f"Pulled {len(incoming)} pages. Previous local files backed up in {backup_dir}.")


if __name__ == "__main__":
    main()
