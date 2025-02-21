create or replace function public.handle_new_user()
  returns trigger
  language plpgsql
  security definer
  set search_path = public
  as $$
declare
  v_organization_id uuid;
begin
  -- Create user entry
  insert into public.users(auth_id)
    values (new.id);
  -- Create default organization for new user
  v_organization_id := public.create_organization('Default', new.id);
  return new;
end;
$$;

