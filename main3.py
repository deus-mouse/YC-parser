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

# МОД: Ожидание появления элементов кнопок выбора города по альтернативному селектору
wait = WebDriverWait(driver, 10)
cities = wait.until(EC.presence_of_all_elements_located(
    (By.XPATH, "//a[contains(@href, 'select-city')]")  # МОД: Изменён селектор для выбора города
))

if cities:
    first_city = cities[0]
    print("Выбираем город:", first_city.text)
    # МОД: Клик по первому городу
    first_city.click()
else:
    print("Города не найдены!")

# МОД: Пауза для наблюдения результатов (при необходимости)
time.sleep(5)
driver.quit()