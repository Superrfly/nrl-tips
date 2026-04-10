#!/usr/bin/env python3
"""
NRL Tips Generator
==================
Run this each week to scrape tryline.com.au, generate tip cards via Claude API,
and deploy to GitHub Pages.

Usage:
  python run.py --round 4
  python run.py --round 4 --season 2026
  python run.py --round 4 --no-deploy        # generate only, skip git push
  python run.py --round 4 --matches 2661,2662,2663  # specify match IDs manually

Requirements:
  pip install httpx anthropic python-dotenv
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Allow running from any directory
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scraper.tryline import scrape_round, scrape_match
from generator.cards import generate_all_cards
from generator.renderer import save_site


def parse_args():
    parser = argparse.ArgumentParser(description="Generate NRL tip cards")
    parser.add_argument("--round", type=int, required=True, help="NRL round number")
    parser.add_argument("--season", type=int, default=2026, help="Season year (default: 2026)")
    parser.add_argument("--no-deploy", action="store_true", help="Skip git push to GitHub Pages")
    parser.add_argument(
        "--matches",
        type=str,
        default="",
        help="Comma-separated list of match_id:slug pairs, e.g. 2661:2026-round-6-rabbitohs-vs-raiders",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Use cached scraped data if available (skip re-scraping)",
    )
    return parser.parse_args()


def load_env():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env file")
        print("  Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    return api_key


def git_deploy(round_num: int, season: int):
    """Commit and push the generated site to GitHub Pages."""
    print("\nDeploying to GitHub Pages...")
    commands = [
        ["git", "add", "site/index.html"],
        ["git", "commit", "-m", f"tips: Round {round_num}, {season}"],
        ["git", "push"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Git error: {result.stderr}")
            print(f"  Command: {' '.join(cmd)}")
            return False
        print(f"  {' '.join(cmd)} ✓")
    print("\nDeployed! Your friends can view tips at your GitHub Pages URL.")
    return True


def main():
    args = parse_args()
    api_key = load_env()

    cache_file = ROOT / f".cache/round_{args.season}_{args.round}.json"
    cache_file.parent.mkdir(exist_ok=True)

    # --- SCRAPE ---
    if args.cache and cache_file.exists():
        print(f"Loading cached data from {cache_file}")
        with open(cache_file) as f:
            matches = json.load(f)
    else:
        if args.matches:
            # Manual match list provided
            match_slugs = []
            for pair in args.matches.split(","):
                pair = pair.strip()
                if ":" in pair:
                    mid, slug = pair.split(":", 1)
                    match_slugs.append({"match_id": int(mid), "slug": slug})
                else:
                    print(f"WARNING: Skipping invalid match entry: {pair}")
            print(f"\nUsing {len(match_slugs)} manually specified matches...")
            matches = []
            for ms in match_slugs:
                m = scrape_match(ms["match_id"], ms["slug"])
                if m:
                    matches.append(m)
        else:
            matches = scrape_round(args.season, args.round)

        if not matches:
            print("\nNo match data found. Try providing match IDs manually with --matches.")
            print("Example: python run.py --round 4 --matches 2661:2026-round-4-dragons-vs-sea-eagles")
            sys.exit(1)

        # Cache the raw scraped data
        with open(cache_file, "w") as f:
            json.dump(matches, f, indent=2)
        print(f"Scraped data cached to {cache_file}")

    # --- GENERATE ---
    print(f"\nGenerating tip cards for {len(matches)} matches...")
    cards = generate_all_cards(matches, api_key)

    if not cards:
        print("No tip cards generated. Check API key and match data.")
        sys.exit(1)

    # Save cards as JSON too (useful for debugging)
    cards_file = ROOT / f".cache/cards_{args.season}_{args.round}.json"
    with open(cards_file, "w") as f:
        json.dump(cards, f, indent=2)

    # --- RENDER ---
    output = ROOT / "site" / "index.html"
    output.parent.mkdir(exist_ok=True)
    save_site(cards, args.round, args.season, str(output))

    # --- DEPLOY ---
    if not args.no_deploy:
        git_deploy(args.round, args.season)
    else:
        print(f"\nSkipped deployment (--no-deploy). Open {output} to preview locally.")


if __name__ == "__main__":
    main()
