#!/usr/bin/env bash
# Play a short round on the bar over HTTP input and grab the front screen.
# Run after `npm run app:install && npm run app:run`. Screens go to a new
# folder test/out/<time>/ as raw 72x16 BGR (decode with test/shots.py <dir>).
cd "$(dirname "$0")" || exit 1
B=http://${1:-10.0.4.20}
O="out/$(date +%H%M%S)"
mkdir -p "$O"
shot() { curl -s -m 5 "$B/api/screen?display=0" -o "$O/$1.raw"; }
key() { curl -s -m 5 -X POST "$B/api/input?key=$1" -o /dev/null -w "$1 %{http_code}\n"; }

sleep 1; shot 01_title
key start; sleep 0.8; shot 02_run
key start; sleep 0.15; shot 03_jump
sleep 1.5; shot 04_run
for i in 1 2 3 4 5 6 7 8; do sleep 1; shot "05_wait_$i"; done
key start; sleep 0.8; shot 06_retry
key back; sleep 1; shot 07_after_back
echo "$O"
