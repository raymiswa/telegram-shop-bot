import random
import string


def generate_pickup_code() -> str:
    letter = random.choice(string.ascii_uppercase)
    number = "".join(random.choices(string.digits, k=4))
    return f"#{letter}{number}"


def convert_to_usdt(amount_rub: float, rate: float) -> float:
    return round(amount_rub / rate, 2)


def validate_trc20_address(address: str) -> bool:
    return address.startswith("T") and len(address) == 34
