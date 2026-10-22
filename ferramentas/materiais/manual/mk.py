import sys
from playwright.sync_api import sync_playwright
D='/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad/manual/'
src,out=sys.argv[1],sys.argv[2]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+D+src); pg.wait_for_timeout(900)
    pg.pdf(path=D+out,width='210mm',height='297mm',print_background=True,prefer_css_page_size=True); b.close()
