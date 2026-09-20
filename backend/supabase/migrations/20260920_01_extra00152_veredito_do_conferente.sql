-- =============================================================
-- SPEC-EXTRA-001.5.2 · unidade F — O VEREDITO DO CONFERENTE MORA NA LINHA
--
-- APPLY:     acrescenta 3 colunas a `insurer_assistance_services`:
--            `veredito_do_conferente`, `conferencia` (jsonb) e `conferido_em`;
--            e um indice parcial para a fila achar o que ainda nao tem veredito.
--            Expand-first: nenhuma coluna existente muda, nenhuma linha e
--            reescrita, nada vira NOT NULL. Rodar de novo nao faz nada.
--
-- VERIFY:    -- 1) as tres colunas existem, todas anulaveis
--            select column_name, data_type, is_nullable
--              from information_schema.columns
--             where table_schema='public'
--               and table_name='insurer_assistance_services'
--               and column_name in ('veredito_do_conferente','conferencia',
--                                   'conferido_em')
--             order by 1;
--            -- esperado: 3 linhas · conferencia=jsonb · is_nullable=YES em todas
--
--            -- 2) o CHECK so aceita os tres vereditos
--            select conname from pg_constraint
--             where conrelid='public.insurer_assistance_services'::regclass
--               and conname='servico_veredito_do_conferente_valido';
--
--            -- 3) o indice da unidade G: quantas linhas `proposto` ainda
--            --    estao SEM veredito? (o GATE G exige 0 depois do --gravar)
--            select count(*) from public.insurer_assistance_services
--             where curadoria='proposto' and veredito_do_conferente is null;
--
-- ROLLBACK:  -- nao destroi dado de ninguem: as colunas so tem o que o
--            -- conferente escreveu, e ele e reexecutavel (--ensaio primeiro).
--            drop index if exists public.ix_ias_sem_veredito;
--            alter table public.insurer_assistance_services
--              drop constraint if exists servico_veredito_do_conferente_valido;
--            alter table public.insurer_assistance_services
--              drop column if exists conferido_em,
--              drop column if exists conferencia,
--              drop column if exists veredito_do_conferente;
--
-- =============================================================
-- POR QUE UMA MIGRATION, E NAO UMA COLUNA QUE JA EXISTE
-- --------------------------------------------------------------
-- 📊 20/09/2026, lido em `20260917_01_extra0015_assistance_plans.sql` e
-- `20260919_01_extra00151_motivo_do_rascunho.sql`: a tabela tem 20 colunas e
-- NENHUMA delas e jsonb ou campo livre de metadados. A unica candidata era
-- `motivo_do_rascunho`, e ela ja tem dono — e o motivo de `para_rascunho`, que
-- a fila mostra ao curador. Escrever o parecer do conferente ali repetiria, com
-- outro nome, o defeito que a 001.5.1 acabou de consertar (o motivo entrava e a
-- `condicao` contratual sumia): dois escritores no mesmo campo, e o segundo
-- apaga o primeiro sem copia.
--
-- POR QUE `conferencia` E jsonb, E NAO TRES COLUNAS DE TEXTO
-- --------------------------------------------------------------
-- O parecer tem forma: `{campos: {pagina|trecho|coberto|limite|plano|produto:
-- ok|diverge|nao_avaliado}, motivos: [...], pagina: n}`. Espalha-lo em colunas
-- fixaria HOJE quais campos o conferente olha — e a unidade A (a ancora de
-- planos) vai acrescentar checagens amanha. O que a fila PERGUNTA de verdade
-- ("esta linha tem veredito? qual?") e a coluna de texto, que e a indexada.
--
-- 🔴 NENHUM ESTADO DE CURADORIA MUDA AQUI. O conferente ANOTA; quem promove a
--    `publicado` continua sendo gente, por `publicar_servico`, com revisor.
-- =============================================================

begin;

alter table public.insurer_assistance_services
  add column if not exists veredito_do_conferente text,
  add column if not exists conferencia            jsonb,
  add column if not exists conferido_em           timestamptz,
  add column if not exists caminho_da_clausula    text;  -- unidade B: de qual clausula a linha saiu (ex.: "9.5.9.2 > Plano Vip > Carro Reserva"); ROLLBACK: drop column junto com as outras tres

comment on column public.insurer_assistance_services.veredito_do_conferente is
  'CONFERE | DIVERGE | NAO_CONSEGUI — o parecer automatico contra a PAGINA do '
  'documento arquivado, escrito por assistance_plans_conferente.conferir_linha '
  '(SPEC-EXTRA-001.5.2, unidade F). ⚠️ NAO e curadoria: nao publica nem recusa, '
  'so diz o que a pagina sustenta. NULL = a linha ainda nao foi conferida.';

comment on column public.insurer_assistance_services.conferencia is
  'O parecer inteiro: {"campos": {"pagina|trecho|coberto|limite|plano|produto": '
  '"ok|diverge|nao_avaliado"}, "motivos": [texto], "pagina": n}. ⛔ Nunca guarda '
  'o trecho do documento (a base guarda so o `trecho_hash`, por contrato).';

comment on column public.insurer_assistance_services.conferido_em is
  'Quando o conferente passou por esta linha. Reconferir sobrescreve os tres '
  'campos juntos — o parecer e derivado, nunca historico.';

do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.insurer_assistance_services'::regclass
       and conname  = 'servico_veredito_do_conferente_valido'
  ) then
    alter table public.insurer_assistance_services
      add constraint servico_veredito_do_conferente_valido check (
        veredito_do_conferente is null
        or veredito_do_conferente in ('CONFERE', 'DIVERGE', 'NAO_CONSEGUI'));
  end if;
end $$;

-- 🔴 O INDICE DO GATE G: "0 linhas em `proposto` sem veredito". A pergunta e
--    feita toda vez que a fila abre, e e sobre a MINORIA das linhas — indice
--    parcial, que nao cresce com o que ja foi conferido.
create index if not exists ix_ias_sem_veredito
    on public.insurer_assistance_services (curadoria)
 where veredito_do_conferente is null;

commit;
