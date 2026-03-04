import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from colorama import init, Fore, Style
import calendar

from error_handler import SeleniumErrorHandler

init(autoreset=True)  # для очистки консоли


def timed_seconds(func):
    """Декоратор: замеряет время выполнения функции в секундах и выводит в консоль."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[timed] {func.__name__}: {elapsed:.2f} сек")
        return result
    return wrapper


class YCParser:
    def __init__(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 15)  # больше таймаут — из-за гео страница может грузиться дольше
        self.error_handler = SeleniumErrorHandler(self.driver, prefix="debug")

        self.url = None
        self.depth = None
        self.freeze = None
        self.masters = defaultdict(int)

    def __call__(self, *, url, depth, freeze):
        self.url = url
        self.depth = depth
        self.freeze = freeze
        return self

    def open_page(self):
        self.driver.get(self.url)
        self.pause()

    @timed_seconds
    def find_masters(self) -> tuple[list[WebElement], int]:
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "name")))
        except Exception as e:
            self.error_handler.handle(e, context="find_masters")

        all_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        master_buttons = [
            el for el in all_buttons
            if el.text.strip() != "Любой специалист"
        ]

        if master_buttons:
            m_count = len(master_buttons)
            print("Видим мастеров:", m_count)
            return master_buttons, m_count
        return [], 0

    @timed_seconds
    def choose_service_page(self):
        """Клик по плавающей кнопке «Выбрать услугу» (ybutton с data-locator='continue_btn')."""
        service_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="continue_btn"]'))
        )
        service_btn.click()
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

    def pause(self):
        time.sleep(self.freeze)

