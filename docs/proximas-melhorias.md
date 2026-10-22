# Melhorias do site de reservas

## 📋 Próximo patch (acumulando)
Quando a usuária disser **"Vamos subir o patch note"**: implementar tudo desta lista de uma vez, testar, entregar e passar o passo a passo de publicação (SQL no Supabase → GitHub → Vercel).

Base atual: **v9** (21/10/2026).

### Pedidos anotados
(nenhum pendente)

### Lembretes
- Manual do dentista (11 páginas, A4 retrato), cartaz A4 e apresentação (24 páginas, paisagem e retrato): regerados em 21/10 com a v9. Fontes em `ferramentas/materiais/`. Se mudar preço, prazo, contato ou tela, regerar.
- Receitas/atestados: o CRO da Dra. Thalia precisa ser cadastrado em Ajustes → Receitas e atestados (ainda não informado).
- Calculadora: começa oculta para os dentistas; a Dra. precisa revisar e tocar em "Revisei, liberar" (o cartaz já cita a calculadora).

### Ideias para depois (sugerir quando fizer sentido; só implementar com aprovação)
- Assinatura digital automática de receita/atestado (certificado ICP-Brasil A1 importado no aparelho, PAdES no navegador). Aguardando a Dra. decidir o tipo de certificado (A1, nuvem ou token).
- Calculadora: mais itens (ex.: dexametasona, nimesulida, cefalexina para tratamento), sempre conferidos na bula.
- Mensagens de push/e-mail ainda dizem "a Dra. Thalia cancelou/confirmou" mesmo quando outro administrador fez a ação; trocar por texto neutro.
- Taxa automática por falta (hoje a falta é só registrada; a reserva já fica cobrada).
- Envio da receita/atestado direto pelo WhatsApp.
- Versão do manual otimizada para celular (páginas estreitas, letra maior).

## Histórico
### v9 (21/10/2026)
- Login único ("Entrar"); admin vai para o painel, dentista para a área dele.
- Administradores em Ajustes → Administradores, com dois níveis (completo e agenda), histórico e trava no banco (RLS e funções). Atalho Painel ↔ Minha área de dentista. Nome do admin editável em Ajustes → Conta.
- Calculadora no painel e na área do dentista (doses por peso/idade, anestésico em tubetes, profilaxia AHA 2021, conversões), com fonte por item, liberação pela Dra. e histórico.

### v8
- Lembrete no WhatsApp nas listas de consultas; aniversariantes; receita e atestado em PDF; financeiro dos pacientes; backup .xlsx com lembrete; relatório de ocupação; seção "Estrutura e valores"; taxa por cancelamento fora do prazo e falta.

### v7
- Prazo de 4 horas; termos de uso com registro (`docs/termos-de-uso.md` = versão 1); logos novas; planos mensais (R$ 1.000 / R$ 600, crédito com 3 dias de aviso).

### v6
- Contato atualizado, "Lembrar de mim", editar/excluir dentista, preços por período, módulo de pacientes, manual e cartaz.

### v5
- Mobile mais limpo; ajustes pelo painel; Pix; lembrete de pagamento; recibo do mês; relatório mensal; Google Agenda; liberação de cadastros.

## Para depois
- Migrar a hospedagem para o Cloudflare Pages (uso comercial gratuito).
- Publicar o app na Play Store (taxa única de cerca de US$ 25).
- Domínio próprio (passo a passo no README).
