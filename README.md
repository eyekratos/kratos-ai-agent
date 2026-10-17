# Kratos — YouTube Scout

A Streamlit MVP for YouTube competitor discovery, public video metadata research, original script generation, title/thumbnail concepts, and a testable publishing plan.

## Features
- Searches public YouTube videos for a niche/topic using YouTube Data API v3.
- Ranks discovered videos by views/day as a rough freshness/velocity signal (not a true virality prediction).
- Uses Gemini to summarize topic/title patterns and produce original scripts and a 2-week test plan.
- Exports the generated strategy as Markdown.

## Local run (Windows)
1. Install Python 3.11+.
2. Create API keys:
   - YouTube: Google Cloud Console → enable **YouTube Data API v3** → create API key.
   - Gemini: Google AI Studio → create API key.
3. In PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:YOUTUBE_API_KEY="YOUR_YOUTUBE_KEY"
$env:GEMINI_API_KEY="YOUR_GEMINI_KEY"
streamlit run app.py
```
4. Open the local URL Streamlit prints.

## Deploy to Streamlit Community Cloud
1. Push this repository to GitHub.
2. Go to https://share.streamlit.io/ and sign in with GitHub.
3. Choose repository `eyekratos/kratos-ai-agent`, branch `main`, main file `app.py`.
4. In app settings → **Secrets**, add:
```toml
YOUTUBE_API_KEY = "your-youtube-key"
GEMINI_API_KEY = "your-gemini-key"
```
5. Deploy. Do not commit API keys to GitHub.

## Notes and limits
- YouTube search results and API quota limits may vary. Views/day is a simple heuristic, not a normalized performance measure.
- This MVP does not upload videos, access private channel analytics, or promise viral results.
- For best posting-time recommendations, use your own YouTube Studio Audience report. Suggested times are hypotheses to test.
- Competitor content is analyzed for patterns only. Do not copy scripts, thumbnails, or copyrighted footage.
