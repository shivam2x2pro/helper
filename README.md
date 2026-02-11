# Browser Agent - Amazon & Flipkart Order Automation

An AI-powered browser automation agent that can search and place orders on Amazon India and Flipkart with human-in-the-loop confirmations.

## Features

- **Search Products**: Search for products on Amazon/Flipkart and get top results
- **Place Orders**: Automated checkout with user confirmations for address, payment, and final order
- **Batch Orders**: Process multiple orders from CSV file
- **Human-in-the-Loop**: User confirms address, payment method, and order placement
- **Persistent Sessions**: Browser profile saves login sessions (no re-login needed)
- **Cost Tracking**: Token usage and cost tracking for each order

## Tech Stack

- **Backend**: Python, FastAPI, browser-use library
- **Frontend**: Next.js, React, TailwindCSS
- **LLM**: GPT-4o (OpenAI)
- **Browser**: Playwright (Chromium)

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API Key

---

## Option 1: Run Without Docker (Development)

### 1. Clone and Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

Create `.env` file in `backend/` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
HEADLESS=false
```

### 3. Run Backend

```bash
cd backend
source venv/bin/activate  # if not already activated
python main.py
```

Backend will start at: `http://localhost:8000`

### 4. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will start at: `http://localhost:3000`

### 5. Access the Application

Open `http://localhost:3000` in your browser.

---

## Option 2: Run With Docker

### 1. Configure Environment

Create `.env` file in `backend/` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
HEADLESS=true
```

### 2. Build and Run with Docker Compose

```bash
# From project root directory
docker-compose up --build
```

This will:
- Build the backend Docker image
- Start the backend service on port 8000
- Mount browser profile for persistent sessions

### 3. Run Frontend Separately

```bash
cd frontend
npm install
npm run dev
```

### 4. Access the Application

Open `http://localhost:3000` in your browser.

---

## Project Structure

```
browser_agent_fullstack/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── agent_controller.py  # Browser-use agent logic
│   ├── prompts.py           # LLM prompts for Amazon/Flipkart
│   ├── schemas.py           # Pydantic models
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Docker configuration
│   ├── .env                 # Environment variables
│   └── browser_profile/     # Persistent browser data (cookies, sessions)
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   └── components/      # React components
│   ├── package.json
│   └── ...
├── docker-compose.yml
└── readme.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/stream` | Start agent task (SSE stream) |
| POST | `/agent/input` | Provide user input to agent |
| POST | `/agent/batch-order` | Start batch order processing |

### Example: Start Order

```bash
curl -X POST http://localhost:8000/agent/stream \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "amazon",
    "action": "order",
    "product_url": "https://www.amazon.in/dp/XXXXXX",
    "quantity": 1
  }'
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `HEADLESS` | Run browser in headless mode | `false` |

### Agent Settings

In `agent_controller.py`:

| Setting | Description | Default |
|---------|-------------|---------|
| `MAX_STEPS` | Maximum steps per order | 35 |
| `temperature` | LLM temperature (0 = deterministic) | 0.0 |
| `model` | OpenAI model | gpt-4o |

---

## Cost Estimation

| Model | Cost per Order (approx) |
|-------|------------------------|
| GPT-4o | $0.30 - $0.50 |
| GPT-4o-mini | $0.02 - $0.03 |

---

## Troubleshooting

### Browser Profile Issues

If login sessions are not persisting:
```bash
# Clear browser profile and re-login
rm -rf backend/browser_profile/*
```

### Docker Memory Issues

If browser crashes in Docker, increase shared memory:
```yaml
# docker-compose.yml
services:
  backend:
    shm_size: '2gb'  # Increase if needed
```

### Agent Stuck in Loop

If agent keeps repeating actions:
- The prompt has been updated to use `wait` action instead of refresh
- Agent will stop after 3 repeated failures

---

## License

MIT
