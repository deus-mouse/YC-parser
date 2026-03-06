import re

def convert_to_minutes(time_text):
    # Замена неразрывных пробелов, обрезка лишних пробелов
    time_text = time_text.replace('\xa0', ' ').strip()
    # Регулярное выражение с именованными группами для часов и минут
    pattern = r'^(?:(?P<hours>\d+)\s*ч)?\s*(?:(?P<minutes>\d+)\s*мин)?$'
    match = re.match(pattern, time_text)
    if match:
        hours = int(match.group('hours')) if match.group('hours') else 0
        minutes = int(match.group('minutes')) if match.group('minutes') else 0
        total = hours * 60 + minutes
        if total > 0:
            return total
    return float('inf')