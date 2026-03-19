#!/bin/bash
# Setup script for LinkedIn Scraper (Chrome Extension + CDP version)
# Installs Python dependencies. Requires Chrome or Chromium to be installed.

set -e

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Checking for Chrome / Chromium..."
if command -v google-chrome &>/dev/null; then
    echo "  Found: $(google-chrome --version)"
elif command -v chromium &>/dev/null; then
    echo "  Found: $(chromium --version)"
elif command -v chromium-browser &>/dev/null; then
    echo "  Found: $(chromium-browser --version)"
else
    echo "  WARNING: Chrome or Chromium not found in PATH."
    echo "  Please install Google Chrome or Chromium before running the scraper."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Set your ANTHROPIC_API_KEY environment variable"
echo "  2. Log in to LinkedIn:  python3 linkedin_scraper.py --login"
echo "  3. Scrape a profile:    python3 linkedin_scraper.py https://www.linkedin.com/in/someone/"
