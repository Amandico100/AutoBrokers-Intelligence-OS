-- =============================================================
-- MIGRATION: 20260930_03_spec123_destravador_modos_e_papeis
-- SPEC:      SPEC-123 — F1a · o destravador e a política
-- AUTOR:     builder F1a (Opus 5.5 xhigh)      DATA: 2026-09-30
-- OBJETIVO:  a chave `cerebro_modos` passa a aceitar `on` (o destravador AGE) e
--            ganha o LIMIAR da decisão DEDUZIR (70 a 100 — nunca abaixo de 70,
--            D2 do Founder); e os dois PAPÉIS de modelo do destravador nascem no
--            catálogo de rotas (`llm_papeis`) com os valores PROVISÓRIOS do
--            contrato — a F2 decide pela bancada e reescreve por migration.
--
-- 📊 ANTES (30/09/2026, SELECT read-only pelo MCP):
--    · `cerebro_modos`: 0 linhas; constraint
--      `ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou`
--      = CHECK (modo = ANY (ARRAY['off','sombra'])); sem coluna `limiar`.
--    · `llm_papeis`: sem `destravador` e sem `destravador_segunda`;
--      `gpt-6.1-sol` (openai) e `claude-sonnet-5-5` (anthropic) APPROVED, os dois
--      com `pii` em classes_de_dado, esforços low..max, sem esforco_minimo_producao.
--
-- 🔴 POR QUE A CONSTRAINT DO `on` SAI (D5 do Founder, 30/09/2026): a porta de
--    ligar deixou de ser "zero erro grave na bancada" (a regra da SPEC-122, que
--    não ligou nada) e passou a ser a CALIBRAÇÃO + zero violação do NUNCA, em
--    CÓDIGO (`app/services/destravador.py`). O banco continua recusando qualquer
--    modo fora de off|sombra|on, e agora recusa limiar < 70.
--
-- 🔴 POR QUE O LIMIAR MORA AQUI E NÃO NO CÓDIGO: a calibração (F2) pode SUBIR o
--    limiar por seguradora/ramo sem deploy. Baixar abaixo de 70 exige ordem do
--    Founder — por isso o CHECK, e não só o `max(70, …)` do código (os dois
--    existem: o banco recusa, o código não confia).
--
-- 🔴 POR QUE DOIS PAPÉIS (D3/D4): a 2ª opinião do DEDUZIR tem de vir de OUTRO
--    PROVEDOR. `destravador` = openai primário / anthropic reserva;
--    `destravador_segunda` = o inverso. O código escolhe, na hora, o candidato da
--    segunda cujo provedor é diferente do que DECIDIU DE FATO (se a reserva
--    decidiu, a segunda troca de lado). Valores PROVISÓRIOS (contrato da SPEC-123):
--    `on conflict do nothing` — esta migration NÃO sobrescreve o que a F2 gravar.
--
-- APPLY:
--   A. cerebro_modos: nova constraint `ck_cerebro_modos_modo_valido`
--      (off|sombra|on) ANTES de soltar a antiga (expand-first: a nova aceita um
--      superconjunto); depois `drop constraint if exists` da antiga.
--   B. cerebro_modos.limiar smallint NOT NULL DEFAULT 70 + CHECK 70..100
--      (`ck_cerebro_modos_limiar_entre_70_e_100`). Tabela com 0 linhas: o NOT NULL
--      com default não reescreve nada.
--   C. llm_papeis: INSERT `destravador` e `destravador_segunda` (on conflict do
--      nothing). O trigger `llm_papeis_so_modelo_governado` confere catálogo,
--      provedor, APPROVED, classe `pii` e esforço — ele recusa a linha se algo
--      não bater.
--   D. comments atualizados (a tabela deixa de dizer que o `on` é recusado).
--
-- VERIFY (read-only; o bloco DO desfaz tudo o que testa):
--   -- 1) as constraints do modo e do limiar, e a antiga fora
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid = 'public.cerebro_modos'::regclass and contype = 'c' order by 1;
--   -- esperado: ck_cerebro_modos_insurer_minusculo · ck_cerebro_modos_limiar_entre_70_e_100
--   --   CHECK (limiar >= 70 AND limiar <= 100) · ck_cerebro_modos_modo_valido
--   --   CHECK (modo = ANY (ARRAY['off','sombra','on'])) · ck_cerebro_modos_ramo_minusculo
--   --   e NENHUMA ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou
--   -- 2) a coluna
--   select column_name, data_type, is_nullable, column_default from information_schema.columns
--    where table_schema = 'public' and table_name = 'cerebro_modos' and column_name = 'limiar';
--   -- esperado: limiar · smallint · NO · 70
--   -- 3) os papéis
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva,
--          esforco_reserva, classe_de_dado, risco, versao
--     from public.llm_papeis where papel like 'destravador%' order by 1;
--   -- esperado: destravador | openai | gpt-6.1-sol | high | anthropic | claude-sonnet-5-5 | NULL | pii | critico | 1
--   --           destravador_segunda | anthropic | claude-sonnet-5-5 | NULL | openai | gpt-6.1-sol | high | pii | critico | 1
--   -- 4) 🔴 O CHECK CONSEGUE RECUSAR (CLAUDE.md §9.3): 69 e 101 recusados, `on` e 70
--   --    ACEITOS (controle), modo inventado recusado — e nada fica gravado.
--   do $$
--   declare v_cid uuid; r69 boolean := false; r101 boolean := false; rtalvez boolean := false;
--           aceitou_on boolean := false; n int;
--   begin
--     select id into v_cid from public.companies order by created_at limit 1;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar)
--       values (v_cid, 'verify_123', 'todos', 'on', 69);
--     exception when check_violation then r69 := true; end;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar)
--       values (v_cid, 'verify_123', 'todos', 'on', 101);
--     exception when check_violation then r101 := true; end;
--     begin
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar)
--       values (v_cid, 'verify_123', 'todos', 'talvez', 80);
--     exception when check_violation then rtalvez := true; end;
--     begin  -- CONTROLE: `on` com 70 PASSA (e é desfeito pelo raise do sub-bloco)
--       insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar)
--       values (v_cid, 'verify_123', 'todos', 'on', 70);
--       aceitou_on := true;
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select count(*) into n from public.cerebro_modos where insurer_key = 'verify_123';
--     if not (r69 and r101 and rtalvez and aceitou_on) or n <> 0 then
--       raise exception 'VERIFY 20260930_03 FALHOU: r69=% r101=% rtalvez=% on70=% sobrou=%',
--         r69, r101, rtalvez, aceitou_on, n;
--     end if;
--     raise notice 'VERIFY 20260930_03 OK: 69/101/talvez recusados, on+70 aceito, nada gravado';
--   end $$;
--
-- ROLLBACK:  (escrito ANTES de aplicar)
--   -- C. os papéis (nenhuma FK aponta para llm_papeis; o código cai em
--   --    ModeloNaoResolvido → o destravador devolve PESSOA, falha fechada)
--   delete from public.llm_papeis where papel in ('destravador', 'destravador_segunda');
--   -- A/B. um `on` gravado não cabe na constraint antiga: vira `off` antes
--   update public.cerebro_modos set modo = 'off', updated_at = now() where modo = 'on';
--   alter table public.cerebro_modos drop constraint if exists ck_cerebro_modos_limiar_entre_70_e_100;
--   alter table public.cerebro_modos drop column if exists limiar;
--   alter table public.cerebro_modos add constraint ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou
--     check (modo in ('off', 'sombra'));
--   alter table public.cerebro_modos drop constraint if exists ck_cerebro_modos_modo_valido;
--   delete from supabase_migrations.schema_migrations where name = 'spec123_destravador_modos_e_papeis';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — a constraint nova (superconjunto) entra antes de a antiga
--               sair; coluna nova com default; papéis novos, nenhum alterado.
-- DESTRUTIVA:   não — nenhum dado muda (cerebro_modos tem 0 linhas; nenhum papel
--               existente é tocado). Esta migration NÃO liga nada: nenhuma linha
--               em cerebro_modos (ligar é da F3/gerente).
-- =============================================================

-- -------------------------------------------------------------
-- A. o modo `on` passa a existir (expand-first: a nova antes de a antiga sair)
-- -------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.cerebro_modos'::regclass
                    and conname = 'ck_cerebro_modos_modo_valido') then
    alter table public.cerebro_modos
      add constraint ck_cerebro_modos_modo_valido check (modo in ('off', 'sombra', 'on'));
  end if;
end $$;

alter table public.cerebro_modos
  drop constraint if exists ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou;

-- -------------------------------------------------------------
-- B. o limiar do DEDUZIR — 70 a 100; nunca abaixo de 70 (D2 do Founder)
-- -------------------------------------------------------------
alter table public.cerebro_modos
  add column if not exists limiar smallint not null default 70;

do $$
begin
  if not exists (select 1 from pg_constraint
                  where conrelid = 'public.cerebro_modos'::regclass
                    and conname = 'ck_cerebro_modos_limiar_entre_70_e_100') then
    alter table public.cerebro_modos
      add constraint ck_cerebro_modos_limiar_entre_70_e_100 check (limiar between 70 and 100);
  end if;
end $$;

-- -------------------------------------------------------------
-- C. os papéis do destravador (PROVISÓRIOS — a F2 reescreve pela bancada)
-- -------------------------------------------------------------
insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco,
  provider_reserva, modelo_reserva, esforco_reserva, classe_de_dado, risco, versao, motivo,
  atualizado_por)
values
  ('destravador',
   'SPEC-123 — o destravador do acionamento: quando o roteiro fixo trava, decide UMA tela com '
   || 'contexto completo (classe, nota 0–100, motivo) — app/services/destravador.py',
   'openai', 'gpt-6.1-sol', 'high', 'anthropic', 'claude-sonnet-5-5', null,
   'pii', 'critico', 1,
   'SPEC-123 F1a · valores PROVISÓRIOS do contrato (30/09/2026); a F2 decide pela bancada (D4)',
   'migration 20260930_03'),
  ('destravador_segunda',
   'SPEC-123 — a 2ª opinião do DEDUZIR, de OUTRO provedor que o que decidiu (D3) — '
   || 'app/services/destravador.py',
   'anthropic', 'claude-sonnet-5-5', null, 'openai', 'gpt-6.1-sol', 'high',
   'pii', 'critico', 1,
   'SPEC-123 F1a · valores PROVISÓRIOS do contrato (30/09/2026); a F2 decide pela bancada (D4)',
   'migration 20260930_03')
on conflict (papel) do nothing;

-- -------------------------------------------------------------
-- D. a tabela diz a verdade de hoje
-- -------------------------------------------------------------
comment on table public.cerebro_modos is
  'SPEC-122 F3 + SPEC-123 F1a — a chave do DESTRAVADOR por corretora × seguradora × ramo: off (padrão; sem linha = off, o produto de hoje byte a byte), sombra (decide e grava no diário, NÃO envia) ou on (age). limiar = a nota mínima do DEDUZIR (70..100; D2 do Founder: nunca abaixo de 70).';
comment on column public.cerebro_modos.modo is
  'off | sombra | on (ck_cerebro_modos_modo_valido). O on era recusado na SPEC-122; a SPEC-123 (D5 do Founder, 30/09/2026) trocou a porta: calibração + zero violação do NUNCA, em código (destravador.py).';
comment on column public.cerebro_modos.limiar is
  'Nota mínima (0–100) para o destravador DEDUZIR sozinho (com 2ª opinião de outro provedor). 70..100 por CHECK; a calibração (SPEC-123 F2) pode SUBIR; baixar abaixo de 70 exige ordem do Founder.';
