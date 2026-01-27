import streamlit as st
import pandas as pd
import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIGURATION =================
INDIAN_CITIES = {
        "India": [
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chhattisgarh",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal"
    ],
    "Andaman and Nicobar Islands": ["Port Blair"],
    "Andhra Pradesh": [
        "Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool",
        "Rajahmundry", "Tirupati", "Kakinada", "Kadapa", "Anantapur",
        "Vizianagaram", "Eluru", "Ongole", "Nandyal", "Machilipatnam"
    ],
    "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Pasighat", "Tawang"],
    "Assam": [
        "Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon",
        "Tinsukia", "Tezpur", "Bongaigaon", "Sivasagar"
    ],
    "Bihar": [
        "Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia",
        "Darbhanga", "Bihar Sharif", "Arrah", "Begusarai", "Katihar",
        "Munger", "Chhapra", "Sasaram", "Hajipur"
    ],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": [
        "Raipur", "Bhilai", "Bilaspur", "Korba", "Durg",
        "Rajnandgaon", "Raigarh", "Jagdalpur", "Ambikapur"
    ],
    "Dadra and Nagar Haveli and Daman and Diu": ["Daman", "Diu", "Silvassa"],
    "Delhi": [
        "New Delhi", "Delhi Cantt", "Vasant Kunj", "Dwarka", "Rohini",
        "Saket", "Connaught Place", "Nehru Place", "Lajpat Nagar",
        "Karol Bagh", "Okhla", "Mayur Vihar"
    ],
    "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda"],
    "Gujarat": [
        "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar",
        "Jamnagar", "Gandhinagar", "Junagadh", "Gandhidham", "Anand",
        "Navsari", "Morbi", "Nadiad", "Surendranagar", "Bharuch",
        "Vapi", "Ankleshwar", "Bhuj", "Porbandar", "Palanpur", "Valsad"
    ],
    "Haryana": [
        "Gurugram", "Faridabad", "Panipat", "Ambala", "Yamunanagar",
        "Rohtak", "Hisar", "Karnal", "Sonipat", "Panchkula",
        "Bhiwani", "Sirsa", "Bahadurgarh", "Jind", "Thanesar"
    ],
    "Himachal Pradesh": [
        "Shimla", "Dharamshala", "Solan", "Mandi", "Baddi",
        "Kullu", "Manali", "Bilaspur", "Chamba", "Hamirpur"
    ],
    "Jammu and Kashmir": [
        "Srinagar", "Jammu", "Anantnag", "Baramulla", "Udhampur",
        "Kathua", "Sopore"
    ],
    "Jharkhand": [
        "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar",
        "Phusro", "Hazaribagh", "Giridih", "Ramgarh", "Medininagar"
    ],
    "Karnataka": [
        "Bangalore", "Mysore", "Hubballi", "Dharwad", "Mangalore",
        "Belagavi", "Davangere", "Bellary", "Vijayapura", "Shivamogga",
        "Tumakuru", "Raichur", "Bidar", "Hospet", "Udupi",
        "Hassan", "Gadag", "Robertsonpet", "Kolar"
    ],
    "Kerala": [
        "Thiruvananthapuram", "Kochi", "Kozhikode", "Kollam", "Thrissur",
        "Kannur", "Alappuzha", "Palakkad", "Kottayam", "Malappuram",
        "Manjeri", "Thalassery", "Ponnani"
    ],
    "Ladakh": ["Leh", "Kargil"],
    "Lakshadweep": ["Kavaratti"],
    "Madhya Pradesh": [
        "Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain",
        "Sagar", "Dewas", "Satna", "Ratlam", "Rewa",
        "Murwara", "Singrauli", "Burhanpur", "Khandwa", "Bhind",
        "Chhindwara", "Guna", "Shivpuri", "Vidisha"
    ],
    "Maharashtra": [
        "Mumbai", "Pune", "Nagpur", "Thane", "Nashik",
        "Kalyan-Dombivli", "Vasai-Virar", "Aurangabad", "Navi Mumbai", "Solapur",
        "Mira-Bhayandar", "Bhiwandi", "Amravati", "Nanded", "Kolhapur",
        "Ulhasnagar", "Sangli", "Malegaon", "Jalgaon", "Akola",
        "Latur", "Dhule", "Ahmednagar", "Chandrapur", "Parbhani",
        "Ichalkaranji", "Jalna", "Bhusawal", "Satara", "Beed",
        "Yavatmal", "Gondia", "Baramati"
    ],
    "Manipur": ["Imphal", "Thoubal"],
    "Meghalaya": ["Shillong", "Tura", "Jowai"],
    "Mizoram": ["Aizawl", "Lunglei"],
    "Nagaland": ["Dimapur", "Kohima"],
    "Odisha": [
        "Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur",
        "Puri", "Balasore", "Bhadrak", "Baripada", "Jharsuguda", "Jeypore"
    ],
    "Puducherry": ["Puducherry", "Karaikal", "Yanam", "Mahe"],
    "Punjab": [
        "Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda",
        "Mohali", "Hoshiarpur", "Pathankot", "Moga", "Abohar",
        "Malerkotla", "Khanna", "Phagwara", "Firozpur", "Kapurthala"
    ],
    "Rajasthan": [
        "Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer",
        "Udaipur", "Bhilwara", "Alwar", "Bharatpur", "Sikar",
        "Pali", "Sri Ganganagar", "Bhiwadi", "Hanumangarh", "Beawar"
    ],
    "Sikkim": ["Gangtok", "Namchi"],
    "Tamil Nadu": [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
        "Tirunelveli", "Tiruppur", "Vellore", "Erode", "Thoothukudi",
        "Dindigul", "Thanjavur", "Ranipet", "Sivakasi", "Karur",
        "Hosur", "Nagercoil", "Kanchipuram", "Kumbakonam", "Cuddalore"
    ],
    "Telangana": [
        "Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar",
        "Ramagundam", "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet",
        "Siddipet", "Miryalaguda"
    ],
    "Tripura": ["Agartala", "Udaipur", "Dharmanagar"],
    "Uttar Pradesh": [
        "Lucknow", "Kanpur", "Ghaziabad", "Agra", "Meerut",
        "Varanasi", "Prayagraj", "Bareilly", "Aligarh", "Moradabad",
        "Saharanpur", "Gorakhpur", "Noida", "Firozabad", "Jhansi",
        "Muzaffarnagar", "Mathura", "Ayodhya", "Rampur", "Shahjahanpur",
        "Farrukhabad", "Maunath Bhanjan", "Hapur", "Etawah", "Mirzapur",
        "Bulandshahr", "Greater Noida"
    ],
    "Uttarakhand": [
        "Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rudrapur",
        "Kashipur", "Rishikesh", "Nainital"
    ],
    "West Bengal": [
        "Kolkata", "Howrah", "Asansol", "Siliguri", "Durgapur",
        "Bardhaman", "Malda", "Baharampur", "Habra", "Kharagpur",
        "Shantipur", "Dankuni", "Haldia", "Raiganj", "Krishnanagar"
    ]
}


# ================= SELENIUM SETUP =================
def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_experimental_option("detach", False)

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def clean_phone(text):
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    if len(digits) < 10:
        return None
    return digits


# ================= STREAMLIT STATE =================
if "results" not in st.session_state:
    st.session_state.results = []

if "logs" not in st.session_state:
    st.session_state.logs = []


def log(msg):
    st.session_state.logs.append(msg)
    log_placeholder.code(
        "\n".join(st.session_state.logs[-20:]),
        language="text"
    )


# ================= UI HEADER =================
st.set_page_config(
    page_title="Wellsure Scraper",
    page_icon="🏢",
    layout="wide"
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 4.5rem;
        font-weight: 900;
        text-align: center;
        color: #002147;
    }
    .sub-title {
        text-align: center;
        color: #B8860B;
        margin-bottom: 30px;
    }
    </style>
    <div class="main-title">WELLSURE</div>
    <div class="sub-title">Automated Lead Discovery System</div>
    """,
    unsafe_allow_html=True
)


# ================= SIDEBAR =================
with st.sidebar:
    st.header("🔍 Search Settings")

    business_name = st.text_input("Business / Brand Name", "MRF")
    state = st.selectbox("State", list(INDIAN_CITIES.keys()))

    # --- New "Select All" Logic ---
    all_cities = INDIAN_CITIES[state]
    select_all = st.checkbox("Select all cities in " + state)

    if select_all:
        selected_cities = st.multiselect("Cities", all_cities, default=all_cities)
    else:
        selected_cities = st.multiselect("Cities", all_cities, default=[all_cities[0]])
    # ------------------------------

    keywords_input = st.text_area(
        "Keywords (comma separated)",
        "authorized dealer, distributor, showroom"
    )
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

    st.markdown("---")
    start_btn = st.button("🚀 START SCRAPING", use_container_width=True)


# ================= MAIN UI & DASHBOARD =================
# ================= MAIN UI =================
m1, m2 = st.columns(2)
total_leads_metric = m1.metric("Leads Collected", len(st.session_state.results))
status_placeholder = m2.empty()
status_placeholder.metric("Status", "Ready")

# Only show the log to keep the UI light
st.subheader("📜 Activity Log")
log_placeholder = st.empty()

# ================= CORE SCRAPER =================
if start_btn:
    if not business_name or not selected_cities:
        st.error("Please enter business name and select cities.")
        st.stop()

    driver = setup_driver()
    status_placeholder.metric("Status", "Scraping...")
    
    # Counter for internal tracking
    new_leads_since_log = 0 

 # ================= IMPROVED SCROLL & EXTRACTION =================
    try:
        for city in selected_cities:
            for key in keywords:
                query = f"{business_name} {key} {city}"
                log(f"🔎 Target: {query}")
                status_placeholder.metric("Status", f"Loading {city}...")
                
                url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                driver.get(url)

                try:
                    # 1. Wait for the results feed to actually appear
                    wait = WebDriverWait(driver, 15)
                    feed_css = "div[role='feed']"
                    feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, feed_css)))
                    
                    # 2. ROBUST SCROLL LOOP
                    log("  ⬇️ Scrolling to end of list (this may take a minute)...")
                    last_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                    
                    while True:
                        # Scroll down to the bottom of the feed
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                        
                        # Wait for new items to load
                        time.sleep(3.5) 
                        
                        # Check if scroll height has changed
                        new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                        
                        # Search for the "You've reached the end of the list" text
                        page_content = driver.page_source
                        if "You've reached the end of the list" in page_content or new_height == last_height:
                            # Double check: try one more scroll just in case
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                            time.sleep(2)
                            if driver.execute_script("return arguments[0].scrollHeight", feed) == new_height:
                                break
                        
                        last_height = new_height
                        current_count = len(driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc"))
                        log(f"  ➜ Loaded {current_count} businesses...")

                    # 3. COLLECT ALL LINKS AFTER SCROLLING IS DONE
                    links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")]
                    log(f"  ✅ Found {len(links)} total links for {city}. Starting extraction...")

                    # 4. EXTRACTION LOOP
                    for link in links:
                        try:
                            driver.get(link)
                            time.sleep(1)
                    
                            # --- Robust business name extraction ---
                            name = None
                            try:
                                name_el = WebDriverWait(driver, 15).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf"))
                                )
                    
                                # wait until text is actually populated
                                WebDriverWait(driver, 10).until(
                                    lambda d: name_el.text.strip() != ""
                                )
                    
                                name = name_el.text.strip()
                            except:
                                name = None
                    
                            # --- Find Phone ---
                            raw_phone = None
                    
                            # Try the aria-label method first
                            phone_elements = driver.find_elements(
                                By.XPATH, "//button[contains(@aria-label,'Phone')]"
                            )
                            if phone_elements:
                                raw_phone = phone_elements[0].get_attribute("aria-label")
                            else:
                                # Fallback: scan all info div text
                                info_divs = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                                for div in info_divs:
                                    if re.search(r"\d{8,}", div.text):
                                        raw_phone = div.text
                                        break
                    
                            phone = clean_phone(raw_phone)
                    
                            if phone and phone not in {d["Phone"] for d in st.session_state.results}:
                                st.session_state.results.append({
                                    "Company": name,
                                    "Phone": phone,
                                    "City": city,
                                    "Keyword": key,
                                    "Link": link
                                })
                    
                                total_leads_metric.metric(
                                    "Leads Collected",
                                    len(st.session_state.results)
                                )
                    
                                # Log every 10 leads to show progress
                                if len(st.session_state.results) % 10 == 0:
                                    log(f"📦 Progress: {len(st.session_state.results)} leads saved.")
                    
                        except:
                            continue  # Skip to next link if one fails
 # Skip to next link if one fails
                except Exception as e:
                    log(f"⚠️ Timeout/No results for: {query}")
                    continue

        status_placeholder.metric("Status", "Finished")
        log("🏁 SCRAPING COMPLETE - All data ready for download.")

    finally:
        driver.quit()

# ================= DOWNLOAD =================
if st.session_state.results:
    st.markdown("---")
    st.success(f"Extraction complete! Total unique leads: **{len(st.session_state.results)}**")
    
    # Convert to DataFrame for Download
    df_final = pd.DataFrame(st.session_state.results)
    
    # Create Excel buffer
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Leads')
    
    st.download_button(
        label="📥 Download Leads as Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"Wellsure_Leads_{business_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )