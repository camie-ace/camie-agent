#!/bin/bash

# Ensure we are in the script's directory to find other scripts
cd "$(dirname "$0")"

echo "Checking for existing SIP dispatch rules..."

# Run the Python script to check rules and capture its output
RULE_STATUS=$(python config/check_dispatch_rules.py)

# Check the output
if [[ "$RULE_STATUS" == "NO_RULES" ]]; then
  echo "No SIP dispatch rules found. Provisioning..."
  echo "Running provision_livekit_trunks.py..."
  python config/provision_livekit_trunks.py
  if [ $? -ne 0 ]; then
    echo "Error running provision_livekit_trunks.py. Aborting."
    exit 1
  fi

  echo "Running provision_livekit_rules.py..."
  python config/provision_livekit_rules.py
  if [ $? -ne 0 ]; then
    echo "Error running provision_livekit_rules.py. Aborting."
    exit 1
  fi
  echo "Provisioning complete."
elif [[ "$RULE_STATUS" == "RULES_EXIST"* ]]; then
  echo "SIP dispatch rules already exist. Skipping provisioning."
elif [[ "$RULE_STATUS" == "ERROR"* ]]; then
  echo "Error checking for SIP dispatch rules. Please check logs from check_dispatch_rules.py. Aborting."
  exit 1
else
  echo "Unknown status from check_dispatch_rules.py: $RULE_STATUS. Aborting."
  exit 1
fi

echo "Starting the agent..."
python -m agent dev

echo "Agent script finished or was terminated."