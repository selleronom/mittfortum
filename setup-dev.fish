#!/usr/bin/env fish

# Native Development Setup for MittFortum Home Assistant Integration
# This script sets up the development environment directly on your Arch Linux system

echo "🏠 Setting up MittFortum Home Assistant development environment (native)"
echo ""

# Check if we're in the right directory
if not test -f "custom_components/mittfortum/manifest.json"
    echo "❌ Error: Please run this script from the mittfortum project root directory"
    exit 1
end

# Check Python version
set python_version (python --version 2>&1 | sed 's/Python //')
echo "🐍 Python version: $python_version"

# Create virtual environment if it doesn't exist
if not test -d .venv
    echo "📦 Creating virtual environment..."
    python -m venv .venv
end

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate.fish

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install development dependencies
echo "📚 Installing development dependencies..."
pip install -r requirements-dev.txt

# Install Home Assistant
echo "🏠 Installing Home Assistant..."
pip install homeassistant

# Create Home Assistant config directory
echo "📁 Setting up Home Assistant configuration..."
mkdir -p ./ha-config
mkdir -p ./ha-config/custom_components

# Copy configuration files
if not test -f ./ha-config/configuration.yaml
    echo "📋 Creating Home Assistant configuration..."
    cp .devcontainer/config/configuration.yaml ./ha-config/
end

if not test -f ./ha-config/secrets.yaml
    echo "🔐 Creating secrets template..."
    cp .devcontainer/config/secrets.yaml.template ./ha-config/secrets.yaml
    echo "⚠️  Please edit ./ha-config/secrets.yaml with your MittFortum credentials"
end

# Link the integration
echo "🔗 Linking MittFortum integration..."
rm -rf ./ha-config/custom_components/mittfortum
ln -sf (pwd)/custom_components/mittfortum ./ha-config/custom_components/mittfortum

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Run initial quality checks
echo "✅ Running initial quality checks..."
echo "  - Formatting code..."
ruff format .
echo "  - Linting code..."
ruff check . --fix
echo "  - Type checking..."
pyrefly .
echo "  - Running tests..."
pytest

echo ""
echo "🎉 Setup complete! Your development environment is ready."
echo ""
echo "📋 Next steps:"
echo "1. Edit secrets: $EDITOR ./ha-config/secrets.yaml"
echo "2. Start HA: hass --config ./ha-config --debug"
echo "3. Open http://localhost:8123"
echo "4. Add MittFortum integration via the UI"
echo ""
echo "🛠️  Development commands:"
echo "• Run tests: pytest"
echo "• Lint code: ruff check ."
echo "• Format code: ruff format ."
echo "• Type check: pyrefly ."
echo "• All checks: pre-commit run --all-files"
echo "• Start HA: hass --config ./ha-config --debug"
echo ""
echo "💡 VS Code tasks are still available via Ctrl+Shift+P → Tasks: Run Task"
