from canvas_runtime import add_write_flags, authorize
import os
import json
import argparse
import mimetypes
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

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
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def load_asset_manifest():
    if ASSET_MANIFEST_PATH.exists():
        from canvas_runtime import bound
        return bound(json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8")), BASE_URL, COURSE_ID)

    return {
        "course_id": COURSE_ID,
        "base_url": BASE_URL,
        "files": {}
    }


def save_asset_manifest(manifest):
    from canvas_runtime import save_json
    save_json(ASSET_MANIFEST_PATH, manifest)


def guess_content_type(file_path):
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or "application/octet-stream"


def start_upload(file_path, folder_path, folder_id, on_duplicate, canvas_name):
    if folder_id:
        folders = []
        next_url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/folders"
        seen = set()
        while next_url:
            if next_url in seen:
                raise RuntimeError("Repeated folder pagination URL.")
            seen.add(next_url)
            response = requests.get(next_url, headers=HEADERS)
            response.raise_for_status()
            folders.extend(response.json())
            next_url = response.links.get("next", {}).get("url")
        if folder_id not in [f["id"] for f in folders]:
            raise ValueError("Folder does not belong to the configured course.")
        url = f"{BASE_URL}/api/v1/folders/{folder_id}/files"
    else:
        url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files"

    payload = {
        "name": canvas_name or file_path.name,
        "size": file_path.stat().st_size,
        "content_type": guess_content_type(file_path),
        "on_duplicate": on_duplicate,
        "success_include[]": ["preview_url", "usage_rights"]
    }

    if not folder_id:
        payload["parent_folder_path"] = folder_path

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def upload_binary(file_path, upload_info, canvas_name=None):
    from canvas_runtime import upload_binary as transfer
    return transfer(file_path, upload_info, BASE_URL, HEADERS, canvas_name)


def main():
    parser = argparse.ArgumentParser(description="Upload a local file to Canvas Files.")
    parser.add_argument("file_path", help="Local file path to upload")
    parser.add_argument(
        "--folder",
        default="CanvasDaemon",
        help="Canvas Files folder path. Example: CanvasDaemon/activities"
    )
    parser.add_argument(
        "--folder-id",
        type=int,
        help="Canvas Files folder ID. If provided, this is used instead of --folder."
    )
    parser.add_argument(
        "--canvas-name",
        help="Filename to use in Canvas. Defaults to the local file name."
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Rename if a file with the same name exists. Default is overwrite."
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    file_path = Path(args.file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Local file not found: {file_path}")

    manifest = load_asset_manifest()
    on_duplicate = "rename" if args.rename else "overwrite"

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    upload_info = start_upload(
        file_path=file_path,
        folder_path=args.folder,
        folder_id=args.folder_id,
        on_duplicate=on_duplicate,
        canvas_name=args.canvas_name
    )

    uploaded_file = upload_binary(file_path, upload_info, args.canvas_name)

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
        "canvas_folder": args.folder,
        "canvas_folder_id": args.folder_id
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
