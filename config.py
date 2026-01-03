import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables")

OWNER_ID = int(os.getenv("OWNER_ID", 0))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment variables")

# CryptoBot Configuration
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
if not CRYPTOBOT_TOKEN:
    raise ValueError("CRYPTOBOT_TOKEN not set in environment variables")

CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Xray Panel Configuration
XUI_PANEL_URL = os.getenv("XUI_PANEL_URL")
XUI_PANEL_PATH = os.getenv("XUI_PANEL_PATH", "/ozsDaJc9vZ4iwfvWZi/panel")
XUI_USERNAME = os.getenv("XUI_USERNAME")
XUI_PASSWORD = os.getenv("XUI_PASSWORD")
XUI_INBOUND_ID = int(os.getenv("XUI_INBOUND_ID", 2))

# Subscription Configuration
SUB_PORT = int(os.getenv("SUB_PORT", 2096))
SUB_EXTERNAL_HOST = os.getenv("SUB_EXTERNAL_HOST")

# News Channel Configuration
NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID", "@spn_newsvpn")
NEWS_CHANNEL_URL = os.getenv("NEWS_CHANNEL_URL", "https://t.me/spn_newsvpn")

# User Agreement
TELEGRAPH_AGREEMENT_URL = os.getenv("TELEGRAPH_AGREEMENT_URL", "https://telegra.ph/example")

# Subscription Prices (months → price in RUB)
PRICES = {
    1: 100,
    3: 249,
    6: 449,
    12: 990
}

# Referral Bonus Configuration
REFERRAL_BONUS_DAYS = 7

# Gift Configuration
GIFT_DAYS = 3
