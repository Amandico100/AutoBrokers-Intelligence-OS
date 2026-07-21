-- SPEC-046 — Aposentadoria REVERSÍVEL das tabelas exclusivas do MVP morto.
--
-- Prova de morte (grep no repo pós-limpeza, 20/07/2026):
--   attendance_cases  -> nenhuma referência viva (rotas cases/* removidas)
--   corridor_runs     -> nenhuma referência viva (runtime TS removido)
--   dispatch_packets  -> nenhuma referência viva
-- (corridor_templates e tenant_corridors FICAM: usadas por lib/admin/tenant-corridor-*.)
--
-- Em vez de DROP + CSV no storage, as tabelas vão para o schema "graveyard":
-- dado intacto, PII continua dentro do banco (service-role only), e reverter
-- é um comando: ALTER TABLE graveyard.<t> SET SCHEMA public;
-- Colheita definitiva (DROP real) só numa migração futura, com o founder ciente.

CREATE SCHEMA IF NOT EXISTS graveyard;
REVOKE ALL ON SCHEMA graveyard FROM PUBLIC;
REVOKE ALL ON SCHEMA graveyard FROM anon, authenticated;

ALTER TABLE IF EXISTS public.attendance_cases SET SCHEMA graveyard;
ALTER TABLE IF EXISTS public.corridor_runs SET SCHEMA graveyard;
ALTER TABLE IF EXISTS public.dispatch_packets SET SCHEMA graveyard;
