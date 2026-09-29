from canvas_runtime import authorize
import os
import json
import argparse
import difflib
import csv
from pathlib import Path
from datetime import datetime

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUPS_DIR = ROOT_DIR / "backups"
MANIFEST_PATH = ROOT_DIR / "manifest.json"
USED_MODULE_PAGES_PATH = ROOT_DIR / "reports" / "pages" / "used_module_pages.csv"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("manifest.json not found. Run pull_pages.py first.")

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def find_active_module_page(filename):
    if not USED_MODULE_PAGES_PATH.exists():
        return None

    with USED_MODULE_PAGES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            local_file = row.get("local_file", "")
            if local_file.endswith(filename):
                html_file = local_file if "/" in local_file else f"pages/{local_file}"
                return {
                    "title": row.get("page_title", ""),
                    "canvas_url": row["canvas_page_url"],
                    "html_file": html_file,
                }

    return None


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
    from canvas_runtime import bound, body_hash, save_json
    parser = argparse.ArgumentParser(description="Diff and safely update a Canvas page.")
    parser.add_argument("filename", help="HTML filename from pages/")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-course", help="Required with --apply")
    parser.add_argument("--no-diff", action="store_true")
    args = parser.parse_args()
    check_env()
    if Path(args.filename).name != args.filename:
        raise ValueError("Pass a plain filename from pages/.")
    manifest = bound(load_manifest(), BASE_URL, COURSE_ID)
    info = manifest["pages"].get(args.filename) or find_active_module_page(args.filename)
    if not info:
        raise ValueError("Page not found in the manifest or active inventory.")
    path = (ROOT_DIR / info["html_file"]).resolve()
    if ROOT_DIR.resolve() not in path.parents:
        raise ValueError("Manifest file points outside this checkout.")
    local_html = path.read_text(encoding="utf-8")
    current = get_canvas_page(info["canvas_url"])
    old = current.get("body") or ""
    print(f"Page: {current.get('title')} ({info['canvas_url']})")
    if not args.no_diff:
        show_diff(old, local_html)
    if not authorize(args, BASE_URL, COURSE_ID):
        return
    if info.get("body_sha256"):
        if body_hash(old) != info["body_sha256"]:
            raise ValueError("Canvas changed since pull. Preserve local edits and merge with a fresh pull.")
    elif info.get("last_canvas_update"):
        if current.get("updated_at") != info["last_canvas_update"]:
            raise ValueError("Canvas changed since pull. Preserve local edits and merge first.")
    else:
        raise ValueError("No conflict baseline. Preserve local edits and pull this page before applying.")
    if old == local_html:
        print("No changes to push.")
        return
    folder = BACKUPS_DIR / ("pre_push_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(parents=True)
    (folder / args.filename).write_text(old, encoding="utf-8")
    save_json(folder / "page.json", current)
    updated = update_canvas_page(info["canvas_url"], local_html)
    # Preserve the authored file. Canvas sanitization is reported, never silently accepted.
    returned_body = updated.get("body")
    if returned_body is None:
        returned_body = get_canvas_page(info["canvas_url"]).get("body") or ""
    info.update({"body_sha256": body_hash(returned_body), "last_canvas_update": updated.get("updated_at")})
    manifest["pages"][args.filename] = info
    save_json(MANIFEST_PATH, manifest)
    if returned_body != local_html:
        print("Canvas adjusted the HTML. Inspect the Canvas rendering before continuing.")
    print(f"Updated {info['canvas_url']}; previous body saved in {folder}.")


if __name__ == "__main__":
    main()
