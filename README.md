# Weather Proxy

A production-ready REST API that proxies [Open-Meteo](https://open-meteo.com/) weather data with caching, observability, and reliability patterns.

## Requirements

- Python 3.11+
- Redis (for caching)
- Docker & Docker Compose (optional, for containerized execution)

## Local Setup

```bash
# Clone the repository
git clone <repo-url>
cd WeatherProxy

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Running the Application

```bash
# Start the API (requires Redis)
uvicorn app.main:app --reload

# The API will be available at http://localhost:8000
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Lint and format checks
ruff check app/ tests/
ruff format --check app/ tests/
```

## Docker

```bash
# Build and run with Docker Compose (includes Redis)
docker-compose up --build

# Access the API at http://localhost:8000
```

## Project Structure

```
app/
  main.py              # FastAPI application
  api/                 # API routes and dependencies
  core/                # Configuration, logging, error handling
  services/            # Business logic
  repositories/        # Data access layer

tests/
  conftest.py          # Pytest fixtures and configuration
  test_health.py       # Health endpoint tests
  
pyproject.toml         # Project metadata and dependencies
README.md              # This file
```

## API Endpoints

- `GET /health` – Health check
- `GET /weather?city=<city>` – Get weather for a city (coming in Block 8)

## Design Decisions

See `docs/adr/0001-architecture.md` for detailed architecture decisions.

## Development

This project follows a block-based development approach with incremental commits. Each block is implemented, tested, and committed separately.
