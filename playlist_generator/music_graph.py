"""Music discovery using Last.fm and MusicBrainz APIs."""

import time
import httpx
from .config import (
    LASTFM_API_KEY, LASTFM_BASE_URL,
    MUSICBRAINZ_BASE_URL, MUSICBRAINZ_USER_AGENT,
    DEFAULT_MAX_TRACKS_PER_ARTIST,
)
from typing import Optional, List, Dict
from .schemas import TrackCandidate

# Rate limiting state
_lastfm_last_call = 0.0
_musicbrainz_last_call = 0.0


def _rate_limit_lastfm():
    """Enforce Last.fm rate limit (5 req/sec)."""
    global _lastfm_last_call
    elapsed = time.time() - _lastfm_last_call
    if elapsed < 0.2:
        time.sleep(0.2 - elapsed)
    _lastfm_last_call = time.time()


def _rate_limit_musicbrainz():
    """Enforce MusicBrainz rate limit (1 req/sec)."""
    global _musicbrainz_last_call
    elapsed = time.time() - _musicbrainz_last_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _musicbrainz_last_call = time.time()


def get_similar_artists(artist: str, limit: int = 10) -> list[str]:
    """Get similar artists from Last.fm."""
    if not LASTFM_API_KEY:
        return []

    _rate_limit_lastfm()
    try:
        resp = httpx.get(
            LASTFM_BASE_URL,
            params={
                "method": "artist.getsimilar",
                "artist": artist,
                "api_key": LASTFM_API_KEY,
                "format": "json",
                "limit": limit,
            },
            timeout=10,
        )
        data = resp.json()
        if "similarartists" in data and "artist" in data["similarartists"]:
            return [a["name"] for a in data["similarartists"]["artist"]]
    except Exception:
        pass
    return []


def get_top_tracks(artist: str, limit: int = DEFAULT_MAX_TRACKS_PER_ARTIST) -> list[TrackCandidate]:
    """Get top tracks for an artist from Last.fm."""
    if not LASTFM_API_KEY:
        return []

    _rate_limit_lastfm()
    try:
        resp = httpx.get(
            LASTFM_BASE_URL,
            params={
                "method": "artist.gettoptracks",
                "artist": artist,
                "api_key": LASTFM_API_KEY,
                "format": "json",
                "limit": limit,
            },
            timeout=10,
        )
        data = resp.json()
        tracks = []
        if "toptracks" in data and "track" in data["toptracks"]:
            for t in data["toptracks"]["track"][:limit]:
                duration = int(t.get("duration", 0)) or None
                tracks.append(TrackCandidate(
                    artist=artist,
                    title=t["name"],
                    duration_seconds=duration,
                    source="lastfm",
                ))
        return tracks
    except Exception:
        return []


def get_artist_tags(artist: str) -> list[str]:
    """Get genre/mood tags for an artist from Last.fm."""
    if not LASTFM_API_KEY:
        return []

    _rate_limit_lastfm()
    try:
        resp = httpx.get(
            LASTFM_BASE_URL,
            params={
                "method": "artist.gettoptags",
                "artist": artist,
                "api_key": LASTFM_API_KEY,
                "format": "json",
            },
            timeout=10,
        )
        data = resp.json()
        if "toptags" in data and "tag" in data["toptags"]:
            return [t["name"] for t in data["toptags"]["tag"][:10]]
    except Exception:
        pass
    return []


def musicbrainz_search_artist(artist: str) -> Optional[dict]:
    """Search MusicBrainz for artist disambiguation."""
    _rate_limit_musicbrainz()
    try:
        resp = httpx.get(
            f"{MUSICBRAINZ_BASE_URL}/artist/",
            params={"query": artist, "fmt": "json", "limit": 1},
            headers={"User-Agent": MUSICBRAINZ_USER_AGENT},
            timeout=10,
        )
        data = resp.json()
        if data.get("artists"):
            return data["artists"][0]
    except Exception:
        pass
    return None


def musicbrainz_get_relations(mbid: str) -> list[str]:
    """Get related artists from MusicBrainz by MBID."""
    _rate_limit_musicbrainz()
    try:
        resp = httpx.get(
            f"{MUSICBRAINZ_BASE_URL}/artist/{mbid}",
            params={"fmt": "json", "inc": "artist-rels"},
            headers={"User-Agent": MUSICBRAINZ_USER_AGENT},
            timeout=10,
        )
        data = resp.json()
        related = []
        for rel in data.get("relations", []):
            if rel.get("type") in ("influenced by", "member of band", "collaboration"):
                target = rel.get("artist", {})
                if target.get("name"):
                    related.append(target["name"])
        return related
    except Exception:
        return []


def expand_artist_graph(
    seed_artists: list[str],
    max_total: int = 20,
) -> list[str]:
    """Expand seed artists using Last.fm similarity + MusicBrainz relations.
    
    Returns a deduplicated list of artists (seeds + discovered).
    """
    seen = set(a.lower() for a in seed_artists)
    result = list(seed_artists)

    for artist in seed_artists:
        if len(result) >= max_total:
            break

        # Last.fm similar artists (primary source)
        similar = get_similar_artists(artist, limit=8)
        for s in similar:
            if s.lower() not in seen and len(result) < max_total:
                seen.add(s.lower())
                result.append(s)

        # MusicBrainz relations (secondary, for disambiguation)
        mb = musicbrainz_search_artist(artist)
        if mb and mb.get("id"):
            relations = musicbrainz_get_relations(mb["id"])
            for r in relations:
                if r.lower() not in seen and len(result) < max_total:
                    seen.add(r.lower())
                    result.append(r)

    return result
