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

# 3. Custom CSS (The UI Polish)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp {margin-top: -30px;}
            
            /* Bigger, friendlier inputs */
            .stTextInput > div > div > input {
                padding: 10px;
                font-size: 16px;
            }
            .stTextArea > div > div > textarea {
                font-size: 16px;
            }
            
            /* THE FIX: Hide the annoying 'Press Enter to submit' text */
            [data-testid="InputInstructions"] {
                display: none;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- HELPER: UNIVERSAL SECRET LOADER ---
def get_secret(key, default_value):
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default_value)

# --- HELPER: SMART PHONE FORMATTER ---
def smart_format_phone(number):
    """Auto-converts 04xx to +614xx"""
    # Remove spaces, dashes, parentheses
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Check for Australian mobile format (04...)
    if clean.startswith("04") and len(clean) == 10:
        return "+61" + clean[1:]
    
    # If they typed 412... (missed the 0)
    if clean.startswith("4") and len(clean) == 9:
        return "+61" + clean
        
    # If it's already +61...
    if clean.startswith("+"):
        return clean
        
    # Fallback: Just return what they typed (let Twilio try it)
    return clean

# 4. Initialize Session State
if "business_name" not in st.session_state:
    st.session_state.business_name = get_secret("BUSINESS_NAME", "ReviewRocket Demo")

if "review_link" not in st.session_state:
    st.session_state.review_link = get_secret("REVIEW_LINK", "https://google.com")

# 5. Security: Login Gate (Fixed Enter Key & Overlap)
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("<h1 style='text-align: center;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    
    # We use a 'form' so pressing Enter works naturally
    with st.form("login_form"):
        password = st.text_input("Enter Access Key", type="password")
        # We use a primary button that spans the width
        submit_button = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit_button:
            if password == "rocket2026":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Access Denied.")
    return False

if not check_password():
    st.stop()

# --- MAIN DASHBOARD ---

st.markdown(f"## {st.session_state.business_name} 🚀")

# Tabs Renamed for Clarity
tab1, tab2, tab3 = st.tabs(["📨 New Invite", "✍️ Reply Drafter", "⚙️ Settings"])

# --- TAB 1: SEND REQUEST (Editable!) ---
with tab1:
    with st.container(border=True):
        st.markdown("### Customer Details")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            customer_name = st.text_input("Name", placeholder="e.g. Sarah")
        with col2:
            # Simple Phone Input (No country code dropdown needed now)
            phone_raw = st.text_input("Mobile", placeholder="0412 345 678")

        st.markdown("### Message Preview")
        # Pre-fill the message but let her edit it!
        default_message = f"Hi {customer_name if customer_name else '[Name]'}, thanks for choosing {st.session_state.business_name}! Please leave us a review here: {st.session_state.review_link}"
        
        final_message = st.text_area("Edit before sending:", value=default_message, height=100)

        if st.button("Send Invite 🚀", use_container_width=True, type="primary"):
            if not customer_name or not phone_raw:
                st.warning("⚠️ Enter name and number first.")
            else:
                try:
                    # Smart Formatting
                    final_phone = smart_format_phone(phone_raw)
                    
                    # Twilio Credentials
                    sid = get_secret("TWILIO_ACCOUNT_SID", "")
                    token = get_secret("TWILIO_AUTH_TOKEN", "")
                    sender = get_secret("TWILIO_PHONE_NUMBER", "")

                    client = Client(sid, token)
                    
                    message = client.messages.create(
                        body=final_message,
                        from_=sender,
                        to=final_phone
                    )
                    st.success(f"✅ Sent to {customer_name} ({final_phone})")
                    time.sleep(2) 
                    
                except Exception as e:
                    st.error(f"Failed: {e}")

# --- TAB 2: REVIEW RESPONDER (Aussie Mode) ---
with tab2:
    st.markdown("### Reply Assistant")
    st.caption("Paste a new review below to generate a professional Aussie response.")
    
    with st.container(border=True):
        review_text = st.text_area("Paste Customer Review:", height=100, placeholder="e.g. Nicolette was amazing! Photos are beautiful...")
        
        if st.button("✨ Write Reply", use_container_width=True):
            if not review_text:
                st.warning("Paste a review first.")
            else:
                try:
                    with st.spinner("Thinking..."):
                        api_key = get_secret("GOOGLE_API_KEY", "")
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-flash-latest')
                        
                        # UPDATED PROMPT FOR AUSSIE TONE
                        prompt = f"""
                        You are the owner of {st.session_state.business_name}, an Australian business.
                        Write a warm, professional, and authentic reply to this customer review.
                        
                        Guidelines:
                        - Use Australian English spelling (e.g., 'honour', 'colour').
                        - Be friendly but professional (don't sound like a robot).
                        - Avoid overly cheesy phrases.
                        - Keep it concise (2-3 sentences max).
                        - Sign it '- The Team' or '- Nicolette'.
                        
                        Review: "{review_text}"
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown("#### Suggested Reply:")
                        st.text_area("Copy this:", value=response.text, height=150)
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- TAB 3: SETTINGS ---
with tab3:
    st.markdown("### Configuration")
    
    with st.container(border=True):
        st.text_input("Business Name", key="business_name")
        st.text_input("Google Review Link", key="review_link")
        st.caption(f"Status: {'✅ Cloud Linked' if 'BUSINESS_NAME' in st.secrets else '⚠️ Local Mode'}")

    st.markdown("---")
    
    if st.button("🔄 Reset / Update Settings", type="secondary"):
        if "business_name" in st.session_state:
            del st.session_state.business_name
        if "review_link" in st.session_state:
            del st.session_state.review_link
        st.rerun()
