# FSPI NHL Rebuild

An independent rebuild of the CME FutureSports Performance Index (FSPI) for all 32 NHL teams,
computed from raw NHL play-by-play and boxscore data using the public
FutureSports NHL Team Index Methodology Guide.

**Result:** matches the official end-of-day values for Oct 11, 2026 to the cent for 29 of 32 teams,
and within 2 points for the other 3. Reproduces FutureSports' published Blackhawks example
(+116.40, CHI 8 STL 3, Oct 15, 2025) exactly.

## Rules found by calibration (not stated in the public guide)

| Rule | Literal reading | What the official values show |
|---|---|---|
| Game clinching goal (+30) | Ordinary game-winning goal | Overtime winner, or a tie-breaking winner in the final minute of regulation (cut-off between 18:16 and 19:00 of the 3rd) |
| Fighting majors | Extended penalty, −2 | 0 points |
| Save % milestones (.940 / .850) | Goalie saves ÷ shots against | Opponent shots on goal vs. all goals allowed, empty-net goals included |

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
