# Code Review Agent

An autonomous AI-powered code review system for GitHub pull requests using FastAPI, Celery, and LangGraph.

## Features

- **Autonomous Code Review**: AI agent analyzes GitHub PRs for style, bugs, performance, security, and best practices
- **Asynchronous Processing**: Uses Celery for background task processing
- **RESTful API**: FastAPI-based API with automatic documentation
- **Flexible AI Backend**: Supports OpenAI GPT-4 or local Ollama models
- **Structured Results**: Returns detailed analysis with file-by-file breakdown
- **Real-time Status**: Track analysis progress with status endpoints

## Architecture

- **FastAPI**: Web framework for the REST API
- **Celery**: Distributed task queue for async processing
- **Redis**: Message broker and result storage
- **LangGraph**: AI agent framework for autonomous code review
- **GitHub API**: Integration for fetching PR data and diffs

## API Endpoints

### POST `/api/v1/analyze-pr`
Start a new PR analysis task.

**Request:**
```json
{
    "repo_url": "https://github.com/user/repo",
    "pr_number": 123,
    "github_token": "optional_token"
}
```

**Response:**
```json
{
    "task_id": "abc123",
    "status": "pending"
}
```

### GET `/api/v1/status/{task_id}`
Check the status of an analysis task.

**Response:**
```json
{
    "task_id": "abc123",
    "status": "processing",
    "progress": 50.0,
    "message": "Analyzing pull request...",
    "created_at": "2024-01-01T12:00:00"
}
```

### GET `/api/v1/results/{task_id}`
Get the results of a completed analysis.

**Response:**
```json
{
    "task_id": "abc123",
    "status": "completed",
    "results": {
        "files": [
            {
                "name": "main.py",
                "path": "src/main.py",
                "issues": [
                    {
                        "type": "style",
                        "line": 15,
                        "description": "Line too long",
                        "suggestion": "Break line into multiple lines",
                        "severity": "low"
                    }
                ],
                "language": "python"
            }
        ],
        "summary": {
            "total_files": 1,
            "total_issues": 1,
            "critical_issues": 0,
            "files_with_issues": 1,
            "languages_detected": ["python"]
        }
    }
}
```

### POST `/api/v1/retrigger/{task_id}`
Retrigger a stuck or failed task.

**Response:**
```json
{
    "task_id": "new-task-id",
    "status": "pending"
}
```

### DELETE `/api/v1/cancel/{task_id}`
Cancel a running or pending task.

**Response:**
```json
{
    "message": "Task abc123 has been cancelled",
    "task_id": "abc123",
    "status": "cancelled"
}
```

### GET `/api/v1/tasks`
List all tasks with optional filtering.

**Query Parameters:**
- `status`: Filter by status (pending, processing, completed, failed, cancelled)
- `limit`: Maximum number of tasks to return (default: 20)

**Response:**
```json
{
    "tasks": [...],
    "total": 10,
    "status_filter": "processing",
    "status_counts": {
        "pending": 2,
        "processing": 3,
        "completed": 5
    },
    "limit": 20
}
```

### POST `/api/v1/cleanup-stuck-tasks`
Clean up tasks stuck in processing state.

**Request:**
```json
{
    "max_age_hours": 2
}
```

**Response:**
```json
{
    "checked_count": 10,
    "cleaned_count": 2,
    "max_age_hours": 2,
    "stuck_tasks": [...]
}
```

## ✅ Current Status

**Fully Working & Tested** (as of latest update):
- ✅ All dependencies resolved and compatible with Python 3.13
- ✅ FastAPI server running on port 8001
- ✅ Celery worker processing tasks successfully
- ✅ GitHub API integration working (public repos without token)
- ✅ AI analysis pipeline complete (OpenAI + Ollama fallback)
- ✅ Real-time progress tracking and detailed logging
- ✅ Task management and result storage working
- ✅ End-to-end testing completed successfully

**Recent Fixes Applied:**
- Fixed `langchain-community` dependency issue
- Resolved Python 3.13 compatibility conflicts
- Updated all LangChain packages to latest compatible versions
- Verified Ollama fallback functionality
- Confirmed GitHub API integration works without authentication for public repos

## Quick Start

### Prerequisites

- **Python 3.13** (tested and working, recommended)
- **Redis server** (for task queue and result storage)
- **GitHub personal access token** (optional for public repos, required for private repos)
- **AI Model Access** (choose one):
  - OpenAI API key (recommended for speed), OR
  - Ollama installation (for local/private processing - automatically used as fallback)

### Quick Start

**Option 1: One-Command Start (Recommended)**
```bash
git clone <repository-url>
cd PythonProject
./run.sh
```

The `run.sh` script will automatically:
- Create virtual environment if needed
- Install all dependencies (including langchain-community)
- Check Redis connection
- Start Celery worker and FastAPI server on port 8001
- Provide cleanup on Ctrl+C

**✅ Fully Working Dependencies:**
All dependency conflicts have been resolved. The application includes:
- `langchain>=0.1.0` - Core LangChain functionality
- `langchain-openai>=0.0.8` - OpenAI integrations
- `langchain-community>=0.0.20` - Community integrations (Ollama support)
- `langgraph>=0.0.40` - Agent workflow framework
- All other dependencies with Python 3.13 compatibility

**🔧 If you encounter any issues:**
```bash
rm -rf venv && ./run.sh
```

**Option 2: Manual Installation**

1. **Clone the repository:**
```bash
git clone <repository-url>
cd PythonProject
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
# Create .env file with your configuration
cat > .env << EOF
# GitHub Configuration (Required)
GITHUB_TOKEN=your_github_token_here

# AI Model Configuration (Choose one)
# Option 1: OpenAI (Recommended)
OPENAI_API_KEY=your_openai_api_key_here
LLM_TYPE=openai
LLM_MODEL=gpt-4

# Option 2: Ollama (Local)
# LLM_TYPE=ollama
# LLM_MODEL=codellama:7b
# OLLAMA_BASE_URL=http://localhost:11434

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
EOF
```

5. **Start Redis server:**
```bash
# macOS (with Homebrew)
brew services start redis

# Ubuntu/Debian
sudo systemctl start redis-server

# Docker
docker run -d -p 6379:6379 redis:alpine
```

6. **Start the services:**

**Terminal 1 - Celery Worker:**
```bash
source venv/bin/activate
celery -A app.services.celery_app worker --loglevel=info --concurrency=1
```

**Terminal 2 - FastAPI Server:**
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 - Monitor Progress (Optional):**
```bash
# Monitor Celery logs
tail -f celery.log

# Or filter for key events
tail -f celery.log | grep -E "📊|📄|🤖|✅|🎉"
```

### Using Ollama (Local AI)

**Automatic Fallback**: The application automatically uses Ollama when no OpenAI API key is provided.

If you prefer to use local AI models instead of OpenAI:

1. Install Ollama: https://ollama.com/download
2. Pull a code model:
```bash
ollama pull codellama:7b
# or
ollama pull llama2:7b
```
3. Set environment variables in `.env`:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b
# Leave OPENAI_API_KEY empty for automatic fallback
```

**Note**: The application will automatically detect when OpenAI is unavailable and fall back to Ollama with the configured model.

## 🚀 Working Example

Here's a complete working example that you can run right now:

```bash
# 1. Start the application
./run.sh

# 2. In another terminal, test with a real GitHub PR
curl -X POST "http://localhost:8001/api/v1/analyze-pr" \
     -H "Content-Type: application/json" \
     -d '{
       "repo_url": "https://github.com/octocat/Hello-World",
       "pr_number": 1
     }'

# Response: {"task_id":"abc123","status":"pending",...}

# 3. Check the status
curl "http://localhost:8001/api/v1/status/abc123"

# 4. Get results when completed
curl "http://localhost:8001/api/v1/results/abc123"
```

**Expected Results:**
- Task processes successfully in ~45 seconds
- Analyzes 1 file (README.md)
- Returns structured analysis with file details and summary
- Uses Ollama for AI analysis (if no OpenAI key provided)

## Configuration

Key environment variables:

- `GITHUB_TOKEN`: GitHub personal access token
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)
- `OLLAMA_BASE_URL`: Ollama server URL (if using Ollama)
- `REDIS_URL`: Redis connection URL
- `DATABASE_URL`: Database connection URL

## Job Management

The system includes comprehensive job management capabilities for handling stuck or failed tasks:

### Command Line Tool

Use the `job_manager.py` script for easy job management:

```bash
# List all tasks
python3 job_manager.py list

# List only processing tasks
python3 job_manager.py list --status processing

# Show task details
python3 job_manager.py details TASK_ID

# Retrigger a stuck task
python3 job_manager.py retrigger TASK_ID

# Cancel a running task
python3 job_manager.py cancel TASK_ID

# Clean up stuck tasks (older than 2 hours)
python3 job_manager.py cleanup --max-age 2
```

### API Examples

```bash
# Start analysis
curl -X POST "http://localhost:8001/api/v1/analyze-pr" \
     -H "Content-Type: application/json" \
     -d '{
       "repo_url": "https://github.com/octocat/Hello-World",
       "pr_number": 1
     }'

# Check status
curl "http://localhost:8001/api/v1/status/abc123"

# Get results
curl "http://localhost:8001/api/v1/results/abc123"

# List all tasks
curl "http://localhost:8001/api/v1/tasks"

# Retrigger stuck task
curl -X POST "http://localhost:8001/api/v1/retrigger/abc123"

# Cancel running task
curl -X DELETE "http://localhost:8001/api/v1/cancel/abc123"

# Clean up stuck tasks
curl -X POST "http://localhost:8001/api/v1/cleanup-stuck-tasks" \
     -H "Content-Type: application/json" \
     -d '{"max_age_hours": 2}'
```

## 📊 Enhanced Analysis Monitoring

The system provides comprehensive real-time monitoring of analysis progress with detailed logging.

### 🔍 Real-Time Progress Tracking

**Enhanced Logging Features:**
- 🚀 **Task Initialization**: Task ID, PR details, repository info
- 📥 **Data Fetching**: GitHub API calls, file fetching progress
- 📊 **Overall Progress**: Files completed/remaining, percentage progress
- 📄 **File Analysis**: Current file, index (1/5), language, changes
- 🤖 **LLM Processing**: File being sent to LLM, estimated time
- ✅ **LLM Completion**: Response received, processing time
- 🎉 **File Completion**: Issues found, files remaining
- 🏁 **Analysis Complete**: Total files, total issues, execution time

### 📋 Example Progress Output

```
[09:58:11] 🚀 Starting PR analysis task (task_id=abc123, repo=octocat/Hello-World)
[09:58:12] 📥 Starting PR data fetch (repository=octocat/Hello-World)
[09:58:14] 📊 Analysis Progress: 0/3 files (0.0%), current_file=README.md
[09:58:14] 📄 Starting file analysis: README.md (1/3), language=markdown
[09:58:15] 🤖 Sending file to LLM: README.md, estimated_time=10-30 seconds
[09:58:28] ✅ LLM analysis completed: README.md (1/3)
[09:58:28] 🎉 File analysis completed: README.md, issues_found=2, files_remaining=2
[09:58:29] 📊 Analysis Progress: 1/3 files (33.3%), current_file=app.py
[09:58:45] 🏁 All files analyzed: total_files=3, total_issues_found=7
```

### 🔧 Monitoring Commands

**Basic Monitoring:**
```bash
# Monitor all progress indicators
tail -f celery.log | grep -E "📊|📄|🤖|✅|🎉|🏁"

# Track specific phases
tail -f celery.log | grep "📊 Analysis Progress"  # Overall progress
tail -f celery.log | grep "🤖 Sending file to LLM"  # LLM processing
tail -f celery.log | grep "🎉 File analysis completed"  # Completions
```

**Performance Analysis:**
```bash
# Track timing and performance
tail -f celery.log | grep -E "execution_time|response_length|estimated_time"

# Monitor file processing order
tail -f celery.log | grep "filename=" | cut -d'=' -f2
```

## 🛠️ Monitoring and Debugging

### Redis Monitor
```bash
# View all tasks and their status
python3 redis_monitor.py

# View detailed task information
python3 redis_monitor.py TASK_ID
```

### Log Monitoring
```bash
# Monitor live logs
python3 log_monitor.py

# Show recent activity
python3 log_monitor.py --recent
```

### Testing
```bash
# Run unit tests
python -m pytest tests/ -v
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## License

MIT License - see LICENSE file for details.