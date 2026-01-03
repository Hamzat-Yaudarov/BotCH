from aiogram import Router, F, types, Bot
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from states import SubscriptionState
from database import db
from payment import payment
from config import PRICES, OWNER_ID
from utils import generate_random_string, calculate_expiry_time, calculate_remaining_time, get_current_timestamp_ms
from xui_client import xui


router = Router()


@router.callback_query(F.data == "subscribe")
async def subscribe(callback: CallbackQuery, state: FSMContext):
    """Начало процесса подписки"""
    await callback.answer()

    inline_keyboard = []
    for months, price in PRICES.items():
        inline_keyboard.append([InlineKeyboardButton(text=f"{months} мес. — {price} ₽", callback_data=f"duration_{months}")])
    inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text(
        "<b>📅 Выберите срок подписки</b>\n\n"
        "Чем дольше подписка, тем больше экономия!",
        reply_markup=keyboard
    )
    await state.set_state(SubscriptionState.select_duration)


@router.callback_query(StateFilter(SubscriptionState.select_duration), F.data.startswith("duration_"))
async def select_duration(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбор срока подписки"""
    await callback.answer()
    user_id = callback.from_user.id
    months = int(callback.data.split("_")[1])

    # Проверяем владелец ли это
    if user_id == OWNER_ID:
        try:
            await create_or_extend_subscription(user_id, months)
            client = await db.get_user_client(user_id)
            sub_url = xui.get_subscription_url(client['sub_id'])

            existing = await db.client_exists(user_id)
            action = "продлена" if existing else "создана"

            await callback.message.edit_text(
                f"<b>✅ Подписка {action} бесплатно!</b>\n\n"
                "Ссылка для подключения:\n"
                f"<code>{sub_url}</code>"
            )
        except Exception as e:
            await callback.message.edit_text(
                "<b>⚠️ Ошибка</b>\n\n"
                "Произошла ошибка при создании подписки. "
                "Пожалуйста, попробуйте позже."
            )
        await state.clear()
        return

    # Обычный пользователь - переходим к оплате
    await state.update_data(months=months, price=PRICES[months])
    inline_keyboard = [
        [InlineKeyboardButton(text="💳 Оплатить через CryptoBot", callback_data="pay_cryptobot")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text(
        "<b>💰 Оплата подписки</b>\n\n"
        f"<b>Период:</b> {months} месяцев\n"
        f"<b>Сумма:</b> {PRICES[months]} ₽\n\n"
        "Выберите способ оплаты:",
        reply_markup=keyboard
    )
    await state.set_state(SubscriptionState.select_payment)


@router.callback_query(StateFilter(SubscriptionState.select_payment), F.data == "pay_cryptobot")
async def pay_cryptobot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Создание счёта в CryptoBot"""
    await callback.answer()

    try:
        data = await state.get_data()
        months = data['months']
        price = data['price']
        order_id = generate_random_string(10)
        bot_username = (await bot.get_me()).username

        pay_url, invoice_id = await payment.create_invoice(price, order_id, bot_username)
        await state.update_data(invoice_id=invoice_id, pay_url=pay_url)

        inline_keyboard = [
            [InlineKeyboardButton(text="💸 Перейти к оплате", url=pay_url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_payment")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await callback.message.edit_text(
            "<b>💳 Оплата готова</b>\n\n"
            "Нажмите кнопку ниже, чтобы перейти к оплате.\n\n"
            "<i>После успешной оплаты нажмите «Проверить оплату»</i>",
            reply_markup=keyboard
        )
        await state.set_state(SubscriptionState.waiting_payment)
    except Exception as e:
        await callback.message.edit_text(
            "<b>⚠️ Ошибка</b>\n\n"
            "Не удалось создать счёт на оплату. "
            "Пожалуйста, попробуйте позже или свяжитесь с поддержкой."
        )


@router.callback_query(StateFilter(SubscriptionState.waiting_payment), F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    await callback.answer()

    data = await state.get_data()
    invoice_id = data['invoice_id']
    pay_url = data.get('pay_url')
    months = data['months']
    user_id = callback.from_user.id

    is_paid = await payment.check_payment(invoice_id)

    if is_paid:
        try:
            await create_or_extend_subscription(user_id, months, is_paid=True)
            client = await db.get_user_client(user_id)
            sub_url = xui.get_subscription_url(client['sub_id'])

            await callback.message.edit_text(
                "<b>🎉 Платёж прошёл успешно!</b>\n\n"
                f"<b>Подписка активирована на {months} месяцев</b>\n\n"
                "Ссылка для подключения:\n"
                f"<code>{sub_url}</code>\n\n"
                "<i>Скопируйте ссылку в приложение VPN</i>"
            )
        except Exception as e:
            await callback.message.edit_text(
                "<b>⚠️ Ошибка активации</b>\n\n"
                "Платёж прошёл, но произошла ошибка при активации подписки. "
                "Свяжитесь с поддержкой, указав номер счёта."
            )
        await state.clear()
    else:
        inline_keyboard = [
            [InlineKeyboardButton(text="💸 Перейти к оплате", url=pay_url)],
            [InlineKeyboardButton(text="✅ Проверить ещё раз", callback_data="check_payment")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await callback.message.edit_text(
            "<b>⏳ Платёж не найден</b>\n\n"
            "Мы не обнаружили вашего платежа. Возможно, он ещё обрабатывается.\n\n"
            "Попробуйте:\n"
            "1. Проверить ещё раз через 30 секунд\n"
            "2. Убедиться, что оплата прошла\n"
            "3. Свяжитесь с поддержкой, если проблема сохранится",
            reply_markup=keyboard
        )


async def create_or_extend_subscription(
    user_id: int,
    add_months: float,
    is_paid: bool = False
) -> str:
    """
    Создать или продлить подписку пользователя

    Args:
        user_id: ID пользователя
        add_months: Количество месяцев для добавления
        is_paid: Была ли оплачена подписка

    Returns:
        URL подписки
    """
    from utils import generate_uuid

    client = await db.get_user_client(user_id)

    if client:
        # Продлеваем существующую подписку
        client_uuid = client['uuid']
        client_sub_id = client['sub_id']
        client_email = client['email']

        current_expiry = xui.get_client_expiry(client_email)
        add_ms = int(add_months * 30 * 24 * 60 * 60 * 1000)
        new_expiry = current_expiry + add_ms
    else:
        # Создаём новую подписку
        client_uuid = generate_uuid()
        client_sub_id = generate_random_string(16)
        client_email = generate_random_string(12)
        new_expiry = calculate_expiry_time(add_months)

    # Обновляем/создаём клиента в XUI панели
    xui.create_or_update_client(client_uuid, client_email, client_sub_id, new_expiry, user_id)

    # Сохраняем в БД
    await db.create_user_client(user_id, client_uuid, client_sub_id, client_email, new_expiry)

    # Если оплачено - отмечаем пользователя и даём бонус рефереру
    if is_paid:
        # Определяем сумму платежа (только для стандартных пакетов)
        months_int = int(add_months)
        amount = PRICES.get(months_int, 0)

        await db.mark_user_paid(user_id, amount, f"invoice_{user_id}_{get_current_timestamp_ms()}")

        # Даём бонус рефереру (+7 дней)
        referrer_id = await db.get_referrer_id(user_id)
        if referrer_id:
            try:
                await create_or_extend_subscription(referrer_id, 7 / 30)  # 7 дней
            except Exception as e:
                pass  # Silently fail if referrer bonus fails

    return xui.get_subscription_url(client_sub_id)
