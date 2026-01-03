#!/bin/bash

###############################################################################
# SPN VPN Bot - Initial Deployment Script
# 
# Использование:
#   chmod +x deploy.sh
#   sudo ./deploy.sh
#
# Этот скрипт выполняет полное начальное развертывание бота:
# 1. Обновляет систему
# 2. Устанавливает зависимости (Python, Git, PostgreSQL клиент)
# 3. Создает пользователя vpnbot
# 4. Клонирует проект
# 5. Создает виртуальное окружение
# 6. Устанавливает Python пакеты
# 7. Создает systemd сервис
# 8. Запускает бота
#
###############################################################################

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка что скрипт запущен от root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Ошибка: этот скрипт должен быть запущен от root${NC}"
   echo "Используйте: sudo ./deploy.sh"
   exit 1
fi

echo -e "${GREEN}=== SPN VPN Bot - Начальное развертывание ===${NC}\n"

# ============================================================================
# Шаг 1: Обновление системы
# ============================================================================
echo -e "${YELLOW}[1/7] Обновление системы...${NC}"
apt update
apt upgrade -y
echo -e "${GREEN}✓ Система обновлена${NC}\n"

# ============================================================================
# Шаг 2: Установка зависимостей
# ============================================================================
echo -e "${YELLOW}[2/7] Установка зависимостей (Python, Git, PostgreSQL)...${NC}"
apt install -y python3 python3-pip python3-venv git postgresql-client
echo -e "${GREEN}✓ Зависимости установлены${NC}\n"

# ============================================================================
# Шаг 3: Создание пользователя vpnbot
# ============================================================================
echo -e "${YELLOW}[3/7] Создание пользователя vpnbot...${NC}"
if id "vpnbot" &>/dev/null; then
    echo "  Пользователь vpnbot уже существует"
else
    useradd -m -s /bin/bash vpnbot
    echo -e "${GREEN}✓ Пользователь vpnbot создан${NC}"
fi
echo

# ============================================================================
# Шаг 4: Клонирование проекта
# ============================================================================
echo -e "${YELLOW}[4/7] Клонирование проекта...${NC}"

# Если проект уже существует, обновляем его
if [ -d "/home/vpnbot/vpn_bot" ]; then
    echo "  Проект уже существует, обновляю..."
    cd /home/vpnbot/vpn_bot
    git pull origin main
else
    echo "  Клонирую новый проект..."
    cd /home/vpnbot
    # Замените на ваш GitHub репозиторий
    git clone https://github.com/YOUR_USERNAME/vpn_bot.git
    cd vpn_bot
fi

# Выправьте права доступа
chown -R vpnbot:vpnbot /home/vpnbot/vpn_bot
echo -e "${GREEN}✓ Проект готов${NC}\n"

# ============================================================================
# Шаг 5: Создание виртуального окружения и установка пакетов
# ============================================================================
echo -e "${YELLOW}[5/7] Создание виртуального окружения Python...${NC}"

cd /home/vpnbot/vpn_bot

# Создайте venv если не существует
if [ ! -d "venv" ]; then
    sudo -u vpnbot python3 -m venv venv
    echo -e "${GREEN}✓ Виртуальное окружение создано${NC}"
else
    echo "  Виртуальное окружение уже существует"
fi

echo -e "${YELLOW}Установка Python пакетов...${NC}"
# Активируйте venv и установите пакеты
sudo -u vpnbot bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo -e "${GREEN}✓ Python пакеты установлены${NC}\n"

# ============================================================================
# Шаг 6: Создание .env файла
# ============================================================================
echo -e "${YELLOW}[6/7] Создание файла .env...${NC}"

if [ ! -f "/home/vpnbot/vpn_bot/.env" ]; then
    sudo -u vpnbot cp .env.example .env
    echo -e "${YELLOW}ВНИМАНИЕ: Создан файл .env из шаблона${NC}"
    echo -e "${RED}ВАЖНО: Отредактируйте /home/vpnbot/vpn_bot/.env с реальными значениями:${NC}"
    echo "  nano /home/vpnbot/vpn_bot/.env"
    echo
    echo -e "${RED}Нужные переменные:${NC}"
    echo "  - BOT_TOKEN (от BotFather в Telegram)"
    echo "  - DATABASE_URL (строка подключения к Neon)"
    echo "  - CRYPTOBOT_TOKEN"
    echo "  - XUI_PANEL_URL, XUI_USERNAME, XUI_PASSWORD"
    echo "  - SUB_EXTERNAL_HOST (IP вашего сервера)"
    echo "  - OWNER_ID (ваш Telegram ID)"
    echo
    read -p "Нажмите Enter когда заполните .env файл..."
else
    echo "  .env файл уже существует"
fi

echo -e "${GREEN}✓ Конфигурация готова${NC}\n"

# ============================================================================
# Шаг 7: Создание systemd сервиса
# ============================================================================
echo -e "${YELLOW}[7/7] Создание systemd сервиса...${NC}"

cat > /etc/systemd/system/vpn-bot.service << 'EOF'
[Unit]
Description=SPN VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=vpnbot
WorkingDirectory=/home/vpnbot/vpn_bot
Environment="PATH=/home/vpnbot/vpn_bot/venv/bin"
EnvironmentFile=/home/vpnbot/vpn_bot/.env

ExecStart=/home/vpnbot/vpn_bot/venv/bin/python3 /home/vpnbot/vpn_bot/vpn_bot.py

# Автоматический перезапуск при сбое
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vpn-bot

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузите systemd конфигурацию
systemctl daemon-reload

# Включите автозапуск
systemctl enable vpn-bot

# Запустите сервис
systemctl start vpn-bot

# Проверьте статус
sleep 2
if systemctl is-active --quiet vpn-bot; then
    echo -e "${GREEN}✓ Сервис создан и запущен успешно${NC}"
else
    echo -e "${RED}✗ Ошибка при запуске сервиса${NC}"
    echo "Посмотрите логи:"
    echo "  sudo journalctl -u vpn-bot -n 50"
    exit 1
fi

echo

# ============================================================================
# Завершение
# ============================================================================
echo -e "${GREEN}=== Развертывание завершено! ===${NC}\n"

echo -e "${GREEN}Полезные команды:${NC}"
echo "  # Просмотр статуса:"
echo "  sudo systemctl status vpn-bot"
echo
echo "  # Просмотр логов:"
echo "  sudo journalctl -u vpn-bot -f"
echo
echo "  # Перезапуск:"
echo "  sudo systemctl restart vpn-bot"
echo
echo "  # Редактирование конфига:"
echo "  nano /home/vpnbot/vpn_bot/.env"
echo

echo -e "${YELLOW}Следующие шаги:${NC}"
echo "  1. Отредактируйте .env файл с реальными данными"
echo "  2. Перезапустите бота: sudo systemctl restart vpn-bot"
echo "  3. Проверьте логи: sudo journalctl -u vpn-bot -f"
echo

systemctl status vpn-bot
