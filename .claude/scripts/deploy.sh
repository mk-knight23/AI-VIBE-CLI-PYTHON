#!/bin/bash

# Deploy Script for [REPO_NAME]
# This script handles deployment to production

set -e  # Exit on error

echo "🚀 Deploying [REPO_NAME]..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: You're on '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build first
echo -e "${YELLOW}Building...${NC}"
bash .claude/scripts/build.sh

# Deploy
echo -e "${YELLOW}Deploying to [PLATFORM]...${NC}"
[DEPLOY_COMMAND]

echo -e "${GREEN}✓ Deployed successfully!${NC}"
echo ""
echo "Live URL: [DEPLOY_URL]"
echo "Deploy logs: [LOGS_URL]"
