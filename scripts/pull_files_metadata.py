import os
import json
import csv
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]

ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
REPORTS_DIR = ROOT_DIR / "reports"
CANVAS_FILES_CSV = REPORTS_DIR / "canvas_files.csv"

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


def get_all_files():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files"
    return canvas_get_all(url, params={"per_page": 100})


def classify_file(filename, content_type):
    name = (filename or "").lower()
    content_type = (content_type or "").lower()

    if name.endswith((".html", ".css", ".js", ".json", ".txt")):
        return "editable"

    if content_type.startswith("image/"):
        return "image"

    if content_type == "application/pdf" or name.endswith(".pdf"):
        return "pdf"

    if content_type.startswith("video/"):
        return "video"

    if content_type.startswith("audio/"):
        return "audio"

    return "other"


def main():
    check_env()
    REPORTS_DIR.mkdir(exist_ok=True)

    files = get_all_files()

    asset_manifest = {
        "course_id": COURSE_ID,
        "base_url": BASE_URL,
        "files": {}
    }

    csv_rows = []

    for file in files:
        filename = file.get("filename") or file.get("display_name") or "unknown"
        file_id = file.get("id")
        content_type = file.get("content-type") or file.get("content_type")
        category = classify_file(filename, content_type)

        row = {
            "file_id": file_id,
            "filename": filename,
            "display_name": file.get("display_name"),
            "category": category,
            "content_type": content_type,
            "size": file.get("size"),
            "url": file.get("url"),
            "folder_id": file.get("folder_id"),
            "created_at": file.get("created_at"),
            "updated_at": file.get("updated_at"),
            "locked": file.get("locked"),
            "hidden": file.get("hidden")
        }

        csv_rows.append(row)
        asset_manifest["files"][str(file_id)] = row

    ASSET_MANIFEST_PATH.write_text(
        json.dumps(asset_manifest, indent=2),
        encoding="utf-8"
    )

    with CANVAS_FILES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file_id",
                "filename",
                "display_name",
                "category",
                "content_type",
                "size",
                "url",
                "folder_id",
                "created_at",
                "updated_at",
                "locked",
                "hidden"
            ]
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    editable_count = sum(1 for row in csv_rows if row["category"] == "editable")

    print("Canvas files pulled successfully.")
    print(f"Total files found: {len(csv_rows)}")
    print(f"Editable files found: {editable_count}")
    print(f"Asset manifest saved to: {ASSET_MANIFEST_PATH}")
    print(f"CSV report saved to: {CANVAS_FILES_CSV}")


if __name__ == "__main__":
    main()