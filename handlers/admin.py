import logging
import aiohttp
from datetime import datetime, timedelta, timezone
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_ID, DEFAULT_SQUAD_UUID
import database as db
from services.remnawave import (
    remnawave_get_or_create_user,
    remnawave_add_to_squad
)


router = Router()


def is_admin(user_id: int) -> bool:
    """Проверить является ли пользователь администратором"""
    return user_id == ADMIN_ID


@router.message(Command("new_code"))
async def admin_new_code(message: Message):
    """Админ команда: создать новый промокод"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) < 4:
            raise ValueError("Not enough arguments")
        
        _, code, days, limit = parts[0], parts[1], int(parts[2]), int(parts[3])
    except (ValueError, IndexError):
        await message.answer("Формат:\n/new_code CODE DAYS LIMIT\n\nПример:\n/new_code SUMMER30 30 100")
        return

    # Создаём промокод
    db.create_promo_code(code.upper(), days, limit)

    await message.answer(
        f"✅ Промокод создан:\n\n"
        f"Код: {code.upper()}\n"
        f"Дней: {days}\n"
        f"Лимит использований: {limit}"
    )
    
    logging.info(f"Admin {message.from_user.id} created promo code {code.upper()}")


@router.message(Command("give_sub"))
async def admin_give_sub(message: Message):
    """Админ команда: выдать подписку пользователю"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError("Not enough arguments")
        
        _, tg_id_str, days_str = parts[0], parts[1], int(parts[2])
        tg_id = int(tg_id_str)
    except (ValueError, IndexError):
        await message.answer("Формат:\n/give_sub TG_ID DAYS\n\nПример:\n/give_sub 123456789 30")
        return

    if not db.acquire_user_lock(tg_id):
        await message.answer("❌ Пользователь занят, попробуй позже")
        return

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Создаём или получаем пользователя в Remnawave
            uuid, username = await remnawave_get_or_create_user(
                session, tg_id, days=days_str, extend_if_exists=True
            )

            if not uuid:
                await message.answer("❌ Ошибка при работе с Remnawave API")
                return

            # Добавляем в сквад
            await remnawave_add_to_squad(session, uuid)

            # Обновляем подписку в БД
            new_until = (datetime.now(timezone.utc) + timedelta(days=days_str)).isoformat()
            db.update_subscription(tg_id, uuid, username, new_until, DEFAULT_SQUAD_UUID)

        await message.answer(
            f"✅ Подписка выдана:\n\n"
            f"Пользователь: {tg_id}\n"
            f"Дней: {days_str}"
        )
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                tg_id,
                f"🎉 Вам выдана подписка на {days_str} дней!\n\n"
                f"Спасибо за использование сервиса SPN VPN!"
            )
        except Exception as e:
            logging.warning(f"Failed to notify user {tg_id}: {e}")
        
        logging.info(f"Admin {message.from_user.id} gave subscription to {tg_id} for {days_str} days")

    except Exception as e:
        logging.error(f"Give subscription error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    finally:
        db.release_user_lock(tg_id)


@router.message(Command("stats"))
async def admin_stats(message: Message):
    """Админ команда: получить статистику"""
    if not is_admin(message.from_user.id):
        return

    # TODO: Реализовать получение статистики
    await message.answer("Статистика ещё не реализована")
