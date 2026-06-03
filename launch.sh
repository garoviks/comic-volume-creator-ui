#!/bin/bash
cd "$(dirname "$0")"
pkill -f "comic_volume_creator_server" 2>/dev/null
sleep 1
python3 comic_volume_creator_server.py &
sleep 2
xdg-open http://localhost:8765/
