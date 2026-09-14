-- =============================================================================
-- MIGRATION: spec_extra0011_llm_max_tokens
-- SPEC:      SPEC-EXTRA-001.1 — BLOCO E "o turno que some, o teto de tokens"
-- AUTOR:     Claude Opus 5 (builder E)              DATA: 2026-09-14
-- OBJETIVO:  o dado `agents.llm_max_tokens` deixa de mentir para quem o lê
--
-- APPLY:     UPDATE de DADO em 8 linhas de `public.agents`, com a tabela de
--            backup `agents_llm_max_tokens_backup_extra0011` guardando o valor
--            ANTERIOR de cada agente, por `agent_id`. Nenhuma coluna é criada,
--            alterada ou removida. Nenhum DEFAULT de schema é tocado.
-- VERIFY:    V0–V4, abaixo. SQL executável, read-only.
-- ROLLBACK:  bloco ROLLBACK ao final — restaura o valor EXATO de cada agente.
--
-- EXPAND-FIRST: sim (a tabela de backup nasce ANTES do UPDATE)
-- DESTRUTIVA:   não (nenhuma linha some; o valor anterior fica guardado)
-- IDEMPOTENTE:  sim (`IF NOT EXISTS` + `ON CONFLICT DO NOTHING` + o WHERE do
--               UPDATE deixa de casar depois da 1ª passada)
--
-- 🔴 POR QUE ESTA MIGRATION EXISTE, se o código já tem piso
-- -----------------------------------------------------------------------------
-- 📊 09/09/2026, Resulta Seguros: `agents.llm_max_tokens` do agente core = 1200;
--    em `token_usage_logs` desde 08/09, 10 de 95 chamadas do chat bateram
--    `output_tokens = 1200` EXATO, e as mesmas 10 respostas estão gravadas em
--    `messages` terminando no meio de uma palavra.
-- O piso de `app/factories/llm_factory.py` (commit `312939f`) já conserta o
-- COMPORTAMENTO. O que continua errado é o DADO: quem abre a tela de
-- configuração lê 1200, e quem ler o banco para decidir qualquer coisa decide
-- errado (CLAUDE.md §12.1 — o nome/valor que mente reinfecta todo leitor
-- seguinte). Esta migration conserta o dado. ⛔ Ela NÃO substitui o piso, e o
-- piso NÃO deve ser revertido junto: são duas redes, não uma escolha.
--
-- 📊 O ESTADO MEDIDO ANTES DE UMA LINHA DE SQL (13/09 e reconferido em 14/09,
--    BLOCO 0 §1.2 premissa 8, `select agent_role, llm_max_tokens, count(*) from
--    public.agents group by 1,2 order by 1,2`):
--        (attendance, 1200, 1)
--        (attendance, 2000, 3)
--        (core,       1200, 3)
--        (core,       2000, 1)
--      = 8 agentes, 4 `core` + 4 `attendance`, nenhum >= 8192.
-- ⚠️ SE A CONTAGEM DE HOJE NÃO BATER, PARE: alguém mexeu entre a medição e o
--    APPLY, e o inventário colado no MANIFEST/relatório deixaria de ser o
--    inventário real. O V0 abaixo é exatamente essa conferência, e roda ANTES.
--
-- ⚠️ `companies.llm_max_tokens` NÃO ENTRA — decisão D-E0011-01, nota 70 × 55.
--    📊 medido em 14/09: 2000 em 5 de 5 corretoras, e a coluna tem 2 leitores:
--    `llm_factory.py:102` (fallback de QUALQUER papel, inclusive `auxiliary` e
--    `subagent`, que mantêm teto baixo DE PROPÓSITO) e `agent_config.py:288`
--    (a tela). Subi-la elevaria o teto de auxiliar e subagente — custo sem um
--    byte de mudança para ninguém (protocolo §2).
--
-- ⚠️ OS `DEFAULT 2000` DE DDL NÃO SÃO TOCADOS AQUI — `schema_completo.sql:454`
--    (agents) e `:581` (companies). São ALTER de estrutura, exigiriam manifesto
--    completo (MIGRATIONS-AUTHORITY §5) e são uma SEGUNDA migration, nunca um
--    `ALTER` pendurado nesta. Ficam registrados como pendência
--    **P-E0011-DEFAULT-DDL-2000**. Os defaults de CÓDIGO (que são os que
--    escrevem hoje) vão a 8192 no mesmo commit desta migration:
--        backend/app/api/agent_config.py:82 (request) · :133 (response) · :288 (fallback)
--        backend/app/models/agent.py:19
--        app/api/admin/sandbox/bootstrap-tenant/route.ts:106  (era 1200)
-- =============================================================================

-- ------------------------------------------------------- V0 (ANTES do APPLY) --
-- 🔴 Rode este bloco ANTES do APPLY e cole a saída no relatório. Ele é o
--    inventário do manifesto de DADO (MIGRATIONS-AUTHORITY §5 adaptada: esta
--    migration não altera schema, então o manifesto exigido é o inventário das
--    linhas afetadas antes e depois).
-- ⛔ NENHUMA PII: só papel, valor e contagem. Nunca nome de agente, nunca id de
--    corretora em prosa.
--
--   select agent_role, llm_max_tokens, count(*)
--     from public.agents
--    group by 1,2 order by 1,2;
--   -- 📊 esperado em 14/09/2026:
--   --   (attendance, 1200, 1) (attendance, 2000, 3) (core, 1200, 3) (core, 2000, 1)
--
--   select count(*) as alvos
--     from public.agents
--    where agent_role in ('core','attendance')
--      and (llm_max_tokens is null or llm_max_tokens < 8192);
--   -- 📊 esperado: 8

-- ----------------------------------------------------------------- APPLY -----
begin;

-- A rede. Ela nasce ANTES do UPDATE (expand-first) e guarda o valor de CADA
-- agente — não uma média, não "o valor mais comum". 🔴 Um ROLLBACK que devolve
-- 2000 a quem tinha 1200 não é rollback: é uma terceira verdade.
create table if not exists public.agents_llm_max_tokens_backup_extra0011 (
    agent_id        uuid primary key,
    company_id      uuid not null,
    valor_anterior  integer,
    capturado_em    timestamptz not null default now()
);

-- ⚠️ RLS ligado: o advisor de segurança do Supabase acusa ERROR para tabela em
-- `public` sem RLS (medido depois do 1º APPLY em 14/09: `rls_disabled_in_public`).
-- O backend usa service role, então ligar não muda nenhum leitor; e a tabela é
-- rede de rollback, não superfície de produto. Idempotente.
alter table public.agents_llm_max_tokens_backup_extra0011 enable row level security;

comment on table public.agents_llm_max_tokens_backup_extra0011 is
  'SPEC-EXTRA-001.1 BLOCO E (P-PILOTO-17): valor de agents.llm_max_tokens ANTES do UPDATE para 8192, por agent_id. E a unica fonte do ROLLBACK. NAO apagar junto com o rollback: ela e a PROVA de que os 8 valores voltaram aos originais.';

-- 🔴 `ON CONFLICT DO NOTHING` é o que torna o APPLY idempotente DE VERDADE:
-- rodar duas vezes não sobrescreve o valor original com 8192. Sem esta linha, a
-- segunda passada transformaria a rede numa cópia do estado novo — e o ROLLBACK
-- passaria a "restaurar" 8192, em silêncio, com o VERIFY todo verde.
insert into public.agents_llm_max_tokens_backup_extra0011 (agent_id, company_id, valor_anterior)
select id, company_id, llm_max_tokens
  from public.agents
 where agent_role in ('core','attendance')
   and (llm_max_tokens is null or llm_max_tokens < 8192)
on conflict (agent_id) do nothing;

update public.agents
   set llm_max_tokens = 8192
 where agent_role in ('core','attendance')
   and (llm_max_tokens is null or llm_max_tokens < 8192);

commit;

-- ---------------------------------------------------------------- VERIFY -----
-- Roda DEPOIS do APPLY. A saída vai COLADA no relatório (protocolo §0.4).

-- V1 — o dado parou de mentir.
--   select agent_role, llm_max_tokens, count(*)
--     from public.agents
--    group by 1,2 order by 1,2;
--   -- esperado: (attendance, 8192, 4) e (core, 8192, 4).
--   -- 🔴 QUALQUER linha de core/attendance abaixo de 8192 REPROVA o gate.

-- V2 — a rede existe, e com os 8 valores ORIGINAIS.
--   select count(*) as linhas_guardadas,
--          count(*) filter (where valor_anterior = 8192) as ja_era_8192
--     from public.agents_llm_max_tokens_backup_extra0011;
--   -- esperado: linhas_guardadas = 8, ja_era_8192 = 0.
--   -- 🔴 `linhas_guardadas = 0` com o UPDATE feito = ROLLBACK IMPOSSÍVEL →
--   --    reprova o gate. `ja_era_8192 > 0` = a rede virou cópia do estado novo
--   --    (alguém rodou o APPLY sem o `on conflict`) → reprova também.

-- V3 — a rede bate, valor a valor, com o que a medição de 14/09 declarou.
--   select valor_anterior, count(*)
--     from public.agents_llm_max_tokens_backup_extra0011
--    group by 1 order by 1;
--   -- esperado: (1200, 4) e (2000, 4).

-- V4 — CONTROLE: nada FORA de core/attendance foi tocado.
--   🔴 Sem esta linha, um WHERE mal escrito passaria despercebido: o V1 só
--      olha para quem mudou, e quem não devia mudar não aparece nele.
--   select agent_role, llm_max_tokens, count(*)
--     from public.agents
--    where agent_role is null or agent_role not in ('core','attendance')
--    group by 1,2 order by 1,2;
--   -- esperado em 14/09/2026: NENHUMA LINHA (📊 os 8 agentes da base são
--   --   4 core + 4 attendance). Se aparecer linha, ela tem de estar com o
--   --   MESMO valor de antes do APPLY.

-- V5 — CONTROLE: `companies.llm_max_tokens` continua intacta (D-E0011-01).
--   select llm_max_tokens, count(*) from public.companies group by 1 order by 1;
--   -- esperado: (2000, 5) — exatamente como antes. Qualquer 8192 aqui é
--   -- escorregão de escopo e REPROVA o gate.

-- -------------------------------------------------------------- ROLLBACK -----
-- Restaura o valor EXATO de cada agente, por `agent_id`.
--
--   update public.agents a
--      set llm_max_tokens = b.valor_anterior
--     from public.agents_llm_max_tokens_backup_extra0011 b
--    where a.id = b.agent_id;
--
-- Conferência do rollback (roda depois dele):
--   select b.valor_anterior, a.llm_max_tokens, count(*)
--     from public.agents a
--     join public.agents_llm_max_tokens_backup_extra0011 b on b.agent_id = a.id
--    group by 1,2 order by 1,2;
--   -- esperado: toda linha com `valor_anterior = llm_max_tokens`
--   --   → (1200, 1200, 4) e (2000, 2000, 4).
--
-- 🔴 A TABELA DE BACKUP NÃO É APAGADA PELO ROLLBACK. Ela é a prova de que os
--    valores voltaram um a um, e apagá-la deixaria a conferência acima sem o
--    lado esquerdo da comparação.
--
-- ⚠️ O rollback do COMPORTAMENTO é outro e NÃO deve ser feito junto: o piso de
--    8192 em `llm_factory.piso_de_saida` continua sendo a rede. Reverter os
--    dois ao mesmo tempo devolveria a resposta cortada ao corretor.
