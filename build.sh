#!/usr/bin/env bash
set -o errexit

# Create Java directory
mkdir -p /opt/java

# Download and install OpenJDK 11 (pre-built binary for Linux)
if [ ! -f /opt/java/jdk-11.0.15/bin/javac ]; then
    echo "Downloading OpenJDK 11..."
    cd /opt/java
    wget -q https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.15%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz
    tar -xzf OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz
    rm OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz
fi

# Set Java environment variables
export JAVA_HOME=/opt/java/jdk-11.0.15
export PATH=$JAVA_HOME/bin:$PATH

# Verify Java installation
echo "Java version:"
java -version
echo "Javac version:"
javac -version

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput
