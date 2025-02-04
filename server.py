from fastapi import FastAPI, Request, Response, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from typing import List
import hashlib
import hmac
import json
import asyncio
from collections import deque
import logging
from datetime import datetime
import psutil
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Meta Webhook Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()


# Store webhook events - using deque with max size to prevent memory issues
WEBHOOK_EVENTS = deque(maxlen=100)

# Store SSE clients
CLIENTS: List[asyncio.Queue] = []

# Webhook Credentials
APP_SECRET = os.getenv("APP_SECRET", "e18fff02092b87e138b6528ccfa4a1ce")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "fitvideodemo")

# Save Webhook Events to JSON File
WEBHOOK_FILE = "webhook_events.json"


def save_events_to_file():
    """Save webhook events to a JSON file."""
    with open(WEBHOOK_FILE, "w") as f:
        json.dump(list(WEBHOOK_EVENTS), f, indent=4)


def load_events_from_file():
    """Load webhook events from the JSON file (if it exists)."""
    if os.path.exists(WEBHOOK_FILE):
        try:
            with open(WEBHOOK_FILE, "r") as f:
                events = json.load(f)
                WEBHOOK_EVENTS.extend(events)
        except Exception as e:
            logger.error(f"Failed to load events from file: {e}")


# Load events from file on startup
load_events_from_file()


@app.get("/health")
async def health_check():
    """Check server health status."""
    uptime_seconds = int(time.time() - START_TIME)
    system_stats = {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime_seconds,
        "system_metrics": system_stats
    }


async def verify_webhook_signature(request: Request, raw_body: bytes) -> bool:
    """Verify that the webhook request is from Meta."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature or not signature.startswith("sha256="):
        logger.error("Signature is missing or not properly formatted")
        return False

    expected_signature = hmac.new(
        APP_SECRET.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature[7:], expected_signature):
        logger.error(f"Signature mismatch: {signature[7:]} != {expected_signature}")
        return False

    return True


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """Verify webhook from Meta."""
    logger.info(f"Received verification request: {hub_mode}, {hub_verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verification successful")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.error("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook events from Meta."""
    raw_body = await request.body()

    if not await verify_webhook_signature(request, raw_body):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(raw_body)
        event_with_time = {
            "timestamp": datetime.now().isoformat(),
            "payload": payload
        }

        WEBHOOK_EVENTS.append(event_with_time)
        save_events_to_file()  # Save to JSON file

        # Notify connected SSE clients
        for client_queue in CLIENTS:
            await client_queue.put(event_with_time)

        logger.info(f"Received webhook: {payload}")
        return {"success": True}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


@app.get("/webhook_events")
async def get_webhook_events():
    """Retrieve all stored webhook events."""
    return {"events": list(WEBHOOK_EVENTS)}


async def event_generator(request: Request):
    """Generate Server-Sent Events."""
    client_queue = asyncio.Queue()
    CLIENTS.append(client_queue)

    try:
        # Send existing events
        for event in WEBHOOK_EVENTS:
            yield f"data: {json.dumps(event)}\n\n"

        # Listen for new events
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(client_queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    finally:
        CLIENTS.remove(client_queue)


@app.get("/events")
async def events(request: Request):
    """SSE endpoint for real-time webhook events."""
    return EventSourceResponse(event_generator(request))


# Serve static HTML
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
