import streamlit as st
import os
from dotenv import load_dotenv
from twilio.rest import Client
import google.generativeai as genai
import time

# 1. Load Environment Variables
load_dotenv()

# 2. Page Configuration (Must be first)
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered")

# 3. Custom CSS for "App-like" feel
# This removes the top bar and footer, and tightens the spacing.
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp {margin-top: -50px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 4. Helper: Phone Number Formatter
def format_phone_number(country_code, number):
    # Remove spaces and dashes
    clean_number = number.replace(" ", "").replace("-", "")
    # Remove leading zero if present (e.g. 0411 -> 411)
    if clean_number.startswith("0"):
        clean_number = clean_number[1:]
    return f"{country_code}{clean_number}"

# 5. Security: Login Gate
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Login Screen UI
    st.markdown("<h1 style='text-align: center;'>ReviewRocket 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Reputation Management System</p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        password = st.text_input("Enter Access Key", type="password")
        if st.button("Login", use_container_width=True):
            if password == "rocket2026":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Access Denied.")
    return False

if not check_password():
    st.stop()

# --- MAIN DASHBOARD ---

# Header
st.markdown("## ReviewRocket 🚀")

# Tabs
tab1, tab2 = st.tabs(["📨 New Request", "⭐ Pending Reviews"])

# --- TAB 1: SEND REQUEST ---
with tab1:
    st.markdown("### Send Review Invite")
    
    # The "Card" Container
    with st.container(border=True):
        customer_name = st.text_input("Customer Name", placeholder="e.g. John Smith")
        
        # Phone Input Layout: [Code] [Number]
        col1, col2 = st.columns([1, 2.5])
        with col1:
            country_code = st.selectbox(
                "Code", 
                ["+61", "+1", "+44", "+64"], # Add more as needed
                index=0 # Default to +61 (Aus)
            )
        with col2:
            phone_raw = st.text_input("Mobile Number", placeholder="e.g. 0411 222 333")

        # Send Button
        if st.button("Send Request 🚀", use_container_width=True, type="primary"):
            if not customer_name or not phone_raw:
                st.warning("⚠️ Please fill in all fields.")
            else:
                try:
                    # Format the number
                    final_phone = format_phone_number(country_code, phone_raw)
                    
                    # Twilio Logic
                    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
                    
                    message = client.messages.create(
                        body=f"Hi {customer_name}, thanks for choosing us! Please leave a 5-star review here: https://reviewrocket.com/review",
                        from_=os.environ["TWILIO_PHONE_NUMBER"],
                        to=final_phone
                    )
                    # Use a Toast notification (looks cleaner)
                    st.toast(f"✅ SMS sent to {customer_name}!", icon="🚀")
                    time.sleep(1) # Give user time to see it
                    
                except Exception as e:
                    st.error(f"Failed: {e}")

# --- TAB 2: AI BRAIN ---
with tab2:
    st.markdown("### Reply Assistant")
    
    with st.container(border=True):
        # Header for the review card
        st.markdown("**Sarah Jenkins** • *2 hours ago*")
        st.markdown("⭐⭐⭐⭐⭐")
        st.info("'Technician was on time and very polite. Fixed the hot water system in under an hour. Highly recommend!'")
        
        if st.button("✨ Generate AI Response", use_container_width=True):
            try:
                with st.spinner("AI is writing..."):
                    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
                    # Using the stable 'latest' model for Free Tier
                    model = genai.GenerativeModel('gemini-flash-latest')
                    
                    prompt = "Write a polite, professional, and short response to this customer review for a plumbing business: 'Technician was on time and very polite. Fixed the hot water system in under an hour. Highly recommend!'. Sign it '- The Team'."
                    
                    response = model.generate_content(prompt)
                    
                    st.markdown("#### Suggested Reply:")
                    st.text_area("Copy this:", value=response.text, height=150)
                    st.toast("Response Generated!", icon="✨")
                    
            except Exception as e:
                st.error(f"AI Error: {e}")