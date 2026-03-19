# LinkedIn Profile Scraper (Chrome Extension + CDP)

Scrapes LinkedIn profile and company pages using a **Chrome extension** and
**Chrome DevTools Protocol (CDP)** — no Playwright required.

## How It Works

1. **Chrome Extension** (`chrome_extension/`) contains a content script that
   extracts structured profile data directly from the LinkedIn DOM.
2. **Python script** launches Chrome with `--remote-debugging-port` and
   `--load-extension`, then uses CDP over WebSocket to:
   - Navigate to the target LinkedIn URL
   - Execute DOM extraction via `Runtime.evaluate`
   - Capture a screenshot via `Page.captureScreenshot`
3. **Claude Vision** analyzes the screenshot to enrich/validate the extracted data.
4. Results are merged (DOM data + Claude analysis) and saved as JSON.

## Requirements

- Python 3.8+
- Google Chrome or Chromium
- An `ANTHROPIC_API_KEY` environment variable

## Quick Start

```bash
# Install Python deps
bash setup.sh

# Log in to LinkedIn (opens a visible Chrome window)
python3 linkedin_scraper.py --login

# Scrape a profile
python3 linkedin_scraper.py https://www.linkedin.com/in/someone/
```

## Files

| File | Purpose |
|------|---------|
| `linkedin_scraper.py` | Main CLI — launches Chrome, coordinates CDP, calls Claude |
| `chrome_extension/manifest.json` | Extension manifest (Manifest V3) |
| `chrome_extension/content.js` | Content script — DOM extraction + popup dismissal |
| `chrome_extension/background.js` | Service worker — screenshot capture coordination |
| `setup.sh` | Installs Python dependencies |
| `requirements.txt` | Python package list |

## Output

Results are saved to the `output/` directory:
- `<slug>_screenshot.png` — page screenshot
- `<slug>.json` — extracted + Claude-analyzed profile data
- `<slug>_logo.png` — profile/company image (if found)
