import os
from datetime import datetime, timezone

import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from google import genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Kratos YouTube Studio", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Studio")
st.caption("Your YouTube workflow, connected from research → script → thumbnail → export. No auto-posting.")

def secret_or_env(name):
    try:
        return st.secrets.get(name, os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")

# API credentials are read only from server-side Streamlit Secrets or environment variables.
# Visitors never need to enter keys, and keys are never shown in the public UI.
gemini_key = secret_or_env("GEMINI_API_KEY")
yt_key = secret_or_env("YOUTUBE_API_KEY")

with st.sidebar:
    st.header("Workspace settings")
    region = st.selectbox("Audience country", ["IN", "US", "GB", "CA", "AU"], index=0)
    language = st.selectbox("Script language", ["Hinglish", "Hindi", "English"])
    st.caption("API credentials are securely configured by the site owner. Visitors do not need their own keys.")
    if not yt_key:
        st.caption("Live YouTube research is currently unavailable; script generation can still work.")

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

def render_roadmap():
    steps = [
        ("01", "Research", "Find topic opportunities", bool(st.session_state.research)),
        ("02", "Script studio", "Build your content package", bool(st.session_state.content_package)),
        ("03", "Thumbnail lab", "Create artwork in this app", bool(st.session_state.thumbnail_bytes)),
        ("04", "Export", "Download your finished assets", bool(st.session_state.content_package and st.session_state.thumbnail_bytes)),
    ]
    html = """<style>
    .kr-roadmap{display:flex;gap:25px;margin:14px 0 24px;font-family:Arial,sans-serif}
    .kr-step{position:relative;flex:1;min-width:0;padding:15px 13px;border:1px solid #263b5b;border-radius:15px;background:linear-gradient(145deg,#121f35,#0b1220);color:#dbeafe}
    .kr-step:not(:last-child):after{content:'';position:absolute;top:31px;left:calc(100% + 1px);width:25px;height:2px;background:linear-gradient(90deg,#4777ff,#39d5c5)}
    .kr-num{font-size:11px;letter-spacing:2px;color:#75a4ff;font-weight:800}
    .kr-name{font-size:15px;font-weight:800;margin-top:8px;color:#f8fafc}
    .kr-desc{font-size:11px;line-height:1.45;color:#9fb1cc;margin-top:5px}
    .kr-state{display:inline-block;margin-top:10px;padding:4px 7px;border-radius:99px;font-size:10px;font-weight:700;background:#202e44;color:#a9bad3}
    .kr-state.done{background:#103b39;color:#73f0d4}.kr-step.done{border-color:#287e78}
    @media(max-width:650px){.kr-roadmap{display:block}.kr-step{margin:0 0 10px!important}.kr-step:after{display:none}}
    </style><div class="kr-roadmap">"""
    for number, name, desc, done in steps:
        status = "COMPLETE" if done else "UP NEXT"
        css = "kr-state done" if done else "kr-state"
        step_css = "kr-step done" if done else "kr-step"
        html += f'<div class="{step_css}"><div class="kr-num">STEP {number}</div><div class="kr-name">{name}</div><div class="kr-desc">{desc}</div><span class="{css}">{status}</span></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def _thumbnail_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def create_designed_thumbnail(topic_text, title_text, style_name):
    """Create a 1280x720 graphic thumbnail locally without an image API."""
    w, h = 1280, 720
    base = Image.new("RGB", (w, h))
    pixels = base.load()
    for y in range(h):
        for x in range(w):
            glow = max(0, 1 - (((x - 1010) / 760) ** 2 + ((y - 120) / 600) ** 2) ** 0.5)
            pixels[x, y] = (int(7 + 10 * glow), int(14 + 24 * glow), int(31 + 50 * glow))
    base = base.convert("RGBA")
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer, "RGBA")
    gd.ellipse((790, 50, 1330, 590), fill=(37, 99, 235, 65))
    gd.ellipse((900, 160, 1240, 500), fill=(20, 184, 166, 35))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(65))
    base = Image.alpha_composite(base, glow_layer)
    draw = ImageDraw.Draw(base, "RGBA")
    for x in range(40, w, 48):
        draw.line((x, 0, x, h), fill=(140, 170, 220, 14), width=1)
    for y in range(30, h, 48):
        draw.line((0, y, w, y), fill=(140, 170, 220, 12), width=1)
    draw.polygon([(860, 0), (1040, 0), (680, 720), (500, 720)], fill=(45, 95, 190, 20))
    draw.rounded_rectangle((68, 65, 365, 112), radius=18, fill=(23, 205, 178, 35), outline=(67, 230, 206, 170), width=2)
    draw.text((88, 78), "KRATOS / CREATOR LAB", font=_thumbnail_font(20, True), fill=(111, 255, 222, 255))
    draw.ellipse((790, 150, 1195, 555), outline=(95, 145, 255, 170), width=5)
    draw.ellipse((840, 200, 1145, 505), outline=(50, 220, 198, 150), width=3)
    draw.rounded_rectangle((870, 255, 1115, 450), radius=28, fill=(15, 32, 61, 230), outline=(112, 161, 255, 210), width=3)
    draw.polygon([(956, 300), (956, 406), (1040, 353)], fill=(86, 243, 211, 255))
    draw.ellipse((1090, 170, 1140, 220), fill=(255, 198, 87, 255))
    draw.ellipse((825, 480, 860, 515), fill=(255, 95, 130, 255))
    raw = (title_text or topic_text or "MAKE IT HAPPEN").strip().upper()
    words, lines, line = raw.split(), [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if len(candidate) > 16 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
        if len(lines) >= 2:
            break
    if line and len(lines) < 3:
        lines.append(line)
    lines = lines[:3] or ["MAKE IT HAPPEN"]
    y = 210
    for line in lines:
        size = 68 if len(line) <= 13 else 54
        font = _thumbnail_font(size, True)
        draw.text((74, y + 6), line, font=font, fill=(0, 0, 0, 190), stroke_width=2, stroke_fill=(0, 0, 0, 190))
        draw.text((68, y), line, font=font, fill=(250, 252, 255, 255), stroke_width=1, stroke_fill=(250, 252, 255, 255))
        y += size + 12
    draw.rounded_rectangle((70, 610, 580, 663), radius=14, fill=(37, 99, 235, 230))
    draw.text((92, 622), "WATCH • LEARN • BUILD", font=_thumbnail_font(22, True), fill=(255, 255, 255, 255))
    draw.text((1130, 650), "16:9", font=_thumbnail_font(18, True), fill=(170, 194, 230, 230))
    output = BytesIO()
    base.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


render_roadmap()


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
    # If the user has configured the owner's YouTube API key but hasn't clicked Research first,
    # fetch public results automatically so the script can use real video evidence.
    if yt_key and not st.session_state.research:
        try:
            with st.spinner("Fetching live YouTube results to ground your content package..."):
                q = topic + (" " + competitors if competitors.strip() else "")
                st.session_state.research = search_videos(q, min(count, 20))
            rows = st.session_state.research
        except Exception as research_error:
            st.warning("Live YouTube research could not run. The script will be clearly labelled as idea generation, not live trend analysis.")
    evidence = "\n".join(
        f"- {x['title']} | channel={x['channel']} | views={x['views']} | views/day={x['views_per_day']} | published={x['published']} | url={x['url']}"
        for x in rows[:15]
    ) or "LIVE DATA UNAVAILABLE: no YouTube API results were supplied. Do not invent current trends, video stats, search volume, or competitor findings. State this limitation briefly once."
    data_status = "Live public YouTube video results are included below. Refer to actual titles and metrics where relevant; do not claim search-volume data or private competitor analytics." if rows else "No live public YouTube results are available for this run. Present this as creative ideation based on general audience patterns, and include only one short limitation note."
    prompt = f"""You are a careful YouTube content strategist and scriptwriter.
Topic: {topic}
Competitor hints: {competitors or 'not provided'}
Format: {fmt}
Target duration: {duration}
Script language: {language}
Audience region: {region}

Use this data-status instruction: {data_status}
Use any public YouTube data below only as imperfect evidence. Never invent metrics or promise virality. Create original scripts; do not copy other creators. Do not repeat a long boilerplate notice; if data is unavailable, use one concise sentence to explain the limitation.

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
    if not st.session_state.thumbnail_bytes and st.session_state.get("thumbnail_autogenerate_pending", False):
        try:
            with st.spinner("Automatically generating thumbnail with Gemini..."):
                st.session_state.thumbnail_bytes = generate_thumbnail(thumbnail_prompt)
            st.session_state.thumbnail_autogenerate_pending = False
            st.success("Thumbnail generated automatically.")
        except Exception as e:
            st.session_state.thumbnail_autogenerate_pending = False
            with st.spinner("Creating a designed thumbnail locally inside Kratos..."):
                st.session_state.thumbnail_bytes = create_designed_thumbnail(
                    topic, thumbnail_text, style
                )
            st.info("Gemini image quota is unavailable, so Kratos created a designed thumbnail locally instead.")
            with st.expander("Why wasn't the AI image generated?"):
                st.caption(str(e)[:1400])
            st.success("Thumbnail created inside Kratos. No other website needed.")

    if st.session_state.thumbnail_bytes:
        st.subheader("🎨 Thumbnail Lab")
        st.image(st.session_state.thumbnail_bytes, use_container_width=True)
        st.download_button(
            "⬇️ Download thumbnail PNG",
            data=st.session_state.thumbnail_bytes,
            file_name="kratos_youtube_thumbnail.png",
            mime="image/png",
        )

if not gemini_key:
    st.error("The site owner has not configured the Gemini API key yet. Please try again later.")
st.caption("This public app uses the site owner’s API quota. The owner is responsible for usage and any provider charges.")
if not yt_key:
    st.info("Live YouTube research is disabled until the site owner configures YOUTUBE_API_KEY in Streamlit Secrets.")

st.divider()
st.subheader("Before publishing")
st.write("Review all facts, titles and claims. Use YouTube Studio audience analytics for your own best publishing times. This app only creates drafts and images; it never uploads or publishes videos.")
st.caption("Public video data is not private competitor analytics. Gemini image generation depends on API quota; if unavailable, Kratos automatically creates an in-app designed thumbnail.")
