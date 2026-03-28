#!/usr/bin/env python3
"""
Парсер свободного времени мастеров на сайте онлайн-записи YClients.

Использование:
    python main.py
    python main.py --url "https://..." --depth 30
"""

import argparse
from parser import BookingParser, MasterFreeTime

DEFAULT_URL = "https://n625088.yclients.com/company/266762/personal/select-master?o="
DEFAULT_DEPTH = 30


def main():
    arg_parser = argparse.ArgumentParser(description="Парсер свободного времени мастеров YClients")
    arg_parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL страницы с мастерами (по умолчанию: {DEFAULT_URL})",
    )
    arg_parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Глубина сканирования в днях (по умолчанию: {DEFAULT_DEPTH})",
    )
    args = arg_parser.parse_args()

    parser = BookingParser(url=args.url, depth_days=args.depth)
    results = parser.run()

    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ: Мастера и их свободное время")
    print("=" * 50)

    for m in sorted(results, key=lambda x: -x.free_minutes):
        print(f"  {m.name}: {m.free_minutes} мин")

    print("=" * 50)
    total = sum(m.free_minutes for m in results)
    print(f"Всего свободных минут: {total}")
    print("=" * 50)


if __name__ == "__main__":
    main()
