"""FastAPI entrypoint. Run from `backend`: `./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000` (or `npm run api`)."""

from fastapi import FastAPI

app = FastAPI(title="pj-data API", version="0.1.0")


@app.get("/")
def root():
    return {"status": "ok", "service": "pj-data"}


@app.get("/health")
def health():
    return {"status": "healthy"}
