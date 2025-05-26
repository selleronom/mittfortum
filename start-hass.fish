#!/usr/bin/env fish

# Start Home Assistant for native development

# Check if we're in the right directory
if not test -f "custom_components/mittfortum/manifest.json"
    echo "❌ Error: Please run this script from the mittfortum project root directory"
    exit 1
end

# Check if virtual environment exists
if not test -d .venv
    echo "❌ Virtual environment not found. Run ./setup-dev.fish first"
    exit 1
end

# Activate virtual environment
source .venv/bin/activate.fish

# Check if config exists
if not test -f ./ha-config/configuration.yaml
    echo "❌ Home Assistant configuration not found. Run ./setup-dev.fish first"
    exit 1
end

# Check if secrets exist
if not test -f ./ha-config/secrets.yaml
    echo "⚠️  Warning: No secrets.yaml found. Create it from the template:"
    echo "   cp .devcontainer/config/secrets.yaml.template ./ha-config/secrets.yaml"
    echo ""
end

# Ensure integration is linked
echo "🔗 Ensuring MittFortum integration is linked..."
rm -rf ./ha-config/custom_components/mittfortum
ln -sf (pwd)/custom_components/mittfortum ./ha-config/custom_components/mittfortum

# Start Home Assistant
echo "🚀 Starting Home Assistant..."
echo "📍 Config directory: ./ha-config"
echo "🌐 Web interface: http://localhost:8123"
echo "🛑 Stop with Ctrl+C"
echo ""

hass --config ./ha-config --debug
