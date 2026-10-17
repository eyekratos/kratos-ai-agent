import os
from datetime import datetime, timezone
from collections import Counter
import streamlit as st
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Scout", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Scout")
st.caption("Competitor research • trend signals • original scripts • publishing planner")

with st.sidebar:
    st.header("Setup")
    yt_key = st.text_input("YouTube Data API key", value=os.getenv("YOUTUBE_API_KEY", ""), type="password")
    gemini_key = st.text_input("Gemini API key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"], index=0)
    st.caption("Keys are used for this session only. For deployment, set them as platform secrets.")

def youtube_client():
    if not yt_key:
        st.error("Add a YouTube Data API key in the sidebar. Create one in Google Cloud Console and enable YouTube Data API v3.")
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
        s, stt = v["snippet"], v.get("statistics", {})
        views = int(stt.get("viewCount", 0))
        published = s.get("publishedAt", "")
        age_days = max((datetime.now(timezone.utc) - datetime.fromisoformat(published.replace("Z","+00:00"))).days, 1) if published else 1
        rows.append({"title": s.get("title",""), "channel": s.get("channelTitle",""), "published": published[:10], "views": views, "likes": int(stt.get("likeCount",0)), "comments": int(stt.get("commentCount",0)), "views_per_day": round(views/age_days), "url": "https://www.youtube.com/watch?v="+v["id"], "description": s.get("description","")[:700]})
    return sorted(rows, key=lambda x:x["views_per_day"], reverse=True)

def ask_gemini(prompt):
    if not gemini_key:
        st.error("Add a Gemini API key in the sidebar.")
        st.stop()
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text or "No text returned."

topic = st.text_input("Your niche / topic", placeholder="e.g. AI tools for students, personal finance, smartphone reviews")
competitors = st.text_input("Competitor channel names (optional, comma-separated)", placeholder="e.g. Creator A, Creator B")
col1, col2, col3 = st.columns(3)
with col1: count = st.selectbox("Videos to research", [10, 20, 30, 50], index=1)
with col2: goal = st.selectbox("Video format", ["YouTube long-form", "YouTube Shorts", "Both"])
with col3: duration = st.selectbox("Target duration", ["30–45 seconds", "60 seconds", "5–8 minutes", "8–12 minutes"])
if "research" not in st.session_state: st.session_state.research = []
if st.button("🔎 Find competitors & video opportunities", type="primary", disabled=not topic.strip()):
    try:
        with st.spinner("Searching public YouTube video metadata..."):
            st.session_state.research = search_videos(topic, count)
        st.success(f"Found {len(st.session_state.research)} videos. Rankings are signals, not a guarantee of virality.")
    except HttpError as e:
        st.error(f"YouTube API error: {e}")
    except Exception as e:
        st.error(f"Research failed: {e}")

rows = st.session_state.research
if rows:
    st.subheader("Video opportunity board")
    st.dataframe([{k:v for k,v in x.items() if k not in ("description",)} for x in rows], use_container_width=True, hide_index=True,
                 column_config={"url": st.column_config.LinkColumn("Video link"), "views": st.column_config.NumberColumn(format="%d"), "views_per_day": st.column_config.NumberColumn("Views/day", format="%d")})
    st.subheader("What might be working?")
    winners = rows[:min(10,len(rows))]
    evidence = "\n".join(f"- {x['title']} | channel={x['channel']} | views={x['views']} | views/day={x['views_per_day']} | published={x['published']} | url={x['url']}" for x in winners)
    if st.button("🧠 Analyse patterns & generate an original script"):
        prompt = f"""You are a YouTube strategist. User niche/topic: {topic}. Format: {goal}. Target duration: {duration}. Output language: {language}. Audience country: {region}.
Analyze these public video metadata signals. Do not claim views prove causation or guarantee virality. Identify repeated topic angles, title/curiosity patterns, freshness and opportunity gaps. Do not copy titles/scripts verbatim; create an original concept.
DATA:
{evidence}
Return:
1) concise competitor landscape and strongest evidence
2) 5 original video ideas ranked by opportunity, each with why now, audience, and a non-guaranteed score out of 10
3) best idea and a compelling but honest title (3 alternatives), thumbnail concept and 3-5 word thumbnail text
4) a complete original script for {duration}, with timestamped beats, hook in first 5 seconds, open loops, examples, retention resets, and clear CTA; avoid fabricated facts and mark claims requiring verification
5) description, chapters (for long-form), hashtags/tags, pinned comment
6) 2-week publishing plan and suggested test slots in {region} local time. Explain these are starting hypotheses; recommend using the creator's YouTube Studio 'When your viewers are on YouTube' report for personalized timing.
7) measurement plan: CTR, first 30-sec retention, average view duration, returning viewers; explain how to iterate after 48 hours.
"""
        with st.spinner("Generating strategy and script..."):
            st.session_state.analysis = ask_gemini(prompt)
    if "analysis" in st.session_state:
        st.markdown(st.session_state.analysis)
        st.download_button("⬇️ Download strategy & script", st.session_state.analysis, file_name="kratos_youtube_strategy.md", mime="text/markdown")
else:
    st.info("Enter a niche or topic and run research. Public search metadata is used; this MVP does not access private analytics or guarantee viral results.")

st.divider()
st.subheader("Publishing-time guidance")
st.write("Use YouTube Studio → Analytics → Audience → “When your viewers are on YouTube” as your primary timing signal. If you have no audience data yet, test 2–3 consistent slots for two weeks, then compare impressions, click-through rate and retention. No universal upload time guarantees reach.")
st.caption("Respect platform terms and copyright. Use competitor videos for research only; write original scripts and use licensed media.")
