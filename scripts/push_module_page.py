# push_module_page.py

import csv
import sys
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

USED_PAGES_CSV = (
    ROOT_DIR
    / "reports"
    / "pages"
    / "used_module_pages.csv"
)


def find_page(filename):
    with USED_PAGES_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            local_file = row.get("local_file", "")

            if local_file.endswith(filename):
                return row

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Push a page that is actively used in a Canvas module."
    )

    parser.add_argument(
        "filename",
        help="Filename from pages/ directory"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually push to Canvas"
    )

    parser.add_argument("--confirm-course", help="Required with --apply")
    args = parser.parse_args()

    if not USED_PAGES_CSV.exists():
        raise FileNotFoundError(
            "reports/pages/used_module_pages.csv not found.\n"
            "Run:\n"
            "python scripts/course_inventory.py"
        )

    page = find_page(args.filename)

    if not page:
        print(
            f"\nPage not found in active module inventory:\n"
            f"  {args.filename}\n"
        )
        return

    print("\nActive Module Page Found")
    print("=" * 80)
    print(f"Module: {page['module_name']}")
    print(f"Page:   {page['page_title']}")
    print(f"File:   {page['local_file']}")
    print("=" * 80)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "push_page.py"),
        args.filename
    ]

    if args.apply:
        cmd.append("--apply")
        if args.confirm_course:
            cmd.extend(["--confirm-course", args.confirm_course])

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
