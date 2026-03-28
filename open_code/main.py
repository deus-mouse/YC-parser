#!/usr/bin/env python3
"""
YC Masters Parser - Parse available slots from YCLIENTS booking system

Usage:
    python main.py "https://n625088.yclients.com/company/266762/personal/select-master?o="
    python main.py "URL" --days 30 --limit 10 --output results.json
"""

import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


@dataclass
class Master:
    id: int
    name: str = ""
    title: str = ""
    shortest_duration_min: int = 0
    available_days: int = 0
    total_slots: int = 0
    total_free_minutes: int = 0


class YClientsParser:
    """Parser for YCLIENTS booking system"""
    
    def __init__(self, url: str, days_ahead: int = 30):
        match = re.match(r'https://n(\d+)\.yclients\.com/company/(\d+)', url)
        if not match:
            raise ValueError("Invalid URL format")
        
        self.form_id = int(match.group(1))
        self.company_id = int(match.group(2))
        self.days_ahead = days_ahead
    
    async def parse(self, days_limit: int = 5, analyze_slots: bool = False) -> list[Master]:
        """Parse masters and their availability"""
        masters = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("Loading page...")
            responses = {}
            
            async def handler(response):
                if "platform.yclients" in response.url:
                    responses[response.url] = response
            
            page.on("response", handler)
            
            await page.goto(
                f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=",
                wait_until="domcontentloaded"
            )
            await page.wait_for_timeout(15000)
            
            # Get master IDs from API
            staff_ids = await self._get_staff_ids(responses)
            print(f"Found {len(staff_ids)} staff IDs")
            
            # Get master names from page
            tiles = await page.query_selector_all("app-staff-tile.master-clickable")
            print(f"Found {len(tiles)} master tiles\n")
            
            for i, tile in enumerate(tiles):
                text = await tile.inner_text()
                name = text.split("\n")[0].strip()
                
                if name and name != "Любой специалист":
                    title_parts = text.split("\n")[1:3] if "\n" in text else []
                    title = " ".join([p.strip() for p in title_parts if p.strip()])[:100]
                    
                    staff_id = staff_ids[i - 1] if i > 0 and i - 1 < len(staff_ids) else 0
                    masters.append(Master(id=staff_id, name=name, title=title))
            
            print(f"Parsed {len(masters)} masters\n")
            
            # Analyze each master
            for i, master in enumerate(masters):
                print(f"[{i+1}] {master.name} (ID: {master.id})")
                
                responses.clear()
                
                await page.goto(
                    f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master.id}",
                    wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(15000)
                
                services = await self._get_services(responses)
                dates = await self._get_dates(responses)
                
                if services:
                    master.shortest_duration_min = services[0]["duration"] // 60
                
                master.available_days = len(dates[:days_limit])
                
                if analyze_slots:
                    slots = await self._get_timeslots(responses)
                    master.total_slots = len(slots)
                    master.total_free_minutes = master.total_slots * master.shortest_duration_min
                
                print(f"    Services: {len(services)}, Dates: {len(dates)}")
                print(f"    Shortest: {master.shortest_duration_min} min, Days: {master.available_days}")
                
                await asyncio.sleep(1)
            
            await browser.close()
        
        return masters
    
    async def _get_staff_ids(self, responses: dict) -> list[int]:
        ids = []
        for response in responses.values():
            try:
                if "search-staff" in response.url:
                    data = await response.json()
                    if isinstance(data, dict):
                        for item in data.get("data", []):
                            if item.get("type") == "booking_search_result_staff":
                                attrs = item.get("attributes", {})
                                if attrs.get("is_bookable"):
                                    ids.append(int(item["id"]))
            except:
                pass
        return ids
    
    async def _get_services(self, responses: dict) -> list[dict]:
        services = []
        for response in responses.values():
            try:
                if "search-services" in response.url:
                    data = await response.json()
                    if isinstance(data, dict):
                        for item in data.get("data", []):
                            if item.get("type") == "booking_search_result_services":
                                attrs = item.get("attributes", {})
                                if attrs.get("is_bookable"):
                                    services.append({
                                        "id": item["id"],
                                        "duration": attrs.get("duration", 0),
                                    })
            except:
                pass
        return sorted(services, key=lambda x: x["duration"])
    
    async def _get_dates(self, responses: dict) -> list[str]:
        dates = []
        for response in responses.values():
            try:
                if "search-dates" in response.url:
                    data = await response.json()
                    if isinstance(data, dict):
                        for item in data.get("data", []):
                            if item.get("type") == "booking_search_result_dates":
                                attrs = item.get("attributes", {})
                                if attrs.get("is_bookable"):
                                    dates.append(attrs.get("date", ""))
            except:
                pass
        return dates
    
    async def _get_timeslots(self, responses: dict) -> list[dict]:
        slots = []
        for response in responses.values():
            try:
                if "search-timeslots" in response.url:
                    data = await response.json()
                    if isinstance(data, dict):
                        for item in data.get("data", []):
                            if item.get("type") == "booking_search_result_timeslots":
                                attrs = item.get("attributes", {})
                                if attrs.get("is_bookable"):
                                    slots.append({
                                        "time": attrs.get("time", ""),
                                    })
            except:
                pass
        return slots


def print_results(masters: list[Master], output_file: str = None):
    """Print and optionally save results"""
    sorted_masters = sorted(masters, key=lambda x: x.total_free_minutes, reverse=True)
    
    print("\n" + "="*70)
    print("MASTERS WITH AVAILABILITY")
    print("="*70)
    
    for m in sorted_masters:
        print(f"\n{m.name}")
        print(f"  ID: {m.id}")
        print(f"  Title: {m.title}")
        print(f"  Shortest service: {m.shortest_duration_min} min")
        print(f"  Available days: {m.available_days}")
        print(f"  Total slots: {m.total_slots}")
        print(f"  Total free minutes: {m.total_free_minutes}")
    
    output = [asdict(m) for m in sorted_masters]
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
    
    return sorted_masters


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YC Masters Parser - Parse available slots from YCLIENTS booking system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py "https://n625088.yclients.com/company/266762/personal/select-master?o="
    python main.py "URL" --days 30 --limit 10
    python main.py "URL" --output results.json
        """
    )
    parser.add_argument("url", help="URL of the masters page")
    parser.add_argument("--days", "-d", type=int, default=30, help="Days ahead to scan (default: 30)")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Days to analyze per master (default: 5)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--slots", "-s", action="store_true", help="Analyze time slots (slower)")
    
    args = parser.parse_args()
    
    print(f"YC Parser - Scanning {args.days} days ahead\n")
    
    yc = YClientsParser(args.url, days_ahead=args.days)
    results = await yc.parse(days_limit=args.limit, analyze_slots=args.slots)
    
    print_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
