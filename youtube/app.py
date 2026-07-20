# -*- coding: utf-8 -*-
"""
YouTube 댓글 분석기 (Apple 스타일 UI)
- 유튜브 링크 입력 → 영상 임베드
- 댓글 수집 개수 설정
- 시간대별 댓글 작성 추이
- 댓글 반응도(좋아요) 분석
- 한글 워드클라우드 (NanumGothic 폰트, GitHub 업로드본 사용)
- API 키는 st.secrets 에서만 로드 (입력창 없음)
"""

import re
import os
import io
import base64
import urllib.request
from datetime import datetime
from collections import Counter

import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
from PIL import Image

# ------------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------------
st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 나눔고딕 폰트 경로 (GitHub 레포에 함께 업로드된 폰트 파일)
# 레포 구조 예시: /fonts/NanumGothic.ttf
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NanumGothic.ttf")

# 폰트가 로컬에 없을 경우를 대비한 GitHub Raw 백업 URL
# 본인 레포 주소로 교체해서 사용하세요.
FONT_RAW_URL = "https://raw.githubusercontent.com/USERNAME/REPO/main/fonts/NanumGothic.ttf"


@st.cache_resource(show_spinner=False)
def ensure_font() -> str:
    """로컬에 폰트가 없으면 GitHub Raw 에서 내려받아 캐시 폴더에 저장한다."""
    if os.path.exists(FONT_PATH):
        return FONT_PATH

    cache_dir = os.path.join(os.path.dirname(__file__), ".font_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cached_font = os.path.join(cache_dir, "NanumGothic.ttf")

    if not os.path.exists(cached_font):
        try:
            urllib.request.urlretrieve(FONT_RAW_URL, cached_font)
        except Exception:
            return None
    return cached_font


# ------------------------------------------------------------------
# Apple 스타일 CSS
# ------------------------------------------------------------------
def inject_apple_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                         "SF Pro Text", "Noto Sans KR", "Helvetica Neue", Arial, sans-serif !important;
        }

        .stApp {
            background-color: #f5f5f7;
        }

        /* 메인 컨테이너 여백 */
        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }

        /* 히어로 타이틀 */
        .apple-hero {
            text-align: center;
            padding: 2.2rem 1rem 1.6rem 1rem;
        }
        .apple-hero h1 {
            font-size: 2.6rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #1d1d1f;
            margin-bottom: 0.4rem;
        }
        .apple-hero p {
            font-size: 1.1rem;
            color: #6e6e73;
            font-weight: 400;
        }

        /* 카드 */
        .apple-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 1.6rem 1.8rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.04);
            margin-bottom: 1.4rem;
        }
        .apple-card h3 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 0.9rem;
            letter-spacing: -0.01em;
        }

        /* 지표 카드 */
        .metric-box {
            background: #ffffff;
            border-radius: 18px;
            padding: 1.3rem 1rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.04);
        }
        .metric-box .value {
            font-size: 1.9rem;
            font-weight: 700;
            color: #0071e3;
            letter-spacing: -0.02em;
        }
        .metric-box .label {
            font-size: 0.85rem;
            color: #6e6e73;
            margin-top: 0.2rem;
        }

        /* 버튼 */
        div.stButton > button {
            background: linear-gradient(180deg, #0077ed 0%, #0071e3 100%);
            color: white;
            border: none;
            border-radius: 980px;
            padding: 0.55rem 1.6rem;
            font-weight: 500;
            font-size: 1rem;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0,113,227,0.25);
        }
        div.stButton > button:hover {
            background: linear-gradient(180deg, #1a86ff 0%, #0077ed 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(0,113,227,0.35);
        }

        /* 사이드바 */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid rgba(0,0,0,0.06);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        /* 인풋 */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
            border-radius: 12px !important;
        }

        /* 탭 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #e8e8ed;
            padding: 4px;
            border-radius: 14px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 0.5rem 1.2rem;
            font-weight: 500;
            color: #1d1d1f;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }

        /* 구분선 */
        hr {
            border: none;
            border-top: 1px solid rgba(0,0,0,0.08);
            margin: 1.6rem 0;
        }

        /* 댓글 리스트 아이템 */
        .comment-item {
            padding: 0.8rem 0;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        .comment-item:last-child {
            border-bottom: none;
        }
        .comment-author {
            font-weight: 600;
            color: #1d1d1f;
            font-size: 0.92rem;
        }
        .comment-text {
            color: #333336;
            font-size: 0.95rem;
            margin-top: 0.15rem;
            line-height: 1.45;
        }
        .comment-meta {
            color: #86868b;
            font-size: 0.8rem;
            margin-top: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# YouTube 데이터 API 관련 함수
# ------------------------------------------------------------------
def get_api_key():
    """API 키는 오직 st.secrets 에서만 가져온다 (입력창 없음)."""
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except Exception:
        return None


def extract_video_id(url: str):
    """다양한 형태의 유튜브 URL에서 video ID를 추출."""
    patterns = [
        r"(?:v=|/videos/|embed/|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None


@st.cache_data(show_spinner=False, ttl=600)
def fetch_video_info(video_id: str, api_key: str):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key,
    }
    res = requests.get(url, params=params, timeout=15)
    data = res.json()
    if "error" in data:
        return None, data["error"].get("message", "알 수 없는 오류")
    items = data.get("items", [])
    if not items:
        return None, "영상을 찾을 수 없습니다."
    return items[0], None


@st.cache_data(show_spinner=False, ttl=600)
def fetch_comments(video_id: str, api_key: str, target_count: int):
    """commentThreads.list 를 페이지네이션하며 댓글을 target_count 만큼 수집."""
    comments = []
    page_token = None
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    error_msg = None

    while len(comments) < target_count:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(100, target_count - len(comments)),
            "order": "time",
            "textFormat": "plainText",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        res = requests.get(url, params=params, timeout=15)
        data = res.json()

        if "error" in data:
            error_msg = data["error"].get("message", "댓글을 불러오는 중 오류가 발생했습니다.")
            break

        for item in data.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append(
                {
                    "author": top.get("authorDisplayName", "익명"),
                    "text": top.get("textDisplay", ""),
                    "like_count": top.get("likeCount", 0),
                    "published_at": top.get("publishedAt"),
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return comments, error_msg


# ------------------------------------------------------------------
# 텍스트 분석 (한글 명사 추출)
# ------------------------------------------------------------------
STOPWORDS = {
    "정말", "진짜", "그냥", "근데", "너무", "그리고", "하지만", "그래서",
    "이거", "저거", "우리", "당신", "여기", "저기", "거기", "이런", "저런",
    "그런", "이번", "제발", "오늘", "내일", "어제", "지금", "완전", "역시",
    "그냥", "정도", "생각", "사람", "영상", "댓글", "구독", "채널", "유튜브",
    "이제", "다시", "때문", "이거", "저희", "자체", "모든", "제일",
}


def get_kiwi():
    """kiwipiepy 형태소 분석기를 지연 로드."""
    try:
        from kiwipiepy import Kiwi
        return Kiwi()
    except Exception:
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"@[\w가-힣]+", " ", text)
    text = re.sub(r"[^\w\sㄱ-ㅎㅏ-ㅣ가-힣]", " ", text)
    return text


def extract_nouns(comments_text_list, kiwi):
    counter = Counter()
    for text in comments_text_list:
        cleaned = clean_text(text)
        if not cleaned.strip():
            continue
        if kiwi is not None:
            try:
                tokens = kiwi.tokenize(cleaned)
                for tok in tokens:
                    if tok.tag.startswith("NN") and len(tok.form) > 1:
                        if tok.form not in STOPWORDS:
                            counter[tok.form] += 1
            except Exception:
                pass
        else:
            # kiwipiepy 미설치시 대체: 2자 이상 한글 어절 단위 카운트
            for word in cleaned.split():
                w = re.sub(r"[^가-힣]", "", word)
                if len(w) > 1 and w not in STOPWORDS:
                    counter[w] += 1
    return counter


def make_wordcloud_image(word_freq: Counter, font_path: str):
    if not word_freq:
        return None
    wc = WordCloud(
        font_path=font_path,
        width=1000,
        height=560,
        background_color="white",
        colormap="Blues",
        max_words=120,
        prefer_horizontal=0.9,
        relative_scaling=0.4,
    ).generate_from_frequencies(word_freq)
    return wc.to_image()


# ------------------------------------------------------------------
# 시각화 (Plotly - Apple 톤의 컬러)
# ------------------------------------------------------------------
APPLE_BLUE = "#0071e3"
APPLE_GRAY = "#86868b"


def plot_time_trend(df: pd.DataFrame):
    df = df.copy()
    df["published_at"] = pd.to_datetime(df["published_at"])
    span_days = (df["published_at"].max() - df["published_at"].min()).days

    if span_days <= 2:
        freq, label = "H", "시간대"
    elif span_days <= 60:
        freq, label = "D", "일자"
    elif span_days <= 730:
        freq, label = "W", "주"
    else:
        freq, label = "M", "월"

    grouped = (
        df.set_index("published_at")
        .resample(freq)
        .size()
        .reset_index(name="count")
    )

    fig = px.area(
        grouped,
        x="published_at",
        y="count",
        labels={"published_at": label, "count": "댓글 수"},
    )
    fig.update_traces(line_color=APPLE_BLUE, fillcolor="rgba(0,113,227,0.12)")
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="-apple-system, Noto Sans KR", color="#1d1d1f"),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
    )
    return fig


def plot_engagement(df: pd.DataFrame):
    top = df.sort_values("like_count", ascending=False).head(10).iloc[::-1]
    top["short_text"] = top["text"].str.slice(0, 24) + top["text"].str.len().gt(24).map(
        lambda x: "..." if x else ""
    )
    fig = go.Figure(
        go.Bar(
            x=top["like_count"],
            y=top["short_text"],
            orientation="h",
            marker_color=APPLE_BLUE,
        )
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="-apple-system, Noto Sans KR", color="#1d1d1f"),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="좋아요 수",
        yaxis_title="",
    )
    return fig


def plot_like_distribution(df: pd.DataFrame):
    fig = px.histogram(df, x="like_count", nbins=30)
    fig.update_traces(marker_color=APPLE_GRAY)
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="-apple-system, Noto Sans KR", color="#1d1d1f"),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="좋아요 수",
        yaxis_title="댓글 수",
        bargap=0.15,
    )
    return fig


# ------------------------------------------------------------------
# 메인 앱
# ------------------------------------------------------------------
def main():
    inject_apple_css()

    st.markdown(
        """
        <div class="apple-hero">
            <h1>YouTube 댓글 분석기</h1>
            <p>링크 하나로 댓글의 흐름과 반응, 그리고 이야기를 한눈에.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    api_key = get_api_key()

    with st.sidebar:
        st.markdown("### ⚙️ 설정")
        video_url = st.text_input("유튜브 영상 링크", placeholder="https://www.youtube.com/watch?v=...")
        comment_count = st.slider("수집할 댓글 개수", min_value=20, max_value=1000, value=200, step=20)
        run = st.button("분석 시작", use_container_width=True)

        st.markdown("---")
        st.caption("API 키는 앱 Secrets(`YOUTUBE_API_KEY`)에서 안전하게 불러옵니다.")

    if not api_key:
        st.warning(
            "⚠️ YouTube API 키가 설정되어 있지 않습니다.\n\n"
            "Streamlit Cloud → App settings → Secrets 에 아래처럼 등록해주세요.\n\n"
            "```toml\nYOUTUBE_API_KEY = \"발급받은_API_키\"\n```"
        )
        return

    if not run:
        st.info("왼쪽 사이드바에 유튜브 링크를 입력하고 **분석 시작** 버튼을 눌러주세요.")
        return

    if not video_url:
        st.error("유튜브 링크를 입력해주세요.")
        return

    video_id = extract_video_id(video_url)
    if not video_id:
        st.error("올바른 유튜브 링크 형식이 아닙니다.")
        return

    with st.spinner("영상 정보를 불러오는 중입니다..."):
        video_info, err = fetch_video_info(video_id, api_key)
    if err:
        st.error(f"영상 정보를 불러오지 못했습니다: {err}")
        return

    snippet = video_info["snippet"]
    stats = video_info.get("statistics", {})

    # ---------------- 영상 영역 ----------------
    col_v, col_i = st.columns([1.3, 1])
    with col_v:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        st.components.v1.iframe(
            f"https://www.youtube.com/embed/{video_id}", height=360
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_i:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        st.markdown(f"### {snippet.get('title','')}")
        st.caption(snippet.get("channelTitle", ""))
        c1, c2, c3 = st.columns(3)
        c1.metric("조회수", f"{int(stats.get('viewCount', 0)):,}")
        c2.metric("좋아요", f"{int(stats.get('likeCount', 0)):,}")
        c3.metric("전체 댓글", f"{int(stats.get('commentCount', 0)):,}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- 댓글 수집 ----------------
    with st.spinner(f"댓글 최대 {comment_count}개를 수집하는 중입니다..."):
        comments, c_err = fetch_comments(video_id, api_key, comment_count)

    if c_err and not comments:
        st.error(f"댓글 수집 중 오류가 발생했습니다: {c_err}")
        return
    if not comments:
        st.warning("이 영상에는 댓글이 없거나, 댓글 기능이 비활성화되어 있습니다.")
        return

    df = pd.DataFrame(comments)
    df["published_at"] = pd.to_datetime(df["published_at"])

    st.markdown("<hr/>", unsafe_allow_html=True)

    # ---------------- 요약 지표 ----------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="value">{len(df):,}</div>'
            f'<div class="label">수집된 댓글</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-box"><div class="value">{int(df["like_count"].sum()):,}</div>'
            f'<div class="label">총 좋아요</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="value">{df["like_count"].mean():.1f}</div>'
            f'<div class="label">평균 좋아요</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-box"><div class="value">{int(df["reply_count"].sum()):,}</div>'
            f'<div class="label">총 답글 수</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    tab1, tab2, tab3 = st.tabs(["📈 시간대별 추이", "🔥 댓글 반응도", "☁️ 워드클라우드"])

    with tab1:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        st.markdown("<h3>시간대별 댓글 작성 추이</h3>", unsafe_allow_html=True)
        st.plotly_chart(plot_time_trend(df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="apple-card">', unsafe_allow_html=True)
            st.markdown("<h3>가장 반응이 뜨거운 댓글 Top 10</h3>", unsafe_allow_html=True)
            st.plotly_chart(plot_engagement(df), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="apple-card">', unsafe_allow_html=True)
            st.markdown("<h3>좋아요 분포</h3>", unsafe_allow_html=True)
            st.plotly_chart(plot_like_distribution(df), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        st.markdown("<h3>인기 댓글 리스트</h3>", unsafe_allow_html=True)
        top10 = df.sort_values("like_count", ascending=False).head(10)
        for _, row in top10.iterrows():
            st.markdown(
                f"""
                <div class="comment-item">
                    <div class="comment-author">{row['author']}</div>
                    <div class="comment-text">{row['text']}</div>
                    <div class="comment-meta">👍 {row['like_count']} · 💬 답글 {row['reply_count']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        st.markdown("<h3>댓글 한글 워드클라우드</h3>", unsafe_allow_html=True)

        font_path = ensure_font()
        if not font_path:
            st.error(
                "나눔고딕 폰트를 찾을 수 없습니다. 레포의 `fonts/NanumGothic.ttf` 경로를 확인하거나 "
                "`FONT_RAW_URL` 값을 본인 GitHub 레포 주소로 수정해주세요."
            )
        else:
            with st.spinner("댓글에서 한글 키워드를 추출하는 중입니다..."):
                kiwi = get_kiwi()
                word_freq = extract_nouns(df["text"].astype(str).tolist(), kiwi)
                img = make_wordcloud_image(word_freq, font_path)

            if img is None:
                st.info("워드클라우드를 만들 만한 한글 키워드가 충분하지 않습니다.")
            else:
                st.image(img, use_container_width=True)

                st.markdown("#### 키워드 빈도 Top 15")
                top_words = pd.DataFrame(
                    word_freq.most_common(15), columns=["키워드", "빈도"]
                )
                fig_bar = px.bar(
                    top_words.iloc[::-1], x="빈도", y="키워드", orientation="h"
                )
                fig_bar.update_traces(marker_color=APPLE_BLUE)
                fig_bar.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(family="-apple-system, Noto Sans KR", color="#1d1d1f"),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
