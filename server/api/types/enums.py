from enum import Enum


class MessageService(str, Enum):
    SMS = "sms"
    IMESSAGE = "imessage"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ApiKeyPermission(str, Enum):
    ALL = "all"
    SEND_ONLY = "send_only"


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    GROWTH = "growth"


class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"
