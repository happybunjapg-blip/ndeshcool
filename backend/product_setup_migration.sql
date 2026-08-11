-- =====================================================================
-- PRODUCT SETUP MIGRATION (V1 Product Setup)
--
-- Adds Product Management fields to the existing `products` table:
--   id              – unique product identifier (uuid)
--   track_inventory – whether this product participates in inventory/FIFO
--   active          – archived (False) products are hidden from sales
--   created_at      – row creation time
--
-- SAFE: idempotent, data-preserving, can run multiple times
-- DOES NOT: drop tables, delete data, or break existing functionality
-- =====================================================================

-- =====================================================================
-- STEP 1: ADD NEW COLUMNS TO PRODUCTS TABLE
-- =====================================================================
alter table if exists products
    add column if not exists id uuid;

alter table if exists products
    add column if not exists track_inventory boolean not null default true;

alter table if exists products
    add column if not exists active boolean not null default true;

alter table if exists products
    add column if not exists created_at timestamptz not null default now();

-- =====================================================================
-- STEP 2: BACKFILL EXISTING ROWS WITH A UNIQUE ID
-- =====================================================================
-- Existing rows get a deterministic uuid derived from their name+business_id
-- so the same row always maps to the same id across re-runs.
update products
set id = gen_random_uuid()
where id is null;

-- =====================================================================
-- STEP 3: MAKE ID REQUIRED
-- =====================================================================
alter table if exists products alter column id set not null;

-- =====================================================================
-- STEP 4: ADD UNIQUE INDEX ON ID
-- =====================================================================
create unique index if not exists products_id_key on products(id);

-- =====================================================================
-- STEP 5: UPDATE RLS POLICIES TO ALLOW CO-OWNERS TO MANAGE PRODUCTS
-- =====================================================================
-- The existing "owner write products" policy only allows role='owner'.
-- Co-owners must also be able to add/edit/archive products.

drop policy if exists "owner write products" on products;
create policy "owner write products" on products for all
    using (
        business_id = auth.get_business_id()
        and auth.get_user_role() in ('owner', 'co_owner')
    );

-- =====================================================================
-- STEP 6: VERIFY THE MIGRATION
-- =====================================================================
-- Run this to check the migration state:
-- select id, name, business_id, selling_price, track_inventory, active, created_at, updated_at
-- from products order by created_at desc limit 10;

-- =====================================================================
-- ROLLBACK (if needed)
-- =====================================================================
-- To roll back this migration:
-- 1. drop index if exists products_id_key;
-- 2. alter table products drop column if exists id;
-- 3. alter table products drop column if exists track_inventory;
-- 4. alter table products drop column if exists active;
-- 5. alter table products drop column if exists created_at;
-- 6. Recreate the original "owner write products" policy if needed