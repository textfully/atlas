from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Tuple
import phonenumbers
from datetime import datetime, timezone
from config.settings import FEATUREBASE_IDENTITY_VERIFICATION_SECRET
from api.types.models import MessageModel
from utils.rate_limiter import check_rate_limit, RateLimiter, get_user_tier
from utils.logger import logger
from utils.supabase_client import SupabaseClient
from services import atlas
from api.auth import AuthService, verify_auth_token, verify_api_key, verify_bearer_token
from api.types.enums import MessageService, MessageStatus
from api.types.requests import MessageRequest, APIKeyRequest
from api.types.responses import (
    APIKeyResponse,
    ContactResponse,
    HealthResponse,
    IdentityResponse,
    MessageResponse,
    CreateAPIKeyResponse,
    OrganizationResponse,
)
import hmac
import hashlib

app = FastAPI(
    title="Textfully API",
    description="iMessage & SMS API for Developers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://textfully.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/messages", response_model=MessageResponse)
async def send_message(
    message: MessageRequest,
    response: Response,
    rate_limit_info: Tuple[str, str, Optional[Dict[str, str]]] = Depends(
        check_rate_limit
    ),
):
    """
    Send a message

    Rate limits:
    - All tiers: 1 message per second
    - Free tier: Also limited to 100 messages per day
    """
    user_id, organization_id, rate_limit_headers = rate_limit_info

    if rate_limit_headers:
        for header, value in rate_limit_headers.items():
            response.headers[header] = value

    try:
        parsed_number = phonenumbers.parse(message.to)
        if not phonenumbers.is_valid_number(parsed_number):
            raise HTTPException(status_code=400, detail="Invalid phone number")

        if message.text.strip() == "":
            raise HTTPException(status_code=400, detail="Message text cannot be empty")

        is_imessage_available = atlas.check_imessage_availability(message.to)

        message_service = (
            MessageService.IMESSAGE
            if message.service == MessageService.IMESSAGE and is_imessage_available
            else MessageService.SMS
        )
        service_prefix = (
            "iMessage" if message_service == MessageService.IMESSAGE else "SMS"
        )
        chat_guid = atlas.get_chat(f"{service_prefix};-;{message.to}")

        if chat_guid:
            message_guid = atlas.send_text(
                chat_guid=chat_guid, message=message.text, method="private-api"
            )
        else:
            message_guid = atlas.create_chat(recipient=message.to, message=message.text)

        if not message_guid:
            raise HTTPException(status_code=500, detail="Failed to send message")

        is_sms_fallback = (
            message.service == MessageService.IMESSAGE and not is_imessage_available
        )

        # Store message in database
        message_data = MessageModel(
            organization_id=organization_id,
            user_id=user_id,
            message_id=message_guid,
            recipient=message.to,
            text=message.text,
            service=message_service,
            status=MessageStatus.SENT,
            sent_at=datetime.now(timezone.utc).isoformat(),
            sms_fallback=is_sms_fallback,
        ).dict(exclude={"id"})

        data, error = await SupabaseClient.store_message(message_data)
        if error:
            logger.error(f"Failed to store message: {error}")
            raise HTTPException(status_code=500, detail="Failed to store message")

        message_id = data[0]["id"]
        return MessageResponse(
            id=message_id,
            recipient=message.to,
            text=message.text,
            service=message.service,
            status=MessageStatus.SENT,
            sent_at=datetime.now(timezone.utc),
            sms_fallback=is_sms_fallback,
        )

    except phonenumbers.NumberParseException:
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/messages/limits")
async def get_message_limits(user_info: Tuple[str, str] = Depends(verify_bearer_token)):
    """Get current rate limit status"""
    user_id, _ = user_info
    tier = await get_user_tier(user_id)
    return await RateLimiter.get_current_limits(user_id, tier)


@app.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str, user_info: Tuple[str, str] = Depends(verify_api_key)
):
    """Get a message details"""
    user_id, organization_id = user_info

    try:
        # Check message ownership and get message
        data, error = await SupabaseClient.execute_query(
            lambda client: client.table("messages")
            .select("*")
            .eq("id", message_id)
            .eq("user_id", user_id)
            .eq("organization_id", organization_id)
            .single()
            .execute()
        )

        if error or not data:
            raise HTTPException(status_code=404, detail="Message not found")

        return MessageResponse(
            id=message_id,
            recipient=data["recipient"],
            text=data["text"],
            service=MessageService(data["service"]),
            status=MessageStatus(data["status"]),
            sent_at=datetime.fromisoformat(data["sent_at"]),
            sms_fallback=data["sms_fallback"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get message")


@app.get("/messages", response_model=List[MessageResponse])
async def fetch_messages(
    user_info: Tuple[str, str] = Depends(verify_bearer_token),
    limit: int = 50,
    offset: int = 0,
):
    """Fetch user's messages"""
    user_id, organization_id = user_info

    try:
        data, error = await SupabaseClient.execute_query(
            lambda client: client.table("messages")
            .select("*")
            .eq("user_id", user_id)
            .eq("organization_id", organization_id)
            .order("sent_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch messages")

        return [
            MessageResponse(
                id=msg["id"],
                recipient=msg["recipient"],
                text=msg["text"],
                service=MessageService(msg["service"]),
                status=MessageStatus(msg["status"]),
                sent_at=datetime.fromisoformat(msg["sent_at"]),
                sms_fallback=msg["sms_fallback"],
            )
            for msg in data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@app.get("/organizations", response_model=List[OrganizationResponse])
async def fetch_organizations(
    user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Fetch user's organizations"""
    user_id, _ = user_info

    try:
        memberships_data, memberships_error = await SupabaseClient.execute_query(
            lambda client: client.table("organization_members")
            .select("organization_id, role")
            .eq("user_id", user_id)
            .execute()
        )

        if memberships_error:
            raise HTTPException(status_code=500, detail="Failed to fetch organizations")

        organization_ids = [mem["organization_id"] for mem in memberships_data]
        role_lookup = {mem["organization_id"]: mem["role"] for mem in memberships_data}

        organizations_data, organizations_error = await SupabaseClient.execute_query(
            lambda client: client.table("organizations")
            .select("*")
            .in_("id", organization_ids)
            .execute()
        )

        if organizations_error:
            raise HTTPException(status_code=500, detail="Failed to fetch organizations")

        return [
            OrganizationResponse(
                id=org["id"],
                name=org["name"],
                role=role_lookup[org["id"]],
                created_at=datetime.fromisoformat(org["created_at"]),
                updated_at=datetime.fromisoformat(org["updated_at"]),
            )
            for org in organizations_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch organizations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch organizations")


@app.get("/contacts", response_model=List[ContactResponse])
async def fetch_contacts(user_info: Tuple[str, str] = Depends(verify_bearer_token)):
    """Fetch organization's contacts"""
    _, organization_id = user_info

    try:
        org_contacts_data, org_contacts_error = await SupabaseClient.execute_query(
            lambda client: client.table("organization_contacts")
            .select("*")
            .eq("organization_id", organization_id)
            .execute()
        )

        if org_contacts_error:
            raise HTTPException(status_code=500, detail="Failed to fetch contacts")

        contact_ids = [oc["contact_id"] for oc in org_contacts_data]

        contacts_data, contacts_error = await SupabaseClient.execute_query(
            lambda client: client.table("contacts")
            .select("phone_number")
            .in_("id", contact_ids)
            .execute()
        )

        if contacts_error:
            raise HTTPException(status_code=500, detail="Failed to fetch contacts")

        phone_number_lookup = {c["id"]: c["phone_number"] for c in contacts_data}

        return [
            ContactResponse(
                id=org_contact["contact_id"],
                phone_number=phone_number_lookup[org_contact["contact_id"]],
                first_name=org_contact["first_name"],
                last_name=org_contact["last_name"],
                is_subscribed=org_contact["is_subscribed"],
                note=org_contact["note"],
                created_at=datetime.fromisoformat(org_contact["created_at"]),
                updated_at=datetime.fromisoformat(org_contact["updated_at"]),
            )
            for org_contact in org_contacts_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch contacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")


@app.post("/api-keys", response_model=CreateAPIKeyResponse)
async def generate_api_key(
    request: APIKeyRequest, user_id: str = Depends(verify_auth_token)
):
    """Generate a new API key"""
    try:
        api_key, created_at = await AuthService.create_api_key(
            user_id, name=request.name, permission=request.permission
        )
        return CreateAPIKeyResponse(api_key=api_key, created_at=created_at)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate API key")


@app.get("/api-keys", response_model=List[APIKeyResponse])
async def fetch_api_keys(user_id: str = Depends(verify_auth_token)):
    """Fetch user's API keys"""
    try:
        data, error = await SupabaseClient.execute_query(
            lambda client: client.table("api_keys")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch API keys")

        return [
            APIKeyResponse(
                id=key["id"],
                name=key["name"],
                permission=key["permission"],
                short_key=key["short_key"],
                is_active=key["is_active"],
                last_used=datetime.fromisoformat(key["last_used"]),
                created_at=datetime.fromisoformat(key["created_at"]),
            )
            for key in data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch API keys")


@app.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: str, user_id: str = Depends(verify_auth_token)):
    """Revoke an API key"""
    try:
        # Check API key ownership
        data, error = await SupabaseClient.execute_query(
            lambda client: client.table("api_keys")
            .select("id")
            .eq("id", key_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if error or not data:
            raise HTTPException(status_code=404, detail="API key not found")

        # Revoke key
        _, error = await SupabaseClient.execute_query(
            lambda client: client.table("api_keys")
            .update({"is_active": False})
            .eq("id", key_id)
            .execute()
        )

        if error:
            raise HTTPException(status_code=500, detail="Failed to revoke API key")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Supabase connection
        _, error = await SupabaseClient.execute_query(
            lambda client: client.rpc("health_check").execute()
        )

        if error:
            raise HTTPException(status_code=503, detail="Database connection failed")

        return HealthResponse(status="healthy")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/identity", response_model=IdentityResponse)
async def get_identity_hash(user_id: str = Depends(verify_auth_token)):
    """
    Get identity verification hash for the authenticated user

    Returns a hash that can be used to verify user identity with third-party services
    """
    try:
        user_hash = hmac.new(
            FEATUREBASE_IDENTITY_VERIFICATION_SECRET.encode(),
            user_id.encode(),
            hashlib.sha256,
        ).hexdigest()

        return IdentityResponse(hash=user_hash)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate identity hash: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate identity hash")
