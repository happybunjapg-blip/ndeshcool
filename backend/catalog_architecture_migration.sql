-- =====================================================================
-- CATALOG ARCHITECTURE MIGRATION
--
-- Redesigns WaterPilot from a generic POS into a water-station ERP:
--   Catalog
--   ├── Physical Products   (existing `products` table, + opening_stock)
--   ├── Services            (new `services` table — no stock)
--   └── Water Configuration (new `water_config` table — the station's
--                            core commodity, configured per litre)
--
-- SAFE: idempotent, data-preserving, can run multiple times.
-- DOES NOT: drop tables, delete data, or break existing functionality.
-- Existing water refill pricing (1 KES/L cost, 10 KES/L sell) is seeded
-- into `water_config` so every existing refill amount/profit is identical.
-- =====================================================================

-- =====================================================================
-- STEP 1: CREATE water_config TABLE
-- =====================================================================
create table if not exists water_config (
    business_id uuid not null references businesses(id) on delete cascade,
    cost_per_litre numeric not null default 1.0,
    selling_price_per_litre numeric not null default 10.0,
    refill_sizes jsonb not null default '[5, 10, 20]'::jsonb,
    custom_allowed boolean not null default true,
    future jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (business_id)
);

-- =====================================================================
-- STEP 2: CREATE services TABLE
-- =====================================================================
create table if not exists services (
    id text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    name text not null,
    cost numeric not null default 0,
    selling_price numeric not null default 0,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (id, business_id),
    unique (name, business_id)
);

-- =====================================================================
-- STEP 3: ADD opening_stock TO products
-- =====================================================================
alter table if exists products
    add column if not exists opening_stock numeric not null default 0;

-- Backfill opening_stock to the current qty for every existing product.
update products set opening_stock = qty where opening_stock = 0 and qty > 0;

-- =====================================================================
-- STEP 4: EXTEND transactions.type CHECK CONSTRAINT to allow service_sale
-- =====================================================================
do $$
begin
    -- Drop the existing check constraint (generated name may vary).
    if exists (
        select 1 from information_schema.table_constraints
        where table_name = 'transactions' and constraint_type = 'CHECK'
    ) then
        execute (
            select 'alter table transactions drop constraint ' || quote_ident(constraint_name)
            from information_schema.table_constraints
            where table_name = 'transactions' and constraint_type = 'CHECK'
            limit 1
        );
    end if;
end $$;

-- Recreate with the new allowed value. Existing rows are preserved.
alter table transactions add constraint transactions_type_check check (
    type in (
        'water_refill', 'product_sale', 'bottle_water_sale',
        'bulk_delivery', 'service_sale', 'customer_payment', 'expense'
    )
);

-- =====================================================================
-- STEP 5: BACKFILL water_config FOR EXISTING BUSINESSES
-- =====================================================================
-- Every business that has any operational data gets a water_config row
-- seeded with the exact values that were previously hardcoded (1 KES/L
-- cost, 10 KES/L sell, refill sizes 5/10/20). This keeps every existing
-- refill amount, cost, and profit byte-for-byte identical.
insert into water_config (business_id, cost_per_litre, selling_price_per_litre, refill_sizes, custom_allowed)
select distinct business_id, 1.0, 10.0, '[5, 10, 20]'::jsonb, true
from products
where business_id is not null
  and business_id not in (select business_id from water_config)
on conflict (business_id) do nothing;

-- =====================================================================
-- STEP 6: ROW LEVEL SECURITY
-- =====================================================================
alter table if exists water_config enable row level security;
alter table if exists services enable row level security;

drop policy if exists "business read water_config" on water_config;
drop policy if exists "owner write water_config" on water_config;
drop policy if exists "business read services" on services;
drop policy if exists "owner write services" on services;

create policy "business read water_config" on water_config for select
    using (business_id = auth.get_business_id());
create policy "owner write water_config" on water_config for all
    using (business_id = auth.get_business_id() and auth.get_user_role() in ('owner', 'co_owner'));
create policy "business read services" on services for select
    using (business_id = auth.get_business_id());
create policy "owner write services" on services for all
    using (business_id = auth.get_business_id() and auth.get_user_role() in ('owner', 'co_owner'));

-- =====================================================================
-- STEP 7: ENABLE REALTIME (safe — ignores if already added)
-- =====================================================================
do $$
begin
    alter publication supabase_realtime add table water_config;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table services;
exception when duplicate_object then null;
end $$;

-- =====================================================================
-- ROLLBACK (if needed)
-- =====================================================================
-- 1. drop table if exists water_config;
-- 2. drop table if exists services;
-- 3. alter table products drop column if exists opening_stock;
-- 4. Recreate the original transactions type check constraint.