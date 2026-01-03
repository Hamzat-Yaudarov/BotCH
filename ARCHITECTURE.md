# 🏗️ Архитектура хостинга SPN VPN Bot

Этот документ показывает как всё работает вместе на вашем VPS сервере.

---

## 📊 Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                         TELEGRAM USERS                           │
│                                                                   │
│    [User1]   [User2]   [User3] ... [UserN]                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    Telegram Bot API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    VPS СЕРВЕР (VirtualHost)                     │
│                    195.133.21.73                                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           SYSTEMD Service Manager                        │  │
│  │  (управляет запуском/остановкой/перезапуском)          │  │
│  │                                                          │  │
│  │  vpn-bot.service (systemd config)                       │  │
│  │  ├─ Type: simple                                        │  │
│  │  ├─ User: vpnbot                                        │  │
│  │  ├─ Restart: always                                     │  │
│  │  └─ ExecStart: python3 vpn_bot.py                       │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │         PYTHON APPLICATION (BOT)                         │  │
│  │                                                          │  │
│  │  vpn_bot.py                                            │  │
│  │  ├─ config.py (читает .env)                           │  │
│  │  ├─ database.py (asyncpg connection pool)             │  │
│  │  ├─ db_models.py (queries)                            │  │
│  │  ├─ services.py (business logic)                       │  │
│  │  ├─ handlers/                                         │  │
│  │  │  ├─ commands.py (/start, /newcode и т.д.)         │  │
│  │  │  └─ callbacks.py (кнопки)                         │  │
│  │  ├─ xui_api.py (X-UI Panel)                          │  │
│  │  └─ cryptobot_api.py (CryptoBot)                      │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                    ┌────────┴────────┐                          │
│                    │                 │                          │
│         ┌──────────▼────────┐   ┌────▼──────────┐              │
│         │  NEON DATABASE    │   │  X-UI PANEL   │              │
│         │  (PostgreSQL)     │   │  (VPN Config) │              │
│         │                  │   │              │              │
│         │ ├─ users        │   │ ├─ clients  │              │
│         │ ├─ promo_codes  │   │ ├─ subscr  │              │
│         │ ├─ referrals    │   │ ├─ traffic │              │
│         │ ├─ paid_users   │   │ └─ inbounds│              │
│         │ └─ user_gifts   │   │            │              │
│         └──────────────────┘   └──────┬─────┘              │
└─────────────────────────────────────────────────────────────┘
                                         │
                            ┌────────────▼──────────┐
                            │ CryptoBot API         │
                            │ (Payment Processing)  │
                            └───────────────────────┘
```

---

## 📁 Структура файлов на VPS

```
/home/vpnbot/
├── vpn_bot/                    # Основная папка проекта
│   ├── venv/                   # Виртуальное окружение Python
│   │   ├── bin/
│   │   │   ├── python          # Python интерпретатор
│   │   │   ├── pip             # Пакетный менеджер
│   │   │   └── activate        # Скрипт активации
│   │   ├── lib/
│   │   │   └── python3.x/      # Установленные пакеты
│   │   └── ...
│   │
│   ├── handlers/               # Обработчики Telegram команд
│   │   ├── __init__.py
│   │   ├── commands.py         # /start, /newcode и т.д.
│   │   └── callbacks.py        # Кнопки и меню
│   │
│   ├── vpn_bot.py              # 🚀 Точка входа (стартует всё)
│   ├── config.py               # Конфигурация (читает .env)
│   ├── database.py             # Подключение к Neon
│   ├── db_models.py            # SQL запросы
│   ├── models.py               # FSM состояния
│   ├── services.py             # Бизнес-логика
│   ├── utils.py                # Утилиты
│   ├── ui.py                   # Интерфейс (кнопки/меню)
│   ├── xui_api.py              # X-UI Panel API
│   ├── cryptobot_api.py        # CryptoBot API
│   │
│   ├── .env                    # 🔒 Конфиг (НЕ в git!)
│   ├── .env.example            # Пример .env
│   ├── .gitignore              # Какие файлы не коммитить
│   ├── requirements.txt        # Список Python пакетов
│   │
│   ├── HOSTING.md              # Подробное руководство
│   ├── QUICK_START.md          # Краткое руководство
│   ├── COMMANDS_REFERENCE.md   # Справочник команд
│   ├── deploy.sh               # Скрипт первого развертывания
│   ├── update.sh               # Скрипт обновления
│   ├── README.md               # Основная документация
│   └── .git/                   # Git история
│
└── backups/                    # 💾 Резервные копии
    ├── backup_20240101_120000.tar.gz
    ├── backup_20240102_150000.tar.gz
    └── ...

/etc/systemd/system/
├── vpn-bot.service             # ⚙️ Конфиг systemd (управление ботом)
└── ...
```

---

## 🔄 Процесс запуска (Boot Sequence)

### Что происходит когда вы нажимаете `systemctl start vpn-bot`:

```
1. systemd читает /etc/systemd/system/vpn-bot.service
   │
2. systemd запускает: 
   python3 /home/vpnbot/vpn_bot/venv/bin/python3 vpn_bot.py
   │
3. Python загружает vpn_bot.py
   │
4. vpn_bot.py импортирует модули:
   ├─ Читает конфиг из .env файла
   ├─ Инициализирует database (создает connection pool к Neon)
   ├─ Подключается к Telegram Bot API
   ├─ Регистрирует обработчики команд и кнопок
   └─ Начинает слушать сообщения от пользователей
   │
5. Бот готов! Когда пользователь пишет /start:
   │
6. Telegram отправляет сообщение на VPS
   │
7. Handler обрабатывает сообщение
   ├─ Читает данные из .env и database
   ├─ Вызывает функции из services.py
   ├─ Отправляет запросы к X-UI Panel API
   ├─ Отправляет запросы к CryptoBot API
   └─ Отправляет ответ пользователю
```

---

## 🔗 Взаимодействие компонентов

```
USER (Telegram)
    │
    ├──► Telegram Bot API
    │
    │    (отправляет сообщение боту)
    │
    └──► VPS Server:8080 (webhook или polling)
         │
         ├──► vpn_bot.py (обработка команды)
         │
         ├──► handlers/commands.py или handlers/callbacks.py
         │    (определяет какой handler вызвать)
         │
         ├──► services.py
         │    (бизнес-логика: добавить пользователя, проверить платеж и т.д.)
         │
         ├──► database.py + db_models.py
         │    (SQL запросы к Neon)
         │
         ├──► NEON DATABASE
         │    (сохранение данных)
         │
         ├──► xui_api.py (если нужно создать/обновить VPN подписку)
         │    (HTTP запрос к X-UI Panel)
         │
         ├──► X-UI PANEL
         │    (создает VPN клиента)
         │
         └──► cryptobot_api.py (если оплата)
              (HTTP запрос к CryptoBot)
              │
              └──► CRYPTOBOT API
                   (создает счет для оплаты)
```

---

## 🔒 Безопасность - слои защиты

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Пользователь VPS (vpnbot)              │
│ ├─ Не имеет root доступа                        │
│ ├─ Может только читать свою папку               │
│ └─ Ограниченные права (не может сломать систему)│
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Layer 2: .env файл (.gitignore)                 │
│ ├─ Содержит токены и пароли                     │
│ ├─ Не попадает в Git историю                    │
│ └─ Есть только на сервере                       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Layer 3: Переменные окружения (systemd)         │
│ ├─ .env загружается в EnvironmentFile           │
│ ├─ Хранятся в памяти процесса                   │
│ └─ Не видны в файловой системе                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Layer 4: HTTPS подключения к внешним API        │
│ ├─ X-UI Panel - HTTPS                           │
│ ├─ CryptoBot API - HTTPS                        │
│ ├─ Neon Database - SSL/TLS                      │
│ └─ Telegram Bot API - HTTPS                     │
└─────────────────────────────────────────────────┘
```

---

## 📊 Жизненный цикл запроса

### Пример: Пользователь нажимает "Оформить подписку"

```
User [Button Click] 
  │
  └──► Telegram
        │
        └──► VPS Bot (callback_query handler)
              │
              ├─1. handlers/callbacks.py:subscribe()
              │   (показывает меню выбора срока)
              │
              └─2. handlers/callbacks.py:select_duration()
                   (пользователь выбирает 1 месяц)
                   │
                   ├─3. handlers/callbacks.py:pay_cryptobot()
                   │   │
                   │   ├─4. services.py:generate_random_string()
                   │   │   (генерирует ID заказа)
                   │   │
                   │   ├─5. cryptobot_api.py:create_cryptobot_invoice()
                   │   │   │
                   │   │   └─ HTTP POST к CryptoBot
                   │   │      "Создать счет на 100 рублей"
                   │   │
                   │   └─6. Отправить ссылку оплаты пользователю
                   │
                   └─7. handlers/callbacks.py:check_payment()
                       (пользователь нажимает "Проверить оплату")
                       │
                       ├─8. cryptobot_api.py:check_cryptobot_payment()
                       │   │
                       │   └─ HTTP GET к CryptoBot
                       │      "Оплачен ли счет?"
                       │
                       ├─9. services.py:create_or_extend_client()
                       │   │
                       │   ├─10. xui_api.py:create_client()
                       │   │    │
                       │   │    └─ HTTP POST к X-UI Panel
                       │   │       "Создать VPN клиента"
                       │   │
                       │   ├─11. db_models.py:create_user()
                       │   │    │
                       │   │    └─ SQL INSERT в users таблицу
                       │   │       (сохранить UUID и sub_id)
                       │   │
                       │   └─12. services.py:add_paid_user()
                       │        │
                       │        └─ SQL INSERT в paid_users таблицу
                       │           (отметить что оплачено)
                       │
                       └─13. Отправить ссылку подписки пользователю
                            "Готово! Вот ваша ссылка для подключения"
```

---

## 🚀 Жизненный цикл процесса

```
┌─ BOOT (загрузка сервера) ────────┐
│                                   │
│ systemd запускает vpn-bot.service │
│         │                          │
│         ▼                          │
│   python3 vpn_bot.py              │
│         │                          │
│         ├─ init_db()              │
│         │  └─ создает таблицы    │
│         │                          │
│         ├─ dp.start_polling()     │
│         │  (слушает сообщения)   │
│         │                          │
│         └─ БОТ РАБОТАЕТ ✅        │
│                                   │
└───────────────────────────────────┘
              │
              │ (пока работает)
              │
         ┌────▼───────┐
         │ MONITORING │
         │             │
         │ journalctl  │ (логирование)
         │ htop        │ (ресурсы)
         └───────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
  CRASH    UPDATE    REBOOT
    │         │         │
    ▼         ▼         ▼
  Auto-    systemctl  Auto-
  Restart  restart    Restart
    │         │         │
    └─────────┴─────────┘
           │
           └──► БОТ РАБОТАЕТ ✅
```

---

## 💾 Стратегия данных

```
┌──────────────────────────────────────────────────┐
│            ДАННЫЕ ПОЛЬЗОВАТЕЛЯ                   │
└──────────────────────────────────────────────────┘

NEON Database (PRIMARY)
├─ users (UUID, sub_id, email)
├─ promo_codes (промокоды)
├─ referrals (кто приласил кого)
├─ paid_users (кто оплатил)
└─ user_gifts (кто получил подарок)

X-UI Panel (SECONDARY - DERIVED)
└─ clients (синхронизируется с users)
   └─ Данные о подключениях (expiry, traffic)

Telegram (LOOKUP ONLY)
└─ Chat members (для проверки подписки на канал)


ПОТОК СИНХРОНИЗАЦИИ:
Bot ──► Neon Database ──► X-UI Panel
        ↑   ↑   ↑
        │   │   └─ Обновление во всех трех местах


РЕЗЕРВНАЯ КОПИЯ:
Daily Backup ──► /home/vpnbot/backups/backup_YYYYMMDD_HHMMSS.tar.gz
                └─ Хранится 30 дней
```

---

## 📈 Масштабирование

Текущая архитектура рассчитана на:
- 📱 ~ 1000-5000 активных пользователей
- 💾 ~ 500 МБ дискового пространства
- 🧠 ~ 100-200 МБ оперативной памяти
- ⚡ ~ 1 Гбит/сек пропускная способность

Если нужно увеличить:
1. **Более мощный VPS** - увеличить CPU и RAM
2. **Несколько ботов** - несколько инстанций на разных портах
3. **Load Balancer** - распределение нагрузки
4. **Database Replication** - для отказоустойчивости

---

## 🔍 Мониторинг в режиме реального времени

```bash
# Что смотреть:

# 1. Логи в реальном времени
sudo journalctl -u vpn-bot -f

# 2. Использование ресурсов
htop

# 3. Подключения к БД
psql -h ep-cool-wave-agw01v53-pooler.c-2.eu-central-1.aws.neon.tech \
     -U neondb_owner -d neondb \
     -c "SELECT count(*) FROM users;"

# 4. Проверка сетевых соединений
netstat -an | grep ESTABLISHED
```

---

Готово! Теперь вы понимаете всю архитектуру системы! 🎉
