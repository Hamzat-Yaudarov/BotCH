import asyncio
import logging
import random
import string
import uuid
import json
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.filters.state import StateFilter

# Constants
BOT_TOKEN = "8520411926:AAFcduqngB2ZMCp3RS4yZ8hwkcyf-yOmWyU"
CRYPTOBOT_TOKEN = "508663:AAZcVJabRaP6NTah1LVJVl3p1E0GYTid9GK"
XUI_PANEL_URL = "https://195.133.21.73:2053"
XUI_PANEL_PATH = "/ozsDaJc9vZ4iwfvWZi/panel"
XUI_USERNAME = "GtFIrnml0B"
XUI_PASSWORD = "yrbFCWxMJY"
SUB_PORT = 2096
SUB_EXTERNAL_HOST = "195.133.21.73"
INBOUND_ID = 2
ADMIN_USERNAME = "Youdarov"
NEWS_CHANNEL_ID = "@spn_newsvpn"
NEWS_CHANNEL_URL = "https://t.me/spn_newsvpn"
TELEGRAPH_AGREEMENT_URL = "https://telegra.ph/Polzovatelskoe-soglashenie-dlya-servisa-SPN-Uskoritel-interneta-01-01"

OWNER_ID = 6910097562

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SubscriptionState(StatesGroup):
    select_duration = State()
    select_payment = State()
    waiting_payment = State()
    enter_promo = State()

PRICES = {
    1: 5,
    3: 249,
    6: 449,
    12: 990
}

# Хранилище: user_id → {"uuid": str, "sub_id": str, "email": str}
user_clients = {}

# Промокоды: code → {"days": int, "activations_left": int}
promo_codes = {}

# Рефералы: referrer_id → list of referred_user_id
referred_by = {}

# Купившие подписку (через оплату): set of user_id
paid_users = set()

# Подарок за канал
user_gifts = set()

def generate_random_string(length=16):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_xui_session():
    session = requests.Session()
    login_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH.replace('/panel', '')}/login/"
    payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        response = session.post(login_url, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"XUI login failed: {resp_json}")
    except Exception as e:
        raise Exception(f"Ошибка подключения к панели: {str(e)}")
    return session

def get_client_expiry(email):
    session = get_xui_session()
    get_traffic_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/getClientTraffics/{email}"
    try:
        response = session.get(get_traffic_url, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"Get client traffic failed: {resp_json}")
        return resp_json['obj']['expiryTime']
    except Exception as e:
        raise Exception(f"Ошибка получения времени клиента: {str(e)}")

def create_or_extend_client(user_id, add_months, is_paid=False):
    session = get_xui_session()

    current_data = user_clients.get(user_id)

    add_ms = int(add_months * 30 * 24 * 60 * 60 * 1000)

    if current_data:
        client_uuid = current_data["uuid"]
        client_sub_id = current_data["sub_id"]
        client_email = current_data["email"]

        current_expiry = get_client_expiry(client_email)
        new_expiry = current_expiry + add_ms

        update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/updateClient/{client_uuid}"
    else:
        client_uuid = str(uuid.uuid4())
        client_sub_id = generate_random_string(16)
        client_email = generate_random_string(12)
        new_expiry = int(datetime.now().timestamp() * 1000) + add_ms
        update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/addClient"

    settings = {
        "clients": [{
            "id": client_uuid,
            "flow": "",
            "email": client_email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": new_expiry,
            "enable": True,
            "tgId": str(user_id),
            "subId": client_sub_id,
            "reset": 0
        }]
    }

    payload = {
        "id": str(INBOUND_ID),
        "settings": json.dumps(settings)
    }

    try:
        response = session.post(update_url, data=payload, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"Operation failed: {resp_json}")
    except Exception as e:
        raise Exception(f"Ошибка операции с клиентом: {str(e)}")

    user_clients[user_id] = {"uuid": client_uuid, "sub_id": client_sub_id, "email": client_email}

    sub_url = f"http://{SUB_EXTERNAL_HOST}:{SUB_PORT}/sub/{client_sub_id}"

    if is_paid:
        paid_users.add(user_id)
        for referrer_id, refs in referred_by.items():
            if user_id in refs:
                create_or_extend_client(referrer_id, 7/30)

    return sub_url

async def has_client(user_id):
    return user_id in user_clients

async def is_subscription_active(user_id):
    if user_id not in user_clients:
        return False
    email = user_clients[user_id]["email"]
    try:
        expiry = get_client_expiry(email)
        return expiry > int(datetime.now().timestamp() * 1000)
    except:
        return False

async def calculate_remaining_time(expiry_time_ms):
    now = int(datetime.now().timestamp() * 1000)
    if expiry_time_ms <= now:
        return "Подписка истекла"
    remaining_ms = expiry_time_ms - now
    days = remaining_ms // (24 * 60 * 60 * 1000)
    hours = (remaining_ms % (24 * 60 * 60 * 1000)) // (60 * 60 * 1000)
    minutes = (remaining_ms % (60 * 60 * 1000)) // (60 * 1000)
    return f"{days} дн. {hours} ч. {minutes} мин."

async def create_cryptobot_invoice(amount_rub: int, order_id: str):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": str(amount_rub),
        "description": f"Подписка SPN {order_id}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/{(await bot.get_me()).username}"
    }
    response = requests.post(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        raise Exception(f"CryptoBot error {response.status_code}: {response.text}")
    data = response.json()
    if not data.get("ok"):
        raise Exception(f"CryptoBot error: {data}")
    return data['result']['pay_url'], data['result']['invoice_id']

async def check_cryptobot_payment(invoice_id: str) -> bool:
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        return False
    data = response.json()
    if not data.get("ok"):
        return False
    invoices = data['result']['items']
    if invoices and invoices[0]['status'] == 'paid':
        return True
    return False

async def show_main(target: Message | CallbackQuery, state: FSMContext = None):
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

@dp.message(Command(commands=['start']))
async def start(message: Message, state: FSMContext):
    args = message.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != message.from_user.id:
                referred_by.setdefault(referrer_id, []).append(message.from_user.id)
        except:
            pass

    data = await state.get_data()
    if data.get("accepted"):
        await show_main(message, state)
        return

    inline_keyboard = [
        [InlineKeyboardButton(text="✅ Принять", callback_data="accept")],
        [InlineKeyboardButton(text="📄 Открыть соглашение", url=TELEGRAPH_AGREEMENT_URL)]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await message.answer("<b>Перед использованием необходимо принять пользовательское соглашение:</b>", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "accept")
async def accept(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(accepted=True)
    try:
        await callback.message.delete()
    except:
        pass
    await show_main(callback, state)

@dp.callback_query(lambda c: c.data == "my_subscription")
async def my_subscription(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in user_clients:
        await callback.message.edit_text("❌ У вас нет активной подписки.")
        return

    email = user_clients[user_id]["email"]
    try:
        expiry_time = get_client_expiry(email)
        remaining = await calculate_remaining_time(expiry_time)
        sub_url = f"http://{SUB_EXTERNAL_HOST}:{SUB_PORT}/sub/{user_clients[user_id]['sub_id']}"
        text = f"<b>📊 Ваша подписка</b>\n\nОсталось: <b>{remaining}</b>\n\nСсылка для подключения:\n<code>{sub_url}</code>"
    except Exception as e:
        text = f"Ошибка получения информации."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "gift")
async def gift(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Проверить", callback_data="check_gift")], [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(f"<b>🎉 Подарок за подписку на канал</b>\n\nПодпишись на {NEWS_CHANNEL_URL} и получи <b>3 дня бесплатно</b>!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "check_gift")
async def check_gift(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id in user_gifts:
        await callback.message.edit_text("❌ Вы уже получили подарок.")
        return

    try:
        member = await bot.get_chat_member(NEWS_CHANNEL_ID, user_id)
        if member.status in ("member", "administrator", "creator"):
            sub_url = create_or_extend_client(user_id, 0.1)
            user_gifts.add(user_id)
            await callback.message.edit_text(f"<b>🎉 Подарок получен!</b>\n+3 дня к подписке\n\nВаша ссылка:\n<code>{sub_url}</code>")
        else:
            await callback.message.edit_text("❌ Вы не подписаны на канал.\nПодпишитесь и нажмите «Проверить» снова.")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка проверки: {str(e)}")

@dp.callback_query(lambda c: c.data == "referral")
async def referral(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    total_referred = len(referred_by.get(user_id, []))
    paid_referred = sum(1 for u in referred_by.get(user_id, []) if u in paid_users)

    text = f"<b>🎁 Бонус за друга</b>\n\nВаша реферальная ссылка:\n<code>{ref_link}</code>\n\nПриглашено: <b>{total_referred}</b>\nКупили подписку: <b>{paid_referred}</b>\n\nЗа каждого купившего — <b>+7 дней</b> к вашей подписке!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "promo")
async def promo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text("<b>🔑 Введите промокод</b>", reply_markup=keyboard)
    await state.set_state(SubscriptionState.enter_promo)

@dp.message(StateFilter(SubscriptionState.enter_promo))
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if code not in promo_codes:
        await message.answer("❌ Промокод не найден или недействителен.")
        await state.clear()
        return

    promo = promo_codes[code]
    if promo["activations_left"] <= 0:
        await message.answer("❌ Промокод исчерпан.")
        await state.clear()
        return

    days = promo["days"]
    months = days / 30
    sub_url = create_or_extend_client(message.from_user.id, months)

    promo["activations_left"] -= 1
    if promo["activations_left"] == 0:
        del promo_codes[code]

    await message.answer(f"<b>✅ Промокод активирован!</b>\n+{days} дней к подписке\n\nВаша ссылка:\n<code>{sub_url}</code>")
    await state.clear()

@dp.callback_query(lambda c: c.data == "subscribe")
async def subscribe(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    inline_keyboard = []
    for months, price in PRICES.items():
        inline_keyboard.append([InlineKeyboardButton(text=f"{months} мес — {price} ₽", callback_data=f"duration_{months}")])
    inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text("<b>📅 Выберите срок подписки</b>", reply_markup=keyboard)
    await state.set_state(SubscriptionState.select_duration)

@dp.callback_query(StateFilter(SubscriptionState.select_duration), lambda c: c.data.startswith("duration_"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    months = int(callback.data.split("_")[1])

    if user_id == OWNER_ID:
        try:
            sub_url = create_or_extend_client(user_id, months)
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

@dp.callback_query(StateFilter(SubscriptionState.select_payment), lambda c: c.data == "pay_cryptobot")
async def pay_cryptobot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    months = data['months']
    price = data['price']
    order_id = generate_random_string(10)
    try:
        pay_url, invoice_id = await create_cryptobot_invoice(price, order_id)
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

@dp.callback_query(StateFilter(SubscriptionState.waiting_payment), lambda c: c.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    invoice_id = data['invoice_id']
    pay_url = data.get('pay_url')
    months = data['months']
    user_id = callback.from_user.id
    if await check_cryptobot_payment(invoice_id):
        try:
            sub_url = create_or_extend_client(user_id, months, is_paid=True)
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

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await show_main(callback, state)

@dp.callback_query(lambda c: c.data == "how_connect")
async def how_connect(callback: CallbackQuery):
    await callback.answer()
    text = "<b>📱 Инструкция по подключению</b>\n\n1. Скачайте приложение:\n• iOS: v2RayTun\n• Android: v2RayNG / Happ\n\n2. Импортируйте ссылку из «Моя подписка»\n\nЕсли возникнут вопросы — пишите в поддержку!"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

# Админские команды
@dp.message(Command("newcode"))
async def newcode(message: Message, command: CommandObject):
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

    promo_codes[code] = {"days": days, "activations_left": activations}
    await message.answer(f"Промокод <b>{code}</b> создан:\n{days} дней\n{activations} активаций")

@dp.message(Command("givesub"))
async def givesub(message: Message, command: CommandObject):
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

@dp.message(Command("message"))
async def admin_message(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        return

    text = command.args
    if not text:
        await message.answer("Использование: /message [текст]")
        return

    success_count = 0
    for user_id in user_clients.keys():
        try:
            await bot.send_message(user_id, text)
            success_count += 1
        except:
            pass

    await message.answer(f"Рассылка завершена: {success_count} пользователей получили сообщение.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())