"""
AI-powered story grouping and clustering for Daily Digest Vibe.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from .models import Story, DigestGroup
from .config import get_config


class EmbeddingProvider:
    """Base class for embedding providers."""
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        raise NotImplementedError
    
    def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        return [self.get_embedding(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"):
        """Initialize OpenAI embedding provider."""
        self.api_key = api_key
        self.model = model
        
        if api_key is None:
            config = get_config()
            self.api_key = config.openai_api_key
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            import openai
            self.client = openai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI embeddings")
    
    def get_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """Get embedding for text using OpenAI API."""
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Failed to get embedding after retries")
    
    def batch_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Get embeddings for multiple texts in batches."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                embeddings.extend([item.embedding for item in response.data])
            except Exception as e:
                # Fallback to individual requests
                for text in batch:
                    embeddings.append(self.get_embedding(text))
        
        return embeddings


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""
    
    def __init__(self, embedding_size: int = 1536):
        """Initialize mock embedding provider."""
        self.embedding_size = embedding_size
        self._text_to_hash = {}
    
    def _text_to_hash_value(self, text: str) -> int:
        """Convert text to a consistent hash value."""
        if text not in self._text_to_hash:
            # Simple hash function
            hash_val = 0
            for char in text:
                hash_val = (hash_val * 31 + ord(char)) % (2**32)
            self._text_to_hash[text] = hash_val
        return self._text_to_hash[text]
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate a mock embedding."""
        hash_val = self._text_to_hash_value(text)
        np.random.seed(hash_val)
        return np.random.randn(self.embedding_size).tolist()


class StoryGrouper:
    """Groups stories using clustering algorithms."""
    
    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        """Initialize story grouper."""
        self.embedding_provider = embedding_provider
        self.config = get_config()
        
        # Initialize embedding provider if not provided
        if self.embedding_provider is None:
            if self.config.ai.use_local_embeddings:
                self.embedding_provider = MockEmbeddingProvider()
            else:
                try:
                    self.embedding_provider = OpenAIEmbeddingProvider()
                except (ValueError, ImportError):
                    # Fall back to mock if OpenAI is not available
                    self.embedding_provider = MockEmbeddingProvider()
    
    def _get_clustering_algorithm(self, algorithm: str, n_clusters: int) -> Any:
        """Get the clustering algorithm instance."""
        if algorithm == "kmeans":
            return KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        elif algorithm == "dbscan":
            return DBSCAN(eps=0.5, min_samples=5)
        elif algorithm == "agglomerative":
            return AgglomerativeClustering(n_clusters=n_clusters)
        else:
            raise ValueError(f"Unknown clustering algorithm: {algorithm}")
    
    def _preprocess_text(self, story: Story) -> str:
        """Preprocess story text for embedding."""
        # Use title + URL domain if available
        text = story.title
        if story.url_domain:
            text = f"{story.title} ({story.url_domain})"
        return text
    
    def generate_embeddings(self, stories: List[Story]) -> List[List[float]]:
        """Generate embeddings for a list of stories."""
        texts = [self._preprocess_text(story) for story in stories]
        return self.embedding_provider.batch_embeddings(texts)
    
    def cluster_stories(self, stories: List[Story], 
                       n_clusters: Optional[int] = None,
                       algorithm: Optional[str] = None) -> List[DigestGroup]:
        """Cluster stories into groups."""
        if not stories:
            return []
        
        # Use config values if not provided
        if n_clusters is None:
            n_clusters = self.config.ai.num_clusters
        if algorithm is None:
            algorithm = self.config.ai.cluster_algorithm
        
        # Adjust n_clusters based on number of stories
        n_clusters = min(n_clusters, len(stories))
        if n_clusters < 2:
            n_clusters = 2
        
        # Generate embeddings
        embeddings = self.generate_embeddings(stories)
        
        # Convert to numpy array
        X = np.array(embeddings)
        
        # Standardize embeddings
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Cluster
        clusterer = self._get_clustering_algorithm(algorithm, n_clusters)
        
        if algorithm == "dbscan":
            labels = clusterer.fit_predict(X_scaled)
            # For DBSCAN, -1 means outlier
            unique_labels = set(labels)
            n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        else:
            labels = clusterer.fit_predict(X_scaled)
        
        # Create groups
        groups = []
        for cluster_id in range(n_clusters):
            cluster_stories = [stories[i] for i, label in enumerate(labels) if label == cluster_id]
            if cluster_stories:
                # Generate a label for the cluster
                label = self._generate_cluster_label(cluster_stories)
                group = DigestGroup(
                    cluster_id=cluster_id,
                    label=label,
                    stories=cluster_stories
                )
                groups.append(group)
        
        # Handle outliers for DBSCAN
        if algorithm == "dbscan" and -1 in labels:
            outlier_stories = [stories[i] for i, label in enumerate(labels) if label == -1]
            if outlier_stories:
                group = DigestGroup(
                    cluster_id=-1,
                    label="Other",
                    stories=outlier_stories
                )
                groups.append(group)
        
        return groups
    
    def _generate_cluster_label(self, stories: List[Story]) -> str:
        """Generate a label for a cluster based on story titles."""
        # Simple approach: use most common words
        from collections import Counter
        import re
        
        all_words = []
        for story in stories:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', story.title.lower())
            all_words.extend(words)
        
        # Common stop words to exclude
        stop_words = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 
                     'was', 'were', 'been', 'have', 'has', 'but', 'not', 'you', 
                     'your', 'they', 'their', 'what', 'when', 'where', 'which'}
        
        filtered_words = [w for w in all_words if w not in stop_words]
        
        if filtered_words:
            word_counts = Counter(filtered_words)
            top_words = [word for word, _ in word_counts.most_common(3)]
            return ' '.join(top_words).title()
        
        return "General"
    
    def find_optimal_clusters(self, stories: List[Story], 
                             max_clusters: int = 15,
                             algorithm: str = "kmeans") -> int:
        """Find the optimal number of clusters using silhouette score."""
        if len(stories) < 10:
            return min(3, len(stories))
        
        # Generate embeddings
        embeddings = self.generate_embeddings(stories)
        X = np.array(embeddings)
        
        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        best_score = -1
        best_n = 3
        
        for n_clusters in range(3, min(max_clusters, len(stories)) + 1):
            try:
                if algorithm == "kmeans":
                    clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                elif algorithm == "agglomerative":
                    clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                else:
                    continue
                
                labels = clusterer.fit_predict(X_scaled)
                
                if len(set(labels)) > 1:  # Need at least 2 clusters for silhouette
                    score = silhouette_score(X_scaled, labels)
                    if score > best_score:
                        best_score = score
                        best_n = n_clusters
            except Exception:
                continue
        
        return best_n if best_n > 2 else 3
    
    def assign_topics(self, stories: List[Story], 
                     n_clusters: Optional[int] = None) -> List[Story]:
        """Assign topic labels to stories using clustering."""
        if n_clusters is None:
            n_clusters = self.config.ai.num_clusters
        
        # Cluster stories
        groups = self.cluster_stories(stories, n_clusters)
        
        # Assign cluster_id and topic_label to each story
        for group in groups:
            for story in group.stories:
                story.cluster_id = group.cluster_id
                story.topic_label = group.label
        
        return stories
    
    def generate_summaries(self, groups: List[DigestGroup]) -> List[DigestGroup]:
        """Generate summaries for each group."""
        # This would use an LLM to generate summaries
        # For now, just use a simple approach
        
        for group in groups:
            if len(group.stories) <= 3:
                # For small groups, list the titles
                titles = [s.title for s in group.stories]
                group.summary = "; ".join(titles)
            else:
                # For larger groups, create a summary
                scores = [s.score for s in group.stories]
                avg_score = sum(scores) / len(scores)
                group.summary = f"{len(group.stories)} stories, avg score: {avg_score:.0f}"
        
        return groups


def create_grouper() -> StoryGrouper:
    """Create a story grouper with default configuration."""
    return StoryGrouper()
