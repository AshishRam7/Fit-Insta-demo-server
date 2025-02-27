# Instagram Automation Server Bot

[![Project Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com/InstaBotDev/instagram-auto-bot)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-blueviolet.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3+-orange.svg)](https://docs.celeryq.dev/en/stable/)

## Overview

This project is a powerful and flexible Instagram automation server bot built using Python, FastAPI, and Celery. It's designed to intelligently handle Instagram Direct Messages (DMs) and comments by leveraging sentiment analysis and a Language Model (Google Gemini) for automated responses.  The bot listens for real-time events from Instagram via webhooks, allowing for proactive engagement with your audience.

**Key Features:**

*   **Real-time Instagram Webhook Handling:**  Receives and processes Instagram webhook events for direct messages and comments.
*   **Webhook Signature Verification:**  Ensures the security of incoming webhooks by verifying signatures from Meta.
*   **Intelligent Response Automation:**
    *   **Sentiment Analysis:** Uses NLTK's VADER to analyze the sentiment of incoming messages and comments (Positive/Negative).
    *   **Language Model Integration (Google Gemini):** Generates contextually relevant responses to DMs based on sentiment and conversation history.
    *   **Default Responses:** Fallback responses are used for sentiment-based replies when the Language Model is unavailable or fails.
*   **Direct Message Automation:**
    *   Manages conversations and queues messages for each conversation.
    *   Schedules delayed responses using Celery to mimic human-like interaction.
    *   Responds to new messages within existing conversations, rescheduling response tasks dynamically.
*   **Comment Automation:**
    *   Automatically replies to Instagram comments based on sentiment (Positive/Negative) with default responses.
    *   Schedules delayed comment replies using Celery.
*   **Account Management:** Stores Instagram access tokens as environment variables, supporting multi-account setup via configuration.
*   **Scalable Task Processing:** Utilizes Celery for asynchronous task management, ensuring efficient handling of responses and preventing blocking the main API server. **Currently configured with in-memory broker and backend for simplified setup.** For production, consider using Redis or RabbitMQ for scalability and reliability.
*   **Real-time Event Streaming (SSE):** Provides a Server-Sent Events endpoint (`/events`) to stream webhook events in real-time to connected clients for monitoring and debugging.
*   **Health Monitoring:** Includes `/ping` and `/health` endpoints for server health checks and uptime monitoring.
*   **Configuration via Environment Variables:**  Easily configure sensitive information (API keys, tokens, account details) using a `.env` file and environment variables.
*   **Detailed Logging:**  Comprehensive logging for debugging and monitoring bot activity.
*   **Cloud-Ready Deployment:** Designed for deployment on cloud platforms like Render or Azure.

## Tech Stack

*   **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (for building the API server)
*   **Asynchronous Task Queue:** [Celery](https://docs.celeryq.dev/en/stable/) (for managing background tasks like sending responses) **(In-Memory Broker & Backend by default)**
*   **Language Model (LLM):** [Google Gemini API](https://ai.google.dev/gemini-api) (for generating dynamic DM responses)
*   **Sentiment Analysis:** [NLTK (VADER)](https://www.nltk.org/howto/vader.html) (for sentiment analysis of text)
*   **Database:** **In-Memory Dictionary** (for storing account access tokens via environment variables - consider more persistent storage like Redis for production)
*   **Real-time Communication:** [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) via `sse_starlette`
*   **HTTP Client:** [requests](https://requests.readthedocs.io/en/latest/) (for making API calls to Instagram and Google Gemini)
*   **Environment Management:** [python-dotenv](https://pypi.org/project/python-dotenv/) (for loading environment variables from `.env` file)
*   **Dependency Management:** [pip](https://pip.pypa.io/en/stable/)

## Setup and Installation

This guide will walk you through setting up the Instagram Automation Bot for cloud deployment. We'll cover:

1.  **Meta Developer Account and Instagram App Setup**
2.  **Webhook Server and Redis (or In-Memory) Instance Hosting (Render Example)**
3.  **Environment Variable Configuration**
4.  **Finalizing Setup and Running the Bot**

Let's begin!

### 1. Meta Developer Account and Instagram App Setup

This section outlines how to create a Meta Developer App, connect it to your Instagram Professional account, and configure webhooks.

**Steps:**

1.  **Create a Meta Developer Account:**
    *   Go to [Meta for Developers](https://developers.facebook.com/) and create an account or log in with your existing Facebook account.

2.  **Create a New App:**
    *   In the Meta Developer portal, click "Create App".
    *   Choose "For your business" and click "Next".
    *   Select "None" for app type and click "Next".
    *   Enter an "App Display Name" (e.g., "Instagram Bot Example App") and click "Create App".

3.  **Connect Instagram App:**
    *   Once your app is created, you'll be taken to the App Dashboard.
    *   Look for the "Add Products" section or find "Products" in the left-hand menu and click "Add Product".
    *   Find "Instagram" and click "Set up".
    *   Choose "Basic Setup" and click "Set Up Webhooks".

4.  **Configure Instagram Webhooks:**
    *   In the Instagram Product settings, navigate to "Webhooks".
    *   Click "Subscribe to Events".
    *   **Callback URL:**  You'll need to provide this later, once your server is deployed. For now, you can use a placeholder URL like `https://your-deployment-url.com/webhook` (you will replace `your-deployment-url.com` with your actual server URL in the next step). Example placeholder: `https://insta-bot-service.onrender.com/webhook`
    *   **Verify Token:** Enter a secret token. **Important:**  Copy and securely store this token. You will need to set this as the `VERIFY_TOKEN` environment variable in your server.  A strong, random string is recommended. Example: `YOUR_VERY_SECRET_VERIFY_TOKEN_STRING`
    *   **Subscription Fields:** Select the following fields:
        *   `messages`
        *   `comments`
        *   `comment_likes`
    *   Click "Verify and Save". The verification will likely fail at this stage because your server isn't running yet at the provided Callback URL.  Don't worry, we'll revisit this after deployment.

5.  **Get App Secret:**
    *   In your App Dashboard, navigate to "App Settings" -> "Basic".
    *   Find the "App Secret" field. Click "Show" and copy your App Secret. **Important:** Store this securely. You will set this as the `APP_SECRET` environment variable. Example Placeholder: `YOUR_META_APP_SECRET_EXAMPLE`

6.  **Connect Instagram Professional Account and Obtain Access Token:**
    *   In the Instagram Product settings, navigate to "Basic Settings".
    *   Scroll down to "Instagram Accounts".
    *   Click "Add or Remove Instagram Testers" if you are in development mode, or directly "Add Instagram Account" if you are ready to connect your production account. Follow the prompts to connect your Instagram Professional account.
    *   Once connected, you'll see your Instagram account listed. Click "Generate Access Token".
    *   Select the Instagram account you just connected and the permissions `instagram_basic`, `instagram_manage_messages`, `instagram_manage_comments`.
    *   Click "Generate Token". **Important:** Copy and securely store this Access Token. You will need to configure this in the `ACCOUNTS` environment variable.  Note that these tokens are usually short-lived for testing and you'll need to use the Meta Graph API to generate long-lived tokens for production. For this guide and initial setup, a short-lived token is sufficient for testing. Example Placeholder: `YOUR_INSTAGRAM_ACCESS_TOKEN_EXAMPLE`
    *   **Get Instagram Account ID (Numeric ID):**  In the "Instagram Accounts" section, you'll see your connected account. Note down the numeric "Instagram ID" displayed. You will need this for the `INSTAGRAM_ACCOUNT_ID` and `ACCOUNTS` environment variables. Example: `123456789012345`

**Keep these values safe:**

*   **App Secret** (`APP_SECRET` environment variable) - Example: `YOUR_META_APP_SECRET_EXAMPLE`
*   **Verify Token** (`VERIFY_TOKEN` environment variable) - Example: `YOUR_VERY_SECRET_VERIFY_TOKEN_STRING`
*   **Instagram Access Token(s)** (Part of the `ACCOUNTS` environment variable) - Example: `YOUR_INSTAGRAM_ACCESS_TOKEN_EXAMPLE`
*   **Instagram Account ID(s)** (Used in `INSTAGRAM_ACCOUNT_ID` and `ACCOUNTS` environment variables) - Example: `123456789012345`

### 2. Webhook Server and Hosting (Render Example)

This section demonstrates deploying the webhook server on Render, a platform-as-a-service, and using Render's Redis instance (or in-memory for simplicity).  The steps are generally applicable to other platforms like Azure, but specific platform configurations will vary.

**Steps for Render:**

1.  **Prepare your Repository for Render:**
    *   Ensure your project repository includes:
        *   Your FastAPI application code (`main.py` or similar).
        *   `requirements.txt` file listing dependencies.
        *   `.env` file (initially, you can leave placeholders for environment variables).
        *   `Procfile` in the root directory to tell Render how to run your app and Celery worker. Create a `Procfile` with the following content:

            ```
            web: uvicorn main:app --host 0.0.0.0 --port $PORT
            worker: celery -A main worker --loglevel=info
            ```
            *(Adjust `main:app` if your FastAPI app is defined differently)*

2.  **Deploy to Render:**
    *   Sign up or log in to [Render](https://render.com/).
    *   Connect your GitHub/GitLab repository to Render.
    *   Create a new Web Service on Render, pointing to your repository.
    *   **Environment:** Choose Python.
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:**  Leave this blank as it's defined in the `Procfile`.
    *   **Instance Type:** Choose a suitable instance type (e.g., Free or Starter for testing).
    *   Click "Create Web Service".

3.  **(Optional but Recommended for Production) Set up Render Redis:**
    *   In your Render dashboard, create a new Redis instance. Render provides managed Redis.
    *   Once created, Render will provide a Redis connection URL (e.g., `redis://render-redis.example.com:6379`).
    *   In your Render Web Service settings (the one you created in step 2), go to "Environment".
    *   Add two environment variables:
        *   `CELERY_BROKER_URL`: Set the value to the Redis connection URL from Render. Example: `redis://render-redis.example.com:6379`
        *   `CELERY_RESULT_BACKEND`: Set the value to the same Redis connection URL. Example: `redis://render-redis.example.com:6379`
    *   **If you want to use In-Memory Broker/Backend (for testing/simplicity):** You can skip setting up Render Redis and leave `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` environment variables unset or set them to `memory://` and `cache+memory://` respectively in your Render environment variables (as defined in your code defaults).

4.  **Get your Render Deployment URL:**
    *   After Render finishes deploying your Web Service, it will provide a live URL (e.g., `insta-bot-service.onrender.com`). **Copy this URL.** This is your server's base URL. Example: `https://insta-bot-service.onrender.com`

5.  **Update Meta Webhook Callback URL:**
    *   Go back to your Meta Developer App, Instagram Webhook settings (from Section 1, Step 4).
    *   **Callback URL:** Replace the placeholder with your Render deployment URL, appending `/webhook` at the end. For example: `https://insta-bot-service.onrender.com/webhook`.
    *   **Verify Token:** Ensure the "Verify Token" is still the same value you set earlier (Example: `YOUR_VERY_SECRET_VERIFY_TOKEN_STRING`).
    *   Click "Verify and Save". This time, the verification should succeed because your server is now running and accessible at the Callback URL.

**Azure Hosting Notes (Simplified - In-Memory Focus):**

For Azure, you would typically use Azure App Service to host your FastAPI application and Azure Cache for Redis for a production-ready Celery broker/backend.  Setting up Azure resources often involves configuring Virtual Networks (VNets) and Network Address Translation (NAT) Gateways, especially when you want to securely connect Azure App Service to Azure Cache for Redis within a VNet.

However, for initial setup and if you are using the **in-memory broker/backend**, you can simplify Azure deployment by:

1.  Deploying your FastAPI app to Azure App Service using Docker or code deployment.
2.  Setting environment variables in Azure App Service configuration.
3.  Forgoing Azure Cache for Redis initially and relying on the in-memory broker/backend, as configured in your code.

For production in Azure, setting up Azure Cache for Redis and properly configuring VNet integration for security and performance is highly recommended. Consult Azure documentation for detailed steps on setting up Azure App Service and Azure Cache for Redis with VNet integration.

### 3. Environment Variable Configuration

Now, let's configure the necessary environment variables for your application. You will set these in your hosting platform's environment settings (e.g., Render Environment variables, Azure App Service Application settings).

**Environment Variables to Set:**

*   **`APP_SECRET`**:  Your Meta App Secret (obtained in Section 1, Step 5). Example: `YOUR_META_APP_SECRET_EXAMPLE`
*   **`VERIFY_TOKEN`**: The Verify Token you defined in Section 1, Step 4. Example: `YOUR_VERY_SECRET_VERIFY_TOKEN_STRING`
*   **`GEMINI_API_KEY`**: Your Google Gemini API Key.  Obtain this from Google Cloud Console after enabling the Gemini API. If you don't intend to use the Gemini LLM, you can still set this, or the bot will use default responses. Example: `AIzaSy...YOUR_GEMINI_API_KEY...abc123`
*   **`INSTAGRAM_ACCOUNT_ID`**: Your primary Instagram Business Account ID (numeric ID, obtained in Section 1, Step 6). Example: `123456789012345`
*   **`ACCOUNTS`**:  A JSON string defining your Instagram account credentials.  Format this as follows, replacing placeholders with your actual values (obtained in Section 1, Step 6):

    ```json
    {
      "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID_1": "YOUR_INSTAGRAM_ACCESS_TOKEN_1",
      "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID_2": "YOUR_INSTAGRAM_ACCESS_TOKEN_2"
      // ... add more accounts if needed
    }
    ```
    **Example:** If your Instagram Account ID is `123456789012345` and your Access Token is `EAA...XYZ`, and you have another account with ID `987654321098765` and token `EBB...ABC`, you would set `ACCOUNTS` to:

    ```json
    {"123456789012345": "YOUR_INSTAGRAM_ACCESS_TOKEN_EXAMPLE", "987654321098765": "EBB...ABC"}
    ```
    If you have multiple accounts, add them as key-value pairs in the JSON. Ensure the JSON is valid.

*   **(Optional, if using Render Redis or similar):**
    *   `CELERY_BROKER_URL`:  Redis connection URL (e.g., from Render Redis). Example: `redis://render-redis.example.com:6379`
    *   `CELERY_RESULT_BACKEND`: Redis connection URL (e.g., from Render Redis). Example: `redis://render-redis.example.com:6379`

**Setting Environment Variables on Render (Example):**

1.  In your Render Web Service dashboard, go to "Environment".
2.  Click "Add Environment Variable".
3.  Enter the variable name (e.g., `APP_SECRET`) and its corresponding value (e.g., `YOUR_META_APP_SECRET_EXAMPLE`).
4.  Repeat for all required environment variables.
5.  Render will automatically redeploy your service when you update environment variables.

**Setting Environment Variables on Azure App Service (Example):**

1.  In your Azure portal, navigate to your App Service.
2.  Go to "Configuration" under "Settings" in the left-hand menu.
3.  Click "New application setting".
4.  Enter the variable name (e.g., `APP_SECRET`) and its value (e.g., `YOUR_META_APP_SECRET_EXAMPLE`).
5.  Click "OK".
6.  Repeat for all required environment variables.
7.  Click "Save" at the top of the Configuration blade. Azure App Service will typically restart your app after configuration changes.

### 4. Finalizing Setup and Running the Bot

1.  **Install NLTK VADER Lexicon:** After deploying your server, you may need to run the NLTK download command.  If you are using Render, you can use the Render Shell feature connected to your deployed service to run:

    ```bash
    python -c "import nltk; nltk.download('vader_lexicon')"
    ```
    For Azure App Service, you might need to include this download step in your Dockerfile if you are using Docker deployment, or ensure it runs during your deployment process.  If you are deploying directly from code to Azure App Service, you might be able to run this command via the Kudu console or SSH into your App Service instance (if enabled).

2.  **Access API Documentation:** Once your application is deployed and running on your chosen platform, you can access the API documentation at `/docs` and `/redoc` endpoints of your deployment URL (e.g., `https://insta-bot-service.onrender.com/docs`).

3.  **Test Webhooks:** Trigger webhook events from Instagram (e.g., send a DM or comment on your connected Instagram account). Monitor your server logs (Render logs, Azure App Service logs) and the SSE endpoint (`/events` - e.g., `https://insta-bot-service.onrender.com/events`) to see if events are being received and processed.

4.  **Health Checks:** Use the `/ping` and `/health` endpoints of your deployment URL (e.g., `https://insta-bot-service.onrender.com/ping` and `https://insta-bot-service.onrender.com/health`) to check the health and uptime of your server.

## Usage

Once set up, the bot will automatically process incoming DMs and comments to your connected Instagram account(s) based on the configured logic.

*   **Direct Messages:** Send a DM to your Instagram Business account. The bot will respond after a delay.
*   **Comments:** Comment on a post on your Instagram Business account. The bot will reply after a delay.
*   **Monitor Events:** Access the SSE stream at `/events` to see real-time webhook events. Example: `https://insta-bot-service.onrender.com/events`

## Customization

*   **Default Responses:** You can modify the default positive and negative responses for DMs and comments in the `main.py` file by changing the `default_dm_response_positive`, `default_dm_response_negative`, `default_comment_response_positive`, and `default_comment_response_negative` variables.
*   **Language Model Prompts:** Customize the system prompt for the Google Gemini model by editing the `collection_system_prompt/system_prompt.txt` file. You can tailor this prompt to guide the LLM to generate responses that better align with your brand voice and communication style.
*   **Sentiment Analysis Threshold:** Adjust the sentiment threshold in the `analyze_sentiment` function in `main.py` to fine-tune how sentiment is classified (Positive/Negative).
*   **Response Delays:** Modify the `random.randint()` values in the webhook handler in `main.py` to change the delay ranges for DM and comment responses.
*   **Celery Configuration:** For production deployments, it is **strongly recommended** to replace the in-memory Celery broker and backend with a more robust solution like Redis or RabbitMQ. Configure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` environment variables accordingly to point to your Redis or RabbitMQ setup.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1.  Fork the repository from [https://github.com/InstaBotDev/instagram-auto-bot](https://github.com/InstaBotDev/instagram-auto-bot).
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/your-bugfix-name`.
3.  Make your changes and commit them: `git commit -m "Add your descriptive commit message"`.
4.  Push your changes to your fork: `git push origin feature/your-feature-name`.
5.  Submit a pull request to the main repository.

Please ensure your code adheres to PEP 8 style guidelines and includes appropriate tests if applicable.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For questions, issues, or feature requests, please [open an issue](https://github.com/InstaBotDev/instagram-auto-bot/issues) on GitHub.

**Disclaimer:** This bot is intended for automation and engagement purposes on Instagram. Please use it responsibly and in compliance with Instagram's terms of service and community guidelines. Avoid excessive automation or spam-like behavior that could violate Instagram's policies.