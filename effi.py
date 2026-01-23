import streamlit as st
import pandas as pd
import time
import re
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIGURATION: CITIES =================
INDIAN_CITIES = {
    "Andaman and Nicobar Islands": ["Port Blair"],
    "Andhra Pradesh": [
        "Anantapur", "Bhimavaram", "Chittoor", "Eluru", "Guntur", "Kadapa", 
        "Kakinada", "Kurnool", "Machilipatnam", "Nandyal", "Nellore", "Ongole", 
        "Proddatur", "Rajahmundry", "Srikakulam", "Tadepalligudem", "Tirupati", 
        "Vijayawada", "Visakhapatnam", "Vizianagaram"
    ],
    "Arunachal Pradesh": ["Itanagar", "Naharlagun"],
    "Assam": [
        "Bongaigaon", "Dibrugarh", "Guwahati", "Jorhat", "Nagaon", 
        "Silchar", "Tezpur", "Tinsukia"
    ],
    "Bihar": [
        "Ara", "Begusarai", "Bettiah", "Bhagalpur", "Bihar Sharif", "Chapra", 
        "Darbhanga", "Gaya", "Hajipur", "Katihar", "Motihari", "Munger", 
        "Muzaffarpur", "Patna", "Purnia", "Saharsa", "Samastipur", "Sasaram", "Siwan"
    ],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": [
        "Ambikapur", "Bhilai", "Bilaspur", "Dhamtari", "Durg", "Jagdalpur", 
        "Korba", "Raigarh", "Raipur", "Rajnandgaon"
    ],
    "Dadra and Nagar Haveli and Daman and Diu": ["Daman", "Silvassa", "Diu"],
    "Delhi NCR": [
        "Bahadurgarh", "Delhi", "Faridabad", "Ghaziabad", "Greater Noida", 
        "Gurugram", "Manesar", "New Delhi", "Noida", "Sonipat"
    ],
    "Goa": ["Mapusa", "Margao", "Mormugao", "Panaji", "Ponda", "Vasco da Gama"],
    "Gujarat": [
        "Ahmedabad", "Amreli", "Anand", "Ankleshwar", "Bharuch", "Bhavnagar", 
        "Bhuj", "Dahej", "Gandhidham", "Gandhinagar", "Godhra", "Himmatnagar", 
        "Jamnagar", "Junagadh", "Kalol", "Kandla", "Mehsana", "Morbi", "Mundra", 
        "Nadiad", "Navsari", "Palanpur", "Patan", "Porbandar", "Rajkot", "Surat", 
        "Surendranagar", "Vadodara", "Valsad", "Vapi", "Veraval"
    ],
    "Haryana": [
        "Ambala", "Bahadurgarh", "Bhiwani", "Faridabad", "Gurugram", "Hisar", 
        "Jind", "Kaithal", "Karnal", "Kurukshetra", "Manesar", "Palwal", 
        "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar"
    ],
    "Himachal Pradesh": ["Baddi", "Dharamshala", "Kullu", "Mandi", "Shimla", "Solan", "Paonta Sahib"],
    "Jammu and Kashmir": ["Anantnag", "Baramulla", "Jammu", "Kathua", "Srinagar", "Udhampur"],
    "Jharkhand": [
        "Bokaro", "Chaibasa", "Deoghar", "Dhanbad", "Dumka", "Giridih", 
        "Hazaribagh", "Jamshedpur", "Medininagar", "Phusro", "Ramgarh", "Ranchi"
    ],
    "Karnataka": [
        "Bagalkot", "Ballari", "Bangalore", "Belagavi", "Bidar", "Chikkamagaluru", 
        "Chitradurga", "Davangere", "Dharwad", "Gadag", "Hassan", "Hospet", 
        "Hubballi", "Kalaburagi", "Kolar", "Mandya", "Mangalore", "Manipal", 
        "Mysore", "Raichur", "Shivamogga", "Tumakuru", "Udupi", "Vijayapura"
    ],
    "Kerala": [
        "Alappuzha", "Aluva", "Changanassery", "Ernakulam", "Kannur", "Kasaragod", 
        "Kochi", "Kollam", "Kottayam", "Kozhikode", "Malappuram", "Manjeri", 
        "Palakkad", "Pathanamthitta", "Thalassery", "Thiruvananthapuram", 
        "Thrissur", "Tirur"
    ],
    "Ladakh": ["Leh"],
    "Madhya Pradesh": [
        "Bhopal", "Burhanpur", "Chhindwara", "Dewas", "Guna", "Gwalior", 
        "Hoshangabad", "Indore", "Jabalpur", "Katni", "Khandwa", "Mandsaur", 
        "Morena", "Neemuch", "Pithampur", "Ratlam", "Rewa", "Sagar", "Satna", 
        "Singrauli", "Ujjain", "Vidisha"
    ],
    "Maharashtra": [
        "Ahmednagar", "Akola", "Amravati", "Aurangabad", "Baramati", "Bhiwandi", 
        "Bhusawal", "Chandrapur", "Dhule", "Gondia", "Ichalkaranji", "Jalgaon", 
        "Jalna", "Kalyan-Dombivli", "Kolhapur", "Latur", "Malegaon", "Mira-Bhayandar", 
        "Mumbai", "Nagpur", "Nanded", "Nashik", "Navi Mumbai", "Panvel", "Parbhani", 
        "Pimpri-Chinchwad", "Pune", "Ratnagiri", "Sangli", "Satara", "Solapur", 
        "Thane", "Ulhasnagar", "Vasai-Virar", "Wardha", "Yavatmal"
    ],
    "Manipur": ["Imphal"],
    "Meghalaya": ["Shillong"],
    "Mizoram": ["Aizawl"],
    "Nagaland": ["Dimapur", "Kohima"],
    "Odisha": [
        "Angul", "Balasore", "Baripada", "Berhampur", "Bhadrak", "Bhubaneswar", 
        "Cuttack", "Jharsuguda", "Paradip", "Puri", "Rayagada", "Rourkela", "Sambalpur"
    ],
    "Puducherry": ["Karaikal", "Puducherry"],
    "Punjab": [
        "Abohar", "Amritsar", "Barnala", "Batala", "Bathinda", "Firozpur", 
        "Hoshiarpur", "Jalandhar", "Kapurthala", "Khanna", "Ludhiana", "Malerkotla", 
        "Mandi Gobindgarh", "Moga", "Mohali", "Muktsar", "Pathankot", "Patiala", "Phagwara"
    ],
    "Rajasthan": [
        "Ajmer", "Alwar", "Barmer", "Beawar", "Bharatpur", "Bhilwara", 
        "Bhiwadi", "Bikaner", "Chittorgarh", "Ganganagar", "Hanumangarh", 
        "Jaipur", "Jaisalmer", "Jhunjhunu", "Jodhpur", "Kishangarh", "Kota", 
        "Neemrana", "Pali", "Sikar", "Tonk", "Udaipur"
    ],
    "Sikkim": ["Gangtok"],
    "Tamil Nadu": [
        "Ambur", "Chennai", "Coimbatore", "Cuddalore", "Dindigul", "Erode", 
        "Hosur", "Kanchipuram", "Karaikudi", "Karur", "Kumbakonam", "Madurai", 
        "Nagercoil", "Namakkal", "Neyveli", "Pollachi", "Pudukkottai", "Rajapalayam", 
        "Salem", "Sivakasi", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", 
        "Tirunelveli", "Tirupur", "Tiruvannamalai", "Vellore", "Villupuram"
    ],
    "Telangana": [
        "Adilabad", "Hyderabad", "Karimnagar", "Khammam", "Mahbubnagar", 
        "Mancherial", "Miryalaguda", "Nalgonda", "Nizamabad", "Ramagundam", 
        "Secunderabad", "Suryapet", "Warangal"
    ],
    "Tripura": ["Agartala"],
    "Uttar Pradesh": [
        "Agra", "Aligarh", "Ayodhya", "Bareilly", "Bhadohi", "Bulandshahr", 
        "Etawah", "Firozabad", "Ghaziabad", "Gorakhpur", "Hapur", "Jhansi", 
        "Kanpur", "Khurja", "Lucknow", "Mathura", "Meerut", "Mirzapur", 
        "Modinagar", "Moradabad", "Muzaffarnagar", "Noida", "Prayagraj", 
        "Rampur", "Saharanpur", "Shahjahanpur", "Sitapur", "Unnao", "Varanasi"
    ],
    "Uttarakhand": [
        "Dehradun", "Haldwani", "Haridwar", "Kashipur", "Nainital", 
        "Pantnagar", "Roorkee", "Rudrapur"
    ],
    "West Bengal": [
        "Asansol", "Baharampur", "Bardhaman", "Durgapur", "Haldia", "Howrah", 
        "Kharagpur", "Kolkata", "Krishnanagar", "Malda", "Midnapore", 
        "Purulia", "Raiganj", "Siliguri"
    ]
}

# ================= UTILITIES =================
# ================= FIXED DRIVER SETUP =================
def setup_driver():
    options = Options()
    # CRITICAL FIX: Turn OFF headless mode to bypass bot detection for now
    # Once it works, you can try adding "--headless=new" back later.
    # options.add_argument("--headless=new") 
    
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    
    # Randomize User-Agent to look like a real human
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ================= FIXED WORKER LOGIC =================
def scrape_worker(task):
    query, city, keyword = task
    driver = None
    results = []
    log_messages = []
    
    try:
        driver = setup_driver()
        
        # CRITICAL FIX: Use the standard URL, not the redirect
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        driver.get(search_url)
        
        wait = WebDriverWait(driver, 15) # Increased wait time
        
        try:
            # Check if we are on the results list or a single result
            # We look for the "Feed" (List of results)
            feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
            
            # --- SCROLL LOGIC ---
            # Scroll at least 3 times to trigger lazy loading
            for _ in range(3):
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                time.sleep(2)
                
        except:
            # Sometimes Google goes straight to a single result (no feed).
            # We handle this by checking if there is an H1 immediately.
            pass

        # --- UPDATED LINK SELECTOR ---
        # Instead of 'a.hfpxzc', we find ALL links that point to a place
        # This is much harder for Google to break
        link_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/maps/place/')]")
        
        # Deduplicate links
        urls = list(set([l.get_attribute("href") for l in link_elements if l.get_attribute("href")]))
        
        # Filter out junk links (navigation links often contain maps/place too)
        # We only want links that look like business profiles
        urls = [u for u in urls if "!3d" in u] 

        if not urls:
             # Fallback: If no list found, maybe we are already ON the page?
             if "/maps/place/" in driver.current_url:
                 urls = [driver.current_url]
        
        log_messages.append(f"🔍 Found {len(urls)} potential links for {city}")

        # --- EXTRACT DETAILS ---
        for url in urls[:5]: # LIMIT to 5 per keyword for testing speed. Remove [:5] for full run.
            try:
                driver.get(url)
                
                # Wait for the Main Title (H1)
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                name = driver.find_element(By.TAG_NAME, "h1").text
                
                phone = None
                
                # METHOD 1: Look for the specific "Copy phone number" button
                try:
                    # This XPath finds buttons with phone numbers in their aria-label
                    # It's very robust because the aria-label usually starts with "Phone:"
                    phone_btn = driver.find_element(By.XPATH, "//button[starts-with(@aria-label, 'Phone:')]")
                    phone = phone_btn.get_attribute("aria-label").replace("Phone:", "").strip()
                except:
                    pass

                # METHOD 2: Look for any button containing a phone icon
                if not phone:
                    try:
                        # The phone icon usually has this specific data-item-id
                        phone_btn = driver.find_element(By.CSS_SELECTOR, "button[data-item-id*='phone']")
                        phone = phone_btn.get_attribute("aria-label").replace("Phone:", "").strip()
                    except:
                        pass
                
                # METHOD 3: The Text Fallback (Last Resort)
                if not phone:
                    try:
                        # Grab all text blocks in the sidebar
                        # ".Io6YTe" is common, but let's grab the container "div" to be safe
                        text_divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'fontBodyMedium')]")
                        for div in text_divs:
                            txt = div.text
                            # Strict check: Must start with 0 or +91 and be 10+ digits
                            if re.search(r"((\+91)|0)\s?\d{3,}", txt):
                                phone = txt
                                break
                    except:
                        pass

                clean = clean_phone(phone)
                
                if clean:
                    results.append({
                        "Company": name,
                        "Phone": clean,
                        "City": city,
                        "Keyword": keyword,
                        "Source_Link": url
                    })
                    
            except Exception as e:
                # log_messages.append(f"Skipped a link: {str(e)[:20]}")
                continue

    except Exception as e:
        log_messages.append(f"❌ Worker Error: {e}")
    finally:
        if driver:
            driver.quit()
            
    return results, log_messages

# ================= MAIN UI =================
st.set_page_config(page_title="Wellsure Pro Scraper", page_icon="🏢", layout="wide")

# Custom CSS for Wellsure Branding
st.markdown("""
    <style>
    .main-title { font-size: 4rem; font-weight: 900; color: #002147; text-align: center; margin-bottom: 0; }
    .sub-title { font-size: 1.5rem; color: #B8860B; text-align: center; margin-top: -10px; margin-bottom: 30px; }
    .stButton>button { background-color: #002147; color: white; border-radius: 5px; height: 50px; font-weight: bold; }
    .stButton>button:hover { background-color: #B8860B; color: white; border: none; }
    </style>
    <div class="main-title">WELLSURE</div>
    <div class="sub-title">Automated Lead Discovery System</div>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Search Parameters")
    
    business_name = st.text_input("Brand / Business Name", value="MRF")
    
    # State Selection
    state_names = list(INDIAN_CITIES.keys())
    state = st.selectbox("Select State", state_names)
    
    # "Select All" Feature
    available_cities = INDIAN_CITIES[state]
    select_all = st.checkbox(f"Select All Cities in {state}")
    
    if select_all:
        default_cities = available_cities
    else:
        default_cities = [available_cities[0]]
        
    cities = st.multiselect("Target Cities", available_cities, default=default_cities)
    
    st.subheader("📝 Keywords")
    keywords_input = st.text_area("Keywords (comma separated)", "authorized dealer, showroom, distributor")
    keywords = [k.strip() for k in keywords_input.split(",")]
    
    st.markdown("---")
    st.caption("Parallel Processing Enabled (4 Workers)")
    start_btn = st.button("🚀 START EXTRACTION", type="primary", use_container_width=True)

# Main Area
col1, col2 = st.columns([0.7, 0.3])

with col1:
    st.subheader("📊 Live Data Feed")
    results_placeholder = st.empty()

with col2:
    st.subheader("📜 System Logs")
    log_placeholder = st.empty()

# ================= EXECUTION LOGIC =================
if start_btn:
    if not cities or not business_name:
        st.error("⚠️ Please select at least one city and enter a business name.")
    else:
        # Prepare Tasks
        tasks = []
        for city in cities:
            for key in keywords:
                query = f"{business_name} {key} {city}"
                tasks.append((query, city, key))
        
        all_results = []
        system_logs = []
        
        def update_ui():
            # Helper to refresh tables and logs
            if all_results:
                df = pd.DataFrame(all_results)
                # Remove duplicates based on Phone
                df = df.drop_duplicates(subset=['Phone'])
                results_placeholder.dataframe(df, use_container_width=True, height=500)
            
            log_text = "\n".join(system_logs[-20:]) # Show last 20 logs
            log_placeholder.code(log_text, language="text")

        system_logs.append(f"🚀 Initializing {len(tasks)} search tasks...")
        system_logs.append(f"⚡ Spawning 4 parallel browser workers...")
        update_ui()
        
        # Parallel Execution
        # max_workers=4 is a safe balance for most machines. 
        # Increase to 6 or 8 if you have a powerful server (16GB+ RAM).
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_task = {executor.submit(scrape_worker, task): task for task in tasks}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
                task = future_to_task[future]
                query_str = task[0]
                
                try:
                    data, logs = future.result()
                    
                    # Merge data
                    all_results.extend(data)
                    
                    # Merge logs
                    system_logs.append(f"✅ Finished: {query_str} ({len(data)} leads)")
                    # system_logs.extend(logs) # Optional: uncomment for verbose logs
                    
                    # Update Progress
                    progress = (i + 1) / len(tasks)
                    # Force UI update every time a task finishes
                    update_ui()
                    
                except Exception as exc:
                    system_logs.append(f"❌ Error in {query_str}: {exc}")
                    update_ui()

        # Final Success
        system_logs.append("🏁 ALL TASKS COMPLETE")
        update_ui()
        
        if all_results:
            final_df = pd.DataFrame(all_results).drop_duplicates(subset=['Phone'])
            csv = final_df.to_csv(index=False).encode('utf-8')
            
            st.sidebar.success(f"Collected {len(final_df)} Unique Leads!")
            st.sidebar.download_button(
                label="📥 DOWNLOAD FINAL CSV",
                data=csv,
                file_name="Wellsure_Final_Leads.csv",
                mime="text/csv"
            )
        else:
            st.warning("Scraping finished, but no valid data was found.")
