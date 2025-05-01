# FoglioAI 📰

A vintage newspaper-style article generator powered by AI agents. This project uses multiple specialized AI agents to research, analyze, and compose articles in the style of a 1920s newspaper.

## Features

- 🤖 Multiple specialized AI agents (Economist, Politics, Historian, etc.)
- 📝 Collaborative article generation with agent reflection
- 🎨 Vintage 1920s newspaper styling
- 📊 Automatic chart and image generation
- 🌐 Web content retrieval and caching
- 🔄 Real-time article composition with streaming updates

## Tech Stack

- FastAPI for the backend API
- CrewAI for agent orchestration
- Redis for agent communication and caching
- Jinja2 for newspaper template rendering
- HTMX + Alpine.js for the frontend
- Poetry for dependency management
- Docker for containerization

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry for Python package management
- Docker and Docker Compose
- Anthropic API key for Claude
- Mistral API key for Mistral AI

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/foglioai.git
   cd foglioai
   ```

2. Create a `.env` file with your API keys:
   ```bash
   ANTHROPIC_API_KEY=your-anthropic-api-key
   MISTRAL_API_KEY=your-mistral-api-key
   ```

### Local Development

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Set up pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

3. Run the development server:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

### Docker Development

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. Access the application:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

3. View logs:
   ```bash
   docker-compose logs -f
   ```

4. Stop the containers:
   ```bash
   docker-compose down
   ```

### Docker Commands

- Rebuild a specific service:
  ```bash
  docker-compose up -d --no-deps --build app
  ```

- View container status:
  ```bash
  docker-compose ps
  ```

- Access Redis CLI:
  ```bash
  docker-compose exec redis redis-cli
  ```

- Access application container:
  ```bash
  docker-compose exec app bash
  ```

## Testing

Run tests with pytest:
```bash
poetry run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
