"""
Command-line interface for Daily Digest Vibe.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, List
from .hn_client import create_client
from .storage import get_storage, StoryStorage
from .ai_grouping import create_grouper
from .preference_learner import create_preference_learner
from .digest_generator import create_digest_generator
from .config import get_config, Config
from .models import Story


console = Console()


@click.group()
@click.option('--config', '-c', 'config_path', help='Path to config file')
def cli(config_path: Optional[str] = None):
    """Daily Digest Vibe - A personalized Hacker News daily digest tool."""
    if config_path:
        # Reset config with custom path
        from .config import reset_config
        reset_config()
        # This will be handled by the subcommands
        pass


@cli.command()
def setup():
    """Initialize the application and create default configuration."""
    console.print(Panel.fit("[bold green]Daily Digest Vibe Setup[/bold green]"))
    
    # Create config
    config = Config()
    config.save()
    
    console.print("[green]✓[/green] Created default configuration file: config.yaml")
    console.print("[green]✓[/green] Created data directory")
    
    # Create a sample config message
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit config.yaml to customize settings")
    console.print("2. Set OPENAI_API_KEY environment variable for AI features")
    console.print("3. Run 'python -m daily_digest fetch' to fetch stories")
    console.print("4. Run 'python -m daily_digest digest' to generate a digest")


@cli.command()
@click.option('--limit', '-n', default=500, help='Number of stories to fetch')
@click.option('--delay', '-d', default=0.1, help='Delay between requests in seconds')
@click.option('--force', '-f', is_flag=True, help='Force refetch all stories')
def fetch(limit: int, delay: float, force: bool):
    """Fetch top stories from Hacker News."""
    console.print(Panel.fit("[bold blue]Fetching Stories[/bold blue]"))
    
    client = create_client()
    storage = get_storage()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Get top story IDs
        task = progress.add_task("Fetching top story IDs...", total=None)
        story_ids = client.get_top_story_ids(limit)
        progress.update(task, description="Fetched story IDs")
        
        # Check which stories we already have
        existing_ids = set(storage.get_story_ids())
        new_ids = [sid for sid in story_ids if sid not in existing_ids]
        
        if not force and new_ids:
            console.print(f"[yellow]Found {len(new_ids)} new stories to fetch[/yellow]")
            story_ids = new_ids
        else:
            console.print(f"[blue]Fetching {len(story_ids)} stories[/blue]")
        
        # Fetch stories
        task = progress.add_task("Fetching stories...", total=len(story_ids))
        stories = []
        
        for i, story_id in enumerate(story_ids):
            story = client.get_story(story_id)
            if story:
                stories.append(story)
                progress.update(task, advance=1, description=f"Fetched {i+1}/{len(story_ids)} stories")
            else:
                progress.update(task, advance=1, description=f"Skipped story {story_id}")
        
        # Save stories
        task = progress.add_task("Saving stories...", total=len(stories))
        for i, story in enumerate(stories):
            storage.save_story(story)
            progress.update(task, advance=1, description=f"Saved {i+1}/{len(stories)} stories")
    
    console.print(f"[green]✓[/green] Fetched and saved {len(stories)} stories")


@cli.command()
@click.option('--hours', '-h', default=24, help='Number of hours to look back')
@click.option('--limit', '-n', default=None, type=int, help='Limit number of stories to process')
def process(hours: int, limit: Optional[int]):
    """Process stories: generate embeddings and assign topics."""
    console.print(Panel.fit("[bold blue]Processing Stories[/bold blue]"))
    
    storage = get_storage()
    grouper = create_grouper()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Get recent stories
        task = progress.add_task("Loading stories...", total=None)
        stories = storage.get_recent_stories(hours=hours)
        progress.update(task, description=f"Loaded {len(stories)} stories")
        
        if limit:
            stories = stories[:limit]
        
        if not stories:
            console.print("[yellow]No stories found to process[/yellow]")
            return
        
        # Generate embeddings and assign topics
        task = progress.add_task("Generating embeddings...", total=None)
        stories_with_topics = grouper.assign_topics(stories)
        progress.update(task, description="Generated embeddings and topics")
        
        # Save updated stories
        task = progress.add_task("Saving stories...", total=len(stories_with_topics))
        for i, story in enumerate(stories_with_topics):
            storage.update_story(story)
            progress.update(task, advance=1, description=f"Saved {i+1}/{len(stories_with_topics)} stories")
    
    console.print(f"[green]✓[/green] Processed {len(stories_with_topics)} stories")


@cli.command()
@click.option('--n-clusters', '-n', default=None, type=int, help='Number of clusters to use')
@click.option('--format', '-f', default='text', type=click.Choice(['text', 'html', 'md']))
@click.option('--output', '-o', default=None, help='Output file path')
@click.option('--hours', '-h', default=24, help='Number of hours to look back')
def digest(n_clusters: Optional[int], format: str, output: Optional[str], hours: int):
    """Generate a daily digest."""
    console.print(Panel.fit("[bold blue]Generating Daily Digest[/bold blue]"))
    
    generator = create_digest_generator()
    storage = get_storage()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Get recent stories
        task = progress.add_task("Loading stories...", total=None)
        stories = storage.get_recent_stories(hours=hours)
        progress.update(task, description=f"Loaded {len(stories)} stories")
        
        # Generate digest
        task = progress.add_task("Generating digest...", total=None)
        digest = generator.generate_digest(stories, n_clusters)
        progress.update(task, description="Generated digest")
        
        # Generate output
        if format == 'text':
            content = generator.generate_text_digest(digest)
        elif format == 'html':
            content = generator.generate_html_digest(digest)
        else:  # markdown
            content = generator.generate_markdown_digest(digest)
        
        progress.update(task, description="Generated output")
    
    # Output
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        console.print(f"[green]✓[/green] Digest saved to {output}")
    else:
        console.print(content)
    
    # Show statistics
    stats = generator.get_digest_statistics(digest)
    console.print("\n[bold]Digest Statistics:[/bold]")
    for key, value in stats.items():
        console.print(f"  {key}: {value}")


@cli.command()
def run():
    """Run the complete pipeline: fetch, process, and generate digest."""
    console.print(Panel.fit("[bold blue]Running Complete Pipeline[/bold blue]"))
    
    # Run fetch
    console.print("\n[bold]Step 1: Fetching stories[/bold]")
    from .cli import fetch
    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(fetch, ['--limit', '500'])
    if result.exit_code != 0:
        console.print(f"[red]Error fetching stories: {result.output}[/red]")
        return
    console.print(result.output)
    
    # Run process
    console.print("\n[bold]Step 2: Processing stories[/bold]")
    from .cli import process
    result = runner.invoke(process, ['--hours', '24'])
    if result.exit_code != 0:
        console.print(f"[red]Error processing stories: {result.output}[/red]")
        return
    console.print(result.output)
    
    # Run digest
    console.print("\n[bold]Step 3: Generating digest[/bold]")
    result = runner.invoke(digest, ['--format', 'text'])
    if result.exit_code != 0:
        console.print(f"[red]Error generating digest: {result.output}[/red]")
        return
    console.print(result.output)
    
    console.print("\n[green]✓[/green] Pipeline completed successfully!")


@cli.command()
@click.option('--hours', '-h', default=24, help='Number of hours to look back')
@click.option('--limit', '-n', default=50, help='Number of stories to show')
def list_stories(hours: int, limit: int):
    """List recent stories."""
    storage = get_storage()
    stories = storage.get_recent_stories(hours=hours)
    
    table = Table(title="Recent Stories")
    table.add_column("ID", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Title", style="bold")
    table.add_column("Author", style="dim")
    table.add_column("Domain", style="dim")
    table.add_column("Age (h)", justify="right")
    table.add_column("Topic", style="cyan")
    table.add_column("Read", justify="center")
    
    for story in stories[:limit]:
        read_status = "✓" if story.user_read else " "
        domain = story.url_domain or ""
        topic = story.topic_label or ""
        age = f"{story.age_hours:.1f}"
        
        table.add_row(
            str(story.id),
            str(story.score),
            story.title[:60] + "..." if len(story.title) > 60 else story.title,
            story.by or "",
            domain,
            age,
            topic,
            read_status
        )
    
    console.print(table)
    console.print(f"\n[dim]Showing {min(limit, len(stories))} of {len(stories)} stories[/dim]")


@cli.command()
@click.argument('story_id', type=int)
def show_story(story_id: int):
    """Show details for a specific story."""
    storage = get_storage()
    story = storage.get_story(story_id)
    
    if not story:
        console.print(f"[red]Story {story_id} not found[/red]")
        return
    
    table = Table(title=f"Story {story.id}")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    
    table.add_row("Title", story.title)
    table.add_row("URL", story.url or "")
    table.add_row("Score", str(story.score))
    table.add_row("Author", story.by or "")
    table.add_row("Domain", story.url_domain or "")
    table.add_row("Time", datetime.fromtimestamp(story.time).strftime('%Y-%m-%d %H:%M:%S UTC'))
    table.add_row("Age", f"{story.age_hours:.1f} hours")
    table.add_row("Comments", str(story.descendants))
    table.add_row("Type", story.type)
    table.add_row("Topic", story.topic_label or "")
    table.add_row("Cluster ID", str(story.cluster_id) if story.cluster_id else "")
    table.add_row("Read", "Yes" if story.user_read else "No")
    table.add_row("Hidden", "Yes" if story.user_hidden else "No")
    table.add_row("Fetched At", story.fetched_at.strftime('%Y-%m-%d %H:%M:%S UTC'))
    
    console.print(table)


@cli.command()
@click.argument('story_id', type=int)
@click.option('--action', '-a', type=click.Choice(['read', 'hide', 'unhide', 'interest', 'uninterest']))
def story_action(story_id: int, action: str):
    """Perform an action on a story (mark as read, hide, etc.)."""
    storage = get_storage()
    learner = create_preference_learner()
    story = storage.get_story(story_id)
    
    if not story:
        console.print(f"[red]Story {story_id} not found[/red]")
        return
    
    if action == 'read':
        learner.mark_read(story)
        console.print(f"[green]✓[/green] Marked story {story_id} as read")
    elif action == 'hide':
        learner.mark_hidden(story)
        console.print(f"[green]✓[/green] Marked story {story_id} as hidden")
    elif action == 'unhide':
        story.user_hidden = False
        storage.update_story(story)
        console.print(f"[green]✓[/green] Unhidden story {story_id}")
    elif action == 'interest':
        learner.mark_interested(story, interested=True)
        console.print(f"[green]✓[/green] Marked story {story_id} as interested")
    elif action == 'uninterest':
        learner.mark_interested(story, interested=False)
        console.print(f"[green]✓[/green] Marked story {story_id} as not interested")


@cli.command()
def preferences():
    """Show and manage user preferences."""
    learner = create_preference_learner()
    stats = learner.get_statistics()
    
    table = Table(title="User Preferences")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    
    table.add_row("Total Stories Read", str(stats['total_stories_read']))
    table.add_row("Total Stories Hidden", str(stats['total_stories_hidden']))
    table.add_row("Topics Tracked", str(stats['topic_count']))
    table.add_row("Domains Tracked", str(stats['domain_count']))
    table.add_row("Authors Tracked", str(stats['author_count']))
    table.add_row("Keywords Tracked", str(stats['keyword_count']))
    table.add_row("Min Score", str(stats['min_score']))
    table.add_row("Max Age (hours)", str(stats['max_age_hours']))
    table.add_row("Hide Read", "Yes" if stats['hide_read'] else "No")
    table.add_row("Learning Rate", f"{stats['learning_rate']:.2f}")
    
    console.print(table)
    
    # Show top preferences
    if stats['topic_count'] > 0:
        console.print("\n[bold]Top Topics:[/bold]")
        topic_weights = learner.get_topic_weights()
        sorted_topics = sorted(topic_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        for topic, weight in sorted_topics:
            console.print(f"  {topic}: {weight:.2f}")
    
    if stats['domain_count'] > 0:
        console.print("\n[bold]Top Domains:[/bold]")
        domain_weights = learner.get_domain_weights()
        sorted_domains = sorted(domain_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        for domain, weight in sorted_domains:
            console.print(f"  {domain}: {weight:.2f}")


@cli.command()
@click.option('--reset', '-r', is_flag=True, help='Reset all preferences')
def stats(reset: bool):
    """Show application statistics."""
    storage = get_storage()
    
    all_stories = storage.get_all_stories()
    recent_stories = storage.get_recent_stories(hours=24)
    
    table = Table(title="Application Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    
    table.add_row("Total Stories", str(len(all_stories)))
    table.add_row("Recent Stories (24h)", str(len(recent_stories)))
    table.add_row("Read Stories", str(len([s for s in all_stories if s.user_read])))
    table.add_row("Hidden Stories", str(len([s for s in all_stories if s.user_hidden])))
    table.add_row("Stories with Topics", str(len([s for s in all_stories if s.topic_label])))
    
    console.print(table)
    
    if reset:
        learner = create_preference_learner()
        learner.reset_preferences()
        console.print("\n[green]✓[/green] Preferences reset")


@cli.command()
@click.option('--config-path', '-c', default=None, help='Path to config file')
def config_show(config_path: Optional[str]):
    """Show current configuration."""
    if config_path:
        config = Config.load(config_path)
    else:
        config = get_config()
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    
    # General
    table.add_row("Top N Stories", str(config.top_n))
    table.add_row("API Base URL", config.api_base)
    
    # Storage
    table.add_row("Storage Type", config.storage.type)
    table.add_row("Storage Path", str(config.storage.path))
    
    # AI
    table.add_row("Embedding Model", config.ai.embedding_model)
    table.add_row("Cluster Algorithm", config.ai.cluster_algorithm)
    table.add_row("Number of Clusters", str(config.ai.num_clusters))
    
    # Schedule
    table.add_row("Fetch Interval (s)", str(config.schedule.fetch_interval))
    table.add_row("Digest Time", config.schedule.digest_time)
    
    console.print(table)
    
    # Show if OpenAI API key is set
    has_key = config.openai_api_key is not None and len(config.openai_api_key) > 0
    console.print(f"\n[bold]OpenAI API Key:[/bold] {'Set' if has_key else 'Not Set'}")


if __name__ == '__main__':
    cli()
