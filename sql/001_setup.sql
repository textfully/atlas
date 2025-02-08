-- Enable necessary extensions
create extension if not exists "uuid-ossp";
create extension if not exists "moddatetime";

-- Create enum types first
create type message_status as ENUM(
  'pending',
  'sent',
  'delivered',
  'read',
  'failed'
);

create type message_service as ENUM(
  'sms',
  'imessage'
);

create type api_key_permission as ENUM(
  'all',
  'send_only'
);

-- Create messages table
create table public.messages(
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references auth.users(id),
  message_id text not null unique,
  recipient text not null,
  text text not null,
  service message_service not null,
  status message_status not null,
  sent_at timestamp with time zone not null,
  delivered_at timestamp with time zone,
  read_at timestamp with time zone,
  created_at timestamp with time zone default now()
);

-- Create API keys table
create table public.api_keys(
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references auth.users(id),
  name text not null,
  key_hash text not null unique,
  permission api_key_permission not null default 'all',
  is_active boolean default true,
  last_used timestamp with time zone,
  created_at timestamp with time zone default now()
);

-- Create indexes
create index idx_messages_user_id on public.messages(user_id);

create index idx_messages_message_id on public.messages(message_id);

create index idx_messages_status on public.messages(status);

create index idx_messages_sent_at on public.messages(sent_at);

create index idx_api_keys_user_id on public.api_keys(user_id);

create index idx_api_keys_key_hash on public.api_keys(key_hash);

create index idx_api_keys_is_active on public.api_keys(is_active);

-- Enable Row Level Security (RLS)
alter table public.messages enable row level security;

alter table public.api_keys enable row level security;

-- RLS Policies for messages
create policy "Users can view their own messages" on public.messages
  for select
    using (auth.uid() = user_id);

create policy "Service role can insert messages" on public.messages
  for insert
    with check (auth.role() = 'service_role');

-- RLS Policies for API keys
create policy "Users can view their own API keys" on public.api_keys
  for select
    using (auth.uid() = user_id);

create policy "Service role can manage API keys" on public.api_keys
  using (auth.role() = 'service_role');

-- Helper Functions
create or replace function public.health_check()
  returns boolean
  language plpgsql
  security definer
  as $$
begin
  return true;
end;
$$;

-- Trigger for updating last_used timestamp on API keys
create or replace function public.update_api_key_last_used()
  returns trigger
  language plpgsql
  security definer
  as $$
begin
  new.last_used = now();
  return new;
end;
$$;

create trigger update_api_key_last_used
  before update on public.api_keys for each row
  execute function public.update_api_key_last_used();

