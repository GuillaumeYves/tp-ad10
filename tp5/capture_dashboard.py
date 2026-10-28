#!/usr/bin/env python3
"""Capturer le tableau de bord avec une session authentifiée."""

import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def capture(destination):
    password = json.loads((ROOT / '.lab/secrets.json').read_text())['grafana_password']
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        page = browser.new_page(viewport={'width': 1700, 'height': 1200})
        page.goto('http://127.0.0.1:3000/login', wait_until='networkidle')
        page.locator('input[name="user"]').fill('admin')
        page.locator('input[name="password"]').fill(password)
        page.locator('button[type="submit"]').click()
        page.wait_for_url(lambda url: '/login' not in url, timeout=30000)
        page.goto('http://127.0.0.1:3000/d/ad10-cluster/ad10?orgId=1&from=now-15m&to=now&kiosk=tv', wait_until='networkidle')
        page.get_by_text('Serveurs supervisés', exact=True).wait_for()
        page.wait_for_timeout(5000)
        page.screenshot(path=str(destination), full_page=True)
        browser.close()


if __name__ == '__main__':
    capture(sys.argv[1])
