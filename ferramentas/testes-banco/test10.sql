\set ON_ERROR_STOP 0
\pset pager off
\pset format unaligned
\pset tuples_only on
\set L '11111111-1111-1111-1111-111111111111'
\set M '22222222-2222-2222-2222-222222222222'
\set A '99999999-9999-9999-9999-999999999999'
-- v10: calculadora só para administrador completo (rodar depois de schema.sql + pre9.sql)
select set_config('app.bypass','on',false);
update public.app_config set calc_liberada = true, calc_itens = '[{"id":"x","nome":"X"}]'::jsonb where id = 1;
select set_config('app.bypass','',false);
-- completo
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'C1 completo dados', jsonb_array_length(public.calc_dados() -> 'itens'), public.calc_dados() ? 'liberada', jsonb_typeof(public.calc_dados() -> 'log');
select 'C1 completo salvar', public.salvar_calc('[{"id":"dip","nome":"Dipirona"}]'::jsonb, true, 1, 'revisou');
select 'C1 liberada ignorada', (select calc_liberada from public.app_config where id = 1);
select 'C1 log', count(*) from public.calc_log;
select 'C2 add lucas agenda', public.adicionar_admin('lucas@x.com', 'agenda') is not null;
reset role;
-- administrador da agenda
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'C3 agenda dados', public.calc_dados();
select 'C3 agenda salvar', public.salvar_calc('[]'::jsonb, null, 1, 'x');
select 'C3 agenda log', count(*) from public.calc_log;
reset role;
-- dentista comum
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'C4 dentista dados', public.calc_dados();
select 'C4 dentista salvar', public.salvar_calc('[]'::jsonb, null, 1, 'x');
select 'C4 dentista log', count(*) from public.calc_log;
reset role;
-- visitante
set role anon; select set_config('request.jwt.claim.sub', '', false);
select 'C5 anon dados', public.calc_dados();
reset role;
-- agenda promovido a completo passa a ver
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'C6 promove lucas', public.mudar_nivel_admin(:'L', 'completo');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'C6 lucas completo dados', jsonb_array_length(public.calc_dados() -> 'itens');
reset role;
