create or replace function leave_organization(p_organization_id uuid, p_user_id uuid)
  returns boolean
  language plpgsql
  security definer
  set search_path = public
  as $$
declare
  v_user_role text;
  v_owner_count integer;
begin
  -- first check if the user is a member of the organization
  select
    "role" into v_user_role
  from
    organization_members
  where
    organization_id = p_organization_id
    and user_id = p_user_id;
  if v_user_role is null then
    raise exception 'User is not a member of this organization';
  end if;
  -- if user is an owner, check if they're the last one
  if v_user_role = 'owner' then
    select
      count(*) into v_owner_count
    from
      organization_members
    where
      organization_id = p_organization_id
      and "role" = 'owner';
    if v_owner_count <= 1 then
      raise exception 'You cannot leave the organization because you are the only owner. Transfer ownership first or delete the organization.';
    end if;
  end if;
  -- remove the user from the organization
  delete from organization_members
  where organization_id = p_organization_id
    and user_id = p_user_id;
  return true;
exception
  when others then
    raise;
end;

$$;

