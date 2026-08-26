# Bundesdata-FC

3D tracking analytics for Bundesliga matches. Sign in, open the dashboard, then use Performance to inspect possession and player fatigue from local match files.

## Prerequisites

* Python 3.9+
* Node.js
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

From the project root, with the virtual environment active:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is at `http://localhost:8000` (`/health` for a quick check).

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/auth`, `/matches`, and `/users` to the API. No frontend env file is required.

Open the app, sign up or log in, then use:

* **Dashboard** — standings and dashboard invitations
* **Performance** — match possession pitch and per-player fatigue

---

## Match Data

Tracking files live in `backend/data/parquet/`. A match appears in Performance only when its parquet is present.

| Match ID | File |
|---|---|
| `union_bayern` | `FCU-FCB.parquet` |
| `frankfurt_bayern` | `SGE-FCB.parquet` |
| `frankfurt_union` | `SGE-FCU.parquet` |
| `dortmund_stuttgart` | `BVB-VFB.parquet` |
| `bayern_hamburg` | `FCB-HSV.parquet` |

Optional XML identity files can go in `backend/data/xml/`. Possession results are cached as JSON under `backend/data/precomputed/<match_id>/possession.json` (Union–Bayern and Frankfurt–Bayern are already included).

---

## Compute Match Information

From the project root, with the virtual environment active:

```bash
python backend/precompute.py --match union_bayern
```

All registered matches:

```bash
python backend/precompute.py --all
```

Computation can take a while. Drop the parquet files into `backend/data/parquet/` first (see the table above).
