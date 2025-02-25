# Instagram Automation Server Bot

[![Project Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com/your-github-username/your-repo-name)
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
*   **Account Management:** Stores and retrieves Instagram access tokens securely using an SQLite database, allowing for multi-account support (expandable).
*   **Scalable Task Processing:** Utilizes Celery for asynchronous task management, ensuring efficient handling of responses and preventing blocking the main API server.
*   **Real-time Event Streaming (SSE):** Provides a Server-Sent Events endpoint (`/events`) to stream webhook events in real-time to connected clients for monitoring and debugging.
*   **Health Monitoring:** Includes `/ping` and `/health` endpoints for server health checks and uptime monitoring.
*   **Configuration via Environment Variables:**  Easily configure sensitive information (API keys, tokens) using a `.env` file.
*   **Detailed Logging:**  Comprehensive logging for debugging and monitoring bot activity.
*   **Easy Setup:**  Simple installation and configuration process.

## Tech Stack

*   **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (for building the API server)
*   **Asynchronous Task Queue:** [Celery](https://docs.celeryq.dev/en/stable/) (for managing background tasks like sending responses)
*   **Language Model (LLM):** [Google Gemini API](https://ai.google.dev/gemini-api) (for generating dynamic DM responses)
*   **Sentiment Analysis:** [NLTK (VADER)](https://www.nltk.org/howto/vader.html) (for sentiment analysis of text)
*   **Database:** [SQLite](https://www.sqlite.org/index.html) (for storing account access tokens - easily replaceable with other databases)
*   **Real-time Communication:** [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) via `sse_starlette`
*   **HTTP Client:** [requests](https://requests.readthedocs.io/en/latest/) (for making API calls to Instagram and Google Gemini)
*   **Environment Management:** [python-dotenv](https://pypi.org/project/python-dotenv/) (for loading environment variables from `.env` file)
*   **Dependency Management:** [pip](https://pip.pypa.io/en/stable/)

## Setup and Installation

Follow these steps to get the Instagram Automation Bot up and running:

1.  **Prerequisites:**
    *   **Python 3.8+:**  Make sure you have Python 3.8 or a later version installed. You can check your Python version by running `python --version` or `python3 --version` in your terminal.
    *   **pip:** Python package installer, usually comes with Python installations.
    *   **Meta Developer Account & App:** You need a Meta Developer account and an Instagram app connected to your Instagram Professional account. Ensure your app has the necessary permissions (e.g., `instagram_basic`, `instagram_manage_messages`, `instagram_manage_comments`).
    *   **Google Cloud Account & Gemini API Key:** To use the Language Model features, you'll need a Google Cloud account and enable the Gemini API to obtain an API key. If you don't want to use the LLM, you can still use the bot with default responses.

2.  **Clone the Repository:**

    ```bash
    git clone https://github.com/your-github-username/your-repo-name.git
    cd your-repo-name
    ```

3.  **Set up Environment Variables:**

    *   Create a `.env` file in the root directory of the project.
    *   Add the following environment variables to your `.env` file, replacing the placeholder values with your actual credentials:

        ```env
        APP_SECRET="YOUR_META_APP_SECRET" # Your Meta App Secret from your Meta Developer App
        VERIFY_TOKEN="YOUR_VERIFY_TOKEN"   # A secret token you define for webhook verification
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY" # Your Google Gemini API Key (optional if not using LLM)
        INSTAGRAM_ACCOUNT_ID="YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID" # Your Instagram Business Account ID (numeric ID)
        ```
        *   **`APP_SECRET`**:  Found in your Meta App settings under "Basic" -> "App Secret".
        *   **`VERIFY_TOKEN`**:  Choose a strong, random string for your verify token. You'll need to use this same token when setting up the webhook in your Meta App.
        *   **`GEMINI_API_KEY`**:  Your API key from Google Cloud for accessing the Gemini API. If you don't intend to use the LLM, you can leave this empty, but the bot will rely solely on default responses.
        *   **`INSTAGRAM_ACCOUNT_ID`**: Your Instagram Business Account ID. This is the numeric ID of your Instagram account.

4.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up NLTK VADER Lexicon:**

    Run the following Python code once to download the necessary NLTK lexicon for sentiment analysis:

    ```bash
    python -c "import nltk; nltk.download('vader_lexicon')"
    ```

6.  **Run Celery Worker:**

    Open a new terminal window and navigate to your project directory. Start the Celery worker to process background tasks:

    ```bash
    celery -A main worker --loglevel=info
    ```
    *(Note: `main` refers to the filename of your FastAPI application if you named it `main.py`. Adjust if your filename is different.)*

7.  **Run FastAPI Application:**

    In another terminal window, navigate to your project directory and start the FastAPI application using uvicorn:

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    *(Again, `main:app` assumes your FastAPI application is in `main.py` and the FastAPI instance is named `app`. Adjust accordingly.)*

    *   `--reload`: Enables automatic code reloading during development. Remove for production.
    *   `--host 0.0.0.0`: Makes the server accessible from outside your local machine.
    *   `--port 8000`: Runs the server on port 8000 (you can change this).

8.  **Access the API Documentation:**

    Once the FastAPI application is running, you can access the automatically generated API documentation at:

    *   [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
    *   [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

    This documentation will help you understand the API endpoints and how to interact with them.

## Usage

1.  **Set up Instagram Webhooks in your Meta App:**

    *   Go to your Meta Developer App Dashboard.
    *   Navigate to your App and then to "Webhooks" -> "Instagram".
    *   Click "Edit Subscription".
    *   **Callback URL:** Enter the URL of your `/webhook` endpoint. If you are running locally and using `uvicorn --host 0.0.0.0`, this would typically be `http://your-public-ip:8000/webhook` or if using a service like ngrok, it would be the ngrok URL followed by `/webhook`. **Important:** For Meta to reach your local server, you'll likely need to use a tool like [ngrok](https://ngrok.com/) to expose your local port to the internet.
    *   **Verify Token:** Enter the `VERIFY_TOKEN` you defined in your `.env` file.
    *   **Subscription Fields:** Select the following fields to subscribe to:
        *   `messages`
        *   `message_deliveries`
        *   `message_reads`
        *   `messaging_postbacks`
        *   `messaging_optins`
        *   `comments`
        *   `feed`
        *   `mentions`
        *   `ratings`
        *   `reactions`
        *   `comment_likes`
        *   `business_account`
    *   Click "Verify and Save". If successful, Meta will verify your webhook endpoint.

2.  **Add Instagram Account Credentials:**

    *   Use the `/accounts` endpoint (POST method) to add or update access tokens for your Instagram accounts. You can use the interactive API documentation at `/docs` or send a POST request using tools like `curl` or Postman.
    *   **Request Body (JSON example):**

        ```json
        {
          "account_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID",
          "access_token": "YOUR_INSTAGRAM_ACCESS_TOKEN"
        }
        ```
        *   **`account_id`**: Your Instagram Business Account ID (numeric ID).
        *   **`access_token`**: The Instagram Access Token for your account. You can generate this token in your Meta Developer App under "Instagram" -> "Basic Permissions" -> "Generate Access Token". Make sure you have granted the necessary permissions to your app for the access token.

3.  **Interact with your Instagram Account:**

    Once the webhook is set up and you've added your account credentials, the bot will automatically start processing incoming DMs and comments.

    *   **Direct Messages:** Send a direct message to your Instagram Business account. The bot will analyze the sentiment and respond after a short delay using the Language Model (if configured) or default responses.
    *   **Comments:** Comment on a post on your Instagram Business account. The bot will analyze the sentiment and reply to your comment after a delay with a default response.

4.  **Monitor Real-time Events (SSE):**

    Open a browser and navigate to the `/events` endpoint: [http://localhost:8000/events](http://localhost:8000/events)

    This endpoint will stream webhook events in real-time as they are received by the server. This is useful for monitoring the bot's activity and debugging.

5.  **Health Checks:**

    *   **Ping:** [http://localhost:8000/ping](http://localhost:8000/ping) - Returns a simple `{"message": "Server is active"}` if the server is running.
    *   **Health:** [http://localhost:8000/health](http://localhost:8000/health) - Provides detailed server health information, including uptime, CPU usage, memory usage, and disk usage.

## Customization

*   **Default Responses:** You can modify the default positive and negative responses for DMs and comments in the `main.py` file by changing the `default_dm_response_positive`, `default_dm_response_negative`, `default_comment_response_positive`, and `default_comment_response_negative` variables.
*   **Language Model Prompts:** Customize the system prompt for the Google Gemini model by editing the `collection_system_prompt/system_prompt.txt` file. You can tailor this prompt to guide the LLM to generate responses that better align with your brand voice and communication style.
*   **Sentiment Analysis Threshold:** Adjust the sentiment threshold in the `analyze_sentiment` function in `main.py` to fine-tune how sentiment is classified (Positive/Negative).
*   **Response Delays:** Modify the `random.randint()` values in the webhook handler in `main.py` to change the delay ranges for DM and comment responses.
*   **Database:** You can easily switch to a different database (e.g., PostgreSQL, MySQL) by modifying the SQLAlchemy database configuration in `main.py`.
*   **Celery Configuration:** For production deployments, you should replace the in-memory Celery broker and backend with a more robust solution like Redis or RabbitMQ. Configure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` accordingly.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/your-bugfix-name`.
3.  Make your changes and commit them: `git commit -m "Add your descriptive commit message"`.
4.  Push your changes to your fork: `git push origin feature/your-feature-name`.
5.  Submit a pull request to the main repository.

Please ensure your code adheres to PEP 8 style guidelines and includes appropriate tests if applicable.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For questions, issues, or feature requests, please [open an issue](https://github.com/your-github-username/your-repo-name/issues) on GitHub.

**Disclaimer:** This bot is intended for automation and engagement purposes on Instagram. Please use it responsibly and in compliance with Instagram's terms of service and community guidelines. Avoid excessive automation or spam-like behavior that could violate Instagram's policies.
