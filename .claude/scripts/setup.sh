#!/bin/bash

# Setup Script for [REPO_NAME]
# This script handles initial setup and installation

set -e  # Exit on error

echo "🚀 Setting up [REPO_NAME]..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node -v)${NC}"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"

[INSTALL_COMMAND]

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create environment file if not exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your values${NC}"
fi

# Run setup tasks
echo -e "${YELLOW}Running setup tasks...${NC}"

[SETUP_TASKS]

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "To start development:"
echo "  [DEV_COMMAND]"
echo ""
echo "To build for production:"
echo "  [BUILD_COMMAND]"
