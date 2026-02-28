-- ============================================================
-- OfferTracker – Supabase schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

-- Enable the uuid-ossp extension (usually already enabled on Supabase)
create extension if not exists "uuid-ossp";

-- -------------------------------------------------------
-- resume_versions
-- -------------------------------------------------------
create table if not exists resume_versions (
    id           text primary key default uuid_generate_v4()::text,
    version_name varchar(50)  not null,
    notes        text,
    file_url     varchar(500),
    created_at   timestamptz  not null default now(),
    updated_at   timestamptz  not null default now()
);

create index if not exists idx_resume_versions_version_name
    on resume_versions (version_name);

-- -------------------------------------------------------
-- applications
-- -------------------------------------------------------
create table if not exists applications (
    id                 text primary key default uuid_generate_v4()::text,
    company_name       varchar(255) not null,
    role_title         varchar(255) not null,
    applied_source     varchar(255),
    url                varchar(500),
    description        text,
    resume_version_id  text references resume_versions(id) on delete set null,
    status             varchar(50)  not null default 'Applied',
    applied_date       date         not null default current_date,
    created_at         timestamptz  not null default now(),
    updated_at         timestamptz  not null default now()
);

create index if not exists idx_applications_company_name on applications (company_name);
create index if not exists idx_applications_role_title   on applications (role_title);

-- -------------------------------------------------------
-- application_stages
-- -------------------------------------------------------
create table if not exists application_stages (
    id              text primary key default uuid_generate_v4()::text,
    application_id  text not null references applications(id) on delete cascade,
    stage_name      varchar(100) not null,
    stage_date      date         not null default current_date,
    notes           text,
    created_at      timestamptz  not null default now(),
    updated_at      timestamptz  not null default now()
);

-- -------------------------------------------------------
-- outcomes  (one-to-one with applications)
-- -------------------------------------------------------
create table if not exists outcomes (
    id               text primary key default uuid_generate_v4()::text,
    application_id   text not null unique references applications(id) on delete cascade,
    status           varchar(50) not null,   -- Offer, Rejected, Withdrawn
    rejection_reason text,
    notes            text,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

-- -------------------------------------------------------
-- reflections  (one-to-one with applications)
-- -------------------------------------------------------
create table if not exists reflections (
    id               text primary key default uuid_generate_v4()::text,
    application_id   text not null unique references applications(id) on delete cascade,
    what_worked      text,
    what_failed      text,
    skill_gaps       jsonb,
    improvement_plan text,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

-- -------------------------------------------------------
-- Auto-update updated_at via trigger
-- -------------------------------------------------------
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Attach trigger to every table
do $$
declare
    tbl text;
begin
    for tbl in
        select unnest(array[
            'resume_versions',
            'applications',
            'application_stages',
            'outcomes',
            'reflections'
        ])
    loop
        execute format(
            'drop trigger if exists trg_updated_at on %I; '
            'create trigger trg_updated_at before update on %I '
            'for each row execute function update_updated_at_column();',
            tbl, tbl
        );
    end loop;
end;
$$;

-- -------------------------------------------------------
-- Row-Level Security (RLS)
-- By default Supabase enables RLS on new tables.
-- For development with the anon/service_role key, allow all.
-- Tighten these policies when you add authentication.
-- -------------------------------------------------------
alter table resume_versions   enable row level security;
alter table applications      enable row level security;
alter table application_stages enable row level security;
alter table outcomes          enable row level security;
alter table reflections       enable row level security;

-- Allow full access for authenticated & anon (development)
create policy "Allow all on resume_versions"   on resume_versions   for all using (true) with check (true);
create policy "Allow all on applications"      on applications      for all using (true) with check (true);
create policy "Allow all on application_stages" on application_stages for all using (true) with check (true);
create policy "Allow all on outcomes"          on outcomes          for all using (true) with check (true);
create policy "Allow all on reflections"       on reflections       for all using (true) with check (true);
