#!/usr/bin/env bash
set -o errexit

# Install Java (JDK) for code execution
apt-get update
apt-get install -y default-jdk gcc

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput
