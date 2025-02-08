from pydantic import BaseModel
from datetime import datetime
from .enums import MessageService, MessageStatus


class HealthResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    id: str
    recipient: str
    text: str
    service: MessageService
    status: MessageStatus
    sent_at: datetime
    sms_fallback: bool


class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class ContactResponse(BaseModel):
    id: str
    phone_number: str
    created_at: datetime
    updated_at: datetime


class CreateAPIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class APIKeyResponse(BaseModel):
    id: str
    name: str
    short_key: str
    permission: str
    is_active: bool
    last_used: datetime
    created_at: datetime

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class IdentityResponse(BaseModel):
    hash: str
