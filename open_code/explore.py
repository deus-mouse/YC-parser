import asyncio
import re
from playwright.async_api import async_playwright
from datetime import datetime, timedelta


async def explore_site():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Go to masters page
        url = "https://n625088.yclients.com/company/266762/personal/select-master?o="
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Get page content
        content = await page.content()
        
        # Save full HTML for analysis
        with open("page_source.html", "w") as f:
            f.write(content)
        
        print("Page loaded. Title:", await page.title())
        
        # Try to find master cards
        # Common selectors for master cards
        selectors = [
            "master-card",
            "[class*='master']",
            "[class*='staff']",
            ".card",
            "a[href*='master']",
            "a[href*='staff']",
        ]
        
        for sel in selectors:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"Selector '{sel}' found {len(elements)} elements")
            except:
                pass
        
        # Get all links
        links = await page.query_selector_all("a")
        print(f"\nFound {len(links)} links on page")
        
        # Print some links that might be masters
        print("\nLinks with 'master' or 'staff':")
        for link in links[:30]:
            href = await link.get_attribute("href")
            if href and ("master" in href.lower() or "staff" in href.lower()):
                print(f"  {href}")
        
        await browser.close()
        print("\nSaved page source to page_source.html")


if __name__ == "__main__":
    asyncio.run(explore_site())
