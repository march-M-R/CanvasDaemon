import argparse
import json
import re
from pathlib import Path
from replace_course_placeholders import apply_values

ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT_DIR / "examples" / "templates" / "pages"
DEFAULT_TEMPLATE_MAP = {
    "overview": "module-overview.html",
    "main_lesson": "main-lesson.html",
    "microlearning": "quick-concept.html",
    "guided_activity": "guided-activity.html",
    "summary": "module-summary.html",
    "progress_checklist": "progress-checklist.html",
    "answer_review": "answer-review.html",
}

def safe(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "module"

def main():
    parser = argparse.ArgumentParser(description="Create local module draft pages from approved reference templates and JSON values.")
    parser.add_argument("module_plan")
    parser.add_argument("--output-dir", default="drafts")
    args = parser.parse_args()
    plan = json.loads(Path(args.module_plan).read_text(encoding="utf-8"))
    values = plan.get("values", {})
    module_slug = safe(plan.get("module_slug") or plan.get("title") or "module")
    out_dir = ROOT_DIR / args.output_dir / module_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = plan.get("templates", DEFAULT_TEMPLATE_MAP)
    created = []
    for key, template_name in templates.items():
        template_path = TEMPLATE_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        out = out_dir / f"{module_slug}-{safe(key)}.html"
        out.write_text(apply_values(template_path.read_text(encoding="utf-8"), values), encoding="utf-8")
        created.append(out)
    print("Created module draft pages:")
    for path in created:
        print(f"- {path}")

if __name__ == "__main__":
    main()
