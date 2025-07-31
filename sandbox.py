def check_working_days(self):
    elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.calendar-day[data-locator="working_day"], div.calendar-day[data-locator="non_working_day"]')
    filtered_elements = []
    for el in elements:
        if el.get_attribute("data-locator") == "non_working_day":
            continue
        filtered_elements.append(el)
    elements = filtered_elements
    # остальная часть метода...

masters = {"Рома": 1000, "Антон": 1000}
master_buttons = {"Рома": 1000, "Антон": 1000, "Маринаfff": 1000, "Лена": 1000}
master = next((name for name in master_buttons if name not in masters), None)  # ← добавил эту строку
print(master)
