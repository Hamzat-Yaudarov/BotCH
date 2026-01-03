import requests
import json
import logging
from datetime import datetime
from config import XUI_PANEL_URL, XUI_PANEL_PATH, XUI_USERNAME, XUI_PASSWORD, INBOUND_ID, SUB_PORT, SUB_EXTERNAL_HOST

logger = logging.getLogger(__name__)

# Отключить предупреждения SSL
requests.packages.urllib3.disable_warnings()


class XUIClient:
    """Клиент для управления XUI панелью"""

    def __init__(self):
        self.session = None

    def get_session(self) -> requests.Session:
        """Получить авторизованную сессию XUI"""
        session = requests.Session()
        login_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH.replace('/panel', '')}/login/"
        payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}

        try:
            response = session.post(login_url, json=payload, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"XUI login failed: {resp_json}")

            logger.info("✅ Авторизация в XUI успешна")
            return session
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации XUI: {str(e)}")
            raise Exception(f"Ошибка подключения к панели: {str(e)}")

    def get_client_expiry(self, email: str) -> int:
        """Получить время истечения клиента"""
        session = self.get_session()
        get_traffic_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/getClientTraffics/{email}"

        try:
            response = session.get(get_traffic_url, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"Get client traffic failed: {resp_json}")

            return resp_json['obj']['expiryTime']
        except Exception as e:
            logger.error(f"❌ Ошибка получения времени клиента: {str(e)}")
            raise Exception(f"Ошибка получения времени клиента: {str(e)}")

    def create_or_update_client(
        self,
        client_uuid: str,
        client_email: str,
        client_sub_id: str,
        expiry_time_ms: int,
        user_id: int
    ) -> None:
        """Создать или обновить клиента в XUI панели"""
        session = self.get_session()

        settings = {
            "clients": [{
                "id": client_uuid,
                "flow": "",
                "email": client_email,
                "limitIp": 0,
                "totalGB": 0,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": str(user_id),
                "subId": client_sub_id,
                "reset": 0
            }]
        }

        # Проверяем есть ли клиент
        try:
            existing_expiry = self.get_client_expiry(client_email)
            # Если есть - обновляем
            update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/updateClient/{client_uuid}"
        except:
            # Если нет - создаём
            update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/addClient"

        payload = {
            "id": str(INBOUND_ID),
            "settings": json.dumps(settings)
        }

        try:
            response = session.post(update_url, data=payload, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"Operation failed: {resp_json}")

            logger.info(f"✅ Клиент {client_email} создан/обновлён")
        except Exception as e:
            logger.error(f"❌ Ошибка операции с клиентом: {str(e)}")
            raise Exception(f"Ошибка операции с клиентом: {str(e)}")

    def get_subscription_url(self, sub_id: str) -> str:
        """Получить URL подписки"""
        return f"http://{SUB_EXTERNAL_HOST}:{SUB_PORT}/sub/{sub_id}"


# Глобальный объект клиента XUI
xui = XUIClient()
