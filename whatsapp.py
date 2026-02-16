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
RESULT_WAIT_MS = 45_000         # WhatsApp can be slow to show the number result
CHATBOX_WAIT_MS = 25_000

WAIT_AFTER_SEND_SEC = 1.5
WAIT_BETWEEN_NUMBERS_SEC = 1.2
# ==========================


def extract_and_clean_phone(value) -> str | None:
    """
    Extract digits from messy cell using regex, remove leading zeros,
    normalize:
      - if 10 digits => prefix DEFAULT_COUNTRY_CODE
      - accept 11-15 digits as-is
    Returns digits only (no +), e.g. 918949756134
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    runs = re.findall(r"\d{6,}", s)
    if not runs:
        return None

    digits = re.sub(r"\D", "", max(runs, key=len))
    digits = digits.lstrip("0")  # remove leading zeros (your requirement)
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


def open_chat_from_not_in_contacts(page, phone_digits: str) -> bool:
    """
    Uses your DOM:
      <span title="+91 89497 56134">+91 89497 56134</span>

    Strategy:
    - Wait for "Not in your contacts" (if present)
    - Find span[title] whose title/text contains our digits (ignoring spaces)
    - Click the span (or parent container)
    """
    last10 = phone_digits[-10:]  # match by last 10 digits (works with formatting)

    # optional label
    try:
        page.locator("text=Not in your contacts").wait_for(timeout=RESULT_WAIT_MS)
    except:
        pass

    # Wait for spans with title to appear
    spans = page.locator("span[title]")
    try:
        spans.first.wait_for(timeout=RESULT_WAIT_MS)
    except:
        return False

    # Find the first span whose title digits contain last10
    count = spans.count()
    for i in range(min(count, 50)):  # cap for safety
        try:
            title = spans.nth(i).get_attribute("title") or ""
            title_digits = re.sub(r"\D", "", title)
            if last10 in title_digits:
                # Click the span; if not clickable, click a parent
                try:
                    spans.nth(i).click(timeout=5000)
                    return True
                except:
                    # Parent containers are often clickable
                    parent = spans.nth(i).locator("xpath=ancestor::div[@role='gridcell' or @role='button' or @role='row'][1]")
                    if parent.count() > 0:
                        parent.first.click(timeout=5000)
                        return True
                    # fallback: click closest div
                    spans.nth(i).locator("xpath=ancestor::div[1]").click(timeout=5000)
                    return True
        except:
            continue

    return False


def send_message(page, msg: str):
    box = page.locator("div[contenteditable='true'][role='textbox']")
    box.wait_for(timeout=CHATBOX_WAIT_MS)
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
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
        )
        page = context.new_page()
        page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web to be ready (QR scan + sync may take time)...")
        wait_for_whatsapp_ready(page)
        print("✅ WhatsApp is ready. Starting automation...")

        for idx, row in df.iterrows():
            phone = row["phone_clean"]

            if not phone:
                df.at[idx, "status"] = "SKIPPED"
                df.at[idx, "note"] = "Could not extract/normalize phone"
                continue

            try:
                wait_for_whatsapp_ready(page, timeout_ms=60_000)

                if not click_new_chat(page):
                    raise RuntimeError("New chat button not found/clickable")

                if not type_in_search(page, phone):
                    raise RuntimeError("Search input not found")

                # ✅ FIXED: Click the actual span[title="+91 ..."] result
                if not open_chat_from_not_in_contacts(page, phone):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "Number row did not appear/click"
                    continue

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
        print(f"\n✅ Done. Results saved to: {out_path}")

        context.close()


if __name__ == "__main__":
    main()
