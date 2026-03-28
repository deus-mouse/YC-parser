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
            context = await browser.new_context()
            page = await context.new_page()
            
            print("Loading masters page...")
            await page.goto(
                f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=",
                wait_until="domcontentloaded"
            )
            await page.wait_for_timeout(10000)
            
            masters = await self._get_masters(page)
            print(f"Found {len(masters)} masters\n")
            
            for i, master in enumerate(masters):
                print(f"[{i+1}/{len(masters)}] {master.name}")
                
                try:
                    analysis = await self._analyze_master(page, master.id, days_limit)
                    master.shortest_duration_min = analysis["duration_min"]
                    master.available_days = analysis["days"]
                    master.slots_count = analysis["slots"]
                    master.free_minutes = analysis["minutes"]
                    print(f"    -> {master.shortest_duration_min}min service, {master.available_days} days, {master.slots_count} slots, {master.free_minutes} min free")
                except Exception as e:
                    print(f"    -> Error: {e}")
                
                results.append(master)
                await asyncio.sleep(0.5)
            
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
    
    async def _analyze_master(self, page, master_id: int, days_limit: int) -> dict:
        api_responses = {}
        
        def capture_response(response):
            if "platform.yclients" in response.url:
                try:
                    data = response.json()
                    if data:
                        api_responses[response.url] = data
                except:
                    pass
        
        page.on("response", capture_response)
        
        await page.goto(
            f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master_id}",
            wait_until="domcontentloaded"
        )
        await page.wait_for_timeout(10000)
        
        page.remove_listener("response", capture_response)
        
        services = self._parse_services(api_responses)
        if not services:
            return {"duration_min": 0, "days": 0, "slots": 0, "minutes": 0}
        
        duration_sec = services[0]["duration"]
        duration_min = duration_sec // 60
        
        dates = self._parse_dates(api_responses)
        if not dates:
            return {"duration_min": duration_min, "days": 0, "slots": 0, "minutes": 0}
        
        total_slots = 0
        for date in dates[:days_limit]:
            api_responses.clear()
            page.on("response", capture_response)
            
            await page.goto(
                f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master_id}",
                wait_until="domcontentloaded"
            )
            await page.wait_for_timeout(8000)
            page.remove_listener("response", capture_response)
            
            slots = self._parse_timeslots(api_responses)
            total_slots += len(slots)
            
            await asyncio.sleep(0.3)
        
        return {
            "duration_min": duration_min,
            "days": min(len(dates), days_limit),
            "slots": total_slots,
            "minutes": total_slots * duration_min
        }
    
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
    
    sorted_results = sorted(results, key=lambda x: x.free_minutes, reverse=True)
    
    print("\n" + "="*70)
    print("RESULTS (sorted by free minutes)")
    print("="*70)
    
    for m in sorted_results:
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
        for m in sorted_results
    ]
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.output}")
    else:
        print("\n" + "="*70)
        print("JSON Output:")
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
