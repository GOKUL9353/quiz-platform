#!/usr/bin/env bash
set -o errexit

APP_DIR="$(pwd)"
JAVA_DIR="$APP_DIR/.java"
mkdir -p "$JAVA_DIR"

if [ ! -f $JAVA_DIR/bin/javac ]; then
    cd $JAVA_DIR
    wget -q https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.15%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.15_10.tar.gz -O java.tar.gz
    tar --strip-components=1 -xzf java.tar.gz
    rm java.tar.gz
fi

export JAVA_HOME=$JAVA_DIR
export PATH=$JAVA_DIR/bin:$PATH

cd "$APP_DIR"
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
