# Copilot Instructions for CanvasDaemon

Read and follow `docs/AI_HELPER_GUIDE.md`.

Key rules: keep secrets and generated course files out of Git; use `assets/` for local media before Canvas upload; use `scripts/prepare_page_assets.py` to upload local page assets and produce Canvas-linked HTML; preserve `--apply --confirm-course COURSE_ID` on all Canvas-writing scripts; run the offline unittest suite before committing script changes.

If you run `scripts/review_course_content.py`, handle automated findings and preserve the content-accuracy checklist as a human approval checklist. Do not claim content accuracy is complete without human review.
