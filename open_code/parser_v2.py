import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, Page


@dataclass
class Master:
    id: int
    name: str = ""
    title: str = ""
    free_minutes: int = 0
    shortest_duration_sec: int = 0
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
        
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._response_handler: Optional[Callable] = None
    
    async def init(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
    
    async def close(self):
        if self.browser:
            await self.browser.close()
    
    async def get_masters(self) -> list[Master]:
        await self.page.goto(
            f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=",
            wait_until="networkidle"
        )
        await self.page.wait_for_timeout(2000)
        
        masters = []
        tiles = await self.page.query_selector_all("app-staff-tile.master-clickable")
        
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
    
    async def analyze_master(self, master: Master, days_limit: int = 10) -> Master:
        api_responses = {}
        
        async def capture_response(response):
            if "platform.yclients" in response.url:
                try:
                    data = await response.json()
                    api_responses[response.url] = data
                except:
                    pass
        
        self.page.on("response", capture_response)
        
        await self.page.goto(
            f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master.id}",
            wait_until="networkidle"
        )
        await self.page.wait_for_timeout(4000)
        
        services = self._parse_services(api_responses)
        if not services:
            self.page.remove_listener("response", capture_response)
            return master
        
        shortest = services[0]
        master.shortest_duration_sec = shortest["duration"]
        
        dates = self._parse_dates(api_responses)
        self.page.remove_listener("response", capture_response)
        
        if not dates:
            return master
        
        total_slots = 0
        total_minutes = 0
        
        for date in dates[:days_limit]:
            api_responses.clear()
            
            self.page.on("response", capture_response)
            await self.page.goto(
                f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master.id}",
                wait_until="networkidle"
            )
            await self.page.wait_for_timeout(2500)
            self.page.remove_listener("response", capture_response)
            
            slots = self._parse_timeslots(api_responses)
            slot_count = len(slots)
            total_slots += slot_count
            total_minutes += slot_count * (shortest["duration"] // 60)
            
            await asyncio.sleep(0.15)
        
        master.free_minutes = total_minutes
        master.available_days = min(len(dates), days_limit)
        master.slots_count = total_slots
        
        return master
    
    def _parse_services(self, responses: dict) -> list[dict]:
        services = []
        for url, data in responses.items():
            if "search-services" in url and isinstance(data.get("data"), list):
                for item in data["data"]:
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
            if "search-dates" in url and isinstance(data.get("data"), list):
                for item in data["data"]:
                    if item.get("type") == "booking_search_result_dates":
                        attrs = item.get("attributes", {})
                        if attrs.get("is_bookable"):
                            dates.append(attrs.get("date", ""))
        return dates
    
    def _parse_timeslots(self, responses: dict) -> list[dict]:
        slots = []
        for url, data in responses.items():
            if "search-timeslots" in url and isinstance(data.get("data"), list):
                for item in data["data"]:
                    if item.get("type") == "booking_search_result_timeslots":
                        attrs = item.get("attributes", {})
                        if attrs.get("is_bookable"):
                            slots.append({
                                "time": attrs.get("time", ""),
                                "datetime": attrs.get("datetime", "")
                            })
        return slots
    
    async def parse(self, days_limit: int = 10) -> list[Master]:
        await self.init()
        
        print("Loading masters...")
        masters = await self.get_masters()
        print(f"Found {len(masters)} masters\n")
        
        results = []
        
        for i, master in enumerate(masters):
            print(f"[{i+1}/{len(masters)}] {master.name} (ID: {master.id})")
            
            try:
                master = await self.analyze_master(master, days_limit)
                results.append(master)
                dur = master.shortest_duration_sec // 60
                print(f"    -> {dur}min service, {master.available_days} days, {master.slots_count} slots, {master.free_minutes} min free")
            except Exception as e:
                print(f"    -> Error: {e}")
            
            await asyncio.sleep(0.2)
        
        return results
    
    def print_results(self, masters: list[Master]):
        sorted_masters = sorted(masters, key=lambda x: x.free_minutes, reverse=True)
        
        print("\n" + "="*70)
        print("RESULTS (sorted by free minutes)")
        print("="*70)
        
        for m in sorted_masters:
            print(f"{m.name}")
            print(f"  ID: {m.id}, Title: {m.title}")
            print(f"  Shortest: {m.shortest_duration_sec//60} min, Days: {m.available_days}, Slots: {m.slots_count}")
            print(f"  Free minutes: {m.free_minutes}\n")
        
        return sorted_masters
    
    def to_json(self, masters: list[Master]) -> list[dict]:
        return [
            {
                "id": m.id,
                "name": m.name,
                "title": m.title,
                "shortest_duration_min": m.shortest_duration_sec // 60,
                "available_days": m.available_days,
                "total_slots": m.slots_count,
                "total_free_minutes": m.free_minutes
            }
            for m in masters
        ]


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="YC Masters Parser")
    parser.add_argument("url", help="URL of masters page")
    parser.add_argument("--days", "-d", type=int, default=30, help="Days ahead to scan")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Days to analyze per master")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    yc = YClientsParser(args.url, days_ahead=args.days)
    
    try:
        results = await yc.parse(days_limit=args.limit)
        sorted_results = yc.print_results(results)
        
        output = yc.to_json(sorted_results)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"\nSaved to {args.output}")
        else:
            print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        await yc.close()


if __name__ == "__main__":
    asyncio.run(main())
