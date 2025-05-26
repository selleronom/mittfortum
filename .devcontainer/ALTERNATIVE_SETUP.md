# Alternative Development Setup (without Docker)

If the devcontainer continues to have issues on Arch Linux, you can set up the development environment directly on your host system:

## 1. Install Python Dependencies

```bash
# Ensure you have Python 3.13 (or compatible version)
python --version

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate.fish  # for fish shell

# Install development dependencies
pip install -r requirements-dev.txt
```

## 2. Install Home Assistant for Testing

```bash
# Install Home Assistant in the same virtual environment
pip install homeassistant>=2025.1.0

# Create a config directory for testing
mkdir -p ./ha-config
```

## 3. Set Up Configuration

```bash
# Copy the devcontainer configuration as a starting point
cp .devcontainer/config/configuration.yaml ./ha-config/
cp .devcontainer/config/secrets.yaml.template ./ha-config/secrets.yaml

# Edit secrets with your credentials
$EDITOR ./ha-config/secrets.yaml
```

## 4. Link Your Integration

```bash
# Create custom_components directory and link your integration
mkdir -p ./ha-config/custom_components
ln -sf "$(pwd)/custom_components/mittfortum" ./ha-config/custom_components/mittfortum
```

## 5. Start Development

```bash
# Run all quality checks
pytest
ruff check .
ruff format .
pyrefly .

# Start Home Assistant
hass --config ./ha-config --debug

# Open http://localhost:8123 in your browser
```

## 6. VS Code Configuration

The existing VS Code tasks will work with this setup. You can use:
- `Ctrl+Shift+P` → "Tasks: Run Task" → Choose any task
- Or run commands directly in the integrated terminal

## 7. Development Workflow

1. Make changes to your integration
2. Run tests: `pytest`
3. Check code quality: `ruff check . && pyrefly .`
4. Restart Home Assistant to see changes
5. Test in the web interface

This approach gives you the same development experience without Docker networking issues.
