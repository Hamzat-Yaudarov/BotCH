import asyncpg
from typing import List, Dict, Optional
from database import pool


# ============= Users (VPN Clients) =============

async def create_user(user_id: int, uuid: str, sub_id: str, email: str) -> bool:
    """Create a new VPN client for user"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO users (user_id, uuid, sub_id, email) 
                   VALUES ($1, $2, $3, $4)""",
                user_id, uuid, sub_id, email
            )
        return True
    except asyncpg.UniqueViolationError:
        return False


async def get_user(user_id: int) -> Optional[Dict]:
    """Get user VPN client info"""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, uuid, sub_id, email FROM users WHERE user_id = $1",
                user_id
            )
        return dict(row) if row else None
    except Exception:
        return None


async def user_exists(user_id: int) -> bool:
    """Check if user has a VPN client"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM users WHERE user_id = $1",
                user_id
            )
        return result is not None
    except Exception:
        return False


# ============= Promo Codes =============

async def create_promo_code(code: str, days: int, activations: int) -> bool:
    """Create a new promo code"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO promo_codes (code, days, activations_left) 
                   VALUES ($1, $2, $3)""",
                code.upper(), days, activations
            )
        return True
    except asyncpg.UniqueViolationError:
        return False


async def get_promo_code(code: str) -> Optional[Dict]:
    """Get promo code info"""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT code, days, activations_left FROM promo_codes WHERE code = $1",
                code.upper()
            )
        return dict(row) if row else None
    except Exception:
        return None


async def activate_promo_code(code: str) -> bool:
    """Decrement activation count and delete if exhausted"""
    try:
        async with pool.acquire() as conn:
            # Decrement activations_left
            result = await conn.execute(
                """UPDATE promo_codes SET activations_left = activations_left - 1 
                   WHERE code = $1 AND activations_left > 0""",
                code.upper()
            )
            
            # If no activations left, delete the code
            await conn.execute(
                "DELETE FROM promo_codes WHERE code = $1 AND activations_left <= 0",
                code.upper()
            )
        return True
    except Exception:
        return False


# ============= Referrals =============

async def add_referral(referrer_id: int, referred_user_id: int) -> bool:
    """Add a referral relationship"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO referrals (referrer_id, referred_user_id) 
                   VALUES ($1, $2)""",
                referrer_id, referred_user_id
            )
        return True
    except (asyncpg.UniqueViolationError, asyncpg.ForeignKeyViolationError):
        return False


async def get_referrals(referrer_id: int) -> List[int]:
    """Get list of users referred by this user"""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT referred_user_id FROM referrals WHERE referrer_id = $1",
                referrer_id
            )
        return [row['referred_user_id'] for row in rows]
    except Exception:
        return []


async def is_referrer_of(referrer_id: int, user_id: int) -> bool:
    """Check if user_id was referred by referrer_id"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                """SELECT 1 FROM referrals 
                   WHERE referrer_id = $1 AND referred_user_id = $2""",
                referrer_id, user_id
            )
        return result is not None
    except Exception:
        return False


# ============= Paid Users =============

async def add_paid_user(user_id: int) -> bool:
    """Mark user as paid"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO paid_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                user_id
            )
        return True
    except Exception:
        return False


async def is_paid_user(user_id: int) -> bool:
    """Check if user has paid"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM paid_users WHERE user_id = $1",
                user_id
            )
        return result is not None
    except Exception:
        return False


async def get_paid_users() -> List[int]:
    """Get all user IDs who paid"""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM paid_users")
        return [row['user_id'] for row in rows]
    except Exception:
        return []


# ============= Gifts =============

async def add_user_gift(user_id: int) -> bool:
    """Mark user as received gift"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_gifts (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                user_id
            )
        return True
    except Exception:
        return False


async def has_user_received_gift(user_id: int) -> bool:
    """Check if user already received gift"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM user_gifts WHERE user_id = $1",
                user_id
            )
        return result is not None
    except Exception:
        return False
