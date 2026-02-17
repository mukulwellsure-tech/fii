import re
import time
import random
import pandas as pd
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ========= CONFIG =========
EXCEL_PATH = "numbers.xlsx"
PHONE_COLUMN = "Phone"
DEFAULT_COUNTRY_CODE = "91"
MESSAGE = "Hello! This is an automated message."

USER_DATA_DIR = "wa_profile"
HEADLESS = False

WHATSAPP_LOAD_TIMEOUT_MS = 120_000
CHATBOX_WAIT_MS = 30_000
NAV_TIMEOUT_MS = 60_000

# Safer behavior controls (compliance-friendly)
MAX_SEND_PER_RUN = 25            # hard cap per run
COOLDOWN_EVERY_N_SENDS = 5       # take a longer break every N sends
COOLDOWN_RANGE_SEC = (30, 75)    # longer breaks
JITTER_RANGE_SEC = (2.5, 6.0)    # normal spacing between numbers (human-ish, not evasion)
FAIL_BACKOFF_BASE_SEC = 10       # exponential backoff base
FAIL_BACKOFF_MAX_SEC = 180       # max backoff

REQUIRE_MANUAL_CONFIRM = False   # set True to approve each send
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
                "div[role='grid'][aria-label='Chat list']",
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


def random_sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))


def click_to_chat_url(phone_digits: str, text: str | None = None) -> str:
    # Let WA open the chat directly. Text param is optional; we still type in editor for reliability.
    # NOTE: text param needs url-encoding; we avoid it and just type.
    return f"https://web.whatsapp.com/send?phone={phone_digits}"


def is_invalid_number_page(page) -> bool:
    # WhatsApp web sometimes shows an “invalid phone number” banner/dialog.
    # We keep this generic to avoid brittle matching.
    candidates = [
        "text=Phone number shared via url is invalid",
        "text=invalid phone number",
        "text=not on WhatsApp",
        "text=Invite to WhatsApp",
    ]
    for c in candidates:
        if page.locator(c).count() > 0:
            return True
    return False


def wait_for_chat_editor(page):
    # WA changes data-tab sometimes; match by role + contenteditable + placeholder
    editor = page.locator(
        "div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message']"
    )
    editor.wait_for(timeout=CHATBOX_WAIT_MS)
    return editor


def send_message(page, msg: str):
    editor = wait_for_chat_editor(page)
    editor.click(timeout=8000)
    page.keyboard.type(msg, delay=15)
    page.keyboard.press("Enter")


@dataclass
class RunStats:
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    not_found: int = 0


def main():
    df = pd.read_excel(EXCEL_PATH)
    if PHONE_COLUMN not in df.columns:
        raise ValueError(f"Excel must contain a '{PHONE_COLUMN}' column")

    df["phone_clean"] = df[PHONE_COLUMN].apply(extract_and_clean_phone)
    df["status"] = ""
    df["note"] = ""

    stats = RunStats()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=HEADLESS,
        )
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT_MS)

        page.goto("https://web.whatsapp.com")
        print("Waiting for WhatsApp Web to be ready (QR scan + sync may take time)...")
        wait_for_whatsapp_ready(page)
        print("✅ WhatsApp ready.")

        consecutive_failures = 0

        for idx, row in df.iterrows():
            phone = row["phone_clean"]

            if stats.sent >= MAX_SEND_PER_RUN:
                df.at[idx, "status"] = "STOPPED"
                df.at[idx, "note"] = f"Reached MAX_SEND_PER_RUN={MAX_SEND_PER_RUN}"
                break

            if not phone:
                df.at[idx, "status"] = "SKIPPED"
                df.at[idx, "note"] = "Bad/empty phone"
                stats.skipped += 1
                continue

            try:
                wait_for_whatsapp_ready(page, timeout_ms=60_000)

                # Open chat via Click-to-Chat
                page.goto(click_to_chat_url(phone), wait_until="domcontentloaded")

                # Give WA time to render chat UI
                random_sleep(2.0, 4.5)

                if is_invalid_number_page(page):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "Invalid / not on WhatsApp (UI indicated)"
                    stats.not_found += 1
                    consecutive_failures = 0
                    continue

                # Optional manual approval (compliance + safety)
                if REQUIRE_MANUAL_CONFIRM:
                    input(f"[MANUAL] Ready to send to {phone}. Press Enter to send...")

                send_message(page, MESSAGE)

                df.at[idx, "status"] = "SENT"
                df.at[idx, "note"] = "OK"
                stats.sent += 1
                consecutive_failures = 0

                # Normal jitter between messages
                random_sleep(*JITTER_RANGE_SEC)

                # Longer cooldown every N sends
                if stats.sent % COOLDOWN_EVERY_N_SENDS == 0:
                    cool = random.uniform(*COOLDOWN_RANGE_SEC)
                    print(f"Cooldown break: sleeping {cool:.1f}s after {stats.sent} sends.")
                    time.sleep(cool)

            except PWTimeout as e:
                stats.failed += 1
                consecutive_failures += 1
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = f"Timeout: {str(e)[:160]}"

                # Exponential backoff on failures (stability, not evasion)
                backoff = min(FAIL_BACKOFF_MAX_SEC, FAIL_BACKOFF_BASE_SEC * (2 ** (consecutive_failures - 1)))
                print(f"Timeout -> backoff {backoff}s (fail streak={consecutive_failures})")
                time.sleep(backoff)

                # Stop condition if it keeps failing
                if consecutive_failures >= 5:
                    print("Too many consecutive failures. Stopping run to avoid damage.")
                    break

            except Exception as e:
                stats.failed += 1
                consecutive_failures += 1
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = str(e)[:180]

                backoff = min(FAIL_BACKOFF_MAX_SEC, FAIL_BACKOFF_BASE_SEC * (2 ** (consecutive_failures - 1)))
                print(f"Error -> backoff {backoff}s (fail streak={consecutive_failures})")
                time.sleep(backoff)

                if consecutive_failures >= 5:
                    print("Too many consecutive failures. Stopping run to avoid damage.")
                    break

            print(f"{idx+1}/{len(df)} -> {phone}: {df.at[idx,'status']}")

        out_path = "numbers_result.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\n✅ Done. Saved results to: {out_path}")
        print(f"Stats: sent={stats.sent}, failed={stats.failed}, skipped={stats.skipped}, not_found={stats.not_found}")

        context.close()


if __name__ == "__main__":
    main()
