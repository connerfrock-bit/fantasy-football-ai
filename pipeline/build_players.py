#!/usr/bin/env python3
"""
Fantasy Football - draft data ingestion (strictly FREE sources, no API keys).

Player identity comes from the Sleeper master (a cross-platform ID crosswalk) and the
Sleeper projection feed anchors the draftable universe. Every other input - ADP, extra
projections, bye weeks - is a pluggable FEED in a registry (see SOURCE REGISTRY below).
To add a feed closer to the season (FFCalc, FantasyPros, Yahoo, ...), write one small
Feed subclass and append it to a registry list; the blending core never changes. Each
feed declares which scoring formats it serves, so per-format rules (e.g. ESPN = PPR-only)
are declarative data, not special-casing.

Projections and ADP are blended (weighted mean) across all enabled feeds, per format;
per-source values AND the consensus are kept so the cockpit's market-edge stays real.
Joins: Sleeper feeds key on player_id (exact); name-keyed feeds (ESPN/FFCalc) match on
normalized name + position.

Outputs (pipeline/data/):
  - ff_players.json   canonical, for any consumer
  - ff_players.js     `window.FF_DRAFT_DATA = {...}`  (loads offline via file://)

stdlib only. Run:  python pipeline/build_players.py
"""

import json, os, re, sys, time, urllib.request
from collections import Counter
from datetime import datetime, timezone

# ----------------------------- config -----------------------------
SEASON = 2026
TEAMS  = 12                       # FFCalc draft size for ADP context
FANTASY_POS = {"QB", "RB", "WR", "TE", "K", "DEF"}
KEEP = {"skill": 320, "K": 32, "DEF": 32}   # draftable universe caps
ADP_NA = 999.0                    # Sleeper/FFCalc sentinel for "undrafted"

# Scoring formats to compute (these drive BOTH projections and ADP). Superflex/2QB is a
# separate roster axis (changes ADP only, via Sleeper's adp_2qb) and is wired when the
# cockpit's QB=2 path is built - not added to this tuple.
FORMATS = ("ppr", "half", "std")

HERE = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(HERE, "data", "raw")
OUT_JSON = os.path.join(HERE, "data", "ff_players.json")
OUT_JS   = os.path.join(HERE, "data", "ff_players.js")
UA = {"User-Agent": "Mozilla/5.0 (FF draft data pull)"}

def log(*a): print(*a, file=sys.stderr)

# ----------------------------- fetch ------------------------------
def fetch_json(url, headers=None, timeout=90):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def cached_json(fname, url, max_age_h=24, headers=None):
    """On-disk cache; the master is ~5 MB so we don't refetch every run."""
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, fname)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_h * 3600:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    data = fetch_json(url, headers)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data

# --------------------------- normalize ----------------------------
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.I)
def norm_name(s):
    s = (s or "").lower().replace("’", "'").replace("'", "").replace(".", "")
    s = _SUFFIX.sub("", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

_POS_FIX = {"PK": "K", "DST": "DEF", "D/ST": "DEF"}
def fix_pos(p): return _POS_FIX.get((p or "").upper(), (p or "").upper())

ESPN_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons"
ESPN_POS  = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DEF"}
# ESPN projection component-stat IDs -> our stat names (verified against Sleeper values).
ESPN_STAT_IDS = {"3": "pass_yd", "4": "pass_td", "20": "pass_int", "23": "rush_att", "24": "rush_yd",
                 "25": "rush_td", "53": "rec", "42": "rec_yd", "43": "rec_td", "58": "tgt", "210": "gp"}
_TEAM_ALIAS = {"WSH": "WAS", "JAC": "JAX", "LA": "LAR", "OAK": "LV", "SD": "LAC", "STL": "LAR"}
def alias(t): return _TEAM_ALIAS.get((t or "").upper(), (t or "").upper())

def adp_or_none(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v >= ADP_NA else round(v, 1)

def wmean(pairs):
    """Weighted mean of (value, weight) pairs (values already non-None). 1 decimal."""
    if not pairs:
        return None
    tot = sum(w for _, w in pairs)
    return round(sum(v * w for v, w in pairs) / tot, 1) if tot else None

def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else None

# ---------------------------- sources -----------------------------
def load_master():
    log("- Sleeper player master ...")
    m = cached_json("sleeper_players.json", "https://api.sleeper.app/v1/players/nfl")
    log(f"  {len(m)} players")
    return m

def load_projections():
    log("- Sleeper projections ...")
    url = f"https://api.sleeper.app/projections/nfl/{SEASON}?season_type=regular"
    p = fetch_json(url)
    log(f"  {len(p)} projection rows")
    return p

def load_ffcalc(fmt):
    try:
        d = fetch_json(f"https://fantasyfootballcalculator.com/api/v1/adp/{fmt}?teams={TEAMS}&year={SEASON}")
        meta = d.get("meta", {})
        rows = d.get("players", [])
        log(f"  FFCalc {fmt:9}: {len(rows):3} players | {meta.get('total_drafts')} drafts | "
            f"{meta.get('start_date')}..{meta.get('end_date')}")
        return rows
    except Exception as e:                       # noqa: BLE001  (one flaky source must not break the run)
        log(f"  FFCalc {fmt}: FAILED ({e}) - continuing without it")
        return []

_ESPN_KONA = None
def _espn_kona():
    """Fetch ESPN kona_player_info once per run (carries BOTH ADP and projections)."""
    global _ESPN_KONA
    if _ESPN_KONA is None:
        flt = {"players": {"limit": 350, "sortDraftRanks": {"sortPriority": 1, "sortAsc": True, "value": "PPR"}}}
        url = f"{ESPN_BASE}/{SEASON}/segments/0/leaguedefaults/3?view=kona_player_info"
        try:
            _ESPN_KONA = fetch_json(url, headers={"x-fantasy-filter": json.dumps(flt)})
        except Exception as e:                   # noqa: BLE001
            log(f"  ESPN: fetch FAILED ({e}) - continuing without it")
            _ESPN_KONA = {"players": []}
    return _ESPN_KONA

def load_espn_adp():
    """ESPN averageDraftPosition (PPR), keyed by (normalized name, pos)."""
    log("- ESPN ADP ...")
    out = {}
    for it in _espn_kona().get("players", []):
        pl = it.get("player") or {}
        pos = ESPN_POS.get(pl.get("defaultPositionId"))
        adp = (pl.get("ownership") or {}).get("averageDraftPosition")
        nm = pl.get("fullName")
        if pos and nm and isinstance(adp, (int, float)) and adp > 0:
            out[(norm_name(nm), pos)] = round(adp, 1)
    log(f"  ESPN ADP: {len(out)} players")
    return out

def load_espn_proj():
    """ESPN season projected points (PPR, leaguedefaults/3), keyed by (normalized name, pos)."""
    log("- ESPN projections ...")
    out = {}
    for it in _espn_kona().get("players", []):
        pl = it.get("player") or {}
        pos = ESPN_POS.get(pl.get("defaultPositionId"))
        nm = pl.get("fullName")
        if not (pos and nm):
            continue
        for s in pl.get("stats", []):            # season projection = src 1 (proj), split 0, period 0
            if (s.get("seasonId") == SEASON and s.get("statSourceId") == 1
                    and s.get("statSplitTypeId") == 0 and s.get("scoringPeriodId") == 0):
                tot = s.get("appliedTotal")
                if isinstance(tot, (int, float)) and tot > 0:
                    out[(norm_name(nm), pos)] = round(tot, 1)
                break
    log(f"  ESPN projections: {len(out)} players")
    return out

def load_espn_stats():
    """ESPN projected component stats, keyed by (normalized name, pos). Maps ESPN stat IDs -> names."""
    log("- ESPN stats ...")
    out = {}
    for it in _espn_kona().get("players", []):
        pl = it.get("player") or {}
        pos = ESPN_POS.get(pl.get("defaultPositionId"))
        nm = pl.get("fullName")
        if not (pos and nm):
            continue
        for s in pl.get("stats", []):
            if (s.get("seasonId") == SEASON and s.get("statSourceId") == 1
                    and s.get("statSplitTypeId") == 0 and s.get("scoringPeriodId") == 0):
                raw = s.get("stats") or {}
                vals = {name: raw[sid] for sid, name in ESPN_STAT_IDS.items() if raw.get(sid) is not None}
                if vals:
                    out[(norm_name(nm), pos)] = vals
                break
    log(f"  ESPN stats: {len(out)} players")
    return out

def load_espn_byes():
    """ESPN team bye weeks (fresh 2026), keyed by canonical team abbrev."""
    try:
        d = fetch_json(f"{ESPN_BASE}/{SEASON}?view=proTeamSchedules_wl")
    except Exception as e:                       # noqa: BLE001
        log(f"  ESPN byes: FAILED ({e})")
        return {}
    teams = (d.get("settings") or {}).get("proTeams") or d.get("proTeams") or []
    out = {alias(t.get("abbrev")): t.get("byeWeek")
           for t in teams if t.get("abbrev") not in (None, "FA") and t.get("byeWeek")}
    log(f"  ESPN byes: {len(out)} teams")
    return out

# ---- Yahoo (OAuth; one operator token) -> draft_analysis ADP ----
YAHOO_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

def _yahoo_game_key(token):
    d = fetch_json(f"{YAHOO_BASE}/game/nfl?format=json", headers={"Authorization": "Bearer " + token})
    return d["fantasy_content"]["game"][0]["game_key"]

def load_yahoo_adp(token, pages=12):
    """Yahoo average_pick (fresh), keyed by (norm_name, pos). Pages draft_analysis 25 at a time."""
    log("- Yahoo ADP ...")
    hdr = {"Authorization": "Bearer " + token}
    gk = _yahoo_game_key(token)
    def flat(lst):
        o = {}
        for it in lst:
            if isinstance(it, dict):
                o.update(it)
        return o
    out = {}
    for pg in range(pages):
        url = f"{YAHOO_BASE}/game/{gk}/players;start={pg*25};count=25;sort=OR/draft_analysis?format=json"
        try:
            players = fetch_json(url, headers=hdr)["fantasy_content"]["game"][1]["players"]
        except Exception as e:                   # noqa: BLE001
            log(f"  Yahoo ADP: page {pg} failed ({e}) - stopping"); break
        n = 0
        for k, v in players.items():
            if k == "count":
                continue
            n += 1
            meta = flat(v["player"][0])
            da   = flat(v["player"][1].get("draft_analysis", []))
            nm = meta.get("name"); nm = nm.get("full") if isinstance(nm, dict) else nm
            pos = fix_pos((meta.get("display_position") or "").split(",")[0])
            ap = adp_or_none(da.get("average_pick"))
            if nm and pos and ap and ap > 0:
                out[(norm_name(nm), pos)] = ap
        if n < 25:
            break
    log(f"  Yahoo ADP: {len(out)} players")
    return out

# =============================== SOURCE REGISTRY ===============================
# Every external feed is a small self-contained class. To ADD a source closer to the
# season, write one subclass + append it to the matching *_feeds() list below; the
# blending core in build() never changes. `enabled=False` keeps a feed wired but
# inactive (e.g. FFCalc until its 2026 data lands). `formats` declares which scoring
# formats the feed can serve, so per-format rules (ESPN = PPR-only) are declarative.
# `weight` lets you trust one source more than another in the blend.

class Feed:
    key, formats = "?", ()
    def __init__(self, enabled=True, weight=1.0):
        self.enabled, self.weight = enabled, weight
    def load(self):
        """Fetch raw data + build an internal lookup. Called once, only if enabled."""

class AdpFeed(Feed):
    def adp(self, player, fmt):   # -> ADP for player in scoring `fmt`, or None
        return None

class ProjFeed(Feed):
    def proj(self, player, fmt):  # -> projected season points for player in `fmt`, or None
        return None

class ByeFeed(Feed):
    def bye(self, player):        # -> bye week for player, or None
        return None

class StatFeed(Feed):
    def stats(self, player):      # -> {stat_name: projected value} for player, or {}
        return {}

# ---- Sleeper: projection feed keyed by player_id (== our canonical id) ----
class SleeperAdp(AdpFeed):
    key, formats = "sleeper", ("ppr", "half", "std", "2qb")   # 2qb latent (for future superflex)
    _F = {"ppr": "adp_ppr", "half": "adp_half_ppr", "std": "adp_std", "2qb": "adp_2qb"}
    def __init__(self, proj_by_id, **kw):
        super().__init__(**kw); self._p = proj_by_id
    def adp(self, player, fmt):
        st = self._p.get(player["id"])
        return adp_or_none(st.get(self._F[fmt])) if st and fmt in self._F else None

class SleeperProj(ProjFeed):
    key, formats = "sleeper", ("ppr", "half", "std")
    _F = {"ppr": "pts_ppr", "half": "pts_half_ppr", "std": "pts_std"}
    def __init__(self, proj_by_id, **kw):
        super().__init__(**kw); self._p = proj_by_id
    def proj(self, player, fmt):
        st = self._p.get(player["id"])
        if not st:
            return None
        key = "pts_std" if player["pos"] in ("K", "DEF") else self._F[fmt]   # K/DEF: no PPR delta
        return r1(st.get(key))

class SleeperStats(StatFeed):
    key = "sleeper"
    _KEYS = ("gp", "rec", "rec_yd", "rec_td", "rush_att", "rush_yd", "rush_td", "pass_yd", "pass_td", "pass_int")
    def __init__(self, proj_by_id, **kw):
        super().__init__(**kw); self._p = proj_by_id
    def stats(self, player):
        st = self._p.get(player["id"]) or {}
        return {k: st[k] for k in self._KEYS if st.get(k) is not None}

# ---- ESPN: one (PPR) ADP joined by name; team byes ----
class EspnAdp(AdpFeed):
    key, formats = "espn", ("ppr", "half")     # one ADP (PPR default); PPR/Half ADP ~identical -> feeds both
    def load(self):
        self._idx = load_espn_adp()
    def adp(self, player, fmt):
        return self._idx.get((norm_name(player["name"]), player["pos"]))

class EspnByes(ByeFeed):
    key = "espn"
    def load(self):
        self._idx = load_espn_byes()
    def bye(self, player):
        return self._idx.get(alias(player["team"]))

class EspnProj(ProjFeed):
    key, formats = "espn", ("ppr",)    # ESPN appliedTotal (leaguedefaults/3) is PPR
    def load(self):
        self._idx = load_espn_proj()
    def proj(self, player, fmt):
        return self._idx.get((norm_name(player["name"]), player["pos"]))

class EspnStats(StatFeed):
    key = "espn"
    def load(self):
        self._idx = load_espn_stats()
    def stats(self, player):
        return self._idx.get((norm_name(player["name"]), player["pos"]), {})

# ---- Fantasy Football Calculator: per-format ADP, name-joined (gated until ~Aug) ----
class FfcalcAdp(AdpFeed):
    key, formats = "ffcalc", ("ppr", "half", "std")
    _EP = {"ppr": "ppr", "half": "half-ppr", "std": "standard"}
    def load(self):
        self._idx = {}
        for fmt, ep in self._EP.items():
            for r in load_ffcalc(ep):
                k = (norm_name(r.get("name")), fix_pos(r.get("position")))
                self._idx.setdefault(k, {})[fmt] = adp_or_none(r.get("adp"))
    def adp(self, player, fmt):
        return self._idx.get((norm_name(player["name"]), player["pos"]), {}).get(fmt)

# ---- Yahoo: one (half-PPR) ADP via OAuth, name-joined ----
class YahooAdp(AdpFeed):
    key, formats = "yahoo", ("ppr", "half")   # one ADP (0.5 PPR default); PPR/Half ADP ~identical -> feeds both
    def load(self):
        try:
            from yahoo_auth import access_token
            self._idx = load_yahoo_adp(access_token())
        except Exception as e:                   # noqa: BLE001  (no creds / token issue -> just skip)
            log(f"  Yahoo ADP: unavailable ({e}) - skipping")
            self._idx = {}
    def adp(self, player, fmt):
        return self._idx.get((norm_name(player["name"]), player["pos"]))

# ---- registries: append a new feed here, nothing else to touch ----
def adp_feeds(proj_by_id):
    return [
        SleeperAdp(proj_by_id, enabled=True),
        EspnAdp(enabled=True),
        YahooAdp(enabled=True),
        FfcalcAdp(enabled=True),     # 2026 mocks live as of Jul 2026 (~1.5k drafts and growing)
        # e.g. FantasyProsAdp(enabled=False), ...
    ]
def proj_feeds(proj_by_id):
    return [
        SleeperProj(proj_by_id, enabled=True),
        EspnProj(enabled=True),
        # e.g. FantasyProsProj(enabled=False), ...
    ]
def bye_feeds():
    return [
        EspnByes(enabled=True),
    ]
def stat_feeds(proj_by_id):
    return [
        SleeperStats(proj_by_id, enabled=True),
        EspnStats(enabled=True),
    ]

def assign_tiers(players, n=8, depth=50):
    """Position-relative tiers per scoring format via natural breaks: within each position
    (sorted by projection) the n-1 LARGEST projection gaps in the top `depth` become tier
    boundaries; everyone past `depth` is the final (replacement) tier. Stored as p['tier'][fmt]."""
    for p in players:
        p["tier"] = {}
    for fmt in FORMATS:
        for pos in ("QB", "RB", "WR", "TE", "K", "DEF"):
            grp = sorted((p for p in players if p["pos"] == pos and p["proj"].get(fmt) is not None),
                         key=lambda p: -p["proj"][fmt])
            if not grp:
                continue
            head = grp[:depth]
            if len(head) <= n:                       # tiny pool: ~one player per tier
                for j, p in enumerate(head):
                    p["tier"][fmt] = j + 1
            else:
                gaps = sorted(range(len(head) - 1),  # indices of the n-1 biggest cliffs
                              key=lambda i: head[i]["proj"][fmt] - head[i + 1]["proj"][fmt], reverse=True)
                breaks = set(gaps[:n - 1])
                t = 1
                for j, p in enumerate(head):
                    if j > 0 and (j - 1) in breaks:
                        t += 1
                    p["tier"][fmt] = t
            last = head[-1]["tier"][fmt]
            for p in grp[depth:]:
                p["tier"][fmt] = last + 1

# ----------------------------- build ------------------------------
def build():
    master = load_master()
    proj_by_id = {str(r.get("player_id")): (r.get("stats") or {}) for r in load_projections()}

    adp_all, proj_all, bye_all = adp_feeds(proj_by_id), proj_feeds(proj_by_id), bye_feeds()
    stat_all = stat_feeds(proj_by_id)
    adp_on  = [f for f in adp_all  if f.enabled]
    proj_on = [f for f in proj_all if f.enabled]
    bye_on  = [f for f in bye_all  if f.enabled]
    stat_on = [f for f in stat_all if f.enabled]
    for f in adp_on + proj_on + bye_on + stat_on:
        f.load()
    adp_keys = [f.key for f in adp_all]      # stable per-source columns (present even when a feed is off)

    def blend_adp(player, fmt):
        per, pairs = {k: None for k in adp_keys}, []
        for f in adp_on:
            if fmt not in f.formats:
                continue
            v = f.adp(player, fmt)
            per[f.key] = v
            if v is not None:
                pairs.append((v, f.weight))
        per["consensus"], per["sources"] = wmean(pairs), len(pairs)
        return per

    def blend_proj(player, fmt):
        pairs = [(f.proj(player, fmt), f.weight) for f in proj_on if fmt in f.formats]
        return wmean([(v, w) for v, w in pairs if v is not None])

    def blend_stats(player):
        acc = {}
        for f in stat_on:
            for k, v in f.stats(player).items():
                if v is not None:
                    acc.setdefault(k, []).append(v)
        return {k: (round(sum(vs) / len(vs), 1) if k.endswith("_td") else round(sum(vs) / len(vs)))
                for k, vs in acc.items()}

    players = []
    for pid, stats in proj_by_id.items():
        mp = master.get(pid)
        if not mp:
            continue
        pos = fix_pos(mp.get("position"))
        if pos not in FANTASY_POS:
            continue
        name = mp.get("full_name") or f"{mp.get('first_name','')} {mp.get('last_name','')}".strip()
        team = mp.get("team") or (pid if pos == "DEF" else None)
        player = {"id": pid, "name": name, "pos": pos, "team": team,
                  "ids": {"sleeper": pid, "espn": mp.get("espn_id"), "yahoo": mp.get("yahoo_id")}}

        proj = {fmt: blend_proj(player, fmt) for fmt in FORMATS}
        if not proj.get("ppr") and not proj.get("std"):      # no usable projection -> skip
            continue
        player["bye"]   = next((b for b in (f.bye(player) for f in bye_on) if b is not None), None)
        player["inj"]   = mp.get("injury_status") or None   # Sleeper: Out/IR/PUP/Sus/Questionable/... (None if healthy)
        player["proj"]  = proj
        player["adp"]   = {fmt: blend_adp(player, fmt) for fmt in FORMATS}
        player["stats"] = blend_stats(player)
        players.append(player)

    assign_tiers(players)
    players.sort(key=lambda p: (p["proj"]["ppr"] or 0), reverse=True)
    skill = [p for p in players if p["pos"] in ("QB", "RB", "WR", "TE")][:KEEP["skill"]]
    ks    = [p for p in players if p["pos"] == "K"][:KEEP["K"]]
    ds    = [p for p in players if p["pos"] == "DEF"][:KEEP["DEF"]]
    keep  = skill + ks + ds

    meta = {
        "season": SEASON, "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "formats": list(FORMATS), "teams": TEAMS, "count": len(keep),
        "adp_sources": [f.key for f in adp_on], "proj_sources": [f.key for f in proj_on],
        "bye_sources": [f.key for f in bye_on], "stat_sources": [f.key for f in stat_on],
    }
    out = {"meta": meta, "players": keep}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("// AUTO-GENERATED by pipeline/build_players.py - do not edit by hand.\n")
        f.write("window.FF_DRAFT_DATA = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")

    _summary(keep, meta, adp_keys)
    return out

def _summary(keep, meta, adp_keys):
    board = sorted(keep, key=lambda p: (p["adp"]["ppr"]["consensus"] is None,
                                        p["adp"]["ppr"]["consensus"] or 9e9))
    log("\n== OUTPUT ==")
    log(f"  {OUT_JSON}")
    log(f"  {OUT_JS}")
    log(f"  ADP feeds: {meta['adp_sources']}  | proj: {meta['proj_sources']}  | formats: {meta['formats']}")
    log(f"  by pos: {dict(Counter(p['pos'] for p in keep))}")
    log("  consensus ADP coverage: " + "  ".join(
        f"{fmt} {sum(1 for p in keep if p['adp'][fmt]['consensus'] is not None)}/{len(keep)}" for fmt in meta["formats"]))
    src_cov = lambda k: max(sum(1 for p in keep if p["adp"][fmt].get(k) is not None) for fmt in meta["formats"])
    log("  per-source (native fmt): " + "  ".join(f"{k} {src_cov(k)}" for k in adp_keys))
    log("\n  Draft board - top 18 by consensus ADP (PPR):")
    log(f'  {"#":>3} {"POS":4}{"NAME":23}{"TM":4}{"PROJ":>6}{"ADP":>6}   sleep   espn   bye')
    for i, p in enumerate(board[:18], 1):
        a = p["adp"]["ppr"]
        log(f'  {i:>3} {p["pos"]:4}{p["name"][:22]:23}{(p["team"] or "?"):4}{p["proj"]["ppr"]:>6}'
            f'{str(a["consensus"]):>6}  {str(a.get("sleeper")):>6} {str(a.get("espn")):>6}   {p["bye"]}')

    # market edge (PPR): one fresh source ranks him later than another -> may slide to you
    def gap(p):
        a = p["adp"]["ppr"]
        return (a.get("espn") - a.get("sleeper")) if (a.get("espn") is not None and a.get("sleeper") is not None) else None
    ranked = lambda p: (p["adp"]["ppr"].get("sleeper") or 999) < 150 and (p["adp"]["ppr"].get("espn") or 999) < 150
    edged  = [p for p in keep if gap(p) is not None and abs(gap(p)) >= 10 and ranked(p)]
    if edged:
        line = lambda p: (f'     {p["pos"]:3} {p["name"][:22]:23} sleeper {str(p["adp"]["ppr"]["sleeper"]):>6}'
                          f'  espn {str(p["adp"]["ppr"]["espn"]):>6}   ({"+" if gap(p) >= 0 else ""}{round(gap(p),1)})')
        log("\n  MARKET EDGE - slides on ESPN (target these; your league lets them fall):")
        for p in sorted(edged, key=gap, reverse=True)[:6]:
            log(line(p))
        log("  goes EARLY on ESPN (don't reach - cheaper elsewhere):")
        for p in sorted(edged, key=gap)[:6]:
            log(line(p))

if __name__ == "__main__":
    build()
