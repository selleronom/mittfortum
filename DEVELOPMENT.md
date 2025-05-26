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

# Development Container Setup

For the best development experience, use the provided VS Code development container. This provides a complete Home Assistant development environment with all tools pre-configured.

## Prerequisites

- [VS Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- [Docker](https://www.docker.com/get-started)

## Quick Start

1. **Open in Container**
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/mittfortum.git
   cd mittfortum

   # Open in VS Code
   code .

   # When prompted, click "Reopen in Container"
   # Or use Command Palette: "Dev Containers: Reopen in Container"
   ```

2. **Initial Setup**
   - The container will automatically install all dependencies
   - Copy and configure secrets:
     ```bash
     cp .devcontainer/config/secrets.yaml.template .devcontainer/config/secrets.yaml
     # Edit with your MittFortum credentials
     ```

3. **Start Development**
   - Run all checks: `.devcontainer/test-integration.sh`
   - Start Home Assistant: `.devcontainer/start-hass.sh`
   - Open http://localhost:8123

## Development Workflow

#### Testing Your Integration

1. **Add Integration in HA**
   - Go to Settings → Devices & Services
   - Click "Add Integration" → Search "MittFortum"
   - Follow setup with your credentials

2. **Monitor Logs**
   ```bash
   # In VS Code terminal or separate terminal
   tail -f /config/home-assistant.log
   ```

3. **Make Changes**
   - Edit integration code
   - Restart HA to see changes
   - Check logs for errors

#### Available VS Code Tasks

Access via `Ctrl+Shift+P` → "Tasks: Run Task":

- **Start Home Assistant**: Launch HA with your integration
- **Run Tests**: Execute all tests with coverage
- **Lint with Ruff**: Check code style
- **Format with Ruff**: Auto-format code
- **Type Check with Pyrefly**: Static type analysis
- **Run All Checks**: Execute complete quality pipeline

#### Quick Commands

```bash
# Run comprehensive test suite
.devcontainer/test-integration.sh

# Individual commands
pytest                          # Run all tests
pytest tests/unit/ -v          # Run unit tests only
ruff check .                   # Lint code
ruff format .                  # Format code
pyrefly .                      # Type check
pre-commit run --all-files     # Run all hooks

# Home Assistant commands
.devcontainer/start-hass.sh    # Start HA
hass --config /config --debug  # Start HA manually with debug
```

### Debugging

#### VS Code Debugging

Use pre-configured debug configurations:
- **Debug Tests**: Debug test suite
- **Debug Specific Test**: Debug current test file
- **Debug Integration**: Debug integration tests
- **Debug Unit Tests**: Debug unit tests only

#### Home Assistant Debugging

```python
# Add to your integration code
import logging
_LOGGER = logging.getLogger(__name__)

# In your functions
_LOGGER.debug("Debug message with data: %s", data)
_LOGGER.info("Info message")
_LOGGER.warning("Warning message")
_LOGGER.error("Error message")
```

### Container Features

The development container includes:

- **Home Assistant Core**: Latest version for testing
- **Python 3.13**: Latest Python with all dev tools
- **Pre-configured VS Code**: Optimized extensions and settings
- **Development Tools**: Ruff, Pyrefly, Pytest, Pre-commit
- **Hot Reload**: Your changes immediately available in HA
- **Debugging Support**: Full VS Code debugging capabilities

### Tips and Best Practices

1. **Fast Development Cycle**
   - Keep HA running during development
   - Only restart when needed (manifest changes, new entities)
   - Use HA's reload functionality when available

2. **Efficient Testing**
   - Run unit tests frequently: `pytest tests/unit/`
   - Run integration tests before commits: `pytest tests/integration/`
   - Use coverage to identify untested code

3. **Code Quality**
   - Format on save is enabled (Ruff)
   - Pre-commit hooks run automatically
   - Type hints are enforced (Pyrefly)

4. **Debugging Strategy**
   - Use VS Code debugger for complex issues
   - Add strategic logging statements
   - Check HA logs regularly: `tail -f /config/home-assistant.log`

### Troubleshooting

#### Container Issues
```bash
# Rebuild container if there are issues
# Command Palette → "Dev Containers: Rebuild Container"

# Check container logs
docker logs <container-id>
```

#### Home Assistant Issues
```bash
# Check configuration syntax
hass --config /config --script check_config

# Start with debug logging
hass --config /config --debug --verbose

# Clear HA cache
rm -rf /config/.storage
```

#### Integration Issues
```bash
# Verify integration is linked
ls -la /config/custom_components/mittfortum

# Check manifest syntax
python -c "import json; print(json.load(open('custom_components/mittfortum/manifest.json')))"

# Test integration loading
python -c "from custom_components.mittfortum import async_setup"
```

For more detailed documentation, see `.devcontainer/README.md`
