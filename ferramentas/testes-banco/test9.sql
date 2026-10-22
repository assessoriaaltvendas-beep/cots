\set ON_ERROR_STOP 0
\pset pager off
\pset format unaligned
\set L '11111111-1111-1111-1111-111111111111'
\set M '22222222-2222-2222-2222-222222222222'
\set A '99999999-9999-9999-9999-999999999999'
select set_config('app.bypass','on',false);
update public.dentists set termos_versao = (select max(versao) from public.termos_versoes);
insert into public.pacientes (nome, telefone) values ('Joana Silva', '(31) 98888-7777');
insert into public.consultas (paciente_id, data, inicio, fim) select id, current_date + 3, '14:00', '15:00' from public.pacientes;
select set_config('app.bypass','',false);
select 'N0 nivel padrao', nivel from public.admins;
-- admin completo
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'N1 acesso', public.meu_acesso();
select 'N1 completo', public.is_admin_completo();
select 'N2 add conta inexistente', public.adicionar_admin('nao@x.com', 'agenda');
select 'N2 add nivel ruim', public.adicionar_admin('lucas@x.com', 'chefe');
select 'N2 add lucas agenda', public.adicionar_admin(' Lucas@X.com ', 'agenda') is not null;
select 'N2 add de novo', public.adicionar_admin('lucas@x.com', 'agenda');
select 'N3 remover a si', public.remover_admin(:'A');
select 'N3 mudar a si', public.mudar_nivel_admin(:'A', 'agenda');
select 'N4 lista', jsonb_array_length(public.listar_admins() -> 'admins'), jsonb_array_length(public.listar_admins() -> 'log');
select 'N4 lucas', x ->> 'nivel', x ->> 'dentista', x ->> 'por' from jsonb_array_elements(public.listar_admins() -> 'admins') x where x ->> 'email' = 'lucas@x.com';
reset role;
-- admin da agenda (Lucas, também dentista)
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'N5 acesso lucas', public.meu_acesso();
select 'N5 is_admin', public.is_admin(), public.is_admin_completo();
select 'N5 ve pacientes', (select count(*) from public.pacientes), (select count(*) from public.consultas), (select count(*) from public.pac_orcamentos);
select 'N5 insere paciente'; insert into public.pacientes (nome) values ('Teste');
select 'N5 ve slots consulta', count(*) from public.slots where consulta;
select 'N5 lista admins', public.listar_admins();
select 'N5 add admin', public.adicionar_admin('mari@x.com', 'agenda');
select 'N5 remove thalia', public.remover_admin(:'A');
select 'N5 cfg prof', public.salvar_cfg_v8('{"profCro":"X"}');
select 'N5 cfg taxa', public.salvar_cfg_v8('{"taxaCancelPct":30}');
select 'N5 ve dentistas', count(*) from public.dentists;
select 'N5 bloquear', public.bloquear(current_date + 20, 9, 10, 'teste') is not null;
select 'N5 calc salvar', public.salvar_calc('[]'::jsonb, true, 1, 'x');
select 'N5 calc dados', public.calc_dados() ->> 'liberada';
select 'N5 nome', public.salvar_meu_nome_admin('Lucas A.');
reset role;
-- dentista comum
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'N6 acesso mari', public.meu_acesso();
select 'N6 calc antes', public.calc_dados() ->> 'liberada', public.calc_dados() -> 'itens';
select 'N6 calc salvar', public.salvar_calc('[]'::jsonb, true, 1, 'x');
select 'N6 log', count(*) from public.admins_log;
reset role;
-- completo: calculadora e níveis
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'N7 liberar sem itens', public.salvar_calc(null, true, null, 'liberou');
select 'N7 salvar', public.salvar_calc('[{"id":"dip","nome":"Dipirona"}]'::jsonb, false, 1, 'revisou');
select 'N7 liberar', public.salvar_calc(null, true, null, 'liberou para os dentistas');
select 'N7 dados', public.calc_dados() ->> 'liberada', jsonb_array_length(public.calc_dados() -> 'itens'), jsonb_array_length(public.calc_dados() -> 'log'), public.calc_dados() ->> 'atualizadaPor';
select 'N7 grande', public.salvar_calc('{"a":1}'::jsonb, null, null, 'x');
select 'N8 lucas completo', public.mudar_nivel_admin(:'L', 'completo');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'N8 lucas ve pacientes', (select count(*) from public.pacientes);
select 'N8 lucas rebaixa thalia', public.mudar_nivel_admin(:'A', 'agenda');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'N8 thalia (agenda) ve pacientes', (select count(*) from public.pacientes);
select 'N8 thalia remove lucas', public.remover_admin(:'L');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'N9 ultimo completo rebaixar', public.mudar_nivel_admin(:'A', 'agenda');
select 'N9 volta thalia', public.mudar_nivel_admin(:'A', 'completo');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'N9 remove lucas', public.remover_admin(:'L');
select 'N9 log', string_agg(acao || ':' || coalesce(detalhe,''), ' | ' order by quando) from public.admins_log;
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'N10 mari calc', public.calc_dados() ->> 'liberada', jsonb_array_length(public.calc_dados() -> 'itens'), public.calc_dados() -> 'log';
reset role;
set role anon; select set_config('request.jwt.claim.sub', '', false);
select 'N11 anon calc', public.calc_dados();
select 'N11 anon acesso', public.meu_acesso();
reset role;
