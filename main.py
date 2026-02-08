import streamlit as st
import google.generativeai as genai
import os
from twilio.rest import Client
from dotenv import load_dotenv
import requests
import history_manager  # Must have history_manager.py in the same folder

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="ReviewRocket Pro", page_icon="🚀", layout="centered")

# --- LOAD SECRETS ---
load_dotenv()

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_MAPS_KEY = st.secrets["GOOGLE_MAPS_KEY"]
    
    TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID") or st.secrets.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN") or st.secrets.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER") or st.secrets.get("TWILIO_PHONE_NUMBER")
    
    USERS = st.secrets["users"]
except Exception as e:
    st.error(f"❌ Configuration Error: Missing secrets. {e}")
    st.stop()

# --- SETUP AI ---
genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNCTIONS ---

def clean_phone_number(phone):
    """Auto-formats Australian numbers to E.164"""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("04"):
        return "+61" + p[1:]
    if p.startswith("4"):
        return "+61" + p
    if not p.startswith("+"):
        return "+61" + p
    return p

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("## 🔒 Login Required")
        password = st.text_input("Password", type="password")
        if st.button("Enter"):
            if password in USERS:
                st.session_state.logged_in = True
                user_data = USERS[password].split("|")
                st.session_state.business_name = user_data[0]
                st.session_state.review_link = user_data[1]
                st.session_state.place_id = user_data[2] if len(user_data) > 2 else None
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        st.stop()

def fetch_google_reviews(place_id, api_key):
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

def generate_sms(client_name, business_name, review_link):
    prompt = f"""
    Write a short, warm SMS (under 160 chars) from '{business_name}' to '{client_name}'.
    Thank them for their business today.
    Politely ask for a 5-star review.
    End with: {review_link}
    No hashtags.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"Hi {client_name}, thanks for choosing {business_name}! We'd love a review: {review_link}"

def send_sms(to_number, body):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        msg = client.messages.create(body=body, from_=TWILIO_PHONE, to=to_number)
        return True, msg.sid
    except Exception as e:
        return False, str(e)

# --- APP START ---
check_login()

# Sidebar Info
with st.sidebar:
    st.title("🚀 ReviewRocket")
    st.write(f"Logged in as:\n**{st.session_state.business_name}**")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.title(f"Hello, {st.session_state.business_name.split()[0]}! 👋")

# Create Tabs
tab1, tab2, tab3 = st.tabs(["📨 Send Invite", "⭐ Reputation", "📜 History"])

# --- TAB 1: SEND INVITE ---
with tab1:
    st.markdown("### New Client Invite")
    
    col1, col2 = st.columns(2)
    with col1:
        # We use keys to allow clearing the form later
        c_name = st.text_input("Client Name", key="input_name")
    with col2:
        c_phone = st.text_input("Phone (e.g. 0412...)", key="input_phone")

    if st.button("✨ Draft Message", type="primary"):
        if c_name and c_phone:
            formatted_phone = clean_phone_number(c_phone)
            st.session_state.target_phone = formatted_phone
            st.session_state.target_name = c_name
            
            with st.spinner("AI is writing..."):
                st.session_state.generated_msg = generate_sms(c_name, st.session_state.business_name, st.session_state.review_link)
        else:
            st.warning("Please enter both Name and Phone.")

    # Show Preview if message is generated
    if "generated_msg" in st.session_state:
        st.info("👇 Preview your message:")
        msg_to_send = st.text_area("Edit if needed:", st.session_state.generated_msg, height=100)
        
        if st.button("🚀 SEND SMS"):
            with st.spinner("Sending..."):
                success, info = send_sms(st.session_state.target_phone, msg_to_send)
                
                if success:
                    st.success(f"✅ Sent to {st.session_state.target_name}!")
                    # Save to History
                    history_manager.add_entry(st.session_state.target_name, st.session_state.target_phone, "Sent")
                    # Clear session to reset form
                    del st.session_state.generated_msg
                else:
                    st.error(f"❌ Failed: {info}")

# --- TAB 2: REVIEWS ---
with tab2:
    st.header("Live Google Stats")
    if st.session_state.place_id:
        rating, count = fetch_google_reviews(st.session_state.place_id, GOOGLE_MAPS_KEY)
        if rating:
            c1, c2, c3 = st.columns(3)
            c1.metric("Rating", f"{rating} ⭐")
            c2.metric("Reviews", f"{count}")
            c3.success("Active")
        else:
            st.warning("Could not load stats. Check Place ID.")

# --- TAB 3: HISTORY ---
with tab3:
    st.header("Client History")
    df = history_manager.load_history()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download CSV", df.to_csv(index=False), "history.csv")
    else:
        st.info("No invites sent yet.")