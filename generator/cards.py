import json
import sys
import os
import ollama
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scraper.positions import parse_scoring_by_position
from scraper.parser import parse_match, format_parsed_for_prompt


SYSTEM_PROMPT = """You are an expert NRL analyst producing tip cards for a weekly footy tipping page shared with friends.

You must respond with valid JSON only. No markdown, no explanation, no text outside the JSON.

Produce a JSON object with this exact structure:
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
    { "sentiment": "positive or negative or neutral", "text": "Punchy stat or fact as one sentence." }
  ],
  "injury_notes": [],
  "ats_picks": [
    {
      "player": "Player name",
      "market": "e.g. Anytime Tryscorer",
      "priority": "featured or standard or value",
      "analysis": "2-3 sentence explanation referencing specific stats."
    }
  ],
  "ou_pick": {
    "pick": "Over or Under",
    "line": "e.g. +51.5",
    "reasoning": "One sentence explanation."
  },
  "summary": "One punchy closing sentence."
}

Rules:
- quick_hits: 7-9 points drawing from H2H, form, 1st/2nd half trends, tries per game, scored first %, position matchups, ELO, injuries
- injury_notes: list any OUT players mentioned in the data and their impact. Empty array if none.
- ats_picks: 2-4 picks, mark the single best as featured, reference actual stats
- ou_pick: always provide based on O/U line, scoring averages, and recent totals
- Be direct and confident, write like a knowledgeable punter
- Use Australian spelling
- Only use stats from the provided data, do not invent numbers
- Respond with JSON only, nothing else
"""


def generate_tip_card(match, elo=None):
    home = match["data"].get("home_team", {}).get("display_name", "Home")
    away = match["data"].get("away_team", {}).get("display_name", "Away")
    print(f"  Generating tip card: {home} vs {away}...")

    parsed = parse_match(match)
    tabs = match.get("tabs", {})
    positions = parse_scoring_by_position(tabs.get("tools", ""))
    parsed["positions"] = positions

    prompt_data = format_parsed_for_prompt(parsed, elo)

    # Add injury data to prompt
    home_inj = match.get("home_injuries", {})
    away_inj = match.get("away_injuries", {})
    injury_lines = []
    if home_inj.get("outs") or home_inj.get("ins"):
        injury_lines.append("\n--- INJURY / TEAM CHANGES ---")
        for p in home_inj.get("outs", []):
            injury_lines.append(f"  {home} OUT: {p}")
        for p in home_inj.get("ins", []):
            injury_lines.append(f"  {home} IN: {p}")
    if away_inj.get("outs") or away_inj.get("ins"):
        if not injury_lines:
            injury_lines.append("\n--- INJURY / TEAM CHANGES ---")
        for p in away_inj.get("outs", []):
            injury_lines.append(f"  {away} OUT: {p}")
        for p in away_inj.get("ins", []):
            injury_lines.append(f"  {away} IN: {p}")
    if injury_lines:
        prompt_data += "\n" + "\n".join(injury_lines)

    # Add scoring positions to prompt
    pos_lines = []
    if positions["home"]:
        pos_lines.append("\n--- SCORING BY POSITION ---")
        pos_lines.append(f"{home} top scoring positions:")
        for p in positions["home"]:
            pos_lines.append(f"  {p['position']} ({p['label']}): scored {p['scored']}, conceded {p['conceded']}")
    if positions["away"]:
        pos_lines.append(f"{away} top scoring positions:")
        for p in positions["away"]:
            pos_lines.append(f"  {p['position']} ({p['label']}): scored {p['scored']}, conceded {p['conceded']}")
    if pos_lines:
        prompt_data += "\n" + "\n".join(pos_lines)

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
        card["top_positions_home"] = positions["home"]
        card["top_positions_away"] = positions["away"]
        card["home_team_name"] = home
        card["away_team_name"] = away

        # Inject tryline dotpoints as guaranteed quick hits at the top
        tryline_hits = []
        for dp in parsed.get("home_dotpoints", []):
            tryline_hits.append({"sentiment": "positive", "text": dp})
        for dp in parsed.get("away_dotpoints", []):
            tryline_hits.append({"sentiment": "positive", "text": dp})
        existing = card.get("quick_hits", [])
        card["quick_hits"] = tryline_hits + existing

        return card

    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse JSON for {home} vs {away}: {e}")
        print(f"  Raw snippet: {raw[:300]}")
        return None
    except Exception as e:
        print(f"  ERROR generating tip card for {home} vs {away}: {e}")
        return None


def generate_all_cards(matches, api_key=None):
    cards = []
    for match in matches:
        elo = match.get("elo")
        card = generate_tip_card(match, elo)
        if card:
            cards.append(card)
    print(f"\nGenerated {len(cards)}/{len(matches)} tip cards.")
    return cards