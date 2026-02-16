import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

EXCEL_PATH = "numbers.xlsx"
PHONE_COLUMN = "Phone"          # your sheet uses "Phone"
DEFAULT_COUNTRY_CODE = "91"     # change if needed

MESSAGE = "Hello! This is an automated message."
WAIT_AFTER_SEND_SEC = 1.5

def extract_and_clean_phone(value) -> str | None:
    """
    Extract phone digits from messy input using regex and normalize:
    - extract digit runs (supports +, spaces, hyphens, text)
    - strip leading zeros
    - if 10 digits => prefix country code (default 91)
    - if already has country code (11-15 digits) => keep
    """
    if pd.isna(value):
        return None

    s = str(value).strip()

    # Find digit runs (handles '0959...', '+91 959...', 'Phone: 0959-...')
    runs = re.findall(r"\d{6,}", s)  # sequences of 6+ digits
    if not runs:
        return None

    # Choose the longest run as the most likely phone
    digits = max(runs, key=len)

    # Keep only digits (just in case)
    digits = re.sub(r"\D", "", digits)

    # Remove leading zeros (your requirement)
    digits = digits.lstrip("0")
    if not digits:
        return None

    # Normalize to E.164-like digits:
    # If it's 10 digits => assume local Indian number -> add country code
    if len(digits) == 10 and DEFAULT_COUNTRY_CODE:
        digits = DEFAULT_COUNTRY_CODE + digits

    # Basic sanity: WhatsApp expects something like 11-15 digits typically
    if len(digits) < 10 or len(digits) > 15:
        return None

    return digits

def main():
    df = pd.read_excel(EXCEL_PATH)

    if PHONE_COLUMN not in df.columns:
        raise ValueError(f"Excel must contain a '{PHONE_COLUMN}' column")

    df["phone_clean"] = df[PHONE_COLUMN].apply(extract_and_clean_phone)
    df["status"] = ""
    df["note"] = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://web.whatsapp.com")
        print("Scan the QR in WhatsApp Web, then press Enter here...")
        input()

        def click_new_chat():
            candidates = [
                page.locator("button[aria-label='New chat']"),
                page.locator("div[role='button'][aria-label='New chat']"),
                page.locator("[data-icon='new-chat-outline']"),
                page.locator("[data-icon='new-chat']"),
                page.locator("span[data-icon='new-chat-outline']"),
            ]
            for c in candidates:
                try:
                    if c.count() > 0:
                        c.first.click(timeout=3000)
                        return True
                except:
                    pass
            return False

        def type_in_search(value: str):
            # WhatsApp uses different DOMs over time; try a few robust strategies
            # First try: an input text box
            for loc in [
                page.locator("input[type='text']"),
                page.locator("div[contenteditable='true']"),
            ]:
                try:
                    loc.first.click(timeout=3000)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(value, delay=35)
                    return True
                except:
                    continue
            return False

        def click_result_for(phone_digits: str):
            # Try to click a row that contains the last 7-10 digits
            last10 = phone_digits[-10:]
            last7 = phone_digits[-7:]

            # wait a moment for results
            time.sleep(1.0)

            # Your UI shows "Not in your contacts" and then the phone row.
            # We'll attempt to click something containing the digits.
            candidates = [
                page.locator(f"text={last10}"),
                page.locator(f"text={last7}"),
                page.locator("text=Not in your contacts"),
            ]

            # If "Not in your contacts" appears, the phone row is typically below it.
            try:
                if page.locator("text=Not in your contacts").count() > 0:
                    # Click the first visible list item beneath
                    rows = page.locator("div[role='listitem']")
                    if rows.count() > 0:
                        rows.nth(0).click(timeout=5000)
                        return True
            except:
                pass

            for c in candidates:
                try:
                    if c.count() > 0:
                        c.first.click(timeout=5000)
                        return True
                except:
                    pass

            # Last resort: click first list item
            try:
                rows = page.locator("div[role='listitem']")
                if rows.count() > 0:
                    rows.nth(0).click(timeout=5000)
                    return True
            except:
                pass

            return False

        def send_message():
            # Chat textbox
            box = page.locator("div[contenteditable='true'][role='textbox']")
            box.wait_for(timeout=15000)
            box.click()
            page.keyboard.type(MESSAGE, delay=20)
            page.keyboard.press("Enter")
            time.sleep(WAIT_AFTER_SEND_SEC)

        for i, row in df.iterrows():
            phone = row["phone_clean"]

            if not phone:
                df.at[i, "status"] = "SKIPPED"
                df.at[i, "note"] = "Could not extract/normalize phone"
                continue

            try:
                if not click_new_chat():
                    raise RuntimeError("New chat button not found")

                if not type_in_search(phone):
                    raise RuntimeError("Search box not found")

                if not click_result_for(phone):
                    df.at[i, "status"] = "NOT_FOUND"
                    df.at[i, "note"] = "No clickable result for number"
                    continue

                send_message()
                df.at[i, "status"] = "SENT"
                df.at[i, "note"] = "OK"

            except PWTimeout as e:
                df.at[i, "status"] = "FAILED"
                df.at[i, "note"] = f"Timeout: {str(e)[:120]}"
            except Exception as e:
                df.at[i, "status"] = "FAILED"
                df.at[i, "note"] = str(e)[:160]

            print(f"{i+1}/{len(df)} -> {phone}: {df.at[i,'status']}")

        out_path = "numbers_result.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\n✅ Done. Saved: {out_path}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
