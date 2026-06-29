# Fintrack — Personal Finance Tracker

A full-stack personal finance application built with **React**, **FastAPI**, and **MongoDB**.

## Quick Start

```bash
docker-compose up --build
```

Then open: **http://localhost:3000**

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
cd backend
pip install -r requirements.txt
pip install pydantic-settings
uvicorn app.main:app --reload
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

**Backend** (set in docker-compose or .env):
- `MONGO_URI` — MongoDB connection string (default: `mongodb://mongo:27017`)
- `SECRET_KEY` — JWT signing key (change in production!)

**Frontend**:
- `REACT_APP_API_URL` — Backend API URL (default: `http://localhost:8000`)
