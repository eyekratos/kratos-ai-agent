# Kratos — YouTube Scout

A browser-based YouTube research and content-drafting app. No Ollama or local AI installation is needed. Gemini generates original ideas and scripts; YouTube Data API v3 is optional and adds live public-video research.

## Features
- Generate original YouTube ideas, scripts, titles, thumbnail concepts, descriptions, hashtags, tags and a two-week content plan with Gemini.
- Optionally search public YouTube video metadata by topic and competitor hints.
- Sort returned videos by a rough views/day signal.
- Download the generated strategy and script as Markdown.
- **Drafting only:** this app never uploads or publishes videos automatically.

## Deploy on Streamlit Community Cloud
1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Select repository `eyekratos/kratos-ai-agent`, branch `main`, main file `app.py`.
3. Deploy the app.
4. In the app's settings → Secrets, add your Gemini key:
```toml
GEMINI_API_KEY = "your-gemini-api-key"
```
5. Optional: add a YouTube Data API key to enable live video research:
```toml
YOUTUBE_API_KEY = "your-youtube-data-api-key"
```

You can also enter keys in the app sidebar for a session. Never commit keys to GitHub or share them in chat.

## API keys
- Gemini: https://aistudio.google.com/apikey — check current free-tier eligibility, region/model access and quotas. No local AI install is required, but free access is not guaranteed and may change.
- YouTube Data API v3 (optional): https://console.cloud.google.com/apis/library/youtube.googleapis.com — enable the API, then create a key at https://console.cloud.google.com/apis/credentials. Public API usage has a quota.

## Local run (optional)
Python 3.10+:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Limits
- Views/day is a rough signal, not a reliable virality prediction.
- The app cannot access private competitor analytics.
- The current version does not render or upload videos automatically.
- Use YouTube Studio Audience analytics for your own channel's best publishing time; generic times are only tests.
- Respect copyright; use competitor videos for research and create original scripts.
