-- =============================================================
-- MIGRATION: 20261002_11_spec126_papel_confirmacao
-- SPEC:      SPEC-126 — U2 (parte A) · o classificador da CONFIRMAÇÃO do acionamento (D5, §3.1 opção 2)
-- AUTOR:     builder U2a (Opus 5.5 xhigh)      DATA: 2026-10-02
-- OBJETIVO:  nasce o PAPEL `confirmacao` no Model Router (`llm_papeis`): o modelo que lê a resposta do
--            segurado à pergunta "…posso acionar?" e devolve {ok · nao · outra_coisa}
--            (`app/atendimento/confirmacao.py`). Primário openai/gpt-6-luna MEDIUM; reserva de OUTRO
--            provedor anthropic/claude-sonnet-5-5 LOW (o mesmo par da `visao`, SPEC-124 F2).
--            Esta migration NÃO liga nada: o portão (`insurer_dispatch_tool`) só passa a consultar o
--            papel na parte B da U2. Sem a linha, `classificar_confirmacao` cai em ModeloNaoResolvido →
--            `outra_coisa` (fail-closed: pede o ok de novo, nunca aciona).
--
-- 📊 ANTES (02/10/2026, lido do snapshot `app/factories/modelos_snapshot.json`, gerado do banco em
--    2026-10-01T22:51:04Z — `python -c "import json;d=json.load(open('app/factories/modelos_snapshot.json',
--    encoding='utf-8'));print('confirmacao' in d['papeis'], d['catalogo']['gpt-6-luna']['capacidades'])"`):
--    · `llm_papeis` SEM `confirmacao` (27 papéis);
--    · gpt-6-luna: APPROVED, openai, classes [interno, pii, publico],
--      🔴 `esforco_minimo_producao` = "medium" (migration 20260924_01) → o esforço "baixo" que o pacote
--      pediu é RECUSADO pelo gatilho `llm_papeis_so_modelo_governado` e por `model_policy._validar`.
--      O piso de produção é MEDIUM — é o que esta linha usa (a bancada mede o mesmo `medium`).
--    · claude-sonnet-5-5: APPROVED, anthropic, classes [interno, pii, publico], níveis low..max, sem mínimo.
--
-- 🔴 POR QUE `pii` E `critico`: a pergunta de confirmação carrega endereço e final de placa, e a leitura
--    decide um acionamento que não se desfaz (T8) — o mesmo risco do `destravador`/`dispatch`.
-- 🔴 POR QUE A RESERVA É DE OUTRO PROVEDOR: a reserva só entra em 429/5xx/timeout/disjuntor aberto
--    (`invocar_com_reserva`); do mesmo provedor ela cairia junto.
--
-- APPLY:
--   A. INSERT `confirmacao` em `llm_papeis` (`on conflict (papel) do nothing` — reaplicar não muda nada;
--      o gatilho `llm_papeis_so_modelo_governado` confere catálogo, provedor, APPROVED, classe e esforço
--      ≥ mínimo, e RECUSA a linha se algo não bater).
--   B. asserção: o estado final é o desta migration, ou a transação inteira desfaz.
--
-- VERIFY (read-only; o bloco DO desfaz o que testa):
--   -- 1) a rota
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva,
--          classe_de_dado, risco, versao, atualizado_por
--     from public.llm_papeis where papel = 'confirmacao';
--   -- esperado: confirmacao | openai | gpt-6-luna | medium | anthropic | claude-sonnet-5-5 | low | pii | critico | 1 | migration 20261002_11
--   -- 2) 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3): a mesma linha com a Luna em `low` é recusada pelo
--   --    gatilho; a linha certa (controle) passa — e nada fica gravado.
--   do $$
--   declare recusou_low boolean := false; aceitou_medium boolean := false; n int;
--   begin
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_126_conf_low', 'verify', 'openai', 'gpt-6-luna', 'low', 'pii', 'critico', 1, 'verify', 'verify');
--     exception when check_violation then recusou_low := true; end;
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_126_conf_medium', 'verify', 'openai', 'gpt-6-luna', 'medium', 'pii', 'critico', 1, 'verify', 'verify');
--       aceitou_medium := true;
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select count(*) into n from public.llm_papeis where papel like 'verify_126_conf%';
--     if not (recusou_low and aceitou_medium) or n <> 0 then
--       raise exception 'VERIFY 20261002_11 FALHOU: low_recusado=% medium_aceito=% sobrou=%', recusou_low, aceitou_medium, n;
--     end if;
--     raise notice 'VERIFY 20261002_11 OK: luna low recusada, medium aceita, nada gravado';
--   end $$;
--   -- 3) o produto lê a rota (regerar o snapshot e resolver pelo Model Router):
--   --   python scripts/gerar_snapshot_de_modelos.py --banco
--   --   python -c "from app.factories import model_policy as M; r=M.resolver('confirmacao'); print(r.model, r.effort, r.classe_de_dado, r.reserva.model, r.reserva.effort)"
--   --   -- esperado: gpt-6-luna medium pii claude-sonnet-5-5 low
--   --   python -m pytest -q tests/test_spec126_u2a_classificador.py -k papel   (o teste do snapshot deixa de pular)
--
-- ROLLBACK:  (escrito ANTES de aplicar; nenhuma FK aponta para llm_papeis — o código cai em
--            ModeloNaoResolvido → `outra_coisa`, falha fechada)
--   delete from public.llm_papeis where papel = 'confirmacao';
--   delete from supabase_migrations.schema_migrations where name = 'spec126_papel_confirmacao';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — uma linha nova; nenhuma coluna, CHECK, gatilho ou rota existente muda.
-- DESTRUTIVA:   não.
-- =============================================================

-- -------------------------------------------------------------
-- A. o papel `confirmacao`
-- -------------------------------------------------------------
insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco,
  provider_reserva, modelo_reserva, esforco_reserva, classe_de_dado, risco, versao, motivo,
  atualizado_por)
values
  ('confirmacao',
   'SPEC-126 U2 — lê a resposta do segurado à pergunta de confirmação do acionamento e devolve ok · nao · outra_coisa (portão = regex E classificador) — app/atendimento/confirmacao.py',
   'openai', 'gpt-6-luna', 'medium', 'anthropic', 'claude-sonnet-5-5', 'low',
   'pii', 'critico', 1,
   'SPEC-126 D5 / §3.1 opção (2) nota 92 · Luna no piso de produção (medium); reserva de outro provedor (par da visao)',
   'migration 20261002_11')
on conflict (papel) do nothing;

-- -------------------------------------------------------------
-- B. asserção — o estado final é o desta migration, ou nada fica
-- -------------------------------------------------------------
do $$
declare n int;
begin
  select count(*) into n from public.llm_papeis
   where papel = 'confirmacao' and provider = 'openai' and modelo_primario = 'gpt-6-luna'
     and esforco = 'medium' and provider_reserva = 'anthropic' and modelo_reserva = 'claude-sonnet-5-5'
     and esforco_reserva = 'low' and classe_de_dado = 'pii' and risco = 'critico';
  if n <> 1 then
    raise exception '20261002_11: estado final inesperado (% de 1 rota certa)', n;
  end if;
end $$;
