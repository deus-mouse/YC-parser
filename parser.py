import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException


class YCParser:
    def __init__(self, sleep_time=0.5):
        self.sleep_time = sleep_time
        self.driver = webdriver.Chrome()  # МОД: инициализация драйвера
        self.wait = WebDriverWait(self.driver, 10)

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

    def open_site(self, url):
        self.driver.get(url)

    def choose_city(self):
        moscow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Москва')]")))  # модифицировано
        moscow_btn.click()  # клик по кнопке "Москва"
        time.sleep(self.sleep_time)

    def choose_address(self):
        address_buttons = self.driver.find_elements(By.CLASS_NAME, "address")
        print("Видим филиалов:", len(address_buttons))
        if address_buttons:
            address_buttons[0].click()  # выбираем первый адрес
            time.sleep(self.sleep_time)

    def choose_individual_services(self):
        individual_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Индивидуальные услуги')]")))
        individual_btn.click()  # клик по "Индивидуальные услуги"
        time.sleep(self.sleep_time)

    def choose_specialist(self):
        specialist_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать специалиста')]")))
        specialist_btn.click()  # клик по "Выбрать специалиста"
        time.sleep(self.sleep_time)

    def choose_master(self):
        masters = self.driver.find_elements(By.CLASS_NAME, "name")
        print("Видим мастеров:", len(masters))
        if len(masters) > 1:
            masters[1].click()  # выбираем первого мастера (индекс 1)
            time.sleep(self.sleep_time)

    def choose_service(self):
        service_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать услугу')]")))
        service_btn.click()  # клик по "Выбрать услугу"
        time.sleep(self.sleep_time)

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
        time.sleep(self.sleep_time)

    def choose_date_and_time(self):
        choose_date_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать дату и время')]")))
        choose_date_btn.click()  # клик по "Выбрать дату и время"
        time.sleep(self.sleep_time)
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
                time.sleep(self.sleep_time)
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