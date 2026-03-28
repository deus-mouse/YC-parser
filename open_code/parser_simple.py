import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


@dataclass
class Master:
    id: int
    name: str = ""
    title: str = ""
    free_minutes: int = 0
    shortest_duration_min: int = 0
    available_days: int = 0
    slots_count: int = 0


class YClientsParser:
    def __init__(self, url: str, days_ahead: int = 30):
        match = re.match(r'https://n(\d+)\.yclients\.com/company/(\d+)', url)
        if not match:
            raise ValueError("Invalid URL format")
        
        self.form_id = int(match.group(1))
        self.company_id = int(match.group(2))
        self.days_ahead = days_ahead
    
    async def run(self, days_limit: int = 5) -> list[Master]:
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # First get masters list
            print("Loading masters...")
            page = await browser.new_page()
            
            responses = {}
            def on_response(response):
                if "platform.yclients" in response.url:
                    try:
                        data = response.json()
                        if data:
                            responses[response.url] = data
                    except:
                        pass
            
            page.on("response", on_response)
            
            await page.goto(
                f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=",
                wait_until="domcontentloaded"
            )
            await page.wait_for_timeout(12000)
            
            masters = await self._get_masters(page)
            print(f"Found {len(masters)} masters\n")
            
            # Get services from cached responses
            services_map = {}
            for url, data in responses.items():
                if "search-services" in url and isinstance(data, dict):
                    items = data.get("data", [])
                    if isinstance(items, list):
                        for item in items:
                            if item.get("type") == "booking_search_result_services":
                                attrs = item.get("attributes", {})
                                if attrs.get("is_bookable"):
                                    for record in items:
                                        if record.get("type") == "booking_search_result_staff":
                                            staff_id = int(record["id"])
                                            services_map[staff_id] = self._parse_services({url: data})
            
            await page.close()
            
            # Process each master
            for i, master in enumerate(masters):
                print(f"[{i+1}/{len(masters)}] {master.name} (ID: {master.id})")
                
                try:
                    # Get fresh data for this master
                    page = await browser.new_page()
                    responses = {}
                    
                    def on_response2(response):
                        if "platform.yclients" in response.url:
                            try:
                                data = response.json()
                                if data:
                                    responses[response.url] = data
                            except:
                                pass
                    
                    page.on("response", on_response2)
                    
                    await page.goto(
                        f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master.id}",
                        wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(12000)
                    
                    services = self._parse_services(responses)
                    if services:
                        master.shortest_duration_min = services[0]["duration"] // 60
                    
                    dates = self._parse_dates(responses)
                    master.available_days = len(dates[:days_limit])
                    
                    timeslots = self._parse_timeslots(responses)
                    master.slots_count = len(timeslots)
                    master.free_minutes = master.slots_count * master.shortest_duration_min
                    
                    print(f"    -> {master.shortest_duration_min}min, {master.available_days} days, {master.slots_count} slots, {master.free_minutes} min free")
                    
                    await page.close()
                    
                except Exception as e:
                    print(f"    -> Error: {e}")
                
                results.append(master)
                await asyncio.sleep(0.3)
            
            await browser.close()
        
        return results
    
    async def _get_masters(self, page) -> list[Master]:
        masters = []
        tiles = await page.query_selector_all("app-staff-tile.master-clickable")
        
        for tile in tiles:
            text = await tile.inner_text()
            name = text.split("\n")[0].strip()
            
            if name and name != "Любой специалист":
                onclick = await tile.get_attribute("onclick") or ""
                id_match = re.search(r'(\d+)', onclick)
                master_id = int(id_match.group(1)) if id_match else 0
                
                title_parts = text.split("\n")[1:3] if "\n" in text else []
                title = " ".join([p.strip() for p in title_parts if p.strip()])[:100]
                
                masters.append(Master(id=master_id, name=name, title=title))
        
        return masters
    
    def _parse_services(self, responses: dict) -> list[dict]:
        services = []
        for url, data in responses.items():
            if "search-services" in url and isinstance(data, dict):
                items = data.get("data", [])
                if isinstance(items, list):
                    for item in items:
                        if item.get("type") == "booking_search_result_services":
                            attrs = item.get("attributes", {})
                            if attrs.get("is_bookable"):
                                services.append({
                                    "id": item["id"],
                                    "duration": attrs.get("duration", 0),
                                    "price": attrs.get("price_min", 0)
                                })
        return sorted(services, key=lambda x: x["duration"])
    
    def _parse_dates(self, responses: dict) -> list[str]:
        dates = []
        for url, data in responses.items():
            if "search-dates" in url and isinstance(data, dict):
                items = data.get("data", [])
                if isinstance(items, list):
                    for item in items:
                        if item.get("type") == "booking_search_result_dates":
                            attrs = item.get("attributes", {})
                            if attrs.get("is_bookable"):
                                dates.append(attrs.get("date", ""))
        return dates
    
    def _parse_timeslots(self, responses: dict) -> list[dict]:
        slots = []
        for url, data in responses.items():
            if "search-timeslots" in url and isinstance(data, dict):
                items = data.get("data", [])
                if isinstance(items, list):
                    for item in items:
                        if item.get("type") == "booking_search_result_timeslots":
                            attrs = item.get("attributes", {})
                            if attrs.get("is_bookable"):
                                slots.append({
                                    "time": attrs.get("time", ""),
                                    "datetime": attrs.get("datetime", "")
                                })
        return slots


def print_results(masters: list[Master], output_file: str = None):
    sorted_masters = sorted(masters, key=lambda x: x.free_minutes, reverse=True)
    
    print("\n" + "="*70)
    print("RESULTS (sorted by free minutes)")
    print("="*70)
    
    for m in sorted_masters:
        print(f"\n{m.name}")
        print(f"  ID: {m.id}, Title: {m.title}")
        print(f"  Shortest: {m.shortest_duration_min} min, Days: {m.available_days}, Slots: {m.slots_count}")
        print(f"  Free minutes: {m.free_minutes}")
    
    output = [
        {
            "id": m.id,
            "name": m.name,
            "title": m.title,
            "shortest_duration_min": m.shortest_duration_min,
            "available_days": m.available_days,
            "total_slots": m.slots_count,
            "total_free_minutes": m.free_minutes
        }
        for m in sorted_masters
    ]
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
    else:
        print("\n" + "="*70)
        print("JSON Output:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    return sorted_masters


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="YC Masters Parser")
    parser.add_argument("url", help="URL of masters page")
    parser.add_argument("--days", "-d", type=int, default=30, help="Days ahead to scan")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Days to analyze per master")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    yc = YClientsParser(args.url, days_ahead=args.days)
    
    results = await yc.run(days_limit=args.limit)
    print_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
