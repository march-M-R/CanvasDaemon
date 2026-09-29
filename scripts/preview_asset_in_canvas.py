from canvas_runtime import add_write_flags, authorize
import os
import json
import argparse
import mimetypes
import webbrowser
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
PREVIEW_CONFIG_PATH = ROOT_DIR / "preview_config.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def load_preview_config():
    if not PREVIEW_CONFIG_PATH.exists():
        raise FileNotFoundError(
            "preview_config.json not found.\n"
            "Run: python scripts/setup_preview_environment.py"
        )

    from canvas_runtime import bound
    return bound(json.loads(PREVIEW_CONFIG_PATH.read_text(encoding="utf-8")), BASE_URL, COURSE_ID)


def resolve_local_file(path_text):
    path = Path(path_text)

    if path.exists():
        return path

    path = ROOT_DIR / path_text

    if path.exists():
        return path

    raise FileNotFoundError(f"Local file not found: {path_text}")


def guess_content_type(file_path):
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or "application/octet-stream"


def start_upload(file_path, folder_path):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files"

    payload = {
        "name": file_path.name,
        "size": file_path.stat().st_size,
        "content_type": guess_content_type(file_path),
        "parent_folder_path": folder_path,
        "on_duplicate": "overwrite"
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def upload_binary(file_path, upload_info, canvas_name=None):
    from canvas_runtime import upload_binary as transfer
    return transfer(file_path, upload_info, BASE_URL, HEADERS, canvas_name)


def upload_preview_asset(file_path, folder_path):
    upload_info = start_upload(file_path, folder_path)
    return upload_binary(file_path, upload_info)


def build_canvas_file_url(file_id):
    return f"{BASE_URL}/courses/{COURSE_ID}/files/{file_id}/download"


def build_canvas_api_endpoint(file_id):
    return f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files/{file_id}"


def build_asset_embed_html(uploaded_file, local_file):
    file_id = uploaded_file.get("id")
    from html import escape
    filename = escape(uploaded_file.get("filename") or local_file.name, quote=True)

    content_type = (
        uploaded_file.get("content-type")
        or uploaded_file.get("content_type")
        or guess_content_type(local_file)
    )

    suffix = local_file.suffix.lower()
    canvas_file_url = build_canvas_file_url(file_id)
    api_endpoint = build_canvas_api_endpoint(file_id)

    if suffix in [".html", ".htm"]:
        return f"""
<iframe
  style="display: block; background: #ffffff; border: none;"
  title="{filename}"
  src="{canvas_file_url}"
  width="100%"
  height="700"
  loading="lazy"
  data-api-endpoint="{api_endpoint}"
  data-api-returntype="File">
</iframe>
""".strip()

    if content_type.startswith("image/") or suffix in [
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"
    ]:
        return f"""
<img
  src="{canvas_file_url}"
  alt="{filename}"
  style="display: block; max-width: 100%; height: auto;"
  data-api-endpoint="{api_endpoint}"
  data-api-returntype="File">
""".strip()

    if suffix == ".pdf" or content_type == "application/pdf":
        return f"""
<iframe
  style="display: block; background: #ffffff; border: none;"
  title="{filename}"
  src="{canvas_file_url}"
  width="100%"
  height="700"
  loading="lazy"
  data-api-endpoint="{api_endpoint}"
  data-api-returntype="File">
</iframe>
""".strip()

    return f"""
<a
  href="{canvas_file_url}"
  target="_blank"
  rel="noopener"
  data-api-endpoint="{api_endpoint}"
  data-api-returntype="File">
  Open file: {filename}
</a>
""".strip()


def build_preview_page_body(local_file, uploaded_file):
    return build_asset_embed_html(uploaded_file, local_file)


def update_preview_page(preview_page_url, html_body):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages/{preview_page_url}"

    current = requests.get(url, headers=HEADERS)
    current.raise_for_status()
    if current.json().get("published"):
        raise ValueError("Refusing to overwrite a published preview page.")

    payload = {
        "wiki_page[body]": html_body,
        "wiki_page[published]": "false"
    }

    response = requests.put(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Upload a local asset to Canvas preview assets and preview only the embedded part inside Canvas."
    )

    parser.add_argument(
        "file_path",
        help="Local file path to preview"
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the Canvas preview page"
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    config = load_preview_config()

    preview_page_url = config["preview_page_url"]
    preview_html_url = config["preview_page_html_url"]
    preview_folder = config.get("preview_asset_folder", "CanvasDaemon Preview Assets")

    local_file = resolve_local_file(args.file_path)

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    print(f"Uploading preview asset: {local_file}")
    uploaded_file = upload_preview_asset(local_file, preview_folder)

    preview_body = build_preview_page_body(local_file, uploaded_file)
    updated_page = update_preview_page(preview_page_url, preview_body)

    print()
    print("Canvas asset preview ready.")
    print(f"Preview page: {updated_page.get('title')}")
    print(f"Uploaded file ID: {uploaded_file.get('id')}")
    print(f"Uploaded file URL: {build_canvas_file_url(uploaded_file.get('id'))}")
    print(f"Canvas preview URL: {preview_html_url}")

    if not args.no_open:
        webbrowser.open(preview_html_url)
        print("Opened preview page in browser.")


if __name__ == "__main__":
    main()
