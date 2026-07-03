-- SPEC-017 P1.2 — Canal WhatsApp multi-tenant (EXPAND-ONLY, sem destruição).
--
-- APPLY:   executar este arquivo no SQL Editor do Supabase (uma vez).
-- VERIFY:  select column_name from information_schema.columns
--            where table_name='integrations'
--              and column_name in ('provider','webhook_token_hash',
--                'webhook_token_prefix','base_url','alert_target',
--                'channel_status','last_seen_at');
--          -- deve retornar as 7 linhas. Nenhuma linha existente é alterada.
-- ROLLBACK: colunas novas são ignoradas pelo código legado; para reverter de
--          verdade (não recomendado): alter table public.integrations
--            drop column if exists <coluna>; -- para cada coluna abaixo.

alter table public.integrations
  add column if not exists provider text not null default 'z-api',
  add column if not exists webhook_token_hash text,
  add column if not exists webhook_token_prefix text,
  add column if not exists base_url text,
  add column if not exists alert_target jsonb,
  add column if not exists channel_status text,
  add column if not exists last_seen_at timestamptz;

-- Lookup do webhook por hash do token (rota /api/v1/webhook/{provider}/{token}).
create index if not exists idx_integrations_webhook_token_hash
  on public.integrations (webhook_token_hash)
  where webhook_token_hash is not null;

comment on column public.integrations.provider is
  'SPEC-017: z-api | evolution | uazapi (seam multi-provider; sem fallback silencioso)';
comment on column public.integrations.webhook_token_hash is
  'SPEC-017: sha256 do token de webhook por integração (plaintext NUNCA é gravado)';
comment on column public.integrations.alert_target is
  'SPEC-017 S17-3: {"number": "..."} destino do alerta de desconexão (nunca o próprio número de atendimento)';
