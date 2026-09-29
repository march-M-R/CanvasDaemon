# AI Helper Guide for CanvasDaemon

This file tells coding assistants such as Codex, GitHub Copilot, Cursor, Claude Code, and similar tools how to work in this repository safely.

## Start Every Work Session by Getting Changes First

Before editing repository files, get the latest GitHub changes:

```bash
git pull --ff-only
```

If the branch has local work, inspect it before pulling:

```bash
git status --short --branch
git diff --stat
```

Before editing live Canvas content, get the latest Canvas state:

```bash
python scripts/test_canvas.py
python scripts/pull_pages.py
python scripts/pull_files_metadata.py
python scripts/course_inventory.py
python scripts/review_course_content.py
python scripts/audit_course_readiness.py
python scripts/review_course_toolkit.py --check-history
```

`push_page.py` also checks whether Canvas changed since the last pull and refuses to overwrite stale content. If it refuses, pull fresh content, merge carefully, preview again, and only then push.

## Repository Boundaries

This GitHub repo is the reusable toolkit. Do not commit course-specific generated output.

Commit these when useful:

- `scripts/`
- `tests/`
- `docs/`
- `examples/templates/`
- `.env.example`
- `README.md`
- `CHANGELOG.md`

Do not commit these:

- `.env`
- `.venv/`
- `pages/`
- `manifest.json`
- `backups/`
- `reports/`
- `canvas_files/`
- `asset_manifest.json`
- `preview_config.json`

## Where Things Go

Use this organization for course work:

| Item | Local Location | Canvas Destination |
|---|---|---|
| Page HTML pulled from Canvas | `pages/` | Canvas Pages |
| New reusable page template | `examples/templates/pages/` | Do not push unchanged |
| Course images and media before upload | `assets/` or course-specific subfolders under `assets/` | Canvas Files |
| Embedded activities such as standalone HTML widgets | `assets/activities/<module>/` locally | Canvas Files, then embedded by URL |
| Quiz banks | `quiz_banks/` | Classic Quizzes through `create_classic_quiz.py` |
| Local reports and generated rewritten pages | `reports/` | Not committed |
| Downloaded Canvas files | `canvas_files/` | Not committed |

Use descriptive filenames. Prefer stable names such as `m03-neural-network-card-sort.html` or `m05-training-data-example.png` over generic names such as `image1.png`.

## Required Canvas Write Pattern

Every script that writes to Canvas must require:

```bash
--apply --confirm-course COURSE_ID
```

Without those flags, commands must be dry runs or refuse to write. Do not add a new Canvas-writing script unless it uses `add_write_flags(parser)` and `authorize(args, BASE_URL, COURSE_ID)` from `scripts/canvas_runtime.py`.

## Page Workflow

1. Pull pages before editing:

   ```bash
   python scripts/pull_pages.py
   ```

2. Edit the local page in `pages/`.
3. If the page references local assets, prepare those assets:

   ```bash
   python scripts/prepare_page_assets.py pages/example.html
   python scripts/prepare_page_assets.py pages/example.html --apply --confirm-course 12345
   ```

   The dry run lists local assets. The apply run uploads assets to Canvas Files and writes a Canvas-linked copy in `reports/prepared_pages/` by default.

4. Preview the page in Canvas:

   ```bash
   python scripts/preview_page_in_canvas.py reports/prepared_pages/example.html --apply --confirm-course 12345
   ```

5. Push only after review:

   ```bash
   python scripts/push_page.py example.html --diff
   python scripts/push_page.py example.html --apply --confirm-course 12345
   ```

If using the rewritten page from `reports/prepared_pages/`, copy the reviewed HTML back into the matching `pages/` file deliberately before pushing.

## Asset Workflow

Use Canvas Files for images, downloadable files, and embedded HTML activities. Do not assume a local `src="assets/..."` path will work for students after the page is pushed to Canvas.

For one file:

```bash
python scripts/upload_canvas_file.py assets/image.png --folder "CanvasDaemon/module-03" --apply --confirm-course 12345
python scripts/pull_files_metadata.py
python scripts/find_asset.py "image.png"
```

For every local file referenced by one page:

```bash
python scripts/prepare_page_assets.py pages/example.html
python scripts/prepare_page_assets.py pages/example.html --folder "CanvasDaemon/module-03" --apply --confirm-course 12345
```

Then preview the rewritten HTML. Use `--rename` when you do not want to overwrite a matching Canvas filename.

## Module Workflow

Create missing modules before adding pages:

```bash
python scripts/create_module.py "Module 3: Building AI Systems"
python scripts/create_module.py "Module 3: Building AI Systems" --position 3 --apply --confirm-course 12345
```

Attach an existing page to a module:

```bash
python scripts/add_page_to_module.py "page-filename.html" "Module 3" --apply --confirm-course 12345
```

## Template Workflow

Use `examples/templates/` as patterns, not as pages to push unchanged. Replace:

- course title and module title
- dates, completion claims, and grading language
- Canvas links
- Panopto or video links
- image references
- embedded activity links
- institution-specific instructions

Use `examples/templates/assets/m2_1_1_examples_patterns.png` as the high-school visual style reference for new illustrations.

## Testing Before Sharing Changes

Run offline tests before committing toolkit changes:

```bash
python -m unittest discover -s tests -v
```

If you add or change a Canvas-writing script, add or update tests showing dry-run behavior and confirmation behavior.

## Good Helper Behavior

A helper should:

- Read `README.md`, `docs/SETUP.md`, `docs/HANDBOOK.md`, and this file before major edits.
- Pull GitHub changes before editing when network access is available.
- Pull Canvas pages and file metadata before touching live course content.
- Keep generated course files out of Git.
- Preview in Canvas before pushing production pages.
- Preserve the explicit write-confirmation guardrails.
- Explain exactly which files changed and which tests were run.
