#!/bin/bash

set -e

echo "🚀 Setting up MittFortum Home Assistant development environment..."

# Ensure we're in the workspace directory
if [ ! -d "/workspaces/mittfortum" ]; then
    echo "❌ Error: /workspaces/mittfortum directory not found"
    exit 1
fi

cd /workspaces/mittfortum

# Verify we have the right files
if [ ! -f "requirements-dev.txt" ]; then
    echo "❌ Error: requirements-dev.txt not found in workspace"
    exit 1
fi

# Update system packages and install essential tools
apt-get update
apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    autoconf \
    build-essential \
    libopenjp2-7 \
    libturbojpeg0-dev \
    tzdata \
    ffmpeg \
    liblapack3 \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    freetype* \
    pkg-config

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install development requirements
pip install -r /workspaces/mittfortum/requirements-dev.txt

# Install additional Home Assistant dependencies
pip install \
    colorlog \
    PyNaCl \
    bcrypt \
    cryptography \
    aiofiles \
    Pillow \
    lxml \
    voluptuous-serialize \
    PyJWT[crypto] \
    packaging

echo "🏠 Setting up Home Assistant configuration..."

# Create Home Assistant config directory if it doesn't exist
mkdir -p /config

# Copy configuration if it doesn't exist
if [ ! -f /config/configuration.yaml ]; then
    cp /workspaces/mittfortum/.devcontainer/config/configuration.yaml /config/
fi

# Create custom_components directory in config and link to development version
mkdir -p /config/custom_components
rm -rf /config/custom_components/mittfortum
ln -sf /workspaces/mittfortum/custom_components/mittfortum /config/custom_components/mittfortum

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Set up pytest for testing
echo "🧪 Setting up testing environment..."
mkdir -p /tmp/pytest-cache
chmod 777 /tmp/pytest-cache

# Change to workspace directory for remaining commands
cd /workspaces/mittfortum

echo "✅ Development environment setup complete!"
echo ""

# Show welcome message
/workspaces/mittfortum/.devcontainer/welcome.sh
