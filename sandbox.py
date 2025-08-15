from selenium import webdriver  # добавлено
from selenium.webdriver.common.by import By  # добавлено
from selenium.webdriver.support.ui import WebDriverWait  # добавлено
from selenium.webdriver.support import expected_conditions as EC  # добавлено
from selenium.common.exceptions import TimeoutException  # добавлено
from selenium.webdriver.common.keys import Keys  # добавлено
import re  # добавлено
import datetime  # добавлено
import time  # добавлено

URL = "https://n625088.yclients.com/company/266762/personal/select-master?o="  # добавлено

def parse_duration(text: str) -> int:  # добавлено
    """Извлекает длительность из текста услуги (в минутах)."""  # добавлено
    match = re.search(r"(\d+)\s*ч", text)  # добавлено
    minutes = 0  # добавлено
    if match:  # добавлено
        hours = int(match.group(1))  # добавлено
        minutes += hours * 60  # добавлено
    match = re.search(r"(\d+)\s*мин", text)  # добавлено
    if match:  # добавлено
        minutes += int(match.group(1))  # добавлено
    return minutes  # добавлено

def get_staff_elements(driver):  # добавлено
    """Возвращает элементы списка специалистов."""  # добавлено
    # обновлено: теперь ищем элементы app-staff-tile с классами staff-block и master-clickable  # изменено
    return driver.find_elements(By.CSS_SELECTOR, "app-staff-tile.staff-block.master-clickable")  # изменено

def get_service_rows(driver):  # добавлено
    """Возвращает элементы услуг на странице выбора услуг."""  # добавлено
    # селектор ищет строку услуги с указанием стоимости; при необходимости изменить  # добавлено
    return driver.find_elements(By.XPATH, "//div[contains(@class,'service')]")  # добавлено

def get_time_slots(driver):  # добавлено
    """Собирает список доступных временных слотов на текущей дате."""  # добавлено
    # селектор находит кнопки с временем; подберите при необходимости  # добавлено
    return driver.find_elements(By.XPATH, "//button[contains(text(), ':')]")  # добавлено

def move_to_next_day(driver):  # добавлено
    """Переключается на следующий день в календаре."""  # добавлено
    # отправляем клавишу вправо календарю; если не работает, можно кликать по конкретным ячейкам  # добавлено
    calendar = driver.find_element(By.TAG_NAME, "body")  # добавлено
    calendar.send_keys(Keys.ARROW_RIGHT)  # добавлено

def main():  # добавлено
    driver = webdriver.Chrome()  # добавлено
    driver.get(URL)  # добавлено
    wait = WebDriverWait(driver, 30)  # добавлено

    results = {}  # добавлено

    try:  # добавлено
        # ждём загрузки списка специалистов  # добавлено
        wait.until(lambda d: len(get_staff_elements(d)) > 0)  # добавлено
        staff_elements = get_staff_elements(driver)  # добавлено
        print(f'{staff_elements=}')
        print(f'{len(staff_elements)=}')

        for idx in range(len(staff_elements)):  # добавлено
            # перезагружаем список при каждой итерации, потому что DOM обновляется  # добавлено
            staff_elements = get_staff_elements(driver)  # добавлено
            staff_elem = staff_elements[idx]  # добавлено
            staff_name = staff_elem.text.split("\n")[0]  # добавлено
            print(f'{staff_name=}')

            staff_elem.click()  # добавлено
            # ждём кнопку "Продолжить" и нажимаем её  # добавлено
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))  # добавлено
            continue_btn.click()  # добавлено

            # на странице выбора услуг разворачиваем все категории  # добавлено
            time.sleep(1)  # добавлено
            toggles = driver.find_elements(By.XPATH, "//button[contains(@aria-label,'развернуть')]")  # добавлено
            for tog in toggles:  # добавлено
                try:  # добавлено
                    tog.click()  # добавлено
                except:  # добавлено
                    pass  # добавлено
            time.sleep(1)  # добавлено

            # собираем все услуги и ищем минимальную длительность  # добавлено
            service_rows = get_service_rows(driver)  # добавлено
            min_minutes = None  # добавлено
            min_checkbox = None  # добавлено
            for row in service_rows:  # добавлено
                text = row.text  # добавлено
                dur = parse_duration(text)  # добавлено
                if dur == 0:  # добавлено
                    continue  # добавлено
                if min_minutes is None or dur < min_minutes:  # добавлено
                    min_minutes = dur  # добавлено
                    # находим чекбокс внутри строки  # добавлено
                    try:  # добавлено
                        checkbox = row.find_element(By.XPATH, ".//input[@type='checkbox']")  # добавлено
                    except:  # добавлено
                        checkbox = row.find_element(By.TAG_NAME, "button")  # добавлено
                    min_checkbox = checkbox  # добавлено
            if min_checkbox is None:  # добавлено
                # если услуг нет, возвращаемся назад  # добавлено
                driver.back()  # добавлено
                continue  # добавлено

            min_checkbox.click()  # добавлено
            # нажимаем продолжить  # добавлено
            continue_btn2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))  # добавлено
            continue_btn2.click()  # добавлено

            # страница выбора времени  # добавлено
            time.sleep(2)  # добавлено
            start_date = datetime.date.today()  # добавлено
            end_date = start_date + datetime.timedelta(days=30)  # добавлено
            total_slots = 0  # добавлено

            # определяем текущую выбранную дату в календаре  # добавлено
            current_date = start_date  # добавлено
            while current_date <= end_date:  # добавлено
                # выбираем ячейку с нужной датой, используя текст числа  # добавлено
                try:  # добавлено
                    day_elem = driver.find_element(By.XPATH, f"//td/button[normalize-space()='{current_date.day}']")  # добавлено
                    day_elem.click()  # добавлено
                    time.sleep(0.5)  # добавлено
                    slots = get_time_slots(driver)  # добавлено
                    total_slots += len(slots)  # добавлено
                except:  # добавлено
                    pass  # добавлено
                # переходим к следующему дню с помощью стрелки  # добавлено
                try:  # добавлено
                    move_to_next_day(driver)  # добавлено
                except:  # добавлено
                    pass  # добавлено
                current_date += datetime.timedelta(days=1)  # добавлено

            # вычисляем общее количество свободных минут  # добавлено
            total_minutes = total_slots * min_minutes  # добавлено
            results[staff_name] = total_minutes  # добавлено

            # возвращаемся к выбору специалиста  # добавлено
            driver.get(URL)  # добавлено
            wait.until(lambda d: len(get_staff_elements(d)) > 0)  # добавлено

    except TimeoutException:  # добавлено
        print("Ошибка загрузки страницы")  # добавлено
    finally:  # добавлено
        driver.quit()  # добавлено

    print(results)  # добавлено

if __name__ == "__main__":  # добавлено
    main()  # добавлено