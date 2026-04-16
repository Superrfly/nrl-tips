import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

HIGH_IMPACT_POSITIONS = {
    "halfback", "half", "five-eighth", "hooker", "fullback",
    "lock", "prop", "winger", "centre"
}

TEAM_SLUG_MAP = {
    "Brisbane Broncos": "broncos",
    "Canberra Raiders": "raiders",
    "Canterbury Bulldogs": "bulldogs",
    "Cronulla-Sutherland Sharks": "sharks",
    "Cronulla Sharks": "sharks",
    "Dolphins": "dolphins",
    "Gold Coast Titans": "titans",
    "Manly Sea Eagles": "sea-eagles",
    "Manly-Warringah Sea Eagles": "sea-eagles",
    "Melbourne Storm": "storm",
    "Newcastle Knights": "knights",
    "New Zealand Warriors": "warriors",
    "North Queensland Cowboys": "cowboys",
    "Parramatta Eels": "eels",
    "Penrith Panthers": "panthers",
    "South Sydney Rabbitohs": "rabbitohs",
    "St George Illawarra Dragons": "dragons",
    "Sydney Roosters": "roosters",
    "Wests Tigers": "tigers",
}


def team_to_slug(team_name):
    if team_name in TEAM_SLUG_MAP:
        return TEAM_SLUG_MAP[team_name]
    return team_name.split()[-1].lower()


def scrape_match_injuries(home_team, away_team, season, round_num):
    home_slug = team_to_slug(home_team)
    away_slug = team_to_slug(away_team)
    url = f"https://www.nrl.com/draw/nrl-premiership/{season}/round-{round_num}/{home_slug}-v-{away_slug}/"

    result = {
        "home": {"ins": [], "outs": [], "high_impact": False},
        "away": {"ins": [], "outs": [], "high_impact": False},
    }

    print(f"    Fetching injuries: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            text = page.inner_text("body")
            browser.close()

        result = parse_ins_outs(text, home_team, away_team)

    except Exception as e:
        print(f"    [Injuries] Error: {e}")

    return result


def parse_ins_outs(text, home_team, away_team):
    result = {
        "home": {"ins": [], "outs": [], "high_impact": False},
        "away": {"ins": [], "outs": [], "high_impact": False},
    }

    home_words = home_team.split()
    away_words = away_team.split()
    home_short = home_words[-1]
    away_short = away_words[-1]
    home_short2 = " ".join(home_words[-2:]) if len(home_words) >= 2 else home_short
    away_short2 = " ".join(away_words[-2:]) if len(away_words) >= 2 else away_short

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    current_team = None
    current_type = None

    skip_phrases = [
        "Team list", "At Fullback", "At Winger", "At Centre",
        "Kick off", "Venue", "Weather", "Round", "Match",
        "News", "Watch", "Draw", "Ladder", "Stats",
        "Get Tickets", "Team Lists", "Team Stats"
    ]

    i = 0
    while i < len(lines):
        line = lines[i]

        matched_team = False
        for team_key, team_result_key in [
            (home_short, "home"),
            (home_short2, "home"),
            (away_short, "away"),
            (away_short2, "away"),
        ]:
            if line.startswith(team_key):
                current_team = team_result_key
                if "Ins" in line or "ins" in line:
                    current_type = "ins"
                elif "Outs" in line or "outs" in line:
                    current_type = "outs"
                matched_team = True
                break

        if not matched_team and line in ("INS", "OUTS"):
            current_type = line.lower()
        elif (not matched_team and
              current_team and
              current_type and
              len(line) > 2 and
              not line.isupper() and
              not any(x in line for x in skip_phrases) and
              re.match(r'^[A-Z][a-z]', line)):
            result[current_team][current_type].append(line)

        i += 1

    for team_key in ["home", "away"]:
        if result[team_key]["outs"]:
            result[team_key]["high_impact"] = True

    return result


def fetch_injury_data(season, round_num, matches=None):
    if not matches:
        return {}

    injury_data = {}
    for match in matches:
        match_id = str(match.get("match_id"))
        data = match.get("data", {})
        home = data.get("home_team", {}).get("display_name", "")
        away = data.get("away_team", {}).get("display_name", "")
        if home and away:
            injuries = scrape_match_injuries(home, away, season, round_num)
            injury_data[match_id] = injuries

    return injury_data


def get_team_injuries(match_id, team, injury_data):
    match_injuries = injury_data.get(str(match_id), {})
    empty = {"ins": [], "outs": [], "high_impact": False}
    return match_injuries.get(team, empty)