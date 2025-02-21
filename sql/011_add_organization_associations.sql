-- Add index for organization_id on messages
create index idx_messages_organization_id on public.messages(organization_id);

-- Update messages RLS policies
drop policy if exists "Users can view their own messages" on public.messages;

create policy "Users can view their organization's messages" on public.messages
  for select
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = messages.organization_id and user_id = auth.uid()));

-- Update API keys table
alter table public.api_keys
  add column organization_id uuid references public.organizations(id);

-- Migrate existing API keys data
create or replace function public.migrate_api_keys_organization()
  returns void
  language plpgsql
  security definer
  as $$
declare
  v_user record;
  v_default_org_id uuid;
begin
  -- For each user with API keys
  for v_user in select distinct
    user_id
  from
    public.api_keys loop
      -- Get their default organization
      select
        organization_id into v_default_org_id
      from
        public.organization_members
      where
        user_id = v_user.user_id
      order by
        created_at asc
      limit 1;
      -- If no organization exists, create one
      if v_default_org_id is null then
        v_default_org_id := public.create_organization('Default', v_user.user_id);
      end if;
      -- Update API keys
      update
        public.api_keys
      set
        organization_id = v_default_org_id
      where
        user_id = v_user.user_id;
    end loop;
end;
$$;

-- Run the API keys migration
select
  public.migrate_api_keys_organization();

-- Now make organization_id not null after data migration
alter table public.api_keys
  alter column organization_id set not null;

-- Add index for organization_id on api_keys
create index idx_api_keys_organization_id on public.api_keys(organization_id);

-- Update API keys RLS policies
drop policy if exists "Users can view their own API keys" on public.api_keys;

create policy "Users can view their organization's API keys" on public.api_keys
  for select
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = api_keys.organization_id and user_id = auth.uid()));

-- Function to migrate messages data
create or replace function public.migrate_messages_organization()
  returns void
  language plpgsql
  security definer
  as $$
declare
  v_user record;
  v_default_org_id uuid;
begin
  -- For each user with messages
  for v_user in select distinct
    user_id
  from
    public.messages loop
      -- Get their default organization
      select
        organization_id into v_default_org_id
      from
        public.organization_members
      where
        user_id = v_user.user_id
      order by
        created_at asc
      limit 1;
      -- If no organization exists, create one
      if v_default_org_id is null then
        v_default_org_id := public.create_organization('Default', v_user.user_id);
      end if;
      -- Update messages
      update
        public.messages
      set
        organization_id = v_default_org_id
      where
        user_id = v_user.user_id;
    end loop;
end;
$$;

-- Run the messages migration
select
  public.migrate_messages_organization();

-- Drop migration functions after running them
drop function if exists public.migrate_api_keys_organization();

drop function if exists public.migrate_messages_organization();

