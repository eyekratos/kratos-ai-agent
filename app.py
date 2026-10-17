import os
from datetime import datetime, timezone

import streamlit as st
from google import genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Scout", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Scout")
st.caption("Research • original ideas and scripts • thumbnail concepts • content planner — no auto-posting")

with st.sidebar:
    st.header("API setup")
    yt_key = st.text_input(
        "YouTube Data API key (optional — for live video research)",
        value=os.getenv("YOUTUBE_API_KEY", ""),
        type="password",
        help="Without this key, you can still generate ideas and scripts using Gemini. Live YouTube video metrics require this key.",
    )
    gemini_key = st.text_input(
        "Gemini API key (required)",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
    )
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"])
    st.caption("Never put API keys in source code or public GitHub. Free quotas and model availability can change.")

def youtube_client():
    return build("youtube", "v3", developerKey=yt_key, cache_discovery=False)

def search_videos(query, max_results=20):
    yt = youtube_client()
    response = yt.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
        order="viewCount",
        regionCode=region,
        relevanceLanguage="en",
    ).execute()
    ids = [x["id"]["videoId"] for x in response.get("items", [])]
    if not ids:
        return []
    details = yt.videos().list(part="snippet,statistics", id=",".join(ids)).execute()
    rows = []
    for v in details.get("items", []):
        s, stats = v["snippet"], v.get("statistics", {})
        views = int(stats.get("viewCount", 0))
        published = s.get("publishedAt", "")
        age_days = max(
            (datetime.now(timezone.utc) - datetime.fromisoformat(published.replace("Z", "+00:00"))).days,
            1,
        ) if published else 1
        rows.append({
            "title": s.get("title", ""),
            "channel": s.get("channelTitle", ""),
            "published": published[:10],
            "views": views,
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "views_per_day": round(views / age_days),
            "url": "https://www.youtube.com/watch?v=" + v["id"],
        })
    return sorted(rows, key=lambda x: x["views_per_day"], reverse=True)

def ask_gemini(prompt):
    if not gemini_key:
        st.error("Add your Gemini API key in the sidebar or Streamlit Secrets.")
        st.stop()
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
    return response.text or "No text returned."

topic = st.text_input("Your niche / topic", placeholder="e.g. AI tools, finance, smartphone reviews")
competitors = st.text_input("Competitor channel names (optional)", placeholder="Creator A, Creator B")
c1, c2, c3 = st.columns(3)
with c1:
    count = st.selectbox("Videos to research", [10, 20, 30, 50], index=1)
with c2:
    fmt = st.selectbox("Video format", ["YouTube Shorts", "Long-form", "Both"], index=2)
with c3:
    duration = st.selectbox("Target duration", ["30–45 seconds", "60 seconds", "5–8 minutes", "8–12 minutes"], index=2)

if "research" not in st.session_state:
    st.session_state.research = []
if "analysis" not in st.session_state:
    st.session_state.analysis = ""

b1, b2 = st.columns(2)
with b1:
    research_clicked = st.button(
        "🔎 Research YouTube videos",
        type="secondary",
        disabled=not topic.strip() or not yt_key,
        help="Requires a YouTube Data API key.",
        use_container_width=True,
    )
with b2:
    generate_clicked = st.button(
        "🧠 Generate ideas & complete script",
        type="primary",
        disabled=not topic.strip() or not gemini_key,
        use_container_width=True,
    )

if research_clicked:
    try:
        with st.spinner("Searching public YouTube video metadata..."):
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
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "url": st.column_config.LinkColumn("Video link"),
            "views": st.column_config.NumberColumn(format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views/day", format="%d"),
        },
    )

if generate_clicked:
    evidence = "\n".join(
        f"- {x['title']} | channel={x['channel']} | views={x['views']} | "
        f"views/day={x['views_per_day']} | published={x['published']} | url={x['url']}"
        for x in rows[:10]
    ) or "No live YouTube data was provided. Do not pretend to have searched YouTube or invent current views, trends, channels, or metrics."
    prompt = f"""Act as an evidence-conscious YouTube strategist.
Topic/niche: {topic}
Competitor hints: {competitors or 'none supplied'}
Format: {fmt}
Target duration: {duration}
Script language: {language}
Audience region: {region}

Use any supplied public video metadata as imperfect signals only. If no live YouTube data is supplied, clearly label the research as idea generation based on general knowledge, not live trend research. Never invent metrics or claim that a topic is currently viral without evidence. Never promise virality or claim views prove causation. Do not copy other creators' scripts; create original material.

VIDEO DATA:
{evidence}

Return:
1. Brief competitor landscape only if evidence is supplied; otherwise state that live competitor data is unavailable.
2. Five original video ideas ranked by potential, with audience, rationale, score /10 and caveat.
3. Best idea, three honest titles, thumbnail concept and 3–5 word thumbnail text.
4. Complete original timestamped script for {duration}, with first-five-second hook, open loops, examples, retention resets and CTA. Flag factual claims that need verification.
5. Description, chapters if long-form, tags, hashtags and pinned comment.
6. Two-week publishing plan with suggested test slots in {region} local time; state that these are hypotheses.
7. Metrics to review after publishing: CTR, first 30-second retention, average view duration and returning viewers.

Keep the output practical, clearly formatted in Markdown, and suitable for a creator to review and manually publish. Do not upload or publish anything.
"""
    try:
        with st.spinner("Generating original ideas and script with Gemini..."):
            st.session_state.analysis = ask_gemini(prompt)
    except Exception as e:
        st.error(f"AI generation failed. Check API key, quota and model availability: {e}")

if st.session_state.analysis:
    st.subheader("Your content package")
    st.markdown(st.session_state.analysis)
    st.download_button(
        "⬇️ Download strategy & script",
        st.session_state.analysis,
        file_name="kratos_youtube_strategy.md",
        mime="text/markdown",
    )

if not yt_key:
    st.info("Gemini-only mode: ideas and scripts work with your Gemini key. Add a YouTube Data API key later if you want live video search and public metrics.")
elif not rows:
    st.info("Add a topic and choose Research YouTube videos for live public metadata, or generate ideas and a script directly.")

st.divider()
st.subheader("Publishing-time guidance")
st.write(
    "Use YouTube Studio → Analytics → Audience → “When your viewers are on YouTube” "
    "as your main timing signal. If you have no audience data, test 2–3 consistent slots "
    "for two weeks and compare CTR and retention."
)
st.caption(
    "This app creates research summaries and drafts only. It never uploads or publishes videos. "
    "Public metadata is not private channel analytics. API quotas and hosting limits apply."
)
