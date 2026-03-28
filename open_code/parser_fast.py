import asyncio
import json
import re
import httpx
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta


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
    API_URL = "https://platform.yclients.com/api/v1/b2c/booking"
    
    def __init__(self, url: str, days_ahead: int = 30):
        match = re.match(r'https://n(\d+)\.yclients\.com/company/(\d+)', url)
        if not match:
            raise ValueError("Invalid URL format")
        
        self.form_id = int(match.group(1))
        self.company_id = int(match.group(2))
        self.days_ahead = days_ahead
        
        self.client: Optional[httpx.AsyncClient] = None
        self.token: str = ""
        self.cookies: dict = {}
    
    async def init(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    async def close(self):
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Referer": f"https://n{self.form_id}.yclients.com/",
            "Accept-Language": "ru-RU",
            "X-Yclients-Application-Platform": "angular-18.2.13",
            "X-Yclients-Application-Name": "client.booking",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    
    async def _api_request(self, endpoint: str, data: dict) -> dict:
        if not self.client:
            await self.init()
        
        url = f"{self.API_URL}/{endpoint}"
        headers = self._get_headers()
        
        response = await self.client.post(url, json=data, headers=headers, cookies=self.cookies)
        
        if response.status_code == 401:
            raise Exception("Unauthorized - need valid token")
        
        if response.status_code == 422:
            raise Exception(f"Bad request - {response.text[:200]}")
        
        response.raise_for_status()
        return response.json()
    
    async def get_token_and_cookies(self):
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            captured = {}
            
            async def capture_request(request):
                if "platform.yclients" in request.url and "search" in request.url:
                    captured["token"] = request.headers.get("authorization", "")
            
            page.on("request", capture_request)
            
            url = f"https://n{self.form_id}.yclients.com/company/{self.company_id}/personal/select-master?o="
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            cookies = await page.context.cookies()
            self.cookies = {c["name"]: c["value"] for c in cookies}
            
            masters = await page.query_selector_all("app-staff-tile.master-clickable")
            if masters:
                await masters[1].click()
                await page.wait_for_timeout(2000)
            
            await browser.close()
            
            if captured.get("token"):
                self.token = captured["token"].replace("Bearer ", "")
            else:
                self.token = "gtcwf654agufy25gsadh"
    
    async def get_masters(self) -> list[Master]:
        data = {
            "context": {"location_id": self.company_id},
            "filter": {
                "datetime": None,
                "records": [{"staff_id": None, "attendance_service_items": []}]
            }
        }
        
        result = await self._api_request("availability/search-staff", data)
        
        masters = []
        staff_data = result.get("data", [])
        
        for item in staff_data:
            if item.get("type") == "booking_search_result_staff":
                attrs = item.get("attributes", {})
                if attrs.get("is_bookable"):
                    master_id = int(item["id"])
                    masters.append(Master(id=master_id, name=f"Master {master_id}"))
        
        return masters
    
    async def get_services(self, master_id: int) -> list[dict]:
        data = {
            "context": {"location_id": self.company_id},
            "filter": {
                "records": [{"staff_id": master_id, "attendance_service_items": []}]
            }
        }
        
        result = await self._api_request("availability/search-services", data)
        
        services = []
        for item in result.get("data", []):
            if item.get("type") == "booking_search_result_services":
                attrs = item.get("attributes", {})
                if attrs.get("is_bookable"):
                    services.append({
                        "id": item["id"],
                        "duration": attrs.get("duration", 0),
                        "price": attrs.get("price_min", 0)
                    })
        
        return sorted(services, key=lambda x: x["duration"])
    
    async def get_available_dates(self, master_id: int, service_ids: list[str]) -> list[str]:
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=self.days_ahead)).strftime("%Y-%m-%d")
        
        data = {
            "context": {"location_id": self.company_id},
            "filter": {
                "date_from": today,
                "date_to": future,
                "records": [
                    {"staff_id": master_id, "attendance_service_items": service_ids}
                ]
            }
        }
        
        result = await self._api_request("availability/search-dates", data)
        
        dates = []
        for item in result.get("data", []):
            if item.get("type") == "booking_search_result_dates":
                attrs = item.get("attributes", {})
                if attrs.get("is_bookable"):
                    dates.append(attrs.get("date", ""))
        
        return dates
    
    async def get_timeslots(self, master_id: int, service_ids: list[str], date: str) -> list[dict]:
        data = {
            "context": {"location_id": self.company_id},
            "filter": {
                "date": date,
                "records": [
                    {"staff_id": master_id, "attendance_service_items": service_ids}
                ]
            }
        }
        
        result = await self._api_request("availability/search-timeslots", data)
        
        slots = []
        for item in result.get("data", []):
            if item.get("type") == "booking_search_result_timeslots":
                attrs = item.get("attributes", {})
                if attrs.get("is_bookable"):
                    slots.append({
                        "time": attrs.get("time", ""),
                        "datetime": attrs.get("datetime", "")
                    })
        
        return slots
    
    async def analyze_master(self, master: Master, days_limit: int = 10) -> Master:
        services = await self.get_services(master.id)
        
        if not services:
            return master
        
        shortest = services[0]
        master.shortest_service_duration = shortest["duration"]
        master.shortest_service_name = f"Service {shortest['id']} ({shortest['duration']//60} min)"
        
        service_ids = [s["id"] for s in services[:5]]
        available_dates = await self.get_available_dates(master.id, service_ids)
        
        total_slots = 0
        total_minutes = 0
        dates_analyzed = 0
        
        for date in available_dates[:days_limit]:
            slots = await self.get_timeslots(master.id, service_ids, date)
            slot_count = len(slots)
            total_slots += slot_count
            total_minutes += slot_count * (shortest["duration"] // 60)
            dates_analyzed += 1
            await asyncio.sleep(0.1)
        
        master.free_minutes = total_minutes
        master.available_days = dates_analyzed
        master.slots_count = total_slots
        
        return master
    
    async def parse(self, days_limit: int = 10) -> list[Master]:
        print("Getting auth token...")
        await self.get_token_and_cookies()
        
        print("Fetching masters list...")
        masters = await self.get_masters()
        print(f"Found {len(masters)} masters")
        
        results = []
        
        for i, master in enumerate(masters):
            print(f"\n[{i+1}/{len(masters)}] Analyzing master {master.id}...")
            
            try:
                master = await self.analyze_master(master, days_limit)
                results.append(master)
                print(f"  -> Duration: {master.shortest_service_duration//60} min, Days: {master.available_days}, Slots: {master.slots_count}, Minutes: {master.free_minutes}")
            except Exception as e:
                print(f"  -> Error: {e}")
            
            await asyncio.sleep(0.2)
        
        return results
    
    def print_results(self, masters: list[Master]):
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        
        sorted_masters = sorted(masters, key=lambda x: x.free_minutes, reverse=True)
        
        for m in sorted_masters:
            print(f"\n{m.name}")
            print(f"  ID: {m.id}")
            print(f"  Shortest: {m.shortest_service_name} ({m.shortest_service_duration//60} min)")
            print(f"  Days: {m.available_days}, Slots: {m.slots_count}, Minutes: {m.free_minutes}")
        
        return sorted_masters
    
    def to_json(self, masters: list[Master]) -> list[dict]:
        return [
            {
                "id": m.id,
                "name": m.name,
                "shortest_service": m.shortest_service_name,
                "duration_min": m.shortest_service_duration // 60,
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
    parser.add_argument("--days", "-d", type=int, default=30, help="Days ahead to scan")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Days to analyze per master")
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
            print(f"\nSaved to {args.output}")
        else:
            print("\n" + "="*70)
            print("JSON Output:")
            print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        await yc_parser.close()


if __name__ == "__main__":
    asyncio.run(main())
