# Daily Digest Vibe

A personalized Hacker News daily digest that learns your preferences and presents the most relevant stories in grouped topics.

## Overview

This tool periodically fetches top stories from Hacker News, groups them by topic using AI, learns what you're interested in, and presents a clean daily digest.

## Features

- **Automated Story Collection**: Fetches top N stories from HN API periodically
- **AI-Powered Grouping**: Uses embeddings and clustering to group related stories
- **Preference Learning**: Tracks your reading habits and filters out uninteresting topics
- **Daily Digest**: Clean presentation of the most important stories

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Digest Vibe                           │
├─────────────────┬─────────────────┬─────────────────┬─────────┤
│  HN API Client   │   Story Storage  │  AI Grouping     │  Digest │
│  (fetch stories) │  (SQLite/JSON)   │  (clustering)    │  Gen    │
└────────┬────────┴────────┬────────┴─────────┬──────────┴────┬────┘
         │                 │                  │               │
         ▼                 ▼                  ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Fetch Top N     │ │  Store/      │ │  Embed &     │ │  Generate    │
│  Stories         │ │  Update      │ │  Cluster     │ │  Daily       │
│  (e.g., 500)     │ │  Stories     │ │  Stories     │ │  Digest      │
└─────────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │                 │                  │               │
         ▼                 ▼                  ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    User Preference Learning                     │
│  - Track clicked/read stories                                 │
│  - Learn topic preferences                                    │
│  - Filter out uninteresting content                           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run initial setup
python -m daily_digest setup

# Fetch and process stories
python -m daily_digest fetch

# Generate daily digest
python -m daily_digest digest

# Run all (fetch + process + generate)
python -m daily_digest run
```

## Configuration

Create a `config.yaml` file:

```yaml
# Number of top stories to fetch
top_n: 500

# HN API base URL
api_base: https://hacker-news.firebaseio.com/v0

# Storage settings
storage:
  type: sqlite  # or json
  path: data/stories.db

# AI settings (optional - requires API keys)
ai:
  embedding_model: text-embedding-ada-002
  cluster_algorithm: kmeans
  num_clusters: 10

# Update schedule (for automated runs)
schedule:
  fetch_interval: 3600  # seconds
  digest_time: "08:00"   # daily digest generation time
```

## Project Structure

```
daily_digest/
├── __init__.py
├── cli.py              # Command-line interface
├── config.py           # Configuration management
├── hn_client.py        # Hacker News API client
├── models.py           # Data models
├── storage.py          # Story storage
├── ai_grouping.py      # AI-powered story grouping
├── preference_learner.py  # User preference learning
├── digest_generator.py # Daily digest generation
└── utils.py            # Utilities

data/
├── stories.db          # SQLite database (or JSON files)
└── preferences.json    # User preferences

tests/
└── test_*.py           # Test files
```

## Hacker News API

The tool uses the official Hacker News Firebase API:
- `https://hacker-news.firebaseio.com/v0/topstories.json` - Top story IDs
- `https://hacker-news.firebaseio.com/v0/item/{id}.json` - Story details

## AI Integration

For AI-powered features, you'll need:
- OpenAI API key for embeddings (or local embedding models)
- Optional: LLM for summarization

Set environment variables:
```bash
export OPENAI_API_KEY=your_key_here
```

## Development

```bash
# Run tests
pytest

# Type checking
mypy daily_digest

# Linting
ruff check daily_digest
```
