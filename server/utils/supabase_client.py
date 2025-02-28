from supabase._async.client import AsyncClient as Client, create_client
from typing import Optional, Tuple, Any, Dict
from config.settings import SUPABASE_URL, SUPABASE_KEY
from utils.logger import logger


class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    async def get_client(cls) -> Client:
        """
        Get Supabase client instance (Singleton pattern)

        Returns:
            Client: Supabase client instance
        """
        if cls._instance is None:
            try:
                cls._instance = await create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                raise

        return cls._instance

    @classmethod
    async def verify_token(cls, token: str) -> Optional[str]:
        """Verify Supabase JWT token

        Returns:
            Optional[str]: User ID if token is valid
        """
        client = await cls.get_client()
        response = await client.auth.get_user(token)

        if response.user:
            return response.user.id
        else:
            return None

    @classmethod
    async def execute_query(
        cls, query_function, *args, **kwargs
    ) -> Tuple[Any, Optional[str]]:
        """
        Execute a Supabase query with error handling

        Args:
            query_function: Async function that performs the Supabase query
            *args: Arguments to pass to the query function
            **kwargs: Keyword arguments to pass to the query function

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """
        try:
            client = await cls.get_client()
            response = await query_function(client, *args, **kwargs)

            # Handle response
            data = getattr(response, "data", response)
            error = getattr(response, "error", None)

            if error:
                logger.error(f"Supabase query error: {error}")

            return data, error

        except Exception as e:
            logger.error(f"Failed to execute Supabase query: {str(e)}")
            return None, str(e)

    @classmethod
    async def fetch_user_data(cls, user_id: str) -> Tuple[Any, Optional[str]]:
        """
        Fetch user data from Supabase

        Args:
            user_id: The user's ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - user_data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("users")
                .select("*")
                .eq("id", user_id)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def delete_user(cls, user_id: str) -> bool:
        """Delete a user from Supabase

        Args:
            user_id (str): The user's ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        client = await cls.get_client()
        response = await client.auth.admin.delete_user(user_id)

        if response.user is not None:
            return True
        else:
            return False

    @classmethod
    async def fetch_organization_messages(
        cls, organization_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch organization messages from Supabase

        Args:
            organization_id (str): The organization's ID
            limit (int): Number of messages to return
            offset (int): Number of messages to skip

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("messages")
                .select("*")
                .eq("organization_id", organization_id)
                .order("sent_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def verify_organization_membership(
        cls, organization_id: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Verify if user has organization access in Supabase

        Args:
            organization_id (str): The organization ID
            user_id (str): The user ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .select("*")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def verify_organization_ownership(
        cls, organization_id: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Verify if user has organization ownership in Supabase

        Args:
            organization_id (str): The organization ID
            user_id (str): The user ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .select("*")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .eq("role", "owner")
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def verify_organization_admin(
        cls, organization_id: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Verify if user is an administrator or owner of an organization

        Args:
            organization_id (str): The organization ID
            user_id (str): The user ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data with the user's role if admin/owner
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .select("*")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .in_("role", ["owner", "administrator"])
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_member_role(
        cls, organization_id: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch the role of a user in an organization

        Args:
            organization_id (str): The organization ID
            user_id (str): The user ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data with the user's role
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .select("role")
                .eq("organization_id", organization_id)
                .eq("user_id", user_id)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_message(
        cls, message_id: str, user_id: str, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch a specific message from Supabase

        Args:
            message_id (str): The message ID
            user_id (str): The user ID
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("messages")
                .select("*")
                .eq("id", message_id)
                .eq("user_id", user_id)
                .eq("organization_id", organization_id)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization_memberships(
        cls, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch organization memberships for a user

        Args:
            user_id (str): The user ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .select("organization_id, role")
                .eq("user_id", user_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organizations(
        cls, organization_ids: list[str]
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch organizations by IDs

        Args:
            organization_ids (list[str]): List of organization IDs

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organizations")
                .select("*")
                .in_("id", organization_ids)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization(
        cls, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch a single organization by ID

        Args:
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organizations")
                .select("*")
                .eq("id", organization_id)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def create_organization(
        cls, name: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Create a new organization and add the creator as owner

        Args:
            name (str): The organization name
            user_id (str): The user ID of the creator

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data with organization ID
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.rpc(
                "create_organization", {"p_name": name, "p_user_id": user_id}
            ).execute()

        return await cls.execute_query(query)

    @classmethod
    async def delete_organization(
        cls, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Delete an organization

        Args:
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organizations")
                .delete()
                .eq("id", organization_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def update_organization(
        cls, organization_id: str, name: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Update an organization's name

        Args:
            organization_id (str): The organization ID
            name (str): The new organization name

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organizations")
                .update({"name": name})
                .eq("id", organization_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization_contacts(
        cls, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch contacts for an organization

        Args:
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_contacts")
                .select("*")
                .eq("organization_id", organization_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_contacts(cls, contact_ids: list[str]) -> Tuple[Any, Optional[str]]:
        """
        Fetch contacts by IDs

        Args:
            contact_ids (list[str]): List of contact IDs

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("contacts")
                .select("phone_number")
                .in_("id", contact_ids)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization_api_keys(
        cls, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Fetch API keys for an organization

        Args:
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("api_keys")
                .select("*")
                .eq("organization_id", organization_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def create_api_key(cls, api_key_data: Dict) -> Tuple[Any, Optional[str]]:
        """
        Create an API key in Supabase

        Args:
            api_key_data (Dict): Dictionary containing API key data

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.table("api_keys").insert(api_key_data).execute()

        return await cls.execute_query(query)

    @classmethod
    async def revoke_api_key(
        cls, key_id: str, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Revoke an API key

        Args:
            key_id (str): The API key ID
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("api_keys")
                .update({"is_active": False})
                .eq("id", key_id)
                .eq("organization_id", organization_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def validate_api_key(cls, key_hash: str) -> Tuple[Any, Optional[str]]:
        """
        Validate an API key in Supabase

        Args:
            key_hash (str): The hashed API key

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("api_keys")
                .select("user_id, organization_id, is_active")
                .eq("key_hash", key_hash)
                .limit(1)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def update_api_key_last_used(
        cls, organization_id: str, key_hash: str, last_used: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Update the last used timestamp for an API key

        Args:
            organization_id (str): The organization's ID
            key_hash (str): The hashed API key
            last_used (str): The last used timestamp

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("api_keys")
                .update({"last_used": last_used})
                .eq("organization_id", organization_id)
                .eq("key_hash", key_hash)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def create_message(cls, message_data: Dict) -> Tuple[Any, Optional[str]]:
        """
        Create a message in Supabase

        Args:
            message_data (Dict): Dictionary containing message data

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.table("messages").insert(message_data).execute()

        return await cls.execute_query(query)

    @classmethod
    async def update_message_status(
        cls, message_id: str, status: str
    ) -> Tuple[Any, Optional[str]]:
        """
        Update message status in Supabase

        Args:
            message_id (str): The message ID
            status (str): The new status

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("messages")
                .update({"status": status})
                .eq("id", message_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def health_check(cls) -> Tuple[Any, Optional[str]]:
        """
        Perform a health check on the Supabase connection

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Supabase response data
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.rpc("health_check").execute()

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization_members(
        cls, organization_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Fetch all members of an organization with their details

        Args:
            organization_id (str): The organization ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Processed member data with user information
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.rpc(
                "fetch_organization_members", {"p_organization_id": organization_id}
            ).execute()

        return await cls.execute_query(query)

    @classmethod
    async def remove_organization_member(
        cls, organization_id: str, member_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Remove a member from an organization

        Args:
            organization_id (str): The organization ID
            member_id (str): The ID of the member to remove

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Success indicator
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.table("organization_members")
                .delete()
                .eq("organization_id", organization_id)
                .eq("user_id", member_id)
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def create_organization_invite(
        cls, organization_id: str, email: str, role: str, invited_by: str
    ) -> Tuple[Any, Optional[str]]:
        """Create an invitation for a user to join an organization

        Args:
            organization_id (str): The organization ID
            email (str): The email of the user to invite
            role (str): The role to assign to the user
            invited_by (str): The ID of the user creating the invite

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Invite ID if successful
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.rpc(
                "create_organization_invite",
                {
                    "p_organization_id": organization_id,
                    "p_email": email,
                    "p_role": role,
                    "p_invited_by": invited_by,
                },
            ).execute()

        return await cls.execute_query(query)

    @classmethod
    async def fetch_organization_invite(
        cls, invite_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Fetch an organization invite by ID

        Args:
            invite_id (str): The invite ID

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Invite data if successful
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return (
                await client.from_("organization_invites")
                .select("*")
                .eq("id", invite_id)
                .single()
                .execute()
            )

        return await cls.execute_query(query)

    @classmethod
    async def leave_organization(
        cls, organization_id: str, user_id: str
    ) -> Tuple[Any, Optional[str]]:
        """Allow a user to leave an organization

        Args:
            organization_id (str): The organization ID
            user_id (str): The ID of the user leaving

        Returns:
            Tuple[Any, Optional[str]]: Contains:
                - data (Any): Success indicator
                - error (Optional[str]): Error message if any
        """

        async def query(client):
            return await client.rpc(
                "leave_organization",
                {"p_organization_id": organization_id, "p_user_id": user_id},
            ).execute()

        return await cls.execute_query(query)
