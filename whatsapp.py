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
RESULT_WAIT_MS = 20_000          # reduced (was 45s)
CHATBOX_WAIT_MS = 15_000         # reduced (was 30s)

WAIT_AFTER_SEND_SEC = 0.25       # reduced (was 1.2s)
WAIT_BETWEEN_NUMBERS_SEC = 0.25  # reduced (was 1.0s)
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
            page.keyboard.type(value, delay=20)  # faster typing
            return True
        except:
            continue
    return False


def no_results_found(page, raw_query_digits: str) -> bool:
    """
    Detect:
      No results found for '1234567890'
    WhatsApp may show the number with or without country code, so we just look for
    the key phrase and any quotes.
    """
    # Fast check without waiting
    if page.locator("text=No results found").count() == 0:
        return False

    # If it exists, confirm it refers to our search (best-effort)
    # We match last 10 digits because that's what user sees most often.
    last10 = raw_query_digits[-10:]
    msg = page.locator("text=No results found").first
    try:
        # Expand nearby text content
        container = msg.locator("xpath=ancestor::div[1]")
        txt = container.inner_text(timeout=1000)
        digits_in_txt = re.sub(r"\D", "", txt)
        return (last10 in digits_in_txt) or ("No results found" in txt)
    except:
        return True


def open_chat_from_not_in_contacts(page, phone_digits: str) -> bool:
    """
    Click the search result row that is rendered as:
      <span title="+91 89497 56134">+91 89497 56134</span>
    """
    last10 = phone_digits[-10:]

    # Wait for either: spans appear OR "No results found" appears
    t0 = time.time()
    while (time.time() - t0) * 1000 < RESULT_WAIT_MS:
        if no_results_found(page, phone_digits):
            return False
        if page.locator("span[title]").count() > 0:
            break
        time.sleep(0.15)

    spans = page.locator("span[title]")
    if spans.count() == 0:
        return False

    count = spans.count()
    for i in range(min(count, 80)):
        try:
            title = spans.nth(i).get_attribute("title") or ""
            title_digits = re.sub(r"\D", "", title)
            if last10 in title_digits:
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
    editor = page.locator(
        "div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message'][data-tab='10']"
    )
    editor.wait_for(timeout=CHATBOX_WAIT_MS)
    editor.click(timeout=8000)
    page.keyboard.type(msg, delay=10)  # faster typing
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

        print("Waiting for WhatsApp Web to be ready...")
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

                # ✅ NEW: handle "No results found for '...'"
                if no_results_found(page, phone):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "No results found"
                    print(f"{idx+1}/{len(df)} -> {phone}: NOT_FOUND")
                    time.sleep(WAIT_BETWEEN_NUMBERS_SEC)
                    continue

                # Try to open the number result
                opened = open_chat_from_not_in_contacts(page, phone)
                if not opened:
                    # If not opened because of no results, mark NOT_FOUND; otherwise generic NOT_FOUND
                    if no_results_found(page, phone):
                        df.at[idx, "status"] = "NOT_FOUND"
                        df.at[idx, "note"] = "No results found"
                    else:
                        df.at[idx, "status"] = "NOT_FOUND"
                        df.at[idx, "note"] = "Number row not clickable/visible"
                    print(f"{idx+1}/{len(df)} -> {phone}: {df.at[idx,'status']}")
                    time.sleep(WAIT_BETWEEN_NUMBERS_SEC)
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
