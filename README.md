# FSPI NHL Rebuild

An independent rebuild of the CME FutureSports Performance Index (FSPI) for all 32 NHL teams,
computed from raw NHL play-by-play and boxscore data using the public
FutureSports NHL Team Index Methodology Guide.

**Result:** matches the official end-of-day values for Oct 11, 2026 to the cent for 30 of 32 teams,
and within 1 point for the other 2 (TBL +0.75, NSH +0.80). Reproduces FutureSports' published Blackhawks example
(+116.40, CHI 8 STL 3, Oct 15, 2025) exactly.

## Scoring rules beyond the literal Points Attribution Table

| Rule | Literal reading | What the rebuild uses | Source |
|---|---|---|---|
| Game clinching goal (+30) | Ordinary game-winning goal | Overtime winner (no shootouts), or in regulation the go-ahead goal (putting the team up by exactly 1) scored at or after 18:00 of the 3rd, in a game won by exactly 1 | Guide definition #11 |
| Fighting majors | Extended penalty, −2 | 0 points when both teams receive a fighting major at the same period and time (matched pairs); any unmatched fighting major scores as extended, −2 | Guide definition #25 |
| Save % milestones (.940 / .850) | Goalie saves ÷ shots against | Opponent shots on goal vs. all goals allowed, empty-net goals included | Calibrated finding |
| Match penalty (MAT) | Ejection, −10 | Both extended penalty (−2) and ejection (−10) | New calibrated finding |

## Files

- `fetch.sh` – downloads one game JSON from sportsdataverse/fastRhockey-nhl-raw and runs the extractor
- `extract.py` – pulls the per-team stats the Points Attribution Table needs
- `fspi.py` – the index engine: per-game points, monthly/season milestones, playoff factor, Stanley Cup, daily index levels
- `compare.py` – compares the rebuild with official closes

## Run

```bash
mkdir -p out raw
# list of game ids, e.g. 2025020001 … 2025021312, 2025030111 …, 2026020001 …
cat ids.txt | xargs -P 8 -n 1 ./fetch.sh
cat out/*.jsonl > games.jsonl
python3 fspi.py      # writes team_games.csv, milestones.csv, index_daily.csv
python3 compare.py   # needs official_20261011.csv (team,official)
```

Data: NHL game data compiled by the open-source sportsdataverse project.
Not affiliated with FutureSports, CME Group or the NHL. Not investment advice.
