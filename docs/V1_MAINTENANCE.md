# V1 maintenance and recovery

## Scope

This release polishes the 25 scripts already tracked in V1 and incorporates the current working improvements to page creation, page pushes/pulls, quiz content construction, and upload naming/folders. It adds one shared runtime, tests, setup documentation, and CI. It does not migrate the repository, replace its visual style, ship the separate V2 experiment, or import the many course-specific repair scripts.

## Interrupted writes

No write is automatically retried. A timeout can mean the server completed a request without returning the response. Inspect Canvas before rerunning a create or upload. For quizzes, `reports/quizzes/created-ID.json` distinguishes identity creation from completed question creation. For discussions, `reports/discussions/created-ID.json` preserves the identity before attachment. These reports are local recovery evidence, not transactional rollback.

## Conflicting page changes

Keep a copy of your edited HTML. Pull into a separate course working folder, compare the current live content, merge deliberately, and work from the refreshed manifest. Do not edit baseline hashes to suppress a conflict. `--overwrite-local` is only for intentionally replacing local content with a backed-up copy of live content.

Backups are in `backups/`. Before-push backups contain the live HTML and page metadata. Before-pull backups contain the previous local files and manifest. Restore an HTML body by copying it into the currently mapped file, review the diff, then push using the normal guarded workflow. Backups do not restore modules, student submissions, permissions, or an entire course.

## Preview and uploads

Use the dedicated unpublished preview page. If it has been published, inspect and unpublish it manually before reuse. Previewing an asset is itself an upload. Uploaded HTML/JavaScript may be downloaded or sanitized by Canvas; validate actual behavior and institutional hosting requirements. A local visual preview cannot prove Canvas rendering or student permission behavior.

File uploads overwrite matching names unless `--rename` is supplied, matching the prior workflow. Changing images can affect every page referencing a replaced file. The upload transport follows Canvas' signed multipart/confirmation protocol, scoped to the configured origin.

## Validation boundaries

Offline tests cover credentials and redirects, page conflicts and backup correctness, write confirmation, import side effects, quiz validation, duplicate module attachment, preview publication protection, and upload callbacks. They do not prove institution-specific Canvas behavior, accessibility, student access, or pedagogical quality. Try the documented workflow in an authorized test course before applying changes to students' content.

The shared runtime intentionally bounds requests with timeouts and does not auto-retry writes. It does not provide a server-side lock; coordinate simultaneous edits. Classic Quiz settings synchronization still does not replace questions. Automated assignment authoring and New Quizzes are outside V1's existing feature set.

## References

- [Canvas file uploads](https://developerdocs.instructure.com/services/canvas/basics/file.file_uploads)
- [Classic Quiz questions](https://developerdocs.instructure.com/services/canvas/resources/quiz_questions)
- [Canvas pages](https://developerdocs.instructure.com/services/canvas/resources/pages)

## Credentials

The old Git history includes a tracked `.env`. Removing it in this release prevents future checkout exposure at the branch tip but cannot revoke old credentials. Rotate the affected token through the institution's Canvas process. History rewriting is a separate coordinated task and was not performed.
