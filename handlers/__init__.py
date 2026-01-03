from aiogram import Router

from .main import router as main_router
from .subscription import router as subscription_router
from .referral import router as referral_router
from .gift import router as gift_router
from .promo import router as promo_router
from .admin import router as admin_router


def get_routers() -> list[Router]:
    """Получить все маршруты"""
    return [
        main_router,
        subscription_router,
        referral_router,
        gift_router,
        promo_router,
        admin_router,
    ]
