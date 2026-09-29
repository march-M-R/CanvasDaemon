import argparse
import html
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

def safe(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "checklist"

def main():
    parser = argparse.ArgumentParser(description="Generate a student progress checklist HTML page from a module plan JSON.")
    parser.add_argument("module_plan")
    parser.add_argument("--output")
    args = parser.parse_args()
    plan = json.loads(Path(args.module_plan).read_text(encoding="utf-8"))
    title = plan.get("title", "Module Progress Checklist")
    items = plan.get("checklist") or plan.get("pages") or []
    lis = []
    for item in items:
        label = item.get("label") or item.get("title") or item.get("filename") or "Complete item"
        href = item.get("url") or "#"
        lis.append(f'<li style="margin:0 0 10px;"><label><input type="checkbox"> <a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(label)}</a></label></li>')
    body = '<div style="max-width:1000px;margin:0 auto;font-family:Arial,sans-serif;color:#363D45;">'
    body += f'<header style="background:#0B0D10;color:white;padding:36px;border-radius:16px;"><h1 style="margin:0;color:white;">{html.escape(title)}</h1><p>Use this checklist to track your progress. Your browser may not save checkmarks after you leave the page.</p></header>'
    body += '<ol style="background:#fff;border:1px solid #D7DCE1;border-radius:12px;padding:24px 24px 24px 44px;">' + ''.join(lis) + '</ol></div>'
    out = Path(args.output) if args.output else ROOT_DIR / "drafts" / (safe(title) + ".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"Wrote: {out}")

if __name__ == "__main__":
    main()
