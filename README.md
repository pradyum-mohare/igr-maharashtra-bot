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

## Deployment Guide

### Option A: AWS EC2 Mumbai (`ap-south-1`) + Vercel (Recommended for Live Portal Access)
Because `freesearchigrservice.maharashtra.gov.in` drops connections from non-Indian cloud IPs, hosting the backend in **AWS Mumbai (`ap-south-1`)** ensures Playwright reaches the portal reliably while Caddy provisions automatic HTTPS for Vercel.

1. **Launch EC2 Instance in `ap-south-1` (Mumbai)**:
   - AMI: **Ubuntu 24.04 LTS** (`t3.small` recommended, or `t2.micro`/`t3.micro` with 2 GB swap).
   - Security Group inbound rules: allow **TCP 22 (SSH)**, **TCP 80 (HTTP)**, and **TCP 443 (HTTPS)** from `0.0.0.0/0`.
2. **SSH into EC2 and install Docker + 2 GB swap**:
   ```bash
   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker $USER && newgrp docker
   ```
3. **Clone & Start with Automatic HTTPS (`sslip.io`)**:
   Replace `<EC2_PUBLIC_IP>` with your instance's public IPv4 (e.g., `13.232.10.20`):
   ```bash
   git clone https://github.com/pradyum-mohare/igr-maharashtra-bot.git
   cd igr-maharashtra-bot
   cat << 'EOF' > .env
   API_DOMAIN=<EC2_PUBLIC_IP>.sslip.io
   CORS_ORIGINS=https://igr-maharashtra-bot.vercel.app
   POSTGRES_USER=igr_user
   POSTGRES_PASSWORD=change_this_strong_password
   POSTGRES_DB=igr_db
   EOF
   docker compose -f docker-compose.prod.yml up -d --build
   ```
4. **Verify**:
   - `https://<EC2_PUBLIC_IP>.sslip.io/health` → `{"status":"ok"}`
   - `https://<EC2_PUBLIC_IP>.sslip.io/docs` → Swagger API Docs
5. **Point Vercel Frontend to AWS Mumbai**:
   - In Vercel → **Settings → Environment Variables**, set `NEXT_PUBLIC_API_URL` = `https://<EC2_PUBLIC_IP>.sslip.io` and **Redeploy**.

### Option B: Render + Vercel (`render.yaml`)
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
