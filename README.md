# SkillSense AI

<p align="center">
  <img src="https://i.ibb.co/M51qFRs5/Screenshot-2025-12-18-125743-removebg-preview.png" alt="SkillSense AI logo" width="120" />
</p>

<p align="center">
  <strong>An AI-powered placement-readiness and skill-verification platform for students, recruiters, universities, and staff reviewers.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2018-111827?style=for-the-badge&logo=react" alt="React 18" />
  <img src="https://img.shields.io/badge/Backend-Django%204.2-0f172a?style=for-the-badge&logo=django" alt="Django 4.2" />
  <img src="https://img.shields.io/badge/API-DRF%20%2B%20JWT-1f2937?style=for-the-badge" alt="DRF and JWT" />
  <img src="https://img.shields.io/badge/UI-Vite%20%2B%20TypeScript-111827?style=for-the-badge&logo=vite" alt="Vite and TypeScript" />
</p>

SkillSense AI brings resume parsing, GitHub-backed engineering analysis, AI interview workflows, recruiter screening, university analytics, and approval operations into one product.

## Highlights

- Multi-role product with dedicated flows for students, recruiters, universities, and staff reviewers
- Evidence-backed scoring across coding, communication, authenticity, and placement readiness
- AI-assisted repo analysis and interview evaluation when provider keys are configured
- Export-ready PDFs for score reports, skill passports, recruiter summaries, and resumes
- In-app approval console for recruiter and university onboarding

## Experience Map

| Audience | What they get |
| --- | --- |
| Students | Resume onboarding, profile extraction, GitHub analysis, AI interview lab, skill passport, progress tracking, roadmap, media uploads |
| Recruiters | Candidate discovery, filters, saved searches, job briefs, match scoring, pipeline states, resume/report downloads, interview scheduling |
| Universities | Cohort analytics, branch/course/year filtering, CSV batch upload, intervention tracking, placement drive planning |
| Staff | Approval login, in-app recruiter/university approval console, Django admin access for deeper operations |

## Feature Overview

### Student Experience

- Resume-based onboarding and profile extraction
- JWT authentication and profile management
- Scorecards for:
  - coding skill index
  - communication score
  - authenticity score
  - placement readiness
- Skill passport with downloadable PDF
- Resume builder with downloadable PDF
- GitHub repository analysis with:
  - repo-level engineering score
  - file-level summaries
  - architecture detection
  - repository and commit signal analysis
  - AI-generated coaching when an LLM key is present
- AI interview lab with:
  - configurable target role
  - configurable seniority
  - configurable interview mode
  - adaptive follow-up questions
  - rubric-based scoring
  - session summary and readiness result
- Progress dashboard, recommendations, roadmap, notifications, and verification tracking

### Recruiter Experience

- Approval-gated recruiter onboarding
- Candidate discovery dashboard
- Search, ranking, filtering, and saved searches
- Job brief creation and match scoring
- Candidate pipeline workflow
- Candidate report and resume download
- Interview scheduling

### University Experience

- Approval-gated university onboarding
- University analytics dashboard
- Cohort filtering by branch, course, and year
- Readiness and score distribution views
- Intervention tracking
- CSV batch upload
- Placement drive creation and tracking

### Staff and Admin Experience

- Django admin support for operational models
- In-app approval console for recruiter and university access review
- Role-based access control
- Environment-driven deployment configuration
- OpenAI-compatible provider support through `OPENAI_API_BASE`

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, TanStack Query, Recharts, Radix UI |
| Backend | Django 4.2, Django REST Framework, Simple JWT, Django CORS Headers |
| Reporting | ReportLab, Matplotlib |
| Parsing | pdfminer.six, PyPDF2, python-docx |
| Storage | SQLite by default, `DATABASE_URL` support for PostgreSQL and other production databases |

## Architecture

```text
src/             React frontend and route-level UI
accounts/        auth, onboarding, profiles, score APIs
skills/          interviews, repo analysis, dashboards, notifications, reports
content/         landing page content blocks
skillsence/      Django settings, URLs, ASGI/WSGI
templates/       Django template shell
dist/            built frontend served by Django when needed
```

## Product Routes

### Public and Auth

- `/`
- `/student/start`
- `/student`
- `/student/register`
- `/recruiter`
- `/recruiter/register`
- `/university`
- `/university/register`
- `/ops/login`

### Staff

- `/ops/approvals`

### Student

- `/dashboard`
- `/dashboard/code`
- `/dashboard/media`
- `/dashboard/passport`
- `/dashboard/interview`
- `/dashboard/progress`
- `/dashboard/roadmap`
- `/dashboard/resume-builder`
- `/dashboard/settings`

### Recruiter

- `/recruiter/dashboard`

### University

- `/university/dashboard`

## API Surface

### Accounts

- `POST /api/accounts/signup/`
- `POST /api/accounts/login/`
- `POST /api/accounts/logout/`
- `GET /api/accounts/profile/`
- `PATCH /api/accounts/profile/`
- `GET /api/accounts/staff/approvals/`
- `POST /api/accounts/staff/approvals/<user_id>/`
- `GET /api/accounts/dashboard/`
- `POST /api/accounts/recalculate/`
- `GET /api/accounts/score-report/`

### Student Skills

- `GET /api/skills/dashboard/`
- `GET /api/skills/activities/`
- `GET /api/skills/verification-steps/`
- `GET /api/skills/recommendations/`
- `GET /api/skills/skill-suggestions/`
- `GET /api/skills/skill-passport/`
- `GET /api/skills/skill-passport/pdf/`
- `GET /api/skills/resume/`
- `GET /api/skills/resume-builder/`
- `GET /api/skills/resume-builder/pdf/`
- `GET /api/skills/notifications/`
- `POST /api/skills/notifications/<id>/read/`
- `GET /api/skills/ai-interview/`
- `POST /api/skills/ai-interview/action/`
- `POST /api/skills/code-analysis/`
- `GET /api/skills/code-analysis/<report_id>/file/?path=...`
- `GET /api/skills/media/`
- `GET /api/skills/progress/`
- `GET /api/skills/roadmap/`
- `GET /api/skills/settings/`
- `GET /api/skills/performance/`

### Recruiter

- `GET /api/skills/recruiter-dashboard/`
- `GET /api/skills/recruiter-dashboard/jobs/`
- `POST /api/skills/recruiter-dashboard/jobs/`
- `GET /api/skills/recruiter-dashboard/pipeline/<candidate_id>/`
- `POST /api/skills/recruiter-dashboard/pipeline/<candidate_id>/`
- `GET /api/skills/recruiter-dashboard/saved-searches/`
- `POST /api/skills/recruiter-dashboard/saved-searches/`
- `GET /api/skills/recruiter-dashboard/report/<student_id>/`
- `GET /api/skills/recruiter-dashboard/resume/<student_id>/`
- `GET /api/skills/interview-schedules/`
- `POST /api/skills/interview-schedules/`

### University

- `GET /api/skills/university-dashboard/`
- `POST /api/skills/university-dashboard/batch-upload/`
- `GET /api/skills/university-dashboard/interventions/<student_id>/`
- `POST /api/skills/university-dashboard/interventions/<student_id>/`
- `GET /api/skills/university-dashboard/drives/`
- `POST /api/skills/university-dashboard/drives/`

## Local Development

### Prerequisites

- Python
- Node.js
- npm

Windows examples below use PowerShell.

### 1. Clone and install

```powershell
git clone <your-repo-url>
cd SkillSense-AI-main
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env.local
```

Minimum local setup:

```env
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=dev-only-secret-key
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

Optional AI and GitHub setup:

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_provider_key
OPENAI_API_BASE=https://api.openai.com/v1/chat/completions
OPENAI_MODEL=gpt-4o-mini
```

Example Groq setup:

```env
OPENAI_API_KEY=your_groq_key
OPENAI_API_BASE=https://api.groq.com/openai/v1/chat/completions
OPENAI_MODEL=llama-3.3-70b-versatile
```

### 3. Run the backend

```powershell
python manage.py migrate
python manage.py runserver
```

Backend default:

- `http://127.0.0.1:8000`

### 4. Run the frontend

```powershell
npm run dev
```

Frontend default:

- `http://127.0.0.1:8080`

The Vite dev server proxies `/api` and `/media` to `VITE_API_PROXY_TARGET` or `http://127.0.0.1:8000` by default, so local frontend requests work even when `VITE_API_BASE_URL` is unset.

### 5. Single-server local run

If you want Django to serve the built frontend:

```powershell
npm run build
python manage.py runserver
```

Then open:

- `http://127.0.0.1:8000`

## Environment Variables

### Core Django

- `DJANGO_DEBUG`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOW_ALL`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_DB_CONN_MAX_AGE`

### Security and Proxy

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`
- `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF`
- `DJANGO_USE_X_FORWARDED_HOST`
- `DJANGO_SECURE_PROXY_SSL_HEADER`
- `DJANGO_SESSION_COOKIE_SAMESITE`
- `DJANGO_CSRF_COOKIE_SAMESITE`
- `DJANGO_X_FRAME_OPTIONS`

### AI and Repository Analysis

- `GITHUB_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `AI_REPO_CACHE_ENABLED`
- `AI_REPO_CACHE_CHARS`
- `AI_REPO_CHUNK_CHARS`
- `AI_REPO_MAX_FILES`
- `AI_REPO_PREVIEW_CHARS`

### Frontend

- `VITE_API_BASE_URL`
- `VITE_API_PROXY_TARGET`

## Validation

### Backend

```powershell
python manage.py check
python manage.py test
```

### Frontend

```powershell
npm run build
```

### Lint

```powershell
npm run lint
```

`npm run build` is the current release gate. If lint fails, that is frontend lint debt rather than a build blocker.

## Deployment Notes

### Production checklist

- Set `DJANGO_DEBUG=false`
- Set a real `DJANGO_SECRET_KEY`
- Set `DJANGO_ALLOWED_HOSTS`
- Set `DJANGO_CORS_ALLOWED_ORIGINS`
- Set `DJANGO_CSRF_TRUSTED_ORIGINS`
- Set `DATABASE_URL`
- Set HTTPS-related security env vars
- Run migrations
- Collect static files
- Configure persistent media storage
- Configure your LLM provider and GitHub token if AI features are required

### Recommended production variables

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com,api.your-domain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com,https://api.your-domain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true
DJANGO_SECURE_HSTS_PRELOAD=true
```

### Build and deploy

```powershell
npm install
npm run build
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn skillsence.wsgi:application --bind 0.0.0.0:8000
```

The repository includes a `Procfile` for platforms that support Procfile-based startup:

```text
web: python manage.py collectstatic --noinput && python manage.py bootstrap_initial_users && gunicorn skillsence.wsgi:application --bind 0.0.0.0:$PORT
```

### Hosting recommendation

This project is best deployed as:

- frontend on Vercel
- backend on Railway, Render, Fly.io, or a VPS
- PostgreSQL for production data
- S3-compatible storage or Blob storage for uploaded files

## Notes

- Repository analysis still works without `OPENAI_API_KEY`, but AI-written coaching falls back to heuristics.
- `OPENAI_API_BASE` keeps the app provider-agnostic for OpenAI-compatible APIs.
- Local runtime artifacts such as `db.sqlite3`, `media/`, logs, and `__pycache__/` should not be committed.

## Repository Structure

```text
accounts/        auth, onboarding, profile, score APIs
content/         landing page content blocks
skills/          interviews, repo analysis, dashboards, reports, notifications
skillsence/      Django settings, project URLs, WSGI
src/             React frontend
templates/       Django template shell
dist/            built frontend output
manage.py        Django entrypoint
Procfile         production process command
```

## Closing Summary

SkillSense AI is a multi-role placement intelligence platform built around verified evidence, practical workflows, and deployable product surfaces.

If you are extending it, the highest-value next steps are:

- deeper recruiter matching
- stronger university reporting
- more evidence-backed student verification
- production deployment hardening
