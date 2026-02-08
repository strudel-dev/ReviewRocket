import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import urllib.parse
import history_manager 
import os

# --- PAGE CONFIGURATION (Mobile Optimized) ---
st.set_page_config(page_title="ReviewRocket", page_icon="🚀", layout="centered", initial_sidebar_state="collapsed")

# --- LOAD SECRETS ---
load_dotenv()

try:
    # Try loading from Streamlit secrets (Cloud) first, then environment (Local)
    if "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        USERS = st.secrets["users"]
    else:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        # For local testing without secrets.toml, you might need a fallback or just rely on secrets.toml
        # This block assumes secrets.toml exists locally too.
        pass
except:
    st.error("❌ Critical Error: Secrets are missing.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNCTIONS ---
def clean_phone(phone):
    """Formats 04xx numbers to +614xx for the link to work"""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"):
        return "+61" + p[1:]
    return p

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("## 🔒 Login")
        password = st.text_input("Password", type="password")
        if st.button("Go"):
            if password in USERS:
                st.session_state.logged_in = True
                data = USERS[password].split("|")
                st.session_state.biz_name = data[0]
                st.session_state.link = data[1]
                
                # Check for Manual Mode
                if len(data) >= 5 and data[2] == "MANUAL":
                    st.session_state.place_id = "MANUAL"
                    st.session_state.manual_rating = data[3]
                    st.session_state.manual_count = data[4]
                else:
                    st.session_state.place_id = data[2]
                
                st.rerun()
            else:
                st.error("❌ Wrong Password")
        st.stop()

def generate_sms(name, biz, link):
    prompt = f"Write a short, warm SMS (under 160 chars) from '{biz}' to '{name}'. Thank them. Ask for a 5-star review. End with: {link}"
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model.generate_content(prompt).text.strip()
    except:
        return f"Hi {name}, thanks for choosing {biz}! Review us here: {link}"

# --- APP START ---
check_login()

st.header(f"🚀 {st.session_state.biz_name}")

# Create Tabs
tab1, tab2 = st.tabs(["📲 New Invite", "📜 History"])

with tab1:
    st.write("### 1. Enter Details")
    c_name = st.text_input("Client Name")
    c_phone = st.text_input("Phone (04...)")

    if st.button("✨ Write Message", type="primary", use_container_width=True):
        if c_name and c_phone:
            st.session_state.phone = clean_phone(c_phone)
            st.session_state.name = c_name
            with st.spinner("AI writing..."):
                st.session_state.msg = generate_sms(c_name, st.session_state.biz_name, st.session_state.link)
        else:
            st.warning("Need Name & Phone")

    if "msg" in st.session_state:
        st.write("### 2. Review & Send")
        final_msg = st.text_area("", st.session_state.msg, height=100)
        
        # --- THE MAGIC MOBILE BUTTON ---
        encoded_msg = urllib.parse.quote(final_msg)
        sms_link = f"sms:{st.session_state.phone}?&body={encoded_msg}"
        
        st.markdown(f'''
            <a href="{sms_link}" target="_parent">
                <button style="
                    width: 100%; 
                    background-color: #007AFF; 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    font-size: 18px; 
                    font-weight: bold; 
                    border: none; 
                    margin-top: 10px;
                    cursor: pointer;">
                    💬 Open in Messages
                </button>
            </a>
        ''', unsafe_allow_html=True)

        if st.button("✅ I Sent It (Save to History)", use_container_width=True):
            history_manager.add_entry(st.session_state.name, st.session_state.phone)
            st.success("Saved!")
            del st.session_state.msg

with tab2:
    df = history_manager.load_history()
    st.dataframe(df, use_container_width=True)