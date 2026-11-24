"""
AWARE-AI Live Demonstration Automation Script.
Robust Selenium execution across all 9 pages and 15 workflow steps,
capturing full-resolution PNG screenshots.
"""

import os
import sys
import time
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

ROOT_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT_DIR / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_DIR = ROOT_DIR / ".demo_chrome_profile"
if PROFILE_DIR.exists():
    try:
        shutil.rmtree(PROFILE_DIR)
    except Exception:
        pass
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    
    chrome_bin = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if os.path.exists(chrome_bin):
        chrome_options.binary_location = chrome_bin
        
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def wait_for_app_ready(driver, timeout=25):
    """Wait until Streamlit elements and navigation labels mount."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        labels = driver.find_elements(By.TAG_NAME, "label")
        for l in labels:
            if "Global Control Tower" in l.text:
                time.sleep(1)
                return
        time.sleep(1)
    raise TimeoutError("Streamlit app did not finish mounting navigation within timeout.")


def select_page(driver, page_prefix):
    """Click on a radio option in the sidebar matching page_prefix."""
    print(f"\n--> Navigating to page: {page_prefix}")
    wait_for_app_ready(driver)
    
    labels = driver.find_elements(By.TAG_NAME, "label")
    target_label = None
    for lbl in labels:
        if page_prefix in lbl.text:
            target_label = lbl
            break
            
    if not target_label:
        raise RuntimeError(f"Could not find label matching '{page_prefix}'. Available: {[l.text for l in labels if l.text]}")
        
    driver.execute_script("arguments[0].scrollIntoView(true);", target_label)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target_label)
    time.sleep(3.5)


def safe_js_click(driver, element):
    """Scroll and execute JavaScript click on element."""
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", element)
    time.sleep(0.5)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)
    time.sleep(1)


def main():
    print("=================================================================")
    print("AWARE-AI: LIVE DEMONSTRATION & SCREENSHOT RECORDING WORKFLOW")
    print("=================================================================")
    
    driver = get_driver()
    results = {}
    
    try:
        print("Connecting to live Streamlit instance at http://localhost:8501 ...")
        driver.get("http://localhost:8501")
        wait_for_app_ready(driver)
        print("Connected successfully and navigation mounted!")
        
        # ─────────────────────────────────────────────────────────────
        # STAGE 1: Global Control Tower
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 1] Global Control Tower")
        select_page(driver, "1. Global Control Tower")
        time.sleep(3)
        shot1 = SCREENSHOTS_DIR / "01_global_control_tower.png"
        driver.save_screenshot(str(shot1))
        print(f"Captured screenshot: {shot1.name}")
        results["stage_1_dashboard"] = {"status": "SUCCESS", "screenshot": str(shot1)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 2: Register New Shipment
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 2] Shipment Management (Register Consignment)")
        select_page(driver, "2. Shipment Management")
        time.sleep(2)
        
        # Click on tab 2: Register New Shipment
        tabs = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stTabs'] button")
        for tab in tabs:
            if "Register New Shipment" in tab.text:
                safe_js_click(driver, tab)
                break
        time.sleep(2)
        
        # Submit the pre-filled registration form
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Submit & Register Shipment" in b.text:
                safe_js_click(driver, b)
                print("Submitted shipment registration form.")
                break
        time.sleep(3)
        
        # Switch back to Active Fleet Overview tab
        tabs = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stTabs'] button")
        if tabs:
            safe_js_click(driver, tabs[0])
        time.sleep(2.5)
        
        shot2 = SCREENSHOTS_DIR / "02_shipment_registered.png"
        driver.save_screenshot(str(shot2))
        print(f"Captured screenshot: {shot2.name}")
        results["stage_2_shipment_registration"] = {"status": "SUCCESS", "screenshot": str(shot2)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 3: Weather Intelligence
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 3] Weather & Maritime Intelligence")
        select_page(driver, "7. Weather & Maritime")
        time.sleep(3)
        shot3 = SCREENSHOTS_DIR / "03_weather_intelligence.png"
        driver.save_screenshot(str(shot3))
        print(f"Captured screenshot: {shot3.name}")
        results["stage_3_weather"] = {"status": "SUCCESS", "screenshot": str(shot3)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 4: Supplier & Inventory Intelligence
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 4] Supplier & Inventory Intelligence")
        select_page(driver, "8. Supplier & Inventory")
        time.sleep(3)
        shot4 = SCREENSHOTS_DIR / "04_supplier_inventory.png"
        driver.save_screenshot(str(shot4))
        print(f"Captured screenshot: {shot4.name}")
        results["stage_4_supplier_inventory"] = {"status": "SUCCESS", "screenshot": str(shot4)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 5: Shipment Risk Analysis & TreeSHAP
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 5] Shipment Risk Analysis & TreeSHAP")
        select_page(driver, "3. Shipment Risk Analysis")
        time.sleep(2)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Run Live ML Inference" in b.text:
                safe_js_click(driver, b)
                print("Clicked 'Run Live ML Inference' button.")
                break
        time.sleep(5)  # Wait for LightGBM + TreeSHAP
        
        shot5 = SCREENSHOTS_DIR / "05_ml_risk_and_shap.png"
        driver.save_screenshot(str(shot5))
        print(f"Captured screenshot: {shot5.name}")
        results["stage_5_ml_shap"] = {"status": "SUCCESS", "screenshot": str(shot5)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 6: Multi-Agent Intelligence Center
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 6] Multi-Agent Intelligence Command Center")
        select_page(driver, "4. Multi-Agent Intelligence")
        time.sleep(2)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Trigger Full 7-Agent Cycle" in b.text:
                safe_js_click(driver, b)
                print("Clicked 'Trigger Full 7-Agent Cycle' button.")
                break
        time.sleep(6)  # Wait for 7-agent cycle to finish
        
        shot6 = SCREENSHOTS_DIR / "06_multi_agent_execution.png"
        driver.save_screenshot(str(shot6))
        print(f"Captured screenshot: {shot6.name}")
        results["stage_6_multi_agent"] = {"status": "SUCCESS", "screenshot": str(shot6)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 7: Root Cause & Impact Analysis
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 7] Root Cause & Impact Analysis")
        select_page(driver, "5. Root Cause & Impact")
        time.sleep(2)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Evaluate Business Impact" in b.text:
                safe_js_click(driver, b)
                print("Clicked 'Evaluate Business Impact' button.")
                break
        time.sleep(3.5)
        
        shot7 = SCREENSHOTS_DIR / "07_root_cause_and_impact.png"
        driver.save_screenshot(str(shot7))
        print(f"Captured screenshot: {shot7.name}")
        results["stage_7_root_cause_impact"] = {"status": "SUCCESS", "screenshot": str(shot7)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 8 & 9: Resilience Planning & Human Approval
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 8 & 9] Resilience Planning & Human Approval")
        select_page(driver, "6. Resilience Planning")
        time.sleep(2)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Generate Autonomous Plans" in b.text:
                safe_js_click(driver, b)
                print("Clicked 'Generate Autonomous Plans' button.")
                break
        time.sleep(5)
        
        shot8 = SCREENSHOTS_DIR / "08_resilience_plans_generated.png"
        driver.save_screenshot(str(shot8))
        print(f"Captured screenshot: {shot8.name}")
        
        # Submit Human Approval Decision
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in all_buttons:
            if "Submit Operational Decision" in b.text:
                safe_js_click(driver, b)
                print("Clicked 'Submit Operational Decision' (APPROVED).")
                break
        time.sleep(4)
            
        shot9 = SCREENSHOTS_DIR / "09_resilience_plan_approved.png"
        driver.save_screenshot(str(shot9))
        print(f"Captured screenshot: {shot9.name}")
        results["stage_8_9_resilience_approval"] = {"status": "SUCCESS", "screenshot_plans": str(shot8), "screenshot_approved": str(shot9)}

        # ─────────────────────────────────────────────────────────────
        # STAGE 10: System Monitoring & Audit Ledger
        # ─────────────────────────────────────────────────────────────
        print("\n[STAGE 10] System Monitoring & Audit Ledger")
        select_page(driver, "9. System Monitoring")
        time.sleep(3)
        shot10 = SCREENSHOTS_DIR / "10_system_monitoring_audit.png"
        driver.save_screenshot(str(shot10))
        print(f"Captured screenshot: {shot10.name}")
        results["stage_10_monitoring"] = {"status": "SUCCESS", "screenshot": str(shot10)}

        print("\n=================================================================")
        print("DEMONSTRATION SUCCESSFULLY EXECUTED ACROSS ALL STAGES!")
        print("=================================================================")
        print(f"Screenshots saved in: {SCREENSHOTS_DIR}")
        
    except Exception as e:
        print(f"\nERROR during live demonstration: {e}")
        import traceback
        traceback.print_exc()
        err_shot = SCREENSHOTS_DIR / "error_snapshot.png"
        driver.save_screenshot(str(err_shot))
        results["error"] = str(e)
    finally:
        driver.quit()
        try:
            shutil.rmtree(PROFILE_DIR)
        except Exception:
            pass
            
    return results


if __name__ == "__main__":
    main()
