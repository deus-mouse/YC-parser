from handler import Handler
import time

URL_city = "https://n82183.yclients.com/"
URL_masters_Zvezdinka = 'https://n248723.yclients.com/company/25809/personal/select-master?o=m739791'
URL_masters_Belorusskaya = 'https://n625088.yclients.com/company/266762/personal/select-master?o='
CITY = 'Москва'
depth_days = 30  # глубина сканирования


def main():
    handler = Handler(freeze=1, url=URL_masters_Zvezdinka, depth=depth_days)
