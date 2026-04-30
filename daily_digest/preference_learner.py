"""
User preference learning for Daily Digest Vibe.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Story, UserPreference
from .storage import get_storage


class PreferenceLearner:
    """Learns and manages user preferences for story filtering."""
    
    def __init__(self, user_id: str = "default"):
        """Initialize preference learner."""
        self.user_id = user_id
        self.storage = get_storage()
        self.preferences = self.storage.get_preferences(user_id)
    
    def save(self) -> bool:
        """Save preferences to storage."""
        return self.storage.save_preferences(self.preferences)
    
    def update_preferences(self, story: Story, action: str, weight: float = 1.0) -> None:
        """Update preferences based on user action."""
        self.preferences.update_from_story(story, action, weight)
        self.save()
    
    def mark_read(self, story: Story) -> None:
        """Mark a story as read."""
        story.user_read = True
        story.last_updated = datetime.utcnow()
        self.storage.update_story(story)
        self.update_preferences(story, "read", weight=1.0)
    
    def mark_hidden(self, story: Story) -> None:
        """Mark a story as hidden."""
        story.user_hidden = True
        story.last_updated = datetime.utcnow()
        self.storage.update_story(story)
        self.update_preferences(story, "hide", weight=-1.0)
    
    def mark_interested(self, story: Story, interested: bool = True) -> None:
        """Mark explicit interest in a story."""
        story.user_interested = interested
        story.last_updated = datetime.utcnow()
        self.storage.update_story(story)
        weight = 2.0 if interested else -2.0
        self.update_preferences(story, "interest", weight=weight)
    
    def get_preference_score(self, story: Story) -> float:
        """Get the preference score for a story."""
        return self.preferences.get_story_score(story)
    
    def should_show_story(self, story: Story) -> bool:
        """Determine if a story should be shown to the user."""
        return self.preferences.should_show_story(story)
    
    def filter_stories(self, stories: List[Story]) -> List[Story]:
        """Filter stories based on user preferences."""
        return [story for story in stories if self.should_show_story(story)]
    
    def rank_stories(self, stories: List[Story]) -> List[Story]:
        """Rank stories by preference score."""
        scored_stories = []
        for story in stories:
            score = self.get_preference_score(story)
            scored_stories.append((score, story))
        
        # Sort by score descending, then by HN score descending
        scored_stories.sort(key=lambda x: (-x[0], -x[1].score))
        return [story for _, story in scored_stories]
    
    def get_recommended_stories(self, stories: List[Story], limit: int = 50) -> List[Story]:
        """Get recommended stories based on preferences."""
        filtered = self.filter_stories(stories)
        ranked = self.rank_stories(filtered)
        return ranked[:limit]
    
    def get_topic_weights(self) -> Dict[str, float]:
        """Get topic weights."""
        return self.preferences.topic_weights
    
    def get_domain_weights(self) -> Dict[str, float]:
        """Get domain weights."""
        return self.preferences.domain_weights
    
    def get_author_weights(self) -> Dict[str, float]:
        """Get author weights."""
        return self.preferences.author_weights
    
    def get_keyword_weights(self) -> Dict[str, float]:
        """Get keyword weights."""
        return self.preferences.keyword_weights
    
    def set_min_score(self, min_score: int) -> None:
        """Set minimum score threshold."""
        self.preferences.min_score = min_score
        self.save()
    
    def set_max_age_hours(self, max_age_hours: float) -> None:
        """Set maximum age in hours."""
        self.preferences.max_age_hours = max_age_hours
        self.save()
    
    def set_hide_read(self, hide_read: bool) -> None:
        """Set whether to hide read stories."""
        self.preferences.hide_read = hide_read
        self.save()
    
    def set_learning_rate(self, learning_rate: float) -> None:
        """Set learning rate."""
        self.preferences.learning_rate = learning_rate
        self.save()
    
    def reset_preferences(self) -> None:
        """Reset all learned preferences."""
        self.preferences = UserPreference(user_id=self.user_id)
        self.save()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get preference statistics."""
        return {
            'total_stories_read': self.preferences.total_stories_read,
            'total_stories_hidden': self.preferences.total_stories_hidden,
            'topic_count': len(self.preferences.topic_weights),
            'domain_count': len(self.preferences.domain_weights),
            'author_count': len(self.preferences.author_weights),
            'keyword_count': len(self.preferences.keyword_weights),
            'min_score': self.preferences.min_score,
            'max_age_hours': self.preferences.max_age_hours,
            'hide_read': self.preferences.hide_read,
            'learning_rate': self.preferences.learning_rate
        }


class MultiUserPreferenceLearner:
    """Manages preferences for multiple users."""
    
    def __init__(self):
        """Initialize multi-user preference learner."""
        self.learners: Dict[str, PreferenceLearner] = {}
    
    def get_learner(self, user_id: str = "default") -> PreferenceLearner:
        """Get or create a preference learner for a user."""
        if user_id not in self.learners:
            self.learners[user_id] = PreferenceLearner(user_id)
        return self.learners[user_id]
    
    def get_all_users(self) -> List[str]:
        """Get all user IDs."""
        return list(self.learners.keys())


def create_preference_learner(user_id: str = "default") -> PreferenceLearner:
    """Create a preference learner for a user."""
    return PreferenceLearner(user_id)
