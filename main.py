from parser import YCParser
import time
from datetime import datetime

URL = "https://n82183.yclients.com/"
CITY = 'Москва'
depth_days = 30
today = datetime.now()


def main():
    parser = YCParser(url=URL, city=CITY,
                      st=3
                      )
    parser.open_site()
    parser.choose_city()
    br_count = len(parser.find_branches())
    print("Видим филиалов:", br_count)

    for br in range(br_count):
        branch_buttons = parser.find_branches()
        branch = branch_buttons[br]
        parser.choose_branch(branch)  # откатываемся к этой странице филиалов
        parser.choose_individual_services()
        parser.choose_specialist()

        m_count = len(parser.find_masters())
        print("Видим мастеров:", m_count)
        for m in range(1, m_count):  # 0 = Любой сотрудник
            master_buttons = parser.find_masters()
            master = master_buttons[m]
            parser.choose_master(master)  # откатываемся к этой странице мастеров
            parser.choose_service_page()
            parser.select_min_service()
            parser.choose_date_and_time()

            # parser.go_back(parser.depth['master'])
            # parser.go_back(parser.depth['service'])
            # parser.go_back(parser.depth['date_and_time'])
            # parser.go_back(parser.depth['service_page'])

            parser.click_working_days(depth_days)
            parser.count_timeslots()
            break
        # parser.go_back(parser.depth['branch'])
        break

    parser.quit()
    print(f'{parser.branches = }')
    print(f'{parser.masters = }')


if __name__ == "__main__":
    main()
