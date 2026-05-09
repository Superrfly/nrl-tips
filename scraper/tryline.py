"""
Scraper for tryline.com.au
Uses Playwright to render pages and click through all 4 tabs:
Preview, Lineup, Stats, Tools
"""

import re
import json
import time
from typing import Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout


BASE_URL = "https://tryline.com.au"


def get_page_html(url: str, wait_ms: int = 2000) -> str:
    """Fetch fully rendered page HTML using headless Chromium."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-AU",
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def scrape_all_tabs(url: str) -> dict:
    results = {
        "preview": "",
        "lineup": "",
        "stats": "",
        "tools": "",
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="en-AU",
            )
            page = context.new_page()

            print(f"    Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Preview tab (default)
            print(f"    Scraping Preview tab...")
            try:
                results["preview"] = page.inner_text("main") or ""
            except Exception as e:
                print(f"    WARNING: Preview failed: {e}")

            # Lineup tab
            print(f"    Scraping Lineup tab...")
            try:
                page.click("text=Lineup", timeout=5000)
                page.wait_for_timeout(2000)
                results["lineup"] = page.inner_text("main") or ""
            except Exception as e:
                print(f"    WARNING: Lineup failed: {e}")

            # Stats tab
            print(f"    Scraping Stats tab...")
            try:
                page.click("text=Stats", timeout=5000)
                page.wait_for_timeout(2000)
                results["stats"] = page.inner_text("main") or ""
            except Exception as e:
                print(f"    WARNING: Stats failed: {e}")

            # Tools tab
            print(f"    Scraping Tools tab...")
            try:
                page.click("text=Tools", timeout=5000)
                page.wait_for_timeout(2000)

                # Click Select All so all teams appear in the comparison table
                try:
                    page.click("text=Select All", timeout=3000)
                    page.wait_for_timeout(1000)
                    print(f"    Selected all teams for position comparison")
                except Exception as e:
                    print(f"    WARNING: Could not click Select All: {e}")

                # Click every "Show All" button to expand truncated table rows
                for _ in range(4):
                    try:
                        page.click("text=Show All", timeout=2000)
                        page.wait_for_timeout(600)
                    except Exception:
                        break

                results["tools"] = page.inner_text("main") or ""
                print(f"    Tools tab scraped ({len(results['tools'])} chars)")

            except Exception as e:
                print(f"    WARNING: Tools tab failed: {e}")

            browser.close()

    except Exception as e:
        print(f"  ERROR in scrape_all_tabs: {e}")

    return results


def extract_next_chunks(html: str) -> list[str]:
    """Extract all __next_f serialised RSC payload strings from the HTML."""
    chunks = []
    pattern = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.DOTALL)
    for match in pattern.finditer(html):
        raw = match.group(1)
        try:
            decoded = raw.encode("utf-8").decode("unicode_escape")
        except Exception:
            decoded = raw
        chunks.append(decoded)
    return chunks


def find_basic_info(html: str) -> Optional[dict]:
    """Extract the basicInfo JSON object from page HTML."""
    chunks = extract_next_chunks(html)
    for chunk in chunks:
        idx = chunk.find('"basicInfo":{')
        if idx == -1:
            idx = chunk.find('"basicInfo":')
            if idx == -1:
                continue
        brace_start = chunk.index("{", idx + len('"basicInfo":'))
        depth = 0
        for i, ch in enumerate(chunk[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(chunk[brace_start: i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def find_match_ids_in_html(html: str) -> list[dict]:
    """Scan HTML for match_id + slug pairs."""
    matches = []
    seen = set()
    for m in re.finditer(r'"match_id":(\d+),"slug":"(2026[^"]+)"', html):
        mid = int(m.group(1))
        slug = m.group(2)
        if mid not in seen:
            seen.add(mid)
            matches.append({"match_id": mid, "slug": slug})
    return matches


def scrape_fixtures(season: int, round_num: int) -> list[dict]:
    """Try to discover all match IDs for a given round."""
    urls = [
        f"{BASE_URL}/nrl/fixtures?season={season}&round={round_num}",
        f"{BASE_URL}/nrl?season={season}&round={round_num}",
        BASE_URL + "/",
    ]
    for url in urls:
        print(f"  Checking fixtures at: {url}")
        try:
            html = get_page_html(url)
            all_matches = find_match_ids_in_html(html)
            round_matches = [
                m for m in all_matches
                if f"round-{round_num}-" in m["slug"] or f"round-{round_num:02d}-" in m["slug"]
            ]
            if round_matches:
                print(f"  Found {len(round_matches)} matches for Round {round_num}")
                return round_matches
            elif all_matches:
                print(f"  Found {len(all_matches)} matches (unfiltered)")
                return all_matches
        except Exception as e:
            print(f"  Error at {url}: {e}")
    return []


def scrape_match(match_id: int, slug: str) -> Optional[dict]:
    """
    Scrape all 4 tabs for a single match page.
    Returns structured data dict.
    """
    url = f"{BASE_URL}/match/{match_id}/{slug}"
    print(f"\n  Scraping: {url}")

    # First load the page normally to get basicInfo from the HTML
    try:
        html = get_page_html(url)
        basic_info = find_basic_info(html)
    except Exception as e:
        print(f"  ERROR on initial load: {e}")
        basic_info = None

    # Now scrape all tabs with Playwright
    try:
        tab_data = scrape_all_tabs(url)
    except Exception as e:
        print(f"  ERROR scraping tabs: {e}")
        tab_data = {"preview": "", "lineup": "", "stats": "", "tools": ""}

    if not basic_info and not any(tab_data.values()):
        print(f"  FAILED: No data found for match {match_id}")
        return None

    return {
        "match_id": match_id,
        "slug": slug,
        "url": url,
        "data": basic_info or {},
        "tabs": tab_data,
    }


def scrape_round(season: int, round_num: int, match_slugs: Optional[list[dict]] = None) -> list[dict]:
    """Scrape all matches for a given round."""
    if match_slugs:
        fixtures = match_slugs
    else:
        print(f"\nDiscovering fixtures for Season {season} Round {round_num}...")
        fixtures = scrape_fixtures(season, round_num)

    if not fixtures:
        print("  Could not auto-discover fixtures. Use --matches to specify them manually.")
        return []

    print(f"\nScraping {len(fixtures)} match pages (all 4 tabs each)...")
    results = []
    for f in fixtures:
        data = scrape_match(f["match_id"], f["slug"])
        if data:
            results.append(data)

    print(f"\nDone: {len(results)}/{len(fixtures)} matches scraped.")
    return results
