"""
Clustering service for Daily Digest Vibe.
Provides smart grouping of stories using various clustering algorithms.
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score

from .models import Story, DigestGroup
from .embedding_service import get_embedding_service, EmbeddingService


# Configure logging
logger = logging.getLogger(__name__)


class ClusteringAlgorithm(Enum):
    """Types of clustering algorithms."""
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    AGGLOMERATIVE = "agglomerative"
    SPECTRAL = "spectral"
    OPTICS = "optics"


@dataclass
class ClusteringResult:
    """Result of a clustering operation."""
    groups: List[DigestGroup]
    algorithm: str
    n_clusters: int
    silhouette_score: Optional[float] = None
    db_score: Optional[float] = None
    processing_time: float = 0.0
    embedding_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusteringConfig:
    """Configuration for clustering service."""
    algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS
    n_clusters: int = 10
    max_clusters: int = 15
    min_cluster_size: int = 2
    optimize_clusters: bool = True
    random_state: int = 42


class ClusteringService:
    """Service for clustering stories into meaningful groups."""
    
    def __init__(self, 
                 embedding_service: Optional[EmbeddingService] = None,
                 config: Optional[ClusteringConfig] = None):
        """Initialize clustering service."""
        self.embedding_service = embedding_service or get_embedding_service()
        self.config = config or ClusteringConfig()
    
    def cluster_stories(self, 
                       stories: List[Story],
                       n_clusters: Optional[int] = None,
                       algorithm: Optional[ClusteringAlgorithm] = None) -> ClusteringResult:
        """Cluster stories into groups."""
        if not stories:
            return ClusteringResult(
                groups=[],
                algorithm="none",
                n_clusters=0
            )
        
        start_time = time.time()
        
        # Use provided values or defaults
        algorithm = algorithm or self.config.algorithm
        n_clusters = n_clusters or self.config.n_clusters
        
        # Adjust n_clusters based on number of stories
        n_clusters = min(n_clusters, len(stories))
        if n_clusters < 2:
            n_clusters = 2
        
        # Generate embeddings
        texts = [self._preprocess_story(story) for story in stories]
        embedding_result = self.embedding_service.batch_embed(texts)
        
        # Convert to numpy array
        X = np.array(embedding_result.embeddings)
        
        # Standardize embeddings
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Find optimal number of clusters if enabled
        if self.config.optimize_clusters and len(stories) >= 10:
            optimal_n = self._find_optimal_clusters(X_scaled, 
                                                   max_clusters=min(self.config.max_clusters, len(stories)),
                                                   algorithm=algorithm)
            if optimal_n > 1:
                n_clusters = optimal_n
        
        # Perform clustering
        labels = self._cluster(X_scaled, n_clusters, algorithm)
        
        # Create groups
        groups = self._create_groups(stories, labels, algorithm)
        
        # Calculate metrics
        silhouette = None
        db_score = None
        if len(set(labels)) > 1:
            try:
                silhouette = silhouette_score(X_scaled, labels)
                db_score = davies_bouldin_score(X_scaled, labels)
            except Exception as e:
                logger.warning(f"Failed to calculate clustering metrics: {e}")
        
        processing_time = time.time() - start_time
        
        return ClusteringResult(
            groups=groups,
            algorithm=algorithm.value,
            n_clusters=n_clusters,
            silhouette_score=silhouette,
            db_score=db_score,
            processing_time=processing_time,
            embedding_info={
                "model": embedding_result.model,
                "provider": embedding_result.provider,
                "latency": embedding_result.latency_seconds
            }
        )
    
    def _preprocess_story(self, story: Story) -> str:
        """Preprocess story for embedding."""
        # Use title + URL domain if available
        text = story.title
        if story.url_domain:
            text = f"{story.title} ({story.url_domain})"
        return text
    
    def _cluster(self, 
                X: np.ndarray,
                n_clusters: int,
                algorithm: ClusteringAlgorithm) -> np.ndarray:
        """Perform clustering using the specified algorithm."""
        try:
            if algorithm == ClusteringAlgorithm.KMEANS:
                from sklearn.cluster import KMeans
                clusterer = KMeans(n_clusters=n_clusters, 
                                  random_state=self.config.random_state,
                                  n_init=10)
                labels = clusterer.fit_predict(X)
            
            elif algorithm == ClusteringAlgorithm.DBSCAN:
                from sklearn.cluster import DBSCAN
                # Adjust eps based on data
                eps = 0.5 if X.shape[1] <= 100 else 0.7
                clusterer = DBSCAN(eps=eps, min_samples=self.config.min_cluster_size)
                labels = clusterer.fit_predict(X)
                # For DBSCAN, -1 means outlier - we'll handle this in _create_groups
            
            elif algorithm == ClusteringAlgorithm.AGGLOMERATIVE:
                from sklearn.cluster import AgglomerativeClustering
                clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                labels = clusterer.fit_predict(X)
            
            elif algorithm == ClusteringAlgorithm.SPECTRAL:
                from sklearn.cluster import SpectralClustering
                clusterer = SpectralClustering(n_clusters=n_clusters, 
                                               random_state=self.config.random_state)
                labels = clusterer.fit_predict(X)
            
            elif algorithm == ClusteringAlgorithm.OPTICS:
                from sklearn.cluster import OPTICS
                clusterer = OPTICS(min_samples=self.config.min_cluster_size)
                labels = clusterer.fit_predict(X)
            
            else:
                raise ValueError(f"Unknown clustering algorithm: {algorithm}")
            
            return labels
            
        except Exception as e:
            logger.error(f"Clustering failed with {algorithm.value}: {e}")
            # Fallback to KMeans
            from sklearn.cluster import KMeans
            clusterer = KMeans(n_clusters=min(n_clusters, 2), 
                              random_state=self.config.random_state,
                              n_init=10)
            return clusterer.fit_predict(X)
    
    def _find_optimal_clusters(self, 
                             X: np.ndarray,
                             max_clusters: int,
                             algorithm: ClusteringAlgorithm) -> int:
        """Find the optimal number of clusters using silhouette score."""
        if max_clusters < 2:
            return 2
        
        best_score = -1
        best_n = 2
        
        for n_clusters in range(2, max_clusters + 1):
            try:
                if algorithm == ClusteringAlgorithm.KMEANS:
                    from sklearn.cluster import KMeans
                    clusterer = KMeans(n_clusters=n_clusters, 
                                      random_state=self.config.random_state,
                                      n_init=10)
                elif algorithm == ClusteringAlgorithm.AGGLOMERATIVE:
                    from sklearn.cluster import AgglomerativeClustering
                    clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                else:
                    continue
                
                labels = clusterer.fit_predict(X)
                
                if len(set(labels)) > 1:  # Need at least 2 clusters for silhouette
                    score = silhouette_score(X, labels)
                    if score > best_score:
                        best_score = score
                        best_n = n_clusters
            except Exception:
                continue
        
        return best_n if best_n >= 2 else 2
    
    def _create_groups(self, 
                      stories: List[Story],
                      labels: np.ndarray,
                      algorithm: ClusteringAlgorithm) -> List[DigestGroup]:
        """Create DigestGroup objects from clustering results."""
        groups = []
        
        # Handle outliers for algorithms like DBSCAN
        if algorithm in [ClusteringAlgorithm.DBSCAN, ClusteringAlgorithm.OPTICS]:
            # -1 means outlier in these algorithms
            outlier_indices = [i for i, label in enumerate(labels) if label == -1]
            if outlier_indices:
                outlier_stories = [stories[i] for i in outlier_indices]
                group = DigestGroup(
                    cluster_id=-1,
                    label="Other",
                    stories=outlier_stories
                )
                groups.append(group)
            
            # Get unique cluster labels (excluding -1)
            unique_labels = set(labels) - {-1}
        else:
            unique_labels = set(labels)
        
        # Create groups for each cluster
        for cluster_id in sorted(unique_labels):
            cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
            cluster_stories = [stories[i] for i in cluster_indices]
            
            if cluster_stories:
                # Generate a label for the cluster
                label = self._generate_cluster_label(cluster_stories)
                group = DigestGroup(
                    cluster_id=cluster_id,
                    label=label,
                    stories=cluster_stories
                )
                groups.append(group)
        
        return groups
    
    def _generate_cluster_label(self, stories: List[Story]) -> str:
        """Generate a descriptive label for a cluster."""
        from collections import Counter
        import re
        
        all_words = []
        for story in stories:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', story.title.lower())
            all_words.extend(words)
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 
            'was', 'were', 'been', 'have', 'has', 'but', 'not', 'you', 
            'your', 'they', 'their', 'what', 'when', 'where', 'which',
            'there', 'here', 'some', 'such', 'only', 'also', 'very', 'more'
        }
        
        filtered_words = [w for w in all_words if w not in stop_words]
        
        if filtered_words:
            word_counts = Counter(filtered_words)
            # Get top 2-3 words
            top_words = [word for word, _ in word_counts.most_common(3)]
            return ' '.join(top_words).title()
        
        # Fallback: use first story title
        if stories:
            return stories[0].title[:30] + "..." if len(stories[0].title) > 30 else stories[0].title
        
        return "General"
    
    def assign_topics(self, 
                     stories: List[Story],
                     n_clusters: Optional[int] = None,
                     algorithm: Optional[ClusteringAlgorithm] = None) -> List[Story]:
        """Assign topic labels to stories using clustering."""
        result = self.cluster_stories(stories, n_clusters, algorithm)
        
        # Assign cluster_id and topic_label to each story
        for group in result.groups:
            for story in group.stories:
                story.cluster_id = group.cluster_id
                story.topic_label = group.label
        
        return stories
    
    def get_cluster_quality(self, 
                         stories: List[Story],
                         n_clusters: Optional[int] = None) -> Dict[str, Any]:
        """Get quality metrics for clustering."""
        if not stories or len(stories) < 2:
            return {"quality": "insufficient_data"}
        
        texts = [self._preprocess_story(story) for story in stories]
        embedding_result = self.embedding_service.batch_embed(texts)
        X = np.array(embedding_result.embeddings)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Use KMeans for quality assessment
        from sklearn.cluster import KMeans
        n_clusters = n_clusters or min(self.config.n_clusters, len(stories))
        
        clusterer = KMeans(n_clusters=n_clusters, random_state=self.config.random_state, n_init=10)
        labels = clusterer.fit_predict(X_scaled)
        
        metrics = {
            "n_clusters": n_clusters,
            "n_samples": len(stories)
        }
        
        if len(set(labels)) > 1:
            try:
                metrics["silhouette_score"] = silhouette_score(X_scaled, labels)
                metrics["db_score"] = davies_bouldin_score(X_scaled, labels)
                metrics["quality"] = "good" if metrics["silhouette_score"] > 0.5 else "fair"
            except Exception:
                metrics["quality"] = "unknown"
        else:
            metrics["quality"] = "single_cluster"
        
        return metrics


def get_clustering_service() -> ClusteringService:
    """Get the global clustering service instance."""
    # Use singleton pattern
    if not hasattr(get_clustering_service, '_instance'):
        get_clustering_service._instance = ClusteringService()
    return get_clustering_service._instance


def create_clustering_service(config: Optional[ClusteringConfig] = None) -> ClusteringService:
    """Create a new clustering service instance."""
    return ClusteringService(config=config)
