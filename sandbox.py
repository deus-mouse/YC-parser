from selenium import webdriver  
from selenium.webdriver.common.by import By  
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.webdriver.support import expected_conditions as EC  
from selenium.common.exceptions import TimeoutException  
from selenium.webdriver.common.keys import Keys  
import re  
import datetime  
import time  

URL = "https://n625088.yclients.com/company/266762/personal/select-master?o="  

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

def get_staff_elements(driver):  
    """Возвращает элементы списка специалистов."""  
    # обновлено: теперь ищем элементы app-staff-tile с классами staff-block и master-clickable  # изменено
    return driver.find_elements(By.CSS_SELECTOR, "app-staff-tile.staff-block.master-clickable")  # изменено

def get_service_rows(driver):  
    """Возвращает элементы услуг на странице выбора услуг."""  
    # изменено: ищем элементы по data-locator='service_title' и возвращаем родительский контейнер center-part  # изменено
    return driver.find_elements(By.XPATH, "//div[@data-locator='service_title']/ancestor::div[contains(@class, 'center-part')]")  # изменено

def get_time_slots(driver):  
    """Собирает список доступных временных слотов на текущей дате."""  
    # селектор находит кнопки с временем; подберите при необходимости  
    return driver.find_elements(By.XPATH, "//button[contains(text(), ':')]")  

def move_to_next_day(driver):  
    """Переключается на следующий день в календаре."""  
    # отправляем клавишу вправо календарю; если не работает, можно кликать по конкретным ячейкам  
    calendar = driver.find_element(By.TAG_NAME, "body")  
    calendar.send_keys(Keys.ARROW_RIGHT)  

def click_arrows(driver):
    toggles = driver.find_elements(By.CSS_SELECTOR,
                                   "ui-kit-svg-icon[data-locator='category_arrow']")  # изменено
    for tog in toggles:
        try:
            tog.click()
        except:
            pass
    time.sleep(1)

def find_and_click_min_service(driver):



def main():  
    driver = webdriver.Chrome()  
    driver.get(URL)  
    wait = WebDriverWait(driver, 30)  

    results = {}  

    try:  
        # ждём загрузки списка специалистов  
        wait.until(lambda d: len(get_staff_elements(d)) > 0)  
        staff_elements = get_staff_elements(driver)  
        print(f'{staff_elements=}')
        print(f'{len(staff_elements)=}')

        for idx in range(len(staff_elements)):  
            # перезагружаем список при каждой итерации, потому что DOM обновляется  
            staff_elements = get_staff_elements(driver)  
            staff_elem = staff_elements[idx]  
            staff_name = staff_elem.text.split("\n")[0]  
            print(f'{staff_name=}')
            if staff_name == 'Любой специалист':
                continue

            staff_elem.click()  
            # ждём кнопку "Продолжить" и нажимаем её  
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))  
            continue_btn.click()  

            # на странице выбора услуг разворачиваем все категории  
            # изменено: ищем стрелки категории (иконки arrow-down-light) data-locator="category_arrow"  # изменено
            time.sleep(1)
            click_arrows(driver)

            # собираем все услуги и ищем минимальную длительность
            find_and_click_min_service(driver)

            service_rows = get_service_rows(driver)
            print(f'{service_rows=}')
            print(f'{len(service_rows)=}')

            min_minutes = None
            min_checkbox = None
            for row in service_rows:
                # извлекаем длительность из span[data-locator="service_seance_length"]
                try:
                    dur_text = row.find_element(
                        By.CSS_SELECTOR, "[data-locator='service_seance_length']"
                    ).get_attribute("textContent")
                    dur = parse_duration(dur_text)
                except Exception:
                    dur = parse_duration(row.text)

                if dur <= 0:
                    continue

                if min_minutes is None or dur < min_minutes:
                    min_minutes = dur
                    min_row = row

            # если нашли минимальную услугу — кликаем по контейнеру строки (без чекбоксов)
            if min_row is None:
                driver.back()
                continue
            print(f'{min_row=}')
            print(f'{min_row.text=}')
            min_row.click()

            # min_checkbox.click()  
            # нажимаем продолжить  
            continue_btn2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продолжить')]")))  
            continue_btn2.click()  

            # страница выбора времени  
            time.sleep(2)  
            start_date = datetime.date.today()  
            end_date = start_date + datetime.timedelta(days=30)  
            total_slots = 0  

            # определяем текущую выбранную дату в календаре  
            current_date = start_date  
            while current_date <= end_date:  
                # выбираем ячейку с нужной датой, используя текст числа  
                try:  
                    day_elem = driver.find_element(By.XPATH, f"//td/button[normalize-space()='{current_date.day}']")  
                    day_elem.click()  
                    time.sleep(0.5)  
                    slots = get_time_slots(driver)  
                    total_slots += len(slots)  
                except:  
                    pass  
                # переходим к следующему дню с помощью стрелки  
                try:  
                    move_to_next_day(driver)  
                except:  
                    pass  
                current_date += datetime.timedelta(days=1)  

            # вычисляем общее количество свободных минут  
            total_minutes = total_slots * min_minutes  
            results[staff_name] = total_minutes  

            # возвращаемся к выбору специалиста  
            driver.get(URL)  
            wait.until(lambda d: len(get_staff_elements(d)) > 0)  

    except TimeoutException:  
        print("Ошибка загрузки страницы")  
    finally:  
        driver.quit()  

    print(results)  

if __name__ == "__main__":  
    main()








