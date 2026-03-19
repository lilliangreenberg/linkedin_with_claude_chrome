#!/bin/bash
# Setup script for LinkedIn Scraper
# Installs Python dependencies and Playwright browser

set -e

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Installing Playwright Chromium browser..."
python3 -m playwright install chromium

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Set your ANTHROPIC_API_KEY environment variable"
echo "  2. Log in to LinkedIn:  python3 linkedin_scraper.py --login"
echo "  3. Scrape a profile:    python3 linkedin_scraper.py https://www.linkedin.com/in/someone/"
