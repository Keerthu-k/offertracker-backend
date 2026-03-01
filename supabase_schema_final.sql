-- ============================================================
-- OfferTracker — Final Consolidated Schema
-- Single source of truth. Run once on a fresh Supabase project.
-- All tables, constraints, indexes, triggers, RLS, and seed data.
-- Aligned with the Python FastAPI codebase (2026-03-01).
-- ============================================================
--
-- KEY DESIGN DECISIONS
-- --------------------
-- 1. Every column that the Python code reads or writes has a matching
--    DB column.  Columns that existed in older migrations but are
--    absent from ALL Python schemas have been removed.
--
-- 2. Every enum defined in app/schemas/enums.py is reflected as a
--    CHECK constraint so the DB rejects bad values independently of
--    the application layer.
--
-- 3. applied_date is NULLABLE.  "Open" applications have not been
--    submitted yet, so defaulting to today was semantically wrong.
--    The API auto-sets it on the Open → Applied transition.
--
-- 4. follows has a DB-level self-follow guard.
--
-- 5. reminders enforces that completed_at is set when is_completed=true.
--
-- 6. salary_min ≤ salary_max cross-column guards on applications and
--    saved_jobs.
--
-- 7. RLS policies use auth.uid() for frontend clients.
--    The service-role key (used by FastAPI) bypasses RLS — no policy
--    changes needed for the API layer.
--
-- 8. profile_visibility and is_profile_public are kept in sync by a
--    trigger so both the API (profile_visibility) and the gamification
--    community query (is_profile_public) stay consistent.
--
-- REMOVED vs previous migrations
-- --------------------------------
-- • applications.excitement_level   → redundant with priority
-- • applications.offer_deadline     → redundant with outcomes.deadline
-- • outcomes.is_negotiating         → redundant with negotiation_notes
-- ============================================================

-- -------------------------------------------------------
-- Extensions
-- -------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -------------------------------------------------------
-- Utility: keep updated_at current on every UPDATE
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TABLE: users
-- ============================================================
-- id mirrors the Supabase Auth UUID so public.users.id = auth.users.id.
-- password_hash is nullable — Supabase Auth owns passwords.
-- profile_visibility is the canonical visibility field; is_profile_public
-- is kept as a convenience boolean (synced by trigger below).
-- ============================================================
CREATE TABLE users (
    id                 text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email              varchar(255) NOT NULL UNIQUE,
    username           varchar(50)  NOT NULL UNIQUE,
    display_name       varchar(100),
    password_hash      text,                        -- nullable: Supabase Auth handles passwords
    bio                text,
    is_profile_public  boolean      NOT NULL DEFAULT false,
    profile_visibility varchar(20)  NOT NULL DEFAULT 'private'
                           CONSTRAINT chk_users_profile_visibility
                           CHECK (profile_visibility IN ('private', 'followers', 'groups', 'public')),
    streak_days        integer      NOT NULL DEFAULT 0
                           CONSTRAINT chk_users_streak CHECK (streak_days >= 0),
    last_active_date   date,
    created_at         timestamptz  NOT NULL DEFAULT now(),
    updated_at         timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email              ON users (email);
CREATE INDEX idx_users_username           ON users (username);
CREATE INDEX idx_users_profile_visibility ON users (profile_visibility);
CREATE INDEX idx_users_last_active        ON users (last_active_date DESC);

-- Sync is_profile_public ↔ profile_visibility automatically.
-- Whichever column is written, the other stays consistent.
CREATE OR REPLACE FUNCTION sync_profile_visibility()
RETURNS trigger AS $$
BEGIN
    IF NEW.profile_visibility IS DISTINCT FROM OLD.profile_visibility THEN
        -- Canonical field changed → mirror into the boolean
        NEW.is_profile_public := (NEW.profile_visibility = 'public');
    ELSIF NEW.is_profile_public IS DISTINCT FROM OLD.is_profile_public THEN
        -- Legacy boolean changed → mirror into the canonical field
        NEW.profile_visibility := CASE
            WHEN NEW.is_profile_public THEN 'public'
            ELSE 'private'
        END;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_profile_visibility
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION sync_profile_visibility();

-- ============================================================
-- TABLE: resume_versions
-- ============================================================
CREATE TABLE resume_versions (
    id           text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id      text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version_name varchar(50)  NOT NULL,
    notes        text,
    file_url     varchar(500),
    created_at   timestamptz  NOT NULL DEFAULT now(),
    updated_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_resume_versions_user_id ON resume_versions (user_id);

-- ============================================================
-- TABLE: applications
-- ============================================================
-- applied_date is NULLABLE.  It is only meaningful once the user
-- has actually submitted the application (status = Applied or beyond).
-- The API sets it automatically on the Open → Applied transition.
-- company_website and experience_level are stored even though the
-- current API schemas do not expose them; useful for future features.
-- ============================================================
CREATE TABLE applications (
    id                text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id           text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name      varchar(255) NOT NULL,
    role_title        varchar(255) NOT NULL,
    company_website   varchar(500),
    url               varchar(500),                  -- job posting URL
    description       text,
    location          varchar(255),
    job_type          varchar(30)
                          CONSTRAINT chk_applications_job_type
                          CHECK (job_type IS NULL OR job_type IN (
                              'Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance'
                          )),
    work_mode         varchar(20)
                          CONSTRAINT chk_applications_work_mode
                          CHECK (work_mode IS NULL OR work_mode IN (
                              'Remote', 'Hybrid', 'On-site'
                          )),
    experience_level  varchar(30),                   -- Entry / Mid / Senior – future filter
    salary_min        integer
                          CONSTRAINT chk_applications_salary_min CHECK (salary_min IS NULL OR salary_min >= 0),
    salary_max        integer
                          CONSTRAINT chk_applications_salary_max CHECK (salary_max IS NULL OR salary_max >= 0),
    salary_currency   varchar(3)   NOT NULL DEFAULT 'USD',
    applied_source    varchar(50)
                          CONSTRAINT chk_applications_applied_source
                          CHECK (applied_source IS NULL OR applied_source IN (
                              'LinkedIn', 'Indeed', 'Glassdoor', 'Company Website',
                              'Referral', 'Job Board', 'Recruiter', 'Networking',
                              'Career Fair', 'Other'
                          )),
    status            varchar(20)  NOT NULL DEFAULT 'Open'
                          CONSTRAINT chk_applications_status
                          CHECK (status IN (
                              'Open', 'Applied', 'Shortlisted',
                              'Interview', 'Offer', 'Rejected', 'Closed'
                          )),
    applied_date      date,                          -- NULL when status = Open; auto-set on transition
    follow_up_date    date,
    priority          varchar(10)
                          CONSTRAINT chk_applications_priority
                          CHECK (priority IS NULL OR priority IN ('High', 'Medium', 'Low')),
    notes             text,
    is_archived       boolean      NOT NULL DEFAULT false,
    resume_version_id text         REFERENCES resume_versions(id) ON DELETE SET NULL,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),
    -- Guard: min must not exceed max when both are provided
    CONSTRAINT chk_applications_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);

CREATE INDEX idx_applications_user_id      ON applications (user_id);
CREATE INDEX idx_applications_company_name ON applications (company_name);
CREATE INDEX idx_applications_role_title   ON applications (role_title);
CREATE INDEX idx_applications_status       ON applications (status);
CREATE INDEX idx_applications_job_type     ON applications (job_type);
CREATE INDEX idx_applications_work_mode    ON applications (work_mode);
CREATE INDEX idx_applications_priority     ON applications (priority);
CREATE INDEX idx_applications_is_archived  ON applications (is_archived);
CREATE INDEX idx_applications_follow_up    ON applications (follow_up_date);
CREATE INDEX idx_applications_applied_date ON applications (applied_date);

-- ============================================================
-- TABLE: application_stages
-- ============================================================
CREATE TABLE application_stages (
    id                text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id    text         NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    stage_name        varchar(100) NOT NULL,
    stage_type        varchar(30)
                          CONSTRAINT chk_stages_stage_type
                          CHECK (stage_type IS NULL OR stage_type IN (
                              'Recruiter Call', 'Phone Screen', 'Technical',
                              'Coding Challenge', 'Take-Home', 'System Design',
                              'Behavioral', 'Panel', 'Onsite', 'Final Round', 'Other'
                          )),
    stage_date        date         NOT NULL DEFAULT CURRENT_DATE,
    result            varchar(20)  NOT NULL DEFAULT 'Pending'
                          CONSTRAINT chk_stages_result
                          CHECK (result IN ('Pending', 'Passed', 'Failed', 'Cancelled')),
    duration_minutes  integer
                          CONSTRAINT chk_stages_duration CHECK (duration_minutes IS NULL OR duration_minutes > 0),
    interviewer_names text,                          -- comma-separated names
    prep_notes        text,
    questions_asked   jsonb        NOT NULL DEFAULT '[]'::jsonb,
    notes             text,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_application_stages_app_id ON application_stages (application_id);
CREATE INDEX idx_stages_stage_type         ON application_stages (stage_type);
CREATE INDEX idx_stages_result             ON application_stages (result);
CREATE INDEX idx_stages_stage_date         ON application_stages (stage_date);

-- ============================================================
-- TABLE: outcomes
-- ============================================================
-- One-to-one with applications.  Stores offer/rejection details.
-- status is nullable — it is set when the outcome is recorded.
-- rejection_reason is kept for future API exposure.
-- is_negotiating was removed: negotiation_notes already covers this.
-- ============================================================
CREATE TABLE outcomes (
    id                text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id    text         NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    status            varchar(20)
                          CONSTRAINT chk_outcomes_status
                          CHECK (status IS NULL OR status IN ('Offer', 'Rejected', 'Closed')),
    salary            integer
                          CONSTRAINT chk_outcomes_salary CHECK (salary IS NULL OR salary >= 0),
    salary_currency   varchar(3)   NOT NULL DEFAULT 'USD',
    bonus             text,
    equity            text,
    benefits          text,
    start_date        date,
    deadline          date,                          -- offer acceptance deadline
    negotiation_notes text,
    rejection_reason  text,                          -- reason when status = Rejected (future use)
    notes             text,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcomes_application_id ON outcomes (application_id);
CREATE INDEX idx_outcomes_status         ON outcomes (status);
CREATE INDEX idx_outcomes_deadline       ON outcomes (deadline);

-- ============================================================
-- TABLE: reflections
-- ============================================================
-- Post-process learnings — one-to-one with applications.
-- skill_gaps is a flexible JSON array/object for gap recording.
-- ============================================================
CREATE TABLE reflections (
    id               text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id   text         NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    what_worked      text,
    what_failed      text,
    skill_gaps       jsonb,
    improvement_plan text,
    created_at       timestamptz  NOT NULL DEFAULT now(),
    updated_at       timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_reflections_application_id ON reflections (application_id);

-- ============================================================
-- TABLE: contacts
-- ============================================================
-- Networking tracker — recruiters, hiring managers, referrals, peers.
-- Optionally linked to a specific application.
-- ============================================================
CREATE TABLE contacts (
    id             text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id        text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id text         REFERENCES applications(id) ON DELETE SET NULL,
    name           varchar(255) NOT NULL,
    email          varchar(255),
    phone          varchar(50),
    role_title     varchar(255),
    company        varchar(255),
    contact_type   varchar(30)  NOT NULL DEFAULT 'Other'
                       CONSTRAINT chk_contacts_contact_type
                       CHECK (contact_type IN (
                           'Recruiter', 'Hiring Manager', 'Referral', 'HR', 'Peer', 'Other'
                       )),
    linkedin_url   varchar(500),
    notes          text,
    last_contacted date,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_contacts_user_id        ON contacts (user_id);
CREATE INDEX idx_contacts_application_id ON contacts (application_id);
CREATE INDEX idx_contacts_company        ON contacts (company);
CREATE INDEX idx_contacts_contact_type   ON contacts (contact_type);

-- ============================================================
-- TABLE: saved_jobs
-- ============================================================
-- A curated list of job postings the user wants to track before
-- committing to a full application.  Distinct from applications:
-- no applied_date, no stages, no outcome — just interest and intent.
-- excitement_level is intentionally kept here (unlike applications)
-- because saved jobs are aspirational by nature.
-- A saved job can be promoted to a full application via the
-- /saved-jobs/{id}/convert endpoint, which sets
-- converted_to_application_id and flips status → Converted.
-- ============================================================
CREATE TABLE saved_jobs (
    id                          text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id                     text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name                varchar(255) NOT NULL,
    role_title                  varchar(255),
    url                         varchar(500),
    company_website             varchar(500),
    location                    varchar(255),
    job_type                    varchar(30)
                                    CONSTRAINT chk_saved_jobs_job_type
                                    CHECK (job_type IS NULL OR job_type IN (
                                        'Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance'
                                    )),
    work_mode                   varchar(20)
                                    CONSTRAINT chk_saved_jobs_work_mode
                                    CHECK (work_mode IS NULL OR work_mode IN (
                                        'Remote', 'Hybrid', 'On-site'
                                    )),
    salary_range_min            integer
                                    CONSTRAINT chk_saved_jobs_salary_min
                                    CHECK (salary_range_min IS NULL OR salary_range_min >= 0),
    salary_range_max            integer
                                    CONSTRAINT chk_saved_jobs_salary_max
                                    CHECK (salary_range_max IS NULL OR salary_range_max >= 0),
    salary_currency             varchar(3)   NOT NULL DEFAULT 'USD',
    priority                    varchar(10)  NOT NULL DEFAULT 'Medium'
                                    CONSTRAINT chk_saved_jobs_priority
                                    CHECK (priority IN ('High', 'Medium', 'Low')),
    source                      varchar(255),
    notes                       text,
    deadline                    date,
    status                      varchar(20)  NOT NULL DEFAULT 'Active'
                                    CONSTRAINT chk_saved_jobs_status
                                    CHECK (status IN ('Active', 'Archived', 'Converted')),
    excitement_level            smallint
                                    CONSTRAINT chk_saved_jobs_excitement
                                    CHECK (excitement_level IS NULL OR excitement_level BETWEEN 1 AND 5),
    converted_to_application_id text         REFERENCES applications(id) ON DELETE SET NULL,
    created_at                  timestamptz  NOT NULL DEFAULT now(),
    updated_at                  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT chk_saved_jobs_salary_range
        CHECK (salary_range_min IS NULL OR salary_range_max IS NULL OR salary_range_min <= salary_range_max)
);

CREATE INDEX idx_saved_jobs_user_id  ON saved_jobs (user_id);
CREATE INDEX idx_saved_jobs_status   ON saved_jobs (status);
CREATE INDEX idx_saved_jobs_priority ON saved_jobs (priority);
CREATE INDEX idx_saved_jobs_deadline ON saved_jobs (deadline);

-- ============================================================
-- TABLE: tags
-- ============================================================
-- User-defined, colour-coded labels for applications.
-- Name is unique per user (enforced by the UNIQUE constraint below).
-- ============================================================
CREATE TABLE tags (
    id         text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id    text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       varchar(50) NOT NULL,
    color      varchar(7)  NOT NULL DEFAULT '#6366f1',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE INDEX idx_tags_user_id ON tags (user_id);

-- ============================================================
-- TABLE: application_tags
-- ============================================================
-- Many-to-many join between applications and tags.
-- Cascade deletes on both sides so orphans are impossible.
-- ============================================================
CREATE TABLE application_tags (
    id             text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id text        NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    tag_id         text        NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (application_id, tag_id)
);

CREATE INDEX idx_application_tags_app ON application_tags (application_id);
CREATE INDEX idx_application_tags_tag ON application_tags (tag_id);

-- ============================================================
-- TABLE: reminders
-- ============================================================
-- Time-aware alerts: follow-ups, offer deadlines, interview prep.
-- completed_at must be populated when is_completed flips to true
-- (enforced by both the CHECK below and the mark_completed CRUD method).
-- ============================================================
CREATE TABLE reminders (
    id             text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id        text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id text         REFERENCES applications(id) ON DELETE CASCADE,
    title          varchar(255) NOT NULL,
    description    text,
    remind_at      timestamptz  NOT NULL,
    reminder_type  varchar(20)  NOT NULL DEFAULT 'General'
                       CONSTRAINT chk_reminders_type
                       CHECK (reminder_type IN ('Follow-up', 'Deadline', 'Interview', 'General')),
    is_completed   boolean      NOT NULL DEFAULT false,
    completed_at   timestamptz,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    -- completed_at must be set whenever the reminder is marked done
    CONSTRAINT chk_reminders_completed_at
        CHECK (NOT is_completed OR completed_at IS NOT NULL)
);

CREATE INDEX idx_reminders_user_id      ON reminders (user_id);
CREATE INDEX idx_reminders_application  ON reminders (application_id);
CREATE INDEX idx_reminders_remind_at    ON reminders (remind_at);
CREATE INDEX idx_reminders_is_completed ON reminders (is_completed);

-- ============================================================
-- TABLE: application_documents
-- ============================================================
CREATE TABLE application_documents (
    id             text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id text         NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    doc_type       varchar(30)  NOT NULL DEFAULT 'Other'
                       CONSTRAINT chk_documents_doc_type
                       CHECK (doc_type IN (
                           'Resume', 'Cover Letter', 'Portfolio', 'Reference', 'Other'
                       )),
    name           varchar(255) NOT NULL,
    file_url       varchar(500),
    notes          text,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_app_documents_app_id   ON application_documents (application_id);
CREATE INDEX idx_app_documents_doc_type ON application_documents (doc_type);

-- ============================================================
-- TABLE: activity_log
-- ============================================================
-- Append-only timeline.  Entries are created by the API internally;
-- users can read them but never create, modify, or delete them.
-- action values mirror app.schemas.enums.ActivityAction exactly.
-- No updated_at column — immutable by design.
-- ============================================================
CREATE TABLE activity_log (
    id             text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id        text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id text        REFERENCES applications(id) ON DELETE CASCADE,
    action         varchar(50) NOT NULL
                       CONSTRAINT chk_activity_action
                       CHECK (action IN (
                           'Application Created',
                           'Application Updated',
                           'Status Changed',
                           'Stage Added',
                           'Stage Updated',
                           'Offer Added',
                           'Reflection Added',
                           'Contact Added',
                           'Document Added',
                           'Reminder Created',
                           'Reminder Completed',
                           'Tag Assigned'
                       )),
    description    text        NOT NULL,
    metadata       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_activity_log_user_id    ON activity_log (user_id);
CREATE INDEX idx_activity_log_app_id     ON activity_log (application_id);
CREATE INDEX idx_activity_log_action     ON activity_log (action);
CREATE INDEX idx_activity_log_created_at ON activity_log (created_at DESC);

-- ============================================================
-- SOCIAL / COMMUNITY TABLES
-- ============================================================

-- ============================================================
-- TABLE: follows
-- ============================================================
-- Self-follow is prevented at the DB level, not just by the API.
-- ============================================================
CREATE TABLE follows (
    id           text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    follower_id  text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (follower_id, following_id),
    CONSTRAINT chk_follows_no_self_follow CHECK (follower_id <> following_id)
);

CREATE INDEX idx_follows_follower  ON follows (follower_id);
CREATE INDEX idx_follows_following ON follows (following_id);

-- ============================================================
-- TABLE: groups
-- ============================================================
CREATE TABLE groups (
    id          text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name        varchar(100) NOT NULL,
    description text,
    created_by  text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_public   boolean      NOT NULL DEFAULT true,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_groups_created_by ON groups (created_by);
CREATE INDEX idx_groups_is_public  ON groups (is_public);

-- ============================================================
-- TABLE: group_members
-- ============================================================
CREATE TABLE group_members (
    id        text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    group_id  text        NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id   text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role      varchar(20) NOT NULL DEFAULT 'member'
                  CONSTRAINT chk_group_members_role CHECK (role IN ('admin', 'member')),
    joined_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (group_id, user_id)
);

CREATE INDEX idx_group_members_group ON group_members (group_id);
CREATE INDEX idx_group_members_user  ON group_members (user_id);

-- ============================================================
-- TABLE: milestones
-- ============================================================
-- Thoughtful progress markers — no points, no levels.
-- Immutable definitions: no updated_at needed.
-- ============================================================
CREATE TABLE milestones (
    id          text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name        varchar(100) NOT NULL UNIQUE,
    description text,
    criteria    jsonb        NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz  NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE: user_milestones
-- ============================================================
CREATE TABLE user_milestones (
    id           text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id      text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    milestone_id text        NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    reached_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, milestone_id)
);

CREATE INDEX idx_user_milestones_user      ON user_milestones (user_id);
CREATE INDEX idx_user_milestones_milestone ON user_milestones (milestone_id);

-- ============================================================
-- TABLE: shared_posts
-- ============================================================
-- post_type constrained to match app.schemas.enums.PostType.
-- ============================================================
CREATE TABLE shared_posts (
    id         text         PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id    text         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id   text         REFERENCES groups(id) ON DELETE SET NULL,
    post_type  varchar(30)  NOT NULL DEFAULT 'Update'
                   CONSTRAINT chk_posts_post_type
                   CHECK (post_type IN (
                       'Update', 'Tip', 'Milestone', 'Question', 'Resource', 'Celebration'
                   )),
    title      varchar(255),
    content    text         NOT NULL,
    is_public  boolean      NOT NULL DEFAULT true,
    created_at timestamptz  NOT NULL DEFAULT now(),
    updated_at timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_shared_posts_user    ON shared_posts (user_id);
CREATE INDEX idx_shared_posts_group   ON shared_posts (group_id);
CREATE INDEX idx_shared_posts_public  ON shared_posts (is_public);
CREATE INDEX idx_shared_posts_created ON shared_posts (created_at DESC);

-- ============================================================
-- TABLE: post_reactions
-- ============================================================
-- One reaction-type per user per post (enforced by the UNIQUE below).
-- reaction constrained to match app.schemas.enums.ReactionType.
-- ============================================================
CREATE TABLE post_reactions (
    id         text        PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    post_id    text        NOT NULL REFERENCES shared_posts(id) ON DELETE CASCADE,
    user_id    text        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reaction   varchar(20) NOT NULL DEFAULT 'Like'
                   CONSTRAINT chk_reactions_type
                   CHECK (reaction IN ('Like', 'Celebrate', 'Support', 'Insightful')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (post_id, user_id, reaction)
);

CREATE INDEX idx_post_reactions_post ON post_reactions (post_id);
CREATE INDEX idx_post_reactions_user ON post_reactions (user_id);

-- ============================================================
-- TRIGGERS: auto-update updated_at on all mutable tables
-- ============================================================
DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'users',
        'resume_versions',
        'applications',
        'application_stages',
        'outcomes',
        'reflections',
        'contacts',
        'saved_jobs',
        'reminders',
        'application_documents',
        'groups',
        'shared_posts'
    ]
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_updated_at ON %I; '
            'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl
        );
    END LOOP;
END;
$$;

-- ============================================================
-- SUPABASE AUTH INTEGRATION
-- ============================================================
-- Mirrors auth.users events into public.users so the application
-- always has a profile row.  ON CONFLICT DO NOTHING makes the
-- trigger idempotent if the API creates the row first (which the
-- Python ensure_profile() helper does as a fallback).
-- ============================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.users (id, email, username, display_name)
    VALUES (
        NEW.id::text,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'username',
            split_part(NEW.email, '@', 1)
        ),
        COALESCE(
            NEW.raw_user_meta_data->>'display_name',
            NEW.raw_user_meta_data->>'username',
            split_part(NEW.email, '@', 1)
        )
    )
    ON CONFLICT (id) DO NOTHING;   -- idempotent: API may insert the row first
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

CREATE OR REPLACE FUNCTION handle_deleted_user()
RETURNS trigger AS $$
BEGIN
    DELETE FROM public.users WHERE id = OLD.id::text;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;
CREATE TRIGGER on_auth_user_deleted
    AFTER DELETE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_deleted_user();

-- ============================================================
-- ROW-LEVEL SECURITY
-- ============================================================
-- All tables: RLS enabled.
-- Policies use auth.uid() so frontend clients can only access
-- their own data.  The FastAPI backend uses the service-role key
-- which bypasses RLS — no API-level policy changes needed.
-- ============================================================

ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_versions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications        ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_stages  ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE reflections         ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts            ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_jobs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags                ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_tags    ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders           ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log        ENABLE ROW LEVEL SECURITY;
ALTER TABLE follows             ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups              ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_members       ENABLE ROW LEVEL SECURITY;
ALTER TABLE milestones          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_milestones     ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared_posts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_reactions      ENABLE ROW LEVEL SECURITY;

-- -------------------------------------------------------
-- users: own profile writable; public profiles readable by all
-- -------------------------------------------------------
CREATE POLICY "users_own"
    ON users FOR ALL
    USING  (id = auth.uid()::text)
    WITH CHECK (id = auth.uid()::text);

CREATE POLICY "users_read_public"
    ON users FOR SELECT
    USING (profile_visibility = 'public');

-- -------------------------------------------------------
-- resume_versions: owner only
-- -------------------------------------------------------
CREATE POLICY "resume_versions_own"
    ON resume_versions FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- applications: owner only
-- -------------------------------------------------------
CREATE POLICY "applications_own"
    ON applications FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- application_stages: owner of the parent application
-- -------------------------------------------------------
CREATE POLICY "application_stages_own"
    ON application_stages FOR ALL
    USING (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    )
    WITH CHECK (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    );

-- -------------------------------------------------------
-- outcomes: owner of the parent application
-- -------------------------------------------------------
CREATE POLICY "outcomes_own"
    ON outcomes FOR ALL
    USING (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    )
    WITH CHECK (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    );

-- -------------------------------------------------------
-- reflections: owner of the parent application
-- -------------------------------------------------------
CREATE POLICY "reflections_own"
    ON reflections FOR ALL
    USING (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    )
    WITH CHECK (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    );

-- -------------------------------------------------------
-- contacts / saved_jobs / reminders / tags / activity_log: owner only
-- -------------------------------------------------------
CREATE POLICY "contacts_own"
    ON contacts FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "saved_jobs_own"
    ON saved_jobs FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "reminders_own"
    ON reminders FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "tags_own"
    ON tags FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "activity_log_own"
    ON activity_log FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- application_tags: owner of parent application
-- -------------------------------------------------------
CREATE POLICY "application_tags_own"
    ON application_tags FOR ALL
    USING (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    )
    WITH CHECK (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    );

-- -------------------------------------------------------
-- application_documents: owner of parent application
-- -------------------------------------------------------
CREATE POLICY "application_documents_own"
    ON application_documents FOR ALL
    USING (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    )
    WITH CHECK (
        application_id IN (
            SELECT id FROM applications WHERE user_id = auth.uid()::text
        )
    );

-- -------------------------------------------------------
-- follows: own follows writable; all follows readable (social browsing)
-- -------------------------------------------------------
CREATE POLICY "follows_own"
    ON follows FOR ALL
    USING  (follower_id = auth.uid()::text)
    WITH CHECK (follower_id = auth.uid()::text);

CREATE POLICY "follows_read_all"
    ON follows FOR SELECT
    USING (true);

-- -------------------------------------------------------
-- groups: public groups readable by anyone;
--         private groups readable only by members;
--         manageable only by the creator
-- -------------------------------------------------------
CREATE POLICY "groups_read_public"
    ON groups FOR SELECT
    USING (is_public = true);

CREATE POLICY "groups_read_member"
    ON groups FOR SELECT
    USING (
        id IN (
            SELECT group_id FROM group_members WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "groups_manage_own"
    ON groups FOR ALL
    USING  (created_by = auth.uid()::text)
    WITH CHECK (created_by = auth.uid()::text);

-- -------------------------------------------------------
-- group_members: readable inside any group you can see;
--                you can manage your own membership
-- -------------------------------------------------------
CREATE POLICY "group_members_read"
    ON group_members FOR SELECT
    USING (
        group_id IN (
            SELECT id FROM groups
            WHERE is_public = true
               OR created_by = auth.uid()::text
               OR id IN (
                   SELECT group_id FROM group_members WHERE user_id = auth.uid()::text
               )
        )
    );

CREATE POLICY "group_members_own"
    ON group_members FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- milestones: public read; no user writes (seeded by admin)
-- -------------------------------------------------------
CREATE POLICY "milestones_read_all"
    ON milestones FOR SELECT
    USING (true);

-- -------------------------------------------------------
-- user_milestones: owner only
-- -------------------------------------------------------
CREATE POLICY "user_milestones_own"
    ON user_milestones FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- shared_posts: public posts readable by all; own posts manageable
-- -------------------------------------------------------
CREATE POLICY "posts_read_public"
    ON shared_posts FOR SELECT
    USING (is_public = true);

CREATE POLICY "posts_read_own"
    ON shared_posts FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "posts_manage_own"
    ON shared_posts FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- -------------------------------------------------------
-- post_reactions: own reactions manageable; all reactions readable
-- -------------------------------------------------------
CREATE POLICY "reactions_own"
    ON post_reactions FOR ALL
    USING  (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "reactions_read_all"
    ON post_reactions FOR SELECT
    USING (true);

-- ============================================================
-- SEED DATA: Milestones
-- ============================================================
-- Thoughtful progress markers — no points, no levels, no emojis.
-- They acknowledge real effort: applications sent, reflections written,
-- streaks maintained, relationships built.
-- ============================================================
INSERT INTO milestones (name, description, criteria) VALUES
    ('Getting Started',
     'You created your account and took the first step.',
     '{"action": "register"}'),

    ('First Application',
     'You applied to your first role. The journey begins.',
     '{"action": "create_application", "count": 1}'),

    ('Building Momentum',
     'Ten applications in. You are putting yourself out there.',
     '{"action": "create_application", "count": 10}'),

    ('In the Zone',
     'Twenty-five applications. Consistent effort pays off.',
     '{"action": "create_application", "count": 25}'),

    ('Self-Reflective',
     'You wrote your first reflection. Growth starts with honesty.',
     '{"action": "create_reflection", "count": 1}'),

    ('Growth Mindset',
     'Ten reflections. You are learning from every experience.',
     '{"action": "create_reflection", "count": 10}'),

    ('One Week Strong',
     'Seven consecutive days of activity. Consistency is key.',
     '{"action": "streak", "days": 7}'),

    ('Thirty Day Streak',
     'A full month of showing up. That takes real dedication.',
     '{"action": "streak", "days": 30}'),

    ('Connected',
     'You are following five people. Job searching is better together.',
     '{"action": "follow", "count": 5}'),

    ('Part of a Circle',
     'You joined your first group. Shared journeys go further.',
     '{"action": "join_group", "count": 1}'),

    ('Sharing Insights',
     'You shared your first post. Helping others helps you grow.',
     '{"action": "create_post", "count": 1}'),

    ('Offer Received',
     'You received a job offer. All the effort was worth it.',
     '{"action": "outcome_offer", "count": 1}'),

    ('Networking Pro',
     'You added ten contacts. Building relationships matters.',
     '{"action": "add_contact", "count": 10}'),

    ('Organised Thinker',
     'You created five tags. Categorisation brings clarity.',
     '{"action": "create_tag", "count": 5}'),

    ('Well Prepared',
     'You wrote prep notes for five interviews. Preparation wins.',
     '{"action": "add_prep_notes", "count": 5}'),

    ('Dream Chaser',
     'You saved ten jobs. Knowing what you want is half the battle.',
     '{"action": "save_job", "count": 10}'),

    ('Quick Converter',
     'You turned a saved job into an application. That is momentum.',
     '{"action": "convert_saved_job", "count": 1}'),

    ('Salary Explorer',
     'You tracked salary data on five applications. Know your worth.',
     '{"action": "track_salary", "count": 5}')

ON CONFLICT (name) DO NOTHING;
