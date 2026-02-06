import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import requests
import pandas as pd
from datetime import datetime

# 1. Load Keys
load_dotenv()
MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY")
AI_KEY = os.environ.get("GOOGLE_API_KEY")

# 2. Config & CSS (Modern UI)
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")
st.markdown("""
<style>
    /* Hiding Streamlit Branding */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp {margin-top: -30px;}
    
    /* Modern Card Style for Reviews */
    .review-card {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .star-rating { color: #f39c12; font-weight: bold; }
    
    /* iPhone Bubble */
    .iphone-bubble {
        background-color: #007AFF; color: white; padding: 15px; border-radius: 18px;
        font-family: -apple-system, sans-serif; font-size: 15px; margin-bottom: 20px;
    }
    
    /* Stats Bar */
    [data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def get_secret(key):
    if key in st.secrets: return st.secrets[key]
    return os.environ.get(key, "")

def smart_format_phone(number):
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("04") and len(clean) == 10: return "+61" + clean[1:]
    if clean.startswith("4") and len(clean) == 9: return "+61" + clean
    return clean

# --- GOOGLE MAPS INTEGRATION ---
def fetch_business_stats(business_name):
    # 1. Find the Place ID
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "places.id,places.rating,places.userRatingCount,places.reviews"
    }
    data = {"textQuery": business_name}
    
    try:
        resp = requests.post(search_url, json=data, headers=headers)
        if resp.status_code == 200 and resp.json().get('places'):
            return resp.json()['places'][0]
    except:
        pass
    return None

# --- SESSION STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "business_name" not in st.session_state: st.session_state.business_name = ""

# --- LOGIN LOGIC ---
def check_login():
    query_params = st.query_params
    url_pass = query_params.get("access", None)
    
    if url_pass:
        validate_user(url_pass)
        return

    if st.session_state.logged_in: return

    st.markdown("<h1 style='text-align: center;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    with st.form("login"):
        password = st.text_input("Access Key", type="password")
        if st.form_submit_button("Login", type="primary", use_container_width=True):
            validate_user(password)
            st.rerun()

def validate_user(password):
    user_db = st.secrets.get("users", {})
    if password in user_db:
        name, link = user_db[password].split("|")
        st.session_state.business_name = name
        st.session_state.review_link = link
        st.session_state.current_user_pass = password
        st.session_state.logged_in = True
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# --- FETCH DATA (Only runs once per session to save API calls) ---
if "stats" not in st.session_state:
    with st.spinner(f"Connecting to Google for {st.session_state.business_name}..."):
        data = fetch_business_stats(st.session_state.business_name)
        st.session_state.stats = data

# --- DASHBOARD HEADER ---
st.markdown(f"### {st.session_state.business_name}")

# SHOW LIVE GOOGLE STATS
if st.session_state.stats:
    rating = st.session_state.stats.get('rating', 'N/A')
    count = st.session_state.stats.get('userRatingCount', 0)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Google Rating", f"{rating} ⭐")
    c2.metric("Total Reviews", f"{count}")
    c3.metric("Invites Sent", len(st.session_state.history))
    st.divider()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📨 Send Invite", "💬 Latest Reviews", "⚙️ Settings"])

# --- TAB 1: INVITE ---
with tab1:
    col1, col2 = st.columns([1, 1.2])
    with col1: name = st.text_input("Customer Name")
    with col2: phone = st.text_input("Mobile Number")

    default_msg = f"Hi {name if name else '...'}, thanks for choosing us! Please leave a review here: {st.session_state.review_link}"
    st.markdown(f'<div class="iphone-bubble">{default_msg}</div>', unsafe_allow_html=True)
    
    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not name or not phone:
            st.toast("⚠️ Missing details")
        else:
            try:
                client = Client(get_secret("TWILIO_ACCOUNT_SID"), get_secret("TWILIO_AUTH_TOKEN"))
                client.messages.create(body=default_msg, from_=get_secret("TWILIO_PHONE_NUMBER"), to=smart_format_phone(phone))
                st.success(f"Sent to {name}!")
                st.session_state.history.append({"Date": datetime.now().strftime("%d/%m"), "Name": name})
                st.rerun() # Refresh stats
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: REVIEW FEED (The New Feature) ---
with tab2:
    st.caption("Recent reviews pulled from Google Maps")
    
    if st.session_state.stats and 'reviews' in st.session_state.stats:
        reviews = st.session_state.stats['reviews']
        
        for review in reviews:
            # Extract review data
            author = review.get('authorAttribution', {}).get('displayName', 'Anonymous')
            stars = review.get('rating', 5)
            text = review.get('text', {}).get('text', 'No text provided.')
            
            # The Card UI
            with st.container(border=True):
                st.markdown(f"**{author}** <span style='float:right'>{'⭐'*stars}</span>", unsafe_allow_html=True)
                st.write(f"_{text}_")
                
                # The "Draft Reply" Button
                if st.button(f"Draft Reply for {author}", key=author):
                    genai.configure(api_key=AI_KEY)
                    model = genai.GenerativeModel('gemini-flash-latest')
                    prompt = f"Write a short, professional Australian response to this review for {st.session_state.business_name}: '{text}'"
                    reply = model.generate_content(prompt)
                    st.text_area("Copy this reply:", value=reply.text, height=100)
    else:
        st.info("No reviews found or Google API limit reached.")

# --- TAB 3: SETTINGS ---
with tab3:
    st.markdown("### 📱 Install App")
    if st.button("Get Auto-Login Link"):
        link = f"https://reviewrocket.streamlit.app/?access={st.session_state.current_user_pass}"
        st.code(link, language="text")
    
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.rerun()
