from aiogram.fsm.state import State, StatesGroup


class SubscriptionState(StatesGroup):
    """Состояния для процесса подписки"""
    select_duration = State()
    select_payment = State()
    waiting_payment = State()
    enter_promo = State()
