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

# 3. Custom CSS (Premium UI Polish)
st.markdown("""
<style>
    /* Clean up the top bar */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {margin-top: -30px;}
    
    /* Input Styling */
    .stTextInput > div > div > input {
        padding: 12px;
        font-size: 16px;
        border-radius: 12px;
    }
    
    /* The "iPhone Bubble" Preview */
    .iphone-bubble {
        background-color: #007AFF;
        color: white;
        padding: 15px;
        border-radius: 18px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 15px;
        line-height: 1.4;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Hide annoying form instructions */
    [data-testid="InputInstructions"] { display: none; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def get_secret(key, default_value):
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default_value)

def smart_format_phone(number):
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("04") and len(clean) == 10:
        return "+61" + clean[1:]
    if clean.startswith("4") and len(clean) == 9:
        return "+61" + clean
    if clean.startswith("+"):
        return clean
    return clean

# 4. Session State Init
if "history" not in st.session_state:
    st.session_state.history = []
if "business_name" not in st.session_state:
    st.session_state.business_name = get_secret("BUSINESS_NAME", "ReviewRocket Demo")
if "review_link" not in st.session_state:
    st.session_state.review_link = get_secret("REVIEW_LINK", "https://google.com")

# 5. LOGIN LOGIC (Magic Link Support)
def check_login():
    # A. Check URL for magic key (?access=rocket2026)
    query_params = st.query_params
    if "access" in query_params and query_params["access"] == "rocket2026":
        st.session_state.password_correct = True
        return True

    # B. Check Session State
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # C. Show Login Form
    st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>Reputation Management System</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        password = st.text_input("Access Key", type="password")
        submit_button = st.form_submit_button("Login", type="primary", use_container_width=True)
        if submit_button:
            if password == "rocket2026":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Incorrect Key")
    return False

if not check_login():
    st.stop()

# --- APP HEADER & INSTALL GUIDE ---
st.markdown(f"### {st.session_state.business_name} 🚀")

# The "Install App" Reminder (Dismissible)
with st.expander("📲 **Tap here to Install App**"):
    st.markdown("""
    **Don't log in again!** Add this to your home screen:
    1. Tap the **Share Icon** (iOS) or **Menu Dots** (Android).
    2. Select **'Add to Home Screen'**.
    3. It will look just like a real app.
    """)
    # Magic Link Generator
    if st.button("🔗 Create Auto-Login Link"):
        st.success("Bookmark this URL to skip login next time!")
        st.code("https://reviewrocket.streamlit.app/?access=rocket2026", language="text")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📨 Invite", "✍️ AI Reply", "⚙️ Settings"])

# --- TAB 1: SEND INVITE ---
with tab1:
    st.markdown("#### New Customer")
    col1, col2 = st.columns([1, 1.2])
    with col1:
        customer_name = st.text_input("Name", placeholder="e.g. Sarah")
    with col2:
        phone_raw = st.text_input("Mobile", placeholder="04...")

    # Dynamic Message Logic
    default_msg = f"Hi {customer_name if customer_name else '...'}, thanks for choosing us! Please leave a review here: {st.session_state.review_link}"
    
    st.markdown("###### Preview")
    # iPhone Bubble
    st.markdown(f'<div class="iphone-bubble">{default_msg}</div>', unsafe_allow_html=True)
    
    with st.expander("Edit Message Text"):
        final_message = st.text_area("Content", value=default_msg, height=100, label_visibility="collapsed")

    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not customer_name or not phone_raw:
            st.toast("⚠️ Enter name and number", icon="⚠️")
        else:
            try:
                final_phone = smart_format_phone(phone_raw)
                
                # Twilio Send
                sid = get_secret("TWILIO_ACCOUNT_SID", "")
                token = get_secret("TWILIO_AUTH_TOKEN", "")
                sender = get_secret("TWILIO_PHONE_NUMBER", "")

                client = Client(sid, token)
                client.messages.create(
                    body=final_message,
                    from_=sender,
                    to=final_phone
                )
                
                st.success(f"✅ Sent to {customer_name}")
                st.balloons()
                
                # Log to History
                st.session_state.history.append({
                    "Date": datetime.now().strftime("%d/%m %H:%M"),
                    "Name": customer_name,
                    "Phone": final_phone
                })
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: AI REPLY ---
with tab2:
    st.info("Paste a customer review below to generate a reply.")
    review_text = st.text_area("Customer Review", height=100, placeholder="Paste review here...")
    
    if st.button("Generate Reply ✨", use_container_width=True):
        if review_text:
            with st.spinner("Writing..."):
                try:
                    genai.configure(api_key=get_secret("GOOGLE_API_KEY", ""))
                    model = genai.GenerativeModel('gemini-flash-latest')
                    prompt = f"Write a warm, short Australian business reply to: '{review_text}'. Sign it '- The Team'."
                    response = model.generate_content(prompt)
                    st.text_area("Suggested Reply", value=response.text, height=150)
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- TAB 3: SETTINGS & HISTORY ---
with tab3:
    st.markdown("### ⚙️ Settings")
    with st.container(border=True):
        st.text_input("Business Name", key="business_name")
        st.text_input("Review Link", key="review_link")
        st.caption(f"Cloud Linked: {'✅ Yes' if 'BUSINESS_NAME' in st.secrets else '⚠️ No'}")
        
        if st.button("🔄 Reset Defaults", type="secondary"):
             if "business_name" in st.session_state: del st.session_state.business_name
             if "review_link" in st.session_state: del st.session_state.review_link
             st.rerun()

    st.markdown("### 📜 Recent History")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No invites sent this session.")
