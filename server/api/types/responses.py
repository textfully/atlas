from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from api.types.enums import MessageService, MessageStatus, OrganizationRole


class HealthResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    id: str
    recipient: str
    text: str
    service: MessageService
    status: MessageStatus
    sent_at: Optional[datetime] = None
    sms_fallback: bool

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class OrganizationResponse(BaseModel):
    id: str
    name: str
    role: OrganizationRole
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ContactResponse(BaseModel):
    id: str
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_subscribed: bool
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class CreateAPIKeyResponse(BaseModel):
    api_key: str
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class APIKeyResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    short_key: str
    permission: str
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class IdentityResponse(BaseModel):
    hash: str
