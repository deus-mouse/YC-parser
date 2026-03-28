"""
Парсер онлайн-записи YCLIENTS.

Сценарий:
1. Открывает страницу выбора мастера.
2. Для каждого мастера выбирает самую короткую услугу.
3. На странице календаря считает число свободных слотов на заданную глубину.
4. Возвращает сумму свободных минут по мастеру.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import urlparse

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


MASTER_NAME_SELECTOR = ".name"
CONTINUE_BUTTON_SELECTOR = '[data-locator="continue_btn"]'
SERVICE_ITEM_SELECTOR = '[data-locator^="service_item_"]'
SERVICE_DURATION_SELECTOR = '[data-locator="service_seance_length"]'
WORKING_DAY_SELECTOR = '[data-locator="available_day"]'
NON_WORKING_DAY_SELECTOR = '[data-locator="unavailable_day"]'
TIMESLOT_SELECTOR = '[data-locator="timeslot"]'
CALENDAR_ICON_BUTTON_SELECTOR = '[data-locator="y-core-icon-button"]'
CALENDAR_TEXT_SELECTOR = '[data-locator="y-core-text"]'
AVAILABILITY_API_PATH = "/api/v1/b2c/booking/availability"

RUSSIAN_MONTHS = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
}


@dataclass
class DayAvailability:
    date: str
    slots: int
    free_minutes: int


@dataclass
class MasterAvailability:
    name: str
    shortest_service_name: str
    shortest_service_duration_min: int
    total_slots: int
    total_free_minutes: int
    days_with_slots: int
    scanned_days: list[DayAvailability] = field(default_factory=list)


def parse_duration_to_minutes(raw_text: str) -> int:
    text = raw_text.replace("\xa0", " ").strip()
    match = re.match(r"^(?:(\d+)\s*ч)?\s*(?:(\d+)\s*мин)?$", text)
    if not match:
        raise ValueError(f"Не удалось распарсить длительность: {raw_text!r}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    total_minutes = hours * 60 + minutes
    if total_minutes <= 0:
        raise ValueError(f"Длительность равна нулю: {raw_text!r}")
    return total_minutes


class YClientsParser:
    def __init__(
        self,
        masters_url: str,
        days_ahead: int = 30,
        headless: bool = True,
        pause_seconds: float = 0.35,
        timeout_ms: int = 20000,
    ) -> None:
        self.masters_url = masters_url
        self.days_ahead = days_ahead
        self.headless = headless
        self.pause_seconds = pause_seconds
        self.timeout_ms = timeout_ms
        self.location_id = self._extract_location_id(masters_url)

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._availability_headers: dict[str, str] = {}

    def __enter__(self) -> "YClientsParser":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        self.page.on("request", self._capture_availability_headers)

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _capture_availability_headers(self, request) -> None:
        if AVAILABILITY_API_PATH not in request.url:
            return
        headers = request.headers
        wanted = [
            "authorization",
            "accept-language",
            "x-yclients-application-action",
            "x-yclients-application-platform",
            "x-yclients-application-name",
            "x-yclients-application-version",
            "x-app-signature",
            "accept",
            "user-agent",
            "referer",
        ]
        for key in wanted:
            value = headers.get(key)
            if value:
                self._availability_headers[key] = value

    def parse(self, master_limit: Optional[int] = None) -> list[MasterAvailability]:
        self._goto_masters_page()
        master_names = self._collect_master_names()
        if master_limit is not None:
            master_names = master_names[:master_limit]

        results: list[MasterAvailability] = []
        total = len(master_names)

        for index, master_name in enumerate(master_names, start=1):
            print(f"[{index}/{total}] {master_name}", file=sys.stderr)
            result = self._analyze_master(master_name)
            results.append(result)
            print(
                f"    shortest={result.shortest_service_duration_min} мин, "
                f"slots={result.total_slots}, free={result.total_free_minutes} мин",
                file=sys.stderr,
            )

        return results

    @staticmethod
    def _extract_location_id(url: str) -> int:
        match = re.search(r"/company/(\d+)", url)
        if not match:
            raise ValueError(f"Не удалось извлечь location_id из URL: {url}")
        return int(match.group(1))

    def _goto_masters_page(self) -> None:
        assert self.page is not None
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                self.page.goto(self.masters_url, wait_until="domcontentloaded")
                self.page.locator(MASTER_NAME_SELECTOR).first.wait_for(
                    state="visible",
                    timeout=self.timeout_ms,
                )
                self._pause(1.0)
                return
            except PlaywrightTimeoutError as exc:
                last_error = exc
                self._pause(1.5 + attempt)
        raise RuntimeError(
            f"Не удалось открыть страницу мастеров после 3 попыток: {self.masters_url}"
        ) from last_error

    def _pause(self, seconds: Optional[float] = None) -> None:
        time.sleep(self.pause_seconds if seconds is None else seconds)

    def _collect_master_names(self) -> list[str]:
        assert self.page is not None
        names: list[str] = []
        masters = self.page.locator(MASTER_NAME_SELECTOR)
        count = masters.count()
        for index in range(count):
            name = masters.nth(index).inner_text().strip()
            if not name or name == "Любой специалист":
                continue
            names.append(name)
        return names

    def _select_master(self, master_name: str) -> None:
        assert self.page is not None
        masters = self.page.locator(MASTER_NAME_SELECTOR)
        count = masters.count()
        for index in range(count):
            locator = masters.nth(index)
            current_name = locator.inner_text().strip()
            if current_name != master_name:
                continue
            locator.scroll_into_view_if_needed()
            locator.click()
            self._pause()
            return
        raise RuntimeError(f"Не удалось найти мастера: {master_name}")

    def _current_staff_id(self) -> int:
        assert self.page is not None
        match = re.search(r"[?&]o=m(\d+)", self.page.url)
        if not match:
            raise RuntimeError(f"Не удалось извлечь staff_id из URL: {self.page.url}")
        return int(match.group(1))

    def _click_continue(self) -> None:
        assert self.page is not None
        button = self.page.locator(CONTINUE_BUTTON_SELECTOR).first
        button.wait_for()
        button.click()
        self._pause(0.8)

    def _wait_for_url_part(self, url_part: str, timeout_ms: Optional[int] = None) -> None:
        assert self.page is not None
        try:
            self.page.wait_for_url(f"**{url_part}**", timeout=timeout_ms or self.timeout_ms)
        except PlaywrightTimeoutError:
            pass

    def _wait_for_any_selector(
        self,
        selectors: list[str],
        timeout_ms: Optional[int] = None,
    ) -> None:
        assert self.page is not None
        deadline = time.time() + ((timeout_ms or self.timeout_ms) / 1000)
        while time.time() < deadline:
            for selector in selectors:
                if self.page.locator(selector).count() > 0:
                    return
            self._pause(0.25)
        joined = ", ".join(selectors)
        raise RuntimeError(f"Не дождались селекторов: {joined}. Текущий URL: {self.page.url}")

    def _expand_all_service_groups(self) -> None:
        assert self.page is not None
        collapse_items = self.page.locator("div.y-core-collapse-item")
        for _ in range(20):
            clicked_any = False
            count = collapse_items.count()
            for index in range(count):
                item = collapse_items.nth(index)
                content = item.locator("div.y-core-collapse-item__content")
                if content.count() == 0:
                    continue
                style = (content.first.get_attribute("style") or "").replace(" ", "")
                is_collapsed = "height:0" in style
                if not is_collapsed:
                    continue
                activator = item.locator(
                    "div[data-activator], div.y-core-collapse-item__activator"
                ).first
                if activator.count() == 0:
                    continue
                activator.scroll_into_view_if_needed()
                activator.click()
                self._pause(0.2)
                clicked_any = True
            if not clicked_any:
                break

    def _select_shortest_service(self) -> tuple[str, int, int]:
        assert self.page is not None
        self._expand_all_service_groups()

        service_items = self.page.locator(SERVICE_ITEM_SELECTOR)
        durations = self.page.locator(SERVICE_DURATION_SELECTOR)

        item_count = service_items.count()
        duration_count = durations.count()
        if item_count == 0 or duration_count == 0:
            raise RuntimeError(
                "На странице услуг ничего не найдено. "
                f"URL: {self.page.url}, service_items={item_count}, durations={duration_count}"
            )

        count = min(item_count, duration_count)
        shortest_index: Optional[int] = None
        shortest_minutes: Optional[int] = None
        shortest_name = ""
        shortest_service_id: Optional[int] = None

        for index in range(count):
            duration_text = durations.nth(index).inner_text()
            try:
                duration_minutes = parse_duration_to_minutes(duration_text)
            except ValueError:
                continue
            if shortest_minutes is None or duration_minutes < shortest_minutes:
                shortest_minutes = duration_minutes
                shortest_index = index
                item = service_items.nth(index)
                item_text = item.inner_text().strip()
                shortest_name = item_text.splitlines()[0].strip() if item_text else ""
                locator_value = item.get_attribute("data-locator") or ""
                id_match = re.search(r"service_item_(\d+)", locator_value)
                if id_match:
                    shortest_service_id = int(id_match.group(1))

        if shortest_index is None or shortest_minutes is None or shortest_service_id is None:
            raise RuntimeError("Не удалось определить самую короткую услугу.")

        item = service_items.nth(shortest_index)
        item.scroll_into_view_if_needed()
        item.click()
        self._pause(0.5)

        return shortest_name, shortest_minutes, shortest_service_id

    def _api_base_url(self) -> str:
        parsed = urlparse(self.masters_url)
        return f"{parsed.scheme}://platform.yclients.com{AVAILABILITY_API_PATH}"

    def _post_availability(self, endpoint: str, payload: dict) -> dict:
        assert self._context is not None
        headers = dict(self._availability_headers)
        headers["content-type"] = "application/json"
        if "referer" not in headers:
            parsed = urlparse(self.masters_url)
            headers["referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        last_error: Optional[Exception] = None
        for attempt in range(8):
            try:
                response = self._context.request.post(
                    f"{self._api_base_url()}/{endpoint}",
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=self.timeout_ms,
                )
                if not response.ok:
                    raise RuntimeError(
                        f"API {endpoint} вернул статус {response.status}: {response.text()[:500]}"
                    )
                return response.json()
            except (PlaywrightError, RuntimeError) as exc:
                last_error = exc
                self._pause(min(2.0 + attempt * 1.5, 12.0))
        raise RuntimeError(f"API {endpoint} не ответил после 8 попыток") from last_error

    def _fetch_bookable_dates(
        self,
        staff_id: int,
        service_id: int,
        date_from: date,
        date_to: date,
    ) -> list[date]:
        payload = {
            "context": {"location_id": self.location_id},
            "filter": {
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "records": [
                    {
                        "staff_id": staff_id,
                        "attendance_service_items": [
                            {"type": "service", "id": service_id},
                        ],
                    }
                ],
            },
        }
        data = self._post_availability("search-dates", payload)
        result: list[date] = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            if not attrs.get("is_bookable"):
                continue
            raw_date = attrs.get("date")
            if not raw_date:
                continue
            result.append(datetime.strptime(raw_date, "%Y-%m-%d").date())
        return sorted(result)

    def _fetch_timeslot_count(self, staff_id: int, service_id: int, target_date: date) -> int:
        payload = {
            "context": {"location_id": self.location_id},
            "filter": {
                "date": target_date.isoformat(),
                "records": [
                    {
                        "staff_id": staff_id,
                        "attendance_service_items": [
                            {"type": "service", "id": service_id},
                        ],
                    }
                ],
            },
        }
        data = self._post_availability("search-timeslots", payload)
        slot_count = 0
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            if attrs.get("is_bookable"):
                slot_count += 1
        return slot_count

    def _visible_calendar_days(self) -> list[tuple[date, str]]:
        assert self.page is not None
        calendar_root = self._calendar_root()
        result: list[tuple[date, str]] = []
        for selector in (WORKING_DAY_SELECTOR, NON_WORKING_DAY_SELECTOR):
            locator = calendar_root.locator(selector)
            count = locator.count()
            for index in range(count):
                element = locator.nth(index)
                raw_date = element.get_attribute("data-locator-date")
                css_class = element.get_attribute("class") or ""
                if not raw_date:
                    continue
                if "out-of-month" in css_class:
                    continue
                try:
                    parsed = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
                result.append((parsed, selector))
        result.sort(key=lambda item: item[0])
        return result

    def _calendar_root(self):
        assert self.page is not None
        calendar = self.page.locator('[data-locator="y-core-calendar"]')
        if calendar.count() > 0:
            return calendar.first
        return self.page.locator("body").first

    def _count_slots_for_day(self, day_value: date, service_duration_min: int) -> DayAvailability:
        assert self.page is not None
        calendar_root = self._calendar_root()
        day_locator = calendar_root.locator(
            f'{WORKING_DAY_SELECTOR}[data-locator-date="{day_value.isoformat()}"]'
        ).first
        if day_locator.count() == 0:
            self._pause(0.5)
        if day_locator.count() == 0:
            return DayAvailability(
                date=day_value.isoformat(),
                slots=0,
                free_minutes=0,
            )
        day_locator.scroll_into_view_if_needed()
        try:
            day_locator.click()
        except PlaywrightTimeoutError:
            day_locator.click(force=True)
        self._pause(0.8)

        slots = self.page.locator(TIMESLOT_SELECTOR)
        slot_count = slots.count()
        return DayAvailability(
            date=day_value.isoformat(),
            slots=slot_count,
            free_minutes=slot_count * service_duration_min,
        )

    def _go_to_next_month(self) -> bool:
        assert self.page is not None
        buttons = self._calendar_root().locator(CALENDAR_ICON_BUTTON_SELECTOR)
        count = buttons.count()
        if count < 2:
            return False
        buttons.nth(1).click()
        self._pause(0.9)
        return True

    def _current_calendar_month(self) -> tuple[int, int]:
        calendar_root = self._calendar_root()
        texts = calendar_root.locator(CALENDAR_TEXT_SELECTOR)
        for index in range(texts.count()):
            raw_text = texts.nth(index).inner_text().strip()
            match = re.match(r"^([А-Яа-я]+)\s+(\d{4})$", raw_text)
            if not match:
                continue
            month_name = match.group(1).lower()
            year = int(match.group(2))
            month = RUSSIAN_MONTHS.get(month_name)
            if month is not None:
                return year, month
        today = date.today()
        return today.year, today.month

    def _scan_calendar(self, service_duration_min: int) -> list[DayAvailability]:
        raise NotImplementedError

    def _scan_calendar_via_api(
        self,
        staff_id: int,
        service_id: int,
        service_duration_min: int,
    ) -> list[DayAvailability]:
        scan_until = date.today() + timedelta(days=self.days_ahead - 1)
        day_results: list[DayAvailability] = []
        available_dates = self._fetch_bookable_dates(
            staff_id=staff_id,
            service_id=service_id,
            date_from=date.today(),
            date_to=scan_until,
        )
        for available_date in available_dates:
            slot_count = self._fetch_timeslot_count(
                staff_id=staff_id,
                service_id=service_id,
                target_date=available_date,
            )
            day_results.append(
                DayAvailability(
                    date=available_date.isoformat(),
                    slots=slot_count,
                    free_minutes=slot_count * service_duration_min,
                )
            )
        return day_results

    def _analyze_master(self, master_name: str) -> MasterAvailability:
        self._goto_masters_page()
        self._select_master(master_name)
        staff_id = self._current_staff_id()
        self._click_continue()
        self._wait_for_url_part("/select-services")
        self._wait_for_any_selector([SERVICE_ITEM_SELECTOR, SERVICE_DURATION_SELECTOR])

        shortest_service_name, shortest_service_duration_min, shortest_service_id = (
            self._select_shortest_service()
        )
        self._click_continue()
        self._wait_for_any_selector([WORKING_DAY_SELECTOR, NON_WORKING_DAY_SELECTOR])

        scanned_days = self._scan_calendar_via_api(
            staff_id=staff_id,
            service_id=shortest_service_id,
            service_duration_min=shortest_service_duration_min,
        )
        total_slots = sum(day.slots for day in scanned_days)
        total_free_minutes = sum(day.free_minutes for day in scanned_days)
        days_with_slots = sum(1 for day in scanned_days if day.slots > 0)

        return MasterAvailability(
            name=master_name,
            shortest_service_name=shortest_service_name,
            shortest_service_duration_min=shortest_service_duration_min,
            total_slots=total_slots,
            total_free_minutes=total_free_minutes,
            days_with_slots=days_with_slots,
            scanned_days=scanned_days,
        )


def results_to_json(results: Iterable[MasterAvailability]) -> str:
    payload = []
    for master in results:
        master_dict = asdict(master)
        payload.append(master_dict)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def print_table(results: list[MasterAvailability]) -> None:
    if not results:
        print("Нет результатов.")
        return

    name_width = max(len(item.name) for item in results)
    duration_width = max(len(str(item.shortest_service_duration_min)) for item in results)
    slots_width = max(len(str(item.total_slots)) for item in results)
    free_width = max(len(str(item.total_free_minutes)) for item in results)

    header = (
        f"{'Мастер':<{name_width}}  "
        f"{'Мин. услуга':>{duration_width}}  "
        f"{'Слоты':>{slots_width}}  "
        f"{'Свободно, мин':>{free_width}}"
    )
    print(header)
    print("-" * len(header))

    for item in sorted(results, key=lambda value: value.total_free_minutes, reverse=True):
        print(
            f"{item.name:<{name_width}}  "
            f"{item.shortest_service_duration_min:>{duration_width}}  "
            f"{item.total_slots:>{slots_width}}  "
            f"{item.total_free_minutes:>{free_width}}"
        )

