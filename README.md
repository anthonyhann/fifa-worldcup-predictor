# 🏆 FIFA World Cup Predictor

<p align="center">
  <strong>A Self-Evolving Quantitative Football Prediction System</strong><br>
  <em>Elo Ratings · Poisson Distribution · Monte Carlo Simulation · Bayesian Inference</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="status">
</p>

---

## 📖 Overview

The **FIFA World Cup Predictor** is a comprehensive, self-improving football prediction engine designed specifically for FIFA World Cup matches. It integrates quantitative modeling (Elo ratings, Poisson distribution, Monte Carlo simulation) with Bayesian probabilistic reasoning and tactical context analysis. What makes it unique is its **self-evolution capability** — after every match, it reviews real-world results, calibrates its parameters, and continuously improves prediction accuracy and betting ROI.

### 🎯 Core Objectives

1. **Maximize prediction accuracy** — learn from every match outcome
2. **Maximize betting returns** — identify value bets and optimize staking strategies

---

## 🧠 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   FIFA World Cup Predictor v3.0                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ Pre-Match    │   │ Post-Match   │   │ Self-Evolution       │ │
│  │ Prediction   │──▶│ Review       │──▶│ Engine               │ │
│  │              │   │              │   │                      │ │
│  │ • Elo Rating │   │ • Web Search │   │ • Parameter Auto-Cal │ │
│  │ • Poisson xG │   │ • Multi-Dim  │   │ • Accuracy Tracking  │ │
│  │ • Monte Carlo│   │   Scoring    │   │ • Trend Detection    │ │
│  │ • Bayesian   │   │ • Elo Update │   │ • Strategy Optimize  │ │
│  │   Inference  │   │ • Stats Sync │   │                      │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                          │                                       │
│                          ▼                                       │
│                 ┌────────────────┐                               │
│                 │ Profit Tracker │                               │
│                 │ • Virtual Bets │                               │
│                 │ • ROI Tracking │                               │
│                 │ • Max Drawdown │                               │
│                 │ • Strategy Comp│                               │
│                 └────────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🔮 Prediction (Quant + Bayesian)

| Feature | Description |
|---------|-------------|
| **Match Prediction** | Elo ratings + Poisson xG → Home/Draw/Away probabilities + most likely scores |
| **Upset Detection** | 3-layer criteria: style mismatch, form variance, tournament advantage |
| **Advancement Simulation** | 100K Monte Carlo runs to project knockout stage probabilities |
| **Odds Value Detection** | Model probability vs. implied market probability; flags ≥3% edge + Kelly stake |
| **Bayesian P0→P1** | Prior → Tactical Context → League Factors → Likelihood Update → Posterior |
| **Tactical Analysis** | Possession trap detection, style counter analysis, tournament-specific modifiers |
| **Scenario Narratives** | Generates 2-4 distinct match scenarios based on tactical mechanisms |
| **v2.0 Opener Patch** | Auto-applies xG correction for tournament openers (favorite goals ×0.5, underdog boost, draw +15%) |

### 🧬 Self-Evolution (v3.0)

| Feature | Description |
|---------|-------------|
| **Post-Match Review** | Web search real results → compare vs. prediction → 100-point multi-dimensional score |
| **Elo Live Update** | Auto-update Elo after each match (K=32 group stage / K=48 knockout) |
| **Parameter Auto-Calibration** | Optimizes Elo weight, draw boost, goal corrections, K-factor from review data |
| **Accuracy Tracking** | Tracks overall/recent directional accuracy with trend detection (improving/stable/declining) |
| **Profit Tracking** | Virtual betting simulation → ROI → strategy comparison (Half-Kelly / Fixed / Value) |
| **Evolution Reports** | Parameter change history, accuracy timeline, strategy optimization suggestions |

---

## 📁 File Structure

```
fifa-worldcup-predictor/
├── README.md                          # You are here (English)
├── README_zh.md                       # Chinese version
├── SKILL.md                           # Full skill definition & workflow
├── scripts/
│   ├── prediction_engine.py           # Core engine (Elo + Poisson + Monte Carlo)
│   ├── odds_fetcher.py                # Live odds from The Odds API
│   ├── post_match_review.py           # Post-match review & web search
│   ├── evolution_engine.py            # Self-evolution & parameter calibration
│   └── profit_tracker.py              # Virtual betting & ROI tracking
├── data/
│   ├── elo_ratings.json               # Elo ratings for 48 World Cup teams
│   ├── team_stats.json                # Team attack/defense stats (EMA updated)
│   └── corrections.json               # Correction factors (openers, upsets, etc.)
├── references/
│   ├── analytical_framework.md        # Bayesian analysis framework reference
│   └── calibration_methodology.md     # Parameter calibration methodology
└── logs/
    ├── prediction_log.md              # Pre-match prediction records
    ├── review_log.jsonl               # Post-match review records (JSONL)
    ├── profit_track.jsonl             # Betting profit/loss records (JSONL)
    ├── evolution_state.json           # Evolution engine state & param history
    └── profit_state.json              # Profit tracking state
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Internet access (for live odds and post-match web search)

### Installation

```bash
# Clone the repository
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor

# No external dependencies required — pure Python standard library!
```

### Predict a Match

```python
from scripts.prediction_engine import FootballPredictionEngine

engine = FootballPredictionEngine(data_dir='data')

# Argentina vs France (knockout stage)
prediction = engine.predict('Argentina', 'France', is_knockout=True)

print(f"Win: {prediction['final']['win_a']}%")
print(f"Draw: {prediction['final']['draw']}%")
print(f"Lose: {prediction['final']['win_b']}%")
print(f"xG: {prediction['xg_a']} - {prediction['xg_b']}")
print(f"Most Likely Score: {prediction['most_likely_scores'][0]}")
```

### Review After Match

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('Argentina', 'France', (2, 1), prediction)

print(f"Review Score: {review['scores']['total']}/100 ({review['scores']['grade']})")
print(f"Elo Changes: {review['elo_changes']}")
print(f"Direction Correct: {review['scores']['direction_correct']}")
```

### Trigger Evolution

```python
from scripts.evolution_engine import EvolutionEngine

evo = EvolutionEngine('.')
result = evo.evolve()

print(f"Evolved: {result['evolved']}")
print(f"Parameters Changed: {list(result.get('changes', {}).keys())}")
print(f"Accuracy Metrics: {evo.compute_accuracy_metrics()}")
```

### Track Profit

```python
from scripts.profit_tracker import ProfitTracker

tracker = ProfitTracker('.')

# Simulate a bet
bet = tracker.simulate_bet(
    'Argentina', 'France', prediction,
    odds={'home': 2.80, 'draw': 3.20, 'away': 2.50},
    actual_score=(2, 1)
)

print(f"Result: {bet['result']}")
print(f"Profit: {bet['profit']}")

# Full report
report = tracker.get_profit_report()
print(f"ROI: {report['roi']}%")
print(f"Max Drawdown: {report['max_drawdown']}%")
```

---

## 🔬 How It Works

### 1. Pre-Match Prediction

```
User Input (Teams, Stage)
    ↓
Elo Rating Comparison → Win Expectancy
    +
Poisson Distribution → Expected Goals (xG)
    +
Correction Factors (Openers, Home Advantage)
    ↓
Base Probability (P0)
    ↓
Bayesian Tactical Context Update
  ├── Possession Trap Detection
  ├── Style Counter Analysis
  ├── Injury/Lineup Likelihood
  └── Tournament-Specific Factors
    ↓
Posterior Probability (P1) + Scenario Narratives
    ↓
Odds Comparison + Kelly Stake Calculation
```

### 2. Post-Match Review

The system searches the web for real match results, then scores predictions on a 100-point scale:

| Dimension | Max Score | Criteria |
|-----------|-----------|----------|
| Direction | 30 | Correct winner = full; correct draw = partial |
| Score | 30 | Exact match gets bonus; close total = up to 20 |
| xG Accuracy | 20 | Error <0.5 goals = 20; <1.0 = 15; <2.0 = 10 |
| Odds Value | 20 | Correct low-probability call = 20 |

Elo ratings and team stats are automatically updated after each review.

### 3. Self-Evolution

After ≥3 match reviews, the evolution engine triggers automatic calibration:

| Parameter | Trigger | Adjustment Logic |
|-----------|---------|------------------|
| `ELO_WEIGHT` | Elo accuracy vs overall | Adjust ±0.05 based on deviation |
| `OPENER_DRAW_BOOST` | Actual opener draw rate | Adjust ±0.03 per round |
| `FAV_GOAL_DISCOUNT` | Opener xG bias | Adjust based on goal deviation |
| `K_FACTOR` | Overall accuracy trend | ↑ if accuracy declining; ↓ if stable/high |

All changes are capped at ±20% per iteration and logged in `evolution_state.json`.

### 4. Profit Tracking

Four strategies tracked simultaneously:

| Strategy | Description |
|----------|-------------|
| **Half-Kelly** | Kelly criterion × 0.5 (conservative) |
| **Full-Kelly** | Full Kelly criterion (aggressive) |
| **Fixed Fraction** | Fixed 5% of bankroll per bet |
| **Value Only** | Bet only when model edge ≥ 3% |

---

## 📊 Data Sources

- **Elo Ratings**: Pre-loaded for 48 World Cup teams, dynamically updated after each match
- **Team Stats**: Goals scored/conceded per match (exponential moving average, α=0.3)
- **Live Odds**: Via The Odds API (`scripts/odds_fetcher.py`)
- **Match Results**: Web search for post-match review
- **Correction Factors**: Empirically calibrated from historical World Cup data

---

## 🛡️ Guardrails

- ⚠️ **Never gives direct betting advice** — provides analytical frameworks only
- 📊 **Never fabricates data** — all calculations executed via code
- 🔍 **Always flags uncertainty** — highlights when model vs. market diverge significantly
- ⚠️ **Always includes risk disclaimer** — at the end of every analysis
- 🎲 **Does NOT predict penalty shootouts** — models only 90/120-minute outcomes
- 🏷️ **Always cites sources** — web search data labeled with URL and timestamp
- 🚫 **Missing data = UNAVAILABLE** — never guesses or interpolates missing values

---

## 📝 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Areas of interest:

- Additional league/tournament support
- More sophisticated tactical models
- Alternative staking strategies
- API integrations for live data

---

<p align="center">
  <sub>Built with ❤️ for football analytics enthusiasts</sub>
</p>
