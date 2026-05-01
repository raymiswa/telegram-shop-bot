import re


def validate_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(re.match(r"^\+7\d{10}$", cleaned) or re.match(r"^8\d{10}$", cleaned))


def validate_trc20_address(address: str) -> bool:
    return address.startswith("T") and len(address) == 34


def convert_to_usdt(amount_rub: float, rate: float) -> float:
    return round(amount_rub / rate, 2)
