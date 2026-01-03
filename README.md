# SPN VPN Bot

Telegram бот для управления подписками на VPN-сервис SPN с интеграцией Neon PostgreSQL для хранения данных.

## 🔒 Безопасность

**ВАЖНО:** Никогда не коммитьте `.env` файл с реальными credentials!

- Все sensitive данные хранятся в переменных окружения (`.env`)
- `.env` файл находится в `.gitignore`
- На VPS сервере используйте переменные окружения системы (systemd, Docker и т.д.)

## 📋 Требования

- Python 3.8+
- PostgreSQL (Neon)
- Telegram Bot Token
- CryptoBot API Token

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта, скопировав из `.env.example`:

```bash
cp .env.example .env
```

Заполните следующие переменные:

```env
# Bot
BOT_TOKEN=ваш_token_от_botfather

# Database (Neon)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require&channel_binding=require

# CryptoBot
CRYPTOBOT_TOKEN=ваш_cryptobot_token

# Xray Panel
XUI_PANEL_URL=https://ваш_ip:2053
XUI_PANEL_PATH=/panel_path
XUI_USERNAME=username
XUI_PASSWORD=password
XUI_INBOUND_ID=2

# Subscription
SUB_PORT=2096
SUB_EXTERNAL_HOST=ваш_server_ip

# Channels
NEWS_CHANNEL_ID=@спн_newsvpn
NEWS_CHANNEL_URL=https://t.me/spn_newsvpn
TELEGRAPH_AGREEMENT_URL=https://telegra.ph/agreement

# Admin
OWNER_ID=ваш_user_id
ADMIN_USERNAME=ваш_username
```

### 3. Запуск бота

```bash
python vpn_bot.py
```

Бот автоматически:
- Подключится к Neon базе данных
- Создаст все необходимые таблицы
- Начнет прослушивать команды

## 📊 Архитектура проекта

```
.
├── vpn_bot.py              # Точка входа
├── config.py               # Конфигурация (читает из .env)
├── database.py             # Neon connection pool и инициализация
├── db_models.py            # Query функции для всех таблиц
├── models.py               # FSM состояния
├── services.py             # Бизнес-логика
├── utils.py                # Утилиты
├── ui.py                   # UI и клавиатуры
├── xui_api.py              # Xray панель API
├── cryptobot_api.py        # CryptoBot API
├── handlers/
│   ├── commands.py         # Команды /start, /newcode и т.д.
│   └── callbacks.py        # Callback handlers для кнопок
├── requirements.txt        # Python зависимости
├── .env.example            # Пример переменных окружения
└── .gitignore             # Git исключения
```

## 💾 База данных

### Таблицы

**users** - VPN клиенты пользователей
```sql
user_id (BIGINT) | uuid | sub_id | email | created_at | updated_at
```

**promo_codes** - Промокоды
```sql
code | days | activations_left | created_at
```

**referrals** - Рефералы
```sql
id | referrer_id | referred_user_id | created_at
```

**paid_users** - Пользователи которые оплатили
```sql
user_id | paid_at
```

**user_gifts** - Пользователи получившие подарок
```sql
user_id | gift_date
```

## 🔐 Развертывание на VPS

### Вариант 1: systemd сервис

Создайте `/etc/systemd/system/vpn-bot.service`:

```ini
[Unit]
Description=SPN VPN Bot
After=network.target

[Service]
Type=simple
User=vpnbot
WorkingDirectory=/home/vpnbot/vpn_bot
Environment="DATABASE_URL=postgresql://..."
Environment="BOT_TOKEN=..."
Environment="CRYPTOBOT_TOKEN=..."
# ... другие переменные ...
ExecStart=/usr/bin/python3 /home/vpnbot/vpn_bot/vpn_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите:
```bash
sudo systemctl enable vpn-bot
sudo systemctl start vpn-bot
```

### Вариант 2: Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "vpn_bot.py"]
```

Запустите:
```bash
docker build -t vpn-bot .
docker run -d \
  -e DATABASE_URL="postgresql://..." \
  -e BOT_TOKEN="..." \
  --name vpn-bot \
  vpn-bot
```

## 📝 Доступные команды

### Пользовательские
- `🆕 Оформить подписку` - Купить подписку
- `📊 Моя подписка` - Информация о подписке
- `📱 Как подключиться` - Инструкция подключения
- `🎁 Бонус за друга` - Реферальная программа
- `🔑 Ввести промокод` - Активировать промокод
- `🎉 Получить подарок` - Подарок за подписку на канал

### Администраторские
- `/newcode [код] [дней] [активаций]` - Создать промокод
- `/givesub [user_id] [дней]` - Выдать подписку
- `/message [текст]` - Рассылка всем пользователям

## 🐛 Troubleshooting

### Ошибка подключения к Neon
```
Failed to initialize database: invalid connection string
```
- Проверьте `DATABASE_URL` в `.env`
- Убедитесь что база данных в Neon создана

### Ошибка подключения к Xray панели
```
Ошибка подключения к панели: Connection refused
```
- Проверьте IP адрес и порт панели
- Убедитесь что панель доступна из вашего VPS

### Бот не отвечает на команды
- Проверьте что `BOT_TOKEN` правильный
- Убедитесь что база данных инициализирована
- Посмотрите логи: `python vpn_bot.py` (без фона)

## 📚 Дополнительно

- [Документация Neon](https://neon.tech/docs)
- [Документация asyncpg](https://magicstack.github.io/asyncpg)
- [Документация aiogram](https://docs.aiogram.dev)
