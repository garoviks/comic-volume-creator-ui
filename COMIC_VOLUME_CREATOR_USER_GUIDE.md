# Comic Volume Creator — User Guide

## Table of Contents
1. [Installation & Setup](#installation--setup)
2. [Quick Start](#quick-start)
3. [Understanding the Interface](#understanding-the-interface)
4. [Scanning Comics](#scanning-comics)
5. [Creating Single Volumes](#creating-single-volumes)
6. [Splitting Large Volumes](#splitting-large-volumes)
7. [Bulk Operations](#bulk-operations)
8. [Filters & Search](#filters--search)
9. [Settings & Customization](#settings--customization)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Installation & Setup

### Requirements
- **Python 3.8+** (Windows, macOS, or Linux)
- **System tools**: `unrar`, `unzip`, `zip`
- **Modern web browser** (Chrome, Firefox, Safari, Edge)
- **Comic files**: .cbz, .cbr, .zip, or .rar archives

### Step 1: Install System Tools

**macOS (using Homebrew):**
```bash
brew install unrar p7zip
```

**Ubuntu/Debian:**
```bash
sudo apt-get install unrar zip unzip
```

**Windows (using Chocolatey):**
```bash
choco install unrar 7zip
```

### Step 2: Start the Server

Navigate to the Comic Volume Creator folder:
```bash
cd /path/to/comic_volume_creator_server.py
python3 comic_volume_creator_server.py
```

You should see:
```
Comic Volume Creator — http://localhost:8765/
Serving: /path/to/comic_volume_creator_mockup.html
Press Ctrl-C to stop.
```

### Step 3: Open the Web Interface

Open your browser and go to:
```
http://localhost:8765/
```

You're ready to go!

---

## Quick Start

### 5-Minute Workflow

1. **Enter your source folder path** (top bar)
   - Example: `/home/user/Comics` or `C:\Users\user\Downloads\Comics`

2. **Click "🔍 Scan Folders"** (blue button)
   - Wait for scan to complete (see console for progress)

3. **Review results** in the table
   - Look at the **Flag** column (Y, S, or M)
   - **Y** = ready to merge (4–6 files)
   - **S** = small series (<4 files)
   - **M** = large volume (>6 files, may want to split)

4. **Create volumes**
   - **Single merge**: Click "✨ Create" on a row
   - **Bulk merge**: Check multiple rows → Click "✨ Create Selected CBZs"
   - **Split first**: For M-flag rows, click "Split" to divide into multiple volumes

5. **Check console** (click "🖥 Console" button, bottom-right)
   - Watch progress as files are extracted, zipped, and merged
   - Green ✔ = success, Red ✖ = error

6. **Done!**
   - Original files are deleted automatically after successful merge
   - New CBZ volumes appear in the same folder

---

## Understanding the Interface

### Header
```
Comic Volume Creator — Bulk CBZ Merger    [❓ Help] [⚙ Settings]
```
- **Left**: App title and description
- **Right**: Help (?) and Settings (⚙) buttons

### Folder Bar
```
📁 Source Root    [/path/to/comics]    [🔍 Scan Folders]
```
- **Input field**: Enter absolute path to your comics folder
- **Scan button**: Start scanning (or press Enter)

### Stats Bar
```
18 Ready (Y/M)  │  7 Small (S)  │  4 CBZ exists  │  6 Skipped folders  │  35 Total series found
```
- Live counts updated after each scan
- Helps you understand what you're working with

### Flag Legend
```
Y = 4–6 files (ready to merge)
S = <4 files (small series)
M = >6 files (large volume)
```

### Toolbar
```
[All statuses ▼] [All flags ▼] 🔍 Search...    ☑ Select All  ☐ Deselect All  📋 Dry Run  ✨ Create Selected CBZs
```
- **Filters**: Narrow down by status or flag
- **Search**: Find series by name
- **Bulk actions**: Select multiple rows, then bulk create or dry-run

### Main Table
| Checkbox | Expand | Folder / Series | Files | Flag | Status | Output Name | Actions |
|----------|--------|-----------------|-------|------|--------|-------------|---------|
| ☐ | ▶ | /path/Series | 6 | Y | Ready | Series v01 (2020).cbz | ✨ 📋 |

- **Checkbox**: Select for bulk operations
- **Expand (▶)**: Show individual files in this series
- **Folder / Series**: Folder path and extracted series name
- **Files**: How many individual comic files detected
- **Flag**: Y/S/M classification
- **Status**: Ready, CBZ exists, Single file
- **Output Name**: Proposed CBZ name (editable by clicking ✏)
- **Actions**: Create, Dry Run, Split (for M-flag rows)

### Console Panel
```
🖥 Console Output                                                              ✕
✔ Scan complete — 35 series found, 0 folders skipped
✨ Creating: Series Name v01 (2020).cbz
  Folder: /path/to/series
  Files:  5 source file(s)
[1/6] Working folder
  ✔ Created: /path/to/series/Series Name v01 (2020)/
[2/6] Extracting 5 file(s)
  → file1.cbr
  ✔ 120 file(s) extracted
  ...
```
- **Green ✔**: Successful operations
- **Red ✖**: Errors
- **Blue ℹ**: Informational messages
- **Orange ⚠**: Warnings

---

## Scanning Comics

### What the Scanner Looks For

The app scans your folders for **individual numbered comic issues**:

✅ Recognized patterns:
- `Series 001.cbr`
- `Series #023.cbz`
- `Series (001) - Story Arc.cbr`
- `Series 01 (of 05).cbz`
- `Series 001 - Subtitle (2020).cbr`

❌ Ignored patterns:
- `Series v01.cbz` (already a volume)
- `Series Vol.2.cbr` (already collected)
- `Series (2020).cbz` (no issue number)

### Scanning Process

1. **Enter folder path** (absolute path required)
   - Example: `/home/user/Comics` (macOS/Linux)
   - Example: `C:\Users\user\Comics` (Windows)
   - **Note**: The path must exist and be readable

2. **Click "🔍 Scan Folders"** or press **Enter** in the path field

3. **Wait for completion**
   - You'll see progress in the console
   - Status bar updates with counts
   - Skipped folders panel appears (if any)

4. **Review results**
   - Each series gets a row in the table
   - Check **Flag** and **Status** columns

### Understanding Scan Results

**Status column** tells you what the app detected:

| Status | Meaning | Action |
|--------|---------|--------|
| **Ready** | Individual issues detected, no existing volume | Safe to merge |
| **CBZ exists** | A volume already exists (v01, vol.2, etc.) | Will create v02, v03, etc. |
| **Single file** | Only one issue found | May not be worth merging |

**Flag column** tells you file count:

| Flag | Files | Recommendation |
|------|-------|-----------------|
| **Y** | 4–6 | Good to merge as-is |
| **S** | <4 | Small; consider waiting for more issues |
| **M** | >6 | Consider splitting into 2–3 volumes |

### Skipped Folders

Some folders are skipped (shown in the "Skipped Folders" panel):
- Contain **sub-subfolders** (more than 2 levels deep)
- Require manual intervention via action_explorer or file manager

---

## Creating Single Volumes

### One-Click Creation

1. **Find a series** in the table (status = "Ready")

2. **Review the output name** (right column)
   - Default: `{Series Name} v01 (year).cbz`
   - Example: `Elsewhere v01 (2018).cbz`

3. **Click "✨ Create"** button on that row
   - A dialog appears showing:
     - Proposed output filename (editable)
     - Command that will be executed
     - 6 steps outlined

4. **Edit filename** if needed
   - Click in the text field and change the name
   - Example: `Elsewhere Complete Collection v01 (2018).cbz`

5. **Click "✨ Create"** to confirm
   - Sit back and watch the console
   - You'll see real-time progress

6. **Done!**
   - Console shows: `✔ Done: Elsewhere v01 (2018).cbz`
   - Row disappears from table
   - Original files deleted

### What Happens Behind the Scenes

The app performs 6 steps automatically:

```
[1/6] Create working folder
  → Temporary folder to hold extracted files
  
[2/6] Extract files
  → Unzip/unrar each .cbz and .cbr file
  → Each issue extracted into own subfolder
    (prevents page-name collisions)
  
[3/6] Zip into CBZ
  → Combine all pages into single .cbz archive
  → Folder structure preserved (for reading order)
  
[4/6] Move to destination
  → Final .cbz moved to original folder
  → Replaces any existing file with same name
  
[5/6] Delete source files
  → Original .cbr and .cbz files removed
  → Only the merged volume remains
  
[6/6] Cleanup
  → Delete temporary working folder
```

### Dry Run (Preview Only)

Before committing, **preview without executing**:

1. Click **"📋 Dry Run"** button on a row
2. Console shows what *would* happen
3. No files are modified
4. Use this to check output names and file lists

---

## Splitting Large Volumes

### When to Split

Use **Split** for series with **Flag M** (>6 files):
- 15 issues? Split into 3 volumes of 5 each
- 12 issues? Split into 2 volumes of 6 each
- Easier to manage and read

### Manual Splitting (Full Control)

1. **Click "Split"** button on an M-flag row
   - A panel expands below the row with 3 columns:
     - **Left**: File selection (checkboxes)
     - **Center**: Volume assignment control
     - **Right**: Volume preview

2. **Select files for v01**
   - Check files 1–6 (or 1–5, etc.)
   - They highlight in the left column

3. **Assign to volume**
   - Text field auto-fills with "v01" (or next volume if v01 exists)
   - Click **"Assign"** button
   - Files now show "v01" badge

4. **Select next batch for v02**
   - Check files 7–12
   - Text field auto-fills with "v02"
   - Click **"Assign"**

5. **Repeat for remaining files**
   - Continue checking and assigning

6. **Review preview**
   - Right column shows all volumes being created
   - Verify file counts and names

7. **Click "✨ Create Volumes"**
   - Merges v01, then v02, then v03, etc.
   - Watch console for real-time progress
   - All source files deleted after final volume completes

### Auto-Suggest Split (Quick Option)

For faster splitting, use **"💡 Suggest Split"**:

1. Click **"Split"** on M-flag row
2. Click **"💡 Suggest Split"** button
   - App automatically balances files
   - Example: 15 files → 3 volumes of 5 each
   - Example: 7 files → 2 volumes of 4+3
3. Review proposed split in preview
4. Click **"✨ Create Volumes"** to proceed

---

## Bulk Operations

### Select Multiple Series

1. **Check row checkboxes** (left column)
   - Check as many rows as you want
   - A counter shows: "N selected"

2. **Use shortcuts** (toolbar)
   - **"☑ Select All"** → Check all visible rows
   - **"☐ Deselect All"** → Uncheck all

3. **Filters work with selection**
   - Filter by status, flag, or search
   - Selection counter remains accurate
   - Only visible rows are affected by Select All

### Bulk Create

1. **Select multiple rows** (see above)

2. **Click "✨ Create Selected CBZs"**
   - App merges them one at a time
   - Console shows progress for each

3. **Watch console**
   - Green ✔ = merged successfully
   - Red ✖ = error (original files preserved)
   - Each series gets its own section in the log

4. **Done!**
   - Successfully merged rows disappear from table
   - Failed rows stay (retry or investigate)

### Bulk Dry Run

1. **Select multiple rows**

2. **Click "📋 Dry Run"** button

3. **Console shows** what would happen:
   ```
   📋 DRY RUN for 3 selected series:
      · Series 1 v01 (2020).cbz  (5 files)
      · Series 2 v01 (2019).cbz  (8 files)
      · Series 3 v02 (2021).cbz  (6 files)
   📋 No files would be changed
   ```

4. **Review and confirm** before bulk creating

---

## Filters & Search

### Status Filter

Filter by **readiness to merge**:

| Filter | Shows |
|--------|-------|
| **All statuses** | Everything |
| **Ready (Y/M)** | Ready to merge (Y and M flags) |
| **CBZ exists** | Volume already exists, will create next (v02, v03, etc.) |
| **Single file** | Only one issue found (not recommended for merging) |

### Flag Filter

Filter by **file count**:

| Filter | Files | Use Case |
|--------|-------|----------|
| **All flags** | Any count | Default |
| **Y (4–6)** | 4–6 files | Quick merge pass |
| **S (<4)** | <4 files | Small series (batch later) |
| **M (>6)** | >6 files | Splitting candidates |

### Search

**Find series by name**:
- Type in search box (e.g., "Spider")
- Table instantly filters (case-insensitive, substring match)
- Works with filters (e.g., Status=Ready + Flag=M + Search="War")

### Combined Filtering Example

**Scenario**: You want to bulk-merge all "ready" series with 4–6 files, ignoring small (<4) and large (>6) series.

1. **Status Filter** → "Ready (Y/M)"
2. **Flag Filter** → "Y"
3. **Result**: Only Y-flag rows shown
4. **Click "☑ Select All"** → Check all visible
5. **Click "✨ Create Selected CBZs"** → Bulk merge

---

## Settings & Customization

### Themes

**Click "⚙ Settings"** → **Colour Theme** section

10 themes available:
- **Midnight Blue** (default) — dark with red/teal accents
- **Dark Crimson** — dark red theme
- **Forest** — dark green theme
- **Amber** — dark orange theme
- **Ocean** — dark blue theme
- **Slate** — neutral grey theme
- **Purple Night** — dark purple theme
- **Nord** — Nordtheme colors
- **Light** — light background theme
- **Sepia** — warm brown theme

Click a swatch to apply immediately. Your choice is saved.

### Font Size

**Click "⚙ Settings"** → **Font Size** section

- **Small** — Compact text, more rows visible
- **Medium** (default) — Balanced
- **Large** — Bigger text, fewer rows visible

### Table Density

**Click "⚙ Settings"** → **Table Density** section

- **Compact** — Minimal padding, tight rows
- **Normal** (default) — Comfortable spacing
- **Relaxed** — Loose rows, easier to read

---

## Tips & Best Practices

### Naming Conventions

**Use consistent file naming** so the scanner works well:

✅ Good patterns:
```
Series Name 001.cbr
Series Name 002 - Subtitle (2020).cbr
Series Name #003.cbz
```

❌ Avoid:
```
1.cbr                    (no series name)
Series (2020).cbz        (no issue number)
Series v01.cbr           (already labeled as volume)
```

### Backup Your Comics

Before bulk merging, **backup your source folder**:
```bash
cp -r /path/to/comics /path/to/comics.backup
```

Once files are merged, originals are deleted. If something goes wrong, you'll have a backup.

### Use Dry Run First

For large bulk operations:
1. **Select rows**
2. **Click "📋 Dry Run"** first
3. **Review console output**
4. **Click "✨ Create Selected CBZs"** when confident

### Monitor the Console

Always **watch the console** during merges:
- See real-time progress
- Catch errors early
- Understand what's happening

### Handle Errors Gracefully

If a merge fails:
1. **Check console** for error message
2. **Original files are preserved** (not deleted)
3. **Retry** or **investigate** the issue
4. **Re-scan** to refresh the table

### Organize by Series

Keep comic files organized:
```
/Comics/
  ├── Series 1/
  │   ├── Series 1 001.cbr
  │   ├── Series 1 002.cbr
  │   └── ...
  ├── Series 2/
  │   ├── Series 2 001.cbz
  │   ├── Series 2 002.cbz
  │   └── ...
```

Scan each series folder separately for cleaner results.

---

## Troubleshooting

### "No results after scan"

**Problem**: Scan completes but table shows no series.

**Solutions**:
1. Check file naming:
   - Files must have issue numbers (001, #23, (001), etc.)
   - Examples that work: `Series 001.cbr`, `Series #023.cbz`
   - Examples that don't: `Series (2020).cbz`, `1.cbr`

2. Check path:
   - Verify folder path is correct
   - Make sure you have read permissions

3. Check console:
   - Look for error messages
   - May indicate path issues

### "Server not found" or "Connection refused"

**Problem**: Browser can't reach the server.

**Solution**:
1. Check server is running:
   ```bash
   python3 comic_volume_creator_server.py
   ```
   Should show: `Comic Volume Creator — http://localhost:8765/`

2. Verify port 8765 is not in use:
   ```bash
   lsof -i :8765  # macOS/Linux
   netstat -ano | findstr :8765  # Windows
   ```

3. Try accessing directly: `http://localhost:8765/`

4. Check firewall isn't blocking port 8765

### "Extraction failed" error

**Problem**: A merge fails during the extract step.

**Solutions**:
1. **Check system tools installed**:
   ```bash
   which unrar unzip zip  # macOS/Linux
   where unrar unzip zip  # Windows
   ```
   If missing, install them (see Installation section)

2. **Check file isn't corrupted**:
   - Try opening it in a reader manually
   - If reader fails too, file is corrupted
   - Skip this file and try again

3. **Check permissions**:
   - Ensure you have write permissions in the folder
   - Try: `touch /path/to/folder/testfile.txt`

### "Zip failed" error

**Problem**: Merge fails during the zip step.

**Solutions**:
1. **Check disk space**:
   - Ensure folder has enough free space
   - Merged archive may be large

2. **Check working folder wasn't deleted**:
   - Don't manually delete temp folders during merge
   - Wait for console to show completion

3. **Retry**:
   - If it's a temporary issue, try again
   - Original files are preserved

### "Files not deleted after merge"

**Problem**: Source files still exist after merge completes.

**Solutions**:
1. **Check console** for `[5/6]` step errors
   - May show permission issues
   - Check file isn't locked by another app

2. **Manual cleanup**:
   - New CBZ file was created successfully
   - You can manually delete the source files
   - Or re-scan and try again

3. **Check permissions**:
   - Ensure files aren't read-only
   - Try: `chmod 644 /path/to/file.cbr`

### "Output name already exists"

**Problem**: A CBZ with that name already exists.

**Solution**:
1. **The app will overwrite it**
   - You'll see in console: "Existing file found at destination, removing"
   - Original CBZ is deleted, new one created

2. **To avoid this**:
   - Edit output name before confirming (click ✏ icon)
   - Use different version number (v02, v03, etc.)

### Theme not saving

**Problem**: Changed theme, but reverts after page refresh.

**Solution**:
1. **Check browser localStorage**:
   - If disabled, settings won't save
   - Enable in browser settings
   - Private/Incognito mode doesn't save

2. **Try different browser**:
   - Some browsers have stricter privacy settings
   - Firefox, Chrome usually work fine

### Keyboard Shortcuts Not Working

**Problem**: Escape doesn't close dialogs, Enter doesn't submit.

**Solution**:
1. **Ensure focus on correct element**:
   - For Escape: anywhere on page works
   - For Enter in path field: must be in the input box
   - For Enter in dialog: focus the input field

2. **Try clicking manually**:
   - Use "Cancel" / "Close" buttons as fallback
   - Buttons always work

---

## FAQ

**Q: Can I undo a merge?**
A: No. After merging, originals are deleted. Keep backups if you want to revert.

**Q: Can I merge without deleting source files?**
A: Not currently. The app always deletes after success. Make a backup if you want to keep originals.

**Q: What if I merge the same files twice?**
A: The second merge would fail (originals already deleted). Create a backup first if you're unsure.

**Q: Can I run multiple merges at once?**
A: No. Merges run sequentially. Large operations may take a few minutes.

**Q: Why are my files ignored?**
A: Files need issue numbers to be detected. See "Naming Conventions" above.

**Q: Can I use .zip or .rar files?**
A: Yes. The scanner recognizes .cbz, .cbr, .zip, and .rar formats.

**Q: How big can a merged volume get?**
A: No hard limit. Test with large series; most readers handle 500+ MB archives fine.

**Q: Where are merged volumes saved?**
A: In the same folder as the source files.

**Q: Can I change the output folder?**
A: Not in this version. Volumes are always created in the source folder.

**Q: What's the difference between Y, S, and M flags?**
A: Just file count. Y=4–6 (good size), S=<4 (small), M=>6 (large, consider splitting).

---

## Getting Help

- **In-app**: Click **"❓ Help"** button in header
- **Console**: Check for error messages (red ✖ text)
- **This guide**: Return to relevant section above
- **Server logs**: Check terminal where you started the server

---

## Version

**Comic Volume Creator v1.1**
- Last updated: April 2024
- Server: comic_volume_creator_server.py
- UI: comic_volume_creator_mockup.html

### v1.1 Changes
- ✨ Expand All / Collapse All buttons in toolbar
- 📊 File size (MB) display in file details
- 💾 Save dry run output to HTML file
- 🎨 Improved UI consistency
