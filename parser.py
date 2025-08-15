import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from colorama import init, Fore, Style
import calendar

init(autoreset=True)  # для очистки консоли


class YCParser:
    def __init__(self, url, city=None, st=0.5):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 5)
        self.url = url
        self.city = city
        self.st = st
        self.branches = defaultdict(int)
        self.masters = defaultdict(int)
        self.depths = {
            'branch': 1,
            'master': 2,
        }

    def convert_to_minutes(self, time_text):
        # Замена неразрывных пробелов, обрезка лишних пробелов
        time_text = time_text.replace('\xa0', ' ').strip()
        # Регулярное выражение с именованными группами для часов и минут
        pattern = r'^(?:(?P<hours>\d+)\s*ч)?\s*(?:(?P<minutes>\d+)\s*мин)?$'
        match = re.match(pattern, time_text)
        if match:
            hours = int(match.group('hours')) if match.group('hours') else 0
            minutes = int(match.group('minutes')) if match.group('minutes') else 0
            total = hours * 60 + minutes
            if total > 0:
                return total
        return float('inf')

    def open_site(self, url=None):
        if url:
            self.driver.get(url)
        else:
            self.driver.get(self.url)
        self.pause()

    def choose_city(self):
        city_items = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.city-item")))  
        for item in city_items:  
            try:  
                title_el = item.find_element(By.CSS_SELECTOR, '[data-locator="city_title"]')  
                if title_el.text.strip() == self.city:  
                    item.click()  
                    self.pause()  
                    return  
            except Exception:  
                continue  
        print(f"Город {self.city} не найден.")  
        self.pause()  

    def find_branches(self):
        branch_buttons = self.driver.find_elements(By.CLASS_NAME, "title")
        self.pause()

        if branch_buttons:
            return branch_buttons
        return []

    def choose_branch(self, branch):
        branch_name = branch.text.strip()
        self.branches[branch_name] = 0
        branch.click()
        self.pause()

    def choose_individual_services(self):
        individual_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Индивидуальные услуги')]")))
        individual_btn.click()  # клик по "Индивидуальные услуги"
        self.pause()

    def choose_specialist(self):
        specialist_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать специалиста')]")))
        specialist_btn.click()  # клик по "Выбрать специалиста"
        self.pause()

    def find_masters(self):
        master_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        self.pause()
        if master_buttons:
            return master_buttons
        return []

    def choose_master(self, master):
        master_name = master.text.strip()
        self.masters[master_name] = 0
        # добавлено: прокрутка мастера в центр экрана
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", master)  # добавлено
        # добавлено: ожидание, пока мастер станет видимым и активным
        self.wait.until(lambda d: master.is_displayed() and master.is_enabled())  # добавлено
        master.click()
        self.pause()

    def choose_service_page(self):
        service_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать услугу')]")))
        service_btn.click()  # клик по "Выбрать услугу"
        self.pause()

    def select_min_service(self):
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'span[data-locator="service_seance_length"]')
        print("Видим услуг:", len(elements))
        min_time = float('inf')
        min_element = None
        for el in elements:
            total_minutes = self.convert_to_minutes(el.text)
            if total_minutes < min_time:
                min_time = total_minutes
                min_element = el
        if min_element:
            print("Минимальное время:", min_time, "минут. Текст:", min_element.text)
            min_element.click()  # выбираем услугу с минимальной длительностью
        else:
            print("Элементы не найдены.")
        self.pause()
        return min_time if min_time != float('inf') else 0

    def choose_date_and_time(self):
        choose_date_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать дату и время')]")))
        choose_date_btn.click()  # клик по "Выбрать дату и время"
        self.pause()

    def check_working_days(self, today, depth: int, master_name: str, min_time: int, branch_name: str):
        current_date = today
        depth_date = today + timedelta(days=depth)

        first_launch = True
        while current_date < depth_date:  # пока дата не превысила текущую
            print('-> WHILE')
            elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.calendar-day[data-locator="working_day"], div.calendar-day[data-locator="non_working_day"]')

            print("Найдено дней:", len(elements))
            current_date, is_end = self.click_working_days(elements, current_date, depth_date, master_name, min_time, branch_name, first_launch)
            first_launch = False

            print(f'{current_date = }')
            print(f'{depth_date = }')
            print(f'{current_date < depth_date = }')

            arrow_right = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="arrow_right"]'))
            )
            arrow_right.click()

            self.pause()

    def click_working_days(self, elements, current_date, depth_date, master_name, min_time, branch_name, first_launch) -> [datetime, bool]:
        cursor_date = datetime.strptime(elements[0].get_attribute("data-locator-date"), '%Y-%m-%d')
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]

        for day in elements:  # todo в цикле если нерабочий, то continue
            try:
                cursor_date = datetime.strptime(day.get_attribute("data-locator-date"), '%Y-%m-%d')
                print(f'++ day = {cursor_date}')

                if cursor_date.date() > depth_date.date():  # достигли глубины сканирования
                    print(f'{cursor_date >= depth_date = }, {Fore.GREEN}достигли глубины сканирования{Style.RESET_ALL}')
                    return cursor_date, True

                if cursor_date.date() < datetime.now().date():
                    print(f'{cursor_date = } {Fore.RED}в прошлом{Style.RESET_ALL}')
                    continue

                if cursor_date.date() < current_date.date():  # уже сканили
                    print(f'{current_date <= cursor_date = }, {Fore.YELLOW}уже сканили{Style.RESET_ALL}')
                    continue

                if day.get_attribute("data-locator") == "non_working_day":
                    print(f'{cursor_date = } {Fore.BLUE}нерабочий{Style.RESET_ALL}')
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView(true);", day)
                locator = (By.CSS_SELECTOR, f'[data-locator="working_day"][data-locator-date="{day.get_attribute("data-locator-date")}"]')
                day_elem = self.wait.until(EC.element_to_be_clickable(locator))
                day_elem.click()  # клик по рабочему дню

                self.pause()
                self.count_timeslots(master_name, min_time)

                if cursor_date.day == last_day:
                    print(f'{cursor_date = } {Fore.YELLOW}достигли последнего дня{Style.RESET_ALL}')
                    return cursor_date, False

            except Exception as e:
                print("Ошибка при клике по элементу:", e)

        return cursor_date, False

    def count_timeslots(self, master_name, min_time):
        print("-> count_timeslots")
        time_slots = self.driver.find_elements(By.CSS_SELECTOR, 'ui-kit-chips[data-locator="timeslot"]')
        count = len(time_slots)
        print("Найдено временных интервалов:", count)
        self.masters[master_name] += min_time * count

    def upsert_branches_dict(self, master_name, branch_name):
        self.branches[branch_name] += self.masters[master_name]

    def quit(self):
        time.sleep(3)
        self.driver.quit()
        
    def pause(self):
        time.sleep(self.st)

    def go_back(self, n):
        for _ in range(n):
            self.driver.back()
            self.pause()
