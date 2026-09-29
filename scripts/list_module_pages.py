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
MANIFEST_PATH = ROOT_DIR / "manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def canvas_get_all(url, params=None):
    results = []

    seen_urls = set()
    while url:
        if url in seen_urls:
            raise RuntimeError("Canvas repeated a pagination URL.")
        seen_urls.add(url)
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()

        results.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None

    return results


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main():
    check_env()

    manifest = load_manifest()

    # Reverse lookup:
    # canvas_url -> local filename
    page_url_to_file = {
        info["canvas_url"]: filename
        for filename, info in manifest["pages"].items()
    }

    modules_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules"
    modules = canvas_get_all(modules_url, params={"per_page": 100})

    print(f"Found {len(modules)} modules.\n")

    module_page_files = []

    for module in modules:
        module_name = module["name"]
        module_id = module["id"]

        print("=" * 80)
        print(f"MODULE: {module_name}")
        print("=" * 80)

        items_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules/{module_id}/items"
        items = canvas_get_all(items_url, params={"per_page": 100})

        found_any_pages = False

        for item in items:
            if item.get("type") != "Page":
                continue

            found_any_pages = True

            page_url = item.get("page_url")
            title = item.get("title")

            local_file = page_url_to_file.get(page_url)

            if local_file:
                module_page_files.append(local_file)
                print(f"- {title}")
                print(f"  Canvas page URL: {page_url}")
                print(f"  Local file: pages/{local_file}")
            else:
                print(f"- {title}")
                print(f"  Canvas page URL: {page_url}")
                print("  Local file: NOT FOUND IN manifest.json")
                print("  Try running: python scripts/pull_pages.py")

        if not found_any_pages:
            print("(No Canvas pages in this module)")

        print()

    # Save a clean list for later use
    output_path = ROOT_DIR / "module_pages.txt"

    unique_files = sorted(set(module_page_files))

    output_path.write_text(
        "\n".join(unique_files),
        encoding="utf-8"
    )

    print("=" * 80)
    print(f"Saved {len(unique_files)} unique module page files to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
