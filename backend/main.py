from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from schemas import AgentRequest, UserInputRequest, BatchOrderRequest
from agent_controller import stream_agent_events, provide_input, stream_batch_order_events
from dotenv import load_dotenv

load_dotenv()

import asyncio
import sys

# Force ProactorEventLoop on Windows to support subprocesses (required for Playwright/browser-use)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/agent/stream")
async def stream_agent(request: AgentRequest):
    return StreamingResponse(
        stream_agent_events(request),
        media_type="text/event-stream"
    )

@app.post("/agent/input")
async def receive_input(request: UserInputRequest):
    return await provide_input(request.session_id, request.input_data)

@app.post("/agent/batch-order")
async def batch_order(request: BatchOrderRequest):
    """
    Process multiple orders from CSV data.
    Keeps browser alive and processes items sequentially.
    """
    return StreamingResponse(
        stream_batch_order_events(request),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
