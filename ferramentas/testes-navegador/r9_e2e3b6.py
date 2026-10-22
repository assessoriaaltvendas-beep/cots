import json, datetime as dt, io
from playwright.sync_api import sync_playwright
from PIL import Image
S='/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad'
mock=open(S+'/app/mock9r.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
t=dt.date.today()
def wd(off):
    d=t+dt.timedelta(days=off)
    return d
L='lucas1'
past=[wd(-7),wd(-14)]
bk=[]
for i,d in enumerate(past):
    bk.append({'id':f'p{i}','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':d.isoformat(),'h_from':14,'h_to':16,'status':'ativo','origem':'area-dentista','pago':False,'criado_em':(dt.datetime.now()-dt.timedelta(days=20)).isoformat()})
fut=wd(5)
if fut.weekday()==6: fut+=dt.timedelta(days=1)
bk.append({'id':'f1','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':fut.isoformat(),'h_from':9,'h_to':11,'status':'ativo','origem':'area-dentista','pago':False,'criado_em':dt.datetime.now().isoformat()})
slots=[{'date':fut.isoformat(),'hour':h,'booking_id':'f1'} for h in (9,10)]
seed={'slots':slots,'bookings':bk,'dentists':[{'id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','whatsapp':'(31) 98841-5460','email':'lucas@x.com','criado_em':'2026-09-01T10:00:00'}],
 'avisos':[],'problemas':[],'espera':[],'admins':['adm1'],
 'faq':[{'id':'q1','pergunta':'Como faço para reservar?','resposta':'Toque em Agendar horário.','ordem':1},{'id':'q2','pergunta':'Posso cancelar?','resposta':'Até 24 horas antes.','ordem':2}],
 'app_config':[],'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':L,'email':'lucas@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
buf=io.BytesIO(); Image.new('RGB',(900,600),(200,170,160)).save(buf,'PNG'); png=buf.getvalue()
errs=[]; log=[]
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def txt(pg,sel): return (pg.text_content(sel) or '').strip()
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    ctx.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.abort()); ctx.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html><body style="background:#e8e2df">mapa</body></html>', content_type='text/html'))
    ctx.add_init_script(init)
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8765/',wait_until='domcontentloaded'); pg.wait_for_timeout(900)
    log.append(('faq visivel', pg.is_visible('#perguntas'), len(pg.query_selector_all('#faq-list details'))))
    log.append(('galeria oculta sem fotos', pg.is_hidden('#fotos')))
    log.append(('mapa', (pg.get_attribute('#gmap','src') or '')[:40]))
    log.append(('instagram', pg.get_attribute('.tb-r[data-href="ig"]','href'), txt(pg,'.tb-r[data-href="ig"]')))
    log.append(('wa flutuante', pg.is_visible('.wa-float')))
    # dentista
    pg.evaluate("location.hash='#dentista'"); pg.wait_for_timeout(300)
    pg.fill('#dl-email','lucas@x.com'); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(900)
    log.append(('reserva rapida', txt(pg,'#ci-alerts')[:120]))
    pg.screenshot(path=S+'/v3/T_dent_inicio.png')
    n0=len(json.loads(pg.evaluate("localStorage.getItem('mockdb')"))['bookings'])
    clk(pg,'[data-qb]'); pg.wait_for_timeout(200); clk(pg,'[data-qb]'); pg.wait_for_timeout(900)
    n1=len(json.loads(pg.evaluate("localStorage.getItem('mockdb')"))['bookings'])
    log.append(('reserva rapida criou', n1-n0, txt(pg,'#ci-alerts')[:80]))
    # comprovante e remarcar na reserva futura f1
    clk(pg,'#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#cr-list [data-cbk=\"f1\"]').click()"); pg.wait_for_timeout(300)
    log.append(('drawer agenda+comprovante', len(pg.query_selector_all('#c-drawer .cal-a')), pg.query_selector('#c-drawer input[data-comp]') is not None))
    pg.set_input_files('#c-drawer input[data-comp]', files=[{'name':'pix.png','mimeType':'image/png','buffer':png}]); pg.wait_for_timeout(1500)
    log.append(('comprovante', txt(pg,'#c-drawer .block:nth-of-type(3)')[:90] if False else [x.get('comprovante_path') for x in json.loads(pg.evaluate("localStorage.getItem('mockdb')"))['bookings'] if x['id']=='f1']))
    pg.screenshot(path=S+'/v3/T_dent_drawer.png')
    clk(pg,'#c-drawer [data-remarcar]'); pg.wait_for_timeout(400)
    log.append(('remarcar banner', txt(pg,'#cn-top')[:70]))
    days=[d for d in pg.query_selector_all('#cn-days .day') if not d.is_disabled()]; days[1].evaluate('e=>e.click()')
    hrs=[x for x in pg.query_selector_all('#cn-hours .hour') if not x.is_disabled() and 'busy' not in (x.get_attribute('class') or '')]
    hrs[1].evaluate('e=>e.click()'); hrs[2].evaluate('e=>e.click()'); pg.wait_for_timeout(150)
    log.append(('repetir oculto ao remarcar', pg.is_hidden('#cn-weeks-wrap')))
    clk(pg,'#cn-confirm'); pg.wait_for_timeout(1000)
    log.append(('remarcado', txt(pg,'#cn-done h2'), [x['status'] for x in json.loads(pg.evaluate("localStorage.getItem('mockdb')"))['bookings'] if x['id']=='f1']))
    clk(pg,'#view-dent [data-dlogout]'); pg.wait_for_timeout(600)
    # admin
    pg.evaluate("location.hash='#admin'"); pg.wait_for_timeout(300)
    pg.fill('#dl-email','t@x.com'); pg.fill('#dl-pass','senha12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(900)
    clk(pg,'#view-admin .side [data-tab="agenda"]'); clk(pg,'#a-views [data-view="semana"]'); pg.wait_for_timeout(200)
    clk(pg,'#a-block'); pg.wait_for_timeout(300)
    tm=t+dt.timedelta(days=2)
    if tm.weekday()==6: tm+=dt.timedelta(days=1)
    pg.fill('#bf-mot','Manutenção'); pg.fill('#bf-d1',tm.isoformat()); pg.fill('#bf-d2',tm.isoformat()); pg.dispatch_event('#bf-d2','change'); pg.wait_for_timeout(200)
    log.append(('bloqueio previa', txt(pg,'#bf-prev')))
    clk(pg,'#bf-go'); pg.wait_for_timeout(900); log.append(('bloqueio', txt(pg,'#bf-fb')))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    log.append(('eventos bloqueio na agenda', len(pg.query_selector_all('.ev.bloqueio'))))
    clk(pg,'#a-new'); pg.wait_for_timeout(300)
    pg.select_option('#nf-dent', L); d3=t+dt.timedelta(days=3)
    if d3.weekday()==6: d3+=dt.timedelta(days=1)
    pg.fill('#nf-date', d3.isoformat()); pg.dispatch_event('#nf-date','change'); pg.wait_for_timeout(150)
    log.append(('nova reserva busy', txt(pg,'#nf-busy')))
    clk(pg,'#nf-go'); pg.wait_for_timeout(800); log.append(('nova reserva painel', txt(pg,'#nf-fb')))
    pg.screenshot(path=S+'/v3/T_admin_form.png')
    clk(pg,'#dr-close'); pg.wait_for_timeout(200)
    pg.screenshot(path=S+'/v3/T_admin_agenda.png')
    clk(pg,'#view-admin .side [data-tab="financeiro"]'); pg.wait_for_timeout(200)
    with pg.expect_download() as d: clk(pg,'#f-csv')
    csv=open(d.value.path(),encoding='utf-8-sig').read().splitlines(); log.append(('csv', d.value.suggested_filename, len(csv), csv[0][:60]))
    clk(pg,'#view-admin .side [data-tab="site"]'); pg.wait_for_timeout(200)
    pg.set_input_files('#sf-file', files=[{'name':'sala.png','mimeType':'image/png','buffer':png}]); pg.wait_for_timeout(1800)
    log.append(('fotos', txt(pg,'#sf-count'), txt(pg,'#sf-fb')))
    pg.fill('#fq-p','O que está incluso no aluguel?'); pg.fill('#fq-r','Cadeira, autoclave e materiais básicos.'); clk(pg,'#fq-form button[type=submit]'); pg.wait_for_timeout(700)
    log.append(('faq painel', len(pg.query_selector_all('#fq-list .mini-row')), txt(pg,'#fq-fb')))
    pg.screenshot(path=S+'/v3/T_admin_site.png', full_page=True)
    clk(pg,'#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(500); pg.evaluate("document.querySelectorAll('.acc').forEach(d=>d.open=true)"); pg.wait_for_timeout(300)
    pg.fill('#em-admin','thalia@x.com'); pg.fill('#em-from','contato@x.com'); pg.fill('#em-key','xkeysib-abc'); clk(pg,'#em-form button[type=submit]'); pg.wait_for_timeout(700)
    log.append(('email status', txt(pg,'#em-status'), txt(pg,'#em-fb')))
    clk(pg,'#em-test'); pg.wait_for_timeout(500); log.append(('email teste', txt(pg,'#em-fb')[:60]))
    pg.screenshot(path=S+'/v3/T_admin_ajustes.png', full_page=True)
    # comprovante visível para a administradora
    clk(pg,'#view-admin .side [data-tab="agenda"]'); clk(pg,'#a-views [data-view="lista"]'); clk(pg,'#chips .chip',2); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#alist [data-bk=\"f1\"]') && document.querySelector('#alist [data-bk=\"f1\"]').click()"); pg.wait_for_timeout(500)
    a=pg.query_selector('#dr-body a.ghost'); log.append(('ver comprovante', a and (a.text_content(), (a.get_attribute('href') or '')[:22])))
    clk(pg,'#dr-close')
    clk(pg,'#view-admin [data-logout]'); pg.wait_for_timeout(600)
    pg.goto('http://localhost:8765/',wait_until='domcontentloaded'); pg.wait_for_timeout(900)
    log.append(('publico galeria', pg.is_visible('#fotos'), len(pg.query_selector_all('#gal .gal-item')), 'faq', len(pg.query_selector_all('#faq-list details'))))
    clk(pg,'#gal .gal-item'); pg.wait_for_timeout(200); log.append(('foto ampliada', pg.is_visible('#lb'))); pg.keyboard.press('Escape')
    pg.screenshot(path=S+'/v3/T_home.png', full_page=True)
    m=b.new_page(viewport={'width':390,'height':844}); m.on('pageerror',lambda e:errs.append(str(e)))
    m.goto('http://localhost:8765/',wait_until='domcontentloaded'); m.wait_for_timeout(800)
    log.append(('mobile largura', m.evaluate('document.documentElement.scrollWidth')))
    m.screenshot(path=S+'/v3/T_home_mob.png', full_page=True)
    b.close()
for l in log: print(l)
print('ERRS', errs)
