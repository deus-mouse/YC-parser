from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from selenium.common.exceptions import ElementClickInterceptedException


def convert_to_minutes(time_text):
    # Приводим строку к виду с обычными пробелами и удаляем лишние пробелы
    time_text = time_text.replace('\xa0', ' ').strip()  # модифицировано: замена неразрывных пробелов
    # Используем регулярное выражение с именованными группами для часов и минут
    pattern = r'^(?:(?P<hours>\d+)\s*ч)?\s*(?:(?P<minutes>\d+)\s*мин)?$'
    match = re.match(pattern, time_text)
    if match:
        hours = int(match.group('hours')) if match.group('hours') else 0
        minutes = int(match.group('minutes')) if match.group('minutes') else 0
        total = hours * 60 + minutes
        if total > 0:
            return total
    return float('inf')


# МОД: Инициализация драйвера (убедитесь, что chromedriver доступен в PATH)
driver = webdriver.Chrome()

# МОД: Открытие сайта
driver.get("https://n82183.yclients.com/")

# МОД: Ожидание появления кнопки с текстом "Москва"
wait = WebDriverWait(driver, 10)
moscow_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Москва')]")))  # МОД: Поиск элемента с текстом "Москва"
# TODO у некоторых мб сразу быть выбор адреса без выбора города,
#  поэтому стоит искать if not address_buttons = driver.find_elements(By.CLASS_NAME, "address")

moscow_btn.click()  # МОД: Клик по кнопке "Москва"
time.sleep(1)

address_buttons = driver.find_elements(By.CLASS_NAME, "address")
print("Видим филиалов:", len(address_buttons))
address_buttons[0].click()  # Выбираем первый адрес
time.sleep(1)

individual_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Индивидуальные услуги')]")))
individual_btn.click()  # МОД: Клик по кнопке "Индивидуальные услуги"
time.sleep(1)

choose_specialist_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать специалиста')]")))
choose_specialist_btn.click()  # МОД: Клик по кнопке "Выбрать специалиста"
time.sleep(1)

staff_block_master_clickable_btn = driver.find_elements(By.CLASS_NAME, "name")
print("Видим мастеров:", len(staff_block_master_clickable_btn))

# Цикл перебирает мастеров
# for i in range(1, len(staff_block_master_clickable_btn)):
#     time.sleep(0.5)
#     print(i)
#     try:
#         # Ждем, пока элемент станет кликабельным (изменено)
#         WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, ".//div[@data-locator='master_name']")))
#         # Прокручиваем элемент в видимую область (изменено)
#         driver.execute_script("arguments[0].scrollIntoView(true);", staff_block_master_clickable_btn[i])
#         staff_block_master_clickable_btn[i].click()  # выбрали мастера
#     except ElementClickInterceptedException:
#         # Альтернативный клик через JavaScript (изменено)
#         driver.execute_script("arguments[0].click();", staff_block_master_clickable_btn[i])

staff_block_master_clickable_btn[1].click()  # выбрали 1-го мастера

choose_service_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать услугу')]")))  # МОД: Поиск элемента с текстом "Москва"
choose_service_btn.click()  # МОД: Клик по кнопке "Выбрать услугу"
time.sleep(1)


# Находим все элементы с временными значениями
elements = driver.find_elements(By.CSS_SELECTOR, 'span[data-locator="service_seance_length"]')
print("Видим услуг:", len(elements))

min_time = float('inf')
min_element = None
for el in elements:
    print("Текст::", el.text)
    total_minutes = convert_to_minutes(el.text)
    print(f"{total_minutes = }")
    if total_minutes < min_time:
        min_time = total_minutes
        min_element = el

if min_element:
    print("Минимальное время:", min_time, "минут. Текст:", min_element.text)
else:
    print("Элементы не найдены.")
time.sleep(1)

min_element.click()  # выбрали самую которткую услугу




# МОД: Пауза для наблюдения результатов (при необходимости)
time.sleep(5)
driver.quit()

