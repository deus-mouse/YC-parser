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
from helper import convert_to_minutes, pause

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
        self.masters = defaultdict(int)

    def __call__(self, *, url, depth):
        self.url = url
        self.depth = depth
        return self


    def open_page(self):
        self.driver.get(self.url)
        pause()

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
    def continue_btn(self):
        """Клик по плавающей кнопке «Выбрать услугу» (ybutton с data-locator='continue_btn')."""
        service_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-locator="continue_btn"]'))
        )
        service_btn.click()
        pause()

    def expand_all_collapse_items(self):
        """Находит все выпадающие блоки (в т.ч. внутри Shadow DOM) и раскрывает их."""
        # Элементы могут быть внутри shadow root — ищем и кликаем через JS
        script = """
        function collectActivators(root, out) {
            try {
                root.querySelectorAll('div.y-core-collapse-item__activator, div[data-activator]').forEach(function(el) { out.push(el); });
                root.querySelectorAll('*').forEach(function(el) {
                    if (el.shadowRoot) collectActivators(el.shadowRoot, out);
                });
            } catch (e) {}
            return out;
        }
        var activators = collectActivators(document, []);
        var clicked = 0;
        activators.forEach(function(el) {
            try {
                if (el.hasAttribute('data-collapse-clicked')) return;
                if (el.offsetParent === null) return;
                el.setAttribute('data-collapse-clicked', '1');
                el.scrollIntoView({block: 'center'});
                el.click();
                clicked++;
            } catch (e) {}
        });
        return clicked;
        """
        total_clicked = 0
        max_rounds = 20
        for _ in range(max_rounds):
            round_clicked = self.driver.execute_script(script)
            total_clicked += round_clicked
            if round_clicked == 0:
                break
            pause()
        print("Раскрыто выпадающих блоков:", total_clicked)

    def select_min_service(self):
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'span[data-locator="service_seance_length"]')
        print("Видим услуг:", len(elements))
        min_time = float('inf')
        min_element = None
        for el in elements:
            total_minutes = convert_to_minutes(el.text)
            if total_minutes < min_time:
                min_time = total_minutes
                min_element = el
        if min_element:
            print("Минимальное время:", min_time, "минут. Текст:", min_element.text)
            min_element.click()  # выбираем услугу с минимальной длительностью
        else:
            print("Элементы не найдены.")
        pause()
        return min_time if min_time != float('inf') else 0

    def choose_date_and_time(self):
        choose_date_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать дату и время')]")))
        choose_date_btn.click()  # клик по "Выбрать дату и время"
        pause()

