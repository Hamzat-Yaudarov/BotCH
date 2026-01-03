import uuid
from datetime import datetime
from config import (
    SUB_PORT,
    SUB_EXTERNAL_HOST,
    REFERRAL_BONUS_DAYS,
    GIFT_DAYS,
)
from database import pool
from xui_api import create_client, update_client, get_client_expiry
from utils import generate_random_string
from db_models import (
    create_user,
    get_user,
    user_exists,
    create_promo_code,
    get_promo_code,
    activate_promo_code as activate_promo_code_db,
    add_referral,
    get_referrals,
    is_referrer_of,
    add_paid_user,
    is_paid_user,
    get_paid_users,
    add_user_gift,
    has_user_received_gift,
)


async def has_client(user_id: int) -> bool:
    """Check if user has a VPN client"""
    return await user_exists(user_id)


async def is_subscription_active(user_id: int) -> bool:
    """Check if user's subscription is active"""
    user = await get_user(user_id)
    if not user:
        return False
    
    email = user["email"]
    try:
        expiry = get_client_expiry(email)
        return expiry > int(datetime.now().timestamp() * 1000)
    except:
        return False


async def create_or_extend_client(user_id: int, add_months: float, is_paid: bool = False) -> str:
    """Create new VPN client or extend existing subscription"""
    current_user = await get_user(user_id)
    
    add_ms = int(add_months * 30 * 24 * 60 * 60 * 1000)
    
    if current_user:
        # Extend existing client
        client_uuid = current_user["uuid"]
        client_sub_id = current_user["sub_id"]
        client_email = current_user["email"]
        
        current_expiry = get_client_expiry(client_email)
        new_expiry = current_expiry + add_ms
        
        update_client(client_uuid, client_sub_id, client_email, new_expiry, user_id)
    else:
        # Create new client
        client_uuid = str(uuid.uuid4())
        client_sub_id = generate_random_string(16)
        client_email = generate_random_string(12)
        new_expiry = int(datetime.now().timestamp() * 1000) + add_ms
        
        create_client(client_uuid, client_sub_id, client_email, new_expiry, user_id)
        
        # Save to database
        await create_user(user_id, client_uuid, client_sub_id, client_email)
    
    # Get fresh user data for sub_id
    user = await get_user(user_id)
    sub_url = f"http://{SUB_EXTERNAL_HOST}:{SUB_PORT}/sub/{user['sub_id']}"
    
    # Handle paid subscription referral bonus
    if is_paid:
        await add_paid_user(user_id)
        
        # Check if this user was referred by someone and give them bonus
        # We need to find who referred this user
        # This requires a reverse lookup, which we can do by checking all users' referrals
        # For efficiency, we should add a reverse_referrer column, but for now we'll do a query
        async with pool.acquire() as conn:
            referrer = await conn.fetchval(
                "SELECT referrer_id FROM referrals WHERE referred_user_id = $1",
                user_id
            )
            if referrer:
                # Give bonus to referrer
                await create_or_extend_client(referrer, REFERRAL_BONUS_DAYS / 30)
    
    return sub_url


async def add_promo_code(code: str, days: int, activations: int):
    """Add new promo code"""
    await create_promo_code(code, days, activations)


async def activate_promo_code(code: str) -> tuple:
    """Activate promo code and return (success, days, message)"""
    promo = await get_promo_code(code)

    if not promo:
        return False, 0, "❌ Промокод не найден или недействителен."

    if promo["activations_left"] <= 0:
        return False, 0, "❌ Промокод исчерпан."

    days = promo["days"]
    await activate_promo_code_db(code)

    return True, days, f"✅ Промокод активирован!\n+{days} дней к подписке"


async def add_referred_user(referrer_id: int, referred_user_id: int):
    """Add user to referral list"""
    if referrer_id != referred_user_id:
        await add_referral(referrer_id, referred_user_id)


async def get_referral_stats(user_id: int) -> tuple:
    """Get referral statistics for user"""
    referrals = await get_referrals(user_id)
    total_referred = len(referrals)
    
    paid_users = await get_paid_users()
    paid_referred = sum(1 for u in referrals if u in paid_users)
    
    return total_referred, paid_referred


async def add_user_gift_db(user_id: int):
    """Mark user as received gift"""
    await add_user_gift(user_id)


async def has_user_received_gift_db(user_id: int) -> bool:
    """Check if user already received gift"""
    return await has_user_received_gift(user_id)
