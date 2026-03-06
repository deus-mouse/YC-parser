from handler import Handler

URL_city = "https://n82183.yclients.com/"
zv = 'https://n248723.yclients.com/company/25809/personal/select-master?o=m739791'
bel = 'https://n625088.yclients.com/company/266762/personal/select-master?o='

depth_days = 30  # глубина сканирования


def main():
    handler = Handler(url=bel, depth=depth_days)
    handler.run()


if __name__ == "__main__":
    main()

