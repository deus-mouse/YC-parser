from parser import YCParser

URL = "https://n82183.yclients.com/"
CITY = 'Москва'


def main():
    parser = YCParser(url=URL, city=CITY, st=3)
    parser.open_site()
    # parser.open_site("https://n82183.yclients.com/company/1041424/personal/select-master?o=")
    parser.choose_city()
    branch_buttons = parser.find_branchs()
    for branch in branch_buttons:
        parser.choose_branch(branch)
        # parser.choose_individual_services()
        # parser.choose_specialist()
        # parser.choose_master()
        # parser.choose_service()
        # parser.select_min_service()
        # parser.choose_date_and_time()
        # parser.click_working_days()
        # parser.count_timeslots()
        # parser.quit()


if __name__ == "__main__":
    main()
