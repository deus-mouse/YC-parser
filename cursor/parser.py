"""
Парсер сайта онлайн-записи YClients.
Собирает свободное время мастеров на заданную глубину (дней).
"""

import re
import time
import calendar
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@dataclass
class MasterFreeTime:
    """Мастер и его свободное время в минутах."""
    name: str
    free_minutes: int


def parse_duration_to_minutes(time_text: str):
    """Парсит текст длительности (например '30 мин' или '1 ч 15 мин') в минуты."""
    time_text = time_text.replace('\xa0', ' ').strip()
    pattern = r'^(?:(?P<hours>\d+)\s*ч)?\s*(?:(?P<minutes>\d+)\s*мин)?$'
    match = re.match(pattern, time_text)
    if match:
        hours = int(match.group('hours')) if match.group('hours') else 0
        minutes = int(match.group('minutes')) if match.group('minutes') else 0
        total = hours * 60 + minutes
        if total > 0:
            return total
    return float('inf')


class BookingParser:
    """Парсер страницы онлайн-записи YClients."""

    def __init__(self, url: str, depth_days: int = 30, pause_sec: float = 0.5):
        self.url = url
        self.depth_days = depth_days
        self.pause_sec = pause_sec
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.results: list[MasterFreeTime] = []

    def _pause(self, sec: Optional[float] = None):
        time.sleep(sec if sec is not None else self.pause_sec)

    def _init_driver(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 15)

    def _close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def run(self) -> list[MasterFreeTime]:
        """Запуск парсинга. Возвращает список мастеров с их свободным временем."""
        self._init_driver()
        try:
            self.driver.get(self.url)
            self._pause()

            masters = self._find_masters()
            if not masters:
                print("Мастера не найдены.")
                return []

            # Сохраняем имена сразу (до навигации), чтобы избежать stale elements
            master_names = [m.text.strip() for m in masters]
            print(f"Найдено мастеров: {len(master_names)}")

            for i, master_name in enumerate(master_names):
                print(f"\n--- Мастер {i + 1}/{len(master_names)}: {master_name} ---")

                # Возвращаемся на страницу мастеров (кроме первого)
                if i > 0:
                    self.driver.get(self.url)
                    self._pause()
                    self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "name")))

                # Ищем мастера по имени (свежие элементы после загрузки)
                master_el = self._find_master_by_name(master_name)
                if not master_el:
                    print(f"Не удалось найти мастера '{master_name}', пропуск")
                    continue

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", master_el
                )
                self.wait.until(lambda d: master_el.is_displayed() and master_el.is_enabled())
                master_el.click()
                self._pause()

                if not self._click_continue():
                    continue

                self._expand_collapse_items()
                min_duration = self._select_shortest_service()
                if min_duration <= 0:
                    print(f"У мастера {master_name} нет услуг, пропуск")
                    self.results.append(MasterFreeTime(name=master_name, free_minutes=0))
                    continue

                if not self._click_continue():
                    continue

                total_free_minutes = self._scan_calendar(master_name, min_duration)
                self.results.append(MasterFreeTime(name=master_name, free_minutes=total_free_minutes))
                print(f"Итого свободных минут у {master_name}: {total_free_minutes}")

            return self.results

        finally:
            self._close()

    def _find_masters(self) -> list[WebElement]:
        """Находит всех мастеров на странице."""
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "name")))
        except Exception as e:
            print(f"Ошибка ожидания мастеров: {e}")
            return []

        all_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        return [el for el in all_buttons if el.text.strip() and el.text.strip() != "Любой специалист"]

    def _find_master_by_name(self, name: str) -> Optional[WebElement]:
        """Находит мастера по имени среди свежих элементов страницы."""
        masters = self._find_masters()
        for m in masters:
            try:
                if m.text.strip() == name:
                    return m
            except Exception:
                continue  # stale element, пропускаем
        return None

    def _click_continue(self) -> bool:
        """Клик по кнопке «Выбрать услугу» / «Выбрать дату и время»."""
        try:
            btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="continue_btn"]'))
            )
            btn.click()
            self._pause()
            return True
        except Exception as e:
            print(f"Ошибка при клике continue: {e}")
            return False

    def _expand_collapse_items(self):
        """Раскрывает все выпадающие блоки (y-core-collapse-item) с услугами."""
        # Сначала проверяем, есть ли выпадающие списки
        collapse_items = self.driver.find_elements(
            By.CSS_SELECTOR, "div.y-core-collapse-item"
        )
        if not collapse_items:
            print("Выпадающие списки не найдены, ищем услуги напрямую")
            return

        print(f"Найдено выпадающих блоков: {len(collapse_items)}")
        self._pause(0.5)  # даём странице отрендериться

        # Раскрываем все collapse-блоки (могут появляться после раскрытия предыдущих)
        for round_num in range(25):
            collapse_items = self.driver.find_elements(
                By.CSS_SELECTOR, "div.y-core-collapse-item"
            )
            clicked = 0
            for item in collapse_items:
                try:
                    # Ищем активатор: div[data-activator] или .y-core-collapse-item__activator
                    try:
                        activator = item.find_element(
                            By.CSS_SELECTOR,
                            "div[data-activator], div.y-core-collapse-item__activator"
                        )
                    except Exception:
                        activator = item  # fallback: клик по всему блоку

                    # Проверяем, свёрнут ли блок (контент с height: 0 или без style)
                    content = item.find_elements(
                        By.CSS_SELECTOR, "div.y-core-collapse-item__content"
                    )
                    style = (content[0].get_attribute("style") or "") if content else ""
                    style_nospace = style.replace(" ", "")
                    # height:0px, height:0, height: 0px — свёрнут
                    is_collapsed = "height:0" in style_nospace or not content
                    if is_collapsed:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", activator
                        )
                        self._pause(0.3)
                        try:
                            activator.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", activator)
                        clicked += 1
                        self._pause(0.5)
                except Exception:
                    continue
            if clicked == 0:
                break

        self._pause(0.5)

    def _select_shortest_service(self) -> int:
        """Выбирает услугу с минимальной длительностью. Возвращает длительность в минутах."""
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, 'span[data-locator="service_seance_length"]'
        )
        if not elements:
            print("Услуги не найдены (проверьте, что выпадающие блоки раскрыты)")
            return 0
        print(f"Найдено услуг: {len(elements)}")

        min_minutes = float('inf')
        min_el = None
        for el in elements:
            mins = parse_duration_to_minutes(el.text)
            if mins < min_minutes:
                min_minutes = mins
                min_el = el

        if min_el:
            min_el.click()
            self._pause()
            return int(min_minutes) if min_minutes != float('inf') else 0
        return 0

    def _scan_calendar(self, master_name: str, slot_duration_min: int) -> int:
        """Проходит по календарю на depth_days вперёд, считает свободные минуты."""
        today = datetime.now().date()
        end_date = today + timedelta(days=self.depth_days)
        total_free_minutes = 0
        current_month_start = today.replace(day=1)

        while current_month_start < end_date:
            day_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div.calendar-day[data-locator="working_day"], div.calendar-day[data-locator="non_working_day"]'
            )

            if not day_elements:
                break

            last_day_of_month = calendar.monthrange(
                current_month_start.year, current_month_start.month
            )[1]

            for day_el in day_elements:
                try:
                    date_str = day_el.get_attribute("data-locator-date")
                    if not date_str:
                        continue

                    day_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                    if day_date > end_date:
                        return total_free_minutes

                    if day_date < today:
                        continue

                    if day_el.get_attribute("data-locator") == "non_working_day":
                        continue

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", day_el
                    )
                    locator = (
                        By.CSS_SELECTOR,
                        f'[data-locator="working_day"][data-locator-date="{date_str}"]'
                    )
                    day_el = self.wait.until(EC.element_to_be_clickable(locator))
                    day_el.click()
                    self._pause()

                    slots = self.driver.find_elements(
                        By.CSS_SELECTOR, 'ui-kit-chips[data-locator="timeslot"]'
                    )
                    slot_count = len(slots)
                    total_free_minutes += slot_duration_min * slot_count

                    if day_date.day == last_day_of_month:
                        break

                except Exception as e:
                    print(f"Ошибка при обработке дня {date_str}: {e}")

            # Переход к следующему месяцу
            try:
                arrow = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="arrow_right"]'))
                )
                arrow.click()
                self._pause()

                if current_month_start.month == 12:
                    current_month_start = current_month_start.replace(
                        year=current_month_start.year + 1, month=1
                    )
                else:
                    current_month_start = current_month_start.replace(
                        month=current_month_start.month + 1
                    )

            except Exception:
                break

        return total_free_minutes
