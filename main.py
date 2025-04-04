# МОД: Импорт необходимых модулей
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time  # МОД: Для паузы
import re

# МОД: Инициализация драйвера (убедитесь, что chromedriver доступен в PATH)
driver = webdriver.Chrome()

# МОД: Открытие сайта
driver.get("https://n82183.yclients.com/")

# МОД: Ожидание появления кнопки с текстом "Москва"
wait = WebDriverWait(driver, 10)
moscow_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Москва')]")))  # МОД: Поиск элемента с текстом "Москва"
# TODO у некоторых мб сразу быть выбор адреса без выбора города,
#  поэтому стоит искать if not address_buttons = driver.find_elements(By.CLASS_NAME, "address")

print("Нажимаем на кнопку с текстом 'Москва':", moscow_btn.text)
moscow_btn.click()  # МОД: Клик по кнопке "Москва"

# button = driver.find_element(By.CLASS_NAME, "address")
# print("Нажимаем на кнопку address:", button.text)
# button.click()  # МОД: Клик по кнопке "Москва"

time.sleep(1)
address_buttons = driver.find_elements(By.CLASS_NAME, "address")
print("Видим филиалов:", len(address_buttons))
address_buttons[0].click()  # Выбираем первый адресс

time.sleep(1)
individual_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Индивидуальные услуги')]")))  # МОД: Поиск элемента с текстом "Москва"
individual_btn.click()  # МОД: Клик по кнопке "Индивидуальные услуги"

time.sleep(1)
choose_specialist_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать специалиста')]")))  # МОД: Поиск элемента с текстом "Москва"
choose_specialist_btn.click()  # МОД: Клик по кнопке "Выбрать специалиста"

time.sleep(1)
staff_block_master_clickable_btn = driver.find_elements(By.CLASS_NAME, "name")
print("Видим мастеров:", len(staff_block_master_clickable_btn))

# for i in range(1, len(staff_block_master_clickable_btn)):
#     time.sleep(1)
#     print(i)
#     staff_block_master_clickable_btn[i].click()  # выбрали мастера

staff_block_master_clickable_btn[1].click()  # выбрали мастера

choose_service_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Выбрать услугу')]")))  # МОД: Поиск элемента с текстом "Москва"
choose_service_btn.click()  # МОД: Клик по кнопке "Выбрать услугу"

services = driver.find_elements(By.CLASS_NAME, "card-content-container")  # добавлено
print("Видим услуг:", len(services))
# Находим все элементы услуг на странице
# Здесь предполагается, что каждая услуга оформлена в элементе с классом "select-services__item"  # изменено
# services = driver.find_elements(By.CLASS_NAME, "select-services__item")  # изменено


min_time = float('inf')
min_service = None

for service in services:
    try:
        # Ищем элемент, содержащий время услуги (текст с "мин")
        duration_element = service.find_element(By.XPATH, ".//*[contains(text(),'мин')]")
        print(f'{duration_element=}')
#
#         duration_text = duration_element.text  # пример: "30 мин"
#         print(f'{duration_text=}')
#
#         # Извлекаем число из текста
#         match = re.search(r'(\d+)', duration_text)
#         if match:
#             minutes = int(match.group(1))
#             if minutes < min_time:
#                 min_time = minutes
#                 min_service = service
    except Exception as ex:
        print(f'{ex=}')
        continue
#
# if min_service:
#     # Пример получения названия услуги (предположим, оно в элементе с классом "service-title")  # изменено
#     service_name = min_service.find_element(By.CLASS_NAME, "service-title").text  # изменено
#     print(f"Услуга с минимальным временем: {service_name} ({min_time} мин)")
#     # При необходимости: min_service.click()
# else:
#     print("Услуги не найдены или время не определено.")

# min_time = float('inf')  # добавлено
# min_service = None      # добавлено
#
# for service in services:  # добавлено
#     print("Услуга:", services)
#
#     # Предполагаем, что время услуги хранится в элементе с классом "service-time" (например, "30 мин")  # добавлено
#     time_text = service.find_element(By.CLASS_NAME, "service-time").text  # добавлено
#     try:  # добавлено
#         minutes = int(time_text.split()[0])  # добавлено
#     except ValueError:  # добавлено
#         continue  # добавлено
#
#     if minutes < min_time:  # добавлено
#         min_time = minutes  # добавлено
#         min_service = service  # добавлено
#
# if min_service:  # добавлено
#     # Предполагаем, что название услуги находится в элементе с классом "service-title"  # добавлено
#     service_name = min_service.find_element(By.CLASS_NAME, "service-title").text  # добавлено
#     print(f"Услуга с минимальным временем: {service_name} ({min_time} мин)")  # добавлено
#     # При необходимости можно активировать услугу:  # добавлено
#     # min_service.click()  # добавлено
# else:  # добавлено
#     print("Услуги не найдены или время не удалось определить.")  # добавлено


# МОД: Пауза для наблюдения результатов (при необходимости)
time.sleep(5)
driver.quit()

