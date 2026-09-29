# CanvasDaemon Setup Guide

Use this guide when setting up CanvasDaemon for the first time on a new computer or for a new Canvas course. The setup is local-first: each teammate keeps their own Canvas token and course ID in a private `.env` file, then uses the shared scripts and templates from the repository.

## What You Need Before You Start

You need:

- Access to the GitHub repository.
- Python 3.10 or newer.
- A Canvas account with permission to edit the target course.
- A Canvas API token.
- The Canvas course ID for the course you want to work on.

Your Canvas API token and `.env` file are private. Do not share them and do not commit them to GitHub.

## 1. Clone the Repository

```bash
git clone https://github.com/march-M-R/CanvasDaemon.git
cd CanvasDaemon
```

If you already have the repository, update it before starting new work:

```bash
git pull
```

## 2. Create a Python Virtual Environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

When the virtual environment is active, your terminal prompt usually shows `(.venv)`.

## 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

If installation fails, check that your virtual environment is active and that your Python version is 3.10 or newer.

## 4. Create Your Private `.env` File

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in your Canvas information:

```bash
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_TOKEN=your-local-token
COURSE_ID=12345
```

Use the course ID from the Canvas course URL. If the URL contains `/courses/12345`, then your `COURSE_ID` is `12345`.

## 5. Get a Canvas API Token

In Canvas, go to your account settings and create a new access token. Copy it into `CANVAS_TOKEN` in your `.env` file.

Treat this token like a password. If you accidentally expose it, delete the token in Canvas and create a new one.

## 6. Test the Canvas Connection

Run the read-only connection check:

```bash
python scripts/test_canvas.py
```

Confirm that the printed Canvas course name and course ID match the course you intend to edit. Do not continue to write commands until this is correct.

## 7. Pull the Current Course Pages

After the connection test passes, pull the Canvas pages into local files:

```bash
python scripts/pull_pages.py
```

This creates local generated files such as:

- `pages/`
- `manifest.json`
- `backups/`

These are working files for your computer. They are ignored by Git and should not be committed.

## 8. Set Up a Canvas Preview Page

Create or reuse a dedicated preview page before pushing changes to real course pages:

```bash
python scripts/setup_preview_environment.py --apply --confirm-course 12345
```

Replace `12345` with your actual course ID. This script creates `preview_config.json`, which tells the preview scripts where to send draft previews.

## 9. Create a Module When Building a New Course

If your Canvas course does not already have the module you need, create it first:

```bash
python scripts/create_module.py "Module 1: Course Foundations"
```

This is a dry run. To actually create the module in Canvas, add explicit confirmation:

```bash
python scripts/create_module.py "Module 1: Course Foundations" --position 1 --apply --confirm-course 12345
```

Replace `12345` with your actual course ID. After creating the module, use `create_page.py` and `add_page_to_module.py` to add course content.

## 10. Preview a Local Page

Preview a local HTML page in Canvas before updating production content:

```bash
python scripts/preview_page_in_canvas.py pages/example.html --apply --confirm-course 12345
```

Open the preview page in Canvas and check layout, links, images, mobile behavior, and student readability.

## 11. Push a Page Only After Review

When a page is ready, compare it first:

```bash
python scripts/push_page.py pages/example.html --diff
```

Then push with explicit course confirmation:

```bash
python scripts/push_page.py pages/example.html --apply --confirm-course 12345
```

The write scripts require `--apply` and `--confirm-course` so you do not accidentally update the wrong course.

## 12. Use the Template Library

Reusable reference examples live in:

```text
examples/templates/
```

Start with `examples/templates/README.md` to see the approved examples for:

- Course welcome page
- Course roadmap
- Resource hub
- Module overview
- Main lesson
- Microlearning page
- Embedded mini activity
- Tool setup guide
- Opening discussion
- Module summary
- Progress checklist
- Quiz answer review
- Image style reference

Use these examples as patterns when creating course pages for a new class.

## 13. Run Local Tests

Before sharing changes with teammates, run the offline test suite:

```bash
python -m unittest discover -s tests -v
```

These tests do not contact Canvas. They check script behavior that can be validated locally.

## 14. Keep Secrets and Generated Files Out of Git

Do not commit:

- `.env`
- `.venv/`
- `pages/`
- `manifest.json`
- `backups/`
- `reports/`
- `canvas_files/`
- `asset_manifest.json`
- `preview_config.json`

These files are either private, generated, or course-specific.

## Quick Setup Checklist

- Clone the repo.
- Create and activate `.venv`.
- Install `requirements.txt`.
- Copy `.env.example` to `.env`.
- Add `CANVAS_BASE_URL`, `CANVAS_TOKEN`, and `COURSE_ID`.
- Run `python scripts/test_canvas.py`.
- Pull pages with `python scripts/pull_pages.py`.
- Create missing modules with `python scripts/create_module.py`.
- For pages with local images or activities, run `python scripts/prepare_page_assets.py pages/example.html` before preview/push.
- Set up preview with `setup_preview_environment.py`.
- Preview before pushing.
- Push only with `--apply --confirm-course COURSE_ID`.
