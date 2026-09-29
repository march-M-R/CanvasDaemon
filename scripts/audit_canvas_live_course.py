import argparse
import csv
import os
from pathlib import Path
from canvas_runtime import load_dotenv, requests

load_dotenv()
BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
ROOT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT_DIR / "reports" / "live_audit"

def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)

def get_all(url, params=None):
    out = []
    seen = set()
    while url:
        if url in seen:
            raise RuntimeError("Repeated pagination URL.")
        seen.add(url)
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        out.extend(response.json())
        url = response.links.get("next", {}).get("url")
        params = None
    return out

def main():
    parser = argparse.ArgumentParser(description="Read-only live Canvas course audit for modules, pages, assignments, quizzes, and files.")
    parser.parse_args()
    check_env()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    findings = []
    modules = get_all(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/modules", {"per_page": 100})
    pages = get_all(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages", {"per_page": 100})
    assignments = get_all(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments", {"per_page": 100})
    quizzes = get_all(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes", {"per_page": 100})
    files = get_all(f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files", {"per_page": 100})
    for module in modules:
        if not module.get("published"):
            findings.append(("warning", "module", module.get("name"), "Module is unpublished."))
    for page in pages:
        if not page.get("published"):
            findings.append(("info", "page", page.get("title"), "Page is unpublished."))
    for assignment in assignments:
        if not assignment.get("published"):
            findings.append(("info", "assignment", assignment.get("name"), "Assignment is unpublished."))
        if assignment.get("points_possible") is None:
            findings.append(("warning", "assignment", assignment.get("name"), "Assignment has no points_possible."))
    for quiz in quizzes:
        if not quiz.get("published"):
            findings.append(("info", "quiz", quiz.get("title"), "Quiz is unpublished."))
    for file in files:
        if file.get("locked") or file.get("hidden"):
            findings.append(("warning", "file", file.get("filename"), "File is locked or hidden."))
    out = REPORT_DIR / "live_course_audit.csv"
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["severity", "type", "name", "message"])
        writer.writerows(findings)
    print("Live Canvas audit complete.")
    print(f"Modules: {len(modules)} Pages: {len(pages)} Assignments: {len(assignments)} Quizzes: {len(quizzes)} Files: {len(files)}")
    print(f"Findings: {len(findings)}")
    print(f"Report: {out}")

if __name__ == "__main__":
    main()
