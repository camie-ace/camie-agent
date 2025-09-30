#!/bin/bash

# Start the API server for accessing call history

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"

# Go to the agent directory
cd "$AGENT_DIR"

# Make sure required packages are installed
pip install fastapi uvicorn

# Start the API server
python -m api.main