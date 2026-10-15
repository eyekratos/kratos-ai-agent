# Kratos AI Agent — YouTube Script MVP

A beginner-friendly first milestone for a cloud-run YouTube workflow:
- Generate a YouTube script from a topic.
- Run manually or on a daily GitHub Actions schedule.
- Download the script as a GitHub Actions artifact.
- Keep API keys in GitHub Secrets, never in source code.

## 1. Create the repository

Create a **private** GitHub repository named `kratos-ai-agent`, then upload all files in this folder while preserving the directory structure.

## 2. Add the Gemini API key

Create a key in Google AI Studio: https://aistudio.google.com/

In GitHub, open:
`Settings → Secrets and variables → Actions → New repository secret`

Name it `GEMINI_API_KEY` and paste the key as the value. Do not put the key in code or commit it.

## 3. Run a workflow

Open `Actions → YouTube Script Pipeline → Run workflow`, enter a topic, then run it. On success, download the `youtube-script` artifact from the workflow run.

The workflow is also scheduled daily for 7:00 PM India time (GitHub may delay scheduled runs).

## 4. Run locally (optional)

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GEMINI_API_KEY="YOUR_API_KEY"
python -m app.main --topic "Why compounding matters"
```

The script is saved to `output/script.txt`.

## Current scope

This is the first working milestone only. It does **not** yet generate voice, render full videos, create thumbnails, upload to YouTube, or provide phone control. Those need separate modules, cloud storage, OAuth/API configuration, and additional deployment steps. Free API/compute quotas and model availability can change.
