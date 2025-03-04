from fastapi import FastAPI, Request, Response, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from typing import List, Dict, Any, Optional  # Importing 'Any' and 'Optional' for type hinting
from pydantic import BaseModel
import hashlib
import hmac
import json
import asyncio
from collections import deque
import logging
from datetime import datetime, timedelta
import psutil
import time
import os
from dotenv import load_dotenv
import requests
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from api_tasks.postmsg import postmsg
from api_tasks.sendreply import sendreply
from celery import Celery
import random
import configparser

"""
This FastAPI application serves as a webhook endpoint for Meta (Facebook/Instagram)
and processes direct messages and comments using Celery for asynchronous tasks.

It leverages Google Gemini API for generating responses and NLTK for sentiment analysis.
Configuration is managed through a config.ini file and environment variables.
"""

nltk.download('vader_lexicon')  # Ensure VADER lexicon is downloaded for sentiment analysis

load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Removed: STATIC_DIR = os.path.join(BASE_DIR, "static") # Static file directory is no longer used

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration Class ---
class Config:
    """
    Configuration class to load settings from config.ini and environment variables.

    Environment variables take precedence over settings in config.ini.
    """
    def __init__(self):
        config_parser = configparser.ConfigParser()
        config_parser.read('config.ini')  # Read settings from config.ini file

        # --- API Section ---
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", config_parser.get('api', 'gemini_api_key'))
        self.MODEL_NAME = os.getenv("MODEL_NAME", config_parser.get('api', 'model_name'))
        self.APP_SECRET = os.getenv("APP_SECRET", config_parser.get('api', 'app_secret'))
        self.VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", config_parser.get('api', 'verify_token'))

        # --- Celery Section ---
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", config_parser.get('celery', 'broker_url'))
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", config_parser.get('celery', 'result_backend'))

        # --- Default Responses Section ---
        self.DEFAULT_DM_RESPONSE_POSITIVE = os.getenv("DEFAULT_DM_RESPONSE_POSITIVE", config_parser.get('defaults', 'dm_response_positive'))
        self.DEFAULT_DM_RESPONSE_NEGATIVE = os.getenv("DEFAULT_DM_RESPONSE_NEGATIVE", config_parser.get('defaults', 'dm_response_negative'))
        self.DEFAULT_COMMENT_RESPONSE_POSITIVE = os.getenv("DEFAULT_COMMENT_RESPONSE_POSITIVE", config_parser.get('defaults', 'comment_response_positive'))
        self.DEFAULT_COMMENT_RESPONSE_NEGATIVE = os.getenv("DEFAULT_COMMENT_RESPONSE_NEGATIVE", config_parser.get('defaults', 'comment_response_negative'))

        # --- Instagram Section ---
        self.INSTAGRAM_ACCOUNT_ID_FOR_COMMENTS = os.getenv("INSTAGRAM_ACCOUNT_ID", config_parser.get('instagram', 'account_id_for_comments'))

        # --- Account Credentials (JSON from ENV, config.ini provides default structure) ---
        accounts_json_str = os.getenv("ACCOUNTS", config_parser.get('instagram', 'accounts_json')) # ENV overrides config.ini
        try:
            self.ACCOUNT_CREDENTIALS: Dict[str, str] = json.loads(accounts_json_str)
            logger.info("Account credentials loaded from environment variable ACCOUNTS.")
        except json.JSONDecodeError:
            self.ACCOUNT_CREDENTIALS: Dict[str, str] = {}
            logger.error("Failed to parse ACCOUNTS environment variable as JSON. Using empty account credentials.")

config = Config()  # Instantiate the configuration object
# --- End Configuration Class ---


# Initialize FastAPI application
app = FastAPI(title="Meta Webhook Server")

# Add CORS middleware to allow cross-origin requests (for development/testing if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - adjust in production for security
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

START_TIME = time.time()  # Record server start time for uptime calculation

# Data structures for webhook event handling
WEBHOOK_EVENTS = deque(maxlen=100)  # Store last 100 webhook events in a deque
CLIENTS: List[asyncio.Queue] = []  # List to hold SSE client queues for event broadcasting

# Webhook Credentials (loaded from config object)
APP_SECRET = config.APP_SECRET
VERIFY_TOKEN = config.VERIFY_TOKEN
gemini_api_key = config.GEMINI_API_KEY
model_name = config.MODEL_NAME

# Default response messages (loaded from config object)
default_dm_response_positive = config.DEFAULT_DM_RESPONSE_POSITIVE
default_dm_response_negative = config.DEFAULT_DM_RESPONSE_NEGATIVE
default_comment_response_positive = config.DEFAULT_COMMENT_RESPONSE_POSITIVE
default_comment_response_negative = config.DEFAULT_COMMENT_RESPONSE_NEGATIVE

WEBHOOK_FILE = "webhook_events.json"  # File to save webhook events for persistence

# --- Celery Configuration ---
CELERY_BROKER_URL = config.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = config.CELERY_RESULT_BACKEND
# ---------------------------

# --- Account Credentials ---
ACCOUNT_CREDENTIALS: Dict[str, str] = config.ACCOUNT_CREDENTIALS
# -------------------------


# Initialize Celery application
celery = Celery(__name__, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',  # Set a consistent timezone
    enable_utc=True,
    broker_connection_retry_on_startup=True
)

message_queue: Dict[str, List[Dict[str, Any]]] = {}  # Store messages per conversation_id
conversation_task_schedules: Dict[str, str] = {}  # Track scheduled task IDs per conversation


def startup_event():
    """Logs active Celery tasks on startup for monitoring purposes."""
    inspector = celery.control.inspect()
    active_tasks = inspector.active()
    if active_tasks:
        task_count = sum(len(tasks) for tasks in active_tasks.values())
        logger.warning(f"WARNING: {task_count} Celery tasks are still active on startup:")
        for worker, tasks in active_tasks.items():
            if tasks:
                logger.warning(f"  Worker {worker}:")
                for task in tasks:
                    logger.warning(f"    - {task['name']} (id: {task['id']})")
    else:
        logger.info("No active Celery tasks on startup.")

startup_event()


@celery.task(name="send_dm")
def send_dm(conversation_id_to_process: str, message_queue_snapshot: Dict[str, List[Dict[str, Any]]], account_id_to_use: str) -> Dict[str, Any]:
    """
    Celery task to process and respond to a conversation's messages.

    Args:
        conversation_id_to_process: The ID of the conversation to process.
        message_queue_snapshot: A snapshot of the message queue for processing.
        account_id_to_use: The Instagram account ID to use for sending the response.

    Returns:
        A dictionary indicating the task status and processed conversation details.
    """
    try:
        if conversation_id_to_process not in message_queue_snapshot or not message_queue_snapshot[conversation_id_to_process]:
            logger.info(f"No messages to process for conversation: {conversation_id_to_process}. Task exiting.")
            return {"status": "no_messages_to_process", "conversation_id": conversation_id_to_process}

        messages = message_queue_snapshot[conversation_id_to_process]  # Use the snapshot to avoid race conditions
        recipient_id = messages[0]["sender_id"]
        combined_text = "\n".join([msg["text"] for msg in messages])

        sentiment = analyze_sentiment(combined_text)  # Analyze sentiment BEFORE LLM call
        logger.info(f"Sentiment Analysis Result: Sentiment: {sentiment}, Combined Text: '{combined_text}'")

        if sentiment == "Positive":
            llm_prompt_suffix = "Respond with a very enthusiastic and thankful tone, acknowledging the compliment. Keep it concise and friendly."
        elif sentiment == "Negative":
            llm_prompt_suffix = "Respond with an apologetic and helpful tone, asking for more details about the issue so we can improve. Keep it concise and professional."
        else: # Neutral or mixed sentiment
            llm_prompt_suffix = "Respond in a helpful and neutral tone. Keep it concise and informative."

        system_prompt_content = ""
        with open("collection_system_prompt/system_prompt.txt", "r") as file:
            system_prompt_content = file.read().strip()
        full_prompt = system_prompt_content + " Message/Conversation input from user: " + combined_text + " "

        # Generate response using LLM
        try:
            response_text = llm_response(gemini_api_key, model_name, full_prompt)
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            if sentiment == "Positive":
                response_text = default_dm_response_positive
            else:
                response_text = default_dm_response_negative

        # Send the combined response
        try:
            access_token_to_use = get_access_token_for_account(account_id_to_use)  # Get access token dynamically
            result = postmsg(access_token_to_use, recipient_id, response_text)  # Use dynamic access token
            logger.info(f"Sent combined response to {recipient_id} using account {account_id_to_use}. Result: {result}")
        except Exception as e:
            logger.error(f"Error sending message to {recipient_id} using account {account_id_to_use}: {e}")

        # Clear ONLY for the processed conversation ID (after successful processing)
        if conversation_id_to_process in message_queue:  # Double check before deleting (race condition safety)
            del message_queue[conversation_id_to_process]
            logger.info(f"Cleared message queue for conversation: {conversation_id_to_process}")
        else:
            logger.warning(f"Conversation ID {conversation_id_to_process} not found in message_queue during clear. Possible race condition.")

        # Clear task schedule after successful processing
        if conversation_id_to_process in conversation_task_schedules:
            del conversation_task_schedules[conversation_id_to_process]

        return {"status": "success", "processed_conversation": conversation_id_to_process, "message_count": len(messages)}

    except Exception as e:
        logger.error(f"Error in send_dm task for conversation {conversation_id_to_process}: {e}")
        raise  # Re-raise exception for Celery to handle retries


@celery.task(name="send_delayed_reply")
def send_delayed_reply(comment_id: str, message_to_be_sent: str, account_id_to_use: str) -> Dict[str, Any]:
    """
    Sends a delayed reply to an Instagram comment using Celery.

    Args:
        comment_id: The ID of the comment to reply to.
        message_to_be_sent: The message content to send as a reply.
        account_id_to_use: The Instagram account ID to use for sending the reply.

    Returns:
        The response data from the sendreply function.
    """
    try:
        access_token_to_use = get_access_token_for_account(account_id_to_use)  # Get access token dynamically
        result = sendreply(access_token_to_use, comment_id, message_to_be_sent)  # Use dynamic access token
        logger.info(f"Reply sent to comment {comment_id} using account {account_id_to_use}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error sending reply to comment {comment_id} using account {account_id_to_use}: {e}")
        raise  # Re-raise exception for Celery retry handling.


def save_events_to_file():
    """Save webhook events to a JSON file for persistence."""
    with open(WEBHOOK_FILE, "w") as f:
        json.dump(list(WEBHOOK_EVENTS), f, indent=4)


def load_events_from_file():
    """Load webhook events from the JSON file at startup if it exists."""
    if os.path.exists(WEBHOOK_FILE):
        try:
            with open(WEBHOOK_FILE, "r") as f:
                events = json.load(f)
                WEBHOOK_EVENTS.extend(events)
        except Exception as e:
            logger.error(f"Failed to load events from file: {e}")


def get_access_token_for_account(account_id: str) -> str:
    """
    Retrieve access token for a given account ID from the ACCOUNT_CREDENTIALS dictionary.

    Args:
        account_id: The Instagram account ID.

    Returns:
        The access token for the given account ID.

    Raises:
        ValueError: If no access token is found for the account ID.
    """
    access_token = ACCOUNT_CREDENTIALS.get(account_id)
    if not access_token:
        logger.error(f"No access token found for account ID: {account_id} in ACCOUNT_CREDENTIALS.")
        raise ValueError(f"No access token found for account ID: {account_id}")
    return access_token


def llm_response(api_key: str, model_name: str, query: str) -> str:
    """
    Generates response using Google Gemini API.

    Args:
        api_key: API key for Google Gemini.
        model_name: Name of the Gemini model to use.
        query: The query/prompt to send to the LLM.

    Returns:
        The text response generated by the LLM.

    Raises:
        Exception: If there's an error during the API request or response processing.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": query}]}]}  # Construct payload with the query
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_json = response.json()
        if 'candidates' in response_json and response_json['candidates']:
            return response_json['candidates'][0]['content']['parts'][0]['text']
        else:
            raise Exception("No candidates found in the response.")
    except requests.exceptions.RequestException as e: # Catch specific request exceptions
        raise Exception(f"API request failed: {str(e)}")
    except json.JSONDecodeError as e: # Catch JSON decoding errors
        raise Exception(f"Failed to decode JSON response: {str(e)}")
    except Exception as e: # Catch any other exceptions
        raise Exception(f"An error occurred: {str(e)}")


def parse_instagram_webhook(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse Instagram webhook events for both direct messages and comments.

    Args:
        data: The full webhook payload received from Meta.

    Returns:
        A list of parsed event dictionaries, each representing a message or comment event.
    """
    results: List[Dict[str, Any]] = []

    try:
        # Extract timestamp from the wrapper data
        event_timestamp = data.get("timestamp")

        # Handle different possible payload structures
        payload = data.get("payload", data) if isinstance(data, dict) else data

        # Extract entries from payload
        entries = payload.get("entry", [])

        logger.info(f"Number of entries found: {len(entries)}")

        for entry in entries:
            # Process Direct Messages
            messaging_events = entry.get("messaging", [])
            for messaging_event in messaging_events:
                sender = messaging_event.get("sender", {})
                recipient = messaging_event.get("recipient", {})
                message = messaging_event.get("message", {})

                if message:
                    message_event_details = {
                        "type": "direct_message",
                        "sender_id": sender.get("id"),
                        "recipient_id": recipient.get("id"),
                        "text": message.get("text"),
                        "message_id": message.get("mid"),
                        "timestamp": event_timestamp,
                        "entry_time": entry.get("time"),
                        "is_echo": message.get("is_echo", False)
                    }
                    results.append(message_event_details)

            # Process Comments
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "comments":
                    comment_value = change.get("value", {})
                    if comment_value:
                        comment_details = {
                            "type": "comment",
                            "comment_id": comment_value.get("id"),
                            "text": comment_value.get("text"),
                            "timestamp": event_timestamp,
                            "media_id": comment_value.get("media", {}).get("id"),
                            "media_type": comment_value.get("media", {}).get("media_product_type"),
                            "from_username": comment_value.get("from", {}).get("username"),
                            "from_id": comment_value.get("from", {}).get("id"),
                            "to_id": entry.get("id"),  # Added 'to_id' to comment details
                            "entry_time": entry.get("time")
                        }
                        results.append(comment_details)

    except Exception as e:
        logger.error(f"Parsing error: {e}")
        logger.error(f"Problematic payload: {json.dumps(data, indent=2)}")

    return results


def analyze_sentiment(comment_text: str) -> str:
    """
    Analyzes sentiment of text using NLTK's VADER sentiment intensity analyzer.

    Args:
        comment_text: The text to analyze for sentiment.

    Returns:
        "Positive" if the sentiment is positive, "Negative" otherwise (neutral is considered negative).
    """
    sia = SentimentIntensityAnalyzer()
    sentiment_scores = sia.polarity_scores(comment_text)

    # Determine sentiment based on compound score
    if sentiment_scores['compound'] > 0.25:
        sentiment = "Positive"
    else:
        sentiment = "Negative"  # Consider neutral as negative for default responses

    return sentiment


# Load events from file on startup
load_events_from_file()


@app.get("/ping")
def ping():
    """Health check endpoint to verify server is running."""
    return {"message": "Server is active"}


@app.get("/health")
async def health_check():
    """
    Endpoint to check the health status of the server and system metrics.

    Returns:
        A dictionary containing server status, timestamp, uptime, and system metrics.
    """
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
    """
    Verify that the webhook request is indeed from Meta by checking the signature.

    Args:
        request: FastAPI Request object containing headers.
        raw_body: Raw request body as bytes.

    Returns:
        True if the signature is valid, False otherwise.
    """
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
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint for Meta.

    This endpoint is called by Meta to verify the webhook subscription.
    It checks the 'hub.mode', 'hub.verify_token', and returns 'hub.challenge' if verification is successful.

    Args:
        hub_mode: The mode of the webhook request (should be 'subscribe').
        hub_verify_token: The verify token sent by Meta.
        hub_challenge: The challenge string sent by Meta for verification.

    Returns:
        Response with the hub_challenge as plain text if verification is successful.

    Raises:
        HTTPException: 403 Forbidden if verification fails.
    """
    logger.info(f"Received verification request: hub_mode={hub_mode}, hub_verify_token={hub_verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verification successful")
        return Response(content=hub_challenge, media_type="text/html")  # Respond with challenge

    logger.error("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")  # Verification failed


@app.post("/webhook")
async def webhook(request: Request):
    """
    Main webhook endpoint to handle incoming webhook events from Meta.

    This endpoint receives real-time updates from Instagram (Direct Messages, Comments, etc.).
    It verifies the request signature, parses the event, and then processes it accordingly,
    queuing tasks for response generation using Celery.

    Args:
        request: FastAPI Request object containing headers and body.

    Returns:
        A dictionary indicating success and the parsed events.

    Raises:
        HTTPException: 400 Bad Request if JSON payload is invalid, 403 Forbidden if signature is invalid.
    """
    raw_body = await request.body() # Get raw request body as bytes
    logger.info(f"Received raw webhook payload: {raw_body.decode('utf-8')}")

    if not await verify_webhook_signature(request, raw_body): # Verify webhook signature
        raise HTTPException(status_code=403, detail="Invalid signature") # Signature verification failed

    try:
        payload = json.loads(raw_body) # Parse JSON payload
        event_with_time = {
            "timestamp": datetime.now().isoformat(),
            "payload": payload
        }

        # Parse the webhook and get events
        parsed_events = parse_instagram_webhook(event_with_time)
        logger.info("Parsed Webhook Events:")
        for event in parsed_events:
            logger.info(json.dumps(event, indent=2))

            # Handle different types of events
            if event["type"] == "direct_message" and event["is_echo"] == False:
                conversation_id = str(event["sender_id"]) + "_" + str(event["recipient_id"])
                account_id_to_use = str(event["recipient_id"])  # Use recipient_id as account_id

                if conversation_id not in message_queue:
                    # New conversation
                    message_queue[conversation_id] = [event] # Initialize message queue for conversation
                    delay = random.randint(1 * 60, 2 * 60)  # Initial delay (1-2 minutes)
                    task = send_dm.apply_async(
                        args=(conversation_id, message_queue.copy(), account_id_to_use),  # Pass account_id
                        countdown=delay, expires=delay + 3600 # Task expires after 1 hour + delay
                    )
                    conversation_task_schedules[conversation_id] = task.id  # Track scheduled task ID
                    logger.info(f"Scheduled initial DM task for new conversation: {conversation_id}, task_id: {task.id}, delay: {delay}s, account_id: {account_id_to_use}")

                else:
                    # Existing conversation - add new message and re-schedule
                    message_queue[conversation_id].append(event) # Append new message to existing conversation queue
                    logger.info(f"Added message to existing conversation: {conversation_id}")

                    # Re-schedule send_dm task with a shorter delay upon new message
                    if conversation_id in conversation_task_schedules:
                        task_id_to_extend = conversation_task_schedules[conversation_id]
                        celery.control.revoke(task_id_to_extend, terminate=False)  # Cancel existing task
                        del conversation_task_schedules[conversation_id]  # Remove old task ID

                        new_delay = 30  # Shorter delay for re-scheduling (e.g., 30 seconds)
                        new_task = send_dm.apply_async(
                            args=(conversation_id, message_queue.copy(), account_id_to_use),  # Pass account_id
                            countdown=new_delay, expires=new_delay + 3600 # Task expires after 1 hour + new delay
                        )
                        conversation_task_schedules[conversation_id] = new_task.id  # Track new task ID
                        logger.info(f"Re-scheduled DM task for conversation: {conversation_id}, task_id: {new_task.id}, new delay: {new_delay}s (due to new message), account_id: {account_id_to_use}")


            elif event["type"] == "comment":  # Handle comment events
                if event["to_id"] in ACCOUNT_CREDENTIALS:  # Check if comment is for a configured account
                    # Analyze sentiment of the comment
                    if event["from_id"] == event["to_id"]: # Ignore comments from the same account
                        logger.info(f"Comment received from the same account ID: {event['from_id']}. Ignoring.")
                        break  # Skip processing comment from same account

                    else:
                        sentiment = analyze_sentiment(event["text"]) # Analyze comment sentiment
                        if sentiment == "Positive":
                            message_to_be_sent = default_comment_response_positive
                        else:
                            message_to_be_sent = default_comment_response_negative

                        account_id_to_use = event["to_id"]  # Use comment's 'to_id' as account_id
                        # Schedule the reply task
                        delay = random.randint(1 * 60, 2 * 60)  # 1 to 2 minutes delay for comment reply
                        send_delayed_reply.apply_async(
                            args=(event["comment_id"], message_to_be_sent, account_id_to_use),  # Pass account_id
                            countdown=delay, expires=delay + 600 # Task expires after 10 minutes + delay
                        )
                        logger.info(f"Scheduled reply task for comment {event['comment_id']} in {delay} seconds using account {account_id_to_use}")
                else:
                    logger.warning(f"Comment received for unconfigured account ID: {event['to_id']}. Ignoring.")
                    # Optionally, handle comments for unconfigured accounts differently

        # Store event and notify clients
        WEBHOOK_EVENTS.append(event_with_time) # Add event to deque
        save_events_to_file() # Save events to file

        # Notify connected SSE clients
        for client_queue in CLIENTS:
            await client_queue.put(event_with_time) # Put event into each client queue

        return {"success": True, "parsed_events": parsed_events} # Return success and parsed events

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") # Invalid JSON payload


@app.get("/webhook_events")
async def get_webhook_events():
    """
    Endpoint to retrieve all stored webhook events.

    Returns:
        A dictionary containing a list of stored webhook events.
    """
    return {"events": list(WEBHOOK_EVENTS)}


async def event_generator(request: Request):
    """
    Asynchronous generator for Server-Sent Events (SSE).

    This generator sends stored webhook events to newly connected clients and then
    listens for new events to broadcast in real-time. It also sends keep-alive messages
    to prevent connection timeouts.

    Args:
        request: FastAPI Request object to check for client disconnection.

    Yields:
        SSE 'data:' messages containing JSON-serialized webhook events.
    """
    client_queue: asyncio.Queue = asyncio.Queue() # Create a queue for this client
    CLIENTS.append(client_queue) # Add client queue to the global list

    try:
        # Send existing events to the newly connected client
        for event in WEBHOOK_EVENTS:
            yield f"data: {json.dumps(event)}\n\n" # Yield existing events as SSE data

        # Listen for new events and send to client
        while not await request.is_disconnected(): # Check if client is still connected
            try:
                event = await asyncio.wait_for(client_queue.get(), timeout=30) # Wait for new event (with timeout)
                yield f"data: {json.dumps(event)}\n\n" # Yield new event as SSE data
            except asyncio.TimeoutError:
                yield ": keepalive\n\n" # Send keepalive message to prevent timeout

    finally:
        CLIENTS.remove(client_queue) # Remove client queue when client disconnects


@app.get("/events")
async def events(request: Request):
    """
    SSE endpoint for real-time webhook events.

    This endpoint establishes a Server-Sent Events connection and uses the event_generator
    to stream webhook events to the client in real-time.

    Args:
        request: FastAPI Request object.

    Returns:
        EventSourceResponse that streams events using the event_generator.
    """
    return EventSourceResponse(event_generator(request)) # Return SSE response using event generator


# Removed: Serve static HTML and mount - Static file serving is no longer used
# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- MODIFICATION: Celery task check on startup ---
# --------------------------------------------------


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) # Run the FastAPI application