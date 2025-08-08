
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class Handler:
    def __init__(self):
        self.driver = webdriver.Chrome()

    def open_site(self, url=None):
        if url:
            self.driver.get(url)
        else:
            self.driver.get(self.url)
        self.pause()

    def set_parser(self, parser):
    def parse_with_branches(self, city):
        self.parser = parser
