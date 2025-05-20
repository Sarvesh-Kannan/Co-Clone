"""
Co-Clone Proxy Service

This service acts as a proxy between the IDE and the LLM model,
providing HTTP/2 support, connection pooling, and request cancellation.
Inspired by GitHub Copilot's architecture.
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional, Set

import httpx
import ollama
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables
load_dotenv(verbose=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("copilot-proxy")

# Constants
MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_CONNECTION_LIFETIME = 3600  # 1 hour in seconds
MAX_ACTIVE_REQUESTS = 100

# Global state
active_tokens: Set[str] = set()
active_requests: Dict[str, asyncio.Task] = {}
connection_pool: httpx.AsyncClient = None
connection_established_time: float = 0

# Statistics
request_count = 0
cancelled_request_count = 0
total_latency = 0
request_start_times: Dict[str, float] = {}

# Models
class CompletionRequest(BaseModel):
    prompt: str
    stream: bool = True
    max_tokens: int = 1024
    temperature: float = 0.7

class TokenResponse(BaseModel):
    token: str
    expires_at: int

class StatusResponse(BaseModel):
    status: str
    uptime: float
    requests: int
    cancellations: int
    avg_latency: float = 0
    active_connections: int = 0
    model: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and clean up resources for the application."""
    global connection_pool, connection_established_time
    
    # Create HTTP client with HTTP/2 support and connection pooling
    connection_pool = httpx.AsyncClient(
        base_url=OLLAMA_HOST,
        http2=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        timeout=httpx.Timeout(60.0)
    )
    connection_established_time = time.time()
    logger.info(f"Initialized connection pool with HTTP/2 support to {OLLAMA_HOST}")
    
    yield
    
    # Clean up resources
    if connection_pool:
        await connection_pool.aclose()
        logger.info("Closed connection pool")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for load balancers."""
    global connection_pool, connection_established_time
    
    # Check if connection pool is too old and needs to be refreshed
    if time.time() - connection_established_time > MAX_CONNECTION_LIFETIME:
        return {"status": "refresh", "reason": "connection pool too old"}
    
    # Check if too many active requests
    if len(active_requests) > MAX_ACTIVE_REQUESTS:
        return {"status": "overloaded", "reason": "too many active requests"}
    
    return {"status": "healthy", "model": MODEL}

@app.get("/token")
async def get_token() -> TokenResponse:
    """Generate a short-lived token for code completion requests."""
    token = str(uuid.uuid4())
    expires_at = int(time.time() + 600)  # 10 minutes expiry
    
    active_tokens.add(token)
    
    # Schedule token cleanup after expiry
    async def remove_token():
        await asyncio.sleep(600)
        active_tokens.discard(token)
    
    asyncio.create_task(remove_token())
    
    return TokenResponse(token=token, expires_at=expires_at)

@app.get("/status")
async def status() -> StatusResponse:
    """Return the status of the proxy service."""
    global request_count, cancelled_request_count, total_latency, connection_established_time
    
    uptime = time.time() - connection_established_time
    avg_latency = total_latency / max(request_count, 1)
    
    return StatusResponse(
        status="running",
        uptime=uptime,
        requests=request_count,
        cancellations=cancelled_request_count,
        avg_latency=avg_latency,
        active_connections=len(active_requests),
        model=MODEL
    )

async def stream_completion(request_id: str, completion_request: CompletionRequest) -> AsyncGenerator[bytes, None]:
    """Stream the completion response from the LLM model."""
    client = ollama.AsyncClient(host=OLLAMA_HOST)
    
    try:
        async for chunk in client.generate(
            model=MODEL,
            prompt=completion_request.prompt,
            stream=True,
            options={
                "temperature": completion_request.temperature,
                "num_predict": completion_request.max_tokens
            }
        ):
            # Check if request has been cancelled
            if request_id not in active_requests:
                logger.info(f"Request {request_id} was cancelled, stopping stream")
                break
                
            # Yield the response as event-stream format
            response_text = chunk["response"]
            if response_text:
                yield f"data: {response_text}\n\n".encode("utf-8")
                
        # End of stream
        yield "data: [DONE]\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Error streaming completion for request {request_id}: {str(e)}")
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n".encode("utf-8")
    finally:
        # Clean up after request is done
        if request_id in active_requests:
            del active_requests[request_id]
        if request_id in request_start_times:
            end_time = time.time()
            latency = end_time - request_start_times[request_id]
            global total_latency
            total_latency += latency
            del request_start_times[request_id]

@app.post("/v1/completions")
async def completion(request: Request, completion_request: CompletionRequest, background_tasks: BackgroundTasks) -> StreamingResponse:
    """Handle code completion requests with streaming and cancellation support."""
    global request_count
    
    # Check authentication token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token or token not in active_tokens:
        return Response(status_code=401, content="Unauthorized")
    
    # Generate a unique ID for this request
    request_id = str(uuid.uuid4())
    request_count += 1
    request_start_times[request_id] = time.time()
    
    # Create a streaming task
    stream_task = asyncio.create_task(stream_completion(request_id, completion_request))
    active_requests[request_id] = stream_task
    
    # Return a streaming response
    return StreamingResponse(
        content=stream_task,
        media_type="text/event-stream",
        headers={
            "X-Request-ID": request_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.delete("/v1/completions/{request_id}")
async def cancel_completion(request_id: str) -> dict:
    """Cancel an ongoing completion request."""
    global cancelled_request_count
    
    if request_id in active_requests:
        task = active_requests.pop(request_id)
        task.cancel()
        cancelled_request_count += 1
        logger.info(f"Cancelled request {request_id}")
        return {"status": "cancelled", "request_id": request_id}
    
    return {"status": "not_found", "request_id": request_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, http="h11", log_level="info") 