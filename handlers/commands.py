from aiogram import Router, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from config import OWNER_ID, TELEGRAPH_AGREEMENT_URL
from services import (
    add_promo_code,
    create_or_extend_client,
    add_referred_user,
)
from db_models import get_user
from ui import show_main

router = Router()


@router.message(Command(commands=['start']))
async def start(message: Message, state: FSMContext):
    """Start command - show user agreement"""
    args = message.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            add_referred_user(referrer_id, message.from_user.id)
        except:
            pass

    data = await state.get_data()
    if data.get("accepted"):
        await show_main(message, state)
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    inline_keyboard = [
        [InlineKeyboardButton(text="✅ Принять", callback_data="accept")],
        [InlineKeyboardButton(text="📄 Открыть соглашение", url=TELEGRAPH_AGREEMENT_URL)]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await message.answer("<b>Перед использованием необходимо принять пользовательское соглашение:</b>", reply_markup=keyboard)


@router.message(Command("newcode"))
async def newcode(message: Message, command: CommandObject):
    """Admin command - create new promo code"""
    if message.from_user.id != OWNER_ID:
        return

    args = command.args
    if not args:
        await message.answer("Использование: /newcode [код] [дней] [активаций]")
        return

    parts = args.split()
    if len(parts) != 3:
        await message.answer("Неверное количество параметров.")
        return

    code = parts[0].upper()
    try:
        days = int(parts[1])
        activations = int(parts[2])
    except:
        await message.answer("Дни и активации должны быть числами.")
        return

    add_promo_code(code, days, activations)
    await message.answer(f"Промокод <b>{code}</b> создан:\n{days} дней\n{activations} активаций")


@router.message(Command("givesub"))
async def givesub(message: Message, command: CommandObject):
    """Admin command - give subscription to user"""
    if message.from_user.id != OWNER_ID:
        return

    args = command.args
    if not args:
        await message.answer("Использование: /givesub [user_id] [дней]")
        return

    parts = args.split()
    if len(parts) != 2:
        await message.answer("Неверное количество параметров.")
        return

    try:
        target_id = int(parts[0])
        days = int(parts[1])
    except:
        await message.answer("user_id и дни должны быть числами.")
        return

    months = days / 30
    sub_url = create_or_extend_client(target_id, months)
    await message.answer(f"Пользователю {target_id} выдано {days} дней.\nСсылка: {sub_url}")


@router.message(Command("message"))
async def admin_message(message: Message, command: CommandObject, bot: Bot):
    """Admin command - broadcast message to all users"""
    if message.from_user.id != OWNER_ID:
        return

    text = command.args
    if not text:
        await message.answer("Использование: /message [текст]")
        return

    success_count = 0
    # Get all users from database
    async with __import__('database').pool.acquire() as conn:
        users = await conn.fetch("SELECT user_id FROM users")

    for row in users:
        user_id = row['user_id']
        try:
            await bot.send_message(user_id, text)
            success_count += 1
        except:
            pass

    await message.answer(f"Рассылка завершена: {success_count} пользователей получили сообщение.")
