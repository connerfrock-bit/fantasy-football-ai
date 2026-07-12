#!/usr/bin/env python3
"""Preview the compiled draft dataset + export a flat CSV for full inspection.
Run: python pipeline/preview.py"""
import json, os, csv
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "data", "ff_players.json")
CSVF = os.path.join(HERE, "data", "ff_players.csv")

d = json.load(open(SRC, encoding="utf-8"))
meta, players = d["meta"], d["players"]

def cons(p, f): return p["adp"][f]["consensus"]
def board_key(p):
    c = cons(p, "ppr"); return (c is None, c if c is not None else 9e9)
def fmt(v, w=6): return f"{v:>{w}}" if v is not None else f"{'-':>{w}}"

adp_src  = meta.get("adp_sources", meta.get("sources", []))
proj_src = meta.get("proj_sources", ["sleeper"])
print("=" * 80)
print(f"COMPILED DRAFT DATA  -  season {meta['season']}")
print(f"ADP feeds: {', '.join(adp_src)}  |  projection feeds: {', '.join(proj_src)}")
print(f"generated {meta['generated']}  |  {meta['count']} players")
print("=" * 80)
print("by position:", dict(Counter(p["pos"] for p in players)))
for f in ("ppr", "half", "std"):
    cov = sum(1 for p in players if cons(p, f) is not None)
    print(f"  {f:4} ADP coverage: {cov}/{len(players)}")

ex = next((p for p in players if p["name"] == "Ja'Marr Chase"), players[0])
print(f"\nSCHEMA - one full record ({ex['name']}):")
print(json.dumps(ex, indent=2, ensure_ascii=False))

idx = {p["name"]: p for p in players}
sample = ["Bijan Robinson", "Christian McCaffrey", "De'Von Achane", "Derrick Henry",
          "Saquon Barkley", "Ja'Marr Chase", "Justin Jefferson", "Travis Kelce",
          "Josh Allen", "Lamar Jackson"]
print("\nCROSS-FORMAT SAMPLE  (projection / consensus ADP, each per scoring format):")
print(f'  {"POS":4}{"NAME":22}{"TM":4}{"BYE":>4}      PROJ ppr/half/std        ADP ppr/half/std')
for n in sample:
    p = idx.get(n)
    if not p: continue
    pr, a = p["proj"], p["adp"]
    proj = f'{fmt(pr["ppr"])}/{fmt(pr["half"])}/{fmt(pr["std"])}'
    adp  = f'{fmt(cons(p,"ppr"),6)}/{fmt(cons(p,"half"),5)}/{fmt(cons(p,"std"),5)}'
    print(f'  {p["pos"]:4}{n[:21]:22}{p["team"]:4}{fmt(p["bye"],4)}   {proj}    {adp}')

# show the PPR ADP source split for a few, to make the averaging explicit
print("\nADP = average of fresh sources  (PPR shown):")
for n in ["De'Von Achane", "Justin Herbert", "Mark Andrews"]:
    p = idx.get(n); a = p["adp"]["ppr"]
    print(f'  {p["name"][:22]:23} sleeper {fmt(a["sleeper"],6)}  espn {fmt(a["espn"],6)}  ->  consensus {fmt(a["consensus"],6)}  (n={a["sources"]})')

# PPR vs STD ranking flips prove projections are genuinely per-format
sk = [p for p in players if p["pos"] in ("RB", "WR", "TE")]
ppr_r = {p["name"]: i + 1 for i, p in enumerate(sorted(sk, key=lambda p: -(p["proj"]["ppr"] or 0)))}
std_r = {p["name"]: i + 1 for i, p in enumerate(sorted(sk, key=lambda p: -(p["proj"]["std"] or 0)))}
movers = sorted(sk, key=lambda p: ppr_r[p["name"]] - std_r[p["name"]])
print("\nFORMAT MATTERS  (rank by PPR proj vs Standard proj - same player pool):")
print("  rise most in PPR (pass-catchers):")
for p in movers[:4]:
    print(f'     {p["pos"]:3} {p["name"][:22]:23} PPR #{ppr_r[p["name"]]:>3}  vs  STD #{std_r[p["name"]]:>3}')
print("  rise most in Standard (TD/early-down):")
for p in movers[-4:][::-1]:
    print(f'     {p["pos"]:3} {p["name"][:22]:23} PPR #{ppr_r[p["name"]]:>3}  vs  STD #{std_r[p["name"]]:>3}')

cols = ["board_rank", "name", "pos", "team", "bye", "inj",
        "proj_ppr", "proj_half", "proj_std",
        "adp_ppr", "adp_half", "adp_std", "adp_ppr_sleeper", "adp_ppr_espn", "adp_sources",
        "gp", "rec", "rec_yd", "rec_td", "rush_att", "rush_yd", "rush_td",
        "pass_yd", "pass_td", "pass_int", "sleeper_id", "espn_id"]
rows = sorted(players, key=board_key)
with open(CSVF, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(cols)
    for i, p in enumerate(rows, 1):
        s = p.get("stats", {})
        w.writerow([i, p["name"], p["pos"], p["team"], p["bye"], p.get("inj"),
                    p["proj"]["ppr"], p["proj"]["half"], p["proj"]["std"],
                    cons(p, "ppr"), cons(p, "half"), cons(p, "std"),
                    p["adp"]["ppr"]["sleeper"], p["adp"]["ppr"]["espn"], p["adp"]["ppr"]["sources"],
                    s.get("gp"), s.get("rec"), s.get("rec_yd"), s.get("rec_td"),
                    s.get("rush_att"), s.get("rush_yd"), s.get("rush_td"),
                    s.get("pass_yd"), s.get("pass_td"), s.get("pass_int"),
                    p["ids"]["sleeper"], p["ids"]["espn"]])
print(f"\nFull dataset exported -> {CSVF}  ({len(rows)} rows - open in Excel)")
