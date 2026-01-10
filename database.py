import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import DATABASE_URL


def get_db_connection():
    """Получить подключение к базе данных"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        raise


def init_db():
    """Инициализация базы данных с необходимыми таблицами"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
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
                action_lock INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT,
                tariff_code TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                provider TEXT,
                invoice_id TEXT,
                payload TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                days INTEGER,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE
            )
        ''')

        conn.commit()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def db_execute(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Выполнить SQL запрос к базе данных
    
    Args:
        query: SQL запрос
        params: Параметры для запроса (кортеж)
        fetchone: Получить одну строку результата
        fetchall: Получить все строки результата
        commit: Коммитить изменения в БД
        
    Returns:
        Результат запроса или None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None
        
        if commit:
            conn.commit()
        
        return result
    except Exception as e:
        logging.error(f"Database query error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def acquire_user_lock(tg_id: int) -> bool:
    """
    Атомарно блокирует пользователя.
    Возвращает True если блок получен, False если уже занят.
    
    Args:
        tg_id: ID пользователя Telegram
        
    Returns:
        True если удалось получить блокировку, False иначе
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET action_lock = 1
            WHERE tg_id = %s AND action_lock = 0
        """, (tg_id,))

        changed = cursor.rowcount
        conn.commit()
        return changed == 1
    except Exception as e:
        logging.error(f"Error acquiring lock: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def release_user_lock(tg_id: int):
    """
    Освобождает блокировку пользователя
    
    Args:
        tg_id: ID пользователя Telegram
    """
    db_execute(
        "UPDATE users SET action_lock = 0 WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


# User management
def get_user(tg_id: int):
    """Получить информацию о пользователе"""
    return db_execute("SELECT * FROM users WHERE tg_id = %s", (tg_id,), fetchone=True)


def user_exists(tg_id: int) -> bool:
    """Проверить существует ли пользователь"""
    result = db_execute("SELECT 1 FROM users WHERE tg_id = %s", (tg_id,), fetchone=True)
    return result is not None


def create_user(tg_id: int, username: str, referrer_id=None):
    """Создать или игнорировать пользователя"""
    db_execute(
        "INSERT INTO users (tg_id, username, referrer_id) VALUES (%s, %s, %s) ON CONFLICT (tg_id) DO NOTHING",
        (tg_id, username, referrer_id),
        commit=True
    )


# Terms and conditions
def accept_terms(tg_id: int):
    """Пользователь принял условия использования"""
    db_execute(
        "UPDATE users SET accepted_terms = TRUE WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


def has_accepted_terms(tg_id: int) -> bool:
    """Проверить принял ли пользователь условия"""
    user = get_user(tg_id)
    return user and user[2]  # accepted_terms column


# Subscription management
def update_subscription(tg_id: int, uuid: str, username: str, subscription_until: str, squad_uuid: str):
    """Обновить подписку пользователя"""
    db_execute(
        "UPDATE users SET remnawave_uuid = %s, remnawave_username = %s, subscription_until = %s, squad_uuid = %s WHERE tg_id = %s",
        (uuid, username, subscription_until, squad_uuid, tg_id),
        commit=True
    )


def has_subscription(tg_id: int) -> bool:
    """Проверить есть ли активная подписка"""
    user = get_user(tg_id)
    return user and user[3] is not None  # remnawave_uuid column


# Payment management
def create_payment(tg_id: int, tariff_code: str, amount: float, provider: str, invoice_id: str):
    """Создать запись о платеже"""
    from datetime import datetime
    db_execute(
        """
        INSERT INTO payments (tg_id, tariff_code, amount, created_at, provider, invoice_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (tg_id, tariff_code, amount, datetime.utcnow().isoformat(), provider, str(invoice_id)),
        commit=True
    )


def get_pending_payments():
    """Получить все ожидающие платежи"""
    return db_execute(
        "SELECT id, tg_id, invoice_id, tariff_code FROM payments WHERE status = 'pending' AND provider = 'cryptobot'",
        fetchall=True
    )


def get_last_pending_payment(tg_id: int):
    """Получить последний ожидающий платеж пользователя"""
    return db_execute(
        "SELECT invoice_id, tariff_code FROM payments WHERE tg_id = %s AND status = 'pending' AND provider = 'cryptobot' ORDER BY id DESC LIMIT 1",
        (tg_id,),
        fetchone=True
    )


def update_payment_status(payment_id: int, status: str):
    """Обновить статус платежа"""
    db_execute(
        "UPDATE payments SET status = %s WHERE id = %s",
        (status, payment_id),
        commit=True
    )


def update_payment_status_by_invoice(invoice_id: str, status: str):
    """Обновить статус платежа по invoice_id"""
    db_execute(
        "UPDATE payments SET status = %s WHERE invoice_id = %s",
        (status, invoice_id),
        commit=True
    )


# Referral management
def update_referral_count(tg_id: int):
    """Увеличить счётчик рефералов"""
    db_execute(
        "UPDATE users SET referral_count = referral_count + 1 WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


def increment_active_referrals(tg_id: int):
    """Увеличить счётчик активных рефералов"""
    db_execute(
        "UPDATE users SET active_referrals = active_referrals + 1 WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


def get_referral_stats(tg_id: int):
    """Получить статистику рефералов пользователя"""
    return db_execute(
        "SELECT referral_count, active_referrals FROM users WHERE tg_id = %s",
        (tg_id,),
        fetchone=True
    )


def get_referrer(tg_id: int):
    """Получить информацию о рефералите"""
    return db_execute(
        "SELECT referrer_id, first_payment FROM users WHERE tg_id = %s",
        (tg_id,),
        fetchone=True
    )


def mark_first_payment(tg_id: int):
    """Отметить что пользователь сделал первый платёж"""
    db_execute(
        "UPDATE users SET first_payment = TRUE WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


# Gift management
def is_gift_received(tg_id: int) -> bool:
    """Проверить получил ли пользователь подарок"""
    user = get_user(tg_id)
    return user and user[8]  # gift_received column


def mark_gift_received(tg_id: int):
    """Отметить что пользователь получил подарок"""
    db_execute(
        "UPDATE users SET gift_received = TRUE WHERE tg_id = %s",
        (tg_id,),
        commit=True
    )


# Promo code management
def get_promo_code(code: str):
    """Получить информацию о промокоде"""
    return db_execute(
        "SELECT days, max_uses, used_count, active FROM promo_codes WHERE code = %s",
        (code,),
        fetchone=True
    )


def create_promo_code(code: str, days: int, max_uses: int):
    """Создать новый промокод"""
    db_execute(
        "INSERT INTO promo_codes (code, days, max_uses, active) VALUES (%s, %s, %s, TRUE) ON CONFLICT (code) DO UPDATE SET days = %s, max_uses = %s, active = TRUE",
        (code.upper(), days, max_uses, days, max_uses),
        commit=True
    )


def increment_promo_usage(code: str):
    """Увеличить счётчик использования промокода"""
    db_execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = %s",
        (code,),
        commit=True
    )
