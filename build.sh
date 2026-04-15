#!/usr/bin/env bash
set -o errexit

# Create Java directory in app (writable location)
mkdir -p $HOME/.jdk

# Download and install OpenJDK 11 if not already present
if [ ! -f $HOME/.jdk/jdk-11.0.15/bin/javac ]; then
    echo "Downloading OpenJDK 11..."
    cd $HOME/.jdk
    wget -q https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.15%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz -O java.tar.gz
    tar -xzf java.tar.gz
    rm java.tar.gz
    echo "Java installed successfully"
fi

# Set Java environment variables
export JAVA_HOME=$HOME/.jdk/jdk-11.0.15
export PATH=$JAVA_HOME/bin:$PATH

# Verify Java installation
echo "Java version:"
java -version 2>&1 || echo "Java not found"
echo "Javac version:"
javac -version 2>&1 || echo "Javac not found"

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput
