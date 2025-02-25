import requests
import json

access_token = "IGAAI8SJHk0mNBZAFB6TF9zejQtcnoyWWlOaGRSaEJyRGlfTXVUMEdveGJiVURXRXNlOUUwZA0QwQ2w4ZAi1HVE5mM2tqdk1jYW94VHVQbHdnWUx1NVduTHg1QzRMY1BzMVdqaEpId3B3X0JxNzM4dWJmWGtsWnZAKb1p4SnNiRzFMZAwZDZD"
recipient_id = "1644347192955956"
message_to_be_sent = "This is a test direct message reply!"

def postmsg(access_token, recipient_id, message_to_be_sent):
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
    return data

print(json.dumps(postmsg(access_token,recipient_id,message_to_be_sent), indent=4))
