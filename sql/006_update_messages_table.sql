-- Add sms_fallback to messages
alter table messages
  add column sms_fallback BOOLEAN default false;

