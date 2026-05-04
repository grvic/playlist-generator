"""CLI interface for Playlist Generator."""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .generator import generate_plan, generate_festival_plan, execute_plan
from .config import YOUTUBE_DAILY_QUOTA, DEFAULT_FESTIVAL_TRACKS_PER_ARTIST

app = typer.Typer(
    name="playlist-generator",
    help="🎵 AI-powered YouTube playlist generator",
)
console = Console()


@app.command()
def generate(
    prompt: str = typer.Argument(
        ...,
        help="Describe the playlist vibe, length, and preferred artists",
    ),
    auto_confirm: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation and create playlist immediately",
    ),
    min_confidence: float = typer.Option(
        0.3, "--min-confidence", "-c",
        help="Minimum confidence for YouTube matches (0-1)",
    ),
):
    """Generate a YouTube playlist from a vibe description."""

    console.print("\n[bold blue]🎵 Playlist Generator[/bold blue]\n")
    console.print(f"[dim]Prompt: {prompt}[/dim]\n")

    # Phase 1: Generate plan
    with console.status("[bold green]Analyzing your vibe..."):
        plan = generate_plan(prompt)

    # Display the plan
    console.print(Panel(
        f"[bold]{plan.name}[/bold]\n\n{plan.description}",
        title="📋 Playlist Plan",
        border_style="blue",
    ))

    # Track table
    table = Table(title=f"🎶 {len(plan.tracks)} Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Artist", style="cyan")
    table.add_column("Track", style="white")
    table.add_column("Source", style="dim")

    for i, track in enumerate(plan.tracks, 1):
        table.add_row(str(i), track.artist, track.title, track.source)

    console.print(table)

    # Quota info
    quota_pct = (plan.estimated_youtube_quota / YOUTUBE_DAILY_QUOTA) * 100
    quota_color = "green" if quota_pct < 50 else "yellow" if quota_pct < 80 else "red"
    console.print(f"\n[{quota_color}]📊 Estimated YouTube quota: {plan.estimated_youtube_quota}/{YOUTUBE_DAILY_QUOTA} ({quota_pct:.0f}%)[/{quota_color}]")

    if plan.estimated_duration_minutes:
        console.print(f"[dim]⏱️  Estimated duration: ~{plan.estimated_duration_minutes} minutes[/dim]")

    # Confirmation
    if not auto_confirm:
        if not Confirm.ask("\n[bold]Create this playlist on YouTube?[/bold]"):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit()

    # Phase 2: Execute
    with console.status("[bold green]Creating playlist on YouTube..."):
        result = execute_plan(plan, min_confidence=min_confidence)

    # Results
    console.print(Panel(
        f"[bold green]✅ Playlist created![/bold green]\n\n"
        f"[bold]{result.playlist_name}[/bold]\n"
        f"🔗 {result.playlist_url}\n\n"
        f"Added: {result.tracks_added} tracks\n"
        f"Skipped: {result.tracks_skipped} tracks",
        title="🎉 Result",
        border_style="green",
    ))

    if result.skipped_tracks:
        console.print("\n[yellow]Skipped tracks:[/yellow]")
        for t in result.skipped_tracks[:10]:
            console.print(f"  [dim]• {t.artist} - {t.title}[/dim]")


@app.command()
def plan_only(
    prompt: str = typer.Argument(..., help="Describe the playlist vibe"),
):
    """Generate and display a plan without creating the playlist."""
    console.print("\n[bold blue]🎵 Plan Preview[/bold blue]\n")

    with console.status("[bold green]Analyzing your vibe..."):
        plan = generate_plan(prompt)

    console.print(Panel(
        f"[bold]{plan.name}[/bold]\n\n{plan.description}",
        title="📋 Plan",
        border_style="blue",
    ))

    table = Table(title=f"🎶 {len(plan.tracks)} Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Artist", style="cyan")
    table.add_column("Track", style="white")

    for i, track in enumerate(plan.tracks, 1):
        table.add_row(str(i), track.artist, track.title)

    console.print(table)
    console.print(f"\n[dim]Quota estimate: {plan.estimated_youtube_quota} units[/dim]")


@app.command()
def festival(
    artists: List[str] = typer.Argument(
        ...,
        help="Artists to include (space-separated, use quotes for multi-word names)",
    ),
    tracks_per_artist: int = typer.Option(
        DEFAULT_FESTIVAL_TRACKS_PER_ARTIST, "--tracks", "-t",
        help="Number of top songs per artist (1-20)",
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n",
        help="Custom playlist name (auto-generated if not provided)",
    ),
    auto_confirm: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation and create playlist immediately",
    ),
    min_confidence: float = typer.Option(
        0.3, "--min-confidence", "-c",
        help="Minimum confidence for YouTube matches (0-1)",
    ),
):
    """Create a playlist from a specific artist lineup (festival prep mode)."""

    console.print("\n[bold orange3]🎪 Festival Mode[/bold orange3]\n")
    console.print(f"[dim]Artists: {', '.join(artists)}[/dim]")
    console.print(f"[dim]Tracks per artist: {tracks_per_artist}[/dim]\n")

    # Phase 1: Generate plan
    with console.status("[bold green]Fetching top tracks..."):
        plan = generate_festival_plan(artists, tracks_per_artist, name)

    # Display the plan
    console.print(Panel(
        f"[bold]{plan.name}[/bold]\n\n{plan.description}",
        title="📋 Festival Playlist Plan",
        border_style="orange3",
    ))

    # Track table
    table = Table(title=f"🎶 {len(plan.tracks)} Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Artist", style="cyan")
    table.add_column("Track", style="white")

    for i, track in enumerate(plan.tracks, 1):
        table.add_row(str(i), track.artist, track.title)

    console.print(table)

    # Quota info
    quota_pct = (plan.estimated_youtube_quota / YOUTUBE_DAILY_QUOTA) * 100
    quota_color = "green" if quota_pct < 50 else "yellow" if quota_pct < 80 else "red"
    console.print(f"\n[{quota_color}]📊 Estimated YouTube quota: {plan.estimated_youtube_quota}/{YOUTUBE_DAILY_QUOTA} ({quota_pct:.0f}%)[/{quota_color}]")

    if plan.estimated_duration_minutes:
        console.print(f"[dim]⏱️  Estimated duration: ~{plan.estimated_duration_minutes} minutes[/dim]")

    # Confirmation
    if not auto_confirm:
        if not Confirm.ask("\n[bold]Create this playlist on YouTube?[/bold]"):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit()

    # Phase 2: Execute
    with console.status("[bold green]Creating playlist on YouTube..."):
        result = execute_plan(plan, min_confidence=min_confidence)

    # Results
    console.print(Panel(
        f"[bold green]✅ Playlist created![/bold green]\n\n"
        f"[bold]{result.playlist_name}[/bold]\n"
        f"🔗 {result.playlist_url}\n\n"
        f"Added: {result.tracks_added} tracks\n"
        f"Skipped: {result.tracks_skipped} tracks",
        title="🎉 Result",
        border_style="green",
    ))

    if result.skipped_tracks:
        console.print("\n[yellow]Skipped tracks:[/yellow]")
        for t in result.skipped_tracks[:10]:
            console.print(f"  [dim]• {t.artist} - {t.title}[/dim]")


if __name__ == "__main__":
    app()
