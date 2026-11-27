# IGR Maharashtra Free Search Automation Bot Agent

Automated property & document search system for the official Maharashtra Department of Registration and Stamps Free Search portal (`https://freesearchigrservice.maharashtra.gov.in/`).

Built with **Next.js (TypeScript + Tailwind CSS)**, **FastAPI**, **Playwright**, and **PostgreSQL**.

---

## Architecture & Repository Structure

```text
igr-maharashtra-bot/
├── docker-compose.yml               # Local PostgreSQL 16 service
├── backend/
│   ├── Dockerfile                   # Production container with Playwright Chromium
│   ├── requirements.txt
│   ├── .env.example
│   ├── storage/documents/           # Stored Index-II PDF / HTML artifacts
│   ├── tests/
│   │   └── test_parser.py           # Parser & selector unit tests
│   └── app/
│       ├── main.py                  # FastAPI entrypoint & lifespan schema recovery
│       ├── config.py                # Pydantic settings
│       ├── database.py              # SQLAlchemy engine & additive schema helper
│       ├── api/jobs.py              # REST endpoints for jobs, CAPTCHA, records & downloads
│       ├── automation/
│       │   ├── selectors.py         # Mode-specific portal DOM selectors
│       │   ├── parser.py            # Index-II normalization & district aliases
│       │   └── bot.py               # Playwright automation & pause/resume CAPTCHA flow
│       ├── models/
│       │   ├── igr_models.py        # SQLAlchemy ORM models
│       │   └── schemas.py           # Pydantic request/response schemas
│       └── services/
│           ├── job_queue.py         # Bounded worker pool & startup job recovery
│           └── storage.py           # Configurable document storage helper
└── frontend/
    ├── Dockerfile
    ├── .env.example
    └── src/
        ├── app/
        │   ├── page.tsx             # Unified search, monitor, job history & records UI
        │   └── records/[id]/page.tsx # Detailed individual registration record view
        ├── components/
        │   ├── SearchForm.tsx       # Property Details & Document Number search form
        │   ├── ActiveJobPanel.tsx   # Live log viewer & manual CAPTCHA prompt
        │   └── StatusBadge.tsx
        └── lib/
            ├── api.ts               # Typed REST client
            └── types.ts             # TypeScript API interfaces
```

---

## Portal Modes & CAPTCHA Workflow

- **Property Details (`PROPERTY`)**: Supports `Mumbai`, `Rest of Maharashtra`, and `Urban Areas` tabs, handling ASP.NET WebForms cascading dropdowns (`Year` -> `District` -> `Tahsil` -> `Village`, or Mumbai's `txtAreaName` autocomplete -> `ddlareaname`) and `Property / Survey / CTS / Gat / Plot No.`.
- **Document Number (`DOCUMENT`)**: Supports `Regular`, `eFiling`, `eRegistration`, and `iSarita 2.0`, cascading `District` -> `Sub-Registrar Office (SRO)` -> `Year` -> `Document Number`.
- **Manual CAPTCHA Verification (Policy-Compliant)**: When CAPTCHA is presented on the portal, the bot captures the image, pauses the live Playwright session with status `AWAITING_CAPTCHA`, and surfaces the CAPTCHA image in the Next.js dashboard (with refresh and visible-browser support). Once submitted, the bot resumes without losing session state.
- **Extraction & Pagination**: Iterates over results pages, opens Index-II views (popup tab, same-page view, or direct download), extracts structured registration fields, saves PDF/HTML files to disk, and deduplicates records in PostgreSQL on `(sro_name, document_number, registration_year)`.

---

## Local Setup

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Backend Setup (FastAPI + Playwright)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Swagger API documentation will be available at `http://localhost:8000/docs`.

### 3. Frontend Setup (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL SQLAlchemy connection string | `postgresql://igr_user:igr_password@localhost:5432/igr_db` |
| `IGR_PORTAL_URL` | Official Maharashtra IGR Free Search URL | `https://freesearchigrservice.maharashtra.gov.in/` |
| `STORAGE_BACKEND` | Storage driver (`local`) | `local` |
| `STORAGE_DIR` | Directory for downloaded Index-II files | `./storage/documents` |
| `HEADLESS` | Run Chromium headless (`false` recommended locally) | `false` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `JOB_CONCURRENCY` | Max concurrent Playwright jobs in queue | `2` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend | `http://localhost:8000` |

---

## API Reference

- `GET /health` — Health check
- `GET /api/metadata/districts` — Supported Maharashtra districts (English & Marathi)
- `GET /api/metadata/sros?district=...` — Cached live portal Sub-Registrar Offices for a district
- `GET /api/metadata/tahsils?district=...` — Cached live portal Tahsils for a district
- `GET /api/metadata/villages?district=...&tahsil=...` — Cached live portal Villages for a tahsil
- `POST /api/jobs` — Queue a new `PROPERTY` or `DOCUMENT` search job
- `GET /api/jobs` — List search jobs (optional `?status=` and `?search_type=` filters)
- `GET /api/jobs/{job_id}` — Detailed job status, CAPTCHA base64 image, logs, and records
- `POST /api/jobs/{job_id}/captcha` — Submit manual CAPTCHA verification and resume job
- `POST /api/jobs/{job_id}/captcha/refresh` — Request a refreshed CAPTCHA image
- `POST /api/jobs/{job_id}/cancel` — Cancel an active or pending job
- `POST /api/jobs/{job_id}/retry` — Retry a failed or cancelled job
- `GET /api/records` — Query saved property records (`?q=`, `?year=`, `?district=`)
- `GET /api/records/{record_id}` — Detailed view of a single registration record
- `GET /api/documents/{doc_id}/download` — Download stored Index-II PDF/HTML document

---

## Running Tests

```bash
cd backend
python -m unittest discover -s tests -v
```

---

## Deployment Guide (Render + Vercel)

### 1. Backend & PostgreSQL on Render (`render.yaml`)
1. Go to [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**.
2. Connect your GitHub repo `pradyum-mohare/igr-maharashtra-bot`. Render reads `render.yaml` automatically to provision:
   - **`igr-postgres`** (Managed PostgreSQL)
   - **`igr-maharashtra-api`** (Docker Web Service from `backend/Dockerfile`, `HEADLESS=true`, health check `/health`)
3. When prompted for **`CORS_ORIGINS`**, enter `*` temporarily (you will update it to your exact Vercel URL in Step 3).
4. Once deployed, verify `https://<your-render-service>.onrender.com/health` and Swagger docs at `https://<your-render-service>.onrender.com/docs`.
   - *Note*: Render Free web services use ephemeral disk storage (downloaded PDFs persist during the running instance; attach a Render Persistent Disk at `/app/storage/documents` on a paid plan for long-term retention).

### 2. Frontend on Vercel
1. Go to [Vercel](https://vercel.com/new) and import `pradyum-mohare/igr-maharashtra-bot`.
2. Set **Root Directory** to **`frontend`** (Framework Preset: **Next.js**).
3. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://<your-render-service>.onrender.com` (no trailing slash).
4. Click **Deploy** to get `https://<your-app>.vercel.app`.

### 3. Lock Down CORS
In Render → `igr-maharashtra-api` → **Environment**, set `CORS_ORIGINS` to `https://<your-app>.vercel.app` and redeploy/save.
