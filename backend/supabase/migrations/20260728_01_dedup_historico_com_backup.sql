-- =====================================================================
-- 20260728_01 — Remover as cópias do history_sync, com backup completo
-- =====================================================================
--
-- POR QUE
-- -------
-- A ingestão de histórico montava o id da mensagem terminando em
-- `abs(hash(texto[:60]))`. `hash()` de string em Python é aleatorizado a cada
-- processo, então o `on_conflict="observer_number,message_id"` — que existe
-- exatamente para impedir duplicação — nunca disparava. Três `history_sync`
-- em 28/07/2026 (14:01, 15:02, 15:43) gravaram o histórico inteiro três vezes.
--
-- A causa foi corrigida em `history_ingest._history_message_id` (sha1 do
-- texto inteiro, estável entre processos, provado com PYTHONHASHSEED=random).
-- Esta migration limpa o que já ficou gravado.
--
-- Medido antes de rodar:
--
--     observed_events         20.506 linhas   ~7.522 mensagens reais
--     attendance_transcripts 116.877 linhas   58.786 mensagens reais
--
-- O QUE É "CÓPIA"
-- ---------------
-- Mesma sessão + mesma direção + mesmo instante + mesmo tipo + mesmo texto.
-- Duas mensagens idênticas, no mesmo segundo, na mesma direção, dentro da
-- mesma sessão são a mesma mensagem — não alguém que disse "Ok" duas vezes
-- no mesmo segundo.
--
-- Linha sem `wa_timestamp` ou sem `text` (foto, áudio, documento) NÃO entra
-- na deduplicação: sem instante ou sem texto não há identidade segura, e a
-- regra do Founder é absoluta — "NENHUMA MSG PODE SER PERDIDA". Perder é
-- irreversível; sobrar não.
--
-- A que fica é a de `created_at` MAIS ANTIGO: foi a primeira a chegar.
--
-- REVERSÍVEL
-- ----------
-- Tudo que sai vai antes para `*_copias_removidas_20260728`, com a linha
-- inteira. O ROLLBACK reinsere e o banco volta ao estado de agora.
--
-- Idempotente: rodar de novo não remove mais nada (não haverá cópias) e não
-- duplica o backup (as tabelas são criadas com IF NOT EXISTS e a inserção
-- ignora o que já está lá).
-- =====================================================================

-- ---------------------------------------------------------------------
-- APPLY
-- ---------------------------------------------------------------------
begin;

-- 1) BACKUP — a linha inteira do que vai sair, antes de sair.
create table if not exists public.observed_events_copias_removidas_20260728
    (like public.observed_events including defaults);
create table if not exists public.attendance_transcripts_copias_removidas_20260728
    (like public.attendance_transcripts including defaults);

alter table public.observed_events_copias_removidas_20260728
    enable row level security;
alter table public.attendance_transcripts_copias_removidas_20260728
    enable row level security;

-- Sem policy: nega tudo para anon/authenticated. Só o service role lê —
-- e ele é quem faria o rollback. É material de conversa de cliente.

with duplicadas as (
    select id
    from (
        select id,
               row_number() over (
                   partition by session_id, direction, wa_timestamp, msg_type, text
                   order by created_at, id
               ) as posicao
        from public.observed_events
        where wa_timestamp is not null and text is not null
    ) t
    where posicao > 1
)
insert into public.observed_events_copias_removidas_20260728
select e.* from public.observed_events e
join duplicadas d on d.id = e.id
where not exists (
    select 1 from public.observed_events_copias_removidas_20260728 b where b.id = e.id
);

with duplicadas as (
    select id
    from (
        select id,
               row_number() over (
                   partition by session_id, direction, wa_timestamp, msg_type, text
                   order by created_at, id
               ) as posicao
        from public.attendance_transcripts
        where wa_timestamp is not null and text is not null
    ) t
    where posicao > 1
)
insert into public.attendance_transcripts_copias_removidas_20260728
select e.* from public.attendance_transcripts e
join duplicadas d on d.id = e.id
where not exists (
    select 1 from public.attendance_transcripts_copias_removidas_20260728 b where b.id = e.id
);

-- 2) PROVA ANTES DE APAGAR — cada linha a remover tem de estar no backup.
--    Se faltar uma, a transação inteira aborta e nada é apagado.
do $$
declare
    faltando bigint;
begin
    select count(*) into faltando
    from (
        select id
        from (
            select id, row_number() over (
                       partition by session_id, direction, wa_timestamp, msg_type, text
                       order by created_at, id) as posicao
            from public.observed_events
            where wa_timestamp is not null and text is not null
        ) t where posicao > 1
    ) d
    where not exists (select 1 from public.observed_events_copias_removidas_20260728 b
                      where b.id = d.id);
    if faltando > 0 then
        raise exception 'ABORTADO: % copias de observed_events sem backup', faltando;
    end if;

    select count(*) into faltando
    from (
        select id
        from (
            select id, row_number() over (
                       partition by session_id, direction, wa_timestamp, msg_type, text
                       order by created_at, id) as posicao
            from public.attendance_transcripts
            where wa_timestamp is not null and text is not null
        ) t where posicao > 1
    ) d
    where not exists (select 1 from public.attendance_transcripts_copias_removidas_20260728 b
                      where b.id = d.id);
    if faltando > 0 then
        raise exception 'ABORTADO: % copias de attendance_transcripts sem backup', faltando;
    end if;
end $$;

-- 3) REMOÇÃO — só o que está provadamente guardado.
delete from public.observed_events e
using public.observed_events_copias_removidas_20260728 b
where b.id = e.id;

delete from public.attendance_transcripts e
using public.attendance_transcripts_copias_removidas_20260728 b
where b.id = e.id;

commit;

-- ---------------------------------------------------------------------
-- VERIFY  —  RODADO EM 28/07/2026, saída real abaixo
-- ---------------------------------------------------------------------
-- A primeira versão deste VERIFY usava NOT EXISTS correlacionado e ESTOUROU
-- O TEMPO em 58 mil linhas. `EXCEPT` faz a mesma pergunta com hash de
-- conjunto e responde. A pergunta não mudou: existe alguma mensagem que
-- estava no backup e sumiu da tabela viva?
--
-- select 'copias que sobraram em observed_events' o, count(*) n from (
--   select 1 from observed_events where wa_timestamp is not null and text is not null
--   group by session_id,direction,wa_timestamp,msg_type,text having count(*)>1) x
-- union all
-- select 'copias que sobraram em attendance_transcripts', count(*) from (
--   select 1 from attendance_transcripts where wa_timestamp is not null and text is not null
--   group by session_id,direction,wa_timestamp,msg_type,text having count(*)>1) x
-- union all
-- select 'MENSAGENS PERDIDAS em observed_events', count(*) from (
--   select session_id,direction,wa_timestamp,msg_type,text from observed_events_copias_removidas_20260728
--   except
--   select session_id,direction,wa_timestamp,msg_type,text from observed_events) x
-- union all
-- select 'MENSAGENS PERDIDAS em attendance_transcripts', count(*) from (
--   select session_id,direction,wa_timestamp,msg_type,text from attendance_transcripts_copias_removidas_20260728
--   except
--   select session_id,direction,wa_timestamp,msg_type,text from attendance_transcripts) x;
--
-- SAÍDA REAL:
--   copias que sobraram em observed_events .............. 0
--   copias que sobraram em attendance_transcripts ....... 0
--   MENSAGENS PERDIDAS em observed_events ............... 0
--   MENSAGENS PERDIDAS em attendance_transcripts ........ 0
--
-- CONTAGENS:
--   observed_events ......... 20.506 -> 8.021   (7.799 únicas + 222 sem
--                                                identidade, que ficam)
--   attendance_transcripts .. 116.900 -> 58.811 (50.001 únicas + 8.808 sem
--                                                identidade + as que
--                                                chegaram ao vivo durante)
--   backup observed_events .............. 12.485
--   backup attendance_transcripts ....... 58.091
--
-- ---------------------------------------------------------------------
-- ROLLBACK  (devolve exatamente o que foi removido)
-- ---------------------------------------------------------------------
-- begin;
-- insert into public.observed_events
-- select b.* from public.observed_events_copias_removidas_20260728 b
-- where not exists (select 1 from public.observed_events e where e.id = b.id);
--
-- insert into public.attendance_transcripts
-- select b.* from public.attendance_transcripts_copias_removidas_20260728 b
-- where not exists (select 1 from public.attendance_transcripts e where e.id = b.id);
-- commit;
--
-- As tabelas de backup NÃO são apagadas por esta migration. Removê-las é
-- decisão separada, depois de o Founder confirmar que os mapas retecidos e o
-- Espelho redestilado estão corretos.
