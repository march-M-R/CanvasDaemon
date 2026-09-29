# CanvasDaemon Agent Instructions

Follow `docs/AI_HELPER_GUIDE.md` before editing this repository. In particular:

- Pull GitHub changes before editing when possible.
- Pull Canvas pages and file metadata before live course edits.
- Keep `.env`, generated `pages/`, manifests, backups, reports, and downloaded Canvas files out of Git.
- Put reusable examples in `examples/templates/`; put course work in generated local folders.
- Upload local page assets to Canvas Files and rewrite links before production pushes.
- Preserve the `--apply --confirm-course COURSE_ID` safety gate on every Canvas-writing script.
- Run `python -m unittest discover -s tests -v` before committing script changes.

- When running `scripts/review_course_content.py`, fix or report automated findings. Use the generated content-accuracy checklist to organize human review, but do not mark checklist items complete without human approval.
