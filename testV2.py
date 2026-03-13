import streamlit as st
import pandas as pd
import time
import re
import urllib.parse
import io

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIGURATION =================
INDIAN_CITIES = {
    "Rajasthan": ["Ajmer", "Jaipur", "Jodhpur", "Kota", "Bikaner", "Udaipur"],
    "Delhi": ["New Delhi", "North Delhi", "South Delhi", "West Delhi"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"]
}

# ================= SELENIUM SETUP =================
def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    # Uncomment the line below if you want it to run in the background
    # options.add_argument("--headless") 
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def clean_phone(text):
    if not text: return None
    digits = re.sub(r"\D", "", text)
    if digits.startswith("91") and len(digits) > 10: digits = digits[2:]
    return digits if len(digits) >= 10 else None

def extract_name_from_url(url):
    if not url: return "Unknown Business"
    match = re.search(r"/maps/place/([^/]+)/data=", url)
    if match:
        raw_name = match.group(1).replace("+", " ")
        return urllib.parse.unquote(raw_name)
    return "Unknown Business"

# ================= UI HEADER =================
st.set_page_config(page_title="Wellsure Master Scraper", page_icon="🏢", layout="wide")

st.markdown(
    """
    <style>
    .main-title { font-size: 4.5rem; font-weight: 900; text-align: center; color: #002147; }
    .sub-title { text-align: center; color: #B8860B; margin-bottom: 30px; }
    .stMetric { background: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 5px solid #002147; }
    </style>
    <div class="main-title">WELLSURE</div>
    <div class="sub-title">Master Lead & GST Discovery System</div>
    """,
    unsafe_allow_html=True
)

if "results" not in st.session_state: st.session_state.results = []
if "logs" not in st.session_state: st.session_state.logs = []

def log(msg):
    st.session_state.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    log_placeholder.code("\n".join(st.session_state.logs[-15:]), language="text")

# ================= SIDEBAR =================
with st.sidebar:
    st.header("🔍 Search Settings")
    business_name = st.text_input("Business / Brand Name", "MRF")
    state = st.selectbox("State", list(INDIAN_CITIES.keys()))
    
    all_cities = INDIAN_CITIES.get(state, [])
    selected_cities = st.multiselect("Cities", all_cities, default=[all_cities[0]] if all_cities else [])

    keywords_input = st.text_area("Keywords (comma separated)", "authorized dealer, distributor, showroom")
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

    st.markdown("---")
    enable_gst = st.checkbox("🔍 Deep-Scan GST (IndiaMart)", value=True)
    max_leads = st.slider("Leads per search", 5, 50, 10)
    start_btn = st.button("🚀 START MASTER SCRAPER", use_container_width=True)

# ================= DASHBOARD =================
m1, m2 = st.columns(2)
total_leads_metric = m1.metric("Leads Collected", len(st.session_state.results))
status_placeholder = m2.empty()
status_placeholder.metric("Status", "Ready")

st.subheader("📜 Activity Log")
log_placeholder = st.empty()

# ================= CORE MASTER ENGINE =================
if start_btn:
    if not business_name or not selected_cities:
        st.error("Please enter business name and select cities.")
        st.stop()

    driver = setup_driver()
    status_placeholder.metric("Status", "Initialising...")
    
    try:
        for city in selected_cities:
            for key in keywords:
                query = f"{business_name} {key} {city}"
                log(f"🔎 Harvesting G-Maps: {query}")
                
                # 1. HARVEST LINKS FROM GOOGLE MAPS
                driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
                
                try:
                    wait = WebDriverWait(driver, 10)
                    feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                    
                    # Scroll to find leads
                    scrolled = 0
                    while scrolled < 3: # Adjust for more results
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                        time.sleep(2)
                        scrolled += 1
                    
                    links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")][:max_leads]
                    log(f"✅ Found {len(links)} links. Processing details...")

                    # 2. EXTRACT DETAILS FOR EACH LINK
                    for link in links:
                        try:
                            driver.get(link)
                            time.sleep(2)
                            
                            # Extract Name
                            try:
                                name = driver.find_element(By.TAG_NAME, "h1").text
                            except:
                                name = extract_name_from_url(link)
                            
                            # Extract Phone
                            raw_phone = None
                            try:
                                phone_elements = driver.find_elements(By.XPATH, "//button[contains(@aria-label,'Phone')]")
                                if phone_elements:
                                    raw_phone = phone_elements[0].get_attribute("aria-label")
                                else:
                                    info_divs = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                                    for div in info_divs:
                                        if re.search(r"\d{8,}", div.text):
                                            raw_phone = div.text
                                            break
                            except: pass
                            
                            phone = clean_phone(raw_phone)
                            
                            if phone and phone not in {d["Phone"] for d in st.session_state.results}:
                                # 3. GST DEEP SCAN (IndiaMart Integration via same driver)
                                gst_no = "Not Checked"
                                if enable_gst:
                                    log(f"📡 Searching GST for: {name}")
                                    # Open IndiaMart search in same window
                                    driver.get(f"https://dir.indiamart.com/search.mp?ss={name}+{city}")
                                    time.sleep(2)
                                    try:
                                        # Click the first company link
                                        first_comp = driver.find_element(By.CSS_SELECTOR, ".m-com-name a, .card-links a")
                                        first_comp.click()
                                        time.sleep(3)
                                        
                                        # Scan for GST pattern in the whole page
                                        page_text = driver.find_element(By.TAG_NAME, "body").text
                                        match = re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', page_text)
                                        gst_no = match.group() if match else "Not Found"
                                    except:
                                        gst_no = "Not Found"

                                # SAVE RESULT
                                st.session_state.results.append({
                                    "Company": name,
                                    "Phone": phone,
                                    "GST": gst_no,
                                    "City": city,
                                    "Keyword": key,
                                    "Google Link": link
                                })
                                total_leads_metric.metric("Leads Collected", len(st.session_state.results))
                                log(f"✨ Saved: {name} | GST: {gst_no}")

                        except Exception: continue
                except Exception as e:
                    log(f"⚠️ Search skipped: {query}")
                    continue

        status_placeholder.metric("Status", "Finished")
        log("🏁 MASTER SCAN COMPLETE.")

    finally:
        driver.quit()

# ================= DOWNLOAD =================
if st.session_state.results:
    st.markdown("---")
    df_final = pd.DataFrame(st.session_state.results)
    st.dataframe(df_final, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Leads')
    
    file_name = f"Wellsure_Master_{state}_{business_name}".replace(" ", "_") + ".xlsx"
    st.download_button("📥 Download Master Excel", data=buffer.getvalue(), file_name=file_name, use_container_width=True)
