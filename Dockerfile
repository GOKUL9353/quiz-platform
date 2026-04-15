# Use a base image with both Python and Java pre-installed
FROM python:3.11-slim

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 \
    PATH=/usr/lib/jvm/java-11-openjdk-amd64/bin:$PATH

# Set working directory
WORKDIR /app

# Install system dependencies including Java and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jdk-headless \
    gcc \
    g++ \
    make \
    git \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Verify installations
RUN echo "Java version:" && java -version && echo "Javac version:" && javac -version && echo "GCC version:" && gcc --version

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p staticfiles /tmp/quiz_runs

# Run migrations and collect static files
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--timeout", "120", "--workers", "3"]

