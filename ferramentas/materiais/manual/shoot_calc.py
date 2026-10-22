import json
from playwright.sync_api import sync_playwright
S='/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad'; O=S+'/manual/shots/'
mock=open(S+'/app/mock9r.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
seed={'slots':[],'bookings':[],'cfg':{'valorHora':50},'secret':'k','sent':[],'admins':['adm1'],'adm':{'adm1':{'nivel':'completo','nome':'Dra. Thalia Santiago'}},'faq':[],'app_config':[],'avisos':[],'problemas':[],'espera':[],
 'dentists':[{'id':'lucas1','nome':'Lucas Andrade','cro':'CRO-MG 41.122','whatsapp':'(31) 98841-5460','email':'lucas@x.com','status':'liberado','criado_em':'2026-09-01T10:00:00'}],
 'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':'lucas1','email':'lucas@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
LIB="(()=>{const d=JSON.parse(localStorage.mockdb); d.calc={itens:CALC_PADRAO,liberada:true,base:1,log:[],em:new Date().toISOString(),por:'Dra. Thalia Santiago'}; localStorage.mockdb=JSON.stringify(d)})()"
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def fill(pg,k,v):
    sel=f'#calc-d [data-cin="{k}"]'; el=pg.query_selector(sel)
    if el.evaluate('e=>e.tagName')=='SELECT': pg.select_option(sel,v)
    elif el.evaluate('e=>e.type')=='checkbox':
        if el.is_checked()!=v: el.evaluate('e=>e.click()')
    else: pg.fill(sel,v)
    pg.wait_for_timeout(150)
with sync_playwright() as p:
    b=p.chromium.launch(); c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    pg0=c.new_page(); pg0.goto('http://localhost:8765/'); pg0.wait_for_timeout(800); PAD=json.loads(pg0.evaluate('JSON.stringify(CALC_PADRAO)')); pg0.close()
    seed['calc']={'itens':PAD,'liberada':True,'base':1,'log':[],'em':'2026-10-21T21:00:00','por':'Dra. Thalia Santiago'}
    init="localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");" if False else "if(!sessionStorage.getItem('x')){sessionStorage.setItem('x',1);localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");}"
    c.add_init_script(init); pg=c.new_page()
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email','lucas@x.com'); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1500)
    print(pg.url, pg.evaluate('JSON.stringify([S.dent,S.isAdmin,!!S.calcD, location.hash])')); pg.screenshot(path='/tmp/dbgc.png')
    clk(pg,'#view-dent .side [data-ctab="calc"]'); pg.wait_for_timeout(800); print(pg.inner_text('#calc-d')[:200])
    clk(pg,'#calc-d [data-csec="med"]'); fill(pg,'med','amoxicilina-susp'); fill(pg,'peso','18'); fill(pg,'anos','4'); fill(pg,'meses','6')
    pg.evaluate("document.querySelector('#calc-d .calc-f').scrollIntoView({block:'start'}); window.scrollBy(0,-70)"); pg.wait_for_timeout(300)
    pg.screenshot(path=O+'calc_med.png')
    clk(pg,'#calc-d [data-csec="anest"]'); pg.wait_for_timeout(200); fill(pg,'anest','articaina'); fill(pg,'peso','22'); fill(pg,'anos','7'); fill(pg,'meses','0')
    pg.evaluate("document.querySelector('#calc-d [data-cin=anest]').scrollIntoView({block:'start'}); window.scrollBy(0,-40)"); pg.wait_for_timeout(300)
    pg.screenshot(path=O+'calc_anest.png')
    b.close()
print('ok')
