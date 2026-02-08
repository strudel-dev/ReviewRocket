import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import urllib.parse
import history_manager 
import os
import requests
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ReviewRocket", 
    page_icon="🚀", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- V6 PREMIUM CSS & UI POLISH ---
st.markdown("""
    <style>
    /* Global App Styling */
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3 { color: #1a1a1a !important; font-family: 'Inter', sans-serif; }
    p, div, span { color: #444; }

    /* The Main "Card" */
    div.block-container {
        background: white; 
        padding: 2rem; 
        border-radius: 24px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.06); 
        max-width: 550px; 
        margin: auto;
    }

    /* Modern Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: #f1f3f5; border-radius: 50px; padding: 6px 16px;
        color: #666; font-size: 14px; font-weight: 600; border: none;
    }
    .stTabs [aria-selected="true"] { background: #222 !important; color: white !important; }

    /* Inputs - Apple Style */
    .stTextInput input {
        background: #f8f9fa !important; border: 1px solid #e9ecef;
        border-radius: 12px; padding: 12px; color: #333 !important;
    }
    .stTextInput input:focus { border-color: #222; }

    /* Review Feed Styling */
    .review-card {
        background: white; border: 1px solid #eee; padding: 16px;
        border-radius: 16px; margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .review-badge-high { background: #e6fcf5; color: #0ca678; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .review-badge-low { background: #fff5f5; color: #fa5252; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SETUP & SECRETS ---
load_dotenv()

try:
    if "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        GOOGLE_MAPS_KEY = st.secrets["GOOGLE_MAPS_KEY"]
        USERS = st.secrets["users"]
    else:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")
except:
    st.error("❌ Critical Error: Secrets are missing.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- CORE FUNCTIONS ---

def clean_phone(phone):
    """Formats 04xx numbers to +614xx for reliable SMS links"""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"): return "+61" + p[1:]
    return p

def check_login():
    """Handles Login for both Manual and Auto accounts"""
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.markdown("<br><h2 style='text-align:center'>Welcome Back</h2>", unsafe_allow_html=True)
        password = st.text_input("Password", type="password", label_visibility="collapsed")
        
        if st.button("Log In", type="primary", use_container_width=True):
            if password in USERS:
                st.session_state.logged_in = True
                data = USERS[password].split("|")
                st.session_state.biz_name = data[0]
                st.session_state.link = data[1]
                
                # Detect Manual Mode vs Auto Mode
                if len(data) >= 5 and data[2] == "MANUAL":
                    st.session_state.place_id = "MANUAL"
                    st.session_state.manual_rating = data[3]
                    st.session_state.manual_count = data[4]
                else:
                    st.session_state.place_id = data[2]
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

def fetch_reviews(place_id, api_key):
    """Fetches Live Google Reviews"""
    if place_id == "MANUAL": return "MANUAL", []
    
    # We fetch 'reviews' and 'url' to enable the Deep Link feature
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=rating,user_ratings_total,reviews,url&key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if "result" in data: 
            return data["result"], data["result"].get("reviews", [])
    except: 
        pass
    return None, []

def generate_sms(name, biz, link):
    """Uses AI to write the text"""
    prompt = f"Write 1 short SMS (max 140 chars) from '{biz}' to '{name}'. Thank them. Ask for 5 stars. Link: {link}"
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model.generate_content(prompt).text.strip()
    except:
        return f"Hi {name}, thanks for choosing {biz}! Review here: {link}"

# --- APP START ---
check_login()

# Header
st.markdown(f"<h2 style='margin-bottom:0px;'>🚀 {st.session_state.biz_name}</h2>", unsafe_allow_html=True)
st.caption("Reputation Manager")

# Tabs
tab1, tab2, tab3 = st.tabs(["New Invite", "Reviews & SEO", "History"])

# --- TAB 1: THE WIZARD ---
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # STATE 1: DRAFTING
    if "msg" not in st.session_state:
        st.markdown("### ✉️ Draft New Message")
        with st.form("invite"):
            c_name = st.text_input("Client Name", placeholder="Jane Doe")
            c_phone = st.text_input("Mobile Number", placeholder="04...")
            
            # Action: Just generates, does NOT save yet
            if st.form_submit_button("✨ Draft Message", type="primary", use_container_width=True):
                if c_name and c_phone:
                    st.session_state.phone = clean_phone(c_phone)
                    st.session_state.name = c_name
                    with st.spinner("Drafting..."):
                        st.session_state.msg = generate_sms(c_name, st.session_state.biz_name, st.session_state.link)
                    st.rerun()
                else:
                    st.warning("Enter Name & Phone")

    # STATE 2: SENDING & CONFIRMING
    else:
        st.info("Draft Ready! Click the blue button to send.")
        
        # Preview Box
        final_msg = st.text_area("Preview:", st.session_state.msg, height=100)
        encoded_msg = urllib.parse.quote(final_msg)
        sms_link = f"sms:{st.session_state.phone}?body={encoded_msg}"
        
        # 1. THE SEND BUTTON (Opens Phone App)
        st.link_button("💬 Open Messages App", url=sms_link, type="primary", use_container_width=True)
        
        # 2. THE FALLBACK (Restored in V6)
        with st.expander("Link didn't work?"):
            st.code(final_msg, language=None)
            st.caption("Copy the text above and paste it manually.")

        st.markdown("---")
        
        # 3. THE CONFIRMATION
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ I Sent It", use_container_width=True):