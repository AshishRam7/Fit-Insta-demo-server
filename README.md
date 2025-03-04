# Instagram Automation Server Bot

[![Project Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com/your-github-username/your-repo-name)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-blueviolet.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3+-orange.svg)](https://docs.celeryq.dev/en/stable/)

## Overview

This project is a robust and scalable **Instagram Automation Server Bot** built using **FastAPI** and **Celery**. It enables **intelligent automation of Instagram Direct Messages (DMs) and comments** through **sentiment analysis** and **Google Gemini (LLM) integration**. The bot listens for **real-time events** via **Instagram Webhooks**, ensuring dynamic and proactive engagement with followers.

### **Key Features**

- **Webhook Handling:** Real-time processing of Instagram messages and comments.
- **Security:** Webhook signature verification for authenticity.
- **Intelligent Responses:**
  - **Sentiment Analysis (VADER - NLTK)** for Positive/Negative categorization.
  - **Google Gemini API** for context-aware message replies.
  - **Fallback Responses** when the LLM is unavailable.
- **Direct Message Automation:**
  - Queueing and scheduling responses for human-like interaction.
  - Handling ongoing conversations dynamically.
- **Comment Automation:**
  - Auto-reply to comments based on sentiment.
  - Scheduled responses to avoid bot-like behavior.
- **Account Management:** Secure storage of **Instagram Access Tokens** in **SQLite**.
- **Scalable Architecture:** Background task execution using **Celery**.
- **Real-time Monitoring:** **Server-Sent Events (SSE)** endpoint to stream webhook events.
- **Health Monitoring:** `/ping` and `/health` endpoints for uptime checks.
- **Configuration Management:** Environment variables stored securely in `.env`.
- **Detailed Logging:** Comprehensive logs for debugging and performance analysis.
- **Ease of Deployment:** Ready for **local development** and **cloud deployment** (e.g., **Render**).

---

## **Architecture**

![diagram-export-3-4-2025-1_51_38-PM](https://github.com/user-attachments/assets/433c5fe7-99be-46f7-8837-452b4485ba69)

The system consists of three primary components:

1. **FastAPI Web Server**: Handles incoming webhook events, processes them, and triggers automation logic.
2. **Celery Task Queue**: Manages background tasks asynchronously to avoid blocking the API server.
3. **Redis** (Broker & Result Backend): Used by Celery for task scheduling and execution.

**Workflow:**
1. Instagram sends a webhook event (message/comment) → Received by FastAPI.
2. FastAPI verifies the webhook signature and extracts the event data.
3. Sentiment analysis and response generation are handled asynchronously via Celery.
4. Responses are either **default sentiment-based** or generated dynamically using **Google Gemini API**.
5. Replies are sent back to Instagram using the Graph API.

---

## **Technology Stack**

| Component  | Technology  |
|------------|-------------|
| **Backend Framework** | FastAPI |
| **Task Queue** | Celery |
| **Language Model** | Google Gemini API |
| **Sentiment Analysis** | NLTK (VADER) |
| **Database** | SQLite (Easily replaceable) |
| **Messaging & Event Processing** | Webhooks, Server-Sent Events (SSE) |
| **API Calls** | requests (Python HTTP client) |
| **Environment Variables** | python-dotenv |

---

## **Installation & Setup**

### **Local Development Setup**

#### **Prerequisites**
- Python 3.11+
- Redis (for Celery broker)

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Install Redis (MacOS)
brew install redis
```

#### **Clone Repository & Setup Environment**

```bash
git clone https://github.com/your-github-username/your-repo-name.git
cd your-repo-name
```

#### **Configure Environment Variables**
Create a `.env` file and add:

```ini
APP_SECRET="your_meta_app_secret"
VERIFY_TOKEN="your_verify_token"
GEMINI_API_KEY="your_gemini_api_key"
INSTAGRAM_ACCOUNT_ID="your_instagram_account_id"
ACCOUNTS={"IG_ACCOUNT_ID_1":"IG_ACCESS_TOKEN_1", "": "", ...}
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

#### **Install Dependencies**

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
```

#### **Run Services**

```bash
# Terminal 1 - Start Celery Worker
celery -A server.celery worker --loglevel=info

# Terminal 2 - Start FastAPI Server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

---

## **Deployment on Render**

**Important Note:** Ensure that the Web Service and Redis Instance are present inside the same Render workspace to make sure the connection between them is established

### **1. Provision Redis Instance**
- Create a **Redis instance** on Render.
- Obtain connection URL(Internal URL): `redis://<username>:<password>@<host>:<port>`.

### **2. Deploy Web Service**
- Create a new **Web Service** on Render.
- Connect the current github repository with the service.
- Enter the below the details in the appropriate sections:
#### **Build Command:**

```bash
pip install -r requirements.txt && python -c "import nltk; nltk.download('vader_lexicon')"
```

#### **Start Command:**

```bash
bash -c "celery -A server.celery worker -l info & uvicorn server:app --host 0.0.0.0 --port 8000"
```

- Set up /health as the server health checkpoint section
- Set up the following Enviroment variables: 
```ini
APP_SECRET="your_meta_app_secret"
VERIFY_TOKEN="your_verify_token"
GEMINI_API_KEY="your_gemini_api_key"
INSTAGRAM_ACCOUNT_ID="your_instagram_account_id"
ACCOUNTS={"IG_ACCOUNT_ID_1":"IG_ACCESS_TOKEN_1", "": "", ...}
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

- Click on deploy service 

---

## **Meta App Setup for Webhooks**

1. **Create a Meta App** on the [Meta Developer Dashboard](https://developers.facebook.com/).

   <img width="947" alt="image" src="https://github.com/user-attachments/assets/89dd2b0f-036a-485f-afe9-391a6d358977" />

3. **Navigate to Products** → **Add Products** → Subscribe to **Instagram**.

   <img width="923" alt="image" src="https://github.com/user-attachments/assets/07922c9f-1166-49e2-afb6-1b55c40f4510" />

5. Click **API Setup with Instagram Login** on the sidepanel under **Products -> Instagram**.

   <img width="166" alt="image" src="https://github.com/user-attachments/assets/8d249dd1-09c7-4bde-8046-ea078f2699dd" />

7. **Add Instagram Tester Accounts and generate access tokens**:
   - Navigate to **App Roles** → **Roles Subsection**.

     ![image](https://github.com/user-attachments/assets/249f270d-982b-425b-b665-e431267085e5)

   - Click **Add People**, select **Instagram Tester Account**, and provide username & login. Verify whether the account has been added by refreshing the page -> perform this for all accounts you want to connect to the server.

     ![image](https://github.com/user-attachments/assets/88d2d7ba-a2bb-4b43-91af-40a4ebdaa8ff)

   - Go to **API Setup with Instagram Login** → **Generate Access Tokens**.

     ![image](https://github.com/user-attachments/assets/a368078f-dde7-4e96-8427-5ba750bb989b)

   - Login with your Instagram account(only public + business + professional Instagram can be added) , and allow all permissions requested.

     ![image](https://github.com/user-attachments/assets/9051b66a-7f04-4f46-9e01-310729b1f1fa)

   - If token generated copy and store safely along with that particular account id(We will be adding this in the environment variables)
   - If a blank white screen appears, inspect the page and search for `IGAA`.

     ![image](https://github.com/user-attachments/assets/33e755ef-35b6-4a05-9c00-5bc8573b41ec)

   - Copy the token and store it securely.

8. Copy details like **App Secret**, **account_id's and their respective access tokens** and add them to the enviroment variables in the right format mentionned already, and refresh the deployment after the change to make sure the changes are live.

9. Set the Webhook URL in Instagram  as `https://<public_deployed_url>/webhook` and use the verification token you had setup in `Environment variables`.

   ![image](https://github.com/user-attachments/assets/9bd7d6a1-e0fe-40f5-9b22-fa723b505e07)

10. Make the App live before the next verification step.

    <img width="866" alt="image" src="https://github.com/user-attachments/assets/a085ce24-7ef0-420d-a29f-bc994f4e3c40" />

11. Toggle the **add certificate** option and then click **Verify Webhook Server** to verify your server and start receiving your webhook notifications.

    ![image](https://github.com/user-attachments/assets/70602b8b-1160-4504-9ad7-64dd691e621f)

12. Subscribe to **comments, live_comments** and the **messages** webhook_fields.

    ![image](https://github.com/user-attachments/assets/669282ad-9623-4c94-b138-02eea097ae6b)


**Importante Note* : The Instagram Account_id and access tokens are sensitive information and need to be stored safely


---


## **API Documentation**

### **Available Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ping` | Server status check |
| `GET` | `/health` | System metrics and health check |
| `GET` | `/events` | Stream webhook events in real-time |
| `POST` | `/webhook` | Handles Instagram webhook events |
| `GET` | `/webhook_events` | Stores and displays Instagram webhook events |


---

## **Customization**

- Modify **default responses** in `server.py`.
- Update **sentiment thresholds** in `analyze_sentiment()`.
- Adjust **response delays** in webhook handlers.
- Fine-tune **Google Gemini prompts** in `system_prompt.txt`.

---

## **CI/CD Pipeline**

- GitHub Actions for automated testing.
- Runs unit tests (`pytest`) on each push.
- Verifies API health endpoints.
- Configuration in `.github/workflows/buildrun.yaml`.

---

## **Contributing**

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push to GitHub: `git push origin feature/your-feature`.
5. Open a **Pull Request**.

---

## **License**

[MIT License](LICENSE)

---

## **Contact**

- [GitHub Issues](https://github.com/your-github-username/your-repo-name/issues)
- Email: `your.email@example.com`

---

**⚠ Disclaimer:** Ensure compliance with Instagram's terms of service. Avoid spam-like behavior that may result in account suspension.

