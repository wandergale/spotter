# ELD Trip Planner

A full-stack web application for planning ELD (Electronic Logging Device) trips. Built with Django REST Framework (backend) and React + TypeScript + Vite (frontend).

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

---

## Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your SECRET_KEY and other values

# Run migrations
python manage.py migrate

# Start development server (runs on http://localhost:8000)
python manage.py runserver
```

### Backend environment variables (`.env`)

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | required |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `NOMINATIM_USER_AGENT` | User agent for Nominatim geocoding | `eld-trip-planner/1.0` |
| `DATABASE_PATH` | SQLite database file path | `db.sqlite3` |

---

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and set VITE_API_URL to your backend URL

# Start development server (runs on http://localhost:5173)
npm run dev
```

### Frontend environment variables (`.env`)

| Variable | Description | Example |
|---|---|---|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |

---

## Running Both Services

Open two terminals:

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Build for Production

**Frontend:**
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

**Backend:**
```bash
# Uses gunicorn + whitenoise for static file serving
gunicorn config.wsgi:application
```
