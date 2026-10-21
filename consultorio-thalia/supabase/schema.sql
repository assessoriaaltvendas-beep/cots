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

-- Dentistas só podem alterar pedido, checklist, avaliação e aviso de comprovante.
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
  new.criado_em := old.criado_em;
  return new;
end $$;
drop trigger if exists proteger_booking on public.bookings;
create trigger proteger_booking before update on public.bookings
  for each row execute function public.proteger_booking();

-- Reserva atômica: cria a reserva e ocupa cada hora; se alguma hora já estiver ocupada, nada é gravado.
create or replace function public.reservar(
  p_nome text, p_cro text, p_tel text, p_date date, p_from int, p_to int,
  p_primeira boolean default false, p_pedido text default null, p_serie text default null, p_origem text default 'site'
) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_id uuid;
  v_dentist uuid;
  h int;
begin
  if coalesce(length(trim(p_nome)), 0) < 2 then raise exception 'NOME_INVALIDO'; end if;
  if length(regexp_replace(coalesce(p_tel, ''), '\D', '', 'g')) < 10 then raise exception 'TELEFONE_INVALIDO'; end if;
  if p_from < public.cfg_abre() or p_to > public.cfg_fecha() or p_to <= p_from then raise exception 'HORARIO_INVALIDO'; end if;
  if not (extract(dow from p_date)::int = any (public.cfg_dias())) then raise exception 'DIA_FECHADO'; end if;
  if (p_date + make_time(p_from, 0, 0)) <= public.agora_local() then raise exception 'HORARIO_PASSADO'; end if;
  if p_date > (public.agora_local()::date + 120) then raise exception 'DATA_DISTANTE'; end if;

  select id into v_dentist from public.dentists where id = auth.uid();

  insert into public.bookings (dentist_id, nome, cro, tel, primeira, date, h_from, h_to, pedido, serie, origem)
  values (v_dentist, trim(p_nome), nullif(trim(p_cro), ''), trim(p_tel), coalesce(p_primeira, false), p_date, p_from, p_to,
          nullif(trim(p_pedido), ''), p_serie, case when v_dentist is null then 'site' else coalesce(p_origem, 'site') end)
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
  update public.bookings set status = 'cancelado' where id = p_id;
  delete from public.slots where booking_id = p_id;
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

grant execute on function public.reservar(text, text, text, date, int, int, boolean, text, text, text) to anon, authenticated;
revoke execute on function public.cancelar(uuid) from public, anon;
grant execute on function public.cancelar(uuid) to authenticated;
grant execute on function public.is_admin() to anon, authenticated;

-- ---------- Atualização em tempo real ----------
do $$
declare t text;
begin
  foreach t in array array['slots', 'bookings', 'avisos', 'problemas', 'espera', 'dentists'] loop
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
