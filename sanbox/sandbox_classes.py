from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import re
import datetime
import time


class YClientsParser:
    def __init__(self, url: str, wait_seconds: int = 30):
        self.url = url
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, wait_seconds)

    # ---------- Low-level helpers ----------
    @staticmethod
    def parse_duration(text: str) -> int:
        """Извлекает длительность из текста услуги (в минутах)."""
        match = re.search(r"(\d+)\s*ч", text)
        minutes = 0
        if match:
            hours = int(match.group(1))
            minutes += hours * 60
        match = re.search(r"(\d+)\s*мин", text)
        if match:
            minutes += int(match.group(1))
        return minutes

    def get_staff_elements(self):
        """Возвращает элементы списка специалистов."""
        return self.driver.find_elements(By.CSS_SELECTOR, "app-staff-tile.staff-block.master-clickable")

    def get_service_rows(self):
        """Возвращает элементы услуг на странице выбора услуг."""
        return self.driver.find_elements(By.XPATH, "//div[@data-locator='service_title']/ancestor::div[contains(@class, 'center-part')]")

    def get_time_slots(self):
        """Собирает список доступных временных слотов на текущей дате."""
        return self.driver.find_elements(By.XPATH, "//button[contains(text(), ':')]")

    def move_to_next_day(self):
        """Переключается на следующий день в календаре."""
        calendar = self.driver.find_element(By.TAG_NAME, "body")
        calendar.send_keys(Keys.ARROW_RIGHT)

    def click_arrows(self):
        toggles = self.driver.find_elements(By.CSS_SELECTOR, "ui-kit-svg-icon[data-locator='category_arrow']")
        for toggle in toggles:
            try:
                toggle.click()
            except Exception:
                pass
        time.sleep(1)

    # ---------- High-level flow ----------
    def run(self) -> dict:
        results = {}
        self.driver.get(self.url)

        try:
            # ждём загрузки списка специалистов
            self.wait.until(lambda d: len(self.get_staff_elements()) > 0)
            staff_elements = self.get_staff_elements()

            for idx in range(len(staff_elements)):
                # Перечитываем элементы на каждой итерации из-за обновления DOM
                staff_elements = self.get_staff_elements()
                staff_elem = staff_elements[idx]
                staff_name = staff_elem.text.split("\n")[0]
                if staff_name == 'Любой специалист':
                    continue

                staff_elem.click()

                # Нажать «Продолжить» после выбора специалиста
                continue_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))
                continue_btn.click()

                # На странице услуг раскрыть все категории
                time.sleep(1)
                self.click_arrows()

                # Найти услугу с минимальной длительностью
                service_rows = self.get_service_rows()
                min_minutes = None
                min_row = None
                for row in service_rows:
                    try:
                        dur_text = row.find_element(By.CSS_SELECTOR, "[data-locator='service_seance_length']").get_attribute("textContent")
                        dur = self.parse_duration(dur_text)
                    except Exception:
                        dur = self.parse_duration(row.text)

                    if dur <= 0:
                        continue

                    if min_minutes is None or dur < min_minutes:
                        min_minutes = dur
                        min_row = row

                if min_row is None:
                    self.driver.back()
                    # Вернуться к списку специалистов
                    self.wait.until(lambda d: len(self.get_staff_elements()) > 0)
                    continue

                # Выбрать найденную услугу
                min_row.click()

                # Нажать «Продолжить» к выбору времени
                continue_btn2 = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))
                continue_btn2.click()

                # Страница выбора времени
                time.sleep(2)
                start_date = datetime.date.today()
                end_date = start_date + datetime.timedelta(days=30)
                total_slots = 0

                current_date = start_date
                while current_date <= end_date:
                    try:
                        day_elem = self.driver.find_element(By.XPATH, f"//td/button[normalize-space()='{current_date.day}']")
                        day_elem.click()
                        time.sleep(0.5)
                        slots = self.get_time_slots()
                        total_slots += len(slots)
                    except Exception:
                        pass
                    try:
                        self.move_to_next_day()
                    except Exception:
                        pass
                    current_date += datetime.timedelta(days=1)

                total_minutes = (total_slots * min_minutes) if min_minutes is not None else 0
                results[staff_name] = total_minutes

                # Вернуться к выбору специалиста
                self.driver.get(self.url)
                self.wait.until(lambda d: len(self.get_staff_elements()) > 0)

        except TimeoutException:
            print("Ошибка загрузки страницы")
        finally:
            self.driver.quit()

        return results


if __name__ == "__main__":
    URL = "https://n625088.yclients.com/company/266762/personal/select-master?o="
    parser = YClientsParser(URL)
    print(parser.run())


