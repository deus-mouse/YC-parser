from handler import Handler

URL_city = "https://n82183.yclients.com/"
URL_masters_Zvezdinka = 'https://n248723.yclients.com/company/25809/personal/select-master?o=m739791'
URL_masters_Belorusskaya = 'https://n625088.yclients.com/company/266762/personal/select-master?o='

depth_days = 30  # глубина сканирования


def main():
    handler = Handler(url=URL_masters_Belorusskaya, depth=depth_days, freeze=5)
    handler.run()


if __name__ == "__main__":
    main()
