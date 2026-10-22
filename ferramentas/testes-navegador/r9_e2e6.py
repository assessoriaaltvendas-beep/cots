import json, datetime as dt, re, io
from playwright.sync_api import sync_playwright
from PIL import Image
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../..')
S = os.environ.get('COTS_SAIDA', '/tmp/cots-testes'); O=S+'/app/s6/'  # pasta de saída (prints, PDFs)
import os; os.makedirs(O, exist_ok=True)
mock='window.MOCK_TERMOS_OK=1;\n' + open(AQUI + '/mock-supabase.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
t=dt.date.today()
def d(off):
    x=t+dt.timedelta(days=off)
    while x.weekday()==6: x+=dt.timedelta(days=1)
    return x.isoformat()
D3=d(3); L='lucas1'
seed={'slots':[{'date':D3,'hour':h,'booking_id':'r1'} for h in (9,10)],'bookings':[{'id':'r1','dentist_id':'rafa','nome':'Rafael Nunes','tel':'(31) 98620-1188','primeira':False,'date':D3,'h_from':9,'h_to':11,'status':'ativo','origem':'area-dentista','pago':False,'valor':100,'criado_em':'2026-10-01T10:00:00'}],
 'dentists':[{'id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','whatsapp':'(31) 98841-5460','email':'lucas@x.com','status':'liberado','criado_em':'2026-09-01T10:00:00'},
             {'id':'rafa','nome':'Rafael Nunes','cro':'CRO-MG 8','whatsapp':'(31) 98620-1188','email':'rafa@x.com','status':'liberado','criado_em':'2026-09-10T10:00:00'}],
 'avisos':[],'problemas':[],'espera':[],'admins':['adm1'],'faq':[],'app_config':[],'sent':[],'secret':'k',
 'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':L,'email':'lucas@x.com','password':'abc12345'},{'id':'rafa','email':'rafa@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
buf=io.BytesIO(); Image.new('RGB',(600,400),(40,40,40)).save(buf,'PNG'); png=buf.getvalue()
errs=[]; log=[]
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def txt(pg,sel): return re.sub(r'\s+',' ',(pg.text_content(sel) or '')).strip()
def db(pg): return json.loads(pg.evaluate("localStorage.getItem('mockdb')"))
def ctx_(b, vp, dsf=1):
    c=b.new_context(viewport=vp, device_scale_factor=dsf)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort()); c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
    c.add_init_script(init); return c
def login_d(pg, email):
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email',email); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1300)
def login_a(pg):
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(600)
    pg.fill('#dl-email','t@x.com'); pg.fill('#dl-pass','senha12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1300)
with sync_playwright() as p:
    b=p.chromium.launch(); c=ctx_(b,{'width':1280,'height':900}); pg=c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900)
    body=txt(pg,'body'); log.append(('contato', '99574-5413' in body, 'Galeria Êxito' in body, '8582' in body, 'wa.me/5531995745413' in pg.content()))
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(500)
    pg.fill('#dl-pass','segredo1'); clk(pg,'#view-dlogin .pw-eye'); log.append(('olho', pg.get_attribute('#dl-pass','type')))
    clk(pg,'#view-dlogin .pw-eye'); log.append(('olho de novo', pg.get_attribute('#dl-pass','type'), 'lembrar', pg.is_checked('#view-dlogin [data-lembrar]')))
    r=pg.evaluate("(()=>{setLembrar(false); sessaoStorage.setItem('tk','v1'); const a=[localStorage.getItem('tk'), sessionStorage.getItem('tk'), sessaoStorage.getItem('tk')]; setLembrar(true); sessaoStorage.setItem('tk','v2'); a.push(localStorage.getItem('tk'), sessionStorage.getItem('tk')); sessaoStorage.removeItem('tk'); return a})()")
    log.append(('lembrar storage', r))
    # dentista: períodos
    login_d(pg,'lucas@x.com'); clk(pg,'#view-dent .side [data-ctab="nova"]'); pg.wait_for_timeout(400)
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{date:'{d(4)}',start:null,end:null}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    log.append(('chips periodo', txt(pg,'#cn-per')))
    pg.screenshot(path=O+'d_periodos.png')
    clk(pg,'#cn-per [data-per="8|13"]'); pg.wait_for_timeout(300)
    log.append(('manha', txt(pg,'#cn-sum'), pg.is_disabled('#cn-confirm')))
    pg.evaluate("(()=>{Object.assign(S.cn,{start:11,end:14}); renderCNova();})()"); pg.wait_for_timeout(300)
    log.append(('11-15', txt(pg,'#cn-peraviso')[:90], 'confirmar desabilitado', pg.is_disabled('#cn-confirm')))
    pg.screenshot(path=O+'d_cruza.png')
    pg.evaluate("(()=>{Object.assign(S.cn,{start:9,end:11}); renderCNova();})()"); pg.wait_for_timeout(300)
    log.append(('3h', txt(pg,'#cn-sum')[-12:], pg.is_disabled('#cn-confirm')))
    clk(pg,'#cn-per [data-per="8|18"]'); pg.wait_for_timeout(200); clk(pg,'#cn-confirm'); pg.wait_for_timeout(1000)
    log.append(('diaria reservada', [(x['h_from'],x['h_to'],x.get('valor')) for x in db(pg)['bookings'] if x['dentist_id']==L]))
    clk(pg,'#view-dent [data-dlogout]'); pg.wait_for_timeout(800)
    # administradora: dentistas
    login_a(pg); clk(pg,'#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(500)
    log.append(('acoes na tabela', len(pg.query_selector_all('#d-body [data-dedit]')), len(pg.query_selector_all('#d-body [data-ddel]'))))
    pg.screenshot(path=O+'a_dentistas.png')
    clk(pg,'#d-body [data-dedit="rafa"]'); pg.wait_for_timeout(400); pg.fill('#de-nome','Rafael Nunes Silva'); clk(pg,'#dr-body button[type=submit]'); pg.wait_for_timeout(700)
    log.append(('editou', txt(pg,'#de-fb'), [x['nome'] for x in db(pg)['dentists'] if x['id']=='rafa'], 'drawer aberto', pg.is_visible('#drawer')))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    clk(pg,'#d-body [data-ddel="rafa"]'); pg.wait_for_timeout(200); log.append(('confirmar', txt(pg,'#d-body [data-ddel="rafa"]')))
    clk(pg,'#d-body [data-ddel="rafa"]'); pg.wait_for_timeout(900)
    dd=db(pg); log.append(('excluiu', [x['id'] for x in dd['dentists']], 'reserva mantida', [(x['nome'],x['dentist_id']) for x in dd['bookings'] if x['id']=='r1']))
    # pacientes
    clk(pg,'#view-admin .side [data-tab="pacientes"]'); pg.wait_for_timeout(500)
    log.append(('aba pacientes', txt(pg,'#p-lista')[:90]))
    clk(pg,'#p-lista [data-pa="novo"]'); pg.wait_for_timeout(400)
    pg.fill('#pp-nome','Joana Silva'); pg.fill('#pp-tel','(31) 98888-1234'); pg.fill('#pp-nasc','1990-05-10'); pg.fill('#pp-obs','Alergia a dipirona.')
    clk(pg,'#dr-body button[type=submit]'); pg.wait_for_timeout(900)
    pid=[x['id'] for x in db(pg)['pacientes']][0]
    log.append(('paciente criado', pg.evaluate('S.pac')==pid, txt(pg,'#pf-nome'), txt(pg,'#pf-sub'), txt(pg,'#pf-dados')[-40:]))
    clk(pg,'#p-ficha [data-pa="agendar"]'); pg.wait_for_timeout(400)
    pg.fill('#cf-data', D3); pg.dispatch_event('#cf-data','change'); pg.select_option('#cf-ini','14:30'); pg.select_option('#cf-fim','15:00'); pg.dispatch_event('#cf-fim','change'); pg.wait_for_timeout(200)
    log.append(('ocupado no dia', txt(pg,'#cf-ocup')))
    clk(pg,'#dr-body button[type=submit]'); pg.wait_for_timeout(1300)
    dd=db(pg); log.append(('consulta', [(c['data']==D3,c['inicio'],c['fim'],c['status']) for c in dd['consultas']], 'slots', sorted([(s['hour'],bool(s.get('consulta'))) for s in dd['slots'] if s['date']==D3])))
    clk(pg,'#p-ficha [data-pa="agendar"]'); pg.wait_for_timeout(400)
    pg.fill('#cf-data', D3); pg.dispatch_event('#cf-data','change'); pg.select_option('#cf-ini','14:45'); pg.select_option('#cf-fim','15:15'); pg.dispatch_event('#cf-fim','change'); pg.wait_for_timeout(200)
    log.append(('choque consulta', pg.is_disabled('#dr-body button[type=submit]'), txt(pg,'#cf-ocup .msg')))
    pg.select_option('#cf-ini','09:30'); pg.select_option('#cf-fim','10:00'); pg.dispatch_event('#cf-fim','change'); pg.wait_for_timeout(200)
    log.append(('choque dentista', pg.is_disabled('#dr-body button[type=submit]')))
    pg.select_option('#cf-ini','16:00'); clk(pg,'#cf-dur [data-dur="45"]'); pg.wait_for_timeout(200); log.append(('duracao 45', pg.input_value('#cf-fim')))
    clk(pg,'#dr-close'); pg.wait_for_timeout(300)
    pg.screenshot(path=O+'a_ficha.png', full_page=True)
    log.append(('lembrete wa', (pg.get_attribute('#pf-cons a.ghost','href') or '')[:60]))
    cid=db(pg)['consultas'][0]['id']
    clk(pg,f'[data-cst="{cid}|realizada"]'); pg.wait_for_timeout(700)
    clk(pg,f'[data-cevo="{cid}"]'); pg.wait_for_timeout(500); pg.fill('#pe-texto','Restauração em resina no dente 36. Retorno em 15 dias.'); clk(pg,'#pf-evo-form button[type=submit]'); pg.wait_for_timeout(900)
    log.append(('evolucao', txt(pg,'#pf-evo')[:90], [e['consulta_id']==cid for e in db(pg)['evolucoes']]))
    pg.set_input_files('#pd-file', files=[{'name':'rx-panoramica.png','mimeType':'image/png','buffer':png},{'name':'orcamento.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4 teste'}]); pg.wait_for_timeout(1800)
    log.append(('docs', txt(pg,'#pd-fb'), txt(pg,'#pf-docs')[:120], txt(pg,'#pf-uso')))
    with pg.expect_popup() as pop: clk(pg,'[data-dopen]')
    log.append(('abrir doc', pop.value.url[:22]))
    pop.value.close()
    did=db(pg)['paciente_docs'][0]['id']; clk(pg,f'[data-docdel="{did}"]'); clk(pg,f'[data-docdel="{did}"]'); pg.wait_for_timeout(700)
    log.append(('doc excluido', len(db(pg)['paciente_docs']), len(db(pg)['files']['pacientes'])))
    pg.screenshot(path=O+'a_ficha2.png', full_page=True)
    clk(pg,'#view-admin .side [data-tab="agenda"]'); clk(pg,'#a-views [data-view="semana"]'); pg.wait_for_timeout(300)
    pg.evaluate(f"(()=>{{S.aDate=new Date('{D3}T12:00'); renderAdmin();}})()"); pg.wait_for_timeout(400)
    log.append(('agenda consulta', txt(pg,'#a-grid .ev.paciente')))
    pg.screenshot(path=O+'a_agenda.png')
    clk(pg,'#a-grid .ev.paciente'); pg.wait_for_timeout(500); log.append(('clique abre ficha', pg.evaluate('S.tab'), pg.evaluate('S.pac')==pid))
    clk(pg,'#view-admin .side [data-tab="resumo"]'); pg.wait_for_timeout(400); log.append(('resumo pac', txt(pg,'#r-pac')[:60]))
    # ajustes: períodos
    clk(pg,'#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(900); pg.evaluate("document.querySelector('[data-acc=valores]').open=true"); pg.wait_for_timeout(200)
    log.append(('periodos form', len(pg.query_selector_all('#vf-pers [data-row="per"]')), pg.is_checked('#vf-dia'), pg.input_value('#vf-dval'), txt(pg,'#sum-valores')))
    pg.fill('#vf-dval','360'); clk(pg,'#vf button[type=submit]'); pg.wait_for_timeout(800)
    log.append(('salvou diaria', txt(pg,'#vf .aj-fb')[:30], db(pg)['cfg'].get('diaria'), db(pg)['cfg'].get('limiteHoras')))
    pg.screenshot(path=O+'a_valores.png', full_page=True)
    clk(pg,'#view-admin [data-logout]'); pg.wait_for_timeout(800)
    # dentista vê ocupado, sem nome
    login_d(pg,'lucas@x.com'); clk(pg,'#view-dent .side [data-ctab="nova"]'); pg.wait_for_timeout(400)
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{date:'{D3}',start:null,end:null}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    log.append(('dentista 14h', txt(pg,'#cn-hours')[60:140], 'Joana' in pg.content(), 'Dipirona' in pg.content()))
    clk(pg,'#view-dent [data-dlogout]'); pg.wait_for_timeout(800)
    # excluir paciente
    login_a(pg); pg.evaluate(f"(()=>{{S.pac='{pid}'; setTab('pacientes');}})()"); pg.wait_for_timeout(500)
    clk(pg,'#p-ficha [data-pa="excluir"]'); clk(pg,'#p-ficha [data-pa="excluir"]'); pg.wait_for_timeout(900)
    dd=db(pg); log.append(('paciente excluido', len(dd['pacientes']), len(dd['consultas']), sorted(s['hour'] for s in dd['slots'] if s['date']==D3)))
    # celular
    m=ctx_(b,{'width':390,'height':844},2).new_page(); m.on('pageerror',lambda e:errs.append(str(e)))
    login_a(m); log.append(('barra celular', [x.text_content().strip() for x in m.query_selector_all('#view-admin .side > button') if x.is_visible()]))
    m.click('#view-admin .more-btn'); m.wait_for_timeout(200); log.append(('mais', txt(m,'#view-admin .more-sheet')))
    m.screenshot(path=O+'m_admin.png')
    b.close()
for l in log: print(*l)
print('ERRS', errs)
