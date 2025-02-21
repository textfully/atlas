from pydantic import BaseModel, Field
from typing import Optional, List
from .enums import MessageService, ApiKeyPermission


class MessageRequest(BaseModel):
    to: str = Field(..., description="Recipient's phone number or email")
    text: str = Field(..., description="Message content")
    service: MessageService = Field(
        default=MessageService.IMESSAGE, description="Message service type"
    )


class APIKeyRequest(BaseModel):
    name: str = Field(..., description="Name for the API key")
    permission: Optional[ApiKeyPermission] = Field(
        default=ApiKeyPermission.ALL, description="API key permission level"
    )


class OrganizationRequest(BaseModel):
    name: str = Field(..., description="Name for the organization")
