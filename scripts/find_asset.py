import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CANVAS_FILES_CSV = ROOT_DIR / "reports" / "files" / "canvas_files.csv"


def normalize(text):
    return (text or "").lower().strip()


def load_assets():
    if not CANVAS_FILES_CSV.exists():
        raise FileNotFoundError(
            "reports/files/canvas_files.csv not found. Run: python scripts/pull_files_metadata.py"
        )

    with CANVAS_FILES_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def snippet_for_asset(row):
    filename = row.get("filename", "")
    url = row.get("url", "")
    category = row.get("category", "")
    content_type = row.get("content_type", "")

    lower_name = filename.lower()

    if category == "image" or content_type.startswith("image/"):
        return f'<img src="{url}" alt="{filename}">'

    if lower_name.endswith(".html"):
        return f'<iframe src="{url}" width="100%" height="650" style="border:0;" title="{filename}"></iframe>'

    if lower_name.endswith(".pdf") or content_type == "application/pdf":
        return f'<a href="{url}" target="_blank" rel="noopener">Open {filename}</a>'

    return f'<a href="{url}" target="_blank" rel="noopener">{filename}</a>'


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/find_asset.py "search text"')
        sys.exit(1)

    search_text = normalize(" ".join(sys.argv[1:]))
    assets = load_assets()

    matches = []

    for row in assets:
        haystack = " ".join([
            row.get("file_id", ""),
            row.get("filename", ""),
            row.get("display_name", ""),
            row.get("category", ""),
            row.get("content_type", ""),
            row.get("url", "")
        ])

        if search_text in normalize(haystack):
            matches.append(row)

    if not matches:
        print(f'No assets found for: "{search_text}"')
        print("\nTry:")
        print('python scripts/find_asset.py "activity"')
        print('python scripts/find_asset.py "png"')
        print('python scripts/find_asset.py "m04"')
        return

    print(f'\nFound {len(matches)} asset match(es) for: "{search_text}"\n')

    for i, row in enumerate(matches, start=1):
        print("=" * 80)
        print(f"{i}. Filename:     {row.get('filename')}")
        print(f"   File ID:      {row.get('file_id')}")
        print(f"   Category:     {row.get('category')}")
        print(f"   Content type: {row.get('content_type')}")
        print(f"   Size:         {row.get('size')}")
        print(f"   Folder ID:    {row.get('folder_id')}")
        print(f"   URL:          {row.get('url')}")
        print()
        print("   Suggested HTML:")
        print(f"   {snippet_for_asset(row)}")
        print()


if __name__ == "__main__":
    main()
