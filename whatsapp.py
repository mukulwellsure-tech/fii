import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ========= CONFIG =========
EXCEL_PATH = "numbers.xlsx"
PHONE_COLUMN = "Phone"
DEFAULT_COUNTRY_CODE = "91"
MESSAGE = "Hello! This is an automated message."

USER_DATA_DIR = "wa_profile"

WHATSAPP_LOAD_TIMEOUT_MS = 120_000
RESULT_WAIT_MS = 45_000
CHATBOX_WAIT_MS = 30_000

WAIT_AFTER_SEND_SEC = 1.2
WAIT_BETWEEN_NUMBERS_SEC = 1.0
# ==========================


def extract_and_clean_phone(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip()
    runs = re.findall(r"\d{6,}", s)
    if not runs:
        return None
    digits = re.sub(r"\D", "", max(runs, key=len))
    digits = digits.lstrip("0")
    if not digits:
        return None
    if len(digits) == 10 and DEFAULT_COUNTRY_CODE:
        digits = DEFAULT_COUNTRY_CODE + digits
    if len(digits) < 10 or len(digits) > 15:
        return None
    return digits


def wait_for_whatsapp_ready(page, timeout_ms=WHATSAPP_LOAD_TIMEOUT_MS):
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
                c.first.click(timeout=8000)
                return True
        except:
            pass
    return False


def type_in_search(page, value: str) -> bool:
    candidates = [
        page.locator("input[type='text']"),
        page.locator("div[contenteditable='true']"),
    ]
    for loc in candidates:
        try:
            loc.first.click(timeout=8000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(value, delay=35)
            return True
        except:
            continue
    return False

def no_results_found(page) -> bool:
    """
    Detects WhatsApp message:
    No results found for 'xxxx'
    """
    try:
        return page.locator("text=No results found").count() > 0
    except:
        return False


def open_chat_from_not_in_contacts(page, phone_digits: str) -> bool:
    last10 = phone_digits[-10:]

    try:
        page.locator("text=Not in your contacts").wait_for(timeout=RESULT_WAIT_MS)
    except:
        pass

    spans = page.locator("span[title]")
    try:
        spans.first.wait_for(timeout=RESULT_WAIT_MS)
    except:
        return False

    count = spans.count()
    for i in range(min(count, 80)):
        try:
            title = spans.nth(i).get_attribute("title") or ""
            title_digits = re.sub(r"\D", "", title)
            if last10 in title_digits:
                # click the span (or clickable parent)
                try:
                    spans.nth(i).click(timeout=8000)
                    return True
                except:
                    parent = spans.nth(i).locator(
                        "xpath=ancestor::div[@role='button' or @role='row' or @role='gridcell'][1]"
                    )
                    if parent.count() > 0:
                        parent.first.click(timeout=8000)
                        return True
                    spans.nth(i).locator("xpath=ancestor::div[1]").click(timeout=8000)
                    return True
        except:
            continue

    return False


def send_message(page, msg: str):
    """
    FIXED: target the actual message editor element from your DOM:
      div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message'][data-tab='10']
    """
    editor = page.locator(
        "div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message'][data-tab='10']"
    )
    editor.wait_for(timeout=CHATBOX_WAIT_MS)

    # Focus properly (WA can ignore typing if not focused)
    editor.click(timeout=8000)

    # Try to set text in a reliable way:
    # (contenteditable doesn't support fill always; we do keyboard)
    page.keyboard.type(msg, delay=15)
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
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
        )
        page = context.new_page()
        page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web to be ready (QR scan + sync may take time)...")
        wait_for_whatsapp_ready(page)
        print("✅ WhatsApp ready.")

        for idx, row in df.iterrows():
            phone = row["phone_clean"]

            if not phone:
                df.at[idx, "status"] = "SKIPPED"
                df.at[idx, "note"] = "Bad/empty phone"
                continue

            try:
                wait_for_whatsapp_ready(page, timeout_ms=60_000)

                if not click_new_chat(page):
                    raise RuntimeError("New chat button not found")

                if not type_in_search(page, phone):
                    raise RuntimeError("Search input not found")

                if no_results_found(page):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "No results found"
                    continue

                if not open_chat_from_not_in_contacts(page, phone):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "Number row not clickable"
                    continue

                # Make sure chat UI is fully loaded before sending
                send_message(page, MESSAGE)

                df.at[idx, "status"] = "SENT"
                df.at[idx, "note"] = "OK"

            except PWTimeout as e:
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = f"Timeout: {str(e)[:160]}"
            except Exception as e:
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = str(e)[:180]

            print(f"{idx+1}/{len(df)} -> {phone}: {df.at[idx,'status']}")
            time.sleep(WAIT_BETWEEN_NUMBERS_SEC)

        out_path = "numbers_result.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\n✅ Done. Saved results to: {out_path}")

        context.close()


if __name__ == "__main__":
    main()
