-- Technical WhatsApp sandbox guard
--
-- A tenant is treated as technical when companies.is_technical=true OR
-- companies.company_kind='technical'. The guard is fail-safe and does not affect
-- normal brokerages.
--
-- Goals:
-- 1) force observer_scope=insurers_only for technical tenants;
-- 2) mark learning_enabled=false/technical_test=true on the integration;
-- 3) block client/insured transcripts for technical tenants;
-- 4) namespace insurer observations so they can be validated without changing
--    the global production maps used by real brokerages.

create or replace function public.is_technical_company(p_company_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.companies c
    where c.id = p_company_id
      and (coalesce(c.is_technical, false) = true
           or lower(coalesce(c.company_kind, '')) = 'technical')
  );
$$;

create or replace function public.enforce_technical_whatsapp_integration()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.purpose = 'observer' and public.is_technical_company(new.company_id) then
    new.alert_target := coalesce(new.alert_target, '{}'::jsonb)
      || jsonb_build_object(
        'observer_scope', 'insurers_only',
        'technical_test', true,
        'learning_enabled', false,
        'history_clients_enabled', false
      );
  end if;
  return new;
end;
$$;

drop trigger if exists trg_integrations_technical_whatsapp_guard on public.integrations;
create trigger trg_integrations_technical_whatsapp_guard
before insert or update of company_id, purpose, alert_target
on public.integrations
for each row
execute function public.enforce_technical_whatsapp_integration();

create or replace function public.isolate_technical_observed_session()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if public.is_technical_company(new.company_id) then
    if new.insurer_key is not null and new.insurer_key not like 'technical__%' then
      new.insurer_key := 'technical__' || new.insurer_key;
    end if;
    new.summary := coalesce(new.summary, '{}'::jsonb)
      || jsonb_build_object('technical_test', true, 'global_learning', false);
  end if;
  return new;
end;
$$;

drop trigger if exists trg_observed_sessions_technical_isolation on public.observed_sessions;
create trigger trg_observed_sessions_technical_isolation
before insert or update of company_id, insurer_key, summary
on public.observed_sessions
for each row
execute function public.isolate_technical_observed_session();

create or replace function public.isolate_technical_observed_event()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if public.is_technical_company(new.company_id) then
    if new.insurer_key is not null and new.insurer_key not like 'technical__%' then
      new.insurer_key := 'technical__' || new.insurer_key;
    end if;
    new.media_meta := coalesce(new.media_meta, '{}'::jsonb)
      || jsonb_build_object('technical_test', true, 'global_learning', false);
  end if;
  return new;
end;
$$;

drop trigger if exists trg_observed_events_technical_isolation on public.observed_events;
create trigger trg_observed_events_technical_isolation
before insert or update of company_id, insurer_key, media_meta
on public.observed_events
for each row
execute function public.isolate_technical_observed_event();

create or replace function public.block_technical_attendance_capture()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if public.is_technical_company(new.company_id) then
    return null;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_attendance_sessions_technical_block on public.attendance_sessions;
create trigger trg_attendance_sessions_technical_block
before insert on public.attendance_sessions
for each row
execute function public.block_technical_attendance_capture();

drop trigger if exists trg_attendance_transcripts_technical_block on public.attendance_transcripts;
create trigger trg_attendance_transcripts_technical_block
before insert on public.attendance_transcripts
for each row
execute function public.block_technical_attendance_capture();

comment on function public.is_technical_company(uuid) is
  'True for platform/test tenants. Used to keep WhatsApp sandbox traffic outside production learning.';
comment on function public.enforce_technical_whatsapp_integration() is
  'Forces insurer-only silent observation and disables global learning for technical tenants.';
