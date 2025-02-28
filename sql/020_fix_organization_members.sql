-- Drop the existing function
drop function if exists public.fetch_organization_members;

-- Function to fetch organization members with user information
create or replace function public.fetch_organization_members(p_organization_id uuid)
  returns table(
    id uuid,
    organization_id uuid,
    user_id uuid,
    role organization_role,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    full_name text,
    email text,
    avatar_url text
  )
  as $$
begin
  return QUERY
  select
    om.id,
    om.organization_id,
    om.user_id,
    om.role,
    om.created_at,
    om.updated_at,
    u.full_name,
    u.email,
    u.avatar_url
  from
    public.organization_members om
    inner join public.users u on om.user_id = u.id
  where
    om.organization_id = p_organization_id;
end;
$$
language plpgsql
security definer;

