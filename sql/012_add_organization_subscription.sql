-- Update the public.subscription_tier enum type
alter type public.subscription_tier_type rename value 'enterprise' to 'growth';

-- Add subscription_tier to organizations table
alter table public.organizations
  add column subscription_tier public.subscription_tier_type not null default 'free';

-- Function to migrate existing subscription tiers
create or replace function public.migrate_subscription_tiers()
  returns void
  language plpgsql
  security definer
  as $$
declare
  v_user record;
  v_organization_id uuid;
begin
  -- For each user with a subscription
  for v_user in
  select
    auth_id,
    subscription_tier
  from
    public.users
  where
    subscription_tier != 'free' loop
      -- Get their default organization
      select
        organization_id into v_organization_id
      from
        public.organization_members
      where
        user_id = v_user.auth_id
      order by
        created_at asc
      limit 1;
      -- Update organization subscription tier
      if v_organization_id is not null then
        update
          public.organizations
        set
          subscription_tier = v_user.subscription_tier
        where
          id = v_organization_id;
      end if;
    end loop;
end;
$$;

-- Run the migration
select
  public.migrate_subscription_tiers();

-- Drop the migration function
drop function if exists public.migrate_subscription_tiers();

