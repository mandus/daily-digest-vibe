"""
Tests for data models.
"""

import pytest
from datetime import datetime
from daily_digest.models import Story, UserPreference, DigestGroup, DailyDigest


def test_story_creation():
    """Test Story model creation."""
    story = Story(
        id=123,
        title="Test Story",
        url="https://example.com",
        score=100,
        time=int(datetime.utcnow().timestamp()),
        descendants=42,
        by="testuser"
    )
    
    assert story.id == 123
    assert story.title == "Test Story"
    assert story.url == "https://example.com"
    assert story.score == 100
    assert story.url_domain == "example.com"
    assert story.is_recent is True


def test_story_from_hacker_news_item():
    """Test creating Story from HN API item."""
    item = {
        'id': 456,
        'title': "Another Test",
        'url': 'https://test.com/article',
        'score': 200,
        'time': int(datetime.utcnow().timestamp()) - 3600,  # 1 hour ago
        'descendants': 10,
        'by': 'author123',
        'kids': [1, 2, 3],
        'type': 'story'
    }
    
    story = Story.from_hacker_news_item(item)
    
    assert story.id == 456
    assert story.title == "Another Test"
    assert story.url_domain == "test.com"
    assert story.age_hours > 0


def test_user_preference_creation():
    """Test UserPreference model creation."""
    prefs = UserPreference(user_id="testuser")
    
    assert prefs.user_id == "testuser"
    assert prefs.learning_rate == 0.1
    assert prefs.min_score == 0
    assert prefs.max_age_hours == 24.0


def test_user_preference_update():
    """Test updating user preferences."""
    prefs = UserPreference(user_id="testuser")
    
    story = Story(
        id=789,
        title="Machine Learning Breakthrough",
        url="https://ai-research.com",
        score=150,
        time=int(datetime.utcnow().timestamp()),
        by="researcher1"
    )
    story.topic_label = "AI"
    
    # Update with read action
    prefs.update_from_story(story, "read", weight=1.0)
    
    assert prefs.total_stories_read == 1
    assert "AI" in prefs.topic_weights
    assert "ai-research.com" in prefs.domain_weights
    assert "researcher1" in prefs.author_weights


def test_user_preference_scoring():
    """Test user preference scoring."""
    prefs = UserPreference(user_id="testuser")
    
    # Create a story with known topic
    story1 = Story(
        id=1,
        title="Python Tips",
        url="https://python.org",
        score=100,
        time=int(datetime.utcnow().timestamp())
    )
    story1.topic_label = "Python"
    
    # Update preferences for Python
    prefs.update_from_story(story1, "read", weight=2.0)
    
    # Create another story
    story2 = Story(
        id=2,
        title="JavaScript News",
        url="https://js.org",
        score=50,
        time=int(datetime.utcnow().timestamp())
    )
    story2.topic_label = "JavaScript"
    
    # Python story should have higher score
    score1 = prefs.get_story_score(story1)
    score2 = prefs.get_story_score(story2)
    
    assert score1 > score2


def test_digest_group_creation():
    """Test DigestGroup creation."""
    story1 = Story(id=1, title="Story 1", score=100)
    story2 = Story(id=2, title="Story 2", score=50)
    
    group = DigestGroup(
        cluster_id=0,
        label="Technology",
        stories=[story1, story2]
    )
    
    assert group.cluster_id == 0
    assert group.label == "Technology"
    assert group.story_count == 2
    assert group.total_score == 150


def test_daily_digest_creation():
    """Test DailyDigest creation."""
    story = Story(id=1, title="Test", score=100)
    group = DigestGroup(
        cluster_id=0,
        label="General",
        stories=[story]
    )
    
    digest = DailyDigest(
        date=datetime.utcnow(),
        groups=[group],
        total_stories=1,
        new_stories_since_last=1
    )
    
    assert digest.total_stories == 1
    assert len(digest.top_groups) == 1
    assert digest.top_groups[0].label == "General"
