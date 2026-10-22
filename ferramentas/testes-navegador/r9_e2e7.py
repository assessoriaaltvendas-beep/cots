import json, datetime as dt, sys
from playwright.sync_api import sync_playwright
S = '/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad'
O = S + '/app/s7/'
import os; os.makedirs(O, exist_ok=True)
mock = open(S + '/app/mock9.js').read()
cfg = "window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'" + 'x' * 60 + "'};"
TERMOS = open(S + '/app/v7.sql').read().split('$TERMOS$')[1]
t = dt.date.today()
def d(off):
    x = t + dt.timedelta(days=off)
    while x.weekday() == 6: x += dt.timedelta(days=1)
    return x.isoformat()
seed = {'slots': [], 'bookings': [], 'cfg': {'pix': '+5531995745413', 'pixNome': 'Thalia Santiago', 'pixCidade': 'Ipatinga'}, 'secret': 'k', 'sent': [],
  'dentists': [{'id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'whatsapp': '(31) 98841-5460', 'email': 'lucas@x.com', 'status': 'liberado', 'criado_em': '2026-09-01T10:00:00'}],
  'avisos': [], 'problemas': [], 'espera': [], 'admins': ['adm1'], 'faq': [], 'app_config': [], 'termos_versoes': [], 'termos_aceites': [], 'planos': [],
  'users': [{'id': 'adm1', 'email': 't@x.com', 'password': 'senha12345'}, {'id': 'lucas1', 'email': 'lucas@x.com', 'password': 'abc12345'}]}
init = "window.TERMOS_MOCK=" + json.dumps(TERMOS) + ";if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb'," + json.dumps(json.dumps(seed)) + ");"
errs = []
def ctx_(b, w=390, h=844):
    c = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
    c.add_init_script(init); return c
def page(c):
    pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'favicon' not in m.text else None); return pg
def clk(pg, sel, i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def chk(name, cond):
    print(('OK  ' if cond else 'FALHA ') + name)
    if not cond: chk.fail += 1
chk.fail = 0
def scroll_bottom(pg, sel): pg.evaluate(f"(()=>{{const b=document.querySelector('{sel}'); b.scrollTop=b.scrollHeight; b.dispatchEvent(new Event('scroll'));}})()"); pg.wait_for_timeout(200)
def mockdb(pg): return pg.evaluate("JSON.parse(localStorage.getItem('mockdb'))")
with sync_playwright() as p:
    b = p.chromium.launch(); c = ctx_(b); pg = page(c)
    # 1) público: rodapé com termos
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(900)
    clk(pg, '.site-foot [data-termos]'); pg.wait_for_timeout(400)
    chk('janela de termos abre', pg.is_visible('#tm') and 'Câmeras de segurança' in pg.inner_text('#tm-body'))
    chk('versão no rodapé da janela', 'Versão 1' in pg.inner_text('#tm-info'))
    pg.screenshot(path=O + 'termos_modal.png'); clk(pg, '#tm-x'); pg.wait_for_timeout(200)
    chk('janela fecha', not pg.is_visible('#tm'))
    # 2) cadastro com rolagem obrigatória
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(600); clk(pg, '#dl-seg [data-dl="reg"]'); pg.wait_for_timeout(500)
    pg.fill('#dr-nome', 'Ana Ribeiro'); pg.fill('#dr-tel', '(31) 91111-2222'); pg.fill('#dr-email', 'ana@exemplo.com'); pg.fill('#dr-pass', 'abc12345'); pg.fill('#dr-pass2', 'abc12345')
    chk('aceite travado antes de rolar', pg.is_disabled('#dr-accept') and pg.is_disabled('#dr-submit'))
    pg.evaluate("document.querySelector('#dr-termos').scrollIntoView({block:'center'})"); pg.screenshot(path=O + 'reg_termos.png')
    scroll_bottom(pg, '#dr-termos')
    chk('aceite liberado depois de rolar', not pg.is_disabled('#dr-accept'))
    chk('botão ainda travado sem marcar', pg.is_disabled('#dr-submit'))
    pg.check('#dr-accept'); pg.wait_for_timeout(100)
    chk('botão liberado ao marcar', not pg.is_disabled('#dr-submit'))
    pg.evaluate("document.querySelector('#dr-accept').scrollIntoView({block:'center'})"); pg.screenshot(path=O + 'reg_aceite.png')
    clk(pg, '#dr-submit'); pg.wait_for_timeout(1400)
    db = mockdb(pg); ana = [x for x in db['dentists'] if x['nome'] == 'Ana Ribeiro']
    chk('conta criada com termos v1', ana and ana[0].get('termos_versao') == 1 and any(a['dentist_id'] == ana[0]['id'] for a in db['termos_aceites']))
    chk('tela de liberação', 'Falta só a liberação' in pg.inner_text('#c-wait'))
    clk(pg, '#c-wait [data-dlogout]'); pg.wait_for_timeout(900)
    # 3) dentista antigo: aceite obrigatório no login
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(600)
    pg.fill('#dl-email', 'lucas@x.com'); pg.fill('#dl-pass', 'abc12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1400)
    chk('tela de termos no login', pg.is_visible('#tg-box') and pg.is_disabled('#tg-ok') and pg.is_disabled('#tg-go'))
    pg.screenshot(path=O + 'gate.png')
    scroll_bottom(pg, '#tg-box'); pg.check('#tg-ok'); pg.wait_for_timeout(100)
    chk('aceitar liberado', not pg.is_disabled('#tg-go'))
    clk(pg, '#tg-go'); pg.wait_for_timeout(1200)
    chk('área aberta depois do aceite', pg.is_hidden('#c-wait') and pg.is_visible('#c-inicio'))
    # 4) pedir plano
    clk(pg, '#view-dent .side [data-ctab="nova"]'); pg.wait_for_timeout(600)
    chk('card de plano na aba reservar', pg.is_visible('#cn-plano') and 'Plano mensal' in pg.inner_text('#cn-plano'))
    pg.evaluate("document.querySelector('#cn-plano .pl-form').open=true"); pg.wait_for_timeout(300)
    pg.select_option('#cn-plano [data-plf="dia"]', '5'); pg.wait_for_timeout(300)
    txt = pg.inner_text('#cn-plano')
    txt = txt.replace('\xa0', ' '); chk('preço e economia', 'R$ 1.000,00 por mês' in txt and 'economia de R$ 400,00' in txt)
    pg.evaluate("document.querySelector('#cn-plano').scrollIntoView({block:'start'}); window.scrollBy(0,-70)"); pg.wait_for_timeout(200); pg.screenshot(path=O + 'plano_form.png')
    clk(pg, '#cn-plano [data-plgo]'); pg.wait_for_timeout(900)
    db = mockdb(pg)
    chk('pedido de plano gravado', len(db['planos']) == 1 and db['planos'][0]['status'] == 'pendente' and db['planos'][0]['dia_semana'] == 5)
    chk('mensagem e lista', 'AGUARDANDO APROVAÇÃO' in pg.inner_text('#cn-plano').upper() and 'Pedido enviado' in pg.inner_text('#cn-plano'))
    pg.screenshot(path=O + 'plano_pedido.png')
    clk(pg, '#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(300)
    chk('regra de 4 horas', '4 horas antes' in pg.inner_text('#cr-rule'))
    # 5) painel: aprovar plano, termos, valores, novo plano
    pg.evaluate("dlogout()"); pg.wait_for_timeout(800)
    pg.set_viewport_size({'width': 1280, 'height': 900})
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(700)
    pg.fill('#dl-email', 't@x.com'); pg.fill('#dl-pass', 'senha12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1500)
    clk(pg, '#view-admin .side [data-tab="resumo"]'); pg.wait_for_timeout(500)
    chk('pedido de plano no resumo', 'pedido de plano mensal' in pg.inner_text('#r-app'))
    pg.screenshot(path=O + 'adm_resumo.png')
    clk(pg, '#r-app [data-plact$="|aprovar"]'); pg.wait_for_timeout(1000)
    db = mockdb(pg); pb = [x for x in db['bookings'] if x.get('plano_id')]
    chk('plano aprovado e reservas criadas', db['planos'][0]['status'] == 'ativo' and len(pb) >= 4)
    print('   reservas do plano:', [(x['date'], x['valor']) for x in sorted(pb, key=lambda x: x['date'])])
    clk(pg, '#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(600)
    chk('card de planos ativos', 'Lucas Andrade' in pg.inner_text('#d-planos') and 'Diária' in pg.inner_text('#d-planos'))
    chk('tag Plano na tabela', 'PLANO' in pg.inner_text('#d-body').upper())
    pg.screenshot(path=O + 'adm_dentistas.png')
    clk(pg, '#d-body tr[data-dent="lucas1"]'); pg.wait_for_timeout(500)
    dtx = pg.inner_text('#dr-body')
    chk('detalhe do dentista: plano e termos', 'Plano mensal' in dtx and 'Versão 1' in dtx)
    pg.screenshot(path=O + 'adm_dent_drawer.png'); clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    # novo plano pelo painel
    clk(pg, '#d-planos [data-pl="novo"]'); pg.wait_for_timeout(500)
    pg.select_option('#pa-d', 'lucas1'); pg.select_option('#pa-op', '2'); pg.select_option('#pa-dia', '2'); pg.wait_for_timeout(300)
    pg.screenshot(path=O + 'adm_novo_plano.png')
    clk(pg, '#pa-go'); pg.wait_for_timeout(900)
    db = mockdb(pg)
    chk('novo plano tarde de terça ativo', any(x['dia_semana'] == 2 and x['status'] == 'ativo' and x['h_from'] == 13 for x in db['planos']))
    chk('mensagem do novo plano', 'Plano ativado' in pg.inner_text('#pa-fb'))
    clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    # termos: nova versão
    clk(pg, '#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(800)
    pg.evaluate("document.querySelector('[data-acc=termos]').open=true"); pg.wait_for_timeout(300)
    chk('termos no ajustes', 'Versão 1' in pg.inner_text('#acc-termos'))
    pg.evaluate("(()=>{const t=document.querySelector('#tf-txt'); t.value=t.value.replace('4 (quatro) horas','6 (seis) horas').replace('9. Aceitação dos termos','9. Aceitação dos termos e do plano mensal');})()")
    pg.fill('#tf-res', 'Prazo de cancelamento passou para 6 horas')
    clk(pg, '#tf button[type=submit]'); pg.wait_for_timeout(1200)
    db = mockdb(pg)
    chk('versão 2 publicada', len(db['termos_versoes']) == 2)
    pg.evaluate("document.querySelector('[data-acc=termos]').open=true"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('details.tv[data-tv=\"2\"]').open=true"); pg.wait_for_timeout(400)
    h2 = pg.inner_html('details.tv[data-tv="2"]')
    chk('histórico mostra o que mudou', '<ins>' in h2 and '<del>' in h2 and '6' in h2)
    pg.evaluate("document.querySelector('details.tv[data-tv=\"2\"]').scrollIntoView({block:'start'})"); pg.wait_for_timeout(200)
    pg.screenshot(path=O + 'adm_termos.png')
    # valores dos planos
    pg.evaluate("document.querySelector('[data-acc=planos]').open=true"); pg.wait_for_timeout(300)
    pg.fill('#plf-d', '1100'); clk(pg, '#plf button[type=submit]'); pg.wait_for_timeout(900)
    db = mockdb(pg)
    chk('valores dos planos salvos', db['cfg']['planos']['diaria'] == 1100)
    pg.evaluate("document.querySelector('[data-acc=planos]').scrollIntoView({block:'start'})"); pg.screenshot(path=O + 'adm_planos_cfg.png')
    pg.evaluate("logout()"); pg.wait_for_timeout(1500)
    # 6) dentista: aceita de novo vendo o que mudou; usa crédito
    pg.set_viewport_size({'width': 390, 'height': 844})
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(700)
    pg.fill('#dl-email', 'lucas@x.com'); pg.fill('#dl-pass', 'abc12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1400)
    gh = pg.inner_html('#c-wait')
    chk('novo aceite com mudanças destacadas', 'atualizados' in gh and '<ins>' in gh and 'Prazo de cancelamento passou' in gh)
    pg.evaluate("(()=>{const m=document.querySelector('#tg-box ins'); m.scrollIntoView({block:'center'});})()"); pg.wait_for_timeout(200)
    pg.screenshot(path=O + 'gate_v2.png')
    scroll_bottom(pg, '#tg-box'); pg.check('#tg-ok'); clk(pg, '#tg-go'); pg.wait_for_timeout(1200)
    chk('aceite v2 gravado', mockdb(pg)['dentists'][0].get('termos_versao') == 2)
    db = mockdb(pg); fut = sorted([x for x in db['bookings'] if x.get('plano_id') and x['h_from'] == 8 and x['status'] == 'ativo'], key=lambda x: x['date'])
    alvo = fut[1]
    clk(pg, '#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(400)
    chk('reserva do plano na lista', 'plano mensal' in pg.inner_text('#cr-list'))
    pg.evaluate(f"document.querySelector('#cr-list [data-cbk=\"{alvo['id']}\"]').click()"); pg.wait_for_timeout(600)
    dr = pg.inner_text('#c-drawer')
    chk('sem botão cancelar normal no plano', 'Confirmar cancelamento' not in dr and 'Remarcar' not in dr.split('Ações')[-1].split('Não vou')[0])
    pg.evaluate("document.querySelector('#c-drawer [data-libdia]').scrollIntoView({block:'center'})"); pg.screenshot(path=O + 'plano_drawer.png')
    clk(pg, '#c-drawer [data-libdia]'); pg.wait_for_timeout(200); clk(pg, '#c-drawer [data-libdia]'); pg.wait_for_timeout(1200)
    db = mockdb(pg); bb = [x for x in db['bookings'] if x['id'] == alvo['id']][0]
    chk('dia virou crédito', bb['status'] == 'credito')
    chk('seletor do crédito aparece', pg.query_selector('#cd-cred') is not None)
    pg.evaluate("document.querySelector('#cd-cred').scrollIntoView({block:'center'})"); pg.screenshot(path=O + 'credito.png')
    nova = pg.eval_on_selector('#cd-cred', 'e=>e.value')
    clk(pg, '#c-drawer [data-usacred]'); pg.wait_for_timeout(1200)
    db = mockdb(pg); bb = [x for x in db['bookings'] if x['id'] == alvo['id']][0]
    chk('crédito usado', bb['status'] == 'ativo' and bb['date'] == nova.split('|')[0])
    clk(pg, '#c-dr-close') if pg.query_selector('#c-dr-close') else None
    pg.wait_for_timeout(300)
    clk(pg, '#view-dent .side [data-ctab="inicio"]'); pg.wait_for_timeout(500); pg.screenshot(path=O + 'inicio.png')
    clk(pg, '#view-dent .side [data-ctab="perfil"]'); pg.wait_for_timeout(500)
    chk('perfil mostra versão aceita', 'Versão 2' in pg.inner_text('#cp-docs'))
    clk(pg, '#c-perfil [data-termos]'); pg.wait_for_timeout(500)
    chk('perfil abre termos', pg.is_visible('#tm') and 'Você aceitou a versão 2' in pg.inner_text('#tm-info'))
    c.close(); b.close()
print('erros JS:', [e for e in errs if 'ERR_FAILED' not in e][:8])
print('FALHAS:', chk.fail)
