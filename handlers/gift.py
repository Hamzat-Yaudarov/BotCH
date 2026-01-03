from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import db
from config import NEWS_CHANNEL_ID, NEWS_CHANNEL_URL
from handlers.subscription import create_or_extend_subscription
from xui_client import xui


router = Router()


@router.callback_query(F.data == "gift")
async def gift(callback: CallbackQuery):
    """Показать информацию о подарке"""
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_gift")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(
        "<b>🎉 Бесплатный подарок</b>\n\n"
        "Подпишитесь на наш канал и получите <b>3 дня бесплатной подписки!</b>\n\n"
        f"Канал: {NEWS_CHANNEL_URL}\n\n"
        "<i>После подписки нажмите кнопку ниже</i>",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "check_gift")
async def check_gift(callback: CallbackQuery, bot: Bot):
    """Проверить получил ли пользователь подарок"""
    await callback.answer()
    user_id = callback.from_user.id

    # Проверяем уже ли получил подарок
    if await db.has_user_received_gift(user_id):
        await callback.message.edit_text(
            "<b>❌ Подарок уже получен</b>\n\n"
            "Вы уже использовали эту программу. "
            "Спасибо за вашу поддержку!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
        )
        return

    try:
        # Проверяем подписан ли на канал
        member = await bot.get_chat_member(NEWS_CHANNEL_ID, user_id)

        if member.status in ("member", "administrator", "creator"):
            # Пользователь подписан - даём подарок
            await create_or_extend_subscription(user_id, 0.1)  # ~3 дня
            await db.add_user_gift(user_id)

            client = await db.get_user_client(user_id)
            sub_url = xui.get_subscription_url(client['sub_id'])

            await callback.message.edit_text(
                "<b>🎉 Подарок получен!</b>\n\n"
                "<b>+3 дня бесплатной подписки</b>\n\n"
                "Ссылка для подключения:\n"
                f"<code>{sub_url}</code>\n\n"
                "<i>Спасибо, что подписались на наш канал!</i>"
            )
        else:
            await callback.message.edit_text(
                "<b>❌ Подписка не найдена</b>\n\n"
                f"Мы не обнаружили вашу подписку на канал {NEWS_CHANNEL_URL}\n\n"
                "Пожалуйста:\n"
                "1. Подпишитесь на канал\n"
                "2. Нажмите «Проверить подписку» ещё раз\n\n"
                "<i>Убедитесь, что вы подписаны от того же аккаунта</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Проверить ещё раз", callback_data="check_gift")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
                ])
            )
    except Exception as e:
        await callback.message.edit_text(
            "<b>⚠️ Ошибка проверки</b>\n\n"
            "Произошла ошибка при проверке подписки на канал. "
            "Пожалуйста, попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
        )
