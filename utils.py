import random
import string
import uuid as uuid_lib
from datetime import datetime


def generate_random_string(length: int = 16) -> str:
    """Генерировать случайную строку из букв и цифр"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_uuid() -> str:
    """Генерировать UUID"""
    return str(uuid_lib.uuid4())


def get_current_timestamp_ms() -> int:
    """Получить текущее время в миллисекундах"""
    return int(datetime.utcnow().timestamp() * 1000)


async def calculate_remaining_time(expiry_time_ms: int) -> str:
    """
    Вычислить оставшееся время до истечения подписки

    Args:
        expiry_time_ms: Время истечения в миллисекундах

    Returns:
        Строка с оставшимся временем
    """
    now = get_current_timestamp_ms()

    if expiry_time_ms <= now:
        return "Подписка истекла"

    remaining_ms = expiry_time_ms - now
    days = remaining_ms // (24 * 60 * 60 * 1000)
    hours = (remaining_ms % (24 * 60 * 60 * 1000)) // (60 * 60 * 1000)
    minutes = (remaining_ms % (60 * 60 * 1000)) // (60 * 1000)

    return f"{days} дн. {hours} ч. {minutes} мин."


def calculate_expiry_time(add_months: float) -> int:
    """
    Вычислить время истечения с добавлением месяцев

    Args:
        add_months: Количество месяцев для добавления (может быть дробным)

    Returns:
        Время истечения в миллисекундах
    """
    add_ms = int(add_months * 30 * 24 * 60 * 60 * 1000)
    return get_current_timestamp_ms() + add_ms
