# :trophy: FIFA World Cup Predictor

<p align="center">
  <strong>Predict World Cup matches. Review real results. Get better over time.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
  <img src="https://img.shields.io/badge/data-live%20odds%20%2B%20lineups%20%2B%20injuries-red" alt="live data">
</p>

> :cn: 中文用户请阅读 [README_zh.md](README_zh.md)

---

## :mag: What is this?

A football prediction tool built for the FIFA World Cup. Give it two teams and it tells you who's likely to win, by what score, and whether the odds are off. After the match, it finds the real result online, compares it against the prediction, and adjusts its own parameters — so it gets sharper with every game it watches.

Like an analyst who never stops studying film.

---

## :dart: What it can do

### :crystal_ball: Before the match

- **Predict win/draw/loss** odds plus the most likely final score
- **Adapt per tournament round** — R1 conservative (×0.5), R2 bounce-back (×1.10), R3 normal, KO defensive (v3.2)
- **Spot potential upsets** with 3-layer detection — style mismatch, form variance, tournament edge
- **Simulate tournament paths** to see each team's odds of reaching the quarters, semis, or final
- **Find mispriced odds** — flags when the model disagrees with the market by a meaningful margin

### :satellite: Live data (new in v3.1)

- **Starting lineups** — auto-fetched ~1 hour before kickoff, including formation analysis
- **Injury reports** — who's out, suspended, or doubtful and how it shifts the odds
- **Live odds** — multi-bookmaker comparison, refreshed every 60 seconds
- **Enhances predictions** — injuries adjust team strength ratings; formations shift expected goals

> Powered by the [BSD Free Football API](https://sports.bzzoiro.com/). Just set `BSD_API_KEY` in your environment — free, no rate limits.

### :bar_chart: After the match

- **Review every prediction** automatically by searching the web for real results
- **Score itself** on a 100-point scale across direction, score accuracy, goal prediction, and value calls
- **Update team ratings** based on what actually happened on the pitch

### :dna: Self-improvement

- **Auto-calibrate** after watching enough matches — tweaks its own parameters
- **Track accuracy over time** so you can see if it's getting smarter
- **Run profit simulations** across multiple betting strategies

---

## :rocket: Quick start

```bash
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor
```

No dependencies to install — pure Python standard library.

### Predict with live data

```python
from scripts.live_data_fetcher import LiveDataFetcher
from scripts.prediction_engine import FootballPredictionEngine

# Pull lineups, injuries, and odds in one call
fetcher = LiveDataFetcher()
live = fetcher.get_full_match_data('Argentina', 'France')

engine = FootballPredictionEngine(data_dir='data')
prediction = engine.predict_with_live_data('Argentina', 'France', live, is_knockout=True)

print(f"Argentina win: {prediction['final']['win_a']}%")
print(f"Draw:          {prediction['final']['draw']}%")
print(f"France win:    {prediction['final']['win_b']}%")
print(f"Injuries: {prediction['live_data']['injuries']['summary']}")
```

### Without live data

```python
prediction = engine.predict('Argentina', 'France', is_knockout=True)
# still works — no API key needed
```

### Review and learn

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('Argentina', 'France', (2, 1), prediction)
print(f"Review: {review['scores']['total']}/100 — {review['scores']['grade']}")

# After 3+ reviews, the evolution engine auto-calibrates
from scripts.evolution_engine import EvolutionEngine
EvolutionEngine('.').evolve()
```

---

## :repeat: The learning loop

1. **Predict** — Elo ratings + Poisson xG + tactical context + live data (injuries/lineups)
2. **Review** — web search for real results, compare, score
3. **Learn** — every 3+ reviews triggers parameter recalibration
4. **Improve** — repeat, and the predictions get tighter

Four betting strategies tracked in parallel: half-Kelly, full-Kelly, fixed-fraction, and value-only.

---

## :file_folder: What's inside

```
fifa-worldcup-predictor/
├── README.md                  # You're reading it
├── README_zh.md               # Chinese version
├── scripts/
│   ├── prediction_engine.py   # Match prediction + live data integration
│   ├── live_data_fetcher.py   # Lineups, injuries, odds (BSD API)
│   ├── bsd_client.py          # BSD API raw client
│   ├── odds_fetcher.py        # Dual-source odds (BSD + The Odds API)
│   ├── post_match_review.py   # Post-match review + web search
│   ├── evolution_engine.py    # Auto-calibration
│   └── profit_tracker.py      # Betting simulations
├── data/                      # Elo ratings, team stats, corrections
├── references/                # Framework docs, calibration methodology
└── logs/                      # Prediction & review records
```

---

## :shield: Boundaries

- It won't tell you what to bet on — probabilities and edges, decisions are yours
- Models only regular and extra time — no penalty shootout predictions
- Shows its work — flags uncertainty when model and market disagree
- Missing data is marked UNAVAILABLE — no guessing
- All web search results are timestamped and sourced

---

## :construction: Roadmap

- [x] ~~Live data — injury reports, lineup announcements, real-time odds~~ :tada:
- [x] ~~Round-adaptive correction — R1→R2→R3→KO dynamic coefficients~~ :tada:
- [x] ~~Upset analysis — 3-layer detection with Tier 1/2/3 classification~~ :tada:
- [ ] Support for more tournaments (Euro, Copa America, domestic leagues)
- [ ] Richer tactical models — player-level tracking, set-piece probabilities
- [ ] More staking strategies — fractional Kelly variants, confidence-weighted scaling
- [ ] Web dashboard for visualizations and accuracy trends

---

## :page_facing_up: License

MIT — see [LICENSE](LICENSE).
