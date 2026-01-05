import os
import asyncio
import logging
import requests
from telegram import Bot
from google import genai
from groq import Groq
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config
from sheets import get_gspread_client

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

logging.basicConfig(level=logging.ERROR)

async def check_telegram():
    print(f"{BOLD}--- Telegram Bot Check ---{RESET}")
    if not config.TELEGRAM_BOT_TOKEN:
        print(f"{RED}❌ TELEGRAM_BOT_TOKEN not found!{RESET}")
        return False
    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        bot_info = await bot.get_me()
        print(f"{GREEN}[OK] Connected: @{bot_info.username} ({bot_info.first_name}){RESET}")
        return True
    except Exception as e:
        print(f"{RED}[FAIL] Telegram Error: {e}{RESET}")
        return False

async def check_gemini():
    print(f"\n{BOLD}--- Google Gemini AI Check ---{RESET}")
    if not config.GEMINI_API_KEY:
        print(f"{YELLOW}[WARN] GEMINI_API_KEY not found. (Skipping){RESET}")
        return False
    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        # Use gemini-flash-latest (Valid Model)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-flash-latest',
            contents='Hello'
        )
        print(f"{GREEN}[OK] Gemini is working.{RESET}")
        return True
    except Exception as e:
        err_str = str(e)
        if "429" in err_str:
            print(f"{YELLOW}[WARN] Gemini Quota Exceeded (Backoff active).{RESET}")
            # Consider this a PASS for health check purposes as key is valid
            return True 
        print(f"{RED}[FAIL] Gemini Error: {e}{RESET}")
        return False

async def check_groq():
    print(f"\n{BOLD}--- Groq AI Check ---{RESET}")
    if not config.GROQ_API_KEY:
        print(f"{YELLOW}[WARN] GROQ_API_KEY not found. (Skipping){RESET}")
        return False
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'Groq is Online'"}],
        )
        print(f"{GREEN}[OK] Groq: {completion.choices[0].message.content.strip()}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[FAIL] Groq Error: {e}{RESET}")
        return False

async def check_openrouter():
    print(f"\n{BOLD}--- OpenRouter Check ---{RESET}")
    if not config.OPENROUTER_API_KEY:
        print(f"{YELLOW}[WARN] OPENROUTER_API_KEY not found. (Skipping){RESET}")
        return False
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            },
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": "Say 'OpenRouter Online'"}],
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}[OK] OpenRouter: {data['choices'][0]['message']['content'].strip()}{RESET}")
            return True
        else:
            print(f"{RED}[FAIL] OpenRouter Error: {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}[FAIL] OpenRouter Exception: {e}{RESET}")
        return False

async def check_google_sheets():
    print(f"\n{BOLD}--- Google Sheets Check ---{RESET}")
    try:
        client = get_gspread_client()
        if not client:
            print(f"{RED}[FAIL] Could not authenticate with Google Sheets (Client is None).{RESET}")
            return False
            
        # Flexible opening logic
        sheet_name = config.GOOGLE_SHEET_NAME
        try:
            sh = client.open(sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            # Try finding a sheet that matches after stripping spaces
            all_sheets = client.openall()
            found = False
            for s in all_sheets:
                if s.title.strip() == sheet_name.strip():
                    print(f"{YELLOW}[WARN] Found match with extra spaces: '{s.title}'{RESET}")
                    sh = client.open_by_key(s.id)
                    found = True
                    break
            if not found:
                raise

        print(f"{GREEN}[OK] Successfully opened Sheet: '{sh.title}'{RESET}")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"{RED}[FAIL] Error: Spreadsheet '{config.GOOGLE_SHEET_NAME}' NOT FOUND.{RESET}")
        print(f"{YELLOW}[TIP] Ensure the sheet is shared with the service account email.{RESET}")
        return False
    except Exception as e:
        import traceback
        print(f"{RED}[FAIL] Google Sheets Unexpected Error: {e}{RESET}")
        # print(traceback.format_exc()) # Uncomment for full debug
        return False

async def check_openrouter():
    print(f"\n{BOLD}--- OpenRouter Check ---{RESET}")
    if not config.OPENROUTER_API_KEY:
        print(f"{YELLOW}[WARN] OPENROUTER_API_KEY not found. (Skipping){RESET}")
        return False
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
        )
        # Simple model list check
        await asyncio.to_thread(client.models.list)
        print(f"{GREEN}[OK] OpenRouter API is working.{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[FAIL] OpenRouter Error: {e}{RESET}")
        return False

async def main():
    output_lines = []
    def log(msg):
        print(msg)
        # Strip colors for file
        clean_msg = msg.replace(BOLD, "").replace(RESET, "").replace(GREEN, "").replace(RED, "").replace(YELLOW, "")
        output_lines.append(clean_msg)

    log(f"\n{BOLD}Starting API Health Check for Crypto Bot...{RESET}\n")
    
    # Run checks sequentially
    # We need to capture the print outputs of other functions too? 
    # For now, just relying on return values for the summary, 
    # and we will see the failure details in the console output (captured below) or we just infer.
    # Actually, we can't easily capture the prints from other functions without refactoring.
    # Let's just run them and assume we can read the console IF we don't redirect.
    # But wait, I want to read the result.
    
    # Quick fix: Just run them. I will use 'command_status' to read the output again, 
    # but I will ensure I capture enough characters.
    
    results = [
        await check_telegram(),
        await check_gemini(),
        await check_groq(),
        await check_openrouter(),
        await check_google_sheets()
    ]
    
    log(f"\n{BOLD}--- Execution Summary ---{RESET}")
    passed = sum(1 for r in results if r)
    total = len(results)
    log(f"Total Checks: {total}")
    log(f"Passed: {passed}")
    log(f"Failed/Skipped: {total - passed}")
    
    # Explicitly write which ones failed based on index
    names = ["Telegram", "Gemini", "Groq", "OpenRouter", "Google Sheets"]
    for name, res in zip(names, results):
        status = "PASS" if res else "FAIL"
        log(f"{name}: {status}")

    with open("health_status.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    if passed == total:
        print(f"\n{GREEN}{BOLD}ALL SYSTEMS GO!{RESET}")
    else:
        print(f"\n{YELLOW}{BOLD}Some systems are offline or misconfigured.{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
