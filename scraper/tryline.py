"""
Scraper for tryline.com.au
Extracts match data from the __next_f JSON embedded in page HTML.
"""

import re
import json
import httpx
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

BASE_URL = "https://tryline.com.au"


def extract_next_data(html: str) -> list[dict]:
    """Extract all __next_f JSON payloads from the page HTML."""
    chunks = []
    # Each self.__next_f.push([1,"..."]) block contains serialised RSC data
    pattern = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.DOTALL)
    for match in pattern.finditer(html):
        raw = match.group(1)
        # Unescape the JS string
        try:
            decoded = raw.encode("utf-8").decode("unicode_escape")
        except Exception:
            decoded = raw
        chunks.append(decoded)
    return chunks


def find_basic_info(chunks: list[str]) -> Optional[dict]:
    """
    Search through RSC chunks for the basicInfo object which contains
    all the match data we need.
    """
    for chunk in chunks:
        # Look for the basicInfo key
        idx = chunk.find('"basicInfo":{')
        if idx == -1:
            continue
        # Find the start of the object
        start = chunk.index("{", idx + len('"basicInfo":'))
        # Walk forward counting braces to find the matching close
        depth = 0
        for i, ch in enumerate(chunk[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(chunk[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def find_fixtures(chunks: list[str]) -> list[dict]:
    """
    Search for a fixtures/matches list in the page data.
    Returns list of match dicts with match_id and slug.
    """
    matches = []
    for chunk in chunks:
        # Look for arrays of match objects
        for m in re.finditer(r'"match_id":(\d+),"slug":"([^"]+)"', chunk):
            matches.append({"match_id": int(m.group(1)), "slug": m.group(2)})
    # Deduplicate
    seen = set()
    unique = []
    for m in matches:
        if m["match_id"] not in seen:
            seen.add(m["match_id"])
            unique.append(m)
    return unique


def scrape_fixtures_page(season: int, round_num: int) -> list[dict]:
    """
    Scrape the fixtures listing page to get all match IDs for a given round.
    URL pattern: tryline.com.au/nrl/fixtures?season=2026&round=4
    Falls back to homepage if that doesn't work.
    """
    urls_to_try = [
        f"{BASE_URL}/nrl/fixtures?season={season}&round={round_num}",
        f"{BASE_URL}/nrl?season={season}&round={round_num}",
        f"{BASE_URL}/",
    ]

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        for url in urls_to_try:
            try:
                print(f"  Trying fixtures URL: {url}")
                r = client.get(url)
                if r.status_code == 200:
                    chunks = extract_next_data(r.text)
                    matches = find_fixtures(chunks)
                    if matches:
                        print(f"  Found {len(matches)} matches at {url}")
                        return matches
            except Exception as e:
                print(f"  Error fetching {url}: {e}")

    return []


def scrape_match(match_id: int, slug: str) -> Optional[dict]:
    """
    Scrape a single match page and return structured data.
    """
    url = f"{BASE_URL}/match/{match_id}/{slug}"
    print(f"  Scraping: {url}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        try:
            r = client.get(url)
            r.raise_for_status()
        except Exception as e:
            print(f"  ERROR fetching match {match_id}: {e}")
            return None

    chunks = extract_next_data(r.text)
    basic_info = find_basic_info(chunks)

    if not basic_info:
        print(f"  WARNING: Could not extract basicInfo for match {match_id}")
        # Fallback: try to find any JSON block with home_team/away_team
        for chunk in chunks:
            if '"home_team"' in chunk and '"away_team"' in chunk:
                try:
                    # Try to find a JSON object containing both
                    for m in re.finditer(r'(\{[^{}]*"home_team"[^{}]*\})', chunk):
                        obj = json.loads(m.group(1))
                        if "home_team" in obj and "away_team" in obj:
                            basic_info = obj
                            break
                except Exception:
                    pass
        if not basic_info:
            return None

    return {
        "match_id": match_id,
        "slug": slug,
        "url": url,
        "data": basic_info,
    }


def scrape_round(season: int, round_num: int, match_slugs: Optional[list[dict]] = None) -> list[dict]:
    """
    Scrape all matches for a given round.
    If match_slugs is provided, use those directly.
    Otherwise attempt to discover them from the fixtures page.
    """
    if match_slugs:
        fixtures = match_slugs
    else:
        print(f"\nDiscovering fixtures for Season {season} Round {round_num}...")
        fixtures = scrape_fixtures_page(season, round_num)

    if not fixtures:
        print("  No fixtures found automatically. You may need to provide match IDs manually.")
        return []

    print(f"\nScraping {len(fixtures)} matches...")
    results = []
    for f in fixtures:
        match_data = scrape_match(f["match_id"], f["slug"])
        if match_data:
            results.append(match_data)

    print(f"\nSuccessfully scraped {len(results)}/{len(fixtures)} matches.")
    return results
