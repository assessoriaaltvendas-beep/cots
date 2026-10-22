# Consultório Odontológico Thalia Santiago (COTS): site de reservas

Memória do projeto para o Claude Code. Leia este arquivo inteiro antes de mexer em qualquer coisa.

## Com quem você fala
- A usuária é da assessoria que cuida do site (não é programadora). Fale sempre em **português do Brasil**, simples e direto, com passo a passo detalhado quando ela precisar clicar em algo (Supabase, GitHub, Vercel).
- Tudo precisa ser **gratuito** (planos free).
- Cliente: Dra. Thalia Santiago, que aluga o consultório por hora para outros dentistas.
  - Site: https://dra-thalia-santiago.vercel.app
  - WhatsApp (31) 99574-5413 (5531995745413) · Instagram @dra.thaliasantiago
  - Rua Juiz de Fora, 52, Galeria Êxito, sala 208, Centro, Ipatinga/MG

## Jeito de trabalhar (combinado com a usuária)
- Ela manda pedidos aos poucos. Você **anota** em `docs/proximas-melhorias.md` (seção "Pedidos anotados") e sugere melhorias, sem implementar.
- Quando ela disser **"Vamos subir o patch note"**: implementar tudo da lista, testar (banco e navegador), atualizar README/manual/apresentação se a tela mudou, mover os itens para o "Histórico" e passar o passo a passo de publicação.
- Só implemente "Ideias para depois" com aprovação dela.

## Divisão com o Claude do chat (claude.ai)
A usuária trabalha com os dois:
- **Aqui (Claude Code):** mudanças no site e no banco, patch notes, testes e publicação. Novos clientes também começam aqui, cada um no seu repositório.
- **No chat do Claude (projeto "Calendario de Agendamento"):** manual, cartaz, apresentação, textos para a Dra., dúvidas e planejamento. Ele lê este repositório para pegar a versão atual.
- **A fonte da verdade é este repositório.** Pedidos anotados no chat também entram em `docs/proximas-melhorias.md`. Ao terminar um patch, atualize o histórico desse arquivo e diga à usuária se a tela mudou (aí o manual e a apresentação precisam ser refeitos no chat).
- Antes de enviar para o GitHub, mostre à usuária um resumo do que vai mudar e espere o "pode subir".

## Regras que não podem ser quebradas
- **Nunca** coloque a chave `service_role`/secret em lugar nenhum do site. O `config.js` leva só a URL do Supabase e a chave pública (anon/publishable).
- **Nunca sobrescreva o `config.js`** real do repositório (ele tem as chaves dela). Pacotes de atualização vão sem `config.js`.
- Dados de pacientes são sensíveis (LGPD): bucket privado, tabelas só para **administrador completo** (RLS + funções), nunca em logs, e-mails ou notificações.
- Não misture dados de empresas diferentes no mesmo Supabase. Outras empresas usam a habilidade/kit `novo-site-agendamento` com contas próprias.
- PDFs gerados por HTML: **sem `box-shadow`** (o leitor do iPhone desenha tarjas escuras). Use borda ou outline.
- Calculadora: valores só de **bula ou referência oficial**, com fonte e data no item. Sem peso/idade ou fora da faixa da bula, não mostrar número. Nada de dose "de cabeça".

## Estrutura do repositório
- `consultorio-thalia/` é o que a Vercel publica:
  - `index.html`: o site inteiro (HTML+CSS+JS puro, ~550 KB). Estado global `S`, dados da empresa em `CFG`, `route()`/`render()`, gavetas com `openForm(titulo, () => elemento)`. Painel: abas em `TABS`; área do dentista: `CTABS`.
  - `config.js`: URL e chave pública do Supabase (não mexer).
  - `supabase/schema.sql`: banco inteiro, **idempotente** (rodar de novo não estraga). Cada versão é um bloco no fim ("-- vN ..."), antes da seção "Arquivos: fotos do consultório".
  - `supabase/functions/push/index.ts`: função Edge `push` (Web Push com VAPID e agenda .ics). Precisa de "Enforce JWT verification" desligado.
  - `sw.js` (cache `thalia-v5`; aumente a versão a cada publicação), `manifest.webmanifest`, `assets/`, `README.md` (guia da usuária).
- `docs/`: `proximas-melhorias.md` (lista de pedidos e histórico) e `termos-de-uso.md` (texto da versão 1 dos termos).
- `ferramentas/`: testes e geradores dos PDFs (não vão para o site).

## Como o sistema funciona (resumo)
- Supabase: Postgres com RLS e funções `security definer` (`is_admin()`, `is_admin_completo()`, `meu_acesso()`, `reservar`, `cancelar`, planos, termos, calculadora…), pg_cron (`rotina_diaria`), pg_net + Brevo (e-mails), Vault (`brevo_api_key`, `vapid_privada`), Storage (`fotos` público, `comprovantes` e `pacientes` privados), Realtime.
- Ajustes especiais no banco: `app.bypass` (migrações), `app.silencioso` (sem avisos). O Supabase tem `pg-safeupdate`: DELETE precisa de WHERE.
- Preços: R$ 50/h até 3h; períodos 8–13, 13–18 e 18–22 a R$ 180; diária 8–18 R$ 350; dia todo R$ 530; mais de 3h cruzando períodos = falar com a Dra. Planos mensais: diária R$ 1.000/mês, meio período R$ 600/mês (valor fixo mesmo com 5 semanas), crédito avisando com 3 dias. Cancelar/remarcar pelo site até 4h antes, com reembolso.
- Status de reserva: `ativo`, `cancelado`, `credito` (dia de plano liberado), `taxa` (cancelada com taxa); falta registrada em `falta`.
- Termos de uso: aceite obrigatório no cadastro (rolagem até o fim), novas versões pedem novo aceite.
- Login único (v9): um botão "Entrar"; quem é admin vai para `#admin`, dentista para `#dentista`. Níveis de admin: `completo` e `agenda`.
- Notificações do painel vão para todos os admins; e-mails para o "e-mail da administradora" em Ajustes → E-mails.

## Testes (rode antes de entregar qualquer mudança)
### Banco (Postgres 16 local simulando o Supabase)
```bash
sudo pg_ctlcluster 16 main start        # se o Postgres estiver parado
cd ferramentas/testes-banco
bash rodar.sh t9 ../../consultorio-thalia/supabase/schema.sql pre9.sql test9.sql   # instalação + testes v9
bash rodar.sh f9 ../../consultorio-thalia/supabase/schema.sql ../../consultorio-thalia/supabase/schema.sql   # rodar 2x sem erro
```
`stub*.sql` simulam `auth`, `storage`, `vault`, `net`. Compare a saída do test9 com `out9.txt`. Teste sempre: instalação do zero, rodar o schema duas vezes e permissões (admin completo, admin da agenda, dentista, visitante).

### Navegador (Playwright + Chromium, supabase-js simulado)
```bash
cd consultorio-thalia && python3 -m http.server 8765 &
cd ferramentas/testes-navegador && python3 e2e9.py     # deve terminar com "FALHAS: 0" e "erros JS: []"
```
- `mock-supabase.js` simula o supabase-js (tabelas, RLS, RPCs). Se criar tabela ou função nova, implemente no mock também.
- Os `r9_e2e*.py` são testes de regressão das versões anteriores.
- **Os scripts têm caminhos absolutos da sessão antiga** (`/tmp/claude-0/.../scratchpad/...`). Ajuste a variável `S`/`O` no topo de cada script para as pastas daqui antes de rodar. Eles leem o mock como `mock9r.js` (= `mock-supabase.js` com `window.MOCK_TERMOS_OK=1;` na primeira linha).
- Teste sempre no celular (390 px) e no computador, sem rolagem lateral.

## Materiais (PDF)
- `ferramentas/materiais/manual/`: `manual.html` (Manual do Dentista, A4 retrato, 11 páginas) e `cartaz.html` (A4 com QR). `shoot.py`/`shoot_calc.py` tiram as telas (390×844 @2x) para `shots/`; `build.py` gera os PDFs (`mk.py` usa `page.pdf` do Playwright).
- `ferramentas/materiais/apresentacao/`: `shoot4.py` tira as telas, `mk_doc4.py` monta o HTML (base de estilos em `doc2.html`), `mk4.py` gera em paisagem e `mk5.py` em retrato (aplica `portrait.css` ao HTML gerado).
- Mesma observação dos caminhos absolutos. Depois de gerar, confira as páginas em imagem (`pdftoppm`) e os QR Codes.

## Publicação (passo a passo para a usuária)
1. Se o `schema.sql` mudou: Supabase → **SQL Editor → New query**, colar o arquivo inteiro → **Run**. Sempre antes dos arquivos.
2. GitHub: commit/push das mudanças em `consultorio-thalia/` (sem tocar no `config.js`). Se ela for subir pelo site do GitHub: **Add file → Upload files**, arrastando o que está **dentro** da pasta (senão cria pasta duplicada).
3. Vercel publica sozinha. Se não publicar: Deployments → Create Deployment → `main` (e "Promote to Production" se ficar como Preview). Site antigo na tela = cache: aba anônima.
- Aviso "Run and enable RLS" no Supabase: clicar no botão verde.

## Contas e limites gratuitos
- Supabase free: limite de projetos ativos por conta. Vercel free não é para uso comercial (alternativa grátis: Cloudflare Pages). Brevo: 300 e-mails/dia.
- Supabase project ref: `jnhinkneolzacfdbivyw`. Repositório: `assessoriaaltvendas-beep/cots`.
