#!/usr/bin/env python
"""
Simple HTTPS development server for Django with self-signed SSL certificate.
"""
import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

if __name__ == '__main__':
    # Run the development server with SSL support
    # Uses pyopenssl for SSL
    sys.argv = [
        'manage.py',
        'runserver',
        '0.0.0.0:8443',  # Run on 8443 (HTTPS port)
        '--nostatic',
    ]
    execute_from_command_line(sys.argv)
