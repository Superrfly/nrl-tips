"""
Generates NRL tip cards using Ollama (local AI - free).
Uses data from all 4 tryline tabs: Preview, Lineup, Stats, Tools.
"""

import json
import ollama
from typing import Optional


def format_match_for_prompt(match: dict) -> str:
    """Convert raw scraped match data into a clean prompt-ready string."""
    d = match.get("data", {})
    tabs = match.get("tabs", {})

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
        "=" * 60,
        f"MATCH: {home.get('display_name')} vs {away.get('display_name')}",
        f"Round: {d.get('round_text')}, {season.get('value')}",
        f"Venue: {venue.get('name')}",
        "=" * 60,
        "",
        "--- LADDER POSITIONS ---",
        f"HOME: {home.get('display_name')} ({home.get('display_name_code')})",
        f"  Rank: {home_rank.get('rank')}th | W{home_rank.get('wins')}-L{home_rank.get('lost')}-D{home_rank.get('drawn')} | Played: {home_rank.get('played')} | Points diff: {home_rank.get('diff')}",
        "",
        f"AWAY: {away.get('display_name')} ({away.get('display_name_code')})",
        f"  Rank: {away_rank.get('rank')}th | W{away_rank.get('wins')}-L{away_rank.get('lost')}-D{away_rank.get('drawn')} | Played: {away_rank.get('played')} | Points diff: {away_rank.get('diff')}",
        "",
        "--- PREVIEW ANALYSIS ---",
        analysis,
        "",
    ]

    if home_dotpoints:
        lines.append(f"PREMATCH INSIGHTS — {home.get('display_name')}:")
        for dp in home_dotpoints:
            lines.append(f"  • {dp}")
        lines.append("")

    if away_dotpoints:
        lines.append(f"PREMATCH INSIGHTS — {away.get('display_name')}:")
        for dp in away_dotpoints:
            lines.append(f"  • {dp}")
        lines.append("")

    # Add tab data — clean and truncate to avoid overwhelming the model
    if tabs.get("lineup"):
        lines.append("--- LINEUP ---")
        lines.append(tabs["lineup"][:2000])
        lines.append("")

    if tabs.get("stats"):
        lines.append("--- STATS (H2H, Tryscorers, First Try, Half Scores) ---")
        lines.append(tabs["stats"][:3000])
        lines.append("")

    if tabs.get("tools"):
        lines.append("--- TOOLS (Attack/Defence Rankings, Scoring by Position) ---")
        lines.append(tabs["tools"][:3000])
        lines.append("")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are an expert NRL analyst producing tip cards for a weekly footy tipping page shared with friends.

You must respond with valid JSON only. No markdown, no explanation, no text outside the JSON.

Given match data from all sections of a match preview (ladder, analysis, lineups, H2H stats, tryscorer history, attack/defence rankings, scoring by position), produce a JSON object with this exact structure:

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
  "top_positions_home": [
    { "position": "e.g. FB", "scored": 3, "conceded": 1 }
  ],
  "top_positions_away": [
    { "position": "e.g. RW", "scored": 4, "conceded": 2 }
  ],
  "ats_picks": [
    {
      "player": "Player name",
      "market": "e.g. Anytime Tryscorer",
      "priority": "featured or standard or value",
      "analysis": "2-3 sentence explanation of why this is a good bet."
    }
  ],
  "summary": "One punchy closing sentence summarising the tip and best bet."
}

Rules:
- quick_hits: 6-8 bullet points. Draw from H2H records, form, attack/defence ranks, scoring position data, tryscorer history, lineup notes, half-time scoring trends.
- top_positions_home and top_positions_away: top 3 scoring positions for each team from the Tools/scoring by position data. If not available leave as empty array.
- ats_picks: 2-4 picks. Mark the single best one as "featured". Use tryscorer history and position matchup data to justify picks.
- Be direct and confident. Write like a knowledgeable punter, not a journalist.
- Use Australian spelling (favour, colour, etc).
- Only reference stats that appear in the provided data. Do not invent numbers.
- Respond with JSON only, nothing else.
"""


def generate_tip_card(match: dict) -> Optional[dict]:
    """Call Ollama to generate a tip card for one match."""
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
        print(f"  Raw output snippet: {raw[:300]}")
        return None
    except Exception as e:
        print(f"  ERROR generating tip card for {home} vs {away}: {e}")
        return None


def generate_all_cards(matches: list[dict], api_key: str = None) -> list[dict]:
    """Generate tip cards for all scraped matches using Ollama."""
    cards = []
    for match in matches:
        card = generate_tip_card(match)
        if card:
            cards.append(card)
    print(f"\nGenerated {len(cards)}/{len(matches)} tip cards.")
    return cards
