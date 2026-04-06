import streamlit as st
import requests
import os
import streamlit.components.v1 as components
from datetime import timedelta

# Config 
API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Tutor - Học tập Cá nhân hóa", layout="wide")

# Theme CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .chat-bubble { background-color: #1c1c1c; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    .stSelectbox label, .stTextArea label { color: #5dade2 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 AI Tutor: Gia sư Bài giảng Thông minh")

# Sidebar - chọn Bài giảng
st.sidebar.header("📚 Khóa học của bạn")
try:
    resp = requests.get(f"{API_BASE_URL}/api/lectures")
    if resp.status_code == 200:
        lectures = {l["title"]: l for l in resp.json()}
        selected_title = st.sidebar.selectbox("Chọn bài giảng:", list(lectures.keys()))
        selected_data = lectures[selected_title]
        lecture_id = selected_data["id"]
        # Convert path to URL served by API static mount
        video_url = f"{API_BASE_URL}/{selected_data.get('video_url')}"
    else:
        st.sidebar.error("Không thể kết nối API")
        st.stop()
except:
    st.sidebar.error("API chưa chạy. Đang đợi...")
    st.stop()

# Layout
col_video, col_qa = st.columns([2, 1])

with col_video:
    st.header("📺 Trình phát Bài giảng")
    
    # Custom Video Player with Timestamp Capture logic
    # We use a trick to communicate back from JS to Streamlit via a query parameter or similar
    # or just use a simple Javascript component that triggers a secret input.
    # For simplicity, we use the HTML5 player and a button to capture current time.
    player_html = f"""
    <div id="video-container">
        <video id="lecture-video" width="100%" controls style="border-radius: 10px;">
            <source src="{video_url}" type="video/mp4">
        </video>
        <div style="margin-top:10px;">
            <button onclick="captureTime()" style="padding:10px; background-color:#5dade2; color:white; border:none; border-radius:5px; cursor:pointer;">
                🕒 Lấy mốc thời gian hiện tại
            </button>
            <span id="current-time-display" style="margin-left: 10px; color:white;">00:00</span>
        </div>
    </div>

    <script>
    var video = document.getElementById('lecture-video');
    var display = document.getElementById('current-time-display');

    function formatTime(seconds) {{
        var date = new Date(0);
        date.setSeconds(seconds);
        return date.toISOString().substr(11, 8);
    }}

    video.addEventListener('timeupdate', function() {{
        display.innerHTML = formatTime(video.currentTime);
    }});

    function captureTime() {{
        var time = video.currentTime;
        // Send time back to parent (Streamlit)
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: time
        }}, '*');
    }}
    </script>
    """
    
    # We use st.components to render the player and catch the message
    # In a real setup, we use a Custom Component, here we simulate with a slider + manual trigger
    # But now we use the JS value returned by the component
    res_time = components.html(player_html, height=450)
    
    # Fallback/Manual input if JS fails
    st.markdown("---")
    current_timestamp = st.number_input("Hoặc nhập giây đang xem:", value=0, min_value=0, max_value=8000)

with col_qa:
    st.header("💬 Đặt câu hỏi cho Gia sư")
    question = st.text_area("Bạn thắc mắc điều gì?", height=150, placeholder="Ví dụ: Giải thích lại phần này giúp tôi...")
    
    if st.button("Gửi Gia sư", use_container_width=True):
        if question:
            with st.spinner("Gia sư đang suy nghĩ..."):
                try:
                    # In this setup, current_timestamp can be sync from the JS
                    # (For this MVP, we use the sync from the slider/number_input)
                    resp = requests.post(
                        f"{API_BASE_URL}/api/lectures/ask",
                        json={
                            "lecture_id": lecture_id,
                            "current_timestamp": float(current_timestamp),
                            "question": question
                        }
                    )
                    if resp.status_code == 200:
                        st.markdown("### 🤖 Gia sư trả lời:")
                        st.info(resp.json()["answer"])
                    else:
                        st.error(f"Lỗi API: {resp.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")
        else:
            st.warning("Vui lòng nhập câu hỏi.")
