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

    def find_masters(self) -> tuple[list[WebElement], int]:
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "name")))
        except Exception as e:
            self.error_handler.handle(e, context="find_masters")

        all_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        self.pause()
        master_buttons = [
            el for el in all_buttons
            if el.text.strip() != "Любой специалист"
        ]

        if master_buttons:
            m_count = len(master_buttons)
            print("Видим мастеров:", m_count)
            return master_buttons, m_count
        return [], 0

    def choose_service_page(self):
        """Клик по кнопке «Выбрать услугу» (span.y-core-button__text с текстом «Выбрать услугу»)."""
        service_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'y-core-button__text') and contains(., 'Выбрать услугу')]"))
        )
        service_btn.click()
        self.pause()

    def pause(self):
        time.sleep(self.freeze)