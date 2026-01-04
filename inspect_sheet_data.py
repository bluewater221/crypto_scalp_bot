import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def inspect_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = r"c:\Users\rajrc\Projects\GitHub\crypto_scalp_bot\credentials.json"
    sheet_name = "Scalper_Logs"
    
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        return

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        
        print(f"🔍 Attempting to open '{sheet_name}'...")
        try:
            sh = client.open(sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ Spreadsheet '{sheet_name}' NOT FOUND by name.")
            print("🔍 Listing all sheets available to find exact name match...")
            all_sheets = client.openall()
            for s in all_sheets:
                print(f" - Found: '{s.title}' (ID: {s.id})")
                if s.title.strip() == sheet_name:
                    print(f"💡 Suggestion: The sheet has extra spaces? Opening by ID instead...")
                    sh = client.open_by_key(s.id)
                    break
            else:
                return

        print(f"✅ Successfully opened: '{sh.title}'")
        worksheets = sh.worksheets()
        print(f"📋 Worksheets found: {len(worksheets)}")
        
        for ws in worksheets:
            rows = ws.get_all_values()
            print(f" - '{ws.title}': {len(rows)} rows (including header)")
            if len(rows) > 0:
                print(f"   First row sample: {rows[0]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_sheet()
