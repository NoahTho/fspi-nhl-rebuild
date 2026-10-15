"""
Independent rebuild of the CME FutureSports Performance Index (FSPI) for NHL teams,
following the public FutureSports NHL Team Index Methodology Guide
(Points Attribution Table, end-of-game / monthly / seasonal milestones,
Seasonal Adjustment Factor, Stanley Cup bonus, 7,500 base level).

Input : games.jsonl (one line per game, produced by extract.py)
Output: team_games.csv  (one row per team per game, with every point component)
        index_daily.csv (daily index level per team)
        milestones.csv  (monthly / seasonal / Stanley Cup awards)

Assumptions where the public material is ambiguous are marked ASSUMPTION.
"""
import json
from collections import defaultdict

import pandas as pd

BASE = 7500.0
SAF = {"R": 1.0, "P": 1.5}

# ---- Points Attribution Table (per occurrence) ----
PAT = {
    "goal_ev": 12, "goal_pp": 10, "goal_sh": 15, "goal_en_adj": -2,
    "ga_ev": -12, "ga_pp": -10, "ga_sh": -15, "ga_en_adj": 7.5,
    "sog": 1.5, "opp_sog": -1.5,
    "save": 0.75, "opp_save": -0.75,
    "fo_win": 0.5, "fo_loss": -0.5,
    "block": 0.8, "blocked_by_opp": -0.8,
    "hit": 0.1, "hit_taken": -0.1,
    "takeaway": 2.5, "giveaway": -0.8,
    "pen_minor": -1, "pen_extended": -2, "pen_misconduct": -4, "pen_ejection": -10,
}
OUTCOME = {"win": 10, "reg_loss": -10, "otso_loss": -5}
GAME_MS = {
    "gf6": 35, "gf5": 20, "gf1": -20,
    "ga6": -35, "ga5": -20, "ga1": 20,
    "sv940": 10, "sv850": -12.5,
    "shutout": 50, "shut_out": -50, "clinch": 30,
}
CLINCH_LATE_SEC = 18 * 60   # guide #11: go-ahead goal at or after 18:00 of the 3rd
MONTHLY = 125
SEASONAL = 250
CUP = 750

CONF = {
    "East": ["BOS", "BUF", "DET", "FLA", "MTL", "OTT", "TBL", "TOR",
             "CAR", "CBJ", "NJD", "NYI", "NYR", "PHI", "PIT", "WSH"],
    "West": ["CHI", "COL", "DAL", "MIN", "NSH", "STL", "UTA", "WPG",
             "ANA", "CGY", "EDM", "LAK", "SJS", "SEA", "VAN", "VGK"],
}

# components grouped for reporting
GROUPS = {
    "Goals": ["goal_ev", "goal_pp", "goal_sh", "goal_en_adj", "ga_ev", "ga_pp", "ga_sh", "ga_en_adj"],
    "Shots & saves": ["sog", "opp_sog", "save", "opp_save"],
    "Possession": ["fo_win", "fo_loss", "takeaway", "giveaway"],
    "Physical": ["block", "blocked_by_opp", "hit", "hit_taken"],
    "Penalties": ["pen_minor", "pen_extended", "pen_misconduct", "pen_ejection"],
    "Result": ["win", "reg_loss", "otso_loss"],
    "Game milestones": list(GAME_MS.keys()),
}


def is_fight(p):
    return p["type"] == "MAJ" and p.get("desc") == "fighting"


def unmatched_fights(pens):
    """Guide #25: a fighting major scores 0 only when both teams received one at the
    same period and time (matched pairs). Returns {team: count of unmatched majors}."""
    by_slot = defaultdict(lambda: defaultdict(int))
    for p in pens:
        if is_fight(p):
            by_slot[(p.get("period"), p.get("time"))][p["team"]] += 1
    out = defaultdict(int)
    for teams in by_slot.values():
        paired = min(teams.values()) if len(teams) == 2 else 0
        for t, n in teams.items():
            out[t] += n - paired
    return out


def penalty_class(p):
    """Index components for one penalty (fighting majors handled by unmatched_fights)."""
    t, dur = p["type"], p["dur"]
    if t in ("MIN", "BEN", "PS"):
        return ["pen_extended" if dur == 4 else "pen_minor"]   # double minor = extended
    if t == "MAJ":
        return [] if is_fight(p) else ["pen_extended"]
    if t == "MIS":
        return ["pen_misconduct"]
    if t == "MAT":
        # Calibrated against official closes: a match penalty scores as both an
        # extended penalty and an ejection.
        return ["pen_extended", "pen_ejection"]
    if t == "GAM":
        return ["pen_ejection"]
    return ["pen_minor"]


def team_game_rows(g):
    rows = []
    so = "SO" in g["periods"]
    goals = [x for x in g["goals"] if x["ptype"] != "SO"]   # shootout goals never count
    fights = unmatched_fights(g["pens"])
    for side, opp in (("home", "away"), ("away", "home")):
        me, them = g[side], g[opp]
        t, o = me["abbr"], them["abbr"]
        c = defaultdict(float)

        for x in goals:
            en = x["modifier"] in ("empty-net", "awarded-empty-net")
            s = x["strength"] if x["strength"] in ("ev", "pp", "sh") else "ev"
            if x["team"] == t:
                c[f"goal_{s}"] += 1
                c["goal_en_adj"] += en
            else:
                c[f"ga_{s}"] += 1
                c["ga_en_adj"] += en

        c["sog"] = me["sog"]
        c["opp_sog"] = them["sog"]
        c["save"] = me["saves"]
        c["opp_save"] = them["saves"]
        c["fo_win"] = me["fo_w"]
        c["fo_loss"] = me["fo_t"] - me["fo_w"]
        c["block"] = me["blocks"]
        c["blocked_by_opp"] = them["blocks"]
        c["hit"] = me["hits"]
        c["hit_taken"] = them["hits"]
        c["takeaway"] = me["take"]
        c["giveaway"] = me["give"]
        for p in g["pens"]:
            if p["team"] == t:
                for k in penalty_class(p):
                    c[k] += 1
        c["pen_extended"] += fights[t]

        gf = sum(1 for x in goals if x["team"] == t)
        ga = sum(1 for x in goals if x["team"] == o)
        fin_me = g[f"final_{side}"]
        fin_them = g[f"final_{opp}"]
        won = fin_me > fin_them
        extra = len(g["periods"]) > 3
        if won:
            c["win"] = 1
        elif extra:
            c["otso_loss"] = 1
        else:
            c["reg_loss"] = 1

        # end-of-game milestones (counts of 1)
        if gf >= 6: c["gf6"] = 1
        elif gf == 5: c["gf5"] = 1
        elif gf == 1: c["gf1"] = 1
        if ga >= 6: c["ga6"] = 1
        elif ga == 5: c["ga5"] = 1
        elif ga == 1: c["ga1"] = 1
        # Team save % calibrated against official closes: opponent shots on goal
        # vs. all non-shootout goals allowed (empty-net goals included).
        sa = them["sog"]
        if sa > 0:
            svp = (sa - ga) / sa
            if svp >= 0.940: c["sv940"] = 1
            elif svp <= 0.850: c["sv850"] = 1
        if ga == 0: c["shutout"] = 1          # 0-0 shootout credits both teams
        if gf == 0: c["shut_out"] = 1
        # "Game clinching goal" (guide #11): the sudden-death OVERTIME winner, or in
        # regulation a go-ahead goal (putting the team up by exactly 1) scored at or
        # after 18:00 of the 3rd in a game won by exactly 1. Shootout wins earn nothing.
        if won and extra and not so:
            c["clinch"] = 1
        elif won and not extra and fin_me - fin_them == 1:
            lead_for_me = 1 if side == "home" else -1
            tie_breaker = None          # last goal that broke a tie in our favour
            for x in goals:             # goals are in game order
                if x["team"] == t and x["home"] - x["away"] == lead_for_me:
                    tie_breaker = x
            x = tie_breaker
            if x and x.get("period") == 3 and x.get("time"):
                mm, ss = (int(v) for v in x["time"].split(":"))
                if mm * 60 + ss >= CLINCH_LATE_SEC:
                    c["clinch"] = 1

        saf = SAF[g["type"]]
        pts = {k: v * PAT[k] * saf for k, v in c.items() if k in PAT}
        pts.update({k: v * OUTCOME[k] * saf for k, v in c.items() if k in OUTCOME})
        pts.update({k: v * GAME_MS[k] * saf for k, v in c.items() if k in GAME_MS})
        row = {
            "game_id": g["game_id"], "season": g["season"], "type": g["type"],
            "date": g["date"], "team": t, "opp": o, "home": side == "home",
            "gf": gf, "ga": ga, "final_for": fin_me, "final_against": fin_them,
            "won": won, "extra": extra, "so": so,
            "points": sum(pts.values()),
        }
        for grp, keys in GROUPS.items():
            row["g_" + grp] = sum(pts.get(k, 0.0) for k in keys)
        for k in list(PAT) + list(OUTCOME) + list(GAME_MS):
            row["n_" + k] = c.get(k, 0)
            row["p_" + k] = pts.get(k, 0.0)
        rows.append(row)
    return rows


def standings(tg):
    s = tg.groupby("team").agg(
        gp=("won", "size"), w=("won", "sum"),
        otl=("n_otso_loss", "sum"),
        rw=("won", lambda x: (x & ~tg.loc[x.index, "extra"]).sum()),
        row_=("won", lambda x: (x & ~tg.loc[x.index, "so"]).sum()),
        gf=("final_for", "sum"), ga=("final_against", "sum"),
    )
    s["pts"] = 2 * s["w"] + s["otl"]
    s["gd"] = s["gf"] - s["ga"]
    return s


def award_extremes(totals, label, value, when, out, higher_good=True):
    """Give +value to every team tied for the max and -value to every team tied for
    the min of `totals` (higher_good=True), or the reverse."""
    hi, lo = totals.max(), totals.min()
    for t in totals.index[totals == hi]:
        out.append({"date": when, "team": t, "milestone": f"Most {label}", "points": value if higher_good else -value})
    if higher_good is not None:
        for t in totals.index[totals == lo]:
            out.append({"date": when, "team": t, "milestone": f"Least {label}", "points": -value if higher_good else value})


def milestones_for_season(tg):
    out = []
    reg = tg[tg["type"] == "R"].copy()
    reg["month"] = reg["date"].str[:7]
    games_per_month = reg.groupby("month")["game_id"].nunique()
    for month, n in games_per_month.items():
        if n < 100:
            continue
        m = reg[reg["month"] == month]
        # credited on the calculation day after the month's last regular-season game
        when = (pd.Timestamp(m["date"].max()) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        tot = m.groupby("team")[["gf", "n_block", "n_takeaway", "n_giveaway"]].sum()
        award_extremes(tot["gf"], "goals (month)", MONTHLY, when, out)
        award_extremes(tot["n_block"], "blocks (month)", MONTHLY, when, out)
        mx = tot["n_takeaway"].max()
        for t in tot.index[tot["n_takeaway"] == mx]:
            out.append({"date": when, "team": t, "milestone": "Most takeaways (month)", "points": MONTHLY})
        mx = tot["n_giveaway"].max()
        for t in tot.index[tot["n_giveaway"] == mx]:
            out.append({"date": when, "team": t, "milestone": "Most giveaways (month)", "points": -MONTHLY})

    # seasonal milestones, only once the regular season is complete (82 GP each)
    gp = reg.groupby("team").size()
    if len(gp) == 32 and (gp == 82).all():
        when = (pd.Timestamp(reg["date"].max()) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        tot = reg.groupby("team")[["gf", "n_block", "n_takeaway", "n_giveaway"]].sum()
        award_extremes(tot["gf"], "goals (season)", SEASONAL, when, out)
        award_extremes(tot["n_block"], "blocks (season)", SEASONAL, when, out)
        mx = tot["n_takeaway"].max()
        for t in tot.index[tot["n_takeaway"] == mx]:
            out.append({"date": when, "team": t, "milestone": "Most takeaways (season)", "points": SEASONAL})
        mx = tot["n_giveaway"].max()
        for t in tot.index[tot["n_giveaway"] == mx]:
            out.append({"date": when, "team": t, "milestone": "Most giveaways (season)", "points": -SEASONAL})
        st = standings(reg)
        for conf, teams in CONF.items():
            c = st.loc[teams].sort_values(["pts", "rw", "row_", "w", "gd"], ascending=False)
            out.append({"date": when, "team": c.index[0], "milestone": f"First in {conf}", "points": SEASONAL})
            out.append({"date": when, "team": c.index[-1], "milestone": f"Last in {conf}", "points": -SEASONAL})

    # Stanley Cup: winner of the last playoff game, once a team has 16 playoff wins
    po = tg[tg["type"] == "P"]
    if len(po):
        wins = po.groupby("team")["won"].sum()
        if wins.max() == 16:
            champ = wins.idxmax()
            last = po[po["team"] == champ]["date"].max()
            out.append({"date": last, "team": champ, "milestone": "Stanley Cup", "points": CUP * SAF["P"]})
    return pd.DataFrame(out)


def build(games_path="games.jsonl"):
    games = [json.loads(l) for l in open(games_path)]
    tg = pd.DataFrame([r for g in games for r in team_game_rows(g)])
    tg = tg.sort_values(["season", "date", "game_id"]).reset_index(drop=True)

    ms_all, daily_all = [], []
    for season, s in tg.groupby("season"):
        ms = milestones_for_season(s)
        if len(ms):
            ms["season"] = season
        ms_all.append(ms)
        teams = sorted(s["team"].unique())
        start = pd.Timestamp(s["date"].min())
        end = pd.Timestamp(max(s["date"].max(), ms["date"].max() if len(ms) else s["date"].max()))
        days = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")
        game_pts = s.groupby(["date", "team"])["points"].sum().unstack(fill_value=0.0)
        ms_pts = ms.groupby(["date", "team"])["points"].sum().unstack(fill_value=0.0) if len(ms) else None
        delta = pd.DataFrame(0.0, index=days, columns=teams)
        delta = delta.add(game_pts.reindex(index=days, columns=teams, fill_value=0.0), fill_value=0.0)
        if ms_pts is not None:
            delta = delta.add(ms_pts.reindex(index=days, columns=teams, fill_value=0.0), fill_value=0.0)
        level = BASE + delta.cumsum()
        level.index.name = "date"
        lv = level.reset_index().melt(id_vars="date", var_name="team", value_name="index")
        lv["season"] = season
        daily_all.append(lv)

    ms_df = pd.concat([m for m in ms_all if len(m)], ignore_index=True)
    daily = pd.concat(daily_all, ignore_index=True)
    return tg, ms_df, daily


if __name__ == "__main__":
    tg, ms, daily = build()
    tg.to_csv("team_games.csv", index=False)
    ms.to_csv("milestones.csv", index=False)
    daily.to_csv("index_daily.csv", index=False)
    print(len(tg), "team-games;", len(ms), "milestone awards;", len(daily), "daily rows")
