-- ============================================================
-- OfferTracker – Supabase schema  (v3)
-- A thoughtful career tracking platform for professionals.
-- Milestones, not medals. Progress, not points.
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

-- Enable extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- -------------------------------------------------------
-- users
-- -------------------------------------------------------
create table if not exists users (
    id                text primary key default uuid_generate_v4()::text,
    email             varchar(255) not null unique,
    username          varchar(50)  not null unique,
    display_name      varchar(100),
    password_hash     text         not null,
    bio               text,
    avatar_url        varchar(500),
    is_profile_public boolean      not null default false,
    streak_days       integer      not null default 0,
    last_active_date  date,
    created_at        timestamptz  not null default now(),
    updated_at        timestamptz  not null default now()
);

create index if not exists idx_users_email    on users (email);
create index if not exists idx_users_username on users (username);

-- -------------------------------------------------------
-- resume_versions  (belongs to a user)
-- -------------------------------------------------------
create table if not exists resume_versions (
    id           text primary key default uuid_generate_v4()::text,
    user_id      text         not null references users(id) on delete cascade,
    version_name varchar(50)  not null,
    notes        text,
    file_url     varchar(500),
    created_at   timestamptz  not null default now(),
    updated_at   timestamptz  not null default now()
);

create index if not exists idx_resume_versions_user_id      on resume_versions (user_id);
create index if not exists idx_resume_versions_version_name on resume_versions (version_name);

-- -------------------------------------------------------
-- applications  (belongs to a user)
-- -------------------------------------------------------
create table if not exists applications (
    id                 text primary key default uuid_generate_v4()::text,
    user_id            text         not null references users(id) on delete cascade,
    company_name       varchar(255) not null,
    role_title         varchar(255) not null,
    location           varchar(255),
    applied_source     varchar(255),
    url                varchar(500),
    description        text,
    resume_version_id  text references resume_versions(id) on delete set null,
    status             varchar(50)  not null default 'Applied',
    applied_date       date         not null default current_date,
    created_at         timestamptz  not null default now(),
    updated_at         timestamptz  not null default now()
);

create index if not exists idx_applications_user_id      on applications (user_id);
create index if not exists idx_applications_company_name on applications (company_name);
create index if not exists idx_applications_role_title   on applications (role_title);
create index if not exists idx_applications_status       on applications (status);

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

create index if not exists idx_application_stages_app_id on application_stages (application_id);

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
-- follows  (user follow system)
-- -------------------------------------------------------
create table if not exists follows (
    id           text primary key default uuid_generate_v4()::text,
    follower_id  text not null references users(id) on delete cascade,
    following_id text not null references users(id) on delete cascade,
    created_at   timestamptz not null default now(),
    unique(follower_id, following_id)
);

create index if not exists idx_follows_follower  on follows (follower_id);
create index if not exists idx_follows_following on follows (following_id);

-- -------------------------------------------------------
-- groups
-- -------------------------------------------------------
create table if not exists groups (
    id          text primary key default uuid_generate_v4()::text,
    name        varchar(100) not null,
    description text,
    created_by  text not null references users(id) on delete cascade,
    is_public   boolean      not null default true,
    created_at  timestamptz  not null default now(),
    updated_at  timestamptz  not null default now()
);

create index if not exists idx_groups_created_by on groups (created_by);

-- -------------------------------------------------------
-- group_members
-- -------------------------------------------------------
create table if not exists group_members (
    id        text primary key default uuid_generate_v4()::text,
    group_id  text not null references groups(id) on delete cascade,
    user_id   text not null references users(id) on delete cascade,
    role      varchar(20) not null default 'member',  -- admin, member
    joined_at timestamptz not null default now(),
    unique(group_id, user_id)
);

create index if not exists idx_group_members_group on group_members (group_id);
create index if not exists idx_group_members_user  on group_members (user_id);

-- -------------------------------------------------------
-- milestones  (thoughtful progress markers)
-- -------------------------------------------------------
create table if not exists milestones (
    id          text primary key default uuid_generate_v4()::text,
    name        varchar(100) not null unique,
    description text,
    criteria    jsonb   not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

-- -------------------------------------------------------
-- user_milestones
-- -------------------------------------------------------
create table if not exists user_milestones (
    id             text primary key default uuid_generate_v4()::text,
    user_id        text not null references users(id) on delete cascade,
    milestone_id   text not null references milestones(id) on delete cascade,
    reached_at     timestamptz not null default now(),
    unique(user_id, milestone_id)
);

create index if not exists idx_user_milestones_user on user_milestones (user_id);

-- -------------------------------------------------------
-- shared_posts  (journey sharing)
-- -------------------------------------------------------
create table if not exists shared_posts (
    id         text primary key default uuid_generate_v4()::text,
    user_id    text not null references users(id) on delete cascade,
    group_id   text references groups(id) on delete set null,
    post_type  varchar(30)  not null default 'update',  -- update, tip, milestone, question
    title      varchar(255),
    content    text         not null,
    is_public  boolean      not null default true,
    created_at timestamptz  not null default now(),
    updated_at timestamptz  not null default now()
);

create index if not exists idx_shared_posts_user  on shared_posts (user_id);
create index if not exists idx_shared_posts_group on shared_posts (group_id);

-- -------------------------------------------------------
-- post_reactions
-- -------------------------------------------------------
create table if not exists post_reactions (
    id         text primary key default uuid_generate_v4()::text,
    post_id    text not null references shared_posts(id) on delete cascade,
    user_id    text not null references users(id) on delete cascade,
    reaction   varchar(20) not null default 'like',
    created_at timestamptz not null default now(),
    unique(post_id, user_id, reaction)
);

create index if not exists idx_post_reactions_post on post_reactions (post_id);

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

-- Attach trigger to every table that has updated_at
do $$
declare
    tbl text;
begin
    for tbl in
        select unnest(array[
            'users',
            'resume_versions',
            'applications',
            'application_stages',
            'outcomes',
            'reflections',
            'groups',
            'shared_posts'
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
-- Seed milestones
-- Thoughtful, professional progress markers — no points, no emojis.
-- They acknowledge effort and consistency, not arbitrary scores.
-- -------------------------------------------------------
insert into milestones (name, description, criteria) values
    ('Getting Started',    'You created your account and took the first step.',                  '{"action": "register"}'),
    ('First Application',  'You applied to your first role. The journey begins.',                '{"action": "create_application", "count": 1}'),
    ('Building Momentum',  'Ten applications in. You are putting yourself out there.',           '{"action": "create_application", "count": 10}'),
    ('In the Zone',        'Twenty-five applications. Consistent effort pays off.',              '{"action": "create_application", "count": 25}'),
    ('Self-Reflective',    'You wrote your first reflection. Growth starts with honesty.',       '{"action": "create_reflection", "count": 1}'),
    ('Growth Mindset',     'Ten reflections. You are learning from every experience.',           '{"action": "create_reflection", "count": 10}'),
    ('One Week Strong',    'Seven consecutive days of activity. Consistency is key.',            '{"action": "streak", "days": 7}'),
    ('Thirty Day Streak',  'A full month of showing up. That takes real dedication.',            '{"action": "streak", "days": 30}'),
    ('Connected',          'You are following five people. Job searching is better together.',   '{"action": "follow", "count": 5}'),
    ('Part of a Circle',   'You joined your first group. Shared journeys go further.',          '{"action": "join_group", "count": 1}'),
    ('Sharing Insights',   'You shared your first post. Helping others helps you grow.',        '{"action": "create_post", "count": 1}'),
    ('Offer Received',     'You received a job offer. All the effort was worth it.',            '{"action": "outcome_offer", "count": 1}')
on conflict (name) do nothing;

-- -------------------------------------------------------
-- Row-Level Security (RLS)
-- -------------------------------------------------------
alter table users              enable row level security;
alter table resume_versions    enable row level security;
alter table applications       enable row level security;
alter table application_stages enable row level security;
alter table outcomes           enable row level security;
alter table reflections        enable row level security;
alter table follows            enable row level security;
alter table groups             enable row level security;
alter table group_members      enable row level security;
alter table milestones         enable row level security;
alter table user_milestones    enable row level security;
alter table shared_posts       enable row level security;
alter table post_reactions     enable row level security;

-- Allow full access for development (tighten when adding Supabase Auth / RLS per user)
create policy "Allow all on users"              on users              for all using (true) with check (true);
create policy "Allow all on resume_versions"    on resume_versions    for all using (true) with check (true);
create policy "Allow all on applications"       on applications       for all using (true) with check (true);
create policy "Allow all on application_stages" on application_stages for all using (true) with check (true);
create policy "Allow all on outcomes"           on outcomes           for all using (true) with check (true);
create policy "Allow all on reflections"        on reflections        for all using (true) with check (true);
create policy "Allow all on follows"            on follows            for all using (true) with check (true);
create policy "Allow all on groups"             on groups             for all using (true) with check (true);
create policy "Allow all on group_members"      on group_members      for all using (true) with check (true);
create policy "Allow all on milestones"         on milestones         for all using (true) with check (true);
create policy "Allow all on user_milestones"    on user_milestones    for all using (true) with check (true);
create policy "Allow all on shared_posts"       on shared_posts       for all using (true) with check (true);
create policy "Allow all on post_reactions"     on post_reactions     for all using (true) with check (true);

-- -------------------------------------------------------
-- Supabase Storage bucket for resume uploads
-- Create via Supabase Dashboard: Storage → New Bucket → "resumes"
-- -------------------------------------------------------
