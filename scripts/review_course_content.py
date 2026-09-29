import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT_DIR / "pages"
REPORT_DIR = ROOT_DIR / "reports" / "course_review"

LOCAL_REF_TAGS = [
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

SKIP_SCHEMES = {"http", "https", "data", "mailto", "tel", "javascript"}

INTERNAL_NOTE_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bDRAFT\b",
    r"\binternal note\b",
    r"\binstructor note\b",
    r"\bfor review only\b",
    r"\bplaceholder\b",
    r"\breplace this\b",
    r"\breplace when making a reusable template\b",
    r"\bcourse-specific destination\b",
    r"\blorem ipsum\b",
]

MOJIBAKE_PATTERNS = ["Ã", "Â", "â€™", "â€œ", "â€\u009d", "â€“", "â€”", "�"]

COURSE_SPECIFIC_PATTERNS = [
    r"Module\s+\d+",
    r"Phase\s+\d+",
    r"Panopto",
    r"Colab",
    r"Gemini",
]

ACCURACY_REVIEW_ITEMS = [
    ("learning_objectives", "Learning objectives/outcomes match the module and page purpose."),
    ("concept_accuracy", "Definitions, explanations, examples, and analogies are technically accurate."),
    ("ai_tool_behavior", "Descriptions of AI tools, models, limitations, hallucinations, privacy, or bias are current and accurate."),
    ("instructions_match_activity", "Student instructions match the embedded activity, notebook, quiz, discussion, or assignment students actually see."),
    ("answers_and_feedback", "Quiz answers, feedback, scoring language, and review explanations are correct."),
    ("links_and_videos_content", "Linked videos, Panopto embeds, external resources, and downloadable files match the lesson content."),
    ("student_level", "Language, examples, and cognitive load fit high-school learners."),
    ("course_sequence", "Prerequisites, module numbers, next steps, and completion claims match the actual course sequence."),
    ("access_and_policy", "Access requirements, tool policies, academic integrity guidance, and privacy notes are accurate for the target course."),
    ("human_final_review", "A human reviewer has previewed this page in Canvas and approved it for students."),
]

ACCURACY_TRIGGER_PATTERNS = [
    (re.compile(r"\b(correct answer|answer:|feedback|points?|score|mastery|quiz)\b", re.I), "assessment or answer language needs accuracy review"),
    (re.compile(r"\b(should|must|required|submit|due|complete|completion|grade|graded)\b", re.I), "requirement or completion language needs course-policy review"),
    (re.compile(r"\b(LLM|large language model|AI|machine learning|model|training data|hallucination|bias|privacy)\b", re.I), "AI concept language needs technical accuracy review"),
    (re.compile(r"\b(Panopto|Colab|Gemini|Canvas|Google Drive|notebook)\b", re.I), "tool or platform instruction needs live-access review"),
]


def is_local_reference(value):
    if not value or value.startswith("#"):
        return False
    parsed = urlsplit(value)
    if parsed.scheme.lower() in SKIP_SCHEMES or parsed.netloc:
        return False
    return bool(parsed.path)


def line_for_offset(text, offset):
    return text.count("\n", 0, offset) + 1


def add(findings, severity, category, file, message, snippet="", line=""):
    findings.append({
        "severity": severity,
        "category": category,
        "file": file,
        "line": line,
        "message": message,
        "snippet": " ".join(snippet.split())[:220],
    })


def page_files(pages_dir):
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.html"))


def text_content(soup):
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def audit_page(path, root):
    findings = []
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    visible_text = text_content(BeautifulSoup(raw, "html.parser"))

    title = soup.find("title")
    h1s = soup.find_all("h1")
    if not title and not h1s:
        add(findings, "warning", "structure", rel, "Page has no <title> or <h1>.")
    if len(h1s) > 1:
        add(findings, "info", "structure", rel, f"Page has {len(h1s)} <h1> elements; verify heading hierarchy.")

    words = re.findall(r"[A-Za-z0-9']+", visible_text)
    if len(words) < 40:
        add(findings, "warning", "student_readiness", rel, f"Page has very little visible text ({len(words)} words).")

    for pattern in INTERNAL_NOTE_PATTERNS:
        for match in re.finditer(pattern, raw, flags=re.I):
            add(findings, "warning", "internal_notes", rel, f"Possible internal note or placeholder: {match.group(0)}", raw[max(0, match.start()-80):match.end()+80], line_for_offset(raw, match.start()))

    for token in MOJIBAKE_PATTERNS:
        offset = raw.find(token)
        if offset >= 0:
            add(findings, "error", "encoding", rel, f"Possible mojibake or replacement character: {token}", raw[max(0, offset-80):offset+80], line_for_offset(raw, offset))

    for link in soup.find_all("a"):
        href = link.get("href", "")
        label = link.get_text(" ", strip=True)
        if href.strip() == "#":
            add(findings, "warning", "links", rel, "Placeholder link href=\"#\" remains.", str(link)[:220])
        if not href.strip():
            add(findings, "warning", "links", rel, "Link is missing href.", str(link)[:220])
        if href.startswith("http://"):
            add(findings, "warning", "links", rel, "Link uses http instead of https.", href)
        if not label and not link.find("img"):
            add(findings, "warning", "accessibility", rel, "Text link has no visible label.", str(link)[:220])
        if link.get("target") == "_blank" and "noopener" not in (link.get("rel") or []):
            add(findings, "info", "links", rel, "target=_blank link should include rel=\"noopener\".", str(link)[:220])

    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt")
        if alt is None or not alt.strip():
            add(findings, "warning", "accessibility", rel, "Image missing meaningful alt text.", str(img)[:220])
        if src.startswith("http://"):
            add(findings, "warning", "assets", rel, "Image uses http instead of https.", src)
        style = img.get("style", "")
        width = img.get("width", "")
        if re.search(r"width\s*:\s*\d{4,}px", style) or (str(width).isdigit() and int(width) > 1200):
            add(findings, "info", "mobile_layout", rel, "Image may be too wide for mobile; verify responsive sizing.", str(img)[:220])

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if not iframe.get("title"):
            add(findings, "warning", "accessibility", rel, "Iframe missing title.", str(iframe)[:220])
        if src.startswith("http://"):
            add(findings, "warning", "embeds", rel, "Iframe uses http instead of https.", src)
        height = iframe.get("height")
        style = iframe.get("style", "")
        if not height and "height" not in style.lower():
            add(findings, "info", "embeds", rel, "Iframe has no explicit height; Canvas preview may collapse or crop it.", str(iframe)[:220])
        if "panopto" in src.lower():
            add(findings, "info", "video", rel, "Panopto embed found; verify it belongs to the target course and student access works.", src)

    for table in soup.find_all("table"):
        style = table.get("style", "")
        width = table.get("width", "")
        if re.search(r"width\s*:\s*\d{4,}px", style) or (str(width).isdigit() and int(width) > 1000):
            add(findings, "info", "mobile_layout", rel, "Wide fixed-width table may overflow on mobile.", str(table)[:220])

    for tag_name, attr in LOCAL_REF_TAGS:
        for tag in soup.find_all(tag_name):
            value = tag.get(attr)
            if not is_local_reference(value):
                continue
            parsed = urlsplit(value)
            target = (path.parent / parsed.path).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                add(findings, "error", "assets", rel, f"Local reference points outside repo: {value}", str(tag)[:220])
                continue
            if not target.exists():
                add(findings, "error", "assets", rel, f"Missing local referenced file: {value}", str(tag)[:220])
            else:
                add(findings, "info", "assets", rel, f"Local asset reference should be uploaded to Canvas Files before production push: {value}", str(tag)[:220])

    # Long em dash chains and typographic artifacts were common manual review targets.
    if raw.count("—") > 12:
        add(findings, "info", "style", rel, f"Page contains many em dashes ({raw.count('—')}); review tone and readability.")

    for pattern in COURSE_SPECIFIC_PATTERNS:
        if re.search(pattern, visible_text, re.I):
            # Useful as an inventory marker, not an error.
            add(findings, "info", "course_specific", rel, f"Course-specific term found; verify it is intended for the target course: {pattern}")

    return findings


def accuracy_review_rows(paths, root):
    rows = []
    for path in paths:
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        raw = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        visible_text = text_content(BeautifulSoup(raw, "html.parser"))
        heading = ""
        h1 = soup.find("h1")
        title = soup.find("title")
        if h1:
            heading = h1.get_text(" ", strip=True)
        elif title:
            heading = title.get_text(" ", strip=True)
        triggers = [label for pattern, label in ACCURACY_TRIGGER_PATTERNS if pattern.search(visible_text)]
        if not triggers:
            triggers = ["general page accuracy review"]
        for key, prompt in ACCURACY_REVIEW_ITEMS:
            rows.append({
                "file": rel,
                "page_title": heading,
                "review_item": key,
                "review_prompt": prompt,
                "suggested_focus": "; ".join(triggers),
                "status": "needs human review",
                "reviewer": "",
                "notes": "",
            })
    return rows


def summarize_by_page(findings):
    rows = defaultdict(lambda: Counter())
    for item in findings:
        rows[item["file"]][item["severity"]] += 1
    return [
        {"file": file, "errors": counts["error"], "warnings": counts["warning"], "info": counts["info"], "total": sum(counts.values())}
        for file, counts in sorted(rows.items())
    ]


def write_reports(findings, pages_inspected, accuracy_rows=None):
    accuracy_rows = accuracy_rows or []
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    findings_csv = REPORT_DIR / "course_content_findings.csv"
    findings_json = REPORT_DIR / "course_content_findings.json"
    page_summary_csv = REPORT_DIR / "course_content_page_summary.csv"
    summary_md = REPORT_DIR / "course_content_review_summary.md"
    accuracy_csv = REPORT_DIR / "content_accuracy_checklist.csv"
    accuracy_md = REPORT_DIR / "content_accuracy_checklist.md"

    with findings_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["severity", "category", "file", "line", "message", "snippet"])
        writer.writeheader()
        writer.writerows(findings)

    counts = Counter(item["severity"] for item in findings)
    payload = {
        "summary": {
            "pages_inspected": pages_inspected,
            "errors": counts["error"],
            "warnings": counts["warning"],
            "info": counts["info"],
            "total_findings": len(findings),
        },
        "findings": findings,
    }
    findings_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with accuracy_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "page_title", "review_item", "review_prompt", "suggested_focus", "status", "reviewer", "notes"])
        writer.writeheader()
        writer.writerows(accuracy_rows)

    accuracy_lines = [
        "# Content Accuracy Checklist",
        "",
        "Coding helper instruction: use this checklist to identify what needs human review. You may gather evidence, point to pages, and suggest edits, but leave `status` as `needs human review` unless a human reviewer approves the item.",
        "",
        "This checklist is intentionally human-reviewed. The script can flag likely review areas, but it cannot prove technical correctness, course alignment, policy accuracy, or whether an answer key is right.",
        "",
        "| File | Page Title | Review Item | Prompt | Suggested Focus | Status | Reviewer | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in accuracy_rows:
        accuracy_lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "/") for col in ["file", "page_title", "review_item", "review_prompt", "suggested_focus", "status", "reviewer", "notes"]) + " |")
    accuracy_md.write_text("\n".join(accuracy_lines) + "\n", encoding="utf-8")

    page_rows = summarize_by_page(findings)
    with page_summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "errors", "warnings", "info", "total"])
        writer.writeheader()
        writer.writerows(page_rows)

    lines = [
        "# Course Content Review",
        "",
        "Coding helper instruction: fix or report automated findings from this review. Do not mark content-accuracy checklist items complete unless a human reviewer has actually approved them.",
        "",
        f"Pages inspected: {pages_inspected}",
        f"Errors: {counts['error']}",
        f"Warnings: {counts['warning']}",
        f"Info: {counts['info']}",
        "",
        "## What this review checks",
        "",
        "- internal notes, placeholders, TODO/FIXME/DRAFT text",
        "- mojibake and replacement characters",
        "- placeholder, empty, or insecure links",
        "- missing image alt text and missing iframe titles",
        "- local images, activities, scripts, PDFs, or iframes that still need Canvas upload/linking",
        "- missing local asset files",
        "- fixed-width layout risks for mobile review",
        "- Panopto/video embeds that need student-access checks",
        "- course-specific terms that should be verified when adapting to another course",
        "- a human content-accuracy checklist for objectives, concepts, AI/tool claims, activity instructions, answer keys, links/videos, level, sequencing, policy, and final Canvas approval",
        "",
        "## Highest priority findings",
        "",
        "| Severity | Category | File | Line | Message |",
        "|---|---|---|---|---|",
    ]
    for item in findings[:50]:
        if item["severity"] in {"error", "warning"}:
            lines.append(f"| {item['severity']} | {item['category']} | {item['file']} | {item['line']} | {item['message'].replace('|', '/')} |")
    if not any(item["severity"] in {"error", "warning"} for item in findings):
        lines.append("| pass | review |  |  | No errors or warnings found. |")
    lines.extend([
        "",
        "## Reports",
        "",
        f"- `{findings_csv.relative_to(ROOT_DIR)}`",
        f"- `{findings_json.relative_to(ROOT_DIR)}`",
        f"- `{page_summary_csv.relative_to(ROOT_DIR)}`",
        f"- `{accuracy_csv.relative_to(ROOT_DIR)}`",
        f"- `{accuracy_md.relative_to(ROOT_DIR)}`",
    ])
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_md, findings_csv, findings_json, page_summary_csv, accuracy_csv, accuracy_md, payload["summary"]


def main():
    parser = argparse.ArgumentParser(description="Run a student-facing course content review over pulled Canvas page HTML.")
    parser.add_argument("--pages-dir", default=str(PAGES_DIR), help="Directory containing pulled Canvas page HTML files")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit nonzero when warnings are present")
    args = parser.parse_args()

    pages_dir = Path(args.pages_dir)
    pages = page_files(pages_dir)
    findings = []
    for page in pages:
        findings.extend(audit_page(page.resolve(), ROOT_DIR))

    accuracy_rows = accuracy_review_rows([page.resolve() for page in pages], ROOT_DIR)
    reports = write_reports(findings, len(pages), accuracy_rows)
    summary = reports[-1]
    print("Course content review complete.")
    print(f"Pages inspected: {summary['pages_inspected']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print("Coding helper instruction: fix or report automated findings; leave content-accuracy checklist items for human approval unless a human reviewer has approved them.")
    print("Reports:")
    for path in reports[:-1]:
        print(f"- {path}")

    if summary["errors"] or (args.fail_on_warning and summary["warnings"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
