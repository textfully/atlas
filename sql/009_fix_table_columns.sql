alter table messages
  add column organization_id UUID references organizations(id) not null;

