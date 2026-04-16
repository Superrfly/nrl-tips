"""
Parses scoring by position data from the Tools tab text.
"""

POSITIONS = ["LW", "LC", "L2R", "FE", "HLF", "R2R", "RC", "RW", "FB", "PR", "HK", "LK"]

POSITION_LABELS = {
    "LW": "Left Wing", "LC": "Left Centre", "L2R": "Left 2nd Row",
    "FE": "Front Edge", "HLF": "Halfback", "R2R": "Right 2nd Row",
    "RC": "Right Centre", "RW": "Right Wing", "FB": "Fullback",
    "PR": "Prop", "HK": "Hooker", "LK": "Lock",
}


def parse_position_block(block: str) -> list:
    """Parse a single scoring by position block into list of position dicts."""
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    results = []
    for i, line in enumerate(lines):
        if line in POSITIONS:
            prev = lines[i - 1] if i > 0 else None
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if prev and prev.lstrip("-").isdigit() and nxt and nxt.lstrip("-").isdigit():
                results.append({
                    "position": line,
                    "label": POSITION_LABELS.get(line, line),
                    "home_scored": int(prev),
                    "away_conceded": int(nxt),
                })
    return results


def parse_scoring_by_position(tools_text: str) -> dict:
    """
    Parse scoring by position from Tools tab text.
    Tools tab has two views separated by AWAY_TEAM_VIEW marker:
    - Home view: home scored / away conceded
    - Away view: away scored / home conceded

    Returns:
    {
        "home": [{"position", "label", "scored", "conceded"}, ...],  top 3 by scored
        "away": [{"position", "label", "scored", "conceded"}, ...]   top 3 by scored
    }
    """
    # Split into home and away views
    if "AWAY_TEAM_VIEW" in tools_text:
        parts = tools_text.split("AWAY_TEAM_VIEW")
        home_text = parts[0]
        away_text = parts[1] if len(parts) > 1 else ""
    else:
        home_text = tools_text
        away_text = ""

    # Parse home view — gives us home scored and away conceded
    home_idx = home_text.find("Scoring by Position")
    home_positions = []
    if home_idx != -1:
        home_block = home_text[home_idx:home_idx + 1000]
        home_positions = parse_position_block(home_block)

    # Parse away view — gives us away scored and home conceded
    away_idx = away_text.find("Scoring by Position")
    away_positions = []
    if away_idx != -1:
        away_block = away_text[away_idx:away_idx + 1000]
        away_positions = parse_position_block(away_block)

    # Build home perspective from home view
    home = sorted(
        [{"position": p["position"], "label": p["label"],
          "scored": p["home_scored"], "conceded": p["away_conceded"]}
         for p in home_positions],
        key=lambda x: x["scored"], reverse=True
    )[:3]

    # Build away perspective from away view (away is now "home" in that view)
    away = sorted(
        [{"position": p["position"], "label": p["label"],
          "scored": p["home_scored"], "conceded": p["away_conceded"]}
         for p in away_positions],
        key=lambda x: x["scored"], reverse=True
    )[:3]

    # Fallback: if away view failed, derive away from home view
    if not away and home_positions:
        away = sorted(
            [{"position": p["position"], "label": p["label"],
              "scored": p["away_conceded"], "conceded": p["home_scored"]}
             for p in home_positions],
            key=lambda x: x["scored"], reverse=True
        )[:3]

    return {"home": home, "away": away}