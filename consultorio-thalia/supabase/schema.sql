-- =====================================================================
-- Consultório Odontológico Thalia Santiago · banco de dados (Supabase)
-- Cole este arquivo inteiro em: Supabase > SQL Editor > New query > Run
-- Pode rodar de novo sem problema: ele recria funções e regras.
-- =====================================================================

-- ---------- Ajustes de funcionamento (mantenha igual ao config.js) ----------
create or replace function public.cfg_abre() returns int language sql immutable as $$ select 8 $$;          -- primeira hora (08:00)
create or replace function public.cfg_fecha() returns int language sql immutable as $$ select 18 $$;        -- encerra às 18:00
create or replace function public.cfg_dias() returns int[] language sql immutable as $$ select array[1,2,3,4,5,6] $$; -- 0=dom ... 6=sáb
create or replace function public.cfg_prazo_cancelamento() returns interval language sql immutable as $$ select interval '24 hours' $$;
create or replace function public.agora_local() returns timestamp language sql stable as $$ select (now() at time zone 'America/Sao_Paulo') $$;

-- ---------- Tabelas ----------
create table if not exists public.admins (
  user_id uuid primary key references auth.users (id) on delete cascade
);

create table if not exists public.dentists (
  id uuid primary key references auth.users (id) on delete cascade,
  nome text not null,
  cro text,
  whatsapp text not null,
  email text,
  especialidade text,
  regras_aceitas_em timestamptz,
  criado_em timestamptz not null default now()
);

create table if not exists public.bookings (
  id uuid primary key default gen_random_uuid(),
  dentist_id uuid references public.dentists (id) on delete set null,
  nome text not null,
  cro text,
  tel text not null,
  primeira boolean not null default false,
  date date not null,
  h_from int not null,
  h_to int not null,
  status text not null default 'ativo' check (status in ('ativo', 'cancelado')),
  origem text not null default 'site',
  pedido text,
  serie text,
  conf_aberta_em timestamptz,
  comprovante_em timestamptz,
  pago boolean not null default false,
  pago_em timestamptz,
  checklist jsonb,
  avaliacao jsonb,
  criado_em timestamptz not null default now(),
  check (h_to > h_from)
);
alter table public.bookings add column if not exists email text;
alter table public.bookings add column if not exists lembrete_em timestamptz;
alter table public.bookings add column if not exists comprovante_path text;
create index if not exists bookings_date_idx on public.bookings (date);
create index if not exists bookings_dentist_idx on public.bookings (dentist_id);

-- Uma linha por hora ocupada: a chave primária impede duas reservas na mesma hora.
create table if not exists public.slots (
  date date not null,
  hour int not null,
  booking_id uuid not null references public.bookings (id) on delete cascade,
  primary key (date, hour)
);

create table if not exists public.avisos (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  texto text not null,
  criado_em timestamptz not null default now()
);

create table if not exists public.problemas (
  id uuid primary key default gen_random_uuid(),
  dentist_id uuid not null references public.dentists (id) on delete cascade,
  nome text not null,
  tel text,
  tipo text not null,
  descricao text not null,
  reserva text,
  foto text check (foto is null or length(foto) < 400000),
  status text not null default 'aberto' check (status in ('aberto', 'resolvido')),
  resolvido_em timestamptz,
  criado_em timestamptz not null default now()
);

create table if not exists public.espera (
  id uuid primary key default gen_random_uuid(),
  dentist_id uuid not null references public.dentists (id) on delete cascade,
  nome text not null,
  tel text,
  date date not null,
  h_from int not null,
  h_to int not null,
  criado_em timestamptz not null default now()
);

-- ---------- Funções auxiliares ----------
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid())
$$;

-- Cria o perfil do dentista quando ele se cadastra pelo site.
create or replace function public.novo_usuario() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.raw_user_meta_data ? 'whatsapp' then
    insert into public.dentists (id, nome, cro, whatsapp, email, especialidade, regras_aceitas_em)
    values (
      new.id,
      coalesce(nullif(trim(new.raw_user_meta_data ->> 'nome'), ''), split_part(new.email, '@', 1)),
      nullif(trim(new.raw_user_meta_data ->> 'cro'), ''),
      trim(new.raw_user_meta_data ->> 'whatsapp'),
      new.email,
      nullif(trim(new.raw_user_meta_data ->> 'especialidade'), ''),
      case when new.raw_user_meta_data ? 'regras_aceitas_em' then now() end
    )
    on conflict (id) do nothing;
  end if;
  return new;
end $$;
drop trigger if exists ao_criar_usuario on auth.users;
create trigger ao_criar_usuario after insert on auth.users
  for each row execute function public.novo_usuario();

-- Dentistas só podem alterar pedido, checklist, avaliação e comprovante.
create or replace function public.proteger_booking() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if coalesce(current_setting('app.bypass', true), '') = 'on' or public.is_admin() then
    return new;
  end if;
  new.id := old.id; new.dentist_id := old.dentist_id; new.nome := old.nome; new.cro := old.cro;
  new.tel := old.tel; new.primeira := old.primeira; new.date := old.date; new.h_from := old.h_from;
  new.h_to := old.h_to; new.status := old.status; new.origem := old.origem; new.serie := old.serie;
  new.conf_aberta_em := old.conf_aberta_em; new.pago := old.pago; new.pago_em := old.pago_em;
  new.criado_em := old.criado_em; new.email := old.email; new.lembrete_em := old.lembrete_em;
  return new;
end $$;
drop trigger if exists proteger_booking on public.bookings;
create trigger proteger_booking before update on public.bookings
  for each row execute function public.proteger_booking();

-- Reserva atômica: cria a reserva e ocupa cada hora; se alguma hora já estiver ocupada, nada é gravado.
drop function if exists public.reservar(text, text, text, date, int, int, boolean, text, text, text);
create or replace function public.reservar(
  p_nome text, p_cro text, p_tel text, p_date date, p_from int, p_to int,
  p_primeira boolean default false, p_pedido text default null, p_serie text default null, p_origem text default 'site',
  p_email text default null, p_dentist uuid default null
) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_id uuid;
  v_dentist uuid;
  v_origem text;
  h int;
begin
  if coalesce(length(trim(p_nome)), 0) < 2 then raise exception 'NOME_INVALIDO'; end if;
  if length(regexp_replace(coalesce(p_tel, ''), '\D', '', 'g')) < 10 then raise exception 'TELEFONE_INVALIDO'; end if;
  if p_from < public.cfg_abre() or p_to > public.cfg_fecha() or p_to <= p_from then raise exception 'HORARIO_INVALIDO'; end if;
  if not (extract(dow from p_date)::int = any (public.cfg_dias())) then raise exception 'DIA_FECHADO'; end if;
  if (p_date + make_time(p_from, 0, 0)) <= public.agora_local() then raise exception 'HORARIO_PASSADO'; end if;
  if p_date > (public.agora_local()::date + 120) then raise exception 'DATA_DISTANTE'; end if;
  if nullif(trim(p_email), '') is not null and trim(p_email) !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then raise exception 'EMAIL_INVALIDO'; end if;

  if p_dentist is not null and public.is_admin() then
    select id into v_dentist from public.dentists where id = p_dentist;
    v_origem := 'painel';
  else
    select id into v_dentist from public.dentists where id = auth.uid();
    v_origem := case when v_dentist is not null then coalesce(nullif(p_origem, 'painel'), 'site')
                     when public.is_admin() then 'painel' else 'site' end;
  end if;

  -- Reserva só com conta liberada pela Dra. Thalia (a administradora reserva para qualquer um).
  if not public.is_admin() then
    if v_dentist is null then raise exception 'LOGIN_NECESSARIO'; end if;
    if exists (select 1 from public.dentists where id = v_dentist and status = 'pendente') then raise exception 'CONTA_PENDENTE'; end if;
    if exists (select 1 from public.dentists where id = v_dentist and status = 'bloqueado') then raise exception 'CONTA_BLOQUEADA'; end if;
  end if;

  insert into public.bookings (dentist_id, nome, cro, tel, email, primeira, date, h_from, h_to, pedido, serie, origem)
  values (v_dentist, trim(p_nome), nullif(trim(p_cro), ''), trim(p_tel), nullif(lower(trim(p_email)), ''), coalesce(p_primeira, false),
          p_date, p_from, p_to, nullif(trim(p_pedido), ''), p_serie, v_origem)
  returning id into v_id;

  begin
    for h in p_from .. p_to - 1 loop
      insert into public.slots (date, hour, booking_id) values (p_date, h, v_id);
    end loop;
  exception when unique_violation then
    raise exception 'HORARIO_OCUPADO';
  end;
  return v_id;
end $$;

-- Bloqueio de horários pela administradora (férias, feriado, manutenção). Para liberar, use cancelar().
create or replace function public.bloquear(p_date date, p_from int, p_to int, p_motivo text default null) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_id uuid;
  h int;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  if p_from < public.cfg_abre() or p_to > public.cfg_fecha() or p_to <= p_from then raise exception 'HORARIO_INVALIDO'; end if;
  if p_date < public.agora_local()::date then raise exception 'HORARIO_PASSADO'; end if;
  insert into public.bookings (nome, tel, date, h_from, h_to, origem)
  values (coalesce(nullif(trim(p_motivo), ''), 'Horário bloqueado'), '', p_date, p_from, p_to, 'bloqueio')
  returning id into v_id;
  begin
    for h in p_from .. p_to - 1 loop
      insert into public.slots (date, hour, booking_id) values (p_date, h, v_id);
    end loop;
  exception when unique_violation then
    raise exception 'HORARIO_OCUPADO';
  end;
  return v_id;
end $$;

-- Cancelamento: a administradora cancela qualquer reserva; o dentista, só as dele e dentro do prazo.
create or replace function public.cancelar(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
declare
  b public.bookings;
begin
  if auth.uid() is null then raise exception 'SEM_PERMISSAO'; end if;
  select * into b from public.bookings where id = p_id;
  if not found then raise exception 'RESERVA_NAO_ENCONTRADA'; end if;
  if not public.is_admin() then
    if b.dentist_id is distinct from auth.uid() then raise exception 'SEM_PERMISSAO'; end if;
    if (b.date + make_time(b.h_from, 0, 0)) - public.agora_local() < public.cfg_prazo_cancelamento() then raise exception 'FORA_DO_PRAZO'; end if;
  end if;
  perform set_config('app.bypass', 'on', true);
  delete from public.slots where booking_id = p_id;
  update public.bookings set status = 'cancelado' where id = p_id;
end $$;

-- ---------- Segurança (Row Level Security) ----------
alter table public.admins enable row level security;
alter table public.dentists enable row level security;
alter table public.bookings enable row level security;
alter table public.slots enable row level security;
alter table public.avisos enable row level security;
alter table public.problemas enable row level security;
alter table public.espera enable row level security;

drop policy if exists "admins: ver a si" on public.admins;
create policy "admins: ver a si" on public.admins for select using (user_id = auth.uid());

drop policy if exists "dentists: ler" on public.dentists;
create policy "dentists: ler" on public.dentists for select using (id = auth.uid() or public.is_admin());
drop policy if exists "dentists: editar" on public.dentists;
create policy "dentists: editar" on public.dentists for update using (id = auth.uid() or public.is_admin()) with check (id = auth.uid() or public.is_admin());

drop policy if exists "bookings: ler" on public.bookings;
create policy "bookings: ler" on public.bookings for select using (public.is_admin() or dentist_id = auth.uid());
drop policy if exists "bookings: editar" on public.bookings;
create policy "bookings: editar" on public.bookings for update using (public.is_admin() or dentist_id = auth.uid()) with check (public.is_admin() or dentist_id = auth.uid());

-- Horários ocupados são públicos (só data e hora; nenhum dado pessoal).
drop policy if exists "slots: ler" on public.slots;
create policy "slots: ler" on public.slots for select using (true);

drop policy if exists "avisos: ler" on public.avisos;
create policy "avisos: ler" on public.avisos for select using (auth.uid() is not null);
drop policy if exists "avisos: publicar" on public.avisos;
create policy "avisos: publicar" on public.avisos for insert with check (public.is_admin());
drop policy if exists "avisos: excluir" on public.avisos;
create policy "avisos: excluir" on public.avisos for delete using (public.is_admin());

drop policy if exists "problemas: ler" on public.problemas;
create policy "problemas: ler" on public.problemas for select using (dentist_id = auth.uid() or public.is_admin());
drop policy if exists "problemas: enviar" on public.problemas;
create policy "problemas: enviar" on public.problemas for insert with check (dentist_id = auth.uid());
drop policy if exists "problemas: atualizar" on public.problemas;
create policy "problemas: atualizar" on public.problemas for update using (public.is_admin()) with check (public.is_admin());

drop policy if exists "espera: ler" on public.espera;
create policy "espera: ler" on public.espera for select using (dentist_id = auth.uid() or public.is_admin());
drop policy if exists "espera: entrar" on public.espera;
create policy "espera: entrar" on public.espera for insert with check (dentist_id = auth.uid());
drop policy if exists "espera: sair" on public.espera;
create policy "espera: sair" on public.espera for delete using (dentist_id = auth.uid() or public.is_admin());

grant execute on function public.reservar(text, text, text, date, int, int, boolean, text, text, text, text, uuid) to anon, authenticated;
revoke execute on function public.bloquear(date, int, int, text) from public, anon;
grant execute on function public.bloquear(date, int, int, text) to authenticated;
revoke execute on function public.cancelar(uuid) from public, anon;
grant execute on function public.cancelar(uuid) to authenticated;
grant execute on function public.is_admin() to anon, authenticated;

-- ---------- Perguntas frequentes (editáveis pelo painel) ----------
create table if not exists public.faq (
  id uuid primary key default gen_random_uuid(),
  pergunta text not null,
  resposta text not null,
  ordem int not null default 0,
  criado_em timestamptz not null default now()
);
alter table public.faq enable row level security;
drop policy if exists "faq: ler" on public.faq;
create policy "faq: ler" on public.faq for select using (true);
drop policy if exists "faq: editar" on public.faq;
create policy "faq: editar" on public.faq for all using (public.is_admin()) with check (public.is_admin());
insert into public.faq (pergunta, resposta, ordem)
select * from (values
  ('Como faço para reservar?', 'Crie sua conta na Área do dentista. Assim que a Dra. Thalia liberar o seu acesso (você recebe um e-mail), escolha o dia e as horas livres e confirme. O horário fica bloqueado para você na hora.', 1),
  ('Qual o tempo mínimo de reserva?', '1 hora. Você pode reservar várias horas seguidas no mesmo dia e repetir o mesmo horário toda semana.', 2),
  ('Posso cancelar ou remarcar?', 'Sim, pela área do dentista, até 24 horas antes do início. Depois disso, fale com a Dra. Thalia pelo WhatsApp.', 3),
  ('E se o horário que eu quero estiver ocupado?', 'Entre na lista de espera pela área do dentista. Se o horário vagar, você recebe um aviso.', 4)
) as v(pergunta, resposta, ordem)
where not exists (select 1 from public.faq);

-- ---------- Configuração de e-mails (preenchida pelo painel, em Ajustes) ----------
create table if not exists public.app_config (
  id int primary key default 1 check (id = 1),
  email_admin text,
  email_remetente text,
  nome_remetente text not null default 'Consultório Thalia Santiago',
  site_url text,
  endereco text not null default 'Rua Juiz de Fora, Centro, Ipatinga/MG',
  whatsapp text not null default '553185825564',
  atualizado_em timestamptz not null default now()
);
insert into public.app_config (id) values (1) on conflict (id) do nothing;
alter table public.app_config enable row level security;
drop policy if exists "config: admin" on public.app_config;
create policy "config: admin" on public.app_config for all using (public.is_admin()) with check (public.is_admin());

-- Extensões usadas pelos e-mails (se der aviso aqui, ative em Database > Extensions: pg_net e pg_cron)
do $$
begin
  begin create extension if not exists pg_net; exception when others then raise notice 'Ative a extensão pg_net em Database > Extensions'; end;
  begin create extension if not exists pg_cron; exception when others then raise notice 'Ative a extensão pg_cron em Database > Extensions'; end;
end $$;

create or replace function public.url_enc(t text) returns text language sql immutable as $$
  select replace(replace(replace(replace(replace(replace(replace(replace(coalesce(t, ''),
    '%', '%25'), ' ', '%20'), ',', '%2C'), '&', '%26'), '#', '%23'), '?', '%3F'), '/', '%2F'), ':', '%3A')
$$;
create or replace function public.esc_html(t text) returns text language sql immutable as $$
  select replace(replace(replace(replace(coalesce(t, ''), '&', '&amp;'), '<', '&lt;'), '>', '&gt;'), '"', '&quot;')
$$;
create or replace function public.dia_semana(d date) returns text language sql immutable as $$
  select (array['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'])[extract(dow from d)::int + 1]
$$;
create or replace function public.quando_txt(d date, h1 int, h2 int) returns text language sql immutable as $$
  select public.dia_semana(d) || ', ' || to_char(d, 'DD/MM/YYYY') || ', das ' || lpad(h1::text, 2, '0') || ':00 às ' || lpad(h2::text, 2, '0') || ':00'
$$;

-- Envia um e-mail pelo Brevo (plano gratuito). Se a chave ou o remetente não estiverem configurados, não faz nada.
create or replace function public.enviar_email(p_para text, p_nome text, p_assunto text, p_corpo text) returns boolean
language plpgsql security definer set search_path = public as $$
declare
  k text;
  c public.app_config;
  html text;
begin
  if p_para is null or p_para !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then return false; end if;
  select * into c from public.app_config where id = 1;
  if c.email_remetente is null then return false; end if;
  begin
    select decrypted_secret into k from vault.decrypted_secrets where name = 'brevo_api_key' limit 1;
  exception when others then k := null; end;
  if k is null then return false; end if;
  html := '<div style="font-family:Arial,sans-serif;background:#faf6f5;padding:24px">'
       || '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #efe4e4">'
       || '<div style="background:#590117;color:#d9bb6f;padding:18px 24px;font-family:Georgia,serif;font-size:18px">' || public.esc_html(c.nome_remetente) || '</div>'
       || '<div style="padding:24px;color:#24161a;font-size:15px;line-height:1.6">' || p_corpo || '</div>'
       || '<div style="padding:14px 24px;border-top:1px solid #efe4e4;color:#7a6a6e;font-size:12px">' || public.esc_html(c.endereco)
       || coalesce(' · <a href="' || c.site_url || '" style="color:#590117">' || replace(replace(c.site_url, 'https://', ''), 'http://', '') || '</a>', '') || '</div></div></div>';
  perform net.http_post(
    url := 'https://api.brevo.com/v3/smtp/email',
    headers := jsonb_build_object('api-key', k, 'Content-Type', 'application/json', 'accept', 'application/json'),
    body := jsonb_build_object(
      'sender', jsonb_build_object('name', c.nome_remetente, 'email', c.email_remetente),
      'to', jsonb_build_array(jsonb_build_object('email', p_para, 'name', coalesce(nullif(p_nome, ''), p_para))),
      'subject', p_assunto,
      'htmlContent', html));
  return true;
exception when others then
  return false;
end $$;
revoke execute on function public.enviar_email(text, text, text, text) from public, anon, authenticated;

create or replace function public.link_agenda(b public.bookings) returns text language plpgsql stable set search_path = public as $$
declare c public.app_config;
begin
  select * into c from public.app_config where id = 1;
  return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
    || '&text=' || public.url_enc('Consultório Thalia Santiago')
    || '&dates=' || to_char(b.date, 'YYYYMMDD') || 'T' || lpad(b.h_from::text, 2, '0') || '0000/' || to_char(b.date, 'YYYYMMDD') || 'T' || lpad(b.h_to::text, 2, '0') || '0000'
    || '&ctz=America/Sao_Paulo&location=' || public.url_enc(c.endereco);
end $$;

-- Gatilhos de e-mail
create or replace function public.email_nova_reserva() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  dest text; c public.app_config;
begin
  if new.origem = 'bloqueio' then return new; end if;
  select * into c from public.app_config where id = 1;
  select coalesce(d.email, new.email) into dest from (select 1) x left join public.dentists d on d.id = new.dentist_id;
  perform public.enviar_email(dest, new.nome, 'Reserva confirmada · ' || to_char(new.date, 'DD/MM') || ' às ' || lpad(new.h_from::text, 2, '0') || 'h',
    '<p>Olá, ' || public.esc_html(split_part(new.nome, ' ', 1)) || '!</p><p>Sua reserva do consultório está confirmada:</p>'
    || '<p style="font-size:17px"><b>' || public.quando_txt(new.date, new.h_from, new.h_to) || '</b></p>'
    || '<p>Você recebe um lembrete por e-mail 2 horas antes.</p>'
    || '<p><a href="' || public.link_agenda(new) || '" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Adicionar à minha agenda</a></p>'
    || coalesce('<p style="color:#7a6a6e">Precisa cancelar? Pela área do dentista, até ' || extract(epoch from public.cfg_prazo_cancelamento())::int / 3600 || ' horas antes: <a href="' || c.site_url || '/#dentista" style="color:#590117">abrir área do dentista</a>.</p>', ''));
  perform public.enviar_email(c.email_admin, 'Dra. Thalia', 'Nova reserva · ' || new.nome,
    '<p><b>' || public.esc_html(new.nome) || '</b>' || coalesce(' (' || public.esc_html(new.cro) || ')', '') || ' reservou o consultório:</p>'
    || '<p style="font-size:17px"><b>' || public.quando_txt(new.date, new.h_from, new.h_to) || '</b></p>'
    || '<p>WhatsApp: ' || public.esc_html(new.tel) || coalesce('<br>Pedido especial: ' || public.esc_html(new.pedido), '') || '</p>'
    || coalesce('<p><a href="' || c.site_url || '/#admin" style="color:#590117">Abrir o painel</a></p>', ''));
  return new;
exception when others then return new;
end $$;
drop trigger if exists email_nova_reserva on public.bookings;
create trigger email_nova_reserva after insert on public.bookings for each row execute function public.email_nova_reserva();

create or replace function public.email_cancelamento() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  c public.app_config; w record;
begin
  if not (old.status = 'ativo' and new.status = 'cancelado') then return new; end if;
  select * into c from public.app_config where id = 1;
  if new.origem <> 'bloqueio' then
    perform public.enviar_email(c.email_admin, 'Dra. Thalia', 'Reserva cancelada · ' || new.nome,
      '<p>A reserva de <b>' || public.esc_html(new.nome) || '</b> foi cancelada:</p><p><b>' || public.quando_txt(new.date, new.h_from, new.h_to) || '</b></p><p>O horário voltou a ficar livre.</p>');
  end if;
  for w in
    select e.*, d.email as dest from public.espera e join public.dentists d on d.id = e.dentist_id
    where e.date = new.date and e.h_from < new.h_to and e.h_to > new.h_from
      and (new.dentist_id is null or e.dentist_id <> new.dentist_id)
      and not exists (select 1 from public.slots s where s.date = e.date and s.hour >= e.h_from and s.hour < e.h_to)
  loop
    perform public.enviar_email(w.dest, w.nome, 'Vaga aberta no consultório · ' || to_char(w.date, 'DD/MM'),
      '<p>Olá, ' || public.esc_html(split_part(w.nome, ' ', 1)) || '!</p><p>O horário que você queria ficou livre:</p>'
      || '<p style="font-size:17px"><b>' || public.quando_txt(w.date, w.h_from, w.h_to) || '</b></p>'
      || coalesce('<p><a href="' || c.site_url || '/#dentista" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Reservar agora</a></p>', '')
      || '<p style="color:#7a6a6e">Quem reservar primeiro fica com o horário.</p>');
  end loop;
  return new;
exception when others then return new;
end $$;
drop trigger if exists email_cancelamento on public.bookings;
create trigger email_cancelamento after update of status on public.bookings for each row execute function public.email_cancelamento();

create or replace function public.email_problema() returns trigger
language plpgsql security definer set search_path = public as $$
declare c public.app_config;
begin
  select * into c from public.app_config where id = 1;
  perform public.enviar_email(c.email_admin, 'Dra. Thalia', 'Problema relatado · ' || new.tipo,
    '<p><b>' || public.esc_html(new.nome) || '</b> relatou um problema (' || public.esc_html(new.tipo) || '):</p>'
    || '<p style="background:#faf6f5;padding:12px;border-radius:10px">' || public.esc_html(new.descricao) || '</p>'
    || coalesce('<p><a href="' || c.site_url || '/#admin" style="color:#590117">Ver no painel</a></p>', ''));
  return new;
exception when others then return new;
end $$;
drop trigger if exists email_problema on public.problemas;
create trigger email_problema after insert on public.problemas for each row execute function public.email_problema();

-- Lembrete 2 horas antes, por e-mail e no celular (roda a cada 10 minutos)
create or replace function public.enviar_lembretes() returns int
language plpgsql security definer set search_path = public as $$
declare
  r record; n int := 0;
begin
  perform public.limpar_push();
  for r in
    select b.*, coalesce(d.email, b.email) as dest from public.bookings b left join public.dentists d on d.id = b.dentist_id
    where b.status = 'ativo' and b.origem <> 'bloqueio' and b.lembrete_em is null
      and (b.date + make_time(b.h_from, 0, 0)) > public.agora_local()
      and (b.date + make_time(b.h_from, 0, 0)) <= public.agora_local() + interval '2 hours'
  loop
    if public.enviar_email(r.dest, r.nome, 'Lembrete: sua reserva começa às ' || lpad(r.h_from::text, 2, '0') || 'h',
      '<p>Olá, ' || public.esc_html(split_part(r.nome, ' ', 1)) || '!</p><p>Passando para lembrar da sua reserva do consultório:</p>'
      || '<p style="font-size:17px"><b>' || public.quando_txt(r.date, r.h_from, r.h_to) || '</b></p>'
      || '<p>Ao terminar, faça o checklist de saída na área do dentista. Bom atendimento!</p>') then
      n := n + 1;
    end if;
    if r.dentist_id is not null then
      perform public.push_para(array[r.dentist_id], 'Sua reserva começa às ' || r.h_from || 'h',
        'Lembrete do consultório: ' || public.hora_txt(r.date, r.h_from, r.h_to) || '. Ao terminar, faça o checklist de saída.', './#dentista', 'lembrete-' || r.id);
    end if;
    perform set_config('app.bypass', 'on', true);
    update public.bookings set lembrete_em = now() where id = r.id;
  end loop;
  return n;
end $$;
revoke execute on function public.enviar_lembretes() from public, anon, authenticated;

do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.unschedule(jobid) from cron.job where jobname = 'lembretes-consultorio';
    perform cron.schedule('lembretes-consultorio', '*/10 * * * *', 'select public.enviar_lembretes()');
  end if;
exception when others then raise notice 'Não foi possível agendar os lembretes: ative pg_cron em Database > Extensions e rode de novo.';
end $$;

-- Funções do painel para configurar os e-mails
create or replace function public.status_email() returns jsonb
language plpgsql security definer set search_path = public as $$
declare c public.app_config; tem boolean := false;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  select * into c from public.app_config where id = 1;
  begin select exists (select 1 from vault.secrets where name = 'brevo_api_key') into tem; exception when others then tem := false; end;
  return jsonb_build_object('chave', tem, 'email_admin', c.email_admin, 'email_remetente', c.email_remetente, 'nome_remetente', c.nome_remetente,
    'pg_net', exists (select 1 from pg_extension where extname = 'pg_net'), 'pg_cron', exists (select 1 from pg_extension where extname = 'pg_cron'));
end $$;

create or replace function public.salvar_config_email(p_email_admin text, p_email_remetente text, p_nome_remetente text, p_site_url text, p_chave text default null) returns void
language plpgsql security definer set search_path = public as $$
declare v uuid;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  update public.app_config set
    email_admin = nullif(lower(trim(p_email_admin)), ''),
    email_remetente = nullif(lower(trim(p_email_remetente)), ''),
    nome_remetente = coalesce(nullif(trim(p_nome_remetente), ''), nome_remetente),
    site_url = coalesce(nullif(rtrim(trim(p_site_url), '/'), ''), site_url),
    atualizado_em = now()
  where id = 1;
  if nullif(trim(p_chave), '') is not null then
    select id into v from vault.secrets where name = 'brevo_api_key';
    if v is null then perform vault.create_secret(trim(p_chave), 'brevo_api_key', 'Chave da API do Brevo');
    else perform vault.update_secret(v, trim(p_chave)); end if;
  end if;
end $$;

create or replace function public.testar_email() returns boolean
language plpgsql security definer set search_path = public as $$
declare c public.app_config;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  select * into c from public.app_config where id = 1;
  return public.enviar_email(c.email_admin, 'Dra. Thalia', 'Teste de e-mail do site',
    '<p>Tudo certo! Os e-mails automáticos do site estão funcionando.</p><p>A partir de agora você recebe um aviso a cada reserva nova, cancelamento e problema relatado.</p>');
end $$;
revoke execute on function public.status_email() from public, anon;
revoke execute on function public.salvar_config_email(text, text, text, text, text) from public, anon;
revoke execute on function public.testar_email() from public, anon;
grant execute on function public.status_email() to authenticated;
grant execute on function public.salvar_config_email(text, text, text, text, text) to authenticated;
grant execute on function public.testar_email() to authenticated;

-- ---------- Notificações no celular (gratuitas, pelo app instalado) ----------
create table if not exists public.push_subs (
  endpoint text primary key check (endpoint ~ '^https://' and length(endpoint) < 1000),
  user_id uuid not null references auth.users (id) on delete cascade,
  p256dh text not null check (length(p256dh) < 200),
  auth text not null check (length(auth) < 100),
  aparelho text check (aparelho is null or length(aparelho) < 80),
  criado_em timestamptz not null default now()
);
create index if not exists push_subs_user_idx on public.push_subs (user_id);
alter table public.push_subs enable row level security;
drop policy if exists "push: ver os meus" on public.push_subs;
create policy "push: ver os meus" on public.push_subs for select using (user_id = auth.uid());

-- Envios em andamento, para apagar aparelhos que desinstalaram o app.
create table if not exists public.push_envios (request_id bigint primary key, criado_em timestamptz not null default now());
alter table public.push_envios enable row level security;

alter table public.app_config add column if not exists vapid_publica text;
alter table public.app_config add column if not exists push_url text;

-- Chave pública (necessária para o celular se inscrever). Não é segredo.
create or replace function public.push_chave_publica() returns text
language sql stable security definer set search_path = public as $$
  select vapid_publica from public.app_config where id = 1 and push_url is not null
$$;
grant execute on function public.push_chave_publica() to anon, authenticated;

create or replace function public.push_inscrever(p_endpoint text, p_p256dh text, p_auth text, p_aparelho text default null) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'SEM_PERMISSAO'; end if;
  insert into public.push_subs (endpoint, user_id, p256dh, auth, aparelho)
  values (p_endpoint, auth.uid(), p_p256dh, p_auth, left(p_aparelho, 79))
  on conflict (endpoint) do update set user_id = excluded.user_id, p256dh = excluded.p256dh, auth = excluded.auth, aparelho = excluded.aparelho, criado_em = now();
end $$;

create or replace function public.push_cancelar(p_endpoint text) returns void
language sql security definer set search_path = public as $$
  delete from public.push_subs where endpoint = p_endpoint and user_id = auth.uid()
$$;
revoke execute on function public.push_inscrever(text, text, text, text) from public, anon;
revoke execute on function public.push_cancelar(text) from public, anon;
grant execute on function public.push_inscrever(text, text, text, text) to authenticated;
grant execute on function public.push_cancelar(text) to authenticated;

-- Envia uma notificação para os aparelhos das pessoas indicadas. Se não estiver configurado, não faz nada.
create or replace function public.push_para(p_users uuid[], p_titulo text, p_corpo text, p_url text default './', p_tag text default null) returns int
language plpgsql security definer set search_path = public as $$
declare
  c public.app_config; k text; subs jsonb; rid bigint;
begin
  if p_users is null or cardinality(p_users) = 0 then return 0; end if;
  select * into c from public.app_config where id = 1;
  if c.push_url is null or c.vapid_publica is null then return 0; end if;
  select jsonb_agg(jsonb_build_object('endpoint', s.endpoint, 'p256dh', s.p256dh, 'auth', s.auth)) into subs
  from public.push_subs s where s.user_id = any (p_users);
  if subs is null then return 0; end if;
  begin
    select decrypted_secret into k from vault.decrypted_secrets where name = 'vapid_privada' limit 1;
  exception when others then k := null; end;
  if k is null then return 0; end if;
  rid := net.http_post(
    url := c.push_url,
    headers := jsonb_build_object('Content-Type', 'application/json'),
    body := jsonb_build_object(
      'vapid', jsonb_build_object('publicKey', c.vapid_publica, 'privateKey', k,
        'subject', coalesce('mailto:' || c.email_admin, c.site_url, 'mailto:contato@consultorio.app')),
      'subs', subs,
      'payload', jsonb_build_object('title', p_titulo, 'body', p_corpo, 'url', coalesce(p_url, './'), 'tag', p_tag)),
    timeout_milliseconds := 10000);
  insert into public.push_envios (request_id) values (rid) on conflict do nothing;
  return jsonb_array_length(subs);
exception when others then
  return 0;
end $$;
revoke execute on function public.push_para(uuid[], text, text, text, text) from public, anon, authenticated;

create or replace function public.push_admins(p_titulo text, p_corpo text, p_tag text default null) returns int
language sql security definer set search_path = public as $$
  select public.push_para(array(select user_id from public.admins), p_titulo, p_corpo, './#admin', p_tag)
$$;
revoke execute on function public.push_admins(text, text, text) from public, anon, authenticated;

create or replace function public.hora_txt(d date, h1 int, h2 int) returns text language sql immutable as $$
  select left(public.dia_semana(d), 3) || ', ' || to_char(d, 'DD/MM') || ', ' || h1 || 'h às ' || h2 || 'h'
$$;

-- Apaga aparelhos que desinstalaram o app ou desligaram as notificações (o serviço responde "não existe mais").
create or replace function public.limpar_push() returns int
language plpgsql security definer set search_path = public as $$
declare r record; n int := 0; k int;
begin
  for r in
    select e.request_id, h.status_code, h.content from public.push_envios e join net._http_response h on h.id = e.request_id
  loop
    if r.status_code = 200 then
      begin
        delete from public.push_subs where endpoint in (select jsonb_array_elements_text(r.content::jsonb -> 'gone'));
        get diagnostics k = row_count;
        n := n + k;
      exception when others then null; end;
    end if;
    delete from public.push_envios where request_id = r.request_id;
  end loop;
  delete from public.push_envios where criado_em < now() - interval '1 day';
  return n;
exception when others then
  return 0;
end $$;
revoke execute on function public.limpar_push() from public, anon, authenticated;

-- Gatilhos de notificação
create or replace function public.push_nova_reserva() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.origem = 'bloqueio' then return new; end if;
  if new.origem = 'painel' then
    if new.dentist_id is not null then
      perform public.push_para(array[new.dentist_id], 'Reserva feita pela Dra. Thalia', public.hora_txt(new.date, new.h_from, new.h_to), './#dentista', 'reserva-' || new.id);
    end if;
  else
    perform public.push_admins('Nova reserva · ' || new.nome, public.hora_txt(new.date, new.h_from, new.h_to), 'nova-' || coalesce(new.serie, new.id::text));
  end if;
  return new;
exception when others then return new;
end $$;
drop trigger if exists push_nova_reserva on public.bookings;
create trigger push_nova_reserva after insert on public.bookings for each row execute function public.push_nova_reserva();

create or replace function public.push_reserva_alterada() returns trigger
language plpgsql security definer set search_path = public as $$
declare w record; adm boolean := public.is_admin();
begin
  if old.status = 'ativo' and new.status = 'cancelado' then
    if new.origem <> 'bloqueio' then
      if adm and new.dentist_id is not null then
        perform public.push_para(array[new.dentist_id], 'Reserva cancelada', 'A Dra. Thalia cancelou sua reserva de ' || public.hora_txt(new.date, new.h_from, new.h_to) || '.', './#dentista', 'reserva-' || new.id);
      elsif not adm then
        perform public.push_admins('Reserva cancelada · ' || new.nome, public.hora_txt(new.date, new.h_from, new.h_to) || '. O horário ficou livre.', 'cancel-' || new.id);
      end if;
    end if;
    for w in
      select distinct e.dentist_id, e.date, e.h_from, e.h_to from public.espera e
      where e.date = new.date and e.h_from < new.h_to and e.h_to > new.h_from
        and (new.dentist_id is null or e.dentist_id <> new.dentist_id)
        and not exists (select 1 from public.slots s where s.date = e.date and s.hour >= e.h_from and s.hour < e.h_to)
    loop
      perform public.push_para(array[w.dentist_id], 'Vaga aberta no consultório', 'O horário que você queria ficou livre: ' || public.hora_txt(w.date, w.h_from, w.h_to) || '. Quem reservar primeiro fica com ele.', './#dentista', 'vaga-' || w.date || '-' || w.h_from);
    end loop;
  end if;
  if not old.pago and new.pago and new.dentist_id is not null then
    perform public.push_para(array[new.dentist_id], 'Pagamento confirmado', 'A Dra. Thalia confirmou o pagamento da reserva de ' || public.hora_txt(new.date, new.h_from, new.h_to) || '.', './#dentista', 'pago-' || new.id);
  end if;
  if new.comprovante_path is not null and new.comprovante_path is distinct from old.comprovante_path then
    perform public.push_admins('Comprovante enviado · ' || new.nome, 'Pagamento da reserva de ' || public.hora_txt(new.date, new.h_from, new.h_to) || '.', 'comp-' || new.id);
  end if;
  return new;
exception when others then return new;
end $$;
drop trigger if exists push_reserva_alterada on public.bookings;
create trigger push_reserva_alterada after update on public.bookings for each row execute function public.push_reserva_alterada();

create or replace function public.push_problema() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform public.push_admins('Problema relatado · ' || new.tipo, new.nome || ': ' || left(new.descricao, 120), 'problema-' || new.id);
  return new;
exception when others then return new;
end $$;
drop trigger if exists push_problema on public.problemas;
create trigger push_problema after insert on public.problemas for each row execute function public.push_problema();

create or replace function public.push_aviso() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform public.push_para(array(select id from public.dentists), 'Mural · ' || new.titulo, left(new.texto, 140), './#dentista', 'aviso-' || new.id);
  return new;
exception when others then return new;
end $$;
drop trigger if exists push_aviso on public.avisos;
create trigger push_aviso after insert on public.avisos for each row execute function public.push_aviso();

-- Funções do painel e do app
create or replace function public.status_push() returns jsonb
language plpgsql security definer set search_path = public as $$
declare c public.app_config; tem boolean := false;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  select * into c from public.app_config where id = 1;
  begin select exists (select 1 from vault.secrets where name = 'vapid_privada') into tem; exception when others then tem := false; end;
  return jsonb_build_object('ativo', tem and c.vapid_publica is not null and c.push_url is not null, 'url', c.push_url,
    'aparelhos', (select count(*) from public.push_subs), 'pessoas', (select count(distinct user_id) from public.push_subs),
    'pg_net', exists (select 1 from pg_extension where extname = 'pg_net'));
end $$;

create or replace function public.salvar_config_push(p_publica text, p_privada text, p_url text) returns void
language plpgsql security definer set search_path = public as $$
declare v uuid; antiga text;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  if p_publica !~ '^[A-Za-z0-9_-]{87}$' or p_privada !~ '^[A-Za-z0-9_-]{43}$' or p_url !~ '^https://[a-z0-9-]+\.supabase\.co/functions/v1/[a-z0-9_-]+$' then
    raise exception 'DADOS_INVALIDOS';
  end if;
  select vapid_publica into antiga from public.app_config where id = 1;
  update public.app_config set vapid_publica = p_publica, push_url = p_url, atualizado_em = now() where id = 1;
  select id into v from vault.secrets where name = 'vapid_privada';
  if v is null then perform vault.create_secret(p_privada, 'vapid_privada', 'Chave privada das notificações');
  else perform vault.update_secret(v, p_privada); end if;
  -- Chaves novas invalidam as inscrições antigas: os aparelhos se inscrevem de novo ao abrir o app.
  if antiga is distinct from p_publica then delete from public.push_subs where endpoint is not null; end if;
end $$;

-- Notificação de teste para os aparelhos da própria pessoa (administradora ou dentista).
create or replace function public.testar_push() returns int
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'SEM_PERMISSAO'; end if;
  return public.push_para(array[auth.uid()], 'Notificações ativadas', 'Tudo certo! Os avisos do consultório vão chegar aqui.',
    case when public.is_admin() then './#admin' else './#dentista' end, 'teste');
end $$;
revoke execute on function public.status_push() from public, anon;
revoke execute on function public.salvar_config_push(text, text, text) from public, anon;
revoke execute on function public.testar_push() from public, anon;
grant execute on function public.status_push() to authenticated;
grant execute on function public.salvar_config_push(text, text, text) to authenticated;
grant execute on function public.testar_push() to authenticated;

-- ---------- Ajustes editáveis pelo painel (valores, funcionamento, Pix, regras) ----------
alter table public.app_config add column if not exists valor_hora numeric(10,2);
alter table public.app_config add column if not exists precos jsonb not null default '{"porDia":{},"porHora":[]}'::jsonb;
alter table public.app_config add column if not exists pacotes jsonb not null default '[]'::jsonb;
alter table public.app_config add column if not exists abre int not null default 8;
alter table public.app_config add column if not exists fecha int not null default 18;
alter table public.app_config add column if not exists dias int[] not null default '{1,2,3,4,5,6}';
alter table public.app_config add column if not exists prazo_cancel_h int not null default 24;
alter table public.app_config add column if not exists pix_chave text;
alter table public.app_config add column if not exists pix_nome text;
alter table public.app_config add column if not exists pix_cidade text not null default 'Ipatinga';
alter table public.app_config add column if not exists regras jsonb;
alter table public.app_config add column if not exists checklist jsonb;
alter table public.app_config add column if not exists espaco jsonb;
alter table public.app_config add column if not exists limite_atraso_dias int;
alter table public.app_config add column if not exists lembrete_pagamento boolean not null default true;
alter table public.app_config add column if not exists relatorio_mensal boolean not null default true;
alter table public.app_config add column if not exists ultimo_relatorio date;
alter table public.app_config add column if not exists agenda_token text;
-- Preço por período (acima do limite de horas avulsas) e diária
alter table public.app_config add column if not exists limite_horas int not null default 3;
alter table public.app_config add column if not exists periodos jsonb not null default '[{"de":8,"ate":13,"valor":180},{"de":13,"ate":18,"valor":180},{"de":18,"ate":22,"valor":180}]'::jsonb;
alter table public.app_config add column if not exists diaria jsonb default '{"de":8,"ate":18,"valor":350}'::jsonb;
alter table public.app_config add column if not exists v6_aplicado boolean not null default false;
-- Valores combinados com a Dra. Thalia (out/2026): R$ 50 a hora e funcionamento até as 22h. Aplicado uma única vez.
update public.app_config set valor_hora = 50, fecha = greatest(fecha, 22), v6_aplicado = true where id = 1 and not v6_aplicado;
alter table public.app_config drop constraint if exists app_config_horario_ok;
alter table public.app_config add constraint app_config_horario_ok check (abre >= 0 and fecha <= 24 and abre < fecha and prazo_cancel_h between 0 and 720
  and (limite_atraso_dias is null or limite_atraso_dias between 1 and 90) and (valor_hora is null or valor_hora >= 0) and cardinality(dias) between 1 and 7);

-- Valor de cada reserva fica gravado: mudar o preço depois não altera reservas antigas.
alter table public.bookings add column if not exists valor numeric(10,2);

-- Horário de funcionamento lido dos ajustes (substitui os valores fixos do começo do arquivo).
create or replace function public.cfg_abre() returns int language sql stable security definer set search_path = public as $$
  select coalesce((select abre from public.app_config where id = 1), 8) $$;
create or replace function public.cfg_fecha() returns int language sql stable security definer set search_path = public as $$
  select coalesce((select fecha from public.app_config where id = 1), 18) $$;
create or replace function public.cfg_dias() returns int[] language sql stable security definer set search_path = public as $$
  select coalesce((select dias from public.app_config where id = 1), array[1,2,3,4,5,6]) $$;
create or replace function public.cfg_prazo_cancelamento() returns interval language sql stable security definer set search_path = public as $$
  select make_interval(hours => coalesce((select prazo_cancel_h from public.app_config where id = 1), 24)) $$;

-- Preço de uma hora: faixa de horário > dia da semana > valor padrão.
create or replace function public.preco_hora(d date, h int) returns numeric
language plpgsql stable security definer set search_path = public as $$
declare c public.app_config; r jsonb; dow int := extract(dow from d)::int;
begin
  select * into c from public.app_config where id = 1;
  for r in select * from jsonb_array_elements(coalesce(c.precos -> 'porHora', '[]'::jsonb)) loop
    if h >= (r ->> 'de')::int and h < (r ->> 'ate')::int
       and (jsonb_typeof(r -> 'dias') is distinct from 'array' or (r -> 'dias') @> to_jsonb(dow)) then
      return (r ->> 'valor')::numeric;
    end if;
  end loop;
  if coalesce(c.precos -> 'porDia', '{}'::jsonb) ? dow::text then return (c.precos -> 'porDia' ->> dow::text)::numeric; end if;
  return c.valor_hora;
end $$;
-- Acima do limite de horas: dentro de um período = valor do período; diária; ou períodos inteiros em sequência.
-- Retorna null quando o intervalo não se encaixa (ex.: 11h às 15h): nesse caso o dentista fala com a Dra. Thalia.
create or replace function public.preco_periodos(h1 int, h2 int) returns numeric
language plpgsql stable security definer set search_path = public as $$
declare c public.app_config; p jsonb; acc numeric := 0; cur int := h1;
begin
  select * into c from public.app_config where id = 1;
  for p in select * from jsonb_array_elements(coalesce(c.periodos, '[]'::jsonb)) loop
    if h1 >= (p ->> 'de')::int and h2 <= (p ->> 'ate')::int then return (p ->> 'valor')::numeric; end if;
  end loop;
  if jsonb_typeof(c.diaria) = 'object' and h1 = (c.diaria ->> 'de')::int and h2 >= (c.diaria ->> 'ate')::int then
    acc := (c.diaria ->> 'valor')::numeric; cur := (c.diaria ->> 'ate')::int;
  end if;
  while cur < h2 loop
    select x into p from jsonb_array_elements(coalesce(c.periodos, '[]'::jsonb)) x where (x ->> 'de')::int = cur and (x ->> 'ate')::int <= h2 limit 1;
    if p is null then return null; end if;
    acc := acc + (p ->> 'valor')::numeric; cur := (p ->> 'ate')::int;
  end loop;
  return acc;
end $$;

create or replace function public.usa_periodo(h1 int, h2 int) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(h2 - h1 > c.limite_horas and jsonb_array_length(coalesce(c.periodos, '[]'::jsonb)) > 0, false) from public.app_config c where c.id = 1
$$;

create or replace function public.preco_reserva(d date, h1 int, h2 int) returns numeric
language plpgsql stable security definer set search_path = public as $$
declare t numeric := 0; v numeric; h int;
begin
  if public.usa_periodo(h1, h2) then return public.preco_periodos(h1, h2); end if;
  for h in h1 .. h2 - 1 loop
    v := public.preco_hora(d, h);
    if v is null then return null; end if;
    t := t + v;
  end loop;
  return t;
end $$;

-- Antes de gravar uma reserva: calcula o valor e confere pagamentos em atraso.
create or replace function public.antes_reserva() returns trigger
language plpgsql security definer set search_path = public as $$
declare lim int; v_tel text;
begin
  if new.origem = 'bloqueio' then return new; end if;
  if new.valor is null then new.valor := public.preco_reserva(new.date, new.h_from, new.h_to); end if;
  if public.is_admin() or coalesce(current_setting('app.bypass', true), '') = 'on' then return new; end if;
  -- Mais horas que o limite, fora de um período/diária: só combinando com a Dra. Thalia.
  if public.usa_periodo(new.h_from, new.h_to) and public.preco_periodos(new.h_from, new.h_to) is null then raise exception 'FORA_DO_PERIODO'; end if;
  select limite_atraso_dias into lim from public.app_config where id = 1;
  if lim is null then return new; end if;
  v_tel := right(regexp_replace(coalesce(new.tel, ''), '\D', '', 'g'), 10);
  if exists (
    select 1 from public.bookings b
    where b.status = 'ativo' and not b.pago and b.origem <> 'bloqueio' and coalesce(b.valor, 0) > 0
      and b.date < public.agora_local()::date - lim
      and ((new.dentist_id is not null and b.dentist_id = new.dentist_id)
           or (length(v_tel) = 10 and right(regexp_replace(b.tel, '\D', '', 'g'), 10) = v_tel))
  ) then
    raise exception 'PAGAMENTO_PENDENTE';
  end if;
  return new;
end $$;
drop trigger if exists antes_reserva on public.bookings;
create trigger antes_reserva before insert on public.bookings for each row execute function public.antes_reserva();

-- O valor gravado só muda pela administradora.
create or replace function public.proteger_valor() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if not (coalesce(current_setting('app.bypass', true), '') = 'on' or public.is_admin()) then new.valor := old.valor; end if;
  return new;
end $$;
drop trigger if exists proteger_valor on public.bookings;
create trigger proteger_valor before update on public.bookings for each row execute function public.proteger_valor();

-- Ajustes que o site precisa mostrar (sem dados sensíveis).
create or replace function public.config_publica() returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object('valorHora', c.valor_hora, 'precos', c.precos, 'pacotes', c.pacotes, 'abre', c.abre, 'fecha', c.fecha,
    'diasAbertos', to_jsonb(c.dias), 'prazoCancelamentoH', c.prazo_cancel_h, 'pix', c.pix_chave, 'pixNome', c.pix_nome, 'pixCidade', c.pix_cidade,
    'regras', c.regras, 'checklist', c.checklist, 'espaco', c.espaco, 'limiteAtrasoDias', c.limite_atraso_dias,
    'limiteHoras', c.limite_horas, 'periodos', c.periodos, 'diaria', c.diaria, 'endereco', c.endereco, 'whatsapp', c.whatsapp)
  from public.app_config c where c.id = 1
$$;
grant execute on function public.config_publica() to anon, authenticated;

create or replace function public.config_admin() returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare c public.app_config;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  select * into c from public.app_config where id = 1;
  return public.config_publica() || jsonb_build_object('lembretePagamento', c.lembrete_pagamento, 'relatorioMensal', c.relatorio_mensal,
    'agendaToken', c.agenda_token, 'pushUrl', c.push_url, 'emailAdmin', c.email_admin);
end $$;

create or replace function public.lista_texto(p jsonb, max_itens int, max_len int) returns jsonb language plpgsql immutable as $$
begin
  if p is null or jsonb_typeof(p) = 'null' then return null; end if;
  if jsonb_typeof(p) <> 'array' or jsonb_array_length(p) > max_itens
     or exists (select 1 from jsonb_array_elements(p) e where jsonb_typeof(e) <> 'string' or length(e #>> '{}') > max_len) then
    raise exception 'DADOS_INVALIDOS';
  end if;
  return (select coalesce(jsonb_agg(trim(e #>> '{}')), '[]'::jsonb) from jsonb_array_elements(p) e where trim(e #>> '{}') <> '');
end $$;

-- Salva os ajustes do painel. Só altera os campos enviados.
create or replace function public.salvar_ajustes(p jsonb) returns void
language plpgsql security definer set search_path = public as $$
declare c public.app_config; v numeric; r jsonb; k text;
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  if jsonb_typeof(p) <> 'object' then raise exception 'DADOS_INVALIDOS'; end if;
  select * into c from public.app_config where id = 1;
  if p ? 'valorHora' then c.valor_hora := nullif(p ->> 'valorHora', '')::numeric; end if;
  if p ? 'precos' then
    if jsonb_typeof(p -> 'precos') <> 'object' then raise exception 'DADOS_INVALIDOS'; end if;
    for k in select jsonb_object_keys(coalesce(p -> 'precos' -> 'porDia', '{}'::jsonb)) loop
      if k !~ '^[0-6]$' or coalesce((p -> 'precos' -> 'porDia' ->> k)::numeric, -1) < 0 then raise exception 'DADOS_INVALIDOS'; end if;
    end loop;
    for r in select * from jsonb_array_elements(coalesce(p -> 'precos' -> 'porHora', '[]'::jsonb)) loop
      if coalesce((r ->> 'de')::int, -1) < 0 or coalesce((r ->> 'ate')::int, 99) > 24 or (r ->> 'de')::int >= (r ->> 'ate')::int or coalesce((r ->> 'valor')::numeric, -1) < 0 then raise exception 'DADOS_INVALIDOS'; end if;
    end loop;
    c.precos := jsonb_build_object('porDia', coalesce(p -> 'precos' -> 'porDia', '{}'::jsonb), 'porHora', coalesce(p -> 'precos' -> 'porHora', '[]'::jsonb));
  end if;
  if p ? 'pacotes' then
    if jsonb_typeof(p -> 'pacotes') <> 'array' or jsonb_array_length(p -> 'pacotes') > 12 then raise exception 'DADOS_INVALIDOS'; end if;
    for r in select * from jsonb_array_elements(p -> 'pacotes') loop
      if coalesce((r ->> 'horas')::numeric, 0) <= 0 or coalesce((r ->> 'valor')::numeric, -1) < 0 then raise exception 'DADOS_INVALIDOS'; end if;
    end loop;
    c.pacotes := p -> 'pacotes';
  end if;
  if p ? 'abre' then c.abre := (p ->> 'abre')::int; end if;
  if p ? 'fecha' then c.fecha := (p ->> 'fecha')::int; end if;
  if p ? 'diasAbertos' then
    c.dias := array(select distinct x::int from jsonb_array_elements_text(p -> 'diasAbertos') x order by 1);
    if exists (select 1 from unnest(c.dias) d where d < 0 or d > 6) then raise exception 'DADOS_INVALIDOS'; end if;
  end if;
  if p ? 'prazoCancelamentoH' then c.prazo_cancel_h := (p ->> 'prazoCancelamentoH')::int; end if;
  if p ? 'pix' then c.pix_chave := left(nullif(trim(p ->> 'pix'), ''), 77); end if;
  if p ? 'pixNome' then c.pix_nome := left(nullif(trim(p ->> 'pixNome'), ''), 25); end if;
  if p ? 'pixCidade' then c.pix_cidade := coalesce(left(nullif(trim(p ->> 'pixCidade'), ''), 15), 'Ipatinga'); end if;
  if p ? 'regras' then c.regras := public.lista_texto(p -> 'regras', 30, 400); end if;
  if p ? 'checklist' then c.checklist := public.lista_texto(p -> 'checklist', 20, 200); end if;
  if p ? 'espaco' then
    if jsonb_typeof(p -> 'espaco') <> 'object' then raise exception 'DADOS_INVALIDOS'; end if;
    c.espaco := jsonb_build_object(
      'equipamentos', coalesce(public.lista_texto(p -> 'espaco' -> 'equipamentos', 40, 200), '[]'::jsonb),
      'inclusos', coalesce(public.lista_texto(p -> 'espaco' -> 'inclusos', 40, 200), '[]'::jsonb),
      'levar', coalesce(public.lista_texto(p -> 'espaco' -> 'levar', 40, 200), '[]'::jsonb),
      'chegada', left(coalesce(p -> 'espaco' ->> 'chegada', ''), 300), 'saida', left(coalesce(p -> 'espaco' ->> 'saida', ''), 300),
      'wifi', left(coalesce(p -> 'espaco' ->> 'wifi', ''), 120));
  end if;
  if p ? 'limiteHoras' then c.limite_horas := (p ->> 'limiteHoras')::int; if c.limite_horas < 1 or c.limite_horas > 24 then raise exception 'DADOS_INVALIDOS'; end if; end if;
  if p ? 'periodos' then
    if jsonb_typeof(p -> 'periodos') <> 'array' or jsonb_array_length(p -> 'periodos') > 6 then raise exception 'DADOS_INVALIDOS'; end if;
    for r in select * from jsonb_array_elements(p -> 'periodos') loop
      if coalesce((r ->> 'de')::int, -1) < 0 or coalesce((r ->> 'ate')::int, 99) > 24 or (r ->> 'de')::int >= (r ->> 'ate')::int or coalesce((r ->> 'valor')::numeric, -1) < 0 then raise exception 'DADOS_INVALIDOS'; end if;
    end loop;
    c.periodos := p -> 'periodos';
  end if;
  if p ? 'diaria' then
    if jsonb_typeof(p -> 'diaria') = 'null' then c.diaria := null;
    elsif coalesce((p -> 'diaria' ->> 'de')::int, -1) < 0 or coalesce((p -> 'diaria' ->> 'ate')::int, 99) > 24 or (p -> 'diaria' ->> 'de')::int >= (p -> 'diaria' ->> 'ate')::int or coalesce((p -> 'diaria' ->> 'valor')::numeric, -1) < 0 then raise exception 'DADOS_INVALIDOS';
    else c.diaria := jsonb_build_object('de', (p -> 'diaria' ->> 'de')::int, 'ate', (p -> 'diaria' ->> 'ate')::int, 'valor', (p -> 'diaria' ->> 'valor')::numeric); end if;
  end if;
  if p ? 'limiteAtrasoDias' then c.limite_atraso_dias := nullif(p ->> 'limiteAtrasoDias', '')::int; end if;
  if p ? 'lembretePagamento' then c.lembrete_pagamento := (p ->> 'lembretePagamento')::boolean; end if;
  if p ? 'relatorioMensal' then c.relatorio_mensal := (p ->> 'relatorioMensal')::boolean; end if;
  update public.app_config set valor_hora = c.valor_hora, precos = c.precos, pacotes = c.pacotes, abre = c.abre, fecha = c.fecha, dias = c.dias,
    prazo_cancel_h = c.prazo_cancel_h, pix_chave = c.pix_chave, pix_nome = c.pix_nome, pix_cidade = c.pix_cidade, regras = c.regras,
    checklist = c.checklist, espaco = c.espaco, limite_atraso_dias = c.limite_atraso_dias, lembrete_pagamento = c.lembrete_pagamento,
    relatorio_mensal = c.relatorio_mensal, limite_horas = c.limite_horas, periodos = c.periodos, diaria = c.diaria, atualizado_em = now()
  where id = 1;
  -- Reservas ainda sem valor (feitas antes de definir o preço) passam a ter o valor atual.
  if p ? 'valorHora' or p ? 'precos' or p ? 'periodos' or p ? 'diaria' or p ? 'limiteHoras' then
    update public.bookings set valor = public.preco_reserva(date, h_from, h_to)
    where valor is null and origem <> 'bloqueio' and status = 'ativo' and not pago;
  end if;
exception
  when invalid_text_representation or numeric_value_out_of_range or check_violation or invalid_parameter_value then raise exception 'DADOS_INVALIDOS';
end $$;
revoke execute on function public.config_admin() from public, anon;
revoke execute on function public.salvar_ajustes(jsonb) from public, anon;
grant execute on function public.config_admin() to authenticated;
grant execute on function public.salvar_ajustes(jsonb) to authenticated;

-- ---------- Cobrança de pagamentos pendentes (e-mail e celular, a cada 3 dias) ----------
create table if not exists public.cobrancas (dentist_id uuid primary key references public.dentists (id) on delete cascade, enviado_em timestamptz not null default now());
alter table public.cobrancas enable row level security;

create or replace function public.brl(v numeric) returns text language sql immutable as $$
  select 'R$ ' || replace(replace(replace(to_char(coalesce(v, 0), 'FM999,999,990.00'), ',', '#'), '.', ','), '#', '.')
$$;

create or replace function public.cobrar_pendentes() returns int
language plpgsql security definer set search_path = public as $$
declare r record; c public.app_config; n int := 0; lista text;
begin
  select * into c from public.app_config where id = 1;
  if not c.lembrete_pagamento then return 0; end if;
  for r in
    select b.dentist_id, d.nome, d.email, count(*) as qtd, sum(b.valor) as total
    from public.bookings b join public.dentists d on d.id = b.dentist_id
    where b.status = 'ativo' and not b.pago and b.origem <> 'bloqueio' and coalesce(b.valor, 0) > 0
      and b.comprovante_em is null and b.comprovante_path is null and b.date < public.agora_local()::date
      and not exists (select 1 from public.cobrancas k where k.dentist_id = b.dentist_id and k.enviado_em > now() - interval '3 days')
    group by b.dentist_id, d.nome, d.email
  loop
    select string_agg('<li>' || public.quando_txt(b.date, b.h_from, b.h_to) || ' · ' || public.brl(b.valor) || '</li>', '' order by b.date) into lista
    from public.bookings b where b.dentist_id = r.dentist_id and b.status = 'ativo' and not b.pago and b.origem <> 'bloqueio'
      and coalesce(b.valor, 0) > 0 and b.comprovante_em is null and b.comprovante_path is null and b.date < public.agora_local()::date;
    perform public.enviar_email(r.email, r.nome, 'Pagamento pendente · ' || public.brl(r.total),
      '<p>Olá, ' || public.esc_html(split_part(r.nome, ' ', 1)) || '!</p><p>Consta pagamento pendente do uso do consultório:</p><ul>' || lista || '</ul>'
      || '<p style="font-size:17px"><b>Total: ' || public.brl(r.total) || '</b></p>'
      || coalesce('<p>Chave Pix: <b>' || public.esc_html(c.pix_chave) || '</b></p>', '')
      || '<p>Na área do dentista, em Financeiro, você encontra o Pix copia e cola e pode enviar o comprovante.</p>'
      || coalesce('<p><a href="' || c.site_url || '/#dentista" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Abrir minha área</a></p>', '')
      || '<p style="color:#7a6a6e">Se você já pagou, envie o comprovante e desconsidere este aviso.</p>');
    perform public.push_para(array[r.dentist_id], 'Pagamento pendente · ' || public.brl(r.total),
      r.qtd || case when r.qtd = 1 then ' reserva aguardando pagamento.' else ' reservas aguardando pagamento.' end || ' Toque para ver o Pix.', './#dentista', 'cobranca');
    insert into public.cobrancas (dentist_id, enviado_em) values (r.dentist_id, now())
      on conflict (dentist_id) do update set enviado_em = excluded.enviado_em;
    n := n + 1;
  end loop;
  return n;
end $$;
revoke execute on function public.cobrar_pendentes() from public, anon, authenticated;

-- ---------- Relatório do mês por e-mail ----------
create or replace function public.relatorio_html(p_mes date) returns text
language plpgsql stable security definer set search_path = public as $$
declare
  ini date := date_trunc('month', p_mes)::date; fim date := (date_trunc('month', p_mes) + interval '1 month')::date;
  c public.app_config; q int; hrs int; prev numeric; v_pago numeric; v_aberto numeric; canc int; cap int; nota numeric; nnotas int; novos int; probs int;
  sem_valor int; top text; mes text;
begin
  select * into c from public.app_config where id = 1;
  select count(*), coalesce(sum(h_to - h_from), 0), sum(valor), coalesce(sum(valor) filter (where pago), 0), coalesce(sum(valor) filter (where not pago), 0), count(*) filter (where valor is null)
    into q, hrs, prev, v_pago, v_aberto, sem_valor
  from public.bookings where status = 'ativo' and origem <> 'bloqueio' and date >= ini and date < fim;
  select count(*) into canc from public.bookings where status = 'cancelado' and origem <> 'bloqueio' and date >= ini and date < fim;
  select count(*) * (c.fecha - c.abre) into cap from generate_series(ini, fim - 1, interval '1 day') g where extract(dow from g)::int = any (c.dias);
  select avg((avaliacao ->> 'nota')::numeric), count(*) into nota, nnotas from public.bookings where avaliacao is not null and date >= ini and date < fim;
  select count(*) into novos from public.dentists where criado_em >= ini and criado_em < fim;
  select count(*) into probs from public.problemas where status = 'aberto';
  select string_agg('<tr><td style="padding:6px 0;border-bottom:1px solid #efe4e4">' || public.esc_html(nome) || '</td><td style="padding:6px 0;border-bottom:1px solid #efe4e4;text-align:right">' || horas || 'h</td><td style="padding:6px 0;border-bottom:1px solid #efe4e4;text-align:right">' || coalesce(public.brl(total), '—') || '</td></tr>', '' order by horas desc)
    into top from (select nome, sum(h_to - h_from) as horas, sum(valor) as total from public.bookings
                   where status = 'ativo' and origem <> 'bloqueio' and date >= ini and date < fim group by nome order by 2 desc limit 8) t;
  mes := (array['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'])[extract(month from ini)::int] || ' de ' || extract(year from ini);
  return '<p>Olá, Dra. Thalia!</p><p>Este é o resumo do consultório em <b>' || mes || '</b>.</p>'
    || '<table style="width:100%;border-collapse:collapse;font-size:15px">'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Reservas</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || q || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Horas reservadas</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || hrs || 'h</b>' || case when cap > 0 then ' (' || round(100.0 * hrs / cap) || '% de ocupação)' else '' end || '</td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Receita prevista</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || coalesce(public.brl(prev), 'Valor a definir') || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Recebido</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || public.brl(v_pago) || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Em aberto</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || public.brl(v_aberto) || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Cancelamentos</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || canc || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Dentistas novos</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || novos || '</b></td></tr>'
    || '<tr><td style="padding:8px 0;border-bottom:1px solid #efe4e4">Avaliação média</td><td style="text-align:right;border-bottom:1px solid #efe4e4"><b>' || coalesce(to_char(nota, 'FM0D0') || ' de 5 (' || nnotas || ')', 'Sem avaliações') || '</b></td></tr>'
    || '<tr><td style="padding:8px 0">Problemas em aberto</td><td style="text-align:right"><b>' || probs || '</b></td></tr></table>'
    || case when sem_valor > 0 then '<p style="color:#7a6a6e">' || sem_valor || ' reserva(s) sem valor definido não entram na receita.</p>' else '' end
    || coalesce('<h3 style="font-family:Georgia,serif;color:#590117;margin:22px 0 6px">Por dentista</h3><table style="width:100%;border-collapse:collapse;font-size:14px">' || top || '</table>', '')
    || coalesce('<p style="margin-top:20px"><a href="' || c.site_url || '/#admin" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Abrir o painel</a></p>', '');
end $$;
revoke execute on function public.relatorio_html(date) from public, anon, authenticated;

create or replace function public.enviar_relatorio(p_mes date default null) returns boolean
language plpgsql security definer set search_path = public as $$
declare c public.app_config; m date := coalesce(p_mes, (date_trunc('month', public.agora_local()) - interval '1 month')::date); ok boolean; mes text;
begin
  if auth.uid() is not null and not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  select * into c from public.app_config where id = 1;
  mes := (array['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'])[extract(month from m)::int];
  ok := public.enviar_email(c.email_admin, 'Dra. Thalia', 'Relatório de ' || mes || ' · consultório', public.relatorio_html(m));
  if ok then perform public.push_admins('Relatório de ' || mes || ' enviado', 'O resumo do mês chegou no seu e-mail.', 'relatorio'); end if;
  return ok;
end $$;
revoke execute on function public.enviar_relatorio(date) from public, anon;
grant execute on function public.enviar_relatorio(date) to authenticated;

-- Rotina diária (9h): cobrança de pendências e, no dia 1º, o relatório do mês anterior.
create or replace function public.rotina_diaria() returns void
language plpgsql security definer set search_path = public as $$
declare c public.app_config; este_mes date := date_trunc('month', public.agora_local())::date;
begin
  begin perform public.cobrar_pendentes(); exception when others then null; end;
  select * into c from public.app_config where id = 1;
  if c.relatorio_mensal and extract(day from public.agora_local()) <= 3 and (c.ultimo_relatorio is null or c.ultimo_relatorio < este_mes) then
    if public.enviar_relatorio((este_mes - interval '1 month')::date) then
      update public.app_config set ultimo_relatorio = este_mes where id = 1;
    end if;
  end if;
end $$;
revoke execute on function public.rotina_diaria() from public, anon, authenticated;

do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.unschedule(jobid) from cron.job where jobname = 'rotina-diaria-consultorio';
    perform cron.schedule('rotina-diaria-consultorio', '0 12 * * *', 'select public.rotina_diaria()');
  end if;
exception when others then raise notice 'Não foi possível agendar a rotina diária: ative pg_cron em Database > Extensions e rode de novo.';
end $$;

-- ---------- Agenda do consultório no Google Agenda (link secreto, só leitura) ----------
create or replace function public.ics_txt(t text) returns text language sql immutable as $$
  select replace(replace(replace(replace(replace(coalesce(t, ''), '\', '\\'), ';', '\;'), ',', '\,'), E'\r', ''), E'\n', '\n')
$$;
create or replace function public.ics_utc(d date, h int) returns text language sql immutable as $$
  select to_char(((d + make_time(h, 0, 0)) at time zone 'America/Sao_Paulo') at time zone 'UTC', 'YYYYMMDD"T"HH24MISS"Z"')
$$;
create or replace function public.ics_fold(l text) returns text language plpgsql immutable as $$
declare o text := ''; begin
  while length(l) > 70 loop o := o || left(l, 70) || E'\r\n '; l := substr(l, 71); end loop;
  return o || l || E'\r\n';
end $$;

create or replace function public.agenda_ics(p_token text) returns text
language plpgsql stable security definer set search_path = public as $$
declare c public.app_config; r record; o text; stamp text := to_char(now() at time zone 'UTC', 'YYYYMMDD"T"HH24MISS"Z"');
begin
  select * into c from public.app_config where id = 1;
  if c.agenda_token is null or p_token is null or length(p_token) < 20 or p_token <> c.agenda_token then raise exception 'TOKEN_INVALIDO'; end if;
  o := E'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Consultorio Thalia Santiago//Reservas//PT\r\nCALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\n'
    || public.ics_fold('X-WR-CALNAME:' || public.ics_txt('Consultório · reservas'))
    || E'X-WR-TIMEZONE:America/Sao_Paulo\r\nREFRESH-INTERVAL;VALUE=DURATION:PT1H\r\nX-PUBLISHED-TTL:PT1H\r\n';
  for r in
    select * from public.bookings where status = 'ativo' and date between public.agora_local()::date - 60 and public.agora_local()::date + 180 order by date, h_from
  loop
    o := o || E'BEGIN:VEVENT\r\n' || 'UID:' || r.id || E'@consultorio-thalia\r\n' || 'DTSTAMP:' || stamp || E'\r\n'
      || 'DTSTART:' || public.ics_utc(r.date, r.h_from) || E'\r\n' || 'DTEND:' || public.ics_utc(r.date, r.h_to) || E'\r\n'
      || public.ics_fold('SUMMARY:' || public.ics_txt(case when r.origem = 'bloqueio' then 'Bloqueado · ' || r.nome else r.nome || ' · ' || (r.h_to - r.h_from) || 'h' end))
      || public.ics_fold('DESCRIPTION:' || public.ics_txt(case when r.origem = 'bloqueio' then 'Horário bloqueado no painel.' else
           concat_ws(E'\n', 'WhatsApp: ' || r.tel, 'CRO: ' || r.cro, 'Pedido especial: ' || r.pedido,
             case when r.valor is not null then 'Valor: ' || public.brl(r.valor) || case when r.pago then ' (pago)' else ' (em aberto)' end end) end))
      || public.ics_fold('LOCATION:' || public.ics_txt(c.endereco))
      || E'END:VEVENT\r\n';
  end loop;
  return o || E'END:VCALENDAR\r\n';
end $$;
grant execute on function public.agenda_ics(text) to anon, authenticated;

create or replace function public.gerar_token_agenda() returns text
language plpgsql security definer set search_path = public as $$
declare t text := replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', '');
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  update public.app_config set agenda_token = t where id = 1;
  return t;
end $$;
revoke execute on function public.gerar_token_agenda() from public, anon;
grant execute on function public.gerar_token_agenda() to authenticated;

-- ---------- Aprovação de cadastros: conta nova só reserva depois que a Dra. Thalia liberar ----------
do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'dentists' and column_name = 'status') then
    alter table public.dentists add column status text;
    update public.dentists set status = 'liberado' where status is null;  -- quem já tinha conta continua com acesso
    alter table public.dentists alter column status set not null;
  end if;
end $$;
alter table public.dentists alter column status set default 'pendente';
alter table public.dentists add column if not exists status_em timestamptz;
alter table public.dentists drop constraint if exists dentists_status_ok;
alter table public.dentists add constraint dentists_status_ok check (status in ('pendente', 'liberado', 'bloqueado'));

create or replace function public.dentista_liberado() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.dentists where id = auth.uid() and status = 'liberado')
$$;
grant execute on function public.dentista_liberado() to anon, authenticated;

-- Só a administradora muda o status (o próprio dentista não consegue se liberar).
create or replace function public.proteger_dentista() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    if not public.is_admin() then new.status := 'pendente'; end if;
    return new;
  end if;
  if not (coalesce(current_setting('app.bypass', true), '') = 'on' or public.is_admin()) then
    new.status := old.status; new.status_em := old.status_em;
  elsif new.status is distinct from old.status then
    new.status_em := now();
  end if;
  return new;
end $$;
drop trigger if exists proteger_dentista on public.dentists;
create trigger proteger_dentista before insert or update on public.dentists for each row execute function public.proteger_dentista();

-- Lista de espera e avisos de problema só para contas liberadas.
drop policy if exists "espera: entrar" on public.espera;
create policy "espera: entrar" on public.espera for insert with check (dentist_id = auth.uid() and public.dentista_liberado());
drop policy if exists "problemas: enviar" on public.problemas;
create policy "problemas: enviar" on public.problemas for insert with check (dentist_id = auth.uid() and public.dentista_liberado());

-- Liberar, bloquear ou voltar para pendente (painel da Dra. Thalia).
create or replace function public.definir_status_dentista(p_id uuid, p_status text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  if p_status not in ('pendente', 'liberado', 'bloqueado') then raise exception 'DADOS_INVALIDOS'; end if;
  perform set_config('app.bypass', 'on', true);
  update public.dentists set status = p_status where id = p_id;
  if not found then raise exception 'DENTISTA_NAO_ENCONTRADO'; end if;
end $$;
revoke execute on function public.definir_status_dentista(uuid, text) from public, anon;
grant execute on function public.definir_status_dentista(uuid, text) to authenticated;

-- Avisos: cadastro novo (para a Dra. Thalia) e acesso liberado (para o dentista).
create or replace function public.aviso_cadastro() returns trigger
language plpgsql security definer set search_path = public as $$
declare c public.app_config;
begin
  select * into c from public.app_config where id = 1;
  if tg_op = 'INSERT' and new.status = 'pendente' then
    perform public.push_admins('Novo cadastro · ' || new.nome, coalesce(new.cro || ' · ', '') || new.whatsapp || '. Toque para liberar ou bloquear o acesso.', 'cadastro-' || new.id);
    perform public.enviar_email(c.email_admin, 'Dra. Thalia', 'Novo cadastro para liberar · ' || new.nome,
      '<p>Um novo dentista se cadastrou e está aguardando a sua liberação:</p>'
      || '<p style="font-size:17px"><b>' || public.esc_html(new.nome) || '</b></p><p>'
      || coalesce('CRO: ' || public.esc_html(new.cro) || '<br>', '') || 'WhatsApp: ' || public.esc_html(new.whatsapp)
      || coalesce('<br>E-mail: ' || public.esc_html(new.email), '') || coalesce('<br>Especialidade: ' || public.esc_html(new.especialidade), '') || '</p>'
      || '<p>Até você liberar, ele não consegue reservar.</p>'
      || coalesce('<p><a href="' || c.site_url || '/#admin" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Liberar ou bloquear no painel</a></p>', ''));
  elsif tg_op = 'UPDATE' and new.status = 'liberado' and old.status is distinct from 'liberado' then
    perform public.enviar_email(new.email, new.nome, 'Seu acesso ao consultório foi liberado',
      '<p>Olá, ' || public.esc_html(split_part(new.nome, ' ', 1)) || '!</p><p>A Dra. Thalia liberou o seu acesso. Você já pode reservar o consultório pela sua área.</p>'
      || coalesce('<p><a href="' || c.site_url || '/#dentista" style="display:inline-block;background:#590117;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">Reservar horário</a></p>', ''));
    perform public.push_para(array[new.id], 'Acesso liberado', 'A Dra. Thalia liberou seu acesso. Você já pode reservar o consultório.', './#dentista', 'liberado');
  end if;
  return new;
exception when others then return new;
end $$;
drop trigger if exists aviso_cadastro on public.dentists;
create trigger aviso_cadastro after insert or update of status on public.dentists for each row execute function public.aviso_cadastro();


-- Pergunta frequente atualizada para o novo jeito de reservar (só troca se o texto nunca foi editado).
update public.faq set resposta = 'Crie sua conta na Área do dentista. Assim que a Dra. Thalia liberar o seu acesso (você recebe um e-mail), escolha o dia e as horas livres e confirme. O horário fica bloqueado para você na hora.'
where pergunta = 'Como faço para reservar?' and resposta = 'Toque em "Agendar horário", informe seus dados, escolha o dia e as horas livres e confirme. O horário fica bloqueado para você na hora.';

-- ---------- Contato do consultório (out/2026) ----------
alter table public.app_config alter column endereco set default 'Rua Juiz de Fora, 52, Galeria Êxito, sala 208, Centro, Ipatinga/MG';
alter table public.app_config alter column whatsapp set default '5531995745413';
update public.app_config set endereco = 'Rua Juiz de Fora, 52, Galeria Êxito, sala 208, Centro, Ipatinga/MG' where id = 1 and endereco = 'Rua Juiz de Fora, Centro, Ipatinga/MG';
update public.app_config set whatsapp = '5531995745413' where id = 1 and whatsapp = '553185825564';

-- ---------- Excluir dentista (a administradora). As reservas antigas ficam no histórico, com o nome. ----------
create or replace function public.excluir_dentista(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception 'SEM_PERMISSAO'; end if;
  if exists (select 1 from public.admins where user_id = p_id) then raise exception 'SEM_PERMISSAO'; end if;
  if not exists (select 1 from public.dentists where id = p_id) then raise exception 'DENTISTA_NAO_ENCONTRADO'; end if;
  begin
    delete from auth.users where id = p_id;               -- apaga o login (e o cadastro, em cascata)
  exception when insufficient_privilege then
    delete from public.dentists where id = p_id;          -- sem permissão no login: apaga só o cadastro (a pessoa perde o acesso à área)
  end;
  delete from public.dentists where id = p_id;
end $$;
revoke execute on function public.excluir_dentista(uuid) from public, anon;
grant execute on function public.excluir_dentista(uuid) to authenticated;

-- ---------- Pacientes da Dra. Thalia (só a administradora vê) ----------
create table if not exists public.pacientes (
  id uuid primary key default gen_random_uuid(),
  nome text not null check (length(trim(nome)) between 2 and 120),
  telefone text check (telefone is null or length(telefone) <= 30),
  cpf text check (cpf is null or length(cpf) <= 20),
  nascimento date,
  email text check (email is null or length(email) <= 120),
  endereco text check (endereco is null or length(endereco) <= 300),
  observacoes text check (observacoes is null or length(observacoes) <= 4000),
  criado_em timestamptz not null default now()
);
create table if not exists public.consultas (
  id uuid primary key default gen_random_uuid(),
  paciente_id uuid not null references public.pacientes (id) on delete cascade,
  data date not null,
  inicio time not null,
  fim time not null,
  status text not null default 'agendada' check (status in ('agendada', 'realizada', 'faltou', 'cancelada')),
  observacao text check (observacao is null or length(observacao) <= 1000),
  criado_em timestamptz not null default now(),
  check (fim > inicio)
);
create index if not exists consultas_data_idx on public.consultas (data);
create index if not exists consultas_paciente_idx on public.consultas (paciente_id);
create table if not exists public.evolucoes (
  id uuid primary key default gen_random_uuid(),
  paciente_id uuid not null references public.pacientes (id) on delete cascade,
  consulta_id uuid references public.consultas (id) on delete set null,
  data date not null default current_date,
  texto text not null check (length(trim(texto)) between 1 and 6000),
  criado_em timestamptz not null default now()
);
create index if not exists evolucoes_paciente_idx on public.evolucoes (paciente_id);
create table if not exists public.paciente_docs (
  id uuid primary key default gen_random_uuid(),
  paciente_id uuid not null references public.pacientes (id) on delete cascade,
  tipo text not null default 'outro' check (tipo in ('prontuario', 'orcamento', 'radiografia', 'outro')),
  nome text not null check (length(nome) <= 200),
  path text not null check (length(path) <= 400),
  tamanho bigint,
  criado_em timestamptz not null default now()
);
create index if not exists paciente_docs_paciente_idx on public.paciente_docs (paciente_id);
do $$
declare t text;
begin
  foreach t in array array['pacientes', 'consultas', 'evolucoes', 'paciente_docs'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "%s: administradora" on public.%I', t, t);
    execute format('create policy "%s: administradora" on public.%I for all using (public.is_admin()) with check (public.is_admin())', t, t);
  end loop;
end $$;

-- Consultas ocupam a agenda: para os dentistas, a hora fica "ocupada" (sem nenhum dado do paciente).
alter table public.slots alter column booking_id drop not null;
alter table public.slots add column if not exists consulta boolean not null default false;

create or replace function public.horas_da_consulta(i time, f time) returns setof int language sql immutable as $$
  select generate_series(extract(hour from i)::int, ceil(extract(epoch from f) / 3600)::int - 1)
$$;

create or replace function public.recalc_slots_consultas(d date) returns void
language plpgsql security definer set search_path = public as $$
begin
  if d is null then return; end if;
  delete from public.slots s where s.date = d and s.consulta and s.booking_id is null
    and not exists (select 1 from public.consultas c where c.data = d and c.status <> 'cancelada'
                    and s.hour in (select public.horas_da_consulta(c.inicio, c.fim)));
  insert into public.slots (date, hour, booking_id, consulta)
  select distinct d, h, null::uuid, true
  from public.consultas c, lateral public.horas_da_consulta(c.inicio, c.fim) h
  where c.data = d and c.status <> 'cancelada'
  on conflict (date, hour) do nothing;
end $$;
revoke execute on function public.recalc_slots_consultas(date) from public, anon, authenticated;

-- Antes de gravar: não pode cruzar com outra consulta nem com reserva de dentista ou bloqueio.
create or replace function public.checar_consulta() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'cancelada' then return new; end if;
  if extract(epoch from new.inicio)::int % 300 <> 0 or extract(epoch from new.fim)::int % 300 <> 0 then raise exception 'HORARIO_INVALIDO'; end if;
  if exists (select 1 from public.consultas c where c.data = new.data and c.id <> new.id and c.status <> 'cancelada'
             and c.inicio < new.fim and c.fim > new.inicio) then
    raise exception 'CONSULTA_CONFLITO';
  end if;
  if exists (select 1 from public.slots s where s.date = new.data and s.booking_id is not null
             and s.hour in (select public.horas_da_consulta(new.inicio, new.fim))) then
    raise exception 'HORARIO_OCUPADO';
  end if;
  return new;
end $$;
drop trigger if exists checar_consulta on public.consultas;
create trigger checar_consulta before insert or update on public.consultas for each row execute function public.checar_consulta();

create or replace function public.consulta_slots() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op in ('UPDATE', 'DELETE') then perform public.recalc_slots_consultas(old.data); end if;
  if tg_op in ('INSERT', 'UPDATE') then perform public.recalc_slots_consultas(new.data); end if;
  return null;
end $$;
drop trigger if exists consulta_slots on public.consultas;
create trigger consulta_slots after insert or update or delete on public.consultas for each row execute function public.consulta_slots();

-- Arquivos dos pacientes (prontuário, orçamento, radiografias): bucket privado, só a administradora.
do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'storage') then
    insert into storage.buckets (id, name, public) values ('pacientes', 'pacientes', false) on conflict (id) do nothing;
    drop policy if exists "pacientes: ver" on storage.objects;
    create policy "pacientes: ver" on storage.objects for select using (bucket_id = 'pacientes' and public.is_admin());
    drop policy if exists "pacientes: enviar" on storage.objects;
    create policy "pacientes: enviar" on storage.objects for insert with check (bucket_id = 'pacientes' and public.is_admin());
    drop policy if exists "pacientes: excluir" on storage.objects;
    create policy "pacientes: excluir" on storage.objects for delete using (bucket_id = 'pacientes' and public.is_admin());
  end if;
end $$;

do $$
declare t text;
begin
  foreach t in array array['pacientes', 'consultas', 'evolucoes', 'paciente_docs'] loop
    if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- ---------- Arquivos: fotos do consultório (públicas) e comprovantes (privados) ----------
do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'storage') then
    insert into storage.buckets (id, name, public) values ('fotos', 'fotos', true) on conflict (id) do nothing;
    insert into storage.buckets (id, name, public) values ('comprovantes', 'comprovantes', false) on conflict (id) do nothing;
    drop policy if exists "fotos: ver" on storage.objects;
    create policy "fotos: ver" on storage.objects for select using (bucket_id = 'fotos');
    drop policy if exists "fotos: enviar" on storage.objects;
    create policy "fotos: enviar" on storage.objects for insert with check (bucket_id = 'fotos' and public.is_admin());
    drop policy if exists "fotos: excluir" on storage.objects;
    create policy "fotos: excluir" on storage.objects for delete using (bucket_id = 'fotos' and public.is_admin());
    drop policy if exists "comprovantes: enviar" on storage.objects;
    create policy "comprovantes: enviar" on storage.objects for insert with check (bucket_id = 'comprovantes' and (storage.foldername(name))[1] = auth.uid()::text);
    drop policy if exists "comprovantes: ver" on storage.objects;
    create policy "comprovantes: ver" on storage.objects for select using (bucket_id = 'comprovantes' and ((storage.foldername(name))[1] = auth.uid()::text or public.is_admin()));
  end if;
end $$;

-- ---------- Atualização em tempo real ----------
do $$
declare t text;
begin
  foreach t in array array['slots', 'bookings', 'avisos', 'problemas', 'espera', 'dentists', 'faq'] loop
    if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- =====================================================================
-- DEPOIS de criar o usuário da Dra. Thalia em Authentication > Users,
-- rode só a linha abaixo trocando o e-mail:
--
-- insert into public.admins (user_id) select id from auth.users where email = 'EMAIL_DA_THALIA@exemplo.com';
-- =====================================================================
