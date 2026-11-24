from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from pathlib import Path

SCREENSHOTS = Path("docs/screenshots")
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

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
    print("Page Title:", d.title)
    
    # Locate all nav links in sidebar
    nav_links = d.find_elements(By.CSS_SELECTOR, "[data-testid='stSidebarNav'] a, [data-testid='stSidebar'] a")
    print("Found navigation links count:", len(nav_links))
    for i, a in enumerate(nav_links):
        print(f"  Link {i}: '{a.text}' (href: {a.get_attribute('href')})")
        
    pages_to_test = [
        "Global Control Tower",
        "Shipment Management",
        "Shipment Risk Analysis",
        "Multi-Agent Intelligence",
        "Root Cause & Impact",
        "Resilience Planning",
        "Weather & Maritime",
        "Supplier & Inventory",
        "System Monitoring",
    ]
    
    for idx, page_name in enumerate(pages_to_test, 1):
        print(f"\n---> Testing Page {idx}: {page_name}")
        # Find link matching page_name
        all_links = d.find_elements(By.CSS_SELECTOR, "[data-testid='stSidebarNav'] a, [data-testid='stSidebar'] a, a[data-testid='stPageLink-NavLink']")
        clicked = False
        for link in all_links:
            if page_name.lower() in link.text.lower():
                d.execute_script("arguments[0].scrollIntoView(true);", link)
                time.sleep(0.5)
                d.execute_script("arguments[0].click();", link)
                clicked = True
                print(f"  Clicked link: '{link.text}'")
                break
                
        if not clicked:
            print(f"  WARNING: Could not find link for '{page_name}', searching all elements...")
            candidates = d.find_elements(By.XPATH, f"//span[contains(text(), '{page_name}')]/ancestor::a")
            if candidates:
                d.execute_script("arguments[0].click();", candidates[0])
                clicked = True
                
        time.sleep(4)
        
        # Verify 0 exceptions
        exceptions = d.find_elements(By.CSS_SELECTOR, "[data-testid='stException']")
        if exceptions:
            print(f"  ERROR on Page {idx}:")
            for exc in exceptions:
                print("    ", exc.text[:200])
        else:
            # Check content
            headers = [h.text for h in d.find_elements(By.TAG_NAME, "h1") if h.text]
            metrics = d.find_elements(By.CSS_SELECTOR, "[data-testid='stMetricValue']")
            tables = d.find_elements(By.CSS_SELECTOR, "[data-testid='stDataFrame']")
            charts = d.find_elements(By.CSS_SELECTOR, "[data-testid='stPlotlyChart']")
            print(f"  SUCCESS! Headers: {headers[:1]} | Metrics: {len(metrics)} | Tables: {len(tables)} | Charts: {len(charts)}")
            
        shot_path = SCREENSHOTS / f"verified_page_{idx}.png"
        d.save_screenshot(str(shot_path))
        print(f"  Saved screenshot: {shot_path.name}")

finally:
    d.quit()
