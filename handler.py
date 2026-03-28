import argparse

from parser import YClientsParser, print_table, results_to_json


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Парсер свободного времени мастеров YCLIENTS.")
    parser.add_argument("url", help="Ссылка на страницу выбора мастеров.")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Глубина сканирования в днях. По умолчанию: 30.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Ограничить количество мастеров для тестового прогона.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Запускать браузер не в headless-режиме.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Печатать только JSON без таблицы.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    if args.days <= 0:
        raise SystemExit("--days должен быть больше 0")

    with YClientsParser(
        masters_url=args.url,
        days_ahead=args.days,
        headless=not args.headed,
    ) as parser:
        results = parser.parse(master_limit=args.limit)

    if not args.json_only:
        print_table(results)
        print()
    print(results_to_json(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
