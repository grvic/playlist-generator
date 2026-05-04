# 🎵 Playlist Generator

AI-powered YouTube playlist generator that creates playlists from natural language vibe descriptions.

## Features

- **AI-powered vibe parsing** — Describe a mood, and Azure OpenAI extracts artists, genres, and moods
- **Smart artist discovery** — Last.fm + MusicBrainz build a relational graph of similar artists
- **Intelligent YouTube matching** — Filters out covers, karaoke, tutorials; prefers official uploads
- **Quota-aware** — Estimates YouTube API usage before executing; preview before committing
- **Two-phase flow** — Plan → Preview → Create (saves quota, improves quality)
- **CLI + Web UI** — Use from terminal or browser

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your keys:
- **Azure OpenAI** — endpoint, API key, model name
- **Last.fm** — Get a free API key at https://www.last.fm/api/account/create
- **YouTube** — OAuth client secret JSON (already in folder)

### 3. Run

**CLI:**
```bash
python run_cli.py "Chill lo-fi vibes for studying, 2 hours, like Nujabes and Bonobo"
```

**Web UI:**
```bash
python run_web.py
# Open http://localhost:8000
```

## Architecture

```
User Prompt
    │
    ▼
Azure OpenAI (parse vibe → structured request)
    │
    ▼
Last.fm + MusicBrainz (expand artist graph, get tracks)
    │
    ▼
Plan Preview (show tracks, estimate quota)
    │
    ▼ (user confirms)
YouTube Data API (search + create playlist)
    │
    ▼
🎶 YouTube Playlist URL
```

## Quota Budget

| Operation | Cost | Example (25 songs) |
|-----------|------|---------------------|
| search.list | 100 units | 2500 |
| playlists.insert | 50 units | 50 |
| playlistItems.insert | 50 units | 1250 |
| **Total** | | **~3800 units** |

Free daily quota: 10,000 units (no billing required).

