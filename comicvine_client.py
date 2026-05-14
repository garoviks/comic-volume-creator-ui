"""ComicVine API client for Comic Volume Creator v1.6."""

import urllib.request
import urllib.parse
import json

BASE_URL = "https://comicvine.gamespot.com/api"
_cache: dict[str, list[dict]] = {}  # session-level cache keyed by series name (lowercase)


def search_volume(series_name: str, api_key: str) -> list[dict]:
    """Search ComicVine for a series/volume. Returns up to 5 results. Caches by name."""
    cache_key = series_name.lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    params = urllib.parse.urlencode({
        'api_key': api_key,
        'format': 'json',
        'query': series_name,
        'resources': 'volume',
        'field_list': 'id,name,start_year,publisher,deck,count_of_issues',
        'limit': 5,
    })
    url = f"{BASE_URL}/search/?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ComicVolumeCreator/1.6'})

    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status == 429:
            raise RuntimeError("ComicVine rate limit exceeded (200 req/hour)")
        data = json.loads(resp.read())

    results = []
    for item in data.get('results', []):
        pub = item.get('publisher') or {}
        results.append({
            'id': item.get('id'),
            'name': item.get('name', ''),
            'start_year': item.get('start_year') or '',
            'publisher': pub.get('name', '') if isinstance(pub, dict) else '',
            'deck': item.get('deck') or '',
            'count_of_issues': item.get('count_of_issues') or 0,
        })

    _cache[cache_key] = results
    return results


def pick_best_match(series_name: str, results: list[dict]) -> dict | None:
    """Auto-select the best matching result by name similarity. Returns None if ambiguous."""
    if not results:
        return None

    name_lower = series_name.lower().strip()

    # Exact match (case-insensitive)
    for r in results:
        if r['name'].lower().strip() == name_lower:
            return r

    # One substring contains the other
    for r in results:
        r_lower = r['name'].lower().strip()
        if name_lower in r_lower or r_lower in name_lower:
            return r

    # Only one result — return it confidently
    if len(results) == 1:
        return results[0]

    return None  # ambiguous — caller should skip or ask user


def build_comicinfo_xml(series_name: str, volume_num: int, first_issue: int | None,
                         issue_count: int, cv_data: dict | None) -> str:
    """Build a ComicInfo.xml string. Uses cv_data if provided, falls back to local values."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
    ]

    def tag(name: str, val) -> None:
        v = str(val).strip() if val is not None else ''
        if v:
            lines.append(f'  <{name}>{v}</{name}>')

    series = (cv_data.get('name') or series_name) if cv_data else series_name
    tag('Series', series)
    if first_issue is not None:
        tag('Number', first_issue)
    tag('Count', issue_count)
    tag('Volume', volume_num)

    if cv_data:
        tag('Publisher', cv_data.get('publisher', ''))
        tag('Year', cv_data.get('start_year', ''))
        tag('Summary', cv_data.get('deck', ''))

    lines.append('</ComicInfo>')
    return '\n'.join(lines) + '\n'
