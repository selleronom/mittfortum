# MittFortum Home Assistant Integration

A Home Assistant custom integration for accessing energy consumption data from Fortum's MittFortum service.

## Features

- **Energy Consumption Monitoring**: Track your energy usage over time
- **Cost Tracking**: Monitor energy costs in SEK
- **Secure OAuth2 Authentication**: Uses Fortum's official authentication system
- **Automatic Token Refresh**: Handles token expiration automatically
- **Device Integration**: Creates a device in Home Assistant for easy management

## Installation

### HACS (Recommended)

 This integration is not yet available in the default HACS repositories, but you can add it as a custom repository:

1. Open HACS in Home Assistant
2. Click on the 3 dots in the top right corner
3. Select "Custom repositories"
4. Add the repository URL: `https://github.com/selleronom/mittfortum`
5. Select "Integration" as the category
6. Click the "ADD" button
7. Search for "MittFortum" in HACS and install it
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/selleronom/mittfortum/releases)
2. Copy the `custom_components/mittfortum` directory to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Configuration > Integrations
2. Click "Add Integration"
3. Search for "MittFortum"
4. Enter your MittFortum username and password
5. Complete the setup

## Entities

The integration creates the following entities:

- **Energy Consumption Sensor**: Total energy consumption in kWh
- **Total Cost Sensor**: Total energy cost in SEK

## Architecture

This integration follows modern Home Assistant development practices:

### Project Structure

```
custom_components/mittfortum/
├── __init__.py              # Integration setup and teardown
├── api/                     # API client modules
│   ├── __init__.py
│   ├── auth.py              # OAuth2 authentication client
│   ├── client.py            # Main API client
│   └── endpoints.py         # API endpoint definitions
├── sensors/                 # Sensor entity modules
│   ├── __init__.py
│   ├── energy.py            # Energy consumption sensor
│   └── cost.py              # Cost sensor
├── config_flow.py           # Configuration flow
├── const.py                 # Constants and configuration
├── coordinator.py           # Data update coordinator
├── device.py                # Device representation
├── entity.py                # Base entity class
├── exceptions.py            # Custom exceptions
├── models.py                # Data models
├── sensor.py                # Sensor platform setup
├── utils.py                 # Utility functions
├── manifest.json            # Integration manifest
├── strings.json             # UI strings
└── translations/            # Localization files
    └── en.json
```

### Key Components

#### OAuth2 Authentication (`api/auth.py`)
- Handles the complete OAuth2 flow with Fortum's SSO system
- Manages token lifecycle (access, refresh, ID tokens)
- Implements PKCE (Proof Key for Code Exchange) for security

#### API Client (`api/client.py`)
- Provides high-level API for consuming Fortum services
- Handles authentication headers and token refresh
- Implements proper error handling and retry logic

#### Data Coordinator (`coordinator.py`)
- Manages data updates from the API
- Implements efficient polling with configurable intervals
- Handles API errors gracefully

#### Data Models (`models.py`)
- Type-safe data structures for API responses
- Consistent data validation and transformation
- Easy serialization/deserialization

#### Custom Exceptions (`exceptions.py`)
- Comprehensive error hierarchy
- Clear error messages for debugging
- Proper exception chaining

### Features

- **Type Safety**: Full type annotations with pyrefly support
- **Error Handling**: Comprehensive exception handling with proper error messages
- **Testing**: Unit and integration tests with high coverage
- **Code Quality**: Pre-commit hooks with black, isort, flake8, and pyrefly
- **Documentation**: Comprehensive docstrings and README
- **Logging**: Structured logging for debugging and monitoring

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run type checking
pyrefly check

# Format code
black custom_components/mittfortum
isort custom_components/mittfortum
```

### Testing

The project includes comprehensive tests:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit

# Run integration tests only
pytest tests/integration

# Run with coverage
pytest --cov=custom_components.mittfortum
```

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **pyrefly**: Type checking
- **pre-commit**: Git hooks for automated checks

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Verify your MittFortum credentials
2. **No Data**: Check that you have energy consumption data in your MittFortum account
3. **Connection Issues**: Verify your internet connection and Home Assistant's network access

### Debug Logging

Add the following to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.mittfortum: debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 3.0.0
- Complete refactor with modern Home Assistant practices
- Improved OAuth2 authentication flow
- Better error handling and logging
- Comprehensive test suite
- Type safety with pyrefly
- Modular architecture

### Version 2.1.1
- Previous version with basic functionality

## Support

- [GitHub Issues](https://github.com/selleronom/mittfortum/issues)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

## Acknowledgments

- Fortum for providing the API
- Home Assistant community for guidance and best practices

To set up this integration, you need to provide your MittFortum username and password.


## Usage

Once the integration is set up, you can start monitoring your energy usage from Home Assistant.
Please note that this integration requires a MittFortum account. If you don't have an account, you can create one on the MittFortum website.
