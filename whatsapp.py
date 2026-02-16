import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ========= CONFIG =========
EXCEL_PATH = "numbers.xlsx"
PHONE_COLUMN = "Phone"          # your sheet column name
DEFAULT_COUNTRY_CODE = "91"     # assumes India if 10-digit after removing leading 0
MESSAGE = "Hello! This is an automated message."

USER_DATA_DIR = "wa_profile"    # persistent profile folder (keeps WhatsApp logged in)
WHATSAPP_LOAD_TIMEOUT_MS = 120_000
WAIT_AFTER_SEND_SEC = 1.5
WAIT_BETWEEN_NUMBERS_SEC = 1.2  # rate limiting / human-ish delay
# ==========================


def extract_and_clean_phone(value) -> str | None:
    """
    Extract digits from messy cell using regex, remove leading zeros,
    and normalize:
      - if 10 digits => prefix DEFAULT_COUNTRY_CODE
      - keep 11-15 digits as-is
    Returns digits only (no +), e.g. 919594820168
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    # pick the longest digit-run (handles '0959...', '+91 959...', 'Phone: 0959-...')
    runs = re.findall(r"\d{6,}", s)
    if not runs:
        return None

    digits = re.sub(r"\D", "", max(runs, key=len))
    digits = digits.lstrip("0")  # remove all leading zeros (your requirement)
    if not digits:
        return None

    if len(digits) == 10 and DEFAULT_COUNTRY_CODE:
        digits = DEFAULT_COUNTRY_CODE + digits

    if len(digits) < 10 or len(digits) > 15:
        return None

    return digits


def wait_for_whatsapp_ready(page, timeout_ms=WHATSAPP_LOAD_TIMEOUT_MS):
    """
    Wait until WhatsApp Web UI is actually ready.
    This handles slow login/sync after QR scan.
    """
    # Keep the wait condition flexible because WA DOM changes often.
    page.wait_for_function(
        """
        () => {
            const selectors = [
                "div[aria-label='Chat list']",
                "input[placeholder*='Search']",
                "button[aria-label='New chat']",
                "div[role='button'][aria-label='New chat']",
                "[data-icon='new-chat-outline']",
                "span[data-icon='new-chat-outline']"
            ];
            return selectors.some(sel => document.querySelector(sel));
        }
        """,
        timeout=timeout_ms
    )


def click_new_chat(page) -> bool:
    candidates = [
        page.locator("button[aria-label='New chat']"),
        page.locator("div[role='button'][aria-label='New chat']"),
        page.locator("[data-icon='new-chat-outline']"),
        page.locator("span[data-icon='new-chat-outline']"),
    ]
    for c in candidates:
        try:
            if c.count() > 0:
                c.first.click(timeout=5000)
                return True
        except:
            pass
    return False


def type_in_search(page, value: str) -> bool:
    # In "New chat" view there is a search field; selector varies.
    candidates = [
        page.locator("input[type='text']"),
        page.locator("div[contenteditable='true']"),
    ]
    for loc in candidates:
        try:
            loc.first.click(timeout=5000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(value, delay=35)
            return True
        except:
            continue
    return False


def click_first_result_row(page) -> bool:
    """
    In your flow, after typing an unknown number, WA shows:
      "Not in your contacts" + a row with the number
    Clicking the first list item is usually the correct action.
    """
    time.sleep(1.0)  # brief wait for results to populate
    try:
        rows = page.locator("div[role='listitem']")
        if rows.count() > 0:
            rows.nth(0).click(timeout=8000)
            return True
    except:
        pass

    # fallback: click any visible button-like item
    try:
        buttons = page.locator("div[role='button']")
        if buttons.count() > 0:
            buttons.nth(0).click(timeout=8000)
            return True
    except:
        pass

    return False


def send_message(page, msg: str):
    # Robust-ish: chat textbox is a contenteditable role=textbox
    box = page.locator("div[contenteditable='true'][role='textbox']")
    box.wait_for(timeout=20000)
    box.click()
    page.keyboard.type(msg, delay=20)
    page.keyboard.press("Enter")
    time.sleep(WAIT_AFTER_SEND_SEC)


def main():
    df = pd.read_excel(EXCEL_PATH)
    if PHONE_COLUMN not in df.columns:
        raise ValueError(f"Excel must contain a '{PHONE_COLUMN}' column")

    df["phone_clean"] = df[PHONE_COLUMN].apply(extract_and_clean_phone)
    df["status"] = ""
    df["note"] = ""

    with sync_playwright() as p:
        # Persistent context = keeps WhatsApp logged in across runs
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
        )
        page = context.new_page()
        page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web to be ready (QR scan + sync may take time)...")
        try:
            wait_for_whatsapp_ready(page)
        except PWTimeout:
            print("⚠️ WhatsApp didn't become ready in time. If QR is showing, scan it and re-run.")
            context.close()
            return

        print("✅ WhatsApp is ready. Starting automation...")

        for i, row in df.iterrows():
            phone = row["phone_clean"]

            if not phone:
                df.at[i, "status"] = "SKIPPED"
                df.at[i, "note"] = "Could not extract/normalize phone"
                continue

            try:
                # Ensure UI is still ready (helpful if WA lags mid-run)
                wait_for_whatsapp_ready(page, timeout_ms=60000)

                if not click_new_chat(page):
                    raise RuntimeError("New chat button not found/clickable")

                if not type_in_search(page, phone):
                    raise RuntimeError("Search input not found")

                if not click_first_result_row(page):
                    df.at[i, "status"] = "NOT_FOUND"
                    df.at[i, "note"] = "No result row to click"
                    continue

                send_message(page, MESSAGE)
                df.at[i, "status"] = "SENT"
                df.at[i, "note"] = "OK"

            except PWTimeout as e:
                df.at[i, "status"] = "FAILED"
                df.at[i, "note"] = f"Timeout: {str(e)[:150]}"
            except Exception as e:
                df.at[i, "status"] = "FAILED"
                df.at[i, "note"] = str(e)[:180]

            print(f"{i+1}/{len(df)} -> {phone}: {df.at[i,'status']}")
            time.sleep(WAIT_BETWEEN_NUMBERS_SEC)

        out_path = "numbers_result.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\n✅ Done. Results saved to: {out_path}")

        context.close()


if __name__ == "__main__":
    main()
