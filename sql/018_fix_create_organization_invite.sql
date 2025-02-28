-- Drop the existing function
drop function if exists public.create_organization_invite;

-- Function to create an organization invite
create or replace function public.create_organization_invite(p_organization_id uuid, p_email text, p_role organization_role, p_invited_by uuid)
  returns table(
    invite_token text,
    inviter_name text,
    inviter_email text,
    organization_name text,
    created_at timestamp with time zone,
    expires_at timestamp with time zone)
  language plpgsql
  security definer
  as $$
declare
  v_token text;
  v_inviter_name text;
  v_inviter_email text;
  v_organization_name text;
  v_created_at timestamp with time zone;
  v_expires_at timestamp with time zone;
begin
  -- Get inviter's name
  select
    full_name into v_inviter_name
  from
    public.users
  where
    id = p_invited_by;
  -- Get inviter's email
  select
    email into v_inviter_email
  from
    public.users
  where
    id = p_invited_by;
  -- Get organization's name
  select
    "name" into v_organization_name
  from
    public.organizations
  where
    id = p_organization_id;
  -- Generate unique token
  v_token := encode(gen_random_bytes(32), 'hex');
  -- Create invite
  insert into public.organization_invites(organization_id, email, role, invited_by, token, expires_at)
    values (p_organization_id, p_email, p_role, p_invited_by, v_token, now() + interval '72 hours')
  returning
    created_at, expires_at into v_created_at, v_expires_at;
  -- Return the invite ID, inviter name, and organization name
  return query
  select
    v_token as invite_token,
    v_inviter_name as inviter_name,
    v_inviter_email as inviter_email,
    v_organization_name as organization_name,
    v_created_at as created_at,
    v_expires_at as expires_at;
end;
$$;

