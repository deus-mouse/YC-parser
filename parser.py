import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException


class YCParser:
    def __init__(self, url, city, st=0.5):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 5)
        self.url = url
        self.city = city
        self.st = st
        self.branchs = {}

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

    def open_site(self):
        self.driver.get(self.url)
        time.sleep(self.st)

    def choose_city(self):
        city_items = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.city-item")))  
        for item in city_items:  
            try:  
                title_el = item.find_element(By.CSS_SELECTOR, '[data-locator="city_title"]')  
                if title_el.text.strip() == self.city:  
                    item.click()  
                    time.sleep(self.st)  
                    return  
            except Exception:  
                continue  
        print(f"Город {self.city} не найден.")  
        time.sleep(self.st)  

    def find_branchs(self):
        branch_buttons = self.driver.find_elements(By.CLASS_NAME, "address")
        print("Видим филиалов:", len(branch_buttons))
        if branch_buttons:
            return branch_buttons
        return None

    def choose_branch(self, branch):
        print(branch.text.strip())  # todo тут нужно имя филиала, а не адрес
        self.branchs[branch] = 0
        print(f'{self.branchs = }')
        # branch.click()
        time.sleep(self.st)

    def choose_individual_services(self):
        individual_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Индивидуальные услуги')]")))
        individual_btn.click()  # клик по "Индивидуальные услуги"
        time.sleep(self.st)

    def choose_specialist(self):
        specialist_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать специалиста')]")))
        specialist_btn.click()  # клик по "Выбрать специалиста"
        time.sleep(self.st)

    def choose_master(self):
        masters = self.driver.find_elements(By.CLASS_NAME, "name")
        print("Видим мастеров:", len(masters))
        if len(masters) > 1:
            masters[1].click()  # выбираем первого мастера (индекс 1)
            time.sleep(self.st)

    def choose_service(self):
        service_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать услугу')]")))
        service_btn.click()  # клик по "Выбрать услугу"
        time.sleep(self.st)

    def select_min_service(self):
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'span[data-locator="service_seance_length"]')
        print("Видим услуг:", len(elements))
        min_time = float('inf')
        min_element = None
        for el in elements:
            print("Текст:", el.text)
            total_minutes = self.convert_to_minutes(el.text)
            print(f"{total_minutes = }")
            if total_minutes < min_time:
                min_time = total_minutes
                min_element = el
        if min_element:
            print("Минимальное время:", min_time, "минут. Текст:", min_element.text)
            min_element.click()  # выбираем услугу с минимальной длительностью
        else:
            print("Элементы не найдены.")
        time.sleep(self.st)

    def choose_date_and_time(self):
        choose_date_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать дату и время')]")))
        choose_date_btn.click()  # клик по "Выбрать дату и время"
        time.sleep(self.st)
        current_date = datetime.now().date().day
        print(f'{current_date = }')

    def click_working_days(self):
        working_days = self.driver.find_elements(By.CSS_SELECTOR, '[data-locator="working_day"]')
        print("Найдено рабочих дней:", len(working_days))
        for day in working_days:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", day)  # модифицировано
                self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="working_day"]')))
                day.click()  # клик по рабочему дню
                time.sleep(self.st)
            except Exception as e:
                print("Ошибка при клике по элементу:", e)

    def count_timeslots(self):
        time_slots = self.driver.find_elements(By.CSS_SELECTOR, 'ui-kit-chips[data-locator="timeslot"]')
        count = len(time_slots)
        print("Найдено временных интервалов:", count)
        return count

    def quit(self):
        time.sleep(5)
        self.driver.quit()