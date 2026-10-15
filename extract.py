"""Extract the per-team stats the FSPI NHL Points Attribution Table needs
from one fastRhockey-nhl-raw game JSON. Prints one JSON line per game."""
import json
import sys


def box_value(team_box, cat, side):
    for row in team_box or []:
        if row["category"] == cat:
            return row[f"{side}Value"]
    return None


def main(path):
    d = json.load(open(path))
    gi = d["game_info"][0]
    sides = {"home": gi["home_team_abbr"], "away": gi["away_team_abbr"]}

    goals = []
    for per in d.get("scoring") or []:
        ptype = per["periodDescriptor"]["periodType"]
        for g in per.get("goals") or []:
            goals.append({
                "team": g["teamAbbrev"]["default"],
                "strength": g.get("strength"),
                "modifier": g.get("goalModifier"),
                "ptype": ptype,
                "period": per["periodDescriptor"]["number"],
                "time": g.get("timeInPeriod"),
                "home": g.get("homeScore"),
                "away": g.get("awayScore"),
            })

    pens = []
    for per in d.get("penalties") or []:
        for p in per.get("penalties") or []:
            pens.append({
                "team": p["teamAbbrev"]["default"],
                "type": p.get("type"),
                "dur": p.get("duration"),
                "desc": p.get("descKey"),
                "period": per["periodDescriptor"]["number"],
                "time": p.get("timeInPeriod"),
            })

    periods = [p["periodDescriptor"]["periodType"] for p in d["linescore"].get("byPeriod", [])]

    teams = {}
    for side, abbr in sides.items():
        fo = box_value(d["team_box"], "faceoffWins", side) or "0/0"
        fw, ft = (int(x) for x in fo.split("/"))
        gs = [g for g in d.get("goalie_stats") or [] if g["home_away"] == side]
        teams[side] = {
            "abbr": abbr,
            "sog": int(box_value(d["team_box"], "sog", side) or 0),
            "fo_w": fw,
            "fo_t": ft,
            "hits": int(box_value(d["team_box"], "hits", side) or 0),
            "blocks": int(box_value(d["team_box"], "blockedShots", side) or 0),
            "give": int(box_value(d["team_box"], "giveaways", side) or 0),
            "take": int(box_value(d["team_box"], "takeaways", side) or 0),
            "saves": sum(g.get("saves") or 0 for g in gs),
            "shots_against": sum(g.get("shots_against") or 0 for g in gs),
        }

    out = {
        "game_id": gi["game_id"],
        "season": gi["season"],
        "type": gi["game_type"],
        "date": gi["game_date"],
        "state": gi.get("game_state"),
        "final_home": gi["home_score"],
        "final_away": gi["away_score"],
        "periods": periods,
        "shootout": d.get("shootout") is not None and len(d.get("shootout") or []) > 0,
        "home": teams["home"],
        "away": teams["away"],
        "goals": goals,
        "pens": pens,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            main(p)
        except Exception as e:  # report and keep going
            print(json.dumps({"error": str(e), "path": p}))
