import json
import requests
from datetime import datetime
from config import (
    XUI_PANEL_URL,
    XUI_PANEL_PATH,
    XUI_USERNAME,
    XUI_PASSWORD,
    XUI_INBOUND_ID,
)


def get_xui_session():
    """Authenticate with XUI panel and return authenticated session"""
    session = requests.Session()
    login_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH.replace('/panel', '')}/login/"
    payload = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        response = session.post(login_url, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"XUI login failed: {resp_json}")
    except Exception as e:
        raise Exception(f"Ошибка подключения к панели: {str(e)}")
    return session


def get_client_expiry(email: str) -> int:
    """Get client's subscription expiry time from XUI panel"""
    session = get_xui_session()
    get_traffic_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/getClientTraffics/{email}"
    try:
        response = session.get(get_traffic_url, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"Get client traffic failed: {resp_json}")
        return resp_json['obj']['expiryTime']
    except Exception as e:
        raise Exception(f"Ошибка получения времени клиента: {str(e)}")


def create_client(client_uuid: str, client_sub_id: str, client_email: str, expiry_time: int, user_id: int):
    """Create or update client on XUI panel"""
    session = get_xui_session()
    
    update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/addClient"
    
    settings = {
        "clients": [{
            "id": client_uuid,
            "flow": "",
            "email": client_email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": expiry_time,
            "enable": True,
            "tgId": str(user_id),
            "subId": client_sub_id,
            "reset": 0
        }]
    }
    
    payload = {
        "id": str(XUI_INBOUND_ID),
        "settings": json.dumps(settings)
    }
    
    try:
        response = session.post(update_url, data=payload, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"Operation failed: {resp_json}")
    except Exception as e:
        raise Exception(f"Ошибка операции с клиентом: {str(e)}")


def update_client(client_uuid: str, client_sub_id: str, client_email: str, new_expiry: int, user_id: int):
    """Update existing client on XUI panel"""
    session = get_xui_session()
    
    update_url = f"{XUI_PANEL_URL}{XUI_PANEL_PATH}/api/inbounds/updateClient/{client_uuid}"
    
    settings = {
        "clients": [{
            "id": client_uuid,
            "flow": "",
            "email": client_email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": new_expiry,
            "enable": True,
            "tgId": str(user_id),
            "subId": client_sub_id,
            "reset": 0
        }]
    }
    
    payload = {
        "id": str(XUI_INBOUND_ID),
        "settings": json.dumps(settings)
    }
    
    try:
        response = session.post(update_url, data=payload, timeout=30, verify=False)
        response.raise_for_status()
        resp_json = response.json()
        if not resp_json.get("success"):
            raise Exception(f"Operation failed: {resp_json}")
    except Exception as e:
        raise Exception(f"Ошибка операции с клиентом: {str(e)}")
