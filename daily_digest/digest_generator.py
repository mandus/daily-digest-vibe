"""
Daily digest generation for Daily Digest Vibe.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import Story, DigestGroup, DailyDigest
from .storage import get_storage
from .ai_grouping import create_grouper
from .preference_learner import create_preference_learner


class DigestGenerator:
    """Generates daily digests from stories."""
    
    def __init__(self, user_id: str = "default"):
        """Initialize digest generator."""
        self.user_id = user_id
        self.storage = get_storage()
        self.grouper = create_grouper()
        self.preference_learner = create_preference_learner(user_id)
    
    def generate_digest(self, stories: Optional[List[Story]] = None, 
                       n_clusters: Optional[int] = None) -> DailyDigest:
        """Generate a daily digest from stories."""
        if stories is None:
            # Get all recent stories (last 24 hours)
            stories = self.storage.get_recent_stories(hours=24)
        
        if not stories:
            return DailyDigest(
                total_stories=0,
                new_stories_since_last=0
            )
        
        # Filter and rank stories based on preferences
        filtered_stories = self.preference_learner.filter_stories(stories)
        ranked_stories = self.preference_learner.rank_stories(filtered_stories)
        
        # Cluster stories into groups
        groups = self.grouper.cluster_stories(ranked_stories, n_clusters)
        
        # Generate summaries for groups
        groups = self.grouper.generate_summaries(groups)
        
        # Sort groups by total score
        sorted_groups = sorted(groups, key=lambda g: g.total_score, reverse=True)
        
        # Calculate new stories since last digest
        # (This would be more sophisticated in a real implementation)
        new_stories_since_last = len([s for s in stories if s.is_recent])
        
        return DailyDigest(
            date=datetime.utcnow(),
            groups=sorted_groups,
            total_stories=len(stories),
            new_stories_since_last=new_stories_since_last
        )
    
    def generate_text_digest(self, digest: Optional[DailyDigest] = None, 
                            n_clusters: Optional[int] = None) -> str:
        """Generate a text-based digest."""
        if digest is None:
            digest = self.generate_digest(n_clusters=n_clusters)
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"DAILY DIGEST - {digest.date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 60)
        lines.append(f"Total stories: {digest.total_stories}")
        lines.append(f"New since last check: {digest.new_stories_since_last}")
        lines.append("")
        
        for i, group in enumerate(digest.top_groups, 1):
            lines.append(f"--- Group {i}: {group.label} ---")
            lines.append(f"Summary: {group.summary}")
            lines.append(f"Stories: {group.story_count}, Total Score: {group.total_score}")
            lines.append("")
            
            # Show top stories in each group
            sorted_stories = sorted(group.stories, key=lambda s: s.score, reverse=True)
            for story in sorted_stories[:5]:  # Top 5 stories per group
                prefix = "[READ]" if story.user_read else "[NEW]"
                lines.append(f"  {prefix} {story.score:4d} pts | {story.title}")
                if story.url:
                    lines.append(f"       {story.url}")
                lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def generate_html_digest(self, digest: Optional[DailyDigest] = None,
                            n_clusters: Optional[int] = None) -> str:
        """Generate an HTML digest."""
        if digest is None:
            digest = self.generate_digest(n_clusters=n_clusters)
        
        html = []
        html.append("<html><head><title>Daily Digest</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }")
        html.append("h1 { color: #ff6600; border-bottom: 2px solid #ff6600; padding-bottom: 10px; }")
        html.append(".group { margin-bottom: 30px; border-left: 4px solid #ff6600; padding-left: 15px; }")
        html.append(".group h2 { margin-top: 0; color: #ff6600; }")
        html.append(".story { margin: 10px 0; padding: 10px; border: 1px solid #eee; border-radius: 5px; }")
        html.append(".story.read { background-color: #f5f5f5; }")
        html.append(".story.new { background-color: #fff8e1; }")
        html.append(".score { color: #ff6600; font-weight: bold; }")
        html.append(".meta { color: #666; font-size: 0.9em; }")
        html.append("</style>")
        html.append("</head><body>")
        html.append(f"<h1>Daily Digest - {digest.date.strftime('%Y-%m-%d %H:%M:%S UTC')}</h1>")
        html.append(f"<p>Total stories: {digest.total_stories} | New: {digest.new_stories_since_last}</p>")
        
        for i, group in enumerate(digest.top_groups, 1):
            html.append(f'<div class="group">')
            html.append(f'<h2>Group {i}: {group.label}</h2>')
            html.append(f'<p><em>{group.summary}</em></p>')
            html.append(f'<p class="meta">{group.story_count} stories, Total Score: {group.total_score}</p>')
            
            sorted_stories = sorted(group.stories, key=lambda s: s.score, reverse=True)
            for story in sorted_stories[:10]:  # Top 10 stories per group
                css_class = "read" if story.user_read else "new"
                html.append(f'<div class="story {css_class}">')
                html.append(f'<span class="score">{story.score} pts</span> ')
                if story.url:
                    html.append(f'<a href="{story.url}">{story.title}</a>')
                else:
                    html.append(f'<span>{story.title}</span>')
                if story.by:
                    html.append(f'<span class="meta"> by {story.by}</span>')
                if story.url_domain:
                    html.append(f'<span class="meta"> ({story.url_domain})</span>')
                html.append(f'<span class="meta"> | {story.descendants} comments</span>')
                html.append('</div>')
            
            html.append('</div>')
        
        html.append("</body></html>")
        return "\n".join(html)
    
    def generate_markdown_digest(self, digest: Optional[DailyDigest] = None,
                                 n_clusters: Optional[int] = None) -> str:
        """Generate a Markdown digest."""
        if digest is None:
            digest = self.generate_digest(n_clusters=n_clusters)
        
        md = []
        md.append("# Daily Digest")
        md.append(f"**Generated:** {digest.date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append("")
        md.append(f"- **Total stories:** {digest.total_stories}")
        md.append(f"- **New since last check:** {digest.new_stories_since_last}")
        md.append("")
        
        for i, group in enumerate(digest.top_groups, 1):
            md.append(f"## Group {i}: {group.label}")
            md.append(f"> {group.summary}")
            md.append(f"*{group.story_count} stories, Total Score: {group.total_score}*")
            md.append("")
            
            sorted_stories = sorted(group.stories, key=lambda s: s.score, reverse=True)
            for story in sorted_stories[:10]:
                prefix = "✓" if story.user_read else "•"
                md.append(f"- {prefix} **{story.score} pts** [{story.title}]({story.url or ''})")
                if story.by:
                    md.append(f"  *by {story.by}*")
                if story.url_domain:
                    md.append(f"  *{story.url_domain}*")
                md.append(f"  *{story.descendants} comments*")
                md.append("")
        
        return "\n".join(md)
    
    def save_digest(self, digest: DailyDigest, format: str = "text") -> str:
        """Save digest to file."""
        from pathlib import Path
        
        # Create digests directory
        digests_dir = Path("data/digests")
        digests_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = digest.date.strftime("%Y%m%d_%H%M%S")
        filename = digests_dir / f"digest_{timestamp}.{format}"
        
        # Generate content based on format
        if format == "text":
            content = self.generate_text_digest(digest)
        elif format == "html":
            content = self.generate_html_digest(digest)
        elif format == "md":
            content = self.generate_markdown_digest(digest)
        else:
            raise ValueError(f"Unknown format: {format}")
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filename)
    
    def get_digest_statistics(self, digest: DailyDigest) -> Dict[str, Any]:
        """Get statistics about a digest."""
        stats = {
            'total_stories': digest.total_stories,
            'new_stories': digest.new_stories_since_last,
            'num_groups': len(digest.groups),
            'total_groups_score': sum(g.total_score for g in digest.groups),
            'avg_stories_per_group': sum(g.story_count for g in digest.groups) / len(digest.groups) if digest.groups else 0
        }
        
        # Top topics
        topic_counts = {}
        for group in digest.groups:
            topic_counts[group.label] = group.story_count
        stats['top_topics'] = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return stats


def create_digest_generator(user_id: str = "default") -> DigestGenerator:
    """Create a digest generator for a user."""
    return DigestGenerator(user_id)
