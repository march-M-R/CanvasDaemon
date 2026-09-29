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
    parser = argparse.ArgumentParser(description="Add multiple existing pages to modules from a JSON sequence.")
    parser.add_argument("sequence_json", help="JSON with items [{filename,module,indent?}] or pages list.")
    add_write_flags(parser)
    args = parser.parse_args()
    data = json.loads(Path(args.sequence_json).read_text(encoding="utf-8"))
    items = data.get("items") or data.get("pages") or data
    if not isinstance(items, list):
        raise ValueError("sequence_json must be a list or contain items/pages.")
    print(f"Plan: attach {len(items)} page(s) to modules.")
    if not authorize(args, BASE_URL, COURSE_ID):
        return
    for item in items:
        cmd = [sys.executable, str(ROOT_DIR / "scripts" / "add_page_to_module.py"), item["filename"], item["module"]]
        if item.get("indent") is not None:
            cmd += ["--indent", str(item["indent"])]
        cmd += ["--apply", "--confirm-course", str(COURSE_ID)]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
