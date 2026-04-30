"""
Storage module for Daily Digest Vibe.
Supports SQLite and JSON storage backends.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Story, UserPreference
from .config import get_config


class BaseStorage:
    """Base storage class."""
    
    def save_story(self, story: Story) -> bool:
        """Save a story."""
        raise NotImplementedError
    
    def get_story(self, story_id: int) -> Optional[Story]:
        """Get a story by ID."""
        raise NotImplementedError
    
    def get_all_stories(self) -> List[Story]:
        """Get all stories."""
        raise NotImplementedError
    
    def get_recent_stories(self, hours: int = 24) -> List[Story]:
        """Get stories from the last N hours."""
        raise NotImplementedError
    
    def update_story(self, story: Story) -> bool:
        """Update a story."""
        raise NotImplementedError
    
    def delete_story(self, story_id: int) -> bool:
        """Delete a story."""
        raise NotImplementedError
    
    def save_preferences(self, preferences: UserPreference) -> bool:
        """Save user preferences."""
        raise NotImplementedError
    
    def get_preferences(self, user_id: str = "default") -> UserPreference:
        """Get user preferences."""
        raise NotImplementedError
    
    def get_story_ids(self) -> List[int]:
        """Get all story IDs."""
        raise NotImplementedError
    
    def close(self) -> None:
        """Close the storage connection."""
        pass


class SQLiteStorage(BaseStorage):
    """SQLite storage backend."""
    
    def __init__(self, db_path: str = "data/stories.db"):
        """Initialize SQLite storage."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path))
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database tables."""
        cursor = self.connection.cursor()
        
        # Stories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            score INTEGER DEFAULT 0,
            time INTEGER DEFAULT 0,
            descendants INTEGER DEFAULT 0,
            author TEXT,
            kids TEXT,  -- JSON array of comment IDs
            type TEXT DEFAULT 'story',
            fetched_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            embedding TEXT,  -- JSON array of floats
            cluster_id INTEGER,
            topic_label TEXT,
            summary TEXT,
            user_interested INTEGER,
            user_read INTEGER DEFAULT 0,
            user_hidden INTEGER DEFAULT 0
        )
        """)
        
        # Preferences table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id TEXT PRIMARY KEY,
            topic_weights TEXT,  -- JSON dict
            domain_weights TEXT,
            author_weights TEXT,
            keyword_weights TEXT,
            min_score INTEGER DEFAULT 0,
            max_age_hours REAL DEFAULT 24.0,
            hide_read INTEGER DEFAULT 1,
            learning_rate REAL DEFAULT 0.1,
            total_stories_read INTEGER DEFAULT 0,
            total_stories_hidden INTEGER DEFAULT 0,
            last_updated TEXT NOT NULL
        )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_time ON stories(time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_cluster ON stories(cluster_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_read ON stories(user_read)")
        
        self.connection.commit()
    
    def _story_to_row(self, story: Story) -> Dict[str, Any]:
        """Convert Story to database row."""
        return {
            'id': story.id,
            'title': story.title,
            'url': story.url,
            'score': story.score,
            'time': story.time,
            'descendants': story.descendants,
            'author': story.by,
            'kids': json.dumps(story.kids),
            'type': story.type,
            'fetched_at': story.fetched_at.isoformat(),
            'last_updated': story.last_updated.isoformat(),
            'embedding': json.dumps(story.embedding) if story.embedding else None,
            'cluster_id': story.cluster_id,
            'topic_label': story.topic_label,
            'summary': story.summary,
            'user_interested': 1 if story.user_interested else 0,
            'user_read': 1 if story.user_read else 0,
            'user_hidden': 1 if story.user_hidden else 0
        }
    
    def _row_to_story(self, row: Dict[str, Any]) -> Story:
        """Convert database row to Story."""
        return Story(
            id=row['id'],
            title=row['title'],
            url=row['url'],
            score=row['score'],
            time=row['time'],
            descendants=row['descendants'],
            by=row['author'],
            kids=json.loads(row['kids']) if row['kids'] else [],
            type=row['type'],
            fetched_at=datetime.fromisoformat(row['fetched_at']),
            last_updated=datetime.fromisoformat(row['last_updated']),
            embedding=json.loads(row['embedding']) if row['embedding'] else None,
            cluster_id=row['cluster_id'],
            topic_label=row['topic_label'],
            summary=row['summary'],
            user_interested=bool(row['user_interested']),
            user_read=bool(row['user_read']),
            user_hidden=bool(row['user_hidden'])
        )
    
    def save_story(self, story: Story) -> bool:
        """Save a story to the database."""
        row = self._story_to_row(story)
        
        cursor = self.connection.cursor()
        columns = ', '.join(row.keys())
        placeholders = ', '.join(['?'] * len(row))
        
        query = f"""
        INSERT OR REPLACE INTO stories ({columns})
        VALUES ({placeholders})
        """
        
        cursor.execute(query, list(row.values()))
        self.connection.commit()
        return True
    
    def get_story(self, story_id: int) -> Optional[Story]:
        """Get a story by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
        row = cursor.fetchone()
        
        if row:
            row_dict = dict(zip([col[0] for col in cursor.description], row))
            return self._row_to_story(row_dict)
        return None
    
    def get_all_stories(self) -> List[Story]:
        """Get all stories."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM stories ORDER BY time DESC")
        
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(zip([col[0] for col in cursor.description], row))
            stories.append(self._row_to_story(row_dict))
        
        return stories
    
    def get_recent_stories(self, hours: int = 24) -> List[Story]:
        """Get stories from the last N hours."""
        cutoff = int(datetime.utcnow().timestamp() - hours * 3600)
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM stories WHERE time >= ? ORDER BY time DESC", (cutoff,))
        
        stories = []
        for row in cursor.fetchall():
            row_dict = dict(zip([col[0] for col in cursor.description], row))
            stories.append(self._row_to_story(row_dict))
        
        return stories
    
    def update_story(self, story: Story) -> bool:
        """Update a story."""
        return self.save_story(story)  # INSERT OR REPLACE handles updates
    
    def delete_story(self, story_id: int) -> bool:
        """Delete a story."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def get_story_ids(self) -> List[int]:
        """Get all story IDs."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM stories")
        return [row[0] for row in cursor.fetchall()]
    
    def save_preferences(self, preferences: UserPreference) -> bool:
        """Save user preferences."""
        cursor = self.connection.cursor()
        
        cursor.execute("""
        INSERT OR REPLACE INTO preferences (
            user_id, topic_weights, domain_weights, author_weights, 
            keyword_weights, min_score, max_age_hours, hide_read, 
            learning_rate, total_stories_read, total_stories_hidden, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            preferences.user_id,
            json.dumps(preferences.topic_weights),
            json.dumps(preferences.domain_weights),
            json.dumps(preferences.author_weights),
            json.dumps(preferences.keyword_weights),
            preferences.min_score,
            preferences.max_age_hours,
            1 if preferences.hide_read else 0,
            preferences.learning_rate,
            preferences.total_stories_read,
            preferences.total_stories_hidden,
            preferences.last_updated.isoformat()
        ))
        
        self.connection.commit()
        return True
    
    def get_preferences(self, user_id: str = "default") -> UserPreference:
        """Get user preferences."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            row_dict = dict(zip([col[0] for col in cursor.description], row))
            return UserPreference(
                user_id=row_dict['user_id'],
                topic_weights=json.loads(row_dict['topic_weights']) if row_dict['topic_weights'] else {},
                domain_weights=json.loads(row_dict['domain_weights']) if row_dict['domain_weights'] else {},
                author_weights=json.loads(row_dict['author_weights']) if row_dict['author_weights'] else {},
                keyword_weights=json.loads(row_dict['keyword_weights']) if row_dict['keyword_weights'] else {},
                min_score=row_dict['min_score'],
                max_age_hours=row_dict['max_age_hours'],
                hide_read=bool(row_dict['hide_read']),
                learning_rate=row_dict['learning_rate'],
                total_stories_read=row_dict['total_stories_read'],
                total_stories_hidden=row_dict['total_stories_hidden'],
                last_updated=datetime.fromisoformat(row_dict['last_updated'])
            )
        
        return UserPreference(user_id=user_id)
    
    def close(self) -> None:
        """Close the database connection."""
        self.connection.close()


class JSONStorage(BaseStorage):
    """JSON file storage backend."""
    
    def __init__(self, stories_file: str = "data/stories.json", 
                 preferences_file: str = "data/preferences.json"):
        """Initialize JSON storage."""
        self.stories_file = Path(stories_file)
        self.preferences_file = Path(preferences_file)
        self.stories_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_data()
    
    def _load_data(self) -> None:
        """Load data from files."""
        self.stories: Dict[int, Dict[str, Any]] = {}
        self.preferences: Dict[str, Dict[str, Any]] = {}
        
        if self.stories_file.exists():
            with open(self.stories_file, 'r') as f:
                data = json.load(f)
                self.stories = {int(k): v for k, v in data.get('stories', {}).items()}
        
        if self.preferences_file.exists():
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
                self.preferences = data.get('preferences', {})
    
    def _save_data(self) -> None:
        """Save data to files."""
        # Save stories
        with open(self.stories_file, 'w') as f:
            json.dump({'stories': self.stories}, f, indent=2)
        
        # Save preferences
        with open(self.preferences_file, 'w') as f:
            json.dump({'preferences': self.preferences}, f, indent=2)
    
    def save_story(self, story: Story) -> bool:
        """Save a story."""
        story_dict = story.to_dict()
        self.stories[story.id] = story_dict
        self._save_data()
        return True
    
    def get_story(self, story_id: int) -> Optional[Story]:
        """Get a story by ID."""
        if story_id in self.stories:
            story_data = self.stories[story_id]
            # Convert datetime strings back to datetime objects
            story_data['fetched_at'] = datetime.fromisoformat(story_data['fetched_at'])
            story_data['last_updated'] = datetime.fromisoformat(story_data['last_updated'])
            return Story(**story_data)
        return None
    
    def get_all_stories(self) -> List[Story]:
        """Get all stories."""
        stories = []
        for story_data in self.stories.values():
            story_data['fetched_at'] = datetime.fromisoformat(story_data['fetched_at'])
            story_data['last_updated'] = datetime.fromisoformat(story_data['last_updated'])
            stories.append(Story(**story_data))
        return sorted(stories, key=lambda s: s.time, reverse=True)
    
    def get_recent_stories(self, hours: int = 24) -> List[Story]:
        """Get stories from the last N hours."""
        cutoff = int(datetime.utcnow().timestamp() - hours * 3600)
        return [s for s in self.get_all_stories() if s.time >= cutoff]
    
    def update_story(self, story: Story) -> bool:
        """Update a story."""
        return self.save_story(story)
    
    def delete_story(self, story_id: int) -> bool:
        """Delete a story."""
        if story_id in self.stories:
            del self.stories[story_id]
            self._save_data()
            return True
        return False
    
    def get_story_ids(self) -> List[int]:
        """Get all story IDs."""
        return list(self.stories.keys())
    
    def save_preferences(self, preferences: UserPreference) -> bool:
        """Save user preferences."""
        pref_dict = preferences.model_dump()
        pref_dict['last_updated'] = preferences.last_updated.isoformat()
        self.preferences[preferences.user_id] = pref_dict
        self._save_data()
        return True
    
    def get_preferences(self, user_id: str = "default") -> UserPreference:
        """Get user preferences."""
        if user_id in self.preferences:
            pref_data = self.preferences[user_id]
            pref_data['last_updated'] = datetime.fromisoformat(pref_data['last_updated'])
            return UserPreference(**pref_data)
        return UserPreference(user_id=user_id)


class StoryStorage:
    """Factory class for creating storage instances."""
    
    _instance: Optional[BaseStorage] = None
    
    @classmethod
    def get_storage(cls) -> BaseStorage:
        """Get a storage instance based on configuration."""
        if cls._instance is None:
            config = get_config()
            
            if config.storage.type == "sqlite":
                cls._instance = SQLiteStorage(str(config.get_storage_path()))
            else:
                cls._instance = JSONStorage(
                    stories_file=config.storage.stories_file,
                    preferences_file=config.storage.preferences_file
                )
        
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the storage instance."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_storage() -> BaseStorage:
    """Get the global storage instance."""
    return StoryStorage.get_storage()
