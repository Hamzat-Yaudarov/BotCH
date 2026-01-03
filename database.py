import asyncpg
import asyncpg
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL базой данных Neon"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Инициализация подключения к БД и создание таблиц"""
        try:
            logger.info(f"🔗 Connecting to database...")
            logger.info(f"DATABASE_URL length: {len(DATABASE_URL) if DATABASE_URL else 0}")
            if not DATABASE_URL:
                logger.error("❌ DATABASE_URL is empty or not set!")
                raise Exception("DATABASE_URL environment variable is not set")

            self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
            logger.info("✅ Подключение к Neon успешно")
            await self._create_tables()
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Соединение с БД закрыто")

    async def _create_tables(self):
        """Создание таблиц если их нет"""
        async with self.pool.acquire() as conn:
            logger.info("📋 Creating tables if they don't exist...")

            # New multi-server client tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_clients_multi (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    server_id VARCHAR(50) NOT NULL,
                    uuid VARCHAR(255) NOT NULL,
                    sub_id VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    expiry_time BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, server_id),
                    UNIQUE(sub_id),
                    UNIQUE(email)
                );
            """)

            # Legacy single-server table (for backward compatibility)
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

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_terms_acceptance (
                    user_id BIGINT PRIMARY KEY,
                    accepted_terms BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            logger.info("✅ Таблицы созданы/проверены")

    # ===== User Clients (Multi-Server) =====

    async def get_user_client(self, user_id: int, server_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Получить данные клиента пользователя

        Args:
            user_id: ID пользователя
            server_id: ID сервера (если None, возвращает первого клиента)
        """
        async with self.pool.acquire() as conn:
            if server_id:
                # Get specific server client
                return await conn.fetchrow(
                    "SELECT * FROM user_clients_multi WHERE user_id = $1 AND server_id = $2",
                    user_id, server_id
                )
            else:
                # Get first client (any server) for backward compatibility
                return await conn.fetchrow(
                    "SELECT * FROM user_clients_multi WHERE user_id = $1 ORDER BY created_at LIMIT 1",
                    user_id
                )

    async def get_user_clients(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить всех клиентов пользователя (на всех серверах)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM user_clients_multi WHERE user_id = $1 ORDER BY server_id",
                user_id
            )
            return [dict(row) for row in rows]

    async def create_user_client(
        self,
        user_id: int,
        uuid: str,
        sub_id: str,
        email: str,
        server_id: str,
        expiry_time: int = 0
    ) -> None:
        """
        Создать или обновить запись клиента для конкретного сервера

        Args:
            user_id: ID пользователя
            uuid: UUID клиента (одинаковый для всех серверов)
            sub_id: ID подписки (уникален для каждого сервера)
            email: Email клиента (одинаковый для всех серверов)
            server_id: ID сервера
            expiry_time: Время истечения в миллисекундах
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_clients_multi (user_id, server_id, uuid, sub_id, email, expiry_time)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (user_id, server_id) DO UPDATE SET
                   uuid = $3, sub_id = $4, email = $5, expiry_time = $6
                """,
                user_id, server_id, uuid, sub_id, email, expiry_time
            )

    async def update_user_client_expiry(self, user_id: int, expiry_time: int, server_id: str = None) -> None:
        """
        Обновить время истечения подписки

        Args:
            user_id: ID пользователя
            expiry_time: Новое время истечения
            server_id: ID сервера (если None, обновляет для всех серверов)
        """
        async with self.pool.acquire() as conn:
            if server_id:
                await conn.execute(
                    "UPDATE user_clients_multi SET expiry_time = $1 WHERE user_id = $2 AND server_id = $3",
                    expiry_time, user_id, server_id
                )
            else:
                # Update all servers
                await conn.execute(
                    "UPDATE user_clients_multi SET expiry_time = $1 WHERE user_id = $2",
                    expiry_time, user_id
                )

    async def client_exists(self, user_id: int, server_id: str = None) -> bool:
        """
        Проверить наличие клиента

        Args:
            user_id: ID пользователя
            server_id: ID сервера (если None, проверяет наличие на любом сервере)
        """
        async with self.pool.acquire() as conn:
            if server_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_clients_multi WHERE user_id = $1 AND server_id = $2",
                    user_id, server_id
                )
            else:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_clients_multi WHERE user_id = $1",
                    user_id
                )
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

    # ===== Terms Acceptance =====

    async def has_accepted_terms(self, user_id: int) -> bool:
        """Проверить принял ли пользователь условия"""
        try:
            if not self.pool:
                logger.error(f"❌ Database pool is None!")
                return False

            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT accepted_terms FROM user_terms_acceptance WHERE user_id = $1",
                    user_id
                )
                accepted = result or False
                logger.info(f"✅ Checking terms for user {user_id}: accepted={accepted}")
                return accepted
        except Exception as e:
            logger.error(f"❌ Error checking terms for user {user_id}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def set_terms_accepted(self, user_id: int) -> None:
        """Отметить что пользователь принял условия"""
        try:
            if not self.pool:
                logger.error(f"❌ Database pool is None!")
                return

            async with self.pool.acquire() as conn:
                logger.info(f"💾 Saving terms for user {user_id}...")
                await conn.execute(
                    """INSERT INTO user_terms_acceptance (user_id, accepted_terms)
                       VALUES ($1, TRUE)
                       ON CONFLICT (user_id) DO UPDATE SET
                       accepted_terms = TRUE
                    """,
                    user_id
                )
                logger.info(f"✅ Terms accepted saved successfully for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error saving terms acceptance for user {user_id}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


# Глобальный объект БД
db = Database()
