do $$
declare
  r RECORD;
begin
  for r in (
    select
      conname,
      conrelid::regclass as table_name
    from
      pg_constraint
    where
      confrelid = 'public.users'::regclass
      and confkey[1] =(
        select
          attnum
        from
          pg_attribute
        where
          attrelid = 'public.users'::regclass
          and attname = 'id'))
      loop
        execute 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT ' || r.conname;
      end loop;
end
$$;

alter table public.users
  drop constraint users_pkey;

create TEMP table user_id_mapping as
select
  id as old_id,
  auth_id as new_id
from
  public.users;

alter table public.users
  drop column id;

alter table public.users
  add primary key (auth_id);

alter table public.users rename column auth_id to id;

alter table public.users
  add constraint users_id_fkey foreign key (id) references auth.users(id) on delete cascade;

alter table public.users
  drop constraint users_auth_id_key;

