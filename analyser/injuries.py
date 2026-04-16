"""
analyser/injuries.py
====================
Scrapes NRL.com for the latest injury/team list updates.
Published each Thursday. Flags key position absences that affect tip confidence.

No API key needed.
"""

import httpx
from bs4 import BeautifulSoup
import re


NRL_INJURIES_URL = "https://www.nrl.com/draw/nrl-premiership/{season}/round-{round}/"

# Positions that have the highest impact on match outcomes
HIGH_IMPACT_POSITIONS = {
    "halfback", "half", "five-eighth", "five eighth", "hooker",
    "fullback", "lock", "prop", "winger"
}


def fetch_injury_news(season: int = 2026, round_num: int = 1) -> dict[str, list[str]]:
    """
    Scrapes NRL.com draw page for team list / injury notes.
    Returns {team_name: [injury_note, ...]}

    Falls back to empty dict if unavailable.
    """
    injuries = {}
    try:
        url = NRL_INJURIES_URL.format(season=season, round=round_num)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # NRL.com renders match cards with team info
        # Look for injury/out markers in the squad lists
        for match_block in soup.select(".match-header, .draw-card, [class*='match']"):
            teams = match_block.select("[class*='team-name'], .team-name, h3")
            outs = match_block.select("[class*='injury'], [class*='out'], .player-out")
            for team_el in teams:
                team_name = team_el.get_text(strip=True)
                if team_name and len(team_name) > 2:
                    injuries.setdefault(team_name, [])
            for out_el in outs:
                note = out_el.get_text(strip=True)
                if note:
                    # Try to associate with nearest team
                    parent_team = out_el.find_parent("[class*='team']")
                    if parent_team:
                        team_el = parent_team.select_one("[class*='team-name']")
                        if team_el:
                            injuries.setdefault(team_el.get_text(strip=True), []).append(note)

    except Exception as e:
        print(f"  [Injuries] Could not fetch NRL injury data ({e}). Continuing without.")

    return injuries


def injury_impact(team: str, injury_data: dict[str, list[str]]) -> dict:
    """
    Returns injury summary for a team.
    {
        has_injuries: bool,
        notes: [str],
        high_impact: bool,  # True if key positions affected
    }
    """
    notes = []
    for key, vals in injury_data.items():
        if team.lower() in key.lower() or key.lower() in team.lower():
            notes.extend(vals)

    high_impact = any(
        pos in note.lower()
        for note in notes
        for pos in HIGH_IMPACT_POSITIONS
    )

    return {
        "has_injuries": bool(notes),
        "notes": notes,
        "high_impact": high_impact,
    }
