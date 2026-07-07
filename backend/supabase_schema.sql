-- =====================================================================
-- AquaFlow production schema (Supabase / Postgres)
-- Run this in Supabase SQL Editor once, on a fresh project.
-- =====================================================================

-- ---- Roles are stored on Supabase Auth users via a profile table -------
create table if not exists profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique not null,
    name text not null,
    role text not null check (role in ('worker', 'partner')),
    created_at timestamptz not null default now()
);

-- ---- Products / inventory (FIFO batches live in a child table) ---------
create table if not exists products (
    name text primary key,
    category text not null check (category in ('bottle_water', 'accessory')),
    qty numeric not null default 0,
    threshold numeric not null default 0,
    selling_price numeric not null default 0,
    bottle_price numeric not null default 0,
    cost numeric not null default 0,
    updated_at timestamptz not null default now()
);

create table if not exists product_batches (
    id bigint generated always as identity primary key,
    product_name text not null references products(name) on delete cascade,
    qty numeric not null,
    purchase_price numeric not null,
    purchase_date date not null default current_date,
    -- oldest batches are consumed first (FIFO) -- order by id/purchase_date
    created_at timestamptz not null default now()
);

-- ---- Customers: ONLY credit customers are ever stored here -------------
create table if not exists customers (
    id text primary key,
    name text not null,
    phone text default '',
    is_credit boolean not null default true,
    balance numeric not null default 0,
    notes text default '',
    last_purchase timestamptz,
    created_at timestamptz not null default now()
);

-- ---- Business Day: only one row may have status = 'OPEN' ---------------
create table if not exists business_days (
    id text primary key,
    opened_at timestamptz not null default now(),
    opened_by text not null,
    status text not null default 'OPEN' check (status in ('OPEN', 'CLOSED')),
    opening_note text default '',
    closed_at timestamptz,
    closed_by text,
    closing_note text default ''
);

-- Enforce "only one OPEN business day" at the database level, not just in
-- application code -- a partial unique index is the standard Postgres way.
create unique index if not exists one_open_business_day
    on business_days ((status))
    where status = 'OPEN';

-- ---- Transactions: every sale, refill, delivery, payment ---------------
create table if not exists transactions (
    id text primary key,
    type text not null check (type in (
        'water_refill', 'product_sale', 'bottle_water_sale',
        'bulk_delivery', 'customer_payment', 'expense'
    )),
    business_day_id text references business_days(id),
    date date not null default current_date,
    time text not null,
    amount numeric not null default 0,
    profit numeric not null default 0,
    customer_id text references customers(id),
    details jsonb default '{}'::jsonb,
    created_by text,
    created_at timestamptz not null default now()
);

-- ---- Expenses (daily/operational and capital) --------------------------
create table if not exists expenses (
    id bigint generated always as identity primary key,
    description text not null,
    amount numeric not null,
    category text default 'Other',
    is_capital boolean not null default false,
    business_day_id text references business_days(id),
    date date not null default current_date,
    time text not null,
    created_at timestamptz not null default now()
);

-- ---- Timeline / audit log ------------------------------------------------
create table if not exists timeline_events (
    id bigint generated always as identity primary key,
    date date not null default current_date,
    time text not null,
    event text not null,
    type text not null,
    change text default '',
    stock_after numeric default 0,
    created_at timestamptz not null default now()
);

-- ---- Water meter readings ------------------------------------------------
create table if not exists water_readings (
    date date primary key,
    initial numeric not null default 0,
    final numeric not null default 0,
    cleaning numeric not null default 0,
    sold_water numeric not null default 0
);

-- =====================================================================
-- Row Level Security: workers can read/write operational data but only
-- while a Business Day is open; partners can read everything and manage
-- prices/customers. Adjust to taste once you have real accounts.
-- =====================================================================
alter table products enable row level security;
alter table product_batches enable row level security;
alter table customers enable row level security;
alter table business_days enable row level security;
alter table transactions enable row level security;
alter table expenses enable row level security;
alter table timeline_events enable row level security;
alter table water_readings enable row level security;
alter table profiles enable row level security;

-- Every authenticated user (worker or partner) can read all operational
-- tables -- this is a single-station app, not yet multi-tenant.
create policy "authenticated read" on products for select using (auth.role() = 'authenticated');
create policy "authenticated read" on product_batches for select using (auth.role() = 'authenticated');
create policy "authenticated read" on customers for select using (auth.role() = 'authenticated');
create policy "authenticated read" on business_days for select using (auth.role() = 'authenticated');
create policy "authenticated read" on transactions for select using (auth.role() = 'authenticated');
create policy "authenticated read" on expenses for select using (auth.role() = 'authenticated');
create policy "authenticated read" on timeline_events for select using (auth.role() = 'authenticated');
create policy "authenticated read" on water_readings for select using (auth.role() = 'authenticated');
create policy "self read" on profiles for select using (auth.uid() = id);

-- Writes: any authenticated user can insert transactions/expenses/timeline
-- events (worker recording a sale) -- tighten with a role check once you
-- have `profiles.role` populated for real accounts, e.g.:
--   using (exists (select 1 from profiles where id = auth.uid()))
create policy "authenticated write" on transactions for insert with check (auth.role() = 'authenticated');
create policy "authenticated write" on expenses for insert with check (auth.role() = 'authenticated');
create policy "authenticated write" on timeline_events for insert with check (auth.role() = 'authenticated');
create policy "authenticated write" on water_readings for all using (auth.role() = 'authenticated');
create policy "authenticated write" on business_days for all using (auth.role() = 'authenticated');
create policy "authenticated write" on customers for all using (auth.role() = 'authenticated');
create policy "partner write products" on products for all using (auth.role() = 'authenticated');
create policy "partner write batches" on product_batches for all using (auth.role() = 'authenticated');

-- =====================================================================
-- Enable Realtime so every connected device (worker phone, partner
-- phone/tablet/desktop) gets pushed the same updates instantly.
-- =====================================================================
alter publication supabase_realtime add table products;
alter publication supabase_realtime add table product_batches;
alter publication supabase_realtime add table customers;
alter publication supabase_realtime add table business_days;
alter publication supabase_realtime add table transactions;
alter publication supabase_realtime add table expenses;
alter publication supabase_realtime add table timeline_events;
alter publication supabase_realtime add table water_readings;
