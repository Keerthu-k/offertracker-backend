# OfferTracker Backend

## 1. What is OfferTracker?
OfferTracker Backend is a FastAPI-based career intelligence API that tracks job applications, interview stages, resume versions, outcomes, and reflections — and turns them into actionable analytics. 

## 2. The Problem It Solves
Most job seekers:
- Apply blindly and forget interview feedback.
- Don't track resume changes.
- Don't know exactly why they are getting rejected.
- Can't identify skill gaps systematically.

OfferTracker solves this by acting as a structured system for capturing, analyzing, and improving your job search strategy. It treats job hunting as a product experiment, a performance pipeline, and a measurable growth system instead of an emotional rollercoaster.

## 3. Conceptual Model & Database Design
The backend models the complete job search lifecycle:

`Company` -> `Job Posting` -> `Application` -> `Stages` -> `Outcome` -> `Reflection`

Additionally:
- `ResumeVersion` is linked directly to the `Application`.
- **Analytics** are derived from the aggregated data.

### Core Domain Objects
- **Company**: Where you applied.
- **JobPosting**: The specific role and its requirements.
- **ResumeVersion**: Snapshot of the specific resume used for that application.
- **Application**: The main entity connecting the job, resume, and application lifecycle.
- **ApplicationStage**: Progress steps (e.g., Recruiter Call, Technical Screen).
- **Outcome**: Final result of the application (e.g., Offer, Rejected, Withdrawn).
- **Reflection**: Post-mortem analysis capturing what worked, what failed, categorized skill gaps, and an improvement plan.

## 4. API Controllers (Routers)
The API is divided into several controllers, each managing a specific part of the job search lifecycle:

- **Companies Controller**: Manages organizational data. Handles creating, updating, and retrieving companies you are targeting.
- **Jobs Controller**: Manages specific job postings associated with companies. Stores job descriptions, URLs, and specific requirements.
- **Resumes Controller**: Manages different versions of your resume. This allows the system to track which resume version performs best for specific industries or roles.
- **Applications Controller**: The central hub of the API. It manages the connection between a job, a resume, and the current status.
    - **Stages Sub-controller**: Tracks individual interview rounds and feedback for a specific application.
    - **Outcome Sub-controller**: Records the final result and rejection reasons for categorization.
    - **Reflection Sub-controller**: Stores post-interview reflections, skill gap analysis, and future improvement plans.

## 5. Architecture & Philosophy
Built with Domain-Driven Design (DDD), the backend is heavily modularized to maintain cleanly separated layers:
- **Models** (`app/models/`): SQLAlchemy 2.0 declarative ORM models.
- **Schemas** (`app/schemas/`): Pydantic V2 schemas governing strict request validation and response serialization.
- **CRUD Operations** (`app/crud/`): Reusable, generic asynchronous CRUD abstractions for database interaction.
- **API Routers** (`app/api/`): Predictable HTTP REST endpoints separated by domain.
- **Database Configuration** (`app/core/`): Application settings, environment variable parsing, and async DB session management.

This architecture ensures the system is not just a standard CRUD app, but an insight-oriented analytics engine. It's built to scale seamlessly, support robust analytics from day one, and easily integrate AI services later.

## 6. Tech Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance async web framework)
- **Database**: PostgreSQL
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async operations & connection pooling)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Validation & Settings**: [Pydantic V2 & Pydantic-Settings](https://docs.pydantic.dev/latest/)
- **Testing**: Pytest & HTTPX (with an in-memory async SQLite fixture for lightning-fast testing)

## 7. How to Setup and Run

### Prerequisites
- Python 3.12+
- A running PostgreSQL server.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Keerthu-k/offertracker-backend.git
   cd offertracker-backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Database Configuration
Ensure your local PostgreSQL database is running. Create a database named `offertracker` (or customize the connection variables in `app/core/config.py`).

By default, the application connects to: `postgresql+asyncpg://postgres:postgres@localhost:5432/offertracker`.

Run Alembic migrations to apply the schema to your database:
```bash
alembic upgrade head
```

### Running the Application

Start the local development server:
```bash
uvicorn app.main:app --reload
```

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
- **ReDoc API Docs**: `http://127.0.0.1:8000/redoc`

### Running Tests
To run the automated integration tests, the app securely spins up an in-memory SQLite database to ensure the live database isn't touched:
```bash
export PYTHONPATH=.
pytest tests/ -v
```

## 8. Future Scope
- **Advanced Analytics Endpoints**: Aggregate data to map out success rates by resume version, time-to-offer metrics, and interview stage conversion rates.
- **Authentication Strategy**: Implement OAuth2 with JWT tokens to secure endpoints.
- **AI Integrations**: Implement NLP summarization of reflection insights to automatically extract trending skill gaps dynamically.
