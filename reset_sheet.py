import sheets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_history():
    logger.info("Connecting to Google Sheets...")
    client = sheets.get_gspread_client()
    if not client:
        logger.error("Failed to connect to Sheets.")
        return

    try:
        sh = sheets.open_spreadsheet(client, sheets.config.GOOGLE_SHEET_NAME)
        worksheet = sh.worksheet("History")
        
        # Clear all content but keep header
        logger.info("Clearing History sheet content...")
        # Get header
        header = worksheet.row_values(1)
        
        # Clear sheet
        worksheet.clear()
        
        # Restore header
        if header:
            worksheet.append_row(header)
        else:
            worksheet.append_row(["ID", "Symbol", "Market", "Side", "Outcome", "PnL%", "Entry", "SL", "TP", "Close Price", "Risk%", "Open Time", "Close Time"])
            
        logger.info("✅ History sheet cleared successfully! Balance will reset to Initial Capital.")
        
    except Exception as e:
        logger.error(f"Error clearing sheet: {e}")

if __name__ == "__main__":
    reset_history()
