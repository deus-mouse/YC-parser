from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# Настройка браузера
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Запуск без интерфейса браузера (опционально)
driver = webdriver.Chrome(options=options)


def get_salon_availability(url):
    driver.get(url)

    # Шаг 1: Выбор первого филиала
    print('1')
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-locator="branch_address"]'))
    )
    print(2)

    branches = driver.find_elements(By.CSS_SELECTOR, '[data-locator="branch_address"]')
    print(f'{branches = }')

    branches[0].click()  # Выбираем первый филиал




    # Шаг 2: Выбор "любой мастер"
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "master-selection"))
    )
    any_master_button = driver.find_element(By.XPATH, "//button[contains(text(), 'любой мастер')]")
    print(f'{any_master_button = }')

    any_master_button.click()

    # Шаг 3: Выбор первой услуги в первом выпадающем списке
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "services"))
    )
    services_dropdown = Select(driver.find_element(By.CLASS_NAME, "services-dropdown"))
    services_dropdown.select_by_index(0)  # Выбираем первую услугу

    # Шаг 4: Определение загруженности в календаре
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "calendar"))
    )
    dates = driver.find_elements(By.CLASS_NAME, "calendar-date")

    availability = []
    for date in dates:
        date_text = date.get_attribute("data-date")
        slots = date.find_elements(By.CLASS_NAME, "available-slot")
        availability.append({
            "date": date_text,
            "slots": len(slots)
        })

    # Закрыть браузер
    driver.quit()

    # Преобразовать в DataFrame и сохранить
    df = pd.DataFrame(availability)
    df.to_csv("salon_availability.csv", index=False)
    return df


# URL первой страницы
url = "https://n625088.yclients.com/select-city/2/select-branch?o="
availability_data = get_salon_availability(url)
print(availability_data)