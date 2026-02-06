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
    # AUTO-FIX: We append 'Australia' to the search to help it find local businesses
    search_query = f"{name} Australia"
    data = {"textQuery": search_query}
    
    try:
        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code == 200:
            results = resp.json()
            if results.get('places'):
                return results['places'][0]
            else:
                st.error(f"❌ Google found 0 results for: '{search_query}'")
                return None
        else:
            # SHOW THE REAL ERROR ON SCREEN
            st.error(f"❌ Google API Error: {resp.status_code}")
            st.code(resp.text) # This will tell us if it's a key issue
            return None
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

# --- STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "place_id" not in st.session_state: st.session_state.place_id = None
if "stats" not in st.session_state: st.session_state.stats = None
if "fetch_attempted" not in st.session_state: st.session_state.fetch_attempted = False

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
        st.session_state.place_id = raw_data[2] if len(raw_data) > 2 else None
        st.session_state.current_user_pass = password
        st.session_state.logged_in = True
        st.session_state.stats = None 
        st.session_state.fetch_attempted = False # Reset fetch attempt
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# --- LOAD STATS ---
if not st.session_state.stats and not st.session_state.fetch_attempted:
    st.session_state.fetch_attempted = True # Mark as tried
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
    # If we tried and failed, show a warning. If we haven't tried, show connecting.
    if st.session_state.fetch_attempted:
        st.warning
