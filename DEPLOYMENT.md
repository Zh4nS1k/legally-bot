# Deploying Legally Bot

This bot is a long-running polling application. **Render.com** (as a Background Worker) is the recommended platform. **Vercel** is NOT recommended for polling bots as it is designed for serverless web functions and will time out.

## Option 1: Render.com (Recommended)

Render is ideal because it supports "Background Workers" which keep your bot running 24/7.

### Steps:
1.  **Push your code to GitHub/GitLab**.
2.  **Sign up/Log in to [Render.com](https://dashboard.render.com/)**.
3.  Click **New +** -> **Background Worker**.
4.  Connect your repository.
5.  **Configure**:
    *   **Name**: `legally-bot` (or your choice)
    *   **Region**: Closest to you (e.g., Frankfurt or Oregon)
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `python legally_bot/bot.py`
6.  **Environment Variables**:
    *   Click "Advanced" or "Environment" tab.
    *   Add all variables from your `.env` file (OPEN (DO NOT upload .env file to public repo!)):
        *   `BOT_TOKEN`: `...`
        *   `MONGO_URI`: `...`
        *   `PINECONE_API_KEY`: `...`
        *   `PINECONE_INDEX_NAME`: `...`
        *   `GOOGLE_API_KEY`: `...` (if used)
        *   `GROQ_API_KEY`: `...`
        *   `SMTP_PASSWORD`: `...`
        *   `SMTP_USER`: `...`
7.  **Deploy**. Render will look for `requirements.txt` in the root (which we created) and install dependencies.

> **Note**: The "Background Worker" service on Render is a paid feature (starts at ~$7/month).
> **Free Option**: You can use "Web Service" properly with a dummy web server, but it will sleep after 15 mins of inactivity unless pinged (e.g. by UptimeRobot). Background Worker is much more reliable.

## Option 2: Railway.app (Alternative)

Railway is also excellent for bots.
1.  Login to Railway -> New Project -> Deploy from GitHub.
2.  It will detect `requirements.txt`.
3.  Go to variables and add your `.env` keys.
4.  It should automatically run `python legally_bot/bot.py` if configured, or you can set the Start Command.
5.  Railway gives $5 free credit (one-time or monthly depending on plan status).

## Why not Vercel?
Vercel is for **Websites** and **Serverless Functions**.
*   It kills processes after ~10-60 seconds.
*   `dp.start_polling()` requires an infinite loop, which Vercel will kill.
*   To use Vercel, you must rewrite the bot to use **Webhooks** and split the code into stateless functions, which requires significant refactoring.
