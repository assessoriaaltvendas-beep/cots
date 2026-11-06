# v11: segurança. Wi-Fi fora da configuração pública e limite de tentativas de login.
import json, os, sys
from playwright.sync_api import sync_playwright
AQUI = os.path.dirname(os.path.abspath(__file__))
mock = 'window.MOCK_TERMOS_OK=1;\n' + open(AQUI + '/mock-supabase.js', encoding='utf-8').read()
cfg = "window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'" + 'x' * 60 + "'};"
WIFI = 'Rede Consultorio / senha-de-teste'
seed = {'slots': [], 'bookings': [], 'cfg': {'valorHora': 50, 'espaco': {'wifi': WIFI, 'chegada': '10 min antes'}}, 'secret': 'k', 'sent': [], 'admins': ['adm1'],
  'adm': {'adm1': {'nivel': 'completo', 'nome': 'Dra. Thalia Santiago'}}, 'faq': [], 'app_config': [], 'avisos': [], 'problemas': [], 'espera': [],
  'dentists': [{'id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'whatsapp': '(31) 98841-5460', 'email': 'lucas@x.com', 'status': 'liberado', 'criado_em': '2026-09-01T10:00:00'},
               {'id': 'novo1', 'nome': 'Rafael Lima', 'cro': '', 'whatsapp': '(31) 96666-2222', 'email': 'rafa@x.com', 'status': 'pendente', 'criado_em': '2026-10-20T10:00:00'}],
  'pacientes': [], 'consultas': [],
  'users': [{'id': 'adm1', 'email': 't@x.com', 'password': 'senha12345'}, {'id': 'lucas1', 'email': 'lucas@x.com', 'password': 'abc12345'}, {'id': 'novo1', 'email': 'rafa@x.com', 'password': 'abc12345'}]}
init = "if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb'," + json.dumps(json.dumps(seed)) + ");"
errs = []
def chk(name, cond, extra=''):
    print(('OK  ' if cond else 'FALHA ') + name + ('' if cond else f'  -> {extra}'))
    if not cond: chk.fail += 1
chk.fail = 0
with sync_playwright() as p:
    b = p.chromium.launch(); c = b.new_context(viewport={'width': 1280, 'height': 900})
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.add_init_script(init); pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900)
    chk('visitante: senha do Wi-Fi fora da configuração pública', (pg.evaluate('CFG.espaco') or {}).get('wifi', '') != WIFI, pg.evaluate('CFG.espaco'))
    # limite de tentativas
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(800)
    chamadas = pg.evaluate("(()=>{window.__n=0;const f=SB.auth.signInWithPassword.bind(SB.auth);SB.auth.signInWithPassword=a=>{window.__n++;return f(a)};return true})()")
    for i in range(5):
        pg.fill('#dl-email', 'lucas@x.com'); pg.fill('#dl-pass', 'errada'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(500)
    chk('5 senhas erradas chegam ao servidor', pg.evaluate('window.__n') == 5, pg.evaluate('window.__n'))
    pg.fill('#dl-pass', 'abc12345'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(500)
    t = pg.inner_text('#dl-fb')
    chk('6ª tentativa bloqueada por 1 minuto sem chamar o servidor', 'Muitas tentativas' in t and '1 minuto' in t and pg.evaluate('window.__n') == 5, t)
    chk('bloqueado não entra mesmo com a senha certa', pg.is_hidden('#view-dent'))
    pg.evaluate("(()=>{const t=JSON.parse(localStorage.getItem('cots_login'));t.ate=Date.now()-1;localStorage.setItem('cots_login',JSON.stringify(t))})()")
    pg.fill('#dl-pass', 'errada'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(500)
    pg.fill('#dl-pass', 'abc12345'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(500)
    chk('depois de mais um erro a espera cresce para 2 minutos', '2 minutos' in pg.inner_text('#dl-fb'), pg.inner_text('#dl-fb'))
    pg.evaluate("(()=>{const t=JSON.parse(localStorage.getItem('cots_login'));t.ate=Date.now()-1;localStorage.setItem('cots_login',JSON.stringify(t))})()")
    pg.fill('#dl-pass', 'abc12345'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(1500)
    chk('passada a espera, a senha certa entra', pg.is_visible('#view-dent'))
    chk('acertar zera a contagem', pg.evaluate("localStorage.getItem('cots_login')") == '{}', pg.evaluate("localStorage.getItem('cots_login')"))
    # Wi-Fi para dentista liberado
    pg.evaluate("setCTab('consultorio')"); pg.wait_for_timeout(800)
    chk('dentista liberado vê o Wi-Fi', WIFI in pg.inner_text('#cc-rot'), pg.inner_text('#cc-rot'))
    pg.evaluate('dlogout()'); pg.wait_for_timeout(1000)
    chk('dentista pendente não recebe o Wi-Fi', pg.evaluate("(async()=>{await SB.auth.signInWithPassword({email:'rafa@x.com',password:'abc12345'});const r=await SB.rpc('wifi_consultorio');await SB.auth.signOut();return r.data})()") is None)
    chk('visitante não recebe o Wi-Fi', pg.evaluate("(async()=>{const r=await SB.rpc('wifi_consultorio');return r.data})()") is None)
    # administração continua vendo e salvando o Wi-Fi
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(800)
    pg.fill('#dl-email', 't@x.com'); pg.fill('#dl-pass', 'senha12345'); pg.evaluate("document.querySelector('#dl-login button[type=submit]').click()"); pg.wait_for_timeout(1500)
    pg.evaluate("setTab('ajustes')"); pg.wait_for_timeout(700); pg.evaluate("ajAbrir('regras')"); pg.wait_for_timeout(500)
    chk('Ajustes mostra o Wi-Fi salvo (não apaga ao salvar)', pg.input_value('#rf-wifi') == WIFI, pg.input_value('#rf-wifi'))
    b.close()
print('erros JS:', errs[:5]); print('FALHAS:', chk.fail)
