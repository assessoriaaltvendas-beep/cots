# Consultório Thalia Santiago · site de reservas

Site de aluguel por hora do consultório, com área do dentista e painel da administradora.

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
insert into public.admins (user_id) select id from auth.users where email = 'EMAIL_DA_THALIA@exemplo.com';
```

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
1. Abra o site e entre em **Administrador** com o e-mail e a senha da Dra. Thalia.
2. Numa janela anônima, crie uma conta em **Área do dentista** e faça uma reserva.
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

## Fotos e perguntas frequentes
No painel, aba **Site**: envie fotos do consultório (aparecem na galeria da página inicial) e escreva as perguntas frequentes.

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
