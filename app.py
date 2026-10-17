import os
from datetime import datetime, timezone
from collections import Counter
import streamlit as st
import requests
from google import genai

st.set_page_config(page_title="Kratos YouTube Agent", page_icon="🎬", layout="wide")
st.title("🎬 Kratos — YouTube Growth Agent")
st.caption("Competitor discovery • breakout-video research • original scripts • upload-time clues")

YT_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

with st.sidebar:
    st.header("Research setup")
    topic = st.text_input("Your niche / topic", "AI tools and money mindset")
    language = st.selectbox("Script language", ["Hinglish", "English", "Hindi"])
    format_type = st.selectbox("Video format", ["YouTube long-form", "YouTube Shorts"])
    audience = st.text_input("Target audience", "Beginners in India")
    days = st.selectbox("Lookback window", [30, 90, 180, 365], index=1)
    max_results = st.slider("Videos to research", 10, 50, 25, 5)
    st.markdown("---")
    st.caption("Add YOUTUBE_API_KEY and GEMINI_API_KEY under Streamlit app Secrets. Never paste keys into code.")

def yt_get(endpoint, params):
    if not YT_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY. Add it in Streamlit app Secrets.")
    params["key"] = YT_KEY
    r = requests.get("https://www.googleapis.com/youtube/v3/" + endpoint, params=params, timeout=25)
    if not r.ok:
        try: detail = r.json().get("error", {}).get("message", r.text)
        except Exception: detail = r.text
        raise RuntimeError(f"YouTube API error: {detail}")
    return r.json()

def search_videos(q, limit):
    data = yt_get("search", {"part":"snippet", "q":q, "type":"video", "maxResults":min(limit,50), "order":"viewCount", "publishedAfter":(datetime.now(timezone.utc).timestamp()-days*86400).__int__() and datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()-days*86400,timezone.utc).isoformat().replace("+00:00","Z")})
    items = data.get("items", [])
    ids = [x["id"]["videoId"] for x in items if x.get("id",{}).get("videoId")]
    if not ids: return []
    stats = yt_get("videos", {"part":"snippet,statistics,contentDetails", "id":",".join(ids)}).get("items", [])
    channel_ids = list(dict.fromkeys(v["snippet"]["channelId"] for v in stats))
    channel_map = {}
    for i in range(0,len(channel_ids),50):
        ch = yt_get("channels", {"part":"snippet,statistics", "id":",".join(channel_ids[i:i+50])}).get("items",[])
        for c in ch:
            channel_map[c["id"]] = {"title":c["snippet"]["title"],"subs":int(c.get("statistics",{}).get("subscriberCount",0) or 0)}
    now = datetime.now(timezone.utc)
    out=[]
    for v in stats:
        s=v["snippet"]; stt=v.get("statistics",{})
        published=datetime.fromisoformat(s["publishedAt"].replace("Z","+00:00"))
        age=max((now-published).total_seconds()/86400, 0.25)
        ch=channel_map.get(s["channelId"],{"title":s["channelTitle"],"subs":0})
        views=int(stt.get("viewCount",0) or 0)
        out.append({"title":s["title"],"channel":ch["title"],"channel_id":s["channelId"],"video_id":v["id"],"url":"https://www.youtube.com/watch?v="+v["id"],"published":published,"views":views,"likes":int(stt.get("likeCount",0) or 0),"comments":int(stt.get("commentCount",0) or 0),"subs":ch["subs"],"views_per_day":round(views/age),"views_sub_ratio":round(views/max(ch["subs"],1),2),"description":s.get("description","")[:500]})
    return sorted(out,key=lambda x:x["views_per_day"],reverse=True)

def make_script(videos):
    if not GEMINI_KEY: raise RuntimeError("Missing GEMINI_API_KEY. Add it in Streamlit app Secrets.")
    client=genai.Client(api_key=GEMINI_KEY)
    examples="\n".join([f'- "{v["title"]}" by {v["channel"]}: {v["views"]:,} views, {v["views_per_day"]:,} views/day, published {v["published"].date()}, URL {v["url"]}' for v in videos[:12]])
    prompt=f"""You are an ethical YouTube growth strategist. Use the competitor research below as evidence, not as text to copy.
Niche/topic: {topic}
Audience: {audience}
Language: {language}
Format: {format_type}
Create an original, high-retention video package. Do not claim any video will definitely go viral. Do not copy competitors' scripts, distinctive wording, or structure verbatim.
Research:
{examples}

Return:
1. What appears to be working (patterns, not guarantees) and why.
2. Three original title options, clear and compelling without misleading clickbait.
3. Thumbnail concept (main visual, 2-4 word text, contrast).
4. A strong 0-15 second hook.
5. Full original script with timestamps/sections, pattern interrupts, examples, and a clear payoff. For Shorts keep it concise and spoken; for long-form give a coherent 5-8 minute script.
6. B-roll / on-screen text suggestions.
7. Description, chapters if relevant, and 5-8 relevant hashtags.
8. A practical publishing test plan and metrics to review after 24/72 hours.
Mark assumptions and avoid invented statistics."""
    response=client.models.generate_content(model="gemini-2.5-flash",contents=prompt)
    return response.text

tab1,tab2,tab3=st.tabs(["🔎 Competitor research","✍️ Script studio","🗓️ Upload plan"])
with tab1:
    st.write("Search public YouTube videos by topic. Results are ranked by recent views-per-day, with subscriber-normalized views as another signal.")
    if st.button("Find competitor videos", type="primary"):
        try:
            with st.spinner("Searching YouTube and collecting public stats…"):
                videos=search_videos(topic,max_results)
                st.session_state["videos"]=videos
            if not videos: st.info("No videos found. Try a broader topic.")
        except Exception as e: st.error(str(e))
    videos=st.session_state.get("videos",[])
    if videos:
        st.success(f"Researched {len(videos)} public videos")
        import pandas as pd
        df=pd.DataFrame([{"Video":v["title"],"Channel":v["channel"],"Views":v["views"],"Views/day":v["views_per_day"],"Views/subs":v["views_sub_ratio"],"Published":v["published"].strftime("%Y-%m-%d %H:%M UTC"),"URL":v["url"]} for v in videos])
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={"URL":st.column_config.LinkColumn("Video link")})
        st.subheader("Breakout candidates")
        for v in videos[:8]:
            with st.container(border=True):
                st.markdown(f"**[{v['title']}]({v['url']})**")
                st.caption(f"{v['channel']} • {v['views']:,} views • {v['views_per_day']:,} views/day • {v['views_sub_ratio']} views per subscriber")
                st.write(v["description"] or "No description")
        st.download_button("Download research CSV", df.to_csv(index=False).encode("utf-8"), "competitor_research.csv", "text/csv")
with tab2:
    st.write("Generate an original script package grounded in the research results. If research is empty, run competitor research first.")
    if st.button("Generate my script", type="primary", disabled=not bool(st.session_state.get("videos"))):
        try:
            with st.spinner("Writing titles, hook, script and thumbnail brief…"):
                st.session_state["script"]=make_script(st.session_state["videos"])
        except Exception as e: st.error(str(e))
    if st.session_state.get("script"):
        st.markdown(st.session_state["script"])
        st.download_button("Download script (.md)", st.session_state["script"], "youtube_script.md", "text/markdown")
with tab3:
    st.subheader("Recommended publishing experiment")
    st.write("Best posting time cannot be reliably inferred from public competitor videos alone. Use this as a test plan, then let your own YouTube Analytics decide.")
    st.markdown("""
    - **Before publishing:** finish title + thumbnail together; make the first 15 seconds deliver the promise.
    - **Initial test (India):** test one weekday evening slot (6–9 PM IST) and one weekend late-morning/afternoon slot (11 AM–2 PM IST) across comparable uploads.
    - **After 24 hours:** review impressions, click-through rate, first-30-second retention and average view duration.
    - **After 72 hours:** compare results against your channel baseline; repeat the better slot with a similar topic.
    - **Shorts:** test different posting windows separately from long-form; compare viewed-vs-swiped-away and retention.
    """)
    st.info("These are starting hypotheses, not a promise of viral reach. Your channel's Audience tab → 'When your viewers are on YouTube' is the best timing signal once enough data exists.")
st.divider()
st.caption("Kratos YouTube Agent • Public YouTube data + Gemini-generated original ideas. Respect copyright, platform policies and API quotas.")
