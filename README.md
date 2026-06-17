# Play-Calling Analytics Dashboard

> Interactive Dash web app that benchmarks a high school football offense against the NFL 2024 play-by-play data, built as a coaching tool for an Indiana 6A varsity program.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Dash](https://img.shields.io/badge/dash-2.17+-purple)
![Plotly](https://img.shields.io/badge/plotly-5.18+-teal)
![License](https://img.shields.io/badge/license-MIT-green)

---

## The question

> Which play-calling tendencies actually move the chains, and where does a high school 6A program diverge from what the NFL does?

Built as the final project for INFO-H 517 Data Visualization, M.S. Sports Analytics program at IU Indianapolis. The app sits next to a coaching staff's existing tape workflow and gives them a numerical lens on their own tendencies versus league-average behavior on the same down and distance.

## Live demo

Hosted on Plotly Cloud. *(Link goes here once the deployment is live.)*

## What's inside

Five interactive visualizations driven by three layered filters, one of which acts as a shared cross-filter that updates two charts in a single round trip to the server.

| # | Visualization | What it answers |
|---|---|---|
| 1 | Pass / run mix by down, faceted vs NFL | When does our offense diverge from the league in play-type selection? |
| 2 | 3rd-down concept conversion, sorted with n labels | Which concepts earn their reps, which are cut candidates? |
| 3 | Field zone × quarter heatmap (diverging, zero-anchored) | Where on the field and when in the game does the offense break down? |
| 4 | QB time-to-throw distributions by down | How does processing speed shift across our quarterback depth chart? |
| 5 | NFL 3rd-and-long EPA leaderboard (custom lollipop) | Which league offenses set the ceiling on this down and distance? |

## Design decisions

- **Marks and channels (Munzner Ch. 5).** Position and length carry every quantitative comparison. Color is reserved for categorical encoding (play type, QB, EPA tier) or magnitude (sequential teal for conversion, diverging red-blue for yards per play).
- **Color (Munzner Ch. 10).** Okabe-Ito qualitative palette throughout, passes deuteranopia, protanopia, and tritanopia simulation. Diverging scale is anchored on zero so positive cells read instantly. Sequential teal for ordered conversion rates.
- **Anomaly annotations.** Three explicit callouts: cut-candidate concepts, the red-zone gap, and the QB processing-speed delta on 3rd down. Annotations point at insight, not at success.
- **Garbage time filter.** NFL leaderboard restricted to competitive snaps (0.05 ≤ win probability ≤ 0.95) and a minimum sample of 20 plays per team to keep the rank stable.
- **Small-sample guard.** Concept chart enforces n ≥ 4 per slice so a 1-for-1 fluke cannot outrank 22-for-30 reps.

## Tech stack

- **Backend.** Python 3.10+, Dash 2.17+, Plotly 5.18+, pandas 2.0+
- **Hosting.** Plotly Cloud (free tier), one-click deploy from a folder upload. The app also runs cleanly on Render via the included `requirements.txt` and the exposed `server = app.server` Flask hook.
- **Data.** nflverse / nflfastR for the NFL 2024 regular season (public). High school play-by-play is hand-charted from Hudl film (not redistributed, see Data section).

## Project structure

```
.
├── app.py              # All application logic in one file
├── requirements.txt    # Python dependencies pinned by minimum version
├── README.md           # You're here
├── LICENSE             # MIT
└── .gitignore          # Excludes data files, virtualenvs, build artifacts
```

The single-file layout is intentional. Plotly Cloud's deployment model uploads a folder and looks for `app.py`. Keeping everything in one module makes deployment a drag-and-drop. Chart builders are pure functions so they're testable in isolation from the Dash layer.

## Running locally

```bash
git clone https://github.com/<your-username>/play-calling-analytics.git
cd play-calling-analytics
pip install -r requirements.txt
python3 app.py
```

The app launches on `http://127.0.0.1:8050`. Synthetic data generators run by default, so the app works immediately with no CSV downloads required.

## Data

The repo ships with two seeded synthetic data generators that produce realistic distributions matching the schema of the real source files. The app loads real CSVs if present alongside `app.py` and falls back to synthetic data otherwise. This was a deliberate design choice:

- **High school play-by-play data is private.** It belongs to the program that charted it. The real CSV is excluded from this repo via `.gitignore` and the synthetic generator stands in for portfolio viewers.
- **NFL data is public.** Pull it from the [nflverse data releases](https://github.com/nflverse/nflverse-data/releases) if you want to run on real numbers. The truncated CSV used in development includes the ten columns referenced in `make_nfl()`.

If you want to use the app on your own program's data, the schema is documented inline in the `make_westfield()` function.

## Methodology details

- **Sample sizes.** Westfield charting includes 500 plays across 14 games of the 2025 varsity season. NFL data sampled at 10,000 plays from the 49,492 total in the nflverse 2024 release.
- **Conversion definition.** 3rd-down conversion = play result in `{First Down, TD}`. Red-zone TD rate = `result == 'TD'` for plays where field zone is `Red Zone`.
- **Time to throw.** Pass plays only, dropbacks measured from snap to release (or to sack). Excluded from run and special teams calculations.
- **EPA leaderboard.** Restricted to teams with n ≥ 20 qualifying snaps and to competitive game states only.

## Future work

- Wire to a real-time Hudl export pipeline so the dashboard updates after each game.
- Add concept-level overlay so the NFL leaderboard's top eight teams reveal which concepts they leaned on.
- Bayesian hierarchical model for concept conversion rates with shrinkage, addressing the small-sample problem the current n threshold only partially solves.

## License

MIT. See [LICENSE](LICENSE).

## Author

Built by Jay R. Kelley, M.S. Sports Analytics candidate at IU Indianapolis, Data Analytics Coach for the Westfield Shamrocks varsity football program.

- LinkedIn: [in/jay-r-k-b7a0a0164](https://linkedin.com/in/jay-r-k-b7a0a0164)
- Email: jekelle@iu.edu

---

*If you're a coach, analyst, or graduate student interested in adapting this for your own program, open an issue or reach out directly. Happy to talk through the schema and the design tradeoffs.*
