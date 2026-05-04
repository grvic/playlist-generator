"""Pydantic schemas for structured data throughout the pipeline."""

from pydantic import BaseModel, Field


class PlaylistRequest(BaseModel):
    """Raw user request parsed into structured form."""
    vibe_description: str
    seed_artists: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    mood_tags: list[str] = Field(default_factory=list)
    target_song_count: int | None = None
    target_duration_minutes: int | None = None
    exclude_keywords: list[str] = Field(default_factory=list)
    include_live: bool = False
    include_remixes: bool = False


class TrackCandidate(BaseModel):
    """A candidate track for the playlist."""
    artist: str
    title: str
    duration_seconds: int | None = None
    source: str = "lastfm"  # lastfm, musicbrainz, ai


class PlaylistPlan(BaseModel):
    """The generated plan before YouTube execution."""
    name: str
    description: str
    tracks: list[TrackCandidate]
    estimated_duration_minutes: int | None = None
    estimated_youtube_quota: int = 0


class YouTubeMatch(BaseModel):
    """A matched YouTube video for a track."""
    track: TrackCandidate
    video_id: str
    video_title: str
    channel: str
    duration_seconds: int | None = None
    confidence: float = 0.0  # 0-1 how confident the match is


class PlaylistResult(BaseModel):
    """Final result of playlist creation."""
    playlist_id: str
    playlist_url: str
    playlist_name: str
    tracks_added: int
    tracks_skipped: int
    skipped_tracks: list[TrackCandidate] = Field(default_factory=list)
