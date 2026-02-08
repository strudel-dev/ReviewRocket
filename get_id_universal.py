import streamlit as st
import requests
import re

# --- 🛠️ CONFIGURATION 🛠️ ---
# 1. Business Name (for the search)
BUSINESS_NAME = "Nicolette Jade Photography"

# 2. Google Maps Link (CRITICAL for hidden businesses)
#    Paste the full link you get when you click the business on Maps
MAPS_LINK = "https://www.google.com.au/maps/place/Nicolette+Jade+Photography/@-33.8453405,150.2712213,9z/data=!4m8!3m7!1s0x4f05ce9beb93eb2d:0x2124090e21d9bffa!8m2!3d-33.8482439!4d150.9319747"
# -----------------------------

def get_api_key():
    try:
        return st.secrets["GOOGLE_MAPS_KEY"]
    except:
        print("❌ CRITICAL: Check your .streamlit/secrets.toml file.")
        return None

def find_place():
    print(f"\n🚀 Starting Universal Search for: '{BUSINESS_NAME}'...")
    
    # --- PHASE 1: Try the Official API ---
    api_key = get_api_key()
    if api_key:
        print("📡 Contacting Google API...")
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress"
        }
        payload = {"textQuery": BUSINESS_NAME}
        
        # Add Location Bias if URL has coordinates
        coords = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', MAPS_LINK)
        if coords:
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": float(coords.group(1)), "longitude": float(coords.group(2))},
                    "radius": 500.0
                }
            }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "places" in data and len(data["places"]) > 0:
            place = data["places"][0]
            print(f"\n✅ API SUCCESS! (Standard Business)")
            print(f"📛 Name: {place['displayName']['text']}")
            print(f"📍 Address: {place['formattedAddress']}")
            print(f"🆔 Place ID: {place['id']}")
            print("-" * 40)
            return # Done!

    # --- PHASE 2: The "Hidden Business" Decoder ---
    print("\n⚠️  API did not return a result (Likely a Service Area Business).")
    print("🕵️  Decoding the URL for hidden IDs...")

    # Look for the pattern: 0x... : 0x... (This is the Hex CID)
    # in your link: ...!1s0x4f05ce9beb93eb2d:0x2124090e21d9bffa...
    match = re.search(r'(0x[a-f0-9]+):(0x[a-f0-9]+)', MAPS_LINK)
    
    if match:
        cid_part_1 = match.group(1)
        cid_part_2 = match.group(2) # This is the unique ID
        
        print(f"\n✅ DECODER SUCCESS! Found Hidden CID.")
        print(f"🔹 CID Segment: {cid_part_2}")
        print("\n👇 ACTION REQUIRED 👇")
        print("Since this business hides its address, the API blocks the ID.")
        print("Click this link to convert the CID to a Place ID instantly:")
        print(f"\n🔗 https://pleper.com/index.php?do=tools&sdo=cid_converter&cid={cid_part_2}\n")
    else:
        print("\n❌ Could not find CID in the link. Make sure you pasted the full Google Maps URL.")

if __name__ == "__main__":
    find_place()