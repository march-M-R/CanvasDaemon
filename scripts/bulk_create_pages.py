from canvas_runtime import add_write_flags, authorize, load_dotenv
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

load_dotenv()
BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
COURSE_ID = os.getenv("COURSE_ID")
ROOT_DIR = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Create multiple Canvas pages from a JSON manifest by delegating to create_page.py.")
    parser.add_argument("pages_json", help="JSON list or object with pages: [{title, body_file, published?}]")
    add_write_flags(parser)
    args = parser.parse_args()
    data = json.loads(Path(args.pages_json).read_text(encoding="utf-8"))
    pages = data.get("pages", data) if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError("pages_json must be a list or contain a pages list.")
    print(f"Plan: create {len(pages)} Canvas page(s).")
    if not authorize(args, BASE_URL, COURSE_ID):
        return
    for page in pages:
        cmd = [sys.executable, str(ROOT_DIR / "scripts" / "create_page.py"), page["title"]]
        if page.get("body_file"):
            cmd += ["--body-file", page["body_file"]]
        if page.get("published"):
            cmd.append("--published")
        cmd += ["--apply", "--confirm-course", str(COURSE_ID)]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
