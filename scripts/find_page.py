import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
USED_MODULE_PAGES_CSV = ROOT_DIR / "reports" / "pages" / "used_module_pages.csv"


def normalize(text):
    return (text or "").lower().strip()


def load_rows():
    if not USED_MODULE_PAGES_CSV.exists():
        raise FileNotFoundError(
            "reports/pages/used_module_pages.csv not found.\n"
            "Run: python scripts/course_inventory.py"
        )

    with USED_MODULE_PAGES_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/find_page.py "search text"')
        sys.exit(1)

    search_text = normalize(" ".join(sys.argv[1:]))
    rows = load_rows()

    matches = []

    for row in rows:
        haystack = " ".join(
            [
                row.get("module_name", ""),
                row.get("page_title", ""),
                row.get("canvas_page_url", ""),
                row.get("local_file", ""),
            ]
        )

        if search_text in normalize(haystack):
            matches.append(row)

    if not matches:
        print(f'No matches found for: "{search_text}"')
        print("\nTry a shorter search, like:")
        print('python scripts/find_page.py "overview"')
        print('python scripts/find_page.py "lesson 2"')
        return

    print(f'\nFound {len(matches)} match(es) for: "{search_text}"\n')

    for i, row in enumerate(matches, start=1):
        local_file = row.get("local_file")

        print("=" * 80)
        print(f"{i}. Module: {row.get('module_name')}")
        print(f"   Page:   {row.get('page_title')}")
        print(f"   URL:    {row.get('canvas_page_url')}")
        print(f"   File:   pages/{local_file}")
        print()
        print(f'   Open:   code "pages/{local_file}"')
        print(f'   Dry:    python scripts/push_module_page.py "{local_file}"')
        print(f'   Push:   python scripts/push_module_page.py "{local_file}" --apply')
        print()


if __name__ == "__main__":
    main()