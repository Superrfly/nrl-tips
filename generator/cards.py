"""
Generates NRL tip cards using the Anthropic API.
Takes scraped match data and produces structured analysis.
"""

import json
import anthropic
from typing import Optional


def format_match_for_prompt(match: dict) -> str:
    """Convert raw scraped match data into a clean prompt-ready string."""
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
        f"Status: {d.get('status')}",
        "",
        f"HOME: {home.get('display_name')} ({home.get('display_name_code')})",
        f"  Ladder: {home_rank.get('rank')}th | W{home_rank.get('wins')}-L{home_rank.get('lost')}-D{home_rank.get('drawn')} | {home_rank.get('played')} played | Points diff: {home_rank.get('diff')}",
        "",
        f"AWAY: {away.get('display_name')} ({away.get('display_name_code')})",
        f"  Ladder: {away_rank.get('rank')}th | W{away_rank.get('wins')}-L{away_rank.get('lost')}-D{away_rank.get('drawn')} | {away_rank.get('played')} played | Points diff: {away_rank.get('diff')}",
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


SYSTEM_PROMPT = """You are an expert NRL analyst producing tip cards for a weekly footy tipping page shared with friends.

Your output must be valid JSON only — no markdown, no preamble, no explanation outside the JSON.

Given match data, produce a JSON object with this exact structure:
{
  "home_team": "Full team name",
  "away_team": "Full team name",
  "round": "Round X",
  "season": "2026",
  "venue": "Venue name",
  "tip": "Home" or "Away",
  "tip_team": "Full name of tipped team",
  "confidence": "High", "Medium" or "Low",
  "quick_hits": [
    { "sentiment": "positive" | "negative" | "neutral", "text": "Fact or stat as a punchy sentence." }
  ],
  "ats_picks": [
    {
      "player": "Player name",
      "market": "e.g. Anytime Tryscorer",
      "odds": "e.g. $2.50 (approx)",
      "priority": "featured" | "standard" | "value",
      "analysis": "2-3 sentence explanation of why this is a good bet."
    }
  ],
  "summary": "One punchy closing sentence summarising the tip and best bet."
}

Rules:
- quick_hits: 5-7 bullet points. Mix of H2H trends, form, attack/defence stats, individual player notes.
- ats_picks: 2-4 picks. Mark the best one as "featured". Include approx odds if inferable, otherwise omit odds field.
- Be direct and confident. Write like a knowledgeable punter, not a journalist.
- Use Australian spelling (favour, colour, etc).
- Do not invent specific statistics not provided in the data. If data is thin, note what's available and be appropriately measured.
"""


def generate_tip_card(match: dict, client: anthropic.Anthropic) -> Optional[dict]:
    """Call Claude API to generate a tip card for one match."""
    prompt_data = format_match_for_prompt(match)

    home = match["data"].get("home_team", {}).get("display_name", "Home")
    away = match["data"].get("away_team", {}).get("display_name", "Away")

    print(f"  Generating tip card: {home} vs {away}...")

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a tip card for this match:\n\n{prompt_data}",
                }
            ],
        )

        raw = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        card = json.loads(raw)
        card["match_url"] = match["url"]
        return card

    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse JSON response for {home} vs {away}: {e}")
        return None
    except Exception as e:
        print(f"  ERROR generating tip card for {home} vs {away}: {e}")
        return None


def generate_all_cards(matches: list[dict], api_key: str) -> list[dict]:
    """Generate tip cards for all scraped matches."""
    client = anthropic.Anthropic(api_key=api_key)
    cards = []

    for match in matches:
        card = generate_tip_card(match, client)
        if card:
            cards.append(card)

    print(f"\nGenerated {len(cards)}/{len(matches)} tip cards.")
    return cards
