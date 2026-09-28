# Fintrack — Personal Finance Tracker

A full-stack personal finance application built with **React**, **FastAPI**, and **MongoDB**.

## Quick Setup (Linux)

Requires Docker with Compose v2. Everything else runs in containers.

```bash
cp .env.example .env                  # then set SECRET_KEY in .env, e.g. to the output of:
                                      #   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up -d --build          # start MongoDB, backend and frontend
```

Then open: **http://localhost:3000** (API docs: **http://localhost:8000/docs**)

Run the backend tests (unit + integration) in a container:

```bash
docker compose --profile test run --rm backend-tests
docker compose --profile test run --rm backend-tests pytest tests/unit -q   # any pytest arguments
```

Optional local Python environment (IDE support, end-to-end tests). Needs only `python3`; the script fetches
Python 3.12 itself if it isn't installed:

```bash
./scripts/setup-venv.sh               # creates backend/.venv, installs test tools and Playwright Chromium
source backend/.venv/bin/activate
cd backend
pytest                                # unit + property + integration (starts its own MongoDB container)
pytest tests/e2e                      # browser tests against http://localhost:3000
```

Stop everything with `docker compose down` (add `-v` to also delete the MongoDB data).

---

## Testing

548 automated tests in six tiers (unit, property-based, integration, API fuzzing, frontend components,
end-to-end with accessibility checks), plus a load test, security scans and mutation testing. They run in CI
on every push. Backend coverage is 100 %, frontend statement coverage 100 %.

| Run | Command |
|---|---|
| Backend tests with coverage gate | `cd backend && pytest --cov` |
| Frontend tests with coverage gate | `cd frontend && npm run test:coverage` |
| API fuzzing / end-to-end | `cd backend && pytest tests/api` · `pytest tests/e2e` |
| Load test / security scans / mutation | `docker compose --profile perf run --rm locust` · `./scripts/security-scan.sh` · `cd backend && mutmut run` |

---

## Services

| Service   | Port  | Description                          |
|-----------|-------|--------------------------------------|
| Frontend  | 3000  | React app (served via nginx)         |
| Backend   | 8000  | FastAPI REST API                     |
| MongoDB   | 27017 | MongoDB database                     |

API docs available at: **http://localhost:8000/docs**

---

## Features

- **Dashboard** — Monthly summary: income, expenses, balance, savings rate + charts
- **Income & Expenses** — Full CRUD with search, filters, pagination
- **Budgets** — Category spending limits with progress bars and overspend alerts
- **Analytics** — Visual charts: pie, line, bar
- **Reports** — Monthly summaries with CSV export
- **Subscriptions** — Track recurring expenses
- **Settings** — Profile and password management

---

## Architecture

```
finance-tracker/
├── frontend/          # React + TypeScript app
│   ├── src/
│   │   ├── pages/     # Dashboard, Transactions, Budgets, etc.
│   │   ├── components/# Sidebar, Layout
│   │   ├── context/   # AuthContext
│   │   ├── api/       # Axios client
│   │   └── types/     # TypeScript types
│   └── Dockerfile
│
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── routers/   # auth, transactions, categories, budgets, dashboard, reports
│   │   ├── schemas/   # Pydantic models
│   │   └── core/      # config, database, security
│   └── Dockerfile
│
├── mongo-init/        # MongoDB init script (indexes)
└── docker-compose.yml
```

---

## Development (without Docker)

### Backend
```bash
./scripts/setup-venv.sh --no-browsers
source backend/.venv/bin/activate
cd backend
SECRET_KEY=dev-only MONGO_URI=mongodb://localhost:27017 uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### MongoDB
```bash
# Use local MongoDB or: docker run -p 27017:27017 mongo:7.0
```

---

## Environment Variables

**Backend** (Docker Compose reads them from `.env` in the project root; see `.env.example`):
- `SECRET_KEY` — JWT signing key, **required**: `docker compose` refuses to start without it
- `MONGO_URI` — MongoDB connection string (default: `mongodb://mongo:27017`)

**Frontend**:
- `REACT_APP_API_URL` — Backend API URL (default: `http://localhost:8000`)
