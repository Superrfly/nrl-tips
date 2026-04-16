"""
scraper/parser.py
=================
Extracts structured data from all 4 tryline tab text dumps.
Includes: H2H, tryscorers, half scores, lineups, attack/defence,
O/U with recent totals, and first try scorer data.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# PREVIEW TAB
# ---------------------------------------------------------------------------

def parse_h2h(preview_text: str) -> dict:
    """Extract H2H record and last 5 H2H scorelines."""
    result = {"home_wins": 0, "away_wins": 0, "draws": 0, "last_5": []}

    m = re.search(r'(\d+)\s*Wins\s*(\d+)\s*Draws\s*(\d+)\s*Wins', preview_text)
    if m:
        result["home_wins"] = int(m.group(1))
        result["draws"] = int(m.group(2))
        result["away_wins"] = int(m.group(3))

    score_pattern = re.compile(
        r'(Round \d+,\s*\d+)\s*\n\s*([\w\s]+?)\s*\n\s*(\d+)\s*-\s*(\d+)\s*\n\s*([\w\s]+)',
        re.MULTILINE
    )
    for m in score_pattern.finditer(preview_text):
        result["last_5"].append({
            "round": m.group(1).strip(),
            "home": m.group(2).strip(),
            "home_score": int(m.group(3)),
            "away_score": int(m.group(4)),
            "away": m.group(5).strip(),
        })

    return result


# ---------------------------------------------------------------------------
# STATS TAB
# ---------------------------------------------------------------------------

def parse_tryscorers(stats_text: str) -> list:
    """
    Extract season tryscorer strike rates.
    Note: these are SEASON rates, not H2H specific.
    Returns: [{"player": "A. Johnston", "rate": "100%", "record": "4/4"}, ...]
    """
    scorers = []
    pattern = re.compile(r'([A-Z]\.\s[\w\'\-]+)\s*\n\s*(\d+%)\s*\((\d+/\d+)\)')
    for m in pattern.finditer(stats_text):
        scorers.append({
            "player": m.group(1).strip(),
            "rate": m.group(2),
            "record": m.group(3),
        })
    return scorers[:5]


def parse_first_try_data(stats_text: str) -> dict:
    """
    Extract first try scorer data for both teams.
    
    Stats tab format:
    First Try
    Team vs          First Try    Minute
    Opponent         tick/cross   4:48
    ...
    
    Returns:
    {
        "home": [{"opponent": str, "scored_first": bool, "minute": str}, ...],
        "away": [{"opponent": str, "scored_first": bool, "minute": str}, ...],
        "home_scored_first_count": int,
        "home_games": int,
        "away_scored_first_count": int,
        "away_games": int,
    }
    """
    result = {
        "home": [],
        "away": [],
        "home_scored_first_count": 0,
        "home_games": 0,
        "away_scored_first_count": 0,
        "away_games": 0,
    }

    idx = stats_text.find("First Try")
    if idx == -1:
        return result

    block = stats_text[idx:idx + 800]
    lines = [l.strip() for l in block.split("\n") if l.strip()]

    # Time pattern e.g. "4:48", "10:42", "12:00"
    time_pattern = re.compile(r'^\d+:\d+$')
    # Team code pattern — 3 uppercase letters or common team short names
    skip = {"First", "Try", "Minute", "Ladder", "Stats", "Round", "H2H", "Preview", "Lineup", "Tools"}

    current_team = "home"
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect switch to away team section
        if "vs" in line and i > 2:
            current_team = "away"
            i += 1
            continue

        # Time pattern = this is a first try minute entry
        if time_pattern.match(line):
            # Look back for opponent name and tick/cross
            opponent = ""
            scored_first = False
            # Scan back up to 3 lines for opponent
            for back in range(1, 4):
                if i - back >= 0:
                    prev = lines[i - back]
                    if prev in ("✓", "✗", "×"):
                        scored_first = (prev == "✓")
                    elif (len(prev) > 1 and
                          prev not in skip and
                          not time_pattern.match(prev) and
                          not prev.isdigit()):
                        opponent = prev
                        break

            entry = {
                "opponent": opponent,
                "scored_first": scored_first,
                "minute": line,
            }
            result[current_team].append(entry)
            if scored_first:
                result[f"{current_team}_scored_first_count"] += 1
            result[f"{current_team}_games"] += 1

        i += 1

    return result


def parse_half_scores(stats_text: str) -> dict:
    """
    Extract 1st half / 2nd half scores per game for both teams.
    Returns: {"home": [{"opponent": str, "first": int, "second": int}], "away": [...]}
    """
    result = {"home": [], "away": []}

    idx = stats_text.find("First Half/Second Half")
    if idx == -1:
        idx = stats_text.find("1st Half / 2nd Half")
    if idx == -1:
        return result

    block = stats_text[idx:idx + 1200]
    lines = [l.strip() for l in block.split("\n") if l.strip()]

    current = "home"
    i = 0
    while i < len(lines):
        line = lines[i]
        if "Second Half -" in line and i > 5:
            current = "away"
        if (not line.isdigit() and
                i + 2 < len(lines) and
                lines[i+1].isdigit() and
                lines[i+2].isdigit() and
                len(line) > 2 and
                not any(x in line for x in ["Half", "Match", "Round", "Ladder", "Stats", "First"])):
            result[current].append({
                "opponent": line,
                "first": int(lines[i+1]),
                "second": int(lines[i+2]),
            })
            i += 3
            continue
        i += 1

    return result


def parse_stats_comparison(stats_text: str) -> dict:
    """Extract key stats comparison metrics."""
    result = {}

    patterns = {
        "tries_per_game": r'([\d.]+)\([\d\-]+\)\s*Tries Per Game\s*([\d.]+)',
        "first_half_pts": r'([\d.]+)\([\d\-]+\)\s*First Half Points\s*([\d.]+)',
        "second_half_pts": r'([\d.]+)\([\d\-]+\)\s*Second Half Points\s*([\d.]+)',
        "scored_first": r'(\d+%\(\d+/\d+\))\s*Scored First\s*(\d+%\(\d+/\d+\))',
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, stats_text)
        if m:
            result[f"home_{key}"] = m.group(1)
            result[f"away_{key}"] = m.group(2)

    return result


# ---------------------------------------------------------------------------
# LINEUP TAB
# ---------------------------------------------------------------------------

POSITION_CODES = ["FB", "LW", "LC", "RC", "RW", "FE", "HLF", "PR", "HK", "L2R", "R2R", "LK"]

SKIP_WORDS = [
    "Interchange", "Reserve", "Match", "Round", "Ladder",
    "Stats", "Preview", "Lineup", "Tools", "Field", "List",
    "Official", "Paid", "View"
]


def parse_lineups(lineup_text: str) -> dict:
    """
    Extract starting 13 and 6 interchange for both teams.
    Interchange alternates home/away: index 0,2,4,6,8,10 = home, 1,3,5,7,9,11 = away.
    """
    result = {
        "home": {"starters": [], "interchange": []},
        "away": {"starters": [], "interchange": []},
    }

    lines = [l.strip() for l in lineup_text.split("\n") if l.strip()]

    # Extract starters
    starters_found = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in POSITION_CODES and i + 1 < len(lines):
            player = lines[i + 1].replace("(C) ", "").strip()
            if (not player.isdigit() and
                    len(player) > 1 and
                    player not in POSITION_CODES and
                    not any(x in player for x in SKIP_WORDS)):
                starters_found.append({"position": line, "player": player})
            i += 2
            continue
        i += 1

    result["home"]["starters"] = starters_found[:13]
    result["away"]["starters"] = starters_found[13:26]

    # Extract interchange — alternates home/away, 6 each
    interchange_players = []
    i = 0
    while i < len(lines):
        if lines[i] == "Interchange" and i + 1 < len(lines):
            player = lines[i + 1].replace("(C) ", "").strip()
            if (not player.isdigit() and
                    len(player) > 1 and
                    not any(x in player for x in SKIP_WORDS) and
                    player not in POSITION_CODES):
                interchange_players.append(player)
            i += 2
            continue
        if "Reserve" in lines[i]:
            break
        i += 1

    for idx, player in enumerate(interchange_players):
        if idx % 2 == 0:
            result["home"]["interchange"].append(player)
        else:
            result["away"]["interchange"].append(player)

    return result


# ---------------------------------------------------------------------------
# TOOLS TAB
# ---------------------------------------------------------------------------

def parse_attack_defence_grid(tools_text: str) -> dict:
    """
    Extract the 3-column attack/defence grid (Right | Centre | Left).
    """
    result = {}

    idx = tools_text.find("Attacking\n")
    if idx == -1:
        return result

    block = tools_text[max(0, idx-200):idx+400]
    lines = [l.strip() for l in block.split("\n") if l.strip()]

    rank_pattern = re.compile(r'^(\d+)(?:st|nd|rd|th)$')
    ranks = [line for line in lines if rank_pattern.match(line)]

    if len(ranks) >= 6:
        result["home_right_attack"] = ranks[0]
        result["away_right_attack"] = ranks[1]
        result["home_overall_attack"] = ranks[2]
        result["away_overall_attack"] = ranks[3]
        result["home_left_defence"] = ranks[4]
        result["away_left_defence"] = ranks[5]

    return result


def parse_attack_defence_detail(tools_text: str) -> dict:
    """Extract detailed attack/defence stats."""
    result = {}

    m = re.search(
        r'(\w[\w\s]+) Attack\s*\nRank\s*\n(\d+)(?:st|nd|rd|th)\s*\nTries\s*\nTries Per Game\s*\n(\d+)\s*\n([\d.]+)',
        tools_text
    )
    if m:
        result["home_attack_rank"] = m.group(2)
        result["home_tries_total"] = m.group(3)
        result["home_tries_per_game"] = m.group(4)

    m = re.search(
        r'(\w[\w\s]+) Defence\s*\nRank\s*\n(\d+)(?:st|nd|rd|th)\s*\nConceded\s*\nConceded Per Game\s*\n(\d+)\s*\n([\d.]+)',
        tools_text
    )
    if m:
        result["away_defence_rank"] = m.group(2)
        result["away_conceded_total"] = m.group(3)
        result["away_conceded_per_game"] = m.group(4)

    m = re.search(
        r'(\w[\w\s]+) / (Right|Left) Side Attack\s*\nRank\s*\nTries\s*\n% Total\s*\n(\d+)(?:st|nd|rd|th)\s*\n(\d+)\s*\n(\d+%)',
        tools_text
    )
    if m:
        result["home_side_attack_side"] = m.group(2)
        result["home_side_attack_rank"] = m.group(3)
        result["home_side_attack_tries"] = m.group(4)
        result["home_side_attack_pct"] = m.group(5)

    m = re.search(
        r'(\w[\w\s]+) / (Right|Left) Side Defence\s*\nRank\s*\nConceded\s*\n(\d+)(?:st|nd|rd|th)\s*\n(\d+)',
        tools_text
    )
    if m:
        result["away_side_defence_side"] = m.group(2)
        result["away_side_defence_rank"] = m.group(3)
        result["away_side_defence_conceded"] = m.group(4)

    return result


def parse_overs_unders(tools_text: str) -> dict:
    """
    Extract O/U line, over/under record, and recent game totals.
    """
    result = {}

    line_m = re.search(r'\+(\d+\.?\d*)', tools_text)
    if line_m:
        result["line"] = "+" + line_m.group(1)

    ou_m = re.search(r'Over:\s*(\d+)\s*Under:\s*(\d+)', tools_text)
    if ou_m:
        result["overs"] = int(ou_m.group(1))
        result["unders"] = int(ou_m.group(2))

    idx = tools_text.find("Overs/Unders Analysis")
    if idx != -1:
        block = tools_text[idx:idx + 500]
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        scores = []
        codes = []
        for line in lines:
            if re.match(r'^\d{2,3}$', line):
                scores.append(int(line))
            elif re.match(r'^[A-Z]{3}$', line) and line not in {"NRL", "H2H", "RD", "L5"}:
                codes.append(line)

        if scores and codes and len(scores) == len(codes):
            line_val = float(result.get("line", "+0").replace("+", "")) if result.get("line") else 0
            result["recent_totals"] = [
                {
                    "opponent_code": codes[i],
                    "total": scores[i],
                    "result": "OVER" if scores[i] > line_val else "UNDER"
                }
                for i in range(len(scores))
            ]

    return result


# ---------------------------------------------------------------------------
# MASTER PARSER
# ---------------------------------------------------------------------------

def parse_match(match: dict) -> dict:
    """Takes a full scraped match dict and returns clean structured data."""
    data = match.get("data", {})
    tabs = match.get("tabs") or {}
    preview = tabs.get("preview", "")
    stats = tabs.get("stats", "")
    lineup = tabs.get("lineup", "")
    tools = tabs.get("tools", "")

    home_name = data.get("home_team", {}).get("display_name", "Home")
    away_name = data.get("away_team", {}).get("display_name", "Away")

    return {
        "home_team": home_name,
        "away_team": away_name,
        "venue": data.get("venue", {}).get("name", ""),
        "venue_capacity": data.get("venue", {}).get("capacity"),
        "referee": data.get("referee", ""),
        "weather": data.get("weather"),
        "datetime": data.get("datetime", ""),
        "round": data.get("round_text", ""),
        "season": data.get("season", {}).get("value", "2026"),
        "analysis": data.get("analysis", ""),
        "home_dotpoints": data.get("home_team_dotpoints") or [],
        "away_dotpoints": data.get("away_team_dotpoints") or [],
        "home_rank": data.get("home_team", {}).get("ranking", {}).get("rank"),
        "home_wins": data.get("home_team", {}).get("ranking", {}).get("wins"),
        "home_losses": data.get("home_team", {}).get("ranking", {}).get("lost"),
        "home_diff": data.get("home_team", {}).get("ranking", {}).get("diff"),
        "away_rank": data.get("away_team", {}).get("ranking", {}).get("rank"),
        "away_wins": data.get("away_team", {}).get("ranking", {}).get("wins"),
        "away_losses": data.get("away_team", {}).get("ranking", {}).get("lost"),
        "away_diff": data.get("away_team", {}).get("ranking", {}).get("diff"),
        "h2h": parse_h2h(preview + stats),
        "tryscorers": parse_tryscorers(stats),
        "first_try": parse_first_try_data(stats),
        "half_scores": parse_half_scores(stats),
        "stats_comparison": parse_stats_comparison(stats),
        "lineups": parse_lineups(lineup),
        "attack_defence_grid": parse_attack_defence_grid(tools),
        "attack_defence_detail": parse_attack_defence_detail(tools),
        "overs_unders": parse_overs_unders(tools),
        "positions": {},
    }


def format_parsed_for_prompt(parsed: dict, elo: dict = None) -> str:
    """Convert parsed structured data into a clean dense prompt string."""
    home = parsed["home_team"]
    away = parsed["away_team"]
    h2h = parsed.get("h2h", {})
    stats = parsed.get("stats_comparison", {})
    half = parsed.get("half_scores", {})
    first_try = parsed.get("first_try", {})
    grid = parsed.get("attack_defence_grid", {})
    detail = parsed.get("attack_defence_detail", {})
    ou = parsed.get("overs_unders", {})
    lineups = parsed.get("lineups", {})
    tryscorers = parsed.get("tryscorers", [])

    lines = [
        "=" * 60,
        f"MATCH: {home} vs {away}",
        f"Round: {parsed['round']}, {parsed['season']}",
        f"Venue: {parsed['venue']} (capacity {parsed.get('venue_capacity', 'N/A')})",
        f"Referee: {parsed.get('referee', 'TBC')}",
        f"Weather: {parsed.get('weather') or 'No data'}",
        "=" * 60,
        "",
        "--- LADDER ---",
        f"{home}: {parsed['home_rank']}th | W{parsed['home_wins']}-L{parsed['home_losses']} | Diff: {parsed['home_diff']}",
        f"{away}: {parsed['away_rank']}th | W{parsed['away_wins']}-L{parsed['away_losses']} | Diff: {parsed['away_diff']}",
        "",
        "--- HEAD TO HEAD ---",
        f"{home} wins: {h2h.get('home_wins','?')} | Draws: {h2h.get('draws',0)} | {away} wins: {h2h.get('away_wins','?')}",
    ]

    if h2h.get("last_5"):
        lines.append("Last 5 H2H results (most recent first):")
        for g in h2h["last_5"][:5]:
            winner = g['home'] if g['home_score'] > g['away_score'] else g['away']
            lines.append(f"  {g.get('round','')}: {g.get('home','')} {g.get('home_score','')}-{g.get('away_score','')} {g.get('away','')} (won: {winner})")

    lines += [
        "",
        "--- 2026 FORM ---",
        f"{home} tries/game: {stats.get('home_tries_per_game','N/A')} | {away} tries/game: {stats.get('away_tries_per_game','N/A')}",
        f"{home} scored first: {stats.get('home_scored_first','N/A')} | {away} scored first: {stats.get('away_scored_first','N/A')}",
        f"{home} 1st half avg: {stats.get('home_first_half_pts','N/A')} pts | {away} 1st half avg: {stats.get('away_first_half_pts','N/A')} pts",
        f"{home} 2nd half avg: {stats.get('home_second_half_pts','N/A')} pts | {away} 2nd half avg: {stats.get('away_second_half_pts','N/A')} pts",
    ]

    if half.get("home"):
        lines.append(f"\n{home} 1st half / 2nd half by game:")
        for g in half["home"][:5]:
            lines.append(f"  vs {g['opponent']}: {g['first']} | {g['second']}")

    if half.get("away"):
        lines.append(f"\n{away} 1st half / 2nd half by game:")
        for g in half["away"][:5]:
            lines.append(f"  vs {g['opponent']}: {g['first']} | {g['second']}")

    # First try scorer data
    lines += ["", "--- FIRST TRY SCORER DATA ---"]
    if first_try.get("home"):
        scored = first_try.get("home_scored_first_count", 0)
        total = first_try.get("home_games", 0)
        lines.append(f"{home} scored first try: {scored}/{total} games this season")
        lines.append(f"{home} first try details:")
        for g in first_try["home"][:6]:
            status = "scored first" if g.get("scored_first") else "did NOT score first"
            lines.append(f"  vs {g['opponent']}: {status} (minute {g['minute']})")

    if first_try.get("away"):
        scored = first_try.get("away_scored_first_count", 0)
        total = first_try.get("away_games", 0)
        lines.append(f"{away} scored first try: {scored}/{total} games this season")
        lines.append(f"{away} first try details:")
        for g in first_try["away"][:6]:
            status = "scored first" if g.get("scored_first") else "did NOT score first"
            lines.append(f"  vs {g['opponent']}: {status} (minute {g['minute']})")

    lines += [
        "",
        "--- ATTACK / DEFENCE ---",
    ]

    if detail.get("home_attack_rank"):
        lines.append(f"{home} overall attack rank: {detail['home_attack_rank']}th | Tries: {detail.get('home_tries_total','?')} | Per game: {detail.get('home_tries_per_game','?')}")
    if detail.get("away_defence_rank"):
        lines.append(f"{away} overall defence rank: {detail['away_defence_rank']}th | Conceded: {detail.get('away_conceded_total','?')} | Per game: {detail.get('away_conceded_per_game','?')}")
    if detail.get("home_side_attack_rank"):
        lines.append(f"{home} {detail.get('home_side_attack_side','')} side attack rank: {detail['home_side_attack_rank']}th | Tries: {detail.get('home_side_attack_tries','?')} ({detail.get('home_side_attack_pct','?')} of total)")
    if detail.get("away_side_defence_rank"):
        lines.append(f"{away} {detail.get('away_side_defence_side','')} side defence rank: {detail['away_side_defence_rank']}th | Conceded: {detail.get('away_side_defence_conceded','?')}")

    if grid:
        lines.append(f"\nAttack/Defence grid (Right | Centre | Left):")
        if grid.get("home_right_attack"):
            lines.append(f"  {home}: right attack {grid['home_right_attack']}th | overall attack {grid.get('home_overall_attack','?')}th | left defence {grid.get('home_left_defence','?')}th")
        if grid.get("away_right_attack"):
            lines.append(f"  {away}: right attack {grid['away_right_attack']}th | overall attack {grid.get('away_overall_attack','?')}th | left defence {grid.get('away_left_defence','?')}th")

    lines += [
        "",
        "--- OVERS / UNDERS ---",
        f"Line: {ou.get('line','N/A')} | Over: {ou.get('overs','?')} Under: {ou.get('unders','?')}",
    ]

    if ou.get("recent_totals"):
        lines.append("Recent combined game totals:")
        for t in ou["recent_totals"]:
            lines.append(f"  vs {t['opponent_code']}: {t['total']} ({t['result']} {ou.get('line','')})")

    if tryscorers:
        lines += [
            "",
            "--- SEASON TRYSCORER STRIKE RATES (2026) ---",
            "Note: season-wide rates, not H2H specific.",
        ]
        for s in tryscorers[:5]:
            lines.append(f"  {s['player']}: {s['rate']} ({s['record']})")

    lines += ["", "--- LINEUP ---"]
    home_starters = lineups.get("home", {}).get("starters", [])
    away_starters = lineups.get("away", {}).get("starters", [])
    if home_starters:
        lines.append(f"{home} starting 13:")
        for p in home_starters:
            lines.append(f"  {p['position']}: {p['player']}")
    if away_starters:
        lines.append(f"{away} starting 13:")
        for p in away_starters:
            lines.append(f"  {p['position']}: {p['player']}")
    if lineups.get("home", {}).get("interchange"):
        lines.append(f"{home} interchange (6): {', '.join(lineups['home']['interchange'])}")
    if lineups.get("away", {}).get("interchange"):
        lines.append(f"{away} interchange (6): {', '.join(lineups['away']['interchange'])}")

    if parsed.get("home_dotpoints"):
        lines += ["", f"--- PREMATCH INSIGHTS — {home} ---"]
        for dp in parsed["home_dotpoints"]:
            lines.append(f"  • {dp}")

    if parsed.get("away_dotpoints"):
        lines += ["", f"--- PREMATCH INSIGHTS — {away} ---"]
        for dp in parsed["away_dotpoints"]:
            lines.append(f"  • {dp}")

    lines += ["", "--- PREVIEW ANALYSIS ---", parsed.get("analysis", "")]

    if elo:
        home_prob = elo.get("home_win_prob", 0.5)
        lines += [
            "",
            "--- ELO MODEL ---",
            f"{home} ELO: {elo.get('home_elo', 1500):.0f} | {away} ELO: {elo.get('away_elo', 1500):.0f}",
            f"Win probability: {home} {home_prob:.0%} | {away} {1-home_prob:.0%}",
            f"ELO tip: {elo.get('tip_team','')} ({elo.get('tip_confidence','')} confidence)",
        ]
        if elo.get("home_injuries", {}).get("notes"):
            lines.append(f"{home} injury concerns: {', '.join(elo['home_injuries']['notes'])}")
        if elo.get("away_injuries", {}).get("notes"):
            lines.append(f"{away} injury concerns: {', '.join(elo['away_injuries']['notes'])}")

    return "\n".join(lines)
