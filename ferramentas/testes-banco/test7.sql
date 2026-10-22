\set ON_ERROR_STOP 0
\pset pager off
\pset format unaligned
\set L '11111111-1111-1111-1111-111111111111'
\set M '22222222-2222-2222-2222-222222222222'
\set A '99999999-9999-9999-9999-999999999999'
select 'MIGRACAO', prazo_cancel_h, v7_aplicado, regras, planos, plano_aviso_dias from public.app_config;
select 'faq', resposta from public.faq where pergunta like 'Posso cancelar%';
select 'termos', versao, length(texto), resumo from public.termos_versoes;
select 'dent', nome, status, termos_versao from public.dentists order by nome;
-- datas: próxima sexta (dia 5) e sextas do mês que vem
select (current_date + ((5 - extract(dow from current_date)::int + 7) % 7 + 7))::date as sex \gset
select (date_trunc('month', current_date) + interval '1 month')::date as prox_ini \gset
select (select g::date from generate_series(:'prox_ini'::date, :'prox_ini'::date + 6, '1 day') g where extract(dow from g) = 5) as sex_prox1 \gset
select (select g::date from generate_series(:'prox_ini'::date, :'prox_ini'::date + 6, '1 day') g where extract(dow from g) = 2) as ter_prox1 \gset
select 'datas', :'sex', :'prox_ini', :'sex_prox1', :'ter_prox1';

-- 1) termos pendentes bloqueiam reserva
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'T1 reservar sem aceite', public.reservar('Lucas','','(31) 98841-5460', :'ter_prox1', 9, 11);
select 'T1 aceitar v1', public.aceitar_termos(1);
select 'T1 reservar com aceite', public.reservar('Lucas','','(31) 98841-5460', :'ter_prox1', 9, 11) is not null;
update public.dentists set termos_versao = 99, status = 'liberado' where id = :'L';
select 'T1 protegido', termos_versao from public.dentists where id = :'L';
select 'T1 aceites visiveis', count(*) from public.termos_aceites;
reset role;
-- 2) cadastro sem termos falha; com termos cria
insert into auth.users (id, email, raw_user_meta_data) values ('33333333-3333-3333-3333-333333333333','sem@x.com','{"nome":"Sem Termos","whatsapp":"(31) 90000-0001"}');
insert into auth.users (id, email, raw_user_meta_data) values ('44444444-4444-4444-4444-444444444444','com@x.com','{"nome":"Com Termos","whatsapp":"(31) 90000-0002","termos_versao":"1"}');
select 'T2 novo', nome, status, termos_versao, termos_aceito_em is not null from public.dentists where id in ('33333333-3333-3333-3333-333333333333','44444444-4444-4444-4444-444444444444');
select 'T2 aceite', count(*) from public.termos_aceites where dentist_id = '44444444-4444-4444-4444-444444444444';
-- 3) nova versão
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'T3 salvar v2', public.salvar_termos(replace((select texto from public.termos_versoes where versao = 1), '4 (quatro) horas', '6 (seis) horas'), 'Prazo de 6 horas');
select 'T3 salvar igual', public.salvar_termos(replace((select texto from public.termos_versoes where versao = 1), '4 (quatro) horas', '6 (seis) horas'), 'x');
select 'T3 dentista salvar', 1;
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'T3 dent salvar termos', public.salvar_termos('texto qualquer com mais de vinte letras', null);
select 'T3 pendente', public.termos_pendentes(:'L');
select 'T3 aceitar antiga', public.aceitar_termos(1);
select 'T3 aceitar v2', public.aceitar_termos(2);
select 'T3 ok', public.termos_pendentes(:'L');
reset role;
set role anon; select set_config('request.jwt.claim.sub', '', false);
select 'T3 anon atual', public.termos_atual() ->> 'versao';
reset role;

-- 4) planos
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'P0 mari pedir sem aceite', public.pedir_plano('diaria', 5, 8, 18, :'sex');
select public.aceitar_termos(2);
-- outro dentista ocupa uma sexta do mês que vem antes da aprovação
select 'P0 mari reserva sexta+7', public.reservar('Mariana','','(31) 99712-3344', (:'sex_prox1'::date + 7), 9, 11) is not null;
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'P1 horas invalidas', public.pedir_plano('diaria', 5, 8, 17, :'sex');
select 'P1 dia errado', public.pedir_plano('diaria', 4, 8, 18, :'sex');
select 'P1 pedir', public.pedir_plano('diaria', 5, 8, 18, :'sex') is not null;
select 'P1 duplicado', public.pedir_plano('periodo', 5, 13, 18, :'sex');
select 'P1 periodo terca', public.pedir_plano('periodo', 2, 13, 18, :'ter_prox1') is not null;
select 'P1 aprovar como dentista', public.aprovar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 5));
select 'P1 meus planos', modalidade, dia_semana, h_from, h_to, valor_mensal, status from public.planos order by dia_semana;
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'P2 aprovar sexta', public.aprovar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 5));
select 'P2 aprovar de novo', public.aprovar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 5));
select 'P2 aprovar terca', public.aprovar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 2));
select 'P2 reservas', to_char(date,'YYYY-MM') mes, count(*), sum(valor), string_agg(to_char(date,'DD')||':'||valor, ' ' order by date) from public.bookings where plano_id is not null and h_from = 8 group by 2 order by 2;
select 'P2 terca', to_char(date,'YYYY-MM') mes, count(*), sum(valor) from public.bookings where plano_id is not null and h_from = 13 group by 2 order by 2;
select 'P2 conflitos', count(*) from public.plano_conflitos;
select 'P2 slots plano', count(*) from public.slots s join public.bookings b on b.id = s.booking_id where b.plano_id is not null;
select 'P2 gerar de novo', public.gerar_planos();
reset role;
select 'P2 rotina', public.rotina_diaria();
-- 5) dentista: cancelar normal bloqueado; liberar dia vira crédito; usar crédito
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'P3 cancelar', public.cancelar((select id from public.bookings where plano_id is not null and date = :'sex_prox1'));
select 'P3 liberar', public.plano_liberar_dia((select id from public.bookings where plano_id is not null and date = :'sex_prox1'));
select 'P3 estado', status, (select count(*) from public.slots where booking_id = b.id) from public.bookings b where plano_id is not null and plano_data_orig = :'sex_prox1';
select 'P3 liberar de novo', public.plano_liberar_dia((select id from public.bookings where plano_id is not null and plano_data_orig = :'sex_prox1'));
select 'P3 credito outro mes', public.plano_usar_credito((select id from public.bookings where plano_data_orig = :'sex_prox1' and plano_id is not null), :'sex', 8, 18);
select 'P3 credito horas erradas', public.plano_usar_credito((select id from public.bookings where plano_data_orig = :'sex_prox1' and plano_id is not null), :'sex_prox1'::date + 3, 8, 13);
select 'P3 credito ocupado', public.plano_usar_credito((select id from public.bookings where plano_data_orig = :'sex_prox1' and plano_id is not null), (:'sex_prox1'::date + 4), 8, 18);
select 'P3 usar credito', public.plano_usar_credito((select id from public.bookings where plano_data_orig = :'sex_prox1' and plano_id is not null), :'sex_prox1'::date + 3, 8, 18);
select 'P3 depois', status, date, h_from, h_to, valor, (select count(*) from public.slots where booking_id = b.id) from public.bookings b where plano_data_orig = :'sex_prox1' and plano_id is not null;
update public.bookings set h_from = 9, plano_id = null where plano_data_orig = :'sex_prox1';
select 'P3 protegido', h_from, plano_id is not null from public.bookings where plano_data_orig = :'sex_prox1';
reset role;
-- crédito com menos de 3 dias: plano criado pela Dra. para amanhã
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'P4 criar amanha', public.criar_plano(:'M', 'periodo', extract(dow from current_date + 1)::int, 18, 22, current_date + 1) ->> 'criadas';
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'P4 liberar <3 dias', public.plano_liberar_dia((select id from public.bookings where plano_id is not null and dentist_id = :'M' and date = current_date + 1));
select 'P4 ver plano de outro', count(*) from public.planos where dentist_id = :'L';
select 'P4 encerrar plano de outro', public.encerrar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 5));
reset role;
-- 6) encerrar
set role authenticated; select set_config('request.jwt.claim.sub', :'L', false);
select 'P5 encerrar', public.encerrar_plano((select id from public.planos where dentist_id = :'L' and dia_semana = 2));
select 'P5 depois', status, fim from public.planos where dentist_id = :'L' and dia_semana = 2;
select 'P5 reservas terca', to_char(date,'YYYY-MM'), status, count(*) from public.bookings where plano_id = (select id from public.planos where dentist_id = :'L' and dia_semana = 2) group by 2,3 order by 2,3;
reset role;
-- 7) cobrança conta crédito; relatório
select set_config('app.bypass','on',false);
update public.bookings set date = current_date - 5, plano_data_orig = current_date - 5 where id = (select id from public.bookings where plano_id is not null and status = 'ativo' and h_from = 8 order by date desc limit 1);
update public.bookings set status = 'credito' where id = (select id from public.bookings where plano_id is not null and date = current_date - 5);
select 'P6 pendentes', count(*) from public.bookings b where b.status in ('ativo','credito') and not b.pago and b.plano_id is not null;
select set_config('app.bypass','',false);
select 'P6 cobrar', public.cobrar_pendentes();
select 'P6 relatorio', length(public.relatorio_html(current_date)) > 100;
select 'P6 calls', count(*) from net.calls;
-- 8) ajustes dos planos
set role authenticated; select set_config('request.jwt.claim.sub', :'A', false);
select 'P7 salvar cfg', public.salvar_planos_cfg(1100, 650, 2);
select 'P7 cfg', public.config_publica() -> 'planos', public.config_publica() -> 'planoAvisoDias', public.config_publica() -> 'prazoCancelamentoH';
select 'P7 recusar', public.recusar_plano((select id from public.planos where status = 'ativo' limit 1), 'x');
reset role;
set role authenticated; select set_config('request.jwt.claim.sub', :'M', false);
select 'P7 salvar cfg dentista', public.salvar_planos_cfg(1, 1, 1);
reset role;
