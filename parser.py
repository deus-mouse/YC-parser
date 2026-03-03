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

        master_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        self.pause()
        for master in master_buttons:
            print(f'{master.text.strip()=}')
            if master.text.strip() == "Любой специалист":
                print("Любой специалист найден")


        if master_buttons:
            m_count = len(master_buttons)
            print("Видим мастеров:", m_count - 1)

            return master_buttons, m_count
        return [], 0

    def pause(self):
        time.sleep(self.freeze)