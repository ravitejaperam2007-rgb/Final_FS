from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opt = Options()
opt.add_argument('--headless=new')
opt.add_argument('--window-size=1920,1080')
opt.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
d = webdriver.Chrome(options=opt)
d.get('http://localhost:8501')
time.sleep(5)
d.save_screenshot('docs/screenshots/landing_inspect.png')
print('Page Title:', d.title)

# Search for radio items or any clickable elements
all_labels = d.find_elements(By.TAG_NAME, 'label')
print('All labels count:', len(all_labels))
for l in all_labels:
    txt = l.text.strip()
    if txt:
        print('  Label:', txt)

radios = d.find_elements(By.CSS_SELECTOR, '[data-testid="stRadio"] label, [role="radiogroup"] label, [data-baseweb="radio"]')
print('Radio selectors count:', len(radios))
for r in radios:
    print('  Radio:', r.text)

# Also check sidebar
sidebar = d.find_elements(By.CSS_SELECTOR, '[data-testid="stSidebar"]')
print('Sidebar found:', len(sidebar))
if sidebar:
    print('Sidebar text snippet:', repr(sidebar[0].text[:300]))

d.quit()
