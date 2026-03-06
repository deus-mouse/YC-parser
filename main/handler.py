
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from parser import YCParser
from datetime import datetime
from helper import pause


class Handler:
    def __init__(self, url, depth):
        self.url = url
        self.depth = depth

        self.parser = None
        self.today = datetime.now()

    def run(self):
        self.parser = YCParser()
        self.parser(url=self.url, depth=self.depth)

        self.parser.open_page()  # страничка с мастерами

        master_buttons, m_count = self.parser.find_masters()

        for master_el in master_buttons:
            master_el.click()
            pause(0.5)
            self.parser.continue_btn()
            self.parser.expand_all_collapse_items()
            # min_time = self.parser.select_min_service()
            # print(f'{min_time = }')
            # self.parser.choose_date_and_time()



            break  ## todo remove

