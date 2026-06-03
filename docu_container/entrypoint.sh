#!/bin/sh
set -e

# Define paths
REPO_DIR="/workspace/wiki-docs"
BUILD_OUTPUT_DIR="/data/public"
SYNC_INTERVAL=${SYNC_INTERVAL:-300} # Default to 5 minutes if not set

echo "🚀 Starting Quartz Auto-Builder Sidecar..."

# Create a temporary loading page so NGINX doesn't return 403 while building
echo "<html><body><h1>Building Documentation... Please wait a few minutes.</h1></body></html>" > "$BUILD_OUTPUT_DIR/index.html"
chmod -R 755 "$BUILD_OUTPUT_DIR"

# 1. Initial Clone if the directory doesn't exist yet
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "📁 Cloning repository from $REPO_URL..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    echo "🔄 Existing repository found. Ensuring clean state..."
    cd "$REPO_DIR" && git fetch origin && git reset --hard origin/main
fi

cd "$REPO_DIR"

# 2. Install Quartz dependencies inside the cloned repo
echo "📦 Installing Quartz dependencies..."
npm i

# 3. Initial Build
echo "🏗️ Running initial Quartz build..."
npx quartz build -d "$BUILD_OUTPUT_DIR"
chmod -R 755 "$BUILD_OUTPUT_DIR"

# 4. The Infinite Sync Loop
while true; do
    echo "🔎 Checking for documentation updates..."
    git fetch origin

    # Check if local main is behind remote main
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "📥 New changes detected! Pulling latest documentation..."
        git pull origin main
        
        echo "🔨 Rebuilding Quartz static files..."
        npx quartz build -d "$BUILD_OUTPUT_DIR"
        chmod -R 755 "$BUILD_OUTPUT_DIR"
        echo "✅ Build complete. Updated files are live."
    else
        echo "💤 No changes detected. Sleeping for $SYNC_INTERVAL seconds."
    fi

    sleep "$SYNC_INTERVAL"
done