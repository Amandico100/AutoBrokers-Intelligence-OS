-- =============================================================
-- MIGRATION: 20261011_05_spec130b_papel_leitura_de_apolice
-- SPEC:      SPEC-130-B — F1 · o motor (D-130B-09) · a ficha única da apólice
-- AUTOR:     builder F1 (Opus 5.5 xhigh)      DATA: 2026-10-11
-- OBJETIVO:  nasce o PAPEL `leitura_de_apolice` no Model Router (`llm_papeis`): o modelo barato que lê a
--            TABELA DE COBERTURAS de um documento de seguro quando o regex não fecha o prêmio (degrau 2, texto
--            MASCARADO — CPF/CNPJ/telefone/e-mail/CEP/placa trocados por marcadores; o dinheiro passa) e as páginas
--            SEM texto como imagem (degrau 3). Quem chama: `app/services/policy_document_evidence_service.py`
--            (`_leitor_modelo_padrao` / `_leitor_visao_padrao` → `invocar_com_reserva('leitura_de_apolice', …)`).
--            Sem a linha, o degrau cai em ModeloNaoResolvido → a leitura fica com o regex e o estado diz
--            "nao_fechou" (falha fechada: nunca uma cobertura inventada, e o corretor vê o aviso).
--
-- 📊 ANTES (11/10/2026, SELECT só leitura pelo MCP no projeto dcajcvlzcjbmyapmklil):
--    · `select … from llm_papeis where papel in ('leitura_de_apolice','visao','canal_cotacao','auxiliar')`
--      → `leitura_de_apolice` AUSENTE; a molde: `visao | openai | gpt-6-luna | medium | anthropic |
--      claude-sonnet-5-5 | low | pii | alto | 5`;
--    · `llm_pricing`: gpt-6-luna openai APPROVED, classes {publico,interno,pii}, níveis
--      {none..max}, esforco_minimo_producao = medium; claude-sonnet-5-5 anthropic APPROVED, classes
--      {publico,interno,pii}, níveis {low..max}, sem mínimo;
--    · CHECKs de llm_papeis: classe ∈ {publico, interno, pii} · risco ∈ {baixo, medio, alto, critico} ·
--      esforço ∈ {none..max} · reserva completa (provider e modelo juntos).
--    · BLOCO 0 da SPEC-130-B item 4: a Luna medium leu a Tokio condomínio (20 linhas, Σ = prêmio líquido,
--      20/20 trechos literais, 123,5 s, US$ 0,0017) e a Allianz empresarial (7 linhas, Σ = líquido, 10,3 s,
--      US$ 0,0006) — `token_usage_logs service_type='bancada_130b'`.
--
-- 🔴 POR QUE `pii`: o texto vai MASCARADO, mas nome de pessoa e endereço não têm forma para a máscara
--    reconhecer — a classe declara o pior caso que pode chegar ao modelo.
-- 🔴 POR QUE `alto` (e não `critico`): o modelo não decide nada sozinho — toda linha dele passa pela conferência
--    do TRECHO LITERAL e a leitura só vale se o JUIZ (Σ prêmio = prêmio líquido) fechar.
-- 🔴 POR QUE A RESERVA É DE OUTRO PROVEDOR, e MEDIUM: a reserva só entra em 429/5xx/timeout/disjuntor aberto
--    (`invocar_com_reserva`); do mesmo provedor ela cairia junto. `medium` (e não o `low` da `visao`) porque a
--    tarefa é ler uma tabela inteira com trecho literal, não descrever uma foto (D-130B-09).
--
-- APPLY (pelo GERENTE — o builder NÃO aplica):
--   A. INSERT `leitura_de_apolice` em `llm_papeis` (`on conflict (papel) do nothing` — reaplicar não muda nada;
--      o gatilho `llm_papeis_so_modelo_governado` confere catálogo, provedor, APPROVED, classe e esforço ≥ mínimo).
--   B. asserção: o estado final é o desta migration, ou a transação inteira desfaz.
--
-- VERIFY (read-only; o bloco DO desfaz o que testa):
--   -- 1) a rota
--   select papel, provider, modelo_primario, esforco, provider_reserva, modelo_reserva, esforco_reserva,
--          classe_de_dado, risco, versao, atualizado_por
--     from public.llm_papeis where papel = 'leitura_de_apolice';
--   -- esperado: leitura_de_apolice | openai | gpt-6-luna | medium | anthropic | claude-sonnet-5-5 | medium |
--   --           pii | alto | 1 | migration 20261011_05
--   -- 2) 🔴 a TRAVA consegue recusar (CLAUDE.md §9.3): a mesma rota com a Luna em `low` é recusada; a certa
--   --    passa; nada fica gravado.
--   do $$
--   declare recusou_low boolean := false; aceitou_medium boolean := false; n int;
--   begin
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_130b_low', 'verify', 'openai', 'gpt-6-luna', 'low', 'pii', 'alto', 1, 'verify', 'verify');
--     exception when check_violation then recusou_low := true; end;
--     begin
--       insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco, classe_de_dado,
--         risco, versao, motivo, atualizado_por)
--       values ('verify_130b_medium', 'verify', 'openai', 'gpt-6-luna', 'medium', 'pii', 'alto', 1, 'verify', 'verify');
--       aceitou_medium := true;
--       raise exception using errcode = 'P0001', message = 'desfaz-controle';
--     exception when sqlstate 'P0001' then null; end;
--     select count(*) into n from public.llm_papeis where papel like 'verify_130b%';
--     if not (recusou_low and aceitou_medium) or n <> 0 then
--       raise exception 'VERIFY 20261011_05 FALHOU: low_recusado=% medium_aceito=% sobrou=%', recusou_low, aceitou_medium, n;
--     end if;
--     raise notice 'VERIFY 20261011_05 OK: luna low recusada, medium aceita, nada gravado';
--   end $$;
--   -- 3) o produto lê a rota (regerar o snapshot e resolver pelo Model Router):
--   --   python scripts/gerar_snapshot_de_modelos.py --banco
--   --   python -c "from app.factories import model_policy as M; r=M.resolver('leitura_de_apolice'); print(r.model, r.effort, r.classe_de_dado, r.reserva.model, r.reserva.effort)"
--   --   -- esperado: gpt-6-luna medium pii claude-sonnet-5-5 medium
--
-- ROLLBACK:  (escrito ANTES de aplicar; nenhuma FK aponta para llm_papeis — o código cai em ModeloNaoResolvido →
--            a leitura fica no regex com o estado "nao_fechou", falha fechada)
--   delete from public.llm_papeis where papel = 'leitura_de_apolice';
--   delete from supabase_migrations.schema_migrations where name = 'spec130b_papel_leitura_de_apolice';
--   -- e regerar o snapshot: python scripts/gerar_snapshot_de_modelos.py --banco
--
-- EXPAND-FIRST: sim — uma linha nova; nenhuma coluna, CHECK, gatilho ou rota existente muda.
-- DESTRUTIVA:   não.
-- =============================================================

-- -------------------------------------------------------------
-- A. o papel `leitura_de_apolice`
-- -------------------------------------------------------------
insert into public.llm_papeis (papel, descricao, provider, modelo_primario, esforco,
  provider_reserva, modelo_reserva, esforco_reserva, classe_de_dado, risco, versao, motivo,
  atualizado_por)
values
  ('leitura_de_apolice',
   'SPEC-130-B — lê a tabela de coberturas de documento de seguro (texto MASCARADO; páginas sem texto como imagem) quando o regex não fecha o prêmio; trecho literal conferido e juiz do prêmio — app/services/policy_document_evidence_service.py',
   'openai', 'gpt-6-luna', 'medium', 'anthropic', 'claude-sonnet-5-5', 'medium',
   'pii', 'alto', 1,
   'SPEC-130-B D-130B-09 nota 80 · BLOCO 0 item 4: Luna medium fechou Tokio COND (20/20 trechos) e Allianz EMPR (7/7) ao centavo; piso de produção medium; reserva de outro provedor',
   'migration 20261011_05')
on conflict (papel) do nothing;

-- -------------------------------------------------------------
-- B. asserção — o estado final é o desta migration, ou nada fica
-- -------------------------------------------------------------
do $$
declare n int;
begin
  select count(*) into n from public.llm_papeis
   where papel = 'leitura_de_apolice' and provider = 'openai' and modelo_primario = 'gpt-6-luna'
     and esforco = 'medium' and provider_reserva = 'anthropic' and modelo_reserva = 'claude-sonnet-5-5'
     and esforco_reserva = 'medium' and classe_de_dado = 'pii' and risco = 'alto';
  if n <> 1 then
    raise exception '20261011_05: estado final inesperado (% de 1 rota certa)', n;
  end if;
end $$;
