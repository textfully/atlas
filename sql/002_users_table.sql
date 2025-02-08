-- Create an enum for valid subscription tiers
create type public.subscription_tier_type as enum(
  'free',
  'basic',
  'pro',
  'enterprise'
);

-- Create users table
create table public.users(
  id uuid default uuid_generate_v4() primary key,
  auth_id uuid references auth.users(id) unique,
  subscription_tier subscription_tier_type not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Create function to update user tier
create or replace function public.update_user_tier(user_id uuid, new_tier text)
  returns void
  language plpgsql
  security definer
  as $$
begin
  if new_tier not in('free', 'basic', 'pro', 'enterprise') then
    raise exception 'Invalid subscription tier';
  end if;
  update
    public.users
  set
    subscription_tier = new_tier,
    updated_at = now()
  where
    auth_id = user_id;
end;
$$;

-- Enable Row Level Security (RLS)
alter table public.users enable row level security;

-- Add RLS policy for users to read their own data
create policy "Users can view own tier" on public.users
  for select
    using (auth.uid() = auth_id);

