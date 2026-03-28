import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class Master:
    id: int
    name: str
    title: str = ""
    free_minutes: int = 0
    shortest_service_duration: int = 0
    shortest_service_name: str = ""
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
        self.api_responses: dict = {}
    
    async def init(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
        async def capture_response(response):
            if "platform.yclients" in response.url:
                try:
                    data = await response.json()
                    self.api_responses[response.url] = data
                except:
                    pass
        
        self.page.on("response", capture_response)
    
    async def close(self):
        if self.browser:
            await self.browser.close()
    
    async def _load_masters_page(self):
        self.api_responses.clear()
        url = f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o="
        await self.page.goto(url, wait_until="networkidle")
        await self.page.wait_for_timeout(2000)
        
        masters = await self.page.query_selector_all("app-staff-tile.master-clickable")
        result = []
        
        for master in masters:
            text = await master.inner_text()
            name = text.split("\n")[0].strip()
            if name and name != "Любой специалист":
                onclick = await master.get_attribute("onclick") or ""
                id_match = re.search(r'(\d+)', onclick)
                master_id = int(id_match.group(1)) if id_match else 0
                
                title_parts = text.split("\n")[1:3] if "\n" in text else []
                title = " ".join([p.strip() for p in title_parts if p.strip()])[:100]
                
                result.append(Master(id=master_id, name=name, title=title))
        
        return result
    
    async def _analyze_single_master(self, master_id: int, days_limit: int) -> dict:
        self.api_responses.clear()
        url = f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o=m{master_id}"
        await self.page.goto(url, wait_until="networkidle")
        await self.page.wait_for_timeout(3000)
        
        services = self._get_services()
        if not services:
            return {"error": "No services found"}
        
        shortest = services[0]
        
        dates = self._get_available_dates()
        if not dates:
            return {
                "shortest_service": f"Service {shortest['id']}",
                "duration_min": shortest["duration"] // 60,
                "dates_found": 0,
                "slots_total": 0,
                "free_minutes": 0
            }
        
        total_slots = 0
        total_minutes = 0
        dates_analyzed = 0
        
        for date in dates[:days_limit]:
            await self.page.goto(url, wait_until="networkidle")
            await self.page.wait_for_timeout(2000)
            
            slots = self._get_timeslots()
            slot_count = len(slots)
            total_slots += slot_count
            total_minutes += slot_count * (shortest["duration"] // 60)
            dates_analyzed += 1
            
            await asyncio.sleep(0.2)
        
        return {
            "shortest_service": f"Service {shortest['id']}",
            "duration_min": shortest["duration"] // 60,
            "dates_found": len(dates),
            "dates_analyzed": dates_analyzed,
            "slots_total": total_slots,
            "free_minutes": total_minutes
        }
    
    def _get_services(self) -> list[dict]:
        services = []
        for url, data in self.api_responses.items():
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
    
    def _get_available_dates(self) -> list[str]:
        dates = []
        for url, data in self.api_responses.items():
            if "search-dates" in url and isinstance(data.get("data"), list):
                for item in data["data"]:
                    if item.get("type") == "booking_search_result_dates":
                        attrs = item.get("attributes", {})
                        if attrs.get("is_bookable"):
                            dates.append(attrs.get("date", ""))
        return dates
    
    def _get_timeslots(self) -> list[dict]:
        slots = []
        for url, data in self.api_responses.items():
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
        
        print("Loading masters list...")
        masters = await self._load_masters_page()
        print(f"Found {len(masters)} masters")
        
        results = []
        
        for i, master in enumerate(masters):
            print(f"\n[{i+1}/{len(masters)}] Analyzing {master.name}...")
            
            try:
                analysis = await self._analyze_single_master(master.id, days_limit)
                
                master.shortest_service_name = analysis.get("shortest_service", "")
                master.shortest_service_duration = analysis.get("duration_min", 0) * 60
                master.available_days = analysis.get("dates_analyzed", 0)
                master.slots_count = analysis.get("slots_total", 0)
                master.free_minutes = analysis.get("free_minutes", 0)
                
                print(f"  -> Duration: {master.shortest_service_duration//60} min, Days: {master.available_days}, Slots: {master.slots_count}, Minutes: {master.free_minutes}")
                results.append(master)
                
            except Exception as e:
                print(f"  -> Error: {e}")
            
            await asyncio.sleep(0.3)
        
        return results
    
    def print_results(self, masters: list[Master]):
        print("\n" + "="*70)
        print("FINAL RESULTS - Masters sorted by free minutes")
        print("="*70)
        
        sorted_masters = sorted(masters, key=lambda x: x.free_minutes, reverse=True)
        
        for m in sorted_masters:
            print(f"\n{m.name}")
            print(f"  ID: {m.id}")
            print(f"  Title: {m.title}")
            print(f"  Shortest service: {m.shortest_service_name} ({m.shortest_service_duration//60} min)")
            print(f"  Available days: {m.available_days}")
            print(f"  Total slots: {m.slots_count}")
            print(f"  Total free minutes: {m.free_minutes}")
        
        return sorted_masters
    
    def to_json(self, masters: list[Master]) -> list[dict]:
        return [
            {
                "id": m.id,
                "name": m.name,
                "title": m.title,
                "shortest_service": m.shortest_service_name,
                "shortest_service_duration_min": m.shortest_service_duration // 60,
                "available_days": m.available_days,
                "total_slots": m.slots_count,
                "total_free_minutes": m.free_minutes
            }
            for m in masters
        ]


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="YC Parser")
    parser.add_argument("url", help="URL of the masters page")
    parser.add_argument("--days", "-d", type=int, default=30, help="Days ahead to scan (default: 30)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Days to analyze per master (default: 10)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    yc_parser = YClientsParser(args.url, days_ahead=args.days)
    
    try:
        results = await yc_parser.parse(days_limit=args.limit)
        sorted_results = yc_parser.print_results(results)
        
        output = yc_parser.to_json(sorted_results)
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {args.output}")
        else:
            print("\n" + "="*70)
            print("JSON Output:")
            print("="*70)
            print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        await yc_parser.close()


if __name__ == "__main__":
    asyncio.run(main())
