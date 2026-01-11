"""
Модуль для инициализации и работы с Supabase.
Используется для хранения данных пользователей, платежей и промокодов.
"""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Инициализируем Supabase клиент
supabase_url = os.getenv("SUPABASE_URL", "")
supabase_key = os.getenv("SUPABASE_KEY", "")

supabase_client: Client = None

if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase_client = None


def is_supabase_enabled() -> bool:
    """Проверить включен ли Supabase"""
    return supabase_client is not None


def init_tables():
    """Инициализировать таблицы в Supabase"""
    if not is_supabase_enabled():
        return
    
    try:
        # Таблица пользователей
        logger.info("Supabase tables will be created via admin panel or migrations")
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")


def get_user(tg_id: int):
    """Получить информацию о пользователе из Supabase"""
    if not is_supabase_enabled():
        return None
    
    try:
        response = supabase_client.table("users").select("*").eq("tg_id", tg_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user {tg_id}: {e}")
        return None


def user_exists(tg_id: int) -> bool:
    """Проверить существует ли пользователь в Supabase"""
    if not is_supabase_enabled():
        return False
    
    try:
        response = supabase_client.table("users").select("tg_id").eq("tg_id", tg_id).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error checking user existence {tg_id}: {e}")
        return False


def create_user(tg_id: int, username: str, referrer_id=None):
    """Создать пользователя в Supabase"""
    if not is_supabase_enabled():
        return
    
    try:
        if not user_exists(tg_id):
            supabase_client.table("users").insert({
                "tg_id": tg_id,
                "username": username,
                "referrer_id": referrer_id,
                "accepted_terms": False,
                "subscription_until": None,
                "gift_received": False,
                "referral_count": 0,
                "active_referrals": 0,
                "first_payment": False,
                "action_lock": 0
            }).execute()
            logger.info(f"User {tg_id} created in Supabase")
    except Exception as e:
        logger.error(f"Error creating user {tg_id}: {e}")


def accept_terms(tg_id: int):
    """Пользователь принял условия использования"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("users").update({
            "accepted_terms": True
        }).eq("tg_id", tg_id).execute()
        logger.info(f"User {tg_id} accepted terms")
    except Exception as e:
        logger.error(f"Error accepting terms for user {tg_id}: {e}")


def has_accepted_terms(tg_id: int) -> bool:
    """Проверить принял ли пользователь условия"""
    if not is_supabase_enabled():
        return False
    
    try:
        user = get_user(tg_id)
        return user and user.get("accepted_terms", False)
    except Exception as e:
        logger.error(f"Error checking terms acceptance for user {tg_id}: {e}")
        return False


def update_subscription(tg_id: int, uuid: str, username: str, subscription_until: str, squad_uuid: str):
    """Обновить подписку пользователя"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("users").update({
            "remnawave_uuid": uuid,
            "remnawave_username": username,
            "subscription_until": subscription_until,
            "squad_uuid": squad_uuid
        }).eq("tg_id", tg_id).execute()
        logger.info(f"Subscription updated for user {tg_id}")
    except Exception as e:
        logger.error(f"Error updating subscription for user {tg_id}: {e}")


def has_subscription(tg_id: int) -> bool:
    """Проверить есть ли активная подписка"""
    if not is_supabase_enabled():
        return False
    
    try:
        user = get_user(tg_id)
        return user and user.get("remnawave_uuid") is not None
    except Exception as e:
        logger.error(f"Error checking subscription for user {tg_id}: {e}")
        return False


def create_payment(tg_id: int, tariff_code: str, amount: float, provider: str, invoice_id: str):
    """Создать запись о платеже"""
    if not is_supabase_enabled():
        return
    
    try:
        from datetime import datetime
        supabase_client.table("payments").insert({
            "tg_id": tg_id,
            "tariff_code": tariff_code,
            "amount": amount,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "provider": provider,
            "invoice_id": str(invoice_id)
        }).execute()
        logger.info(f"Payment created for user {tg_id}")
    except Exception as e:
        logger.error(f"Error creating payment for user {tg_id}: {e}")


def get_pending_payments():
    """Получить все ожидающие платежи"""
    if not is_supabase_enabled():
        return []
    
    try:
        response = supabase_client.table("payments").select("*").eq("status", "pending").eq("provider", "cryptobot").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting pending payments: {e}")
        return []


def get_last_pending_payment(tg_id: int):
    """Получить последний ожидающий платеж пользователя"""
    if not is_supabase_enabled():
        return None
    
    try:
        response = supabase_client.table("payments").select("invoice_id, tariff_code").eq("tg_id", tg_id).eq("status", "pending").eq("provider", "cryptobot").order("id", ascending=False).limit(1).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting last pending payment for user {tg_id}: {e}")
        return None


def update_payment_status(payment_id: int, status: str):
    """Обновить статус платежа"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("payments").update({
            "status": status
        }).eq("id", payment_id).execute()
        logger.info(f"Payment {payment_id} status updated to {status}")
    except Exception as e:
        logger.error(f"Error updating payment {payment_id} status: {e}")


def update_payment_status_by_invoice(invoice_id: str, status: str):
    """Обновить статус платежа по invoice_id"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("payments").update({
            "status": status
        }).eq("invoice_id", invoice_id).execute()
        logger.info(f"Payment {invoice_id} status updated to {status}")
    except Exception as e:
        logger.error(f"Error updating payment {invoice_id} status: {e}")


def update_referral_count(tg_id: int):
    """Увеличить счётчик рефералов"""
    if not is_supabase_enabled():
        return
    
    try:
        user = get_user(tg_id)
        if user:
            new_count = (user.get("referral_count", 0) or 0) + 1
            supabase_client.table("users").update({
                "referral_count": new_count
            }).eq("tg_id", tg_id).execute()
            logger.info(f"Referral count increased for user {tg_id}")
    except Exception as e:
        logger.error(f"Error updating referral count for user {tg_id}: {e}")


def increment_active_referrals(tg_id: int):
    """Увеличить счётчик активных рефералов"""
    if not is_supabase_enabled():
        return
    
    try:
        user = get_user(tg_id)
        if user:
            new_count = (user.get("active_referrals", 0) or 0) + 1
            supabase_client.table("users").update({
                "active_referrals": new_count
            }).eq("tg_id", tg_id).execute()
            logger.info(f"Active referrals increased for user {tg_id}")
    except Exception as e:
        logger.error(f"Error incrementing active referrals for user {tg_id}: {e}")


def get_referral_stats(tg_id: int):
    """Получить статистику рефералов пользователя"""
    if not is_supabase_enabled():
        return None
    
    try:
        user = get_user(tg_id)
        if user:
            return (user.get("referral_count", 0), user.get("active_referrals", 0))
        return None
    except Exception as e:
        logger.error(f"Error getting referral stats for user {tg_id}: {e}")
        return None


def get_referrer(tg_id: int):
    """Получить информацию о рефералите"""
    if not is_supabase_enabled():
        return None
    
    try:
        user = get_user(tg_id)
        if user:
            return (user.get("referrer_id"), user.get("first_payment", False))
        return None
    except Exception as e:
        logger.error(f"Error getting referrer info for user {tg_id}: {e}")
        return None


def mark_first_payment(tg_id: int):
    """Отметить что пользователь сделал первый платёж"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("users").update({
            "first_payment": True
        }).eq("tg_id", tg_id).execute()
        logger.info(f"First payment marked for user {tg_id}")
    except Exception as e:
        logger.error(f"Error marking first payment for user {tg_id}: {e}")


def is_gift_received(tg_id: int) -> bool:
    """Проверить получил ли пользователь подарок"""
    if not is_supabase_enabled():
        return False
    
    try:
        user = get_user(tg_id)
        return user and user.get("gift_received", False)
    except Exception as e:
        logger.error(f"Error checking gift status for user {tg_id}: {e}")
        return False


def mark_gift_received(tg_id: int):
    """Отметить что пользователь получил подарок"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("users").update({
            "gift_received": True
        }).eq("tg_id", tg_id).execute()
        logger.info(f"Gift marked as received for user {tg_id}")
    except Exception as e:
        logger.error(f"Error marking gift received for user {tg_id}: {e}")


def get_promo_code(code: str):
    """Получить информацию о промокоде"""
    if not is_supabase_enabled():
        return None
    
    try:
        response = supabase_client.table("promo_codes").select("*").eq("code", code.upper()).execute()
        if response.data:
            data = response.data[0]
            return (data.get("days"), data.get("max_uses"), data.get("used_count", 0), data.get("active", True))
        return None
    except Exception as e:
        logger.error(f"Error getting promo code {code}: {e}")
        return None


def create_promo_code(code: str, days: int, max_uses: int):
    """Создать новый промокод"""
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("promo_codes").upsert({
            "code": code.upper(),
            "days": days,
            "max_uses": max_uses,
            "used_count": 0,
            "active": True
        }).execute()
        logger.info(f"Promo code {code} created")
    except Exception as e:
        logger.error(f"Error creating promo code {code}: {e}")


def increment_promo_usage(code: str):
    """Увеличить счётчик использования промокода"""
    if not is_supabase_enabled():
        return
    
    try:
        promo = get_promo_code(code)
        if promo:
            new_count = promo[2] + 1
            supabase_client.table("promo_codes").update({
                "used_count": new_count
            }).eq("code", code.upper()).execute()
            logger.info(f"Promo code {code} usage incremented")
    except Exception as e:
        logger.error(f"Error incrementing promo code usage for {code}: {e}")


def acquire_user_lock(tg_id: int) -> bool:
    """
    Атомарно блокирует пользователя.
    Возвращает True если блок получен, False если уже занят.
    """
    if not is_supabase_enabled():
        return True
    
    try:
        user = get_user(tg_id)
        if user and not user.get("action_lock", 0):
            supabase_client.table("users").update({
                "action_lock": 1
            }).eq("tg_id", tg_id).eq("action_lock", 0).execute()
            return True
        return False
    except Exception as e:
        logger.error(f"Error acquiring lock for user {tg_id}: {e}")
        return False


def release_user_lock(tg_id: int):
    """
    Освобождает блокировку пользователя
    """
    if not is_supabase_enabled():
        return
    
    try:
        supabase_client.table("users").update({
            "action_lock": 0
        }).eq("tg_id", tg_id).execute()
        logger.info(f"Lock released for user {tg_id}")
    except Exception as e:
        logger.error(f"Error releasing lock for user {tg_id}: {e}")
