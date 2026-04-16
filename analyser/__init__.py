"""
analyser/__init__.py
====================
Combines ELO ratings and injury data into a structured tip recommendation
for each match. Called from run.py before card generation.

Usage:
    from analyser import analyse_round

    analysis = analyse_round(matches, season=2026, round_num=6)
    # analysis is a dict keyed by match_id
"""

from .elo import fetch_elo_ratings, analyse_matchup
from .injuries import fetch_injury_news, injury_impact


def analyse_round(matches: list[dict], season: int = 2026, round_num: int = 1) -> dict[str, dict]:
    """
    Takes the list of scraped match dicts from tryline scraper.
    Returns a dict keyed by match_id with full analysis for each game.

    Each value:
    {
        home_elo, away_elo,
        home_win_prob,
        tip_team,
        tip_prob,
        tip_confidence,   # "Strong" / "Moderate" / "Slight"
        tip_summary,      # one-liner for the card
        home_injuries,    # {has_injuries, notes, high_impact}
        away_injuries,
        adjusted_confidence,  # may downgrade if injuries detected
        recommendation,   # final plain-English tip sentence
    }
    """
    print("\n[Analyser] Fetching ELO ratings...")
    ratings = fetch_elo_ratings()
    if ratings:
        print(f"  Got ELO ratings for {len(ratings)} teams.")
    else:
        print("  Using league average (1500) for all teams.")

    print("[Analyser] Fetching injury data...")
    injury_data = fetch_injury_news(season=season, round_num=round_num)
    if injury_data:
        print(f"  Got injury data for {len(injury_data)} teams.")
    else:
        print("  No injury data available — continuing without.")

    results = {}

    for match in matches:
        match_id = match.get("match_id") or match.get("id") or str(id(match))
        data = match.get("data", match)  # handle both wrapper and flat formats

        home_team = (
            data.get("home_team", {}).get("display_name")
            or data.get("home_team", {}).get("name")
            or data.get("home", "Home Team")
        )
        away_team = (
            data.get("away_team", {}).get("display_name")
            or data.get("away_team", {}).get("name")
            or data.get("away", "Away Team")
        )

        # ELO analysis
        elo = analyse_matchup(home_team, away_team, ratings)

        # Injury analysis
        home_inj = injury_impact(home_team, injury_data)
        away_inj = injury_impact(away_team, injury_data)

        # Adjust confidence if key injuries detected
        confidence = elo["tip_confidence"]
        injury_warning = ""

        if elo["tip_team"] == home_team and home_inj["high_impact"]:
            # Our tip team has a key injury — downgrade confidence
            if confidence == "Strong":
                confidence = "Moderate"
            elif confidence == "Moderate":
                confidence = "Slight"
            injury_warning = f" Note: {home_team} has a high-impact injury concern."

        elif elo["tip_team"] == away_team and away_inj["high_impact"]:
            if confidence == "Strong":
                confidence = "Moderate"
            elif confidence == "Moderate":
                confidence = "Slight"
            injury_warning = f" Note: {away_team} has a high-impact injury concern."

        # Build final recommendation sentence
        prob_pct = f"{elo['tip_prob']:.0%}"
        recommendation = (
            f"Tip {elo['tip_team']} — {confidence} confidence ({prob_pct} win probability "
            f"by ELO).{injury_warning}"
        )

        results[str(match_id)] = {
            **elo,
            "home_injuries": home_inj,
            "away_injuries": away_inj,
            "adjusted_confidence": confidence,
            "recommendation": recommendation,
        }

        print(f"  {home_team} vs {away_team} → {recommendation}")

    return results
