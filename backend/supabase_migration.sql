-- =====================================================================
-- AquaFlow Migration: Add multi-business authentication
-- 
-- SAFE for existing databases with data.
-- IDEMPOTENT: safe to run multiple times.
-- PRESERVES all existing data.
--
-- Run this in Supabase SQL Editor.
-- =====================================================================

-- =====================================================================
-- STEP 1: Create new tables (idempotent)
-- =====================================================================

create table if not exists businesses (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_id uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists invitations (
    code text primary key,
    business_id uuid not null references businesses(id) on delete cascade,
    owner_invite boolean not null default false,
    email text default '',
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    is_invalidated boolean not null default false
);

-- =====================================================================
-- STEP 2: Add columns to existing tables (idempotent via IF NOT EXISTS)
-- =====================================================================

-- Profiles: add new columns
alter table if exists profiles 
    add column if not exists first_name text not null default '';
alter table if exists profiles 
    add column if not exists last_name text not null default '';
alter table if exists profiles 
    add column if not exists phone text not null default '';
alter table if exists profiles 
    add column if not exists business_id uuid;

-- Migrate existing 'name' data to 'first_name' (only if 'name' column exists)
do $$
begin
    if exists (
        select 1 from information_schema.columns 
        where table_name = 'profiles' and column_name = 'name'
    ) then
        update profiles set first_name = name 
        where name is not null and first_name = '';
    end if;
end $$;

-- Operational tables: add business_id columns
alter table if exists products 
    add column if not exists business_id uuid;
alter table if exists product_batches 
    add column if not exists business_id uuid;
alter table if exists customers 
    add column if not exists business_id uuid;
alter table if exists business_days 
    add column if not exists business_id uuid;
alter table if exists transactions 
    add column if not exists business_id uuid;
alter table if exists expenses 
    add column if not exists business_id uuid;
alter table if exists timeline_events 
    add column if not exists business_id uuid;
alter table if exists water_readings 
    add column if not exists business_id uuid;

-- =====================================================================
-- STEP 3: Update role constraint BEFORE adding the new one
-- =====================================================================

-- First migrate existing 'partner' roles to 'owner' (safe even if column doesn't exist)
do $$
begin
    if exists (
        select 1 from information_schema.columns 
        where table_name = 'profiles' and column_name = 'role'
    ) then
        update profiles set role = 'owner' where role = 'partner';
    end if;
end $$;

-- Now safely drop old constraint and add new one
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'profiles' and constraint_name = 'profiles_role_check'
    ) then
        alter table profiles drop constraint profiles_role_check;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'profiles' and constraint_name = 'profiles_role_check'
    ) then
        alter table profiles add constraint profiles_role_check 
            check (role in ('owner', 'worker'));
    end if;
end $$;

-- =====================================================================
-- STEP 4: Create a default business for existing data
-- =====================================================================

do $$
declare
    default_biz_id uuid;
    existing_profile_count int;
begin
    select id into default_biz_id from businesses 
    where name = 'Default Business' limit 1;
    
    select count(*) into existing_profile_count from profiles;
    
    if existing_profile_count > 0 and default_biz_id is null then
        insert into businesses (name, owner_id, created_at)
        values ('Default Business', null, now())
        returning id into default_biz_id;
        
        update profiles set business_id = default_biz_id where business_id is null;
        update products set business_id = default_biz_id where business_id is null;
        update product_batches set business_id = default_biz_id where business_id is null;
        update customers set business_id = default_biz_id where business_id is null;
        update business_days set business_id = default_biz_id where business_id is null;
        update transactions set business_id = default_biz_id where business_id is null;
        update expenses set business_id = default_biz_id where business_id is null;
        update timeline_events set business_id = default_biz_id where business_id is null;
        update water_readings set business_id = default_biz_id where business_id is null;
    end if;
end $$;

-- =====================================================================
-- STEP 5: Add foreign key constraints (idempotent)
-- =====================================================================

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'profiles' and constraint_name = 'profiles_business_id_fkey'
    ) then
        alter table profiles alter column business_id set not null;
        alter table profiles add constraint profiles_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'products' and constraint_name = 'products_business_id_fkey'
    ) then
        alter table products alter column business_id set not null;
        alter table products add constraint products_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'product_batches' and constraint_name = 'product_batches_business_id_fkey'
    ) then
        alter table product_batches alter column business_id set not null;
        alter table product_batches add constraint product_batches_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'customers' and constraint_name = 'customers_business_id_fkey'
    ) then
        alter table customers alter column business_id set not null;
        alter table customers add constraint customers_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'business_days' and constraint_name = 'business_days_business_id_fkey'
    ) then
        alter table business_days alter column business_id set not null;
        alter table business_days add constraint business_days_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'transactions' and constraint_name = 'transactions_business_id_fkey'
    ) then
        alter table transactions alter column business_id set not null;
        alter table transactions add constraint transactions_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'expenses' and constraint_name = 'expenses_business_id_fkey'
    ) then
        alter table expenses alter column business_id set not null;
        alter table expenses add constraint expenses_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'timeline_events' and constraint_name = 'timeline_events_business_id_fkey'
    ) then
        alter table timeline_events alter column business_id set not null;
        alter table timeline_events add constraint timeline_events_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'water_readings' and constraint_name = 'water_readings_business_id_fkey'
    ) then
        alter table water_readings alter column business_id set not null;
        alter table water_readings add constraint water_readings_business_id_fkey 
            foreign key (business_id) references businesses(id) on delete cascade;
    end if;
end $$;

-- =====================================================================
-- STEP 6: Update primary keys to include business_id
-- =====================================================================

-- Products: drop foreign key from product_batches first, then PK, then recreate
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'product_batches' and constraint_type = 'FOREIGN KEY'
        and constraint_name = 'product_batches_product_name_fkey'
    ) then
        alter table product_batches drop constraint product_batches_product_name_fkey;
    end if;
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'product_batches' and constraint_type = 'FOREIGN KEY'
        and constraint_name = 'product_batches_product_name_business_id_fkey'
    ) then
        alter table product_batches drop constraint product_batches_product_name_business_id_fkey;
    end if;
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'products' and constraint_type = 'PRIMARY KEY'
        and constraint_name = 'products_pkey'
    ) then
        alter table products drop constraint products_pkey cascade;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'products' and constraint_type = 'PRIMARY KEY'
    ) then
        alter table products add primary key (name, business_id);
    end if;
end $$;

-- Customers
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'customers' and constraint_type = 'PRIMARY KEY'
        and constraint_name = 'customers_pkey'
    ) then
        alter table customers drop constraint customers_pkey;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'customers' and constraint_type = 'PRIMARY KEY'
    ) then
        alter table customers add primary key (id, business_id);
    end if;
end $$;

-- Business Days
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'business_days' and constraint_type = 'PRIMARY KEY'
        and constraint_name = 'business_days_pkey'
    ) then
        alter table business_days drop constraint business_days_pkey;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'business_days' and constraint_type = 'PRIMARY KEY'
    ) then
        alter table business_days add primary key (id, business_id);
    end if;
end $$;

-- Transactions
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'transactions' and constraint_type = 'PRIMARY KEY'
        and constraint_name = 'transactions_pkey'
    ) then
        alter table transactions drop constraint transactions_pkey;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'transactions' and constraint_type = 'PRIMARY KEY'
    ) then
        alter table transactions add primary key (id, business_id);
    end if;
end $$;

-- Water readings
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'water_readings' and constraint_type = 'PRIMARY KEY'
        and constraint_name = 'water_readings_pkey'
    ) then
        alter table water_readings drop constraint water_readings_pkey;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'water_readings' and constraint_type = 'PRIMARY KEY'
    ) then
        alter table water_readings add primary key (date, business_id);
    end if;
end $$;

-- Product batches: update foreign key
do $$
begin
    if exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'product_batches' and constraint_type = 'FOREIGN KEY'
        and constraint_name = 'product_batches_product_name_fkey'
    ) then
        alter table product_batches drop constraint product_batches_product_name_fkey;
    end if;
    if not exists (
        select 1 from information_schema.table_constraints 
        where table_name = 'product_batches' and constraint_type = 'FOREIGN KEY'
    ) then
        alter table product_batches 
            add foreign key (product_name, business_id) 
            references products(name, business_id) on delete cascade;
    end if;
end $$;

-- =====================================================================
-- STEP 7: Add indexes
-- =====================================================================

create unique index if not exists one_open_business_day_per_business
    on business_days (business_id, ((status)))
    where status = 'OPEN';

-- =====================================================================
-- STEP 8: Create helper function to get current user's business_id
-- =====================================================================
-- This function uses SECURITY DEFINER (bypasses RLS) to read the profiles
-- table without causing infinite recursion.

create or replace function auth.get_business_id()
returns uuid
language sql
security definer
stable
as $$
    select business_id from public.profiles where id = auth.uid();
$$;

create or replace function auth.get_user_role()
returns text
language sql
security definer
stable
as $$
    select role from public.profiles where id = auth.uid();
$$;

-- =====================================================================
-- STEP 9: Row Level Security (idempotent — DROP IF EXISTS + CREATE)
-- =====================================================================

-- Enable RLS
alter table if exists businesses enable row level security;
alter table if exists profiles enable row level security;
alter table if exists invitations enable row level security;
alter table if exists products enable row level security;
alter table if exists product_batches enable row level security;
alter table if exists customers enable row level security;
alter table if exists business_days enable row level security;
alter table if exists transactions enable row level security;
alter table if exists expenses enable row level security;
alter table if exists timeline_events enable row level security;
alter table if exists water_readings enable row level security;

-- Drop old policies
drop policy if exists "users read own business" on businesses;
drop policy if exists "self read" on profiles;
drop policy if exists "self update" on profiles;
drop policy if exists "owner read profiles" on profiles;
drop policy if exists "owner manage invitations" on invitations;
drop policy if exists "worker read invitations" on invitations;
drop policy if exists "business read products" on products;
drop policy if exists "business read batches" on product_batches;
drop policy if exists "business read customers" on customers;
drop policy if exists "business read business_days" on business_days;
drop policy if exists "business read transactions" on transactions;
drop policy if exists "business read expenses" on expenses;
drop policy if exists "business read timeline" on timeline_events;
drop policy if exists "business read water_readings" on water_readings;
drop policy if exists "owner write products" on products;
drop policy if exists "owner write batches" on product_batches;
drop policy if exists "business write transactions" on transactions;
drop policy if exists "business write expenses" on expenses;
drop policy if exists "business write timeline" on timeline_events;
drop policy if exists "business write water_readings" on water_readings;
drop policy if exists "business write business_days" on business_days;
drop policy if exists "business write customers" on customers;
drop policy if exists "authenticated read" on products;
drop policy if exists "authenticated read" on product_batches;
drop policy if exists "authenticated read" on customers;
drop policy if exists "authenticated read" on business_days;
drop policy if exists "authenticated read" on transactions;
drop policy if exists "authenticated read" on expenses;
drop policy if exists "authenticated read" on timeline_events;
drop policy if exists "authenticated read" on water_readings;
drop policy if exists "authenticated write" on transactions;
drop policy if exists "authenticated write" on expenses;
drop policy if exists "authenticated write" on timeline_events;
drop policy if exists "authenticated write" on water_readings;
drop policy if exists "authenticated write" on business_days;
drop policy if exists "authenticated write" on customers;
drop policy if exists "partner write products" on products;
drop policy if exists "partner write batches" on product_batches;

-- Create new policies using SECURITY DEFINER helper functions
-- to avoid infinite recursion (policies cannot query the same table they protect)

create policy "users read own business" on businesses
    for select using (id = auth.get_business_id());

create policy "self read" on profiles
    for select using (auth.uid() = id);

create policy "self update" on profiles
    for update using (auth.uid() = id);

create policy "owner read profiles" on profiles
    for select using (
        business_id = auth.get_business_id()
        and auth.get_user_role() = 'owner'
    );

create policy "owner manage invitations" on invitations
    for all using (business_id = auth.get_business_id());

create policy "worker read invitations" on invitations
    for select using (is_invalidated = false and expires_at > now());

create policy "business read products" on products for select
    using (business_id = auth.get_business_id());
create policy "business read batches" on product_batches for select
    using (business_id = auth.get_business_id());
create policy "business read customers" on customers for select
    using (business_id = auth.get_business_id());
create policy "business read business_days" on business_days for select
    using (business_id = auth.get_business_id());
create policy "business read transactions" on transactions for select
    using (business_id = auth.get_business_id());
create policy "business read expenses" on expenses for select
    using (business_id = auth.get_business_id());
create policy "business read timeline" on timeline_events for select
    using (business_id = auth.get_business_id());
create policy "business read water_readings" on water_readings for select
    using (business_id = auth.get_business_id());

create policy "owner write products" on products for all
    using (business_id = auth.get_business_id() and auth.get_user_role() = 'owner');
create policy "owner write batches" on product_batches for all
    using (business_id = auth.get_business_id() and auth.get_user_role() = 'owner');

create policy "business write transactions" on transactions for insert
    with check (business_id = auth.get_business_id());
create policy "business write expenses" on expenses for insert
    with check (business_id = auth.get_business_id());
create policy "business write timeline" on timeline_events for insert
    with check (business_id = auth.get_business_id());
create policy "business write water_readings" on water_readings for all
    using (business_id = auth.get_business_id());
create policy "business write business_days" on business_days for all
    using (business_id = auth.get_business_id());
create policy "business write customers" on customers for all
    using (business_id = auth.get_business_id());

-- =====================================================================
-- STEP 9: Enable Realtime (safe — ignores if already added)
-- =====================================================================
do $$
begin
    alter publication supabase_realtime add table products;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table product_batches;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table customers;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table business_days;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table transactions;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table expenses;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table timeline_events;
exception when duplicate_object then null;
end $$;

do $$
begin
    alter publication supabase_realtime add table water_readings;
exception when duplicate_object then null;
end $$;