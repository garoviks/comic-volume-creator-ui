"""Metron API client for Comic Volume Creator v1.6.

Authentication: HTTP Basic Auth (free account at metron.cloud)
Rate limit: 20 req/min, 5,000 req/day
"""

import urllib.request
import urllib.parse
import json
import base64

BASE_URL = "https://metron.cloud/api"
_cache: dict[str, list[dict]] = {}  # session-level cache keyed by series name (lowercase)


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def search_series(series_name: str, username: str, password: str) -> list[dict]:
    """Search Metron for a comic series by name. Returns up to 5 results. Session-cached."""
    cache_key = series_name.lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    params = urllib.parse.urlencode({'name': series_name, 'format': 'json'})
    url = f"{BASE_URL}/series/?{params}"
    req = urllib.request.Request(url, headers={
        'Authorization': _auth_header(username, password),
        'User-Agent': 'ComicVolumeCreator/1.6',
    })

    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status == 401:
            raise RuntimeError("Metron authentication failed — check username and password")
        if resp.status == 429:
            raise RuntimeError("Metron rate limit exceeded (20 req/min)")
        data = json.loads(resp.read())

    results = []
    for item in (data.get('results') or [])[:5]:
        pub = item.get('publisher') or {}
        results.append({
            'id': item.get('id'),
            'name': item.get('name', ''),
            'year_began': item.get('year_began') or '',
            'publisher': pub.get('name', '') if isinstance(pub, dict) else '',
            'desc': item.get('desc') or '',
            'issue_count': item.get('issue_count') or 0,
        })

    _cache[cache_key] = results
    return results


def pick_best_match(series_name: str, results: list[dict]) -> dict | None:
    """Auto-select best matching result by name similarity. Returns None if ambiguous."""
    if not results:
        return None

    name_lower = series_name.lower().strip()

    # Exact match (case-insensitive)
    for r in results:
        if r['name'].lower().strip() == name_lower:
            return r

    # One name contains the other
    for r in results:
        r_lower = r['name'].lower().strip()
        if name_lower in r_lower or r_lower in name_lower:
            return r

    # Only one result — return it
    if len(results) == 1:
        return results[0]

    return None  # ambiguous — caller falls back to filename-only


def build_comicinfo_xml(series_name: str, volume_num: int, first_issue: int | None,
                         issue_count: int, metron_data: dict | None) -> str:
    """Build ComicInfo.xml string. Uses metron_data if provided, falls back to local values."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
    ]

    def tag(name: str, val) -> None:
        v = str(val).strip() if val is not None else ''
        if v:
            lines.append(f'  <{name}>{v}</{name}>')

    series = (metron_data.get('name') or series_name) if metron_data else series_name
    tag('Series', series)
    if first_issue is not None:
        tag('Number', first_issue)
    tag('Count', issue_count)
    tag('Volume', volume_num)

    if metron_data:
        tag('Publisher', metron_data.get('publisher', ''))
        tag('Year', metron_data.get('year_began', ''))
        tag('Summary', metron_data.get('desc', ''))

    lines.append('</ComicInfo>')
    return '\n'.join(lines) + '\n'
