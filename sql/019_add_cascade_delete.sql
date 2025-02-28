-- Drop existing constraints first
alter table public.organization_members
  drop constraint if exists organization_members_organization_id_fkey;

alter table public.organization_invites
  drop constraint if exists organization_invites_organization_id_fkey;

alter table public.organization_contacts
  drop constraint if exists organization_contacts_organization_id_fkey;

alter table public.api_keys
  drop constraint if exists api_keys_organization_id_fkey;

alter table public.messages
  drop constraint if exists messages_organization_id_fkey;

-- Recreate constraints with ON DELETE CASCADE
alter table public.organization_members
  add constraint organization_members_organization_id_fkey foreign key (organization_id) references public.organizations(id) on delete cascade;

alter table public.organization_invites
  add constraint organization_invites_organization_id_fkey foreign key (organization_id) references public.organizations(id) on delete cascade;

alter table public.organization_contacts
  add constraint organization_contacts_organization_id_fkey foreign key (organization_id) references public.organizations(id) on delete cascade;

alter table public.api_keys
  add constraint api_keys_organization_id_fkey foreign key (organization_id) references public.organizations(id) on delete cascade;

alter table public.messages
  add constraint messages_organization_id_fkey foreign key (organization_id) references public.organizations(id) on delete cascade;

