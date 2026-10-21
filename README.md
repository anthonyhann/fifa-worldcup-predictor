<div align="center">

# 🏆 FIFA World Cup Predictor

### A World Cup prediction engine that grades itself after every match

Elo ratings + Poisson xG + 100,000-run Monte Carlo + Bayesian tactical context — then automatic post-match review and round-adaptive self-calibration. **Zero dependencies: pure Python standard library.**

[![version](https://img.shields.io/badge/version-v4.17-blue?style=flat-square)](SKILL.md)
[![python](https://img.shields.io/badge/python-3.10%2B-green?style=flat-square)](#-quickstart)
[![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?style=flat-square)](#-quickstart)
[![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
[![stars](https://img.shields.io/github/stars/anthonyhann/fifa-worldcup-predictor?style=flat-square)](https://github.com/anthonyhann/fifa-worldcup-predictor/stargazers)

[Quickstart](#-quickstart) · [How it learns](#-the-learning-loop) · [Numbers](#-numbers-verifiable-in-this-repo) · [Layout](#-repository-layout) · [Boundaries](#-boundaries--when-not-to-use-it) · [中文版](README_zh.md)

</div>

## Most prediction tools, probably

- Tell you who wins — then **never look back** at what actually happened
- Use the same coefficients for Round 1 and the knockout final, as if tournament dynamics didn't exist
- Say "trust the model" with **no accuracy ledger** you can audit

This engine does the opposite: after each match it fetches the real result, scores its own prediction on a 100-point scale, updates team ratings, and recalibrates its per-round coefficients — with an overfitting defense that rejects jumps it can't justify. Every iteration is logged, so you can watch it get sharper (or catch it getting worse).

## What it can do

| Stage | Capability |
|---|---|
| 🔮 **Pre-match** | Win/draw/loss probabilities + most likely scores (Elo + Poisson + 100k Monte Carlo), round-adaptive coefficients (R1 conservative ×0.5 → R2 bounce-back ×1.10 → R3 normal → KO defensive), 3-layer upset detection, tournament-path simulation, mispriced-odds flags with Kelly sizing |
| 🛰️ **Live data** | Starting lineups + formations ~1h before kickoff, injury reports, multi-bookmaker odds — injuries shift strength ratings, formations shift expected goals (BSD API, free key) |
| 📺 **Live scores** | Real-time results via the worldcup2026 REST API (all 104 matches, no auth), auto-fed into the review engine |
| 📊 **Post-match** | Auto-review every prediction against the real result; 100-point scoring across direction / exact score / goal totals / value calls; Elo ratings updated from what actually happened |
| 🧬 **Self-evolution** | Round-adaptive auto-calibration after 3+ reviews, backtest validation before applying new parameters, triple overfitting defense (adjacent-round reversal >0.45, single-step change >0.20, <3 matches = low confidence) |
| 💰 **Profit tracking** | 4 staking strategies simulated in parallel: half-Kelly / full-Kelly / fixed-2% / value-only, with ROI and max-drawdown reports |

## 🚀 Quickstart

```bash
# 1. Clone (no pip install — pure standard library)
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor

# 2. Look at the current accuracy ledger
python3 scripts/evolution_engine.py --report

# 3. Predict a match
python3 -c "
from scripts.prediction_engine import FootballPredictionEngine
engine = FootballPredictionEngine(data_dir='data')
p = engine.predict('Argentina', 'France', is_knockout=True)
print(p['final'])  # win/draw/loss probabilities + top scores
"
```

**For AI agents** — this repo ships a [SKILL.md](SKILL.md). Paste this to your agent:

> Read the SKILL.md in https://github.com/anthonyhann/fifa-worldcup-predictor and predict <Team A> vs <Team B> with it.

Optional: set `BSD_API_KEY` to enrich predictions with lineups, injuries and live odds. Without it, everything above still works.

## 🔁 The learning loop

1. **Predict** — Elo + Poisson xG + tactical context + live data
2. **Review** — fetch the real result, score the prediction, log it
3. **Learn** — every 3+ reviews triggers round-adaptive recalibration, backtested before applied
4. **Improve** — coefficients drift toward reality, one match at a time

The loop is documented in public: [SKILL.md](SKILL.md) records **23 version iterations (v1.1 → v4.17)**, each with the lesson that caused it. The most instructive one — **v4.7**: the engine caught *its own metric-inflation bug* (self-reported accuracy 98.6% → real 36.7% after the fix) and reset its parameters accordingly. A predictor that audits itself is the point.

## 📊 Numbers, verifiable in this repo

- **13 Python scripts**, ~5,750 LOC, **0 third-party dependencies** (json / math / urllib only)
- **48 national teams** with Elo ratings + attack/defense stats; **54 correction factors** (`data/`)
- **100,000** Monte Carlo simulations per tournament path (`prediction_engine.py`)
- **4** staking strategies tracked (`profit_tracker.py`)
- **365** post-match review entries logged (`logs/review_log.jsonl`) and counting
- Self-tracked accuracy, as documented in [SKILL.md](SKILL.md): **~78% win/draw/loss direction**, ~38% overall, 55% on the most recent 20 matches — self-reported, auditable, and honest about its misses (handicap direction: 1/9, marked low-confidence)
- **2** free data APIs integrated: BSD Football API (lineups/injuries/odds) + worldcup2026 (104-match live scores)

## 📂 Repository layout

```
fifa-worldcup-predictor/
├── SKILL.md                  # Full capability spec + 23-version evolution log
├── scripts/
│   ├── prediction_engine.py  # Core engine: Elo + Poisson + Monte Carlo + consensus (41 methods)
│   ├── live_data_fetcher.py  # Lineups / injuries / odds / live scores
│   ├── evolution_engine.py   # Auto-calibration + backtest + overfitting defense
│   ├── post_match_review.py  # 100-point review scoring + result fetching
│   ├── profit_tracker.py     # 4-strategy betting simulation
│   ├── odds_fetcher.py       # Dual-source odds comparison
│   ├── wc2026_client.py      # worldcup2026 REST API client
│   └── …                     # + diagnostics, backtest, batch runners (13 total)
├── data/                     # elo_ratings / team_stats / corrections / h2h (48 teams)
├── references/               # Analytical framework, calibration methodology, live-data integration
├── outputs/                  # Sample prediction reports (R32 batches)
└── logs/                     # prediction_log.md, review_log.jsonl (365 entries), profit_track.jsonl
```

## ⚠️ Boundaries — when NOT to use it

- **It is not betting advice.** It outputs probabilities and market edges; every decision (and its consequences) is yours.
- **No penalty shootouts.** Only regular and extra time are modeled.
- **Scope is the 48-team 2026 World Cup.** Euro, Copa America and domestic leagues are on the roadmap, not supported today.
- **Live features need network.** Offline it still predicts from cached data, just without lineups/injuries/odds.
- **Self-reported accuracy.** The ~38% overall / ~78% direction figures come from its own review log — treat this as a research tool, and run your own backtests before trusting it with anything real.


## 🙋 About

Built and iterated in public across the 2026 World Cup — 23 documented versions, each driven by a real match the model got wrong. It is dogfooded daily during the tournament, and the accuracy ledger is part of the repo. If it saves you from hand-tuning Elo coefficients at 2 a.m., a ⭐ tells the next analyst it works.

## License

MIT — see [LICENSE](LICENSE).
