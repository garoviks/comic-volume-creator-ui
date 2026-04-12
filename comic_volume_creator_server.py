"""
Comic Volume Creator Server
Serves comic_volume_creator_mockup.html and provides JSON API endpoints.

Usage:
    python3 comic_volume_creator_server.py [--port 8765]

Endpoints:
    GET  /              — serves comic_volume_creator_mockup.html
    POST /api/scan      — body: {"path": "/some/comics/root"}
                          returns: {"results": [...], "skipped": [...]}
    POST /api/create    — body: {"folder": "...", "files": [...], "outname": "..."}
                          returns: {"success": true/false, "log": "...", "cbz_name": "..."}
"""

import os
import re
import json
import shutil
import subprocess
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, 'comic_volume_creator_mockup.html')

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
    m = re.match(r'^(.*?)(?:\s+(?:#?\d+|\(\d{1,3}\))(?:\s*\(of\s*\d+\))?)', name, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()
    # fallback: scan_comics approach
    result = re.sub(r'(\s|#)(0{1,2})?\d.*', '', name, flags=re.IGNORECASE).strip()
    return result or name


def extract_year(filename: str) -> str | None:
    m = re.search(r'\((\d{4})\)', filename)
    return m.group(1) if m else None


def is_numbered_issue(filename: str) -> bool:
    """True if filename looks like an individual numbered issue (not an existing volume)."""
    if is_volume(filename):
        return False
    return bool(re.search(r'0\d|00\d', filename))


def get_next_volume_number(folder_path: str, series: str) -> int:
    """Scan folder for existing {series} vNN.cbz files and return max+1."""
    escaped = re.escape(series)
    pattern = re.compile(r'^' + escaped + r'.*\bv(\d+)\b.*\.cbz$', re.IGNORECASE)
    max_vol = 0
    try:
        for f in os.listdir(folder_path):
            m = pattern.match(f)
            if m:
                max_vol = max(max_vol, int(m.group(1)))
    except OSError:
        pass
    return max_vol + 1


# ── Scan logic ──────────────────────────────────────────────────────────────

def scan_single_folder(folder_path: str) -> dict[str, dict]:
    """Return {series: {files: [...], years: set()}} for one folder."""
    groups: dict[str, dict] = {}
    try:
        entries = [e for e in os.scandir(folder_path) if e.is_file()]
    except OSError:
        return groups

    for entry in sorted(entries, key=lambda e: e.name):
        name = entry.name
        if os.path.splitext(name)[1].lower() not in COMIC_EXTS:
            continue
        if not is_numbered_issue(name):
            continue
        series = extract_series(name)
        year   = extract_year(name)
        if series not in groups:
            groups[series] = {'files': [], 'years': set()}
        groups[series]['files'].append(name)
        if year:
            groups[series]['years'].add(year)

    return groups


def has_subdirs(path: str) -> bool:
    try:
        return any(e.is_dir() for e in os.scandir(path))
    except OSError:
        return False


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
        for series, data in sorted(groups.items()):
            files = sorted(data['files'])
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
                'id':     row_id,
                'folder': folder_path,
                'series': series,
                'files':  files,
                'file_sizes': file_sizes,
                'flag':   flag,
                'status': status,
                'outname': outname,
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

    return results, skipped


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
        for filename in sorted(files):
            src  = os.path.join(abs_path, filename)
            stem = os.path.splitext(filename)[0]
            ext  = os.path.splitext(filename)[1].lower()
            subdir = os.path.join(working_dir, stem)
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
                results, skipped = scan_root(root)
                self.send_json(200, {'results': results, 'skipped': skipped})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif path == '/api/create':
            body = self.read_json_body()
            folder  = body.get('folder', '').strip()
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
    parser.add_argument('--port', type=int, default=8765)
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
