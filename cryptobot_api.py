import requests
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL


async def create_cryptobot_invoice(amount_rub: int, order_id: str, bot_username: str) -> tuple:
    """Create invoice in CryptoBot and return (pay_url, invoice_id)"""
    url = f"{CRYPTOBOT_API_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": str(amount_rub),
        "description": f"Подписка SPN {order_id}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/{bot_username}"
    }
    response = requests.post(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        raise Exception(f"CryptoBot error {response.status_code}: {response.text}")
    data = response.json()
    if not data.get("ok"):
        raise Exception(f"CryptoBot error: {data}")
    return data['result']['pay_url'], data['result']['invoice_id']


async def check_cryptobot_payment(invoice_id: str) -> bool:
    """Check if CryptoBot invoice is paid"""
    url = f"{CRYPTOBOT_API_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        return False
    data = response.json()
    if not data.get("ok"):
        return False
    invoices = data['result']['items']
    if invoices and invoices[0]['status'] == 'paid':
        return True
    return False
