#!/bin/bash

# Start Home Assistant development server
# This script makes it easy to start HA with the correct configuration

set -e

CONFIG_DIR="/config"
WORKSPACE_DIR="/workspaces/mittfortum"

echo "🏠 Starting Home Assistant for MittFortum development..."

# Ensure secrets file exists
if [ ! -f "${CONFIG_DIR}/secrets.yaml" ]; then
    echo "📝 Creating secrets.yaml from template..."
    cp "${CONFIG_DIR}/secrets.yaml.template" "${CONFIG_DIR}/secrets.yaml"
    echo "⚠️  Please edit /config/secrets.yaml with your actual credentials"
fi

# Ensure custom component is linked
echo "🔗 Ensuring MittFortum integration is linked..."
mkdir -p "${CONFIG_DIR}/custom_components"
rm -rf "${CONFIG_DIR}/custom_components/mittfortum"
ln -sf "${WORKSPACE_DIR}/custom_components/mittfortum" "${CONFIG_DIR}/custom_components/mittfortum"

# Start Home Assistant
echo "🚀 Starting Home Assistant..."
echo "📍 Config directory: ${CONFIG_DIR}"
echo "🌐 Web interface will be available at: http://localhost:8123"
echo ""

cd "${WORKSPACE_DIR}"
hass --config "${CONFIG_DIR}" --debug
