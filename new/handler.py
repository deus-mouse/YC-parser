
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from parser import YCParser
from datetime import datetime


class Handler:
    def __init__(self, url, depth, freeze):
        self.url = url
        self.depth = depth
        self.freeze = freeze

        self.parser = None
        self.today = datetime.now()

    def run(self):
        self.parser = YCParser()
        self.parser(url=self.url, depth=self.depth, freeze=self.freeze)

        self.parser.open_page()  # страничка с мастерами

        self.find_masters()


    def find_masters(self):
        master_buttons = self.parser.find_masters()
        m_count = len(master_buttons)
        print("Видим мастеров:", m_count-1)