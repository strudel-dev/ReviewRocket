import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import requests
from datetime import datetime

# 1. Load Keys
load_dotenv()
MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY")
AI_KEY = os.environ.get("GOOGLE_API_KEY")

st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp {margin-top: -30px;}
    .review-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .iphone-bubble { background-color: #007AFF; color: white; padding: 15px; border-radius: 18px; margin-bottom: 10px; font-family: sans-serif; }
    .stTextInput > div > div > input { padding: 12px; font-size: 16px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

def get_secret(key):
    return st.secrets.get(key) or os.environ.get(key, "")

def smart_format_phone(number):
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("04") and len(clean) == 10: return "+61" + clean[1:]
    if clean.startswith("4") and len(clean) == 9: return "+61" + clean
    return clean

# --- ROBUST GOOGLE MAPS FETCH ---
def fetch_stats_by_id(place_id):
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "displayName,rating,userRatingCount,reviews"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching ID: {e}")
    return None

def fetch_stats_by_search(name):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.reviews,places.id"
    }
    data = {"textQuery": name}
    try:
        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code == 200 and resp.json().get('places'):
            return resp.json()['places'][0]
    except:
        pass
    return None

# --- SESSION STATE INITIALIZATION (The Fix) ---
if "history" not in st.session_state: st.session_state.history = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False
# We explicitly create these variables so the app never crashes checking for them
if "place_id" not in st.session_state: st.session_state.place_id = None
if "stats" not in st.session_state: st.session_state.stats = None

def check_login():
    query = st.query_params
    url_pass = query.get("access", None)
    if url_pass: validate_user(url_pass)
    
    if not st.session_state.logged_in:
        st.markdown("<h1 style='text-align: center;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
        with st.form("login"):
            password = st.text_input("Access Key", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                validate_user(password)
                st.rerun()

def validate_user(password):
    user_db = st.secrets.get("users", {})
    if password in user_db:
        raw_data = user_db[password].split("|")
        st.session_state.business_name = raw_data[0]
        st.session_state.review_link = raw_data[1]
        # Safe check for Place ID
        st.session_state.place_id = raw_data[2] if len(raw_data) > 2 else None
        st.session_state.current_user_pass = password
        st.session_state.logged_in = True
        # Force refresh of stats
        st.session_state.stats = None 
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# --- LOAD STATS ---
if not st.session_state.stats:
    if st.session_state.place_id:
        st.session_state.stats = fetch_stats_by_id(st.session_state.place_id)
    else:
        st.session_state.stats = fetch_stats_by_search(st.session_state.business_name)

# --- APP UI ---
st.markdown(f"### {st.session_state.business_name}")

if st.session_state.stats:
    rating = st.session_state.stats.get('rating', 'N/A')
    count = st.session_state.stats.get('userRatingCount', 0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Rating", f"{rating} ⭐")
    c2.metric("Reviews", f"{count}")
    c3.metric("Invites", len(st.session_state.history))
else:
    st.warning("⚠️ Connecting to Google Maps...")

st.divider()

tab1, tab2, tab3 = st.tabs(["📨 Invite", "💬 Reviews", "⚙️ Settings"])

with tab1:
    col1, col2 = st.columns([1, 1.2])
    with col1: name = st.text_input("Name", placeholder="e.g. Sarah")
    with col2: phone = st.text_input("Mobile", placeholder="04...")
    
    default_msg = f"Hi {name if name else '...'}, thanks for choosing {st.session_state.business_name}! Review us here: {st.session_state.review_link}"
    st.markdown("###### Customize Message:")
    msg = st.text_area("Content", value=default_msg, height=100, label_visibility="collapsed")
    st.markdown(f'<div class="iphone-bubble">{msg}</div>', unsafe_allow_html=True)
    
    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not name or not phone: st.toast("Enter name & number")
        else:
            try:
                client = Client(get_secret("TWILIO_ACCOUNT_SID"), get_secret("TWILIO_AUTH_TOKEN"))
                client.messages.create(body=msg, from_=get_secret("TWILIO_PHONE_NUMBER"), to=smart_format_phone(phone))
                st.success(f"Sent to {name}!")
                st.balloons()
                st.session_state.history.append({"Date": datetime.now().strftime("%d/%m"), "Name": name})
            except Exception as e: st.error(f"Error: {e}")

with tab2:
    if st.session_state.stats and 'reviews' in st.session_state.stats:
        reviews = st.session_state.stats['reviews']
        for r in reviews:
            author = r.get('authorAttribution', {}).get('displayName', 'Anonymous')
            stars = r.get('rating', 5)
            text = r.get('text', {}).get('text', '')
            with st.container(border=True):
                st.markdown(f"**{author}** <span style='float:right'>{'⭐'*stars}</span>", unsafe_allow_html=True)
                if text:
                    st.markdown(f"_{text}_")
                    if st.button("Draft Reply", key=author):
                        with st.spinner("Writing..."):
                            genai.configure(api_key=AI_KEY)
                            model = genai.GenerativeModel('gemini-flash-latest')
                            reply = model.generate_content(f"Write a short, warm Aussie reply for {st.session_state.business_name} to: '{text}'")
                            st.text_area("Copy this:", value=reply.text, height=100)
                else:
                    st.caption("(No text provided)")
    else:
        st.info("No reviews found yet.")
        # FIX: Safe check for place_id prevents the crash here
        if not st.session_state.get("place_id"):
            st.caption("Tip: Add the Place ID to secrets.toml for better results.")

with tab3:
    st.markdown("### ⚙️ Settings")
    st.text_input("Business", value=st.session_state.business_name, disabled=True)
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        # Clear stats on logout so next user gets fresh data
        st.session_state.stats = None
        st.rerun()
