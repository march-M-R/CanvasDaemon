import os
import json
import csv
from pathlib import Path
from collections import defaultdict

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT_DIR / "manifest.json"
REPORTS_DIR = ROOT_DIR / "reports"
PAGES_REPORTS_DIR = REPORTS_DIR / "pages"

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
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("manifest.json not found. Run pull_pages.py first.")

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main():
    check_env()
    PAGES_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    all_manifest_pages = manifest["pages"]

    canvas_url_to_file = {
        info["canvas_url"]: filename
        for filename, info in all_manifest_pages.items()
    }

    title_to_files = defaultdict(list)

    for filename, info in all_manifest_pages.items():
        title_to_files[info["title"]].append(filename)

    used_pages = []
    used_files = set()

    modules_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules"
    modules = canvas_get_all(modules_url, params={"per_page": 100})

    for module in modules:
        module_id = module["id"]
        module_name = module["name"]

        items_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules/{module_id}/items"
        items = canvas_get_all(items_url, params={"per_page": 100})

        for position, item in enumerate(items, start=1):
            if item.get("type") != "Page":
                continue

            page_url = item.get("page_url")
            local_file = canvas_url_to_file.get(page_url)

            row = {
                "module_name": module_name,
                "module_position": module.get("position"),
                "item_position": position,
                "page_title": item.get("title"),
                "canvas_page_url": page_url,
                "local_file": local_file or "NOT_FOUND_IN_MANIFEST",
            }

            used_pages.append(row)

            if local_file:
                used_files.add(local_file)

    all_files = set(all_manifest_pages.keys())
    unused_files = sorted(all_files - used_files)

    duplicate_titles = {
        title: files
        for title, files in title_to_files.items()
        if len(files) > 1
    }

    used_csv = PAGES_REPORTS_DIR / "used_module_pages.csv"
    unused_txt = PAGES_REPORTS_DIR / "unused_pages.txt"
    duplicates_txt = PAGES_REPORTS_DIR / "duplicate_titles.txt"
    summary_txt = PAGES_REPORTS_DIR / "inventory_summary.txt"

    with used_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "module_name",
                "module_position",
                "item_position",
                "page_title",
                "canvas_page_url",
                "local_file",
            ],
        )
        writer.writeheader()
        writer.writerows(used_pages)

    unused_txt.write_text(
        "\n".join(unused_files),
        encoding="utf-8",
    )

    duplicate_lines = []

    for title, files in sorted(duplicate_titles.items()):
        duplicate_lines.append(f"\nTITLE: {title}")
        for file in files:
            duplicate_lines.append(f"  - {file}")

    duplicates_txt.write_text(
        "\n".join(duplicate_lines),
        encoding="utf-8",
    )

    summary = f"""
COURSE INVENTORY SUMMARY
========================

Course ID: {COURSE_ID}
Base URL: {BASE_URL}

Total Canvas pages pulled:
{len(all_files)}

Pages used in Modules:
{len(used_files)}

Pages not used in Modules:
{len(unused_files)}

Duplicate page titles:
{len(duplicate_titles)}

Reports created:
- reports/pages/used_module_pages.csv
- reports/pages/unused_pages.txt
- reports/pages/duplicate_titles.txt
- reports/pages/inventory_summary.txt
""".strip()

    summary_txt.write_text(summary, encoding="utf-8")

    print(summary)


if __name__ == "__main__":
    main()
