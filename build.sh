#!/usr/bin/env bash
# build.sh - Setup script for Render deployment

echo "Starting build process..."

# Create necessary directories
mkdir -p data
mkdir -p logs
mkdir -p temp
mkdir -p temp_uploads

# Set permissions
chmod -R 755 data logs temp temp_uploads

# Create initial database if it doesn't exist
touch data/posts.db

echo "Build process completed!"