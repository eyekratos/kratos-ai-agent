# Kratos — YouTube Scout

A browser-based YouTube research and script-planning app. No Ollama or local AI installation is needed. Script generation uses the Gemini API, subject to any free-tier access and current quotas.

## Features
- Search public YouTube video metadata by topic.
- Sort by a rough views/day signal.
- Generate original video ideas, scripts, titles, thumbnail concepts, descriptions and a two-week publishing test plan.
- Download the generated plan as Markdown.

## Deploy on Streamlit Community Cloud
1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Select repository `eyekratos/kratos-ai-agent`, branch `main`, main file `app.py`.
3. Deploy the app.
4. In the app's settings → Secrets, add:
```toml
YOUTUBE_API_KEY = "your-youtube-data-api-key"
GEMINI_API_KEY = "your-gemini-api-key"
```
You can also enter keys in the app sidebar for a session. Never commit keys to GitHub.

## API keys
- YouTube Data API v3: https://console.cloud.google.com/ — enable the API and create a key. Public API usage has a quota.
- Gemini: https://aistudio.google.com/ — check current free-tier eligibility, region/model access and quotas. No local AI install is required, but free access is not guaranteed and may change.

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
- For posting time, use YouTube Studio Audience analytics; generic times are only tests.
- Respect copyright; use competitor videos for research and create original scripts.
