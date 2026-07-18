"""Diagnóstico rápido do fluxo de login Kling (headless)."""
from __future__ import annotations

import asyncio


async def probe(*, press_escape: bool) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
        await page.goto("https://kling.ai/app/video/new", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        btn = page.locator('button:has-text("One-click Sign In")')
        if await btn.count():
            await btn.first.click(force=True)
        await page.wait_for_timeout(3000)

        if press_escape:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

        email_buttons = page.locator("div.sign-in-button")
        count = await email_buttons.count()
        texts = []
        for i in range(count):
            texts.append((await email_buttons.nth(i).inner_text()).strip())

        welcome = page.get_by_text("Welcome to Kling AI")
        print(f"escape={press_escape} welcome={await welcome.count()} email_buttons={texts}")
        await browser.close()


async def main() -> None:
    print("--- sem Escape ---")
    await probe(press_escape=False)
    print("--- com Escape (bug antigo) ---")
    await probe(press_escape=True)


if __name__ == "__main__":
    asyncio.run(main())
