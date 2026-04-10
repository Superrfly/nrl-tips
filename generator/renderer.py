"""
Renders tip cards as a static HTML page for GitHub Pages.
"""

import json
from datetime import datetime


CONFIDENCE_COLOUR = {
    "High": ("#EAF3DE", "#3B6D11", "#639922"),
    "Medium": ("#FAEEDA", "#633806", "#BA7517"),
    "Low": ("#FCEBEB", "#791F1F", "#E24B4A"),
}

SENTIMENT_DOT = {
    "positive": "#639922",
    "negative": "#E24B4A",
    "neutral": "#BA7517",
}

PRIORITY_STYLE = {
    "featured": "border-left: 3px solid #639922;",
    "standard": "",
    "value": "border-left: 3px solid #BA7517;",
}

PRIORITY_BADGE = {
    "featured": ('<span class="badge badge-green">Best Bet</span>', ),
    "standard": ('', ),
    "value": ('<span class="badge badge-amber">Value</span>', ),
}


def render_card(card: dict, game_num: int) -> str:
    conf = card.get("confidence", "Medium")
    bg, text_col, border_col = CONFIDENCE_COLOUR.get(conf, CONFIDENCE_COLOUR["Medium"])
    tip_team = card.get("tip_team", card.get("tip", ""))

    # Quick hits
    qh_html = ""
    for qh in card.get("quick_hits", []):
        dot_col = SENTIMENT_DOT.get(qh.get("sentiment", "neutral"), "#BA7517")
        qh_html += f"""
        <div class="qh-row">
          <div class="dot" style="background:{dot_col}"></div>
          <div class="qh-text">{qh.get("text", "")}</div>
        </div>"""

    # ATS picks
    ats_html = ""
    for pick in card.get("ats_picks", []):
        priority = pick.get("priority", "standard")
        left_border = PRIORITY_STYLE.get(priority, "")
        badge = PRIORITY_BADGE.get(priority, ("",))[0]
        odds = f'<span class="ats-odds">{pick["odds"]}</span>' if pick.get("odds") else ""
        ats_html += f"""
        <div class="ats-block" style="{left_border}">
          <div class="ats-header">
            {badge}
            <span class="ats-name">{pick.get("player", "")} — {pick.get("market", "")}</span>
            {odds}
          </div>
          <div class="ats-body">{pick.get("analysis", "")}</div>
        </div>"""

    tryline_url = card.get("match_url", "https://tryline.com.au")

    return f"""
    <div class="card" id="game-{game_num}">
      <div class="card-header">
        <div class="game-label">GAME {game_num}</div>
        <div class="matchup">{card.get("home_team")} <span class="vs">v</span> {card.get("away_team")}</div>
        <div class="meta">{card.get("round")} · {card.get("season")} · {card.get("venue", "")}</div>
      </div>

      <div class="tip-bar" style="background:{bg}; border-color:{border_col};">
        <div class="tip-label" style="color:{text_col};">TIP</div>
        <div class="tip-team" style="color:{text_col};">{tip_team}</div>
        <div class="tip-conf" style="color:{text_col}; background:rgba(0,0,0,0.08); border-radius:12px; padding:2px 10px; font-size:12px;">{conf} confidence</div>
      </div>

      <div class="section-label">QUICK HITS</div>
      <div class="quick-hits">{qh_html}</div>

      <div class="section-label">ATS / VALUE</div>
      <div class="ats-section">{ats_html}</div>

      <div class="summary">{card.get("summary", "")}</div>

      <a class="tryline-link" href="{tryline_url}" target="_blank" rel="noopener">View full stats on Tryline →</a>
    </div>"""


def render_page(cards: list[dict], round_num: int, season: int) -> str:
    generated = datetime.now().strftime("%-d %B %Y, %-I:%M%p").lower()
    nav_links = ""
    for i, card in enumerate(cards, 1):
        home_short = card.get("home_team", "").split()[-1]
        away_short = card.get("away_team", "").split()[-1]
        nav_links += f'<a href="#game-{i}">{home_short} v {away_short}</a>'

    cards_html = ""
    for i, card in enumerate(cards, 1):
        cards_html += render_card(card, i)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>NRL Tips — Round {round_num}, {season}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #0f0f0f;
      --surface: #1a1a1a;
      --surface2: #222;
      --border: rgba(255,255,255,0.08);
      --text: #f0f0f0;
      --muted: #888;
      --green: #639922;
      --amber: #BA7517;
      --red: #E24B4A;
      --radius: 12px;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 0 0 4rem;
    }}

    .site-header {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 1.25rem 1.5rem;
      position: sticky;
      top: 0;
      z-index: 10;
    }}

    .site-header h1 {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 2px;
    }}

    .site-header .sub {{
      font-size: 12px;
      color: var(--muted);
    }}

    .nav {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 0.75rem 1.5rem;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
      position: sticky;
      top: 60px;
      z-index: 9;
    }}

    .nav a {{
      font-size: 12px;
      color: var(--muted);
      text-decoration: none;
      padding: 3px 10px;
      border: 1px solid var(--border);
      border-radius: 20px;
      transition: all 0.15s;
    }}

    .nav a:hover {{
      color: var(--text);
      border-color: rgba(255,255,255,0.2);
    }}

    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 1.25rem;
      max-width: 1200px;
      margin: 1.5rem auto;
      padding: 0 1.25rem;
    }}

    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    .card-header {{
      padding: 1rem 1.1rem 0.75rem;
      border-bottom: 1px solid var(--border);
    }}

    .game-label {{
      font-size: 10px;
      letter-spacing: 0.08em;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 4px;
    }}

    .matchup {{
      font-size: 17px;
      font-weight: 600;
      line-height: 1.3;
    }}

    .vs {{
      color: var(--muted);
      font-weight: 400;
      font-size: 14px;
      margin: 0 4px;
    }}

    .meta {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 3px;
    }}

    .tip-bar {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0.6rem 1.1rem;
      border-left: 4px solid transparent;
    }}

    .tip-label {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
    }}

    .tip-team {{
      font-size: 14px;
      font-weight: 600;
      flex: 1;
    }}

    .section-label {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      color: var(--muted);
      text-transform: uppercase;
      padding: 0.75rem 1.1rem 0.25rem;
    }}

    .quick-hits {{
      padding: 0 1.1rem 0.5rem;
    }}

    .qh-row {{
      display: flex;
      gap: 9px;
      align-items: flex-start;
      margin-bottom: 8px;
    }}

    .dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 5px;
    }}

    .qh-text {{
      font-size: 13px;
      line-height: 1.55;
      color: #ccc;
    }}

    .ats-section {{
      padding: 0 1.1rem 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .ats-block {{
      background: var(--surface2);
      border-radius: 8px;
      padding: 0.65rem 0.85rem;
      border: 1px solid var(--border);
    }}

    .ats-header {{
      display: flex;
      align-items: center;
      gap: 7px;
      flex-wrap: wrap;
      margin-bottom: 5px;
    }}

    .ats-name {{
      font-size: 13px;
      font-weight: 600;
      flex: 1;
    }}

    .ats-odds {{
      font-size: 12px;
      color: var(--muted);
    }}

    .ats-body {{
      font-size: 12px;
      line-height: 1.6;
      color: #aaa;
    }}

    .badge {{
      font-size: 10px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 10px;
      flex-shrink: 0;
    }}

    .badge-green {{ background: #EAF3DE; color: #3B6D11; }}
    .badge-amber {{ background: #FAEEDA; color: #633806; }}

    .summary {{
      font-size: 13px;
      font-weight: 500;
      color: #ddd;
      padding: 0.75rem 1.1rem;
      border-top: 1px solid var(--border);
      margin-top: auto;
      line-height: 1.5;
    }}

    .tryline-link {{
      display: block;
      font-size: 11px;
      color: var(--muted);
      text-decoration: none;
      padding: 0.5rem 1.1rem;
      border-top: 1px solid var(--border);
      transition: color 0.15s;
    }}

    .tryline-link:hover {{ color: var(--text); }}

    .footer {{
      text-align: center;
      font-size: 12px;
      color: var(--muted);
      margin-top: 2rem;
    }}

    @media (max-width: 600px) {{
      .cards-grid {{ grid-template-columns: 1fr; padding: 0 0.75rem; }}
      .nav {{ top: 56px; }}
    }}
  </style>
</head>
<body>

<header class="site-header">
  <h1>NRL Tips — Round {round_num}, {season}</h1>
  <div class="sub">Generated {generated} · Data via Tryline</div>
</header>

<nav class="nav">
  {nav_links}
</nav>

<div class="cards-grid">
  {cards_html}
</div>

<div class="footer">Data sourced from tryline.com.au · For entertainment purposes only</div>

</body>
</html>"""


def save_site(cards: list[dict], round_num: int, season: int, output_path: str = "site/index.html"):
    html = render_page(cards, round_num, season)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nSite saved to: {output_path}")
    return html
