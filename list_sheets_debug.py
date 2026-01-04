import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def list_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = r"c:\Users\rajrc\Projects\GitHub\crypto_scalp_bot\credentials.json"
    
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        return

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        
        print("🔍 Searching for available spreadsheets...")
        all_sheets = client.openall()
        
        if not all_sheets:
            print("📭 No spreadsheets found. Make sure you have shared the sheet with:")
            with open(creds_file, 'r') as f:
                data = json.load(f)
                print(f"👉 {data.get('client_email')}")
            return

        print(f"✅ Found {len(all_sheets)} sheets:")
        for s in all_sheets:
            print(f" - {s.title} (ID: {s.id})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_sheets()
