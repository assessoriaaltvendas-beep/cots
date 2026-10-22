import json, datetime as dt
from playwright.sync_api import sync_playwright
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../..')
S = os.environ.get('COTS_SAIDA', '/tmp/cots-testes'); O=S+'/app/'; os.makedirs(O, exist_ok=True)  # pasta de saída (prints, PDFs)
mock='window.MOCK_TERMOS_OK=1;\n' + open(AQUI + '/mock-supabase.js').read()
cfg="window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'"+'x'*60+"'};"
t=dt.date.today(); L='lucas1'
fut=t+dt.timedelta(days=5)
if fut.weekday()==6: fut+=dt.timedelta(days=1)
seed={'slots':[],'bookings':[{'id':'p1','dentist_id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','tel':'(31) 98841-5460','primeira':False,'date':(t-dt.timedelta(days=7)).isoformat(),'h_from':14,'h_to':16,'status':'ativo','origem':'area-dentista','pago':False,'criado_em':'2026-10-01T10:00:00'}],
 'dentists':[{'id':L,'nome':'Lucas Andrade','cro':'CRO-MG 1','whatsapp':'(31) 98841-5460','email':'lucas@x.com','criado_em':'2026-09-01T10:00:00'}],
 'avisos':[],'problemas':[],'espera':[],'admins':['adm1'],'faq':[],'app_config':[],
 'users':[{'id':'adm1','email':'t@x.com','password':'senha12345'},{'id':L,'email':'lucas@x.com','password':'abc12345'}]}
init="if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb',"+json.dumps(json.dumps(seed))+");"
fake='''(() => { if (!window.PushManager) return;
  const mk = d => d && ({ endpoint: d.endpoint, options: { applicationServerKey: Uint8Array.from(atob(d.key.replace(/-/g,'+').replace(/_/g,'/') + '='.repeat((4 - d.key.length % 4) % 4)), c => c.charCodeAt(0)).buffer },
    toJSON() { return { endpoint: d.endpoint, keys: { p256dh: 'B' + 'x'.repeat(86), auth: 'a'.repeat(22) } }; },
    async unsubscribe() { localStorage.removeItem('fakesub'); return true; } });
  PushManager.prototype.getSubscription = async function () { return mk(JSON.parse(localStorage.getItem('fakesub') || 'null')); };
  PushManager.prototype.subscribe = async function (o) { const k = btoa(String.fromCharCode(...new Uint8Array(o.applicationServerKey))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,''); const d = { endpoint: 'https://fcm.googleapis.com/fcm/send/' + Math.random().toString(36).slice(2), key: k }; localStorage.setItem('fakesub', JSON.stringify(d)); return mk(d); };
})();'''
errs=[]; log=[]
fn={'mode':'401'}
def clk(pg,sel,i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def txt(pg,sel): return (pg.text_content(sel) or '').strip()
def db(pg): return json.loads(pg.evaluate("localStorage.getItem('mockdb')"))
def fnroute(r):
    if fn['mode']=='401': r.fulfill(status=401, body='{"msg":"Invalid JWT"}', headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'})
    else: r.fulfill(status=200, body='{"ok":true,"funcao":"push"}', headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'})
def ctx_(b, vp, perms):
    c=b.new_context(viewport=vp)
    if perms: c.grant_permissions(perms, origin='http://localhost:8765')
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort()); c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
    c.route('https://abcdefghijkl.supabase.co/functions/v1/push', fnroute)
    perm = 'granted' if perms else 'default'
    c.add_init_script("if(!localStorage.getItem('perm'))localStorage.setItem('perm','%s');Object.defineProperty(Notification,'permission',{get:()=>localStorage.getItem('perm')});Notification.requestPermission=async()=>{localStorage.setItem('perm','granted');return 'granted'};" % perm)
    c.add_init_script(init); c.add_init_script(fake); return c
with sync_playwright() as p:
    b=p.chromium.launch()
    c=ctx_(b,{'width':1280,'height':900},['notifications','clipboard-read','clipboard-write']); pg=c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(700)
    pg.fill('#dl-email','t@x.com'); pg.fill('#dl-pass','senha12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1200)
    log.append(('resumo dica sem config', txt(pg,'#r-app')))
    clk(pg,'#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(600); pg.evaluate("document.querySelectorAll('.acc').forEach(d=>d.open=true)"); pg.wait_for_timeout(300)
    log.append(('card admin', txt(pg,'#app-a')[:160]))
    clk(pg,'#app-a [data-app="copiar"]'); pg.wait_for_timeout(700)
    clip=pg.evaluate('navigator.clipboard.readText()'); log.append(('copiar', txt(pg,'#app-a .msg'), 'Deno.serve' in clip, len(clip)))
    clk(pg,'#app-a [data-app="configurar"]'); pg.wait_for_timeout(700); log.append(('config 401', txt(pg,'#app-a .msg')))
    fn['mode']='ok'; clk(pg,'#app-a [data-app="configurar"]'); pg.wait_for_timeout(1200); log.append(('config ok', txt(pg,'#app-a .msg'), db(pg).get('push',{}).get('url')))
    log.append(('tag config', txt(pg,'#app-a .push-cfg summary')))
    clk(pg,"#app-a [data-app=\"ligar\"]"); pg.wait_for_timeout(1500)
    d=db(pg); log.append(('ativar', txt(pg,'#app-a .msg'), [(x['user_id'],x['aparelho']) for x in d.get('subs',[])], len(d.get('pushes',[]))))
    log.append(('estado', txt(pg,'#app-a .app-row:nth-child(2) b')))
    pg.screenshot(path=O+'s_admin_ajustes.png', full_page=False, clip={'x':0,'y':0,'width':1280,'height':900})
    el=pg.query_selector('#app-a'); el.scroll_into_view_if_needed(); el.screenshot(path=O+'s_card_admin.png')
    clk(pg,'#app-a [data-app="testar"]'); pg.wait_for_timeout(700); log.append(('testar', txt(pg,'#app-a .msg')))
    clk(pg,'#app-a [data-app="desligar"]'); pg.wait_for_timeout(700); log.append(('desligar', txt(pg,'#app-a .msg'), len(db(pg).get('subs',[])), pg.evaluate("localStorage.getItem('fakesub')")))
    clk(pg,'#app-a [data-app="ligar"]'); pg.wait_for_timeout(1200); log.append(('religar', len(db(pg).get('subs',[]))))
    # service worker: entrega de push e clique
    reg=pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!(r&&r.active))"); log.append(('sw ativo', reg))
    try:
        cdp=c.new_cdp_session(pg); regs=[]
        cdp.on('ServiceWorker.workerRegistrationUpdated', lambda e: regs.extend(e['registrations']))
        cdp.send('ServiceWorker.enable'); pg.wait_for_timeout(500)
        rid=[r for r in regs if not r.get('isDeleted')][0]['registrationId']
        cdp.send('ServiceWorker.deliverPushMessage', {'origin':'http://localhost:8765','registrationId':rid,'data':json.dumps({'title':'Nova reserva · Lucas Andrade','body':'sex, 23/10, 14h às 16h','url':'./#admin','tag':'nova-1'})})
        pg.wait_for_timeout(1200)
        log.append(('notificacao exibida', pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.getNotifications()).then(n=>n.map(x=>[x.title,x.body,x.tag,x.data&&x.data.url]))")))
    except Exception as e: log.append(('cdp push', 'erro', str(e)[:200]))
    clk(pg,'#view-admin [data-logout]'); pg.wait_for_timeout(1200)
    d=db(pg); log.append(('logout remove do aparelho', len(d.get('subs',[])), 'sub do navegador mantida', bool(pg.evaluate("localStorage.getItem('fakesub')"))))
    # dentista no mesmo aparelho: reinscreve sozinho
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email','lucas@x.com'); pg.fill('#dl-pass','abc12345'); clk(pg,'#dl-login button[type=submit]'); pg.wait_for_timeout(1500)
    d=db(pg); log.append(('dentista auto-inscrito', [x['user_id'] for x in d.get('subs',[])]))
    log.append(('dica inicio (ja ativo)', txt(pg,'#ci-alerts')[:60]))
    clk(pg,'#view-dent .side [data-ctab="perfil"]'); pg.wait_for_timeout(500)
    log.append(('card dentista', txt(pg,'#app-d')[:200]))
    # abrir pelo ícone do app
    pg.goto('http://localhost:8765/?app=1'); pg.wait_for_timeout(1500)
    log.append(('abre pelo app', pg.url, pg.is_visible('#view-dent')))
    # aparelho novo, sem permissão ainda (mobile)
    m=ctx_(b,{'width':390,'height':844},None).new_page(); m.on('pageerror',lambda e:errs.append(str(e)))
    m.goto('http://localhost:8765/#dentista'); m.wait_for_timeout(700)
    m.evaluate("(()=>{const d=JSON.parse(localStorage.getItem('mockdb'));d.push={pub:'"+db(pg)['push']['pub']+"',priv:'x',url:'https://abcdefghijkl.supabase.co/functions/v1/push'};localStorage.setItem('mockdb',JSON.stringify(d))})()")
    m.reload(); m.wait_for_timeout(700)
    m.fill('#dl-email','lucas@x.com'); m.fill('#dl-pass','abc12345'); clk(m,'#dl-login button[type=submit]'); m.wait_for_timeout(1500)
    log.append(('dica no inicio', txt(m,'#ci-alerts')[:110]))
    m.screenshot(path=O+'s_m_inicio.png')
    clk(m,'#ci-alerts [data-app="dispensar"]'); m.wait_for_timeout(300); log.append(('dica dispensada', 'Avisos no celular' not in txt(m,'#ci-alerts')))
    clk(m,'#view-dent .side [data-ctab="perfil"]'); m.wait_for_timeout(500)
    el=m.query_selector('#app-d'); el.scroll_into_view_if_needed(); el.screenshot(path=O+'s_m_card.png')
    log.append(('mobile largura', m.evaluate('document.documentElement.scrollWidth')))
    b.close()
for l in log: print(*l)
print('ERRS', errs)
