import re


def parse_date(date: str) -> str:
    return re.sub(r'\?|y', '', date, flags=re.IGNORECASE) if date else None
