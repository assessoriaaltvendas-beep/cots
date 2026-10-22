\set ON_ERROR_STOP 0
\pset pager off
\pset format unaligned
\set L '11111111-1111-1111-1111-111111111111'
\set A '99999999-9999-9999-9999-999999999999'
select (current_date + 10)::date as d10 \gset
select (current_date + 11)::date as d11 \gset
select set_config('app.bypass','on',false);
update public.dentists set termos_versao = (select max(versao) from public.termos_versoes);
select set_config('app.bypass','',false);
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select public.reservar('Lucas','','(31) 98841-5460', (select d::date from generate_series(current_date + 10, current_date + 16, '1 day') d where extract(dow from d) between 1 and 6 limit 1), 9, 11) as b1 \gset
select 'X0 dentista taxa', public.cancelar_com_taxa(:'b1', 100);
select 'X0 dentista falta', public.marcar_falta(:'b1', true);
update public.bookings set falta = true where id = :'b1';
reset role;
select 'X0 protegido', falta from public.bookings where id = :'b1';
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'X1 taxa 50', public.cancelar_com_taxa(:'b1', 50);
select 'X1 estado', status, valor, valor_original, (select count(*) from public.slots where booking_id = :'b1') from public.bookings where id = :'b1';
select 'X1 de novo', public.cancelar_com_taxa(:'b1', 50);
select 'X2 falta', public.marcar_falta(:'b1', true);
select 'X2 estado', falta from public.bookings where id = :'b1';
select 'X3 cfg', public.salvar_cfg_v8('{"taxaCancelPct":50,"profNome":"Dra. Thalia Santiago","profCro":"CRO-MG 12345"}');
select 'X3 cfg ruim', public.salvar_cfg_v8('{"taxaCancelPct":150}');
select 'X3 admin', public.config_admin() ->> 'taxaCancelPct', public.config_admin() ->> 'profCro';
insert into public.pacientes (nome, telefone) values ('Joana Silva', '(31) 98888-7777');
insert into public.pac_orcamentos (paciente_id, descricao, valor, status, parcelas, primeiro_venc) select id, 'Tratamento de canal', 900, 'aprovado', 3, current_date from public.pacientes;
insert into public.pac_pagamentos (paciente_id, orcamento_id, valor, forma) select paciente_id, id, 300, 'pix' from public.pac_orcamentos;
select 'X4 fin', (select count(*) from public.pac_orcamentos), (select sum(valor) from public.pac_pagamentos);
insert into public.paciente_docs (paciente_id, tipo, nome, path) select id, 'receita', 'Receita.pdf', 'x/receita.pdf' from public.pacientes;
select 'X5 doc receita', count(*) from public.paciente_docs where tipo = 'receita';
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'X6 dentista ve fin', (select count(*) from public.pac_orcamentos), (select count(*) from public.pac_pagamentos);
select 'X6 dentista ve taxa', status, valor from public.bookings where id = :'b1';
reset role;
select 'X7 cobrar', public.cobrar_pendentes();
select 'X7 relatorio', length(public.relatorio_html(current_date)) > 100;
select 'X8 rotina', public.rotina_diaria();
