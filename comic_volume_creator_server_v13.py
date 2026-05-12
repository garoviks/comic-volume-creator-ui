"""
Comic Volume Creator Server v1.3
Serves comic_volume_creator_v13.html and provides JSON API endpoints.

Usage:
    python3 comic_volume_creator_server_v13.py [--port 8003]

Endpoints:
    GET  /                   — serves comic_volume_creator_v13.html
    GET  /api/browse         — query: ?path=/folder/path
                               returns: HTML listing of folder contents
    GET  /api/exclusions     — query: ?path=/root/path
                               returns: {"exclusions": [...]}
    POST /api/scan           — body: {"path": "/some/comics/root"}
                               returns: {"results": [...], "skipped": [...], "exclusions": [...]}
    POST /api/create         — body: {"folder": "...", "files": [...], "outname": "..."}
                               returns: {"success": true/false, "log": "...", "cbz_name": "..."}
    POST /api/exclusions     — body: {"root": "...", "action": "add"|"remove", "folder": "..."}
                               returns: {"exclusions": [...]}
"""

import os
import re
import json
import shutil
import subprocess
import argparse
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, 'comic_volume_creator_v13.html')

COMIC_EXTS = {'.cbz', '.cbr'}

VOLUME_PATTERN = re.compile(
    r'\b(?:v|vol|book|t)\.?\s*\d+|TPB|Omnibus|Collection|Graphic\s*Novel|GN|HC|Complete',
    re.IGNORECASE
)

# ── Comic filename utilities ────────────────────────────────────────────────

def is_volume(name: str) -> bool:
    return bool(VOLUME_PATTERN.search(name))


def extract_series(filename: str) -> str:
    """Strip issue number and everything after it to get bare series name."""
    name = re.sub(r'\.(cbz|cbr)$', '', filename, flags=re.IGNORECASE)
    # action_explorer approach: handles (001) parenthesised numbers and #001 hash prefix
    m = re.match(r'^(.*?)(?:\s+(?:#\d+|0\d+|\d{3,}|\(\d{1,3}\))(?:\s*\(of\s*\d+\))?)', name, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()
    # fallback: require zero-padded number to avoid cutting titles with bare digits
    result = re.sub(r'(\s|#)0\d.*', '', name, flags=re.IGNORECASE).strip()
    return result or name


def extract_year(filename: str) -> str | None:
    m = re.search(r'\((\d{4})\)', filename)
    return m.group(1) if m else None


def is_numbered_issue(filename: str) -> bool:
    """True if filename looks like an individual numbered issue (not an existing volume)."""
    if is_volume(filename):
        return False
    return bool(re.search(r'0\d|00\d', filename))


def extract_issue_number(filename: str) -> int | None:
    """Extract the issue number from a filename. Returns int or None."""
    # Match patterns like: 001, #001, (001), 01, #01, etc.
    m = re.search(r'(?:#|\()?(\d{1,3})(?:\)|(?:\s*\(of|\s|$))', filename)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, IndexError):
            return None
    return None


def extract_zero_padded_issue(filename: str) -> int | None:
    """Extract only zero-padded issue numbers (01, 001, 023, etc.).
    Avoids picking up stray numbers from series titles like 'Season 2' or '100 Bullets'.
    Used in auto-logic conditions C and D.
    """
    m = re.search(r'(?:^|[\s#(])(0\d{1,2})(?!\d)', filename)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, IndexError):
            return None
    return None


def get_next_volume_number(folder_path: str, series: str) -> int:
    """Scan folder for existing {series} vNN.cbz/.cbr files and return max+1."""
    escaped = re.escape(series)
    pattern = re.compile(r'^' + escaped + r'.*\bv(\d+)\b.*\.(?:cbz|cbr)$', re.IGNORECASE)
    max_vol = 0
    try:
        for f in os.listdir(folder_path):
            m = pattern.match(f)
            if m:
                max_vol = max(max_vol, int(m.group(1)))
    except OSError:
        pass
    return max_vol + 1


def has_any_volume(folder_path: str, series: str) -> bool:
    """Check if any volume of a series exists in folder."""
    escaped = re.escape(series)
    pattern = re.compile(r'^' + escaped + r'.*\bv(\d+)\b.*\.(?:cbz|cbr)$', re.IGNORECASE)
    try:
        for f in os.listdir(folder_path):
            if pattern.match(f):
                return True
    except OSError:
        pass
    return False


def is_redundant_with_last_volume(files: list[str], next_vol: int) -> bool:
    """
    Check if individual files are redundant (same issues that were in last volume).
    Logic: if v01 exists (next_vol=2) and lowest issue is 001-004, likely redundant.
    If lowest issue is 005+, they're new issues for v02 (ready state).
    """
    if next_vol <= 1:
        return False  # No volume exists yet

    issue_numbers = []
    for f in files:
        num = extract_issue_number(f)
        if num is not None:
            issue_numbers.append(num)

    if not issue_numbers:
        return False

    min_issue = min(issue_numbers)

    # If v01 exists (next_vol=2) and files start from 001-004, they're redundant
    if next_vol == 2 and min_issue <= 4:
        return True

    # For v02 exists (next_vol=3): v02 likely covers 005-008, so redundant if min <= 8
    if next_vol == 3 and min_issue <= 8:
        return True

    # General pattern: if min issue falls within previous volume range, it's redundant
    # Each volume ~4-8 issues, so rough check
    if next_vol > 3:
        expected_max_of_last = (next_vol - 1) * 4 + 4
        if min_issue <= expected_max_of_last:
            return True

    return False


# ── Scan logic ──────────────────────────────────────────────────────────────

def scan_single_folder(folder_path: str) -> dict[str, dict]:
    """Return {series: {files: [...], years: set()}} for one folder."""
    groups: dict[str, dict] = {}
    try:
        entries = [e for e in os.scandir(folder_path) if e.is_file()]
    except OSError:
        return groups

    for entry in sorted(entries, key=lambda e: e.name.lower()):
        name = entry.name
        if os.path.splitext(name)[1].lower() not in COMIC_EXTS:
            continue
        if not is_numbered_issue(name):
            continue
        series = extract_series(name)
        year   = extract_year(name)
        key = series.lower()
        if key not in groups:
            groups[key] = {'files': [], 'years': set(), 'display_series': series}
        groups[key]['files'].append(name)
        if year:
            groups[key]['years'].add(year)

    return groups


def has_subdirs(path: str) -> bool:
    try:
        return any(e.is_dir() for e in os.scandir(path))
    except OSError:
        return False


# ── Exclusions file (per scan-root) ─────────────────────────────────────────

EXCLUSIONS_FILE = '.comic_exclusions.md'


def read_exclusions(root_path: str) -> dict[str, list[str]]:
    """Read exclusions from .comic_exclusions.md. Returns {'always': [...], 'temp': [...]}."""
    path = os.path.join(root_path, EXCLUSIONS_FILE)
    result = {'always': [], 'temp': []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            current_section = None
            for line in f:
                line = line.rstrip()
                if line.strip() == '## Always Exclude':
                    current_section = 'always'
                elif line.strip() == '## Temp Exclude':
                    current_section = 'temp'
                elif line.startswith('## '):
                    current_section = None
                elif current_section and line.startswith('- '):
                    folder = line[2:].strip()
                    if folder:
                        result[current_section].append(folder)
    except FileNotFoundError:
        pass
    return result


def write_exclusions(root_path: str, always: list[str], temp: list[str]) -> None:
    """Write always and temp exclusion lists to .comic_exclusions.md."""
    filepath = os.path.join(root_path, EXCLUSIONS_FILE)
    lines = ['# Comic Volume Creator — Exclusions', '', '## Always Exclude']
    for p in sorted(set(always)):
        lines.append(f'- {p}')
    lines += ['', '## Temp Exclude']
    for p in sorted(set(temp)):
        lines.append(f'- {p}')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


# ── Auto-logic (conditions A–D) ─────────────────────────────────────────────

def _has_current_year(files: list[str]) -> bool:
    current_year = str(datetime.datetime.now().year)
    return any(f'({current_year})' in fname for fname in files)


def _of_n_total(files: list[str]) -> int | None:
    """Return the total N from the first (X of N) or X (of N) pattern found, or None."""
    for fname in files:
        m = re.search(r'\((\d+)\s+of\s+(\d+)\)', fname, re.IGNORECASE)
        if m:
            return int(m.group(2))
        m = re.search(r'\d+\s+\(of\s+(\d+)\)', fname, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _check_condition_a(files: list[str]) -> bool:
    """Temp.exclude: current year AND series is incomplete per (X of N) pattern."""
    if not _has_current_year(files):
        return False
    total = _of_n_total(files)
    if total is None:
        return False
    return len(files) < total


def _check_condition_a2(files: list[str]) -> bool:
    """Incomplete: past year AND series is incomplete per (X of N) pattern."""
    if _has_current_year(files):
        return False
    total = _of_n_total(files)
    if total is None:
        return False
    return len(files) < total


def _check_condition_b(files: list[str], folder_path: str, series: str, next_vol: int) -> bool:
    """Temp.exclude: current year AND prev volume exists AND available < expected volume size."""
    if next_vol <= 1:
        return False
    if not _has_current_year(files):
        return False
    issue_nums = sorted(n for n in (extract_issue_number(f) for f in files) if n is not None)
    if not issue_nums:
        return False
    first_issue = issue_nums[0]
    expected_vol_size = first_issue - 1
    if expected_vol_size <= 0:
        return False
    return len(files) < expected_vol_size


def _check_condition_c(files: list[str], next_vol: int) -> bool:
    """Incomplete: any gap in issue sequence.
    Only applied when no previous volume exists (next_vol == 1).
    When a previous volume exists, missing earlier issues are expected to be in it.
    Uses zero-padded extractor to avoid picking up stray numbers from series titles.
    """
    if next_vol > 1:
        return False
    issue_nums = sorted(set(n for n in (extract_zero_padded_issue(f) for f in files) if n is not None))
    if len(issue_nums) < 1:
        return False
    if issue_nums[0] > 1:
        return True
    for i in range(len(issue_nums) - 1):
        if issue_nums[i + 1] - issue_nums[i] > 1:
            return True
    return False


def _check_condition_d(files: list[str], highest_year: str | None) -> bool:
    """Incomplete (soft): past year AND atypical count (3 or 5) AND not consecutive from 001.
    Consecutive-from-001 series are likely complete mini-series, not missing issues.
    Uses zero-padded extractor to avoid picking up stray numbers from series titles.
    """
    if not highest_year:
        return False
    current_year = datetime.datetime.now().year
    if int(highest_year) >= current_year:
        return False
    if len(files) not in (3, 5):
        return False
    # Don't flag if issues are consecutive starting from 001
    issue_nums = sorted(set(n for n in (extract_zero_padded_issue(f) for f in files) if n is not None))
    if not issue_nums:
        return False
    if issue_nums[0] == 1 and all(issue_nums[i+1] - issue_nums[i] == 1 for i in range(len(issue_nums)-1)):
        return False
    return True


def _check_condition_e(files: list[str], next_vol: int) -> bool:
    """Temp.exclude: current year AND fewer than 4 files AND no (of N) completion indicator.
    Catches ongoing current-year series with too few issues to form a volume yet.
    Only when no previous volume exists (next_vol == 1).
    """
    if next_vol > 1:
        return False
    if not _has_current_year(files):
        return False
    if len(files) >= 4:
        return False
    for fname in files:
        if re.search(r'\(of\s+\d+\)', fname, re.IGNORECASE):
            return False
    return True


def _is_consecutive(nums: list[int]) -> bool:
    """Return True if sorted list of ints has no gaps."""
    return all(nums[i+1] - nums[i] == 1 for i in range(len(nums) - 1))


def _check_auto_ready(files: list[str], next_vol: int, highest_year: str | None) -> bool:
    """Return True if confident the series is complete and ready to archive.

    Criterion 1: explicit (N of N) completion marker in any filename.
    Criterion 2: past year + consecutive sequence starting from 001.
    Criterion 3: past year + typical volume size (4 or 6) + consecutive sequence.
    Criterion 4: previous volume exists + consecutive sequence + not current year.
    """
    current_year = datetime.datetime.now().year

    # Bail out if (of N) pattern explicitly shows we don't have all issues
    of_n = _of_n_total(files)
    if of_n is not None and len(files) < of_n:
        return False

    # Criterion 1 — any file has (X of N) and we have all N issues
    for fname in files:
        m = re.search(r'\((\d+)\s+of\s+(\d+)\)', fname, re.IGNORECASE)
        if not m:
            m = re.search(r'(\d+)\s+\(of\s+(\d+)\)', fname, re.IGNORECASE)
        if m:
            total = int(m.group(2))
            if total > 0 and len(files) == total:
                return True

    past_year = highest_year is not None and int(highest_year) < current_year
    issue_nums = sorted(set(n for n in (extract_zero_padded_issue(f) for f in files) if n is not None))

    if len(issue_nums) >= 2:
        consecutive = _is_consecutive(issue_nums)

        # Criterion 2 — past year + consecutive from 001 + at least 4 files
        if past_year and consecutive and issue_nums[0] == 1 and len(files) >= 4:
            return True

        # Criterion 3 — past year + standard volume size + consecutive
        if past_year and len(files) in (4, 6) and consecutive:
            return True

        # Criterion 4 — previous volume exists + consecutive + not current year + at least 4 files
        if next_vol > 1 and past_year and consecutive and len(files) >= 4:
            return True

    return False


def apply_auto_logic(results: list[dict]) -> None:
    """Run conditions A–E then Auto.Ready on scan results, updating status in-place."""
    for row in results:
        if row['status'] != 'ready':
            continue
        files = row['files']
        folder = row['folder']
        series = row['series']
        next_vol = get_next_volume_number(folder, series)
        highest_year = str(max(int(y) for y in row.get('years_set', []))) if row.get('years_set') else None

        if _check_condition_a(files):
            row['status'] = 'temp_exclude'
        elif _check_condition_a2(files):
            row['status'] = 'incomplete'
        elif _check_condition_b(files, folder, series, next_vol):
            row['status'] = 'temp_exclude'
        elif _check_condition_c(files, next_vol):
            row['status'] = 'incomplete'
        elif _check_condition_d(files, highest_year):
            row['status'] = 'incomplete'
        elif _check_condition_e(files, next_vol):
            row['status'] = 'temp_exclude'
        elif _check_auto_ready(files, next_vol, highest_year):
            row['status'] = 'auto_ready'


def scan_root(root_path: str) -> tuple[list[dict], list[dict]]:
    """
    Scan root + one level of subfolders.
    Returns (results, skipped):
      results: list of series group dicts
      skipped: list of {path, subcount} dicts (folders with sub-subfolders)
    """
    results: list[dict] = []
    skipped: list[dict] = []
    row_id  = 0

    def process(folder_path: str):
        nonlocal row_id
        groups = scan_single_folder(folder_path)
        for key, data in sorted(groups.items()):
            series = data['display_series']
            files = sorted(data['files'], key=lambda f: (extract_issue_number(f) or extract_zero_padded_issue(f) or 0, f.lower()))
            n = len(files)
            flag = 'M' if n > 6 else ('S' if n < 4 else 'Y')
            highest_year = str(max(int(y) for y in data['years'])) if data['years'] else None
            next_vol = get_next_volume_number(folder_path, series)
            vol_str  = f'v{next_vol:02d}'
            outname  = f'{series} {vol_str}'
            if highest_year:
                outname += f' ({highest_year})'
            # Determine status
            cbz_final = os.path.join(folder_path, outname + '.cbz')
            if os.path.exists(cbz_final):
                status = 'exists'
            elif is_redundant_with_last_volume(files, next_vol):
                status = 'redundant'
            elif n == 1:
                status = 'single'
            else:
                status = 'ready'
            # Calculate file sizes
            file_sizes = {}
            for fname in files:
                fpath = os.path.join(folder_path, fname)
                try:
                    size_mb = os.path.getsize(fpath) / (1024 * 1024)
                    file_sizes[fname] = round(size_mb, 1)
                except OSError:
                    file_sizes[fname] = 0

            results.append({
                'id':       row_id,
                'folder':   folder_path,
                'series':   series,
                'files':    files,
                'file_sizes': file_sizes,
                'flag':     flag,
                'status':   status,
                'outname':  outname,
                'years_set': list(data['years']),
            })
            row_id += 1

    root_no_subdirs = not has_subdirs(root_path)
    if root_no_subdirs:
        process(root_path)

    try:
        for entry in sorted(os.scandir(root_path), key=lambda e: e.name.lower()):
            if not entry.is_dir():
                continue
            if has_subdirs(entry.path):
                try:
                    sub_names = [e.name for e in os.scandir(entry.path) if e.is_dir()]
                    skipped.append({'path': entry.path, 'subcount': len(sub_names)})
                except OSError:
                    skipped.append({'path': entry.path, 'subcount': 0})
            else:
                process(entry.path)
    except OSError:
        pass

    # Apply auto-logic (conditions A–D)
    apply_auto_logic(results)

    # Apply exclusions from file (strip folder paths for comparison to handle trailing spaces)
    exclusions = read_exclusions(root_path)
    always_set = set(p.strip() for p in exclusions['always'])
    temp_set   = set(p.strip() for p in exclusions['temp'])
    for row in results:
        folder_key = row['folder'].strip()
        if folder_key in always_set:
            row['status'] = 'exclude'
        elif folder_key in temp_set:
            row['status'] = 'temp_exclude'

    return results, skipped, exclusions


# ── CBZ creation (from action_explorer_v12.py) ──────────────────────────────

def create_cbz_direct(abs_path: str, files: list[str], outname: str) -> tuple[bool, str]:
    """Build a CBZ from exactly the listed files. Returns (success, log_text)."""
    log: list[str] = []
    working_dir    = os.path.join(abs_path, outname)
    cbz_name       = outname + '.cbz'
    cbz_in_working = os.path.join(working_dir, cbz_name)
    cbz_final      = os.path.join(abs_path, cbz_name)

    def ok(msg):   log.append(f'  ✔ {msg}')
    def err(msg):  log.append(f'  ✖ {msg}')
    def info(msg): log.append(f'  · {msg}')

    try:
        log.append(f'\n[1/6] Working folder')
        if os.path.exists(working_dir):
            info(f'Existing folder found, removing: {outname}/')
            shutil.rmtree(working_dir)
            ok('Removed.')
        os.makedirs(working_dir)
        ok(f'Created: {working_dir}')

        log.append(f'\n[2/6] Extracting {len(files)} file(s)')
        sorted_files = sorted(files, key=lambda f: (extract_issue_number(f) or extract_zero_padded_issue(f) or 0, f.lower()))
        pad = len(str(len(sorted_files)))
        for idx, filename in enumerate(sorted_files, 1):
            src  = os.path.join(abs_path, filename)
            stem = os.path.splitext(filename)[0]
            ext  = os.path.splitext(filename)[1].lower()
            subdir = os.path.join(working_dir, f'{str(idx).zfill(pad)}_{stem}')
            os.makedirs(subdir)
            log.append(f'\n  → {filename}')
            info(f'Subfolder: {stem}/')
            if ext in ('.cbr', '.rar'):
                cmd = ['unrar', 'e', '-o+', '-inul', src, subdir + os.sep]
                info('Tool: unrar')
            else:
                cmd = ['unzip', '-o', '-q', src, '-d', subdir]
                info('Tool: unzip')
            info('Command: ' + ' '.join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 and ext in ('.cbr', '.rar'):
                # Some .cbr files are actually ZIP archives — fall back to unzip
                info('unrar failed, retrying with unzip (file may be ZIP-format .cbr)')
                cmd = ['unzip', '-o', '-q', src, '-d', subdir]
                info('Tool: unzip (fallback)')
                result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                err(f'Extraction failed (exit code {result.returncode})')
                if result.stderr.strip():
                    err(result.stderr.strip())
                raise RuntimeError(f'Extraction failed on {filename}')
            extracted = sorted(os.listdir(subdir))
            ok(f'{len(extracted)} file(s) extracted')

        log.append(f'\n[3/6] Zipping into {cbz_name}')
        info(f'Command: zip -r "{cbz_in_working}" .')
        result = subprocess.run(
            ['zip', '-r', cbz_in_working, '.'],
            capture_output=True, text=True, cwd=working_dir
        )
        if result.returncode != 0:
            err(f'zip failed (exit code {result.returncode})')
            if result.stderr.strip():
                err(result.stderr.strip())
            raise RuntimeError('zip failed')
        cbz_bytes = os.path.getsize(cbz_in_working)
        size_str  = (f'{cbz_bytes/1024**3:.2f} GB' if cbz_bytes >= 1024**3
                     else f'{cbz_bytes/1024**2:.1f} MB' if cbz_bytes >= 1024**2
                     else f'{cbz_bytes/1024:.1f} KB')
        ok(f'Created {cbz_name} ({size_str})')

        log.append(f'\n[4/6] Moving CBZ to destination')
        info(f'To: {cbz_final}')
        if os.path.exists(cbz_final):
            info('Existing CBZ at destination — replacing.')
            os.remove(cbz_final)
        shutil.move(cbz_in_working, cbz_final)
        ok(f'Moved: {cbz_name}')

        log.append(f'\n[5/6] Deleting {len(files)} original source file(s)')
        for filename in files:
            src = os.path.join(abs_path, filename)
            info(f'Deleting: {filename}')
            try:
                os.remove(src)
                ok('Deleted.')
            except OSError as e:
                err(f'Could not delete {filename}: {e}')

        log.append(f'\n[6/6] Cleanup')
        info(f'Removing working folder: {working_dir}')
        shutil.rmtree(working_dir)
        ok('Working folder removed.')

        log.append(f'\n✔ Done: {cbz_name}')
        return True, '\n'.join(log)

    except Exception as e:
        err(f'FAILED: {e}')
        log.append(f'\n[cleanup] Removing working folder after failure')
        if os.path.exists(working_dir):
            try:
                shutil.rmtree(working_dir)
                log.append('  · Working folder removed.')
            except Exception as ce:
                log.append(f'  ✖ Could not remove working folder: {ce}')
        return False, '\n'.join(log)


# ── HTTP server ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        if args and isinstance(args[0], str) and any(m in args[0] for m in ('GET', 'POST')):
            print(f'  {self.address_string()} — {args[0]}')

    def send_json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        return json.loads(raw) if raw else {}

    def send_folder_listing(self, folder_path: str):
        """Send HTML listing of folder contents."""
        try:
            entries = sorted(os.scandir(folder_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            entries = []

        rows = []
        for entry in entries:
            is_dir = entry.is_dir()
            name = entry.name
            size = ''
            if not is_dir:
                try:
                    size_b = entry.stat().st_size
                    if size_b >= 1024**3:
                        size = f'{size_b / 1024**3:.1f} GB'
                    elif size_b >= 1024**2:
                        size = f'{size_b / 1024**2:.1f} MB'
                    else:
                        size = f'{size_b / 1024:.1f} KB'
                except OSError:
                    size = '—'

            icon = '📁' if is_dir else '📄'
            rows.append(f'<tr><td>{icon}</td><td>{name}</td><td style="text-align:right; color:#888; font-size:0.9rem;">{size}</td></tr>')

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Folder: {os.path.basename(folder_path)}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #121212;
      color: #e0e0e0;
      padding: 20px;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
      background: #1e1e2e;
      border: 1px solid #0f3460;
      border-radius: 8px;
      padding: 20px;
    }}
    h1 {{
      color: #e94560;
      font-size: 1.3rem;
      margin-bottom: 20px;
      word-break: break-all;
    }}
    .breadcrumb {{
      font-size: 0.85rem;
      color: #888;
      margin-bottom: 15px;
      padding: 10px;
      background: #0d0d1a;
      border-radius: 4px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    tr:hover {{
      background: #2a2a3e;
    }}
    td {{
      padding: 10px;
      border-bottom: 1px solid #2a2a3e;
    }}
    td:first-child {{
      width: 30px;
      text-align: center;
    }}
    td:last-child {{
      width: 120px;
    }}
    .empty {{
      text-align: center;
      padding: 40px;
      color: #888;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📁 {os.path.basename(folder_path)}</h1>
    <div class="breadcrumb">{folder_path}</div>
    <table>
      {(''.join(rows) if rows else '<tr><td colspan="3" class="empty">Folder is empty</td></tr>')}
    </table>
  </div>
</body>
</html>'''

        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ('/', '/index.html'):
            try:
                with open(HTML_FILE, 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_error(404, 'HTML file not found')
        elif path == '/api/browse':
            import urllib.parse
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            folder = query.get('path', [''])[0].strip()
            if not folder or not os.path.isdir(folder):
                self.send_error(400, 'Invalid path')
                return
            try:
                self.send_folder_listing(folder)
            except Exception as e:
                self.send_error(500, f'Error: {str(e)}')
        elif path == '/api/exclusions':
            import urllib.parse
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            root = query.get('path', [''])[0].strip()
            if not root or not os.path.isdir(root):
                self.send_json(400, {'error': f'Invalid path: {root!r}'})
                return
            self.send_json(200, {'exclusions': read_exclusions(root)})  # returns {always, temp}
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split('?')[0]

        if path == '/api/scan':
            body = self.read_json_body()
            root = body.get('path', '').strip()
            if not root or not os.path.isdir(root):
                self.send_json(400, {'error': f'Path not found or not a directory: {root!r}'})
                return
            try:
                results, skipped, exclusions = scan_root(root)
                self.send_json(200, {'results': results, 'skipped': skipped, 'exclusions': exclusions})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif path == '/api/exclusions':
            body = self.read_json_body()
            root   = body.get('root', '').strip()
            action = body.get('action', '').strip()
            folder = body.get('folder', '').strip()
            excl_type = body.get('type', 'always').strip()  # 'always' or 'temp'
            if not root or not os.path.isdir(root):
                self.send_json(400, {'error': f'Invalid root: {root!r}'})
                return
            exclusions = read_exclusions(root)
            if action == 'add' and folder:
                if excl_type == 'temp' and folder not in exclusions['temp']:
                    exclusions['temp'].append(folder)
                elif excl_type == 'always' and folder not in exclusions['always']:
                    exclusions['always'].append(folder)
                    exclusions['temp'] = [f for f in exclusions['temp'] if f != folder]
                write_exclusions(root, exclusions['always'], exclusions['temp'])
            elif action == 'remove':
                exclusions['always'] = [f for f in exclusions['always'] if f != folder]
                exclusions['temp']   = [f for f in exclusions['temp']   if f != folder]
                write_exclusions(root, exclusions['always'], exclusions['temp'])
            self.send_json(200, {'exclusions': exclusions})

        elif path == '/api/create':
            body = self.read_json_body()
            folder  = body.get('folder', '')  # Don't strip - preserve exact folder path including trailing spaces
            files   = body.get('files', [])
            outname = body.get('outname', '').strip().removesuffix('.cbz')
            if not folder or not files or not outname:
                self.send_json(400, {'error': 'Missing folder, files, or outname'})
                return
            if not os.path.isdir(folder):
                self.send_json(400, {'error': f'Folder not found: {folder!r}'})
                return
            success, log = create_cbz_direct(folder, files, outname)
            self.send_json(200 if success else 500,
                           {'success': success, 'log': log, 'cbz_name': outname + '.cbz'})

        else:
            self.send_error(404)


def main():
    parser = argparse.ArgumentParser(description='Comic Volume Creator server')
    parser.add_argument('--port', type=int, default=8003)
    args = parser.parse_args()

    print(f'Comic Volume Creator — http://localhost:{args.port}/')
    print(f'Serving: {HTML_FILE}')
    print('Press Ctrl-C to stop.\n')

    server = HTTPServer(('', args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
