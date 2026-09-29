# Changelog

## 0.2.4 — Process guide

- Added `docs/PROCESS_GUIDE.md` and `docs/PROCESS_GUIDE.html` documenting the full repo cleanup and toolkit preparation process.
- Linked the process guide from `README.md` for teammates and future maintainers.

## 0.2.3 — AI helper and page asset workflow

- Added repo instructions for AI coding helpers through `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/canvasdaemon.mdc`, and `docs/AI_HELPER_GUIDE.md`.
- Added `scripts/prepare_page_assets.py` to find local asset references in a page, upload those assets to Canvas Files, and write a Canvas-linked HTML copy.
- Added regression tests for page asset collection and link rewriting.
- Updated README, setup guide, and handbook to include the AI-helper and asset-preparation workflows.

## 0.2.2 — Module creation workflow

- Added `scripts/create_module.py` for guarded Canvas module creation with dry-run default, duplicate-name protection, optional position, publishing, unlock date, sequential progress, and prerequisite module IDs.
- Added regression tests for module creation dry runs, duplicate detection, and payload construction.
- Updated README, setup guide, and handbook to document module creation.

## 0.2.1 — Teammate handbook

- Add a detailed teammate handbook in Markdown and HTML.
- Document setup, repository navigation, template use, page workflows, file/image workflows, preview workflows, discussions, Classic Quizzes, Panopto discovery, script capabilities, safety rules, recovery, and team practices.
- Link the handbook from the README.

## 0.2.0 — V1 maintenance

- Preserve existing script entrypoints, course content, and course imagery.
- Add a shared runtime for explicit checkout configuration, HTTPS validation, timeouts, and protected credential routing.
- Default every Canvas write command to dry-run; require `--apply --confirm-course ID` to write.
- Protect local page edits during pull; preflight downloads before replacing content; back up previous local files.
- Detect remote page changes before push and update the synchronization baseline afterward.
- Bind page, preview, and upload manifests to their course.
- Fix signed upload/confirmation handling and prevent forwarding Canvas tokens to external storage.
- Paginate page listing, detect repeated pagination URLs, and make the connection check safe to import.
- Validate quiz questions before creating a quiz; retain new quiz/discussion identities for interrupted-run recovery.
- Preserve quiz publication status on settings updates unless explicitly specified; create new quizzes unpublished.
- Avoid duplicate page placements and protect published preview pages.
- Add dependencies, environment example, regression tests, and CI.
- Remove the tracked `.env` from the current tree. The public branch history was later rewritten to remove the exposed `.env` from earlier commits.

### Migration

Add `--confirm-course ID` to existing `--apply` commands. Commands that previously wrote immediately now require both flags. Read the README before rerunning an older runbook command. Old page manifests remain usable when they include a last-update timestamp; fresh pulls add stronger body hashes. Course-specific untracked scripts are outside this maintenance release and may still use earlier conventions.
