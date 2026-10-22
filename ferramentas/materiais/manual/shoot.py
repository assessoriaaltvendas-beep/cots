import json, datetime as dt, re, io
from playwright.sync_api import sync_playwright
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../../..'); O = AQUI + '/shots/'
mock='window.MOCK_TERMOS_OK=1;\n' + open(RAIZ + '/ferramentas/testes-navegador/mock-supabase.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
t=dt.date.today()
def d(off):
    x=t+dt.timedelta(days=off)
    while x.weekday()==6: x+=dt.timedelta(days=1)
    return x.isoformat()
L='lucas1'
bk=[]
def add(i,date,a,b,pago=False,extra=None):
    r={'id':i,'dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 41.122','tel':'(31) 98841-5460','primeira':False,'date':date,'h_from':a,'h_to':b,'status':'ativo','origem':'area-dentista','pago':pago,'valor':None,'criado_em':'2026-10-01T10:00:00'}
    if extra: r.update(extra)
    bk.append(r)
add('p1',d(-14),14,16,True,{'checklist':{'itens':[],'feitoEm':'2026-10-07T16:00:00'},'avaliacao':{'nota':5,'comentario':'','em':'2026-10-07T17:00:00'}})
add('p2',d(-7),14,16,True,{'checklist':{'itens':[],'feitoEm':'2026-10-14T16:00:00'}})
add('p3',d(-1),8,13,False)
add('f1',d(2),14,16); add('f2',d(9),14,16)
slots=[{'date':x['date'],'hour':h,'booking_id':x['id']} for x in bk if x['date']>=t.isoformat() for h in range(x['h_from'],x['h_to'])]
slots += [{'date':d(4),'hour':h,'booking_id':'o1'} for h in (9,10,15)]
bk.append({'id':'o1','dentist_id':'outro','nome':'Outro','tel':'(31) 90000-0000','primeira':False,'date':d(4),'h_from':9,'h_to':11,'status':'ativo','origem':'site','pago':False,'criado_em':'2026-10-01T10:00:00'})
seed={'slots':slots,'bookings':bk,'cfg':{'pix':'+5531995745413','pixNome':'Thalia Santiago','pixCidade':'Ipatinga'},'secret':'k','sent':[],
 'dentists':[{'id':L,'nome':'Lucas Andrade','cro':'CRO-MG 41.122','whatsapp':'(31) 98841-5460','email':'lucas@x.com','status':'liberado','criado_em':'2026-09-01T10:00:00'},
             {'id':'bia','nome':'Beatriz Lima','cro':'CRO-MG 52.880','whatsapp':'(31) 91234-5678','email':'bia@x.com','status':'pendente','criado_em':'2026-10-21T09:12:00'}],
 'avisos':[{'id':'av1','titulo':'Feriado de Finados','texto':'No dia 2/11 o consultório estará fechado.','criado_em':'2026-10-20T10:00:00'}],'problemas':[],'espera':[],'admins':['adm1'],'faq':[],'app_config':[],
 'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':L,'email':'lucas@x.com','password':'abc12345'},{'id':'bia','email':'bia@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def ctx_(b):
    c=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort()); c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html><body style="margin:0;background:#ece6e3"></body></html>', content_type='text/html'))
    c.add_init_script(init); return c
def top(pg, sel, off=70):
    pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}'); if(e){{e.scrollIntoView({{block:'start'}}); window.scrollBy(0,-{off});}}}})()"); pg.wait_for_timeout(250)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=ctx_(b).new_page()
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(1000); pg.screenshot(path=O+'home.png')
    clk(pg,'#start'); pg.wait_for_timeout(500); clk(pg,'#dl-seg [data-dl="reg"]'); pg.wait_for_timeout(300)
    pg.fill('#dr-nome','Ana Ribeiro'); pg.fill('#dr-cro','CRO-MG 12.345'); pg.fill('#dr-tel','(31) 91111-2222'); pg.fill('#dr-email','ana@exemplo.com')
    top(pg,'#dl-title',110); pg.screenshot(path=O+'reg.png')
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(400); clk(pg,'#dl-seg [data-dl="login"]')
    pg.fill('#dl-email','bia@x.com'); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1300)
    pg.screenshot(path=O+'wait.png'); clk(pg,'#c-wait [data-dlogout]'); pg.wait_for_timeout(1000)
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email','lucas@x.com'); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1400)
    clk(pg,'#view-dent .side [data-ctab="inicio"]'); pg.wait_for_timeout(500); pg.screenshot(path=O+'inicio.png')
    clk(pg,'#view-dent .side [data-ctab="nova"]'); pg.wait_for_timeout(400)
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{date:'{d(4)}',start:null,end:null}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    top(pg,'#cn-day',20); pg.screenshot(path=O+'nova_dia.png')
    clk(pg,'#cn-per [data-per="13|18"]'); pg.wait_for_timeout(300)
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{start:11,end:12}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    top(pg,'#cn-opts',80); pg.screenshot(path=O+'nova_confirma.png')
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{start:11,end:14}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    top(pg,'#cn-opts',80); pg.screenshot(path=O+'nova_cruza.png')
    clk(pg,'#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(400); pg.screenshot(path=O+'reservas.png')
    pg.evaluate("document.querySelector('#cr-list [data-cbk=\"f1\"]').click()"); pg.wait_for_timeout(600); pg.screenshot(path=O+'drawer.png')
    pg.evaluate("const h=[...document.querySelectorAll('#c-drawer h4')].find(x=>/Pagar com Pix/.test(x.textContent)); if(h) h.scrollIntoView({block:'start'})"); pg.wait_for_timeout(300); pg.screenshot(path=O+'drawer_pix.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.evaluate("(()=>{const x=document.querySelector('#c-drawer .icon-btn, #c-drawer [aria-label=Fechar]'); if(x) x.click();})()"); pg.wait_for_timeout(300)
    clk(pg,'#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(300)
    pg.evaluate("(()=>{const e=document.querySelector('#cr-list [data-cbk=\"p3\"]'); if(e) e.click();})()"); pg.wait_for_timeout(600)
    pg.evaluate("const h=[...document.querySelectorAll('#c-drawer h4')].find(x=>/Checklist/.test(x.textContent)); if(h) h.scrollIntoView({block:'start'})"); pg.wait_for_timeout(300); pg.screenshot(path=O+'checklist.png')
    pg.evaluate("(()=>{const x=document.querySelector('#c-drawer .icon-btn, #c-drawer [aria-label=Fechar]'); if(x) x.click();})()"); pg.wait_for_timeout(300)
    clk(pg,'#view-dent .side [data-ctab="financeiro"]'); pg.wait_for_timeout(500); pg.screenshot(path=O+'fin.png')
    top(pg,'#cf-pix',70); pg.screenshot(path=O+'fin_pix.png')
    clk(pg,'#view-dent .side [data-ctab="consultorio"]'); pg.wait_for_timeout(500); pg.screenshot(path=O+'consultorio.png')
    clk(pg,'#view-dent .side [data-ctab="perfil"]'); pg.wait_for_timeout(500)
    pg.evaluate("const e=new Event('beforeinstallprompt');e.prompt=()=>{};e.userChoice=Promise.resolve({});window.dispatchEvent(e)"); pg.wait_for_timeout(200)
    top(pg,'#app-d',90); pg.screenshot(path=O+'app.png')
    b.close()
print('ok')
