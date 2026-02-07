import streamlit as st
import requests
import os
import google.generativeai as genai
from urllib.parse import quote

# 1. SETUP & STYLE
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")

st.markdown("""
<style>
    .stApp {margin-top: -30px;}
    
    /* The "Native Send" Button Style */
    .sms-button {
        display: inline-block;
        background-color: #007AFF; /* iPhone Blue */
        color: white;
        padding: 12px 24px;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 12px;
        width: 100%;
        font-family: -apple-system, sans-serif;
        font-weight: 500;
        margin-top: 10px;
    }
    .sms-button:hover { background-color: #0056b3; color: white; }
    
    /* Other Styles */
    .review-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .iphone-bubble { background-color: #E9E9EB; color: black; padding: 15px; border-radius: 18px; margin-bottom: 10px; font-family: sans-serif; }
</style>
""", unsafe_allow_html=True)

# 2. KEY LOADER
def get_secret(key):
    if key in st.secrets: return st.secrets[key]
    return os.environ.get(key, None)

# 3. GOOGLE MAPS & AI (Same as before)
def fetch_stats(place_id, api_key):
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

# 4. STATE
if "history" not in st.session_state: st.session_state.history = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# 5. LOGIN
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
    if "users" in st.secrets and password in st.secrets["users"]:
        raw = st.secrets["users"][password].split("|")
        st.session_state.business_name = raw[0]
        st.session_state.review_link = raw[1]
        st.session_state.place_id = raw[2] if len(raw) > 2 else None
        st.session_state.logged_in = True
    else:
        st.error("Invalid Key")

check_login()
if not st.session_state.logged_in: st.stop()

# 6. DASHBOARD
st.markdown(f"### {st.session_state.business_name}")

# Fetch Stats
stats = fetch_stats(st.session_state.place_id, get_secret("GOOGLE_MAPS_KEY"))

if stats:
    c1, c2, c3 = st.columns(3)
    c1.metric("Rating", f"{stats.get('rating', 'N/A')} ⭐")
    c2.metric("Reviews", f"{stats.get('userRatingCount', 0)}")
    c3.metric("Invites Sent", len(st.session_state.history))
st.divider()

# 7. TABS
tab1, tab2, tab3 = st.tabs(["📲 Send (Native)", "💬 Reviews", "⚙️ Settings"])

# --- TAB 1: NATIVE SEND ---
with tab1:
    st.caption("Generate a text and open your phone's message app.")
    
    # Simple Input (Just Name)
    name = st.text_input("Client Name", placeholder="e.g. Sarah")
    
    # Pre-filled Message
    default_msg = f"Hi {name if name else '...'}, thanks for choosing {st.session_state.business_name}! Could you leave us a quick review? It really helps: {st.session_state.review_link}"
    
    # Editable box
    msg_content = st.text_area("Message", value=default_msg, height=100)
    
    # THE MAGIC LINK GENERATOR
    # We encode the message so it works in a URL
    encoded_msg = quote(msg_content)
    
    # This HTML button opens the native SMS app
    html_button = f"""
    <a href="sms:?&body={encoded_msg}" class="sms-button" target="_blank">
       💬 Open in Messages
    </a>
    """
    
    # Show the button
    st.markdown(html_button, unsafe_allow_html=True)
    
    # Tracking Button (Optional)
    if st.button("Mark as Sent (For Stats)"):
        if name:
            st.session_state.history.append({"Name": name})
            st.success(f"Tracked invite to {name}!")
            st.rerun()
        else:
            st.toast("Enter a name first")

# --- TAB 2: AI REVIEWS ---
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
                        prompt = f"Write a short, warm Australian reply for {st.session_state.business_name} to: '{text}'"
                        try:
                            reply = model.generate_content(prompt)
                            st.text_area("Copy this:", value=reply.text)
                        except:
                            st.error("AI Error")
    else:
        st.info("No reviews found.")

# --- TAB 3: SETTINGS ---
with tab3:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
