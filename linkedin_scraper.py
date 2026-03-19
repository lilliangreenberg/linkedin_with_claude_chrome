#!/usr/bin/env python3
"""
LinkedIn Profile Scraper

Uses Playwright (Chrome) to visit a LinkedIn profile, take a screenshot,
and uses Claude's vision to extract profile information.

Supports persistent cookies so you only need to log in once.

Usage:
    python3 linkedin_scraper.py <linkedin_profile_url>
    python3 linkedin_scraper.py --login   # Log in to LinkedIn first (interactive)
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import anthropic
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


SCRIPT_DIR = Path(__file__).parent.resolve()
COOKIES_FILE = SCRIPT_DIR / "linkedin_cookies.json"
OUTPUT_DIR = SCRIPT_DIR / "output"


def save_cookies(context):
    """Save browser cookies to a JSON file."""
    cookies = context.cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"Cookies saved to {COOKIES_FILE}")


def load_cookies(context):
    """Load cookies from file into the browser context."""
    if COOKIES_FILE.exists():
        cookies = json.loads(COOKIES_FILE.read_text())
        context.add_cookies(cookies)
        print(f"Loaded {len(cookies)} cookies from {COOKIES_FILE}")
        return True
    return False


def close_popups(page):
    """Attempt to close common LinkedIn pop-ups and modals."""
    popup_selectors = [
        # "Sign in" / "Join" modal dismiss
        'button[aria-label="Dismiss"]',
        'button[aria-label="Close"]',
        # Messaging overlay
        'button.msg-overlay-bubble-header__control--close',
        # Cookie consent
        'button[action-type="DENY"]',
        # Generic modal close buttons
        '.artdeco-modal__dismiss',
        '.artdeco-toast-item__dismiss',
        # "See more" notification prompts
        'button.artdeco-notification-badge__dismiss',
        # GDPR / cookie banners
        '#artdeco-global-alert-container button',
    ]
    closed = 0
    for selector in popup_selectors:
        try:
            buttons = page.query_selector_all(selector)
            for btn in buttons:
                if btn.is_visible():
                    btn.click()
                    closed += 1
                    time.sleep(0.3)
        except Exception:
            pass
    if closed:
        print(f"Closed {closed} pop-up(s)")


def take_screenshot(page, url):
    """Navigate to URL, wait, close popups, and screenshot."""
    print(f"Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    print("Waiting 5 seconds for page to fully load...")
    time.sleep(5)

    close_popups(page)
    time.sleep(1)

    # Scroll to top to capture the header/profile area
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Create a filename from the URL
    slug = re.sub(r'[^a-zA-Z0-9]', '_', url.split("linkedin.com/")[-1].strip("/"))
    if not slug:
        slug = "profile"

    screenshot_path = OUTPUT_DIR / f"{slug}_screenshot.png"
    page.screenshot(path=str(screenshot_path), full_page=False)
    print(f"Screenshot saved to {screenshot_path}")
    return screenshot_path, slug


def extract_logo_url_from_page(page):
    """Try to extract the company/profile logo URL directly from the page DOM."""
    selectors = [
        # Company page logo
        'img.org-top-card-primary-content__logo',
        'img.artdeco-entity-image--square',
        # Profile photo
        'img.pv-top-card-profile-picture__image',
        'img.presence-entity__image',
        # Generic profile images
        'img[data-ghost-classes*="profile"]',
        '.pv-top-card--photo img',
        'img.profile-photo-edit__preview',
    ]
    for selector in selectors:
        try:
            imgs = page.query_selector_all(selector)
            for img in imgs:
                src = img.get_attribute("src")
                if src and src.startswith("http") and "data:image" not in src:
                    return src
        except Exception:
            pass
    return None


def analyze_with_claude(screenshot_path):
    """Use Claude's vision to extract profile info from the screenshot."""
    client = anthropic.Anthropic()

    image_data = base64.standard_b64encode(screenshot_path.read_bytes()).decode("utf-8")

    print("Analyzing screenshot with Claude...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze this LinkedIn profile/company page screenshot. "
                            "Extract ALL useful information you can see and return it as JSON. "
                            "Include these fields where available:\n"
                            "- name: person or company name\n"
                            "- headline: the headline/tagline\n"
                            "- company: current company name (for person profiles)\n"
                            "- title: current job title (for person profiles)\n"
                            "- location: geographic location\n"
                            "- industry: industry or sector\n"
                            "- about: summary/about text if visible\n"
                            "- connections: connection/follower count\n"
                            "- experience: list of visible experience entries\n"
                            "- education: list of visible education entries\n"
                            "- website: any website URLs shown\n"
                            "- profile_url: the LinkedIn URL if visible\n"
                            "- any other useful fields you can identify\n\n"
                            "Return ONLY valid JSON, no markdown fences or extra text."
                        ),
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown fences if present
    if response_text.startswith("```"):
        response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print("Warning: Claude's response was not valid JSON. Saving raw text.")
        return {"raw_response": response_text}


def download_logo(logo_url, slug, cookies=None):
    """Download the logo image to the output directory."""
    if not logo_url:
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Convert playwright cookies to requests cookies
        jar = {}
        if cookies:
            for c in cookies:
                jar[c["name"]] = c["value"]

        resp = requests.get(logo_url, headers=headers, cookies=jar, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 100:
            # Determine extension from content type
            ct = resp.headers.get("content-type", "")
            ext = ".png"
            if "jpeg" in ct or "jpg" in ct:
                ext = ".jpg"
            elif "svg" in ct:
                ext = ".svg"
            elif "gif" in ct:
                ext = ".gif"

            logo_path = OUTPUT_DIR / f"{slug}_logo{ext}"
            logo_path.write_bytes(resp.content)
            print(f"Logo saved to {logo_path}")
            return str(logo_path)
    except Exception as e:
        print(f"Warning: Could not download logo: {e}")
    return None


def do_login():
    """Open a browser for manual LinkedIn login and save cookies."""
    print("Opening Chrome for LinkedIn login...")
    print("Please log in manually. The browser will stay open for 120 seconds.")
    print("Once logged in, press Enter in this terminal (or wait for timeout).")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")

        try:
            input("Press Enter after logging in (or Ctrl+C to cancel)...")
        except (EOFError, KeyboardInterrupt):
            print("\nWaiting 60 seconds for login...")
            time.sleep(60)

        save_cookies(context)
        browser.close()

    print("Login complete! You can now scrape profiles.")


def scrape_profile(url):
    """Main scraping workflow."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Load saved cookies
        has_cookies = load_cookies(context)
        if not has_cookies:
            print("Warning: No saved cookies found. Run with --login first to log in.")
            print("Proceeding anyway (you may see a login page)...\n")

        page = context.new_page()

        # Take screenshot
        screenshot_path, slug = take_screenshot(page, url)

        # Try to get logo URL from page
        logo_url = extract_logo_url_from_page(page)
        print(f"Logo URL from page: {logo_url or 'not found'}")

        # Get cookies for download requests
        current_cookies = context.cookies()

        # Save updated cookies (may have new session tokens)
        save_cookies(context)

        browser.close()

    # Analyze screenshot with Claude
    profile_data = analyze_with_claude(screenshot_path)

    # Add metadata
    profile_data["_source_url"] = url
    profile_data["_scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    profile_data["_screenshot"] = str(screenshot_path)

    # Download logo
    # Prefer logo URL from Claude's analysis if available, fall back to DOM extraction
    final_logo_url = logo_url
    if not final_logo_url and isinstance(profile_data.get("logo_url"), str):
        final_logo_url = profile_data["logo_url"]

    logo_path = download_logo(final_logo_url, slug, cookies=current_cookies)
    if logo_path:
        profile_data["_logo_file"] = logo_path

    # Save JSON
    json_path = OUTPUT_DIR / f"{slug}.json"
    json_path.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False))
    print(f"\nProfile data saved to {json_path}")

    # Print summary
    print("\n--- Extracted Info ---")
    for key, value in profile_data.items():
        if not key.startswith("_") and key != "raw_response":
            print(f"  {key}: {value}")

    return profile_data


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Profile Scraper")
    parser.add_argument("url", nargs="?", help="LinkedIn profile/company URL to scrape")
    parser.add_argument("--login", action="store_true", help="Open browser for manual LinkedIn login")
    args = parser.parse_args()

    if args.login:
        do_login()
        return

    if not args.url:
        parser.print_help()
        print("\nExamples:")
        print("  python3 linkedin_scraper.py --login")
        print("  python3 linkedin_scraper.py https://www.linkedin.com/in/someone/")
        print("  python3 linkedin_scraper.py https://www.linkedin.com/company/some-company/")
        sys.exit(1)

    if "linkedin.com" not in args.url:
        print("Error: URL must be a LinkedIn URL")
        sys.exit(1)

    scrape_profile(args.url)


if __name__ == "__main__":
    main()
