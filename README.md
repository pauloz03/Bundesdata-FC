# Bundesdata-FC

## Prerequisites

Before running the project, make sure you have:

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

Run this command from the project root:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Run the Authentication Backend

Open another terminal:

```bash
cd backend
```

Activate the virtual environment again if needed:

### macOS / Linux

```bash
source ../venv/bin/activate
```

Then run:

```bash
npm install
npm start
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

Create a `.env` file and add the following variables.

## Required Backend Environment Variables

### Cognito — JWKS Verification (`/protected`) + `/auth` Routes

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
```

### AWS Authentication

```env
COGNITO_REGION=
COGNITO_USER_POOL_ID=
COGNITO_APP_CLIENT_ID=
```

### Football API Data

Used only for media and image fetching. The project can still run without it.

```env
FOOTBALL_API_KEY=
```
