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
    def __init__(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 5)

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

    def find_masters(self):
        master_button_prev = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'name')]")))
        print(f'{master_button_prev = }')
        print(f'{len(master_button_prev) = }')

        print(f'{self.driver.title = }')
        master_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        self.pause()
        if master_buttons:
            m_count = len(master_buttons)
            print("Видим мастеров:", m_count - 1)
            return master_buttons
        return []

    def pause(self):
        time.sleep(self.freeze)