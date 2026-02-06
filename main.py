import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import time
import pandas as pd
from datetime import datetime

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
        border-radius: 8px;
    }
    
    /* Success Message Styling */
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        border-radius: 10px;
    }
    
    /* The "iPhone Bubble" Preview */
    .iphone-bubble {
        background-color: #007AFF;
        color: white;
        padding: 15px;
        border-radius: 18px;
        font-family: sans-serif;
        font-size: 15px;
        line-height: 1.4;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        max-width: 80%;
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

# 4. Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []

if "business_name" not in st.session_state:
    st.session_state.business_name = get_secret("BUSINESS_NAME", "ReviewRocket Demo")

if "review_link" not in st.session_state:
    st.session_state.review_link = get_secret("REVIEW_LINK", "https://google.com")

# 5. Login Gate
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey; margin-bottom: 30px;'>Reputation Management System</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        password = st.text_input("Access Key", type="password", placeholder="Enter password...")
        submit_button = st.form_submit_button("Login", type="primary", use_container_width=True)
        if submit_button:
            if password == "rocket2026":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Incorrect Key")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR (SETTINGS) ---
with st.sidebar:
    st.title("⚙️ Settings")
    st.text_input("Business Name", key="business_name")
    st.text_input("Review Link", key="review_link")
    
    st.divider()
    
    st.caption(f"Status: {'✅ Cloud Linked' if 'BUSINESS_NAME' in st.secrets else '⚠️ Local Mode'}")
    
    if st.button("🔄 Reset Defaults", type="secondary", use_container_width=True):
        if "business_name" in st.session_state: del st.session_state.business_name
        if "review_link" in st.session_state: del st.session_state.review_link
        st.rerun()

# --- MAIN APP ---
st.title(f"{st.session_state.business_name}")

tab1, tab2, tab3 = st.tabs(["📨 Send Invite", "✍️ Reply AI", "📜 History"])

# --- TAB 1: SEND INVITE ---
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        customer_name = st.text_input("Customer Name", placeholder="e.g. Sarah")
    with col2:
        phone_raw = st.text_input("Mobile Number", placeholder="04...")

    # Dynamic Message Logic
    default_msg = f"Hi {customer_name if customer_name else '...'}, thanks for choosing us! Please leave a review here: {st.session_state.review_link}"
    
    st.markdown("###### 👇 Message Preview")
    
    # The Visual "iPhone" Bubble
    st.markdown(f'<div class="iphone-bubble">{default_msg}</div>', unsafe_allow_html=True)
    
    # Hidden editable box (optional, keeps UI clean)
    with st.expander("Edit Message Text"):
        final_message = st.text_area("Content", value=default_msg, height=100, label_visibility="collapsed")

    if st.button("Send Invite 🚀", type="primary", use_container_width=True):
        if not customer_name or not phone_raw:
            st.toast("⚠️ Please enter a name and number", icon="⚠️")
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
                
                # Success Logic
                st.success(f"✅ Sent to {customer_name}")
                st.balloons() # A little dopamine hit
                
                # Log to History
                st.session_state.history.append({
                    "Date": datetime.now().strftime("%H:%M"),
                    "Name": customer_name,
                    "Phone": final_phone,
                    "Status": "Sent"
                })
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: AI REPLY ---
with tab2:
    st.info("Paste a customer review below to generate a professional reply.")
    review_text = st.text_area("Customer Review", height=100, placeholder="Paste review here...")
    
    if st.button("Generate Reply ✨", use_container_width=True):
        if review_text:
            with st.spinner("Thinking..."):
                try:
                    genai.configure(api_key=get_secret("GOOGLE_API_KEY", ""))
                    model = genai.GenerativeModel('gemini-flash-latest')
                    prompt = f"Write a warm, short Australian business reply to: '{review_text}'. Sign it '- The Team'."
                    response = model.generate_content(prompt)
                    st.text_area("Suggested Reply", value=response.text, height=150)
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- TAB 3: HISTORY ---
with tab3:
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No messages sent this session.")
