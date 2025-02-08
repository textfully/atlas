-- Create a function to set initial user data
create or replace function public.handle_new_user()
  returns trigger
  language plpgsql
  security definer
  set search_path = public
  as $$
begin
  -- Create user entry
  insert into public.users(auth_id)
    values(new.id);
  return new;
end;
$$;

-- Create trigger for new user creation
create trigger on_auth_user_created
  after insert on auth.users for each row
  execute function public.handle_new_user();

