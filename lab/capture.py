#!/usr/bin/env python3
"""Captures de pages et de sorties de commandes enregistrées."""

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--title", default="Résultat de commande")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        if args.source.startswith(("http://", "https://")):
            page.goto(args.source, wait_until="networkidle")
        else:
            content = Path(args.source).read_text()
            page.set_content("<!doctype html><meta charset='utf-8'><style>body{margin:32px;background:#111827;color:#e5e7eb}h1{font:22px sans-serif}pre{font:16px/1.5 monospace;white-space:pre-wrap}</style>"
                             + f"<h1>{html.escape(args.title)}</h1><pre>{html.escape(content)}</pre>")
        page.screenshot(path=args.destination, full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
