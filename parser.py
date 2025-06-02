import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException
from collections import defaultdict


class YCParser:
    def __init__(self, url, city, st=0.5):
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
        time_text = time_text.replace('\xa0', ' ').strip()  # модифицировано
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
        # branch_buttons = self.driver.find_elements(By.CLASS_NAME, "address")
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
            # print("Текст:", el.text)
            total_minutes = self.convert_to_minutes(el.text)
            # print(f"{total_minutes = }")
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
        depth_date = today + timedelta(days=depth)
        last_day_on_first_page = None

        # working_date_list = [el.get_attribute("data-locator-date") for el in working_days]  # даты списком
        current_date = today
        while current_date < depth_date:  # пока дата не превысила текущую
            print('-> WHILE')
            working_days = self.driver.find_elements(By.CSS_SELECTOR, '[data-locator="working_day"]')
            print("Найдено рабочих дней:", len(working_days))
            if not working_days:
                print('-> WHILE break')
                break
            _date = self.click_working_days(working_days, master_name, min_time, branch_name)
            print(f'{current_date = }')
            print(f'{depth_date = }')
            print(f'{current_date < depth_date = }')

            arrow_right = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="arrow_right"]'))
            )
            arrow_right.click()

            current_date = _date



    def click_working_days(self, working_days, master_name, min_time, branch_name) -> datetime:
        for day in working_days:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", day)  # модифицировано
                self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="working_day"]')))
                day.click()  # клик по рабочему дню
                self.pause()
                self.count_timeslots(master_name, min_time)
            except Exception as e:
                print("Ошибка при клике по элементу:", e)

        last_working_day_str = working_days[-1].get_attribute("data-locator-date")
        last_working_day = datetime.strptime(last_working_day_str, '%Y-%m-%d')



        return last_working_day

    def count_timeslots(self, master_name, min_time):
        time_slots = self.driver.find_elements(By.CSS_SELECTOR, 'ui-kit-chips[data-locator="timeslot"]')
        count = len(time_slots)
        # print("Найдено временных интервалов:", count)
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
