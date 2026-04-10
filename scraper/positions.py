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


def parse_scoring_by_position(tools_text: str) -> dict:
    """
    Parse scoring by position from Tools tab text.
    Returns:
        {
            "home": [{"position": "LW", "label": "Left Wing", "scored": 5, "conceded": 3}, ...],
            "away": [{"position": "LW", "label": "Left Wing", "scored": 3, "conceded": 5}, ...]
        }
    Both sorted by scored descending (top scorers first), top 3 only.
    """
    idx = tools_text.find("Scoring by Position")
    if idx == -1:
        return {"home": [], "away": []}

    block = tools_text[idx: idx + 1000]
    lines = [l.strip() for l in block.split("\n") if l.strip()]

    all_positions = []
    for i, line in enumerate(lines):
        if line in POSITIONS:
            prev = lines[i - 1] if i > 0 else None
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if prev and prev.lstrip("-").isdigit() and nxt and nxt.lstrip("-").isdigit():
                all_positions.append({
                    "position": line,
                    "label": POSITION_LABELS.get(line, line),
                    "home_scored": int(prev),
                    "away_conceded": int(nxt),
                })

    home = sorted(
        [{"position": p["position"], "label": p["label"],
          "scored": p["home_scored"], "conceded": p["away_conceded"]}
         for p in all_positions],
        key=lambda x: x["scored"], reverse=True
    )[:3]

    away = sorted(
        [{"position": p["position"], "label": p["label"],
          "scored": p["away_conceded"], "conceded": p["home_scored"]}
         for p in all_positions],
        key=lambda x: x["scored"], reverse=True
    )[:3]

    return {"home": home, "away": away}
