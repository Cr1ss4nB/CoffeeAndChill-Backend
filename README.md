# CoffeeAndChill-Backend

## Linting & Formatting

```bash
# Format code with black
black .

# Run flake8 linter
flake8 .

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

## Architecture

- `app/core/` - Core utilities (config, database, security, redis)
- `app/models/` - Data models
- `app/schemas/` - Pydantic schemas
- `app/routers/` - API endpoints
- `tests/` - Test files