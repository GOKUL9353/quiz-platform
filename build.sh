#!/usr/bin/env bash
set -o errexit

# Create Java directory
JAVA_DIR="/tmp/java"
mkdir -p $JAVA_DIR

# Download and install OpenJDK 11
if [ ! -f $JAVA_DIR/jdk-11/bin/javac ]; then
    echo "Downloading OpenJDK 11..."
    cd $JAVA_DIR
    wget -q https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.15%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz -O java.tar.gz
    tar --strip-components=1 -xzf java.tar.gz
    rm java.tar.gz
    echo "Java installed successfully"
fi

# Verify installation
ls -la $JAVA_DIR/bin/java 2>/dev/null && echo "✓ Java found" || echo "✗ Java NOT found"
ls -la $JAVA_DIR/bin/javac 2>/dev/null && echo "✓ Javac found" || echo "✗ Javac NOT found"

# Set environment
export JAVA_HOME=$JAVA_DIR
export PATH=$JAVA_DIR/bin:$PATH

# Test
echo "Java version:"
$JAVA_DIR/bin/java -version
echo "Javac version:"
$JAVA_DIR/bin/javac -version

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput
