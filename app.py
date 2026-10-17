import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Scout", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Scout")
st.caption("Free-first • Competitor research • Original scripts • Publishing planner")

with st.sidebar:
    st.header("Free setup")
    yt_key = st.text_input("YouTube Data API key (free quota)", value=os.getenv("YOUTUBE_API_KEY", ""), type="password")
    ollama_url = st.text_input("Local Ollama URL", value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model = st.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", "qwen3:4b"))
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"], index=0)
    st.caption("No paid AI API is required. Ollama must be running on the same computer as this app.")

def youtube_client():
    if not yt_key:
        st.error("Add a YouTube Data API key. It has a free quota; enable YouTube Data API v3 in Google Cloud Console.")
        st.stop()
    return build("youtube", "v3", developerKey=yt_key, cache_discovery=False)

def search_videos(query, max_results=20):
    yt = youtube_client()
    response = yt.search().list(part="snippet", q=query, type="video", maxResults=max_results, order="viewCount", regionCode=region, relevanceLanguage="en").execute()
    ids = [x["id"]["videoId"] for x in response.get("items", [])]
    if not ids:
        return []
    details = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
    rows = []
    for v in details.get("items", []):
        s, stats = v["snippet"], v.get("statistics", {})
        views = int(stats.get("viewCount", 0))
        published = s.get("publishedAt", "")
        age_days = max((datetime.now(timezone.utc) - datetime.fromisoformat(published.replace("Z","+00:00"))).days, 1) if published else 1
        rows.append({"title": s.get("title",""), "channel": s.get("channelTitle",""), "published": published[:10], "views": views, "likes": int(stats.get("likeCount",0)), "comments": int(stats.get("commentCount",0)), "views_per_day": round(views/age_days), "url": "https://www.youtube.com/watch?v="+v["id"]})
    return sorted(rows, key=lambda x:x["views_per_day"], reverse=True)

def ask_local_ollama(prompt):
    url = ollama_url.rstrip("/") + "/api/generate"
    payload = json.dumps({"model": ollama_model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "").strip() or "Local model returned no text."
    except urllib.error.URLError as e:
        raise RuntimeError("Could not connect to Ollama. Start Ollama first and verify the model is installed. Details: " + str(e))

topic = st.text_input("Your niche / topic", placeholder="e.g. AI tools for students, personal finance, smartphone reviews")
competitors = st.text_input("Competitor channel names (optional; used as research hints)", placeholder="e.g. Creator A, Creator B")
col1, col2, col3 = st.columns(3)
with col1: count = st.selectbox("Videos to research", [10, 20, 30, 50], index=1)
with col2: goal = st.selectbox("Video format", ["YouTube long-form", "YouTube Shorts", "Both"])
with col3: duration = st.selectbox("Target duration", ["30–45 seconds", "60 seconds", "5–8 minutes", "8–12 minutes"])
if "research" not in st.session_state: st.session_state.research = []
if st.button("🔎 Find competitors & video opportunities", type="primary", disabled=not topic.strip()):
    try:
        with st.spinner("Searching public YouTube video metadata..."):
            search_query = topic + (" " + competitors if competitors.strip() else "")
            st.session_state.research = search_videos(search_query, count)
        st.success(f"Found {len(st.session_state.research)} videos. These are research signals, not a guarantee of virality.")
    except HttpError as e:
        st.error(f"YouTube API error: {e}")
    except Exception as e:
        st.error(f"Research failed: {e}")

rows = st.session_state.research
if rows:
    st.subheader("Video opportunity board")
    st.dataframe(rows, use_container_width=True, hide_index=True,
        column_config={"url": st.column_config.LinkColumn("Video link"), "views": st.column_config.NumberColumn(format="%d"), "views_per_day": st.column_config.NumberColumn("Views/day", format="%d")})
    winners = rows[:min(10, len(rows))]
    evidence = "\n".join(f"- {x['title']} | channel={x['channel']} | views={x['views']} | views/day={x['views_per_day']} | published={x['published']} | url={x['url']}" for x in winners)
    if st.button("🧠 Analyse patterns & generate original script"):
        prompt = f"""You are an evidence-conscious YouTube strategist. Niche/topic: {topic}. Competitor hints: {competitors or 'discover from results'}. Format: {goal}. Target duration: {duration}. Output language: {language}. Audience country: {region}.
Use the supplied public video metadata as limited signals, not proof of causation. Do not promise virality. Do not copy any creator's script or reproduce their distinctive expression. Generate original concepts.
DATA:
{evidence}
Provide:
1. competitor landscape and evidence-backed patterns
2. five original video ideas ranked by opportunity, with audience, angle and a non-guaranteed score /10
3. best idea, three honest clickable titles, thumbnail concept and 3-5 word thumbnail text
4. a complete original script for {duration}, timestamped beats, hook in first 5 seconds, open loops, examples, retention resets and CTA; flag claims needing fact-checking
5. description, chapters if long-form, tags/hashtags and pinned comment
6. two-week publishing plan with suggested test slots in {region} local time. Explain these are hypotheses and YouTube Studio Audience analytics should override generic timing advice.
7. measurement plan for CTR, first 30-second retention, average view duration and returning viewers; what to review after 48 hours.
"""
        try:
            with st.spinner("Generating locally with Ollama; this can take a few minutes..."):
                st.session_state.analysis = ask_local_ollama(prompt)
        except Exception as e:
            st.error(str(e))
    if "analysis" in st.session_state:
        st.markdown(st.session_state.analysis)
        st.download_button("⬇️ Download strategy & script", st.session_state.analysis, file_name="kratos_youtube_strategy.md", mime="text/markdown")
else:
    st.info("Enter a niche/topic and run research. Public YouTube metadata is used; private channel analytics are not accessed.")

st.divider()
st.subheader("Free publishing-time guidance")
st.write("Use YouTube Studio → Analytics → Audience → “When your viewers are on YouTube” as your primary timing signal. Without audience data, test 2–3 consistent slots for two weeks and compare CTR and retention.")
st.caption("This version does not upload videos automatically. It avoids paid AI APIs by generating scripts with your local Ollama model. YouTube API quotas and free hosting limits still apply.")
