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
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
        "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
        "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
        "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
        "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
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
    "Madhya Pradesh": [
        "Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain",
        "Sagar", "Dewas", "Satna", "Ratlam", "Rewa",
        "Murwara", "Singrauli", "Burhanpur", "Khandwa", "Bhind",
        "Chhindwara", "Guna", "Shivpuri", "Vidisha"
    ],
    "Maharashtra": [
        "Mumbai", "Pune", "Nagpur", "Thane", "Nashik",
        "Aurangabad", "Navi Mumbai", "Solapur"
    ],
    "Rajasthan": [
        "Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer",
        "Udaipur", "Bhilwara", "Alwar", "Bharatpur", "Sikar",
        "Pali", "Sri Ganganagar", "Bhiwadi", "Hanumangarh", "Beawar"
    ],
    "Tamil Nadu": [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
        "Tirunelveli", "Tiruppur", "Vellore", "Erode", "Thoothukudi"
    ],
    "Telangana": [
        "Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar"
    ],
    "Uttar Pradesh": [
        "Lucknow", "Kanpur", "Ghaziabad", "Agra", "Meerut",
        "Varanasi", "Prayagraj", "Bareilly", "Aligarh", "Moradabad"
    ],
    "Uttarakhand": [
        "Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rudrapur"
    ],
    "West Bengal": [
        "Kolkata", "Howrah", "Asansol", "Siliguri", "Durgapur"
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
    log_placeholder.code("\n".join(st.session_state.logs[-20:]), language="text")


# ================= UI =================
st.set_page_config(page_title="Wellsure Scraper", page_icon="🏢", layout="wide")

with st.sidebar:
    st.header("🔍 Search Settings")
    business_name = st.text_input("Business / Brand Name", "MRF")
    state = st.selectbox("State", list(INDIAN_CITIES.keys()))

    all_cities = INDIAN_CITIES[state]
    select_all = st.checkbox("Select all cities in " + state)

    selected_cities = (
        all_cities if select_all else st.multiselect("Cities", all_cities, default=[all_cities[0]])
    )

    keywords = [k.strip() for k in st.text_area(
        "Keywords (comma separated)",
        "authorized dealer, distributor, showroom"
    ).split(",") if k.strip()]

    start_btn = st.button("🚀 START SCRAPING", use_container_width=True)


st.subheader("📜 Activity Log")
log_placeholder = st.empty()


# ================= SCRAPER =================
if start_btn:
    driver = setup_driver()

    try:
        for city in selected_cities:
            for key in keywords:
                query = f"{business_name} {key} {city}"
                log(f"🔎 {query}")

                driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")

                wait = WebDriverWait(driver, 15)
                feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))

                last_height = 0
                while True:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                    time.sleep(3)
                    new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                    if new_height == last_height:
                        break
                    last_height = new_height

                links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")]

                for link in links:
                    try:
                        driver.get(link)
                        time.sleep(2)

                        name = driver.title.split(" - Google Maps")[0]
                        phone = None

                        for div in driver.find_elements(By.CLASS_NAME, "Io6YTe"):
                            if re.search(r"\d{8,}", div.text):
                                phone = clean_phone(div.text)
                                break

                        if phone and phone not in {d["Phone"] for d in st.session_state.results}:
                            st.session_state.results.append({
                                "Company": name,
                                "Phone": phone,
                                "City": city,
                                "Keyword": key,
                                "Link": link
                            })

                    except:
                        continue
    finally:
        driver.quit()


# ================= DOWNLOAD =================
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.download_button(
        "📥 Download Excel",
        df.to_excel(index=False),
        file_name="wellsure_leads.xlsx"
    )
