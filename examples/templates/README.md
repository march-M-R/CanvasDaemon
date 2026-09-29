# Template Reference Library

These examples are the approved reference set for building another Canvas course with this repository. They are not live course exports to push unchanged. Treat each file as a pattern: copy the structure, replace the course-specific text, update links, and use the scripts from `scripts/` to publish to the target course.

## What is included

| Type | Reference |
|---|---|
| Course welcome | `pages/course-welcome.html` |
| Course roadmap | `pages/course-roadmap.html` |
| Orientation / resource hub | `pages/course-guide.html` |
| Module overview | `pages/module-overview.html` |
| Main lesson | `pages/main-lesson.html` |
| Quick concept / microlearning | `pages/quick-concept.html` |
| Embedded micro-learning mini activity | `pages/guided-activity.html` |
| Tool setup / recovery guide | `pages/tool-setup.html` |
| Opening discussion | `pages/opening-discussion.html` |
| Module summary with video | `pages/module-summary.html` |
| Interactive progress checklist | `pages/progress-checklist.html` |
| Quiz answer review | `pages/answer-review.html` |

`metadata/template-library.json` records the original source, adaptation notes, image dependencies, and embed counts for each reference.

## Image style reference

Use `assets/m2_1_1_examples_patterns.png` as the visual style reference for new course illustrations: student-facing, high-school setting, concrete learning metaphor, warm classroom energy, and clear connection to the concept being taught.

Avoid abstract futuristic dashboard imagery unless the page specifically calls for that visual language. The reusable course style should feel like high-school students working through AI ideas with familiar objects, scenes, and visual jokes.

## How to use these examples

1. Start a fresh course workspace or clone of this repository.
2. Configure `.env` from `.env.example`.
3. Pull the target course with `python scripts/pull_pages.py`.
4. Copy the closest reference page into `pages/` under a new filename.
5. Replace titles, links, videos, activity assets, completion language, and any course-specific claims.
6. Preview or push with the guarded `--apply --confirm-course COURSE_ID` workflow.

Videos and Canvas file links in these examples may still point to the original course or require Stevens sign-in. Replace them before publishing to another course.
