-- =====================================================================
-- FORCE FIX: Run this ENTIRE script in Supabase SQL Editor
-- =====================================================================

-- 1. Show me all current invitations with their owner_invite values
select code, owner_invite, created_at from invitations order by created_at desc;

-- 2. Add the column (safe if already exists)
alter table invitations add column if not exists owner_invite boolean;

-- 3. Force ALL existing rows to have owner_invite = FALSE
update invitations set owner_invite = false;

-- 4. Make the column required going forward
alter table invitations alter column owner_invite set not null;
alter table invitations alter column owner_invite set default false;

-- 5. Show me the fixed data
select code, owner_invite, created_at from invitations order by created_at desc;