# Kratos — YouTube Scout (Free-first)

A local-first YouTube research and script-planning app. AI generation uses Ollama on your own computer, so no paid AI API key is required.

## What it does
- Searches public YouTube video metadata through YouTube Data API v3.
- Sorts found videos by a rough views-per-day signal.
- Uses your local Ollama model to create original ideas, scripts, title/thumbnail concepts, metadata, and a two-week publishing plan.
- Exports the output as Markdown.

## What you need
- Python 3.10+
- A free YouTube Data API key (Google Cloud Console; enable YouTube Data API v3; subject to daily quota)
- Ollama installed locally with a model downloaded (the app default is `qwen3:4b`)
- Internet connection for YouTube public data; AI generation runs locally

## Windows setup
1. Install Ollama from https://ollama.com/ and start it.
2. In a terminal, download a model if needed:
```powershell
ollama pull qwen3:4b
```
3. Create a YouTube API key at https://console.cloud.google.com/ after enabling YouTube Data API v3.
4. In PowerShell, from this repository folder:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
streamlit run app.py
```
5. Open the local URL printed by Streamlit. In the sidebar, keep Ollama URL as `http://localhost:11434` and choose the model you downloaded.

## Free hosting
You can try Streamlit Community Cloud, but its hosted server cannot normally reach Ollama running on your personal laptop at `localhost`. For the fully free local-AI setup, run Streamlit on your own computer. Cloud hosting with local AI requires a separately reachable inference service and may not be free.

## Important limits
- YouTube API has quotas; search quota can be exhausted.
- Views/day is a rough signal, not a true virality score.
- No script can guarantee virality.
- This MVP does not upload videos to YouTube or read private channel analytics.
- Never commit API keys to GitHub. Competitor content is for research; publish original scripts and licensed visuals.
