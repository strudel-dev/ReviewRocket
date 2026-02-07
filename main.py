import streamlit as st
import requests
import os
import google.generativeai as genai
from urllib.parse import quote

# 1. PAGE CONFIG
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")

st.markdown("""
<style>
    .stApp {margin-top: -30px;}
    
    /* The Native SMS Button */
    .sms-button {
        display: inline-block;
        background-color: #007AFF; /* iPhone Blue */
        color: white;
        padding: 15px;
        text-align: center;
        text-decoration: none;
        font-size: 18px;
        border-radius: 14px;
        width: 100%;
        font-family: sans-serif;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .sms-button:hover { background-color: #0056b3; color: white; }
</style>
""", unsafe_allow_html=True)

# 2. KEY LOADER
def get_secret(key):
    if key in st.secrets: return st.secrets[key]
    return os.environ.get(key, None)

# 3. GOOGLE MAPS FETCH
def fetch_stats(place_id, api_key):
    # If no ID/Key, return fake data so app doesn't break
    if not place_id or not api_key: return None
    
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "displayName,rating,userRatingCount,reviews"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200: return resp.json()
    except: return None
    return None

# 4. LOGIN LOGIC
if "logged_in" not in st.session_state: st.session_state.logged_in = False

def check_login():
    query = st.query_params
    url_pass = query.get("access", None)
    if url_pass: validate_user(url_pass)
    
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>ReviewRocket 🚀</h2>", unsafe_allow_html=True)
        password = st.text_input("Access Key", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            validate_user(password)
            st.rerun()

def validate_user(password):
    if "users" in st.secrets and password in st.secrets["users"]:
        raw = st.secrets["users"][password].split("|")
        st.session_state.business_name = raw[0]
        st.session_state.review_link = raw[1]
        # Handle optional Place ID
        st.session_state.place_id = raw[2] if len(raw) > 2 else None
        st.session_state.logged_in = True
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# 5. DASHBOARD HEADER
st.markdown(f"### {st.session_state.business_name}")

# Try to fetch real stats, otherwise use placeholders
stats = fetch_stats(st.session_state.place_id, get_secret("GOOGLE_MAPS_KEY"))

# METRICS ROW
c1, c2 = st.columns(2)
if stats:
    c1.metric("Rating", f"{stats.get('rating', '5.0')} ⭐")
    c2.metric("Total Reviews", f"{stats.get('userRatingCount', '0')}")
else:
    # Fallback if API fails
    c1.metric("Rating", "5.0 ⭐")
    c2.metric("Status", "Connected")

st.divider()

# 6. MAIN TABS
tab1, tab2 = st.tabs(["📲 Send Invite", "💬 AI Reviews"])

# --- TAB 1: NATIVE SENDER ---
with tab1:
    st.info("💡 Type name, click button, send from YOUR phone.")
    
    # Simple Inputs
    client_name = st.text_input("Client Name", placeholder="e.g. Sarah")
    
    # Message Generator
    default_msg = f"Hi {client_name if client_name else '...'}, thanks for choosing {st.session_state.business_name}! Could you leave us a quick review? It really helps: {st.session_state.review_link}"
    
    msg_content = st.text_area("Message Preview", value=default_msg, height=100)
    
    # ENCODE FOR SMS LINK
    # This turns spaces into %20 so it works in the URL
    encoded_msg = quote(msg_content)
    
    # THE MAGIC BUTTON
    # 'sms:&body=' works on iOS and Android
    st.markdown(f"""
    <a href="sms:&body={encoded_msg}" class="sms-button">
       💬 Open in Messages
    </a>
    """, unsafe_allow_html=True)

# --- TAB 2: REVIEWS ---
with tab2:
    if stats and 'reviews' in stats:
        for r in stats['reviews']:
            author = r.get('authorAttribution', {}).get('displayName', 'Anonymous')
            stars = r.get('rating', 5)
            text = r.get('text', {}).get('text', '')
            
            with st.container(border=True):
                st.markdown(f"**{author}** <span style='float:right'>{'⭐'*stars}</span>", unsafe_allow_html=True)
                if text:
                    st.write(f"_{text}_")
                    if st.button("Draft Reply", key=author):
                        genai.configure(api_key=get_secret("GOOGLE_API_KEY"))
                        model = genai.GenerativeModel('gemini-flash-latest')
                        prompt = f"Write a short, warm Australian reply to: '{text}'"
                        try:
                            reply = model.generate_content(prompt)
                            st.text_area("Copy this:", value=reply.text)
                        except: st.error("AI Error")
    else:
        st.info("Reviews will appear here once the Place ID is connected.")
        st.caption("For now, use the 'Send Invite' tab to get more!")

# Logout
st.markdown("---")
if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()
