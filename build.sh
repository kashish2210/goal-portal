#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  build.sh  —  Render build script for GoalTrack
#  Runs once per deploy BEFORE the web service starts.
# ─────────────────────────────────────────────────────────────
set -o errexit   # Exit immediately on any error

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Seeding demo data (idempotent — safe to run repeatedly)..."
python manage.py seed_demo_users

echo "==> Build complete!"
