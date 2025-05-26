# Development Setup Guide

This guide will help you set up a development environment for the MittFortum Home Assistant integration.

## Prerequisites

- Python 3.13
- Home Assistant Core development environment
- Git
- Virtual environment support (venv or conda)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/mittfortum.git
   cd mittfortum
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Run tests:**
   ```bash
   pytest
   ```

## Development Workflow

### Code Quality

We use several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **pyrefly**: Static type checking
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks for code quality

### Running Code Quality Checks

```bash
# Lint and format code
ruff check .
ruff format .

# Type checking
pyrefly check

# Run tests with coverage
pytest tests/ --cov=custom_components/mittfortum --cov-report=html
```

### Testing

#### Unit Tests
```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest tests/unit/ -v
```

#### Integration Tests
```bash
# Run integration tests
pytest tests/integration/

# Run with Home Assistant test environment
pytest tests/integration/ --hass-ws
```

### Project Structure

```
custom_components/mittfortum/
├── __init__.py              # Integration setup
├── config_flow.py           # Configuration flow
├── const.py                 # Constants
├── coordinator.py           # Data coordinator
├── device.py               # Device representation
├── entity.py               # Base entity class
├── exceptions.py           # Custom exceptions
├── manifest.json           # Integration manifest
├── models.py               # Data models
├── sensor.py               # Sensor platform
├── utils.py                # Utility functions
├── api/                    # API client modules
│   ├── __init__.py
│   ├── auth.py             # OAuth2 authentication
│   ├── client.py           # API client
│   └── endpoints.py        # API endpoints
└── sensors/                # Sensor implementations
    ├── __init__.py
    ├── energy.py           # Energy sensors
    └── cost.py             # Cost sensors
```

## Testing with Home Assistant

### Development Environment Setup

1. **Set up Home Assistant development environment:**
   ```bash
   git clone https://github.com/home-assistant/core.git
   cd core
   script/setup
   source venv/bin/activate
   ```

2. **Link your integration:**
   ```bash
   # Create symlink to your integration
   ln -s /path/to/your/mittfortum/custom_components/mittfortum \
         /path/to/core/homeassistant/components/mittfortum
   ```

3. **Run Home Assistant in development mode:**
   ```bash
   hass --config config_dev
   ```

### Testing Configuration

Create a test configuration file:

```yaml
# config_dev/configuration.yaml
default_config:

logger:
  default: info
  logs:
    custom_components.mittfortum: debug

# Test with demo data
mittfortum:
  username: "test_user"
  password: "test_password"
```

## API Development

### OAuth2 Flow Testing

You can test the OAuth2 flow using the included test client:

```python
import asyncio
from custom_components.mittfortum.api.auth import OAuth2AuthClient

async def test_auth():
    client = OAuth2AuthClient("client_id", "client_secret")
    # Test authentication flow
    auth_url = await client.get_authorization_url()
    print(f"Visit: {auth_url}")
    # ... complete flow
```

### API Client Testing

Test the API client with mock data:

```python
import asyncio
from unittest.mock import AsyncMock
from custom_components.mittfortum.api.client import FortumAPIClient

async def test_api():
    mock_auth = AsyncMock()
    client = FortumAPIClient(mock_hass, mock_auth)
    data = await client.get_consumption_data()
    print(f"Data: {data}")
```

## Contributing

### Before Submitting a PR

1. **Run all tests:**
   ```bash
   pytest tests/
   ```

2. **Run code quality checks:**
   ```bash
   pre-commit run --all-files
   ```

3. **Update documentation:**
   - Update README.md if needed
   - Update CHANGELOG.md
   - Add docstrings to new functions

4. **Test with real Home Assistant:**
   - Test the integration with a real HA instance
   - Verify all sensors work correctly
   - Test configuration flow

### Commit Message Convention

We follow conventional commits:

```
feat: add new energy sensor
fix: resolve authentication timeout issue
docs: update API documentation
test: add tests for cost sensor
refactor: improve error handling
```

### Release Process

1. Update version in `manifest.json`
2. Update `CHANGELOG.md`
3. Create a tag: `git tag v3.0.0`
4. Push: `git push origin v3.0.0`
5. GitHub Actions will handle the release

## Troubleshooting

### Common Issues

1. **Import errors:**
   - Ensure you're in the virtual environment
   - Check that all dependencies are installed

2. **Test failures:**
   - Check that test fixtures are correct
   - Verify mock objects are set up properly

3. **Home Assistant integration issues:**
   - Check logs for detailed error messages
   - Verify manifest.json is correct
   - Ensure all required dependencies are listed

### Debug Logging

Enable debug logging in Home Assistant:

```yaml
logger:
  default: warning
  logs:
    custom_components.mittfortum: debug
    custom_components.mittfortum.api: debug
```

### Performance Profiling

Profile the integration performance:

```python
import cProfile
import pstats

# Profile API calls
pr = cProfile.Profile()
pr.enable()
# ... your code here
pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats()
```

## Resources

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Home Assistant Architecture](https://developers.home-assistant.io/docs/architecture_index)
- [Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index)
- [OAuth2 Implementation Guide](https://developers.home-assistant.io/docs/auth_index)
