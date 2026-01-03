from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserClient(BaseModel):
    """Модель VPN клиента пользователя"""
    user_id: int
    uuid: str
    sub_id: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expiry_time: int = 0  # Timestamp в миллисекундах

    class Config:
        from_attributes = True


class PromoCode(BaseModel):
    """Модель промокода"""
    code: str
    days: int
    activations_left: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Referral(BaseModel):
    """Модель реферального запроса"""
    referrer_id: int
    referred_user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class PaidUser(BaseModel):
    """Модель пользователя, который оплатил"""
    user_id: int
    amount: int  # Сумма в RUB
    paid_at: datetime = Field(default_factory=datetime.utcnow)
    invoice_id: str

    class Config:
        from_attributes = True


class UserGift(BaseModel):
    """Модель подарка за подписку на канал"""
    user_id: int
    received_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
