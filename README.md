# Kratos — YouTube Studio

A Streamlit app for YouTube research, original script writing, and AI thumbnail generation. It never uploads or publishes videos.

## Features
- Generate an original script, titles, description, tags, hashtags, pinned comment and content calendar using the OpenAI API.
- Generate a downloadable AI thumbnail PNG using the OpenAI Images API.
- Optionally search public YouTube video metadata and sort by a rough views/day signal with YouTube Data API v3.
- Download the script/content package as Markdown.

## Deploy on Streamlit Community Cloud
1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Select repository `eyekratos/kratos-ai-agent`, branch `main`, main file `app.py`.
3. Deploy the app or open the existing deployment and wait for it to install the updated requirements.
4. In app Settings → Secrets, add:
```toml
OPENAI_API_KEY = "your-openai-api-key"
YOUTUBE_API_KEY = "your-youtube-data-api-key"
```
The YouTube key is optional. You can also enter keys in the app sidebar for the current session. Never commit keys to GitHub or share them in chat.

## API keys and billing
- OpenAI API key: https://platform.openai.com/api-keys
- OpenAI API billing/usage: https://platform.openai.com/settings/organization/billing/overview
- YouTube Data API v3 (optional): enable at https://console.cloud.google.com/apis/library/youtube.googleapis.com, then create a key at https://console.cloud.google.com/apis/credentials.

**Important:** ChatGPT subscriptions and OpenAI API billing are separate. API access, model availability and image generation may require an API billing method and are usage-billed. Check current pricing and limits before generating images.

## Local run (optional)
Python 3.10+:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Limits
- Views/day is only a rough signal, not a reliable virality prediction.
- The app cannot access private competitor analytics.
- Video scripts and generated thumbnails should be reviewed before use.
- This app does not upload or publish content automatically.
