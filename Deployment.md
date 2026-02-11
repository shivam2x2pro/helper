# Deployment Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API Key
- Git
- Docker & Docker Compose (for containerized deployment)

---

## 1. Local Development Deployment

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Backend Environment Variables

Create `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
HEADLESS=false
```

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | Yes |
| `HEADLESS` | Run browser without UI (`true`/`false`) | No (default: `false`) |

### Start Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend runs at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

### Verify

Open `http://localhost:5173` in your browser. The frontend should connect to the backend at `http://localhost:8000`.

---

## 2. Docker Deployment (Backend Only)

Docker runs the backend in a container. The frontend still runs separately.

### Configure Environment

Create `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

> Note: `HEADLESS` is automatically set to `true` in docker-compose.yml.

### Build and Run

```bash
# From project root
docker-compose up --build
```

This will:
- Build the backend image (Python 3.11 + Chromium)
- Start backend on port `8000`
- Allocate 2GB shared memory for the browser
- Mount `browser_profile/` for persistent login sessions
- Auto-restart on failure

### Run Frontend

```bash
cd frontend
npm install
npm run dev
```

### Stop

```bash
docker-compose down
```

---

## 3. Production Deployment (VPS / Cloud Server)

### Server Requirements

- Ubuntu 22.04+ (or similar Linux)
- 2+ GB RAM (Chromium needs memory)
- 2+ CPU cores

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd browser_agent_fullstack
```

### Step 2: Deploy Backend with Docker

```bash
# Create environment file
cp backend/.env.example backend/.env   # or create manually
nano backend/.env
# Set: OPENAI_API_KEY=your_key_here

# Build and start
docker-compose up --build -d
```

### Step 3: Build Frontend for Production

```bash
cd frontend
npm install
npm run build
```

This creates a `dist/` folder with static files.

### Step 4: Serve Frontend

Option A - Using a static file server:

```bash
npm install -g serve
serve -s dist -l 3000
```

Option B - Using Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /agent/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

> The proxy config above disables buffering for SSE (Server-Sent Events) to work properly.

---

## 4. Environment Configuration Reference

### Backend (`backend/.env`)

| Variable | Description | Dev Default | Prod Default |
|----------|-------------|-------------|--------------|
| `OPENAI_API_KEY` | OpenAI API key | - | - |
| `HEADLESS` | Headless browser mode | `false` | `true` |

### Agent Settings (`backend/agent_controller.py`)

| Setting | Description | Default |
|---------|-------------|---------|
| `MAX_STEPS` | Max steps per agent task | 25 |
| `temperature` | LLM randomness (0 = deterministic) | 0.0 (order) / 0.2 (search) |
| `model` | OpenAI model | gpt-4o |

### Ports

| Service | Port |
|---------|------|
| Backend (FastAPI) | 8000 |
| Frontend (Vite dev) | 5173 |

---

## 5. Browser Profile (Persistent Sessions)

The `backend/browser_profile/` directory stores browser cookies and login sessions. This means you don't need to re-login to Amazon/Flipkart after the first time.

- In Docker, this directory is mounted as a volume
- To reset sessions: `rm -rf backend/browser_profile/*`
- Do NOT commit this directory to git

---

## 6. Troubleshooting

### Browser crashes in Docker

Increase shared memory in `docker-compose.yml`:

```yaml
shm_size: '4gb'   # increase from 2gb
```

### Playwright not finding browser

```bash
# Inside the backend environment
playwright install chromium
playwright install-deps chromium
```

### CORS errors in browser

The backend allows all origins by default (`allow_origins=["*"]`). For production, restrict this in `backend/main.py` to your frontend domain.

### SSE stream not working behind reverse proxy

Ensure your proxy disables buffering:

```nginx
proxy_buffering off;
proxy_cache off;
chunked_transfer_encoding off;
```

### Port already in use

```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>
```
