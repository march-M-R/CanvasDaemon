# CanvasDaemon

Canvas LMS automation for curriculum teams. Edit course content locally, review it in Canvas, and apply deliberate changes using the existing scripts.

This is the **V1 maintenance update (0.2.0)**. It keeps the established course content and visual style. The separate V2 experiment and its new example imagery are not part of this release.

## Handbook

Start with the setup guide if you are configuring CanvasDaemon for the first time, then use the teammate handbook for the full navigation, workflow, and script guide:

- [Setup guide — Markdown](docs/SETUP.md)
- [Setup guide — HTML](docs/SETUP.html)
- [Handbook — Markdown](docs/HANDBOOK.md)
- [Handbook — HTML](docs/HANDBOOK.html)
- [AI helper guide — Markdown](docs/AI_HELPER_GUIDE.md)
- [AI helper guide — HTML](docs/AI_HELPER_GUIDE.html)

## Setup

Use Python 3.10 or newer with a current OpenSSL build. From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows, use `py -m venv .venv` and `.venv\Scripts\Activate.ps1`; copy `.env.example` to `.env` in your editor. Set your Canvas HTTPS origin, personal token, and course ID locally. Never paste tokens into chat or commit them. Explicit shell variables take precedence over this checkout's `.env`; a parent folder's `.env` is not discovered.

```bash
python scripts/test_canvas.py
```

Check the printed course name and ID before continuing. This command is read-only.

## Daily page workflow

```bash
python scripts/pull_pages.py
python scripts/course_inventory.py
python scripts/find_page.py "lesson title"
python scripts/push_page.py "your-page-filename.html"
python scripts/push_page.py "your-page-filename.html" --apply --confirm-course 12345
```

Replace `12345` with your configured course ID. Edit the file identified in `manifest.json` before running `push_page.py`.

Pull downloads and checks all pages before replacing local files. Unpushed edits stop the pull. Preserve and merge those edits; use `--overwrite-local` only when you deliberately want a backed-up replacement. Backups now contain the **previous local content**, not another copy of the newly downloaded content.

Push displays a diff, detects remote changes since pull, and backs up the live page before writing. An update preserves publication status, so changing an already-published page is immediately student-facing. Older manifests use the last Canvas update timestamp until a successful pull/push records a body hash. Entries with no baseline must be pulled before applying.

## Every Canvas write is explicit

All write entrypoints default to a dry run. Apply requires both `--apply` and `--confirm-course ID`. This is an intentional command-line change from earlier V1 scripts.

```bash
python scripts/create_page.py "Lesson title" --body-file lesson.html
python scripts/create_page.py "Lesson title" --body-file lesson.html --apply --confirm-course 12345
python scripts/add_page_to_module.py "your-page-filename.html" "Module title" --apply --confirm-course 12345
python scripts/upload_canvas_file.py assets/image.png --rename --apply --confirm-course 12345
python scripts/create_classic_quiz.py quiz_banks/example.json --apply --confirm-course 12345
python scripts/create_discussion.py "Discussion title" --message-file discussion.html --apply --confirm-course 12345
```

Commands validate configuration even in dry-run mode; they may read Canvas to resolve existing resources. Create operations can still produce duplicates if rerun after an uncertain network failure. Inspect Canvas first. Quiz/discussion creation records the new identity before subsequent steps so partial completion can be investigated. Reattaching the same page to a module is a no-op.

Uploads retain the original overwrite behavior unless `--rename` is supplied. Folder IDs are checked against the configured course. Upload storage receives no Canvas token; only validated Canvas confirmation URLs receive it.

## Canvas previews

```bash
python scripts/setup_preview_environment.py --apply --confirm-course 12345
python scripts/preview_page_in_canvas.py "your-page-filename.html" --apply --confirm-course 12345
python scripts/preview_asset_in_canvas.py assets/image.png --apply --confirm-course 12345
```

Omit the two apply flags to inspect without writing. Preview configuration is bound to its course, and a published preview page is protected from overwrite. Use `--no-open` to avoid opening a browser. Actual Canvas rendering and student access still require review.

## Available scripts

| Workflow | Scripts |
|---|---|
| Read and find pages | `pull_pages.py`, `list_pages.py`, `list_module_pages.py`, `course_inventory.py`, `find_page.py`, `find_any_page.py` |
| Create/update pages and modules | `create_module.py`, `create_page.py`, `push_page.py`, `push_module_page.py`, `add_page_to_module.py` |
| Files and images | `pull_files_metadata.py`, `find_asset.py`, `upload_canvas_file.py`, `prepare_page_assets.py`, `download_editable_files.py`, `download_referenced_editable_files.py` |
| Classic Quizzes | `create_classic_quiz.py`, `pull_classic_quizzes.py`, `find_quiz.py`, `sync_classic_quiz.py` |
| Discussions | `create_discussion.py` |
| Video inventory | `discover_panopto.py` extracts Panopto references from local pages; it does not create videos |
| Previews | `setup_preview_environment.py`, `preview_page_in_canvas.py`, `preview_asset_in_canvas.py` |

`sync_classic_quiz.py` synchronizes **settings only**, not questions. It preserves publication status when `published` is omitted; an explicitly supplied value changes it. New quizzes are always created unpublished. Creation supports multiple choice, true/false, multiple answer, short answer, essay, and zero-point five-option survey items using the existing JSON format. New Quizzes are not supported. Review keys, points, feedback, and student-facing rendering before publication.

## Working on another course

This repository is now set up as a reusable toolkit. The old live course page exports, downloaded Canvas files, backups, and course manifests are not tracked at the branch tip. For another course, create your own `.env`, run the read-only connection check, then pull that course to generate a fresh local `pages/` folder and `manifest.json`.

The approved reference patterns live in [`examples/templates/`](examples/templates/README.md). Use one example of each kind as a starting point: course welcome, roadmap, resource hub, module overview, main lesson, microlearning page, embedded mini activity, tool setup, opening discussion, module summary, progress checklist, and quiz answer review.

Use `examples/templates/assets/m2_1_1_examples_patterns.png` as the image-style reference for new high-school course illustrations. The intended style is student-facing, classroom/story based, concrete, warm, and concept-driven. Replace videos, Canvas links, activity assets, and completion claims before publishing to a different course.

## Tests and maintenance

```bash
python -m unittest discover -s tests -v
```

Tests use temporary files and mocked HTTP responses. They do not contact Canvas. CI runs the same checks. This release has not been validated by writing to a live course.

See [CHANGELOG.md](CHANGELOG.md) for migration details, [docs/HANDBOOK.md](docs/HANDBOOK.md) for the full teammate guide, and [docs/V1_MAINTENANCE.md](docs/V1_MAINTENANCE.md) for limitations and recovery. The older [HTML runbook](CanvasDaemon_Runbook.html) remains useful background; the handbook and README take precedence for command flags.

## Credential history

The real `.env` is not tracked at the current branch tip, and the public branch history was rewritten to remove it from earlier commits. Keep `.env` local only, and rotate any credential that may have been exposed before the cleanup.
