from canvas_runtime import add_write_flags, authorize, load_dotenv
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from validate_course_plan import validate_plan

load_dotenv()
BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
COURSE_ID = os.getenv("COURSE_ID")
ROOT_DIR = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Scaffold a Canvas course from a plan by creating modules and pages.")
    parser.add_argument("course_plan")
    parser.add_argument("--validate-only", action="store_true")
    add_write_flags(parser)
    args = parser.parse_args()
    plan = json.loads(Path(args.course_plan).read_text(encoding="utf-8"))
    findings = validate_plan(plan, ROOT_DIR)
    errors = [f for f in findings if f[0] == "error"]
    for severity, where, message in findings:
        print(f"{severity.upper()}: {where}: {message}")
    if errors:
        raise SystemExit(1)
    modules = plan.get("modules", [])
    page_count = sum(len(module.get("pages", [])) for module in modules)
    print(f"Plan: scaffold {len(modules)} module(s) and {page_count} page(s).")
    if args.validate_only:
        return
    if not authorize(args, BASE_URL, COURSE_ID):
        return
    for index, module in enumerate(modules, start=1):
        cmd = [sys.executable, str(ROOT_DIR / "scripts" / "create_module.py"), module["title"], "--position", str(module.get("position", index))]
        if module.get("published"):
            cmd.append("--published")
        cmd += ["--apply", "--confirm-course", str(COURSE_ID)]
        subprocess.run(cmd, check=True)
        for page in module.get("pages", []):
            create = [sys.executable, str(ROOT_DIR / "scripts" / "create_page.py"), page["title"]]
            body_file = page.get("body_file") or page.get("file")
            if body_file:
                create += ["--body-file", body_file]
            if page.get("published"):
                create.append("--published")
            create += ["--apply", "--confirm-course", str(COURSE_ID)]
            subprocess.run(create, check=True)
    print("Scaffold complete. Pull pages, review manifest filenames, then attach pages with bulk_add_pages_to_module.py if needed.")

if __name__ == "__main__":
    main()
