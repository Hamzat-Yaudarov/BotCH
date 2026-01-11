# Настройка Supabase для SPN VPN Bot

Этот документ описывает, как настроить базу данных Supabase для работы с ботом.

## Обзор

Бот поддерживает два типа хранилищ данных:
- **SQLite** (для локальной разработки) - используется по умолчанию
- **Supabase** (для продакшена на VPS) - используется, когда заданы переменные окружения

## Шаг 1: Создание таблиц в Supabase

Для работы с Supabase необходимо создать следующие таблицы:

### Таблица `users`

```sql
CREATE TABLE users (
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_referrer_id ON users(referrer_id);
```

### Таблица `payments`

```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL,
    tariff_code TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    provider TEXT,
    invoice_id TEXT UNIQUE,
    payload TEXT,
    FOREIGN KEY (tg_id) REFERENCES users(tg_id)
);

CREATE INDEX idx_payments_tg_id ON payments(tg_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
```

### Таблица `promo_codes`

```sql
CREATE TABLE promo_codes (
    code TEXT PRIMARY KEY,
    days INTEGER NOT NULL,
    max_uses INTEGER NOT NULL,
    used_count INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_promo_codes_active ON promo_codes(active);
```

## Шаг 2: Включение RLS (Row Level Security) - опционально

Для повышенной безопасности можно включить RLS политики:

```sql
-- Включаем RLS для таблиц
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_codes ENABLE ROW LEVEL SECURITY;

-- Создаем политики (пример)
CREATE POLICY "Allow service role" ON users
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');
```

## Шаг 3: Настройка переменных окружения

После создания таблиц, добавьте следующие переменные в `.env` файл:

```env
# Supabase configuration
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=YOUR_PUBLISHABLE_API_KEY
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres
```

Получить эти данные можно в панели управления Supabase:
1. Project Settings → API
2. Скопируйте Project URL
3. Скопируйте Publishable key (для `SUPABASE_KEY`)
4. Database → Connection pooling → Получите PostgreSQL URL для `DATABASE_URL`

## Шаг 4: Безопасность

⚠️ **ВАЖНО**: Никогда не коммитьте `.env` файл в репозиторий!

Уже настроено в `.gitignore`:
- `.env`
- `.env.local`
- `.env.*.local`

## Использование на VPS

При развёртывании на VPS сервере используйте системные переменные окружения вместо `.env` файла:

```bash
# Установка переменных в системе
export SUPABASE_URL="https://YOUR_PROJECT_ID.supabase.co"
export SUPABASE_KEY="YOUR_PUBLISHABLE_API_KEY"
export DATABASE_URL="postgresql://..."

# Запуск бота
python main.py
```

Или используйте файл systemd (см. `spn-vpn-bot.service`):

```ini
[Service]
Environment="SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co"
Environment="SUPABASE_KEY=YOUR_PUBLISHABLE_API_KEY"
Environment="DATABASE_URL=postgresql://..."
```

## Миграция данных из SQLite в Supabase

Если у вас уже есть данные в SQLite, следуйте этим шагам:

1. Экспортируйте данные из SQLite:
```python
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('spn_vpn_bot.db')
cursor = conn.cursor()

# Экспортируем данные
cursor.execute('SELECT * FROM users')
users = cursor.fetchall()
# ... далее импортируем в Supabase
```

2. Импортируйте в Supabase через admin API или CSV

## Проверка подключения

Бот автоматически проверит подключение к Supabase при запуске:

```
Supabase client initialized successfully
```

Если вы видите ошибку, проверьте:
- Правильность SUPABASE_URL и SUPABASE_KEY
- Доступ в интернет
- Статус Supabase сервера

## Отладка

Для отладки включите логирование:

```env
LOG_LEVEL=DEBUG
```

И проверьте логи:
```bash
tail -f bot.log
```

## Дополнительная информация

- [Документация Supabase](https://supabase.com/docs)
- [Python Supabase SDK](https://github.com/supabase-community/supabase-py)
- [PostgreSQL документация](https://www.postgresql.org/docs/)
