import os
import base64
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Studio", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Studio")
st.caption("Research videos • write scripts • generate AI thumbnails • download your content — no auto-posting")

def secret_or_env(name):
    try:
        return st.secrets.get(name, os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")

with st.sidebar:
    st.header("API setup")
    openai_key = st.text_input(
        "OpenAI API key (script + thumbnail)",
        value=secret_or_env("OPENAI_API_KEY"),
        type="password",
        help="OpenAI API billing is separate from a ChatGPT subscription.",
    )
    yt_key = st.text_input(
        "YouTube Data API key (live search)",
        value=secret_or_env("YOUTUBE_API_KEY"),
        type="password",
        help="Optional. Without it, you can still write scripts and generate thumbnails.",
    )
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"])
    st.caption("Never commit API keys to GitHub. API usage may incur charges.")

topic = st.text_input("Video topic / niche", placeholder="e.g. 5 AI tools that save time")
competitors = st.text_input("Competitor channel names (optional)", placeholder="Creator A, Creator B")
c1, c2, c3 = st.columns(3)
with c1:
    count = st.selectbox("Videos to research", [10, 20, 30, 50], index=1)
with c2:
    fmt = st.selectbox("Video format", ["YouTube Shorts", "Long-form", "Both"], index=2)
with c3:
    duration = st.selectbox("Target duration", ["30–45 seconds", "60 seconds", "5–8 minutes", "8–12 minutes"], index=2)

style = st.selectbox(
    "Thumbnail style",
    ["Cinematic high contrast", "Clean tech editorial", "Dark luxury", "Bright creator style", "Minimal and premium"],
)
thumbnail_text = st.text_input("Thumbnail text (optional)", placeholder="Leave blank to let the AI decide")
if "research" not in st.session_state:
    st.session_state.research = []
if "content_package" not in st.session_state:
    st.session_state.content_package = ""
if "thumbnail_bytes" not in st.session_state:
    st.session_state.thumbnail_bytes = None

def get_openai_client():
    if not openai_key:
        st.error("Add your OpenAI API key in the sidebar or Streamlit Secrets.")
        st.stop()
    return OpenAI(api_key=openai_key)

def youtube_client():
    if not yt_key:
        st.error("Add a YouTube Data API key in the sidebar to use live YouTube research.")
        st.stop()
    return build("youtube", "v3", developerKey=yt_key, cache_discovery=False)

def search_videos(query, max_results=20):
    yt = youtube_client()
    response = yt.search().list(
        part="snippet", q=query, type="video", maxResults=max_results,
        order="viewCount", regionCode=region, relevanceLanguage="en"
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
            (datetime.now(timezone.utc) - datetime.fromisoformat(published.replace("Z", "+00:00"))).days, 1
        ) if published else 1
        rows.append({
            "title": s.get("title", ""), "channel": s.get("channelTitle", ""),
            "published": published[:10], "views": views,
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "views_per_day": round(views / age_days),
            "url": "https://www.youtube.com/watch?v=" + v["id"],
        })
    return sorted(rows, key=lambda x: x["views_per_day"], reverse=True)

def generate_script(prompt):
    client = get_openai_client()
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )
    return response.output_text or "No text returned."

def generate_thumbnail(prompt):
    client = get_openai_client()
    result = client.images.generate(
        model="gpt-image-1.5",
        prompt=prompt,
        size="1536x1024",
        quality="high",
        output_format="png",
        n=1,
    )
    return base64.b64decode(result.data[0].b64_json)

left, right = st.columns(2)
with left:
    research_clicked = st.button(
        "🔎 Research live YouTube videos",
        disabled=not topic.strip() or not yt_key,
        use_container_width=True,
    )
with right:
    script_clicked = st.button(
        "✍️ Generate script + content package",
        type="primary",
        disabled=not topic.strip() or not openai_key,
        use_container_width=True,
    )

if research_clicked:
    try:
        with st.spinner("Searching public YouTube video metadata..."):
            q = topic + (" " + competitors if competitors.strip() else "")
            st.session_state.research = search_videos(q, count)
        st.success(f"Found {len(st.session_state.research)} videos.")
    except HttpError as e:
        st.error(f"YouTube API error: {e}")
    except Exception as e:
        st.error(f"Research failed: {e}")

rows = st.session_state.research
if rows:
    st.subheader("Live YouTube opportunity board")
    st.dataframe(
        rows, use_container_width=True, hide_index=True,
        column_config={
            "url": st.column_config.LinkColumn("Video link"),
            "views": st.column_config.NumberColumn(format="%d"),
            "views_per_day": st.column_config.NumberColumn("Views/day", format="%d"),
        },
    )

if script_clicked:
    evidence = "\n".join(
        f"- {x['title']} | channel={x['channel']} | views={x['views']} | views/day={x['views_per_day']} | published={x['published']} | url={x['url']}"
        for x in rows[:15]
    ) or "No live YouTube results supplied. Do not invent current trends, video stats, or competitor findings."
    prompt = f"""You are a careful YouTube content strategist and scriptwriter.
Topic: {topic}
Competitor hints: {competitors or 'not provided'}
Format: {fmt}
Target duration: {duration}
Script language: {language}
Audience region: {region}

Use the public YouTube data below only as imperfect evidence. If no live results are supplied, clearly say this is ideation, not live trend research. Never invent metrics or promise virality. Create original scripts; do not copy other creators.

LIVE VIDEO DATA:
{evidence}

Create a complete content package in well-formatted Markdown:
1. Short research summary and caveats.
2. Five original video ideas ranked by audience appeal with reasons.
3. Recommended idea, three honest title options, hook and thumbnail concept.
4. Complete timestamped script for {duration}, in {language}, with strong opening, examples, transitions, retention resets and CTA. Mark facts that need checking.
5. Video description, chapters if long-form, tags, hashtags and pinned comment.
6. A two-week content calendar.
7. Post-publishing metrics to review (CTR, early retention, average view duration).
8. At the end add a clearly labelled 'AI THUMBNAIL PROMPT' with a detailed 16:9 thumbnail concept for the recommended idea. Visual style: {style}. Thumbnail text preference: {thumbnail_text or 'choose 2–5 short readable words'}.
Do not upload or publish anything."""
    try:
        with st.spinner("Writing original script and content package with OpenAI..."):
            st.session_state.content_package = generate_script(prompt)
            st.session_state.thumbnail_bytes = None
    except Exception as e:
        st.error(f"Script generation failed: {e}")

if st.session_state.content_package:
    st.subheader("Your script & content package")
    st.markdown(st.session_state.content_package)
    st.download_button(
        "⬇️ Download script & content package",
        st.session_state.content_package,
        file_name="kratos_content_package.md",
        mime="text/markdown",
    )

    thumbnail_prompt = f"""Create a professional YouTube thumbnail, wide 16:9 composition, for this video topic: {topic}.
Recommended content and script context:
{st.session_state.content_package[:5000]}

Style: {style}.
Thumbnail text: {thumbnail_text or 'choose a short, punchy 2–5 word phrase relevant to the topic'}.
Make the focal subject large and readable on mobile, use strong contrast, clear visual hierarchy, intentional negative space, expressive but believable imagery, crisp lighting, polished creator-economy art direction, and a clean background. Avoid clutter, tiny text, logos/watermarks, fake UI, fabricated statistics, and misleading claims. Keep all text inside safe margins. The final image should look like a clickable but honest YouTube thumbnail. Landscape 16:9, no borders."""
    if st.button("🖼️ Generate AI thumbnail", type="primary", disabled=not openai_key):
        try:
            with st.spinner("Generating thumbnail with OpenAI Images API... this can take a little while."):
                st.session_state.thumbnail_bytes = generate_thumbnail(thumbnail_prompt)
            st.success("Thumbnail generated.")
        except Exception as e:
            st.error(f"Thumbnail generation failed. Check API access, billing, model access and quota: {e}")

    if st.session_state.thumbnail_bytes:
        st.subheader("Generated thumbnail")
        st.image(st.session_state.thumbnail_bytes, use_container_width=True)
        st.download_button(
            "⬇️ Download thumbnail PNG",
            data=st.session_state.thumbnail_bytes,
            file_name="kratos_youtube_thumbnail.png",
            mime="image/png",
        )

if not openai_key:
    st.info("Add an OpenAI API key to generate scripts and thumbnails. OpenAI API billing is separate from ChatGPT Plus/Go/Pro subscriptions.")
if not yt_key:
    st.info("YouTube live research is optional. Add a YouTube Data API key to search public videos and retrieve available public statistics.")

st.divider()
st.subheader("Before publishing")
st.write("Review all facts, titles and claims. Use YouTube Studio audience analytics for your own best publishing times. This app only creates drafts and images; it never uploads or publishes videos.")
st.caption("Public video data is not private competitor analytics. API quotas, model access, and charges apply.")
