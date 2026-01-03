import requests
import logging
from config import CRYPTOBOT_TOKEN

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Обработчик платежей через CryptoBot"""

    def __init__(self):
        self.api_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}

    async def create_invoice(self, amount_rub: int, order_id: str, bot_username: str) -> tuple[str, str]:
        """
        Создать счёт в CryptoBot

        Args:
            amount_rub: Сумма в рублях
            order_id: ID заказа
            bot_username: Имя бота в Telegram

        Returns:
            Кортеж (pay_url, invoice_id)
        """
        url = f"{self.api_url}/createInvoice"
        params = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": str(amount_rub),
            "description": f"Подписка SPN {order_id}",
            "paid_btn_name": "callback",
            "paid_btn_url": f"https://t.me/{bot_username}"
        }

        try:
            response = requests.post(url, headers=self.headers, params=params, timeout=30)

            if response.status_code != 200:
                raise Exception(f"CryptoBot error {response.status_code}: {response.text}")

            data = response.json()

            if not data.get("ok"):
                raise Exception(f"CryptoBot error: {data}")

            pay_url = data['result']['pay_url']
            invoice_id = data['result']['invoice_id']

            logger.info(f"✅ Счёт создан: {invoice_id}")
            return pay_url, invoice_id

        except Exception as e:
            logger.error(f"❌ Ошибка создания счёта: {str(e)}")
            raise

    async def check_payment(self, invoice_id: str) -> bool:
        """
        Проверить статус платежа

        Args:
            invoice_id: ID счёта

        Returns:
            True если оплачено, False если нет
        """
        url = f"{self.api_url}/getInvoices"
        params = {"invoice_ids": invoice_id}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"❌ Ошибка при проверке платежа: {response.status_code}")
                return False

            data = response.json()

            if not data.get("ok"):
                logger.error(f"❌ Ошибка API CryptoBot: {data}")
                return False

            invoices = data['result']['items']

            if invoices and invoices[0]['status'] == 'paid':
                logger.info(f"✅ Платёж подтверждён: {invoice_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки платежа: {str(e)}")
            return False


# Глобальный объект обработчика платежей
payment = PaymentProcessor()
