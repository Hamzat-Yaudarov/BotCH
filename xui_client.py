import requests
import json
import logging
from typing import List, Dict
from config import XUI_SERVERS

logger = logging.getLogger(__name__)

# Отключить предупреждения SSL
requests.packages.urllib3.disable_warnings()


class XUIServerClient:
    """Клиент для управления одной XUI панелью"""

    def __init__(self, server_config: Dict):
        self.config = server_config
        self.name = server_config["name"]
        self.url = server_config["url"]
        self.path = server_config["path"]
        self.username = server_config["username"]
        self.password = server_config["password"]
        self.inbound_id = server_config["inbound_id"]
        self.sub_port = server_config["sub_port"]
        self.sub_host = server_config["sub_host"]

    def get_session(self) -> requests.Session:
        """Получить авторизованную сессию XUI"""
        session = requests.Session()
        login_url = f"{self.url}{self.path.replace('/panel', '')}/login/"
        payload = {"username": self.username, "password": self.password}

        try:
            response = session.post(login_url, json=payload, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"XUI login failed: {resp_json}")

            logger.info(f"✅ Авторизация в XUI успешна ({self.name})")
            return session
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации XUI ({self.name}): {str(e)}")
            raise Exception(f"Ошибка подключения к панели {self.name}: {str(e)}")

    def get_client_expiry(self, email: str) -> int:
        """Получить время истечения клиента"""
        session = self.get_session()
        get_traffic_url = f"{self.url}{self.path}/api/inbounds/getClientTraffics/{email}"

        try:
            response = session.get(get_traffic_url, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"Get client traffic failed: {resp_json}")

            return resp_json['obj']['expiryTime']
        except Exception as e:
            logger.error(f"❌ Ошибка получения времени клиента ({self.name}): {str(e)}")
            raise Exception(f"Ошибка получения времени клиента ({self.name}): {str(e)}")

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
            update_url = f"{self.url}{self.path}/api/inbounds/updateClient/{client_uuid}"
        except:
            # Если нет - создаём
            update_url = f"{self.url}{self.path}/api/inbounds/addClient"

        payload = {
            "id": str(self.inbound_id),
            "settings": json.dumps(settings)
        }

        try:
            response = session.post(update_url, data=payload, timeout=30, verify=False)
            response.raise_for_status()
            resp_json = response.json()

            if not resp_json.get("success"):
                raise Exception(f"Operation failed: {resp_json}")

            logger.info(f"✅ Клиент {client_email} создан/обновлён на {self.name}")
        except Exception as e:
            logger.error(f"❌ Ошибка операции с клиентом ({self.name}): {str(e)}")
            raise Exception(f"Ошибка операции с клиентом ({self.name}): {str(e)}")

    def get_subscription_url(self, sub_id: str) -> str:
        """Получить URL подписки"""
        return f"http://{self.sub_host}:{self.sub_port}/sub/{sub_id}"


class XUIMultiServerClient:
    """Клиент для управления несколькими XUI панелями"""

    def __init__(self):
        self.servers = [XUIServerClient(config) for config in XUI_SERVERS]
        logger.info(f"✅ Инициализировано {len(self.servers)} XUI серверов")

    def create_or_update_client_on_all_servers(
        self,
        client_uuid: str,
        client_email: str,
        client_sub_id: str,
        expiry_time_ms: int,
        user_id: int
    ) -> None:
        """Создать или обновить клиента на ВСЕ сервера"""
        logger.info(f"📋 Создание клиента на {len(self.servers)} серверах для user {user_id}")
        
        for server in self.servers:
            try:
                server.create_or_update_client(
                    client_uuid, client_email, client_sub_id, expiry_time_ms, user_id
                )
            except Exception as e:
                logger.error(f"❌ Не удалось создать клиента на {server.name}: {e}")
                raise Exception(f"Ошибка на сервере {server.name}: {str(e)}")

    def get_subscription_urls(self, sub_id: str) -> List[str]:
        """Получить URL подписок со всех серверов"""
        return [server.get_subscription_url(sub_id) for server in self.servers]

    def get_client_expiry_from_first_server(self, email: str) -> int:
        """Получить время истечения клиента с первого сервера (они одинаковые на всех)"""
        return self.servers[0].get_client_expiry(email)


# Глобальный объект клиента XUI (множественный)
xui = XUIMultiServerClient()
