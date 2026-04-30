"""
AI-powered story grouping and clustering for Daily Digest Vibe.
Now uses the new EmbeddingService and ClusteringService.
"""

from typing import List, Optional, Dict, Any
from .models import Story, DigestGroup
from .clustering_service import get_clustering_service, ClusteringAlgorithm
from .embedding_service import get_embedding_service


# For backward compatibility, keep the old interface but use new services
class EmbeddingProvider:
    """Base class for embedding providers (deprecated - use EmbeddingService)."""
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        service = get_embedding_service()
        return service.embed(text)
    
    def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        service = get_embedding_service()
        result = service.batch_embed(texts)
        return result.embeddings


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider (deprecated - use EmbeddingService)."""
    pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider (deprecated - use EmbeddingService)."""
    pass


class StoryGrouper:
    """Groups stories using clustering algorithms (now uses new services)."""
    
    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        """Initialize story grouper."""
        self.embedding_provider = embedding_provider
        self.config = None  # Will be loaded from get_config() when needed
        self.clustering_service = get_clustering_service()
    
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
        if self.embedding_provider:
            return self.embedding_provider.batch_embeddings(texts)
        else:
            service = get_embedding_service()
            result = service.batch_embed(texts)
            return result.embeddings
    
    def cluster_stories(self, stories: List[Story], 
                       n_clusters: Optional[int] = None,
                       algorithm: Optional[str] = None) -> List[DigestGroup]:
        """Cluster stories into groups."""
        # Convert algorithm string to enum
        algo_enum = None
        if algorithm:
            try:
                algo_enum = ClusteringAlgorithm(algorithm)
            except ValueError:
                pass
        
        # Use new clustering service
        result = self.clustering_service.cluster_stories(
            stories, 
            n_clusters=n_clusters,
            algorithm=algo_enum
        )
        
        return result.groups
    
    def find_optimal_clusters(self, stories: List[Story], 
                             max_clusters: int = 15,
                             algorithm: str = "kmeans") -> int:
        """Find the optimal number of clusters using silhouette score."""
        try:
            algo_enum = ClusteringAlgorithm(algorithm)
        except ValueError:
            algo_enum = ClusteringAlgorithm.KMEANS
        
        metrics = self.clustering_service.get_cluster_quality(stories, max_clusters)
        return metrics.get("n_clusters", min(3, len(stories)))
    
    def assign_topics(self, stories: List[Story], 
                     n_clusters: Optional[int] = None) -> List[Story]:
        """Assign topic labels to stories using clustering."""
        # Use new clustering service
        return self.clustering_service.assign_topics(stories, n_clusters)
    
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
