# Consultório Thalia Santiago · site de reservas

Site de aluguel por hora do consultório, com área do dentista, painel da administração e calculadora clínica (só para o administrador completo).

- `index.html`: o site inteiro
- `config.js`: onde entram os dados do Supabase (passo 6)
- `assets/`: logos e ícone
- `supabase/schema.sql`: banco de dados e regras de segurança (passo 4)
- `supabase/functions/push/index.ts`: função que entrega as notificações no celular
- `sw.js` e `manifest.webmanifest`: fazem o site funcionar como app

O site roda na **Vercel** (hospedagem) e usa o **Supabase** (banco de dados e login). Os dois têm plano gratuito.

---

## Passo a passo para colocar no ar

### 1. Criar a conta no GitHub
1. Acesse **github.com/signup** e crie sua conta.
2. No canto superior direito, clique em **+ → New repository**.
3. Nome: `consultorio-thalia`. Pode deixar **Private**. Clique em **Create repository**.
4. Na página do repositório, clique em **uploading an existing file**.
5. Arraste **todo o conteúdo** desta pasta (os arquivos `index.html`, `config.js`, `README.md` e as pastas `assets` e `supabase`). Clique em **Commit changes**.

### 2. Criar o projeto no Supabase
1. Acesse **supabase.com** e entre com sua conta do GitHub.
2. Clique em **New project**. Nome: `consultorio-thalia`. Crie uma senha forte para o banco e guarde. Região: **South America (São Paulo)**.
3. Aguarde o projeto ficar pronto (1 a 2 minutos).

### 3. Ajustar o login por e-mail
O servidor de e-mail que vem com o Supabase só envia **2 e-mails por hora**. Por isso:
1. Vá em **Authentication → Sign In / Providers → Email**.
2. Desligue **Confirm email** e salve. Assim, o dentista entra logo depois de criar a conta, sem precisar confirmar o e-mail.

> Mais tarde, para a recuperação de senha funcionar bem com muitos dentistas, configure um envio de e-mail próprio (Brevo ou Resend têm plano grátis) em **Authentication → Emails → SMTP Settings**.

### 4. Criar o banco de dados
1. Em **Database → Extensions**, procure e ative **pg_net** e **pg_cron** (usadas pelos e-mails automáticos).
2. No menu lateral, abra **SQL Editor → New query**.
3. Abra o arquivo `supabase/schema.sql`, copie **tudo**, cole no editor e clique em **Run**.
4. Deve aparecer "Success". Se rodar de novo, não tem problema.

### 5. Criar o acesso da Dra. Thalia (administradora)
1. Vá em **Authentication → Users → Add user → Create new user**.
2. Coloque o e-mail e a senha da Dra. Thalia e marque **Auto Confirm User**. Clique em **Create user**.
3. Volte ao **SQL Editor → New query**, cole a linha abaixo trocando o e-mail e clique em **Run**:

```sql
insert into public.admins (user_id, nivel, nome) select id, 'completo', 'Dra. Thalia Santiago' from auth.users where email = 'EMAIL_DA_THALIA@exemplo.com';
```

Isso só é feito uma vez. Os outros administradores a Dra. Thalia adiciona pelo próprio painel (veja **Administradores**, abaixo).

### 6. Ligar o site ao Supabase
1. No Supabase, vá em **Project Settings → API Keys**. Copie a **Publishable key** (começa com `sb_publishable_`). Se o projeto mostrar a chave antiga **anon public**, ela também funciona.
2. Em **Project Settings → Data API** (ou na página inicial do projeto), copie o **Project URL** (algo como `https://abcdefgh.supabase.co`).
3. No GitHub, abra o arquivo `config.js`, clique no lápis (**Edit**), cole os dois valores no lugar de `COLE_AQUI...` e clique em **Commit changes**.

> Nunca use a chave **secret** ou **service_role** no `config.js`.

### 7. Publicar na Vercel
1. Acesse **vercel.com/signup** e entre com sua conta do GitHub.
2. Clique em **Add New → Project** e escolha o repositório `consultorio-thalia` (**Import**).
3. Em **Framework Preset**, deixe **Other**. Clique em **Deploy**.
4. Em cerca de 1 minuto o site fica no ar, num endereço como `consultorio-thalia.vercel.app`.
5. Para trocar o nome do endereço: **Settings → Domains → Edit** (por exemplo, `thalia-santiago.vercel.app`, se estiver livre).

### 8. Informar ao Supabase o endereço do site
1. No Supabase, vá em **Authentication → URL Configuration**.
2. Em **Site URL**, coloque o endereço do site (ex.: `https://thalia-santiago.vercel.app`).
3. Em **Redirect URLs**, clique em **Add URL** e coloque o mesmo endereço com `/**` no final (ex.: `https://thalia-santiago.vercel.app/**`). Salve.

Sem este passo, os links de recuperação de senha não voltam para o site.

### 9. Testar
1. Abra o site, toque em **Entrar** e use o e-mail e a senha da Dra. Thalia: ela vai direto para o painel.
2. Numa janela anônima, toque em **Entrar → Criar conta**, crie uma conta de dentista e faça uma reserva.
3. Confira se a reserva aparece no painel da Dra. Thalia.

---

## E-mails automáticos (grátis)
Confirmação de reserva, lembrete 2 horas antes, aviso de vaga aberta e avisos para a Dra. Thalia.
1. Crie uma conta grátis em **brevo.com** (até 300 e-mails por dia).
2. No Brevo, cadastre e confirme o e-mail remetente (Remetentes / Senders) e gere uma chave de API (SMTP e API → Chaves de API).
3. No painel do site, vá em **Ajustes → E-mails automáticos**, preencha os campos, cole a chave e toque em **Salvar**. Depois, **Enviar e-mail de teste**.

## App no celular e notificações (grátis)
O site funciona como um app: no celular, abra o site e instale pelo navegador (Android: menu ⋮ → Instalar app; iPhone: Safari → Compartilhar → Adicionar à Tela de Início). Pelo ícone, ele abre direto na área de quem já entrou.

Para ligar as notificações (uma vez só):
1. No Supabase, abra **Edge Functions → Deploy a new function → Via Editor**. Nome: `push`. Apague o exemplo, cole o conteúdo de `supabase/functions/push/index.ts` e clique em **Deploy**.
2. Na função `push`, em **Details**, desligue **Enforce JWT verification** e salve.
3. No painel do site, vá em **Ajustes → App no celular → Configuração das notificações** e toque em **Verificar e ativar**.
4. Cada pessoa toca em **Ativar** (no Início ou no Perfil) no celular dela. No iPhone, precisa estar com o app instalado.

Avisos enviados: lembrete 2 horas antes, vaga aberta, reserva feita ou cancelada pela Dra. Thalia, pagamento confirmado e avisos do mural (dentistas); nova reserva, cancelamento, comprovante e problema relatado (Dra. Thalia).

## Liberação de cadastros
Quem cria conta na Área do dentista fica **aguardando liberação** e não consegue reservar.
A Dra. Thalia recebe notificação e e-mail a cada cadastro novo e, no painel (Resumo ou aba **Dentistas**), toca em **Liberar** ou **Bloquear**.
Quando a conta é liberada, o dentista recebe um e-mail. Reservar exige conta liberada; a página inicial continua mostrando os horários livres.

## Ajustes pelo painel (sem mexer em código)
No painel, aba **Ajustes**:
- **Valores:** valor da hora, preço por dia da semana, preço por faixa de horário e pacotes de horas. Cada reserva guarda o valor de quando foi feita; dá para ajustar uma reserva específica nos detalhes dela.
- **Funcionamento:** dias abertos, horário de abrir e fechar, prazo de cancelamento.
- **Datas fechadas:** feriados, férias e manutenção.
- **Pagamentos e Pix:** chave Pix (gera QR Code e Pix copia e cola com o valor de cada reserva), lembrete automático de pagamento e bloqueio de novas reservas para quem está com pagamento atrasado.
- **Regras, checklist e espaço:** textos que aparecem para os dentistas.
- **Relatório mensal e Google Agenda:** resumo do mês por e-mail todo dia 1º e link para ver as reservas no Google Agenda.

O recibo do mês em PDF fica em Financeiro (dentista) e nos detalhes de cada dentista (painel).

## Entrar e administradores
- O site tem um só botão **Entrar**. Depois do login, quem é administrador vai para o painel; quem é dentista vai para a área do dentista.
- Em **Ajustes → Administradores**, a Dra. Thalia adiciona administradores pelo e-mail de uma conta que já existe no site (normalmente um dentista), muda o nível ou remove. Ninguém muda o próprio acesso, e sempre fica pelo menos um administrador completo. Cada alteração fica no histórico (quem fez e quando).
- **Administrador completo:** vê e altera tudo, inclusive pacientes, documentos, receitas, financeiro dos pacientes e a lista de administradores.
- **Administrador da agenda:** cuida de dentistas, reservas, agenda, planos, cobranças, mural e site. Não vê pacientes: as consultas aparecem só como "Ocupado". O backup dele sai sem as planilhas de pacientes. Essa trava também está no banco de dados, não só na tela.
- Quem é administrador e também dentista tem o atalho **Minha área de dentista** no painel (e **Painel da administração** na área do dentista).
- As notificações do painel (cadastro novo, pedido de plano, reserva, problema) chegam para todos os administradores. Os e-mails continuam indo para o e-mail de Ajustes → E-mails.
- Em **Ajustes → Conta**, cada administrador pode mudar o nome que aparece no painel.

## Calculadora
Aba **Calculadora** no painel, **só para o administrador completo** (dentistas e administradores da agenda não veem a aba, e o banco recusa o acesso):
- **Medicamentos:** dose por peso e idade (dipirona, paracetamol, ibuprofeno, amoxicilina, azitromicina), em mg, mL e gotas, com intervalo e máximo por dia.
- **Anestésico:** dose máxima em mg e em tubetes (lidocaína, mepivacaína, articaína, prilocaína, bupivacaína), com o limite de epinefrina para cardiopatas.
- **Profilaxia** de endocardite (esquema da AHA 2021) e **Conversões** (mg → mL/gotas e diluição, como a do hipoclorito).
- Cada item mostra a fonte (bula ou referência) e a data da conferência. Sem peso e idade, abaixo da idade/peso da bula ou fora da tabela, a calculadora não mostra número.
- A Dra. Thalia pode editar, desativar ou incluir itens; tudo fica no histórico.
- É uma ferramenta de apoio: a decisão e a prescrição são do profissional.

## Uso no dia a dia (v10)
- **Avisos:** confirmações aparecem num aviso rápido na parte de baixo da tela.
- **Desfazer:** depois de cancelar uma reserva ou excluir algo, aparece **Desfazer** por 5 segundos. Se tocar, nada é gravado.
- **Sem internet:** uma faixa vermelha avisa no topo; quando a conexão volta, os dados são atualizados.
- **App no celular:** puxe a tela para baixo (no topo) para atualizar. No Android, o celular vibra de leve ao confirmar uma reserva.
- **Entrar:** o site lembra o último e-mail usado neste aparelho.
- Quem prefere menos movimento (opção de acessibilidade do celular ou computador) vê o site sem animações.

## Pacientes da Dra. Thalia
No painel, aba **Pacientes** (só administrador completo vê):
- **Cadastro** do paciente: nome, telefone, CPF, nascimento, e-mail, endereço e observações de saúde.
- **Consultas** de 15 em 15 minutos. O horário fica ocupado na agenda dos dentistas (sem nenhum dado do paciente). Botões de lembrete no WhatsApp, realizada, faltou, remarcar e cancelar.
- **Evolução:** o que foi feito em cada consulta, com data.
- **Documentos:** prontuário, orçamento, radiografias e outros arquivos (foto ou PDF), num armazenamento privado. O plano gratuito do Supabase guarda cerca de 1 GB; fotos grandes são reduzidas automaticamente.
- As consultas aparecem na Agenda (em verde) e em "Pacientes de hoje", no Resumo.

- **Lembrete no WhatsApp:** em cada consulta agendada (na ficha, em "Consultas de hoje" e "Próximas consultas"), o ícone verde abre o WhatsApp do paciente com dia, hora e endereço.
- **Aniversariantes:** no Resumo e na aba Pacientes, quem faz aniversário na semana, com botão para mandar parabéns.
- **Receita e atestado em PDF** com a logo, direto da ficha (botões Receita e Atestado). O PDF é baixado e fica salvo nos documentos do paciente. Nome e CRO da assinatura em Ajustes → Receitas e atestados.
- **Financeiro do paciente:** orçamentos (em aberto, aprovado, recusado), parcelas com vencimento, pagamentos recebidos e recibo em PDF. O total a receber aparece na aba Pacientes e no Financeiro do painel.

Dados de saúde são sensíveis (LGPD): só dê o nível **administrador completo** para quem pode ver dados de pacientes. Para o prontuário digital substituir o papel com validade legal, confira as regras do CRO (normalmente exigem assinatura com certificado digital).

## Termos de uso
No cadastro, o dentista lê os **termos e condições de uso** numa caixa com rolagem: o aceite só libera depois de rolar até o final, e a conta só é criada com o aceite marcado. Dentistas que já tinham conta aceitam no próximo acesso.
- A Dra. Thalia edita o texto em **Ajustes → Termos de uso**. Cada publicação vira uma nova versão, com data e resumo; o histórico mostra o que mudou (trecho removido riscado, trecho novo destacado).
- Com uma versão nova, todos os dentistas leem e aceitam de novo no próximo acesso, vendo o que mudou. Sem o aceite, não conseguem reservar.
- O painel mostra quem aceitou cada versão e quando (aba Dentistas, nos detalhes de cada um). Os termos ficam também no rodapé do site e no Perfil do dentista.

## Planos mensais
Plano 1x por semana, no mesmo dia e período: **diária R$ 1.000/mês** e **meio período R$ 600/mês** (valores em Ajustes → Planos mensais). O valor do mês é o mesmo com 4 ou 5 semanas; no primeiro mês, cobra só as semanas a partir do início.
- O dentista pede o plano na aba **Reservar**; a Dra. Thalia aprova no Resumo ou na aba Dentistas (ou cria um plano direto, já ativo, em Dentistas → Novo plano).
- O site reserva sozinho as semanas do mês atual e do próximo, e renova todo mês (rotina diária). Datas já ocupadas ficam de fora e a Dra. Thalia é avisada.
- Não vai poder ir num dia? Avisando pela área do dentista com **3 dias** de antecedência (ajustável), o dia vira **crédito** para remarcar outro dia do mesmo mês. Com menos de 3 dias, o dia é perdido. O valor do mês não muda.
- Encerrar o plano: vale até o fim do mês atual; as reservas dos meses seguintes são canceladas.

## Prazo de cancelamento
Cancelar ou remarcar pelo site: até **4 horas** antes do início, com direito a reembolso (Ajustes → Funcionamento).

## Preços
Em Ajustes → Valores: valor da hora (até o limite de horas avulsas), períodos (manhã, tarde, noite) e diária. Acima do limite, o dentista reserva um período ou a diária; intervalos que cruzam períodos aparecem com o botão "Falar com a Dra. Thalia".

## Faltas e cancelamento fora do prazo
Na reserva (Agenda → toque na reserva): **Cancelar com taxa** libera o horário e deixa cobrada a taxa (padrão em Ajustes → Faltas e cancelamento fora do prazo: 100%, 75%, 50% ou 25% do valor). A taxa aparece no Financeiro do dentista, no Pix do mês e no recibo. **O dentista faltou** registra a falta (a reserva continua cobrada).

## Backup
Em Ajustes → Backup: uma planilha do Excel (abre no Google Planilhas) com reservas, dentistas, planos, pacientes, consultas, evoluções, orçamentos, pagamentos, documentos, problemas e aceites dos termos. Todo dia 1º chega um lembrete. Os arquivos anexados ficam no Supabase (Storage). Guarde a planilha em local seguro: ela tem dados de saúde.

## Relatório de ocupação
No Financeiro do painel: mapa de ocupação por dia da semana e horário (últimas 4, 8 ou 12 semanas, ou próximas 4), com os horários mais procurados e os mais vazios, bons para promoção.

## Fotos e perguntas frequentes
No painel, aba **Site**: envie fotos do consultório (aparecem na galeria da página inicial) e escreva as perguntas frequentes. Os equipamentos e o que está incluso no aluguel (Ajustes → Regras, checklist e espaço) aparecem na página inicial, na seção Estrutura e valores, junto com os preços.

## Domínio próprio (opcional)
1. Compre o domínio em **registro.br** (um .com.br custa em torno de R$ 40 por ano).
2. Na Vercel, abra o projeto → **Settings → Domains → Add** e digite o domínio (ex.: `consultoriothalia.com.br`). Adicione também a versão com `www`.
3. A Vercel mostra os registros de DNS a criar. No registro.br, abra o domínio → **DNS** → **Editar zona** e crie exatamente os registros que a Vercel mostrar (normalmente um registro **A** para o domínio e um **CNAME** para o `www`). Em algumas horas o site abre no novo endereço.
4. No Supabase, em **Authentication → URL Configuration**, troque o **Site URL** e o **Redirect URL** para o novo endereço.
5. No painel do site, em **Ajustes → E-mails automáticos**, toque em **Salvar** de novo (assim os links dos e-mails usam o novo endereço).
6. Me peça para trocar o endereço da prévia de link (`og:url` e `og:image` no começo do `index.html`).

## Como mudar algo depois
- **Valores, horários, Pix, regras e checklist:** pelo painel, em Ajustes (veja acima).
- **Textos fixos do site, endereço, telefone e Instagram:** no começo do `index.html`, no bloco `const CFG = { ... }`. Edite pelo GitHub (lápis) e a Vercel publica sozinha em 1 minuto.

## Segurança
- Cada dentista vê somente as próprias reservas, avisos e lista de espera.
- Visitantes sem conta só veem quais horários estão ocupados, nunca nomes ou telefones.
- Duas pessoas não conseguem reservar a mesma hora: o banco recusa a segunda reserva.
- Dentistas não conseguem marcar reservas como pagas, mudar o valor, nem cancelar depois do prazo; só a administradora.
- Contas novas só reservam depois de liberadas pela administradora; o dentista não consegue se liberar sozinho.
- Dados de pacientes (cadastro, consultas, evolução, documentos e financeiro) só são entregues pelo banco ao administrador completo.
