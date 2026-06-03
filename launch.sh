#!/bin/bash
cd "$(dirname "$0")"
pkill -f "comic_volume_creator_server" 2>/dev/null
sleep 1
python3 comic_volume_creator_server.py &
until nc -z localhost 8016 2>/dev/null; do sleep 0.2; done
xdg-open http://localhost:8016/
