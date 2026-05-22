#!/bin/bash

# Setup script for Ground Station frontend testing infrastructure
# Run this script once to install all testing dependencies

set -e  # Exit on error

echo "🚀 Setting up Ground Station Frontend Testing..."
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the frontend directory."
    exit 1
fi

echo "📦 Installing npm dependencies..."
npm install

echo ""
echo "🎭 Installing Playwright browsers..."
npx playwright install --with-deps

echo ""
echo "✅ Testing infrastructure setup complete!"
echo ""
echo "📚 Quick Start:"
echo "  • Run unit tests:         npm test"
echo "  • Run tests with UI:      npm run test:ui"
echo "  • Run E2E tests:          npm run test:e2e"
echo "  • Run E2E with UI:        npm run test:e2e:ui"
echo "  • Generate coverage:      npm run test:coverage"
echo ""
echo "📖 Documentation:"
echo "  • Quick start guide:      cat TEST-QUICKSTART.md"
echo "  • Full testing guide:     cat TESTING.md"
echo ""
echo "🎉 Happy testing!"
