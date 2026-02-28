# OfferTracker Backend

A thoughtful career tracking platform for professionals. Keep a personal database of your job applications, share your journey with friends and circles, and let natural milestones quietly mark your progress.

---

## 1. What is OfferTracker?

OfferTracker is a **FastAPI-powered career intelligence API** built for professionals who want clarity in their job search — not another chore. 

Our core philosophy is simple: **Milestones, not medals. Progress, not points.** Most job trackers treat applying for jobs as an automated Kanban board, built for transaction volume. The job search is historically lonely and demoralizing. OfferTracker elevates this by focusing entirely on *reflection* (what worked, what failed, identifying skill gaps) and genuine progress mapping.

It's a **personal database** that keeps your entire search history organised: which companies you applied to, what happened at each interview stage, whether you got an offer or a rejection, and most importantly — what you learned from the experience.

It's also a place to **share your journey** with friends and trusted circles. Not a social media platform. Not a competition. Just a lightweight space where people going through the same thing can see how each other is doing, exchange tips, and stay motivated by showing up together.

The application form is **flat and simple** — just the company name, role, and you're done. Everything else is optional. It should take seconds, not minutes. The goal is to make tracking feel effortless so you actually do it.

---

## 2. Why We Built This

Most job seekers:

- Apply blindly and forget what happened in each interview.
- Don't track which resume version performs best.
- Have no structured way to figure out *why* they keep getting rejected.
- Can't identify and close skill gaps systematically.
- Search alone, with no one to share the ups and downs with.

OfferTracker treats the job search as a **shared, reflective process** — not a grind:

| Pain Point | What OfferTracker Does |
|---|---|
| Forgetting interview feedback | Structured **Stages** with per-round notes |
| No resume tracking | **Resume Versions** linked to each application |
| Unknown rejection patterns | **Outcomes** with categorised rejection reasons + personal analytics |
| No systematic skill-gap analysis | **Reflections** — what worked, what didn't, skill gaps, improvement plan |
| Searching alone | **Follow friends**, join **groups**, share **updates and tips** |
| No sense of progress | Quiet **milestones** that acknowledge your effort naturally |

---

## 3. Conceptual Model & Database Design

### Core Lifecycle

```
User ──► Application (Company + Role + Location)
            │
            ├──► Stages (Recruiter Call → Technical Screen → Final → ...)
            ├──► Outcome (Offer / Rejected / Withdrawn)
            └──► Reflection (what_worked, what_failed, skill_gaps, improvement_plan)
```

### Social & Progress Layer

```
User ──► Follows (stay connected with friends)
     ──► Groups (circles of people in similar situations)
     ──► Posts (share updates, tips, milestones, questions)
     ──► Milestones (quiet progress markers, reached naturally)
```

### All 13 Database Tables

| Table | Description |
|---|---|
| `users` | Accounts — email, username, password hash, activity streak |
| `resume_versions` | Per-user snapshots of resumes with optional file uploads |
| `applications` | Job applications — company, role, location, source, status, date |
| `application_stages` | Interview rounds per application — stage name, date, notes |
| `outcomes` | Final result per application — Offer / Rejected / Withdrawn |
| `reflections` | Post-mortem per application — skill gaps (JSON), improvement plan |
| `follows` | User → User connection graph |
| `groups` | Circles — public or private |
| `group_members` | Membership records with role (admin / member) |
| `milestones` | 12 progress markers — reached naturally through real activity |
| `user_milestones` | Milestones reached by each user |
| `shared_posts` | Journey sharing — updates, tips, milestones, questions |
| `post_reactions` | Simple reactions on posts |

The full schema with indexes, triggers, RLS policies, and seed data lives in [supabase_schema.sql](supabase_schema.sql).

---

## 4. Authentication

OfferTracker uses a simple **JWT-based auth** system:

1. **Register** (`POST /api/v1/auth/register`) — creates a user, hashes password with bcrypt, returns a JWT.
2. **Login** (`POST /api/v1/auth/login`) — verifies credentials, returns a JWT.
3. **All other endpoints** require a `Bearer <token>` header — enforced via a FastAPI dependency (`get_current_user`).

Every resource (applications, resumes, etc.) is **scoped to the authenticated user**. Users can only see/edit their own data. Public profiles are opt-in.

---Roadmap & Architectural Findings

Based on architectural reviews and product insights, we are tracking the following technical debt and future enhancements:

### Product & Usability Scope
- **Granular Privacy Controls**: The current `is_profile_public` boolean is too binary for the secretive nature of job hunting. We will implement granular visibility (e.g., Private, Friends Only, Group Only).
- **Pro-Level Compensation Tracking**: Upgrading the `outcomes` table to structure compensation data (base salary, bonus, equity, currency) and enforce `deadline_date` for expiring offers, aiding professionals juggling actual numbers.
- **Analytics & Networking**: Converting the `applied_source` to a strict Enum (no more fragmented free-text) and properly deploying the `contacts` table to track recruiter and referral relationships (bridging the gap between our CRUD files and the database).

### Security & Architecture Scope
- **Fix "Split-Brain" Auth**: We are removing the manual Supabase-to-FastAPI `public.users` sync in our login endpoints. Instead, we'll use a **PostgreSQL Trigger** directly in Supabase to guarantee profile creation and eliminate the risk of zombie accounts.
- **Enforce Row Level Security (RLS)**: Adding strict `ENABLE ROW LEVEL SECURITY` policies to all tables in `supabase_schema.sql` to protect data at the database layer (scoping strictly to `auth.uid() = user_id`).
- **Standardize Schema**: Dropping the legacy `password_hash` column from `public.users` (delegated completely to Supabase Auth) and properly creating the missing tables for contacts, tags, and reminders to match existing CRUD logic.

---

## 6. 

## 5. API Reference

**Base URL**: `http://127.0.0.1:8000` &nbsp;|&nbsp; **Prefix**: `/api/v1`

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and receive JWT |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/me` | Get current user profile |
| `PUT` | `/users/me` | Update current user profile |
| `GET` | `/users/search?q=` | Search public user profiles |
| `GET` | `/users/{user_id}` | View a public user profile |

### Resumes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/resumes/` | List my resume versions |
| `POST` | `/resumes/` | Create a resume version |
| `GET` | `/resumes/{id}` | Get a resume version |
| `PUT` | `/resumes/{id}` | Update a resume version |
| `DELETE` | `/resumes/{id}` | Delete a resume version |

### Applications

The form is intentionally flat. Only `company_name` and `role_title` are required — everything else is optional and fills itself with sensible defaults.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/applications/` | List my applications (with stages, outcome, reflection) |
| `POST` | `/applications/` | Create a new application |
| `GET` | `/applications/{id}` | Get application with nested relations |
| `PUT` | `/applications/{id}` | Update an application |
| `DELETE` | `/applications/{id}` | Delete an application (cascades) |

### Application — Stages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/stages` | Add an interview stage |
| `PUT` | `/applications/{id}/stages/{stage_id}` | Update a stage |
| `DELETE` | `/applications/{id}/stages/{stage_id}` | Delete a stage |

### Application — Outcome

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/outcome` | Set the outcome |
| `PUT` | `/applications/{id}/outcome/{outcome_id}` | Update the outcome |
| `DELETE` | `/applications/{id}/outcome/{outcome_id}` | Delete the outcome |

### Application — Reflection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/reflection` | Add a reflection |
| `PUT` | `/applications/{id}/reflection/{reflection_id}` | Update a reflection |
| `DELETE` | `/applications/{id}/reflection/{reflection_id}` | Delete a reflection |

### Social — Follows

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/follow/{user_id}` | Follow a user |
| `DELETE` | `/social/follow/{user_id}` | Unfollow a user |
| `GET` | `/social/followers/{user_id}` | List followers |
| `GET` | `/social/following/{user_id}` | List following |
| `GET` | `/social/follow-stats/{user_id}` | Get follower / following counts |

### Social — Groups (Circles)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/groups` | Create a group |
| `GET` | `/social/groups` | List public groups |
| `GET` | `/social/groups/mine` | List my groups |
| `GET` | `/social/groups/{group_id}` | Get group details |
| `PUT` | `/social/groups/{group_id}` | Update group (creator only) |
| `DELETE` | `/social/groups/{group_id}` | Delete group (creator only) |
| `POST` | `/social/groups/{group_id}/join` | Join a group |
| `DELETE` | `/social/groups/{group_id}/leave` | Leave a group |
| `GET` | `/social/groups/{group_id}/members` | List group members |

### Social — Posts & Reactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/posts` | Create a post (update / tip / milestone / question) |
| `GET` | `/social/posts/feed` | Public feed (optional `group_id` filter) |
| `GET` | `/social/posts/mine` | My posts |
| `PUT` | `/social/posts/{post_id}` | Update a post (author only) |
| `DELETE` | `/social/posts/{post_id}` | Delete a post (author only) |
| `POST` | `/social/posts/{post_id}/react` | React to a post |
| `DELETE` | `/social/posts/{post_id}/react` | Remove reaction |

### Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/progress/milestones` | List all milestones |
| `GET` | `/progress/milestones/mine` | My reached milestones |
| `GET` | `/progress/community` | Active community members (public profiles) |
| `GET` | `/progress/stats` | My progress summary (applications, offers, rejections, streaks) |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/resumes/{resume_id}` | Upload a resume file (PDF / Word, max 10 MB) |

> Full request / response schemas are documented in [api_schema_for_frontend.md](api_schema_for_frontend.md) and in the interactive Swagger UI at `/docs`.

---

## 6. Milestones — Thoughtful Progress, Not Gamification

We don't do points, levels, or leaderboards. Those work for games, not for professionals navigating a stressful career transition.

Instead, OfferTracker tracks **milestones** — natural moments in your job search journey that deserve quiet acknowledgment. They're reached automatically as you use the app. No grinding, no competition.

| Milestone | What It Means |
|-----------|--------------|
| Getting Started | You created your account and took the first step. |
| First Application | You applied to your first role. The journey begins. |
| Building Momentum | Ten applications in. You're putting yourself out there. |
| In the Zone | Twenty-five applications. Consistent effort pays off. |
| Self-Reflective | You wrote your first reflection. Growth starts with honesty. |
| Growth Mindset | Ten reflections. You're learning from every experience. |
| One Week Strong | Seven consecutive days of activity. Consistency is key. |
| Thirty Day Streak | A full month of showing up. That takes real dedication. |
| Connected | You're following five people. Job searching is better together. |
| Part of a Circle | You joined your first group. Shared journeys go further. |
| Sharing Insights | You shared your first post. Helping others helps you grow. |
| Offer Received | You received a job offer. All the effort was worth it. |

**Consistency tracking** is the only metric we surface: how many consecutive days you've been active. It's a gentle reminder to keep showing up — not a score to inflate.

---

## 7. Architecture & Philosophy

Built with **Domain-Driven Design (DDD)**, modularised into cleanly separated layers:

```
app/
├── api/
│   └── endpoints/         # HTTP route handlers (auth, users, applications, social, progress, upload)
├── core/
│   ├── config.py          # Settings & environment variables
│   ├── database.py        # Supabase client singleton
│   ├── dependencies.py    # get_current_user JWT dependency
│   ├── security.py        # JWT creation / verification, bcrypt hashing
│   └── gamification.py    # Streak tracking & milestone checker
├── crud/
│   ├── crud_base.py       # Generic CRUD (get, get_multi, create, update, remove, get_by_field)
│   ├── crud_application.py
│   ├── crud_resume.py
│   ├── crud_user.py       # Email/username lookup, streak, search
│   ├── crud_social.py     # Follows, groups, posts, reactions
│   └── crud_gamification.py # Milestones, community view
└── schemas/
    ├── application.py     # Application, Stage, Outcome, Reflection
    ├── resume.py          # ResumeVersion
    ├── user.py            # Register, Login, Token, Profile
    ├── social.py          # Follow, Group, Post, Reaction
    └── gamification.py    # Milestone, Community, UserStats
```

### Design Principles

- **Flat over nested.** The application form takes two fields. Everything else is optional.
- **Your data, your control.** Every resource is user-scoped. Private by default, public by choice.
- **Progress, not performance.** No points, no leaderboard. Just honest tracking.
- **Social, not social media.** Share with friends and circles who understand what you're going through.
- **Light, not heavy.** The system should make your job search easier, never harder.

---

## 8. Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | [Supabase](https://supabase.com/) (Managed PostgreSQL + Storage) |
| DB Client | [supabase-py](https://github.com/supabase/supabase-py) |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| Validation | Pydantic V2 & Pydantic-Settings |
| File Upload | Supabase Storage via `python-multipart` |
| Testing | Pytest + HTTPX (mock Supabase client, no live DB needed) |

---

## 9. How to Setup and Run

### Prerequisites
- Python 3.12+

### Installation

```bash
git clone https://github.com/Keerthu-k/offertracker-backend.git
cd offertracker-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database & Storage Configuration

1. **Create a Supabase project** at [supabase.com](https://supabase.com/).
2. **Run the schema** — open the SQL Editor and execute the contents of [supabase_schema.sql](supabase_schema.sql).
3. **Create a Storage bucket** — Dashboard → Storage → New Bucket → name it `resumes` (public).
4. **Create a `.env` file** in the project root:
   ```env
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=your-anon-or-service-role-key
   JWT_SECRET_KEY=your-long-random-secret-string
   ```

### Running the Server

```bash
uvicorn app.main:app --reload
```

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | Base URL |
| `http://127.0.0.1:8000/docs` | Swagger UI (interactive) |
| `http://127.0.0.1:8000/redoc` | ReDoc |

### Running Tests

Tests use a fully in-memory mock Supabase client — no live database needed:

```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 10. Future Scope

- **Advanced Analytics** — stage conversion funnels, time-to-offer metrics, resume-version performance ranking.
- **AI Integrations** — NLP-powered summarisation of reflections, auto-extracted skill-gap trends.
- **Notifications** — gentle nudges for streak continuity, group activity, and milestones reached.
- **Frontend** — a clean, minimal React / Next.js dashboard. The API schema is already documented for handoff.
