import argparse
import csv
import json
import subprocess
from collections import Counter
from pathlib import Path

import audit_course_readiness as readiness

ROOT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT_DIR / "reports" / "review"

REQUIRED_DOCS = [
    "README.md",
    "CHANGELOG.md",
    "docs/SETUP.md",
    "docs/SETUP.html",
    "docs/HANDBOOK.md",
    "docs/HANDBOOK.html",
    "docs/AI_HELPER_GUIDE.md",
    "docs/AI_HELPER_GUIDE.html",
    "docs/PROCESS_GUIDE.md",
    "docs/PROCESS_GUIDE.html",
    "docs/V1_MAINTENANCE.md",
]

AI_HELPER_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    ".cursor/rules/canvasdaemon.mdc",
]

REQUIRED_SCRIPTS = [
    "scripts/test_canvas.py",
    "scripts/pull_pages.py",
    "scripts/push_page.py",
    "scripts/push_module_page.py",
    "scripts/create_module.py",
    "scripts/create_page.py",
    "scripts/add_page_to_module.py",
    "scripts/prepare_page_assets.py",
    "scripts/upload_canvas_file.py",
    "scripts/preview_page_in_canvas.py",
    "scripts/preview_asset_in_canvas.py",
    "scripts/setup_preview_environment.py",
    "scripts/course_inventory.py",
    "scripts/audit_course_readiness.py",
    "scripts/create_discussion.py",
    "scripts/create_assignment.py",
    "scripts/create_classic_quiz.py",
    "scripts/sync_classic_quiz.py",
    "scripts/validate_course_plan.py",
    "scripts/scaffold_course.py",
    "scripts/build_module_from_template.py",
    "scripts/bulk_create_pages.py",
    "scripts/bulk_add_pages_to_module.py",
    "scripts/replace_course_placeholders.py",
    "scripts/generate_module_checklist.py",
    "scripts/audit_canvas_live_course.py",
    "scripts/export_course_package.py",
]

FORBIDDEN_TRACKED_PATHS = {
    ".env",
    "manifest.json",
    "asset_manifest.json",
    "preview_config.json",
}

FORBIDDEN_TRACKED_PREFIXES = [
    "pages/",
    "backups/",
    "reports/",
    "canvas_files/",
    ".venv/",
]

EXPECTED_TEMPLATE_KEYS = {
    "course-welcome",
    "course-roadmap",
    "course-guide",
    "quick-concept",
    "tool-setup",
    "opening-discussion",
    "answer-review",
    "module-overview",
    "main-lesson",
    "guided-activity",
    "module-summary",
    "progress-checklist",
}


def result(check, status, message, file=""):
    return {"check": check, "status": status, "file": file, "message": message}


def run_git(root, args, timeout=30):
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if completed.returncode != 0:
        return None, completed.stderr.strip() or completed.stdout.strip()
    return completed.stdout, ""


def check_required_files(root, paths, check_name):
    rows = []
    for rel in paths:
        path = root / rel
        if path.exists():
            rows.append(result(check_name, "pass", "Required file exists.", rel))
        else:
            rows.append(result(check_name, "fail", "Required file is missing.", rel))
    return rows


def check_git_clean_and_tracked(root, include_history=False):
    rows = []
    status, err = run_git(root, ["status", "--short", "--branch"])
    if status is None:
        rows.append(result("git", "warn", f"Could not read git status: {err}"))
    else:
        changed = [line for line in status.splitlines() if line and not line.startswith("##")]
        if changed:
            rows.append(result("git", "warn", f"Working tree has {len(changed)} changed/untracked file(s). Review before sharing."))
        else:
            rows.append(result("git", "pass", "Working tree is clean."))

    tracked, err = run_git(root, ["ls-files"])
    if tracked is None:
        rows.append(result("git_tracked_files", "warn", f"Could not list tracked files: {err}"))
        return rows

    bad = []
    for rel in tracked.splitlines():
        if rel in FORBIDDEN_TRACKED_PATHS or any(rel.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES):
            bad.append(rel)
    if bad:
        rows.append(result("git_tracked_files", "fail", "Generated or secret files are tracked: " + ", ".join(bad[:20])))
    else:
        rows.append(result("git_tracked_files", "pass", "No forbidden generated/secret paths are tracked."))

    if include_history:
        history, err = run_git(root, ["log", "--all", "--name-only", "--pretty=format:"], timeout=60)
        if history is None:
            rows.append(result("git_history", "warn", f"Could not scan git history: {err}"))
        else:
            env_hits = [line for line in history.splitlines() if line == ".env" or line.endswith("/.env")]
            if env_hits:
                rows.append(result("git_history", "fail", ".env appears in local git history."))
            else:
                rows.append(result("git_history", "pass", ".env was not found in local git history."))
    return rows


def check_template_library(root):
    rows = []
    metadata_path = root / "examples" / "templates" / "metadata" / "template-library.json"
    if not metadata_path.exists():
        return [result("templates", "fail", "Template metadata is missing.", str(metadata_path.relative_to(root)))]
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [result("templates", "fail", f"Template metadata is invalid JSON: {exc}", str(metadata_path.relative_to(root)))]

    templates = metadata.get("templates", [])
    keys = {item.get("key") for item in templates}
    approved_count = metadata.get("approved_count")
    if approved_count == len(templates) == 12:
        rows.append(result("templates", "pass", "Template library has 12 approved examples."))
    else:
        rows.append(result("templates", "fail", f"Expected 12 approved templates; metadata says {approved_count}, list has {len(templates)}."))

    missing_keys = sorted(EXPECTED_TEMPLATE_KEYS - keys)
    extra_keys = sorted(keys - EXPECTED_TEMPLATE_KEYS)
    if missing_keys or extra_keys:
        rows.append(result("templates", "fail", f"Template keys differ. Missing={missing_keys}; extra={extra_keys}"))
    else:
        rows.append(result("templates", "pass", "Expected template types are present."))

    style_ref = metadata.get("image_style_reference", {}).get("reference_copy")
    if style_ref and (root / "examples" / "templates" / style_ref).exists():
        rows.append(result("templates", "pass", "High-school image style reference exists.", f"examples/templates/{style_ref}"))
    else:
        rows.append(result("templates", "fail", "High-school image style reference is missing.", f"examples/templates/{style_ref or ''}"))

    for item in templates:
        ref = item.get("reference_page")
        if not ref or not (root / "examples" / "templates" / ref).exists():
            rows.append(result("templates", "fail", "Template reference page is missing.", f"examples/templates/{ref or ''}"))
        for dep in item.get("dependencies", []):
            copy = dep.get("review_copy")
            if copy and not (root / "examples" / "templates" / copy).exists():
                rows.append(result("templates", "fail", "Template dependency copy is missing.", f"examples/templates/{copy}"))
    if not any(row["status"] == "fail" and row["check"] == "templates" for row in rows):
        rows.append(result("templates", "pass", "Template pages and dependency copies are present."))
    return rows


def check_readme_links(root):
    rows = []
    readme = root / "README.md"
    if not readme.exists():
        return [result("readme_links", "fail", "README is missing.", "README.md")]
    text = readme.read_text(encoding="utf-8")
    expected = [
        "docs/SETUP.md",
        "docs/SETUP.html",
        "docs/HANDBOOK.md",
        "docs/HANDBOOK.html",
        "docs/AI_HELPER_GUIDE.md",
        "docs/AI_HELPER_GUIDE.html",
        "docs/PROCESS_GUIDE.md",
        "docs/PROCESS_GUIDE.html",
    ]
    missing = [rel for rel in expected if rel not in text]
    if missing:
        rows.append(result("readme_links", "fail", "README is missing documentation links: " + ", ".join(missing), "README.md"))
    else:
        rows.append(result("readme_links", "pass", "README links to setup, handbook, AI-helper, and process docs.", "README.md"))
    return rows


def check_script_safety(root):
    original = readiness.ROOT_DIR
    try:
        readiness.ROOT_DIR = root
        findings = readiness.audit_script_safety()
    finally:
        readiness.ROOT_DIR = original
    if not findings:
        return [result("write_safety", "pass", "Canvas-writing scripts use the shared write confirmation gate.")]
    return [result("write_safety", "fail", f["message"], f["file"]) for f in findings]


def run_local_audit(root):
    original_root = readiness.ROOT_DIR
    original_report = readiness.REPORT_DIR
    try:
        readiness.ROOT_DIR = root
        readiness.REPORT_DIR = root / "reports" / "review" / "course_readiness"
        findings = []
        findings.extend(readiness.audit_repo_state())
        findings.extend(readiness.audit_manifests())
        pages = readiness.page_files(root / "pages")
        page_findings, local_refs = readiness.audit_pages(pages)
        findings.extend(page_findings)
        findings.extend(readiness.audit_script_safety())
        findings.extend(readiness.audit_templates())
        counts = Counter(f["severity"] for f in findings)
        summary = {
            "pages_inspected": len(pages),
            "local_asset_references": len(local_refs),
            "errors": counts.get("error", 0),
            "warnings": counts.get("warning", 0),
            "info": counts.get("info", 0),
            "total_findings": len(findings),
        }
        readiness.write_reports(findings, summary, local_refs)
    finally:
        readiness.ROOT_DIR = original_root
        readiness.REPORT_DIR = original_report
    rows = [result("course_readiness_audit", "pass" if summary["errors"] == 0 else "fail", f"Audit finished: {summary['errors']} errors, {summary['warnings']} warnings, {summary['info']} info.")]
    return rows, summary


def run_tests(root):
    completed = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    status = "pass" if completed.returncode == 0 else "fail"
    message = "Offline regression tests passed." if completed.returncode == 0 else "Offline regression tests failed."
    return result("tests", status, message), completed.stdout


def write_review_reports(root, rows, audit_summary, test_output=None):
    review_dir = root / "reports" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    json_path = review_dir / "toolkit_review.json"
    csv_path = review_dir / "toolkit_review_findings.csv"
    md_path = review_dir / "toolkit_review_summary.md"
    test_path = review_dir / "unittest_output.txt"

    counts = Counter(row["status"] for row in rows)
    payload = {"summary": dict(counts), "course_readiness_audit": audit_summary, "findings": rows}
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["status", "check", "file", "message"])
        writer.writeheader()
        writer.writerows(rows)

    if test_output is not None:
        test_path.write_text(test_output, encoding="utf-8")

    lines = [
        "# CanvasDaemon Toolkit Review",
        "",
        f"Pass: {counts.get('pass', 0)}",
        f"Warn: {counts.get('warn', 0)}",
        f"Fail: {counts.get('fail', 0)}",
        "",
        "## Findings",
        "",
        "| Status | Check | File | Message |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['status']} | {row['check']} | {row.get('file','')} | {row['message'].replace('|', '/')} |")
    lines.extend([
        "",
        "## Related Reports",
        "",
        f"- `{json_path.relative_to(root)}`",
        f"- `{csv_path.relative_to(root)}`",
        "- `reports/review/course_readiness/`",
    ])
    if test_output is not None:
        lines.append(f"- `{test_path.relative_to(root)}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, csv_path, json_path


def main():
    parser = argparse.ArgumentParser(description="Run the consolidated CanvasDaemon toolkit review checklist.")
    parser.add_argument("--check-history", action="store_true", help="Also scan local Git history for .env path entries.")
    parser.add_argument("--include-tests", action="store_true", help="Also run the offline unittest suite and store the output.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit nonzero when warnings are present.")
    args = parser.parse_args()

    root = ROOT_DIR
    rows = []
    rows.extend(check_git_clean_and_tracked(root, include_history=args.check_history))
    rows.extend(check_required_files(root, REQUIRED_DOCS, "docs"))
    rows.extend(check_required_files(root, AI_HELPER_FILES, "ai_helper_instructions"))
    rows.extend(check_required_files(root, REQUIRED_SCRIPTS, "scripts"))
    rows.extend(check_readme_links(root))
    rows.extend(check_template_library(root))
    rows.extend(check_script_safety(root))
    audit_rows, audit_summary = run_local_audit(root)
    rows.extend(audit_rows)

    test_output = None
    if args.include_tests:
        test_row, test_output = run_tests(root)
        rows.append(test_row)

    report_paths = write_review_reports(root, rows, audit_summary, test_output)
    counts = Counter(row["status"] for row in rows)

    print("CanvasDaemon toolkit review complete.")
    print(f"Pass: {counts.get('pass', 0)}")
    print(f"Warn: {counts.get('warn', 0)}")
    print(f"Fail: {counts.get('fail', 0)}")
    print("Reports:")
    for path in report_paths:
        print(f"- {path}")

    if counts.get("fail", 0) or (args.fail_on_warning and counts.get("warn", 0)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
