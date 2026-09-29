from canvas_runtime import add_write_flags, authorize
import argparse
import os

from canvas_runtime import load_dotenv
from canvas_runtime import requests

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

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


def list_modules():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules"
    return canvas_get_all(url, params={"per_page": 100})


def find_exact_module(name):
    target = name.strip().lower()
    for module in list_modules():
        if module.get("name", "").strip().lower() == target:
            return module
    return None


def build_payload(args):
    payload = {
        "module[name]": args.title,
        "module[published]": str(args.published).lower(),
    }

    if args.position is not None:
        payload["module[position]"] = args.position

    if args.unlock_at:
        payload["module[unlock_at]"] = args.unlock_at

    if args.require_sequential_progress:
        payload["module[require_sequential_progress]"] = "true"

    for module_id in args.prerequisite_module_id:
        payload.setdefault("module[prerequisite_module_ids][]", []).append(module_id)

    return payload


def create_module(payload):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules"
    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Create a Canvas module safely.")
    parser.add_argument("title", help="New Canvas module title")
    parser.add_argument("--position", type=int, help="Optional 1-based position in the Canvas module list")
    parser.add_argument("--published", action="store_true", help="Publish the module immediately")
    parser.add_argument("--unlock-at", help="Optional ISO 8601 unlock date/time, such as 2026-10-01T09:00:00-04:00")
    parser.add_argument(
        "--require-sequential-progress",
        action="store_true",
        help="Require students to move through module requirements in order"
    )
    parser.add_argument(
        "--prerequisite-module-id",
        action="append",
        default=[],
        help="Canvas module ID that must be completed first; may be repeated"
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    existing = find_exact_module(args.title)
    if existing:
        print("Module already exists; no new module is needed.")
        print(f"Module: {existing.get('name')}")
        print(f"Module ID: {existing.get('id')}")
        print(f"Position: {existing.get('position')}")
        return

    payload = build_payload(args)

    print("Plan: create Canvas module")
    print(f"Title: {args.title}")
    print(f"Published: {args.published}")
    if args.position is not None:
        print(f"Position: {args.position}")
    if args.unlock_at:
        print(f"Unlock at: {args.unlock_at}")
    if args.require_sequential_progress:
        print("Require sequential progress: True")
    if args.prerequisite_module_id:
        print("Prerequisite module IDs: " + ", ".join(args.prerequisite_module_id))

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    created = create_module(payload)

    print("\nCreated Canvas module successfully.")
    print(f"Module: {created.get('name')}")
    print(f"Module ID: {created.get('id')}")
    print(f"Position: {created.get('position')}")
    print(f"Published: {created.get('published')}")
    print("\nNext recommended commands:")
    print("python scripts/list_module_pages.py")
    print(f'python scripts/add_page_to_module.py "page-filename.html" "{created.get("name")}"')


if __name__ == "__main__":
    main()
