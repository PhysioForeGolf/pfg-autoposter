#!/bin/sh
# usage: tools/unlock_music.sh KEY   -> decrypts audio/music-locked/*.enc into audio/music/
cd "$(dirname "$0")/.." && mkdir -p audio/music
for f in audio/music-locked/*.enc; do
  openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:"$1" -in "$f" -out "audio/music/$(basename "$f" .enc)" || exit 1
done
ls audio/music
