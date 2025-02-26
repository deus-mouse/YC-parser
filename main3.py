# МОД: Импорт необходимых модулей
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time  # МОД: Для паузы

# МОД: Инициализация драйвера (убедитесь, что chromedriver доступен в PATH)
driver = webdriver.Chrome()

# МОД: Открытие сайта
driver.get("https://n82183.yclients.com/")

# МОД: Ожидание появления кнопки с текстом "Москва"
wait = WebDriverWait(driver, 10)
moscow_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Москва')]")))  # МОД: Поиск элемента с текстом "Москва"

print("Нажимаем на кнопку с текстом 'Москва':", moscow_btn.text)
moscow_btn.click()  # МОД: Клик по кнопке "Москва"

# button = driver.find_element(By.CLASS_NAME, "address")
# print("Нажимаем на кнопку address:", button.text)
# button.click()  # МОД: Клик по кнопке "Москва"

buttons = driver.find_elements(By.CLASS_NAME, "address")
print("Видим филиалов:", len(buttons))

buttons[0].click()  # Выбираем первую кнопку

# МОД: Пауза для наблюдения результатов (при необходимости)
time.sleep(2)
driver.quit()