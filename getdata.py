import requests
import json

gemini_api_key = "AIzaSyDgH-W60Vk--3rSbTq91lzYoMfc1j1RzFE"
model_name = "gemini-1.5-flash"

with open("collection_system_prompt/system_prompt.txt", "r") as file:
        system_prompt = file.read().strip()

def llm_response(api_key, model_name, query):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    prompt_text = f"""
    {system_prompt} Message/Conversation sent by user: {query}
    """
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.ok:
            response_json = response.json()
            if 'candidates' in response_json and response_json['candidates']:
                return response_json['candidates'][0]['content']['parts'][0]['text']
            else:
                return "No candidates found in the response."
        else:
            return f"Error: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
print(llm_response(gemini_api_key, model_name, "Hey your content has been great for the past few days , what happened?"))