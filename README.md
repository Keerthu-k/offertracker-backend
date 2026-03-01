# OfferTracker

A career intelligence API for professionals who want genuine clarity in their job search — not another chore.

---

## 1. What is OfferTracker?

OfferTracker is a **FastAPI-powered backend** built around one core idea: the job search deserves more than a Kanban board.

Most trackers record what happened. OfferTracker is built to help you understand *why* — why certain interview rounds go well, why certain resume versions perform better, what skill gaps keep surfacing, and how consistent your effort actually is.

At its core it is a **personal job search database**: every application, every interview stage, every offer and rejection, every reflection written after the fact. The entry form is intentionally flat — just `company_name` and `role_title` are required. Everything else is optional. Adding an application should take five seconds, not five minutes.

Beyond the personal tracker, OfferTracker has a lightweight **social layer** — follow friends, join circles, share updates and tips. Not a social media platform, not a competition. Just a small space where people navigating the same experience can see how each other is doing.

Progress is surfaced through **milestones**: quiet, automatic markers reached by actually using the product. No points, no leaderboard.

---

## 2. Why This Exists

| Problem | What OfferTracker does about it |
|---|---|
| Forgetting what happened in each interview round | Structured **Stages** with per-round notes, prep notes, and questions asked |
| Not knowing which resume version performs best | **Resume Versions** — label, store, and link each version to every application |
| No idea why rejections keep happening | **Outcomes** with compensation details, **Reflections** with structured post-mortems |
| Skill gaps identified in interviews slip through the cracks | `skill_gaps` JSON field in Reflections + a dedicated improvement plan |
| Job search feels like searching alone | **Follows**, **Groups**, and a shared **Post** feed |
| No sense of consistent effort | **Streak tracking** and natural **Milestones** reached through real activity |
| Interesting jobs forgotten before applying | **Saved Jobs** — bookmark postings and convert them to applications when ready |
| No visibility into search performance | **Analytics dashboard** — pipeline funnel, response rates, source effectiveness, salary insights |

---

## 3. Data Model

### Application Lifecycle

```
Open → Applied → Shortlisted → Interview → Offer → Closed
                                                  ↘ Rejected  (at any point)
                                                  ↘ Closed    (user withdraws at any point)
```

Auto-transitions happen silently:
- Creating an application with `status: Applied` auto-sets `applied_date` to today.
- Adding a Stage to an `Applied` application auto-moves it to `Interview`.
- Posting an Outcome auto-moves the application to `Offer`.

### Core Application Structure

```
Application (company, role, status, salary range, source, priority, ...)
    │
    ├── Stages[]        (Recruiter Call, Technical, Onsite, ...)
    ├── Outcome         (offer details, compensation, deadline)
    ├── Reflection      (what_worked, what_failed, skill_gaps, improvement_plan)
    ├── Contacts[]      (recruiters, hiring managers, referrals)
    ├── Documents[]     (cover letters, portfolios, references)
    └── Reminders[]     (follow-up dates, deadlines, interview prep)
```

### Social & Progress Layer

```
User ──► Follows        (stay connected with people on the same journey)
     ──► Groups         (circles — public or private)
     ──► Posts          (updates, tips, milestones, questions, resources, celebrations)
     ──► Milestones     (12 progress markers, reached automatically)
     ──► Saved Jobs     (bookmarked postings, convertible to full applications)
     ──► Activity Log   (automatic timeline of every action taken)
```

### Database Tables

| Table | Description |
|---|---|
| `users` | Accounts — email, username, streak, profile visibility |
| `resume_versions` | Resume snapshots with optional file upload |
| `applications` | Core job applications — full metadata, status, salary range |
| `application_stages` | Interview rounds — type, result, questions asked, prep notes |
| `outcomes` | Offer details — compensation, equity, start date, deadline |
| `reflections` | Post-mortem — what worked, what failed, skill gaps (JSON), improvement plan |
| `contacts` | Networking contacts linked to applications or standalone |
| `documents` | Cover letters, portfolios, references per application |
| `reminders` | Scheduled reminders — follow-ups, deadlines, interview prep |
| `saved_jobs` | Bookmarked job postings, promotable to full applications |
| `follows` | User → User connection graph |
| `groups` | Circles — public or private |
| `group_members` | Membership with role (admin / member) |
| `milestones` | 12 progress markers |
| `user_milestones` | Milestones reached by each user |
| `shared_posts` | Community posts — updates, tips, milestones, questions |
| `post_reactions` | Reactions on posts |
| `activity_log` | Full chronological event history per user |

The full schema with indexes, triggers, and RLS policies lives in [supabase_schema_final.sql](supabase_schema_final.sql).

---

## 4. Authentication

Authentication is handled entirely by **Supabase Auth**:

1. **Register** (`POST /api/v1/auth/register`) — signs up via Supabase Auth, creates a profile row in `public.users`, and awards the *Getting Started* milestone. Returns a session JWT.
2. **Login** (`POST /api/v1/auth/login`) — authenticates via Supabase Auth, returns the session JWT.
3. **All other endpoints** require an `Authorization: Bearer <token>` header, verified by the `get_current_user` FastAPI dependency against the `SUPABASE_JWT_SECRET`.

Every resource is scoped strictly to the authenticated user. Users can only read or modify their own data. Public profiles are opt-in via `profile_visibility`.

---

## 5. API Reference

**Base URL**: `http://127.0.0.1:8000` &nbsp;|&nbsp; **Prefix**: `/api/v1`

> Full request / response schemas — including all fields, types, enums, and examples — are in [api_schema_for_frontend.md](api_schema_for_frontend.md).  
> Interactive docs are at `http://127.0.0.1:8000/docs`.

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new account |
| `POST` | `/auth/login` | Log in and receive a JWT |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/me` | Get the authenticated user's profile |
| `PUT` | `/users/me` | Update profile (display name, bio, visibility) |
| `GET` | `/users/search?q=` | Search public user profiles |
| `GET` | `/users/{user_id}` | View a public user profile |

### Resumes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/resumes/` | List resume versions |
| `POST` | `/resumes/` | Create a resume version |
| `GET` | `/resumes/{id}` | Get a resume version by ID |
| `PUT` | `/resumes/{id}` | Update a resume version |
| `DELETE` | `/resumes/{id}` | Delete a resume version |

### Applications

Only `company_name` and `role_title` are required. Everything else defaults gracefully.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/applications/` | List applications — filter by `status`, `priority` |
| `POST` | `/applications/` | Create an application |
| `GET` | `/applications/{id}` | Get application with stages, outcome, and reflection |
| `PUT` | `/applications/{id}` | Update an application |
| `DELETE` | `/applications/{id}` | Delete an application (cascades all relations) |

### Application — Stages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/stages` | Add an interview stage |
| `PUT` | `/applications/{id}/stages/{stage_id}` | Update a stage |
| `DELETE` | `/applications/{id}/stages/{stage_id}` | Delete a stage |

### Application — Outcome (Offer Details)

One outcome per application. Creating one auto-transitions the application to `Offer`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/outcome` | Record offer details |
| `PUT` | `/applications/{id}/outcome/{outcome_id}` | Update offer details |
| `DELETE` | `/applications/{id}/outcome/{outcome_id}` | Remove offer details |

### Application — Reflection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/applications/{id}/reflection` | Add a post-interview reflection |
| `PUT` | `/applications/{id}/reflection/{reflection_id}` | Update a reflection |
| `DELETE` | `/applications/{id}/reflection/{reflection_id}` | Delete a reflection |

### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/contacts/` | List contacts — filter by `application_id`, `contact_type` |
| `POST` | `/contacts/` | Add a contact |
| `GET` | `/contacts/{contact_id}` | Get a contact by ID |
| `PUT` | `/contacts/{contact_id}` | Update a contact |
| `DELETE` | `/contacts/{contact_id}` | Delete a contact |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/documents/` | List documents — filter by `application_id` |
| `POST` | `/documents/` | Attach a document to an application |
| `GET` | `/documents/{document_id}` | Get a document by ID |
| `PUT` | `/documents/{document_id}` | Update a document |
| `DELETE` | `/documents/{document_id}` | Delete a document |

### Reminders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reminders/` | List reminders — filter by `is_completed`, `application_id` |
| `POST` | `/reminders/` | Create a reminder |
| `GET` | `/reminders/{reminder_id}` | Get a reminder by ID |
| `PUT` | `/reminders/{reminder_id}` | Update a reminder |
| `DELETE` | `/reminders/{reminder_id}` | Delete a reminder |
| `POST` | `/reminders/{reminder_id}/complete` | Mark a reminder as completed |

### Saved Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/saved-jobs/` | List saved jobs — filter by `status`, `priority` |
| `POST` | `/saved-jobs/` | Bookmark a new job posting |
| `GET` | `/saved-jobs/{id}` | Get a saved job by ID |
| `PUT` | `/saved-jobs/{id}` | Update a saved job (archive via `status: Archived`) |
| `DELETE` | `/saved-jobs/{id}` | Delete a saved job |
| `POST` | `/saved-jobs/{id}/convert` | Promote to a full application |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/dashboard` | Full dashboard — pipeline funnel, rates, source breakdown, weekly trend, salary insights |
| `GET` | `/analytics/activity` | Activity timeline — filter by `application_id` |
| `GET` | `/analytics/questions` | Personal interview question bank, aggregated from all stages |

### Social — Follows

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/follow/{user_id}` | Follow a user |
| `DELETE` | `/social/follow/{user_id}` | Unfollow a user |
| `GET` | `/social/followers/{user_id}` | List followers |
| `GET` | `/social/following/{user_id}` | List accounts this user follows |
| `GET` | `/social/follow-stats/{user_id}` | Get follower / following counts |

### Social — Groups

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/groups` | Create a group |
| `GET` | `/social/groups` | List public groups |
| `GET` | `/social/groups/mine` | List groups you belong to |
| `GET` | `/social/groups/{group_id}` | Get group details |
| `PUT` | `/social/groups/{group_id}` | Update group (creator only) |
| `DELETE` | `/social/groups/{group_id}` | Delete group (creator only) |
| `POST` | `/social/groups/{group_id}/join` | Join a group |
| `DELETE` | `/social/groups/{group_id}/leave` | Leave a group |
| `GET` | `/social/groups/{group_id}/members` | List group members |

### Social — Posts & Reactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/social/posts` | Create a post |
| `GET` | `/social/posts/feed` | Public feed — filter by `group_id` |
| `GET` | `/social/posts/mine` | Your posts |
| `PUT` | `/social/posts/{post_id}` | Update a post (author only) |
| `DELETE` | `/social/posts/{post_id}` | Delete a post (author only) |
| `POST` | `/social/posts/{post_id}/react` | Add a reaction |
| `DELETE` | `/social/posts/{post_id}/react` | Remove a reaction |

### Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/progress/milestones` | List all available milestones |
| `GET` | `/progress/milestones/mine` | Milestones you have reached |
| `GET` | `/progress/community` | Active members with public profiles |
| `GET` | `/progress/stats` | Your summary — applications, offers, rejections, streak, milestones |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/resumes/{resume_id}` | Upload a resume file (PDF or Word, max 10 MB) — updates `file_url` on the resume version |

---

## 6. Milestones

No points, no leaderboard. Just 12 quiet markers that acknowledge real effort.

| Milestone | Triggered by |
|-----------|--------------|
| Getting Started | Creating an account |
| First Application | Creating the first application |
| Building Momentum | 10 applications created |
| In the Zone | 25 applications created |
| Self-Reflective | Writing the first reflection |
| Growth Mindset | Writing 10 reflections |
| One Week Strong | 7 consecutive days of activity |
| Thirty Day Streak | 30 consecutive days of activity |
| Connected | Following 5 users |
| Part of a Circle | Joining a group |
| Sharing Insights | Creating a post |
| Offer Received | Recording a job offer |

The only metric surfaced on an ongoing basis is **streak days** — how many consecutive days you have been active. A gentle, honest signal.

---

## 7. Architecture

```
app/
├── api/
│   └── endpoints/
│       ├── auth.py            # Register, login
│       ├── users.py           # Profile management
│       ├── resumes.py         # Resume versions
│       ├── applications.py    # Applications, stages, outcomes, reflections
│       ├── contacts.py        # Networking contacts
│       ├── documents.py       # Application documents
│       ├── reminders.py       # Scheduled reminders
│       ├── saved_jobs.py      # Job bookmarks + convert-to-application
│       ├── analytics.py       # Dashboard, activity log, question bank
│       ├── social.py          # Follows, groups, posts, reactions
│       ├── gamification.py    # Milestones, community, stats
│       └── upload.py          # Supabase Storage file upload
├── core/
│   ├── config.py              # Pydantic settings — env vars
│   ├── database.py            # Supabase client singleton
│   ├── dependencies.py        # get_current_user JWT dependency
│   ├── security.py            # JWT verification
│   └── gamification.py        # Streak tracking + milestone check
├── crud/                      # Data access layer — one file per domain
└── schemas/                   # Pydantic request/response models
```

### Design Principles

- **Flat over nested.** The application form is two required fields. Everything else is optional.
- **User-scoped by default.** Every resource is private unless explicitly made public.
- **Auto-transitions are silent.** Status changes triggered by user actions (adding a stage, logging an offer) happen automatically, so the UI stays consistent without extra API calls.
- **Progress, not performance.** Milestones and streaks reward consistency, not volume.
- **Social without the noise.** Posts and follows are lightweight — a place to share the journey, not perform it.

---

## 8. Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) 0.100+ |
| Database | [Supabase](https://supabase.com/) (hosted PostgreSQL + Storage) |
| DB Client | [supabase-py](https://github.com/supabase/supabase-py) |
| Auth | Supabase Auth (JWT) |
| Validation | Pydantic V2 + Pydantic-Settings |
| File Upload | Supabase Storage via `python-multipart` |
| Testing | Pytest + HTTPX (mock Supabase client — no live DB required) |
| Python | 3.12+ |

---

## 9. Setup & Running

### Prerequisites

- Python 3.12 or later
- A [Supabase](https://supabase.com/) project

### Installation

```bash
git clone https://github.com/Keerthu-k/offertracker-backend.git
cd offertracker-backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com/).
2. Open the **SQL Editor** in the Supabase dashboard and run the entire contents of [supabase_schema_final.sql](supabase_schema_final.sql).
3. Go to **Storage → New Bucket** and create a bucket named `resumes`. Set it to public.
4. In **Settings → API**, copy your Project URL, `anon` key, `service_role` key, and JWT secret.

### Environment Variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Running the Server

```bash
uvicorn app.main:app --reload
```

| URL | What you get |
|-----|-------------|
| `http://127.0.0.1:8000` | API root |
| `http://127.0.0.1:8000/docs` | Swagger UI — interactive, authenticated |
| `http://127.0.0.1:8000/redoc` | ReDoc — clean reference view |

### Running Tests

The test suite uses a fully mocked Supabase client — no live database is needed:

```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 10. Future Direction

- **Richer Analytics** — stage-level conversion funnels, time-to-offer tracking, resume version performance comparison.
- **AI Integrations** — reflection summarisation, auto-tagged skill gaps, job description keyword analysis.
- **Notifications** — configurable nudges for streak breaks, reminder deadlines, and milestone triggers.
- **Granular Privacy** — move beyond the current public/private binary to per-resource visibility controls.
- **Frontend** — a minimal, focused dashboard. The API schema is fully documented in [api_schema_for_frontend.md](api_schema_for_frontend.md) and ready for handoff.
