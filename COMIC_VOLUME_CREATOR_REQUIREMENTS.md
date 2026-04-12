# Comic Volume Creator — Requirements

## Overview

Comic Volume Creator is a web-based tool for scanning comic collections and merging individual numbered comic files (.cbz, .cbr) into consolidated volumes. It automates the process of detecting related issues, proposing volume names, and creating merged archives.

---

## Functional Requirements

### FR1: Folder Scanning
- **Scan source directory** for comic files (.cbz, .cbr, .zip, .rar)
- **Detect individual numbered issues** (files matching patterns like "Series 001.cbr", "Series #023.cbz")
- **Group files by series name** using intelligent regex extraction
- **Extract metadata** (series name, issue number, publication year, subtitles)
- **Identify existing volumes** to avoid re-merging (patterns: v01, Vol.2, Book 1, TPB, Omnibus, etc.)
- **Handle deep folder structures** (support up to 2 levels of nesting)
- **Report skipped folders** that contain sub-subfolders (require manual intervention)

### FR2: Series Classification
- **Classify by file count**:
  - Flag **Y** = 4–6 files (ready to merge)
  - Flag **S** = <4 files (small series)
  - Flag **M** = >6 files (large volume, candidate for splitting)
- **Auto-detect existing volumes** and suggest next volume number (v01 → v02, v03, etc.)
- **Extract year information** from filenames and use highest year in volume name
- **Extract and preserve subtitles** (e.g., "Series 001 - Story Arc Name")

### FR3: Single Volume Creation
- **Create CBZ volumes** by:
  1. Extracting each source file to isolated subfolder
  2. Zipping them together (preserving folder structure for reading order)
  3. Moving final CBZ to destination
  4. Deleting original source files
  5. Cleaning up working directories
- **User-editable output names** before confirming merge
- **Dry-run capability** to preview what would happen without executing
- **Robust error handling** with automatic cleanup on failure

### FR4: Split Large Volumes
- **Enable splitting for M-flag rows** (>6 files)
- **Manual file selection** via checkboxes
- **Per-file volume assignment** (select files → assign to v01, v02, v03, etc.)
- **Smart volume numbering** (detect existing volumes, auto-suggest next)
- **Auto-suggest splits** (balanced distribution: 15 files → 3×5 files, etc.)
- **Volume preview panel** showing proposed volumes and file counts
- **Batch creation** of split volumes via sequential API calls

### FR5: Filtering & Search
- **Status filter**: Ready (Y/M), CBZ exists, Single file
- **Flag filter**: Y, S, M, or all
- **Series search** by name (case-insensitive substring match)
- **Multi-filter combinations** (e.g., "Ready" + "Flag M")

### FR6: Bulk Operations
- **Row-level checkboxes** for multi-select
- **Bulk actions**: Create Selected CBZs, Dry Run
- **Select All / Deselect All** buttons
- **Selection counter** badge in toolbar

### FR7: Console Output
- **Real-time progress logging** for merge operations
- **Color-coded messages**:
  - Green (✔) = success
  - Red (✖) = error
  - Blue (ℹ) = information
  - Orange (⚠) = warning
- **Expandable/collapsible console panel** (fixed at bottom)
- **Stream log lines** with small delays for readability

### FR8: Settings & Personalization
- **Theme selection** (10 built-in themes: Midnight Blue, Dark Crimson, Forest, Amber, Ocean, Slate, Purple Night, Nord, Light, Sepia)
- **Font size adjustment** (small, medium, large)
- **Table density control** (compact, normal, relaxed)
- **Persist settings** to browser localStorage

### FR9: Help & Documentation
- **In-app help modal** (❓ button) with:
  - Quick start guide
  - Flag legend
  - Feature explanations
  - Keyboard shortcuts
  - Troubleshooting tips
- **Accessible via Escape key**

---

## Non-Functional Requirements

### Performance
- **Scan response** <5 seconds for typical collections (100-500 folders)
- **Table rendering** smooth with 100+ rows
- **File selection** in split panel responsive even with 20+ files
- **Merge operations** use system commands (unrar, unzip, zip) for efficiency

### Reliability
- **Atomic operations**: No partial merges; original files kept until CBZ fully created
- **Automatic cleanup** on failure (working folders removed, original files preserved)
- **Crash resilience**: Browser reload recovers state (filters, selections reset but no data loss)

### Usability
- **Responsive layout** (grid-based split panel, scrollable lists)
- **Color-blind friendly** (uses shape/text + colour for status indicators)
- **Keyboard support** (Escape, Enter in path field, Enter in dialogs)
- **Intuitive feedback** (toasts for errors, console for detailed logs)

### Security
- **No credential storage** (file paths only)
- **Local API only** (server runs on localhost:8765)
- **Path validation** (reject invalid directories before attempting scan)
- **Subprocess safety** (proper quote handling, no shell injection)

### Maintainability
- **Modular JS architecture** (separate functions for UI, API, state)
- **CSS custom properties** for theming
- **Clear variable naming** (splitMode, splitState, currentFilter, etc.)
- **Documented API endpoints** (/api/scan, /api/create)

---

## Use Cases

### UC1: New Comic Collector
User has 50 downloaded comic issues for a series and wants to organize them into a single volume.

**Flow**: Scan → filter status="Ready" → click "Create" → confirm → wait for console → done.

### UC2: Large Collection Curation
User has a folder with 200+ comics from multiple series, varying file counts. Wants to batch-process all "ready" series at once.

**Flow**: Scan → filter flag="Y" → Select All → Dry Run (preview) → Create Selected CBZs.

### UC3: Complex Split
User has a 30-issue series that should be split into 3 volumes (issues 1–10, 11–20, 21–30).

**Flow**: Scan → click "Split" on M-flag row → manually check files 1–10 → assign v01 → check files 11–20 → assign v02 → check files 21–30 → assign v03 → Create Volumes.

### UC4: Incremental Merging
User adds new issues to an existing series weekly and wants to keep creating new volumes (v02, v03, etc.) without touching v01.

**Flow**: Scan (detects v01 exists) → Create (auto-suggests v02 for new files) → confirm → done.

---

## Out of Scope

- **Comic metadata enrichment** (no OMDB/comicvine integration)
- **Manual metadata editing** (series name, year extracted from filename only)
- **Cloud storage support** (local filesystem only)
- **Multi-user access control** (designed for single-user localhost server)
- **Undo/revert operations** (no archive of merged files; user keeps originals if needed)
- **Comic reader integration** (server only hosts web UI, no comic viewing)
- **Advanced scheduling** (no recurring scans or background tasks)

---

## Constraints

- **Requires system tools**: `unrar`, `unzip`, `zip` must be installed
- **Single merge at a time**: Sequential processing (no parallel merges)
- **Folder structure limit**: Scans max 2 levels deep (current dir + 1 subfolder level)
- **Volume naming**: Always includes series name + volume number (v01, v02, etc.) + year
- **File deletion**: Source files deleted after successful merge (irreversible)

---

## Success Metrics

1. **Merge success rate** ≥99% (only fails on unrecoverable system errors)
2. **Average scan time** <3 seconds per 100 folders
3. **User can complete bulk merge** of 10 series in <2 minutes (UI + execution)
4. **Zero accidental file loss** (atomic operations, automatic cleanup on failure)
