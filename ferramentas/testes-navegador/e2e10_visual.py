# v10: efeitos, avisos, Desfazer, login e temas (com animações ligadas: navigator.webdriver desativado).
import json, datetime as dt, re, os, sys
from playwright.sync_api import sync_playwright
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../..')
S = os.environ.get('COTS_SAIDA', '/tmp/cots-testes')
O = S + '/app/s10v/'; os.makedirs(O, exist_ok=True)
mock = 'window.MOCK_TERMOS_OK=1;\n' + open(AQUI + '/mock-supabase.js').read()
cfg = "window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'" + 'x' * 60 + "'};"
t = dt.date.today()
def d(off):
    x = t + dt.timedelta(days=off)
    while x.weekday() == 6: x += dt.timedelta(days=1)
    return x.isoformat()
bk = [{'id': 'f1', 'dentist_id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'tel': '(31) 98841-5460', 'primeira': False, 'date': d(5), 'h_from': 9, 'h_to': 11, 'status': 'ativo', 'origem': 'area-dentista', 'pago': False, 'valor': 100, 'criado_em': '2026-10-01T10:00:00'},
      {'id': 'f2', 'dentist_id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'tel': '(31) 98841-5460', 'primeira': False, 'date': d(6), 'h_from': 14, 'h_to': 16, 'status': 'ativo', 'origem': 'area-dentista', 'pago': True, 'valor': 100, 'criado_em': '2026-10-01T10:00:00'},
      {'id': 'f3', 'dentist_id': 'mari1', 'nome': 'Mariana Costa', 'cro': 'CRO-MG 50.000', 'tel': '(31) 97777-1111', 'primeira': False, 'date': d(2), 'h_from': 8, 'h_to': 13, 'status': 'ativo', 'origem': 'area-dentista', 'pago': False, 'valor': 180, 'criado_em': '2026-10-01T10:00:00'}]
slots = [{'date': b['date'], 'hour': h, 'booking_id': b['id']} for b in bk for h in range(b['h_from'], b['h_to'])]
seed = {'slots': slots, 'bookings': bk, 'cfg': {'valorHora': 50}, 'secret': 'k', 'sent': [], 'admins': ['adm1'], 'adm': {'adm1': {'nivel': 'completo', 'nome': 'Dra. Thalia Santiago'}},
  'faq': [{'id': 'q1', 'pergunta': 'Posso levar meu material?', 'resposta': 'Sim.', 'ordem': 1, 'criadoEm': '2026-10-01'}], 'app_config': [], 'avisos': [], 'problemas': [], 'espera': [],
  'dentists': [{'id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'whatsapp': '(31) 98841-5460', 'email': 'lucas@x.com', 'status': 'liberado', 'criado_em': '2026-09-01T10:00:00'},
               {'id': 'mari1', 'nome': 'Mariana Costa', 'cro': 'CRO-MG 50.000', 'whatsapp': '(31) 97777-1111', 'email': 'mari@x.com', 'status': 'liberado', 'criado_em': '2026-09-01T10:00:00'}],
  'pacientes': [], 'consultas': [],
  'users': [{'id': 'adm1', 'email': 't@x.com', 'password': 'senha12345'}, {'id': 'lucas1', 'email': 'lucas@x.com', 'password': 'abc12345'}, {'id': 'mari1', 'email': 'mari@x.com', 'password': 'abc12345'}]}
init = "window.UNDO_MS=1500;if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb'," + json.dumps(json.dumps(seed)) + ");"
errs = []
def chk(name, cond, extra=''):
    print(('OK  ' if cond else 'FALHA ') + name + ('' if cond else f'  -> {extra}'))
    if not cond: chk.fail += 1
chk.fail = 0
def clk(pg, sel, i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def mockdb(pg): return pg.evaluate("JSON.parse(localStorage.getItem('mockdb'))")
def txt(pg, sel): return re.sub(r'\s+', ' ', pg.inner_text(sel)).strip()
def login(pg, email, pw, hash='#dentista'):
    pg.goto('http://localhost:8765/' + hash); pg.wait_for_timeout(800)
    pg.fill('#dl-email', email); pg.fill('#dl-pass', pw); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1600)
def sair(pg):
    if not pg.is_hidden('#view-admin'): pg.evaluate('logout()')
    else: pg.evaluate('dlogout()')
    pg.wait_for_timeout(1200)
def semRolagem(pg, w, nome): chk(f'{nome}: sem rolagem lateral', pg.evaluate('document.documentElement.scrollWidth') <= w + 1, pg.evaluate('document.documentElement.scrollWidth'))
with sync_playwright() as p:
    b = p.chromium.launch(args=['--disable-blink-features=AutomationControlled'])
    def ctx(w, h, mob=False):
        c = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, is_mobile=mob, has_touch=mob)
        c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
        c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
        c.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
        c.add_init_script(init); return c
    c = ctx(1280, 900); pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900)
    chk('animações ligadas neste teste', pg.evaluate('MOV') is True)
    chk('site: seções com revelação ao rolar', pg.evaluate("document.querySelectorAll('#site .rv').length") > 3)
    pg.evaluate("window.scrollTo(0, 1600)"); pg.wait_for_timeout(900)
    chk('site: topo com sombra ao rolar', pg.evaluate("document.body.classList.contains('rolou') && getComputedStyle(document.querySelector('.top')).boxShadow !== 'none'"))
    chk('site: seções reveladas', pg.evaluate("document.querySelectorAll('#site .rv.rv-in').length") > 0)
    pg.screenshot(path=O + 'site_rolado.png')
    # login: erros, foco e e-mail lembrado
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(800)
    chk('login: cartão com animação de entrada', pg.evaluate("getComputedStyle(document.getElementById('view-dlogin')).animationName") == 'v10card')
    pg.fill('#dl-email', ''); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(150)
    chk('login vazio: campos em vermelho', pg.evaluate("[...document.querySelectorAll('#dl-login input.inv')].map(i=>i.id)") == ['dl-email', 'dl-pass'])
    chk('login vazio: mensagem balança', pg.evaluate("!!document.querySelector('#dl-fb .msg.shake')"))
    pg.wait_for_timeout(500)
    pg.fill('#dl-email', 'lucas@x.com'); chk('digitar tira o vermelho', pg.evaluate("!document.getElementById('dl-email').classList.contains('inv')"))
    pg.fill('#dl-pass', 'errada'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(700)
    chk('senha errada: e-mail e senha marcados', set(pg.evaluate("[...document.querySelectorAll('#dl-login input.inv')].map(i=>i.id)")) == {'dl-email', 'dl-pass'}, txt(pg, '#dl-fb'))
    clk(pg, '#dl-seg [data-dl="reg"]'); pg.wait_for_timeout(120)
    chk('troca animada para Criar conta', pg.evaluate("getComputedStyle(document.getElementById('dl-reg')).animationName") == 'v10form')
    clk(pg, '#dl-seg [data-dl="login"]'); pg.wait_for_timeout(300)
    pg.focus('#dl-email'); chk('foco destacado no campo', pg.evaluate("getComputedStyle(document.getElementById('dl-email')).boxShadow") != 'none')
    pg.fill('#dl-pass', 'abc12345')
    chk('enviar: botão carregando', pg.evaluate("(()=>{document.getElementById('dl-login').requestSubmit();return document.querySelector('#dl-login button[type=submit]').classList.contains('is-loading')})()"))
    pg.wait_for_timeout(250)
    chk('check animado de sucesso', pg.evaluate("!!document.querySelector('.check-ok')"))
    pg.wait_for_timeout(1500)
    chk('entrou na área do dentista', pg.is_visible('#view-dent'))
    chk('botão volta ao normal', pg.evaluate("!document.querySelector('.is-loading')"))
    sair(pg); pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(800)
    chk('lembra o último e-mail', pg.input_value('#dl-email') == 'lucas@x.com', pg.input_value('#dl-email'))
    # Desfazer cancelamento (dentista)
    pg.fill('#dl-pass', 'abc12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1600)
    clk(pg, '#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(700)
    pg.evaluate("document.querySelector('[data-cbk=\"f1\"]').click()"); pg.wait_for_timeout(600)
    cb = "[...document.querySelectorAll('#c-drawer button.danger')].find(b=>/ancela/.test(b.textContent))"
    pg.evaluate(f"{cb}.click()"); pg.wait_for_timeout(150); pg.evaluate(f"{cb}.click()"); pg.wait_for_timeout(300)
    chk('aviso com Desfazer', 'Desfazer' in txt(pg, '#toasts') and 'Reserva cancelada' in txt(pg, '#toasts'), pg.evaluate("document.getElementById('toasts')?.innerText"))
    pg.screenshot(path=O + 'desfazer.png')
    clk(pg, '#toasts .toast-undo'); pg.wait_for_timeout(2000)
    chk('Desfazer mantém a reserva', [x for x in mockdb(pg)['bookings'] if x['id'] == 'f1'][0]['status'] == 'ativo')
    pg.evaluate(f"{cb}.click()"); pg.wait_for_timeout(150); pg.evaluate(f"{cb}.click()"); pg.wait_for_timeout(2200)
    chk('sem Desfazer, cancela depois do prazo', [x for x in mockdb(pg)['bookings'] if x['id'] == 'f1'][0]['status'] == 'cancelado')
    # sem internet
    c.set_offline(True); pg.wait_for_timeout(300)
    chk('faixa de sem internet', pg.is_visible('#offline'))
    c.set_offline(False); pg.wait_for_timeout(400)
    chk('faixa some e avisa', pg.is_hidden('#offline') and 'Conexão restabelecida' in pg.evaluate("document.getElementById('toasts').innerText"))
    sair(pg)
    # painel: KPIs contando, abas, gaveta, temas
    login(pg, 't@x.com', 'senha12345', '#admin')
    clk(pg, '#view-admin .side [data-tab="agenda"]'); pg.wait_for_timeout(400)
    clk(pg, '#view-admin .side [data-tab="resumo"]')
    chk('troca de aba com transição', pg.evaluate("document.getElementById('t-resumo').classList.contains('tab-enter')"))
    pg.wait_for_timeout(1200)
    chk('números do Resumo no valor final', pg.evaluate("[...document.querySelectorAll('#t-resumo .kpi b')].every(b=>!b.dataset.contando)"))
    for tema in ('claro', 'escuro'):
        pg.evaluate(f"setTema('{tema}','painel')"); pg.wait_for_timeout(300)
        pg.screenshot(path=O + f'admin_resumo_{tema}.png', full_page=True); semRolagem(pg, 1280, f'painel {tema} computador')
        clk(pg, '#view-admin .side [data-tab="agenda"]'); pg.wait_for_timeout(500)
        pg.screenshot(path=O + f'admin_agenda_{tema}.png')
        clk(pg, '#view-admin .side [data-tab="resumo"]'); pg.wait_for_timeout(300)
    chk('tema escuro aplicado', pg.evaluate("document.body.classList.contains('tema-escuro')"))
    pg.evaluate("setTema('claro','painel')")
    clk(pg, '#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#t-dentistas [data-dent]').click()"); pg.wait_for_timeout(100)
    chk('gaveta desliza', pg.evaluate("getComputedStyle(document.getElementById('drawer')).animationName") == 'v10slide')
    pg.wait_for_timeout(500); pg.screenshot(path=O + 'gaveta.png'); clk(pg, '#dr-close')
    c.close()
    # celular 390 px: claro e escuro, botão voltar ao topo
    c = ctx(390, 844, True); pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900); semRolagem(pg, 390, 'site celular')
    pg.evaluate("window.scrollTo(0, 2000)"); pg.wait_for_timeout(500)
    chk('celular: botão voltar ao topo', pg.is_visible('#to-top'))
    clk(pg, '#to-top'); pg.wait_for_timeout(1200)
    chk('voltou ao topo', pg.evaluate('window.scrollY') < 5, pg.evaluate('window.scrollY'))
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(800); pg.screenshot(path=O + 'm_login.png'); semRolagem(pg, 390, 'login celular')
    login(pg, 't@x.com', 'senha12345', '#admin')
    for tema in ('claro', 'escuro'):
        pg.evaluate(f"setTema('{tema}','painel')"); pg.wait_for_timeout(300)
        for tab in ('resumo', 'agenda', 'dentistas', 'ajustes'):
            pg.evaluate(f"setTab('{tab}')"); pg.wait_for_timeout(700)
            semRolagem(pg, 390, f'painel celular {tema} {tab}')
        pg.evaluate("setTab('resumo')"); pg.wait_for_timeout(900); pg.screenshot(path=O + f'm_admin_{tema}.png', full_page=True)
    pg.evaluate("setTema('claro','painel')")
    sair(pg); login(pg, 'mari@x.com', 'abc12345')
    for tema in ('claro', 'escuro'):
        pg.evaluate(f"setTema('{tema}','dentista')"); pg.wait_for_timeout(300)
        for tab in ('inicio', 'reservas', 'nova', 'financeiro', 'consultorio', 'perfil'):
            pg.evaluate(f"setCTab('{tab}')"); pg.wait_for_timeout(600)
            semRolagem(pg, 390, f'dentista celular {tema} {tab}')
        pg.evaluate("setCTab('inicio')"); pg.wait_for_timeout(900); pg.screenshot(path=O + f'm_dent_{tema}.png', full_page=True)
    pg.evaluate("toast('Teste de aviso')"); pg.wait_for_timeout(300); pg.screenshot(path=O + 'm_toast.png')
    # puxar para atualizar (simulando o app instalado) e vibração ao reservar
    pg.evaluate("window.scrollTo(0,0); APP.standalone = () => true; window.__vib = []; navigator.vibrate = x => { window.__vib.push(x); return true; }; S.__loads = 0; const L = S.store.loadAll; S.store.loadAll = (...a) => { S.__loads++; return L.apply(S.store, a); }")
    pg.evaluate("""(()=>{const T=y=>new Touch({identifier:1,target:document.body,clientX:200,clientY:y});
      window.dispatchEvent(new TouchEvent('touchstart',{touches:[T(100)]}));
      window.dispatchEvent(new TouchEvent('touchmove',{touches:[T(300)]}));
      window.dispatchEvent(new TouchEvent('touchend',{touches:[]}));})()""")
    pg.wait_for_timeout(800)
    chk('puxar para atualizar recarrega os dados', pg.evaluate('S.__loads') >= 1 and 'Atualizado' in pg.evaluate("document.getElementById('toasts').innerText"))
    pg.evaluate("sucessoReserva()"); chk('vibra ao confirmar reserva', pg.evaluate('window.__vib') == [35])
    c.close(); b.close()
print('erros JS:', errs[:6]); print('FALHAS:', chk.fail)
