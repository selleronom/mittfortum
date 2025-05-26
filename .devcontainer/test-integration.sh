#!/bin/bash

# Quick integration test script
# This script runs a comprehensive test of the integration

set -e

echo "🧪 Running MittFortum Integration Tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "📦 Installing/updating dependencies..."
pip install -r requirements-dev.txt > /dev/null 2>&1
print_status $? "Dependencies installed"

echo "🧹 Cleaning cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
print_status 0 "Cache cleaned"

echo "📝 Formatting code..."
ruff format . > /dev/null 2>&1
print_status $? "Code formatted"

echo "🔍 Linting code..."
ruff check . --fix > /dev/null 2>&1
print_status $? "Code linted"

echo "🏷️  Type checking..."
pyrefly . > /dev/null 2>&1
print_status $? "Type checking passed"

echo "🧪 Running unit tests..."
pytest tests/unit/ -v --tb=short
print_status $? "Unit tests passed"

echo "🔗 Running integration tests..."
pytest tests/integration/ -v --tb=short
print_status $? "Integration tests passed"

echo "📊 Running tests with coverage..."
pytest --cov=custom_components.mittfortum --cov-report=term-missing --cov-fail-under=80 > /dev/null 2>&1
coverage_result=$?
if [ $coverage_result -eq 0 ]; then
    print_status 0 "Coverage threshold met"
else
    print_warning "Coverage might be below threshold, check manually"
fi

echo "✨ Running pre-commit hooks..."
pre-commit run --all-files > /dev/null 2>&1
print_status $? "Pre-commit hooks passed"

echo ""
echo -e "${GREEN}🎉 All tests passed! Your integration is ready for development.${NC}"
echo ""
echo "🚀 Next steps:"
echo "1. Start Home Assistant: .devcontainer/start-hass.sh"
echo "2. Open http://localhost:8123"
echo "3. Add your MittFortum integration"
echo ""
echo "📋 Development commands:"
echo "- Run specific test: pytest tests/unit/test_coordinator.py -v"
echo "- Watch logs: tail -f /config/home-assistant.log"
echo "- Restart HA: systemctl restart home-assistant@/config.service"
