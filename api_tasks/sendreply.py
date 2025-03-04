import requests
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)  # Ensure logger is defined

def sendreply(access_token, comment_id, message_to_be_sent):
    """Sends a reply to an Instagram comment."""
    logger.info(f"Send Reply Function Triggered: Sending reply to comment {comment_id} using access token: {access_token}")
    url = f"https://graph.instagram.com/v22.0/{comment_id}/replies"

    params = {
        "message": message_to_be_sent,
        "access_token": access_token
    }

    response = requests.post(url, params=params)
    data = response.json()
    logger.info(f"Response from Instagram Reply API: {data}")
    return data