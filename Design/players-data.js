// Shared player database for the Fantasy Football AI Tool.
// In the real product this is replaced by a live feed (nflverse advanced stats +
// licensed projections). Here it's a cleaned, static 2026 sample so the
// Lineup Optimizer and Player Database render against one source of truth.
//
// =============================== DATA CONTRACT ===============================
// Each entry in window.FF_PLAYERS is the shape the real backend must return.
// Replace this file's hard-coded `raw` array with a fetch from your API; keep
// the SAME field names and the UI + engines work unchanged.
//
//   name          string   Player full name (unique key used across all pages)
//   pos           enum     'QB' | 'RB' | 'WR' | 'TE'   (DST/K live in the cockpit only)
//   team          string   NFL team abbrev
//   bye           int      Bye week number
//   seasonProj    number   Season-long projected PPR points  <- LICENSED PROJECTION
//   consistency   0..1     Week-to-week reliability; drives floor/ceiling spread.
//                          Derive from coefficient of variation of weekly scores.
//   opp           string   THIS WEEK's opponent (e.g. '@BAL')        <- schedule feed
//   oppRank       1..32    Opp defense rank vs this position, 1=stingiest..32=most
//                          generous. SOURCE: points-allowed-to-position (DvP).
//   adv           object   Position-specific advanced stats  <- nflverse / PFF:
//                            WR/TE: tgt(target share %), route(route %), adot,
//                                   snap(snap %), rz(RZ tgt/gm), yac
//                            RB:    rush(rush share %), snap, tgt(tgt share %),
//                                   rz(RZ touch/gm), ypt(yds/touch)
//                            QB:    snap, pyd(pass yds/gm), ryd(rush yds/gm), tdg(TD/gm)
//
// DERIVED below (compute server-side in production, not in the client):
//   weekProj, floor, ceiling   weekly range = seasonProj/17 * matchupMult, widened
//                              by (1-consistency). Replace with REAL weekly
//                              projections when available; keep floor/ceiling.
//   matchup, tag               human labels derived from oppRank / consistency.
//   ovrRank, posRank           rankings by seasonProj.
//
// NOTE: the Draft Cockpit uses its OWN inline pool (VORP/ADP/tiers + DST/K) and
// does NOT read this file — unify them onto this contract during the real build.
// ============================================================================
(function () {
  // raw: [name, pos, team, bye, seasonProj(PPR), consistency 0-1, opp, oppRankVsPos(1=stingiest..32=most generous), adv{}]
  // adv keys — WR/TE: tgt(target share %), route(route %), adot, snap, rz(RZ tgt/gm), yac
  //            RB: rush(rush share %), snap, tgt(target share %), rz(RZ touch/gm), ypt(yds/touch)
  //            QB: snap, pyd(pass yds/gm), ryd(rush yds/gm), tdg(total TD/gm)
  var raw = [
    ['Ja\u2019Marr Chase','WR','CIN',10,350,0.82,'@BAL',24,{tgt:31,route:92,adot:11.8,snap:94,rz:2.1,yac:5.2}],
    ['Justin Jefferson','WR','MIN',6,330,0.80,'vs GB',19,{tgt:30,route:90,adot:12.5,snap:93,rz:1.8,yac:4.6}],
    ['CeeDee Lamb','WR','DAL',10,322,0.78,'@PHI',9,{tgt:29,route:91,adot:9.4,snap:95,rz:1.7,yac:5.8}],
    ['Puka Nacua','WR','LAR',8,315,0.77,'vs SEA',22,{tgt:30,route:88,adot:8.1,snap:90,rz:1.4,yac:6.1}],
    ['Amon-Ra St. Brown','WR','DET',8,305,0.83,'@CHI',16,{tgt:28,route:93,adot:7.6,snap:92,rz:1.9,yac:5.5}],
    ['Malik Nabers','WR','NYG',11,312,0.74,'vs DAL',27,{tgt:32,route:89,adot:10.2,snap:91,rz:1.6,yac:4.9}],
    ['Nico Collins','WR','HOU',6,298,0.73,'@IND',20,{tgt:27,route:87,adot:12.9,snap:89,rz:1.5,yac:4.3}],
    ['Brian Thomas Jr.','WR','JAX',8,295,0.70,'vs TEN',29,{tgt:26,route:86,adot:13.4,snap:90,rz:1.4,yac:5.0}],
    ['A.J. Brown','WR','PHI',9,288,0.72,'vs DAL',12,{tgt:26,route:85,adot:11.1,snap:88,rz:1.7,yac:4.7}],
    ['Drake London','WR','ATL',5,290,0.74,'@NO',23,{tgt:29,route:90,adot:9.8,snap:92,rz:1.6,yac:4.2}],
    ['Ladd McConkey','WR','LAC',12,278,0.71,'vs KC',7,{tgt:25,route:84,adot:8.9,snap:87,rz:1.2,yac:5.6}],
    ['Tyreek Hill','WR','MIA',12,275,0.68,'@BUF',6,{tgt:27,route:86,adot:11.6,snap:89,rz:1.3,yac:5.9}],
    ['Garrett Wilson','WR','NYJ',9,272,0.70,'vs NE',26,{tgt:28,route:88,adot:10.4,snap:90,rz:1.4,yac:4.8}],
    ['Marvin Harrison Jr.','WR','ARI',8,268,0.69,'@SF',8,{tgt:26,route:85,adot:12.2,snap:88,rz:1.5,yac:4.1}],
    ['Tee Higgins','WR','CIN',10,265,0.67,'@BAL',24,{tgt:23,route:82,adot:11.9,snap:84,rz:1.6,yac:4.0}],
    ['Davante Adams','WR','LAR',8,260,0.71,'vs SEA',22,{tgt:25,route:86,adot:10.1,snap:87,rz:1.7,yac:3.9}],
    ['Jaxon Smith-Njigba','WR','SEA',8,258,0.70,'@LAR',14,{tgt:26,route:87,adot:9.2,snap:89,rz:1.2,yac:5.3}],
    ['Mike Evans','WR','TB',9,252,0.66,'vs ATL',18,{tgt:23,route:80,adot:13.1,snap:83,rz:2.0,yac:3.5}],
    ['Terry McLaurin','WR','WAS',12,250,0.67,'@DAL',10,{tgt:25,route:85,adot:12.4,snap:88,rz:1.6,yac:4.4}],
    ['Jaylen Waddle','WR','MIA',12,246,0.66,'@BUF',6,{tgt:24,route:84,adot:9.7,snap:86,rz:1.1,yac:5.7}],
    ['DK Metcalf','WR','PIT',5,244,0.64,'vs CLE',15,{tgt:24,route:82,adot:12.8,snap:85,rz:1.5,yac:4.2}],
    ['DJ Moore','WR','CHI',5,240,0.67,'vs DET',13,{tgt:25,route:86,adot:9.5,snap:88,rz:1.4,yac:5.1}],
    ['Zay Flowers','WR','BAL',7,238,0.66,'vs CIN',21,{tgt:24,route:85,adot:9.1,snap:87,rz:1.0,yac:5.4}],
    ['Courtland Sutton','WR','DEN',12,232,0.64,'@LV',25,{tgt:24,route:83,adot:11.3,snap:86,rz:1.8,yac:3.8}],
    ['Rome Odunze','WR','CHI',5,230,0.62,'vs DET',13,{tgt:22,route:81,adot:12.6,snap:84,rz:1.3,yac:4.0}],

    ['Bijan Robinson','RB','ATL',5,360,0.84,'@NO',28,{rush:74,snap:82,tgt:14,rz:3.2,ypt:5.4}],
    ['Jahmyr Gibbs','RB','DET',8,345,0.79,'@CHI',17,{rush:62,snap:68,tgt:13,rz:2.8,ypt:5.7}],
    ['Saquon Barkley','RB','PHI',9,335,0.81,'vs DAL',20,{rush:78,snap:78,tgt:9,rz:3.4,ypt:5.6}],
    ['Christian McCaffrey','RB','SF',14,320,0.80,'vs ARI',26,{rush:72,snap:84,tgt:16,rz:3.0,ypt:5.1}],
    ['De\u2019Von Achane','RB','MIA',12,315,0.72,'@BUF',11,{rush:64,snap:70,tgt:15,rz:2.5,ypt:5.9}],
    ['Ashton Jeanty','RB','LV',8,300,0.74,'vs DEN',19,{rush:80,snap:76,tgt:11,rz:3.1,ypt:4.9}],
    ['Jonathan Taylor','RB','IND',6,290,0.75,'vs HOU',16,{rush:79,snap:74,tgt:7,rz:3.3,ypt:5.2}],
    ['Derrick Henry','RB','BAL',7,285,0.78,'vs CIN',23,{rush:82,snap:66,tgt:4,rz:3.8,ypt:5.5}],
    ['Josh Jacobs','RB','GB',5,278,0.76,'@MIN',13,{rush:77,snap:72,tgt:9,rz:3.5,ypt:4.8}],
    ['Bucky Irving','RB','TB',9,272,0.71,'vs ATL',24,{rush:68,snap:69,tgt:12,rz:2.6,ypt:5.3}],
    ['Kyren Williams','RB','LAR',8,268,0.73,'vs SEA',18,{rush:75,snap:71,tgt:8,rz:3.2,ypt:4.6}],
    ['Chase Brown','RB','CIN',10,262,0.69,'@BAL',9,{rush:70,snap:73,tgt:13,rz:2.4,ypt:4.7}],
    ['Kenneth Walker III','RB','SEA',8,250,0.66,'@LAR',12,{rush:71,snap:64,tgt:10,rz:2.7,ypt:4.9}],
    ['James Cook','RB','BUF',7,248,0.68,'vs MIA',22,{rush:69,snap:62,tgt:9,rz:2.9,ypt:5.0}],
    ['Breece Hall','RB','NYJ',9,245,0.67,'vs NE',25,{rush:66,snap:70,tgt:14,rz:2.3,ypt:4.5}],
    ['Omarion Hampton','RB','LAC',12,240,0.64,'vs KC',8,{rush:67,snap:60,tgt:8,rz:2.5,ypt:4.8}],
    ['Chuba Hubbard','RB','CAR',14,232,0.65,'@TB',15,{rush:73,snap:67,tgt:7,rz:2.8,ypt:4.4}],
    ['Alvin Kamara','RB','NO',5,222,0.66,'vs ATL',17,{rush:60,snap:65,tgt:16,rz:2.2,ypt:4.6}],
    ['David Montgomery','RB','DET',8,212,0.67,'@CHI',14,{rush:55,snap:48,tgt:5,rz:3.6,ypt:4.7}],
    ['Joe Mixon','RB','HOU',6,218,0.64,'vs IND',20,{rush:74,snap:63,tgt:8,rz:3.0,ypt:4.5}],

    ['Josh Allen','QB','BUF',7,410,0.85,'vs MIA',21,{snap:99,pyd:248,ryd:38,tdg:2.6}],
    ['Lamar Jackson','QB','BAL',7,405,0.84,'vs CIN',19,{snap:99,pyd:232,ryd:54,tdg:2.5}],
    ['Jayden Daniels','QB','WAS',12,385,0.80,'@DAL',16,{snap:99,pyd:226,ryd:46,tdg:2.2}],
    ['Jalen Hurts','QB','PHI',9,365,0.79,'vs DAL',14,{snap:99,pyd:218,ryd:42,tdg:2.3}],
    ['Joe Burrow','QB','CIN',10,360,0.81,'@BAL',11,{snap:99,pyd:276,ryd:9,tdg:2.4}],
    ['Patrick Mahomes','QB','KC',10,350,0.80,'@LAC',13,{snap:99,pyd:264,ryd:18,tdg:2.2}],
    ['Baker Mayfield','QB','TB',9,345,0.74,'vs ATL',24,{snap:99,pyd:258,ryd:12,tdg:2.3}],
    ['Bo Nix','QB','DEN',12,338,0.73,'@LV',23,{snap:99,pyd:236,ryd:22,tdg:2.0}],
    ['Kyler Murray','QB','ARI',8,332,0.72,'@SF',9,{snap:99,pyd:228,ryd:31,tdg:2.0}],
    ['Caleb Williams','QB','CHI',5,325,0.70,'vs DET',15,{snap:99,pyd:240,ryd:25,tdg:1.9}],

    ['Brock Bowers','TE','LV',8,290,0.79,'vs DEN',26,{tgt:24,route:88,adot:7.8,snap:90,rz:1.6,yac:5.4}],
    ['Trey McBride','TE','ARI',8,268,0.77,'@SF',11,{tgt:25,route:89,adot:6.9,snap:91,rz:1.4,yac:4.8}],
    ['George Kittle','TE','SF',14,250,0.72,'vs ARI',22,{tgt:20,route:82,adot:8.4,snap:85,rz:1.7,yac:6.2}],
    ['Sam LaPorta','TE','DET',8,235,0.71,'@CHI',18,{tgt:19,route:84,adot:7.2,snap:86,rz:1.5,yac:4.9}],
    ['T.J. Hockenson','TE','MIN',6,218,0.70,'vs GB',16,{tgt:21,route:83,adot:7.6,snap:84,rz:1.3,yac:4.4}],
    ['Mark Andrews','TE','BAL',7,212,0.66,'vs CIN',20,{tgt:18,route:78,adot:8.1,snap:80,rz:1.8,yac:3.8}],
    ['David Njoku','TE','CLE',9,205,0.67,'@PIT',12,{tgt:20,route:81,adot:7.4,snap:83,rz:1.4,yac:4.6}],
    ['Travis Kelce','TE','KC',10,192,0.68,'@LAC',14,{tgt:19,route:80,adot:6.8,snap:82,rz:1.5,yac:4.2}]
  ];

  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  var players = raw.map(function (r) {
    var p = { name: r[0], pos: r[1], team: r[2], bye: r[3], seasonProj: r[4], consistency: r[5], opp: r[6], oppRank: r[7], adv: r[8] };
    // weekly projection range derived from role + matchup
    var baseWeek = p.seasonProj / 17;
    var matchupMult = 0.88 + (p.oppRank / 32) * 0.24;       // 0.88 (tough) .. 1.12 (smash)
    p.weekProj = Math.round(baseWeek * matchupMult * 10) / 10;
    var spread = clamp((1 - p.consistency) * 0.62 + 0.16, 0.16, 0.7);
    p.floor = Math.round(p.weekProj * (1 - spread * 0.62) * 10) / 10;
    p.ceiling = Math.round(p.weekProj * (1 + spread) * 10) / 10;
    p.spread = spread;
    p.matchupMult = matchupMult;
    // matchup label
    if (p.oppRank >= 24) p.matchup = 'great';
    else if (p.oppRank >= 18) p.matchup = 'good';
    else if (p.oppRank >= 12) p.matchup = 'neutral';
    else if (p.oppRank >= 7) p.matchup = 'tough';
    else p.matchup = 'avoid';
    // tag
    if (p.consistency >= 0.8) p.tag = 'Safe floor';
    else if (p.spread >= 0.45) p.tag = 'Boom / bust';
    else if (p.matchup === 'great') p.tag = 'Smash spot';
    else if (p.matchup === 'avoid') p.tag = 'Tough matchup';
    else p.tag = 'Steady';
    return p;
  });

  // rankings
  var byProj = players.slice().sort(function (a, b) { return b.seasonProj - a.seasonProj; });
  byProj.forEach(function (p, i) { p.ovrRank = i + 1; });
  ['QB','RB','WR','TE'].forEach(function (pos) {
    players.filter(function (p) { return p.pos === pos; })
      .sort(function (a, b) { return b.seasonProj - a.seasonProj; })
      .forEach(function (p, i) { p.posRank = i + 1; });
  });

  window.FF_PLAYERS = players;
  window.FF_TEAMS = Array.from(new Set(players.map(function (p) { return p.team; }))).sort();
})();
