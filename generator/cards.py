"""
Generates NRL tip cards using Ollama (local AI - free).
"""

import json
import ollama
from typing import Optional


def format_match_for_prompt(match: dict) -> str:
    d = match["data"]
    home = d.get("home_team", {})
    away = d.get("away_team", {})
    venue = d.get("venue", {})
    season = d.get("season", {})
    home_rank = home.get("ranking", {})
    away_rank = away.get("ranking", {})
    home_dotpoints = d.get("home_team_dotpoints") or []
    away_dotpoints = d.get("away_team_dotpoints") or []
    analysis = d.get("analysis", "")

    lines = [
        f"MATCH: {home.get('display_name')} vs {away.get('display_name')}",
        f"Round: {d.get('round_text')}, {season.get('value')}",
        f"Venue: {venue.get('name')}",
        "",
        f"HOME: {home.get('display_name')}",
        f"  Ladder: {home_rank.get('rank')}th | W{home_rank.get('wins')}-L{home_rank.get('lost')}-D{home_rank.get('drawn')} | Points diff: {home_rank.get('diff')}",
        "",
        f"AWAY: {away.get('display_name')}",
        f"  Ladder: {away_rank.get('rank')}th | W{away_rank.get('wins')}-L{away_rank.get('lost')}-D{away_rank.get('drawn')} | Points diff: {away_rank.get('diff')}",
        "",
        "PREVIEW ANALYSIS:",
        analysis,
        "",
    ]

    if home_dotpoints:
        lines.append(f"INSIGHTS — {home.get('display_name')}:")
        for dp in home_dotpoints:
            lines.append(f"  • {dp}")
        lines.append("")

    if away_dotpoints:
        lines.append(f"INSIGHTS — {away.get('display_name')}:")
        for dp in away_dotpoints:
            lines.append(f"  • {dp}")
        lines.append("")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are an expert NRL analyst producing tip cards for a weekly footy tipping page.

You must respond with valid JSON only. No markdown, no explanation, no text outside the JSON.

Given match data, produce a JSON object with this exact structure:
{
  "home_team": "Full team name",
  "away_team": "Full team name",
  "round": "Round X",
  "season": "2026",
  "venue": "Venue name",
  "tip": "Home or Away",
  "tip_team": "Full name of tipped team",
  "confidence": "High or Medium or Low",
  "quick_hits": [
    { "sentiment": "positive or negative or neutral", "text": "Punchy stat or fact." }
  ],
  "ats_picks": [
    {
      "player": "Player name",
      "market": "e.g. Anytime Tryscorer",
      "priority": "featured or standard or value",
      "analysis": "2-3 sentence explanation."
    }
  ],
  "summary": "One punchy closing sentence."
}

Rules:
- quick_hits: 5-7 points mixing H2H, form, attack/defence stats, player notes
- ats_picks: 2-4 picks, mark best one as featured
- Be direct and confident, write like a knowledgeable punter
- Only use stats provided in the data, do not invent numbers
- Respond with JSON only, nothing else
"""


def generate_tip_card(match: dict) -> Optional[dict]:
    prompt_data = format_match_for_prompt(match)
    home = match["data"].get("home_team", {}).get("display_name", "Home")
    away = match["data"].get("away_team", {}).get("display_name", "Away")
    print(f"  Generating tip card: {home} vs {away}...")

    try:
        response = ollama.chat(
            model="gemma3:12b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate a tip card for this match:\n\n{prompt_data}"},
            ],
            options={"temperature": 0.7},
        )
        raw = response["message"]["content"].strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        card = json.loads(raw)
        card["match_url"] = match["url"]
        return card

    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse JSON for {home} vs {away}: {e}")
        return None
    except Exception as e:
        print(f"  ERROR generating tip card for {home} vs {away}: {e}")
        return None


def generate_all_cards(matches: list[dict], api_key: str = None) -> list[dict]:
    cards = []
    for match in matches:
        card = generate_tip_card(match)
        if card:
            cards.append(card)
    print(f"\nGenerated {len(cards)}/{len(matches)} tip cards.")
    return cards
