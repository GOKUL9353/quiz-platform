#!/usr/bin/env bash
set -o errexit

echo "========== BUILD SCRIPT STARTED =========="
echo "Current directory: $(pwd)"
echo "Script location: $0"
echo "Script directory: $(dirname "$0")"

# Create Java directory
APP_DIR="$(pwd)"
JAVA_DIR="$APP_DIR/.java"
mkdir -p "$JAVA_DIR"

# Download and install OpenJDK 11
if [ ! -f $JAVA_DIR/bin/javac ]; then
    echo ""
    echo ">>> Downloading OpenJDK 11..."
    cd $JAVA_DIR
    wget -q https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.15%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz -O java.tar.gz
    tar --strip-components=1 -xzf java.tar.gz
    rm java.tar.gz
    echo ">>> Java installed successfully"
else
    echo ">>> Java already installed"
fi

# Verify installation
echo ""
echo ">>> Verifying Java installation..."
ls -la $JAVA_DIR/bin/java && echo "✓ Java found" || echo "✗ Java NOT found"
ls -la $JAVA_DIR/bin/javac && echo "✓ Javac found" || echo "✗ Javac NOT found"

# Set environment
export JAVA_HOME=$JAVA_DIR
export PATH=$JAVA_DIR/bin:$PATH

# Test Java
echo ""
echo ">>> Java versions:"
$JAVA_DIR/bin/java -version
$JAVA_DIR/bin/javac -version

# Make sure we're in app root where requirements.txt is
echo ""
echo ">>> Checking for requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "✓ requirements.txt found in $(pwd)"
else
    echo "✗ requirements.txt NOT found in $(pwd)"
    echo "Files in current directory:"
    ls -la
    exit 1
fi

# Install Python dependencies
echo ""
echo ">>> Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and collect static files
echo ""
echo ">>> Running Django migrations..."
python manage.py migrate

echo ""
echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "========== BUILD SCRIPT COMPLETED SUCCESSFULLY =========="
