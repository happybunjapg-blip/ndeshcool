-- =====================================================================
-- AquaFlow Database Setup
-- =====================================================================
-- 
-- If this is a NEW Supabase project:
--   Run this entire file in Supabase SQL Editor.
--
-- If you ALREADY have operational data:
--   Run backend/supabase_migration.sql instead!
--   It will preserve all your existing data.
--
-- =====================================================================

-- ---- Businesses: every user belongs to exactly one business ----------
create table if not exists businesses (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_id uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now()
);

-- ---- Profiles: linked to auth.users, each user has one profile -------
create table if not exists profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique not null,
    first_name text not null,
    last_name text not null,
    phone text default '',
    role text not null check (role in ('owner', 'worker')),
    business_id uuid not null references businesses(id) on delete cascade,
    created_at timestamptz not null default now()
);

-- ---- Invitations: owner generates codes for workers to join ----------
create table if not exists invitations (
    code text primary key,
    business_id uuid not null references businesses(id) on delete cascade,
    email text default '',
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    is_invalidated boolean not null default false
);

-- ---- Products / inventory (FIFO batches live in a child table) ---------
create table if not exists products (
    name text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    category text not null check (category in ('bottle_water', 'accessory')),
    qty numeric not null default 0,
    threshold numeric not null default 0,
    selling_price numeric not null default 0,
    bottle_price numeric not null default 0,
    cost numeric not null default 0,
    updated_at timestamptz not null default now(),
    primary key (name, business_id)
);

create table if not exists product_batches (
    id bigint generated always as identity primary key,
    product_name text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    qty numeric not null,
    purchase_price numeric not null,
    purchase_date date not null default current_date,
    created_at timestamptz not null default now(),
    foreign key (product_name, business_id) references products(name, business_id) on delete cascade
);

-- ---- Customers: ONLY credit customers are ever stored here -------------
create table if not exists customers (
    id text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    name text not null,
    phone text default '',
    is_credit boolean not null default true,
    balance numeric not null default 0,
    notes text default '',
    last_purchase timestamptz,
    created_at timestamptz not null default now(),
    primary key (id, business_id)
);

-- ---- Business Day: only one row may have status = 'OPEN' per business ---
create table if not exists business_days (
    id text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    opened_at timestamptz not null default now(),
    opened_by text not null,
    status text not null default 'OPEN' check (status in ('OPEN', 'CLOSED')),
    opening_note text default '',
    closed_at timestamptz,
    closed_by text,
    closing_note text default '',
    primary key (id, business_id)
);

-- Enforce "only one OPEN business day per business" at the database level.
create unique index if not exists one_open_business_day_per_business
    on business_days (business_id, ((status)))
    where status = 'OPEN';

-- ---- Transactions: every sale, refill, delivery, payment ---------------
create table if not exists transactions (
    id text not null,
    business_id uuid not null references businesses(id) on delete cascade,
    type text not null check (type in (
        'water_refill', 'product_sale', 'bottle_water_sale',
        'bulk_delivery', 'customer_payment', 'expense'
    )),
    business_day_id text,
    date date not null default current_date,
    time text not null,
    amount numeric not null default 0,
    profit numeric not null default 0,
    customer_id text,
    details jsonb default '{}'::jsonb,
    created_by text,
    created_at timestamptz not null default now(),
    primary key (id, business_id)
);

-- ---- Expenses (daily/operational and capital) --------------------------
create table if not exists expenses (
    id bigint generated always as identity primary key,
    business_id uuid not null references businesses(id) on delete cascade,
    description text not null,
    amount numeric not null,
    category text default 'Other',
    is_capital boolean not null default false,
    business_day_id text,
    date date not null default current_date,
    time text not null,
    created_at timestamptz not null default now()
);

-- ---- Timeline / audit log ------------------------------------------------
create table if not exists timeline_events (
    id bigint generated always as identity primary key,
    business_id uuid not null references businesses(id) on delete cascade,
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
    date date not null,
    business_id uuid not null references businesses(id) on delete cascade,
    initial numeric not null default 0,
    final numeric not null default 0,
    cleaning numeric not null default 0,
    sold_water numeric not null default 0,
    primary key (date, business_id)
);

-- =====================================================================
-- Row Level Security
-- =====================================================================
alter table businesses enable row level security;
alter table profiles enable row level security;
alter table invitations enable row level security;
alter table products enable row level security;
alter table product_batches enable row level security;
alter table customers enable row level security;
alter table business_days enable row level security;
alter table transactions enable row level security;
alter table expenses enable row level security;
alter table timeline_events enable row level security;
alter table water_readings enable row level security;

-- Users can read their own business's data
create policy "users read own business" on businesses
    for select using (id in (select business_id from profiles where id = auth.uid()));

-- Users can read their own profile
create policy "self read" on profiles
    for select using (auth.uid() = id);

-- Users can update their own profile
create policy "self update" on profiles
    for update using (auth.uid() = id);

-- Business owners can read all profiles in their business
create policy "owner read profiles" on profiles
    for select using (
        business_id in (select business_id from profiles where id = auth.uid() and role = 'owner')
    );

-- Invitations: owners can manage, workers can read valid ones
create policy "owner manage invitations" on invitations
    for all using (
        business_id in (select business_id from profiles where id = auth.uid() and role = 'owner')
    );

create policy "worker read invitations" on invitations
    for select using (is_invalidated = false and expires_at > now());

-- Every authenticated user can read operational data for their business
create policy "business read products" on products for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read batches" on product_batches for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read customers" on customers for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read business_days" on business_days for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read transactions" on transactions for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read expenses" on expenses for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read timeline" on timeline_events for select
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business read water_readings" on water_readings for select
    using (business_id in (select business_id from profiles where id = auth.uid()));

-- Owners can write to products, batches, customers
create policy "owner write products" on products for all
    using (business_id in (select business_id from profiles where id = auth.uid() and role = 'owner'));
create policy "owner write batches" on product_batches for all
    using (business_id in (select business_id from profiles where id = auth.uid() and role = 'owner'));

-- Any authenticated user in the business can write transactions/expenses/timeline/water
create policy "business write transactions" on transactions for insert
    with check (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business write expenses" on expenses for insert
    with check (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business write timeline" on timeline_events for insert
    with check (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business write water_readings" on water_readings for all
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business write business_days" on business_days for all
    using (business_id in (select business_id from profiles where id = auth.uid()));
create policy "business write customers" on customers for all
    using (business_id in (select business_id from profiles where id = auth.uid()));

-- =====================================================================
-- Enable Realtime
-- =====================================================================
alter publication supabase_realtime add table products;
alter publication supabase_realtime add table product_batches;
alter publication supabase_realtime add table customers;
alter publication supabase_realtime add table business_days;
alter publication supabase_realtime add table transactions;
alter publication supabase_realtime add table expenses;
alter publication supabase_realtime add table timeline_events;
alter publication supabase_realtime add table water_readings;