"""
FastAPI web interface for Daily Digest Vibe.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, List
import uvicorn

from daily_digest.models import Story, DailyDigest, DigestGroup
from daily_digest.storage import get_storage
from daily_digest.digest_generator import create_digest_generator
from daily_digest.preference_learner import create_preference_learner
from daily_digest.hn_client import create_client


app = FastAPI(title="Daily Digest Vibe")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main digest page."""
    generator = create_digest_generator()
    storage = get_storage()
    
    # Get recent stories
    stories = storage.get_recent_stories(hours=24)
    
    # Generate digest
    digest = generator.generate_digest(stories, n_clusters=5)
    
    # Get user statistics
    learner = create_preference_learner()
    stats = learner.get_statistics()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "digest": digest,
        "stats": stats,
        "page_title": "Daily Digest"
    })


@app.get("/stories", response_class=HTMLResponse)
async def list_stories(request: Request, hours: int = 24, limit: int = 100):
    """List all recent stories."""
    storage = get_storage()
    stories = storage.get_recent_stories(hours=hours)
    
    return templates.TemplateResponse("stories.html", {
        "request": request,
        "stories": stories[:limit],
        "total": len(stories),
        "page_title": "All Stories"
    })


@app.get("/story/{story_id}", response_class=HTMLResponse)
async def show_story(request: Request, story_id: int):
    """Show a single story."""
    storage = get_storage()
    story = storage.get_story(story_id)
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    return templates.TemplateResponse("story.html", {
        "request": request,
        "story": story,
        "page_title": story.title
    })


@app.post("/story/{story_id}/read")
async def mark_read(story_id: int):
    """Mark a story as read."""
    storage = get_storage()
    learner = create_preference_learner()
    story = storage.get_story(story_id)
    
    if story:
        learner.mark_read(story)
        return {"status": "ok", "message": "Story marked as read"}
    
    raise HTTPException(status_code=404, detail="Story not found")


@app.post("/story/{story_id}/hide")
async def mark_hidden(story_id: int):
    """Mark a story as hidden."""
    storage = get_storage()
    learner = create_preference_learner()
    story = storage.get_story(story_id)
    
    if story:
        learner.mark_hidden(story)
        return {"status": "ok", "message": "Story marked as hidden"}
    
    raise HTTPException(status_code=404, detail="Story not found")


@app.post("/story/{story_id}/interest")
async def mark_interest(story_id: int, interested: bool = True):
    """Mark explicit interest in a story."""
    storage = get_storage()
    learner = create_preference_learner()
    story = storage.get_story(story_id)
    
    if story:
        learner.mark_interested(story, interested=interested)
        return {"status": "ok", "message": "Interest updated"}
    
    raise HTTPException(status_code=404, detail="Story not found")


@app.get("/preferences", response_class=HTMLResponse)
async def preferences(request: Request):
    """Show user preferences."""
    learner = create_preference_learner()
    stats = learner.get_statistics()
    
    return templates.TemplateResponse("preferences.html", {
        "request": request,
        "stats": stats,
        "topic_weights": learner.get_topic_weights(),
        "domain_weights": learner.get_domain_weights(),
        "author_weights": learner.get_author_weights(),
        "page_title": "Preferences"
    })


@app.get("/fetch", response_class=HTMLResponse)
async def fetch_stories(request: Request, limit: int = 500):
    """Fetch new stories from HN."""
    client = create_client()
    storage = get_storage()
    
    # Get top story IDs
    story_ids = client.get_top_story_ids(limit)
    
    # Check which stories we already have
    existing_ids = set(storage.get_story_ids())
    new_ids = [sid for sid in story_ids if sid not in existing_ids]
    
    # Fetch new stories
    stories = client.get_stories(new_ids, delay=0.05)
    
    # Save stories
    for story in stories:
        storage.save_story(story)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/process", response_class=HTMLResponse)
async def process_stories(request: Request, hours: int = 24):
    """Process stories to generate embeddings and topics."""
    from daily_digest.ai_grouping import create_grouper
    
    storage = get_storage()
    grouper = create_grouper()
    
    # Get recent stories
    stories = storage.get_recent_stories(hours=hours)
    
    # Generate embeddings and assign topics
    stories_with_topics = grouper.assign_topics(stories, n_clusters=10)
    
    # Save updated stories
    for story in stories_with_topics:
        storage.update_story(story)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/refresh", response_class=HTMLResponse)
async def refresh_all(request: Request):
    """Fetch and process new stories."""
    # Fetch new stories
    client = create_client()
    storage = get_storage()
    
    story_ids = client.get_top_story_ids(500)
    existing_ids = set(storage.get_story_ids())
    new_ids = [sid for sid in story_ids if sid not in existing_ids]
    
    if new_ids:
        stories = client.get_stories(new_ids, delay=0.05)
        for story in stories:
            storage.save_story(story)
    
    # Process all recent stories
    from daily_digest.ai_grouping import create_grouper
    grouper = create_grouper()
    
    all_stories = storage.get_recent_stories(hours=24)
    stories_with_topics = grouper.assign_topics(all_stories, n_clusters=10)
    
    for story in stories_with_topics:
        storage.update_story(story)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/digest")
async def api_digest(hours: int = 24, n_clusters: int = 5):
    """Get digest as JSON."""
    generator = create_digest_generator()
    storage = get_storage()
    
    stories = storage.get_recent_stories(hours=hours)
    digest = generator.generate_digest(stories, n_clusters=n_clusters)
    
    return digest.model_dump()


@app.get("/api/stories")
async def api_stories(hours: int = 24, limit: int = 100):
    """Get stories as JSON."""
    storage = get_storage()
    stories = storage.get_recent_stories(hours=hours)
    
    return {
        "stories": [s.to_dict() for s in stories[:limit]],
        "total": len(stories)
    }


def main():
    """Run the web server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
