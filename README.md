# NRL Tips

Automatically scrapes [tryline.com.au](https://tryline.com.au), generates tip cards via Claude API, and publishes to GitHub Pages.

## Setup (one time)

### 1. Clone and install dependencies
```bash
git clone https://github.com/YOUR_USERNAME/nrl-tips.git
cd nrl-tips
pip install -r requirements.txt
```

### 2. Add your Anthropic API key
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
Get a key at [console.anthropic.com](https://console.anthropic.com).

### 3. Set up GitHub Pages
1. Push this repo to GitHub
2. Go to **Settings → Pages**
3. Set source to **GitHub Actions**
4. That's it — the workflow deploys automatically on every push

---

## Usage

### Automatic (recommended)
Run once each week when the round tips are ready:
```bash
python run.py --round 4
```
This will:
1. Scrape all 8 games from tryline.com.au
2. Generate tip cards via Claude API
3. Render the HTML page
4. Push to GitHub → auto-deploys to GitHub Pages within ~60 seconds

### If auto-discovery fails
If the scraper can't find the round fixtures automatically, grab the match URLs from tryline.com.au and pass them manually:
```bash
python run.py --round 4 --matches \
  "2640:2026-round-4-dragons-vs-sea-eagles,\
   2641:2026-round-4-roosters-vs-manly,\
   2642:2026-round-4-broncos-vs-cowboys"
```

### Preview without deploying
```bash
python run.py --round 4 --no-deploy
# Then open site/index.html in your browser
```

### Re-run generation without re-scraping
```bash
python run.py --round 4 --cache
```

---

## Share with friends
After deploying, your tips page lives at:
```
https://YOUR_USERNAME.github.io/nrl-tips
```
Share that link — it updates automatically every week.

---

## Project structure
```
nrl-tips/
├── run.py                  # Main entry point
├── requirements.txt
├── .env                    # Your API key (not committed)
├── scraper/
│   └── tryline.py          # Scrapes tryline.com.au
├── generator/
│   ├── cards.py            # Claude API tip card generator
│   └── renderer.py         # HTML page renderer
├── site/
│   └── index.html          # Generated output (committed)
└── .github/
    └── workflows/
        └── deploy.yml      # Auto-deploys site/ to GitHub Pages
```
