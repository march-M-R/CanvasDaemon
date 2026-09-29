from canvas_runtime import authorize
import os
import csv
import argparse
from pathlib import Path
from datetime import datetime

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
DISCUSSION_REPORTS_DIR = ROOT_DIR / "reports" / "discussions"
DISCUSSIONS_CSV = DISCUSSION_REPORTS_DIR / "created_discussions.csv"

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


def find_module_by_name(module_name):
    modules = list_modules()
    matches = [
        module for module in modules
        if module_name.lower() in module["name"].lower()
    ]

    if not matches:
        raise ValueError(f'No module found matching: "{module_name}"')

    if len(matches) > 1:
        print("\nMultiple modules matched. Be more specific:\n")
        for module in matches:
            print(f'- {module["name"]}')
        raise SystemExit(1)

    return matches[0]


def load_message(args):
    if args.message_file:
        message_path = Path(args.message_file)
        if not message_path.exists():
            raise FileNotFoundError(f"Message file not found: {message_path}")
        return message_path.read_text(encoding="utf-8")

    if args.message:
        return args.message

    return f"<p>{args.title}</p>"


def create_discussion_topic(
    title,
    message,
    published=False,
    discussion_type="threaded",
    require_initial_post=False
):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/discussion_topics"

    payload = {
        "title": title,
        "message": message,
        "published": str(published).lower(),
        "discussion_type": discussion_type,
        "require_initial_post": str(require_initial_post).lower()
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def add_discussion_to_module(module_id, discussion_id, title, indent=0):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules/{module_id}/items"

    payload = {
        "module_item[type]": "Discussion",
        "module_item[title]": title,
        "module_item[content_id]": discussion_id,
        "module_item[indent]": indent
    }

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def append_discussion_report(discussion, module, module_item, source_message_file):
    DISCUSSION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = DISCUSSIONS_CSV.exists()

    with DISCUSSIONS_CSV.open("a", newline="", encoding="utf-8") as f:
        fieldnames = [
            "created_at",
            "discussion_id",
            "title",
            "published",
            "html_url",
            "module_id",
            "module_name",
            "module_item_id",
            "module_item_position",
            "source_message_file"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "discussion_id": discussion.get("id"),
            "title": discussion.get("title"),
            "published": discussion.get("published"),
            "html_url": discussion.get("html_url"),
            "module_id": module.get("id") if module else "",
            "module_name": module.get("name") if module else "",
            "module_item_id": module_item.get("id") if module_item else "",
            "module_item_position": module_item.get("position") if module_item else "",
            "source_message_file": source_message_file or ""
        })


def print_plan(args, module, message):
    print("\nPlanned discussion:")
    print("=" * 80)
    print(f"Title:                {args.title}")
    print(f"Module:               {module['name'] if module else '(not adding to module)'}")
    print(f"Published:            {args.published}")
    print(f"Discussion type:      {args.discussion_type}")
    print(f"Require initial post: {args.require_initial_post}")
    print(f"Indent:               {args.indent}")
    print(f"Message length:       {len(message)} characters")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Create a Canvas discussion topic and optionally add it to a module."
    )
    parser.add_argument("title", help="Discussion title")
    parser.add_argument(
        "--module",
        help="Module name or partial module name to add the discussion to"
    )
    parser.add_argument(
        "--message",
        help="Discussion body HTML. For longer content, prefer --message-file."
    )
    parser.add_argument(
        "--message-file",
        help="Local HTML file to use as the discussion body"
    )
    parser.add_argument(
        "--published",
        action="store_true",
        help="Publish the discussion immediately"
    )
    parser.add_argument(
        "--discussion-type",
        choices=["threaded", "side_comment"],
        default="threaded",
        help="Canvas discussion type"
    )
    parser.add_argument(
        "--require-initial-post",
        action="store_true",
        help="Students must post before seeing replies"
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=0,
        help="Module item indent level"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the discussion in Canvas. Without this, dry-run only."
    )

    parser.add_argument("--confirm-course", help="Required with --apply; must equal COURSE_ID")
    args = parser.parse_args()
    check_env()
    if args.apply:
        authorize(args, BASE_URL, COURSE_ID)

    if args.message and args.message_file:
        raise ValueError("Use either --message or --message-file, not both.")

    message = load_message(args)
    module = find_module_by_name(args.module) if args.module else None

    print_plan(args, module, message)

    if not args.apply:
        print("\nDRY RUN ONLY. Nothing was created.")
        print("To create for real, add --apply:")
        example = f'python scripts/create_discussion.py "{args.title}"'
        if args.module:
            example += f' --module "{args.module}"'
        if args.message_file:
            example += f' --message-file "{args.message_file}"'
        elif args.message:
            example += f' --message "{args.message}"'
        if args.published:
            example += " --published"
        if args.require_initial_post:
            example += " --require-initial-post"
        if args.discussion_type != "threaded":
            example += f" --discussion-type {args.discussion_type}"
        if args.indent:
            example += f" --indent {args.indent}"
        print(example + f" --apply --confirm-course {COURSE_ID}")
        return

    discussion = create_discussion_topic(
        title=args.title,
        message=message,
        published=args.published,
        discussion_type=args.discussion_type,
        require_initial_post=args.require_initial_post
    )

    from canvas_runtime import save_json
    save_json(DISCUSSION_REPORTS_DIR / f"created-{discussion['id']}.json", discussion)

    module_item = None
    if module:
        module_item = add_discussion_to_module(
            module_id=module["id"],
            discussion_id=discussion["id"],
            title=discussion["title"],
            indent=args.indent
        )

    append_discussion_report(
        discussion=discussion,
        module=module,
        module_item=module_item,
        source_message_file=args.message_file
    )

    print("\nDiscussion created successfully.")
    print(f"Title: {discussion.get('title')}")
    print(f"Discussion ID: {discussion.get('id')}")
    print(f"Published: {discussion.get('published')}")
    print(f"URL: {discussion.get('html_url')}")

    if module_item:
        print("\nAdded to module successfully.")
        print(f"Module: {module['name']}")
        print(f"Module item title: {module_item.get('title')}")
        print(f"Module item position: {module_item.get('position')}")

    print(f"\nReport updated: {DISCUSSIONS_CSV}")


if __name__ == "__main__":
    main()
