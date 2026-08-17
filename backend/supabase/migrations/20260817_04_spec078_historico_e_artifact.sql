-- =============================================================
-- MIGRATION: spec078_historico_e_artifact
-- SPEC:      SPEC-078 — Bloco F.3, F.4 e F.7
-- AUTOR:     Claude Opus 5                     DATA: 2026-08-17
-- OBJETIVO:  Fazer o histórico de rotina caber em Entregas (F.3), guardar o
--            relatório INTEIRO em vez de 500 caracteres (F.4), e instrumentar
--            a idade dos boletos guardados no Storage (F.7).
--
-- APPLY:     ⛔ NÃO APLICADA. Escrita para o Founder aplicar.
--            `apply_migration` via MCP 📊 NÃO é transacional (medido na
--            SPEC-075): cada bloco numerado abaixo é idempotente POR SI e pode
--            ser colado separadamente, na ordem.
-- VERIFY:    bloco 6 ao final. Rodar depois de aplicar; a saída esperada está
--            escrita ao lado de cada consulta.
-- ROLLBACK:  bloco 7 ao final. Reversível — a única perda é o texto completo
--            das execuções ocorridas entre o APPLY e o ROLLBACK.
--
-- EXPAND-FIRST: sim — só adiciona coluna, índice, trigger e função.
-- DESTRUTIVA:   não — nenhuma linha apagada, nenhuma coluna removida,
--               nenhum NOT NULL novo.
-- =============================================================
--
-- POR QUE ESTA MIGRATION EXISTE
--
-- 📊 MEDIDO EM 17/08/2026, projeto dcajcvlzcjbmyapmklil:
--
--     routine_runs                     32 linhas
--     routine_runs.company_id          NÃO EXISTE
--     routine_runs com output_preview  32 de 32
--     maior output_preview             500 caracteres
--     média                            489 caracteres
--     execuções com EXATAMENTE 500     29  ← ou seja, 91% foram TRUNCADAS
--     execuções com work_run_id        0
--
-- Duas consequências, e as duas doem no mesmo lugar:
--
-- 1. SEM `company_id`, a rota de Entregas não pode ler esta tabela.
--    Toda fonte de lá é filtrada por `.eq('company_id', empresa)` — o backend
--    usa service role, e é o filtro no código, não a policy, que protege
--    (CLAUDE.md §7). Uma sexta fonte que só soubesse `routine_id` obrigaria a
--    montar a lista de rotinas antes, e o próximo a copiar o padrão perderia o
--    filtro sem perceber. Denormalizar a coluna é o que mantém a regra
--    verificável por leitura: `.from('routine_runs').eq('company_id', …)`.
--
-- 2. `output_preview = output[:500]` (`routine_engine.py:257`) descartava o
--    relatório no ato. O relatório da cobrança tem até 4000 caracteres, e as
--    duas seções que EXIGEM ação humana — "PRECISA DE VOCE" e "Clientes
--    encontrados" — ficam depois do caractere 500 em toda execução com
--    inadimplente. 📊 29 execuções em que isso aconteceu.
--
-- ⚠️ O QUE ESTA COLUNA PASSA A GUARDAR
--
-- `output_full` recebe o relatório da rotina de cobrança, que 📊 contém
-- CPF/CNPJ e telefone de segurado em texto claro
-- (`billing_collection.py:1069-1140`). A leitura é feita SOMENTE pela página
-- tenant-scoped `/dashboard/entregas/rotina/[runId]`, com
-- `.eq('company_id', …)` explícito. Não vai para RAG, não vai para Qdrant, não
-- vai para log e não entra em artifact compartilhável.
--
-- RLS: `routine_runs` 📊 já tem `relrowsecurity = true` e ZERO policies — ou
-- seja, fechada para anon e authenticated. Esta migration não a abre.
-- =============================================================


-- -------------------------------------------------------------------------
-- 1. `routine_runs` passa a saber de quem é
-- -------------------------------------------------------------------------
-- Nullable de propósito. Um `NOT NULL` aqui quebraria HOJE o segundo escritor
-- da tabela (`routine_engine.py:553`, a projeção do Work Run), que não passa
-- `company_id`. Expand-first: a coluna nasce, a trigger do bloco 3 garante que
-- ela nunca fique vazia, e o `NOT NULL` fica para uma migration de
-- endurecimento depois de o banco provar que não há mais nulos.

alter table public.routine_runs
  add column if not exists company_id uuid;

comment on column public.routine_runs.company_id is
  'SPEC-078 F.3: dono da execução, copiado de routines.company_id. Denormalizado '
  'para que a rota de Entregas filtre por .eq(company_id) como todas as outras '
  'fontes — o backend usa service role e o filtro no código é a proteção real.';


-- -------------------------------------------------------------------------
-- 2. Backfill: as 32 execuções que já existem ganham dono
-- -------------------------------------------------------------------------
-- Idempotente pelo `where company_id is null`. Rodar duas vezes não faz nada
-- na segunda.

update public.routine_runs rr
   set company_id = r.company_id
  from public.routines r
 where r.id = rr.routine_id
   and rr.company_id is null;


-- -------------------------------------------------------------------------
-- 3. A trigger que impede a coluna de voltar a nascer vazia
-- -------------------------------------------------------------------------
-- Por que uma trigger e não "corrigir os escritores": 📊 a tabela tem DOIS
-- escritores hoje, e a SPEC-078 só autoriza tocar num deles nesta rodada. Um
-- terceiro escritor amanhã — um teste, um script, um endpoint — nasceria sem
-- dono e a linha ficaria invisível em Entregas sem nenhum erro visível.
--
-- A trigger é a regra estrutural: quem não disser de quem é, o banco descobre
-- pela rotina. Quem disser, é respeitado (o `coalesce` não sobrescreve).

create or replace function public.routine_runs_herda_empresa()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.company_id is null then
    select r.company_id into new.company_id
      from public.routines r
     where r.id = new.routine_id;
  end if;
  return new;
end;
$$;

comment on function public.routine_runs_herda_empresa() is
  'SPEC-078 F.3: toda execução de rotina herda o company_id da rotina. Sem isto '
  'uma linha sem dono fica invisível em Entregas — e falha em silêncio.';

drop trigger if exists trg_routine_runs_herda_empresa on public.routine_runs;
create trigger trg_routine_runs_herda_empresa
  before insert on public.routine_runs
  for each row execute function public.routine_runs_herda_empresa();


-- -------------------------------------------------------------------------
-- 4. O índice que a rota de Entregas usa
-- -------------------------------------------------------------------------
-- A consulta é sempre a mesma: "as últimas N execuções DESTA corretora".
-- O índice existente é `(routine_id, started_at desc)`, que não serve para ela.

create index if not exists idx_routine_runs_company
  on public.routine_runs (company_id, started_at desc);


-- -------------------------------------------------------------------------
-- 5. O relatório inteiro
-- -------------------------------------------------------------------------
-- `output_preview` NÃO é removido nem derivado. Ele continua sendo escrito, e
-- passa a ter um papel declarado: é a coluna BARATA que a lista de Entregas lê.
-- Derivar o preview no momento da leitura obrigaria a rota a trazer 4 KB por
-- linha, 120 linhas por fonte, só para cortar 500 caracteres na memória.
--
-- 🔴 NÃO há backfill de `output_full`. As 32 execuções antigas perderam 87% do
-- texto no ato da gravação — copiar o preview truncado para cá apresentaria
-- 500 caracteres como se fossem o relatório inteiro. A página diz, para essas,
-- que a execução é anterior ao registro completo. Mentir por conveniência de
-- schema é pior que a lacuna.

alter table public.routine_runs
  add column if not exists output_full text;

comment on column public.routine_runs.output_full is
  'SPEC-078 F.4: o relatório COMPLETO da execução. output_preview continua sendo '
  'os primeiros 500 caracteres deste texto, e existe para a lista de Entregas '
  'não arrastar 4 KB por linha. ⚠️ Contém CPF/CNPJ e telefone de segurado: '
  'lido só pela página tenant-scoped /dashboard/entregas/rotina/[runId]. Não vai '
  'para RAG, nem para log, nem para artifact compartilhável.';


-- -------------------------------------------------------------------------
-- 6. F.7 — a idade dos boletos guardados passa a ser CONTÁVEL
-- -------------------------------------------------------------------------
-- 📊 MEDIDO EM 17/08/2026, `storage.objects`:
--
--     portal-evidence   62 objetos   5977 kB   mais antigo 11/07/2026
--                       5 com mais de 30 dias · 0 com mais de 60 · 0 com 90
--
-- São boletos de terceiros — dado financeiro de segurado — sem NENHUMA rotina
-- de descarte. Esta SPEC não apaga nada (§15). Ela faz três coisas:
--
--   (a) dá um número à pergunta "quantos objetos velhos eu tenho?", que hoje
--       ninguém consegue responder sem abrir o console do Supabase;
--   (b) devolve a resposta POR CORRETORA — o caminho do objeto é
--       `{company_id}/{portal_key}/{job_id}/boleto-*.pdf`, então a primeira
--       pasta é o dono, e uma política de retenção que não sabe de quem é o
--       arquivo não é política, é faxina;
--   (c) deixa a purga escrita e DESLIGADA (`billing_collection.py`,
--       `purgar_evidencias_antigas`, atrás de PORTAL_EVIDENCE_PURGE_ENABLED).
--
-- A função é só LEITURA. Ela não apaga nada e não pode apagar nada.

create or replace function public.portal_evidence_por_idade(dias integer default 90)
returns table (
  company_id text,
  objetos bigint,
  mais_velhos_que_o_prazo bigint,
  bytes bigint,
  mais_antigo timestamptz
)
language sql
stable
security definer
set search_path = storage, public
as $$
  select
    split_part(o.name, '/', 1)                                   as company_id,
    count(*)                                                     as objetos,
    count(*) filter (
      where o.created_at < now() - make_interval(days => greatest(dias, 1))
    )                                                            as mais_velhos_que_o_prazo,
    coalesce(sum((o.metadata->>'size')::bigint), 0)              as bytes,
    min(o.created_at)                                            as mais_antigo
  from storage.objects o
  where o.bucket_id = 'portal-evidence'
  group by 1
  order by 3 desc, 2 desc;
$$;

comment on function public.portal_evidence_por_idade(integer) is
  'SPEC-078 F.7: quantos boletos cada corretora tem guardados no bucket '
  'portal-evidence e quantos passaram do prazo. SOMENTE LEITURA — a purga é '
  'outra coisa, está escrita em billing_collection.purgar_evidencias_antigas e '
  'nasce DESLIGADA. Ligar é decisão do Founder (PENDENCIAS.md).';

revoke all on function public.portal_evidence_por_idade(integer) from public, anon;
grant execute on function public.portal_evidence_por_idade(integer) to service_role;


-- =============================================================
-- VERIFY — rodar DEPOIS de aplicar. Saída esperada ao lado.
-- =============================================================
--
-- 1) as duas colunas existem
--
-- select column_name, data_type, is_nullable
--   from information_schema.columns
--  where table_schema='public' and table_name='routine_runs'
--    and column_name in ('company_id','output_full');
--    → 2 linhas: company_id uuid YES · output_full text YES
--
-- 2) o backfill não deixou órfã
--
-- select count(*) as sem_dono from public.routine_runs where company_id is null;
--    → 0
--
-- 3) a trigger existe e está armada
--
-- select tgname, tgenabled from pg_trigger
--  where tgrelid='public.routine_runs'::regclass and not tgisinternal;
--    → trg_routine_runs_herda_empresa | O
--
-- 4) a distribuição por corretora bate com a das rotinas
--
-- select company_id, count(*) from public.routine_runs group by 1 order by 2 desc;
--    → 04b5cdbc-04cd-4ddf-8e4b-f43efb062fab | 32   (📊 medido antes de aplicar)
--
-- 5) o índice existe
--
-- select indexname from pg_indexes
--  where schemaname='public' and tablename='routine_runs';
--    → idx_routine_runs_routine · idx_routine_runs_company
--
-- 6) a contagem por idade responde
--
-- select * from public.portal_evidence_por_idade(30);
--    → 1 linha: 04b5cdbc-… | 62 | 5 | ~6120000 | 2026-07-11 07:13:25+00
--      (📊 medido em 17/08/2026 pela consulta equivalente direta em
--       storage.objects — ver o cabeçalho do bloco 6)
--
-- =============================================================
-- ROLLBACK — reversível. Perde-se o `output_full` gravado no intervalo.
-- =============================================================
--
-- drop trigger if exists trg_routine_runs_herda_empresa on public.routine_runs;
-- drop function if exists public.routine_runs_herda_empresa();
-- drop function if exists public.portal_evidence_por_idade(integer);
-- drop index if exists public.idx_routine_runs_company;
-- alter table public.routine_runs drop column if exists output_full;
-- alter table public.routine_runs drop column if exists company_id;
--
-- ⚠️ Depois do ROLLBACK, a rota de Entregas volta a não ter a sexta fonte e a
-- página /dashboard/entregas/rotina/[runId] passa a devolver 404 em tudo. O
-- código tolera a ausência das colunas? NÃO — e isso é de propósito: uma rota
-- que finge funcionar sem a coluna esconderia o rollback até alguém procurar um
-- relatório e não achar.
