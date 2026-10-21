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
  ('Como faço para reservar?', 'Toque em "Agendar horário", informe seus dados, escolha o dia e as horas livres e confirme. O horário fica bloqueado para você na hora.', 1),
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
    || coalesce('<p style="color:#7a6a6e">Precisa cancelar? Pela área do dentista, até 24 horas antes: <a href="' || c.site_url || '/#dentista" style="color:#590117">abrir área do dentista</a>.</p>', ''));
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
  if antiga is distinct from p_publica then delete from public.push_subs; end if;
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
