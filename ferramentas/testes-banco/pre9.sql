select set_config('app.bypass','on',false);
insert into auth.users (id, email, raw_user_meta_data) values
 ('11111111-1111-1111-1111-111111111111','lucas@x.com','{"nome":"Lucas Andrade","whatsapp":"(31) 98841-5460","termos_versao":"1"}'),
 ('22222222-2222-2222-2222-222222222222','mari@x.com','{"nome":"Mariana","whatsapp":"(31) 99712-3344","termos_versao":"1"}'),
 ('99999999-9999-9999-9999-999999999999','thalia@x.com','{}');
insert into public.admins values ('99999999-9999-9999-9999-999999999999');
update public.dentists set status = 'liberado';
update public.app_config set regras = '["Respeite o horário.","Cancelamentos pelo site podem ser feitos até 24 horas antes do início. Depois disso, fale com a Dra. Thalia."]'::jsonb;
select 'pre', prazo_cancel_h from public.app_config;
