from typing import Optional
from pydantic import BaseModel, field_serializer
from datetime import datetime
from api.types.enums import (
    ApiKeyPermission,
    MessageService,
    MessageStatus,
)


class ApiKeyModel(BaseModel):
    id: str
    organization_id: str
    user_id: str
    name: str
    short_key: str
    key_hash: str
    permission: ApiKeyPermission
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_serializer("last_used", "created_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()


class MessageModel(BaseModel):
    id: str
    user_id: str
    organization_id: str
    message_id: str
    recipient: str
    text: str
    service: MessageService
    status: MessageStatus
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    sms_fallback: bool

    @field_serializer("sent_at", "delivered_at", "read_at", "created_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()
