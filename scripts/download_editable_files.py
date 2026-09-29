import os
import json
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")

ROOT_DIR = Path(__file__).resolve().parents[1]

ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
EDITABLE_DIR = ROOT_DIR / "canvas_files" / "editable"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

EDITABLE_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".txt"
}


def load_manifest():
    if not ASSET_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "asset_manifest.json not found. Run pull_files_metadata.py first."
        )

    return json.loads(
        ASSET_MANIFEST_PATH.read_text(encoding="utf-8")
    )


def safe_filename(name):
    return (
        name.replace("/", "_")
        .replace("\\", "_")
        .strip()
    )


def download_file(url, destination):
    from canvas_runtime import download
    destination.write_bytes(download(url, HEADERS))


def main():
    manifest = load_manifest()

    EDITABLE_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    for _, file_info in manifest["files"].items():

        filename = file_info.get("filename")

        if not filename:
            continue

        extension = Path(filename).suffix.lower()

        if extension not in EDITABLE_EXTENSIONS:
            continue

        url = file_info.get("url")

        if not url:
            continue

        local_path = EDITABLE_DIR / safe_filename(filename)

        try:
            download_file(url, local_path)

            print(f"Downloaded: {filename}")

            downloaded += 1

        except Exception as e:
            print(f"Failed: {filename}")
            print(e)

    print()
    print(f"Editable files downloaded: {downloaded}")
    print(f"Location: {EDITABLE_DIR}")


if __name__ == "__main__":
    main()
