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
    import re
    import html

    def parse_content_sections(markdown_text):
        """Split generated Markdown into workflow nodes, keeping all text with its section."""
        lines = markdown_text.strip().splitlines()
        sections = []
        current_title = "Content overview"
        current_lines = []
        for line in lines:
            match = re.match(r"^\\s*(?:#{1,4}\\s*)?(\\d{1,2})[.)]\\s+(.+)$", line.strip())
            is_ai_prompt = line.strip().lower().startswith("ai thumbnail prompt")
            if match and current_lines:
                sections.append((current_title, "\\n".join(current_lines).strip()))
                current_title = match.group(2).strip().strip("*#")
                current_lines = []
            elif match:
                current_title = match.group(2).strip().strip("*#")
            elif is_ai_prompt and current_lines:
                sections.append((current_title, "\\n".join(current_lines).strip()))
                current_title = "AI Thumbnail Prompt"
                current_lines = []
            current_lines.append(line)
        if current_lines:
            sections.append((current_title, "\\n".join(current_lines).strip()))
        # Merge the initial heading-only fragment into the first meaningful section.
        cleaned = []
        for title, body in sections:
            if not body:
                continue
            cleaned.append((title, body))
        return cleaned

    def compact_node_body(markdown_text):
        """Render Markdown as small, readable workflow bullets rather than one long paragraph."""
        rendered = []
        for raw in markdown_text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            line = re.sub(r"^[-*+]\\s+", "", line)
            line = re.sub(r"^\\d+[.)]\\s+", "", line)
            line = re.sub(r"\\*\\*(.*?)\\*\\*", r"\\1", line)
            line = re.sub(r"\\*(.*?)\\*", r"\\1", line)
            if line:
                rendered.append(line)
        return rendered

    sections = parse_content_sections(st.session_state.content_package)
    st.markdown("""
    <style>
    .wf-head{border:1px solid #2a4266;border-radius:18px;padding:20px 23px;background:linear-gradient(110deg,#14213a,#101827 65%,#16343d);margin:10px 0 20px}
    .wf-kicker{font-size:11px;letter-spacing:2.5px;font-weight:800;color:#7cb6ff}
    .wf-title{font-size:25px;font-weight:850;color:#f7faff;margin-top:6px}
    .wf-sub{font-size:13px;color:#a7bad5;margin-top:5px}
    .wf-canvas{border:1px solid #263b57;border-radius:18px;padding:18px;background:radial-gradient(circle at 20% 0%,#162741 0,#0b1220 55%);margin-bottom:20px}
    .wf-node{border:1px solid #385477;border-radius:14px;background:linear-gradient(145deg,#15243a,#101827);padding:14px 16px;color:#e8f0ff;min-height:118px}
    .wf-node-head{display:flex;align-items:center;gap:10px;margin-bottom:9px}
    .wf-number{width:34px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#16b8a6);font-weight:900;color:#fff;font-size:12px;flex-shrink:0}
    .wf-node-title{font-weight:800;font-size:15px;color:#fff}
    .wf-node-text{font-size:12px;line-height:1.6;color:#b7c7df}
    .wf-connector{height:30px;display:flex;align-items:center;justify-content:center;color:#39d5c5;font-size:22px;font-weight:900;letter-spacing:3px}
    .wf-node ul{padding-left:17px;margin:8px 0 0}.wf-node li{margin:5px 0}
    .wf-output{border-color:#287e78;background:linear-gradient(145deg,#12332f,#101827)}
    .wf-chip{display:inline-block;border:1px solid #2b5266;border-radius:99px;padding:4px 8px;font-size:10px;letter-spacing:.7px;color:#78ead7;margin:0 5px 5px 0}
    </style>
    <div class="wf-head">
      <div class="wf-kicker">KRATOS / AI WORKFLOW</div>
      <div class="wf-title">Your YouTube Content Pipeline</div>
      <div class="wf-sub">Follow the connected steps. Every stage shows the key information and deliverable.</div>
      <div style="margin-top:12px"><span class="wf-chip">01 RESEARCH</span><span class="wf-chip">02 IDEAS</span><span class="wf-chip">03 SCRIPT</span><span class="wf-chip">04 PUBLISHING KIT</span><span class="wf-chip">05 THUMBNAIL</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇️ Download full content package (.md)",
        st.session_state.content_package,
        file_name="kratos_content_package.md",
        mime="text/markdown",
    )

    # Display every generated section as a workflow node, connected vertically.
    for idx, (section_title, body) in enumerate(sections):
        node_num = idx + 1
        title_safe = html.escape(re.sub(r"^\\d+[.)]\\s*", "", section_title).strip())
        body_lines = compact_node_body(body)
        if not body_lines:
            body_lines = ["Details are included in the downloadable full content package."]
        # Keep the node scannable; the full original package remains downloadable.
        preview_lines = body_lines[:8]
        list_html = "".join(f"<li>{html.escape(line[:260])}</li>" for line in preview_lines)
        if len(body_lines) > len(preview_lines):
            list_html += f"<li><em>{len(body_lines) - len(preview_lines)} more details in the downloadable package</em></li>"
        node_class = "wf-node wf-output" if ("thumbnail" in title_safe.lower() or "calendar" in title_safe.lower()) else "wf-node"
        st.markdown(
            f'<div class="wf-canvas"><div class="{node_class}"><div class="wf-node-head"><div class="wf-number">{node_num:02d}</div><div class="wf-node-title">{title_safe}</div></div><div class="wf-node-text"><ul>{list_html}</ul></div></div></div>',
            unsafe_allow_html=True,
        )
        if idx < len(sections) - 1:
            st.markdown('<div class="wf-connector">│<br>↓</div>', unsafe_allow_html=True)

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
            st.warning(f"Gemini image generation was unavailable: {e}")
            with st.spinner("Creating a designed thumbnail locally inside Kratos..."):
                st.session_state.thumbnail_bytes = create_designed_thumbnail(
                    topic, thumbnail_text, style
                )
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
    st.info("Add a Gemini API key to generate scripts and thumbnails.")
st.info("Gemini image generation uses the Gemini API. Image-model access and billing may differ from text generation; check Google AI Studio pricing and quota.")
if not yt_key:
    st.info("YouTube live research is optional. Add a YouTube Data API key to search public videos and retrieve available public statistics.")

st.divider()
st.subheader("Before publishing")
st.write("Review all facts, titles and claims. Use YouTube Studio audience analytics for your own best publishing times. This app only creates drafts and images; it never uploads or publishes videos.")
st.caption("Public video data is not private competitor analytics. Gemini image generation depends on API quota; if unavailable, Kratos automatically creates an in-app designed thumbnail.")
