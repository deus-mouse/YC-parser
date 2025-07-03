
def get_calendar_day_status(self):
    from datetime import datetime
    elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.calendar-day')
    today = datetime.now().date()
    statuses = []
    for el in elements:
        date_str = el.get_attribute('data-locator-date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj < today:
            status = 'past'
        elif date_obj == today:
            status = 'today'
        else:
            status = 'future'
        statuses.append((el, date_obj, status))
    return statuses