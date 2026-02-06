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
    /* Clean UI */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp {margin-top: -30px;}
    
    /* Modern Card Style */
    .review-card {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* iPhone Bubble (Visual Preview) */
    .iphone-bubble {
        background-color: #007AFF; color: white; padding: 15px; border-radius: 18px;
        font-family: -apple-system, sans-serif; font-size: 15px; margin-bottom: 10px;
        line-height: 1.4;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input { padding: 12px; font-size: 16px; border-radius: 10px; }
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
    # Search specifically for the business name
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.reviews"
    }
    # We add "Australia" to the query to help Google find it
    data = {"textQuery": f"{business_name}"}
    
    try:
        resp = requests.post(search_url, json=data, headers=headers)
        if resp.status_code == 200:
            results = resp.json()
            if results.get('places'):
                return results['places'][0]
            else:
                print(f"DEBUG: No places found for '{business_name}'")
        else:
            print(f"DEBUG: API Error {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"DEBUG: Connection Error {e}")
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
        # Clear old stats when switching users
        if "stats" in st.session_state:
            del st.session_state.stats
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# --- FETCH DATA (Runs once per login) ---
if "stats" not in st.session_state:
    data = fetch_business_stats(st.session_state.business_name)
    st.session_state.stats = data

# --- DASHBOARD HEADER ---
st.markdown(f"### {st.session_state.business_name}")

# SHOW LIVE GOOGLE STATS
if st.session_state.stats:
    rating = st.session_state.stats.get('rating', 'N/A')
    count = st.session_state.stats.get('userRatingCount', 0)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Rating", f"{rating} ⭐")
    c2.metric("Reviews", f"{count}")
    c3.metric("Invites", len(st.session_state.history))
else:
    # If fetch failed, show a subtle warning but don't break the app
    st.caption("⚠️ Could not auto-sync with Google Maps. (Check name spelling)")

st.divider()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📨 Invite", "💬 Reviews", "⚙️ Settings"])

# --- TAB 1: INVITE (RESTORED FEATURES) ---
with tab1:
    col1, col2 = st.columns([1, 1.2])
    with col1: 
        name_input = st.text_input("Customer Name", placeholder="e.g. Sarah")
    with col2: 
        phone_input = st.text_input("Mobile Number", placeholder="04...")

    # Logic: If they type a name, use it. If not, use generic placeholder.
    display_name = name_input if name_input else "[Customer Name]"
    
    # Base Message
    default_msg = f"Hi {display_name}, thanks for choosing {st.session_state.business_name}! Please leave us a review here: {st.session_state.review_link}"
    
    # 1. THE EDITABLE BOX IS BACK
    st.markdown("###### Customize Message:")
    final_message = st.text_area("Message Content", value=default_msg, height=100, label_visibility="collapsed")

    # 2. THE VISUAL PREVIEW IS BACK
    st.markdown(f'<div class="iphone-bubble">{final_message}</div>', unsafe_allow_html=True)
    
    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not name_input or not phone_input:
            st.toast("⚠️ Please enter Name and Number")
        else:
            try:
                client = Client(get_secret("TWILIO_ACCOUNT_SID"), get_secret("TWILIO_AUTH_TOKEN"))
                client.messages.create(body=final_message, from_=get_secret("TWILIO_PHONE_NUMBER"), to=smart_format_phone(phone_input))
                st.success(f"✅ Sent to {name_input}")
                st.balloons()
                st.session_state.history.append({"Date": datetime.now().strftime("%d/%m"), "Name": name_input})
            except Exception as e:
                st.error(f"Twilio Error: {e}")

# --- TAB 2: REVIEW FEED ---
with tab2:
    if st.session_state.stats and 'reviews' in st.session_state.stats:
        reviews = st.session_state.stats['reviews']
        st.info(f"Showing last {len(reviews)} reviews from Google.")
        
        for review in reviews:
            # Extract review data (safe get)
            author = review.get('authorAttribution', {}).get('displayName', 'Anonymous')
            stars = review.get('rating', 5)
            text = review.get('text', {}).get('text', '') # Some reviews are just stars
            
            # The Card UI
            with st.container(border=True):
                st.markdown(f"**{author}** <span style='float:right'>{'⭐'*stars}</span>", unsafe_allow_html=True)
                if text:
                    st.markdown(f"_{text}_")
                    
                    # The "Draft Reply" Button
                    if st.button(f"Draft Reply", key=f"btn_{author}"):
                        with st.spinner("Writing..."):
                            genai.configure(api_key=AI_KEY)
                            model = genai.GenerativeModel('gemini-flash-latest')
                            prompt = f"Write a short, warm Australian business reply to this review: '{text}'. Sign it '- The Team'."
                            reply = model.generate_content(prompt)
                            st.text_area("Copy this:", value=reply.text, height=100)
                else:
                    st.caption("(Star rating only - no text to reply to)")
    else:
        st.warning(f"Could not find reviews for '{st.session_state.business_name}'.")
        st.caption("Tip: Ensure the Business Name in Settings matches Google Maps exactly.")

# --- TAB 3: SETTINGS ---
with tab3:
    st.markdown("### ⚙️ Settings")
    st.text_input("Business Name", value=st.session_state.business_name, disabled=True)
    
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        if "stats" in st.session_state: del st.session_state.stats
        st.rerun()
