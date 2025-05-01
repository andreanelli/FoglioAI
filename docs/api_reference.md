# FoglioAI API Reference

This document describes the main endpoints for the article generation API.

---

## POST `/api/compose`
**Description:** Start a new article generation job.

**Request Body:**
```json
{
  "topic": "The Rise of Artificial Intelligence",
  "style_guide": {
    "tone": "1920s newspaper",
    "length": "longform"
  }
}
```

**Response:**
```json
{
  "article_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Usage Examples:**
- **curl:**
  ```bash
  curl -X POST http://localhost:8000/api/compose \
    -H "Content-Type: application/json" \
    -d '{"topic": "The Rise of Artificial Intelligence", "style_guide": {"tone": "1920s newspaper", "length": "longform"}}'
  ```
- **Python (requests):**
  ```python
  import requests
  resp = requests.post(
      "http://localhost:8000/api/compose",
      json={
          "topic": "The Rise of Artificial Intelligence",
          "style_guide": {"tone": "1920s newspaper", "length": "longform"}
      }
  )
  print(resp.json())
  ```

**Errors:**
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected error

**Rate Limiting:** 10 requests per minute per client

---

## GET `/api/compose/{article_id}`
**Description:** Get the status of an article generation job.

**Response:**
```json
{
  "article_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending", // or "in_progress", "completed", "failed"
  "error": null
}
```

**Usage Examples:**
- **curl:**
  ```bash
  curl http://localhost:8000/api/compose/123e4567-e89b-12d3-a456-426614174000
  ```
- **Python (requests):**
  ```python
  import requests
  resp = requests.get("http://localhost:8000/api/compose/123e4567-e89b-12d3-a456-426614174000")
  print(resp.json())
  ```

**Errors:**
- `404 Not Found`: Article not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected error

**Rate Limiting:** 10 requests per minute per client

---

## GET `/api/compose/{article_id}/html`
**Description:** Get the generated article as HTML (vintage newspaper style).

**Response:**
- Content-Type: `text/html`
- Body: Rendered HTML of the article

**Usage Examples:**
- **curl:**
  ```bash
  curl http://localhost:8000/api/compose/123e4567-e89b-12d3-a456-426614174000/html
  ```
- **Python (requests):**
  ```python
  import requests
  resp = requests.get("http://localhost:8000/api/compose/123e4567-e89b-12d3-a456-426614174000/html")
  print(resp.text)  # HTML content
  ```

**Errors:**
- `404 Not Found`: Article not found
- `400 Bad Request`: Article not ready
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected error

**Rate Limiting:** 10 requests per minute per client

---

## GET `/api/compose/{article_id}/events`
**Description:** Subscribe to Server-Sent Events (SSE) for real-time article generation progress.

**Response:**
- Content-Type: `text/event-stream`
- Events:
  - `progress`: ArticleProgress JSON
  - `error`: ArticleError JSON
  - `completed`: ComposeResponse JSON

**Example Event:**
```
event: progress
data: {"article_id": "123e4567-e89b-12d3-a456-426614174000", "agent_id": "editor", "message": "Writing introduction..."}
```

**Usage Example (Python SSE client):**
```python
import requests

with requests.get(
    "http://localhost:8000/api/compose/123e4567-e89b-12d3-a456-426614174000/events",
    stream=True,
) as resp:
    for line in resp.iter_lines():
        if line:
            print(line.decode())
```

**Errors:**
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected error

**Rate Limiting:** 10 requests per minute per client

---

## Error Handling Patterns
- All error responses are JSON with a `detail` field:
  ```json
  { "detail": "Rate limit exceeded" }
  ```
- Handle 429 errors by retrying after a delay.
- Handle 400/404/500 errors by displaying the error message to the user.

---

## Integration Guide: Event Stream Handling
- Use an SSE client (e.g., Python `requests` with `stream=True`, or JavaScript `EventSource`) to receive real-time progress.
- Each event is prefixed with `event: <type>` and followed by a JSON payload.
- Example (JavaScript):
  ```js
  const evtSource = new EventSource('/api/compose/123e4567-e89b-12d3-a456-426614174000/events');
  evtSource.onmessage = function(event) {
    console.log(event.data);
  };
  evtSource.addEventListener('progress', function(event) {
    const data = JSON.parse(event.data);
    // handle progress
  });
  evtSource.addEventListener('completed', function(event) {
    // handle completion
  });
  evtSource.addEventListener('error', function(event) {
    // handle error
  });
  ```

---

## General Notes
- All endpoints are rate limited (10 requests/minute per client).
- No authentication is required for these endpoints (unless otherwise configured).
- Error responses are JSON with a `detail` field describing the error.
- For more details on request/response models, see the OpenAPI docs at `/docs` or `/openapi.json` when running the server. 