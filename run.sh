#!/bin/bash

# Make Click happy
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Start the app
cd /home/scouting/quickscout
source venv/bin/activate
export PYTHONUNBUFFERED=1
gunicorn -w 4 -b 127.0.0.1:5000 quickscout:app
