from aiogram import Router, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import (
    OWNER_ID,
    NEWS_CHANNEL_ID,
    NEWS_CHANNEL_URL,
    PRICES,
    GIFT_DAYS,
)
from models import SubscriptionState
from services import (
    has_client,
    is_subscription_active,
    create_or_extend_client,
    get_referral_stats,
    activate_promo_code,
    add_user_gift_db,
    has_user_received_gift_db,
)
from db_models import get_user
from utils import calculate_remaining_time, generate_random_string
from xui_api import get_client_expiry
from cryptobot_api import create_cryptobot_invoice, check_cryptobot_payment
from ui import show_main

router = Router()


@router.callback_query(lambda c: c.data == "accept")
async def accept(callback: CallbackQuery, state: FSMContext):
    """Accept user agreement"""
    await callback.answer()
    await state.update_data(accepted=True)
    try:
        await callback.message.delete()
    except:
        pass
    await show_main(callback, state)


@router.callback_query(lambda c: c.data == "my_subscription")
async def my_subscription(callback: CallbackQuery):
    """Show user's subscription details"""
    await callback.answer()
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.message.edit_text("❌ У вас нет активной подписки.")
        return

    email = user["email"]
    try:
        expiry_time = get_client_expiry(email)
        remaining = await calculate_remaining_time(expiry_time)
        sub_url = f"http://195.133.21.73:2096/sub/{user['sub_id']}"
        text = f"<b>📊 Ваша подписка</b>\n\nОсталось: <b>{remaining}</b>\n\nСсылка для подключения:\n<code>{sub_url}</code>"
    except Exception as e:
        text = f"Ошибка получения информации."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "gift")
async def gift(callback: CallbackQuery):
    """Show gift offer"""
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проверить", callback_data="check_gift")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(
        f"<b>🎉 Подарок за подписку на канал</b>\n\nПодпишись на {NEWS_CHANNEL_URL} и получи <b>{GIFT_DAYS} дня бесплатно</b>!",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data == "check_gift")
async def check_gift(callback: CallbackQuery, bot: Bot):
    """Check if user is subscribed to news channel and give gift"""
    await callback.answer()
    user_id = callback.from_user.id
    if await has_user_received_gift_db(user_id):
        await callback.message.edit_text("❌ Вы уже получили подарок.")
        return

    try:
        member = await bot.get_chat_member(NEWS_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            sub_url = await create_or_extend_client(user_id, GIFT_DAYS / 30)
            await add_user_gift_db(user_id)
            await callback.message.edit_text(
                f"<b>🎉 Подарок получен!</b>\n+{GIFT_DAYS} дня к подписке\n\nВаша ссылка:\n<code>{sub_url}</code>"
            )
        else:
            await callback.message.edit_text("❌ Вы не подписаны на канал.\nПодпишитесь и нажмите «Проверить» снова.")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка проверки: {str(e)}")


@router.callback_query(lambda c: c.data == "referral")
async def referral(callback: CallbackQuery, bot: Bot):
    """Show referral program"""
    await callback.answer()
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    total_referred, paid_referred = await get_referral_stats(user_id)

    text = f"<b>🎁 Бонус за друга</b>\n\nВаша реферальная ссылка:\n<code>{ref_link}</code>\n\nПриглашено: <b>{total_referred}</b>\nКупили подписку: <b>{paid_referred}</b>\n\nЗа каждого купившего — <b>+7 дней</b> к вашей подписке!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "promo")
async def promo(callback: CallbackQuery, state: FSMContext):
    """Start promo code input"""
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text("<b>🔑 Введите промокод</b>", reply_markup=keyboard)
    await state.set_state(SubscriptionState.enter_promo)


@router.message(StateFilter(SubscriptionState.enter_promo))
async def process_promo(message: Message, state: FSMContext):
    """Process promo code input"""
    code = message.text.strip().upper()
    success, days, msg = await activate_promo_code(code)
    
    if success:
        months = days / 30
        sub_url = await create_or_extend_client(message.from_user.id, months)
        await message.answer(f"{msg}\n\nВаша ссылка:\n<code>{sub_url}</code>")
    else:
        await message.answer(msg)
    
    await state.clear()


@router.callback_query(lambda c: c.data == "subscribe")
async def subscribe(callback: CallbackQuery, state: FSMContext):
    """Start subscription process - select duration"""
    await callback.answer()
    inline_keyboard = []
    for months, price in PRICES.items():
        inline_keyboard.append([InlineKeyboardButton(text=f"{months} мес — {price} ₽", callback_data=f"duration_{months}")])
    inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text("<b>📅 Выберите срок подписки</b>", reply_markup=keyboard)
    await state.set_state(SubscriptionState.select_duration)


@router.callback_query(StateFilter(SubscriptionState.select_duration), lambda c: c.data.startswith("duration_"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    """Select subscription duration"""
    await callback.answer()
    user_id = callback.from_user.id
    months = int(callback.data.split("_")[1])

    if user_id == OWNER_ID:
        try:
            sub_url = await create_or_extend_client(user_id, months)
            action = "продлена" if await is_subscription_active(user_id) else "создана"
            await callback.message.edit_text(f"<b>✅ Подписка {action} бесплатно!</b>\n\nВаша ссылка:\n<code>{sub_url}</code>")
        except Exception as e:
            await callback.message.edit_text(f"Ошибка: {str(e)}")
        await state.clear()
        return

    await state.update_data(months=months, price=PRICES[months])
    inline_keyboard = [
        [InlineKeyboardButton(text="💳 CryptoBot", callback_data="pay_cryptobot")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text(f"<b>💰 Оплата за {months} мес — {PRICES[months]} ₽</b>", reply_markup=keyboard)
    await state.set_state(SubscriptionState.select_payment)


@router.callback_query(StateFilter(SubscriptionState.select_payment), lambda c: c.data == "pay_cryptobot")
async def pay_cryptobot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Create CryptoBot invoice"""
    await callback.answer()
    data = await state.get_data()
    months = data['months']
    price = data['price']
    order_id = generate_random_string(10)
    try:
        bot_username = (await bot.get_me()).username
        pay_url, invoice_id = await create_cryptobot_invoice(price, order_id, bot_username)
        await state.update_data(invoice_id=invoice_id, pay_url=pay_url)
        inline_keyboard = [
            [InlineKeyboardButton(text="💸 Оплатить", url=pay_url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_payment")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await callback.message.edit_text("<b>💳 Перейдите к оплате</b>\n\nПосле оплаты нажмите «Проверить оплату»", reply_markup=keyboard)
        await state.set_state(SubscriptionState.waiting_payment)
    except Exception as e:
        await callback.message.edit_text("Ошибка создания счёта. Попробуйте позже.")


@router.callback_query(StateFilter(SubscriptionState.waiting_payment), lambda c: c.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Check if payment is received"""
    await callback.answer()
    data = await state.get_data()
    invoice_id = data['invoice_id']
    pay_url = data.get('pay_url')
    months = data['months']
    user_id = callback.from_user.id
    
    if await check_cryptobot_payment(invoice_id):
        try:
            sub_url = await create_or_extend_client(user_id, months, is_paid=True)
            action = "продлена" if await is_subscription_active(user_id) else "оформлена"
            await callback.message.edit_text(f"<b>🎉 Оплата прошла успешно!</b>\nПодписка {action}\n\nВаша ссылка:\n<code>{sub_url}</code>")
        except Exception as e:
            await callback.message.edit_text(f"Оплата прошла, но ошибка активации: {str(e)}")
        await state.clear()
    else:
        inline_keyboard = [
            [InlineKeyboardButton(text="💸 Оплатить", url=pay_url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_payment")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await callback.message.edit_text("⏳ Оплата ещё не прошла.\nПодождите и нажмите «Проверить оплату» снова.", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await callback.answer()
    await state.clear()
    await show_main(callback, state)


@router.callback_query(lambda c: c.data == "how_connect")
async def how_connect(callback: CallbackQuery):
    """Show connection instructions"""
    await callback.answer()
    text = "<b>📱 Инструкция по подключению</b>\n\n1. Скачайте приложение:\n• iOS: v2RayTun\n• Android: v2RayNG / Happ\n\n2. Импортируйте ссылку из «Моя подписка»\n\nЕсли возникнут вопросы — пишите в поддержку!"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)
