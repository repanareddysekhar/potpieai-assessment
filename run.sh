#!/bin/bash

# Code Review Agent - Quick Start Script
echo "🤖 Code Review Agent - Quick Start"
echo "=================================="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ] || [ ! -d "venv/lib/python*/site-packages/fastapi" ]; then
    echo "📥 Installing dependencies..."
    pip install --upgrade pip
    if ! pip install -r requirements.txt; then
        echo "❌ Dependency installation failed. Trying with clean install..."
        pip install --force-reinstall -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies. Try:"
            echo "   rm -rf venv && ./run.sh"
            exit 1
        fi
    fi
elif [ "$1" = "--reinstall" ]; then
    echo "🔄 Reinstalling dependencies..."
    pip install --upgrade pip
    pip install --force-reinstall -r requirements.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration:"
    echo "   - GITHUB_TOKEN=your_token_here"
    echo "   - OPENAI_API_KEY=your_key_here (or configure Ollama)"
    echo "   - REDIS_URL=redis://localhost:6379/0"
    echo
    echo "❌ Please configure .env file and run again."
    exit 1
fi

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first:"
    echo "   brew services start redis  # macOS"
    echo "   sudo systemctl start redis  # Linux"
    echo "   docker run -d -p 6379:6379 redis  # Docker"
    exit 1
fi
echo "✅ Redis is running"

# Kill any existing Celery workers
echo "🧹 Cleaning up existing workers..."
pkill -f "celery.*worker" 2>/dev/null || true
sleep 1

# Start services
echo
echo "🚀 Starting Code Review Agent..."
echo "================================"
echo

# Start Celery worker in background
echo "📋 Starting Celery worker..."
celery -A app.services.celery_app worker --loglevel=info --concurrency=1 > celery.log 2>&1 &
CELERY_PID=$!
echo "✅ Celery worker started (PID: $CELERY_PID)"

# Wait a moment for Celery to start
sleep 2

# Start FastAPI server
echo "🌐 Starting FastAPI server..."
echo "📡 API will be available at: http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop all services"
echo

# Function to cleanup on exit
cleanup() {
    echo
    echo "🛑 Shutting down services..."
    kill $CELERY_PID 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start FastAPI server (this will block)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
