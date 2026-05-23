from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import config

#Validate config at startup
config.validate()

app = FastAPI(
    title="SkeletonIQ API",
    description="3D biomechanical performance analytics for Bundesliga analysts",
    version="0.1.0",
)

# ── CORS — allow local React dev server 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# Matches
@app.get("/matches")
def get_matches():
    """Return list of available matches."""
    return {
        "matches": [
            {"id": match_id, "label": match_id.replace("_", " ").title()}
            for match_id in config.MATCHES.keys()
        ]
    }


#  Placeholder routes — filled in as we build each service 
@app.get("/matches/{match_id}/players")
def get_players(match_id: str):
    return {"match_id": match_id, "players": [], "message": "not implemented yet"}


@app.get("/matches/{match_id}/players/{jersey}/fatigue")
def get_fatigue(match_id: str, jersey: int, team: int = 1):
    return {"match_id": match_id, "jersey": jersey, "team": team, "curve": [], "message": "not implemented yet"}


@app.get("/matches/{match_id}/players/{jersey}/events")
def get_events(match_id: str, jersey: int, team: int = 1):
    return {"match_id": match_id, "jersey": jersey, "events": [], "message": "not implemented yet"}