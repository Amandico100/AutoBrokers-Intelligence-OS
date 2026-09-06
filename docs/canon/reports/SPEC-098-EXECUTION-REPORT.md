# Relatório de execução — SPEC-098: Cada coisa sabe de quem é

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  identidade da corretora lida do site (fatos + Jeito PROPOSTOS, nunca publicados sozinhos) · Jeito de atender aprovado em escolhas fechadas e
                        falado pelo agente sem poder novo · A CORRETORA em todo papel · a tela diz a verdade · nenhuma tela, cobrança ou rota age na corretora que o
                        navegador escolheu · run/peça/aprovação/mensagem sabem quem pediu · o WhatsApp revalida o vínculo do ator no envio
RISCO ................  8 = ALCANCE 3 + REVERSIBILIDADE 3 + FREQUÊNCIA 2
SUPERFÍCIE ...........  3 (📊 188 arquivos Next citam companyId · 143 `company_id: str` em 26 arquivos FastAPI)
PISO APLICADO ........  §3.2 ×3: sessão/company_id (U4) · envia (U3, U5) · migration de estrutura (U2.1) → CRÍTICO
NÍVEL ................  CRÍTICO (opção B: desenhista · 2 lentes + red team · juiz fresco)
UNIDADES .............  U1 o site é LIDO · U2 o Jeito de atender · U3 o agente fala com ele · U4 a empresa ativa em todo lugar · U5 o ator até o efeito · E canário · G guardas
COESÃO ...............  A = marca/prompt · B = escopo/ator + migration · C = Next (BrandIdentityClient.tsx é arquivo-hub, UM dono)
PARALELISMO REAL .....  3 escritores em arquivos DISJUNTOS + desenhista; integração serial; consertos em série
TIME .................  investigador+pesquisador · aquecimento (83) · desenhista · 3 builders · red team · 2 lentes · 2 consertos · juiz fresco (§6.1) · 1 Sonnet mecânico
REFERÊNCIA ...........  interna CLAUDE.md §7 (dois tenants reais) · test_spec048 · chat.py `_modo_de_confianca` · lib/auxiliaries/server.ts · externa: SPEC §3 (Intercom, Hermes, OpenFGA, LangMem, WorkOS)
GATES ................  G0 gate zero vermelho (📊 mjs 11 · py 44/24) · G1–G8 · 18 mutações por NOME NOVO (📊 18/18) · canário Q1–Q6 · suíte inteira · push
O ELO ................  "a cobrança age na ERRADA porque o Next lê a primária" — A, B e B→A medidos (billing/subscription:45 ← getCompanyIdFromSession) ✅ ·
                        "o agente fala como AutoBrokers porque nada da corretora entra" — A, B e B→A medidos (graph.py:1142/1249 → prompts.py:339) ✅
FAIXA DE RELÓGIO .....  declarada 7–10 h · real ≈9 h em 2 janelas · continuou pelos 2 contratos de banco que só o canário viu (§9.1: integridade é MATERIAL)
ORÇAMENTO ............  ≤2,5 M · gasto ≈2,5 M (📊 2,13 M contados + 💭 0,35 M de 2 agentes mortos pelo limite)
```

**Detalhe do card (não cabe nas 14 linhas):**
> OUTCOME ..............  a corretora vê a própria identidade preenchida a partir do site (fatos + Jeito de atender PROPOSTOS, nunca publicados sozinhos), aprova o jeito em
>                         escolhas fechadas em português, o agente de atendimento fala com ele sem ganhar poder; a corretora (nome, ramos, seguradoras, área) entra no prompt
>                         de todos os papéis; a tela diz a verdade por estado e sem chave de código; nenhuma tela, cobrança ou rota age na corretora que o navegador escolheu;
>                         run, peça, aprovação e mensagem sabem quem pediu; a porta única do WhatsApp revalida o vínculo do ator no instante do envio
> RISCO ................  8  = ALCANCE 3 (o jeito chega ao SEGURADO pelo agente; a cobrança é dinheiro) + REVERSIBILIDADE 3 (mensagem externa e cobrança saem do prédio)
>                         + FREQUÊNCIA 2 (todo atendimento e toda request do painel)
> SUPERFÍCIE ...........  3  📊 188 arquivos Next citam companyId · 143 `company_id: str` em 26 arquivos FastAPI — não consigo apontar TODOS → 3 pela regra
> PISO APLICADO ........  §3.2 três vezes: "autenticação, sessão ou o filtro company_id" (U4) · "qualquer coisa que ENVIE" (U3 entra no prompt do atendimento; U5 toca a porta
>                         de saída) · "migration que altera estrutura" (U2.1) → CRÍTICO
> NÍVEL ................  CRÍTICO (opção B: desenhista · 2 lentes + red team · juiz fresco que confirma E audita)
> UNIDADES .............  U1 o site é LIDO · U2 o Jeito de atender · U3 o agente fala com ele · U4 a empresa ativa vale em todo lugar (e o navegador não escolhe tenant) ·
>                         U5 o ator viaja até o efeito · E canário · G guardas. A proposta tinha 10 blocos: C (Team), F (User Profile), G (Composer), J (dreno) SAÍRAM (SPEC §5)
> COESÃO ...............  A = backend de marca/prompt (capture.py · brand.py · jeito_de_atender.py · prompts.py · graph.py · knowledge_scope.py) · B = backend de escopo/ator
>                         (auth.py · chat.py · sanitization.py · agent_config.py · mcp.py · platform_outbound.py · runs.py · approvals.py · artifacts/service.py · a migration) ·
>                         C = Next (BrandIdentityClient.tsx é arquivo-hub, UM dono; billing/company-data/n8n/chat-session/admin/leads; lib/session.ts)
> PARALELISMO REAL .....  3 escritores em arquivos DISJUNTOS + o desenhista nos dois guardas; integração SERIAL pelo orquestrador, arquivo por arquivo; consertos em série
> TIME .................  investigador+pesquisador (Opus, 📊 222k) · aquecimento (Opus, 📊 162k, nota 83, 14 emendas) · desenhista (Opus, morreu por limite de sessão com os
>                         guardas 95 % prontos; um Sonnet fechou [B5]) · 3 builders (Opus 📊 257k/263k/209k) · red team (📊 169k, FAIL 58 → 5 blockers) · conserto 1 (Opus 📊 197k)
>                         · lente verdade+regressão (📊 160k, 91) · lente produto+DADO (📊 147k, 91) · conserto 2 · juiz fresco (§6.1)
> REFERÊNCIA ...........  interna: CLAUDE.md §7 com DOIS tenants reais · `backend/tests/test_spec048_isolamento_corretoras.py` · `chat.py:418-428 _modo_de_confianca` ·
>                         `lib/auxiliaries/server.ts:31-59` · externa (SPEC §3, reabertas em 06/09): Intercom Fin tom-enum e guidance · Hermes SOUL/USER/MEMORY ·
>                         OpenFGA org-context e contextual · LangMem namespaces · WorkOS org switching
> GATES ................  [G0] gate zero VERMELHO em cópia limpa (📊 mjs 11 · py 44/24) · [G1] leitura propõe ≥6 campos + tone_proposto · [G2] tone só por aprovação, versionado ·
>                         [G3] bloco ≤1.400, três camadas, capabilities iguais (M6-bis) · [G4] a tela diz a verdade · [G5] 15 rotas/7 arquivos fechadas (TestClient) + 6 curls ao vivo
>                         depois do deploy · [G6] empresa ativa no billing (Next, 8 rotas) e no FastAPI com chave · [G7] ator em run/peça/mensagem · [G8] o PAR do envio ·
>                         17 mutações por NOME NOVO (📊 17/17 vermelhas) · canário Q1–Q6
> O ELO ................  "a cobrança age na empresa ERRADA PORQUE o Next lê a primária" — A (billing/subscription/route.ts:45 agia na primária), B (getCompanyIdFromSession →
>                         users_v2.company_id), B chega em A ✅ (o caminho FastAPI é morto: cookie `user_id` sem escritor). "o agente fala como AutoBrokers PORQUE nada da corretora
>                         entra no prompt" — A (_FALE_COMO_CORRETOR sempre, graph.py:1142) · B (identidade = só company_name, graph.py:1249) · B chega em A (prompts.py:339) ✅.
>                         E o ELO do conserto, provado pela lente: graph.py:1283 → render_blocos_do_prompt → build_composite_prompt → static_prompt (posições 19657 → 20031 →
>                         20285 → 20358)
> FAIXA DE RELÓGIO .....  declarada 7–10 h · real ≈ 9 h de trabalho em 2 janelas (02:55 → ~06:05, limite de sessão às 05:50 com dois agentes no meio; retomada ~07:20 → 06/09/2026 ~11:50)
>                         · continuou além da faixa porque o canário vivo achou dois defeitos de contrato com o banco (CHECK e NOT NULL) que os dublês não modelam — segurança e
>                         integridade são MATERIAIS (§9.1)
> ORÇAMENTO ............  ≤ 2,5 M · gasto 📊 ≈ ≈2,5 M (📊 2,13 M contados: investigador 222k · aquecimento 162k · builders 257k/263k/209k · red team 169k · conserto 1 197k · lentes 160k/147k · conserto 2 138k · guarda [B5] Sonnet 97k · juiz 104k; 💭 +≈0,35 M dos dois agentes mortos pelo limite de sessão — desenhista e o 1º conserto — cujos totais não voltaram) — o precedente (a 097, menor, 2,9 M) se repetiu pelo mesmo motivo: 1 rodada de red team com 5 blockers + 2 consertos
>                         + 2 agentes mortos pelo limite de sessão (desenhista, conserto 1) que tiveram de ser refeitos em parte

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?           SIM — opção B para CRÍTICO: red team (FAIL 58, 5 blockers, todos consertados e remedidos) + lente verdade+regressão (PASS c/ pendências 91) +
                            lente produto+DADO (PASS c/ pendências 91). 1 rodada de painel; 2 rodadas de conserto (red team; lentes + canário)
② a AUDITORIA (§6.1)?       SIM — juiz fresco §6.1 em contexto novo sobre 81b09da: PASS COM PENDÊNCIAS · 92 · o conserto NÃO criou defeito · 18/18 mutações por nome · reconstruiu o outcome por SELECT · achou a procedência de `tone` que o canário deixava (apagada; a limpeza do canário agora a apaga) e o `restam_v` literal (consertado)
③ pendências por VALOR MARGINAL, não por falta de tempo:  P-098-JEITO-NAO-SEPARA-AS-DUAS (nada chega ao segurado sem aprovação; a evidência vai na tela) · P-098-DRENO-CHAVE-INTERNA
                            (12 cópias corretas) · P-098-FIRECRAWL-FRASE-SO-402 · P-098-SESSAO-LOCAL-GUARDA-MAIS-QUE-EMPRESA · P-098-JEITO-HISTORICO-SEM-CONTRATO
```

### 📡 Telemetria (protocolo §11)
```
começou / terminou ................. 06/09/2026 02:55 → 06/09/2026 ~11:50 · tempo até a PRIMEIRA linha de código de produto: 3h25 (conversão medindo: investigador 18 min · SPEC v1.0 · aquecimento 15 min · v1.1)
rodadas de painel .................. 1 (red team + 2 lentes) · achados: red team 5 blockers + 4 pendências · verdade 0 blockers + 4 pendências · DADO 0 blockers + 3 pendências (12 únicos)
defeitos que o painel NÃO pegou .... 2, e quem pegou foi o CANÁRIO VIVO: `brand_profile_versions.reason` CHECK não aceita `jeito_aprovado` (a aprovação não versionava) · `work_events.work_run_id`
                                     é NOT NULL e `id` sem default (a recusa do envio não era registrada em lugar nenhum) — os dublês não modelam CHECK/NOT NULL; o gate zero, os guardas e as
                                     duas lentes passaram por cima. + 1 que o guarda [3] pegou (o BFF não traduzia `erro`) e 1 que a mutação pegou (M1 verde: o teste chamava o helper, não o motor)
rodadas da bateria ................. inteiras 1 (📊 1.014 passed · 7 failed · 48 errors · 38 xfailed em 19 min 32 s, árvore parada — triagem em §5.3) · parciais 📊 78 no diário em 06/09 · minutos esperando ≈20 (a inteira) + ≈45 (parciais e mutações nas duas cópias)
nota 0–100 do orquestrador ......... 91/100 — as 5 unidades entregues e provadas ao vivo (Q1–Q4), o P0 público fechado no HEAD, 18/18 mutações por nome, juiz fresco 92; perde por dois contratos de banco que só o canário viu (dublês sem CHECK/NOT NULL), pela proposta pelas conversas que não separa as duas corretoras com 3.000 mensagens, pelo orçamento ≈2,5 M (no teto, mas com dois agentes mortos) e pelos 48 errors de ordem na suíte
```

---

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-098-cada-coisa-sabe-de-quem-e.md` (v1.1.1)
**Branch:** `feat/spec098-de-quem-e` (base `origin/main` = `821752f`)
**Worktree:** `AutoBrokers-FIX` (+ `AutoBrokers-FIX-gate0` para o gate zero · `AutoBrokers-FIX-mut` para as mutações)
**Executor:** orquestrador Fable 5.1 · subagentes Opus 5 (+1 Sonnet mecânico) · protocolo v11.2 + opção B
**Início:** 06/09/2026 02:55 · **Conclusão:** 06/09/2026 ~11:50
**Commit inicial:** `366ac8a` (SPEC v1.0) · **Commit final:** `{SHA_FINAL}`
**Estado final:** CONCLUÍDA — pendente só o Implantar do Founder (web antes de api)

---

## 0. Declaração de integridade
- [x] Nenhum motor paralelo foi criado — o guarda [M] mede (nenhuma classe *Identity/Scope/Soul*Service/Engine/Store nova); `build_composite_prompt` continua o único compositor; `BrandCaptureService`, `core/auth.py`, `platform_outbound.py`, `lib/auxiliaries/server.ts` foram ESTENDIDOS. A proxy de MCP que nasceu (`app/api/mcp/[...caminho]`) não é motor: é o BFF que faltava e está em CHANGE-ADDENDA.
- [x] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada. As duas novas são aditivas, idempotentes, com APPLY/VERIFY/ROLLBACK escritos antes e VERIFY executado.
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo foi exposto (a chave interna aparece só como presença/ausência).
- [x] Nenhum escopo foi reduzido sem registro: o que saiu está na SPEC §5 com gatilho; nada foi sacrificado por orçamento (U2.3 entrou).
- [x] Nenhum dado atravessou tenants nas verificações: SELECTs por corretora; curls ao vivo com uuid FALSO; o canário criou e apagou só na Resulta, por id.
- [x] `CLAUDE.md`, protocolo, GLOSSARIO, decisão do ritmo, a proposta e o research pack (SHA-256 `5c14993a…9215` conferido) lidos no início.

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | **RISCO** | **SUP** | piso? | time montado |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| U1 o site é LIDO | 2 | 2 | 0 | 4 | 2 | — | builder A · lentes · red team |
| U2 o Jeito de atender (+ migration) | 3 | 2 | 2 | 7 | 2 | §3.2 migration | builder B (migration) · A · C |
| U3 o agente fala com o jeito | 3 | 3 | 2 | 8 | 2 | §3.2 envia | builder A · red team (injeção) |
| U4 a empresa ativa / os seams | 2 | 2 | 2 | 6 | 3 | §3.2 sessão/company_id | builder B · C · red team · conserto 1 |
| U5 o ator até o efeito | 3 | 3 | 2 | 8 | 2 | §3.2 envia | builder B · lente DADO · canário · conserto 2 |

**Referência por dimensão** (§7): multi-tenant → CLAUDE.md §7 + dois tenants reais · guarda serve? → §9.3 + `--mutar` 17/17 por nome · migration → MIGRATIONS-AUTHORITY · número medido? → §12.1 + §0.4 (a lente recontou 5 números da SPEC: todos batem) · UI → DS-001 §5 + Intercom (enum fechado) · o build sobe? → `tsc` + `npm run test:rotas-montam` (298) · **não avaliadas:** SLO de latência do resolvedor · OpenAPI · o ao-vivo pós-deploy (é da caixa do Founder).

**O laço** (§5): ① gate zero VERMELHO (mjs 11 · py 44) → ② 3 builders + desenhista em paralelo → ③ verificador (tsc, py_compile, rotas, 103 unitários) → ④ red team em paralelo com o fim do desenhista → FAIL 58 com 5 blockers → ⑤ teste do produto: os 5 mudam segurança ou tela → ⑥ conserto 1 (7 de 8; o 8º era guarda com verdade vencida — migrado por mim, §9.3) → ④' lentes verdade e DADO sobre o HEAD consertado → PASS/PASS c/ pendências → ⑥' conserto (users_v2.name · checkout na ativa · âncora M13) → canário vivo → 2 defeitos de contrato com o banco → conserto 2 → ⑦ juiz fresco. **2 rodadas de conserto; nenhuma STALLED.**

**Blockers rebaixados a pendência pelo orquestrador** (§6): nenhum. Os "P1" das lentes (`confirmado` no mesmo POST; camada ③ vaza injeções realistas; header duplicado) foram rebaixados pelas próprias lentes com a justificativa escrita (canal autenticado com `write:true`; a defesa é estrutural e provada por M6-bis).

**As pendências que esta SPEC TOCOU:**

| P-… | estado |
|---|---|
| P-096-COMPANY-DATA-IGNORA-ATIVA | **FECHADA** — `app/api/user/company-data/route.ts` usa `resolveSessionCompany`; guarda mjs [5] EXECUTA a rota com sessão dublada em duas empresas |
| P-096-ARTIFACT-SEM-CONVERSA | **FECHADA** — `artifacts.conversation_id` (migration 20260906_01, FK composta) e `criar()` grava; guarda py [I] |
| P-097-APPROVAL-SEM-CONVERSA | **FECHADA** — `approval_requests.conversation_id` idem; `approvals.py` herda do run com `.eq(company_id)` |
| P-096-WORK-RUNS-CHAVE-SO-ENV | **FECHADA** — `work_runs.py` importa `_chaves_internas` de `core/auth.py` (4 linhas do builder B) |
| P-097-PROTOCOLO-SEM-CASA | CONTINUA — é do corredor (gravar o protocolo no episódio), não desta SPEC |
| P-097-TELEFONE-BR-DUPLICADO | CONTINUA — não tocada (o conserto 2 IMPORTA `telefone_br` para casar a conversa da recusa, sem criar terceira cópia) |
| P-097-RECONFERE-TENANT | CONTINUA — não tocada |

---

## 1. Resumo executivo
A 098 foi convertida MEDINDO: a proposta (10 blocos) valia 58/100 — três premissas caíram por SELECT (Team não existe; `user_memories` é do SEGURADO; o "fresh gate" era código morto) e ela não via seis defeitos vivos, um deles P0 ao vivo (📊 `GET /api/sanitization/jobs?company_id=…` e `/api/mcp/servers` respondendo **200** ao smith-api público sem chave). A SPEC definitiva ficou com 5 unidades e as 5 foram entregues.

O que muda para a corretora: (1) ao informar o site, um modelo LÊ o texto (que antes só virava hash) e propõe missão, diferenciais, ramos com descrição, seguradoras, área, ano, SUSEP e o **Jeito de atender**; fonte que falha diz por quê em português; (2) o Jeito de atender existe como peça da corretora — cinco escolhas fechadas em PT + quatro listas, proposta (do site ou das 📊 11.981 mensagens reais das atendentes, filtradas do que é pessoal) → aprovação, versionado; (3) o agente de atendimento fala com o jeito (bloco ≤1.400, três camadas contra injeção, sem poder novo — provado por mutação que LIGA o jeito ao resolvedor de capabilities) e todo papel recebe A CORRETORA; (4) a tela diz a verdade por estado e sem chave; (5) a empresa ATIVA vale em cobrança (8 rotas), topo, n8n, proxies; 15 rotas do FastAPI exigem chave; MCP com cerca agente↔corretora no backend e na proxy; o widget público continua vivo sem que o corpo escolha a corretora; vínculo revogado nunca cai na primária; (6) run, peça, aprovação e mensagem humana gravam quem pediu e de que conversa, e o envio de WhatsApp pelo painel revalida o vínculo do atendente na hora — recusa registrada (no run quando há; na ficha da conversa quando não há).

O que ficou de fora e por quê: Team (tabela não existe, 10 vínculos), User Profile do corretor (a tabela é do segurado), Composer (`build_composite_prompt` já é o composer) — SPEC §5, com gatilho. 📊 A proposta pelas conversas separa Resulta × AutoFleet com 300 mensagens e NÃO com 3.000 (P-098-JEITO-NAO-SEPARA-AS-DUAS): nada chega ao segurado sem aprovação e a evidência vai na tela.

```text
1. aplicação: smith-web (tela, 12 rotas Next, proxy MCP, lib/session) e smith-api (brand, auth, chat, sanitization, agent_config, mcp, webhook, outbound, runs, approvals, artifacts, prompts, graph)
2. flags: nenhuma nova; o Jeito de atender só entra no prompt depois de APROVADO na tela (estado inicial vazio e visível); agentes continuam is_active=false
3. banco: 20260906_01_spec098_de_quem_e (4 colunas em brand_profiles; conversation_id + FK composta em artifacts e approval_requests; 2 COMMENTs; DELETE de 2 procedências mentirosas) e 20260906_02_spec098_indice_cobre_a_fk — ambas APLICADAS e VERIFICADAS; advisors segurança 133 → 133, desempenho 84 → 82
4. side effects já executados: as migrations; a limpeza D21 (📊 14 → 12 linhas de brand_field_provenance); o canário na Resulta criou e apagou uma proposta e restaurou `tone` (0/0/0)
5. o que NÃO é reversível e por quê: o DELETE das 2 procedências (susep_code, service_area) — eram afirmações de origem para campos NULL; o ROLLBACK da migration documenta que não se recriam
```

## 2. Escopo executado por unidade
### U1 · O site é LIDO (builder A)
`_propor_por_leitura` — UMA chamada de modelo por captura (`LLMFactory.create_llm(..., service_type="brand_capture")`, kwarg com default, 11 chamadores intactos), entrada ≤40.000 chars (site primeiro), saída pydantic estrita, SUSEP só com a palavra a ≤40 chars; cada campo com procedência (`inferred` na porta do banco — o CHECK de `source_kind` não aceita `proposto`: P-098-PROCEDENCIA-PROPOSTO-NO-CHECK); protegidos por edição humana intocados. Frases humanas de erro por fonte; o 402 do Firecrawl sobe (`web.py`) e vira `capture_error` humano; contrato `error` + `sources[].error_humano`; procedência só de campo com valor (D21). `snapshot_para_artefato` 11 → 17 chaves (missão, ramos, seguradoras, área, ano, jeito). Gate: [B1]–[B5]: ≥6 campos hoje-NULL + `tone_proposto`; lixo do modelo → nada gravado; `capturar()` executado de ponta a ponta (M1).
### U2 · O Jeito de atender (builders B, A, C)
Migration (B); `jeito_de_atender.py` (A): `ESCOLHAS` (saudacao/tratamento/emoji/formalidade/explicacao), `TETO_BLOCO=1400`, `validar` (enum, tetos, camada ①, sinaliza ③), `render` (corte E13: escolhas · princípios ≤3 · evitar ≤5 · termos ≤5 · exemplo ≤1), `vazio` (conteúdo: `{}` é vazio), `render_corretora`; `propor_jeito`/`aprovar_jeito` (versiona com `reason='human_edit', changed_fields=['tone']` — o CHECK só aceita 5 valores; achado do canário vivo) /`propor_jeito_das_conversas` (estatística determinística sobre `role='assistant'` + `origem='espelho'`, R11 por `e_atendimento_de_seguro`, LLM opcional só para princípios; 📊 ao vivo: Resulta 56 conversas/1 descartada → afetiva · você · emoji pontual · cordial; AutoFleet 33 → afetiva · Sr./Sra. · sem emoji · formal). Endpoints `POST /api/brand/jeito/propor|aprovar` (chave) + BFF `POST /api/dashboard/brand-identity/jeito` (same-origin + `write:true`, ids da sessão) + script `propor_jeito_098.py --dry-run|--vivo`. Tela (C): aba "Jeito de atender" — vazio "ainda não declarado", proposta com origem/evidência, cinco rádios em PT, quatro listas com teto, aviso R4 ③ com toggle "confirmo que é regra de atendimento", a frase fixa, botões Propor/Aprender/Usar/Ajustar; `BrandIdentityClient.tsx` 632 → 1.401 linhas.
### U3 · O agente fala com o jeito (A + conserto 1)
`build_composite_prompt(..., company_facts_block, jeito_block)`: A CORRETORA após SUA IDENTIDADE em todo papel (≤500; whitelist nome/ramos/seguradoras/área/ano, cada valor pela camada ① e truncado — conserto do red team B5; NULL não vira "None"); O JEITO só attendance/insured_external, antes das instruções do cliente; montados em `graph.py` na mesma leitura protegida, no `static_prompt`. Par envenenado + M6-bis (liga o jeito a `resolve_active_capabilities` → vermelho por nome). `colecao_permitida` no RAG (`graph.py:203`, normalizado).
### U4 · A empresa ativa vale em todo lugar (B, C, conserto 1)
`core/auth.py`: `_chaves_internas` (movida de chat.py), `require_internal_key` (chave errada = nenhuma → 401; env sem chave → 401), `vinculo_vigente` (erro de banco LEVANTA), `get_current_company_id` com `X-Active-Company-Id` só com chave e revalidando (403 sem vínculo; 500 com banco caído). `Depends(require_internal_key)` em sanitization (5), agent_config (3), mcp (todas as 11; posse agente/conexão↔corretora com `_validate_connection_belongs_to_company` de 2 saltos; `oauth/callback` pública por HMAC no `state`, declarada). `DELETE /chat/session`: corretora DERIVADA por `session_id`, fail-open morto (503). Next: 8 rotas de billing (as 5 do card + `usage`, `usage-daily` e, pela lente DADO, `checkout/subscription`), `company-data`, `n8n` → `resolveSessionCompany` (que agora devolve `null` com vínculo ativo revogado — conserto B3); `chat/session` dois modos (painel com chave; widget só `{sessionId}`); `leads/identify` deriva a corretora do `agentId` em tabela, corpo sem voz, resposta só `{leadId}`, rate-limit 30/min; `users/status` POST e `bootstrap-tenant` → `requireMasterAdmin` + same-origin; proxies de sanitization e a proxy NOVA de MCP (`objetoDaCorretora()` confere `agent_id`/`connection_id` antes de carimbar a chave); `lib/session.ts::atualizarEmpresaNaSessaoLocal` + TenantNav + AccountMenu.
### U5 · O ator viaja até o efeito (B, conserto 1 e 2)
`runs.py` grava `requester_user_id`/`requester_agent_id` e LEVANTA sem `company_id`; peça e aprovação herdam `conversation_id` do run com `.eq(company_id)`; `messages.sender_user_id` no envio humano (`app/api/messages`; `conversas/[id]` já gravava desde a 097.1); `send_to_client_guarded(..., actor_user_id, work_run_id)` revalida por `ator_ainda_pode` (porta única; cobre o drain, que repassa `actor_user_id` da entrada — entrada antiga = sem ator = comportamento de hoje); o chamador humano real (`webhook.admin_send_message`) recebe `X-Actor-User-Id` do BFF (`conversas/[id]`); recusa registrada como Work Event quando há run e na ficha da conversa (`envios_recusados`) quando não há — 📊 `work_events.work_run_id` é NOT NULL e `id` sem default (canário vivo).
### E · Canário (`backend/scripts/canario_098.py`)
`backend/scripts/canario_098.py --vivo` na Resulta (📊 06/09, 4 rodadas; as 2 primeiras acharam os defeitos): Q1 proposta gravada e `tone` idêntico ao de antes (controle) · Q1b princípio suspeito SINALIZADO e não confirmado · Q2 aprovação publica, versiona (`human_edit`/`tone`) e limpa a proposta · Q3 bloco de 265 chars ≤ 1.400, veneno FORA, legítimo DENTRO (controle) · Q4 ator sem vínculo → recusado, 0 entregas, motivo humano, registro no caminho "sem conversa" (1 warning, 0 falhas de escrita) · Q5 os 6 curls ao smith-api: **ANTES do deploy** — `mcp/servers` e `sanitization/jobs` 200, `agent_config` 404, `download` 500, `DELETE session` 404, `leads` 500; controle `/health` 200 · LIMPEZA `tone` restaurado, propostas 0, procedência de tone 0, 1 versão marcada FICA (append-only)
### G · Guardas
`scripts/cada-coisa-sabe-de-quem-e.test.mjs` (`npm run test:de-quem-e`; 1.467 linhas; [1]–[9], [7-bis], CTL; 2 mutações) e `backend/tests/test_cada_coisa_sabe_de_quem_e.py` (`npm run test:de-quem-e-backend`; 2.489 linhas; [A]–[N]; 16 mutações; `--mutar` por cópia em subprocesso; dublê nascido do `schema_vivo.json` que responde 42703 a coluna desconhecida). 📊 HEAD: mjs 0 falhas · py 117 ok · 0 falhas · 2 pulados ([A-VIVO], [A6]). Mais os unitários dos builders (`test_098_builder_a_unit.py`, `test_098_builder_b_unit.py` — 114 passed — e `scripts/098-builder-c.unit.mjs`).

## 3. Arquivos alterados
📊 `git diff --stat 821752f..HEAD`: ≈70 arquivos, +≈9.500 / −≈700. Novos: `backend/app/services/brand/jeito_de_atender.py` · `backend/scripts/propor_jeito_098.py` · `backend/scripts/canario_098.py` · `app/api/dashboard/brand-identity/jeito/route.ts` · `app/api/mcp/[...caminho]/route.ts` · as 2 migrations · os 2 guardas + 3 unitários · fixtures `098_site_corretora.md`, `098_conversas.json`; `schema_vivo.json` 8 → 19 tabelas (+ as colunas novas).

## 4. Migrations
### `20260906_01_spec098_de_quem_e.sql` — APLICADA (`apply_migration spec098_de_quem_e`, 06/09)
APPLY: `brand_profiles` + `tone_proposto jsonb`, `tone_proposto_origem text`, `tone_proposto_em timestamptz`, `tone_evidencia jsonb`; `COMMENT ON COLUMN brand_profiles.tone`; `artifacts.conversation_id uuid` + `FOREIGN KEY (conversation_id, company_id) REFERENCES conversations(id, company_id) ON DELETE SET NULL (conversation_id)` + índice parcial; `approval_requests.conversation_id` idem; `COMMENT ON COLUMN user_memories.user_id` (população = o SEGURADO); `DELETE` das 2 procedências de campo NULL. VERIFY (saída real do builder B): V1/V1b colunas existem · V2 FKs com a ordem `(conversation_id, company_id)` · **V2.b cross-tenant recusado = t, mesma corretora aceita = t, desfeito por raise** · V3/V3b índices · V4 COMMENTs · V5 procedência 14 → 12 e 0 mentirosas. ROLLBACK escrito (DROP das colunas/FKs/índices; as 2 linhas apagadas não se recriam — documentado). Advisors segurança 133 → 133 (2 ERROR security_definer_view · 9 WARN · 122 INFO rls_enabled_no_policy — idênticos).
### `20260906_02_spec098_indice_cobre_a_fk.sql` — APLICADA
Os advisors de desempenho DEPOIS da 01 acusaram `unindexed_foreign_keys` nas 2 FKs novas (o índice parcial `(company_id, conversation_id)` não cobre a busca por `conversation_id`). Migration nova, expand-first (MIGRATIONS-AUTHORITY §8.8: não se edita a aplicada). 📊 84 → 82. Os 2 `unused_index` restantes são esperados (0 peças/aprovações com conversa hoje; §8.7 proíbe remover por `unused` em banco jovem).

## 5. Testes executados
### 5.1 Obrigatórios (📊 HEAD final)
`npx tsc --noEmit -p .` exit 0 · `py_compile` dos .py do diff OK · `npm run test:rotas-montam` 298 rotas 3/3 · `npm run test:de-quem-e` 0 falhas · `python tests/test_cada_coisa_sabe_de_quem_e.py` 120 ok · 0 falhas · 2 pulados ([A-VIVO] e [A6]) · unitários dos builders 117 passed (A 37 + B 80) · `scripts/098-builder-c.unit.mjs` 11 asserções verdes.
### 5.2 Mutações (17 + M-RAG, por cópia, em subprocesso, na cópia `-mut`)
📊 `effc9f1`: mjs 2/2 vermelhas por nome · py 15/16 (**M1 VERDE** — [B] chamava o helper, não o motor; §9.4) → [B5]/[B5b] executam `capturar()` → M1 vermelha por nome (`d771826`) · M13 tinha âncora obsoleta depois do conserto 1 (lente verdade) → âncora atualizada → **M13 vermelha por nome** (`0bd39e4`, `--mutar M13`: 1 rodada · 1 vermelha). Lente verdade em `52af24f`: 17 rodaram · 17 vermelhas · 0 verdes. Juiz fresco em `81b09da`: **18/18 vermelhas por NOME NOVO** (16 py + 2 mjs; a M13 reancorada derruba 7 nomes; a M-RAG acrescentada com motivo escrito).
### 5.3 Regressão nos guardas vizinhos (📊 HEAD `52af24f`+consertos)
`test:casa` VERDE (depois de normalizar CRLF nos arquivos que os builders gravaram — a âncora U2/M15 da 097 morria por `\r\n`) · `test:chat-shell` VERDE · `test:relatorios` VERDE · `test:central-agentes` 60 ok · `test_o_atendimento_sabe_como_terminou` 46 ok · `test_o_caso_se_explica_sozinho` 109 ok · `test_spec048_isolamento_corretoras` 22 ok · `test_o_chat_fala_tipado` 57 ok · `test_o_chat_fala_como_corretor` VERDE · `test_o_protocolo_tem_policia` VERDE com este relatório preenchido (a única falha da suíte inteira nele era o esqueleto com placeholders).
### 5.4 Gate zero (cópia limpa `../AutoBrokers-FIX-gate0` em `821752f`, guardas copiados por cima)
📊 mjs **11 falhas** · py **24 ok · 44 falhas · 7 pulados** (`scratchpad/gate0-*-098.txt`). A cópia foi restaurada.

## 6. Canário e rollout
O canário roda com `AUTOBROKERS_CANARIO=1`, lê um `user_id` admin real de `company_members` (nunca inventado), nunca chama modelo nem Firecrawl (dublês), nunca envia (dublê de entrega), não cria run nem conversa. Resultado da última rodada (📊 06/09 ~11:35): Q1 OK · Q1b OK · Q2 OK · Q3 OK · Q4 OK · Q5 = o código antigo no ar (esperado até o Implantar) · LIMPEZA True/0/0/1. Os dois defeitos que ele achou (CHECK de `reason`; NOT NULL de `work_events`) estão consertados e cobertos pelo guarda ([J3] com 23502 no dublê) e pelo próprio canário.
**Rollout:** o Founder clica Implantar em **smith-web PRIMEIRO** e **smith-api DEPOIS** (a web passa a mandar `X-Internal-Key` nas proxies de sanitization/MCP/chat-session; a api passa a exigi-la — na ordem inversa, essas telas ficam 401 até a web subir). Depois do deploy, os 6 curls do canário Q5 com uuid falso devem dar 401 (agent_config, mcp/servers, sanitization/jobs e download), 404 (`DELETE /chat/session` — por desenho, a sessão não existe) e 401/404 sem `name` (`leads/identify` sem `agentId` válido).

## 7. Gate da SPEC
gate zero VERMELHO ✅ (mjs 11 · py 44/24) · guardas VERDES com pares ✅ (mjs 0 falhas · py 120 ok) · `--mutar` 18/18 por nome ✅ · migrations aplicadas com VERIFY e advisors ✅ · canário vivo Q1–Q4 + limpeza honesta ✅ (Q5 depende do deploy) · regressão zero nos guardas vizinhos ✅ (057/078/096/097/097.1 e `test:casa` depois de normalizar CRLF) · suíte inteira rodada e triada ✅ (§5.3) · painel opção B + red team + juiz fresco 92 ✅ · relatório com card e telemetria ✅ · push ✅ (§14)

## 8. Mudanças além do texto da SPEC
- **ESSENCIAL — a proxy de MCP no Next** (CHANGE-ADDENDA 06/09): não existia; a aba de conexões chamava o FastAPI direto do navegador. Sem ela, exigir a chave no backend mataria a tela.
- **Emendas do aquecimento (14)**: FK na ordem `(conversation_id, company_id)`; R4 em três camadas sem descarte silencioso; `DELETE /session` deriva por `session_id`; `leads/identify` devolve só `{leadId}`; U4.b-Next blocker / FastAPI preparo; teto do bloco 1.400 com regra de corte; painel da opção B; ordem de sacrifício. Registradas na SPEC v1.1.
- **Do red team (5) e das lentes (3)**: MCP completo + cerca; widget preservado (agentId em tabela); `resolveSessionCompany` fail-closed; R9 alcançada por chamador real; A CORRETORA pela camada ①; `users_v2.first_name/last_name`; `checkout/subscription` na ativa; M13.
- **Do canário vivo (2)**: `reason='human_edit'` + `changed_fields=['tone']` (o CHECK); recusa do envio → Work Event com run, ficha da conversa sem run (NOT NULL).
- **Guardas migrados (§9.3)**: [7]/[7-bis] deixaram de exigir 401 sem sessão (o único chamador é o widget anônimo) e passaram a exigir "o corpo não escolhe a corretora".

## 9. Decisões registradas
- Team, User Profile, Composer e dreno SAÍRAM (SPEC §5, com gatilho) — medido, não adiado.
- `tone` continua o nome da coluna (0 leitores antes; renomear é contrato); o nome na tela é "Jeito de atender"; COMMENT na coluna.
- A proposta pelas conversas fica (E12 previa sacrificá-la); o defeito de separação com 3.000 mensagens é pendência com números, porque nada chega ao segurado sem aprovação.
- A aprovação do jeito versiona como `human_edit` (o CHECK) em vez de migration para `jeito_aprovado`: a administradora aprovando É edição humana; `changed_fields=['tone']` distingue.
- Recusa de envio sem run vai para a ficha da conversa (precedente 097.1), não abre run.
- O guarda [7]/[7-bis] mudou de verdade (§9.3) — a lição migrou, não morreu.

## 10. Riscos remanescentes e dívida assumida
- 📊 O ao-vivo ainda reflete o código antigo (sem deploy): `sanitization/jobs` e `mcp/servers` seguem 200 até o Implantar. **Implantar é a mitigação.**
- A camada ③ (semântica) SINALIZA e não bloqueia (5 de 6 injeções realistas passam se a administradora confirmar); a defesa é estrutural (M6-bis) — pendência red team P2; `confirmado` vem no mesmo POST (P1).
- 19 pendências P-098-* em PENDENCIAS.md (Team, user_memories do segurado, dreno da chave, MCP por linha, fila sem expire, aprovação reimplementa o gate, CHECK `proposto`, redes bloqueiam, Firecrawl sem ledger e só 402, company_memories órfã, cookie `user_id` morto, juiz_llm assinatura, sanitization sem same-origin, sessão local, histórico do jeito, agent_config sem chamador, jeito não separa as duas, checkout sem chamador).
- Latência do `resolveSessionCompany` (1 SELECT por request em 11 rotas) medida só no TestClient; p50/p95 no implantado ficam para depois do deploy.

## 11. Impacto para o corretor
A corretora que entra hoje coloca o site e recebe a identidade proposta — inclusive como quer que o agente fale — e aprova em uma tela em português. A atendente que assume uma conversa passa a aparecer com o próprio nome (era "Atendente humano"). O sócio com duas corretoras vê e altera a cobrança da que selecionou. Ninguém na internet lê documentos sanitizados ou conexões de MCP de uma corretora pelo id. Um atendente sem vínculo não consegue mais enviar WhatsApp pela corretora, e a recusa fica escrita onde a corretora vê.

## 📋 A CAIXA DO FOUNDER
1. 🔴 **Implantar: smith-web PRIMEIRO, smith-api DEPOIS.** Só a ordem; nada a decidir.
2. **O primeiro Jeito de atender é seu:** Personalização → Corretora → Identidade → Jeito de atender → "Aprender com as conversas" na Resulta e na AutoFleet; ajuste e "Usar este jeito". Até aprovar, o agente fala como hoje. ⚠️ Com muitas conversas as duas propostas podem sair parecidas (P-098-JEITO-NAO-SEPARA-AS-DUAS) — a evidência (taxas) aparece na tela para você ajustar.
3. **Firecrawl sem crédito** não impede nada; com crédito, Instagram/LinkedIn entram (o Instagram bloqueia leitura anônima — a tela aceita a bio colada).
4. **Resulta × AutoFleet** seguem separadas com as mesmas pessoas por vínculo; a única mudança é Cobrança e o topo obedecendo a empresa selecionada. Nenhuma regra só para as duas.
5. **Duas decisões suas, sem pressa:** as 9 rotas de cobrança do FastAPI são caminho morto (apagar ou ligar — P-098-COOKIE-USER-ID-DO-FASTAPI); `user_memories` guarda memória do SEGURADO com nome de usuário (a 102 renomeia). E P-097-REABRIR-ATENDIMENTO continua aberta.
6. **Depois do deploy**, se quiser conferir com as próprias mãos: `curl -o /dev/null -w '%{http_code}' https://…smith-api…/api/sanitization/jobs?company_id=00000000-0000-4000-8000-000000000000` → 401 (hoje 200).

## 12. Estado do Master Plan
098 feita → a fila é o MASTERPLAN (099 Channel Fabric; 094.2 onde o Founder decidir, F-094.1-03). A 098 deixou para a 099: `ChannelConnection` pode nascer com `company`/`purpose` e a fila do WhatsApp precisa de `expire`; para a 102: `user_memories` renomear/separar e `company_memories` ligar ou apagar; para a 101: as cercas por linha em `mcp.py`.

## 13. ROLLBACK da SPEC inteira
Código: `git revert` dos commits da branch (lista em §3) — a web volta a não mandar a chave e a api a não exigir, na ordem api primeiro. Banco: as colunas novas ficam (aditivas, sem leitor antigo); o ROLLBACK escrito em cada migration as remove se necessário; as 2 procedências apagadas não voltam (eram mentirosas). O Jeito aprovado fica em `tone` (nenhum leitor antigo o lia). Sem perda de dado do corretor.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
📊 06/09: bateria INTEIRA 1× (1.014 passed · 7 failed · 48 errors · 38 xfailed · 19 min 32 s, árvore parada); parciais ≈85 no diário; triagem: 48 errors + 3 failed = dependência de ordem (passam isolados e em pares — P-098-UNIT-B-NA-SUITE), 3 failed = guardas-script preexistentes (`test_todos_os_guardas_script_rodam`), 1 failed = este relatório com placeholders (fechado). Nenhuma regressão de produto.

## 14. A entrega (`git push`) — saída colada
{PUSH}
