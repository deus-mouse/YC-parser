from parser import YCParser


def main():
    parser = YCParser(sleep_time=0.5)
    # parser.open_site("https://n82183.yclients.com/")
    parser.open_site("https://n82183.yclients.com/company/1041424/personal/select-master?o=")
    # parser.choose_city()
    # parser.choose_address()
    # parser.choose_individual_services()
    parser.choose_specialist()
    parser.choose_master()
    parser.choose_service()
    parser.select_min_service()
    parser.choose_date_and_time()
    parser.click_working_days()
    parser.count_timeslots()
    parser.quit()

if __name__ == "__main__":
    main()