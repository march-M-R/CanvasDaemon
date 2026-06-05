import os
import json
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT_DIR / "manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    if not BASE_URL or not TOKEN or not COURSE_ID:
        raise RuntimeError(
            "Missing .env values. Required: CANVAS_BASE_URL, CANVAS_TOKEN, COURSE_ID"
        )


def canvas_get_all(url, params=None):
    results = []

    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()

        results.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None

    return results


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("manifest.json not found. Run pull_pages.py first.")

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def find_page_in_manifest(filename):
    manifest = load_manifest()

    if filename not in manifest["pages"]:
        raise ValueError(f"File not found in manifest.json: {filename}")

    return manifest["pages"][filename]


def list_modules():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules"
    return canvas_get_all(url, params={"per_page": 100})


def find_module_by_name(module_name):
    modules = list_modules()
    matches = [
        module for module in modules
        if module_name.lower() in module["name"].lower()
    ]

    if not matches:
        raise ValueError(f'No module found matching: "{module_name}"')

    if len(matches) > 1:
        print("\nMultiple modules matched. Be more specific:\n")
        for module in matches:
            print(f'- {module["name"]}')
        raise SystemExit(1)

    return matches[0]


def add_page_to_module(module_id, page_title, page_url, indent=0):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules/{module_id}/items"

    payload = {
        "module_item[type]": "Page",
        "module_item[title]": page_title,
        "module_item[page_url]": page_url,
        "module_item[indent]": indent
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()

    return response.json()


def main():
    check_env()

    parser = argparse.ArgumentParser(
        description="Add an existing Canvas page to a Canvas Module."
    )
    parser.add_argument("filename", help="HTML filename from pages/")
    parser.add_argument("module", help="Module name or partial module name")
    parser.add_argument("--indent", type=int, default=0, help="Module item indent level")

    args = parser.parse_args()

    page_info = find_page_in_manifest(args.filename)
    page_title = page_info["title"]
    page_url = page_info["canvas_url"]

    module = find_module_by_name(args.module)

    created_item = add_page_to_module(
        module_id=module["id"],
        page_title=page_title,
        page_url=page_url,
        indent=args.indent
    )

    print("\nPage added to module successfully.")
    print(f"Module: {module['name']}")
    print(f"Page title: {page_title}")
    print(f"Canvas page URL key: {page_url}")
    print(f"Module item title: {created_item.get('title')}")
    print(f"Module item position: {created_item.get('position')}")
    print("\nNext recommended commands:")
    print("python scripts/course_inventory.py")
    print("python scripts/find_page.py \"{}\"".format(page_title))


if __name__ == "__main__":
    main()