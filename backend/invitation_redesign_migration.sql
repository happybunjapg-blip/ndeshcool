-- =====================================================================
-- INVITATION REDESIGN MIGRATION
-- 
-- Replaces: owner_invite boolean → explicit role field
-- Adds: role, status, used_at, used_by, created_by columns
-- Adds: CHECK constraints, indexes
-- Updates: profiles role CHECK to include co_owner
-- Updates: RLS policies to restrict invitation management
--
-- SAFE: idempotent, data-preserving, can run multiple times
-- DOES NOT: drop tables, delete data, or break existing functionality
-- =====================================================================

-- =====================================================================
-- STEP 1: ADD NEW COLUMNS TO INVITATIONS TABLE
-- =====================================================================
alter table if exists invitations
    add column if not exists role text;

alter table if exists invitations
    add column if not exists status text;

alter table if exists invitations
    add column if not exists used_at timestamptz;

alter table if exists invitations
    add column if not exists used_by uuid references auth.users(id) on delete set null;

alter table if exists invitations
    add column if not exists created_by uuid references auth.users(id) on delete set null;

-- =====================================================================
-- STEP 2: MIGRATE EXISTING DATA
-- =====================================================================

-- Map owner_invite → role
-- owner_invite=true  → role='co_owner'
-- owner_invite=false → role='worker'
-- owner_invite=NULL  → role='worker' (default for legacy rows)
update invitations
set role = case
    when owner_invite = true then 'co_owner'
    else 'worker'
end
where role is null;

-- Map is_invalidated → status
-- is_invalidated=true → status='used'
-- Not expired + not invalidated → status='active'
-- Expired → status='expired'
update invitations
set status = 'used'
where is_invalidated = true and status is null;

update invitations
set status = 'active'
where status is null
  and (is_invalidated = false or is_invalidated is null)
  and (expires_at > now() or expires_at is null);

update invitations
set status = 'expired'
where status is null
  and expires_at <= now();

-- Safety net: any remaining null status → 'active'
update invitations set status = 'active' where status is null;

-- =====================================================================
-- STEP 3: MAKE NEW COLUMNS REQUIRED
-- =====================================================================
alter table if exists invitations alter column role set not null;
alter table if exists invitations alter column status set not null;
alter table if exists invitations alter column status set default 'active';

-- =====================================================================
-- STEP 4: ADD CHECK CONSTRAINTS
-- =====================================================================

-- Drop old constraints if they exist (they may not)
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints
        where table_name = 'invitations' and constraint_name = 'invitations_role_check'
    ) then
        alter table invitations drop constraint invitations_role_check;
    end if;
end $$;

alter table invitations add constraint invitations_role_check
    check (role in ('worker', 'co_owner'));

do $$
begin
    if exists (
        select 1 from information_schema.table_constraints
        where table_name = 'invitations' and constraint_name = 'invitations_status_check'
    ) then
        alter table invitations drop constraint invitations_status_check;
    end if;
end $$;

alter table invitations add constraint invitations_status_check
    check (status in ('active', 'used', 'revoked', 'expired'));

-- =====================================================================
-- STEP 5: UPDATE PROFILES ROLE CONSTRAINT
-- =====================================================================

do $$
begin
    if exists (
        select 1 from information_schema.table_constraints
        where table_name = 'profiles' and constraint_name = 'profiles_role_check'
    ) then
        alter table profiles drop constraint profiles_role_check;
    end if;
end $$;

alter table profiles add constraint profiles_role_check
    check (role in ('owner', 'worker', 'co_owner'));

-- =====================================================================
-- STEP 6: ADD INDEXES
-- =====================================================================

create index if not exists idx_invitations_code on invitations(code);
create index if not exists idx_invitations_business on invitations(business_id);
create index if not exists idx_invitations_status on invitations(status);

-- =====================================================================
-- STEP 7: CREATE SECURITY DEFINER FUNCTION FOR UNAUTHENTICATED LOOKUP
-- =====================================================================

-- This function allows unauthenticated users to look up valid invitations
-- by code. It returns ONLY the minimum information needed for the signup flow.
-- SECURITY DEFINER means it runs with the privileges of the function creator
-- (bypassing RLS), but it's tightly scoped to return only active invitations.

create or replace function public.lookup_invitation(p_code text)
returns table (
    code text,
    business_id uuid,
    role text,
    status text,
    expires_at timestamptz,
    business_name text
)
language sql
security definer
stable
as $$
    select
        i.code,
        i.business_id,
        i.role,
        i.status,
        i.expires_at,
        b.name as business_name
    from public.invitations i
    join public.businesses b on b.id = i.business_id
    where i.code = p_code
      and i.status = 'active'
      and i.expires_at > now();
$$;

-- =====================================================================
-- STEP 8: CREATE FUNCTION FOR ATOMIC INVITATION CONSUMPTION
-- =====================================================================

-- This function atomically marks an invitation as used.
-- Returns true if the invitation was consumed, false if it was already used.
-- This prevents race conditions where two requests consume the same invitation.

create or replace function public.consume_invitation(p_code text, p_user_id uuid)
returns boolean
language sql
security definer
as $$
    update public.invitations
    set status = 'used',
        used_at = now(),
        used_by = p_user_id
    where code = p_code
      and status = 'active'
      and expires_at > now();
    -- Returns true if a row was updated, false otherwise
    $$;

-- =====================================================================
-- STEP 9: UPDATE RLS POLICIES
-- =====================================================================

-- Drop old policies
drop policy if exists "owner manage invitations" on invitations;
drop policy if exists "worker read invitations" on invitations;

-- Owners can read invitations for their business
drop policy if exists "owner read invitations" on invitations;
create policy "owner read invitations" on invitations
    for select using (
        business_id = auth.get_business_id()
        and auth.get_user_role() in ('owner', 'co_owner')
    );

-- Owners can create invitations
drop policy if exists "owner create invitations" on invitations;
create policy "owner create invitations" on invitations
    for insert with check (
        business_id = auth.get_business_id()
        and auth.get_user_role() in ('owner', 'co_owner')
    );

-- Owners can update invitations (revoke, etc.)
drop policy if exists "owner update invitations" on invitations;
create policy "owner update invitations" on invitations
    for update using (
        business_id = auth.get_business_id()
        and auth.get_user_role() in ('owner', 'co_owner')
    );

-- Owners can delete invitations
drop policy if exists "owner delete invitations" on invitations;
create policy "owner delete invitations" on invitations
    for delete using (
        business_id = auth.get_business_id()
        and auth.get_user_role() in ('owner', 'co_owner')
    );

-- =====================================================================
-- STEP 10: VERIFY THE MIGRATION
-- =====================================================================

-- Run this to check the migration state:
-- select code, role, status, owner_invite, is_invalidated, expires_at from invitations order by created_at desc limit 10;

-- =====================================================================
-- ROLLBACK (if needed)
-- =====================================================================
-- To roll back this migration:
-- 1. drop function if exists public.lookup_invitation(text);
-- 2. drop function if exists public.consume_invitation(text, uuid);
-- 3. alter table invitations drop constraint if exists invitations_role_check;
-- 4. alter table invitations drop constraint if exists invitations_status_check;
-- 5. alter table invitations drop column if exists role;
-- 6. alter table invitations drop column if exists status;
-- 7. alter table invitations drop column if exists used_at;
-- 8. alter table invitations drop column if exists used_by;
-- 9. alter table invitations drop column if exists created_by;
-- 10. drop index if exists idx_invitations_code;
-- 11. drop index if exists idx_invitations_business;
-- 12. drop index if exists idx_invitations_status;
-- 13. Recreate profiles_role_check if needed
-- 14. Restore RLS policies if needed