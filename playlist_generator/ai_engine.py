"""Azure OpenAI integration for parsing user prompts into structured playlist requests."""

import json
from openai import AzureOpenAI
from .config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL
from .schemas import PlaylistRequest

SYSTEM_PROMPT = """You are a music expert assistant. Given a user's description of a playlist they want, 
extract structured information. Return ONLY valid JSON with these fields:

{
  "vibe_description": "short summary of the mood/vibe",
  "seed_artists": ["list of specific artists mentioned or strongly implied"],
  "genres": ["genres that match the description"],
  "mood_tags": ["mood descriptors like 'energetic', 'melancholic', 'chill'"],
  "target_song_count": number or null,
  "target_duration_minutes": number or null (convert hours to minutes),
  "exclude_keywords": ["things to avoid like 'live', 'acoustic' if mentioned"],
  "include_live": false,
  "include_remixes": false
}

If the user mentions "2 hours", set target_duration_minutes to 120.
If they say "30 songs", set target_song_count to 30.
If neither is specified, set target_song_count to 25.
Infer artists from context even if not explicitly named (e.g., "something like Radiohead" → seed_artists: ["Radiohead"]).
Be generous with mood_tags and genres - the more the better for discovery."""


def get_client() -> AzureOpenAI:
    """Create Azure OpenAI client."""
    # Parse the endpoint to extract base URL and deployment info
    # The endpoint format is: https://host/api/projects/{project}/openai/v1/responses
    # We need: https://host/api/projects/{project}
    base = AZURE_OPENAI_ENDPOINT
    if "/openai/" in base:
        base = base.split("/openai/")[0]

    return AzureOpenAI(
        azure_endpoint=base,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-12-01-preview",
    )


def parse_user_prompt(user_prompt: str) -> PlaylistRequest:
    """Use Azure OpenAI to parse a natural language prompt into a structured PlaylistRequest."""
    client = get_client()

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return PlaylistRequest(**data)


def suggest_additional_artists(request: PlaylistRequest, count: int = 10) -> list[str]:
    """Ask AI to suggest more artists based on the parsed request."""
    client = get_client()

    prompt = f"""Based on this playlist vibe, suggest {count} artists that would fit well.
    
Vibe: {request.vibe_description}
Genres: {', '.join(request.genres)}
Moods: {', '.join(request.mood_tags)}
Seed artists: {', '.join(request.seed_artists)}

Return ONLY a JSON array of artist names, e.g. ["Artist 1", "Artist 2", ...]
Do not repeat the seed artists. Focus on variety while maintaining the vibe."""

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a music recommendation expert. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    # Handle both {"artists": [...]} and plain [...]
    if isinstance(data, list):
        return data
    if "artists" in data:
        return data["artists"]
    # Try first list value
    for v in data.values():
        if isinstance(v, list):
            return v
    return []
