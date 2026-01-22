# =====================================================
# GOOGLE MAPS DISTRIBUTOR SCRAPER – ACTUALLY WORKING
# =====================================================

import time
import random
import re
import os
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# ================= USER INPUT =================
BUSINESS_NAME = "MRF"
STATE_NAME = "Rajasthan"
OUTPUT_FILE = f"{BUSINESS_NAME}_Distributors_{STATE_NAME}.xlsx"

CITIES = ["Jodhpur", "Jaipur"]
KEYWORDS = ["authorized dealer distributor", "Tyres Exclusive", "T&S"]

WAIT_MIN = 1.2
WAIT_MAX = 2.5

# ================= DRIVER =================
def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ================= UTIL =================
def normalize_phone(text):
    digits = re.sub(r"\D", "", text)
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else ""

def extract_phone(driver, timeout=8):
    """
    Extract phone from Google Maps popup layer (AeaXub → Io6YTe)
    Handles spaced numbers like: 093090 08880
    """

    try:
        phone_el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.AeaXub div.Io6YTe")
            )
        )
        raw = phone_el.text.strip()
        return normalize_phone(raw)

    except:
        pass

    # Fallback 1: phone button aria-label
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(@aria-label,'Phone')]")
        return normalize_phone(btn.get_attribute("aria-label"))
    except:
        pass

    # Fallback 2: regex scan (last resort)
    try:
        match = re.search(r'(\+91[\s-]?)?\d[\d\s]{8,}\d', driver.page_source)
        if match:
            return normalize_phone(match.group())
    except:
        pass

    return ""


def click_back(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Back']"))
        ).click()
        time.sleep(1.2)
    except:
        driver.back()
        time.sleep(1.5)

def save_rows(rows):
    if not rows:
        return
    df_new = pd.DataFrame(rows)
    if os.path.exists(OUTPUT_FILE):
        df_old = pd.read_excel(OUTPUT_FILE)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df.drop_duplicates(subset=["Phone"], inplace=True)
    else:
        df = df_new
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"💾 Saved total: {len(df)}")

# ================= SCRAPER =================
def scrape_query(driver, query):
    print("🔎 Loading:", query)
    driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")

    # Wait for feed, NOT cards
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
    )

    # Bootstrap scroll (CRITICAL)
    for _ in range(5):
        driver.execute_script("""
            const feed = document.querySelector('div[role="feed"]');
            if (feed) feed.scrollTop = feed.scrollHeight;
        """)
        time.sleep(1)

    results = []
    processed = set()
    idx = 0

    while True:
        cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")

        if idx >= len(cards):
            break

        try:
            card = cards[idx]
            name = card.get_attribute("aria-label")
            idx += 1

            if not name or name in processed:
                continue
            if BUSINESS_NAME.lower() not in name.lower():
                continue

            processed.add(name)

            driver.execute_script("arguments[0].scrollIntoView(true);", card)
            time.sleep(0.4)
            card.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "DUwDvf"))
            )

            phone = extract_phone(driver)
            if phone:
                results.append({
                    "Business": BUSINESS_NAME,
                    "Distributor_Name": name,
                    "Phone": phone,
                    "Search_Query": query,
                    "Scraped_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            click_back(driver)
            time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))

        except StaleElementReferenceException:
            continue
        except Exception:
            click_back(driver)
            continue

    return results

# ================= MAIN =================
def main():
    driver = setup_driver()
    try:
        for city in CITIES:
            for key in KEYWORDS:
                query = f"{BUSINESS_NAME} {key} {city}"
                rows = scrape_query(driver, query)
                save_rows(rows)
    finally:
        driver.quit()

    print("✅ DONE — REAL SCRAPING COMPLETE")

if __name__ == "__main__":
    main()
