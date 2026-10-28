#!/usr/bin/env bash
# Clean-install test of the .tgz the official way (as on any other bar):
# remove the app, POST /api/apps/stage, POST /api/apps/install, launch, press
# START, grab screens. curl only. Output -> test/stage_out.txt, screens ->
# test/shots/*.raw (72x16 BGR; test/shots.py turns them into PNGs).
# The high score (app localStorage) is saved first and put back if the
# reinstall removed it.
cd "$(dirname "$0")"
B=http://${1:-10.0.4.20}
ID=community.dino_run
LS=/ext/apps_data/jsrunner/$ID.localstorage.json
PKG=$(ls ../dist/$ID-*.tgz | tail -1)
mkdir -p shots && rm -f shots/*
{
  echo "package: $PKG"
  curl -s -m 5 "$B/api/storage/read?path=$LS" -o hiscore_backup.json -w "save hiscore %{http_code}\n"
  curl -s -m 5 -X POST "$B/api/apps/quit" -w 'quit %{http_code}\n' -o /dev/null
  for try in 1 2 3; do                     # the bar may still be closing the app
    sleep 2
    D=$(curl -s -m 10 -X DELETE "$B/api/apps?app_id=$ID" -w ' %{http_code}')
    echo "delete try $try: $D"
    case "$D" in *" 200") break;; esac
  done
  echo "listed after delete: $(curl -s -m 5 "$B/api/apps/list" | grep -c "\"$ID\"")"
  STAGE=$(curl -s -m 120 -X POST -H 'Content-Type: application/octet-stream' --data-binary "@$PKG" "$B/api/apps/stage" -w ' %{http_code}')
  echo "stage: $STAGE"
  KEY=$(printf '%s' "$STAGE" | sed -n 's/.*"install_key"[[:space:]]*:[[:space:]]*"\{0,1\}\([^",}]*\).*/\1/p')
  echo "key: $KEY"
  echo "install: $(curl -s -m 60 -X POST "$B/api/apps/install?install_key=$KEY" -w ' %{http_code}')"
  sleep 1
  echo "list: $(curl -s -m 5 "$B/api/apps/list" | tr '{' '\n' | grep "$ID")"
  if grep -q '"hi"' hiscore_backup.json 2>/dev/null; then
    NOW=$(curl -s -m 5 "$B/api/storage/read?path=$LS")
    case "$NOW" in *'"hi"'*) echo "hiscore kept";;
      *) curl -s -m 5 -X POST -H 'Content-Type: application/octet-stream' --data-binary @hiscore_backup.json \
           "$B/api/storage/write?path=$LS" -w "hiscore restored %{http_code}\n" -o /dev/null;;
    esac
  fi
  echo "launch: $(curl -s -m 5 -X POST "$B/api/apps/launch?app_id=$ID" -w ' %{http_code}')"
  sleep 2.5
  curl -s -m 5 "$B/api/screen?display=0" -o shots/title_1.raw -w "shot title_1 %{http_code}\n"
  sleep 1.7
  curl -s -m 5 "$B/api/screen?display=0" -o shots/title_2.raw -w "shot title_2 %{http_code}\n"
  curl -s -m 5 -X POST "$B/api/input?key=start" -o /dev/null -w "start %{http_code}\n"
  for i in 01 02 03 04 05 06 07 08 09 10 11 12; do
    sleep 0.4
    curl -s -m 5 "$B/api/screen?display=0" -o "shots/play_$i.raw" -w "shot play_$i %{http_code}\n"
  done
  sleep 1
  curl -s -m 5 "$B/api/screen?display=0" -o shots/over_1.raw -w "shot over_1 %{http_code}\n"
} > stage_out.txt 2>&1
echo stage test done
