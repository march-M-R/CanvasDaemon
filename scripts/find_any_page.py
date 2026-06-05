import csv
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT_DIR / "manifest.json"
USED_MODULE_PAGES_CSV = ROOT_DIR / "reports" / "used_module_pages.csv"


def normalize(text):
    return (text or "").lower().strip()


def load_manifest_pages():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("manifest.json not found. Run: python scripts/pull_pages.py")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest["pages"]


def load_active_files():
    if not USED_MODULE_PAGES_CSV.exists():
        raise FileNotFoundError(
            "reports/used_module_pages.csv not found.\n"
            "Run: python scripts/course_inventory.py"
        )

    active_files = set()

    with USED_MODULE_PAGES_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            local_file = row.get("local_file")
            if local_file and local_file != "NOT_FOUND_IN_MANIFEST":
                active_files.add(local_file)

    return active_files


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/find_any_page.py "search text"')
        sys.exit(1)

    search_text = normalize(" ".join(sys.argv[1:]))

    pages = load_manifest_pages()
    active_files = load_active_files()

    matches = []

    for filename, info in pages.items():
        title = info.get("title", "")
        canvas_url = info.get("canvas_url", "")
        html_file = info.get("html_file", "")

        haystack = " ".join([
            filename,
            title,
            canvas_url,
            html_file
        ])

        if search_text in normalize(haystack):
            status = "ACTIVE - used in Modules" if filename in active_files else "UNUSED - not in Modules"

            matches.append({
                "filename": filename,
                "title": title,
                "canvas_url": canvas_url,
                "html_file": html_file,
                "status": status
            })

    if not matches:
        print(f'No matches found for: "{search_text}"')
        return

    active_count = sum(1 for match in matches if match["status"].startswith("ACTIVE"))
    unused_count = len(matches) - active_count

    print(f'\nFound {len(matches)} match(es) for: "{search_text}"')
    print(f"Active: {active_count}")
    print(f"Unused: {unused_count}\n")

    for i, match in enumerate(matches, start=1):
        print("=" * 80)
        print(f"{i}. Title:  {match['title']}")
        print(f"   Status: {match['status']}")
        print(f"   URL:    {match['canvas_url']}")
        print(f"   File:   {match['html_file']}")
        print()
        print(f'   Open:   code "{match["html_file"]}"')

        if match["status"].startswith("ACTIVE"):
            print(f'   Dry:    python scripts/push_module_page.py "{match["filename"]}"')
            print(f'   Push:   python scripts/push_module_page.py "{match["filename"]}" --apply')
        else:
            print(f'   Dry:    python scripts/push_page.py "{match["filename"]}"')
            print(f'   Push:   python scripts/push_page.py "{match["filename"]}" --apply')
        print()


if __name__ == "__main__":
    main()