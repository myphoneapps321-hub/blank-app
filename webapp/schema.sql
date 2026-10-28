-- =====================================================================
--  Indicateurs de performance des adductions de DRPN — schéma Supabase
--  À exécuter dans Supabase : SQL Editor -> coller -> Run
--  (puis exécuter seed.sql pour charger les données de départ)
-- =====================================================================

-- ---------- Tables ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  email text,
  role text not null default 'agent',   -- 'dr' (responsable) ou 'agent'
  secteur int,                            -- 1..4 pour un agent ; null pour la DR
  created_at timestamptz default now()
);

create table if not exists public.centres (
  id bigint generated always as identity primary key,
  centre text not null,
  secteur int not null,
  categorie int not null default 1,       -- 1 petites/moyennes · 2 grandes · 3 stations
  type text not null default 'potable',   -- 'potable' ou 'brute'
  lineaire numeric default 0,
  prod_sup numeric default 0, prod_sout numeric default 0, prod_dess numeric default 0,
  achat_dr numeric default 0, achat_ext numeric default 0, cession_dr numeric default 0,
  srm numeric default 0, amendis numeric default 0, pertes numeric default 0,
  updated_at timestamptz default now(),
  updated_by uuid
);

create table if not exists public.flux (
  id bigint generated always as identity primary key,
  source text not null,
  destination text not null,
  volume numeric default 0,
  secteur int,                            -- secteur de la source (cadrage agent)
  updated_at timestamptz default now(),
  updated_by uuid
);

-- ---------- Fonctions utilitaires (rôle / secteur de l'utilisateur) ----------
create or replace function public.my_role() returns text
  language sql stable security definer set search_path=public as
$$ select role from public.profiles where id = auth.uid() $$;

create or replace function public.my_secteur() returns int
  language sql stable security definer set search_path=public as
$$ select secteur from public.profiles where id = auth.uid() $$;

-- Création automatique d'une ligne profile à l'inscription d'un utilisateur
create or replace function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path=public as
$$ begin
  insert into public.profiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- Sécurité par ligne (RLS) ----------
alter table public.profiles enable row level security;
alter table public.centres  enable row level security;
alter table public.flux     enable row level security;

-- profiles : chacun lit son profil ; la DR lit tout
drop policy if exists p_profiles_select on public.profiles;
create policy p_profiles_select on public.profiles for select
  using ( id = auth.uid() or public.my_role() = 'dr' );

-- centres : lecture pour tout utilisateur connecté (consolidation + référentiel)
drop policy if exists p_centres_select on public.centres;
create policy p_centres_select on public.centres for select
  using ( auth.role() = 'authenticated' );
-- modification : la DR partout ; un agent uniquement son secteur
drop policy if exists p_centres_update on public.centres;
create policy p_centres_update on public.centres for update
  using ( public.my_role()='dr' or secteur = public.my_secteur() )
  with check ( public.my_role()='dr' or secteur = public.my_secteur() );
drop policy if exists p_centres_insert on public.centres;
create policy p_centres_insert on public.centres for insert
  with check ( public.my_role()='dr' or secteur = public.my_secteur() );
drop policy if exists p_centres_delete on public.centres;
create policy p_centres_delete on public.centres for delete
  using ( public.my_role()='dr' );

-- flux : mêmes règles (secteur = secteur de la source)
drop policy if exists p_flux_select on public.flux;
create policy p_flux_select on public.flux for select
  using ( auth.role() = 'authenticated' );
drop policy if exists p_flux_update on public.flux;
create policy p_flux_update on public.flux for update
  using ( public.my_role()='dr' or secteur = public.my_secteur() )
  with check ( public.my_role()='dr' or secteur = public.my_secteur() );
drop policy if exists p_flux_insert on public.flux;
create policy p_flux_insert on public.flux for insert
  with check ( public.my_role()='dr' or secteur = public.my_secteur() );
drop policy if exists p_flux_delete on public.flux;
create policy p_flux_delete on public.flux for delete
  using ( public.my_role()='dr' or secteur = public.my_secteur() );

-- ---------- Temps réel (consolidation automatique) ----------
alter publication supabase_realtime add table public.centres;
alter publication supabase_realtime add table public.flux;

-- =====================================================================
--  Après exécution : lancer seed.sql, puis créer les comptes
--  (Authentication -> Users) et affecter role/secteur dans profiles :
--    update profiles set role='dr'    where email='dr@...';
--    update profiles set role='agent', secteur=1 where email='spn1@...';
--    ... spn2/3/4
-- =====================================================================
