# Consultório Thalia Santiago · site de reservas

Site de aluguel por hora do consultório, com área do dentista e painel da administradora.

- `index.html`: o site inteiro
- `config.js`: onde entram os dados do Supabase (passo 6)
- `assets/`: logos e ícone
- `supabase/schema.sql`: banco de dados e regras de segurança (passo 4)

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

## Fotos e perguntas frequentes
No painel, aba **Site**: envie fotos do consultório (aparecem na galeria da página inicial) e escreva as perguntas frequentes.

## Como mudar algo depois
- **Textos, regras de uso, checklist, valor da hora, preços por dia ou horário (`precos`), chave Pix, pacotes, Instagram, informações do espaço:** ficam no começo do código dentro de `index.html`, no bloco `const CFG = { ... }`. Edite pelo GitHub (lápis) e a Vercel publica sozinha em 1 minuto.
- **Horário de funcionamento, dias abertos e prazo de cancelamento:** mude no `CFG` do `index.html` **e também** no começo do `supabase/schema.sql` (funções `cfg_abre`, `cfg_fecha`, `cfg_dias`, `cfg_prazo_cancelamento`). Depois rode o `schema.sql` de novo no SQL Editor.

## Segurança
- Cada dentista vê somente as próprias reservas, avisos e lista de espera.
- Visitantes sem conta só veem quais horários estão ocupados, nunca nomes ou telefones.
- Duas pessoas não conseguem reservar a mesma hora: o banco recusa a segunda reserva.
- Dentistas não conseguem marcar reservas como pagas nem cancelar depois do prazo; só a administradora.
