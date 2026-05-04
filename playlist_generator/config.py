"""Configuration management via environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CLIENT_SECRET_PATH = PROJECT_ROOT / os.getenv(
    "YOUTUBE_CLIENT_SECRET_PATH",
    "client_secret.json"
)
TOKEN_PATH = PROJECT_ROOT / "token.json"

# Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1-1")

# Last.fm
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"

# MusicBrainz
MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_USER_AGENT = "PlaylistGenerator/0.1.0 (github.com/grvic/playlist-generator)"

# YouTube
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
YOUTUBE_DAILY_QUOTA = 10_000
YOUTUBE_SEARCH_COST = 100
YOUTUBE_INSERT_PLAYLIST_COST = 50
YOUTUBE_INSERT_ITEM_COST = 50

# Defaults
DEFAULT_MAX_TRACKS_PER_ARTIST = 3
DEFAULT_MAX_ARTISTS_EXPANDED = 20
DEFAULT_PLAYLIST_SIZE = 25

# Festival mode
DEFAULT_FESTIVAL_TRACKS_PER_ARTIST = 5
MAX_FESTIVAL_TRACKS_PER_ARTIST = 20
