#!/bin/bash
# Absolute path to project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Activate venv
source "$PROJECT_DIR/venv/bin/activate"

# Run the app and output errors
python "$PROJECT_DIR/whisper-py.py" 2>&1 | tee "$PROJECT_DIR/whisper-launch.log"
echo
