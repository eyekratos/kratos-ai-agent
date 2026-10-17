import os
from datetime import datetime, timezone
import streamlit as st
from google import genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Scout", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Scout")
st.caption("Competitor research • original scripts • thumbnail concepts • publishing planner")

with st.sidebar:
    st.header("Free API setup")
    yt_key = st.text_input("YouTube Data API key", value=os.getenv("YOUTUBE_API_KEY", ""), type="password")
    gemini_key = st.text_input("Gemini API key (free tier, if available)", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"])
    st.caption("No local AI installation. API free-tier availability, limits and model access can change.")

def youtube_client():
    if not yt_key:
        st.error("Enter a YouTube Data API key in the sidebar. Enable YouTube Data API v3 in Google Cloud Console.")
        st.stop()
    return build("youtube", "v3", developerKey=yt_key, cache_discovery=False)

def search_videos(query, max_results=20):
    yt = youtube_client()
    response = yt.search().list(part="snippet", q=query, type="video", maxResults=max_results, order="viewCount", regionCode=region, relevanceLanguage="en").execute()
    ids = [x["id"]["videoId"] for x in response.get("items", [])]
    if not ids:
        return []
    details = yt.videos().list(part="snippet,statistics", id=",".join(ids)).execute()
    rows = []
    for v in details.get("items", []):
        s, stats = v["snippet"], v.get("statistics", {})
        views = int(stats.get("viewCount", 0))
        published = s.get("publishedAt", "")
        age_days = max((datetime.now(timezone.utc) - datetime.fromisoformat(published.replace("Z","+00:00"))).days, 1) if published else 1
        rows.append({"title": s.get("title",""), "channel": s.get("channelTitle",""), "published": published[:10], "views": views, "likes": int(stats.get("likeCount",0)), "comments": int(stats.get("commentCount",0)), "views_per_day": round(views/age_days), "url": "https://www.youtube.com/watch?v="+v["id"]})
    return sorted(rows, key=lambda x:x["views_per_day"], reverse=True)

def ask_gemini(prompt):
    if not gemini_key:
        st.error("Enter a Gemini API key. Check Google AI Studio for current free-tier availability and limits.")
        st.stop()
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text or "No text returned."

topic = st.text_input("Your niche / topic", placeholder="e.g. AI tools, finance, smartphone reviews")
competitors = st.text_input("Competitor channel names (optional)", placeholder="Creator A, Creator B")
c1, c2, c3 = st.columns(3)
with c1: count = st.selectbox("Videos to research", [10, 20, 30, 50], index=1)
with c2: fmt = st.selectbox("Video format", ["YouTube Shorts", "Long-form", "Both"], index=2)
with c3: duration = st.selectbox("Target duration", ["30–45 seconds", "60 seconds", "5–8 minutes", "8–12 minutes"], index=2)
if "research" not in st.session_state: st.session_state.research = []
if st.button("🔎 Find competitors & opportunities", type="primary", disabled=not topic.strip()):
    try:
        with st.spinner("Searching public YouTube metadata..."):
            query = topic + (" " + competitors if competitors.strip() else "")
            st.session_state.research = search_videos(query, count)
        st.success(f"Found {len(st.session_state.research)} videos.")
    except HttpError as e:
        st.error(f"YouTube API error: {e}")
    except Exception as e:
        st.error(f"Research failed: {e}")

rows = st.session_state.research
if rows:
    st.subheader("Video opportunity board")
    st.dataframe(rows, use_container_width=True, hide_index=True, column_config={"url": st.column_config.LinkColumn("Video link"), "views": st.column_config.NumberColumn(format="%d"), "views_per_day": st.column_config.NumberColumn("Views/day", format="%d")})
    evidence = "\n".join(f"- {x['title']} | channel={x['channel']} | views={x['views']} | views/day={x['views_per_day']} | published={x['published']} | url={x['url']}" for x in rows[:10])
    if st.button("🧠 Generate strategy and original script"):
        prompt = f"""Act as an evidence-conscious YouTube strategist. Topic/niche: {topic}. Competitor hints: {competitors or 'discover from results'}. Format: {fmt}. Target duration: {duration}. Script language: {language}. Audience region: {region}.
Use public metadata as imperfect signals only; never promise virality or claim views prove causation. Do not copy other creators' scripts. Produce original ideas.
VIDEO DATA:
{evidence}
Return: (1) competitor landscape and evidence-backed patterns; (2) five original video ideas ranked by opportunity, why, audience, score /10 with caveat; (3) best idea, three honest titles, thumbnail concept and 3-5 word thumbnail text; (4) complete original timestamped script for {duration}, first-five-second hook, open loops, examples, retention resets and CTA, flag facts to verify; (5) description, chapters if long-form, tags, hashtags, pinned comment; (6) two-week publishing plan with suggested test slots in {region} local time and explain these are hypotheses; (7) metrics to check after 48 hours: CTR, first 30-second retention, average view duration and returning viewers.
"""
        try:
            with st.spinner("Generating script..."):
                st.session_state.analysis = ask_gemini(prompt)
        except Exception as e:
            st.error(f"AI generation failed. Check API key, quota and model availability: {e}")
    if "analysis" in st.session_state:
        st.markdown(st.session_state.analysis)
        st.download_button("⬇️ Download strategy & script", st.session_state.analysis, file_name="kratos_youtube_strategy.md", mime="text/markdown")
else:
    st.info("Enter a topic and search. This tool uses public YouTube video metadata; it does not access private analytics.")

st.divider()
st.subheader("Publishing-time guidance")
st.write("Use YouTube Studio → Analytics → Audience → “When your viewers are on YouTube” as your main timing signal. If you have no audience data, test 2–3 consistent slots for two weeks and compare CTR and retention.")
st.caption("This MVP researches and drafts; it does not automatically upload videos. Free quotas and hosting limits apply. Original scripts and licensed media are recommended.")
