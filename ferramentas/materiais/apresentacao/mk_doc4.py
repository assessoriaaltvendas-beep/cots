import re
D = '/tmp/claude-0/-home-claude/dcc176e0-b17e-526f-b4d8-21aa4df71887/scratchpad/pdf/'
head = open(D + 'doc2.html').read().split('</style>')[0]
head = re.sub(r'box-shadow:[^;}]*;?', '', head)
head = head.replace('.phone{border:2mm solid #1f1416;', '.phone{border:2mm solid #1f1416;outline:0.4mm solid #b8953f;')
head += """
.cover .r .shot{border:0.5mm solid rgba(217,187,111,.55)}
.phone img{height:118mm}
.three.four{grid-template-columns:repeat(4,1fr);gap:5mm}
.three.four .card{padding:6mm 5mm 5mm}
.three.four .card h3{font-size:12.5pt}
.price{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:6mm}
.price div{border:1px solid var(--ln);border-radius:3mm;padding:3mm 3.5mm;background:#fff}
.price b{display:block;font:600 13pt Lora;color:var(--w);white-space:nowrap}
.price span{font-size:8.6pt;color:var(--mu)}
.price div.hl{background:var(--gs);border-color:#ecdcae}
.split.r{grid-template-columns:1fr 92mm}
.ph-row{display:flex;gap:6mm;justify-content:center;align-items:flex-start}
.ph-row .phone img{height:112mm}
.tag3{display:inline-block;font:600 6.8pt Inter;letter-spacing:.1em;text-transform:uppercase;background:var(--gs);color:var(--w2);padding:.8mm 2.2mm;border-radius:99px;margin-left:2mm;vertical-align:2pt}
.pdfprev{border:1px solid var(--ln);border-radius:2mm;overflow:hidden;background:#fff}
.pdfprev img{display:block;width:100%}
.three .card ul{font-size:9pt}
"""
FOOT = '<div class="foot"><span><b>Consultório Odontológico Thalia Santiago</b> · Site de reservas</span><span>{n}</span></div>'
pages = []
def li(items): return '\n'.join(f'<li><b>{a}</b> <span>{b}</span></li>' for a, b in items)
def split(eye, title, items, img, lead='', rev=False):
    lst = f'<ul class="f">{li(items)}</ul>'; sh = f'<div><div class="shot"><img src="shots4/{img}.png" alt=""></div></div>'
    pages.append(f'<div class="eye">{eye}</div><h2>{title}</h2>' + (f'<p class="lead">{lead}</p>' if lead else '') + f'<div class="split{" r" if rev else ""}">' + (sh + lst if rev else lst + sh) + '</div>')
def two(eye, title, a, b, lead=''):
    col = lambda x: f'<div><div class="shot"><img src="shots4/{x[0]}.png" alt=""></div><ul class="f mini">{li(x[1])}</ul></div>'
    pages.append(f'<div class="eye">{eye}</div><h2>{title}</h2>' + (f'<p class="lead">{lead}</p>' if lead else '') + f'<div class="two">{col(a)}{col(b)}</div>')
def raw(h): pages.append(h)

raw('''<div class="eye">Visão geral</div><h2>Um site, <em>três áreas</em></h2>
<p class="lead">Cada pessoa vê só o que precisa. Só reserva quem tem conta liberada pela Dra. Thalia e aceitou os termos de uso, e o banco de dados impede que duas pessoas reservem o mesmo horário.</p>
<div class="three">
<div class="card"><div class="n">01</div><h3>Página inicial</h3><p>Vitrine do consultório para dentistas que querem conhecer e alugar.</p>
<ul><li>Fotos, equipamentos, valores e mapa</li><li>Horários livres em tempo real</li><li>Cadastro com termos de uso</li></ul></div>
<div class="card"><div class="n">02</div><h3>Área do dentista</h3><p>Conta própria, liberada pela Dra. Thalia.</p>
<ul><li>Reservar por hora, período, diária ou plano mensal</li><li>Pix com QR Code e recibo em PDF</li><li>Calculadora clínica e app no celular</li></ul></div>
<div class="card"><div class="n">03</div><h3>Painel da Dra. Thalia</h3><p>Login único; a Dra. escolhe quem administra.</p>
<ul><li>Dentistas, agenda, planos, financeiro e administradores</li><li>Pacientes: ficha, receita, atestado e financeiro</li><li>Ajustes, termos, backup e relatórios</li></ul></div>
</div>
<div class="band">
<div><b>Hora, período ou plano</b><span>R$ 50/h, período R$ 180, diária R$ 350 e planos mensais com desconto</span></div>
<div><b>Seguro</b><span>Cadastro liberado pela Dra., termos aceitos e horário bloqueado na hora</span></div>
<div><b>App</b><span>Instala no celular e recebe notificações, sem loja de aplicativos</span></div>
<div><b>R$ 0</b><span>Hospedagem, banco, e-mails e notificações em planos gratuitos</span></div>
</div>''')
split('01 · Página inicial', 'A vitrine do <em>consultório</em>', [
    ('Agenda ao vivo.', 'Mostra os próximos horários livres do consultório.'),
    ('Estrutura e valores.', 'Equipamentos, o que está incluso no aluguel e os preços, com o plano mensal.'),
    ('Galeria e dúvidas.', 'Fotos e perguntas frequentes, editáveis pelo painel.'),
    ('Mapa, Instagram e WhatsApp.', 'Localização real, link para @dra.thaliasantiago e botão flutuante do WhatsApp.'),
    ('Termos de uso.', 'Sempre disponíveis no rodapé do site.'),
    ('Agendar horário.', 'Leva para entrar na conta ou criar o cadastro.')], 'home')
split('01 · Página inicial', 'Estrutura e <em>valores</em>', [
    ('Equipamentos.', 'Lista cadastrada em Ajustes, com destaque na página inicial.'),
    ('Incluso no aluguel.', 'O que o dentista não precisa levar.'),
    ('Preços claros.', 'Hora, período, diária e plano mensal, sempre com os valores atuais.'),
    ('Dois caminhos.', 'Agendar horário pelo site ou combinar uma visita pelo WhatsApp.')], 'home_estrutura',
    lead='A página mostra por que vale a pena alugar o consultório antes mesmo do cadastro.')
raw('''<div class="eye">01 · Página inicial</div><h2>Do cadastro à <em>reserva</em></h2>
<p class="lead">Ninguém reserva sem passar pela Dra. Thalia. Assim, só profissionais conferidos usam a agenda.</p>
<div class="steps">
<div><div class="shot"><img src="shots4/p_reg.png" alt=""></div><div class="k"><i>1</i><b>Cria a conta</b></div><p>Nome, CRO, WhatsApp e e-mail. Lê os termos até o final para liberar o aceite.</p></div>
<div><div class="shot"><img src="shots4/p_wait.png" alt=""></div><div class="k"><i>2</i><b>Aguarda</b></div><p>A tela mostra que o cadastro foi recebido e está em análise.</p></div>
<div><div class="shot"><img src="shots4/a_dentistas.png" alt=""></div><div class="k"><i>3</i><b>Dra. Thalia libera</b></div><p>Ela recebe notificação e e-mail e toca em Liberar ou Bloquear.</p></div>
<div><div class="shot"><img src="shots4/d_nova.png" alt=""></div><div class="k"><i>4</i><b>Reserva</b></div><p>O dentista recebe um e-mail e já escolhe dia e horário livres.</p></div>
</div>''')
raw('''<div class="eye">Segurança jurídica</div><h2>Termos de uso <em>com registro</em></h2>
<div class="split" style="grid-template-columns:1fr 70mm 1fr">
<ul class="f">
<li><b>Leitura obrigatória.</b> <span>No cadastro, o aceite só libera depois de rolar o texto até o final. Sem o aceite, o banco de dados não cria a conta.</span></li>
<li><b>Versões com histórico.</b> <span>A Dra. Thalia edita o texto em Ajustes. Cada publicação vira uma versão com data e resumo.</span></li>
<li><b>O que mudou, destacado.</b> <span>Trecho removido riscado e trecho novo em verde, no painel e na tela do dentista.</span></li>
<li><b>Novo aceite.</b> <span>A cada versão, todos aceitam de novo no próximo acesso. Sem aceite, não reservam.</span></li>
<li><b>Quem aceitou e quando.</b> <span>Data e versão de cada aceite, na ficha de cada dentista.</span></li>
</ul>
<div class="phone"><img src="shots4/m_gate.png" alt="" style="height:112mm"></div>
<div><div class="shot"><img src="shots4/a_termos.png" alt=""></div><p class="cap">Histórico de versões no painel, com a comparação entre a versão 2 e a 1.</p></div>
</div>''')
split('02 · Área do dentista', 'Tudo do dentista <em>num lugar só</em>', [
    ('Início.', 'Próxima reserva em destaque, créditos do plano e os avisos mais importantes.'),
    ('Reserva rápida.', 'O site aprende o horário de sempre e oferece reservar de novo com dois toques.'),
    ('Níveis de fidelidade.', 'Novo no consultório, Frequente (10h) e Parceiro da casa (40h).'),
    ('Mural.', 'Avisos publicados pela Dra. Thalia, com notificação no celular.'),
    ('Consultório.', 'Endereço, regras de uso, chegada e saída, equipamentos e o que levar.'),
    ('Perfil.', 'Dados profissionais, senha, termos aceitos, tema claro ou escuro e o app no celular.')], 'd_inicio')
raw('''<div class="eye">02 · Área do dentista</div><h2>Hora, período <em>ou diária</em></h2>
<div class="split">
<div><ul class="f">
<li><b>Até 3 horas, por hora.</b> <span>Toca na hora inicial e na final; o valor aparece antes de confirmar.</span></li>
<li><b>Acima de 3 horas, por período.</b> <span>Manhã, tarde, noite, diária ou dia todo, com um toque.</span></li>
<li><b>Entre períodos, com a Dra.</b> <span>Ex.: 11h às 15h. O site trava e mostra o botão para falar com ela.</span></li>
<li><b>Repetir toda semana e lista de espera.</b> <span>Reserva em série e aviso quando um horário vagar.</span></li>
<li><b>Remarcar ou cancelar até 4 horas antes.</b> <span>Com direito a reembolso, como dizem os termos.</span></li>
</ul>
<div class="price"><div><b>R$ 50</b><span>por hora, até 3 horas</span></div><div><b>R$ 180</b><span>manhã, tarde ou noite</span></div><div><b>R$ 350</b><span>diária, 8h às 18h</span></div></div></div>
<div><div class="shot"><img src="shots4/d_nova.png" alt=""></div></div></div>''')
raw('''<div class="eye">02 · Área do dentista</div><h2>Plano <em>mensal</em></h2>
<div class="split">
<div><ul class="f">
<li><b>1x por semana, mesmo dia e período.</b> <span>O dentista pede na aba Reservar e vê as próximas datas livres ou ocupadas.</span></li>
<li><b>Aprovação da Dra. Thalia.</b> <span>Ela aprova no painel, ou cria um plano direto para um dentista.</span></li>
<li><b>Reservas automáticas.</b> <span>O site reserva o mês atual e o próximo, e renova todo mês.</span></li>
<li><b>Valor fixo.</b> <span>O mesmo com 4 ou 5 semanas; no primeiro mês, só as semanas a partir do início.</span></li>
<li><b>Crédito.</b> <span>Avisando com 3 dias de antecedência, o dia vira crédito para remarcar no mesmo mês.</span></li>
</ul>
<div class="price"><div class="hl"><b>R$ 1.000</b><span>diária por mês (R$ 250 cada)</span></div><div class="hl"><b>R$ 600</b><span>meio período por mês (R$ 150 cada)</span></div><div><b>3 dias</b><span>de aviso para virar crédito</span></div></div></div>
<div><div class="shot"><img src="shots4/d_plano.png" alt=""></div></div></div>''')
two('02 · Área do dentista', 'Pagar com <em>Pix</em>', ('d_drawer_pix', [
    ('Pix de cada reserva.', 'QR Code e Pix copia e cola já com o valor certo.'),
    ('Comprovante.', 'Envia a foto ou o PDF do pagamento direto na reserva.'),
    ('Lembrete no celular.', 'Agenda do celular ou Google Agenda, com alarme 2 horas antes.')]),
    ('d_fin_pix', [
    ('Extrato do mês.', 'Cada reserva com valor e situação: paga, em aberto ou comprovante enviado.'),
    ('Pix do total em aberto.', 'Um QR Code com a soma do mês, inclusive do plano mensal.'),
    ('Recibo em PDF.', 'Recibo do mês com as reservas pagas, pronto para guardar ou enviar.')]))
split('03 · Painel da Dra. Thalia', 'O consultório <em>num relance</em>', [
    ('Resumo.', 'Reservas de hoje, próximas reservas, horas do mês e dentistas novos.'),
    ('Pedidos para decidir.', 'Cadastros novos e pedidos de plano mensal, com Aprovar e Recusar.'),
    ('Pacientes de hoje.', 'Consultas do dia com lembrete no WhatsApp e os aniversariantes da semana.'),
    ('Ocupação e financeiro.', 'Gráfico da semana e receita prevista do mês.'),
    ('Avaliações.', 'Nota média do consultório e os últimos comentários.'),
    ('Backup.', 'Aviso quando faz mais de 30 dias que a planilha não é baixada.')], 'a_resumo')
split('03 · Painel da Dra. Thalia', 'Dentistas <em>e planos</em>', [
    ('Liberar e bloquear.', 'Um toque; o dentista recebe e-mail e notificação.'),
    ('Editar e excluir.', 'Dados de cada dentista, com o histórico preservado.'),
    ('Planos mensais.', 'Ativos, pedidos para aprovar, créditos abertos e o total por mês. Encerrar vale até o fim do mês.'),
    ('Termos de uso.', 'Quem ainda não aceitou a versão atual aparece marcado.'),
    ('Ficha de cada dentista.', 'Reservas, horas, plano, aceites dos termos, recibo do mês e WhatsApp.')], 'a_dent_drawer')
two('03 · Painel da Dra. Thalia', 'Agenda <em>completa</em>', ('a_agenda', [
    ('Semana, dia ou lista.', 'Reservas, planos, bloqueios e consultas dos pacientes da Dra.'),
    ('Confirmar pelo WhatsApp.', 'Mensagem pronta com nome, data e horário.'),
    ('Fechar datas.', 'Férias, feriados ou manutenção somem da agenda dos dentistas.')]),
    ('a_taxa', [
    ('Cancelar com taxa.', 'Fora do prazo: libera o horário e cobra 100%, 75%, 50% ou 25% do valor.'),
    ('O dentista faltou.', 'Registra a falta; a reserva continua cobrada.'),
    ('Pagamento e valor.', 'Marcar como pago e ajustar o valor de uma reserva específica.')]))
split('04 · Pacientes da Dra. Thalia', 'O consultório <em>dela também</em>', [
    ('Cadastro de pacientes.', 'Nome, telefone, CPF, nascimento e observações. Só a Dra. Thalia vê.'),
    ('Consultas de 15 em 15 minutos.', 'Ocupam a agenda: para os dentistas, o horário aparece só como ocupado.'),
    ('Lembrete no WhatsApp.', 'Ícone verde em cada consulta, com dia, hora e endereço prontos.'),
    ('Aniversariantes da semana.', 'Com botão para mandar parabéns.'),
    ('Busca rápida.', 'Por nome, telefone ou CPF, e o total a receber no topo.')], 'a_pacientes')
raw('''<div class="eye">04 · Pacientes da Dra. Thalia</div><h2>Ficha <em>completa</em></h2>
<div class="split" style="grid-template-columns:1fr 1fr 62mm">
<div><div class="shot"><img src="shots4/a_ficha.png" alt=""></div><ul class="f mini">
<li><b>Consultas e evolução.</b> <span>O que foi feito em cada consulta, com data.</span></li>
<li><b>Documentos.</b> <span>Prontuário, orçamento e radiografias num armazenamento privado.</span></li></ul></div>
<div><div class="shot"><img src="shots4/a_ficha_fin.png" alt=""></div><ul class="f mini">
<li><b>Financeiro do paciente.</b> <span>Orçamentos, parcelas (paga, a vencer ou vencida) e pagamentos.</span></li>
<li><b>Recibo em PDF.</b> <span>Com o valor por extenso, a logo e a assinatura.</span></li></ul></div>
<div><div class="pdfprev"><img src="shots4/receita.png" alt=""></div><p class="cap">Receita e atestado em PDF com a logo, gerados na ficha e salvos nos documentos.</p></div>
</div>''')
two('03 · Painel da Dra. Thalia', 'Financeiro e <em>ocupação</em>', ('a_financeiro', [
    ('Visão do mês.', 'Receita prevista, horas, reservas e cancelamentos, por dentista.'),
    ('Cobrança automática.', 'Lembrete a cada 3 dias e, se quiser, bloqueio para quem está em atraso.'),
    ('Pacientes.', 'Recebido no mês, a receber e parcelas vencidas.')]),
    ('a_ocup', [
    ('Mapa de ocupação.', 'Por dia da semana e horário, nas últimas 4, 8 ou 12 semanas.'),
    ('Mais procurados e mais vazios.', 'Os horários vazios são os melhores para promoção.'),
    ('Planilha do mês.', 'Exporta para o Excel ou o Google Planilhas.')]))
two('03 · Painel da Dra. Thalia', 'Ajustes <em>sem mexer em código</em>', ('a_ajustes', [
    ('Valores e funcionamento.', 'Hora, períodos, diária, dias abertos, horário e prazo de 4 horas.'),
    ('Planos e termos.', 'Valor dos planos, aviso para crédito e o texto dos termos de uso.'),
    ('Faltas e receitas.', 'Taxa padrão por cancelamento fora do prazo; nome e CRO da assinatura.')]),
    ('a_valores', [
    ('Pix.', 'Gera QR Code e copia e cola de cada reserva, com prévia para testar no banco.'),
    ('Regras e espaço.', 'Regras de uso, checklist de saída, equipamentos e Wi-Fi.'),
    ('Tudo em um lugar.', 'Também app no celular, e-mails, aparência e conta.')]))
two('03 · Painel da Dra. Thalia', 'Relatório, backup e <em>site</em>', ('a_rel', [
    ('Relatório mensal.', 'Todo dia 1º no e-mail: reservas, ocupação, receita, pendências e avaliações.'),
    ('Google Agenda.', 'As reservas aparecem na agenda do Google da Dra. Thalia.')]),
    ('a_backup', [
    ('Backup em planilha.', 'Um arquivo do Excel com 11 abas: reservas, dentistas, planos, pacientes, consultas e financeiro.'),
    ('Lembrete todo dia 1º.', 'Notificação e e-mail para baixar o backup do mês.')]))
split('03 · Painel da Dra. Thalia', 'Administradores <em>com dois níveis</em>', [
    ('Um só botão Entrar.', 'Quem é administrador vai direto para o painel; dentista vai para a área dele.'),
    ('Administrador completo.', 'Vê tudo, inclusive pacientes, documentos e financeiro dos pacientes, e gerencia os administradores.'),
    ('Administrador da agenda.', 'Cuida de dentistas, reservas, agenda, planos, cobranças, mural e site. Consultas aparecem só como “Ocupado”.'),
    ('Trava no banco de dados.', 'Os dados dos pacientes nem chegam ao aparelho de quem não é administrador completo.'),
    ('Histórico.', 'Quem adicionou, mudou o nível ou removeu cada administrador, e quando.'),
    ('Dentista e administrador.', 'Um atalho alterna entre o painel e a área de dentista.')], 'a_admins')
split('05 · Calculadora clínica', 'Doses com <em>fonte da bula</em>', [
    ('Medicamentos.', 'Dipirona, paracetamol, ibuprofeno, amoxicilina e azitromicina: dose por vez em mg, mL e gotas, intervalo e máximo por dia.'),
    ('Anestésico em tubetes.', 'Dose máxima por peso, com limite de epinefrina para cardiopatas.'),
    ('Profilaxia e conversões.', 'Esquema da AHA 2021, mg → mL/gotas e diluição de hipoclorito.'),
    ('Segura por padrão.', 'Sem peso e idade, ou fora da faixa da bula, não mostra número.'),
    ('Revisada pela Dra.', 'Ela revisa, edita e libera para os dentistas; cada alteração fica registrada.')], 'a_calc',
    lead='No painel e na área do dentista, para as contas do dia a dia na cadeira.')
raw('''<div class="eye">App no celular</div><h2>Um app, <em>sem loja de aplicativos</em></h2>
<div class="split"><div><ul class="f">
<li><b>Instala direto do site.</b> <span>No Android, pelo botão “Instalar app”; no iPhone, pelo Safari em Compartilhar → Adicionar à Tela de Início.</span></li>
<li><b>Ícone com a logo nova.</b> <span>O dente dourado da COTS na tela do celular.</span></li>
<li><b>Notificações gratuitas.</b> <span>Lembretes, vagas, cobranças, cadastros, planos, termos e avisos do mural.</span></li>
<li><b>Pix no celular.</b> <span>Copia o código e paga no app do banco, sem digitar nada.</span></li></ul>
<div class="nts">
<div class="nt"><img src="icon-192.png" alt=""><div><small>Thalia Santiago · agora</small><b>Pedido de plano · Rafael Nunes</b><span>Diária · toda sexta-feira, 8h às 18h · R$ 1.000,00/mês. Toque para aprovar.</span></div></div>
<div class="nt"><img src="icon-192.png" alt=""><div><small>Thalia Santiago · agora</small><b>Sua reserva começa às 14h</b><span>Lembrete do consultório: sex, 23/10, 14h às 16h.</span></div></div>
</div></div>
<div class="app-phones"><div class="phone"><img src="shots4/app_inicio.png" alt=""></div><div class="phone b"><img src="shots4/app_pix.png" alt=""></div></div></div>''')
raw('''<div class="eye">Avisos automáticos</div><h2>Ninguém <em>esquece</em> nada</h2>
<table class="tt">
<tr><th>Quando</th><th>Quem recebe</th><th>Como chega</th></tr>
<tr><td>Cadastro novo e acesso liberado</td><td class="who">Dra. Thalia / dentista</td><td>E-mail e notificação.</td></tr>
<tr><td>Reserva feita e 2 horas antes</td><td class="who">Dentista e Dra. Thalia</td><td>Confirmação por e-mail e lembrete por e-mail e notificação.</td></tr>
<tr><td>Cancelamento e vaga aberta</td><td class="who">Dra. Thalia, dentista e lista de espera</td><td>E-mail e notificação; quem esperava o horário é avisado.</td></tr>
<tr><td>Plano mensal</td><td class="who">Dra. Thalia e dentista</td><td>Pedido, aprovação, dia liberado como crédito, crédito usado e encerramento.</td></tr>
<tr><td>Termos de uso atualizados</td><td class="who">Dentistas</td><td>Notificação; o novo aceite é pedido no próximo acesso.</td></tr>
<tr><td>Pagamentos</td><td class="who">Dra. Thalia e dentista</td><td>Comprovante enviado, pagamento confirmado e lembrete a cada 3 dias.</td></tr>
<tr><td>Mural e problemas</td><td class="who">Dentistas / Dra. Thalia</td><td>Notificação de aviso novo; e-mail e notificação de problema relatado.</td></tr>
<tr><td>Dia 1º do mês</td><td class="who">Dra. Thalia</td><td>Relatório do mês anterior e lembrete de backup.</td></tr>
</table>
<div class="note"><b>Tudo automático e sem custo:</b> e-mails e notificações saem sozinhos. No WhatsApp, as mensagens (confirmação, lembrete de consulta, parabéns) abrem prontas e são enviadas com um toque; o envio automático exigiria a API paga da Meta.</div>''')
raw('''<div class="eye">Custos e segurança</div><h2>Operação <em>sem mensalidade</em></h2>
<div class="cost">
<div><b>Hospedagem</b><div class="p">R$ 0</div><span>Vercel, plano gratuito. Alternativa gratuita para uso comercial: Cloudflare Pages.</span></div>
<div><b>Banco e login</b><div class="p">R$ 0</div><span>Supabase gratuito, com cerca de 1 GB para documentos dos pacientes.</span></div>
<div><b>E-mails</b><div class="p">R$ 0</div><span>Brevo gratuito, até 300 e-mails por dia.</span></div>
<div><b>Notificações</b><div class="p">R$ 0</div><span>Pelo app instalado, dentro do plano gratuito do Supabase.</span></div>
<div><b>Pix e PDFs</b><div class="p">R$ 0</div><span>QR Code do Banco Central, recibos, receitas e atestados gerados no próprio site.</span></div>
</div>
<div class="sec3">
<div><h3>Segurança</h3><ul class="f">
<li><span>Só reserva quem a Dra. Thalia liberou e aceitou a versão atual dos termos.</span></li>
<li><span>Cada dentista vê só as próprias reservas, planos, avisos e comprovantes.</span></li>
<li><span>Pacientes, documentos e financeiro dos pacientes: só administrador completo (LGPD).</span></li>
<li><span>Visitantes veem apenas quais horários estão ocupados, nunca nomes ou telefones.</span></li></ul></div>
<div><h3>Próximos passos</h3><ol class="nx">
<li>Rodar a atualização do banco e subir os arquivos do site.</li>
<li>Cadastrar o CRO, revisar os termos e liberar a calculadora.</li>
<li>Enviar as fotos e a lista de equipamentos.</li>
<li>Instalar o app, ativar as notificações e conectar o Google Agenda.</li>
<li>Imprimir o cartaz e enviar o manual aos dentistas parceiros.</li></ol></div>
</div>''')

body = []
for i, h in enumerate(pages):
    body.append(f'<section class="pg">\n{h}\n{FOOT.format(n=i + 2)}\n</section>')
cover = '''<section class="pg cover">
<div class="l"><img src="logo-dourado.webp" alt="">
<h1>Site de reservas do <em>consultório</em></h1>
<p>Aluguel por hora, período ou plano mensal para outros dentistas, com agenda ao vivo, termos de uso, app no celular, Pix integrado, calculadora clínica e um painel completo para a Dra. Thalia e a equipe, inclusive para os pacientes dela.</p>
<div class="meta">Apresentação das funcionalidades · Versão completa · Outubro de 2026</div></div>
<div class="r"><div class="arc"></div><div class="shot s1"><img src="shots4/home.png" alt=""></div><div class="shot s2"><img src="shots4/mob_home.png" alt=""></div></div>
</section>'''
end = '''<section class="pg end"><img src="logo-dourado.webp" alt="">
<h2>Pronto para <em>receber reservas</em></h2>
<p>dra-thalia-santiago.vercel.app</p>
<div class="c"><span>Rua Juiz de Fora, 52, Galeria Êxito, sala 208 · Centro · Ipatinga/MG</span><span>(31) 99574-5413</span><span>@dra.thaliasantiago</span></div>
</section>'''
open(D + 'doc4.html', 'w').write(head + '</style></head><body>\n' + cover + '\n' + '\n'.join(body) + '\n' + end + '\n</body></html>')
print(len(pages) + 2, 'páginas')
