from parser import YCParser
from handler import Handler
import time
from datetime import datetime

URL_city = "https://n82183.yclients.com/"
URL_masters = 'https://n248723.yclients.com/company/25809/personal/select-master?o=m739791'
URL_masters_Belorusskaya = 'https://n625088.yclients.com/company/266762/personal/select-master?o='
CITY = 'Москва'
depth_days = 30  # глубина сканирования
today = datetime.now()


def main():
    handler = Handler(st=1, url=URL_masters_Belorusskaya, today=today, depth_days=depth_days)
    handler.open_site(URL_city)

    city_on_page = handler.find_city(CITY)
    masters_on_page = handler.find_masters()

    if city_on_page:
        handler.start_from_city()
    elif masters_on_page:
        handler.start_from_masters()



    # parser = YCParser(url=URL_city, city=CITY,
    #                   st=1
    #                   )

    # parser.open_site()
    # parser.choose_city()
    # br_count = len(parser.find_branches())
    # print("Видим филиалов:", br_count)
    #
    # for br in range(br_count):
    #     branch_buttons = parser.find_branches()
    #     branch = branch_buttons[br]
    #     branch_name = branch.text.strip()
    #     print(f'Выбираем филиал: {branch_name}')
    #
    #     parser.choose_branch(branch)  # откатываемся к этой странице филиалов
    #     parser.choose_individual_services()
    #     parser.choose_specialist()

        # master_buttons = parser.find_masters()
        # m_count = len(master_buttons)
        # print("Видим мастеров:", m_count-1)
        #
        # while len(parser.masters) < m_count-1:  # 0 = "Любой специалист"
        # # while len(parser.masters) < 2:  # 0 = "Любой специалист"
        #     print(f'--------> посчитано мастеров {len(parser.masters)}')
        #     master_buttons = parser.find_masters()
        #     master = next((master for master in master_buttons if master.text.strip() not in parser.masters and master.text.strip() != "Любой специалист"), None)
        #     master_name = master.text.strip()
        #     print(f'{master_name = }')
        #
        #     parser.choose_master(master)  # страница мастеров
        #     parser.choose_service_page()
        #     min_time = parser.select_min_service()
        #     parser.choose_date_and_time()
        #     parser.check_working_days(today, depth_days, master_name, min_time, branch_name)
        #     parser.upsert_branches_dict(master_name, branch_name)
        #
        #     parser.go_back(parser.depths['master'])  # откатываемся к странице мастеров
        #     # parser.go_back(parser.depth['service'])
        #     # parser.go_back(parser.depth['date_and_time'])
        #     # parser.go_back(parser.depth['service_page'])
        #     print(f'{parser.branches = }')
        #     print(f'{parser.masters = }')
        #     # break  # todo remove
        # # parser.go_back(parser.depth['branch'])
        # break

    # parser.quit()
    # print(f'{parser.branches = }')
    # print(f'{parser.masters = }')


if __name__ == "__main__":
    main()
