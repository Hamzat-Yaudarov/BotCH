from aiogram import Router, F, types, Bot
from aiogram.filters import Command, CommandObject

from database import db
from config import OWNER_ID
from handlers.subscription import create_or_extend_subscription
from xui_client import xui


router = Router()


@router.message(Command("newcode"))
async def newcode(message: types.Message, command: CommandObject):
    """Команда для создания нового промокода (только для админа)"""
    if message.from_user.id != OWNER_ID:
        return

    args = command.args
    if not args:
        await message.answer(
            "<b>📝 Создание промокода</b>\n\n"
            "<b>Использование:</b>\n"
            "<code>/newcode КОД ДНЕЙ АКТИВАЦИЙ</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/newcode SUMMER2024 30 100</code>\n\n"
            "Это создаст промокод SUMMER2024 на 30 дней с 100 активациями"
        )
        return

    parts = args.split()
    if len(parts) != 3:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Укажите точно 3 параметра: КОД, ДНЕЙ, АКТИВАЦИЙ"
        )
        return

    code = parts[0].upper()
    try:
        days = int(parts[1])
        activations = int(parts[2])
    except:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Дни и активации должны быть числами"
        )
        return

    await db.create_promo_code(code, days, activations)
    await message.answer(
        "<b>✅ Промокод создан</b>\n\n"
        f"<b>Код:</b> {code}\n"
        f"<b>Дней:</b> {days}\n"
        f"<b>Активаций:</b> {activations}"
    )


@router.message(Command("givesub"))
async def givesub(message: types.Message, command: CommandObject):
    """Команда для выдачи подписки пользователю (только для админа)"""
    if message.from_user.id != OWNER_ID:
        return

    args = command.args
    if not args:
        await message.answer(
            "<b>🎁 Выдача подписки пользователю</b>\n\n"
            "<b>Использование:</b>\n"
            "<code>/givesub USER_ID ДНЕЙ</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/givesub 123456789 30</code>\n\n"
            "Это выдаст пользователю с ID 123456789 подписку на 30 дней"
        )
        return

    parts = args.split()
    if len(parts) != 2:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Укажите точно 2 параметра: USER_ID, ДНЕЙ"
        )
        return

    try:
        target_id = int(parts[0])
        days = int(parts[1])
    except:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "USER_ID и дни должны быть числами"
        )
        return

    try:
        months = days / 30
        sub_url = await create_or_extend_subscription(target_id, months)
        await message.answer(
            "<b>✅ Подписка выдана</b>\n\n"
            f"<b>Пользователь:</b> {target_id}\n"
            f"<b>Дней:</b> {days}\n\n"
            "<b>Ссылка подписки:</b>\n"
            f"<code>{sub_url}</code>"
        )
    except Exception as e:
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Не удалось выдать подписку. Проверьте ID пользователя."
        )


@router.message(Command("message"))
async def admin_message(message: types.Message, command: CommandObject, bot: Bot):
    """Команда для массовой рассылки сообщений (только для админа)"""
    if message.from_user.id != OWNER_ID:
        return

    text = command.args
    if not text:
        await message.answer(
            "<b>📢 Массовая рассылка</b>\n\n"
            "<b>Использование:</b>\n"
            "<code>/message ТЕКСТ_СООБЩЕНИЯ</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/message Привет! Это сообщение от администратора</code>"
        )
        return

    user_ids = await db.get_all_user_ids()
    success_count = 0
    failed_count = 0

    await message.answer(
        "<b>📊 Рассылка начата</b>\n\n"
        f"Отправляю сообщение {len(user_ids)} пользователям...\n\n"
        "<i>Это может занять некоторое время</i>"
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success_count += 1
        except:
            failed_count += 1

    await message.answer(
        "<b>✅ Рассылка завершена</b>\n\n"
        f"<b>Успешно отправлено:</b> {success_count}\n"
        f"<b>Ошибок:</b> {failed_count}\n"
        f"<b>Всего пользователей:</b> {len(user_ids)}"
    )
