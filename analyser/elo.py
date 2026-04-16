"""
analyser/elo.py
===============
Scrapes current NRL ELO ratings from aussportstipping.com and calculates
win probabilities for each matchup.

No API key needed — free public data.
"""

import httpx
from bs4 import BeautifulSoup


ELO_URL = "https://www.aussportstipping.com/sports/nrl/elo_ratings/"

# Home ground advantage in ELO points (calibrated for NRL)
HOME_ADVANTAGE = 50

# Team name normalisation — tryline names -> aussportstipping names
TEAM_MAP = {
    "Brisbane Broncos": "Brisbane",
    "Canberra Raiders": "Canberra",
    "Canterbury Bulldogs": "Canterbury",
    "Cronulla Sharks": "Cronulla",
    "Dolphins": "Dolphins",
    "Gold Coast Titans": "Gold Coast",
    "Manly Sea Eagles": "Manly",
    "Melbourne Storm": "Melbourne",
    "Newcastle Knights": "Newcastle",
    "New Zealand Warriors": "Warriors",
    "North Queensland Cowboys": "North Queensland",
    "Parramatta Eels": "Parramatta",
    "Penrith Panthers": "Penrith",
    "South Sydney Rabbitohs": "South Sydney",
    "St George Illawarra Dragons": "St George Illawarra",
    "Sydney Roosters": "Sydney",
    "Wests Tigers": "Wests Tigers",
    # Short names
    "Broncos": "Brisbane",
    "Raiders": "Canberra",
    "Bulldogs": "Canterbury",
    "Sharks": "Cronulla",
    "Titans": "Gold Coast",
    "Sea Eagles": "Manly",
    "Storm": "Melbourne",
    "Knights": "Newcastle",
    "Warriors": "Warriors",
    "Cowboys": "North Queensland",
    "Eels": "Parramatta",
    "Panthers": "Penrith",
    "Rabbitohs": "South Sydney",
    "Dragons": "St George Illawarra",
    "Roosters": "Sydney",
    "Tigers": "Wests Tigers",
}


def fetch_elo_ratings() -> dict[str, float]:
    """
    Scrapes current ELO ratings from aussportstipping.com.
    Returns dict of {team_name: elo_rating}.
    Falls back to league average (1500) for any missing team.
    """
    ratings = {}
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(ELO_URL, headers=headers, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # The ratings table has columns: Rank, Team, Rating, ...
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if len(cells) >= 3:
                team_raw = cells[1].get_text(strip=True)
                rating_raw = cells[2].get_text(strip=True)
                try:
                    rating = float(rating_raw.replace(",", ""))
                    ratings[team_raw] = rating
                except ValueError:
                    continue

    except Exception as e:
        print(f"  [ELO] Warning: could not fetch ratings ({e}). Using league average 1500.")

    return ratings


def normalise_team(name: str, ratings: dict[str, float]) -> str:
    """Maps a tryline team name to the aussportstipping key."""
    # Direct match
    if name in ratings:
        return name
    # Map via TEAM_MAP
    mapped = TEAM_MAP.get(name)
    if mapped and mapped in ratings:
        return mapped
    # Fuzzy — find first partial match
    name_lower = name.lower()
    for key in ratings:
        if key.lower() in name_lower or name_lower in key.lower():
            return key
    return name


def win_probability(elo_home: float, elo_away: float, home_advantage: float = HOME_ADVANTAGE) -> float:
    """
    Standard ELO win probability formula.
    Returns probability (0-1) that the home team wins.
    """
    adjusted_home = elo_home + home_advantage
    return 1 / (1 + 10 ** ((elo_away - adjusted_home) / 400))


def elo_label(prob: float) -> str:
    """Human-readable confidence label from win probability."""
    if prob >= 0.70:
        return "Strong"
    elif prob >= 0.58:
        return "Moderate"
    elif prob >= 0.50:
        return "Slight"
    else:
        return "Slight"  # away team is actually favourite


def analyse_matchup(home_team: str, away_team: str, ratings: dict[str, float]) -> dict:
    """
    Given home and away team names and the ratings dict, returns:
    {
        home_elo, away_elo,
        home_win_prob,   # 0-1
        tip_team,        # name of recommended team
        tip_confidence,  # "Strong" / "Moderate" / "Slight"
        tip_summary,     # one-line explanation
    }
    """
    default = 1500.0

    home_key = normalise_team(home_team, ratings)
    away_key = normalise_team(away_team, ratings)

    home_elo = ratings.get(home_key, default)
    away_elo = ratings.get(away_key, default)

    prob = win_probability(home_elo, away_elo)

    if prob >= 0.5:
        tip_team = home_team
        tip_prob = prob
    else:
        tip_team = away_team
        tip_prob = 1 - prob

    confidence = elo_label(tip_prob)

    diff = abs(home_elo - away_elo)
    summary = (
        f"ELO: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f} "
        f"(+{HOME_ADVANTAGE} home). "
        f"{tip_team} win probability: {tip_prob:.0%} ({confidence})."
    )

    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "home_win_prob": round(prob, 3),
        "tip_team": tip_team,
        "tip_prob": round(tip_prob, 3),
        "tip_confidence": confidence,
        "elo_diff": round(diff, 1),
        "tip_summary": summary,
    }
