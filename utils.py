import random
import string
from datetime import datetime


def generate_random_string(length: int = 16) -> str:
    """Generate random string of specified length"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


async def calculate_remaining_time(expiry_time_ms: int) -> str:
    """Calculate remaining subscription time and return formatted string"""
    now = int(datetime.now().timestamp() * 1000)
    if expiry_time_ms <= now:
        return "Подписка истекла"
    remaining_ms = expiry_time_ms - now
    days = remaining_ms // (24 * 60 * 60 * 1000)
    hours = (remaining_ms % (24 * 60 * 60 * 1000)) // (60 * 60 * 1000)
    minutes = (remaining_ms % (60 * 60 * 1000)) // (60 * 1000)
    return f"{days} дн. {hours} ч. {minutes} мин."
