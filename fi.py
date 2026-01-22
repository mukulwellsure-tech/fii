# =====================================================
# GOOGLE MAPS DISTRIBUTOR SCRAPER – ROBUST VERSION
# =====================================================
import time
import re
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= USER INPUT =================
BUSINESS_NAME = "MRF"
STATE_NAME = "Rajasthan"
OUTPUT_FILE = f"{BUSINESS_NAME}_Distributors_{STATE_NAME}.xlsx"

# Combine these for your searches
CITIES = ["Jodhpur", "Jaipur", "Udaipur", "Kota"]
KEYWORDS = ["authorized dealer", "tyre distributor", "tyre showroom"]

# ================= SETUP DRIVER =================
def setup_driver():
    options = Options()
    # Mask automation to prevent immediate blocking
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ================= EXTRACTION LOGIC =================
def extract_phone(driver):
    """
    Tries multiple methods to find the phone number on the details page.
    """
    try:
        # Method 1: Look for the specific button with 'phone' icon or aria-label
        # This XPATH looks for any button that has a phone icon or 'phone' in the label
        phone_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Phone:')]")
        return phone_btn.get_attribute("aria-label").replace("Phone:", "").strip()
    except:
        pass

    try:
        # Method 2: The classic class search (Io6YTe) inside a specific container
        # We look for the element that contains text starting with +91 or 0
        elements = driver.find_elements(By.CLASS_NAME, "Io6YTe")
        for el in elements:
            text = el.text.strip()
            # Simple check if it looks like a phone number
            if re.match(r'^(\+91|0)?[ -]?\d{3,}', text):
                return text
    except:
        pass
    
    return "Not Found"

def extract_name(driver):
    try:
        return driver.find_element(By.TAG_NAME, "h1").text
    except:
        return ""

# ================= CORE LOGIC =================
def get_business_urls(driver, query):
    print(f"🔎 Searching: {query}")
    driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
    
    # 1. Wait for the Feed (Sidebar) to load
    try:
        wait = WebDriverWait(driver, 10)
        # Check for the sidebar feed element
        feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
    except:
        print("   ❌ No results found or layout changed.")
        return []

    # 2. Scroll Loop to load all results
    print("   ⬇️ Scrolling to load all results...")
    last_height = driver.execute_script("return arguments[0].scrollHeight", feed)
    
    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
        time.sleep(2) # Give G-Maps time to load the new batch (Critical)
        
        new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
        
        # If we encounter the "You've reached the end of the list" element, break
        if "You've reached the end of the list" in driver.page_source:
            break
            
        if new_height == last_height:
            # Try one more nudge just in case
            time.sleep(1)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
            if driver.execute_script("return arguments[0].scrollHeight", feed) == last_height:
                break
        
        last_height = new_height

    # 3. Harvest Links
    # The 'hfpxzc' class is the transparent link overlay covering the business card
    links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
    urls = [link.get_attribute("href") for link in links]
    
    print(f"   ✅ Found {len(urls)} businesses.")
    return list(set(urls)) # Remove duplicates

def process_urls(driver, urls, query):
    data = []
    
    for i, url in enumerate(urls):
        try:
            driver.get(url)
            
            # Wait for the H1 (Business Name) to confirm page load
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            
            name = extract_name(driver)
            phone = extract_phone(driver)
            
            # Filter logic: Only keep if it matches requirements
            if BUSINESS_NAME.lower() in name.lower() or True: # 'True' keeps everything, adjust if needed
                print(f"   [{i+1}/{len(urls)}] {name} -> {phone}")
                data.append({
                    "Business Name": name,
                    "Phone": phone,
                    "City": query.split()[-1], # Rough guess of city from query
                    "URL": url,
                    "Search Query": query
                })
        except Exception as e:
            print(f"   ⚠️ Error scraping {url}: {e}")
            continue
            
    return data

def save_to_excel(new_data):
    if not new_data:
        return
    
    df_new = pd.DataFrame(new_data)
    
    if os.path.exists(OUTPUT_FILE):
        df_existing = pd.read_excel(OUTPUT_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        # Drop duplicates based on URL to avoid re-saving the same business
        df_combined.drop_duplicates(subset=['URL'], keep='last', inplace=True)
    else:
        df_combined = df_new
        
    df_combined.to_excel(OUTPUT_FILE, index=False)
    print(f"💾 Saved {len(new_data)} new rows to {OUTPUT_FILE}")

# ================= MAIN =================
def main():
    driver = setup_driver()
    
    try:
        all_data = []
        
        for city in CITIES:
            for keyword in KEYWORDS:
                query = f"{BUSINESS_NAME} {keyword} {city}"
                
                # Step 1: Get all Links for this query
                urls = get_business_urls(driver, query)
                
                if not urls:
                    continue
                
                # Step 2: Visit each link and extract data
                batch_data = process_urls(driver, urls, query)
                
                # Step 3: Save progressively (so you don't lose data if it crashes)
                save_to_excel(batch_data)
                
    finally:
        driver.quit()
        print("🏁 Scraping Complete.")

if __name__ == "__main__":
    main()
