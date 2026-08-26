"""
FastAPI entrypoint.

Run from backend/:
  ./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import auth, matches, users

config.validate()

app = FastAPI(
    title="SkeletonIQ API",
    description="3D biomechanical performance analytics for Bundesliga analysts",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/explore")
def explore():
    """Matches for the Explore page."""
    return {
        "matches": [
            {
                "id":        mid,
                "label":     config.MATCH_METADATA.get(mid, {}).get("label", mid),
                "date":      config.MATCH_METADATA.get(mid, {}).get("date"),
                "home_team": config.MATCH_METADATA.get(mid, {}).get("home_team"),
                "away_team": config.MATCH_METADATA.get(mid, {}).get("away_team"),
            }
            for mid in config.MATCHES
            if mid in config.MATCH_METADATA
        ]
    }
