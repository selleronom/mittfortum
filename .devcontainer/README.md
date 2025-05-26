# MittFortum Home Assistant Development Container

This development container provides a complete environment for developing and testing the MittFortum Home Assistant integration.

## Features

- **Home Assistant Core**: Latest version for testing your integration
- **Python 3.13**: Latest Python version with all development tools
- **Pre-configured VS Code**: Extensions and settings optimized for HA development
- **Development Tools**: Ruff, Pyrefly, Pytest, Pre-commit hooks
- **Hot Reload**: Your integration changes are immediately available in HA

## Quick Start

1. **Open in Dev Container**
   - Install the "Dev Containers" extension in VS Code
   - Open the project folder
   - Click "Reopen in Container" when prompted (or use Command Palette: "Dev Containers: Reopen in Container")

2. **Wait for Setup**
   - The container will automatically install dependencies and set up the environment
   - This may take a few minutes on first run

3. **Configure Secrets**
   ```bash
   cp .devcontainer/config/secrets.yaml.template .devcontainer/config/secrets.yaml
   # Edit the secrets.yaml file with your actual MittFortum credentials
   ```

4. **Start Home Assistant**
   - Use VS Code Task: `Ctrl+Shift+P` → "Tasks: Run Task" → "Start Home Assistant"
   - Or run in terminal: `.devcontainer/start-hass.sh`
   - Open http://localhost:8123 in your browser

## Development Workflow

### Testing Your Integration

1. **Add the Integration**
   - Go to Settings → Devices & Services in HA
   - Click "Add Integration"
   - Search for "MittFortum"
   - Follow the setup flow

2. **View Logs**
   - Check logs in HA: Settings → System → Logs
   - Or view in terminal where HA is running

3. **Make Changes**
   - Edit your integration code
   - Restart HA to see changes: Settings → System → Restart

### Available VS Code Tasks

- **Start Home Assistant**: Launch HA development server
- **Run Tests**: Execute all tests
- **Run Tests with Coverage**: Test with coverage report
- **Lint with Ruff**: Check code style and errors
- **Format with Ruff**: Auto-format code
- **Type Check with Pyrefly**: Static type checking
- **Run All Checks**: Execute all quality checks
- **Install Development Dependencies**: Update dev dependencies
- **Clean Cache**: Remove Python cache files

### Command Line Tools

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=custom_components.mittfortum --cov-report=term-missing

# Lint code
ruff check .

# Format code
ruff format .

# Type check
pyrefly .

# Run all pre-commit hooks
pre-commit run --all-files

# Start Home Assistant manually
hass --config /config --debug
```

## Directory Structure

```
/workspace/                    # Your integration code
├── custom_components/mittfortum/  # The integration
├── tests/                     # Test files
└── .devcontainer/             # Container configuration

/config/                       # Home Assistant configuration
├── configuration.yaml         # HA config with integration enabled
├── secrets.yaml               # Your credentials (create from template)
└── custom_components/         # Symlinked to your integration
```

## Configuration Files

### Home Assistant Configuration

The devcontainer includes a pre-configured `configuration.yaml` that:
- Enables debug logging for your integration
- Includes sample automations and templates
- Has optimal settings for development

### Secrets Management

1. Copy the template: `cp .devcontainer/config/secrets.yaml.template .devcontainer/config/secrets.yaml`
2. Edit with your actual credentials
3. The secrets file is gitignored for security

## Debugging

### VS Code Debugging

Use the pre-configured debug configurations:
- **Debug Tests**: Debug all tests
- **Debug Specific Test**: Debug the currently open test file
- **Debug Integration Test**: Debug integration tests only
- **Debug Unit Tests**: Debug unit tests only

### Home Assistant Debugging

1. Enable debug logging in configuration.yaml:
   ```yaml
   logger:
     logs:
       custom_components.mittfortum: debug
   ```

2. View logs in HA or terminal
3. Use `pdb` or VS Code debugger in your code

## Tips

- **Fast Development**: Keep HA running and restart it after changes
- **Hot Reload**: Some changes might not require a full restart
- **Log Watching**: Use `tail -f /config/home-assistant.log` to watch logs
- **Integration Reload**: Some integrations support reload without restart

## Troubleshooting

### Container Won't Start
- Check Docker is running
- Ensure you have enough disk space
- Try rebuilding: Command Palette → "Dev Containers: Rebuild Container"

### Home Assistant Won't Start
- Check `/config/configuration.yaml` syntax
- Ensure secrets.yaml exists and has valid credentials
- Check logs for specific error messages

### Integration Not Found
- Verify the symlink: `ls -la /config/custom_components/`
- Restart Home Assistant
- Check integration manifest.json is valid

### Tests Failing
- Run `pip install -r requirements-dev.txt`
- Clear cache: `find . -name "__pycache__" -exec rm -rf {} +`
- Check Python path and imports

## Support

For issues with the MittFortum integration itself, please check:
- Integration logs in Home Assistant
- Test results: `pytest -v`
- Code quality: `ruff check .`
- Type checking: `pyrefly .`
