#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scraper.tryline import scrape_round, scrape_match
from analyser import analyse_round
from scraper.injuries import fetch_injury_data, get_team_injuries, _team_names_from_slug
from generator.cards import generate_all_cards
from generator.renderer import save_site


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--no-deploy", action="store_true")
    parser.add_argument("--matches", type=str, default="")
    return parser.parse_args()


def git_deploy(round_num, season):
    print("\nDeploying to GitHub Pages...")
    for cmd in [
        ["git", "add", "site/index.html"],
        ["git", "commit", "-m", f"tips: Round {round_num} {season}"],
        ["git", "push"],
    ]:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Git error: {result.stderr.strip()}")
            return False
        print(f"  {' '.join(cmd)} OK")
    print("  Deployed.")
    return True


def main():
    args = parse_args()
    round_num = args.round
    season = args.season

    print(f"\n=== NRL Tips — Round {round_num}, {season} ===\n")

    if args.matches:
        match_slugs = []
        for pair in args.matches.split(","):
            pair = pair.strip()
            if ":" in pair:
                mid, slug = pair.split(":", 1)
                match_slugs.append({"match_id": int(mid), "slug": slug})
        print(f"Scraping {len(match_slugs)} specified matches...")
        matches = []
        for ms in match_slugs:
            data = scrape_match(ms["match_id"], ms["slug"])
            if data:
                matches.append(data)
    else:
        matches = scrape_round(season, round_num)

    if not matches:
        print("No match data found.")
        sys.exit(1)

    print(f"\nScraped {len(matches)} matches.")

    analysis = analyse_round(matches, season=season, round_num=round_num)

    print("\nFetching injury data from NRL.com...")
    injury_data = fetch_injury_data(season, round_num, matches=matches)

    for match in matches:
        match_id = str(match.get("match_id"))
        if match_id in analysis:
            match["elo"] = analysis[match_id]
        match["home_injuries"] = get_team_injuries(match_id, "home", injury_data)
        match["away_injuries"] = get_team_injuries(match_id, "away", injury_data)
        home_inj = match["home_injuries"]
        away_inj = match["away_injuries"]
        home_name = match.get("data", {}).get("home_team", {}).get("display_name", "")
        away_name = match.get("data", {}).get("away_team", {}).get("display_name", "")
        if not home_name or not away_name:
            home_name, away_name = _team_names_from_slug(match.get("slug", ""))
        if home_inj.get("ins") or home_inj.get("outs"):
            print(f"  {home_name} — IN: {home_inj.get('ins', [])} | OUT: {home_inj.get('outs', [])}")
        if away_inj.get("ins") or away_inj.get("outs"):
            print(f"  {away_name} — IN: {away_inj.get('ins', [])} | OUT: {away_inj.get('outs', [])}")

    print(f"\nGenerating tip cards via Ollama (gemma3:12b)...")
    cards = generate_all_cards(matches)

    if not cards:
        print("No cards generated.")
        sys.exit(1)

    for card, match in zip(cards, matches):
        elo = match.get("elo", {})
        if elo:
            card["win_prob_home"] = elo.get("home_win_prob")
            card["elo_home"] = elo.get("home_elo")
            card["elo_away"] = elo.get("away_elo")
            card["elo_recommendation"] = elo.get("recommendation", "")

        home_inj = match.get("home_injuries", {})
        away_inj = match.get("away_injuries", {})
        home_name = match.get("data", {}).get("home_team", {}).get("display_name", "Home")
        away_name = match.get("data", {}).get("away_team", {}).get("display_name", "Away")

        all_injury_notes = []
        for player in home_inj.get("outs", []):
            all_injury_notes.append(f"{home_name}: {player} — OUT")
        for player in away_inj.get("outs", []):
            all_injury_notes.append(f"{away_name}: {player} — OUT")
        for player in home_inj.get("ins", []):
            all_injury_notes.append(f"{home_name}: {player} — IN")
        for player in away_inj.get("ins", []):
            all_injury_notes.append(f"{away_name}: {player} — IN")
        if all_injury_notes:
            card["injury_notes"] = all_injury_notes

    os.makedirs(ROOT / "site", exist_ok=True)
    save_site(cards, round_num, season, output_path=str(ROOT / "site" / "index.html"))

    if not args.no_deploy:
        git_deploy(round_num, season)
    else:
        print(f"\nDone. Open site/index.html to preview.")

    print(f"\n{len(cards)}/{len(matches)} tip cards generated.")


if __name__ == "__main__":
    main()
