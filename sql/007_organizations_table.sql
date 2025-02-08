-- Organization roles enum
create type public.organization_role as enum(
  'developer', -- Can use API
  'administrator', -- Can manage settings
  'owner' -- Full control and can transfer ownership
);

-- Organizations table
create table public.organizations(
  id uuid default uuid_generate_v4() primary key,
  name text not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Organization members table
create table public.organization_members(
  id uuid default uuid_generate_v4() primary key,
  organization_id uuid references public.organizations(id) not null,
  user_id uuid references auth.users(id) not null,
  role organization_role not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  -- Each user can only have one role per organization
  unique (organization_id, user_id)
);

-- Organization invites table
create table public.organization_invites(
  id uuid default uuid_generate_v4() primary key,
  organization_id uuid references public.organizations(id) not null,
  email text not null,
  role organization_role not null,
  invited_by uuid references auth.users(id) not null,
  token text not null unique, -- Used for invite link
  expires_at timestamp with time zone not null,
  created_at timestamp with time zone default now(),
  -- Prevent duplicate invites
  unique (organization_id, email)
);

-- Add indexes
create index idx_org_members_org_id on public.organization_members(organization_id);

create index idx_org_members_user_id on public.organization_members(user_id);

create index idx_org_invites_email on public.organization_invites(email);

create index idx_org_invites_token on public.organization_invites(token);

-- Update triggers
create trigger set_organizations_updated_at
  before update on public.organizations for each row
  execute procedure moddatetime(updated_at);

create trigger set_organization_members_updated_at
  before update on public.organization_members for each row
  execute procedure moddatetime(updated_at);

-- RLS Policies
-- Organizations
alter table public.organizations enable row level security;

create policy "Users can view their organizations" on public.organizations
  for select
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = id and user_id = auth.uid()));

create policy "Owners and admins can update their organizations" on public.organizations
  for update
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = id and user_id = auth.uid() and role in ('owner', 'administrator')));

-- Organization Members
alter table public.organization_members enable row level security;

create policy "Users can view members in their organizations" on public.organization_members
  for select
    using (exists (
      select
        1
      from
        public.organization_members as current_user_membership
      where
        current_user_membership.organization_id = organization_id and current_user_membership.user_id = auth.uid()));

create policy "Owners and admins can manage members" on public.organization_members
  for all
    using (exists (
      select
        1
      from
        public.organization_members as current_user_membership
      where
        current_user_membership.organization_id = organization_id and current_user_membership.user_id = auth.uid() and current_user_membership.role in ('owner', 'administrator')));

-- Organization Invites
alter table public.organization_invites enable row level security;

create policy "Users can view invites in their organizations" on public.organization_invites
  for select
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = organization_invites.organization_id and user_id = auth.uid()));

create policy "Owners and admins can manage invites" on public.organization_invites
  for all
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = organization_invites.organization_id and user_id = auth.uid() and role in ('owner', 'administrator')));

-- Helper Functions
-- Function to create an organization
create or replace function public.create_organization(p_name text, p_user_id uuid)
  returns uuid
  language plpgsql
  security definer
  as $$
declare
  v_organization_id uuid;
begin
  -- Create organization
  insert into public.organizations(name)
    values (p_name)
  returning
    id into v_organization_id;
  -- Add creator as owner
  insert into public.organization_members(organization_id, user_id, role)
    values (v_organization_id, p_user_id, 'owner');
  return v_organization_id;
end;
$$;

-- Function to transfer organization ownership
create or replace function public.transfer_organization_ownership(p_organization_id uuid, p_from_user_id uuid, p_to_user_id uuid)
  returns void
  language plpgsql
  security definer
  as $$
begin
  -- Verify current owner
  if not exists(
    select
      1
    from
      public.organization_members
    where
      organization_id = p_organization_id
      and user_id = p_from_user_id
      and role = 'owner') then
  raise exception 'Only the owner can transfer ownership';
end if;
  -- Update roles in a transaction
  update
    public.organization_members
  set
    role = 'administrator'
  where
    organization_id = p_organization_id
    and user_id = p_from_user_id;
  update
    public.organization_members
  set
    role = 'owner'
  where
    organization_id = p_organization_id
    and user_id = p_to_user_id;
end;
$$;

-- Function to create an organization invite
create or replace function public.create_organization_invite(p_organization_id uuid, p_email text, p_role organization_role, p_invited_by uuid)
  returns uuid
  language plpgsql
  security definer
  as $$
declare
  v_invite_id uuid;
  v_token text;
begin
  -- Generate unique token
  v_token := encode(gen_random_bytes(32), 'hex');
  -- Create invite
  insert into public.organization_invites(organization_id, email, role, invited_by, token, expires_at)
    values (p_organization_id, p_email, p_role, p_invited_by, v_token, now() + interval '7 days')
  returning
    id into v_invite_id;
  return v_invite_id;
end;
$$;

-- Function to accept an organization invite
create or replace function public.accept_organization_invite(p_token text, p_user_id uuid)
  returns void
  language plpgsql
  security definer
  as $$
declare
  v_invite record;
begin
  -- Get and validate invite
  select
    * into v_invite
  from
    public.organization_invites
  where
    token = p_token
    and expires_at > now();
  if v_invite is null then
    raise exception 'Invalid or expired invite';
  end if;
  -- Add member
  insert into public.organization_members(organization_id, user_id, role)
    values (v_invite.organization_id, p_user_id, v_invite.role);
  -- Delete used invite
  delete from public.organization_invites
  where id = v_invite.id;
end;
$$;

