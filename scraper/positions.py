"""
Parses scoring by position data from the Tools tab text (post-Select All).
The tab shows a league-wide comparison table in tab-separated format.
"""

POSITIONS = ["LW", "LC", "L2R", "FE", "HLF", "R2R", "RC", "RW", "FB", "PR", "HK", "LK"]

POSITION_LABELS = {
    "LW": "Left Wing", "LC": "Left Centre", "L2R": "Left 2nd Row",
    "FE": "Front Edge", "HLF": "Halfback", "R2R": "Right 2nd Row",
    "RC": "Right Centre", "RW": "Right Wing", "FB": "Fullback",
    "PR": "Prop", "HK": "Hooker", "LK": "Lock",
}

_SKIP_LINES = {
    "2026", "2025", "All Rounds", "Show All", "Relative", "Select All",
    "Example - Conceding to LW means opposition LW has scored X tries against them",
    "NRL Scoring by Position", "Select 2 or more teams to compare side by side",
}


def _parse_table_section(text: str, section_header: str) -> dict[str, dict[str, int]]:
    """Return {team_short_name_lower: {position: count}} for a scored/conceded section."""
    idx = text.find(section_header)
    if idx == -1:
        return {}

    chunk = text[idx + len(section_header):]
    lines = chunk.split("\n")

    header: list[str] = []
    result: dict[str, dict[str, int]] = {}
    current_team: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Stop when the next section starts
        if "Tries Scored By Position" in stripped or "Tries Conceded By Position" in stripped:
            break

        if stripped in _SKIP_LINES:
            continue

        # Header row: tab-indented, contains position codes
        if line.startswith("\t") and not header:
            cols = [c.strip() for c in line.split("\t") if c.strip()]
            if any(c in POSITIONS for c in cols):
                header = cols
            continue

        # Data row: tab-indented numbers
        if line.startswith("\t") and header and current_team is not None:
            vals = [v.strip() for v in line.split("\t") if v.strip()]
            if vals and all(v.lstrip("-").isdigit() for v in vals):
                nums = [int(v) for v in vals]
                result[current_team] = dict(zip(header, nums))
            continue

        # Team name row: not tab-indented
        if not line.startswith("\t") and stripped:
            current_team = stripped.lower()

    return result


def _find_team(data: dict[str, dict], team_name: str) -> dict[str, int]:
    """Find a team's row by matching the last word of the team name."""
    if not team_name:
        return {}
    short = team_name.strip().split()[-1].lower()
    if short in data:
        return data[short]
    for key in data:
        if short in key or key in short:
            return data[key]
    return {}


def _top_positions(scored: dict[str, int], opp_conceded: dict[str, int], top_n: int = 4) -> list[dict]:
    rows = []
    for pos in POSITIONS:
        s = scored.get(pos, 0)
        if s > 0:
            rows.append({
                "position": pos,
                "label": POSITION_LABELS.get(pos, pos),
                "scored": s,
                "opp_conceded": opp_conceded.get(pos, 0),
            })
    return sorted(rows, key=lambda x: x["scored"], reverse=True)[:top_n]


def parse_scoring_by_position(tools_text: str, home_team: str = "", away_team: str = "") -> dict:
    """
    Parse scoring/conceding by position for home and away teams.

    Returns:
    {
        "home": [{"position", "label", "scored", "opp_conceded"}, ...],  # top 4
        "away": [{"position", "label", "scored", "opp_conceded"}, ...],  # top 4
    }
    scored      = tries this team scored at that position
    opp_conceded = tries the opponent concedes at that position
    """
    scored_data = _parse_table_section(tools_text, "Tries Scored By Position")
    conceded_data = _parse_table_section(tools_text, "Tries Conceded By Position")

    home_scored = _find_team(scored_data, home_team)
    home_conceded = _find_team(conceded_data, home_team)
    away_scored = _find_team(scored_data, away_team)
    away_conceded = _find_team(conceded_data, away_team)

    return {
        "home": _top_positions(home_scored, away_conceded),
        "away": _top_positions(away_scored, home_conceded),
    }
