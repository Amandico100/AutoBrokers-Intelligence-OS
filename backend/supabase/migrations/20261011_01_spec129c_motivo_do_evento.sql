-- =============================================================
-- MIGRATION: 20261011_01_spec129c_motivo_do_evento
-- SPEC:      SPEC-129-C — conserto (canário AO VIVO §3.5) · o PORQUÊ da recusa
-- AUTOR:     builder do conserto, lado do portal (Opus 5.5)      DATA: 2026-10-11
-- OBJETIVO:  `multicalculo_eventos` ganha a coluna `motivo text` (nula): o texto da seguradora que explica a recusa,
--            saneado (sem URL, sem chave, sem dado pessoal — `portal_worker.multicalculo.motor.erro_curto`) e cortado em
--            300 caracteres. 📊 No canário de 11/10, Tokio, Chubb e Bradesco recusaram o condomínio com a família
--            DESCONHECIDA e o porquê se perdeu: a tabela não tinha onde guardá-lo.
--
-- 📊 ANTES (11/10/2026, SELECT só leitura pelo MCP no projeto dcajcvlzcjbmyapmklil):
--    · information_schema.columns de multicalculo_eventos → id, calculo_id, pedido_id, company_id,
--      solicitante_company_id, tipo, seguradora, seguradora_codigo, pacote, tipo_de_pacote, familia, oferta_id, chave,
--      t_s, criado_em — NENHUMA coluna de texto livre ou jsonb que caiba o motivo (`chave` é a identidade única do
--      evento, `familia` é a classe); por isso a coluna nova, e não reaproveitar uma existente.
--    · constraints: ck_mc_eventos_chave (1..300), ck_mc_eventos_tipo, fk_mc_eventos_calculo, uq_mc_eventos_chave.
--
-- 🔴 O CÓDIGO PODE SUBIR ANTES DESTA MIGRATION: o motor tenta gravar o motivo e, se o banco responder que a coluna não
--    existe (PGRST204), grava o evento SEM ele e não tenta de novo naquela vida (`Motor._gravar_linha_de_evento`). A
--    narração nunca se perde por causa do porquê.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. ALTER TABLE ... ADD COLUMN IF NOT EXISTS motivo text (nula, sem default — nenhuma linha antiga é reescrita;
--      o gatilho "evento não se reescreve" não é tocado porque ADD COLUMN sem default não faz UPDATE).
--   B. CHECK ck_mc_eventos_motivo (motivo nulo ou 1..300 caracteres), NOT VALID + VALIDATE (a tabela só tem nulos).
--   C. COMMENT na coluna.
--
-- VERIFY (read-only):
--   select (select count(*) from information_schema.columns
--            where table_schema = 'public' and table_name = 'multicalculo_eventos' and column_name = 'motivo'
--              and data_type = 'text' and is_nullable = 'YES') as coluna,
--          (select count(*) from pg_constraint
--            where conrelid = 'public.multicalculo_eventos'::regclass and conname = 'ck_mc_eventos_motivo'
--              and convalidated) as check_validado,
--          (select count(*) from public.multicalculo_eventos where motivo is not null) as motivos_gravados;
--   -- esperado logo após o APPLY: 1 · 1 · 0
--   -- 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3): a definição REAL do check, copiada do catálogo para uma tabela
--   --    temporária — 301 caracteres e o texto vazio são recusados, 300 passam; nada fica gravado.
--   do $$
--   declare def text; recusas int := 0;
--   begin
--     select pg_get_constraintdef(oid) into def from pg_constraint
--      where conrelid = 'public.multicalculo_eventos'::regclass and conname = 'ck_mc_eventos_motivo';
--     create temp table verify_129c_motivo (motivo text) on commit drop;
--     execute 'alter table verify_129c_motivo add constraint ck ' || def;
--     insert into verify_129c_motivo values (null), (repeat('x', 300));
--     begin insert into verify_129c_motivo values (repeat('x', 301)); exception when check_violation then recusas := recusas + 1; end;
--     begin insert into verify_129c_motivo values (''); exception when check_violation then recusas := recusas + 1; end;
--     if recusas <> 2 then raise exception 'VERIFY 20261011_01 FALHOU: % recusas (esperado 2)', recusas; end if;
--     raise notice 'VERIFY 20261011_01 OK: 301 recusado, vazio recusado, 300 e nulo aceitos';
--   end $$;
--
-- ROLLBACK (só se nenhum código depender da coluna; o motor sobrevive sem ela, ver acima):
--   alter table public.multicalculo_eventos drop constraint if exists ck_mc_eventos_motivo;
--   alter table public.multicalculo_eventos drop column if exists motivo;
--
-- EXPAND-FIRST: sim (só acrescenta; nada é removido nem reescrito)
-- DESTRUTIVA:   não
-- IDEMPOTENTE:  sim (IF NOT EXISTS / checagem no catálogo)
-- =============================================================

begin;

alter table public.multicalculo_eventos add column if not exists motivo text;

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.multicalculo_eventos'::regclass and conname = 'ck_mc_eventos_motivo') then
    alter table public.multicalculo_eventos
      add constraint ck_mc_eventos_motivo check (motivo is null or (length(motivo) between 1 and 300)) not valid;
  end if;
end $$;

alter table public.multicalculo_eventos validate constraint ck_mc_eventos_motivo;

comment on column public.multicalculo_eventos.motivo is
  'SPEC-129-C: o porquê da recusa — o texto da seguradora saneado (sem URL, chave ou dado pessoal; motor.erro_curto), '
  'até 300 caracteres. Nulo quando a seguradora não disse nada.';

commit;
