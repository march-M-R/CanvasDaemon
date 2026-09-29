from canvas_runtime import add_write_flags, authorize, load_dotenv, requests
import argparse
import os
from pathlib import Path

load_dotenv()
BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)

def create_assignment(args, description):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments"
    payload = {
        "assignment[name]": args.title,
        "assignment[description]": description,
        "assignment[published]": str(args.published).lower(),
        "assignment[points_possible]": args.points,
        "assignment[submission_types][]": args.submission_type,
    }
    if args.due_at:
        payload["assignment[due_at]"] = args.due_at
    if args.allowed_extensions:
        for ext in args.allowed_extensions.split(","):
            payload.setdefault("assignment[allowed_extensions][]", []).append(ext.strip().lstrip("."))
    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Create a Canvas assignment safely.")
    parser.add_argument("title")
    parser.add_argument("--description-file")
    parser.add_argument("--points", default="0")
    parser.add_argument("--submission-type", default="online_text_entry", choices=["online_text_entry", "online_url", "online_upload", "none", "external_tool"])
    parser.add_argument("--allowed-extensions", help="Comma-separated extensions for online_upload")
    parser.add_argument("--due-at", help="ISO 8601 due date/time")
    parser.add_argument("--published", action="store_true")
    add_write_flags(parser)
    args = parser.parse_args()
    check_env()
    description = Path(args.description_file).read_text(encoding="utf-8") if args.description_file else f"<p>{args.title}</p>"
    print(f"Plan: create assignment {args.title!r} worth {args.points} point(s).")
    if not authorize(args, BASE_URL, COURSE_ID):
        return
    assignment = create_assignment(args, description)
    print("Created assignment successfully.")
    print(f"ID: {assignment.get('id')}")
    print(f"URL: {assignment.get('html_url')}")

if __name__ == "__main__":
    main()
