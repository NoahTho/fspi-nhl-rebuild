#!/bin/bash
# fetch.sh GAMEID -> downloads raw JSON into its own dir, extracts, deletes the raw file
id="$1"
dir="./raw/g_$id"
mkdir -p "$dir"
url="https://raw.githubusercontent.com/sportsdataverse/fastRhockey-nhl-raw/main/nhl/json/final/$id.json"
for i in 1 2 3; do
  curl -s -f -m 120 -o "$dir/$id.json" "$url" && break
  sleep 2
done
if [ -s "$dir/$id.json" ]; then
  python3 -I ./extract.py "$dir/$id.json" > "./out/$id.jsonl"
else
  echo "{\"error\":\"download\",\"id\":\"$id\"}" > "./out/$id.jsonl"
fi
rm -rf "$dir"
