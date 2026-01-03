#!/bin/bash

###############################################################################
# SPN VPN Bot - Update/Redeploy Script
#
# Использование:
#   chmod +x update.sh
#   sudo ./update.sh
#
# Этот скрипт обновляет проект и перезапускает бота:
# 1. Останавливает бота
# 2. Скачивает новый код с GitHub
# 3. Обновляет Python пакеты
# 4. Перезапускает бота
# 5. Проверяет статус
#
# Используйте этот скрипт когда нужно:
# - Обновить код (после git push)
# - Обновить зависимости
# - Применить исправления ошибок
#
###############################################################################

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверка что скрипт запущен от root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Ошибка: этот скрипт должен быть запущен от root${NC}"
   echo "Используйте: sudo ./update.sh"
   exit 1
fi

PROJECT_DIR="/home/vpnbot/vpn_bot"
BACKUP_DIR="/home/vpnbot/backups"

echo -e "${GREEN}=== SPN VPN Bot - Обновление ===${NC}\n"

# ============================================================================
# Шаг 1: Проверка проекта
# ============================================================================
echo -e "${YELLOW}[1/5] Проверка проекта...${NC}"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Ошибка: проект не найден в $PROJECT_DIR${NC}"
    echo "Сначала запустите: sudo ./deploy.sh"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Ошибка: файл .env не найден${NC}"
    echo "Откопируйте его из .env.example"
    exit 1
fi

echo -e "${GREEN}✓ Проект найден${NC}\n"

# ============================================================================
# Шаг 2: Создание резервной копии
# ============================================================================
echo -e "${YELLOW}[2/5] Создание резервной копии...${NC}"

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"

cd "$PROJECT_DIR"
tar -czf "$BACKUP_FILE" . --exclude=venv --exclude=__pycache__ --exclude=.git

echo -e "${GREEN}✓ Резервная копия создана: $BACKUP_FILE${NC}\n"

# ============================================================================
# Шаг 3: Остановка бота
# ============================================================================
echo -e "${YELLOW}[3/5] Остановка бота...${NC}"

if systemctl is-active --quiet vpn-bot; then
    systemctl stop vpn-bot
    sleep 2
    echo -e "${GREEN}✓ Бот остановлен${NC}"
else
    echo "  Бот не работает"
fi
echo

# ============================================================================
# Шаг 4: Обновление кода и зависимостей
# ============================================================================
echo -e "${YELLOW}[4/5] Обновление кода и зависимостей...${NC}"

cd "$PROJECT_DIR"

# Скачайте новый код
echo "  Скачиваю новый код..."
git fetch origin
git reset --hard origin/main

echo "  Обновляю Python пакеты..."
# Обновите пакеты
sudo -u vpnbot bash -c "source venv/bin/activate && pip install --upgrade -r requirements.txt"

echo -e "${GREEN}✓ Код и зависимости обновлены${NC}\n"

# ============================================================================
# Шаг 5: Запуск бота
# ============================================================================
echo -e "${YELLOW}[5/5] Запуск бота...${NC}"

systemctl start vpn-bot

# Дайте боту время на запуск
sleep 3

if systemctl is-active --quiet vpn-bot; then
    echo -e "${GREEN}✓ Бот успешно запущен${NC}"
else
    echo -e "${RED}✗ Ошибка при запуске бота${NC}"
    echo "Посмотрите логи:"
    echo "  sudo journalctl -u vpn-bot -n 50"
    exit 1
fi

echo

# ============================================================================
# Завершение
# ============================================================================
echo -e "${GREEN}=== Обновление завершено! ===${NC}\n"

echo -e "${BLUE}Информация об обновлении:${NC}"
echo "  Время: $(date)"
echo "  Резервная копия: $BACKUP_FILE"
echo "  Git коммит: $(cd $PROJECT_DIR && git log -1 --oneline)"
echo

echo -e "${GREEN}Полезные команды:${NC}"
echo "  # Просмотр статуса:"
echo "  sudo systemctl status vpn-bot"
echo
echo "  # Просмотр логов:"
echo "  sudo journalctl -u vpn-bot -f"
echo
echo "  # Откат на предыдущую версию:"
echo "  sudo systemctl stop vpn-bot"
echo "  cd $PROJECT_DIR"
echo "  tar -xzf $BACKUP_FILE ."
echo "  sudo systemctl start vpn-bot"
echo

systemctl status vpn-bot
