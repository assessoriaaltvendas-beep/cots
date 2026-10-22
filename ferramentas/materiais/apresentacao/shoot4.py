import json, datetime as dt, random, subprocess, os
from playwright.sync_api import sync_playwright
import os; AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.abspath(AQUI + '/../../..'); O = AQUI + '/shots4/'
os.makedirs(O, exist_ok=True)
mock = 'window.MOCK_TERMOS_OK=1;\n' + open(RAIZ + '/ferramentas/testes-navegador/mock-supabase.js').read()
cfg = "window.APP_CONFIG={supabaseUrl:'https://abcdefghijkl.supabase.co',supabaseAnonKey:'" + 'x' * 60 + "'};"
T1 = open(RAIZ + '/consultorio-thalia/supabase/schema.sql').read().split('$TERMOS$')[1]
T2 = T1.replace('4 (quatro) horas', '6 (seis) horas')
t = dt.date.today(); random.seed(3)
ds = [('lucas1', 'Lucas Andrade', 'CRO-MG 41.122', '(31) 98841-5460', 'lucas@x.com'), ('mari', 'Mariana Costa', 'CRO-MG 38.910', '(31) 99712-3301', 'mari@x.com'), ('rafa', 'Rafael Nunes', 'CRO-MG 45.077', '(31) 98620-1188', 'rafa@x.com'), ('julia', 'Júlia Prado', 'CRO-MG 50.231', '(31) 99155-0042', 'ju@x.com')]
bk = []; slots = []; n = 0
def add(did, d, a, b, pago=False, st='ativo'):
    global n; n += 1; nm = [x for x in ds if x[0] == did][0]
    v = 50 * (b - a) if b - a <= 3 else 180
    bk.append({'id': f'b{n}', 'dentist_id': did, 'nome': nm[1], 'cro': nm[2], 'tel': nm[3], 'email': nm[4], 'primeira': False, 'date': d.isoformat(), 'h_from': a, 'h_to': b, 'status': st, 'origem': 'area-dentista', 'pago': pago, 'valor': v, 'criado_em': (dt.datetime.now() - dt.timedelta(days=30)).isoformat()})
    if d < t and random.random() < .25: bk[-1]['avaliacao'] = {'nota': random.choice([5, 5, 5, 4, 4]), 'comentario': random.choice(['Consultório impecável, tudo funcionando.', 'Ótima localização e equipamentos novos.', '', 'Atendimento da Dra. Thalia sempre muito atencioso.', '']), 'em': d.isoformat() + 'T18:00:00'}
    if st == 'ativo' and d >= t: slots.extend({'date': d.isoformat(), 'hour': h, 'booking_id': f'b{n}'} for h in range(a, b))
for off in range(-60, 12):
    d = t + dt.timedelta(days=off)
    if d.weekday() == 6: continue
    for did, a, b, p in [('lucas1', 14, 16, .45), ('rafa', 18, 22, .35), ('julia', 9, 11, .3)]:
        if random.random() < p: add(did, d, a, b, pago=off < -3 and random.random() < .8)
nasc = lambda off, y: (t + dt.timedelta(days=off)).replace(year=(t + dt.timedelta(days=off)).year - y).isoformat()
pac = [('pa1', 'Joana Silva', '(31) 98888-7777', '123.456.789-00', nasc(0, 34)), ('pa2', 'Pedro Rocha', '(31) 97777-6666', '', nasc(3, 41)), ('pa3', 'Ana Beatriz Souza', '(31) 99123-4567', '', '1988-03-12'), ('pa4', 'Carlos Mendes', '(31) 98555-1212', '', '1975-07-30')]
cons = [('c1', 'pa1', t.isoformat(), '19:00', '19:45'), ('c2', 'pa3', t.isoformat(), '20:00', '20:30'), ('c3', 'pa2', (t + dt.timedelta(days=1)).isoformat(), '13:00', '13:45'), ('c4', 'pa4', (t + dt.timedelta(days=2)).isoformat(), '08:00', '09:00')]
seed = {'slots': slots, 'bookings': bk, 'secret': 'k', 'sent': [], 'admins': ['adm1', 'mari'], 'adm': {'adm1': {'nivel': 'completo', 'nome': 'Dra. Thalia Santiago'}, 'mari': {'nivel': 'agenda', 'em': '2026-10-21T18:00:00', 'por': 'Dra. Thalia Santiago'}}, 'admlog': [{'quando': '2026-10-21T18:00:00', 'autor': 'Dra. Thalia Santiago', 'email': 'mari@x.com', 'acao': 'adicionou', 'detalhe': 'administrador da agenda'}], 'avisos': [{'id': 'av1', 'titulo': 'Feriado de Finados', 'texto': 'No dia 2/11 o consultório estará fechado.', 'criado_em': (t - dt.timedelta(days=1)).isoformat() + 'T10:00:00'}], 'problemas': [], 'espera': [], 'app_config': [],
  'cfg': {'pix': '+5531995745413', 'pixNome': 'Thalia Santiago', 'pixCidade': 'Ipatinga', 'valorHora': 50, 'agendaToken': 'f' * 64, 'profNome': 'Dra. Thalia Santiago', 'profCro': 'CRO-MG 00000', 'profEspecialidade': 'Cirurgiã-dentista',
          'espaco': {'equipamentos': ['Cadeira odontológica com refletor de LED', 'Autoclave', 'Ultrassom e jato de bicarbonato', 'Fotopolimerizador', 'Raio X'], 'inclusos': ['Esterilização dos instrumentais', 'Luvas, gorros e máscaras', 'Wi-Fi e ar-condicionado'], 'levar': ['Materiais específicos do seu procedimento'], 'chegada': 'Chegue 10 minutos antes.', 'saida': 'Faça o checklist de saída.', 'wifi': 'COTS · senha na recepção'}},
  'faq': [{'id': 'q1', 'pergunta': 'O que está incluso no aluguel?', 'resposta': 'Cadeira odontológica, autoclave, fotopolimerizador e materiais básicos.', 'ordem': 1}, {'id': 'q2', 'pergunta': 'Posso cancelar ou remarcar?', 'resposta': 'Sim, até 4 horas antes, com direito a reembolso.', 'ordem': 2}, {'id': 'q3', 'pergunta': 'Como funciona o pagamento?', 'resposta': 'Por Pix, e você envia o comprovante pela sua área.', 'ordem': 3}],
  'dentists': [{'id': i, 'nome': nm, 'cro': c, 'whatsapp': w, 'email': e, 'status': 'liberado', 'criado_em': '2026-08-01T10:00:00', 'termos_versao': 1 if i == 'julia' else 2, 'termos_aceito_em': '2026-10-20T10:00:00'} for i, nm, c, w, e in ds] + [{'id': 'bia', 'nome': 'Beatriz Lima', 'cro': 'CRO-MG 52.880', 'whatsapp': '(31) 91234-5678', 'email': 'bia@x.com', 'status': 'pendente', 'criado_em': t.isoformat() + 'T09:12:00', 'termos_versao': 2}],
  'termos_versoes': [{'id': 'tv1', 'versao': 1, 'texto': T1, 'resumo': 'Versão inicial', 'criado_em': '2026-10-21T10:00:00'}, {'id': 'tv2', 'versao': 2, 'texto': T2, 'resumo': 'Prazo de cancelamento com reembolso passou para 6 horas', 'criado_em': '2026-10-22T09:00:00'}],
  'termos_aceites': [{'id': f'ta{i}', 'dentist_id': d[0], 'versao': v, 'aceito_em': '2026-10-21T11:00:00'} for i, (d, v) in enumerate([(x, 1) for x in ds] + [(x, 2) for x in ds if x[0] != 'julia'])],
  'planos': [{'id': 'pl1', 'dentist_id': 'rafa', 'modalidade': 'diaria', 'dia_semana': 5, 'h_from': 8, 'h_to': 18, 'valor_mensal': 1000, 'inicio': (t + dt.timedelta(days=(4 - t.weekday()) % 7 or 7)).isoformat(), 'status': 'pendente', 'criado_em': t.isoformat() + 'T08:00:00'}],
  'pacientes': [{'id': i, 'nome': nm, 'telefone': tel, 'cpf': cpf, 'nascimento': nz, 'criado_em': '2026-09-01T10:00:00'} for i, nm, tel, cpf, nz in pac],
  'consultas': [{'id': i, 'paciente_id': p, 'data': d, 'inicio': a, 'fim': z, 'status': 'agendada', 'criado_em': '2026-10-01T10:00:00'} for i, p, d, a, z in cons],
  'evolucoes': [{'id': 'e1', 'paciente_id': 'pa1', 'data': (t - dt.timedelta(days=7)).isoformat(), 'texto': 'Abertura coronária e odontometria no dente 36. Retorno em 7 dias.', 'criado_em': '2026-10-14T10:00:00'}],
  'pac_orcamentos': [{'id': 'o1', 'paciente_id': 'pa1', 'descricao': 'Tratamento de canal no dente 36', 'valor': 900, 'status': 'aprovado', 'parcelas': 3, 'primeiro_venc': (t - dt.timedelta(days=7)).isoformat(), 'data': (t - dt.timedelta(days=7)).isoformat(), 'criado_em': '2026-10-14T10:00:00'},
                     {'id': 'o2', 'paciente_id': 'pa1', 'descricao': 'Clareamento caseiro', 'valor': 650, 'status': 'aberto', 'parcelas': 1, 'data': t.isoformat(), 'criado_em': '2026-10-21T10:00:00'}],
  'pac_pagamentos': [{'id': 'g1', 'paciente_id': 'pa1', 'orcamento_id': 'o1', 'data': (t - dt.timedelta(days=7)).isoformat(), 'valor': 300, 'forma': 'pix', 'criado_em': '2026-10-14T10:00:00'}],
  'users': [{'id': 'adm1', 'email': 't@x.com', 'password': 'senha12345'}, {'id': 'bia', 'email': 'bia@x.com', 'password': 'abc12345'}] + [{'id': i, 'email': e, 'password': 'abc12345'} for i, _, _, _, e in ds]}
def _pad():
    with sync_playwright() as p0:
        b0 = p0.chromium.launch(); g = b0.new_page(); g.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock)); g.goto('http://localhost:8765/'); g.wait_for_timeout(700); v = json.loads(g.evaluate('JSON.stringify(CALC_PADRAO)')); b0.close(); return v
seed['calc'] = {'itens': _pad(), 'liberada': True, 'base': 1, 'em': '2026-10-21T21:30:00', 'por': 'Dra. Thalia Santiago', 'log': [{'quando': '2026-10-21T21:30:00', 'autor': 'Dra. Thalia Santiago', 'acao': 'revisou e liberou a calculadora para os dentistas'}]}
init = "if(!localStorage.getItem('mockdb'))localStorage.setItem('mockdb'," + json.dumps(json.dumps(seed)) + ");"
def clk(pg, sel, i=0): pg.query_selector_all(sel)[i].evaluate('e=>e.click()')
def top(pg, sel, off=80): pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}'); if(e){{e.scrollIntoView({{block:'start'}}); window.scrollBy(0,-{off});}}}})()"); pg.wait_for_timeout(300)
def login(pg, email, pw, admin=False):
    if admin:
        pg.goto('http://localhost:8765/#admin'); pg.wait_for_timeout(600); pg.fill('#dl-email', email); pg.fill('#dl-pass', pw); clk(pg, '#dl-login button[type=submit]')
    else:
        pg.goto('http://localhost:8765/#dentista'); pg.wait_for_timeout(600); clk(pg, '#dl-seg [data-dl="login"]'); pg.fill('#dl-email', email); pg.fill('#dl-pass', pw); clk(pg, '#dl-login button[type=submit]')
    pg.wait_for_timeout(1400)
with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=2, accept_downloads=True)
    c.route('**/supabase-js@2.110.1**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=mock))
    c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=cfg))
    c.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    c.route('https://www.google.com/**', lambda r: r.fulfill(status=200, body='<html><body style="margin:0;background:#ece6e3;display:grid;place-items:center;height:100vh;font:14px sans-serif;color:#8a7a7d">Mapa do Google</body></html>', content_type='text/html'))
    c.add_init_script(init)
    pg = c.new_page()
    pg.goto('http://localhost:8765/'); pg.wait_for_timeout(1200); pg.screenshot(path=O + 'home.png')
    top(pg, '#estrutura', 60); pg.screenshot(path=O + 'home_estrutura.png')
    # cadastro com termos
    clk(pg, '#start'); pg.wait_for_timeout(500); clk(pg, '#dl-seg [data-dl="reg"]'); pg.wait_for_timeout(400)
    pg.fill('#dr-nome', 'Beatriz Lima'); pg.fill('#dr-cro', 'CRO-MG 52.880'); pg.fill('#dr-tel', '(31) 91234-5678'); pg.fill('#dr-email', 'bia@exemplo.com')
    top(pg, '#dr-pass', 120); pg.screenshot(path=O + 'p_reg.png')
    login(pg, 'bia@x.com', 'abc12345'); pg.screenshot(path=O + 'p_wait.png'); clk(pg, '#c-wait [data-dlogout]'); pg.wait_for_timeout(800)
    # dentista
    login(pg, 'lucas@x.com', 'abc12345')
    clk(pg, '#view-dent .side [data-ctab="inicio"]'); pg.wait_for_timeout(500); pg.screenshot(path=O + 'd_inicio.png')
    clk(pg, '#view-dent .side [data-ctab="nova"]'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#cn-plano .pl-form').open=true"); pg.wait_for_timeout(300); pg.screenshot(path=O + 'd_plano.png')
    pg.evaluate("document.querySelector('#cn-plano .pl-form').open=false"); pg.wait_for_timeout(200)
    fd = [x for x in bk if x['date'] > t.isoformat()][0]['date']
    nd = (t + dt.timedelta(days=4)); nd = nd + dt.timedelta(days=1) if nd.weekday() == 6 else nd
    pg.evaluate(f"(()=>{{Object.assign(S.cn,{{date:'{nd.isoformat()}',start:null,end:null}}); renderCNova();}})()"); pg.wait_for_timeout(300)
    top(pg, '#cn-day', 30); pg.screenshot(path=O + 'd_nova.png')
    clk(pg, '#view-dent .side [data-ctab="financeiro"]'); pg.wait_for_timeout(500); top(pg, '#cf-pix', 110); pg.screenshot(path=O + 'd_fin_pix.png')
    clk(pg, '#view-dent .side [data-ctab="reservas"]'); pg.wait_for_timeout(300)
    fut = [x for x in bk if x['dentist_id'] == 'lucas1' and x['date'] > t.isoformat()]
    pg.evaluate(f"document.querySelector('#cr-list [data-cbk=\"{fut[0]['id']}\"]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("const h=[...document.querySelectorAll('#c-drawer h4')].find(x=>/Pagar com Pix/.test(x.textContent)); if(h) h.scrollIntoView({block:'start'})"); pg.wait_for_timeout(300)
    pg.screenshot(path=O + 'd_drawer_pix.png')
    pg.evaluate("dlogout()"); pg.wait_for_timeout(900)
    # painel
    login(pg, 't@x.com', 'senha12345', admin=True)
    pg.evaluate("S.store.rpc('criar_plano', { p_dentist: 'mari', p_modalidade: 'periodo', p_dia: 2, p_from: 8, p_to: 13, p_inicio: proximasDatas(2, 1, iso(new Date()))[0] })"); pg.wait_for_timeout(900)
    pg.evaluate("S.store.refresh()"); pg.wait_for_timeout(900)
    clk(pg, '#view-admin .side [data-tab="resumo"]'); pg.wait_for_timeout(600); pg.screenshot(path=O + 'a_resumo.png')
    top(pg, '#r-pac', 90); pg.screenshot(path=O + 'a_resumo2.png')
    clk(pg, '#view-admin .side [data-tab="dentistas"]'); pg.wait_for_timeout(600); pg.screenshot(path=O + 'a_dentistas.png')
    pg.evaluate("document.querySelector('#d-body tr[data-dent=\"mari\"]').click()"); pg.wait_for_timeout(500); pg.screenshot(path=O + 'a_dent_drawer.png'); clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    clk(pg, '#view-admin .side [data-tab="agenda"]'); pg.wait_for_timeout(500); clk(pg, '#a-views [data-view="semana"]'); pg.wait_for_timeout(400); pg.screenshot(path=O + 'a_agenda.png')
    pg.evaluate(f"openDrawer({{ type: 'booking', id: '{fut[1]['id']}' }})"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-taxa]').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300); pg.screenshot(path=O + 'a_taxa.png'); clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    clk(pg, '#view-admin .side [data-tab="pacientes"]'); pg.wait_for_timeout(600); pg.screenshot(path=O + 'a_pacientes.png')
    clk(pg, '#p-hoje [data-pac="pa1"]'); pg.wait_for_timeout(700); pg.screenshot(path=O + 'a_ficha.png')
    top(pg, '#pf-fin', 80); pg.screenshot(path=O + 'a_ficha_fin.png')
    clk(pg, '[data-doc8="receita"]'); pg.wait_for_timeout(500)
    pg.fill('#rx-itens', 'Amoxicilina 500 mg ............ 21 cápsulas\nTomar 1 cápsula de 8 em 8 horas por 7 dias.\n\nIbuprofeno 600 mg ............ 6 comprimidos\nTomar 1 comprimido de 12 em 12 horas, se houver dor.')
    pg.fill('#rx-obs', 'Evitar alimentos muito quentes nas primeiras 24 horas.')
    pg.screenshot(path=O + 'a_receita_form.png')
    with pg.expect_download() as di: clk(pg, '#rx-go')
    di.value.save_as(O + 'receita.pdf'); pg.wait_for_timeout(600); clk(pg, '#dr-close'); pg.wait_for_timeout(300)
    clk(pg, '#view-admin .side [data-tab="financeiro"]'); pg.wait_for_timeout(700); pg.screenshot(path=O + 'a_financeiro.png')
    top(pg, '#f-ocup', 80); pg.screenshot(path=O + 'a_ocup.png')
    clk(pg, '#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(1000); pg.screenshot(path=O + 'a_ajustes.png')
    for acc, nm in [('valores', 'a_valores'), ('planos', 'a_planos'), ('termos', 'a_termos'), ('backup', 'a_backup'), ('rel', 'a_rel'), ('pag', 'a_pix')]:
        pg.evaluate("document.querySelectorAll('#t-ajustes details.acc').forEach(d=>d.open=false)")
        pg.evaluate(f"document.querySelector('[data-acc={acc}]').open=true"); pg.wait_for_timeout(350)
        if acc == 'termos':
            pg.evaluate("document.querySelector('details.tv[data-tv=\"2\"]').open=true"); pg.wait_for_timeout(400); top(pg, 'details.tv[data-tv="2"]', 80)
        else: top(pg, f'[data-acc={acc}]', 80)
        pg.screenshot(path=O + nm + '.png')
    clk(pg, '#view-admin .side [data-tab="site"]'); pg.wait_for_timeout(600); pg.screenshot(path=O + 'a_site.png')
    clk(pg, '#view-admin .side [data-tab="ajustes"]'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelectorAll('#t-ajustes details.acc').forEach(d=>d.open=false)")
    pg.evaluate("document.querySelector('[data-acc=admins]').open=true"); pg.wait_for_timeout(900); top(pg, '[data-acc=admins]', 30); pg.screenshot(path=O + 'a_admins.png')
    clk(pg, '#view-admin .side [data-tab="calc"]'); pg.wait_for_timeout(900)
    for k, v in [('peso', '18'), ('anos', '4')]: pg.fill(f'#calc-a [data-cin="{k}"]', v); pg.wait_for_timeout(150)
    pg.select_option('#calc-a [data-cin="med"]', 'dipirona-gotas'); pg.wait_for_timeout(300)
    for k, v in [('peso', '18'), ('anos', '4')]: pg.fill(f'#calc-a [data-cin="{k}"]', v); pg.wait_for_timeout(150)
    top(pg, '#calc-a .calc-adm', 20); pg.screenshot(path=O + 'a_calc.png')
    pg.evaluate("logout()"); pg.wait_for_timeout(1500)
    # celular
    m = c.new_page(); m.set_viewport_size({'width': 390, 'height': 844})
    m.goto('http://localhost:8765/'); m.wait_for_timeout(1000); m.screenshot(path=O + 'mob_home.png')
    login(m, 'lucas@x.com', 'abc12345')
    clk(m, '#view-dent .side [data-ctab="inicio"]'); m.wait_for_timeout(500); m.screenshot(path=O + 'app_inicio.png')
    clk(m, '#view-dent .side [data-ctab="financeiro"]'); m.wait_for_timeout(500); top(m, '#cf-pix', 70); m.screenshot(path=O + 'app_pix.png')
    m.evaluate("dlogout()"); m.wait_for_timeout(900)
    login(m, 'ju@x.com', 'abc12345')
    m.evaluate("(()=>{const x=document.querySelector('#tg-box ins'); if(x) x.scrollIntoView({block:'center'});})()"); m.wait_for_timeout(300); m.screenshot(path=O + 'm_gate.png')
    b.close()
subprocess.run(['pdftoppm', '-r', '110', '-png', '-singlefile', O + 'receita.pdf', O + 'receita'], check=True)
print('ok')
