#!/bin/bash
# Quick setup script for cleanup_waiting_room command

# Create logs directory if it doesn't exist
mkdir -p logs

# Test the cleanup command
echo "Testing cleanup_waiting_room command..."
python manage.py cleanup_waiting_room --dry-run

if [ $? -eq 0 ]; then
    echo "✓ Command test successful!"
    echo ""
    echo "To run the cleanup periodically, add this to your crontab:"
    echo "* * * * * cd $(pwd) && python manage.py cleanup_waiting_room --inactivity-timeout 45 >> logs/cleanup.log 2>&1"
    echo ""
    echo "Or run it continuously in background:"
    echo "nohup python manage.py cleanup_waiting_room --inactivity-timeout 45 &"
else
    echo "✗ Command test failed. Check Django settings."
    exit 1
fi
