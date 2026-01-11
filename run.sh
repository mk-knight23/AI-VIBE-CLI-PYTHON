#!/bin/bash

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the AI Agent
python3 main.py "$@"
