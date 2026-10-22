from playwright.sync_api import sync_playwright
import os; S = os.path.dirname(os.path.abspath(__file__)) + '/'
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+S+'doc4.html'); pg.wait_for_timeout(1200)
    pg.pdf(path=S+'out4.pdf',width='297mm',height='210mm',print_background=True,prefer_css_page_size=True); b.close()
