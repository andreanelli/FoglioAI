# Redis Integration Guide

This guide explains how to use the Redis integration in the FoglioAI project for data storage and agent communication.

## Overview

The Redis integration consists of several components:

1. **RedisStorage**: Core storage implementation for article runs, memos, citations, and visuals
2. **AgentScratchpad**: Pub/Sub system for agent communication
3. **Utility Functions**: Helper functions for error handling, ID generation, time handling, and validation

## Storage

### RedisStorage

The `RedisStorage` class provides methods to store and retrieve data models:

```python
from app.storage.redis import RedisStorage
from redis import Redis

# Initialize storage
redis_client = Redis(host="localhost", port=6379, decode_responses=True)
storage = RedisStorage(redis_client)

# Store an article run
storage.save_article_run(article_run)

# Retrieve an article run
article = storage.get_article_run(article_id)

# Store a memo
storage.save_agent_memo(memo, article_id)

# Get all memos for an article
memos = storage.get_agent_memos(article_id)

# Store a citation
storage.save_citation(citation, article_id)

# Get all citations for an article
citations = storage.get_citations(article_id)
```

### Data TTL

All data stored in Redis has a Time-To-Live (TTL) to prevent unbounded growth:

```python
from datetime import timedelta
from app.utils.time import calculate_ttl

# Calculate TTL with bounds
ttl = calculate_ttl(
    base_ttl=timedelta(days=7),
    min_ttl=timedelta(days=1),
    max_ttl=timedelta(days=30)
)

# Store with custom TTL
storage.save_article_run(article_run, ttl=ttl)
```

## Agent Communication

### AgentScratchpad

The `AgentScratchpad` class provides a pub/sub system for agent communication:

```python
from app.pubsub.scratchpad import agent_scratchpad, Message, MessageType

# Subscribe to article updates
def handle_message(message: Message) -> None:
    print(f"Received message: {message}")

agent_scratchpad.subscribe_to_article(article_id, handle_message)

# Publish a message
message = Message(
    type=MessageType.AGENT_PROGRESS,
    agent_id="researcher",
    article_id=article_id,
    content={"progress": 50}
)
agent_scratchpad.publish_message(message)

# Get message history
history = agent_scratchpad.get_message_history(article_id)

# Clean up
agent_scratchpad.clear_message_history(article_id)
agent_scratchpad.unsubscribe_from_article(article_id)
```

### Message Types

Available message types:

- `AGENT_STARTED`: Agent has started processing
- `AGENT_PROGRESS`: Progress update from an agent
- `AGENT_COMPLETED`: Agent has completed its task
- `AGENT_ERROR`: Agent encountered an error
- `CITATION_ADDED`: New citation was added
- `VISUAL_ADDED`: New visual was added
- `EDITOR_FEEDBACK`: Feedback from the editor agent

## Error Handling

### Retry Decorator

The `@retry` decorator handles transient Redis errors:

```python
from app.utils.errors import retry

@retry(retries=3, delay=1.0, backoff=2.0)
def redis_operation():
    # Redis operation that might fail
    pass
```

### Validation

Utility functions for data validation:

```python
from app.utils.validation import validate_url, validate_image_data

# Validate URL
if validate_url(url):
    # URL is valid

# Validate image data
try:
    validate_image_data(
        data,
        max_size=1024 * 1024,  # 1MB
        allowed_mime_types=["image/png", "image/jpeg"]
    )
except ValidationError as e:
    print(f"Invalid image: {e}")
```

## Development Setup

1. Start Redis:
   ```bash
   docker-compose up -d redis
   ```

2. Configure environment:
   ```bash
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   ```

3. Run tests:
   ```bash
   pytest tests/integration/test_redis_integration.py -v
   ```

## Performance Considerations

1. **Connection Pooling**: The Redis client uses connection pooling by default. Configure pool size based on your needs.

2. **Batch Operations**: Use pipeline for batch operations:
   ```python
   with redis_client.pipeline() as pipe:
       pipe.set("key1", "value1")
       pipe.set("key2", "value2")
       pipe.execute()
   ```

3. **TTL Management**: All data has TTL to prevent memory issues. Monitor Redis memory usage.

4. **Message History**: Message history is capped to prevent unbounded growth.

## Best Practices

1. Always use the retry decorator for Redis operations
2. Set appropriate TTLs for your data
3. Clean up message history when no longer needed
4. Use validation functions to ensure data integrity
5. Monitor Redis memory usage and connection pool metrics
6. Use integration tests to verify Redis functionality

## Troubleshooting

Common issues and solutions:

1. **Connection Errors**:
   - Check Redis host and port configuration
   - Verify Redis is running
   - Check network connectivity

2. **Memory Issues**:
   - Monitor Redis memory usage
   - Adjust TTL values
   - Clear message history regularly

3. **Performance Issues**:
   - Use connection pooling
   - Batch operations with pipeline
   - Monitor slow operations in Redis logs

## API Reference

See the following modules for detailed API documentation:

- `app.storage.redis`: Storage implementation
- `app.pubsub.scratchpad`: Agent communication
- `app.utils.errors`: Error handling
- `app.utils.time`: Time utilities
- `app.utils.validation`: Data validation 