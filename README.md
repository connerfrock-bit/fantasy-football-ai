# 🏈 Fantasy Football Draft Tool

A personal fantasy football draft & season tool: a Python data pipeline that blends
**multi-source consensus rankings** (ADP + projections) with three self-contained
HTML dashboards — a **Draft Cockpit**, a **Player Database**, and a **Lineup Optimizer**.

No accounts, no API keys, no dependencies to install — just Python's standard library.

---

## Quick start

### Windows — the easy way
**Double-click [`run.bat`](run.bat).** It starts the local server and opens the app in your
browser automatically. Keep that window open while you use the app; close it to stop.

### Any OS — the manual way
From the project folder:

```bash
python -m http.server 8000
```

Then open **http://localhost:8000/** in your browser. That landing page links to all three
dashboards.

> **Why a server?** The pages load the rankings data file, which browsers block over
> `file://`. This tiny built-in server fixes that — you can't just double-click the HTML.
> If port 8000 is busy, use `python -m http.server 8001` and open `http://localhost:8001/`.

---

## Running from a fresh clone

```bash
git clone https://github.com/connerfrock-bit/fantasy-football-ai.git
cd fantasy-football-ai
python -m http.server 8000
```

Open **http://localhost:8000/**. The rankings work immediately — a compiled data snapshot
ships with the repo, so there's nothing to build first.

**Requirements:** [Python 3](https://www.python.org/downloads/) and any web browser.

---

## The three dashboards

| Dashboard | What it does |
|---|---|
| **Draft Cockpit** | Run a live or mock draft — real-time board, tiers, injury flags, and pick recommendations. |
| **Player Database** | Browse and sort every player by consensus ADP, projections, and tier across PPR / Half / Standard. |
| **Lineup Optimizer** | Set your best weekly starters from the roster you drafted in the Cockpit. |

---

## Refreshing the rankings

The committed data is a snapshot. To pull the latest numbers on demand:

```bash
python pipeline/build_players.py
```

Then reload the page in your browser (`Ctrl+R`). No keys needed — every source is free.

**Automatic daily refresh (Windows):** a Task Scheduler job (`FF Data Refresh`) runs
`pipeline/refresh.py` every day at 6 AM and rewrites the data files. The landing page shows
when the rankings were last updated.

---

## Data sources

Consensus ADP is blended from five free sources:

- **Sleeper** · **ESPN** · **MyFantasyLeague** · **FantasyCalc** · **Fantasy Football Calculator**

Projections come from Sleeper and ESPN. (Yahoo was a source until Yahoo closed its Fantasy
API to open access in mid-2026; the feed is wired but disabled pending an access application.)

---

## Project layout

```
index.html              Landing page (links to the dashboards)
run.bat                 One-click Windows launcher
Design/                 The three .dc.html dashboards + shared runtime (support.js)
pipeline/
  build_players.py      Builds the consensus dataset from all sources
  refresh.py            Daily runner (build + export), used by the scheduled task
  data/ff_players.*     Compiled output (json / js / csv) consumed by the dashboards
```
