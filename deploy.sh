#!/bin/bash

# Configuration
PROJECT_DIR="/var/www/kitaly/kitaly"
VENV_PATH="$PROJECT_DIR/venv"
SERVICE_NAME="kitaly"

echo "🚀 Starting deployment..."

# 1. Pull latest changes
echo "📥 Pulling latest code from GitHub..."
cd $PROJECT_DIR
# We assume the user is on the main branch
git pull origin main

# 2. Activate virtual environment and update dependencies
echo "📦 Updating dependencies..."
source $VENV_PATH/bin/activate
pip install -r requirements.txt

# 3. Run database migrations
echo "🗄️ Running database migrations..."
flask db upgrade

# 4. Compile translations (if needed)
echo "🌐 Compiling translations..."
pybabel compile -d translations

# 5. Restart the application service
echo "🔄 Restarting Gunicorn service..."
sudo systemctl restart $SERVICE_NAME

# 6. Restart Nginx (optional, usually not needed for code changes, but good for safety)
# sudo systemctl restart nginx

echo "✅ Deployment complete! Website is live."
