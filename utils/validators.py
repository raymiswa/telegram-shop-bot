import re


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+7\d{10}$", phone.replace(" ", "").replace("-", "")))


def normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-\(\)]", "", phone)
