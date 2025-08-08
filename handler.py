
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time



class Handler:
    def __init__(self, st):
        self.st = st

        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 5)


    def open_site(self, url=None):
        if url:
            self.driver.get(url)
        else:
            self.driver.get(self.url)
        self.pause()

    def find_city(self, city):
        city_items = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.city-item")))
        for item in city_items:
            try:
                title_el = item.find_element(By.CSS_SELECTOR, '[data-locator="city_title"]')
                if title_el.text.strip() == city:
                    return True
            except Exception:
                continue
        print(f"Город {city} не найден.")
        self.pause()
        return False



    def parse_with_branches(self, city):
        self.parser = parser

    def pause(self):
        time.sleep(self.st)