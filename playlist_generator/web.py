"""FastAPI web interface for Playlist Generator."""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .generator import generate_plan, generate_festival_plan, execute_plan
from typing import Optional
from .schemas import PlaylistPlan
from .config import YOUTUBE_DAILY_QUOTA, DEFAULT_FESTIVAL_TRACKS_PER_ARTIST

app = FastAPI(title="Playlist Generator", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# In-memory plan storage (single user for now)
_current_plan: Optional[PlaylistPlan] = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with prompt input."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/plan", response_class=HTMLResponse)
async def create_plan(request: Request, prompt: str = Form(...)):
    """Generate a playlist plan from user prompt."""
    global _current_plan
    try:
        plan = generate_plan(prompt)
        _current_plan = plan
        quota_pct = (plan.estimated_youtube_quota / YOUTUBE_DAILY_QUOTA) * 100
        return templates.TemplateResponse("plan.html", {
            "request": request,
            "plan": plan,
            "quota_pct": quota_pct,
            "prompt": prompt,
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": str(e),
        })


@app.post("/create", response_class=HTMLResponse)
async def create_playlist(request: Request):
    """Execute the current plan and create YouTube playlist."""
    global _current_plan
    if not _current_plan:
        return RedirectResponse("/", status_code=302)

    try:
        result = execute_plan(_current_plan)
        plan = _current_plan
        _current_plan = None
        return templates.TemplateResponse("result.html", {
            "request": request,
            "result": result,
            "plan": plan,
        })
    except Exception as e:
        return templates.TemplateResponse("plan.html", {
            "request": request,
            "plan": _current_plan,
            "quota_pct": (_current_plan.estimated_youtube_quota / YOUTUBE_DAILY_QUOTA) * 100,
            "error": str(e),
            "prompt": "",
        })


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/festival", response_class=HTMLResponse)
async def festival_home(request: Request):
    """Festival mode landing page."""
    return templates.TemplateResponse("festival.html", {
        "request": request,
        "default_tracks_per_artist": DEFAULT_FESTIVAL_TRACKS_PER_ARTIST,
    })


@app.post("/festival/plan", response_class=HTMLResponse)
async def festival_plan(
    request: Request,
    artists: str = Form(...),
    tracks_per_artist: int = Form(DEFAULT_FESTIVAL_TRACKS_PER_ARTIST),
    playlist_name: str = Form(""),
):
    """Generate a festival playlist plan."""
    global _current_plan
    try:
        artist_list = [a.strip() for a in artists.split("\n") if a.strip()]
        plan = generate_festival_plan(
            artists=artist_list,
            tracks_per_artist=tracks_per_artist,
            name=playlist_name.strip() or None,
        )
        _current_plan = plan
        quota_pct = (plan.estimated_youtube_quota / YOUTUBE_DAILY_QUOTA) * 100
        return templates.TemplateResponse("plan.html", {
            "request": request,
            "plan": plan,
            "quota_pct": quota_pct,
            "prompt": f"Festival mode: {', '.join(artist_list[:5])}",
        })
    except Exception as e:
        return templates.TemplateResponse("festival.html", {
            "request": request,
            "error": str(e),
            "default_tracks_per_artist": DEFAULT_FESTIVAL_TRACKS_PER_ARTIST,
        })
