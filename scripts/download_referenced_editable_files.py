import csv
import json
import re
from pathlib import Path

from canvas_runtime import requests
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]

PAGES_DIR = ROOT_DIR / "pages"
REPORTS_DIR = ROOT_DIR / "reports"
USED_MODULE_PAGES_CSV = REPORTS_DIR / "pages" / "used_module_pages.csv"

ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
OUTPUT_DIR = ROOT_DIR / "canvas_files" / "editable" / "referenced"

EDITABLE_EXTENSIONS = {".html", ".css", ".js", ".json", ".txt"}


def load_active_page_files():
    if not USED_MODULE_PAGES_CSV.exists():
        raise FileNotFoundError(
            "reports/pages/used_module_pages.csv not found.\n"
            "Run: python scripts/course_inventory.py"
        )

    active_files = []

    with USED_MODULE_PAGES_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            local_file = row.get("local_file")
            if local_file and local_file != "NOT_FOUND_IN_MANIFEST":
                active_files.append(local_file)

    return active_files


def load_asset_manifest():
    if not ASSET_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "asset_manifest.json not found.\n"
            "Run: python scripts/pull_files_metadata.py"
        )

    return json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))


def extract_file_ids_from_html(html):
    file_ids = set()

    for match in re.findall(r"/files/(\d+)", html):
        file_ids.add(match)

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "img", "iframe", "source", "script", "link"]):
        for attr in ["href", "src"]:
            value = tag.get(attr)
            if not value:
                continue

            match = re.search(r"/files/(\d+)", value)
            if match:
                file_ids.add(match.group(1))

    return file_ids


def safe_filename(name):
    return name.replace("/", "_").replace("\\", "_").strip()


def is_editable(filename):
    return Path(filename).suffix.lower() in EDITABLE_EXTENSIONS


def download_file(url, destination):
    response = requests.get(url)
    response.raise_for_status()
    destination.write_bytes(response.content)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    active_page_files = load_active_page_files()
    manifest = load_asset_manifest()
    canvas_files = manifest["files"]

    referenced_file_ids = set()

    for page_file in active_page_files:
        page_path = PAGES_DIR / page_file

        if not page_path.exists():
            continue

        html = page_path.read_text(encoding="utf-8", errors="replace")
        referenced_file_ids.update(extract_file_ids_from_html(html))

    print(f"Referenced Canvas file IDs found in active pages: {len(referenced_file_ids)}")

    downloaded = 0
    skipped_non_editable = 0
    missing_from_manifest = 0

    for file_id in sorted(referenced_file_ids):
        file_info = canvas_files.get(str(file_id))

        if not file_info:
            missing_from_manifest += 1
            print(f"Missing from asset_manifest.json: file_id={file_id}")
            continue

        filename = file_info.get("filename") or file_info.get("display_name")

        if not filename or not is_editable(filename):
            skipped_non_editable += 1
            continue

        url = file_info.get("url")

        if not url:
            print(f"No URL found for: {filename}")
            continue

        destination = OUTPUT_DIR / f"{file_id}__{safe_filename(filename)}"

        try:
            download_file(url, destination)
            downloaded += 1
            print(f"Downloaded referenced editable file: {destination.name}")
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

    print()
    print("Done.")
    print(f"Referenced file IDs: {len(referenced_file_ids)}")
    print(f"Downloaded editable files: {downloaded}")
    print(f"Skipped non-editable files: {skipped_non_editable}")
    print(f"Missing from manifest: {missing_from_manifest}")
    print(f"Output folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
