import pandas as pd
import os
from datetime import datetime

HISTORY_FILE = "client_history.csv"

def load_history():
    """Loads the history from the CSV file."""
    if not os.path.exists(HISTORY_FILE):
        return pd.DataFrame(columns=["Date", "Client Name", "Phone", "Status"])
    return pd.read_csv(HISTORY_FILE)

def add_entry(name, phone, status="Sent"):
    """Adds a new client invite to the history."""
    df = load_history()
    new_entry = pd.DataFrame([{
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Client Name": name,
        "Phone": phone,
        "Status": status
    }])
    # Append safely
    df = pd.concat([new_entry, df], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False)