import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8520411926:AAFcduqngB2ZMCp3RS4yZ8hwkcyf-yOmWyU")
logger.info(f"✅ BOT_TOKEN loaded: {'***' + BOT_TOKEN[-10:] if BOT_TOKEN else 'NOT SET'}")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "508663:AAZcVJabRaP6NTah1LVJVl3p1E0GYTid9GK")

# XUI Panel Configuration
XUI_PANEL_URL = os.getenv("XUI_PANEL_URL", "https://195.133.21.73:2053")
XUI_PANEL_PATH = os.getenv("XUI_PANEL_PATH", "/ozsDaJc9vZ4iwfvWZi/panel")
XUI_USERNAME = os.getenv("XUI_USERNAME", "GtFIrnml0B")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "yrbFCWxMJY")

# Subscription Configuration
SUB_PORT = int(os.getenv("SUB_PORT", "2096"))
SUB_EXTERNAL_HOST = os.getenv("SUB_EXTERNAL_HOST", "195.133.21.73")
INBOUND_ID = int(os.getenv("INBOUND_ID", "2"))

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
