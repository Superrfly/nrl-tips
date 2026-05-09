"""
generator/renderer.py
Renders tip cards as a static HTML page for GitHub Pages.
Includes ELO win probability bar, scoring positions, injury notes, O/U pick.
"""

from datetime import datetime

CONFIDENCE_COLOUR = {
    "High":   ("#EAF3DE", "#3B6D11", "#639922"),
    "Medium": ("#FAEEDA", "#633806", "#BA7517"),
    "Low":    ("#FCEBEB", "#791F1F", "#E24B4A"),
}

SENTIMENT_DOT = {
    "positive": "#639922",
    "negative":  "#E24B4A",
    "neutral":   "#BA7517",
}

PRIORITY_STYLE = {
    "featured": "border-left: 3px solid #639922;",
    "standard": "",
    "value":    "border-left: 3px solid #BA7517;",
}

PRIORITY_BADGE = {
    "featured": '<span class="badge badge-green">Best Bet</span>',
    "standard": "",
    "value":    '<span class="badge badge-amber">Value</span>',
}


def render_prob_bar(home_team: str, away_team: str, home_prob) -> str:
    if home_prob is None:
        return ""
    away_prob = 1 - home_prob
    home_short = home_team.split()[-1]
    away_short = away_team.split()[-1]
    return f"""
    <div class="prob-bar-section">
      <div class="prob-label">
        <span>{home_short} {home_prob:.0%}</span>
        <span class="prob-title">Win Probability (ELO)</span>
        <span>{away_short} {away_prob:.0%}</span>
      </div>
      <div class="prob-bar">
        <div class="prob-home" style="width:{home_prob*100:.1f}%"></div>
        <div class="prob-away" style="width:{away_prob*100:.1f}%"></div>
      </div>
    </div>"""


def render_positions_block(positions: list, attack_team: str, defend_team: str) -> str:
    if not positions:
        return ""
    defend_short = defend_team.split()[-1]
    rows = f"""
          <div class="pos-row pos-header">
            <span class="pos-code"></span>
            <span class="pos-label"></span>
            <span class="pos-scored">Scored</span>
            <span class="pos-conceded">{defend_short} conc.</span>
          </div>"""
    for p in positions[:4]:
        rows += f"""
          <div class="pos-row">
            <span class="pos-code">{p.get('position','')}</span>
            <span class="pos-label">{p.get('label','')}</span>
            <span class="pos-scored">&#9650; {p.get('scored',0)}</span>
            <span class="pos-conceded">&#9660; {p.get('opp_conceded', p.get('conceded', 0))}</span>
          </div>"""
    return f"""
        <div class="pos-block">
          <div class="pos-team-name">{attack_team.split()[-1]} Attack</div>
          {rows}
        </div>"""


def render_card(card: dict, game_num: int) -> str:
    conf = card.get("confidence", "Medium")
    bg, text_col, border_col = CONFIDENCE_COLOUR.get(conf, CONFIDENCE_COLOUR["Medium"])
    tip_team = card.get("tip_team", "")
    home_team = card.get("home_team", "")
    away_team = card.get("away_team", "")

    # Quick hits
    qh_html = ""
    for qh in card.get("quick_hits", []):
        dot_col = SENTIMENT_DOT.get(qh.get("sentiment", "neutral"), "#BA7517")
        qh_html += f"""
        <div class="qh-row">
          <div class="dot" style="background:{dot_col}"></div>
          <div class="qh-text">{qh.get("text","")}</div>
        </div>"""

    # Injury notes
    injury_html = ""
    injury_notes = [n for n in card.get("injury_notes", []) if n]
    if injury_notes:
        items = "".join(f'<div class="injury-item">&#9888; {n}</div>' for n in injury_notes)
        injury_html = f"""
      <div class="section-label">INJURY CONCERNS</div>
      <div class="injury-section">{items}</div>"""

    # Scoring positions vs defence
    home_pos = render_positions_block(
        card.get("top_positions_home", []),
        card.get("home_team_name", home_team),
        card.get("away_team_name", away_team),
    )
    away_pos = render_positions_block(
        card.get("top_positions_away", []),
        card.get("away_team_name", away_team),
        card.get("home_team_name", home_team),
    )
    positions_html = ""
    if home_pos or away_pos:
        positions_html = f"""
      <div class="section-label">SCORING POSITIONS vs DEFENCE</div>
      <div class="positions-grid">{home_pos}{away_pos}</div>"""

    # O/U pick
    ou = card.get("ou_pick", {})
    ou_html = ""
    if ou and ou.get("pick"):
        ou_colour = "#639922" if ou.get("pick","").lower() == "over" else "#E24B4A"
        ou_html = f"""
      <div class="ou-block">
        <span class="ou-pick" style="color:{ou_colour};">{ou.get('pick','').upper()} {ou.get('line','')}</span>
        <span class="ou-reason">{ou.get('reasoning','')}</span>
      </div>"""

    # ATS picks
    ats_html = ""
    for pick in card.get("ats_picks", []):
        priority = pick.get("priority", "standard")
        badge = PRIORITY_BADGE.get(priority, "")
        left_border = PRIORITY_STYLE.get(priority, "")
        odds = f'<span class="ats-odds">{pick["odds"]}</span>' if pick.get("odds") else ""
        ats_html += f"""
        <div class="ats-block" style="{left_border}">
          <div class="ats-header">
            {badge}
            <span class="ats-name">{pick.get("player","")} &mdash; {pick.get("market","")}</span>
            {odds}
          </div>
          <div class="ats-body">{pick.get("analysis","")}</div>
        </div>"""

    # ELO
    prob_bar = render_prob_bar(home_team, away_team, card.get("win_prob_home"))
    elo_nums = ""
    if card.get("elo_home") and card.get("elo_away"):
        elo_nums = (
            f'<div class="elo-nums">ELO &mdash; {home_team.split()[-1]}: '
            f'<strong>{card["elo_home"]:.0f}</strong> &nbsp;|&nbsp; '
            f'{away_team.split()[-1]}: <strong>{card["elo_away"]:.0f}</strong></div>'
        )

    tryline_url = card.get("match_url", "https://tryline.com.au")

    return f"""
    <div class="card" id="game-{game_num}">
      <div class="card-header">
        <div class="game-label">GAME {game_num}</div>
        <div class="matchup">{home_team} <span class="vs">v</span> {away_team}</div>
        <div class="meta">{card.get("round")} &middot; {card.get("season")} &middot; {card.get("venue","")}</div>
      </div>
      <div class="tip-bar" style="background:{bg}; border-left:4px solid {border_col};">
        <div class="tip-label" style="color:{text_col};">TIP</div>
        <div class="tip-team" style="color:{text_col};">{tip_team}</div>
        <div class="tip-conf" style="color:{text_col}; background:rgba(0,0,0,0.08); border-radius:12px; padding:2px 10px; font-size:12px;">{conf} confidence</div>
      </div>
      {prob_bar}
      {elo_nums}
      <div class="section-label">QUICK HITS</div>
      <div class="quick-hits">{qh_html}</div>
      {injury_html}
      {positions_html}
      <div class="section-label">O/U PICK</div>
      {ou_html}
      <div class="section-label">ATS / VALUE</div>
      <div class="ats-section">{ats_html}</div>
      <div class="summary">{card.get("summary","")}</div>
      <a class="tryline-link" href="{tryline_url}" target="_blank" rel="noopener">Full stats on Tryline &rarr;</a>
    </div>"""


def render_page(cards: list, round_num: int, season: int) -> str:
    generated = datetime.now().strftime("%d %b %Y, %I:%M %p")
    nav_links = "".join(
        f'<a href="#game-{i+1}">{c.get("home_team","").split()[-1]} v {c.get("away_team","").split()[-1]}</a>\n'
        for i, c in enumerate(cards)
    )
    cards_html = "".join(render_card(c, i+1) for i, c in enumerate(cards))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>NRL Tips &mdash; Round {round_num}, {season}</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0f1117;--surface:#1a1d27;--surface2:#1f2233;--border:rgba(255,255,255,0.07);--text:#e8eaf0;--muted:#6b7080;--green:#639922;--amber:#BA7517;--red:#E24B4A;--radius:12px}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding-bottom:4rem}}
    .site-header{{text-align:center;padding:2rem 1rem 0.5rem}}
    .site-header h1{{font-size:1.5rem;font-weight:700}}
    .sub{{font-size:12px;color:var(--muted);margin-top:4px}}
    .nav{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:0.5rem 1rem;display:flex;gap:0.5rem;flex-wrap:wrap;z-index:10}}
    .nav a{{font-size:11px;color:var(--muted);text-decoration:none;padding:3px 8px;border:1px solid var(--border);border-radius:4px}}
    .nav a:hover{{color:var(--text)}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1.25rem;padding:1.5rem;max-width:1400px;margin:0 auto}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);display:flex;flex-direction:column;overflow:hidden}}
    .card-header{{padding:1rem 1.1rem 0.75rem;border-bottom:1px solid var(--border)}}
    .game-label{{font-size:10px;letter-spacing:0.08em;color:var(--muted);text-transform:uppercase;margin-bottom:4px}}
    .matchup{{font-size:17px;font-weight:600}}
    .vs{{color:var(--muted);font-weight:400;font-size:14px;margin:0 6px}}
    .meta{{font-size:11px;color:var(--muted);margin-top:4px}}
    .tip-bar{{display:flex;align-items:center;gap:10px;padding:0.6rem 1.1rem}}
    .tip-label{{font-size:10px;font-weight:700;letter-spacing:0.1em}}
    .tip-team{{font-size:14px;font-weight:600;flex:1}}
    .prob-bar-section{{padding:0.5rem 1.1rem 0}}
    .prob-label{{display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:4px}}
    .prob-title{{font-size:10px;color:var(--muted);opacity:0.7}}
    .prob-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden}}
    .prob-home{{background:var(--green)}}
    .prob-away{{background:#3a4a5c}}
    .elo-nums{{font-size:10px;color:var(--muted);padding:4px 1.1rem 0}}
    .elo-nums strong{{color:var(--text)}}
    .section-label{{font-size:10px;font-weight:600;letter-spacing:0.08em;color:var(--muted);text-transform:uppercase;padding:0.75rem 1.1rem 0.25rem}}
    .quick-hits{{padding:0 1.1rem 0.5rem}}
    .qh-row{{display:flex;gap:9px;align-items:flex-start;margin-bottom:8px}}
    .dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:5px}}
    .qh-text{{font-size:12px;line-height:1.55;color:#ccc}}
    .injury-section{{padding:0 1.1rem 0.5rem}}
    .injury-item{{font-size:12px;color:#f0a070;margin-bottom:4px;line-height:1.5}}
    .positions-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:0 1.1rem 0.75rem}}
    .pos-block{{background:var(--surface2);border-radius:8px;padding:0.65rem 0.75rem;border:1px solid var(--border)}}
    .pos-team-name{{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px}}
    .pos-row{{display:flex;align-items:center;gap:6px;margin-bottom:5px;font-size:12px}}
    .pos-header .pos-scored,.pos-header .pos-conceded{{color:var(--muted);font-weight:400;font-size:10px;letter-spacing:0.04em}}
    .pos-code{{font-weight:700;color:#eee;min-width:30px}}
    .pos-label{{color:var(--muted);font-size:11px;flex:1}}
    .pos-scored{{color:var(--green);font-weight:600;min-width:42px;text-align:right}}
    .pos-conceded{{color:var(--red);font-weight:600;min-width:52px;text-align:right}}
    .ou-block{{display:flex;align-items:center;gap:10px;padding:0.4rem 1.1rem 0.75rem;font-size:13px}}
    .ou-pick{{font-weight:700;font-size:14px}}
    .ou-reason{{color:var(--muted);font-size:12px}}
    .ats-section{{padding:0 1.1rem 0.5rem;display:flex;flex-direction:column;gap:10px}}
    .ats-block{{background:var(--surface2);border-radius:8px;padding:0.65rem 0.85rem;border:1px solid var(--border)}}
    .ats-header{{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:5px}}
    .ats-name{{font-size:13px;font-weight:600;flex:1}}
    .ats-odds{{font-size:12px;color:var(--muted)}}
    .ats-body{{font-size:12px;line-height:1.6;color:#aaa}}
    .badge{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;flex-shrink:0}}
    .badge-green{{background:#EAF3DE;color:#3B6D11}}
    .badge-amber{{background:#FAEEDA;color:#633806}}
    .summary{{font-size:13px;font-weight:500;color:#ddd;padding:0.75rem 1.1rem;border-top:1px solid var(--border);margin-top:auto;line-height:1.5}}
    .tryline-link{{display:block;font-size:11px;color:var(--muted);text-decoration:none;padding:0.5rem 1.1rem;border-top:1px solid var(--border);transition:color 0.15s}}
    .tryline-link:hover{{color:var(--text)}}
    .footer{{text-align:center;font-size:12px;color:var(--muted);margin-top:2rem;padding-bottom:2rem}}
    @media(max-width:600px){{.cards-grid{{grid-template-columns:1fr;padding:0.75rem}}}}
  </style>
</head>
<body>
<header class="site-header">
  <h1>NRL Tips &mdash; Round {round_num}, {season}</h1>
  <div class="sub">Generated {generated} &middot; Tryline stats + ELO model &middot; gemma3:12b</div>
</header>
<nav class="nav">{nav_links}</nav>
<div class="cards-grid">{cards_html}</div>
<div class="footer">Data: tryline.com.au + ELO model &middot; For entertainment purposes only</div>
</body>
</html>"""


def save_site(cards: list, round_num: int, season: int, output_path: str = "site/index.html"):
    html = render_page(cards, round_num, season)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Site saved: {output_path}")
    return html
