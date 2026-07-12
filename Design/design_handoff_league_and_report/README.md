# Handoff: League Board + Draft Day Report Card

## Overview
Two features added to the **Draft Cockpit** (a fantasy-football live-draft / simulation tool):

1. **League Board** — a modal, openable at any time during a draft, that lets the user click any of the teams in the league (their own + every opponent) and inspect that team's roster, position composition, projected starter points, and full pick log.
2. **Draft Day Report Card** — a full-screen page that opens once the draft is complete: it lists every pick the user made (with `round.pick` labels), grades the user's roster strengths & weaknesses by position, and assigns letter grades to every team in the league.

Both features read entirely from data that already exists in the draft engine (the `draftedBy` map of which team drafted which player). No new data sources are required.

## About the Design Files
The file in this bundle — `Draft Cockpit.dc.html` — is a **design reference / working prototype written in HTML + a small reactive component runtime**. It is *not* meant to be shipped as-is. The task is to **recreate these two features inside your real codebase** (React, Vue, Svelte, SwiftUI, native, etc.) using its existing components, state management, and styling patterns. If the cockpit already exists in your app, you are adding two surfaces to it; the prototype shows exactly how they should look and behave.

The prototype's template syntax (`{{ value }}`, `<sc-for>`, `<sc-if>`) is just this runtime's way of doing `map`/conditional rendering — translate it to your framework's equivalents (`.map()`, `&&`, `v-for`, `ForEach`, etc.).

## Fidelity
**High-fidelity.** Final colors, typography, spacing, and interactions. Recreate the UI pixel-perfectly using your codebase's libraries. All hex values, sizes, and copy below are exact.

---

## Shared context (the existing engine)

These already exist in the cockpit and the two new features depend on them. If you're porting the whole app, you already have these; if you're only adding these features, here's what they rely on:

- `draftedBy` — object: `{ [playerName]: { team: <0-indexed team idx>, pick: <overall pick number> } }`.
- `this.players` — array of player objects: `{ name, pos, team, proj, vorp, tier, consAdp, ... }`. `pos` ∈ `QB | RB | WR | TE | K | DST`.
- `this.TEAMS` — number of teams (4–16). `this.myTeam` — the user's 0-indexed slot.
- `this.numQB`, `this.numFlex`, `this.numBench` — roster format. `this.ROSTER_MAX` — total roster size.
- Helpers:
  - `teamOnClock(overall)` → which team idx is picking at a given overall pick (snake order).
  - `pickLabel(overall)` → `"round.pick"` string, e.g. `"2.09"` (round number, then pick-in-round zero-padded to 2 digits).
  - `teamName(idx)` → `"YOU"` if `idx === myTeam`, else `"Team " + (idx+1)`.
  - `posColor(pos)` / `posBg(pos)` → see Design Tokens.
  - `buildRoster(players)` → returns `{ rows, bench, starterPts }`. `rows` is a list of slot rows (QB / RB1 / RB2 / WR1 / WR2 / TE / FLEX / D/ST / K + a BENCH divider + bench rows), each row carrying `{ isRow, isDivider, label, labelColor, name, sub, pts, ptsColor, nameColor, bg }`. `starterPts` is the summed projection of the filled *starting* slots. This is the single source of truth for "how good is a roster" — reuse it for any team, not just the user's.

Two small generic helpers were added to the engine for these features:

```
nextPickForTeam(team, fromOverall):
    for p from fromOverall to TEAMS*ROSTER_MAX:
        if teamOnClock(p) === team: return p
    return null

teamPlayersFor(team):                      // (inline in render)
    players
      .filter(p => draftedBy[p.name]?.team === team)
      .sort by draftedBy[p.name].pick asc   // draft order
```

---

## Screen 1 — League Board (modal)

### Trigger
A header button labeled **“League board”** (with a 6px `#5aa9f0` dot to its left), styled like the existing Lineup/Players buttons: padding `8px 12px`, radius `8px`, border `1px solid #2a2e37`, bg `#1a1d23`, text `#9aa0a9` 12px/700; hover bg `#22262e`, text `#e9eaec`.

Clicking it opens the modal at a **default selected team**: the team currently on the clock if that isn't you (so you see who's picking), otherwise the first opponent.

The **Recent Picks ticker** rows at the bottom of the cockpit are also clickable — clicking any pick opens the modal focused on that pick's team. Add `cursor:pointer` and a hover `border-color:#3a3f49` to ticker chips.

### State
- `viewTeam: number | null` — `null` = closed; a team index = open and showing that team. Add to initial state as `null`.
- `openTeam(idx)` → set `viewTeam = idx`. `closeLeague()` → set `viewTeam = null`.
- Derived: `leagueOpen = viewTeam != null` (guard `viewTeam` to a valid `0..TEAMS-1` range first; treat out-of-range as `null`).

### Layout
Full-viewport overlay: `position:fixed; inset:0; z-index:50; background:rgba(6,8,11,.72)`, flex-centered, padding `30px`. Clicking the backdrop closes; clicking the card does not (stop propagation).

Card: `width:940px; max-width:100%; height:78vh`, `background:#14161b`, `border:1px solid #262a33`, `border-radius:16px`, `overflow:hidden`, `box-shadow:0 30px 80px rgba(0,0,0,.6)`. Flex column:

1. **Header bar** (flex none, padding `16px 22px`, bottom border `#20242c`):
   - `LEAGUE BOARD` — 12px/700, letter-spacing 1.4px, `#9aa0a9`.
   - Subtitle (JetBrains Mono 11px, `#7e838d`): `"<TEAMS> teams · who's drafting what"`.
   - Close button pushed right (`margin-left:auto`): 30×30, radius 8px, border `#2a2e37`, bg `#1a1d23`, `✕` 15px `#aeb2ba`; hover bg `#22262e`, white.

2. **Body** (flex 1, `display:flex`, min-height:0):
   - **Team list** (left, `width:300px`, right border `#20242c`, `overflow-y:auto`, padding 10px): one row per team.
     - Row: flex column, gap 7px, padding `11px 12px`, margin-bottom 6px, radius 10px, `cursor:pointer`. Selected row: bg `#1c2027`, border `1px solid #3a3f49`; unselected: bg `transparent`, border `1px solid #191c22`. Hover bg `#1c2027`.
     - Row line 1 (flex, align center, gap 8px): an **on-the-clock dot** (7×7, `#f5b14c`, `blink 1.1s infinite`) shown only if that team is on the clock; team name 13.5px/700 (`#3ddc91` if it's YOU, else `#e9eaec`); a green **YOU** badge if it's the user (9px/800, `#06130d` on `#3ddc91`, padding `2px 5px`, radius 4px); pushed right, a pick-count label (JetBrains Mono 10.5px `#7e838d`): `"N picks"` (or `"1 pick"`).
     - Row line 2 (flex wrap, gap 4px): **position chips** — one per position the team holds, in fixed order `QB, RB, WR, TE, K, DST`, label `"<count> <POS>"` (use `DEF` instead of `DST`), JetBrains Mono 9.5px/700, colored with `posColor(pos)` text on `posBg(pos)`, padding `2px 6px`, radius 5px. If the team has no picks yet, show `"no picks yet"` (10px, `#5a5f68`) instead.
   - **Detail pane** (right, flex 1, flex column):
     - **Detail header** (padding `16px 22px`, bottom border `#20242c`): team name 18px/800; an `ON THE CLOCK` pill if applicable (10px/700, `#f5b14c` on `rgba(245,177,76,.13)`, padding `3px 8px`, radius 20px); a sub-line (JetBrains Mono 11px `#7e838d`): `"<N> / <ROSTER_MAX> drafted · next pick <label>"` (next pick from `nextPickForTeam(team, overall)`, or `"done"`). Pushed right: a `PROJ STARTER PTS` stat (10px `#7e838d` label; value JetBrains Mono 20px/700 `#3ddc91`).
     - **Detail body** (flex 1, `display:flex`):
       - **Roster slots** (flex 1, `overflow-y:auto`, padding 12px): render `buildRoster(teamPlayers).rows` exactly like the existing left-hand "MY ROSTER" panel — divider rows (10px/700 `#5a5f68` with top border) and player rows (34px position label, name + `pos · team` sub, right-aligned proj). Empty slots use the diagonal-striped bg `repeating-linear-gradient(45deg,#141519,#141519 6px,#16171c 6px,#16171c 12px)`.
       - **Pick log** (right, `width:250px`, left border `#20242c`, `overflow-y:auto`, padding `12px 14px`): heading `DRAFT PICKS` (10px/700 `#7e838d`). One row per pick in **reverse draft order** (most recent first): pick label (JetBrains Mono 10px `#6b7079`, width 32px), a 4×22 position color bar, name 12.5px/600 ellipsized, and a `pos · team` sub (JetBrains Mono 9.5px `#7e838d`). If no picks: `"No picks yet."` (12px `#5a5f68`).

### Behavior
- Selecting a team in the left list updates the detail pane (sets `viewTeam`).
- The board reflects live state — if opened mid-draft, on-the-clock indicators and counts are current.

---

## Screen 2 — Draft Day Report Card (full page)

### Trigger
On the existing **DRAFT COMPLETE** state, add a button **“View Draft Report Card →”**: `margin-top:6px`, gradient bg `linear-gradient(135deg,#3ddc91,#22b873)`, no border, text `#06130d` 14px/800, padding `13px 24px`, radius 11px; hover `filter:brightness(1.07)`.

### State
- `showReport: boolean` — initial `false`. `onOpenReport` sets `true`, `onCloseReport` sets `false`.
- Derived: `reportOpen = draftIsComplete && showReport`. (Gating on completion means a reset, which clears completion, also hides the report.)

### Layout
Full-viewport page: `position:fixed; inset:0; z-index:60; background:#0b0c0f; overflow-y:auto`. Inner container `max-width:1160px; margin:0 auto; padding:26px 30px 60px`.

1. **Top bar** (flex, gap 12px, margin-bottom 22px): the app's `D` logo mark (30×30, gradient `135deg,#3ddc91,#1f8a5b`, radius 7px), league name 13px/700, and pushed right a **“← Back to cockpit”** button (bg `#1a1d23`, border `#2a2e37`, `#aeb2ba` 12px/700, padding `9px 16px`, radius 9px; hover bg `#22262e`) → `onCloseReport`.

2. **Hero** (flex, gap 18px, margin-bottom 18px):
   - **Left card** (flex 1, bg `linear-gradient(135deg,#161922,#121419)`, border `#20242c`, radius 16px, padding 28px): eyebrow `DRAFT REPORT CARD` (11px/700, letter-spacing 2px, `#3ddc91`); headline `"Your draft is in the books."` (34px/800, letter-spacing -.5px); sub-line (14px `#9aa0a9`, max-width 560px): the summary string + `"<N> picks · <starterPts> projected starter points."`.
   - **Grade card** (flex none, `width:236px`, bg = grade bg tint, border = grade color, radius 16px, centered column): `YOUR GRADE` label (11px/700 `#9aa0a9`); the **letter grade** at 84px/800 in the grade color; rank label `"<ordinal> of <TEAMS>"` (13px/700 `#cfd2d7`).

3. **Two-column grid** (`grid-template-columns:1.15fr 1fr; gap:18px; margin-bottom:18px`):
   - **Your Picks card** (bg `#14161b`, border `#20242c`, radius 14px): header `YOUR PICKS` (11px/700 `#9aa0a9`) + a right-aligned `round.pick` caption. One row per pick **in draft order**: a `round.pick` badge (JetBrains Mono 12px/700 `#cfd2d7`, bg `#0f1115`, border `#20242c`, padding `5px 9px`, radius 7px, min-width 50px, centered), a 5×30 position color bar, name 14px/700 ellipsized, `pos · team` sub (JetBrains Mono 10.5px `#7e838d`), right-aligned proj (JetBrains Mono 13px/600 `#9aa0a9`). Row hover bg `#191c22`.
   - **Right column** (flex column, gap 18px):
     - **Roster Strengths card**: header dot `#3ddc91` + `ROSTER STRENGTHS` (11px/700 `#3ddc91`). One row per strength: a position pill (13px/800, `posColor` on `posBg`, width 58px, padding `9px 0`, radius 9px, centered), then a tier word (14px/700 `#3ddc91` — `Elite` / `Strong`) and a detail line (12px `#9aa0a9`): `"<ordinal> of <TEAMS> in the league at <POS>"`.
     - **Roster Weaknesses card**: same structure, header dot + text `#f0726a`; tier word `#f0726a` (`Thin` / `Barren`).

4. **League Draft Grades card** (full width, bg `#14161b`, border `#20242c`, radius 14px): header `LEAGUE DRAFT GRADES` (11px/700 `#9aa0a9`) + caption `"ranked by projected starting lineup"`. One row per team, **sorted best→worst by starterPts**, padding `11px 12px`, radius 10px, margin-bottom 4px. Your team's row: bg `rgba(61,220,145,.06)`, border `rgba(61,220,145,.35)`; others: transparent bg, border `#191c22`. Row contents (flex, gap 14px, align center):
   - rank number (JetBrains Mono 12px `#6b7079`, width 24px, right-aligned);
   - team name block (width 150px): name 14px/700 (`#3ddc91` if YOU else `#e9eaec`) + green `YOU` badge if applicable;
   - a strength bar (flex 1, height 8px, track `#0f1115`, radius 5px; fill width = `starterPts / maxStarterPts`, fill color = grade color at `opacity:.55`);
   - a note (JetBrains Mono 12px `#7e838d`, width 84px): `"Best: <POS>"` — the team's strongest position by z-score;
   - the **grade badge** (Hanken Grotesk 20px/800, grade color on grade-bg tint, width 58px, padding `5px 0`, radius 9px, centered).

---

## Core algorithm — grades & strengths/weaknesses

All grading is **relative to the league** (a curve), so there's always a top and bottom team. Pure functions, no side effects. Compute once when rendering the report.

```
// per-team strength metric = projected points of their STARTING lineup
for each team t:
    teamStarterPts[t] = buildRoster(teamPlayersFor(t)).starterPts

mean, sd = mean & population std-dev of teamStarterPts across all teams
for each team t:
    z[t]     = sd ? (teamStarterPts[t] - mean) / sd : 0
    grade[t] = gradeFromZ(z[t])

gradeFromZ(z):                       // z-score → letter on a curve
    z >= 1.25 -> 'A+'   z >= 0.8  -> 'A'    z >= 0.45 -> 'A-'
    z >= 0.18 -> 'B+'   z >= -0.06-> 'B'    z >= -0.32-> 'B-'
    z >= -0.6 -> 'C+'   z >= -0.95-> 'C'    z >= -1.3 -> 'C-'
    else      -> 'D'

rank = teams sorted by starterPts desc, 1-indexed
maxStarterPts = max over teams (for the bar widths)
```

**Strengths / weaknesses (user's team only):**

```
baseStarters = { QB: numQB, RB: 2, WR: 2, TE: 1, K: 1, DST: 1 }

posStrengthFor(players, pos):        // sum of best-N projections at a position
    k = baseStarters[pos]
    return sum of top-k players (by proj) of that pos

for pos in [QB, RB, WR, TE]:
    vals  = posStrengthFor(eachTeam, pos)
    z_pos = (myValue - mean(vals)) / std(vals)
    rank_pos = 1 + count(vals > myValue)

strengths  = positions with z_pos >= 0.45, sorted by z desc
weaknesses = positions with z_pos <= -0.45, sorted by z asc
// guarantee at least one of each: if empty, take the single best / worst position by z.
// then drop any position that landed in BOTH lists from weaknesses.

tier word: z>=1.0 'Elite' | z>=0.45 'Strong' | z<=-1.0 'Barren' | z<=-0.45 'Thin' | else 'Average'
detail:    "<ordinal(rank_pos)> of <TEAMS> in the league at <POS>"
summary:   "Strongest at <strength POSes joined by ' & '>. Thin at <weakness POSes joined by ' & '>."
```

**Per-team "Best: POS" note** (league grades list): for each team, the position (`QB|RB|WR|TE`) with the highest z-score of `posStrengthFor` vs the league mean/sd for that position.

```
gradeColor(g): A* -> #3ddc91 | B* -> #5aa9f0 | C* -> #f5b14c | D -> #f0726a
gradeBg(g):    A* -> rgba(61,220,145,.12) | B* -> rgba(90,169,240,.12)
               C* -> rgba(245,177,76,.12) | D -> rgba(240,114,106,.12)
ordinal(n):    1->1st, 2->2nd, 3->3rd, 4->4th … (standard English ordinals)
```

---

## Interactions & Behavior summary
- **League board**: opens via header button or by clicking a ticker pick; closes via ✕ or backdrop click; selecting a team in the left list swaps the detail pane. Live data.
- **Report card**: opens via the button on the completion screen; closes via “← Back to cockpit”. Read-only. Hidden automatically if the draft is reset (no longer complete).
- The blinking on-the-clock dot uses `@keyframes blink { 0%,100% { opacity:1 } 50% { opacity:.35 } }` at `1.1s infinite`.

## State Management
| State | Type | Default | Purpose |
|---|---|---|---|
| `viewTeam` | `number \| null` | `null` | Which team the League Board is showing; `null` = closed |
| `showReport` | `boolean` | `false` | Whether the Report Card page is open (only effective once the draft is complete) |

No data fetching — everything derives from the existing `draftedBy` map and `this.players`.

## Design Tokens
**Surfaces:** page `#0d0e11` / report page `#0b0c0f` · panel `#14161b` · inset `#0f1115` · raised `#1a1d23` / `#191c22` · header `#101216`
**Borders:** `#20242c` (primary) · `#262a33` · `#2a2e37` · `#191c22` (subtle) · `#3a3f49` (selected/hover)
**Text:** primary `#e9eaec` · secondary `#9aa0a9` · muted `#7e838d` · faint `#6b7079` / `#5a5f68` · bright `#cfd2d7`
**Accents:** green `#3ddc91` (positive/YOU) · blue `#5aa9f0` (WR / info) · amber `#f5b14c` (on-clock / caution) · red/coral `#f0726a` (QB / weakness)
**Position colors (`posColor`):** QB `#f0726a` · RB `#4fd1ab` · WR `#5aa9f0` · TE `#c98bf0` · K/DST `#8b8f98`
**Position bg (`posBg`):** QB `rgba(240,114,106,.14)` · RB `rgba(79,209,171,.14)` · WR `rgba(90,169,240,.14)` · TE `rgba(201,139,240,.14)`
**Radius:** chips 4–7px · cards/rows 9–10px · panels 12–16px
**Typography:** UI = **Hanken Grotesk** (400–800); numbers/labels/mono = **JetBrains Mono** (400–700). Both from Google Fonts.
**Shadow (modal):** `0 30px 80px rgba(0,0,0,.6)`

## Assets
None. No images or icons — the `D` logo is a CSS gradient tile with a text glyph, position bars/dots are plain divs. Use your app's existing iconography if you prefer.

## Files
- `Draft Cockpit.dc.html` — the full working prototype. The two features live in:
  - **Template** (markup): the `<!-- ===== LEAGUE / OPPONENTS MODAL ===== -->` block and the `<!-- ===== DRAFT REPORT CARD ===== -->` block, plus the header “League board” button and the “View Draft Report Card →” button on the complete screen.
  - **Logic** (in the `<script ... data-dc-script>` class): the `openTeam` / `closeLeague` / `nextPickForTeam` methods, and the `// ===== LEAGUE BOARD` and `// ===== DRAFT REPORT CARD` sections inside `renderVals()`.
