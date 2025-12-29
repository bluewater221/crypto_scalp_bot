import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config
import logging
import os
import json

logger = logging.getLogger(__name__)

def get_gspread_client():
    """Authenticates with Google Sheets."""
    try:
        # Check if JSON file exists, if not check for ENV content
        if not os.path.exists(config.GOOGLE_SHEETS_JSON):
            logger.warning("Google Sheets JSON not found. Logging skipped.")
            return None
            
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SHEETS_JSON, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Google Sheets Auth Error: {e}")
        return None

def log_signal(signal_data):
    """Logs the signal to the sheet."""
    client = get_gspread_client()
    if not client:
        return

    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).sheet1
        # Format: Symbol, Date, Side, Entry, SL, TP, Setup
        row = [
            signal_data['symbol'],
            str(signal_data.get('timestamp', '')),
            signal_data['side'],
            signal_data['entry'],
            signal_data['stop_loss'],
            signal_data['take_profit'],
            signal_data['setup']
        ]
        sheet.append_row(row)
        logger.info(f"Signal logged to Sheets: {signal_data['symbol']}")
    except Exception as e:
        logger.error(f"Failed to log to Sheet: {e}")
