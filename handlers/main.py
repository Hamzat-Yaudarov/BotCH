from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)

from database import db
from config import TELEGRAPH_AGREEMENT_URL, ADMIN_USERNAME
from xui_client import xui
from utils import get_current_timestamp_ms


router = Router()


@router.message(Command(commands=['start']))
async def start(message: Message, state: FSMContext):
    args = message.text.split()
    referrer_id = None

    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != message.from_user.id:
                await db.add_referral(referrer_id, message.from_user.id)
        except:
            pass

    data = await state.get_data()
    if data.get("accepted"):
        await show_main_menu(message, state)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я принимаю условия", callback_data="accept")],
            [InlineKeyboardButton(text="📄 Ознакомиться с соглашением", url=TELEGRAPH_AGREEMENT_URL)]
        ]
    )

    await message.answer(
        "<b>📄 Пользовательское соглашение</b>\n\n"
        "Перед началом использования сервиса <b>SPN VPN</b> необходимо ознакомиться "
        "и принять условия пользовательского соглашения.\n\n"
        "Это обязательное требование для продолжения работы с сервисом.\n\n"
        "<b>Вы подтверждаете своё согласие?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "accept")
async def accept(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(accepted=True)

    try:
        await callback.message.delete()
    except:
        pass

    await show_main_menu(callback, state)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await show_main_menu(callback, state)


async def show_main_menu(target: Message | CallbackQuery, state: FSMContext = None):
    user_id = target.from_user.id

    client_exists = await db.client_exists(user_id)
    active = False

    if client_exists:
        client = await db.get_user_client(user_id)
        active = client["expiry_time"] > get_current_timestamp_ms()

    row = [
        InlineKeyboardButton(
            text="🔄 Продлить подписку" if active else "🆕 Оформить подписку",
            callback_data="subscribe"
        )
    ]

    if client_exists:
        row.append(
            InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription")
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text="📱 Инструкция по подключению", callback_data="how_connect")],
            [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral")],
            [InlineKeyboardButton(text="🎟️ Активировать промокод", callback_data="promo")],
            [InlineKeyboardButton(text="🎉 Бесплатный бонус", callback_data="gift")],
            [InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{ADMIN_USERNAME}")]
        ]
    )

    text = (
        "<b>🚀 SPN VPN</b>\n"
        "<i>Безопасность • Скорость • Свобода</i>\n\n"
        "Добро пожаловать в сервис защищённого доступа к интернету.\n\n"
        "Выберите нужное действие:"
    )

    if isinstance(target, Message):
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        try:
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except:
            await target.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "my_subscription")
async def my_subscription(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    client = await db.get_user_client(user_id)
    if not client:
        await callback.message.edit_text(
            "<b>❌ Подписка не найдена</b>\n\n"
            "На вашем аккаунте нет активной подписки.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]]
            ),
            parse_mode="HTML"
        )
        return

    try:
        from utils import calculate_remaining_time

        expiry_time = xui.get_client_expiry(client["email"])
        await db.update_user_client_expiry(user_id, expiry_time)

        remaining = await calculate_remaining_time(expiry_time)
        sub_url = xui.get_subscription_url(client["sub_id"])

        text = (
            "<b>📊 Ваша подписка</b>\n\n"
            f"<b>⏳ Осталось:</b> {remaining}\n\n"
            "<b>🔗 Ссылка для подключения:</b>\n"
            f"<code>{sub_url}</code>\n\n"
            "<i>Скопируйте ссылку и импортируйте её в VPN-приложение</i>"
        )
    except:
        text = (
            "<b>⚠️ Ошибка получения данных</b>\n\n"
            "Не удалось загрузить информацию о подписке."
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]]
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "how_connect")
async def how_connect(callback: CallbackQuery):
    await callback.answer()

    text = (
        "<b>📱 Инструкция по подключению VPN</b>\n\n"
        "<b>1️⃣ Установите приложение:</b>\n"
        "• <b>iOS:</b> v2RayTun\n"
        "• <b>Android:</b> v2RayNG или Happ\n\n"
        "<b>2️⃣ Получите ссылку подписки:</b>\n"
        "Раздел «Моя подписка»\n\n"
        "<b>3️⃣ Импортируйте ссылку</b>\n\n"
        "<b>4️⃣ Подключитесь</b>\n\n"
        "<i>Поддержка всегда на связи</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]]
        ),
        parse_mode="HTML"
    )