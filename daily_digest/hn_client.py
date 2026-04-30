"""
Hacker News API client for Daily Digest Vibe.
"""

import time
import requests
from typing import List, Dict, Any, Optional
from .models import Story
from .config import get_config


class HNClient:
    """Client for interacting with the Hacker News API."""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, base_url: Optional[str] = None, max_retries: int = 3):
        """Initialize the HN client."""
        self.base_url = base_url or self.BASE_URL
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DailyDigestVibe/0.1.0"
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a request to the HN API with retries."""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    def get_top_story_ids(self, limit: int = 500) -> List[int]:
        """Get the top story IDs from HN."""
        story_ids = self._make_request("topstories.json")
        return story_ids[:limit]
    
    def get_new_story_ids(self, limit: int = 500) -> List[int]:
        """Get the newest story IDs from HN."""
        story_ids = self._make_request("newstories.json")
        return story_ids[:limit]
    
    def get_best_story_ids(self, limit: int = 500) -> List[int]:
        """Get the best story IDs from HN."""
        story_ids = self._make_request("beststories.json")
        return story_ids[:limit]
    
    def get_story(self, story_id: int) -> Optional[Story]:
        """Get a single story by ID."""
        try:
            item = self._make_request(f"item/{story_id}.json")
            if item and item.get('type') == 'story':
                return Story.from_hacker_news_item(item)
            return None
        except Exception:
            return None
    
    def get_stories(self, story_ids: List[int], delay: float = 0.1) -> List[Story]:
        """Get multiple stories by IDs with rate limiting."""
        stories = []
        
        for story_id in story_ids:
            story = self.get_story(story_id)
            if story:
                stories.append(story)
            time.sleep(delay)  # Rate limiting
        
        return stories
    
    def get_top_stories(self, limit: int = 500, delay: float = 0.1) -> List[Story]:
        """Get the top stories from HN."""
        story_ids = self.get_top_story_ids(limit)
        return self.get_stories(story_ids, delay)
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        try:
            return self._make_request(f"user/{username}.json")
        except Exception:
            return None
    
    def get_max_item_id(self) -> int:
        """Get the current maximum item ID."""
        return self._make_request("maxitem.json")
    
    def fetch_stories_with_retry(self, story_ids: List[int], max_retries: int = 3) -> List[Story]:
        """Fetch stories with retry logic for failed requests."""
        stories = []
        failed_ids = []
        
        # First attempt
        for story_id in story_ids:
            story = self.get_story(story_id)
            if story:
                stories.append(story)
            else:
                failed_ids.append(story_id)
            time.sleep(0.1)
        
        # Retry failed IDs
        for attempt in range(max_retries):
            if not failed_ids:
                break
            
            new_failed_ids = []
            for story_id in failed_ids:
                story = self.get_story(story_id)
                if story:
                    stories.append(story)
                else:
                    new_failed_ids.append(story_id)
                time.sleep(0.1)
            
            failed_ids = new_failed_ids
        
        return stories


def create_client() -> HNClient:
    """Create a HN client with configuration from settings."""
    config = get_config()
    return HNClient(base_url=config.api_base)
