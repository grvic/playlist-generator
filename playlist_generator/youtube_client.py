"""YouTube Data API v3 client for searching and creating playlists."""

import re
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .config import (
    CLIENT_SECRET_PATH, TOKEN_PATH, YOUTUBE_SCOPES,
    YOUTUBE_SEARCH_COST, YOUTUBE_INSERT_PLAYLIST_COST, YOUTUBE_INSERT_ITEM_COST,
)
from .schemas import TrackCandidate, YouTubeMatch, PlaylistResult

# Keywords to filter out unwanted results
EXCLUDE_KEYWORDS = re.compile(
    r'\b(karaoke|cover|tutorial|lesson|reaction|review|unboxing|parody|8d\s*audio|sped\s*up|slowed|nightcore)\b',
    re.IGNORECASE
)

PREFER_KEYWORDS = re.compile(
    r'(official\s*(video|audio|music\s*video)|topic|vevo|provided to youtube)',
    re.IGNORECASE
)


def authenticate_cli() -> Credentials:
    """Authenticate via CLI (local browser OAuth flow)."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), YOUTUBE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_PATH), YOUTUBE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return creds


def get_youtube_service(creds: Credentials = None):
    """Build YouTube API service."""
    if creds is None:
        creds = authenticate_cli()
    return build("youtube", "v3", credentials=creds)


def search_track(
    youtube,
    track: TrackCandidate,
    exclude_live: bool = True,
) -> YouTubeMatch | None:
    """Search YouTube for a specific track and return the best match."""
    query = f"{track.artist} - {track.title}"
    if exclude_live:
        query += " -live -cover"

    try:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            videoCategoryId="10",  # Music category
            maxResults=5,
        ).execute()
    except Exception:
        return None

    best_match = None
    best_score = -1.0

    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]

        # Skip unwanted content
        if EXCLUDE_KEYWORDS.search(title):
            continue

        # Score the result
        score = 0.0
        title_lower = title.lower()
        artist_lower = track.artist.lower()
        track_lower = track.title.lower()

        # Artist name in title or channel
        if artist_lower in title_lower or artist_lower in channel.lower():
            score += 0.4

        # Track name in title
        if track_lower in title_lower:
            score += 0.3

        # Official content boost
        if PREFER_KEYWORDS.search(title) or PREFER_KEYWORDS.search(channel):
            score += 0.2

        # VEVO or Topic channel boost
        if "vevo" in channel.lower() or "- topic" in channel.lower():
            score += 0.1

        if score > best_score:
            best_score = score
            best_match = YouTubeMatch(
                track=track,
                video_id=video_id,
                video_title=title,
                channel=channel,
                confidence=min(score, 1.0),
            )

    return best_match


def create_playlist(
    youtube,
    title: str,
    description: str,
    privacy: str = "private",
) -> str:
    """Create a new YouTube playlist. Returns playlist ID."""
    response = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {"privacyStatus": privacy},
        },
    ).execute()
    return response["id"]


def add_video_to_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    """Add a video to a playlist. Returns True on success."""
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                },
            },
        ).execute()
        return True
    except Exception:
        return False


def estimate_quota(track_count: int) -> int:
    """Estimate YouTube API quota usage for a given number of tracks."""
    return (
        YOUTUBE_INSERT_PLAYLIST_COST
        + (track_count * YOUTUBE_SEARCH_COST)
        + (track_count * YOUTUBE_INSERT_ITEM_COST)
    )


def execute_playlist_creation(
    youtube,
    title: str,
    description: str,
    matches: list[YouTubeMatch],
) -> PlaylistResult:
    """Create a playlist and add all matched videos."""
    playlist_id = create_playlist(youtube, title, description)
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    added = 0
    skipped = []

    for match in matches:
        if add_video_to_playlist(youtube, playlist_id, match.video_id):
            added += 1
        else:
            skipped.append(match.track)

    return PlaylistResult(
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        playlist_name=title,
        tracks_added=added,
        tracks_skipped=len(skipped),
        skipped_tracks=skipped,
    )
