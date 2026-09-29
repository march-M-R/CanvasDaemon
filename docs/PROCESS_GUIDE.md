# CanvasDaemon Process Guide

This guide documents the decisions and workflows that turned CanvasDaemon from a course-specific working repo into a reusable toolkit teammates can use with Codex, Copilot, Cursor, Claude Code, or another coding helper.

Use this when you want to repeat the same process for another course, audit the repository before sharing it, or explain why the repo is organized this way.

## What Was Requested and How It Was Handled

| Request | What changed in the repo | Repeatable process |
|---|---|---|
| Make the repo reusable for teammates building their own courses | Cleaned the repo into a toolkit shape, with reusable scripts, docs, and templates at the branch tip | Keep scripts/docs/templates tracked; keep generated course exports local |
| Polish existing scripts and push updates to GitHub | Updated and pushed the maintained V1 toolkit scripts and safety behavior | Run tests, commit focused changes, push to `main` |
| Remove `.env` and remove it from earlier commits | Removed real credentials from the current branch and cleaned public branch history | Track only `.env.example`; ignore `.env`; rotate exposed tokens |
| Decide what to do with all exported pages | Removed generated course pages from the shared branch | Pull pages locally per course; do not commit `pages/` or `manifest.json` |
| Keep one best example for each template type | Added `examples/templates/` with one approved reference per page/activity type | Treat examples as patterns; replace course-specific text, links, media, and claims |
| Include a mini-activity reference | Added an embedded mini-activity example to the template set | Use standalone HTML activities as Canvas Files and embed them by Canvas URL |
| Use the high-school course image style | Kept the approved high-school-style image reference | Use `examples/templates/assets/m2_1_1_examples_patterns.png` as the visual style reference |
| Create handbook documentation | Added Markdown and HTML handbook files | Maintain `docs/HANDBOOK.md` first, then regenerate `docs/HANDBOOK.html` |
| Create setup documentation | Added Markdown and HTML setup files | Use `docs/SETUP.md` for first-time teammate onboarding |
| Add module creation support | Added `scripts/create_module.py` | Create missing modules with dry-run first, then `--apply --confirm-course` |
| Confirm every write script has a safety gate | Standardized write scripts on shared `add_write_flags` and `authorize` helpers | Every Canvas write must require `--apply --confirm-course COURSE_ID` |
| Help AI coding assistants know what to do | Added AI-helper instructions for Codex, Copilot, Cursor, and Claude | Keep `docs/AI_HELPER_GUIDE.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, and `.cursor/rules/canvasdaemon.mdc` current |
| Upload page assets and link them correctly | Added `scripts/prepare_page_assets.py` | Scan local page references, upload assets to Canvas Files, write Canvas-linked HTML, then preview |

## Process 1: Prepare the Repo Before Sharing

Start from a clean branch:

```bash
git status --short --branch
git pull --ff-only
```

Check for secrets or generated course files:

```bash
git ls-files .env
rg -n "CANVAS_TOKEN|Bearer|instructure.com" .
```

The shared branch should not track:

- `.env`
- `.venv/`
- `pages/`
- `manifest.json`
- `backups/`
- `reports/`
- `canvas_files/`
- `asset_manifest.json`
- `preview_config.json`

Keep `.env.example` tracked so teammates know which variables to create locally.

If a secret was ever committed, remove it from history and rotate the credential in Canvas. After cleanup, verify:

```bash
git log --all --name-only --pretty=format: | rg '(^|/)\.env$'
```

No output means `.env` is not present in the checked local history.

## Process 2: Onboard a Teammate

A teammate starts with:

```bash
git clone https://github.com/march-M-R/CanvasDaemon.git
cd CanvasDaemon
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

They edit `.env` locally:

```bash
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_TOKEN=your-local-token
COURSE_ID=12345
```

Then they run a read-only check:

```bash
python scripts/test_canvas.py
```

They should confirm the printed course name and course ID before running any write command.

## Process 3: Get Someone Else's Changes First

There are two sources of change: GitHub and Canvas.

For GitHub changes:

```bash
git status --short --branch
git pull --ff-only
```

If local edits exist, review them before pulling:

```bash
git diff --stat
git diff
```

For Canvas changes:

```bash
python scripts/test_canvas.py
python scripts/pull_pages.py
python scripts/pull_files_metadata.py
python scripts/course_inventory.py
```

`push_page.py` protects against stale Canvas edits. If Canvas changed since the last pull, it refuses to write. Pull fresh content, merge the local change by hand, preview again, and then push.

## Process 4: Use the Template Library

Start with:

```text
examples/templates/README.md
```

The template library keeps one approved example of each reusable pattern:

- course welcome
- course roadmap
- resource hub
- module overview
- main lesson
- microlearning page
- embedded mini activity
- tool setup
- opening discussion
- module summary
- progress checklist
- quiz answer review
- image style reference

Copy structure and style, but replace all course-specific content:

- course title
- module title
- learning outcomes
- dates and completion language
- Canvas links
- video links
- image references
- activity links
- grading language
- institution-specific instructions

Use this image as the style reference for new high-school illustrations:

```text
examples/templates/assets/m2_1_1_examples_patterns.png
```

## Process 5: Create a Module

Dry run first:

```bash
python scripts/create_module.py "Module 3: Building AI Systems"
```

Create it for real:

```bash
python scripts/create_module.py "Module 3: Building AI Systems" --position 3 --apply --confirm-course 12345
```

Useful options:

```bash
python scripts/create_module.py "Module 4: Responsible AI" --published --apply --confirm-course 12345
python scripts/create_module.py "Module 5: Model Evaluation" --prerequisite-module-id 123 --apply --confirm-course 12345
python scripts/create_module.py "Module 6: Final Project" --unlock-at 2026-10-01T09:00:00-04:00 --apply --confirm-course 12345
```

The script checks for an exact existing module name before creating a new one.

## Process 6: Create or Update a Page

Pull Canvas pages first:

```bash
python scripts/pull_pages.py
```

Create a new page from a local HTML file:

```bash
python scripts/create_page.py "Lesson title" --body-file lesson.html
python scripts/create_page.py "Lesson title" --body-file lesson.html --apply --confirm-course 12345
```

Update an existing page:

```bash
python scripts/push_page.py "lesson-filename.html"
python scripts/push_page.py "lesson-filename.html" --apply --confirm-course 12345
```

Attach a page to a module:

```bash
python scripts/add_page_to_module.py "lesson-filename.html" "Module 3" --apply --confirm-course 12345
```

For pages already known to be module-active:

```bash
python scripts/course_inventory.py
python scripts/push_module_page.py "lesson-filename.html" --apply --confirm-course 12345
```

## Process 7: Upload Assets and Link Them Correctly

Canvas pages should not depend on local file paths like `../assets/image.png` after publishing. Upload assets to Canvas Files and use Canvas URLs.

For one file:

```bash
python scripts/upload_canvas_file.py assets/image.png --folder "CanvasDaemon/module-03"
python scripts/upload_canvas_file.py assets/image.png --folder "CanvasDaemon/module-03" --apply --confirm-course 12345
python scripts/pull_files_metadata.py
python scripts/find_asset.py "image.png"
```

For all local assets referenced by one page:

```bash
python scripts/prepare_page_assets.py pages/example.html
python scripts/prepare_page_assets.py pages/example.html --folder "CanvasDaemon/module-03" --apply --confirm-course 12345
```

The dry run lists local references. The apply run uploads the assets, updates `asset_manifest.json`, and writes a Canvas-linked copy under:

```text
reports/prepared_pages/
```

Preview the rewritten page before pushing it. If the rewritten page looks right, copy the reviewed HTML back into the matching `pages/` file deliberately, then run `push_page.py`.

Use `--rename` if you do not want to overwrite a same-named Canvas file.

## Process 8: Preview Before Production Pushes

Set up the preview page once per course:

```bash
python scripts/setup_preview_environment.py --apply --confirm-course 12345
```

Preview a page:

```bash
python scripts/preview_page_in_canvas.py pages/example.html --apply --confirm-course 12345
```

Preview a prepared Canvas-linked page:

```bash
python scripts/preview_page_in_canvas.py reports/prepared_pages/example.html --apply --confirm-course 12345
```

Preview an asset:

```bash
python scripts/preview_asset_in_canvas.py assets/image.png --apply --confirm-course 12345
```

Check layout, links, images, activity embeds, mobile behavior, and student readability in Canvas.

## Process 9: Create Discussions

Create a discussion from text or HTML:

```bash
python scripts/create_discussion.py "Opening Discussion" --message-file discussion.html
python scripts/create_discussion.py "Opening Discussion" --message-file discussion.html --module "Module 2" --apply --confirm-course 12345
```

Options include publishing, discussion type, require-initial-post, module placement, and module item indent.

## Process 10: Create and Sync Classic Quizzes

Create an unpublished Classic Quiz from JSON:

```bash
python scripts/create_classic_quiz.py quiz_banks/example.json
python scripts/create_classic_quiz.py quiz_banks/example.json --apply --confirm-course 12345
```

Pull and search quiz inventory:

```bash
python scripts/pull_classic_quizzes.py
python scripts/find_quiz.py "quiz title"
```

Sync quiz shell/settings:

```bash
python scripts/sync_classic_quiz.py quiz_banks/example.json
python scripts/sync_classic_quiz.py quiz_banks/example.json --apply --confirm-course 12345
```

`sync_classic_quiz.py` synchronizes settings only, not questions. New quizzes are created unpublished.

## Process 11: Document the Toolkit

Primary documentation files:

- `README.md` for the quick overview
- `docs/SETUP.md` for first-time setup
- `docs/HANDBOOK.md` for the full teammate handbook
- `docs/AI_HELPER_GUIDE.md` for AI coding assistant behavior
- `docs/PROCESS_GUIDE.md` for the complete process history and repeatable workflows
- `docs/V1_MAINTENANCE.md` for maintenance limitations and recovery notes

When changing a Markdown guide, update its HTML counterpart too.

## Process 12: Guide AI Coding Helpers

AI helpers should read:

- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/canvasdaemon.mdc`
- `docs/AI_HELPER_GUIDE.md`

These files tell helpers to:

- pull repo changes before editing when possible
- pull Canvas state before live course edits
- keep generated course files out of Git
- organize pages, assets, activities, and quizzes correctly
- upload local assets to Canvas Files before production linking
- preserve `--apply --confirm-course COURSE_ID`
- run tests before committing script changes

## Process 13: Keep Every Canvas Write Guarded

Every script that writes to Canvas must use the shared safety helpers:

```python
from canvas_runtime import add_write_flags, authorize
```

Add flags:

```python
add_write_flags(parser)
```

Gate the write:

```python
if not authorize(args, BASE_URL, COURSE_ID):
    return
```

This means a script only writes when the command includes both:

```bash
--apply --confirm-course 12345
```

If someone forgets the flags, the command stays a dry run or refuses to write. If the course ID is wrong, the command refuses to write.

## Process 14: Run Student-Facing Course Content Review

Run this after pulling pages, after broad course edits, and before a major preview/push pass:

```bash
python scripts/review_course_content.py
```

This consolidates the manual course review checks: internal notes, placeholders, TODO/FIXME/DRAFT text, encoding artifacts, placeholder or empty links, missing alt text, missing iframe titles, local assets that still need Canvas upload, missing local assets, mobile layout risks, Panopto/student-access review markers, and course-specific terms to verify when adapting a page. Reports are written under:

```text
reports/course_review/
```

Use `--fail-on-warning` when warnings should block the handoff.

## Process 15: Run a Detailed Readiness Audit

Run the local audit before a major Canvas push, before handing a course workspace to another teammate, or after a coding helper makes broad edits:

```bash
python scripts/audit_course_readiness.py
```

The audit is read-only. It checks local repo state, manifests, pulled pages, missing local assets, image alt text, placeholder links, template library files, and script write-safety gates. It writes detailed reports under:

```text
reports/audit/
```

Use this stricter mode if warnings should fail the command:

```bash
python scripts/audit_course_readiness.py --fail-on-warning
```

## Process 16: Run the Consolidated Review Checklist

Run one command to consolidate the manual review checks from the toolkit cleanup process:

```bash
python scripts/review_course_toolkit.py --check-history --include-tests
```

This checks Git cleanliness, forbidden tracked files, optional `.env` history, required documentation, AI-helper files, required scripts, README links, template library completeness, image-style reference, write-safety gates, the detailed readiness audit, and offline tests. Reports are written under:

```text
reports/review/
```

Use `--fail-on-warning` for stricter handoff reviews.

## Process 17: Run Tests Before Sharing

Run:

```bash
python -m unittest discover -s tests -v
```

The test suite is offline and uses mocked Canvas responses. It verifies core safety behavior such as:

- config validation
- cross-course request refusal
- dry-run write protection
- page backup and stale remote protection
- duplicate module attachment no-op
- module creation dry-run behavior
- asset collection and rewrite behavior
- upload callback scoping
- quiz validation

## Process 18: Commit and Push a Toolkit Change

Review changes:

```bash
git status --short --branch
git diff --stat
git diff
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Commit:

```bash
git add <changed files>
git commit -m "Clear description of the change"
```

Push:

```bash
git push origin main
```

After pushing, confirm:

```bash
git status --short --branch
git log -1 --oneline
```

## Current Share-Ready State

The repo is now designed to be shared as a reusable course-building toolkit. It includes:

- cleaned history and ignored local secrets
- one approved template reference set
- Markdown and HTML setup, handbook, AI-helper, and process documentation
- guarded write scripts
- module creation
- page creation and push workflows
- Canvas preview workflows
- asset upload and page asset preparation workflows
- student-facing course content review reports
- detailed local readiness audit reports
- consolidated toolkit review reports
- Classic Quiz and discussion workflows
- offline regression tests

Teammates can use this repo with a coding helper, but they should still review every Canvas preview before pushing production content.
