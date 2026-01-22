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
    options.add_experimental_option("detach", True)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def clean_phone(text):
    if not text: return None
    digits = re.sub(r"\D", "", text) 
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:] 
    if len(digits) < 10: return None 
    return digits

# ================= UI HEADER =================
st.set_page_config(page_title="Wellsure Scraper", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .main-title {
        font-size: 5rem;
        font-weight: 900;
        color: #002147; /* Deep Navy */
        text-align: center;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #B8860B; /* Gold Accent */
        text-align: center;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    </style>
    <div class="main-title">WELLSURE</div>
    <div class="sub-title">Automated Lead Discovery System</div>
    """, unsafe_allow_html=True)

# ================= SIDEBAR =================
with st.sidebar:
    st.header("🔍 Search Settings")
    
    business_name = st.text_input("Business / Brand Name", value="MRF")
    state = st.selectbox("Select State", list(INDIAN_CITIES.keys()))
    
    cities = st.multiselect("Target Cities", INDIAN_CITIES[state], default=[INDIAN_CITIES[state][0]])
    
    st.subheader("📝 Keywords")
    default_keywords = "authorized dealer, distributor, showroom"
    keywords_input = st.text_area("Keywords (comma separated)", default_keywords)
    keywords = [k.strip() for k in keywords_input.split(",")]
    
    st.markdown("---")
    start_btn = st.button("🚀 START SCRAPING", type="primary", use_container_width=True)

# ================= MAIN LAYOUT =================
col1, col2 = st.columns([0.65, 0.35])

with col1:
    st.subheader("📊 Live Data Results")
    results_placeholder = st.empty() # Table goes here

with col2:
    st.subheader("📜 Activity Log")
    log_placeholder = st.empty() # Logs go here

# ================= LOGIC =================
if start_btn:
    if not business_name or not cities:
        st.error("⚠️ Please enter a business name and select at least one city.")
    else:
        driver = setup_driver()
        all_data = []
        logs = []

        def update_log(msg):
            logs.append(msg)
            # Show last 15 logs
            log_placeholder.code("\n".join(logs[-15:]), language="text")

        try:
            total_searches = len(cities) * len(keywords)
            update_log(f"🚀 Initializing search for {total_searches} queries...")

            for city in cities:
                for key in keywords:
                    query = f"{business_name} {key} {city}"
                    
                    # --- 1. SEARCH ---
                    # CORRECTED URL HERE:
                    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                    update_log(f"🔎 Searching: {query}")
                    driver.get(search_url)

                    try:
                        # Wait for sidebar
                        wait = WebDriverWait(driver, 10)
                        feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                        
                        # --- 2. ROBUST SCROLLING ---
                        update_log("   ⬇️ Scrolling to load results...")
                        last_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                        
                        # Scroll loop
                        while True:
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                            time.sleep(2) # Wait for load
                            new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                            
                            # Stop if end of list text appears
                            if "You've reached the end of the list" in driver.page_source:
                                break
                            
                            if new_height == last_height:
                                # Try one more wait to be sure
                                time.sleep(1.5)
                                new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                                if new_height == last_height:
                                    break
                            last_height = new_height
                        
                        # --- 3. HARVEST LINKS ---
                        link_elements = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
                        urls = list(set([l.get_attribute("href") for l in link_elements]))
                        update_log(f"   ✅ Found {len(urls)} locations. extracting details...")

                        # --- 4. EXTRACT DETAILS ---
                        for i, url in enumerate(urls):
                            try:
                                driver.get(url)
                                # Wait for title to confirm load
                                WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                                
                                # Extract Name
                                try: name = driver.find_element(By.TAG_NAME, "h1").text
                                except: name = "Unknown"

                                # Extract Phone (Robust)
                                raw_phone = None
                                try:
                                    # Try button first
                                    btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Phone:')]")
                                    raw_phone = btn.get_attribute("aria-label").replace("Phone:", "").strip()
                                except:
                                    # Try text fallback
                                    try:
                                        els = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                                        for el in els:
                                            if re.match(r'^(\+91|0)?[ -]?\d{3,}', el.text):
                                                raw_phone = el.text
                                                break
                                    except: pass
                                
                                phone = clean_phone(raw_phone)

                                if phone:
                                    # DUPLICATE CHECK
                                    if not any(d['Phone'] == phone for d in all_data):
                                        all_data.append({
                                            "Company": name,
                                            "Phone": phone,
                                            "City": city,
                                            "Keyword": key,
                                            "Link": url
                                        })
                                        # Update Table
                                        results_placeholder.dataframe(pd.DataFrame(all_data), height=400)
                                        update_log(f"   [+] Saved: {name}")
                                    else:
                                        update_log(f"   [!] Duplicate ignored: {name}")
                                else:
                                    update_log(f"   [-] No number: {name}")

                            except Exception as e:
                                continue # Skip failed individual pages

                    except Exception as e:
                        update_log(f"⚠️ Search failed for {query}")
            
            update_log("🏁 WORK COMPLETE")
            
            # --- DOWNLOAD BUTTON ---
            if all_data:
                df = pd.DataFrame(all_data)
                csv = df.to_csv(index=False).encode('utf-8')
                st.sidebar.success(f"Collected {len(all_data)} Leads!")
                st.sidebar.download_button(
                    label="📥 DOWNLOAD EXCEL/CSV",
                    data=csv,
                    file_name="Wellsure_Leads.csv",
                    mime="text/csv",
                    key='download-csv'
                )
            else:
                st.warning("Scraping finished but no valid numbers were found.")

        except Exception as e:
            st.error(f"Critical Error: {e}")
        finally:
            driver.quit()
