-- Add short_key to api_keys
alter table api_keys
  add column short_key TEXT;

-- Add an index for faster lookups
create index idx_api_keys_short_key on api_keys(short_key);

