import json, datetime as dt, re, subprocess
from playwright.sync_api import sync_playwright
import cv2, numpy as np
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../..')
S = os.environ.get('COTS_SAIDA', '/tmp/cots-testes'); O=S+'/app/s5/'  # pasta de saída (prints, PDFs)
import os; os.makedirs(O, exist_ok=True)
mock='window.MOCK_TERMOS_OK=1;\n' + open(AQUI + '/mock-supabase.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
t=dt.date.today()
def d(off):
    x=t+dt.timedelta(days=off)
    while x.weekday()==6: x+=dt.timedelta(days=1)
    return x.isoformat()
L='lucas1'
bk=[
 {'id':'p1','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':d(-9),'h_from':14,'h_to':16,'status':'ativo','origem':'area-dentista','pago':True,'valor':None,'avaliacao':{'nota':5,'comentario':'Consultório impecável, tudo funcionando.','em':'2026-10-12T10:00:00'},'criado_em':'2026-10-01T10:00:00'},
 {'id':'p2','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':d(-2),'h_from':9,'h_to':11,'status':'ativo','origem':'area-dentista','pago':False,'valor':None,'avaliacao':{'nota':4,'comentario':'','em':'2026-10-19T10:00:00'},'criado_em':'2026-10-01T10:00:00'},
 {'id':'f1','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':d(4),'h_from':14,'h_to':16,'status':'ativo','origem':'area-dentista','pago':False,'valor':None,'criado_em':'2026-10-01T10:00:00'}]
seed={'slots':[{'date':d(4),'hour':h,'booking_id':'f1'} for h in (14,15)],'bookings':bk,
 'dentists':[{'id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','whatsapp':'(31) 98841-5460','email':'lucas@x.com','status':'liberado','criado_em':'2026-09-01T10:00:00'},
             {'id':'mari','nome':'Mariana Costa','cro':'CRO-MG 7','whatsapp':'(31) 99712-3301','email':'mari@x.com','status':'pendente','criado_em':'2026-10-20T15:00:00'},
             {'id':'rafa','nome':'Rafael Nunes','cro':'CRO-MG 8','whatsapp':'(31) 98620-1188','email':'rafa@x.com','status':'bloqueado','criado_em':'2026-09-10T10:00:00'}],
 'avisos':[],'problemas':[],'espera':[],'admins':['adm1'],'faq':[],'app_config':[],'sent':[],'secret':'k',
 'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':L,'email':'lucas@x.com','password':'abc12345'},{'id':'mari','email':'mari@x.com','password':'abc12345'},{'id':'rafa','email':'rafa@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
errs=[]; log=[]
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def txt(pg,sel): return re.sub(r'\s+',' ',(pg.text_content(sel) or '')).strip()
def db(pg): return json.loads(pg.evaluate("localStorage.getItem('mockdb')"))
def ctx_(b, vp, mobile=False):
    c=b.new_context(viewport=vp, accept_downloads=True, device_scale_factor=2 if mobile else 1)
    c.grant_permissions(['clipboard-read','clipboard-write'], origin='http://localhost:8765')
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort()); c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
    c.route('https://abcdefghijkl.supabase.co/functions/v1/push**', lambda r: r.fulfill(status=200, body='BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n' if 'agenda=' in r.request.url else '{"ok":true,"funcao":"push","versao":2}', headers={'Access-Control-Allow-Origin':'*'}))
    c.add_init_script(init); return c
def qr_of(pg, sel):
    png=pg.query_selector(sel).screenshot(); img=cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_GRAYSCALE)
    img=cv2.copyMakeBorder(img,40,40,40,40,cv2.BORDER_CONSTANT,value=255); return cv2.QRCodeDetector().detectAndDecode(img)[0]
def login_d(pg, email):
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email',email); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1300)
with sync_playwright() as p:
    b=p.chromium.launch(); c=ctx_(b,{'width':1280,'height':900}); pg=c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)))
    # A. página inicial leva ao login
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900)
    clk(pg,'#start'); pg.wait_for_timeout(500)
    log.append(('agendar -> login', pg.url.split('/')[-1], txt(pg,'#dl-title'), txt(pg,'#dl-lead')[:60]))
    log.append(('como funciona', txt(pg,'#como .steps4')[:120]))
    # B. administradora
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(600)
    pg.fill('#dl-email','t@x.com'); pg.fill('#dl-pass','senha12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1300)
    log.append(('resumo pendentes', txt(pg,'#r-app')[:110], 'badge', txt(pg,'#view-admin .side [data-tab="dentistas"] .badge')))
    log.append(('avaliacoes', txt(pg,'#r-aval')[:150]))
    pg.screenshot(path=O+'a_resumo.png')
    clk(pg,'#r-app [data-acesso="mari|liberado"]'); pg.wait_for_timeout(900)
    log.append(('liberou mari', [x['status'] for x in db(pg)['dentists'] if x['id']=='mari'], db(pg)['sent'][-1:], 'pend agora', txt(pg,'#r-app')[:40]))
    clk(pg,'#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(500)
    log.append(('tabela tags', txt(pg,'#d-body')[:200]))
    pg.evaluate("document.querySelector('#d-body tr[data-dent=\"rafa\"]').click()"); pg.wait_for_timeout(500)
    log.append(('drawer rafael', txt(pg,'#dr-body .acesso-box')[:140], bool(pg.query_selector('#dr-body [data-recibo]'))))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    # Ajustes
    clk(pg,'#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(900)
    log.append(('resumos ajustes', [txt(pg,'#sum-'+k) for k in ['valores','func','fechadas','pag','regras','rel','app','email','tema']]))
    pg.screenshot(path=O+'a_ajustes.png', full_page=True)
    pg.evaluate("document.querySelector('[data-acc=valores]').open=true"); pg.wait_for_timeout(200)
    pg.fill('#vf-hora','80'); pg.fill('#vf [data-vdia="6"]','90'); clk(pg,'[data-aj="addfaixa"]'); clk(pg,'[data-aj="addpac"]')
    pg.select_option('#vf-faixas [data-k="de"]','18'); pg.select_option('#vf-faixas [data-k="ate"]','20'); pg.fill('#vf-faixas [data-k="valor"]','100')
    pg.fill('#vf-pacs [data-k="horas"]','10'); pg.fill('#vf-pacs [data-k="valor"]','700')
    clk(pg,'#vf button[type=submit]'); pg.wait_for_timeout(900)
    dd=db(pg); log.append(('valores salvos', txt(pg,'#vf .aj-fb'), dd['cfg']['valorHora'], dd['cfg']['precos'], dd['cfg']['pacotes'], 'valores reservas', [x.get('valor') for x in dd['bookings']], 'resumo', txt(pg,'#sum-valores')))
    pg.evaluate("document.querySelector('[data-acc=valores]').open=false; document.querySelector('[data-acc=func]').open=true"); pg.wait_for_timeout(200)
    pg.select_option('#ff-abre','7'); pg.select_option('#ff-fecha','20'); clk(pg,'#ff button[type=submit]'); pg.wait_for_timeout(900)
    log.append(('funcionamento', txt(pg,'#ff .aj-fb')[:40], db(pg)['cfg']['abre'], db(pg)['cfg']['fecha'], txt(pg,'#sum-func')))
    pg.select_option('#ff-fecha','6'); clk(pg,'#ff button[type=submit]'); pg.wait_for_timeout(300); log.append(('fecha antes de abrir', txt(pg,'#ff .aj-fb')))
    pg.evaluate("document.querySelector('[data-acc=func]').open=false; document.querySelector('[data-acc=pag]').open=true"); pg.wait_for_timeout(200)
    pg.select_option('#pf-tipo','cel'); pg.fill('#pf-chave','(31) 98582-5564'); pg.fill('#pf-nome','Thalia Santiago'); pg.wait_for_timeout(300)
    log.append(('pix previa qr', qr_of(pg,'#pf-prev .pix-qr svg')[:60]))
    pg.select_option('#pf-lim','5'); clk(pg,'#pf button[type=submit]'); pg.wait_for_timeout(900)
    log.append(('pix salvo', txt(pg,'#pf .aj-fb'), db(pg)['cfg']['pix'], db(pg)['cfg']['limiteAtrasoDias']))
    pg.screenshot(path=O+'a_pag.png', full_page=True)
    pg.evaluate("document.querySelector('[data-acc=pag]').open=false; document.querySelector('[data-acc=regras]').open=true"); pg.wait_for_timeout(200)
    pg.fill('#rf-check','Instrumentais recolhidos\nBancada limpa\nLuzes apagadas'); pg.fill('#rf-eq','Cadeira Gnatus\nAutoclave 21L'); pg.fill('#rf-wifi','Consultorio / 1234')
    clk(pg,'#rf button[type=submit]'); pg.wait_for_timeout(900); log.append(('regras', txt(pg,'#rf .aj-fb'), db(pg)['cfg']['checklist'], db(pg)['cfg']['espaco']['equipamentos']))
    pg.evaluate("document.querySelector('[data-acc=regras]').open=false; document.querySelector('[data-acc=rel]').open=true"); pg.wait_for_timeout(200)
    clk(pg,'[data-aj="relatorio"]'); pg.wait_for_timeout(600); log.append(('relatorio', txt(pg,'#acc-rel .aj-fb')))
    clk(pg,'#gf-agenda [data-aj="agenda"]'); pg.wait_for_timeout(800); log.append(('agenda link', pg.input_value('#gf-agenda input')[-40:], txt(pg,'#acc-rel .aj-fb')[:30]))
    clk(pg,'[data-aj="testaragenda"]'); pg.wait_for_timeout(600); log.append(('testar agenda', txt(pg,'#acc-rel .aj-fb')))
    clk(pg,'#gf-rel'); pg.wait_for_timeout(800); log.append(('rel toggle', db(pg)['cfg']['relatorioMensal'], txt(pg,'#acc-rel .aj-fb')))
    pg.evaluate("document.querySelector('[data-acc=fechadas]').open=true"); pg.wait_for_timeout(200)
    clk(pg,'[data-aj="bloquear"]'); pg.wait_for_timeout(500); log.append(('fechar datas abre form', pg.is_visible('#bf-mot')))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    # valor de uma reserva
    clk(pg,'#view-admin .side [data-tab="agenda"]'); clk(pg,'#a-views [data-view="lista"]'); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelectorAll('#chips .chip').forEach(c=>{ if(/Todas/.test(c.textContent)) c.click() })"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#alist [data-bk=\"f1\"]').click()"); pg.wait_for_timeout(500)
    log.append(('valor na reserva', pg.input_value('#dr-body .val-edit input')))
    pg.fill('#dr-body .val-edit input','150'); clk(pg,'#dr-body .val-edit button'); pg.wait_for_timeout(700)
    log.append(('valor editado', [x.get('valor') for x in db(pg)['bookings'] if x['id']=='f1'], txt(pg,'#dr-body .val-edit .hint')))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    # recibo pela administradora
    clk(pg,'#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#d-body tr[data-dent=\"lucas1\"]').click()"); pg.wait_for_timeout(500)
    with pg.expect_download() as dl: clk(pg,'#dr-body [data-recibo]')
    path=dl.value.path(); raw=open(path,'rb').read(); open(O+'recibo_admin.pdf','wb').write(raw)
    log.append(('recibo admin', dl.value.suggested_filename, raw[:5], subprocess.run(['pdftotext','-layout',O+'recibo_admin.pdf','-'],capture_output=True,text=True).stdout.strip().replace('\n',' | ')[:400]))
    clk(pg,'#dr-close'); clk(pg,'#view-admin [data-logout]'); pg.wait_for_timeout(800)
    # C. dentista liberado: Pix e recibo
    login_d(pg,'lucas@x.com')
    log.append(('dentista inicio', txt(pg,'#c-inicio')[:80]))
    clk(pg,'#view-dent .side [data-ctab="financeiro"]'); pg.wait_for_timeout(600)
    log.append(('fin pix', txt(pg,'#cf-pix')[:200]))
    q=qr_of(pg,'#cf-pix .pix-qr svg'); log.append(('qr mes', q[:30], '540' in q, re.search(r'54\d\d([\d.]+)',q).group(1) if q else None))
    clk(pg,'#cf-pix [data-pixcp]'); pg.wait_for_timeout(300); log.append(('copiou', pg.evaluate('navigator.clipboard.readText()')==q, txt(pg,'#cf-pix .pix-fb')))
    pg.screenshot(path=O+'d_fin.png', full_page=True)
    with pg.expect_download() as dl: clk(pg,'#cf-pix [data-recibo]')
    raw=open(dl.value.path(),'rb').read(); open(O+'recibo_dent.pdf','wb').write(raw); log.append(('recibo dentista', dl.value.suggested_filename, raw[:5]))
    clk(pg,'#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#cr-list [data-cbk=\"f1\"]').click()"); pg.wait_for_timeout(600)
    q2=qr_of(pg,'#c-drawer .pix-qr svg'); log.append(('pix reserva', '5406150.00' in q2, q2[-30:]))
    clk(pg,'#view-dent [data-dlogout]'); pg.wait_for_timeout(800)
    # D. bloqueado e cadastro novo
    login_d(pg,'rafa@x.com'); log.append(('bloqueado ve', txt(pg,'#c-wait')[:90], 'menu oculto', not pg.is_visible('#view-dent .side')))
    clk(pg,'#c-wait [data-dlogout]'); pg.wait_for_timeout(800)
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(600)
    clk(pg,'#dl-seg [data-dl="reg"]'); pg.wait_for_timeout(200)
    pg.fill('#dr-nome','Beatriz Lima'); pg.fill('#dr-tel','(31) 91234-5678'); pg.fill('#dr-email','bia@x.com'); pg.fill('#dr-pass','abc12345'); pg.fill('#dr-pass2','abc12345'); clk(pg,'#dr-accept'); clk(pg,'#dl-reg button[type=submit]'); pg.wait_for_timeout(1500)
    log.append(('cadastro novo', txt(pg,'#c-wait')[:120], [x['status'] for x in db(pg)['dentists'] if x['email']=='bia@x.com']))
    pg.screenshot(path=O+'d_wait.png')
    # dentista pendente tentando reservar direto pela função (simula burlar a tela)
    r=pg.evaluate("window.supabase.createClient('a','b').rpc('reservar',{p_nome:'Beatriz Lima',p_tel:'(31) 91234-5678',p_date:'%s',p_from:9,p_to:10})" % d(5))
    log.append(('pendente reserva via api', r.get('error')))
    b.close()
for l in log: print(*l)
print('ERRS', errs)
