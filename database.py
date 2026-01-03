import asyncio
import logging
from typing import Optional
import asyncpg
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Global connection pool
pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool and create tables"""
    global pool
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database connection pool created successfully")
        await create_tables()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()
        logger.info("Database connection pool closed")


async def create_tables():
    """Create all required tables"""
    global pool
    
    tables = """
    -- Users table for storing VPN client info
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        uuid VARCHAR(36) NOT NULL UNIQUE,
        sub_id VARCHAR(16) NOT NULL UNIQUE,
        email VARCHAR(16) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Promo codes table
    CREATE TABLE IF NOT EXISTS promo_codes (
        code VARCHAR(50) PRIMARY KEY,
        days INT NOT NULL,
        activations_left INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Referral tracking
    CREATE TABLE IF NOT EXISTS referrals (
        id SERIAL PRIMARY KEY,
        referrer_id BIGINT NOT NULL,
        referred_user_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(referrer_id, referred_user_id)
    );

    -- Users who paid for subscription
    CREATE TABLE IF NOT EXISTS paid_users (
        user_id BIGINT PRIMARY KEY,
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Users who received gift
    CREATE TABLE IF NOT EXISTS user_gifts (
        user_id BIGINT PRIMARY KEY,
        gift_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for faster queries
    CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
    CREATE INDEX IF NOT EXISTS idx_referrals_referred_user_id ON referrals(referred_user_id);
    """
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(tables)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


async def get_connection():
    """Get a connection from the pool"""
    global pool
    if not pool:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return pool.acquire()
