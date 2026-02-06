import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import time

# 1. Load Environment Variables (For Local)
load_dotenv()

# 2. Page Configuration
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")

# 3. Custom CSS
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp {margin-top: -50px;}
            .stTextInput > div > div > input {
                border-radius: 10px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- HELPER: UNIVERSAL SECRET LOADER ---
def get_secret(key, default_value):
    """Checks st.secrets first (Cloud), then os.environ (Local)."""
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default_value)

# 4. Initialize Session State
if "business_name" not in st.session_state:
    st.session_state.business_name = get_secret("BUSINESS_NAME", "ReviewRocket Demo")

if "review_link" not in st.session_state:
    st.session_state.review_link = get_secret("REVIEW_LINK", "https://google.com")

# 5. Helper: Phone Formatter
def format_phone_number(country_code, number):
    clean_number = number.replace(" ", "").replace("-", "")
    if clean_number.startswith("0"):
        clean_number = clean_number[1:]
    return f"{country_code}{clean_number}"

# 6. Security: Login Gate
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("<h1 style='text-align: center;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        password = st.text_input("Enter Access Key", type="password")
        if st.button("Login", use_container_width=True, type="primary"):
            if password == "rocket2026":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Access Denied.")
    return False

if not check_password():
    st.stop()

# --- MAIN DASHBOARD ---

st.markdown("## ReviewRocket 🚀")

tab1, tab2, tab3 = st.tabs(["📨 New Request", "⭐ Pending Reviews", "⚙️ Settings"])

# --- TAB 1: SEND REQUEST ---
with tab1:
    st.markdown("### Send Review Invite")
    
    with st.container(border=True):
        customer_name = st.text_input("Customer Name", placeholder="e.g. John Smith")
        
        col1, col2 = st.columns([1, 2.5])
        with col1:
            country_code = st.selectbox("Code", ["+61", "+1", "+44", "+64"], index=0)
        with col2:
            phone_raw = st.text_input("Mobile Number", placeholder="e.g. 0411 222 333")

        st.caption(f"📝 **Preview:** Hi [Name], thanks for choosing {st.session_state.business_name}! Please leave us a review here: {st.session_state.review_link}")

        if st.button("Send Request 🚀", use_container_width=True, type="primary"):
            if not customer_name or not phone_raw:
                st.warning("⚠️ Please fill in all fields.")
            else:
                try:
                    final_phone = format_phone_number(country_code, phone_raw)
                    
                    # Credentials
                    sid = get_secret("TWILIO_ACCOUNT_SID", "")
                    token = get_secret("TWILIO_AUTH_TOKEN", "")
                    sender = get_secret("TWILIO_PHONE_NUMBER", "")

                    client = Client(sid, token)
                    
                    msg_body = f"Hi {customer_name}, thanks for choosing {st.session_state.business_name}! Please leave us a review here: {st.session_state.review_link}"
                    
                    message = client.messages.create(
                        body=msg_body,
                        from_=sender,
                        to=final_phone
                    )
                    st.toast(f"✅ Sent to {customer_name}!", icon="🚀")
                    time.sleep(1)
                    
                except Exception as e:
                    st.error(f"Failed: {e}")

# --- TAB 2: AI BRAIN ---
with tab2:
    st.markdown("### Reply Assistant")
    with st.container(border=True):
        st.markdown("**Sarah Jenkins** • *2 hours ago*")
        st.markdown("⭐⭐⭐⭐⭐")
        st.info("'Technician was on time and very polite. Fixed the hot water system in under an hour. Highly recommend!'")
        
        if st.button("✨ Generate AI Response", use_container_width=True):
            try:
                with st.spinner("Writing reply..."):
                    api_key = get_secret("GOOGLE_API_KEY", "")
                    genai.configure(api_key=api_key)
                    
                    model = genai.GenerativeModel('gemini-flash-latest')
                    
                    prompt = f"Write a short, professional response to this review for {st.session_state.business_name}. Review: 'Technician was on time...'. Sign it '- The Team'."
                    
                    response = model.generate_content(prompt)
                    st.text_area("Copy this:", value=response.text, height=150)
            except Exception as e:
                st.error(f"AI Error: {e}")

# --- TAB 3: SETTINGS ---
with tab3:
    st.markdown("### Configuration")
    
    with st.container(border=True):
        st.text_input("Business Name", key="business_name")
        st.text_input("Google Review Link", key="review_link")
        
        # DEBUG info
        st.caption(f"System Status: {'Connected to Cloud Secrets ✅' if 'BUSINESS_NAME' in st.secrets else 'Using Default Mode ⚠️'}")

    st.markdown("---")
    
    # THE RESET BUTTON
    if st.button("🔄 Reset to Original Settings", type="secondary"):
        if "business_name" in st.session_state:
            del st.session_state.business_name
        if "review_link" in st.session_state:
            del st.session_state.review_link
        st.rerun()
