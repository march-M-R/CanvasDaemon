# CanvasDaemon

Canvas LMS automation toolkit for curriculum teams, instructional designers, and AI-assisted course development.

CanvasDaemon provides a local-first workflow for building, previewing, and managing Canvas content safely.

## Core Workflow

```text
Edit Locally
      ↓
Preview in Canvas
      ↓
Validate Rendering
      ↓
Push to Production
```

## Features

### Page Management

* Pull Canvas pages into local files
* Search active module pages
* Search all pages
* Safe page updates
* Automatic backups before push
* Dry-run deployment workflow

### Asset Management

* Pull Canvas file inventory
* Search Canvas assets
* Download referenced editable files
* Canvas-native asset preview

### Quiz Management

* Create Classic Quizzes from JSON
* Inventory existing quizzes
* Search quizzes
* Synchronize quiz settings
* Version-control quiz definitions

### Preview Environment

CanvasDaemon includes a dedicated Canvas preview system.

```text
Local HTML
      ↓
Preview Page
      ↓
Actual Canvas Rendering
```

This makes it possible to validate Canvas behavior before updating production pages.

## Major Components

### Pages

* pull_pages.py
* find_page.py
* find_any_page.py
* push_page.py
* push_module_page.py

### Assets

* pull_files_metadata.py
* find_asset.py
* download_referenced_editable_files.py

### Quizzes

* create_classic_quiz.py
* find_quiz.py
* sync_classic_quiz.py

### Preview System

* setup_preview_environment.py
* preview_page_in_canvas.py
* preview_asset_in_canvas.py

## Documentation

Open:

CanvasDaemon_Runbook.html

for the complete interactive project guide.

## Current Version

v0.1.0

Implemented:

* Page automation
* Asset automation
* Quiz automation
* Canvas preview environment
* Inventory and reporting workflows

Planned:

* Quiz question synchronization
* Panopto integration
* Unified daemon CLI
* Web interface
