-- Create a storage bucket for message attachments
insert into storage.buckets(id, name, public)
  values ('message-attachments', 'message-attachments', false);

-- Add storage policy
create policy "Users can upload their own attachments" on storage.objects
  for insert
    with check (bucket_id = 'message-attachments'
    and auth.uid() = owner);

create policy "Users can view their own attachments" on storage.objects
  for select
    using (bucket_id = 'message-attachments'
      and auth.uid() = owner);

