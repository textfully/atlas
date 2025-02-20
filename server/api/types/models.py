from pydantic import BaseModel
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
    created_at: datetime
    updated_at: datetime


class ApiKeyModel(BaseModel):
    id: str
    user_id: str
    name: str
    short_key: str
    key_hash: str
    permission: ApiKeyPermission
    is_active: bool
    last_used: datetime
    created_at: datetime


class ContactModel(BaseModel):
    id: str
    phone_number: str
    created_at: datetime
    updated_at: datetime


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
    delivered_at: datetime
    read_at: datetime
    created_at: datetime
    sms_fallback: bool


class OrganizationContactModel(BaseModel):
    id: str
    organization_id: str
    contact_id: str
    first_name: str
    last_name: str
    is_subscribed: bool
    notes: str
    created_at: datetime
    updated_at: datetime


class OrganizationInviteModel(BaseModel):
    id: str
    organization_id: str
    email: str
    role: OrganizationRole
    invited_by: str
    token: str
    expires_at: datetime
    created_at: datetime


class OrganizationMemberModel(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: OrganizationRole
    created_at: datetime
    updated_at: datetime


class OrganizationModel(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
