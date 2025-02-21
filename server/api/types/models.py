from typing import Optional
from pydantic import BaseModel, field_serializer
from datetime import datetime
from api.types.enums import (
    ApiKeyPermission,
    MessageService,
    MessageStatus,
    OrganizationRole,
    SubscriptionTier,
)


class UserModel(BaseModel):
    id: str
    auth_id: str
    subscription_tier: SubscriptionTier
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()


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


class ContactModel(BaseModel):
    id: str
    phone_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
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


class OrganizationContactModel(BaseModel):
    id: str
    organization_id: str
    contact_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_subscribed: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()


class OrganizationInviteModel(BaseModel):
    id: str
    organization_id: str
    email: str
    role: OrganizationRole
    invited_by: str
    token: str
    expires_at: datetime
    created_at: Optional[datetime] = None

    @field_serializer("expires_at", "created_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()


class OrganizationMemberModel(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: OrganizationRole
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()


class OrganizationModel(BaseModel):
    id: str
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.isoformat()
