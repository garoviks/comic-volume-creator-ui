# Comic Volume Creator — Architecture

## System Overview

Comic Volume Creator is a **client-server web application** for batch processing comic files:

```
┌─────────────────────┐
│   User Browser      │
│ (comic_volume_      │
│  creator_mockup.    │
│  html)              │
│                     │
│  • UI Components    │
│  • State Management │
│  • Theme Engine     │
│  • API Calls        │
└──────────┬──────────┘
           │
        (HTTP)
           │
┌──────────▼──────────────────┐
│ Python HTTP Server          │
│ (comic_volume_creator_      │
│  server.py)                 │
│                             │
│  POST /api/scan         ◄──┼──► Filesystem scan
│  POST /api/create       ◄──┼──► CBZ merge (unrar, unzip, zip)
│  GET  /index.html       ◄──┼──► Serve HTML
│                             │
│  • JSON API                 │
│  • Path validation          │
│  • Process management       │
│  • Error handling           │
└─────────────────────────────┘
```

---

## Technology Stack

### Backend
- **Language**: Python 3.8+
- **Web Framework**: `http.server.BaseHTTPRequestHandler` (built-in stdlib)
- **File Operations**: `os`, `shutil`, `re`
- **Subprocess Control**: `subprocess` (unrar, unzip, zip)
- **Data Format**: JSON (request/response bodies)

### Frontend
- **Markup**: HTML5
- **Styling**: CSS3 with custom properties (CSS variables for theming)
- **Scripting**: Vanilla JavaScript (ES6+, no frameworks)
- **Storage**: Browser `localStorage` (settings persistence)
- **Protocols**: HTTP/1.1 (REST-style API, no WebSockets)

### Dependencies
- System: `unrar`, `unzip`, `zip`
- Python: Standard library only (no pip requirements)
- Browser: Modern ES6 support (Chrome 51+, Firefox 54+, Safari 10+, Edge 15+)

---

## Data Flow

### Scan Flow

```
User enters path
        ↓
POST /api/scan {"path": "/path/to/comics"}
        ↓
Server: scan_root()
  • Recursively walk directory (max 2 levels)
  • For each folder: scan_single_folder()
    - List .cbz/.cbr files
    - Filter: detect numbered issues (regex: 0\d|00\d)
    - Filter: exclude existing volumes (regex: v\d+, vol\d+, book\d+, etc.)
    - Group by series name (regex: extract series from filename)
    - Calculate flags (S|Y|M based on file count)
    - Detect existing volumes, suggest next vNN
  • Collect skipped folders (those with sub-subfolders)
        ↓
Response: JSON
{
  "results": [
    {
      "id": 0,
      "folder": "/path/to/series",
      "series": "Series Name",
      "files": ["file1.cbr", "file2.cbr", ...],
      "flag": "M",
      "status": "ready",
      "outname": "Series Name v02"
    },
    ...
  ],
  "skipped": [
    {"path": "/path/with/subfolders", "subcount": 5},
    ...
  ]
}
        ↓
Browser: renderTable()
  • Populate table rows with results
  • Update stats bar (counts by flag/status)
  • Show skipped folders panel
```

### Create Flow (Single or Split)

```
User clicks "Create" or "Create Volumes"
        ↓
Browser validates + prepares request
        ↓
POST /api/create {
  "folder": "/abs/path",
  "files": ["file1.cbr", "file2.cbr", ...],
  "outname": "Series Name v01"
}
        ↓
Server: create_cbz_direct()

[1] Create working folder: working_dir = {outname}/
[2] Extract each file
    for each file:
      • Determine ext (.cbr vs .cbz)
      • Create subfolder: working_dir/{filename_stem}/
      • Run: unrar e -o+ file.cbr working_dir/{stem}/
             OR unzip -o -q file.cbz -d working_dir/{stem}/
[3] Zip working folder
    cwd = working_dir
    zip -r {outname}.cbz .
    (Result: working_dir/{outname}.cbz)
[4] Move to destination
    shutil.move(working_dir/{outname}.cbz, {folder}/{outname}.cbz)
[5] Delete source files
    for each file in files:
      os.remove({folder}/{file})
[6] Cleanup
    shutil.rmtree(working_dir)
        ↓
Response: JSON
{
  "success": true,
  "log": "[1/6] ...\n  ✔ ...\n[2/6] ...\n...",
  "cbz_name": "Series Name v01.cbz"
}
        ↓
Browser: doConfirmedCreate() or createSplitVolumes()
  • Stream log lines to console (18ms delay per line)
  • On success: remove row from table, update stats
  • On failure: keep row, log errors
```

---

## Component Architecture

### Backend Components

#### 1. **comic_volume_creator_server.py**

**Utility Functions:**
- `is_volume(name)` — detect if filename is already a volume
- `extract_series(filename)` — strip issue number, get bare series name
- `extract_year(filename)` — extract 4-digit year
- `is_numbered_issue(filename)` — detect individual issues (not volumes)
- `get_next_volume_number(folder, series)` — scan for vNN, return max+1

**Scan Logic:**
- `scan_single_folder(folder)` — group files by series, return {series: {files, years}}
- `has_subdirs(path)` — check if path has subdirectories
- `scan_root(root_path)` — orchestrate full scan, return (results, skipped)

**CBZ Creation:**
- `create_cbz_direct(abs_path, files, outname)` — 6-step merge process

**HTTP Handler:**
- `Handler` class extending `BaseHTTPRequestHandler`
- `do_GET()` — serve index.html
- `do_POST()` — handle /api/scan and /api/create
- `send_json()` — format JSON responses
- `read_json_body()` — parse POST bodies

#### 2. **Key Algorithms**

**Series Extraction (action_explorer approach):**
```python
name = re.sub(r'\.(cbz|cbr)$', '', filename)
match = re.match(r'^(.*?)(?:\s+(?:#?\d+|\(\d{1,3}\))(?:\s*\(of\s*\d+\))?)', name)
series = match.group(1).strip() if match else name
```
Handles: `Series 001`, `Series #001`, `Series (001)`, `Series 001 (of 5)`, etc.

**Volume Detection:**
```python
VOLUME_PATTERN = r'\b(?:v|vol|book|t)\.?\s*\d+|TPB|Omnibus|Collection|...'
```
Catches: v01, vol.2, Vol 3, Book 1, T1, TPB, Omnibus, Graphic Novel, HC, Complete

**Flag Calculation:**
```python
file_count = len(files)
if file_count > 6:    flag = 'M'  # large volume
elif file_count < 4:  flag = 'S'  # small series
else:                 flag = 'Y'  # ready (4-6 files)
```

**Volume Number Detection:**
```python
pattern = re.compile(r'^' + escaped_series + r'.*\bv(\d+)\b.*\.cbz$', re.IGNORECASE)
max_vol = max of all captured group(1) integers, or 0 if none found
next_vol = max_vol + 1
```

### Frontend Components

#### 1. **State Management**

```javascript
let data = [];              // [{id, folder, series, files, flag, status, outname}, ...]
let expanded = new Set();   // row IDs with expanded file lists
let selected = new Set();   // row IDs with checkboxes checked
let splitMode = null;       // ID of row currently in split edit mode
let splitState = {};        // {rowId: {fileAssignments: {filename: 'v01'}, ...}}
let currentFilter = 'all';
let currentFlagFilter = 'all';
let currentSearch = '';
```

#### 2. **Core Functions**

**Data Loading:**
- `scanFolders()` — POST /api/scan, update data[], renderTable()
- `updateStats(results, skipped)` — refresh stat badges
- `renderSkipped(skipped)` — render skipped folders panel

**Rendering:**
- `renderTable()` — apply filters, render main rows + file subrows + split panel
- `renderSplitPanel(row)` — generate HTML for split editing UI
- `statusBadge(s)`, `flagBadge(f)` — format status/flag display

**Filtering:**
- `filterTable()` — read select values, apply filters, re-render
- `searchTable(val)` — update currentSearch, re-render
- `updateSelBadge()` — show/hide "N selected" badge

**Split Volumes:**
- `toggleSplitPanel(id)` — open/close split edit for row
- `updateSplitPreview(id)` — refresh volume assignments, auto-suggest next vol
- `assignVolumeToSelected(id)` — batch assign files to volume
- `suggestSplit(id)` — auto-balance files into volumes
- `createSplitVolumes(id)` — POST /api/create for each volume sequentially

**Create Operations:**
- `createOne(id)` — open confirm dialog for single volume
- `doConfirmedCreate()` — POST /api/create, stream log to console
- `createSelected()` — POST /api/create for each selected row
- `dryRunOne(id)`, `dryRun()` — preview without executing

**UI Interaction:**
- `openSettings()`, `closeSettings()` — theme/density panel
- `openHelp()`, `closeHelp()` — help modal
- `applyTheme(id)` — update CSS variables, save to localStorage
- `setFontSize(size)`, `setDensity(density)` — adjust layout
- `toggleConsole()` — show/hide console panel
- `addLog(msg, cls)` — stream message to console

#### 3. **CSS Architecture**

**Theming:**
```css
:root {
  --bg: #121212;
  --accent: #e94560;
  --text: #e0e0e0;
  /* ... 20+ color variables */
}
```
Themes defined as JavaScript objects mapping var names → hex values. On theme change, all variables updated via `document.documentElement.style.setProperty()`.

**Layout:**
- **Header**: Flexbox row (title + buttons)
- **Folder bar**: Flexbox row (label + input + buttons)
- **Stats bar**: Flex row with dividers
- **Toolbar**: Flex row (filters on left, actions on right)
- **Table**: CSS `border-collapse`, responsive columns
- **Split panel**: CSS Grid (3 columns: files, control, preview)
- **Console**: Fixed position bottom, collapsible

---

## API Specification

### POST /api/scan

**Request:**
```json
{
  "path": "/absolute/path/to/comics"
}
```

**Response (200):**
```json
{
  "results": [
    {
      "id": 0,
      "folder": "/path/to/series1",
      "series": "Series Name",
      "files": ["001.cbr", "002.cbr"],
      "flag": "Y",
      "status": "ready",
      "outname": "Series Name v01 (2020)"
    }
  ],
  "skipped": [
    {
      "path": "/path/with/subfolders",
      "subcount": 5
    }
  ]
}
```

**Response (400/500):**
```json
{
  "error": "Path not found or not a directory: ..."
}
```

### POST /api/create

**Request:**
```json
{
  "folder": "/abs/path/to/series",
  "files": ["001.cbr", "002.cbr", "003.cbr"],
  "outname": "Series v01"
}
```

**Response (200):**
```json
{
  "success": true,
  "log": "[1/6] Working folder\n  ✔ Created: ...\n[2/6] ...\n...",
  "cbz_name": "Series v01.cbz"
}
```

**Response (500, on failure):**
```json
{
  "success": false,
  "log": "[1/6] ...\n  ✖ ...\n[cleanup] Removing working folder...",
  "cbz_name": "Series v01.cbz"
}
```

---

## Error Handling & Resilience

### Backend Resilience

1. **Path Validation**: Check `os.path.isdir()` before scanning
2. **Atomic Merge**: All steps in try/except; on error:
   - Log error message
   - Delete working folder (cleanup)
   - Return `(False, log)` — originals untouched
3. **Subprocess Safety**:
   - Validate file paths (no `..` sequences)
   - Quote command arguments
   - Capture stderr for logging
   - Check return codes

### Frontend Resilience

1. **Network Errors**: Catch `fetch()` errors → display "Network error" in console
2. **Invalid Input**: Alert user before API call (empty volume name, no files selected)
3. **State Recovery**: Filters/selections reset on reload; original data can be re-scanned
4. **Optimistic UI**: Row disappears after successful merge (can re-scan to confirm)

### Data Integrity

- **No partial merges**: Working folder cleaned up even if zip partially fails
- **Original files preserved** on merge failure
- **Idempotent operations**: Re-running scan is safe (no file modification)
- **Atomic file deletion**: Only delete originals after CBZ fully written and moved

---

## Performance Considerations

### Scan Performance
- **Linear with folder count**: O(n) directory traversal
- **Regex matching**: O(k) per filename (k = string length)
- **Overall**: <5s for 500 folders (typical SSD)

### UI Performance
- **Lazy rendering**: Only visible table rows rendered initially
- **Debounced filtering**: Search updates on input (no per-keystroke re-render)
- **Scrollable lists**: Split panel file list capped at 300px height
- **Async logging**: Console lines streamed with 18ms delays (non-blocking)

### Merge Performance
- **Subprocess I/O**: Limited by disk speed (main bottleneck)
- **Sequential processing**: Simpler error handling than parallel
- **Per-file subfolders**: Prevents page naming collisions between issues

---

## Known Limitations

1. **Folder depth**: Only scans 2 levels (cwd + subfolders)
2. **Volume numbering**: Auto-detection assumes patterns like "Series v01.cbz" (not flexible for custom naming)
3. **No concurrent merges**: Sequential processing only (one /api/create at a time)
4. **File deletion**: Irreversible after successful merge
5. **No metadata editing**: Series/year extracted from filename only
6. **System dependency**: Requires unrar, unzip, zip on PATH

---

## Future Enhancements

- **Parallel merges** (ThreadPoolExecutor for /api/create)
- **Undo support** (archive original files in shadow folder)
- **Custom volume naming** (templates like `{series}__{year}__v{num}`)
- **Batch scanning** (queue multiple /api/scan requests)
- **WebSocket support** (real-time log streaming instead of polling)
- **Database integration** (PostgreSQL for merge history, deduplication)
- **Docker deployment** (containerized server, simplified setup)
