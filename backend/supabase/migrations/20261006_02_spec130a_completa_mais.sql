-- =============================================================
-- MIGRATION: 20261006_02_spec130a_completa_mais
-- SPEC:      SPEC-130-A — F4 A 3ª opção "Mais completa" (completa+, D-MC-69 / D-130A-09)
-- AUTOR:     builder F4 (Opus 5.5)            DATA: 2026-10-06
-- OBJETIVO:  o pedido e o cálculo do multicálculo passam a aceitar a opção `completa_mais` (a padrão + pequenos reparos,
--            `portal_worker/multicalculo/presets.py:_COMPLETA_MAIS`), calculada no MESMO negócio depois da econômica.
--
-- 📊 ANTES (texto de 20261005_01, APLICADA 05/10 — não lido do banco nesta fatia: o builder não toca o banco; o VERIFY
--    abaixo confere a forma DEPOIS do APPLY):
--    · ck_mc_pedidos_opcoes  check (cardinality(opcoes) >= 1 and opcoes <@ array['padrao', 'economica']::text[])
--    · ck_mc_calculos_opcao  check (opcao in ('padrao', 'economica', 'ajuste'))
--
-- APPLY:  num ÚNICO bloco DO (uma transação): para cada uma das duas CHECKs, SÓ se o texto atual ainda não admite
--         `completa_mais`: drop + add com a lista ALARGADA. Expand-only: todo valor que valia continua valendo
--         (padrao, economica; ajuste no cálculo); a cardinalidade ≥ 1 do pedido e a `ck_mc_calculos_ajuste` (só o ajuste
--         tem origem) ficam intactas. Idempotente (2ª execução = nada muda).
--
-- VERIFY (read-only · esperado: 1 · 1 · 2 · 1):
--   select (select count(*) from pg_constraint where conrelid='public.multicalculo_pedidos'::regclass
--             and conname='ck_mc_pedidos_opcoes' and pg_get_constraintdef(oid) like '%cardinality%'
--             and pg_get_constraintdef(oid) like '%''padrao''%' and pg_get_constraintdef(oid) like '%''economica''%'
--             and pg_get_constraintdef(oid) like '%''completa_mais''%') pedidos_opcoes,
--          (select count(*) from pg_constraint where conrelid='public.multicalculo_calculos'::regclass
--             and conname='ck_mc_calculos_opcao'
--             and pg_get_constraintdef(oid) like '%''padrao''%' and pg_get_constraintdef(oid) like '%''economica''%'
--             and pg_get_constraintdef(oid) like '%''ajuste''%' and pg_get_constraintdef(oid) like '%''completa_mais''%')
--            calculos_opcao,
--          (select count(*) from pg_constraint where conname in ('ck_mc_pedidos_opcoes','ck_mc_calculos_opcao')
--             and contype='c' and convalidated) validadas,
--          (select count(*) from pg_constraint where conrelid='public.multicalculo_calculos'::regclass
--             and conname='ck_mc_calculos_ajuste') ajuste_intacto;
--
-- VERIFY comportamental (o DO desfaz o que testa — raise P0001 no fim do sub-bloco; nada fica).
-- 🔴 `text[] || 'literal'` é AMBÍGUO em PL/pgSQL (defeito real de 06/10 na 20261006_01): todo item leva `::text`.
--   do $$
--   declare a uuid; p uuid; c1 uuid; r text; res text[] := '{}';
--   begin
--     select id into a from public.companies where company_kind='client' order by created_at limit 1;
--     if a is null then raise exception 'VERIFY 20261006_02: falta uma corretora cliente'; end if;
--     begin
--       -- 1 · o pedido com as 3 opções entra
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--               values (a,'auxiliar',array['padrao','economica','completa_mais']::text[],array[a],'x') returning id into p;
--             r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pedido_tres='||r)::text;
--       if p is null then   -- sem o pedido do 1, os próximos não têm onde se apoiar: um pedido da 129-B (controle)
--         insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--           values (a,'auxiliar',array['padrao']::text[],array[a],'x') returning id into p;
--       end if;
--       -- 2 · CONTROLE: o pedido da 129-B (padrão + econômica) continua entrando
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--               values (a,'auxiliar',array['padrao','economica']::text[],array[a],'x'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pedido_duas='||r)::text;
--       -- 3 · opção desconhecida no pedido → recusa (a lista continua FECHADA)
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--               values (a,'auxiliar',array['padrao','completa']::text[],array[a],'x'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pedido_desconhecida='||r)::text;
--       -- 4 · pedido sem opção → recusa (a cardinalidade ≥ 1 ficou)
--       begin insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)
--               values (a,'auxiliar','{}'::text[],array[a],'x'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('pedido_vazio='||r)::text;
--       -- 5 · CONTROLE: o cálculo da padrão entra (é a origem do 8)
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas)
--               values (p,a,a,'padrao','{}') returning id into c1; r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('calculo_padrao='||r)::text;
--       -- 6 · o cálculo da completa+ entra
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas)
--               values (p,a,a,'completa_mais','{"reparoRapido": true}'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('calculo_completa_mais='||r)::text;
--       -- 7 · opção desconhecida no cálculo → recusa
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas)
--               values (p,a,a,'completa_maiss','{}'); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('calculo_desconhecida='||r)::text;
--       -- 8 · a completa+ com origem (só o AJUSTE tem origem) → `ck_mc_calculos_ajuste` recusa
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas,
--                                                       origem_calculo_id)
--               values (p,a,a,'completa_mais','{}',c1); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('completa_mais_com_origem='||r)::text;
--       -- 9 · CONTROLE: o ajuste (com origem) continua entrando
--       begin insert into public.multicalculo_calculos (pedido_id, solicitante_company_id, company_id, opcao, coberturas,
--                                                       origem_calculo_id)
--               values (p,a,a,'ajuste','{}',c1); r := 'aceito';
--       exception when check_violation then r := 'recusado'; end;  res := res || ('ajuste='||r)::text;
--       raise exception using errcode='P0001', message='desfaz';
--     exception when sqlstate 'P0001' then null;
--     end;
--     if res is distinct from array['pedido_tres=aceito','pedido_duas=aceito','pedido_desconhecida=recusado',
--                                   'pedido_vazio=recusado','calculo_padrao=aceito','calculo_completa_mais=aceito',
--                                   'calculo_desconhecida=recusado','completa_mais_com_origem=recusado',
--                                   'ajuste=aceito']::text[] then
--       raise exception 'VERIFY 20261006_02 FALHOU: %', res;
--     end if;
--     raise notice 'VERIFY 20261006_02 OK: %', res;
--   end $$;
--
-- ROLLBACK (🔴 executar é decisão do Founder — MIGRATIONS-AUTHORITY §8.6; RECUSA se houver linha com `completa_mais`,
--           que a CHECK estreitada não deixaria existir; volta o texto EXATO de 20261005_01):
--   do $$ begin
--     if exists (select 1 from public.multicalculo_calculos where opcao = 'completa_mais')
--        or exists (select 1 from public.multicalculo_pedidos where 'completa_mais' = any(opcoes)) then
--       raise exception 'ROLLBACK 20261006_02 recusado: há pedido ou cálculo da completa+ — apagar dado é decisão do Founder';
--     end if;
--     alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_opcoes;
--     alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_opcoes
--       check (cardinality(opcoes) >= 1 and opcoes <@ array['padrao', 'economica']::text[]);
--     alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_opcao;
--     alter table public.multicalculo_calculos add constraint ck_mc_calculos_opcao
--       check (opcao in ('padrao', 'economica', 'ajuste'));
--   end $$;
--
-- EXPAND-FIRST: sim (as duas CHECKs são ALARGADAS, nunca estreitadas; nada é removido nem renomeado)
-- DESTRUTIVA:   não
-- LOCK:         ACCESS EXCLUSIVE breve em `multicalculo_pedidos` e `multicalculo_calculos` (drop + add da CHECK, que
--               revalida as linhas existentes — tabelas pequenas) — aplicar com `set lock_timeout='5s'`.
-- ORDEM:        ANTES do código que PEDE `completa_mais` (a porta da F4). O código de hoje nunca grava `completa_mais`,
--               então aplicar antes do Implantar não muda nada para ele; Implantar antes de aplicar = a porta aceita e o
--               banco recusa o INSERT (check_violation) — fail-closed, nada sai no Agger.
-- =============================================================

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.multicalculo_pedidos'::regclass and conname = 'ck_mc_pedidos_opcoes'
                    and pg_get_constraintdef(oid) like '%completa_mais%') then
    alter table public.multicalculo_pedidos drop constraint if exists ck_mc_pedidos_opcoes;
    alter table public.multicalculo_pedidos add constraint ck_mc_pedidos_opcoes
      check (cardinality(opcoes) >= 1 and opcoes <@ array['padrao', 'economica', 'completa_mais']::text[]);
  end if;
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.multicalculo_calculos'::regclass and conname = 'ck_mc_calculos_opcao'
                    and pg_get_constraintdef(oid) like '%completa_mais%') then
    alter table public.multicalculo_calculos drop constraint if exists ck_mc_calculos_opcao;
    alter table public.multicalculo_calculos add constraint ck_mc_calculos_opcao
      check (opcao in ('padrao', 'economica', 'completa_mais', 'ajuste'));
  end if;
end $$;

comment on constraint ck_mc_pedidos_opcoes on public.multicalculo_pedidos is
  'SPEC-129-B + SPEC-130-A F4: as opções que um pedido pode pedir — padrao, economica e completa_mais (a padrão + '
  'pequenos reparos, D-MC-69). Gêmeo de app/services/multicalculo/porta.py:OPCOES.';
comment on constraint ck_mc_calculos_opcao on public.multicalculo_calculos is
  'SPEC-129-B + SPEC-130-A F4: padrao, economica, completa_mais (presets em portal_worker/multicalculo/presets.py) e '
  'ajuste (o recálculo do corretor, o único com origem).';
