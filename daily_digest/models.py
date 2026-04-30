"""
Data models for Daily Digest Vibe.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class Story(BaseModel):
    """Represents a Hacker News story."""
    
    id: int
    title: str
    url: Optional[str] = None
    score: int = 0
    time: int = 0  # Unix timestamp
    descendants: int = 0  # Number of comments
    by: Optional[str] = None  # Author
    kids: List[int] = Field(default_factory=list)  # Comment IDs
    type: str = "story"
    
    # Additional metadata
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # AI-generated fields
    embedding: Optional[List[float]] = None
    cluster_id: Optional[int] = None
    topic_label: Optional[str] = None
    summary: Optional[str] = None
    
    # User preference fields
    user_interested: Optional[bool] = None
    user_read: bool = False
    user_hidden: bool = False
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def url_domain(self) -> Optional[str]:
        """Extract domain from URL."""
        if not self.url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.netloc
    
    @property
    def age_hours(self) -> float:
        """Calculate age in hours."""
        if not self.time:
            return 0.0
        age_seconds = datetime.utcnow().timestamp() - self.time
        return age_seconds / 3600
    
    @property
    def is_recent(self) -> bool:
        """Check if story is recent (less than 24 hours old)."""
        return self.age_hours < 24
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling datetime objects."""
        data = self.model_dump()
        data['fetched_at'] = self.fetched_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_hacker_news_item(cls, item: Dict[str, Any]) -> "Story":
        """Create Story from Hacker News API item."""
        return cls(
            id=item.get('id', 0),
            title=item.get('title', ''),
            url=item.get('url'),
            score=item.get('score', 0),
            time=item.get('time', 0),
            descendants=item.get('descendants', 0),
            by=item.get('by'),
            kids=item.get('kids', []),
            type=item.get('type', 'story')
        )


class UserPreference(BaseModel):
    """Represents user preferences for story filtering."""
    
    user_id: str = "default"
    
    # Topic preferences (topic -> weight, higher = more interested)
    topic_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Domain preferences
    domain_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Author preferences
    author_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Keyword preferences
    keyword_weights: Dict[str, float] = Field(default_factory=dict)
    
    # General preferences
    min_score: int = 0
    max_age_hours: Optional[float] = 24.0  # Only show stories newer than this
    hide_read: bool = True
    
    # Learning parameters
    learning_rate: float = 0.1
    
    # Statistics
    total_stories_read: int = 0
    total_stories_hidden: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)
    
    def update_from_story(self, story: Story, action: str, weight: float = 1.0) -> None:
        """Update preferences based on user action on a story."""
        if story.topic_label:
            current = self.topic_weights.get(story.topic_label, 0)
            self.topic_weights[story.topic_label] = current + (weight * self.learning_rate)
        
        if story.url_domain:
            current = self.domain_weights.get(story.url_domain, 0)
            self.domain_weights[story.url_domain] = current + (weight * self.learning_rate)
        
        if story.by:
            current = self.author_weights.get(story.by, 0)
            self.author_weights[story.by] = current + (weight * self.learning_rate)
        
        # Extract keywords from title
        keywords = self._extract_keywords(story.title)
        for keyword in keywords:
            current = self.keyword_weights.get(keyword, 0)
            self.keyword_weights[keyword] = current + (weight * self.learning_rate)
        
        # Update statistics
        if action == "read":
            self.total_stories_read += 1
        elif action == "hide":
            self.total_stories_hidden += 1
        
        self.last_updated = datetime.utcnow()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - can be enhanced
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Filter out common words
        stop_words = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was', 'were', 'been', 'have', 'has'}
        return [w for w in words if w not in stop_words]
    
    def get_story_score(self, story: Story) -> float:
        """Calculate a preference score for a story."""
        score = 0.0
        
        # Topic score
        if story.topic_label and story.topic_label in self.topic_weights:
            score += self.topic_weights[story.topic_label]
        
        # Domain score
        if story.url_domain and story.url_domain in self.domain_weights:
            score += self.domain_weights[story.url_domain] * 0.5
        
        # Author score
        if story.by and story.by in self.author_weights:
            score += self.author_weights[story.by] * 0.3
        
        # Keyword score
        keywords = self._extract_keywords(story.title)
        for keyword in keywords:
            if keyword in self.keyword_weights:
                score += self.keyword_weights[keyword] * 0.2
        
        # Base score from HN
        score += story.score * 0.01
        
        # Age penalty
        if self.max_age_hours and story.age_hours > self.max_age_hours:
            score -= 100  # Heavy penalty for old stories
        
        return score
    
    def should_show_story(self, story: Story) -> bool:
        """Determine if a story should be shown to the user."""
        if story.user_hidden:
            return False
        
        if self.hide_read and story.user_read:
            return False
        
        if self.max_age_hours and story.age_hours > self.max_age_hours:
            return False
        
        if story.score < self.min_score:
            return False
        
        return True


class DigestGroup(BaseModel):
    """Represents a group of stories in the digest."""
    
    cluster_id: int
    label: str
    stories: List[Story] = Field(default_factory=list)
    summary: Optional[str] = None
    
    @property
    def total_score(self) -> int:
        """Total score of all stories in group."""
        return sum(story.score for story in self.stories)
    
    @property
    def story_count(self) -> int:
        """Number of stories in group."""
        return len(self.stories)


class DailyDigest(BaseModel):
    """Represents a complete daily digest."""
    
    date: datetime = Field(default_factory=datetime.utcnow)
    groups: List[DigestGroup] = Field(default_factory=list)
    total_stories: int = 0
    new_stories_since_last: int = 0
    
    @property
    def top_groups(self) -> List[DigestGroup]:
        """Get groups sorted by total score."""
        return sorted(self.groups, key=lambda g: g.total_score, reverse=True)
