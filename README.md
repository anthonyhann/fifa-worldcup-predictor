# FIFA World Cup Predictor

<p align="center">
  <strong>Predict World Cup matches. Review real results. Get better over time.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
</p>

> 中文用户请阅读 [README_zh.md](README_zh.md)

---

## What is this?

This tool helps you predict FIFA World Cup matches. You feed it two teams and it tells you who's likely to win, by what score, and whether the betting odds look off. That's the baseline. What sets it apart is that after each match, it checks what actually happened and calibrates itself — so the more matches it watches, the better it gets.

Think of it as an analyst who never stops studying film.

---

## What it can do

### Before the match

- **Predict win/draw/loss odds** for any World Cup matchup, along with the most likely final score
- **Spot potential upsets** early — when a weaker team has a real shot due to style mismatches or tournament context
- **Simulate tournament paths** to see each team's odds of reaching the quarters, semis, or final
- **Find mispriced betting odds** — if the market says one thing and the model disagrees by enough margin, it flags it
- **Generate match scenarios** — not just numbers, but narratives about how the game might play out

### After the match

- **Review every prediction** automatically by searching for real match results
- **Score itself** on a 100-point scale across direction, score accuracy, goal prediction, and value calls
- **Update team ratings** based on what actually happened on the pitch

### Self-improvement

- **Auto-calibrate** after watching enough matches — tweaks its own internal parameters based on what it got wrong
- **Track accuracy over time** so you can see if it's getting smarter or needs attention
- **Run profit simulations** across multiple betting strategies to see which approach would have made money

---

## Quick start

```bash
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor
```

That's it. No dependencies to install — the whole thing runs on Python's standard library.

### Predict a match

```python
from scripts.prediction_engine import FootballPredictionEngine

engine = FootballPredictionEngine(data_dir='data')

# Argentina vs France, knockout stage
prediction = engine.predict('Argentina', 'France', is_knockout=True)

print(f"Argentina win: {prediction['final']['win_a']}%")
print(f"Draw:          {prediction['final']['draw']}%")
print(f"France win:    {prediction['final']['win_b']}%")
print(f"Most likely:   {prediction['most_likely_scores'][0]}")
```

### Review the result

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('Argentina', 'France', (2, 1), prediction)

print(f"Review: {review['scores']['total']}/100 — {review['scores']['grade']}")
print(f"Direction correct: {review['scores']['direction_correct']}")
```

### Check how it's improving

```python
from scripts.evolution_engine import EvolutionEngine

evo = EvolutionEngine('.')
evo.evolve()          # auto-calibrates if enough data
print(evo.compute_accuracy_metrics())
```

### Simulate betting returns

```python
from scripts.profit_tracker import ProfitTracker

tracker = ProfitTracker('.')
bet = tracker.simulate_bet(
    'Argentina', 'France', prediction,
    odds={'home': 2.80, 'draw': 3.20, 'away': 2.50},
    actual_score=(2, 1)
)
print(f"Result: {bet['result']}, Profit: {bet['profit']}")

report = tracker.get_profit_report()
print(f"ROI: {report['roi']}%, Max drawdown: {report['max_drawdown']}%")
```

---

## The learning loop

The system runs on a simple cycle:

1. **Predict** — Elo ratings set a baseline, Poisson distribution estimates expected goals, then tactical context and tournament factors refine the numbers
2. **Review** — after the match, it searches the web for the real score and compares against the prediction
3. **Learn** — every 3+ reviews triggers a recalibration pass that adjusts how much weight to give each factor
4. **Improve** — repeat, and the predictions get tighter

It tracks four betting strategies in parallel (half-Kelly, full-Kelly, fixed-fraction, and value-only) so you can see which approach fits your risk tolerance.

---

## What's inside

```
fifa-worldcup-predictor/
├── README.md                    # You're reading it
├── README_zh.md                 # Chinese version
├── scripts/
│   ├── prediction_engine.py     # Match prediction
│   ├── post_match_review.py     # Post-match review + web search
│   ├── evolution_engine.py      # Auto-calibration
│   ├── profit_tracker.py        # Betting simulations
│   └── odds_fetcher.py          # Live odds (The Odds API)
├── data/
│   ├── elo_ratings.json         # 48-team Elo ratings
│   ├── team_stats.json          # Attack/defense stats
│   └── corrections.json         # Calibrated correction factors
└── logs/                        # Prediction & review records
```

---

## Boundaries

Some things this tool is explicitly not designed for:

- It won't tell you what to bet on. It surfaces probabilities and edges; decisions are yours
- It doesn't predict penalty shootout outcomes — models only regular and extra time
- It shows its work. When the model disagrees with market odds by a lot, it tells you rather than papering over it
- If something goes wrong or data is missing, it says so instead of guessing
- Every web search result is timestamped and sourced

---

## Roadmap

Things we'd like to build next:

- [ ] Support for other tournaments and leagues (Euro, Copa America, domestic leagues)
- [ ] Richer tactical models — player-level tracking, formation analysis, set-piece probabilities
- [ ] More staking strategies — fractional Kelly variants, confidence-weighted scaling
- [ ] Live data integrations — injury reports, lineup announcements, real-time odds feeds
- [ ] Web dashboard to visualize predictions, reviews, and accuracy trends

Feel free to pick one and open a PR.

---

## License

MIT — see [LICENSE](LICENSE).
