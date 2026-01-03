from aiogram import Router, F, types
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from states import SubscriptionState
from database import db
from handlers.subscription import create_or_extend_subscription
from xui_client import xui


router = Router()


@router.callback_query(F.data == "promo")
async def promo(callback: types.CallbackQuery, state: FSMContext):
    """Показать окно ввода промокода"""
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(
        "<b>🎟️ Активировать промокод</b>\n\n"
        "Если у вас есть промокод, введите его ниже:",
        reply_markup=keyboard
    )
    await state.set_state(SubscriptionState.enter_promo)


@router.message(StateFilter(SubscriptionState.enter_promo))
async def process_promo(message: types.Message, state: FSMContext):
    """Обработить введённый промокод"""
    code = message.text.strip().upper()

    promo = await db.get_promo_code(code)

    if not promo:
        await message.answer(
            "<b>❌ Промокод не найден</b>\n\n"
            "Убедитесь, что вы правильно ввели код. "
            "Если проблема сохранится, свяжитесь с поддержкой."
        )
        await state.clear()
        return

    if promo['activations_left'] <= 0:
        await message.answer(
            "<b>❌ Промокод истёк</b>\n\n"
            "К сожалению, этот промокод больше не доступен. "
            "Попробуйте другой код или оформите платную подписку."
        )
        await state.clear()
        return

    # Используем промокод
    used = await db.use_promo_code(code)
    if not used:
        await message.answer(
            "<b>❌ Ошибка активации</b>\n\n"
            "Не удалось активировать промокод. Попробуйте позже."
        )
        await state.clear()
        return

    # Создаём/продлеваем подписку
    days = promo['days']
    months = days / 30

    try:
        await create_or_extend_subscription(message.from_user.id, months)
        client = await db.get_user_client(message.from_user.id)
        sub_url = xui.get_subscription_url(client['sub_id'])

        await message.answer(
            "<b>✅ Промокод успешно активирован!</b>\n\n"
            f"<b>Добавлено:</b> +{days} дней\n\n"
            "Ссылка для подключения:\n"
            f"<code>{sub_url}</code>\n\n"
            "<i>Скопируйте ссылку в приложение VPN</i>"
        )
    except Exception as e:
        await message.answer(
            "<b>⚠️ Ошибка при активации</b>\n\n"
            "Промокод активирован, но произошла ошибка при создании подписки. "
            "Свяжитесь с поддержкой."
        )

    await state.clear()
