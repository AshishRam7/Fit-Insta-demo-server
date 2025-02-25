import requests
import json

# Replace with actual comment ID and access token
def sendreply():
    comment_id = "18089022370492854"  
    access_token = "IGAAI8SJHk0mNBZAFB6TF9zejQtcnoyWWlOaGRSaEJyRGlfTXVUMEdveGJiVURXRXNlOUUwZA0QwQ2w4ZAi1HVE5mM2tqdk1jYW94VHVQbHdnWUx1NVduTHg1QzRMY1BzMVdqaEpId3B3X0JxNzM4dWJmWGtsWnZAKb1p4SnNiRzFMZAwZDZD"
    message_to_be_sent = "This is a comment reply!"

    url = f"https://graph.instagram.com/v22.0/{comment_id}/replies"

    params = {
        "message": "Thanks a lot!",
        "access_token": access_token
    }

    response = requests.post(url, params=params)
    data = response.json()
    return data

print(json.dumps(data, indent=4))
