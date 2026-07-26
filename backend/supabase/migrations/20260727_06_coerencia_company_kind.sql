-- =============================================================
-- MIGRATION: coerencia_company_kind
-- SPEC:      SPEC-061 (correcao encontrada em uso real)
-- AUTOR:     Executor Opus                DATA: 2026-07-27
-- OBJETIVO:  impedir que `company_kind` e `is_technical` se contradigam.
--
-- APPLY:     1 update de coerencia (idempotente) + 1 CHECK constraint.
-- VERIFY:    ver bloco VERIFY ao final.
-- ROLLBACK:  drop da constraint (o dado corrigido permanece).
--
-- EXPAND-FIRST: sim — a constraint so passa a valer para escrita nova.
-- DESTRUTIVA:   nao
--
-- O QUE ACONTECEU
-- ---------------
-- `AMANDUS SEGUROS` estava com `company_kind = 'client'` E `is_technical =
-- true`. Os dois campos dizem coisas opostas:
--
--   company_kind='client'  -> "isto e uma corretora"
--   is_technical=true      -> "isto e infraestrutura da plataforma"
--
-- E `is_technical` nao e cosmetico. Ele TIRA a empresa de:
--
--   * `/admin/corretoras`      — some do Cockpit
--   * `intelligence/tick.py`   — nao recebe deteccao nem briefing
--   * `weekly_report.py`       — fica fora do relatorio semanal
--   * `intelligence/origem.py` — vira "origem interna", entao o que ela
--                                produz nao conta como sinal
--
-- O Founder usa a AMANDUS como corretora de ensaio: e onde ele navega,
-- mexe nos cards e testa sem tocar numa corretora de verdade. Com a marca
-- errada, ela era o pior dos dois mundos — parecia uma corretora na lista de
-- empresas e nao recebia nada do produto.
--
-- POR QUE UM CHECK E NAO SO O UPDATE
-- ----------------------------------
-- O update conserta hoje. A constraint impede que a proxima empresa criada
-- por um caminho diferente nasca contraditoria de novo — e este defeito e
-- silencioso: a empresa aparece, parece ativa, e simplesmente nunca recebe
-- briefing. Ninguem abre chamado por um briefing que nao sabia que existia.
-- =============================================================

-- 1. Coerencia do que ja existe. Idempotente: rodar de novo nao muda nada.
update public.companies
   set is_technical = false, updated_at = now()
 where company_kind = 'client' and is_technical is true;

update public.companies
   set is_technical = true, updated_at = now()
 where company_kind is not null
   and company_kind <> 'client'
   and is_technical is false;

-- 2. A regra, no banco.
--
-- `company_kind` nulo fica de fora: ha empresas antigas sem o campo, e
-- recusa-las na escrita quebraria fluxo que hoje funciona. A constraint cobra
-- coerencia de quem DECLARA o tipo — que e o caminho novo.
alter table public.companies
  drop constraint if exists companies_kind_e_tecnica_coerentes_ck;

alter table public.companies
  add constraint companies_kind_e_tecnica_coerentes_ck
  check (
    company_kind is null
    or (company_kind = 'client' and is_technical is not true)
    or (company_kind <> 'client' and is_technical is true)
  );

comment on constraint companies_kind_e_tecnica_coerentes_ck on public.companies is
  'company_kind e is_technical nao podem se contradizer. Corretora marcada como '
  'tecnica some do Cockpit, do briefing e do relatorio semanal sem que ninguem '
  'perceba. SPEC-061.';

-- =============================================================
-- VERIFY
-- =============================================================
-- select company_name, company_kind, is_technical,
--        case when company_kind = 'client' and is_technical then 'CONTRADITORIO'
--             when company_kind <> 'client' and not is_technical then 'CONTRADITORIO'
--             else 'coerente' end as coerencia
--   from public.companies order by created_at;
--   -- esperado: todas 'coerente'
--
-- -- E a constraint precisa RECUSAR a contradicao (rode dentro de um bloco DO
-- -- encerrado por `raise exception`, para nao persistir):
-- --   update companies set is_technical = true
-- --    where company_kind = 'client' limit 1;   -> check_violation
--
-- =============================================================
-- ROLLBACK
-- =============================================================
-- alter table public.companies
--   drop constraint if exists companies_kind_e_tecnica_coerentes_ck;
--
-- O dado corrigido NAO e revertido: AMANDUS voltar a ser "tecnica" seria
-- reintroduzir o defeito, nao desfazer a migration.
-- =============================================================
