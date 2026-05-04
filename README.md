# 🎵 Playlist Generator

AI-powered YouTube playlist generator that creates playlists from natural language vibe descriptions or specific artist lineups.

## Features

- **AI-powered vibe parsing** — Describe a mood, and Azure OpenAI extracts artists, genres, and moods
- **🎪 Festival mode** — Provide a list of artists and get a playlist with their top songs (no AI needed)
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
# AI vibe mode
python run_cli.py generate "Chill lo-fi vibes for studying, 2 hours, like Nujabes and Bonobo"

# Festival mode
python run_cli.py festival "Arctic Monkeys" "Tame Impala" "Billie Eilish" --tracks 5 --name "Primavera 2026"
```

**Web UI:**
```bash
python run_web.py
# Open http://localhost:8000 (AI mode)
# Open http://localhost:8000/festival (Festival mode)
```

## Modes

### AI Vibe Mode (default)
Describe a mood or vibe in natural language. The AI parses your prompt, discovers similar artists, and builds a diverse playlist.

### 🎪 Festival Mode
Provide an explicit list of artists (e.g., a festival lineup). The app fetches their top tracks from Last.fm and creates a playlist with only those artists — no AI expansion, no surprises. Configure how many songs per artist (1–20, default 5). Tracks are interleaved round-robin for variety.

## Architecture

```
User Prompt                          Artist List
    │                                     │
    ▼                                     ▼
Azure OpenAI (parse vibe)          Last.fm (top tracks)
    │                                     │
    ▼                                     │
Last.fm + MusicBrainz (expand)           │
    │                                     │
    └──────────────┬──────────────────────┘
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

