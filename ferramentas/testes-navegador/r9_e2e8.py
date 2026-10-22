import json, datetime as dt, zipfile, io, re
from playwright.sync_api import sync_playwright
S = '/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad'
O = S + '/app/s8/'
import os; os.makedirs(O, exist_ok=True)
mock = open(S + '/app/mock9r.js').read()
cfg = "window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'" + 'x' * 60 + "'};"
t = dt.date.today()
def d(off):
    x = t + dt.timedelta(days=off)
    while x.weekday() == 6: x += dt.timedelta(days=1)
    return x.isoformat()
anos = lambda off, y: (t + dt.timedelta(days=off)).replace(year=(t + dt.timedelta(days=off)).year - y).isoformat()
bk = [{'id': 'f1', 'dentist_id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'tel': '(31) 98841-5460', 'primeira': False, 'date': d(5), 'h_from': 9, 'h_to': 11, 'status': 'ativo', 'origem': 'area-dentista', 'pago': False, 'valor': 100, 'criado_em': '2026-10-01T10:00:00'},
      {'id': 'p1', 'dentist_id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'tel': '(31) 98841-5460', 'primeira': False, 'date': d(-2), 'h_from': 14, 'h_to': 16, 'status': 'ativo', 'origem': 'area-dentista', 'pago': False, 'valor': 100, 'criado_em': '2026-10-01T10:00:00'}]
for i in range(1, 9):
    bk.append({'id': f'h{i}', 'dentist_id': 'lucas1', 'nome': 'Lucas Andrade', 'tel': '(31) 98841-5460', 'primeira': False, 'date': d(-7 * i), 'h_from': 8, 'h_to': 13, 'status': 'ativo', 'origem': 'area-dentista', 'pago': True, 'valor': 180, 'criado_em': '2026-09-01T10:00:00'})
slots = [{'date': b['date'], 'hour': h, 'booking_id': b['id']} for b in bk if b['date'] >= t.isoformat() for h in range(b['h_from'], b['h_to'])]
seed = {'slots': slots, 'bookings': bk, 'cfg': {'pix': '+5531995745413', 'pixNome': 'Thalia Santiago', 'pixCidade': 'Ipatinga', 'valorHora': 50,
  'espaco': {'equipamentos': ['Cadeira odontológica com refletor de LED', 'Autoclave', 'Ultrassom e jato de bicarbonato', 'Fotopolimerizador', 'Raio X'], 'inclusos': ['Esterilização dos instrumentais', 'Luvas, gorros e máscaras', 'Wi-Fi e ar-condicionado'], 'levar': [], 'chegada': '', 'saida': '', 'wifi': ''}},
  'secret': 'k', 'sent': [], 'admins': ['adm1'], 'faq': [], 'app_config': [], 'avisos': [], 'problemas': [], 'espera': [],
  'dentists': [{'id': 'lucas1', 'nome': 'Lucas Andrade', 'cro': 'CRO-MG 41.122', 'whatsapp': '(31) 98841-5460', 'email': 'lucas@x.com', 'status': 'liberado', 'criado_em': '2026-09-01T10:00:00'}],
  'pacientes': [{'id': 'pa1', 'nome': 'Joana Silva', 'telefone': '(31) 98888-7777', 'cpf': '123.456.789-00', 'nascimento': anos(0, 34), 'criado_em': '2026-10-01T10:00:00'},
                {'id': 'pa2', 'nome': 'Pedro Rocha', 'telefone': '(31) 97777-6666', 'nascimento': anos(3, 41), 'criado_em': '2026-10-01T10:00:00'}],
  'consultas': [{'id': 'c1', 'paciente_id': 'pa1', 'data': t.isoformat(), 'inicio': '23:20', 'fim': '23:50', 'status': 'agendada', 'criado_em': '2026-10-01T10:00:00'},
                {'id': 'c2', 'paciente_id': 'pa2', 'data': d(1), 'inicio': '10:00', 'fim': '10:45', 'status': 'agendada', 'criado_em': '2026-10-01T10:00:00'}],
  'users': [{'id': 'adm1', 'email': 't@x.com', 'password': 'senha12345'}, {'id': 'lucas1', 'email': 'lucas@x.com', 'password': 'abc12345'}]}
init = "if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb'," + json.dumps(json.dumps(seed)) + ");"
errs = []
def chk(name, cond):
    print(('OK  ' if cond else 'FALHA ') + name)
    if not cond: chk.fail += 1
chk.fail = 0
def clk(pg, sel, i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def mockdb(pg): return pg.evaluate("JSON.parse(localStorage.getItem('mockdb'))")
def baixa(pg, fn):
    with pg.expect_download() as di: fn()
    dl = di.value; path = O + dl.suggested_filename; dl.save_as(path); return path, open(path, 'rb').read()
with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=1, accept_downloads=True)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html></html>', content_type='text/html'))
    c.add_init_script(init)
    pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    # página inicial
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(1000)
    est = pg.inner_text('#estrutura') if pg.is_visible('#estrutura') else ''
    chk('seção estrutura e valores', 'Autoclave' in est and 'Plano mensal' in est.title() or 'PLANO MENSAL' in est.upper())
    pg.evaluate("document.querySelector('#estrutura').scrollIntoView()"); pg.wait_for_timeout(300); pg.screenshot(path=O + 'home_estrutura.png')
    # painel
    pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(600)
    pg.fill('#dl-email', 't@x.com'); pg.fill('#dl-pass', 'senha12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1500)
    clk(pg, '#view-admin .side [data-tab="resumo"]'); pg.wait_for_timeout(500)
    rp = pg.inner_html('#r-pac')
    chk('resumo: aniversariante e lembrete', 'Joana Silva' in rp and 'faz 34 anos' in rp and 'wa.me' in rp)
    chk('resumo: aviso de backup', 'Backup do consultório' in pg.inner_text('#r-app'))
    pg.screenshot(path=O + 'resumo.png')
    clk(pg, '#view-admin .side [data-tab="pacientes"]'); pg.wait_for_timeout(500)
    lw = pg.get_attribute('#p-hoje .wa-ic', 'href') or ''
    chk('lembrete no WhatsApp na lista de hoje', 'wa.me/5531988887777' in lw and 'lembrar' in lw.replace('%20', ' '))
    chk('card de aniversariantes', not pg.is_hidden('#p-aniv') and 'Pedro Rocha' in pg.inner_text('#p-aniv'))
    pg.screenshot(path=O + 'pacientes.png')
    clk(pg, '#p-hoje [data-pac="pa1"]'); pg.wait_for_timeout(600)
    chk('ficha com financeiro e botões', pg.is_visible('#pf-fin') and pg.query_selector('[data-doc8="receita"]') is not None)
    # orçamento aprovado em 3x
    clk(pg, '#pf-fin [data-fin8="orc"]'); pg.wait_for_timeout(400)
    pg.fill('#of-desc', 'Tratamento de canal no dente 36'); pg.fill('#of-val', '900'); pg.select_option('#of-parc', '3'); pg.select_option('#of-st', 'aprovado')
    clk(pg, '#dr-body form [type=submit]'); pg.wait_for_timeout(700)
    db = mockdb(pg); chk('orçamento gravado', len(db['pac_orcamentos']) == 1 and db['pac_orcamentos'][0]['parcelas'] == 3)
    clk(pg, '#pf-fin [data-fin8^="pag|"]'); pg.wait_for_timeout(400)
    chk('pagamento sugere a parcela', pg.input_value('#gf-val') == '300.00')
    clk(pg, '#dr-body form [type=submit]'); pg.wait_for_timeout(700)
    ft = pg.inner_text('#pf-fin')
    chk('parcela paga e saldo', 'R$ 600,00' in ft.replace('\xa0', ' ') and 'PAGA' in ft.upper())
    pg.evaluate("document.querySelector('#pf-fin').scrollIntoView()"); pg.screenshot(path=O + 'ficha_fin.png')
    path, data = baixa(pg, lambda: clk(pg, '#pf-fin [data-recpac]'))
    chk('recibo PDF do paciente', data[:5] == b'%PDF-' and b'trezentos reais' in data and b'DCTDecode' in data)
    # receita e atestado
    clk(pg, '[data-doc8="receita"]'); pg.wait_for_timeout(400)
    pg.fill('#rx-itens', 'Amoxicilina 500 mg ............ 21 cápsulas\nTomar 1 cápsula de 8 em 8 horas por 7 dias.\n\nIbuprofeno 600 mg ............ 6 comprimidos\nTomar 1 comprimido de 12 em 12 horas, se houver dor.')
    path, data = baixa(pg, lambda: clk(pg, '#rx-go'))
    pg.wait_for_timeout(800)
    chk('receita PDF com logo', data[:5] == b'%PDF-' and b'DCTDecode' in data and b'Amoxicilina' in data)
    os.replace(path, O + 'receita.pdf')
    db = mockdb(pg); chk('receita salva nos documentos', any(x['tipo'] == 'receita' for x in db['paciente_docs']))
    clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    clk(pg, '[data-doc8="atestado"]'); pg.wait_for_timeout(400)
    chk('atestado usa horário da consulta de hoje', pg.input_value('#at-h1') == '23:20')
    pg.select_option('#at-dias', '1')
    path, data = baixa(pg, lambda: clk(pg, '#at-go')); pg.wait_for_timeout(800)
    chk('atestado PDF', b'Atesto' in data and b'1 dia' in data); os.replace(path, O + 'atestado.pdf')
    clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    # ajustes: CRO, taxa, backup
    clk(pg, '#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(900)
    pg.evaluate("document.querySelector('[data-acc=prof]').open=true"); pg.wait_for_timeout(200)
    pg.fill('#prf-cro', 'CRO-MG 12345'); clk(pg, '#prf [type=submit]'); pg.wait_for_timeout(600)
    chk('CRO salvo', mockdb(pg)['cfg'].get('profCro') == 'CRO-MG 12345')
    pg.evaluate("document.querySelector('[data-acc=taxa]').open=true"); pg.wait_for_timeout(200)
    pg.select_option('#txf-pct', '50'); clk(pg, '#txf [type=submit]'); pg.wait_for_timeout(600)
    chk('taxa padrão salva', mockdb(pg)['cfg'].get('taxaCancelPct') == 50)
    pg.evaluate("document.querySelector('[data-acc=backup]').open=true"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('[data-acc=prof]').scrollIntoView()"); pg.screenshot(path=O + 'ajustes.png')
    path, data = baixa(pg, lambda: clk(pg, '#acc-backup [data-backup]'))
    z = zipfile.ZipFile(io.BytesIO(data)); wb = z.read('xl/workbook.xml').decode()
    chk('backup xlsx com abas', all(n in wb for n in ['Reservas', 'Pacientes', 'Orçamentos', 'Pagamentos pacientes', 'Termos aceites']) and 'Joana Silva' in z.read('xl/worksheets/sheet4.xml').decode())
    os.replace(path, O + 'backup.xlsx')
    # taxa na reserva futura e falta na passada
    pg.evaluate("openDrawer({ type: 'booking', id: 'f1' })"); pg.wait_for_timeout(500)
    chk('bloco de taxa na reserva', 'Cancelar com taxa' in pg.inner_text('#dr-body'))
    pg.evaluate("document.querySelector('[data-taxa]').scrollIntoView({block:'center'})"); pg.screenshot(path=O + 'taxa.png')
    clk(pg, '[data-taxa]'); pg.wait_for_timeout(200); clk(pg, '[data-taxa]'); pg.wait_for_timeout(900)
    bb = [x for x in mockdb(pg)['bookings'] if x['id'] == 'f1'][0]
    chk('cancelada com taxa de 50%', bb['status'] == 'taxa' and bb['valor'] == 50 and not any(s['booking_id'] == 'f1' for s in mockdb(pg)['slots']))
    clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    pg.evaluate("openDrawer({ type: 'booking', id: 'p1' })"); pg.wait_for_timeout(500)
    clk(pg, '[data-falta="p1"]'); pg.wait_for_timeout(600)
    chk('falta registrada', [x for x in mockdb(pg)['bookings'] if x['id'] == 'p1'][0].get('falta') is True)
    clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    # financeiro: pacientes e ocupação
    clk(pg, '#view-admin .side [data-tab="financeiro"]'); pg.wait_for_timeout(700)
    oc = pg.inner_text('#f-ocup')
    chk('relatório de ocupação', 'Mais procurados' in oc.title() or 'MAIS PROCURADOS' in oc.upper())
    chk('financeiro dos pacientes no painel', 'R$ 300,00' in pg.inner_text('#f-pac').replace('\xa0', ' '))
    pg.evaluate("document.querySelector('#f-pac').scrollIntoView()"); pg.screenshot(path=O + 'financeiro.png', full_page=False)
    pg.select_option('#oc-per', '12p'); pg.wait_for_timeout(300)
    chk('troca de período da ocupação', 'Últimas 12' in pg.inner_text('#f-ocup') or '12' in pg.input_value('#oc-per'))
    # celular
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.wait_for_timeout(300)
    clk(pg, '#view-admin .side [data-tab="pacientes"]'); pg.wait_for_timeout(500)
    clk(pg, '#p-body tr, #p-hoje [data-pac="pa1"]'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#pf-fin').scrollIntoView()"); pg.screenshot(path=O + 'm_ficha_fin.png')
    pg.evaluate("logout()"); pg.wait_for_timeout(1500)
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(800); pg.evaluate("document.querySelector('#estrutura').scrollIntoView()"); pg.wait_for_timeout(300); pg.screenshot(path=O + 'm_home_estrutura.png')
    # dentista vê a taxa
    pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(600)
    pg.fill('#dl-email', 'lucas@x.com'); pg.fill('#dl-pass', 'abc12345'); clk(pg, '#dl-login button[type=submit]'); pg.wait_for_timeout(1400)
    clk(pg, '#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(300); clk(pg, '#cr-seg [data-crv="historico"]'); pg.wait_for_timeout(300)
    h = pg.inner_text('#cr-list')
    chk('dentista vê a taxa e a falta', 'taxa por cancelamento' in h and 'falta registrada' in h)
    pg.screenshot(path=O + 'm_dent_hist.png')
    c.close(); b.close()
print('erros JS:', errs[:6]); print('FALHAS:', chk.fail)
