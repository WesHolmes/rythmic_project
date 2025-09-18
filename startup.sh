#!/bin/bash

# Azure App Service Linux startup script
echo "Starting Azure App Service on Linux..."

# Set environment variables
export PYTHONPATH="/home/site/wwwroot"
export FLASK_ENV="production"

# Install any missing dependencies
pip install -r requirements.txt

# Run database migrations if needed
python -c "
try:
    from migrations.azure_production_migration import run_azure_migration
    run_azure_migration()
    print('Migration completed successfully')
except Exception as e:
    print(f'Migration failed or not needed: {e}')
"

# Start the application with gunicorn optimized for WebSockets
exec gunicorn --bind 0.0.0.0:8000 \
    --workers 1 \
    --worker-class eventlet \
    --worker-connections 1000 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    "app:app"