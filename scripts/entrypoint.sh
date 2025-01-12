#!/bin/bash
set -e

# Configuration
REDIS_LOCK_KEY="django_migrations_lock"
REDIS_COMPLETE_KEY="django_migrations_complete"
LOCK_TIMEOUT=300  # 5 minutes
MAX_WAIT=600     # 10 minutes
RETRY_INTERVAL=5  # 5 seconds
REDIS_HOST="redis"  # Extract host to a variable for easier configuration

# Function definitions moved outside the main logic for better readability
wait_for_redis() {
    until redis-cli -h $REDIS_HOST ping; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
}

check_migrations_complete() {
    redis-cli -h $REDIS_HOST GET $REDIS_COMPLETE_KEY
}

acquire_lock() {
    redis-cli -h $REDIS_HOST SET $REDIS_LOCK_KEY $HOSTNAME NX EX $LOCK_TIMEOUT
}

run_migrations() {
    # Clear any stale completion flag at startup
    redis-cli -h $REDIS_HOST DEL $REDIS_COMPLETE_KEY
    
    elapsed=0
    while [ $elapsed -lt $MAX_WAIT ]; do
        if [ "$(check_migrations_complete)" = "true" ]; then
            echo "Migrations already completed, proceeding with main process"
            return 0
        fi

        if [ "$(acquire_lock)" = "OK" ]; then
            echo "Acquired lock, running migrations..."
            python manage.py migrate --no-input
            
            # Mark migrations as complete and release lock
            redis-cli -h $REDIS_HOST SET $REDIS_COMPLETE_KEY "true" EX 86400  # 24 hour expiry
            redis-cli -h $REDIS_HOST DEL $REDIS_LOCK_KEY
            echo "Migrations completed successfully"
            return 0
        fi

        echo "Waiting for migrations..."
        sleep $RETRY_INTERVAL
        elapsed=$((elapsed + RETRY_INTERVAL))
    done

    echo "Timeout waiting for migrations"
    return 1
}

# Main logic
if [ "$ENABLE_MIGRATION_MANAGEMENT" = "true" ]; then
    wait_for_redis
    run_migrations || exit 1
else
    echo "Migration management is disabled, skipping migrations."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the main process
exec "$@" 