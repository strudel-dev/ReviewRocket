import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import urllib.parse
import history_manager 
import os
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ReviewRocket", 
    page_icon="🚀", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- V3 CSS: SAFE & HIGH CONTRAST ---
st.markdown("""
    <style>
    /* 1. Global Background (Matches config.toml) */
    .stApp {
        background-color: #f0f2f6;
    }

    /* 2. Card Container (White Box) */
    div.block-container {
        background-color: #ffffff;
        padding: 2rem 2rem 4rem 2rem;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        max-width: 600px;
        margin: auto;
    }

    /* 3. Inputs - Apple Style */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #333333 !important;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 12px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #007AFF;
        box-shadow: 0 0 0 2px rgba(0,122,255,0.2);
    }
    
    /* 4. Text Visibility Safety */
    h1, h2, h3, p, li, .stMarkdown {
        color: #333333 !important;
    }
    
    /* 5. Metrics (Reputation) */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #eee;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        color: #666 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #333 !important;
    }

    /* 6. Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f3f5;
        border-radius: 8px;
        padding: 8px 16px;
        color: #555 !important;
        border: none;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007AFF !important;
        color: white !important;
    }

    /* Hide Streamlit Bloat */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- LOAD SECRETS ---
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

# --- LOGIC FUNCTIONS ---
def clean_phone(phone):
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"):
        return "+61" + p[1:]
    return p

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        # Centered Login Card
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<h2 style='text-align: center;'>🔐 Login</h2>", unsafe_allow_html=True)
            password = st.text_input("Access Code", type="password", label_visibility="collapsed", placeholder="Enter Password")
            if st.button("Unlock Dashboard", use_container_width=True):
                if password in USERS:
                    st.session_state.logged_in = True
                    data = USERS[password].split("|")
                    st.session_state.biz_name = data[0]
                    st.session_state.link = data[1]
                    
                    if len(data) >= 5 and data[2] == "MANUAL":
                        st.session_state.place_id = "MANUAL"
                        st.session_state.manual_rating = data[3]
                        st.session_state.manual_count = data[4]
                    else:
                        st.session_state.place_id = data[2]
                    st.rerun()
                else:
                    st.error("❌ Invalid Code")
        st.stop()

def fetch_google_reviews(place_id, api_key):
    if place_id == "MANUAL":
        return st.session_state.manual_rating, st.session_state.manual_count
    if not place_id or place_id == "NULL":
        return None, None
    
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=rating,user_ratings_total&key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if "result" in data:
            return data["result"].get("rating", 0.0), data["result"].get("user_ratings_total", 0)
    except:
        pass
    return None, None

def generate_sms(name, biz, link):
    prompt = f"Write a short, warm, professional SMS (under 160 chars) from '{biz}' to '{name}'. Thank them for their business today. Ask for a 5-star review. End with: {link}"
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model.generate_content(prompt).text.strip()
    except:
        return f"Hi {name}, thanks for choosing {biz}! We'd love your feedback: {link}"

# --- APP LAYOUT ---
check_login()

# Header Area
st.markdown(f"<h1 style='text-align: center; margin-bottom: 5px;'>🚀 {st.session_state.biz_name}</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666; font-size: 14px; margin-bottom: 25px;'>Reputation Management System</p>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["✨ New Invite", "📊 Reputation", "📜 History"])


# --- TAB 1: SMART WIZARD ---
with tab1:
    # LOGIC: If we have a message, show STEP 2. If not, show STEP 1.
    
    # --- STEP 2: REVIEW & SEND (The "Action" Screen) ---
    if "msg" in st.session_state:
        st.markdown("### ✅ Ready to Send")
        
        # 1. The Message Preview (Editable)
        final_msg = st.text_area("Message Preview:", st.session_state.msg, height=120)
        
        # 2. The Magic Link
        encoded_msg = urllib.parse.quote(final_msg)
        sms_link = f"sms:{st.session_state.phone}?body={encoded_msg}"
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 3. BIG PRIMARY ACTION BUTTON
        # We use st.link_button because it works perfectly on mobile
        st.link_button(
            label="💬 Open in Messages App", 
            url=sms_link, 
            type="primary", 
            use_container_width=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4. Secondary Actions (Grid Layout)
        col_done, col_edit = st.columns(2)
        
        with col_done:
            # "Sent" button clears the state and goes back to Step 1
            if st.button("✅ Mark Sent", use_container_width=True):
                history_manager.add_entry(st.session_state.name, st.session_state.phone)
                st.toast("Saved to History!", icon="🎉")
                del st.session_state.msg
                st.rerun()

        with col_edit:
            # "Edit" button just clears the message to go back, but keeps name/phone
            if st.button("🔄 Start Over", use_container_width=True):
                del st.session_state.msg
                st.rerun()

    # --- STEP 1: INPUT DETAILS (The "Start" Screen) ---
    else:
        st.markdown("### 👤 New Invite")
        
        with st.form("invite_form", clear_on_submit=False):
            # Pre-fill if we hit "Start Over"
            default_name = st.session_state.get("name", "")
            # We don't pre-fill phone usually for privacy, but we can:
            # default_phone = st.session_state.get("phone", "")
            
            c_name = st.text_input("Client Name", value=default_name, placeholder="e.g. John Smith")
            c_phone = st.text_input("Mobile Number", placeholder="e.g. 0412 345 678")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # The Trigger
            submitted = st.form_submit_button("✨ Draft Message", type="primary", use_container_width=True)
            
            if submitted:
                if c_name and c_phone:
                    st.session_state.phone = clean_phone(c_phone)
                    st.session_state.name = c_name
                    with st.spinner("AI is writing..."):
                        st.session_state.msg = generate_sms(c_name, st.session_state.biz_name, st.session_state.link)
                    st.rerun() # FORCE RELOAD TO SWITCH TO STEP 2
                else:
                    st.warning("⚠️ Please enter Name and Phone")

# --- TAB 2: REPUTATION ---
with tab2:
    st.markdown("### Live Performance")
    rating, count = fetch_google_reviews(st.session_state.place_id, GOOGLE_MAPS_KEY)
    
    if rating:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Google Rating", f"{rating} ⭐", delta="Excellent", delta_color="normal")
        with col2:
            st.metric("Total Reviews", f"{count}", delta="+1 this week") # Placeholder delta
        
        st.markdown(f"""
        <div style='background-color: #e8f5e9; padding: 15px; border-radius: 10px; border-left: 5px solid #4caf50; margin-top: 20px;'>
            <h4 style='margin:0; color: #2e7d32;'>Status: Healthy</h4>
            <p style='margin:0; font-size: 14px; color: #666;'>Your business is appearing correctly on Maps.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Could not load stats. Check Place ID.")

# --- TAB 3: HISTORY ---
with tab3:
    st.markdown("### Sent Invites")
    df = history_manager.load_history()
    
    # Styled Dataframe
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn("Time Sent", format="D MMM, HH:mm"),
            "Name": "Client",
            "Phone": "Mobile"
        }
    )