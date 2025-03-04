import requests
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)  # Ensure logger is defined

def postmsg(access_token, recipient_id, message_to_be_sent):
    """Sends a direct message to Instagram."""
    logger.info(f"Post Function Triggered: Sending DM to recipient {recipient_id} using access token: {access_token}")
    url = "https://graph.instagram.com/v21.0/me/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    json_body = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_to_be_sent
        }
    }

    response = requests.post(url, headers=headers, json=json_body)
    data = response.json()
    logger.info(f"Response from Instagram API: {data}")
    return data