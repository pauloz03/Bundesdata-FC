# Bundesdata-FC

## Prerequisites

Before running the project, make sure you have:

* Python 3.9+
* Node.js (for frontend development)
* PostgreSQL (for auth — coming soon)
* A virtual environment tool such as `venv`

---

## Clone the Repository

```bash
git clone https://github.com/pauloz03/Bundesdata-FC.git
cd Bundesdata-FC
```

---

## Create and Activate a Virtual Environment

```bash
python -m venv venv
```

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

---

## Start the FastAPI Server

From the `backend` directory:

```bash
cd backend
./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or from the project root if `main` is on your Python path:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## Compute Match Information

Pick the desired match and run:

```bash
python backend/precompute.py --match union_bayern
```

> Note: Computation time can be long.

### Faster Computation with Local Parquet Files

Download the parquet files and point `LOCAL_PARQUET_DIR` to that folder:

```bash
LOCAL_PARQUET_DIR="/absolute/path/to/parquet-folder" python backend/precompute.py --match union_bayern
```

---

# Environment Variables

Create a `backend/.env` file. See `backend/.env.example` for the template.

## PostgreSQL Auth (to be implemented)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/bundesdata
JWT_SECRET=your-secret-key
```

## Local Demo Mode

Skip auth and serve matches from local parquet only:

```env
SKIP_AUTH=1
```

## Football API Data (optional)

Used only for media and image fetching. The project can still run without it.

```env
FOOTBALL_API_KEY=
```

## AWS / S3 (optional)

Only needed if reading match data from S3:

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
```
