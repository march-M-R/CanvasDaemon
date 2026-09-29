import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]

PAGES_DIR = ROOT_DIR / "pages"
MANIFEST_PATH = ROOT_DIR / "manifest.json"
PANOPTO_MANIFEST_PATH = ROOT_DIR / "panopto_manifest.json"
REPORTS_DIR = ROOT_DIR / "reports"
PANOPTO_CSV = REPORTS_DIR / "panopto_videos.csv"


def load_page_manifest():
    if not MANIFEST_PATH.exists():
        return {}

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest.get("pages", {})


def is_panopto_url(url):
    return "panopto" in (url or "").lower()


def extract_video_id(url):
    """
    Panopto embed URLs often look like:
    .../Panopto/Pages/Embed.aspx?id=VIDEO_ID

    Sometimes the useful ID may be under different params,
    so we check common keys.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    for key in ["id", "sessionId", "sessionid"]:
        if key in query and query[key]:
            return query[key][0]

    match = re.search(r"([a-f0-9-]{20,})", url, re.IGNORECASE)
    if match:
        return match.group(1)

    return url


def extract_panopto_embeds(html):
    soup = BeautifulSoup(html, "html.parser")
    embeds = []

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")

        if is_panopto_url(src):
            embeds.append({
                "type": "iframe",
                "url": src,
                "title": iframe.get("title", ""),
                "width": iframe.get("width", ""),
                "height": iframe.get("height", "")
            })

    for link in soup.find_all("a"):
        href = link.get("href", "")

        if is_panopto_url(href):
            embeds.append({
                "type": "link",
                "url": href,
                "title": link.get_text(strip=True),
                "width": "",
                "height": ""
            })

    return embeds


def main():
    REPORTS_DIR.mkdir(exist_ok=True)

    page_manifest = load_page_manifest()

    videos = {}
    rows = []

    page_files = sorted(PAGES_DIR.glob("*.html"))

    for page_path in page_files:
        filename = page_path.name
        html = page_path.read_text(encoding="utf-8", errors="replace")

        embeds = extract_panopto_embeds(html)

        if not embeds:
            continue

        page_info = page_manifest.get(filename, {})
        page_title = page_info.get("title", "")

        for embed in embeds:
            url = embed["url"]
            video_id = extract_video_id(url)

            if video_id not in videos:
                videos[video_id] = {
                    "video_id": video_id,
                    "embed_url": url,
                    "first_seen_title": embed.get("title", ""),
                    "found_in": []
                }

            videos[video_id]["found_in"].append({
                "page_file": filename,
                "page_title": page_title,
                "embed_type": embed["type"]
            })

            rows.append({
                "video_id": video_id,
                "page_file": filename,
                "page_title": page_title,
                "embed_type": embed["type"],
                "embed_title": embed.get("title", ""),
                "width": embed.get("width", ""),
                "height": embed.get("height", ""),
                "embed_url": url
            })

    panopto_manifest = {
        "videos": videos
    }

    PANOPTO_MANIFEST_PATH.write_text(
        json.dumps(panopto_manifest, indent=2),
        encoding="utf-8"
    )

    with PANOPTO_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "video_id",
                "page_file",
                "page_title",
                "embed_type",
                "embed_title",
                "width",
                "height",
                "embed_url"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Panopto discovery complete.")
    print(f"Pages scanned: {len(page_files)}")
    print(f"Unique Panopto videos found: {len(videos)}")
    print(f"Panopto references found: {len(rows)}")
    print(f"Manifest saved to: {PANOPTO_MANIFEST_PATH}")
    print(f"CSV report saved to: {PANOPTO_CSV}")


if __name__ == "__main__":
    main()
