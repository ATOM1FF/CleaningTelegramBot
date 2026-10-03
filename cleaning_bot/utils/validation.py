import re

PHONE_PATTERN = re.compile(r"^\+?998\d{9}$")
SIZE_PATTERN = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*[xх×*]\s*(\d+(?:[.,]\d+)?)\s*$", re.IGNORECASE)


def normalize_phone(value: str) -> str | None:
    normalized = re.sub(r"[\s()-]", "", value)
    if not PHONE_PATTERN.fullmatch(normalized):
        return None
    return normalized if normalized.startswith("+") else f"+{normalized}"


def parse_size(value: str) -> tuple[float, float] | None:
    match = SIZE_PATTERN.fullmatch(value)
    if not match:
        return None
    width = float(match.group(1).replace(",", "."))
    length = float(match.group(2).replace(",", "."))
    if width <= 0 or length <= 0 or width > 100 or length > 100:
        return None
    return width, length
