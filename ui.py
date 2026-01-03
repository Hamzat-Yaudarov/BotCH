from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import ADMIN_USERNAME
from services import has_client, is_subscription_active


async def show_main(target: Message | CallbackQuery, state: FSMContext = None):
    """Show main menu"""
    user_id = target.from_user.id if isinstance(target, Message) else target.from_user.id
    client_exists = await has_client(user_id)
    active = await is_subscription_active(user_id)

    inline_keyboard = []

    if active:
        row = [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscribe")]
    else:
        row = [InlineKeyboardButton(text="🆕 Оформить подписку", callback_data="subscribe")]

    if client_exists:
        row.append(InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"))

    inline_keyboard.append(row)

    inline_keyboard += [
        [InlineKeyboardButton(text="📱 Как подключиться", callback_data="how_connect")],
        [InlineKeyboardButton(text="🎁 Бонус за друга", callback_data="referral")],
        [InlineKeyboardButton(text="🔑 Ввести промокод", callback_data="promo")],
        [InlineKeyboardButton(text="☎️ Поддержка", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton(text="🎉 Получить подарок", callback_data="gift")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    text = "<b>🚀 SPN — Ускоритель интернета</b>\n\nВыберите действие:"
    if isinstance(target, Message):
        await target.answer(text, reply_markup=keyboard)
    else:
        try:
            await target.message.edit_text(text, reply_markup=keyboard)
        except:
            await target.message.answer(text, reply_markup=keyboard)
