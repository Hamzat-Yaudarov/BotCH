import asyncio
import asyncpg
import logging
from config import DATABASE_URL


logger = logging.getLogger(__name__)

# Глобальный пул соединений
pool = None


async def init_db():
    """Инициализация подключения к Supabase PostgreSQL и создание необходимых таблиц"""
    global pool
    
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Connected to Supabase PostgreSQL database")
        
        # Создаём таблицы если их нет
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    tg_id BIGINT PRIMARY KEY,
                    username TEXT,
                    accepted_terms BOOLEAN DEFAULT FALSE,
                    remnawave_uuid TEXT,
                    remnawave_username TEXT,
                    subscription_until TEXT,
                    squad_uuid TEXT,
                    referrer_id BIGINT,
                    gift_received BOOLEAN DEFAULT FALSE,
                    referral_count INTEGER DEFAULT 0,
                    active_referrals INTEGER DEFAULT 0,
                    first_payment BOOLEAN DEFAULT FALSE,
                    action_lock INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT REFERENCES users(tg_id),
                    tariff_code TEXT,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT,
                    invoice_id TEXT UNIQUE,
                    payload TEXT
                );
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code TEXT PRIMARY KEY,
                    days INTEGER,
                    max_uses INTEGER,
                    used_count INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            logger.info("Database tables initialized successfully")
    
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


async def close_db():
    """Закрытие подключения к БД"""
    global pool
    if pool:
        await pool.close()
        logger.info("Database pool closed")


async def db_execute(query, params=(), fetchone=False, fetchall=False):
    """
    Выполнить SQL запрос к Supabase PostgreSQL
    
    Args:
        query: SQL запрос
        params: Параметры для запроса (кортеж)
        fetchone: Получить одну строку результата
        fetchall: Получить все строки результата
        
    Returns:
        Результат запроса или None
    """
    if not pool:
        logger.error("Database pool not initialized")
        return None
    
    try:
        async with pool.acquire() as conn:
            if fetchone:
                result = await conn.fetchrow(query, *params)
                return result
            elif fetchall:
                result = await conn.fetch(query, *params)
                return result
            else:
                await conn.execute(query, *params)
                return None
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return None


# ════════════════════════════════════════════════
#         USER MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def get_user(tg_id: int):
    """Получить информацию о пользователе"""
    query = "SELECT * FROM users WHERE tg_id = $1"
    return await db_execute(query, (tg_id,), fetchone=True)


async def user_exists(tg_id: int) -> bool:
    """Проверить существует ли пользователь"""
    result = await db_execute("SELECT 1 FROM users WHERE tg_id = $1", (tg_id,), fetchone=True)
    return result is not None


async def create_user(tg_id: int, username: str, referrer_id=None):
    """Создать пользователя (если уже существует, игнорируется)"""
    query = """
        INSERT INTO users (tg_id, username, referrer_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (tg_id) DO NOTHING
    """
    await db_execute(query, (tg_id, username, referrer_id))


# ════════════════════════════════════════════════
#       TERMS AND CONDITIONS FUNCTIONS
# ════════════════════════════════════════════════

async def accept_terms(tg_id: int):
    """Пользователь принял условия использования"""
    query = "UPDATE users SET accepted_terms = TRUE WHERE tg_id = $1"
    await db_execute(query, (tg_id,))


async def has_accepted_terms(tg_id: int) -> bool:
    """Проверить принял ли пользователь условия"""
    user = await get_user(tg_id)
    return user and user['accepted_terms']


# ════════════════════════════════════════════════
#      SUBSCRIPTION MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def update_subscription(tg_id: int, uuid: str, username: str, subscription_until: str, squad_uuid: str):
    """Обновить подписку пользователя"""
    query = """
        UPDATE users 
        SET remnawave_uuid = $1, remnawave_username = $2, 
            subscription_until = $3, squad_uuid = $4, updated_at = CURRENT_TIMESTAMP
        WHERE tg_id = $5
    """
    await db_execute(query, (uuid, username, subscription_until, squad_uuid, tg_id))


async def has_subscription(tg_id: int) -> bool:
    """Проверить есть ли активная подписка"""
    user = await get_user(tg_id)
    return user and user['remnawave_uuid'] is not None


# ════════════════════════════════════════════════
#       PAYMENT MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def create_payment(tg_id: int, tariff_code: str, amount: float, provider: str, invoice_id: str):
    """Создать запись о платеже"""
    query = """
        INSERT INTO payments (tg_id, tariff_code, amount, provider, invoice_id)
        VALUES ($1, $2, $3, $4, $5)
    """
    await db_execute(query, (tg_id, tariff_code, amount, provider, str(invoice_id)))


async def get_pending_payments():
    """Получить все ожидающие платежи"""
    query = """
        SELECT id, tg_id, invoice_id, tariff_code 
        FROM payments 
        WHERE status = 'pending' AND provider = 'cryptobot'
    """
    return await db_execute(query, fetchall=True)


async def get_last_pending_payment(tg_id: int):
    """Получить последний ожидающий платеж пользователя"""
    query = """
        SELECT invoice_id, tariff_code 
        FROM payments 
        WHERE tg_id = $1 AND status = 'pending' AND provider = 'cryptobot'
        ORDER BY id DESC 
        LIMIT 1
    """
    return await db_execute(query, (tg_id,), fetchone=True)


async def update_payment_status(payment_id: int, status: str):
    """Обновить статус платежа"""
    query = "UPDATE payments SET status = $1 WHERE id = $2"
    await db_execute(query, (status, payment_id))


async def update_payment_status_by_invoice(invoice_id: str, status: str):
    """Обновить статус платежа по invoice_id"""
    query = "UPDATE payments SET status = $1 WHERE invoice_id = $2"
    await db_execute(query, (status, invoice_id))


# ════════════════════════════════════════════════
#       REFERRAL MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def update_referral_count(tg_id: int):
    """Увеличить счётчик рефералов"""
    query = "UPDATE users SET referral_count = referral_count + 1 WHERE tg_id = $1"
    await db_execute(query, (tg_id,))


async def increment_active_referrals(tg_id: int):
    """Увеличить счётчик активных рефералов"""
    query = "UPDATE users SET active_referrals = active_referrals + 1 WHERE tg_id = $1"
    await db_execute(query, (tg_id,))


async def get_referral_stats(tg_id: int):
    """Получить статистику рефералов пользователя"""
    query = "SELECT referral_count, active_referrals FROM users WHERE tg_id = $1"
    return await db_execute(query, (tg_id,), fetchone=True)


async def get_referrer(tg_id: int):
    """Получить информацию о рефералите"""
    query = "SELECT referrer_id, first_payment FROM users WHERE tg_id = $1"
    return await db_execute(query, (tg_id,), fetchone=True)


async def mark_first_payment(tg_id: int):
    """Отметить что пользователь сделал первый платёж"""
    query = "UPDATE users SET first_payment = TRUE WHERE tg_id = $1"
    await db_execute(query, (tg_id,))


# ════════════════════════════════════════════════
#       GIFT MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def is_gift_received(tg_id: int) -> bool:
    """Проверить получил ли пользователь подарок"""
    user = await get_user(tg_id)
    return user and user['gift_received']


async def mark_gift_received(tg_id: int):
    """Отметить что пользователь получил подарок"""
    query = "UPDATE users SET gift_received = TRUE WHERE tg_id = $1"
    await db_execute(query, (tg_id,))


# ════════════════════════════════════════════════
#       PROMO CODE MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def get_promo_code(code: str):
    """Получить информацию о промокоде"""
    query = "SELECT days, max_uses, used_count, active FROM promo_codes WHERE code = $1"
    return await db_execute(query, (code,), fetchone=True)


async def create_promo_code(code: str, days: int, max_uses: int):
    """Создать новый промокод"""
    query = """
        INSERT INTO promo_codes (code, days, max_uses, active)
        VALUES ($1, $2, $3, TRUE)
        ON CONFLICT (code) DO UPDATE SET 
            days = $2, max_uses = $3, active = TRUE
    """
    await db_execute(query, (code.upper(), days, max_uses))


async def increment_promo_usage(code: str):
    """Увеличить счётчик использования промокода"""
    query = "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = $1"
    await db_execute(query, (code,))


# ════════════════════════════════════════════════
#       USER LOCK MANAGEMENT FUNCTIONS
# ════════════════════════════════════════════════

async def acquire_user_lock(tg_id: int) -> bool:
    """
    Атомарно блокирует пользователя.
    Возвращает True если блок получен, False если уже занят.
    """
    if not pool:
        logger.error("Database pool not initialized")
        return False
    
    try:
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users
                SET action_lock = 1
                WHERE tg_id = $1 AND action_lock = 0
            """, tg_id)
            
            # asyncpg возвращает строку "UPDATE X" где X - количество обновленных строк
            return "1" in result
    except Exception as e:
        logger.error(f"Acquire user lock error: {e}")
        return False


async def release_user_lock(tg_id: int):
    """Освобождает блокировку пользователя"""
    query = "UPDATE users SET action_lock = 0 WHERE tg_id = $1"
    await db_execute(query, (tg_id,))
