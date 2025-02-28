from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Tuple
import phonenumbers
from datetime import datetime, timezone
from constants.templates import organization_invite_template
from utils.email_client import send_email
from config.settings import FEATUREBASE_IDENTITY_VERIFICATION_SECRET
from api.types.models import MessageModel
from utils.rate_limiter import check_rate_limit, RateLimiter, get_organization_tier
from utils.logger import logger
from utils.supabase_client import SupabaseClient
from services import atlas
from api.auth import (
    AuthService,
    verify_api_key,
    verify_bearer_token,
    verify_bearer_token_skip_org_check,
)
from api.types.enums import MessageService, MessageStatus, OrganizationRole
from api.types.requests import (
    MessageRequest,
    APIKeyRequest,
    OrganizationRequest,
    InviteMemberRequest,
)
from api.types.responses import (
    APIKeyResponse,
    ContactResponse,
    HealthResponse,
    IdentityResponse,
    MessageResponse,
    CreateAPIKeyResponse,
    OrganizationResponse,
    OrganizationMemberResponse,
    InviteMemberResponse,
    UserResponse,
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


@app.get("/users/{user_id}", response_model=UserResponse)
async def fetch_user(
    user_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Fetch a single user by ID"""
    u_id, _ = user_info

    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if user_id != u_id:
            raise HTTPException(status_code=403, detail="Invalid user ID")

        data, error = await SupabaseClient.fetch_user_data(user_id)

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch user")

        if not data:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=data["id"],
            full_name=data["full_name"],
            email=data["email"],
            avatar_url=data["avatar_url"],
            phone=data["phone"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user")


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Delete a user"""
    u_id, _ = user_info

    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if user_id != u_id:
            raise HTTPException(status_code=403, detail="Invalid user ID")

        success = await SupabaseClient.delete_user(user_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete user")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@app.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    response: Response,
    rate_limit_info: Tuple[str, str, Dict[str, str]] = Depends(check_rate_limit),
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
        parsed_number = phonenumbers.parse(request.to)
        if not phonenumbers.is_valid_number(parsed_number):
            raise HTTPException(status_code=400, detail="Invalid phone number")

        if request.text.strip() == "":
            raise HTTPException(status_code=400, detail="Message text cannot be empty")

        is_imessage_available = atlas.check_imessage_availability(request.to)

        message_service = (
            MessageService.IMESSAGE
            if request.service == MessageService.IMESSAGE and is_imessage_available
            else MessageService.SMS
        )
        service_prefix = (
            "iMessage" if message_service == MessageService.IMESSAGE else "SMS"
        )
        chat_guid = atlas.get_chat(f"{service_prefix};-;{request.to}")

        if chat_guid:
            message_guid = atlas.send_text(
                chat_guid=chat_guid, message=request.text, method="private-api"
            )
        else:
            message_guid = atlas.create_chat(recipient=request.to, message=request.text)

        if not message_guid:
            raise HTTPException(status_code=500, detail="Failed to send message")

        is_sms_fallback = (
            request.service == MessageService.IMESSAGE and not is_imessage_available
        )

        # Store message in database
        message_data = MessageModel(
            id="",
            organization_id=organization_id,
            user_id=user_id,
            message_id=message_guid,
            recipient=request.to,
            text=request.text,
            service=message_service,
            status=MessageStatus.SENT,
            sent_at=datetime.now(timezone.utc),
            sms_fallback=is_sms_fallback,
        ).model_dump(exclude={"id"}, exclude_unset=True)

        data, error = await SupabaseClient.create_message(message_data)
        if error:
            logger.error(f"Failed to store message: {error}")
            raise HTTPException(status_code=500, detail="Failed to store message")

        await RateLimiter.increment_daily_count(organization_id)

        message_id = data[0]["id"]
        return MessageResponse(
            id=message_id,
            recipient=request.to,
            text=request.text,
            service=request.service,
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
    _, org_id = user_info
    tier = await get_organization_tier(org_id)
    return await RateLimiter.get_current_limits(org_id, tier)


@app.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Get a message details"""
    user_id, org_id = user_info

    try:
        if not message_id:
            raise HTTPException(status_code=400, detail="Message ID is required")

        data, error = await SupabaseClient.fetch_message(message_id, user_id, org_id)

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch message")

        if not data:
            raise HTTPException(status_code=404, detail="Message not found")

        return MessageResponse(
            id=message_id,
            recipient=data["recipient"],
            text=data["text"],
            service=MessageService(data["service"]),
            status=MessageStatus(data["status"]),
            sent_at=data["sent_at"],
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
    """Fetch organization's messages"""
    _, org_id = user_info

    try:
        data, error = await SupabaseClient.fetch_organization_messages(
            org_id, limit, offset
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
                sent_at=msg["sent_at"],
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
    user_info: Tuple[str, Optional[str]] = Depends(verify_bearer_token_skip_org_check)
):
    """Fetch user's organizations"""
    user_id, _ = user_info

    try:
        memberships_data, memberships_error = (
            await SupabaseClient.fetch_organization_memberships(user_id)
        )

        if memberships_error or not memberships_data:
            raise HTTPException(
                status_code=500, detail="Failed to fetch organization memberships"
            )

        organization_ids = [mem["organization_id"] for mem in memberships_data]
        role_lookup = {mem["organization_id"]: mem["role"] for mem in memberships_data}

        organizations_data, organizations_error = (
            await SupabaseClient.fetch_organizations(organization_ids)
        )

        if organizations_error:
            raise HTTPException(status_code=500, detail="Failed to fetch organizations")

        return [
            OrganizationResponse(
                id=org["id"],
                name=org["name"],
                role=role_lookup[org["id"]],
                created_at=org["created_at"],
                updated_at=org["updated_at"],
            )
            for org in organizations_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch organizations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch organizations")


@app.post("/organizations", response_model=OrganizationResponse)
async def create_organization(
    request: OrganizationRequest,
    user_info: Tuple[str, Optional[str]] = Depends(verify_bearer_token_skip_org_check),
):
    """Create a new organization"""
    user_id, _ = user_info

    try:
        if not request.name:
            raise HTTPException(status_code=400, detail="Organization name is required")

        organization_id, error = await SupabaseClient.create_organization(
            name=request.name, user_id=user_id
        )

        if error:
            raise HTTPException(status_code=500, detail="Failed to create organization")

        org_data, org_error = await SupabaseClient.fetch_organization(organization_id)

        if org_error or not org_data:
            raise HTTPException(status_code=500, detail="Failed to fetch organization")

        return OrganizationResponse(
            id=org_data["id"],
            name=org_data["name"],
            role=OrganizationRole.OWNER,
            created_at=org_data["created_at"],
            updated_at=org_data["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create organization")


@app.get("/organizations/{organization_id}", response_model=OrganizationResponse)
async def fetch_organization(
    organization_id: str,
    user_info: Tuple[str, Optional[str]] = Depends(verify_bearer_token),
):
    """Fetch a single organization by ID"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        data, error = await SupabaseClient.fetch_organization(organization_id)

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch organization")

        if not data:
            raise HTTPException(status_code=404, detail="Organization not found")

        member_role, member_role_error = await SupabaseClient.fetch_member_role(
            organization_id, user_id
        )

        if member_role_error:
            raise HTTPException(status_code=500, detail="Failed to fetch member role")

        return OrganizationResponse(
            id=data["id"],
            name=data["name"],
            role=OrganizationRole(member_role["role"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch organization")


@app.delete("/organizations/{organization_id}", status_code=204)
async def delete_organization(
    organization_id: str,
    user_info: Tuple[str, Optional[str]] = Depends(verify_bearer_token),
):
    """Delete an organization"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        ownership_data, ownership_error = (
            await SupabaseClient.verify_organization_ownership(organization_id, user_id)
        )

        if ownership_error:
            raise HTTPException(
                status_code=500, detail="Failed to verify organization ownership"
            )

        if not ownership_data:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners can delete the organization",
            )

        _, error = await SupabaseClient.delete_organization(organization_id)

        if error:
            raise HTTPException(status_code=500, detail="Failed to delete organization")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete organization")


@app.patch("/organizations/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    request: OrganizationRequest,
    user_info: Tuple[str, Optional[str]] = Depends(verify_bearer_token),
):
    """Update an organization's name"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        if not request.name:
            raise HTTPException(status_code=400, detail="Organization name is required")

        admin_data, admin_error = await SupabaseClient.verify_organization_admin(
            organization_id, user_id
        )

        if admin_error:
            raise HTTPException(
                status_code=500, detail="Failed to verify organization permissions"
            )

        if not admin_data:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners and administrators can update the organization name",
            )

        data, error = await SupabaseClient.update_organization(
            organization_id, request.name
        )

        if error:
            raise HTTPException(status_code=500, detail="Failed to update organization")

        if not data or len(data) == 0:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_data = data[0]
        return OrganizationResponse(
            id=org_data["id"],
            name=org_data["name"],
            role=admin_data["role"],
            created_at=org_data["created_at"],
            updated_at=org_data["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update organization")


@app.get(
    "/organizations/{organization_id}/members",
    response_model=List[OrganizationMemberResponse],
)
async def fetch_organization_members(
    organization_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Fetch all members of an organization"""
    _, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        members_data, error = await SupabaseClient.fetch_organization_members(
            organization_id
        )

        if error:
            raise HTTPException(
                status_code=500, detail="Failed to fetch organization members"
            )

        if not members_data:
            return []

        return [
            OrganizationMemberResponse(
                id=member["id"],
                organization_id=member["organization_id"],
                user_id=member["user_id"],
                role=member["role"],
                created_at=member["created_at"],
                updated_at=member["updated_at"],
                full_name=member["full_name"],
                email=member["email"],
                avatar_url=member["avatar_url"],
            )
            for member in members_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch organization members: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch organization members"
        )


@app.delete("/organizations/{organization_id}/members/{member_id}", status_code=204)
async def remove_organization_member(
    organization_id: str,
    member_id: str,
    user_info: Tuple[str, str] = Depends(verify_bearer_token),
):
    """Remove a member from an organization"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if not member_id:
            raise HTTPException(status_code=400, detail="Member ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        admin_data, admin_error = await SupabaseClient.verify_organization_admin(
            organization_id, user_id
        )

        if admin_error:
            raise HTTPException(
                status_code=500, detail="Failed to verify organization permissions"
            )

        if not admin_data:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners and administrators can remove users",
            )

        _, error = await SupabaseClient.remove_organization_member(
            organization_id, member_id
        )

        if error:
            raise HTTPException(
                status_code=500, detail="Failed to remove organization member"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove organization member: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to remove organization member"
        )


@app.post(
    "/organizations/{organization_id}/invites", response_model=InviteMemberResponse
)
async def invite_organization_member(
    organization_id: str,
    request: InviteMemberRequest,
    user_info: Tuple[str, str] = Depends(verify_bearer_token),
):
    """Invite a user to join an organization"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        admin_data, admin_error = await SupabaseClient.verify_organization_admin(
            organization_id, user_id
        )

        if admin_error:
            raise HTTPException(
                status_code=500, detail="Failed to verify organization permissions"
            )

        if not admin_data:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners and administrators can invite users",
            )

        if not request.email:
            raise HTTPException(status_code=400, detail="Email is required")

        if request.role not in [
            OrganizationRole.DEVELOPER,
            OrganizationRole.ADMINISTRATOR,
        ]:
            raise HTTPException(
                status_code=400, detail="Role must be 'developer' or 'administrator'"
            )

        invite_data, create_error = await SupabaseClient.create_organization_invite(
            organization_id=organization_id,
            email=request.email,
            role=request.role,
            invited_by=user_id,
        )

        if create_error or not invite_data:
            raise HTTPException(
                status_code=500, detail=f"Failed to create invite: {create_error}"
            )

        email = send_email(
            request.email,
            f"{invite_data['inviter_name']} invited you to join {invite_data['organization_name']} on Textfully",
            organization_invite_template(
                inviter_name=invite_data["inviter_name"],
                inviter_email=invite_data["inviter_email"],
                organization_name=invite_data["organization_name"],
                invite_link=f"https://textfully.dev/invites/{invite_data['invite_token']}",
                expires_at=invite_data["expires_at"],
            ),
        )

        if not email:
            raise HTTPException(
                status_code=500, detail="Failed to send invitation email"
            )

        return InviteMemberResponse(
            invite_token=invite_data["invite_token"],
            inviter_name=invite_data["inviter_name"],
            organization_name=invite_data["organization_name"],
            created_at=invite_data["created_at"],
            expires_at=invite_data["expires_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invite organization member: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to invite organization member"
        )


@app.post("/organizations/{organization_id}/leave", response_model=None)
async def leave_organization(
    organization_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Leave an organization"""
    user_id, org_id = user_info

    try:
        if not organization_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        if organization_id != org_id:
            raise HTTPException(status_code=403, detail="Invalid organization ID")

        _, error = await SupabaseClient.leave_organization(organization_id, user_id)

        if error:
            raise HTTPException(status_code=400, detail=str(error))

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to leave organization: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to leave organization")


@app.get("/contacts", response_model=List[ContactResponse])
async def fetch_contacts(user_info: Tuple[str, str] = Depends(verify_bearer_token)):
    """Fetch organization's contacts"""
    _, org_id = user_info

    try:
        org_contacts_data, org_contacts_error = (
            await SupabaseClient.fetch_organization_contacts(org_id)
        )

        if org_contacts_error:
            raise HTTPException(status_code=500, detail="Failed to fetch contacts")

        contact_ids = [oc["contact_id"] for oc in org_contacts_data]

        contacts_data, contacts_error = await SupabaseClient.fetch_contacts(contact_ids)

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
                created_at=org_contact["created_at"],
                updated_at=org_contact["updated_at"],
            )
            for org_contact in org_contacts_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch contacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")


@app.post("/api-keys", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: APIKeyRequest, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Create a new API key"""
    user_id, org_id = user_info

    try:
        api_key, created_at = await AuthService.create_api_key(
            user_id=user_id,
            organization_id=org_id,
            name=request.name,
            permission=request.permission,
        )
        return CreateAPIKeyResponse(api_key=api_key, created_at=created_at)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create API key")


@app.get("/api-keys", response_model=List[APIKeyResponse])
async def fetch_api_keys(user_info: Tuple[str, str] = Depends(verify_bearer_token)):
    """Fetch organization's API keys"""
    _, org_id = user_info

    try:
        data, error = await SupabaseClient.fetch_organization_api_keys(org_id)

        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch API keys")

        return [
            APIKeyResponse(
                id=key["id"],
                organization_id=key["organization_id"],
                name=key["name"],
                permission=key["permission"],
                short_key=key["short_key"],
                is_active=key["is_active"],
                last_used=key["last_used"],
                created_at=key["created_at"],
            )
            for key in data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch API keys")


@app.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str, user_info: Tuple[str, str] = Depends(verify_bearer_token)
):
    """Revoke an API key"""
    _, org_id = user_info

    try:
        if not key_id:
            raise HTTPException(status_code=400, detail="Key ID is required")

        _, error = await SupabaseClient.revoke_api_key(key_id, org_id)

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
        _, error = await SupabaseClient.health_check()

        if error:
            raise HTTPException(status_code=503, detail="Database connection failed")

        return HealthResponse(status="healthy")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/identity", response_model=IdentityResponse)
async def get_identity_hash(user_info: Tuple[str, str] = Depends(verify_bearer_token)):
    """
    Get identity verification hash for the authenticated user

    Returns a hash that can be used to verify user identity with third-party services
    """
    user_id, _ = user_info

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
