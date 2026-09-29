from canvas_runtime import add_write_flags, authorize
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from canvas_runtime import load_dotenv
import upload_canvas_file as uploader

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "reports" / "prepared_pages"

ASSET_ATTRIBUTES = [
    ("img", "src"),
    ("iframe", "src"),
    ("script", "src"),
    ("source", "src"),
    ("audio", "src"),
    ("video", "src"),
    ("video", "poster"),
    ("link", "href"),
    ("a", "href"),
]

SKIP_SCHEMES = {"http", "https", "data", "mailto", "tel", "javascript"}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def is_local_reference(value):
    if not value or value.startswith("#"):
        return False
    parsed = urlsplit(value)
    if parsed.scheme.lower() in SKIP_SCHEMES or parsed.netloc:
        return False
    return bool(parsed.path)


def resolve_reference(page_path, value):
    parsed = urlsplit(value)
    local_path = (page_path.parent / parsed.path).resolve()
    try:
        local_path.relative_to(ROOT_DIR.resolve())
    except ValueError:
        raise ValueError(f"Refusing asset outside this checkout: {value}")
    return local_path, parsed


def collect_local_assets(page_path):
    soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")
    references = []
    seen = set()

    for tag_name, attr in ASSET_ATTRIBUTES:
        for tag in soup.find_all(tag_name):
            value = tag.get(attr)
            if not is_local_reference(value):
                continue
            local_path, parsed = resolve_reference(page_path, value)
            key = (str(local_path), tag_name, attr, value)
            if key in seen:
                continue
            seen.add(key)
            references.append({
                "tag": tag_name,
                "attribute": attr,
                "original": value,
                "path": local_path,
                "parsed": parsed,
                "exists": local_path.exists(),
            })

    return references


def rewrite_html(page_path, replacements):
    soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")
    for tag_name, attr in ASSET_ATTRIBUTES:
        for tag in soup.find_all(tag_name):
            value = tag.get(attr)
            if value in replacements:
                tag[attr] = replacements[value]
    return str(soup)


def upload_asset(path, folder, rename):
    on_duplicate = "rename" if rename else "overwrite"
    upload_info = uploader.start_upload(
        file_path=path,
        folder_path=folder,
        folder_id=None,
        on_duplicate=on_duplicate,
        canvas_name=None,
    )
    return uploader.upload_binary(path, upload_info)


def canvas_url_with_suffix(uploaded_file, parsed):
    url = uploaded_file.get("url") or uploaded_file.get("preview_url")
    if not url:
        raise RuntimeError(f"Canvas did not return a usable URL for file ID {uploaded_file.get('id')}")
    target = urlsplit(url)
    return urlunsplit((target.scheme, target.netloc, target.path, parsed.query, parsed.fragment))


def default_output_path(page_path):
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / page_path.name


def main():
    parser = argparse.ArgumentParser(
        description="Find local assets referenced by an HTML page, upload them to Canvas Files, and write a Canvas-linked HTML copy."
    )
    parser.add_argument("page", help="Local HTML page to inspect")
    parser.add_argument(
        "--folder",
        default="CanvasDaemon/page-assets",
        help="Canvas Files folder path for uploaded assets"
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Rename duplicate Canvas files instead of overwriting matching names"
    )
    parser.add_argument(
        "--output",
        help="Where to write the rewritten HTML. Defaults to reports/prepared_pages/<page name>."
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite the original page file after uploading assets"
    )
    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    page_path = Path(args.page)
    if not page_path.exists():
        raise FileNotFoundError(f"Page file not found: {page_path}")
    page_path = page_path.resolve()

    refs = collect_local_assets(page_path)
    missing = [ref for ref in refs if not ref["exists"]]

    print(f"Page: {page_path}")
    print(f"Local asset references found: {len(refs)}")
    if refs:
        for ref in refs:
            status = "OK" if ref["exists"] else "MISSING"
            print(f"- [{status}] {ref['tag']} {ref['attribute']}={ref['original']} -> {ref['path']}")

    if missing:
        raise FileNotFoundError("One or more referenced local assets are missing. Fix the paths before uploading.")

    if not refs:
        print("No local assets need upload or rewriting.")
        return

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    replacements = {}
    uploaded_by_path = {}
    manifest = uploader.load_asset_manifest()

    for ref in refs:
        path = ref["path"]
        if path not in uploaded_by_path:
            uploaded = upload_asset(path, args.folder, args.rename)
            uploaded_by_path[path] = uploaded
            file_id = str(uploaded.get("id"))
            manifest["files"][file_id] = {
                "file_id": uploaded.get("id"),
                "filename": uploaded.get("filename") or path.name,
                "display_name": uploaded.get("display_name"),
                "category": "uploaded_page_asset",
                "content_type": uploaded.get("content-type") or uploaded.get("content_type"),
                "size": uploaded.get("size"),
                "url": uploaded.get("url"),
                "preview_url": uploaded.get("preview_url"),
                "folder_id": uploaded.get("folder_id"),
                "created_at": uploaded.get("created_at"),
                "updated_at": uploaded.get("updated_at"),
                "locked": uploaded.get("locked"),
                "hidden": uploaded.get("hidden"),
                "local_source": str(path),
                "canvas_folder": args.folder,
                "canvas_folder_id": None,
            }
        replacements[ref["original"]] = canvas_url_with_suffix(uploaded_by_path[path], ref["parsed"])

    uploader.save_asset_manifest(manifest)

    rewritten = rewrite_html(page_path, replacements)
    if args.in_place:
        output_path = page_path
    else:
        output_path = Path(args.output).resolve() if args.output else default_output_path(page_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rewritten, encoding="utf-8")

    print("\nPrepared page assets successfully.")
    print(f"Uploaded unique assets: {len(uploaded_by_path)}")
    print(f"Rewritten HTML: {output_path}")
    print("\nNext recommended commands:")
    print(f'python scripts/preview_page_in_canvas.py "{output_path}" --apply --confirm-course {COURSE_ID}')
    print("Then review in Canvas before pushing the production page.")


if __name__ == "__main__":
    main()
