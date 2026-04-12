# Comic Volume Creator

A web-based tool for scanning, organizing, and merging individual comic files (.cbz, .cbr) into consolidated volumes.

## Quick Start

### 1. Install System Tools

**macOS (Homebrew):**
```bash
brew install unrar p7zip
```

**Ubuntu/Debian:**
```bash
sudo apt-get install unrar zip unzip
```

**Windows (Chocolatey):**
```bash
choco install unrar 7zip
```

### 2. Start the Server

```bash
cd /home/nesha/scripts/comic_volume_creator
python3 comic_volume_creator_server.py
```

You should see:
```
Comic Volume Creator — http://localhost:8765/
Serving: /path/to/comic_volume_creator_mockup.html
Press Ctrl-C to stop.
```

### 3. Open in Browser

```
http://localhost:8765/
```

## Files

| File | Purpose |
|------|---------|
| `comic_volume_creator_server.py` | Backend server (Python) |
| `comic_volume_creator_mockup.html` | Web UI (HTML/CSS/JS) |
| `split_volumes_mockup.html` | Split volumes feature mockup (reference) |
| `COMIC_VOLUME_CREATOR_REQUIREMENTS.md` | Functional & non-functional requirements |
| `COMIC_VOLUME_CREATOR_ARCHITECTURE.md` | System design, APIs, components |
| `COMIC_VOLUME_CREATOR_USER_GUIDE.md` | Complete user documentation |
| `README.md` | This file |

## Documentation

- **New to the app?** → Read [COMIC_VOLUME_CREATOR_USER_GUIDE.md](COMIC_VOLUME_CREATOR_USER_GUIDE.md)
- **Building/extending?** → Read [COMIC_VOLUME_CREATOR_ARCHITECTURE.md](COMIC_VOLUME_CREATOR_ARCHITECTURE.md)
- **Project scope?** → Read [COMIC_VOLUME_CREATOR_REQUIREMENTS.md](COMIC_VOLUME_CREATOR_REQUIREMENTS.md)

## Features

✅ Scan folders for individual comic issues  
✅ Auto-group by series name & metadata extraction  
✅ Single-click volume creation (merge multiple issues → 1 CBZ)  
✅ Split large volumes into multiple archives  
✅ Bulk operations (create multiple volumes at once)  
✅ Filtering & search (by status, flag, series name)  
✅ 10 color themes + customizable UI  
✅ Real-time console output  
✅ In-app help & full documentation  

## Workflow

1. Enter source folder path
2. Click "🔍 Scan Folders"
3. Review results (Y/S/M flags indicate file count)
4. Click "✨ Create" on a row, or select multiple + "✨ Create Selected CBZs"
5. For large series (Flag M): use "Split" button to divide into multiple volumes
6. Watch console for real-time progress
7. Done! (merged CBZ created, originals deleted on success)

## Requirements

- **Python 3.8+**
- **System tools**: unrar, unzip, zip
- **Browser**: Modern (Chrome, Firefox, Safari, Edge)
- **Comic files**: .cbz, .cbr, .zip, .rar archives with numbered issues

## Troubleshooting

See **COMIC_VOLUME_CREATOR_USER_GUIDE.md** → "Troubleshooting" section

## Support

Click the **"❓ Help"** button in the app for in-app help and FAQs.

---

**Location**: `/home/nesha/scripts/comic_volume_creator/`

**Version**: v1.1

**Last Updated**: April 2024
