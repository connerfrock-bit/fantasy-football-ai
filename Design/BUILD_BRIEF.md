# Fantasy Football AI — Build Brief (Claude Code Handoff)

This package is a **working, interactive design prototype** of a fantasy-football draft + season tool, built as three self-contained HTML pages. It is the **spec for the UI and the decision engines**. The hard part of the real product — live data — is intentionally faked here with a clean static sample. Read this whole file before building.

---

## What's in the package

| File | What it is | Notes |
|---|---|---|
| `Draft Cockpit.dc.html` | Live draft-day assistant + simulator | Has its **own inline player pool** (incl. DST/K, ADP, VORP, tiers) |
| `Lineup Optimizer.dc.html` | Weekly start/sit optimizer, multi-league | Reads `players-data.js`; persists teams to `localStorage` |
| `Player Database.dc.html` | Sortable advanced-stat table | Reads `players-data.js` |
| `players-data.js` | The shared player DB (the data contract) | See the DATA CONTRACT header comment inside the file |
| `support.js` | Rendering runtime for the `.dc.html` files | Do not hand-edit |

> The pages are authored as "Design Components" (`.dc.html`). For a production rewrite you do **not** need that runtime — treat the markup as the component tree and the `class Component { renderVals() }` logic as the view-model. Port to React/Vue/Svelte directly; every value the template reads is returned from `renderVals()`.

---

## The #1 thing to understand: data is 75% of this product

Everything here is a thin wrapper around four data feeds that **do not exist in the prototype**:

1. **Player universe** — every rostered NFL player, position, team, depth chart, bye. (Free: nflverse, Sleeper API.)
2. **Advanced stats (3 yrs)** — target share, air yards, aDOT, snap %, route %, red-zone usage, rush share, YPC. (Free: **nflverse / nflfastR**. Paid: PFF.)
3. **Projections** — season + weekly points per player. **This is the moat and the hardest piece.** License first (FantasyPros, SportsData.io, FantasyNerds), build your own model later.
4. **Live in-season feed** — injuries, depth-chart moves, snap counts, Vegas lines, weather, results. (SportsData.io, or stitched from free sources.)

**ADP / consensus rankings** (the draft edge): pull from multiple sources — ESPN, Sleeper, Yahoo, FantasyPros — normalize to one scale, and store both the per-source value and a blended consensus. The prototype *simulates* this from one base ADP; replace with real multi-source ingestion.

> ESPN has **no official draft API**. Auto-syncing a live ESPN draft is the single riskiest integration. Design for the **manual fallback the prototype already implements** (you tap players off the board) as the reliable path; treat any ESPN automation as best-effort.

---

## The decision engines (these ARE production-ready logic)

The math in these files is real and is your backend spec. Port it server-side and feed it real numbers.

### Draft recommendation (`Draft Cockpit.dc.html`)
Blends four signals into one score per available player:
- **VORP** — `proj − replacementBaseline[pos]`, where the baseline is the Nth-best player at the position and **N scales with league size** (`buildPlayers()` → `replIdx`). Bigger leagues → deeper replacement → different values.
- **Positional need** — `needMult(pos)` weights by your current roster vs. required slots (respects the **numQB / numFlex** league settings).
- **Tier cliff** — last player in a talent tier gets a bump (`inTier`).
- **Run risk** — how many at the position will be gone before your next snake pick (`likelyGone`, uses consensus ADP + the snake math in `teamOnClock`).
- **Market edge** — experts-vs-ESPN ADP delta surfaces players your league-mates will let slide.
K/DST are suppressed until the final picks (`needMult` returns ~0 early). Scoring format (PPR/half/standard) re-ranks via an estimated-receptions adjustment.

### Weekly optimizer (`Lineup Optimizer.dc.html`)
- **Projection range** per player: `floor / proj / ceiling` from `weekProj × matchupMult`, widened by `(1 − consistency)`. Replace the derivation with **real weekly projections**; keep the floor/ceiling concept.
- **Optimal lineup**: max projected points subject to slot eligibility (`optimalLineup`), respecting user **Start/Sit locks** (`currentLineup`).
- **Start/sit intelligence**: points left on bench, closest call (floor vs ceiling), matchup/volatility flags.
- Best public signal to add for production: **Vegas implied team totals**.

### Waiver analyzer (NOT built — next feature)
Rank by **opportunity change** (snap/target share trending up, vacated touches from injuries ahead on the depth chart, RoS schedule), not last week's points. Output targets for *that team's* needs + a suggested FAAB bid %. Sleeper gives trending adds / % rostered free.

---

## Architecture (recommended)

```
Ingestion jobs (daily + live)  →  Normalized DB (players, stats, projections, ADP, your leagues/rosters)
        →  Engine services (draft / lineup / waiver)  →  API  →  Fast, mobile-friendly, offline-tolerant frontend
```
- **Draft day must be bulletproof:** preload everything before the draft; never block on the network while you're on the clock. The prototype keeps all state client-side for exactly this reason.
- **In-season freshness:** automated daily pipelines, or the tool rots by Week 3.

---

## State & integration notes

- **Lineup Optimizer** persists to `localStorage` key `ffOptimizerTeams_v1` → `{ teams: [{id,name,roster:[names],locks:{}}], activeId }`. Multi-league is first-class.
- **Draft Cockpit** persists setup config to `ffCockpitConfig_v1`.
- **Integration to finish (designed, not wired):** at the end of a draft, write the drafted skill players into `ffOptimizerTeams_v1` as a new team so the user flows draft → season management seamlessly. Requires a unified player-id key (see next point).
- **Unify the player key.** The cockpit currently uses its own inline pool; the optimizer/database use `players-data.js`. In production, both must read **one** source keyed by a stable player ID (not name string). The `players-data.js` DATA CONTRACT comment defines the canonical field shape — converge everything onto it.

---

## Suggested build order

1. **Data layer first.** Stand up ingestion for player universe + advanced stats (nflverse) + one projection source + multi-source ADP. Normalize, store, key by player ID.
2. **Draft tool** on top of that data (the engines already exist here).
3. **Weekly optimizer** (add Vegas/matchup/weather).
4. **Waiver intelligence** + live-season tracking.
5. **League auto-import** (Sleeper has a real API; ESPN/Yahoo are harder) and mobile polish.

Scope v1 to ONE format (e.g. 10-team PPR snake) before generalizing — the prototype already parameterizes teams/scoring/roster, but test one path end-to-end first.

---

## Running the prototype
Open any of the three `.dc.html` files in a browser. They cross-link via the in-app nav. No build step. To produce a single offline file for sharing, run an HTML inliner (note: that path needs a `<template id="__bundler_thumbnail">` added per page — not required for the Claude Code build).
