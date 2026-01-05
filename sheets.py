import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config
import logging
import os
import json

logger = logging.getLogger(__name__)

def get_gspread_client():
    """Authenticates with Google Sheets via File OR Env Var JSON."""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # 1. Try Configured File Path
        if os.path.exists(config.GOOGLE_SHEETS_JSON):
            creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_SHEETS_JSON, scope)
            return gspread.authorize(creds)
            
        # 2. Try JSON String in Environment Variable
        # Sometimes config.GOOGLE_SHEETS_JSON might hold the content itself if user pasted it there
        # Or check a dedicated env var if config logic didn't capture it
        json_content = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        if json_content and json_content.strip().startswith('{'):
            try:
                creds_dict = json.loads(json_content)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                return gspread.authorize(creds)
            except json.JSONDecodeError:
                logger.warning("Env Var 'GOOGLE_SHEETS_CREDENTIALS_JSON' is not valid JSON.")

        logger.warning(f"Google Sheets Creds not found. Checked file '{config.GOOGLE_SHEETS_JSON}' and Env Var.")
        return None

    except Exception as e:
        logger.error(f"Google Sheets Auth Error: {e}")
        return None

def open_spreadsheet(client, name):
    """Opens a spreadsheet by name, with fallback for stripped titles."""
    try:
        return client.open(name)
    except gspread.exceptions.SpreadsheetNotFound:
        # Try finding a sheet that matches after stripping spaces
        all_sheets = client.openall()
        for s in all_sheets:
            if s.title.strip() == name.strip():
                logger.info(f"Found match with stripped name: '{s.title}'")
                return client.open_by_key(s.id)
        raise

def log_signal(signal_data):
    """Logs the signal to the sheet."""
    client = get_gspread_client()
    if not client:
        return

    try:
        sh = open_spreadsheet(client, config.GOOGLE_SHEET_NAME)
        # Try to find 'Signals' sheet, or use sheet1
        try:
            sheet = sh.worksheet("Signals")
        except:
            sheet = sh.sheet1
            
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

def log_closed_trade(trade_data):
    """Logs a closed trade to the 'History' worksheet."""
    client = get_gspread_client()
    if not client: return

    try:
        # Open or Create 'History' worksheet
        sh = open_spreadsheet(client, config.GOOGLE_SHEET_NAME)
        try:
            sheet = sh.worksheet("History")
        except:
            sheet = sh.add_worksheet(title="History", rows="1000", cols="20")
            # Add Header
            sheet.append_row(["ID", "Symbol", "Market", "Side", "Outcome", "PnL%", "Entry", "SL", "TP", "Close Price", "Risk%", "Open Time", "Close Time"])
        
        row = [
            trade_data.get('id', ''),
            trade_data.get('symbol', ''),
            trade_data.get('market', ''),
            trade_data.get('side', ''),
            trade_data.get('outcome', ''),
            trade_data.get('pnl_pct', 0),
            trade_data.get('entry', 0),
            trade_data.get('sl', 0),
            trade_data.get('tp', 0),
            trade_data.get('close_price', 0),
            trade_data.get('risk_pct', 0.005),
            trade_data.get('open_time', ''),
            trade_data.get('close_time', '')
        ]
        sheet.append_row(row)
        logger.info(f"Closed Trade logged to Sheets: {trade_data['symbol']}")
    except Exception as e:
        logger.error(f"Failed to log closed trade to Sheet: {e}")

def fetch_trade_history():
    """Fetches all closed trades from 'History' sheet to restore balance."""
    client = get_gspread_client()
    if not client: return []

    try:
        sh = open_spreadsheet(client, config.GOOGLE_SHEET_NAME)
        try:
            sheet = sh.worksheet("History")
        except:
            return [] # No history yet

        records = sheet.get_all_records()
        
        def safe_float(val):
            """Cleans and converts sheet value to float, handling % signs."""
            if isinstance(val, (int, float)): return float(val)
            if not val: return 0.0
            try:
                s_val = str(val).strip()
                is_pct = '%' in s_val
                # Remove symbols and commas
                clean_val = s_val.replace('%', '').replace('$', '').replace('₹', '').replace(',', '').strip()
                num = float(clean_val)
                return num / 100.0 if is_pct else num
            except:
                return 0.0

        cleaned_records = []
        for r in records:
            try:
                # Identify PnL key (Sheets might have PnL% or Pct)
                pnl_key = next((k for k in ['PnL%', 'Pct', 'pnl_pct'] if k in r), None)
                r['pnl_pct'] = safe_float(r[pnl_key]) if pnl_key else 0.0
                
                # Standard numeric fields
                r['entry'] = safe_float(r.get('Entry', r.get('entry', 0)))
                r['sl'] = safe_float(r.get('SL', r.get('sl', 0)))
                r['close_price'] = safe_float(r.get('Close Price', r.get('close_price', 0)))
                r['risk_pct'] = safe_float(r.get('Risk%', r.get('risk_pct', 0.005)))
                
                # Normalize keys to match trade_manager expectation (lowercase)
                r['market'] = r.get('Market', r.get('market', 'UNKNOWN'))
                r['side'] = r.get('Side', r.get('side', 'LONG'))
                r['outcome'] = r.get('Outcome', r.get('outcome', 'LOSS'))
                r['symbol'] = r.get('Symbol', r.get('symbol', 'UNKNOWN'))
                
                cleaned_records.append(r)
            except Exception as e:
                logger.warning(f"Skipping malformed trade record: {e}")
                continue
            
        return cleaned_records
    except Exception as e:
        logger.error(f"Failed to fetch trade history: {e}")
        return []


