"""Orchestrates the full playlist generation pipeline."""

import random
from typing import Optional
from .schemas import PlaylistRequest, PlaylistPlan, TrackCandidate, YouTubeMatch, PlaylistResult
from .ai_engine import parse_user_prompt, suggest_additional_artists
from .music_graph import expand_artist_graph, get_top_tracks
from .youtube_client import (
    get_youtube_service, search_track, estimate_quota,
    execute_playlist_creation, authenticate_cli,
)
from .config import (
    DEFAULT_PLAYLIST_SIZE, DEFAULT_MAX_TRACKS_PER_ARTIST,
    DEFAULT_MAX_ARTISTS_EXPANDED, YOUTUBE_DAILY_QUOTA,
    DEFAULT_FESTIVAL_TRACKS_PER_ARTIST, MAX_FESTIVAL_TRACKS_PER_ARTIST,
)


def generate_plan(user_prompt: str) -> PlaylistPlan:
    """Phase 1: Parse prompt and build a track plan without touching YouTube."""

    # Step 1: AI parses the user's natural language prompt
    request = parse_user_prompt(user_prompt)

    # Step 2: Determine target track count
    target_count = request.target_song_count or DEFAULT_PLAYLIST_SIZE
    if request.target_duration_minutes and not request.target_song_count:
        # Estimate ~3.5 min per song average
        target_count = max(5, request.target_duration_minutes // 4)

    # Step 3: AI suggests additional artists if seed list is small
    all_seed_artists = list(request.seed_artists)
    if len(all_seed_artists) < 3:
        ai_suggestions = suggest_additional_artists(request, count=8)
        all_seed_artists.extend(ai_suggestions)

    # Step 4: Expand artist graph via Last.fm + MusicBrainz
    max_artists = min(DEFAULT_MAX_ARTISTS_EXPANDED, target_count)
    expanded_artists = expand_artist_graph(all_seed_artists, max_total=max_artists)

    # Step 5: Collect top tracks from each artist
    all_tracks: list[TrackCandidate] = []
    tracks_per_artist = min(DEFAULT_MAX_TRACKS_PER_ARTIST, max(1, target_count // len(expanded_artists) + 1))

    for artist in expanded_artists:
        tracks = get_top_tracks(artist, limit=tracks_per_artist + 2)
        all_tracks.extend(tracks[:tracks_per_artist + 2])

    # Step 6: Deduplicate and enforce diversity
    seen_titles = set()
    artist_count: dict[str, int] = {}
    final_tracks: list[TrackCandidate] = []

    # Shuffle for variety
    random.shuffle(all_tracks)

    for track in all_tracks:
        key = f"{track.artist.lower()}|{track.title.lower()}"
        if key in seen_titles:
            continue
        if artist_count.get(track.artist.lower(), 0) >= DEFAULT_MAX_TRACKS_PER_ARTIST:
            continue

        seen_titles.add(key)
        artist_count[track.artist.lower()] = artist_count.get(track.artist.lower(), 0) + 1
        final_tracks.append(track)

        if len(final_tracks) >= target_count:
            break

    # Step 7: Build the plan
    estimated_quota = estimate_quota(len(final_tracks))
    estimated_duration = None
    tracks_with_duration = [t for t in final_tracks if t.duration_seconds]
    if tracks_with_duration:
        avg_duration = sum(t.duration_seconds for t in tracks_with_duration) / len(tracks_with_duration)
        estimated_duration = int((avg_duration * len(final_tracks)) / 60)

    plan = PlaylistPlan(
        name=f"🎵 {request.vibe_description[:50]}",
        description=f"AI-generated playlist | Vibe: {request.vibe_description} | "
                    f"Genres: {', '.join(request.genres[:3])} | "
                    f"Moods: {', '.join(request.mood_tags[:3])}",
        tracks=final_tracks,
        estimated_duration_minutes=estimated_duration,
        estimated_youtube_quota=estimated_quota,
    )

    return plan


def execute_plan(plan: PlaylistPlan, min_confidence: float = 0.3) -> PlaylistResult:
    """Phase 2: Search YouTube and create the playlist."""

    # Check quota feasibility
    if plan.estimated_youtube_quota > YOUTUBE_DAILY_QUOTA:
        raise ValueError(
            f"Estimated quota ({plan.estimated_youtube_quota}) exceeds daily limit "
            f"({YOUTUBE_DAILY_QUOTA}). Reduce playlist size to ~"
            f"{YOUTUBE_DAILY_QUOTA // 150} tracks."
        )

    # Authenticate and build service
    creds = authenticate_cli()
    youtube = get_youtube_service(creds)

    # Search for each track
    matches: list[YouTubeMatch] = []
    skipped: list[TrackCandidate] = []

    for track in plan.tracks:
        match = search_track(youtube, track)
        if match and match.confidence >= min_confidence:
            matches.append(match)
        else:
            skipped.append(track)

    if not matches:
        raise ValueError("No tracks could be matched on YouTube. Try different artists or a broader vibe.")

    # Create playlist and add videos
    result = execute_playlist_creation(youtube, plan.name, plan.description, matches)
    result.skipped_tracks.extend(skipped)
    result.tracks_skipped += len(skipped)

    return result


def generate_festival_plan(
    artists: list[str],
    tracks_per_artist: int = DEFAULT_FESTIVAL_TRACKS_PER_ARTIST,
    name: Optional[str] = None,
) -> PlaylistPlan:
    """Generate a playlist plan from an explicit artist list (festival mode).

    No AI expansion — only the provided artists are used.
    Tracks are interleaved round-robin for variety.
    """
    # Validate and normalize inputs
    cleaned = []
    seen = set()
    for a in artists:
        normalized = a.strip()
        if not normalized:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        cleaned.append(normalized)

    if not cleaned:
        raise ValueError("Please provide at least one artist.")

    tracks_per_artist = max(1, min(tracks_per_artist, MAX_FESTIVAL_TRACKS_PER_ARTIST))

    # Fetch top tracks per artist
    artist_tracks: dict[str, list[TrackCandidate]] = {}
    for artist in cleaned:
        tracks = get_top_tracks(artist, limit=tracks_per_artist)
        artist_tracks[artist] = tracks

    # Round-robin interleave for better listening flow
    final_tracks: list[TrackCandidate] = []
    for i in range(tracks_per_artist):
        for artist in cleaned:
            if i < len(artist_tracks[artist]):
                final_tracks.append(artist_tracks[artist][i])

    if not final_tracks:
        raise ValueError("Could not find tracks for any of the provided artists. Check the names and try again.")

    # Build playlist name
    if not name:
        if len(cleaned) <= 4:
            name = f"🎪 Festival Prep: {', '.join(cleaned)}"
        else:
            name = f"🎪 Festival Prep: {', '.join(cleaned[:3])} & {len(cleaned) - 3} more"

    # Summary of what was fetched vs requested
    shortfalls = [
        f"{a} ({len(artist_tracks[a])}/{tracks_per_artist})"
        for a in cleaned
        if len(artist_tracks[a]) < tracks_per_artist
    ]
    description = f"Festival playlist | {len(cleaned)} artists, up to {tracks_per_artist} songs each"
    if shortfalls:
        description += f" | Fewer tracks available: {', '.join(shortfalls)}"

    estimated_quota = estimate_quota(len(final_tracks))
    estimated_duration = None
    tracks_with_duration = [t for t in final_tracks if t.duration_seconds]
    if tracks_with_duration:
        avg_duration = sum(t.duration_seconds for t in tracks_with_duration) / len(tracks_with_duration)
        estimated_duration = int((avg_duration * len(final_tracks)) / 60)

    return PlaylistPlan(
        name=name,
        description=description,
        tracks=final_tracks,
        estimated_duration_minutes=estimated_duration,
        estimated_youtube_quota=estimated_quota,
    )
