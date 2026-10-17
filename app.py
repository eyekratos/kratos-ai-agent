import os
from datetime import datetime, timezone

import streamlit as st
from io import BytesIO
from google import genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Studio", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Studio")
st.caption("Research videos • write scripts and generate AI thumbnails with Gemini • no auto-posting")

def secret_or_env(name):
    try:
        return st.secrets.get(name, os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")

with st.sidebar:
    st.header("API setup")
    gemini_key = st.text_input(
        "Gemini API key (script writing)",
        value=secret_or_env("GEMINI_API_KEY"),
        type="password",
        help="Used to generate scripts and content packages.",
    )
    yt_key = st.text_input(
        "YouTube Data API key (live search)",
        value=secret_or_env("YOUTUBE_API_KEY"),
        type="password",
        help="Optional. Adds live public YouTube search and available statistics.",
    )
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"])
    st.caption("Never commit API keys to GitHub. Check each provider's current quotas and pricing.")

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
if "thumbnail_prompt_fallback" not in st.session_state:
    st.session_state.thumbnail_prompt_fallback = ""

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
    if not gemini_key:
        st.error("Add your Gemini API key in the sidebar or Streamlit Secrets to generate scripts.")
        st.stop()
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )
    return response.text or "No text returned."

def generate_thumbnail(prompt):
    if not gemini_key:
        raise RuntimeError("Add your Gemini API key in the sidebar or Streamlit Secrets as GEMINI_API_KEY.")

    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=prompt,
        config={
            "response_modalities": ["IMAGE"],
        },
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()

    text_parts = [part.text for part in response.parts if getattr(part, "text", None)]
    detail = " ".join(text_parts)[:800] or "The model returned no image data."
    raise RuntimeError(detail)

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
        disabled=not topic.strip() or not gemini_key,
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
        with st.spinner("Writing script and content package with Gemini..."):
            st.session_state.content_package = generate_script(prompt)
            st.session_state.thumbnail_bytes = None
            st.session_state.thumbnail_prompt_fallback = ""
            st.session_state.thumbnail_autogenerate_pending = True
    except Exception as e:
        st.error(f"Script generation failed in Gemini. Check Gemini API key, model access and quota: {e}")

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
    # Generate the thumbnail automatically after a new content package is created.
    # Session-state guard prevents a new image request on every Streamlit rerun.
    if not st.session_state.thumbnail_bytes and st.session_state.get("thumbnail_autogenerate_pending", False):
        try:
            with st.spinner("Automatically generating thumbnail with Gemini..."):
                st.session_state.thumbnail_bytes = generate_thumbnail(thumbnail_prompt)
            st.session_state.thumbnail_autogenerate_pending = False
            st.success("Thumbnail generated automatically.")
        except Exception as e:
            st.session_state.thumbnail_autogenerate_pending = False
            st.session_state.thumbnail_prompt_fallback = thumbnail_prompt
            st.warning(f"Gemini could not create the image (often because image-model quota is unavailable): {e}")
            st.info("You can still create the thumbnail in a browser image generator. Copy or download the prompt below, open the generator, paste it, and choose a 16:9 landscape image.")

    if st.session_state.thumbnail_bytes:
        st.subheader("Generated thumbnail")
        st.image(st.session_state.thumbnail_bytes, use_container_width=True)
        st.download_button(
            "⬇️ Download thumbnail PNG",
            data=st.session_state.thumbnail_bytes,
            file_name="kratos_youtube_thumbnail.png",
            mime="image/png",
        )

    if st.session_state.thumbnail_prompt_fallback:
        st.subheader("Free thumbnail fallback")
        st.text_area("Ready-to-use AI thumbnail prompt", value=st.session_state.thumbnail_prompt_fallback, height=220)
        st.download_button(
            "⬇️ Download thumbnail prompt",
            data=st.session_state.thumbnail_prompt_fallback,
            file_name="kratos_thumbnail_prompt.txt",
            mime="text/plain",
        )
        st.link_button("🎨 Open FreeImgGen", "https://freeimggen.com/", use_container_width=True)
        st.caption("This is a separate browser service. Paste the prompt there; free limits and terms may change.")

if not gemini_key:
    st.info("Add a Gemini API key to generate scripts and thumbnails.")
st.info("Gemini image generation uses the Gemini API. Image-model access and billing may differ from text generation; check Google AI Studio pricing and quota.")
if not yt_key:
    st.info("YouTube live research is optional. Add a YouTube Data API key to search public videos and retrieve available public statistics.")

st.divider()
st.subheader("Before publishing")
st.write("Review all facts, titles and claims. Use YouTube Studio audience analytics for your own best publishing times. This app only creates drafts and images; it never uploads or publishes videos.")
st.caption("Public video data is not private competitor analytics. Provider quotas and model availability apply; free image generation is not guaranteed.")
