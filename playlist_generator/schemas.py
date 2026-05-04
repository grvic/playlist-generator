"""Pydantic schemas for structured data throughout the pipeline."""

from typing import Optional, List
from pydantic import BaseModel, Field


class PlaylistRequest(BaseModel):
    """Raw user request parsed into structured form."""
    vibe_description: str
    seed_artists: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    mood_tags: List[str] = Field(default_factory=list)
    target_song_count: Optional[int] = None
    target_duration_minutes: Optional[int] = None
    exclude_keywords: List[str] = Field(default_factory=list)
    include_live: bool = False
    include_remixes: bool = False


class TrackCandidate(BaseModel):
    """A candidate track for the playlist."""
    artist: str
    title: str
    duration_seconds: Optional[int] = None
    source: str = "lastfm"


class PlaylistPlan(BaseModel):
    """The generated plan before YouTube execution."""
    name: str
    description: str
    tracks: List[TrackCandidate]
    estimated_duration_minutes: Optional[int] = None
    estimated_youtube_quota: int = 0


class YouTubeMatch(BaseModel):
    """A matched YouTube video for a track."""
    track: TrackCandidate
    video_id: str
    video_title: str
    channel: str
    duration_seconds: Optional[int] = None
    confidence: float = 0.0


class PlaylistResult(BaseModel):
    """Final result of playlist creation."""
    playlist_id: str
    playlist_url: str
    playlist_name: str
    tracks_added: int
    tracks_skipped: int
    skipped_tracks: List[TrackCandidate] = Field(default_factory=list)
