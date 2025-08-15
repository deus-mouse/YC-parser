
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from parser import YCParser


class Handler:
    def __init__(self, st, url, today, depth_days):
        self.st = st
        self.url = url
        self.city = None
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 5)
        self.parser = None
        self.today = today
        self.depth_days = depth_days

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
                    self.city = city
                    return True
            except Exception:
                continue
        print(f"Город {city} не найден.")
        self.pause()
        return False

    def find_masters(self):
        master_buttons = self.driver.find_elements(By.CLASS_NAME, "name")
        self.pause()
        if master_buttons:
            return True
        return False

    def start_from_city(self):
        self.parser = YCParser(url=self.url, city=self.city, st=self.st)
        self.parser.open_site()
        self.parser.choose_city()
        br_count = len(self.parser.find_branches())
        print("Видим филиалов:", br_count)

        for br in range(br_count):
            branch_buttons = self.parser.find_branches()
            branch = branch_buttons[br]
            branch_name = branch.text.strip()
            print(f'Выбираем филиал: {branch_name}')

            self.parser.choose_branch(branch)  # откатываемся к этой странице филиалов
            self.parser.choose_individual_services()
            self.parser.choose_specialist()
            self.run_from_masters(branch_name)
            break

        self.parser.quit()
        print(f'{self.parser.branches = }')
        print(f'{self.parser.masters = }')

    def start_from_masters(self):
        self.parser = YCParser(url=self.url, st=self.st)

    def run_from_masters(self, branch_name=None):
        master_buttons = self.parser.find_masters()
        m_count = len(master_buttons)
        print("Видим мастеров:", m_count - 1)

        while len(self.parser.masters) < m_count - 1:  # 0 = "Любой специалист"
            # while len(parser.masters) < 2:  # 0 = "Любой специалист"
            print(f'--------> посчитано мастеров {len(self.parser.masters)}')
            master_buttons = self.parser.find_masters()
            master = next((master for master in master_buttons if
                           master.text.strip() not in self.parser.masters and master.text.strip() != "Любой специалист"),
                          None)
            master_name = master.text.strip()
            print(f'{master_name = }')

            self.parser.choose_master(master)  # страница мастеров
            self.parser.choose_service_page()
            min_time = self.parser.select_min_service()
            self.parser.choose_date_and_time()
            self.parser.check_working_days(self.today, self.depth_days, master_name, min_time, branch_name)
            self.parser.upsert_branches_dict(master_name, branch_name)

            self.parser.go_back(self.parser.depths['master'])  # откатываемся к странице мастеров
            # parser.go_back(parser.depth['service'])
            # parser.go_back(parser.depth['date_and_time'])
            # parser.go_back(parser.depth['service_page'])
            print(f'{self.parser.branches = }')
            print(f'{self.parser.masters = }')
            # break  # todo remove
        # parser.go_back(parser.depth['branch'])



    def pause(self):
        time.sleep(self.st)