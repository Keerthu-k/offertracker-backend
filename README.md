# OfferTracker Backend

A gamified, social job-search intelligence platform. Track applications, reflect on interviews, share knowledge with friends, and level up while you land your next role.

---

## 1. What is OfferTracker?

OfferTracker is a **FastAPI-powered career intelligence API** that goes far beyond a spreadsheet of applications. It models the *entire* job-search lifecycle — from resume versioning and application tracking, through interview stages and outcomes, all the way to structured post-mortem reflections — and layers a **social + gamification system** on top so the process stays motivating.

Every piece of data feeds into **per-user analytics**: offer vs. rejection rates, interview-stage conversion funnels, skill-gap frequency, streaks, XP, and a public leaderboard.

---

## 2. The Problem It Solves

Most job seekers:

- Apply blindly and forget what happened in each interview.
- Don't track which resume version performs best.
- Have no structured way to figure out *why* they keep getting rejected.
- Can't identify and close skill gaps systematically.
- Job-search alone, with no accountability or peer support.

OfferTracker solves all of this by treating job hunting as a **measurable, collaborative growth system** instead of an emotional rollercoaster:

| Pain Point | OfferTracker Solution |
|---|---|
| Forgetting interview feedback | Structured **Stages** with per-round notes |
| No resume tracking | **Resume Versions** linked to each application |
| Unknown rejection patterns | **Outcomes** with categorised rejection reasons + analytics |
| No systematic skill-gap analysis | **Reflections** with `skill_gaps` JSON + `improvement_plan` |
| Lonely, unmotivating process | **Social features** — follow friends, join groups, share tips |
| No sense of progress | **Gamification** — XP, levels, daily streaks, 12 unlockable achievements |

---

## 3. Conceptual Model & Database Design

### Core Lifecycle

```
User ──► Application (Company + Role)
            │
            ├──► Stages (Recruiter Call → Technical Screen → Final → ...)
            ├──► Outcome (Offer / Rejected / Withdrawn)
            └──► Reflection (what_worked, what_failed, skill_gaps, improvement_plan)
```

### Social & Gamification Layer

```
User ──► Follows (follower ↔ following)
     ──► Groups ──► Group Members (admin / member)
     ──► Shared Posts ──► Post Reactions
     ──► Achievements ──► User Achievements
```

### All 13 Database Tables

| Table | Description |
|---|---|
| `users` | Accounts — email, username, password hash, XP, level, streak |
| `resume_versions` | Per-user snapshots of resumes with optional file uploads |
| `applications` | Job applications — company, role, source, URL, status, date |
| `application_stages` | Interview rounds per application — stage name, date, notes |
| `outcomes` | Final result per application — Offer / Rejected / Withdrawn |
| `reflections` | Post-mortem per application — skill gaps (JSON), improvement plan |
| `follows` | User → User follow graph |
| `groups` | Community groups (public / private) |
| `group_members` | Membership records with role (admin / member) |
| `achievements` | 12 seeded achievement definitions with XP rewards |
| `user_achievements` | Earned achievements per user |
| `shared_posts` | Knowledge-sharing posts — updates, tips, milestones, questions |
| `post_reactions` | Reactions (likes, etc.) on posts |

The full schema with indexes, triggers, RLS policies, and seed data lives in [`supabase_schema.sql`](supabase_schema.sql).

---

## 4. Authentication

OfferTracker uses a simple **JWT-based auth** system:

1. **Register** (`POST /api/v1/auth/register`) — creates a user, hashes password with bcrypt, returns a JWT.
2. **Login** (`POST /api/v1/auth/login`) — verifies credentials, returns a JWT.
3. **All other endpoints** require a `Bearer <token>` header — enforced via a FastAPI dependency (`get_current_user`).

Every resource (applications, resumes, etc.) is **scoped to the authenticated user**. Users can only see/edit their own data.

---

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

### Social — Groups

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

### Gamification

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gamification/achievements` | List all achievements |
| `GET` | `/gamification/achievements/mine` | My earned achievements |
| `GET` | `/gamification/leaderboard` | Global XP leaderboard |
| `GET` | `/gamification/stats` | My analytics (applications, offers, rejections, streaks, XP) |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/resumes/{resume_id}` | Upload a resume file (PDF / Word, max 10 MB) |

> Full request / response schemas are documented in [`api_schema_for_frontend.md`](api_schema_for_frontend.md) and in the interactive Swagger UI at `/docs`.

---

## 6. Gamification System

| Mechanic | How It Works |
|----------|-------------|
| **XP** | Earned per action — Apply (+10), Stage (+5), Outcome (+15), Reflection (+20), Post (+10), Follow/Join (+5) |
| **Levels** | `level = floor(√(xp / 50)) + 1` — scales progressively |
| **Streaks** | Consecutive daily activity; resets after a missed day |
| **Achievements** | 12 unlockable badges — from *First Steps* (register) to *Offer Landed* (first offer) |

### Seeded Achievements

| Badge | Criteria | XP Reward |
|-------|----------|-----------|
| 🚀 First Steps | Register an account | 50 |
| 📝 First Application | 1 application | 20 |
| 🔥 Hustler | 10 applications | 50 |
| ⚡ Machine | 25 applications | 100 |
| 🪞 Self-Aware | 1 reflection | 30 |
| 🧠 Reflective Mind | 10 reflections | 80 |
| 📅 Streak 7 | 7-day activity streak | 50 |
| 🏆 Streak 30 | 30-day activity streak | 150 |
| 🦋 Social Butterfly | Follow 5 users | 30 |
| 🤝 Team Player | Join first group | 20 |
| 💡 Knowledge Sharer | First post | 20 |
| 🎉 Offer Landed | Receive first offer | 200 |

---

## 7. Architecture & Philosophy

Built with **Domain-Driven Design (DDD)**, the backend is modularised into cleanly separated layers:

```
app/
├── api/
│   └── endpoints/         # HTTP route handlers (auth, users, applications, social, gamification, upload)
├── core/
│   ├── config.py          # Settings & environment variables
│   ├── database.py        # Supabase client singleton
│   ├── dependencies.py    # get_current_user JWT dependency
│   ├── security.py        # JWT creation / verification, bcrypt hashing
│   └── gamification.py    # XP engine & achievement checker
├── crud/
│   ├── crud_base.py       # Generic CRUD (get, get_multi, create, update, remove, get_by_field)
│   ├── crud_application.py
│   ├── crud_resume.py
│   ├── crud_user.py       # Email/username lookup, XP, streak, search
│   ├── crud_social.py     # Follows, groups, posts, reactions
│   └── crud_gamification.py # Achievements, leaderboard
└── schemas/
    ├── application.py     # Application, Stage, Outcome, Reflection
    ├── resume.py          # ResumeVersion
    ├── user.py            # Register, Login, Token, Profile
    ├── social.py          # Follow, Group, Post, Reaction
    └── gamification.py    # Achievement, Leaderboard, UserStats
```

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
2. **Run the schema** — open the SQL Editor and execute the contents of [`supabase_schema.sql`](supabase_schema.sql).
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
pytest tests/ -v
```

---

## 10. Future Scope

- **Advanced Analytics Endpoints** — stage conversion funnels, time-to-offer metrics, resume-version performance ranking.
- **AI Integrations** — NLP-powered summarisation of reflections, auto-extracted skill-gap trends.
- **Notifications** — real-time alerts for new followers, group activity, and achievement unlocks.
- **Frontend** — React / Next.js dashboard with the API schema already documented for handoff.
