import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8520411926:AAFcduqngB2ZMCp3RS4yZ8hwkcyf-yOmWyU")
logger.info(f"✅ BOT_TOKEN loaded: {'***' + BOT_TOKEN[-10:] if BOT_TOKEN else 'NOT SET'}")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "508663:AAZcVJabRaP6NTah1LVJVl3p1E0GYTid9GK")

# XUI Panels Configuration - список серверов для создания клиентов
# Каждый пользователь будет создан на всех этих серверах с одинаковыми UUID и Email
XUI_SERVERS = [
    {
        "name": "Server 1",
        "url": os.getenv("XUI_PANEL_URL_1", "https://195.133.21.73:2053"),
        "path": os.getenv("XUI_PANEL_PATH_1", "/ozsDaJc9vZ4iwfvWZi/panel"),
        "username": os.getenv("XUI_USERNAME_1", "GtFIrnml0B"),
        "password": os.getenv("XUI_PASSWORD_1", "yrbFCWxMJY"),
        "sub_port": int(os.getenv("SUB_PORT_1", "2096")),
        "sub_host": os.getenv("SUB_EXTERNAL_HOST_1", "195.133.21.73"),
        "inbound_id": int(os.getenv("INBOUND_ID_1", "2"))
    },
    {
        "name": "Server 2",
        "url": os.getenv("XUI_PANEL_URL_2", "https://5.129.219.118:2053"),
        "path": os.getenv("XUI_PANEL_PATH_2", "/gAqwp06Wzq8HWNEo0f/panel"),
        "username": os.getenv("XUI_USERNAME_2", ""),
        "password": os.getenv("XUI_PASSWORD_2", ""),
        "sub_port": int(os.getenv("SUB_PORT_2", "2096")),
        "sub_host": os.getenv("SUB_EXTERNAL_HOST_2", "195.133.21.73"),
        "inbound_id": int(os.getenv("INBOUND_ID_2", "1"))
    }
]

# Legacy single-server configuration (для обратной совместимости)
XUI_PANEL_URL = XUI_SERVERS[0]["url"]
XUI_PANEL_PATH = XUI_SERVERS[0]["path"]
XUI_USERNAME = XUI_SERVERS[0]["username"]
XUI_PASSWORD = XUI_SERVERS[0]["password"]
SUB_PORT = XUI_SERVERS[0]["sub_port"]
SUB_EXTERNAL_HOST = XUI_SERVERS[0]["sub_host"]
INBOUND_ID = XUI_SERVERS[0]["inbound_id"]

logger.info(f"✅ Loaded {len(XUI_SERVERS)} XUI servers")

# Admin Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Youdarov")
OWNER_ID = int(os.getenv("OWNER_ID", "6910097562"))

# Channel Configuration
NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID", "@spn_newsvpn")
NEWS_CHANNEL_URL = os.getenv("NEWS_CHANNEL_URL", "https://t.me/spn_newsvpn")
TELEGRAPH_AGREEMENT_URL = os.getenv("TELEGRAPH_AGREEMENT_URL", "https://telegra.ph/Polzovatelskoe-soglashenie-dlya-servisa-SPN-Uskoritel-interneta-01-01")

# Database Configuration (Neon)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Amb6VC5tLaDB@ep-cool-wave-agw01v53-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
if DATABASE_URL:
    # Show masked version
    masked_url = DATABASE_URL.split('@')[0] + '@' + DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else "***"
    logger.info(f"✅ DATABASE_URL loaded: {masked_url}")
else:
    logger.error("❌ DATABASE_URL NOT SET!")

# Subscription Prices (months -> price in RUB)
PRICES: Dict[int, int] = {
    1: 100,
    3: 249,
    6: 449,
    12: 990
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
