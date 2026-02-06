import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import time
from datetime import datetime
import pandas as pd

# 1. Load Environment Variables
load_dotenv()

# 2. Page Configuration
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")

# 3. Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {margin-top: -30px;}
    .stTextInput > div > div > input { padding: 12px; font-size: 16px; border-radius: 12px; }
    .iphone-bubble {
        background-color: #007AFF; color: white; padding: 15px; border-radius: 18px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 15px;
        line-height: 1.4; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    [data-testid="InputInstructions"] { display: none; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def get_secret(key):
    # Checks Cloud Secrets first, then Local .env
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, "")

def smart_format_phone(number):
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("04") and len(clean) == 10: return "+61" + clean[1:]
    if clean.startswith("4") and len(clean) == 9: return "+61" + clean
    if clean.startswith("+"): return clean
    return clean

# 4. Session State Init
if "history" not in st.session_state: st.session_state.history = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "business_name" not in st.session_state: st.session_state.business_name = ""
if "review_link" not in st.session_state: st.session_state.review_link = ""

# 5. MULTI-USER LOGIN SYSTEM
def check_login():
    # A. Check URL Magic Link (?access=password)
    query_params = st.query_params
    url_pass = query_params.get("access", None)
    
    if url_pass:
        validate_user(url_pass)
        return

    # B. If already logged in, skip
    if st.session_state.logged_in:
        return

    # C. Show Login Form
    st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>Reputation Management System</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        password_input = st.text_input("Access Key", type="password")
        submit_button = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit_button:
            validate_user(password_input)
            st.rerun()

def validate_user(password):
    # 1. Get the list of users from secrets
    # We try to get 'users' table, if not found, fallback to empty dict
    user_db = st.secrets.get("users", {})
    
    # 2. Check if password exists in our "Phonebook"
    if password in user_db:
        # Found them! format is "Name|Link"
        user_data = user_db[password]
        name, link = user_data.split("|")
        
        st.session_state.business_name = name
        st.session_state.review_link = link
        st.session_state.current_user_pass = password # Save for magic link
        st.session_state.logged_in = True
    else:
        st.error("Invalid Access Key")

# Run Login Check
check_login()
if not st.session_state.logged_in:
    st.stop()

# --- APP HEADER ---
st.markdown(f"### {st.session_state.business_name} 🚀")

with st.expander("📲 **Tap here to Install / Magic Link**"):
    st.markdown("""
    **Save time:** Add to home screen or bookmark the link below.
    """)
    if st.button("🔗 Create Auto-Login Link"):
        # Generates link specific to THIS user's password
        magic_link = f"https://reviewrocket.streamlit.app/?access={st.session_state.current_user_pass}"
        st.code(magic_link, language="text")
        st.success("Copy this link! It contains your unique login key.")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📨 Invite", "✍️ AI Reply", "⚙️ Settings"])

# --- TAB 1: INVITE ---
with tab1:
    col1, col2 = st.columns([1, 1.2])
    with col1: customer_name = st.text_input("Name", placeholder="e.g. Sarah")
    with col2: phone_raw = st.text_input("Mobile", placeholder="04...")

    default_msg = f"Hi {customer_name if customer_name else '...'}, thanks for choosing us! Please leave a review here: {st.session_state.review_link}"
    
    st.markdown(f'<div class="iphone-bubble">{default_msg}</div>', unsafe_allow_html=True)
    
    with st.expander("Edit Message"):
        final_message = st.text_area("Content", value=default_msg, height=100, label_visibility="collapsed")

    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not customer_name or not phone_raw:
            st.toast("⚠️ Enter name and number", icon="⚠️")
        else:
            try:
                final_phone = smart_format_phone(phone_raw)
                client = Client(get_secret("TWILIO_ACCOUNT_SID"), get_secret("TWILIO_AUTH_TOKEN"))
                client.messages.create(body=final_message, from_=get_secret("TWILIO_PHONE_NUMBER"), to=final_phone)
                
                st.success(f"✅ Sent to {customer_name}")
                st.balloons()
                st.session_state.history.append({"Date": datetime.now().strftime("%d/%m %H:%M"), "Name": customer_name})
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: AI ---
with tab2:
    review_text = st.text_area("Customer Review", height=100, placeholder="Paste review here...")
    if st.button("Generate Reply ✨", use_container_width=True):
        if review_text:
            with st.spinner("Writing..."):
                genai.configure(api_key=get_secret("GOOGLE_API_KEY"))
                model = genai.GenerativeModel('gemini-flash-latest')
                prompt = f"Write a warm, short Australian business reply for {st.session_state.business_name} to: '{review_text}'."
                response = model.generate_content(prompt)
                st.text_area("Suggested Reply", value=response.text, height=150)

# --- TAB 3: SETTINGS ---
with tab3:
    st.markdown("### ⚙️ Account Details")
    st.info(f"Logged in as: **{st.session_state.business_name}**")
    st.text_input("Business Name (Temporary)", key="business_name")
    st.text_input("Review Link (Temporary)", key="review_link")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
