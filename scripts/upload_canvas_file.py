import os
import json
import argparse
import mimetypes
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    if not BASE_URL or not TOKEN or not COURSE_ID:
        raise RuntimeError(
            "Missing .env values. Required: CANVAS_BASE_URL, CANVAS_TOKEN, COURSE_ID"
        )


def load_asset_manifest():
    if ASSET_MANIFEST_PATH.exists():
        return json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))

    return {
        "course_id": COURSE_ID,
        "base_url": BASE_URL,
        "files": {}
    }


def save_asset_manifest(manifest):
    ASSET_MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )


def guess_content_type(file_path):
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or "application/octet-stream"


def start_upload(file_path, folder_path, on_duplicate):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files"

    payload = {
        "name": file_path.name,
        "size": file_path.stat().st_size,
        "content_type": guess_content_type(file_path),
        "parent_folder_path": folder_path,
        "on_duplicate": on_duplicate,
        "success_include[]": ["preview_url", "usage_rights"]
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def upload_binary(file_path, upload_info):
    upload_url = upload_info["upload_url"]
    upload_params = upload_info["upload_params"]

    with file_path.open("rb") as f:
        files = {
            "file": (file_path.name, f, guess_content_type(file_path))
        }

        response = requests.post(
            upload_url,
            data=upload_params,
            files=files,
            allow_redirects=True
        )

    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        # Some Canvas/S3 flows return a redirect/HTML response.
        # If so, follow the Location header if available.
        location = response.headers.get("Location")
        if location:
            final_response = requests.get(location, headers=HEADERS)
            final_response.raise_for_status()
            return final_response.json()

        raise RuntimeError(
            "Upload completed but Canvas did not return JSON. "
            "Check Canvas Files to confirm upload."
        )


def main():
    check_env()

    parser = argparse.ArgumentParser(description="Upload a local file to Canvas Files.")
    parser.add_argument("file_path", help="Local file path to upload")
    parser.add_argument(
        "--folder",
        default="CanvasDaemon",
        help="Canvas Files folder path. Example: CanvasDaemon/activities"
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Rename if a file with the same name exists. Default is overwrite."
    )

    args = parser.parse_args()

    file_path = Path(args.file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Local file not found: {file_path}")

    on_duplicate = "rename" if args.rename else "overwrite"

    upload_info = start_upload(
        file_path=file_path,
        folder_path=args.folder,
        on_duplicate=on_duplicate
    )

    uploaded_file = upload_binary(file_path, upload_info)

    manifest = load_asset_manifest()

    file_id = str(uploaded_file.get("id"))

    manifest["files"][file_id] = {
        "file_id": uploaded_file.get("id"),
        "filename": uploaded_file.get("filename") or file_path.name,
        "display_name": uploaded_file.get("display_name"),
        "category": "uploaded_local",
        "content_type": uploaded_file.get("content-type") or uploaded_file.get("content_type"),
        "size": uploaded_file.get("size"),
        "url": uploaded_file.get("url"),
        "preview_url": uploaded_file.get("preview_url"),
        "folder_id": uploaded_file.get("folder_id"),
        "created_at": uploaded_file.get("created_at"),
        "updated_at": uploaded_file.get("updated_at"),
        "locked": uploaded_file.get("locked"),
        "hidden": uploaded_file.get("hidden"),
        "local_source": str(file_path),
        "canvas_folder": args.folder
    }

    save_asset_manifest(manifest)

    print("\nUploaded file successfully.")
    print(f"Local file: {file_path}")
    print(f"Canvas file ID: {uploaded_file.get('id')}")
    print(f"Canvas filename: {uploaded_file.get('filename')}")
    print(f"Canvas URL: {uploaded_file.get('url')}")
    print(f"Canvas folder: {args.folder}")
    print("\nNext:")
    print("python scripts/pull_files_metadata.py")


if __name__ == "__main__":
    main()