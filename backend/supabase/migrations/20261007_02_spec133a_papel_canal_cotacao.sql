-- =============================================================
-- MIGRATION: 20261007_02_spec133a_papel_canal_cotacao
-- SPEC:      SPEC-133-A — U4 (D-133A-01) · a conversa do canal "Quem Cobra Menos" no WhatsApp
-- AUTOR:     builder F2 (Opus 5.5)      DATA: 2026-10-07
-- OBJETIVO:  nasce o PAPEL `canal_cotacao` no Model Router (`llm_papeis`): o modelo que só ENTENDE a resposta LIVRE
--            que a regra não entendeu (sim/não dito de outro jeito, "rodo uns mil e duzentos", "vou pensar") e devolve
--            JSON {valor, fora_do_escopo} (`app/services/canal/conversa.py:entender`). A conversa é guiada por ESTADO;
--            CPF, placa, CEP, nome e datas NUNCA vão ao modelo. Primário openai/gpt-6-luna MEDIUM (o mais barato
--            aprovado); reserva de OUTRO provedor anthropic/claude-sonnet-5-5 LOW (o par da `confirmacao`).
--            Sem a linha, `entender` cai em ModeloNaoResolvido → None → a conversa PERGUNTA DE NOVO (fail-closed:
--            nunca inventa uma resposta).
--
-- 📊 ANTES (07/10/2026, SELECT só leitura pelo MCP no projeto dcajcvlzcjbmyapmklil):
--    · `select papel from llm_papeis where papel='canal_cotacao'` → 0 linhas;
--    · a forma da linha: `confirmacao | openai | gpt-6-luna | medium | anthropic | claude-sonnet-5-5 | low | pii |
--      critico | 1` (a molde desta);
--    · `llm_pricing` APPROVED: gpt-6-luna openai US$ 0,10/0,50 por 1 M, classes publico,interno,pii,
--      esforco_minimo_producao = medium (🔴 `low` é RECUSADO pelo gatilho `llm_papeis_so_modelo_governado`);
--      claude-sonnet-5-5 anthropic US$ 2/10, classes publico,interno,pii;
--    · CHECKs: classe ∈ {publico, interno, pii} · risco ∈ {baixo, medio, alto, critico} · reserva completa.
--
-- 🔴 POR QUE `pii`: a resposta livre de uma pessoa pode trazer dado pessoal sem querer ("sou a Maria, 31 anos").
-- 🔴 POR QUE `alto` (e não `critico`): o modelo não decide nada que saia do prédio — a REGRA reconfere o valor que ele
--    devolve e a conversa só segue com o valor reconferido; o envio ao Agger depende do perfil inteiro validado.
-- 🔴 POR QUE A RESERVA É DE OUTRO PROVEDOR: a reserva só entra em 429/5xx/timeout/disjuntor aberto
--    (`invocar_com_reserva`); do mesmo provedor ela cairia junto.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. INSERT `canal_cotacao` em `llm_papeis` (`on conflict (papel) do nothing` — reaplicar não muda nada; o gatilho
--      `llm_papeis_so_modelo_governado` confere catálogo, provedor, APPROVED, classe e esforço ≥ mínimo).
--   B. asserção: o estado final é o desta migration, ou a transação inteira desfaz.
--
-- VERIFY (read-only; o bloco DO desfaz o que testa):
--   -- 1) a rota
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva,
--          classe_de_dado, risco, versao, atualizado_por
--     from public.llm_papeis where papel = 'canal_cotacao';
--   -- esperado: canal_cotacao | openai | gpt-6-luna | medium | anthropic | claude-sonnet-5-5 | low | pii | alto | 1 | migration 20261007_02
--   -- 2) 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3): a mesma linha com a Luna em `low` é recusada; a certa passa;
--   --    nada fica gravado.
--   do $$
--   declare recusou_low boolean := false; aceitou_medium boolean := false; n int;
--   begin
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_133a_low', 'verify', 'openai', 'gpt-6-luna', 'low', 'pii', 'alto', 1, 'verify', 'verify');
--     exception when check_violation then recusou_low := true; end;
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_133a_medium', 'verify', 'openai', 'gpt-6-luna', 'medium', 'pii', 'alto', 1, 'verify', 'verify');
--       aceitou_medium := true;
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select count(*) into n from public.llm_papeis where papel like 'verify_133a%';
--     if not (recusou_low and aceitou_medium) or n <> 0 then
--       raise exception 'VERIFY 20261007_02 FALHOU: low_recusado=% medium_aceito=% sobrou=%', recusou_low, aceitou_medium, n;
--     end if;
--     raise notice 'VERIFY 20261007_02 OK: luna low recusada, medium aceita, nada gravado';
--   end $$;
--   -- 3) o produto lê a rota (regerar o snapshot e resolver pelo Model Router):
--   --   python scripts/gerar_snapshot_de_modelos.py --banco
--   --   python -c "from app.factories import model_policy as M; r=M.resolver('canal_cotacao'); print(r.model, r.effort, r.classe_de_dado, r.reserva.model, r.reserva.effort)"
--   --   -- esperado: gpt-6-luna medium pii claude-sonnet-5-5 low
--
-- ROLLBACK:  (escrito ANTES de aplicar; nenhuma FK aponta para llm_papeis — o código cai em ModeloNaoResolvido →
--            a conversa pergunta de novo, falha fechada)
--   delete from public.llm_papeis where papel = 'canal_cotacao';
--   delete from supabase_migrations.schema_migrations where name = 'spec133a_papel_canal_cotacao';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — uma linha nova; nenhuma coluna, CHECK, gatilho ou rota existente muda.
-- DESTRUTIVA:   não.
-- =============================================================

-- -------------------------------------------------------------
-- A. o papel `canal_cotacao`
-- -------------------------------------------------------------
insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco,
  provider_reserva, modelo_reserva, esforco_reserva, classe_de_dado, risco, versao, motivo,
  atualizado_por)
values
  ('canal_cotacao',
   'SPEC-133-A U4 — entende a resposta LIVRE da pessoa na conversa do canal (sim/não, número, intenção) e devolve {valor, fora_do_escopo}; a regra reconfere — app/services/canal/conversa.py',
   'openai', 'gpt-6-luna', 'medium', 'anthropic', 'claude-sonnet-5-5', 'low',
   'pii', 'alto', 1,
   'SPEC-133-A D-133A-01 nota 86 · o mais barato aprovado (gpt-6-luna, piso de produção medium); reserva de outro provedor (par da confirmacao)',
   'migration 20261007_02')
on conflict (papel) do nothing;

-- -------------------------------------------------------------
-- B. asserção — o estado final é o desta migration, ou nada fica
-- -------------------------------------------------------------
do $$
declare n int;
begin
  select count(*) into n from public.llm_papeis
   where papel = 'canal_cotacao' and provider = 'openai' and modelo_primario = 'gpt-6-luna'
     and esforco = 'medium' and provider_reserva = 'anthropic' and modelo_reserva = 'claude-sonnet-5-5'
     and esforco_reserva = 'low' and classe_de_dado = 'pii' and risco = 'alto';
  if n <> 1 then
    raise exception '20261007_02: estado final inesperado (% de 1 rota certa)', n;
  end if;
end $$;
