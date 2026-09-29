import argparse
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def load_plan(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Course plan must be a JSON object.")
    return data


def validate_plan(plan, root=ROOT_DIR):
    findings = []
    modules = plan.get("modules")
    if not isinstance(modules, list):
        return [("error", "modules", "Course plan must contain a modules list.")]
    module_titles = set()
    page_titles = set()
    for mi, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            findings.append(("error", f"modules[{mi}]", "Module entry must be an object.")); continue
        title = module.get("title")
        if not title:
            findings.append(("error", f"modules[{mi}]", "Module missing title."))
        elif title.lower() in module_titles:
            findings.append(("warning", title, "Duplicate module title."))
        else:
            module_titles.add(title.lower())
        pages = module.get("pages", [])
        if not isinstance(pages, list):
            findings.append(("error", title or f"modules[{mi}]", "pages must be a list.")); continue
        for pi, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                findings.append(("error", f"{title} page {pi}", "Page entry must be an object.")); continue
            ptitle = page.get("title")
            body_file = page.get("body_file") or page.get("file")
            if not ptitle:
                findings.append(("error", f"{title} page {pi}", "Page missing title."))
            elif ptitle.lower() in page_titles:
                findings.append(("warning", ptitle, "Duplicate page title."))
            else:
                page_titles.add(ptitle.lower())
            if body_file and not (root / body_file).exists():
                findings.append(("error", ptitle or body_file, f"Body file not found: {body_file}"))
            for asset in page.get("assets", []):
                if not (root / asset).exists():
                    findings.append(("error", ptitle or body_file or "asset", f"Asset not found: {asset}"))
        for key in ["discussion_file", "quiz_json", "assignment_file"]:
            value = module.get(key)
            if value and not (root / value).exists():
                findings.append(("error", title or key, f"Referenced file not found: {value}"))
    return findings


def main():
    parser = argparse.ArgumentParser(description="Validate a CanvasDaemon course plan JSON file.")
    parser.add_argument("plan")
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()
    findings = validate_plan(load_plan(args.plan))
    errors = sum(1 for sev, _, _ in findings if sev == "error")
    warnings = sum(1 for sev, _, _ in findings if sev == "warning")
    for sev, where, msg in findings:
        print(f"{sev.upper()}: {where}: {msg}")
    if not findings:
        print("Course plan looks valid.")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    if errors or (warnings and args.fail_on_warning):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
