import streamlit as st
import requests
import re

# --- CONFIGURATION --------------------------
BUSINESS_NAME = "Nicolette Jade Photography"
# Paste the map link here (Required for hidden businesses)
MAPS_LINK = "https://www.google.com.au/maps/place/Nicolette+Jade+Photography/@-33.8453405,150.2712213,9z/data=!4m8!3m7!1s0x4f05ce9beb93eb2d:0x2124090e21d9bffa!8m2!3d-33.8482439!4d150.9319747"
# --------------------------------------------

def get_api_key():
    try:
        return st.secrets["GOOGLE_MAPS_KEY"]
    except:
        return None

def brute_force_id_from_url(url):
    """
    If the API fails, this function downloads the Google Maps page
    and hunts for the ID in the raw code.
    """
    print(f"⛏️  API failed. Attempting to extract ID directly from link...")
    
    # We pretend to be a real browser so Google sends us the full data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        # Look for the pattern "ChIJ..." followed by roughly 27 random chars
        match = re.search(r'(ChIJ[\w-]{20,})', response.text)
        
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        print(f"❌ Brute force error: {e}")
        return None

def find_place():
    print(f"🔎 Searching for: {BUSINESS_NAME}")
    
    # --- METHOD 1: OFFICIAL API ---
    api_key = get_api_key()
    if api_key:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress"
        }
        payload = {"textQuery": BUSINESS_NAME}
        
        # Add bias if link has coords
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
            print(f"\n✅ API SUCCESS: Found {place['displayName']['text']}")
            print(f"🆔 Place ID: {place['id']}")
            return

    # --- METHOD 2: BRUTE FORCE (If API found nothing) ---
    found_id = brute_force_id_from_url(MAPS_LINK)
    
    if found_id:
        print(f"\n✅ BRUTE FORCE SUCCESS: Found hidden ID!")
        print(f"🆔 Place ID: {found_id}")
        print("-" * 30)
        print(f'"user_id" = "{BUSINESS_NAME}|{MAPS_LINK}|{found_id}"')
        print("-" * 30)
    else:
        print("\n❌ FAILED. Could not find ID via API or Link.")

if __name__ == "__main__":
    find_place()