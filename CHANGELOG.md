# Changelog

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
- Remove the tracked `.env` from the current tree. Historical credentials still require owner remediation.

### Migration

Add `--confirm-course ID` to existing `--apply` commands. Commands that previously wrote immediately now require both flags. Read the README before rerunning an older runbook command. Old page manifests remain usable when they include a last-update timestamp; fresh pulls add stronger body hashes. Course-specific untracked scripts are outside this maintenance release and may still use earlier conventions.
