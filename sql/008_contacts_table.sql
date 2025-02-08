-- Create contacts table (just stores the phone number)
create table public.contacts(
  id uuid default uuid_generate_v4() primary key,
  phone_number text not null unique, -- This will be the unique identifier
);

-- Rename user_contacts to organization_contacts
create table public.organization_contacts(
  id uuid default uuid_generate_v4() primary key,
  organization_id uuid references public.organizations(id) not null,
  contact_id uuid references public.contacts(id) not null,
  -- Organization-specific contact details
  first_name text,
  last_name text,
  is_subscribed boolean default true,
  -- Organization-specific metadata
  notes text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  -- Each contact should only be linked once per organization
  unique (organization_id, contact_id)
);

-- Create indexes
create index idx_contacts_phone_number on public.contacts(phone_number);

create index idx_organization_contacts_organization_id on public.organization_contacts(organization_id);

create index idx_organization_contacts_contact_id on public.organization_contacts(contact_id);

create index idx_organization_contacts_subscription on public.organization_contacts(organization_id, is_subscribed);

-- Add updated_at trigger
create or replace function public.handle_updated_at()
  returns trigger
  language plpgsql
  as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_organization_contacts_updated_at
  before update on public.organization_contacts for each row
  execute procedure moddatetime(updated_at);

-- Add RLS policies
alter table public.contacts enable row level security;

alter table public.organization_contacts enable row level security;

-- Anyone can view contacts (they're like a phone book)
create policy "Anyone can view contacts" on public.contacts
  for select to authenticated
    using (true);

-- Service role can manage contacts
create policy "Service role can manage contacts" on public.contacts to service_role
  using (true)
  with check (true);

-- Users can view their organization contacts
create policy "Users can view their organization contacts" on public.organization_contacts
  for select
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = organization_contacts.organization_id and user_id = auth.uid()));

-- Users can manage their organization contacts
create policy "Users can manage their organization contacts" on public.organization_contacts
  for all
    using (exists (
      select
        1
      from
        public.organization_members
      where
        organization_id = organization_contacts.organization_id and user_id = auth.uid()));

-- Helper Functions
-- Function to normalize phone numbers
create or replace function public.normalize_phone_number(phone_number text)
  returns text
  language plpgsql
  immutable
  as $$
begin
  -- Validate E.164 format:
  -- 1. Must start with '+'
  -- 2. Must contain only digits after '+'
  -- 3. Total length must be between 8 and 15 characters (including '+')
  if not phone_number ~ '^\+[0-9]{7,14}$' then
    raise exception 'Invalid phone number format. Must be in E.164 format (e.g., +12345678901)';
  end if;
  return phone_number;
end;
$$;

-- Function to get or create a contact
create or replace function public.get_or_create_contact(p_phone text)
  returns uuid
  language plpgsql
  security definer
  as $$
declare
  v_contact_id uuid;
  v_normalized_phone text;
begin
  -- Normalize phone number
  v_normalized_phone := public.normalize_phone_number(p_phone);
  -- Try to get existing contact
  select
    id into v_contact_id
  from
    public.contacts
  where
    phone_number = v_normalized_phone;
  -- Create if doesn't exist
  if v_contact_id is null then
    insert into public.contacts(phone_number)
      values (v_normalized_phone)
    returning
      id into v_contact_id;
  end if;
  return v_contact_id;
end;
$$;

-- Function to add or update an organization's contact
create or replace function public.upsert_organization_contact(p_organization_id uuid, p_phone text, p_first_name text default null, p_last_name text default null, p_notes text default null, p_is_subscribed boolean default true)
  returns uuid
  language plpgsql
  security definer
  as $$
declare
  v_contact_id uuid;
begin
  -- Get or create contact
  v_contact_id := public.get_or_create_contact(p_phone);
  -- Create or update organization's contact relationship
  insert into public.organization_contacts(organization_id, contact_id, first_name, last_name, notes, is_subscribed)
    values (p_organization_id, v_contact_id, p_first_name, p_last_name, p_notes, p_is_subscribed)
  on conflict (organization_id, contact_id)
    do update set
      first_name = excluded.first_name, last_name = excluded.last_name, notes = excluded.notes, is_subscribed = excluded.is_subscribed, updated_at = now();
  return v_contact_id;
end;
$$;

-- Function to search organization's contacts
create or replace function public.search_organization_contacts(p_organization_id uuid, p_query text, p_subscribed_only boolean default false)
  returns table(
    contact_id uuid,
    phone_number text,
    first_name text,
    last_name text,
    is_subscribed boolean,
    notes text)
  language plpgsql
  security definer
  as $$
begin
  return query
  select
    c.id as contact_id,
    c.phone_number,
    oc.first_name,
    oc.last_name,
    oc.is_subscribed,
    oc.notes
  from
    public.contacts c
    inner join public.organization_contacts oc on c.id = oc.contact_id
  where
    oc.organization_id = p_organization_id
    and(not p_subscribed_only
      or oc.is_subscribed)
    and(c.phone_number ilike '%' || p_query || '%'
      or oc.first_name ilike '%' || p_query || '%'
      or oc.last_name ilike '%' || p_query || '%')
  order by
    oc.created_at desc;
end;
$$;

