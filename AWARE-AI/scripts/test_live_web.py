from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opt = Options()
opt.add_argument('--headless=new')
opt.add_argument('--window-size=1920,1080')
opt.add_argument('--no-sandbox')
opt.add_argument('--disable-gpu')
opt.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
d = webdriver.Chrome(options=opt)
try:
    d.get('http://localhost:8501')
    time.sleep(5)
    d.save_screenshot('docs/screenshots/live_dashboard_verified.png')
    
    # Check for exceptions on page
    exceptions = d.find_elements(By.CSS_SELECTOR, '[data-testid="stException"]')
    if exceptions:
        print('PAGE EXCEPTION OCCURRED:')
        for exc in exceptions:
            print(exc.text)
    else:
        print('SUCCESS: Streamlit page loaded cleanly with ZERO exceptions!')
        h1s = d.find_elements(By.TAG_NAME, 'h1')
        for h in h1s:
            print('  Heading:', h.text)
        kpis = d.find_elements(By.CSS_SELECTOR, '[data-testid="stMetricLabel"], [data-testid="stMetricValue"]')
        print('  KPI Count:', len(kpis))
finally:
    d.quit()
