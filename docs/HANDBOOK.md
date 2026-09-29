# CanvasDaemon Handbook

This handbook explains how to use CanvasDaemon as a reusable course-building toolkit. It is written for teammates who want to build or maintain their own Canvas courses using the same workflow, scripts, and approved reference templates.

CanvasDaemon lets you work locally, preview deliberately, and write to Canvas only when you are ready. The safest habit is simple: pull the course into a local workspace, edit files locally, preview in Canvas, then push with explicit confirmation.

## Table of Contents

1. [What CanvasDaemon Can Do](#what-canvasdaemon-can-do)
2. [How the Repository Is Organized](#how-the-repository-is-organized)
3. [First-Time Setup](#first-time-setup)
4. [The Daily Workflow](#the-daily-workflow)
5. [Using the Template Reference Library](#using-the-template-reference-library)
6. [Module Workflows](#module-workflows)
7. [Page Workflows](#page-workflows)
8. [Canvas File and Image Workflows](#canvas-file-and-image-workflows)
9. [Preview Workflows](#preview-workflows)
10. [Discussion Workflows](#discussion-workflows)
11. [Classic Quiz Workflows](#classic-quiz-workflows)
12. [Panopto and Video Inventory](#panopto-and-video-inventory)
13. [Detailed Readiness Audit](#detailed-readiness-audit)
14. [Script Reference](#script-reference)
15. [Safety Rules](#safety-rules)
16. [Recovery and Troubleshooting](#recovery-and-troubleshooting)
17. [Recommended Team Practices](#recommended-team-practices)

## What CanvasDaemon Can Do

CanvasDaemon supports a local-first workflow for Canvas course production. It can:

- Check that your Canvas credentials and course ID work.
- Pull Canvas pages into local HTML files.
- Search active module pages and all pulled pages.
- Inventory which pages are used in modules and which ones appear unused.
- Diff local edits against Canvas before writing.
- Push page updates back to Canvas with backups and explicit confirmation.
- Create new Canvas modules.
- Create new Canvas pages from local HTML.
- Add existing pages to Canvas modules.
- Set up and use a dedicated Canvas preview page.
- Preview local page HTML inside Canvas before production updates.
- Pull Canvas file metadata and search for uploaded assets.
- Upload files to Canvas Files.
- Preview uploaded assets in Canvas.
- Download editable Canvas files and referenced editable assets.
- Create unpublished Classic Quizzes from JSON.
- Pull Classic Quiz inventory.
- Search Classic Quiz inventory.
- Sync Classic Quiz settings.
- Create Canvas discussions and optionally add them to modules.
- Scan local pages for Panopto references.
- Keep one approved reference example for each course page pattern.

CanvasDaemon does not replace instructional review, accessibility review, copyright review, student access checks, or final Canvas QA. It automates the mechanical parts so humans can focus on the course.

## How the Repository Is Organized

The shared GitHub repo is now a toolkit, not a full exported course. Generated course pages and backups are intentionally not tracked at the branch tip.

| Path | Purpose |
|---|---|
| `scripts/` | Canvas automation scripts. |
| `docs/HANDBOOK.md` | This guide. |
| `docs/V1_MAINTENANCE.md` | Maintenance notes, recovery boundaries, and safety details. |
| `examples/templates/` | Approved reusable page and activity reference library. |
| `examples/templates/pages/` | One reference HTML page for each page type. |
| `examples/templates/assets/` | Assets required by the reference examples, including the image style reference. |
| `examples/templates/screenshots/` | Desktop and mobile screenshots of each reference page. |
| `examples/templates/metadata/template-library.json` | Structured metadata for the reference library. |
| `assets/` | Small test assets tracked with the toolkit. Put new local assets here before upload. |
| `quiz_banks/` | Example quiz JSON files. Add course quiz banks here locally or in a course branch. |
| `tests/` | Offline regression tests. These do not contact Canvas. |
| `.env.example` | Template for local Canvas configuration. |
| `.gitignore` | Ignores local secrets, generated pages, backups, reports, Canvas downloads, preview config, and virtualenvs. |
| `CanvasDaemon_Runbook.html` | Older visual runbook. Useful background, but this handbook and README are the current source of truth. |

These folders are generated locally and should not be committed:

| Generated Path | Created By | Purpose |
|---|---|---|
| `pages/` | `pull_pages.py`, `create_page.py` | Local Canvas page HTML files. |
| `manifest.json` | `pull_pages.py`, page creation/push scripts | Local mapping between Canvas pages and files. |
| `backups/` | Pull and push scripts | Local recovery copies. |
| `reports/` | Inventory scripts | CSV and text reports. |
| `canvas_files/` | File download scripts | Downloaded Canvas file content. |
| `asset_manifest.json` | `pull_files_metadata.py` | Local mapping for Canvas Files. |
| `preview_config.json` | `setup_preview_environment.py` | Preview page configuration. |
| `.env` | You | Local credentials. Never commit. |
| `.venv/` | You | Local Python environment. Never commit. |

## First-Time Setup

For a standalone onboarding page, use the [CanvasDaemon Setup Guide](SETUP.md). The shorter setup path is below.

Clone the repository:

```bash
git clone https://github.com/march-M-R/CanvasDaemon.git
cd CanvasDaemon
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create your local `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_TOKEN=your-local-token
COURSE_ID=12345
```

Use the Canvas course ID from the course URL. For example, if the course URL contains `/courses/12345`, your `COURSE_ID` is `12345`.

Run the read-only connection check:

```bash
python scripts/test_canvas.py
```

Before doing any writes, confirm the printed course name and course ID are the course you intend to edit.

## The Daily Workflow

Most page work follows this sequence:

```bash
python scripts/test_canvas.py
python scripts/pull_pages.py
python scripts/course_inventory.py
python scripts/find_page.py "overview"
python scripts/preview_page_in_canvas.py "filename.html" --apply --confirm-course 12345
python scripts/push_module_page.py "filename.html"
python scripts/push_module_page.py "filename.html" --apply --confirm-course 12345
```

The first push command is a dry run. It shows what would change. The second one writes to Canvas.

If you are creating new course content from a template:

1. Pick the closest example from `examples/templates/pages/`.
2. Copy it into your local `pages/` folder after you have pulled the target course.
3. Rename it clearly.
4. Replace course-specific text, links, video embeds, images, activity assets, and completion language.
5. Create or update the Canvas page using the guarded scripts.
6. Preview in Canvas.
7. Add to the correct module.
8. Push only after the dry run looks right.

## Using the Template Reference Library

The approved examples live in `examples/templates/`.

| Template Type | File |
|---|---|
| Course welcome | `examples/templates/pages/course-welcome.html` |
| Course roadmap | `examples/templates/pages/course-roadmap.html` |
| Orientation / resource hub | `examples/templates/pages/course-guide.html` |
| Module overview | `examples/templates/pages/module-overview.html` |
| Main lesson | `examples/templates/pages/main-lesson.html` |
| Quick concept / microlearning | `examples/templates/pages/quick-concept.html` |
| Embedded micro-learning mini activity | `examples/templates/pages/guided-activity.html` |
| Tool setup / recovery guide | `examples/templates/pages/tool-setup.html` |
| Opening discussion | `examples/templates/pages/opening-discussion.html` |
| Module summary with video | `examples/templates/pages/module-summary.html` |
| Interactive progress checklist | `examples/templates/pages/progress-checklist.html` |
| Quiz answer review | `examples/templates/pages/answer-review.html` |

Use these examples as patterns, not finished content. Before publishing in a new course, replace:

- Course title and module title.
- Lesson titles and learning outcomes.
- Links to Canvas pages, modules, assignments, files, and discussions.
- Panopto/video embeds.
- Iframes and embedded activity file references.
- Quiz, checklist, and completion language.
- Any original course-specific claims.
- Images that do not fit the new course.

The image style reference is:

```text
examples/templates/assets/m2_1_1_examples_patterns.png
```

Use it as the guide for new course illustrations: high-school setting, student-facing, warm, concrete, story-based, and tied to the learning concept. Avoid abstract futuristic dashboard imagery unless the page truly needs that mood.

For coding assistants, use [AI Helper Guide](AI_HELPER_GUIDE.md) as the repo-specific instruction source.

## Module Workflows

Create a module when you are building a new course shell or adding a new unit:

```bash
python scripts/create_module.py "Module 3: Building AI Systems"
```

The default command is a dry run. To write to Canvas, confirm the course explicitly:

```bash
python scripts/create_module.py "Module 3: Building AI Systems" --position 3 --apply --confirm-course 12345
```

Useful options:

```bash
python scripts/create_module.py "Module 4: Responsible AI" --published --apply --confirm-course 12345
python scripts/create_module.py "Module 5: Model Evaluation" --prerequisite-module-id 123 --apply --confirm-course 12345
python scripts/create_module.py "Module 6: Final Project" --unlock-at 2026-10-01T09:00:00-04:00 --apply --confirm-course 12345
```

The script checks for an exact existing module name before creating a new one. After the module exists, create or pull pages and attach them with `add_page_to_module.py`.

## Page Workflows

### Pull Pages

Pulling downloads Canvas page bodies into `pages/` and updates `manifest.json`.

```bash
python scripts/pull_pages.py
```

If you have local edits, the pull will stop rather than overwrite them. Use this as a signal to save or merge your work. Only use overwrite when you deliberately want the live Canvas copy to replace local edits:

```bash
python scripts/pull_pages.py --overwrite-local
```

### Inventory the Course

After pulling, run:

```bash
python scripts/course_inventory.py
```

This builds reports that help distinguish active module pages from unused pages. That matters because Canvas courses often contain duplicate old pages with similar titles.

### Find a Page

Search active module pages:

```bash
python scripts/find_page.py "data"
```

Search all pulled pages:

```bash
python scripts/find_any_page.py "data"
```

Prefer `find_page.py` for production edits because it focuses on pages currently used in modules.

### Edit a Page

Open the local HTML file from `pages/` in your editor. Keep edits scoped to the intended page.

### Preview a Page in Canvas

Set up the preview environment once:

```bash
python scripts/setup_preview_environment.py --apply --confirm-course 12345
```

Preview a local page:

```bash
python scripts/preview_page_in_canvas.py "filename.html" --apply --confirm-course 12345
```

Use `--no-open` if you do not want the script to open a browser:

```bash
python scripts/preview_page_in_canvas.py "filename.html" --apply --confirm-course 12345 --no-open
```

### Push a Page

Dry run first:

```bash
python scripts/push_page.py "filename.html"
```

Apply only after the diff is correct:

```bash
python scripts/push_page.py "filename.html" --apply --confirm-course 12345
```

For active module pages, prefer:

```bash
python scripts/push_module_page.py "filename.html"
python scripts/push_module_page.py "filename.html" --apply --confirm-course 12345
```

`push_module_page.py` verifies that the page is in the module inventory before delegating to the page push workflow.

### Create a New Page

Create a dry-run plan:

```bash
python scripts/create_page.py "New Lesson Title" --body-file local-page.html
```

Create the page:

```bash
python scripts/create_page.py "New Lesson Title" --body-file local-page.html --apply --confirm-course 12345
```

Use `--published` only when the page should be published immediately:

```bash
python scripts/create_page.py "New Lesson Title" --body-file local-page.html --published --apply --confirm-course 12345
```

### Add a Page to a Module

Dry run:

```bash
python scripts/add_page_to_module.py "new-lesson-title.html" "Module 2"
```

Apply:

```bash
python scripts/add_page_to_module.py "new-lesson-title.html" "Module 2" --apply --confirm-course 12345
```

You can indent the module item:

```bash
python scripts/add_page_to_module.py "new-lesson-title.html" "Module 2" --indent 1 --apply --confirm-course 12345
```

## Canvas File and Image Workflows

### Pull File Metadata

```bash
python scripts/pull_files_metadata.py
```

This creates `asset_manifest.json` and file reports. It does not download every file body.

### Find Assets

```bash
python scripts/find_asset.py "checklist"
```

Use this to locate Canvas file IDs and generate snippets for embedding assets.

### Upload a File

Dry run:

```bash
python scripts/upload_canvas_file.py assets/image.png
```

Apply:

```bash
python scripts/upload_canvas_file.py assets/image.png --apply --confirm-course 12345
```

Upload into a folder:

```bash
python scripts/upload_canvas_file.py assets/image.png --folder "CanvasDaemon/images" --apply --confirm-course 12345
```

Rename if a matching filename already exists instead of overwriting:

```bash
python scripts/upload_canvas_file.py assets/image.png --rename --apply --confirm-course 12345
```

Use a Canvas-side filename:

```bash
python scripts/upload_canvas_file.py assets/image.png --canvas-name "module-2-hero.png" --apply --confirm-course 12345
```

### Download Editable Files

Download editable Canvas files:

```bash
python scripts/download_editable_files.py
```

Download files referenced by pulled pages:

```bash
python scripts/download_referenced_editable_files.py
```

These are useful for embedded HTML activities, JS/CSS files, and other editable Canvas-hosted assets.

## Preview Workflows

Canvas may sanitize HTML, change iframe behavior, or require file permissions. Preview in Canvas when visual or embedded behavior matters.

Set up preview:

```bash
python scripts/setup_preview_environment.py --apply --confirm-course 12345
```

Preview a page:

```bash
python scripts/preview_page_in_canvas.py "filename.html" --apply --confirm-course 12345
```

Preview a standalone asset, such as an HTML activity:

```bash
python scripts/preview_asset_in_canvas.py "assets/activities/activity.html" --apply --confirm-course 12345
```

If the preview page has been published, the script protects it from overwrite. Inspect Canvas and unpublish or recreate the preview setup before continuing.

## Discussion Workflows

Create a discussion from inline HTML:

```bash
python scripts/create_discussion.py "Opening Discussion" --message "<p>Prompt goes here.</p>"
```

Create from an HTML file:

```bash
python scripts/create_discussion.py "Opening Discussion" --message-file discussion.html
```

Create and add to a module:

```bash
python scripts/create_discussion.py "Opening Discussion" --message-file discussion.html --module "Module 2"
```

Apply:

```bash
python scripts/create_discussion.py "Opening Discussion" --message-file discussion.html --module "Module 2" --apply --confirm-course 12345
```

Optional flags:

```bash
--published
--discussion-type threaded
--discussion-type side_comment
--require-initial-post
--indent 1
```

New discussions can still duplicate an existing discussion if rerun after an uncertain network failure. Inspect Canvas before rerunning.

## Classic Quiz Workflows

CanvasDaemon supports Classic Quizzes, not New Quizzes.

### Create a Quiz

Put quiz JSON in `quiz_banks/`.

Validate JSON:

```bash
python -m json.tool quiz_banks/my_quiz.json
```

Dry run:

```bash
python scripts/create_classic_quiz.py quiz_banks/my_quiz.json
```

Create the quiz:

```bash
python scripts/create_classic_quiz.py quiz_banks/my_quiz.json --apply --confirm-course 12345
```

New quizzes are created unpublished.

### Inventory Quizzes

```bash
python scripts/pull_classic_quizzes.py
```

### Find a Quiz

```bash
python scripts/find_quiz.py "module 2"
```

### Sync Quiz Settings

Dry run:

```bash
python scripts/sync_classic_quiz.py quiz_banks/my_quiz.json
```

Apply:

```bash
python scripts/sync_classic_quiz.py quiz_banks/my_quiz.json --apply --confirm-course 12345
```

`sync_classic_quiz.py` syncs quiz shell/settings only. It does not replace quiz questions.

## Panopto and Video Inventory

Scan local pulled pages for Panopto embeds:

```bash
python scripts/discover_panopto.py
```

This writes `panopto_manifest.json` and a report. It does not create, upload, or edit videos.

When adapting templates for another course, replace Panopto links and iframes with the new course videos.

## Detailed Readiness Audit

Run the read-only audit before sharing a course workspace, before major Canvas pushes, or when a coding helper has made many changes:

```bash
python scripts/audit_course_readiness.py
```

The audit checks local-only repo state, manifests, pulled pages, missing local assets, image alt text, placeholder links, template library files, and whether Canvas-writing scripts use the shared safety gate. It writes:

```text
reports/audit/course_readiness_summary.txt
reports/audit/course_readiness_findings.csv
reports/audit/course_readiness_audit.json
reports/audit/local_asset_references.csv
```

Use `--fail-on-warning` if you want the command to exit nonzero on warnings in CI or a stricter review pass. The audit is local and read-only; it does not contact Canvas.

## Script Reference

| Script | What It Does | Writes to Canvas? |
|---|---|---|
| `test_canvas.py` | Checks Canvas connection and configured course. | No |
| `pull_pages.py` | Downloads Canvas pages into `pages/` and updates `manifest.json`. | No |
| `list_pages.py` | Lists Canvas pages. | No |
| `list_module_pages.py` | Lists pages attached to modules. | No |
| `course_inventory.py` | Builds active/unused page reports. | No |
| `audit_course_readiness.py` | Runs a local readiness audit and writes detailed reports. | No |
| `find_page.py` | Searches active module pages. | No |
| `find_any_page.py` | Searches all pulled pages. | No |
| `push_page.py` | Diffs and updates a Canvas page. | Yes, only with `--apply --confirm-course` |
| `push_module_page.py` | Pushes a page verified as module-active. | Yes, only with `--apply --confirm-course` |
| `create_module.py` | Creates a new Canvas module. | Yes, only with `--apply --confirm-course` |
| `create_page.py` | Creates a new Canvas page. | Yes, only with `--apply --confirm-course` |
| `add_page_to_module.py` | Adds an existing page to a Canvas module. | Yes, only with `--apply --confirm-course` |
| `setup_preview_environment.py` | Creates/reuses a dedicated Canvas preview page. | Yes, only with `--apply --confirm-course` |
| `preview_page_in_canvas.py` | Writes local HTML to the preview page. | Yes, only with `--apply --confirm-course` |
| `pull_files_metadata.py` | Pulls Canvas file metadata. | No |
| `find_asset.py` | Searches local file metadata. | No |
| `upload_canvas_file.py` | Uploads a local file to Canvas Files. | Yes, only with `--apply --confirm-course` |
| `prepare_page_assets.py` | Finds local page asset references, uploads them, and writes Canvas-linked HTML. | Yes, only with `--apply --confirm-course` |
| `preview_asset_in_canvas.py` | Uploads/previews a local asset in Canvas. | Yes, only with `--apply --confirm-course` |
| `download_editable_files.py` | Downloads editable Canvas files. | No |
| `download_referenced_editable_files.py` | Downloads editable files referenced by pages. | No |
| `create_discussion.py` | Creates a discussion and optionally places it in a module. | Yes, only with `--apply --confirm-course` |
| `create_classic_quiz.py` | Creates an unpublished Classic Quiz from JSON. | Yes, only with `--apply --confirm-course` |
| `pull_classic_quizzes.py` | Pulls Classic Quiz inventory. | No |
| `find_quiz.py` | Searches local quiz inventory. | No |
| `sync_classic_quiz.py` | Syncs Classic Quiz shell/settings. | Yes, only with `--apply --confirm-course` |
| `discover_panopto.py` | Scans local pages for Panopto references. | No |

## Safety Rules

CanvasDaemon is designed around explicit writes.

1. Run a dry run before applying.
2. Use `--apply --confirm-course COURSE_ID` only when you are ready to write.
3. Read the printed course name and ID before writing.
4. Pull before editing a course you have not touched recently.
5. Use `find_page.py` or `course_inventory.py` before editing module pages.
6. Prefer `push_module_page.py` for active course pages.
7. Preview pages that include iframes, scripts, video embeds, or complex layout.
8. Keep `.env` local.
9. Never commit `pages/`, `backups/`, `canvas_files/`, `reports/`, `manifest.json`, `asset_manifest.json`, `preview_config.json`, `.env`, or `.venv`.
10. Do not rerun create commands after a timeout until you inspect Canvas.
11. Coordinate with teammates so two people do not push the same page at the same time.
12. Published Canvas pages update immediately for students.

## Recovery and Troubleshooting

### “My pull stopped because of local edits”

The script is protecting your work. Copy your changes somewhere safe, compare with Canvas, then decide whether to merge or use:

```bash
python scripts/pull_pages.py --overwrite-local
```

The overwrite path backs up previous local content first.

### “Canvas changed since my last pull”

The push script detected a stale local baseline. Pull again, compare the live content with your local edit, merge deliberately, then rerun the push.

### “A create command timed out”

Inspect Canvas before rerunning. The server may have created the page, quiz, discussion, or upload even if your terminal did not receive the final response.

For interrupted quiz creation, check local recovery reports under `reports/quizzes/` if they were generated.

For interrupted discussion creation, check local recovery reports under `reports/discussions/` if they were generated.

### “The preview page is published”

CanvasDaemon protects a published preview page from overwrite. In Canvas, inspect the preview page and unpublish it, or create a fresh preview setup if needed.

### “The asset preview/upload changed an existing file”

By default, Canvas file uploads overwrite matching names. Use `--rename` to avoid overwriting:

```bash
python scripts/upload_canvas_file.py assets/image.png --rename --apply --confirm-course 12345
```

### “A page looks different in Canvas than locally”

Canvas sanitizes and renders HTML differently than a browser opening a local file. Use `preview_page_in_canvas.py` for Canvas-rendered QA.

### “The repo does not contain pages anymore”

Correct. The shared repo is a toolkit. Each teammate pulls their own course to generate their own local `pages/` and `manifest.json`.

## Recommended Team Practices

Use one folder per course:

```text
CanvasDaemon-course-a/
CanvasDaemon-course-b/
```

Do not share `.env` files. Each person should create their own token and configure their own course ID.

Use branches for reusable script or documentation changes. Do not commit local generated course exports.

Before a teammate starts a new course, they should:

1. Clone the repo.
2. Read this handbook.
3. Create `.env`.
4. Run `test_canvas.py`.
5. Pull their course.
6. Review `examples/templates/`.
7. Start with dry runs and previews.

When creating a new course from the reference library, agree on these details first:

- Course structure and module names.
- Page template choices.
- Image style.
- Where videos live.
- Which activities are embedded.
- Who owns each module.
- When a module is ready for Canvas publish review.

## Quick Start Checklist

```bash
git clone https://github.com/march-M-R/CanvasDaemon.git
cd CanvasDaemon
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python scripts/test_canvas.py
python scripts/pull_pages.py
python scripts/course_inventory.py
```

Then open:

```text
examples/templates/README.md
examples/templates/pages/
```

Pick a reference, adapt it, preview it, and push only with:

```bash
--apply --confirm-course YOUR_COURSE_ID
```
