#!/bin/bash
cd "$(dirname "$0")"
python3 comic_volume_creator_server.py &
sleep 2
chromium-browser http://localhost:8765/
