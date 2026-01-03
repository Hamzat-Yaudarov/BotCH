import asyncpg
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL базой данных Neon"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Инициализация подключения к БД и создание таблиц"""
        try:
            self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
            logger.info("✅ Подключение к Neon успешно")
            await self._create_tables()
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise

    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Соединение с БД закрыто")

    async def _create_tables(self):
        """Создание таблиц если их нет"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_clients (
                    user_id BIGINT PRIMARY KEY,
                    uuid VARCHAR(255) NOT NULL,
                    sub_id VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    expiry_time BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code VARCHAR(50) PRIMARY KEY,
                    days INT NOT NULL,
                    activations_left INT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_user_id BIGINT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_user_id)
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS paid_users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    invoice_id VARCHAR(255) NOT NULL UNIQUE,
                    paid_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Добавляем колонку amount если её нет (для существующих таблиц)
            try:
                # Проверяем, существует ли колонка
                column_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='paid_users' AND column_name='amount'
                    )
                """)

                if not column_exists:
                    await conn.execute("""
                        ALTER TABLE paid_users ADD COLUMN amount INT NOT NULL DEFAULT 0;
                    """)
                    logger.info("✅ Колонка 'amount' добавлена в таблицу 'paid_users'")
            except Exception as e:
                logger.error(f"⚠️ Ошибка при добавлении колонки 'amount': {e}")

            # Добавляем колонку invoice_id если её нет (для существующих таблиц)
            try:
                # Проверяем, существует ли колонка
                column_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='paid_users' AND column_name='invoice_id'
                    )
                """)

                if not column_exists:
                    await conn.execute("""
                        ALTER TABLE paid_users ADD COLUMN invoice_id VARCHAR(255) UNIQUE DEFAULT NULL;
                    """)
                    logger.info("✅ Колонка 'invoice_id' добавлена в таблицу 'paid_users'")
            except Exception as e:
                logger.error(f"⚠️ Ошибка при добавлении колонки 'invoice_id': {e}")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_gifts (
                    user_id BIGINT PRIMARY KEY,
                    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            logger.info("✅ Таблицы созданы/проверены")

    # ===== User Clients =====

    async def get_user_client(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные клиента пользователя"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM user_clients WHERE user_id = $1", user_id)

    async def create_user_client(
        self,
        user_id: int,
        uuid: str,
        sub_id: str,
        email: str,
        expiry_time: int = 0
    ) -> None:
        """Создать запись клиента"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_clients (user_id, uuid, sub_id, email, expiry_time)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (user_id) DO UPDATE SET
                   uuid = $2, sub_id = $3, email = $4, expiry_time = $5
                """,
                user_id, uuid, sub_id, email, expiry_time
            )

    async def update_user_client_expiry(self, user_id: int, expiry_time: int) -> None:
        """Обновить время истечения подписки"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE user_clients SET expiry_time = $1 WHERE user_id = $2",
                expiry_time, user_id
            )

    async def client_exists(self, user_id: int) -> bool:
        """Проверить наличие клиента"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM user_clients WHERE user_id = $1", user_id)
            return result > 0

    # ===== Promo Codes =====

    async def get_promo_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Получить промокод"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM promo_codes WHERE code = $1", code)

    async def create_promo_code(self, code: str, days: int, activations: int) -> None:
        """Создать промокод"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO promo_codes (code, days, activations_left)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (code) DO UPDATE SET
                   days = $2, activations_left = $3
                """,
                code.upper(), days, activations
            )

    async def use_promo_code(self, code: str) -> bool:
        """Использовать промокод (уменьшить активации)"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                promo = await conn.fetchrow("SELECT * FROM promo_codes WHERE code = $1", code)
                if not promo or promo['activations_left'] <= 0:
                    return False

                await conn.execute(
                    "UPDATE promo_codes SET activations_left = activations_left - 1 WHERE code = $1",
                    code
                )
                
                # Удалить если закончились активации
                await conn.execute(
                    "DELETE FROM promo_codes WHERE code = $1 AND activations_left <= 0",
                    code
                )
                return True

    # ===== Referrals =====

    async def add_referral(self, referrer_id: int, referred_user_id: int) -> None:
        """Добавить реферального пользователя"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """INSERT INTO referrals (referrer_id, referred_user_id)
                       VALUES ($1, $2)
                       ON CONFLICT DO NOTHING
                    """,
                    referrer_id, referred_user_id
                )
            except asyncpg.UniqueViolationError:
                pass

    async def get_referrals(self, referrer_id: int) -> List[int]:
        """Получить список рефералов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT referred_user_id FROM referrals WHERE referrer_id = $1",
                referrer_id
            )
            return [row['referred_user_id'] for row in rows]

    # ===== Paid Users =====

    async def mark_user_paid(self, user_id: int, amount: int, invoice_id: str) -> None:
        """Отметить пользователя как оплативого"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO paid_users (user_id, amount, invoice_id)
                   VALUES ($1, $2, $3)
                """,
                user_id, amount, invoice_id
            )

    async def is_user_paid(self, user_id: int) -> bool:
        """Проверить оплатил ли пользователь"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM paid_users WHERE user_id = $1",
                user_id
            )
            return result > 0

    # ===== User Gifts =====

    async def has_user_received_gift(self, user_id: int) -> bool:
        """Проверить получил ли пользователь подарок"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM user_gifts WHERE user_id = $1",
                user_id
            )
            return result > 0

    async def add_user_gift(self, user_id: int) -> None:
        """Добавить подарок пользователю"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO user_gifts (user_id) VALUES ($1)",
                    user_id
                )
            except asyncpg.UniqueViolationError:
                pass

    # ===== Utility Methods =====

    async def get_all_user_ids(self) -> List[int]:
        """Получить список всех user_id для рассылки"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM user_clients")
            return [row['user_id'] for row in rows]

    async def get_paid_referrals(self, referrer_id: int) -> List[int]:
        """Получить список оплативших рефералов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT p.user_id
                   FROM paid_users p
                   INNER JOIN referrals r ON p.user_id = r.referred_user_id
                   WHERE r.referrer_id = $1
                """,
                referrer_id
            )
            return [row['user_id'] for row in rows]

    async def get_referrer_id(self, user_id: int) -> Optional[int]:
        """Получить ID пригласившего пользователя"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT referrer_id FROM referrals WHERE referred_user_id = $1 LIMIT 1",
                user_id
            )
            return result


# Глобальный объект БД
db = Database()
