import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT_DIR / "reports" / "audit"
PAGES_DIR = ROOT_DIR / "pages"
MANIFEST_PATH = ROOT_DIR / "manifest.json"
ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
TEMPLATE_DIR = ROOT_DIR / "examples" / "templates"

LOCAL_ASSET_TAGS = [
    ("img", "src"),
    ("iframe", "src"),
    ("script", "src"),
    ("source", "src"),
    ("audio", "src"),
    ("video", "src"),
    ("video", "poster"),
    ("link", "href"),
    ("a", "href"),
]

WRITE_METHODS = ("requests.post", "requests.put", "requests.delete")
SKIP_SCHEMES = {"http", "https", "data", "mailto", "tel", "javascript"}
GENERATED_OR_SECRET_PATHS = [
    ".env",
    ".venv",
    "pages",
    "manifest.json",
    "backups",
    "reports",
    "canvas_files",
    "asset_manifest.json",
    "preview_config.json",
]


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"__error__": str(exc)}


def is_local_reference(value):
    if not value or value.startswith("#"):
        return False
    parsed = urlsplit(value)
    if parsed.scheme.lower() in SKIP_SCHEMES or parsed.netloc:
        return False
    return bool(parsed.path)


def page_files(pages_dir=PAGES_DIR):
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.html"))


def audit_repo_state():
    findings = []
    for rel in GENERATED_OR_SECRET_PATHS:
        path = ROOT_DIR / rel
        if path.exists():
            severity = "warning"
            if rel == ".env":
                severity = "info"
            findings.append({
                "category": "repo_state",
                "severity": severity,
                "file": rel,
                "message": f"Local-only path exists: {rel}. Keep it out of Git.",
            })
    gitignore = ROOT_DIR / ".gitignore"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        for rel in [".env", "pages/", "manifest.json", "backups/", "reports/", "canvas_files/", "asset_manifest.json", "preview_config.json"]:
            pattern = rel.rstrip("/")
            if pattern not in text and rel not in text:
                findings.append({
                    "category": "repo_state",
                    "severity": "warning",
                    "file": ".gitignore",
                    "message": f"Expected ignore rule missing or unclear for {rel}.",
                })
    return findings


def audit_manifests():
    findings = []
    manifest = load_json(MANIFEST_PATH)
    if manifest is None:
        findings.append({"category": "manifest", "severity": "info", "file": "manifest.json", "message": "No page manifest found. Run pull_pages.py for a course workspace."})
    elif "__error__" in manifest:
        findings.append({"category": "manifest", "severity": "error", "file": "manifest.json", "message": f"Invalid JSON: {manifest['__error__']}"})
    else:
        pages = manifest.get("pages", {})
        for filename, info in pages.items():
            html_file = info.get("html_file") or f"pages/{filename}"
            if not (ROOT_DIR / html_file).exists():
                findings.append({"category": "manifest", "severity": "warning", "file": html_file, "message": "Manifest entry points to a missing local page file."})
            if not info.get("body_sha256") and not info.get("last_canvas_update"):
                findings.append({"category": "manifest", "severity": "warning", "file": html_file, "message": "Manifest entry has no conflict baseline; pull before applying updates."})
    assets = load_json(ASSET_MANIFEST_PATH)
    if assets is None:
        findings.append({"category": "manifest", "severity": "info", "file": "asset_manifest.json", "message": "No asset manifest found. Run pull_files_metadata.py after configuring a course."})
    elif "__error__" in assets:
        findings.append({"category": "manifest", "severity": "error", "file": "asset_manifest.json", "message": f"Invalid JSON: {assets['__error__']}"})
    return findings


def audit_pages(paths):
    findings = []
    titles = Counter()
    local_refs = []
    placeholder_patterns = [
        (re.compile(r'href=["\']#["\']', re.I), "Placeholder link href=\"#\" remains."),
        (re.compile(r'title=["\'][^"\']*replace when making a reusable template', re.I), "Template replacement note remains."),
        (re.compile(r'Course-specific destination', re.I), "Course-specific destination placeholder remains."),
    ]
    for path in paths:
        rel = str(path.relative_to(ROOT_DIR))
        text = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(text, "html.parser")
        title = soup.find("title")
        h1 = soup.find("h1")
        page_title = (title.get_text(strip=True) if title else None) or (h1.get_text(strip=True) if h1 else None)
        if page_title:
            titles[page_title.strip().lower()] += 1
        else:
            findings.append({"category": "page", "severity": "warning", "file": rel, "message": "No <title> or <h1> found."})
        for img in soup.find_all("img"):
            if not img.get("alt"):
                findings.append({"category": "accessibility", "severity": "warning", "file": rel, "message": "Image missing alt text."})
        for pattern, message in placeholder_patterns:
            if pattern.search(text):
                findings.append({"category": "placeholder", "severity": "warning", "file": rel, "message": message})
        for tag_name, attr in LOCAL_ASSET_TAGS:
            for tag in soup.find_all(tag_name):
                value = tag.get(attr)
                if not is_local_reference(value):
                    continue
                parsed = urlsplit(value)
                target = (path.parent / parsed.path).resolve()
                try:
                    target.relative_to(ROOT_DIR.resolve())
                except ValueError:
                    findings.append({"category": "asset", "severity": "error", "file": rel, "message": f"Local reference points outside repo: {value}"})
                    continue
                local_refs.append((rel, value, target))
                if not target.exists():
                    findings.append({"category": "asset", "severity": "error", "file": rel, "message": f"Missing local asset reference: {value}"})
    for normalized, count in titles.items():
        if count > 1:
            findings.append({"category": "page", "severity": "info", "file": "pages/", "message": f"Duplicate page title appears {count} times: {normalized}"})
    return findings, local_refs


def audit_script_safety():
    findings = []
    for path in sorted((ROOT_DIR / "scripts").glob("*.py")):
        rel = str(path.relative_to(ROOT_DIR))
        text = path.read_text(encoding="utf-8")
        writes = any(token in text for token in WRITE_METHODS)
        delegates_write = path.name == "push_module_page.py"
        if writes or delegates_write:
            if "add_write_flags(parser)" not in text:
                findings.append({"category": "script_safety", "severity": "error", "file": rel, "message": "Canvas-writing script does not use add_write_flags(parser)."})
            if "authorize(args" not in text and not delegates_write:
                findings.append({"category": "script_safety", "severity": "error", "file": rel, "message": "Canvas-writing script does not call authorize(args, ...)."})
    return findings


def audit_templates():
    findings = []
    expected = [
        TEMPLATE_DIR / "README.md",
        TEMPLATE_DIR / "metadata" / "template-library.json",
        TEMPLATE_DIR / "assets" / "m2_1_1_examples_patterns.png",
    ]
    for path in expected:
        if not path.exists():
            findings.append({"category": "templates", "severity": "warning", "file": str(path.relative_to(ROOT_DIR)), "message": "Expected template library file is missing."})
    pages_dir = TEMPLATE_DIR / "pages"
    if pages_dir.exists():
        html_count = len(list(pages_dir.glob("*.html")))
        if html_count < 10:
            findings.append({"category": "templates", "severity": "warning", "file": str(pages_dir.relative_to(ROOT_DIR)), "message": f"Template page count looks low: {html_count}."})
    else:
        findings.append({"category": "templates", "severity": "warning", "file": "examples/templates/pages", "message": "Template pages folder is missing."})
    return findings


def write_reports(findings, summary, local_refs):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "course_readiness_audit.json"
    csv_path = REPORT_DIR / "course_readiness_findings.csv"
    txt_path = REPORT_DIR / "course_readiness_summary.txt"
    refs_path = REPORT_DIR / "local_asset_references.csv"

    json_path.write_text(json.dumps({"summary": summary, "findings": findings}, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["severity", "category", "file", "message"])
        writer.writeheader()
        writer.writerows(findings)

    with refs_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "reference", "resolved_path", "exists"])
        writer.writeheader()
        for page, value, target in local_refs:
            writer.writerow({"page": page, "reference": value, "resolved_path": str(target), "exists": target.exists()})

    lines = [
        "CanvasDaemon Course Readiness Audit",
        "====================================",
        "",
        f"Pages inspected: {summary['pages_inspected']}",
        f"Local asset references: {summary['local_asset_references']}",
        f"Errors: {summary['errors']}",
        f"Warnings: {summary['warnings']}",
        f"Info: {summary['info']}",
        "",
        "Reports:",
        f"- {json_path}",
        f"- {csv_path}",
        f"- {refs_path}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, refs_path, txt_path


def main():
    parser = argparse.ArgumentParser(description="Run a read-only CanvasDaemon course readiness audit.")
    parser.add_argument("--pages-dir", default=str(PAGES_DIR), help="Directory of local Canvas page HTML files to inspect")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit nonzero when warnings are present")
    args = parser.parse_args()

    pages_dir = Path(args.pages_dir)

    findings = []
    findings.extend(audit_repo_state())
    findings.extend(audit_manifests())
    pages = page_files(pages_dir)
    page_findings, local_refs = audit_pages(pages)
    findings.extend(page_findings)
    findings.extend(audit_script_safety())
    findings.extend(audit_templates())

    counts = Counter(f["severity"] for f in findings)
    summary = {
        "pages_inspected": len(pages),
        "local_asset_references": len(local_refs),
        "errors": counts.get("error", 0),
        "warnings": counts.get("warning", 0),
        "info": counts.get("info", 0),
        "total_findings": len(findings),
    }
    paths = write_reports(findings, summary, local_refs)

    print("CanvasDaemon course readiness audit complete.")
    print(f"Pages inspected: {summary['pages_inspected']}")
    print(f"Local asset references: {summary['local_asset_references']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print("Reports:")
    for path in paths:
        print(f"- {path}")

    if summary["errors"] or (args.fail_on_warning and summary["warnings"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
