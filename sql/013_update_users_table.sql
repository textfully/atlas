-- Update triggers
create or replace trigger set_users_updated_at
  before update on public.users for each row
  execute procedure moddatetime(updated_at);

-- Delete update_user_tier function
drop function if exists public.update_user_tier;

-- Delete subscription_tier column
alter table public.users
  drop column if exists subscription_tier;

-- Update handle_new_user function
-- Add new columns to users table with default value to allow the migration
alter table public.users
  add column full_name text,
  add column avatar_url text;

-- Create temporary function to populate existing users with full_name and avatar_url
create or replace function public.populate_existing_users_data()
  returns void
  language plpgsql
  security definer
  as $$
begin
  update
    public.users u
  set
    full_name =(
      select
        raw_user_meta_data ->> 'full_name'
      from
        auth.users
      where
        id = u.auth_id), avatar_url =(
      select
        raw_user_meta_data ->> 'avatar_url'
      from
        auth.users
      where
        id = u.auth_id)
  where
    u.full_name is null;
end;
$$;

-- Execute the function to populate existing data
select
  public.populate_existing_users_data();

-- Drop the temporary function
drop function if exists public.populate_existing_users_data();

-- Now make the column not null
alter table public.users
  alter column full_name set not null;

create or replace function public.handle_new_user()
  returns trigger
  language plpgsql
  security definer
  as $$
declare
  v_organization_id uuid;
  v_avatar_url text;
  v_name text;
begin
  -- Extract name from raw_user_meta_data and set it to full_name
  v_name := new.raw_user_meta_data ->> 'full_name';
  -- If user has an avatar, set it to the avatar_url
  if new.raw_user_meta_data ->> 'avatar_url' is not null then
    v_avatar_url := new.raw_user_meta_data ->> 'avatar_url';
  end if;
  -- Create user entry with profile information
  insert into public.users(id, full_name, avatar_url)
    values (new.id, v_name, v_avatar_url);
  -- Create default organization for new user
  v_organization_id := public.create_organization('Default', new.id);
  return new;
end;
$$;

-- Add RLS policy for users to read their own data
create policy "Users can view own data" on public.users
  for select
    using (auth.uid() = id);

