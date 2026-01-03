from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import db


router = Router()


@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery, bot: Bot):
    """Показать реферальную программу"""
    await callback.answer()
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    # Получаем статистику
    all_referrals = await db.get_referrals(user_id)
    paid_referrals = await db.get_paid_referrals(user_id)

    total_referred = len(all_referrals)
    paid_referred = len(paid_referrals)

    text = (
        "<b>🎁 Реферальная программа</b>\n\n"
        "<b>Зарабатывайте вместе с нами!</b>\n\n"
        "<b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "<b>📊 Статистика:</b>\n"
        f"• Всего приглашено: <b>{total_referred}</b>\n"
        f"• Купили подписку: <b>{paid_referred}</b>\n\n"
        "<b>💎 Ваш доход:</b>\n"
        f"За каждого друга, который купит подписку, вы получите <b>+7 дней</b> бесплатно!\n\n"
        "<i>Поделитесь ссылкой и начните зарабатывать прямо сейчас</i>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)
