# Relatório de execução — SPEC-EXTRA-001.6: A cobrança prova que funciona

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  a rotina de cobrança roda em `equipe`: a atendente recebe 1 mensagem INTEIRA por segurado com N
                        boletos, nunca a mesma parcela duas vezes, nunca o mesmo segurado 2× em 7 dias; cada portal diz em
                        português por que não entrou; credencial recusada é classe própria, chega ao dono e o robô para de
                        bater na porta trancada
RISCO ................  6 = ALCANCE 2 (em `equipe` quem recebe é a atendente) + REVERSIBILIDADE 3 (mensagem sai do prédio)
                        + FREQUÊNCIA 1 (toda semana)
SUPERFÍCIE ...........  2 — vários comportamentos em lugares LISTADOS: billing_collection · platform_outbound ·
                        whatsapp_service · portal_worker/worker · 6 journeys · app/api/portal · PainelDeRotinas ·
                        conectores/portais · central-agentes
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" + migration que altera ESTRUTURA (coluna + índice + função) → CRÍTICO
NÍVEL ................  CRÍTICO · laço curto (D-PILOTO-20 / diagnóstico §13.7): builders Opus · 1 juiz fresco Opus com
                        canário vivo + 1 lente do DADO · sem aquecimento, sem painel de 3, sem red team
UNIDADES .............  B0 medir · P0 a mensagem chega inteira (implantável no 1º dia) · B1 ninguém é cobrado 2× ·
                        B2 a sessão morre e alguém sabe · B3 o portal é vigiado antes da rotina · B4 a prova tem leitor ·
                        B5 canário vivo + docs
COESÃO ...............  P0+B1 = billing_collection (hub, UM dono por vez) · B2+B3 = portal_worker + app/api/portal ·
                        B4 = worker (texto da tela) + billing_collection (PII) — serial depois de B1
PARALELISMO REAL .....  B1 (backend/app/services) ∥ B2+B3 (backend/portal_worker) — arquivos disjuntos; ≤ 3 agentes
TIME .................  orquestrador Fable (mede, monta, registra) · builders Opus 5 esforço máximo · juiz fresco Opus 5 ·
                        lente do dado Opus 5
REFERÊNCIA ...........  interna: `tests/test_a_cobranca_esta_como_estava.py` (CONTROLE, a migrar §12.3) ·
                        `tests/test_a_cobranca_chega_a_quem_deve.py` (162 asserções da EXTRA-001) ·
                        `supabase/migrations/20260907_01_*.sql` · corpus `tests/corpus/telas_reais_de_portal/`
                        externa: proposta §13 (Playwright auth/locators · Microsoft Circuit Breaker · AWS jitter ·
                        PostgreSQL partial indexes) — reaproveitadas, não reabertas (D-PILOTO-14: pesquisa só em padrão novo)
GATES ................  G1–G12 com M1–M12 vermelhas · canário Q1–Q6 herdado + Q7–Q10 · suíte inteira · `git push` com saída
O ELO ................  "a atendente recebe 5 mensagens PORQUE o envio não pede bloco único" — A medido (📊 13/09, motor:
                        texto 332 ch → 2 balões · nota 321 → 2 · teste 520 → 3) · B medido (`billing_collection.py:1153` e
                        `platform_outbound.py:1478` chamam `send_message` sem `bloco_unico`) · B chega em A ✅ (com
                        `_fatiar_documento` os três viram 1)
FAIXA DE RELÓGIO .....  💭 6–9 h declarada · real: (preencher ao fim)
ORÇAMENTO ............  💭 ≤ 1 M tokens de subagentes (laço curto) · gasto: (preencher ao fim)
BLOCKER (o que é) ....  muda um byte do que a ATENDENTE lê, do que o SEGURADO recebe, do que fica no BANCO ou de quem
                        pode LER. Tudo o mais é pendência (protocolo §2)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?            (preencher: laço curto = 1 juiz fresco + 1 lente do dado)
② a AUDITORIA / juiz fresco? (preencher)
③ pendências por VALOR MARGINAL: (preencher)
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** proposta `docs/canon/specs-propostas/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md` (executada como está — D-PILOTO-20: sem conversão)
**Branch:** `feat/extra-001-6-cobranca`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 13/09/2026: HEAD = origin/main = `de79a130d1063323166907a28b54f80e7c704b9b`, 0 atrás, 0 à frente)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (builders, juiz fresco, lente do dado)
**Início:** 13/09/2026 · **Conclusão:** (preencher)
**Commit inicial:** `de79a130d1063323166907a28b54f80e7c704b9b`
**Commit final:** (preencher)
**Estado final:** EM EXECUÇÃO

---

## 0. Declaração de integridade

- [ ] Nenhum motor paralelo foi criado.
- [ ] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
- [ ] Nenhum DDL monolítico foi aplicado.
- [ ] Nenhum segredo foi exposto (TESTE-A/TESTE-B só por alias).
- [ ] Nenhum escopo foi reduzido sem decisão registrada.
- [ ] Nenhum dado atravessou tenants.
- [x] `CLAUDE.md`, protocolo §0–§5, diagnóstico §0/§7/§9/§12/§13, proposta, research pack, D-PILOTO-*, `MIGRATIONS-AUTHORITY.md` e o relatório da EXTRA-001 lidos no início.

(as caixas restantes fecham no fim, com a prova)

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | RISCO | SUP | piso? | time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| P0 mensagem inteira + motivo + Allianz + blocker + governador | 2 | 3 | 1 | 6 | 1 | §3.2 envia | orquestrador (builder) · verificador mecânico · juiz fresco ao fim |
| B1 dedup + agrupar + janela + migration | 2 | 3 | 1 | 6 | 2 | §3.2 envia + migration | builder Opus · verificador · juiz + lente do dado |
| B2 sessão/health/session_reused/Allianz | 2 | 2 | 1 | 5 | 1 | herda (portal) | builder Opus · verificador · juiz |
| B3 prólogo login_check + backoff + breaker + telas | 2 | 2 | 1 | 5 | 2 | herda | builder Opus · verificador · juiz |
| B4 texto da tela + fila com leitor + print redigido + PII | 2 | 2 | 1 | 5 | 2 | migration 03 altera DADO | builder Opus · verificador · juiz |
| B5 canário + docs | 0 | 0 | 0 | 0 | 1 | — | orquestrador |

---

## 1. BLOCO 0 — as 15 premissas remedidas (13/09/2026, HEAD `de79a13`, projeto `dcajcvlzcjbmyapmklil`)

> 🔴 O número do executor vence (protocolo §5 ①). Toda divergência com a proposta está marcada **DIVERGE**.

| # | premissa | comando | 📊 valor em 13/09 (executor) | proposta | veredito |
|---|---|---|---|---|---|
| 1 | o ledger nunca escreveu | `select count(*) from billing_sent_log` (+ `where send_mode='real'` / `'test'`) | **0 · 0 · 0** | 0 | ✅ |
| 2 | a rotina está desligada e sem destino | `select is_active,next_run_at,config->>'send_mode',length(config->>'team_number'),length(config->>'attendant_name') from routines where config->>'kind'='billing_collection'` | `false` · `2026-09-14 14:01 UTC` · `test` · **0** · **0** — e a chave `attendant_name` **nem existe** no config (chaves: kind, send_mode, portal_keys, team_number, test_number, message_locked, message_template, approval_required, confirmacao_cliente, management_provider, poll_timeout_seconds, max_boletos_por_execucao) | idem | ✅ |
| 3 | o governador contou 7 | `select date_trunc('day',created_at)::date,count(*) from platform_sends where kind='billing' and created_at>='2026-09-09' group by 1` | 10/09 **7** · 11/09 **7** (todos os kinds da história: `billing` 18 · `acionamento_protocolo` 1) | 7 · 7 | ✅ |
| 4 | o texto real vira mais de um balão | motor: `build_customer_message` + `_nota_interna_para_a_equipe` + `_format_test_message` → `split_whatsapp_balloons` vs `_fatiar_documento` (item 💭 ilustrativo, `attendant_name=''` e `'Saionara'`) | texto **332–336 ch → 2** · nota **321 → 2** · teste **520–524 → 3** · com `_fatiar_documento` → **1, 1, 1** · com `attendant_name=''` a linha 2 é literalmente *"Aqui é a nossa equipe, da Resulta, tudo bem?"* | 331/322/517 → 2/2/3 | ✅ (±5 ch pelo item ilustrativo) |
| 5 | `error` é sempre nulo nos jobs | `select count(*) filter (where error is null), count(*) from portal_jobs` | **124/129** — os 5 não-nulos são `vidros_lanternas.abrir_atendimento` de 06–10/07 (worker caído, Playwright sem binário); **100% nulo em todo job de cobrança e login** | 100% | ⚠️ **DIVERGE no número, não na conclusão**: para o relatório da cobrança, `error` continua sendo sempre NULL |
| 6 | o motivo existe em `evidence.message` | `select distinct portal_key,status,evidence->>'message' from portal_jobs where status in ('failed','needs_human') and finished_at>='2026-09-01'` | Allianz `needs_human` *"tela pos-login Allianz nao reconhecida"* (2) · Mapfre `failed` *"a MAPFRE recusou a credencial (autenticacao invalida)"* (2) · Zurich `needs_human` *"200 com ZERO parcelas em 45/90 dias, duas vezes seguidas — NAO afirmo que ela esta em dia"* (2) | idem | ✅ |
| 7 | a sessão nunca vence | `select portal_key,health,verified_at from portal_sessions order by verified_at` | **8 linhas, 8 `ok`**; Resulta: Allianz `verified_at` **17/08** (27 dias), HDI/Tokio/Yelum 11/09; Zurich **14/08**; e 3 linhas de 12/08 de outra empresa (a técnica) | 8 `ok`, Allianz 17/08, Zurich 14/08 | ✅ |
| 8 | `portal_accounts.health` não tem escritor | `select health,count(*) from portal_accounts group by 1` | **16 de 16 = `unknown`** (8 portais × 2 empresas) | 16/16 | ✅ |
| 9 | `available_at` nunca escrito | `select count(*) from portal_jobs where available_at is not null` | **0** | 0 | ✅ |
| 10 | `attempts` nunca lido | `select max(attempts) from portal_jobs` + `worker.py:1001` (lê `available_at`) e `:1017` (`attempts+1`) | **1**; linhas exatas | 1 | ✅ |
| 11 | a PII está no relatório da execução | `... where t.config->>'kind'='billing_collection' and r.output_full like '%CPF/CNPJ%'` | **7 de 49**; com dígitos de documento (`~ 'CPF/CNPJ[: ]+[0-9]'`): **6** | 7/49 | ✅ |
| 12 | os prints existem e são a ÚNICA fonte do texto | `select split_part(name,'/',2),count(*) from storage.objects where bucket_id='portal-evidence' and name like '%desfecho%' group by 1` + `length(evidence->>'body_text')`, `length(evidence->>'debug_dom')` | **6 `done` · 4 `needs-human` · 2 `failed`**; `body_text` e `debug_dom` **NULL** nos 6 jobs não-done; 📊 `md5sum` dos 12: **6 telas distintas** (Allianz, Mapfre e Zurich byte-idênticas nos dois dias) | 6/4/2; 0 | ✅ + o achado dos pares |
| 13 | ninguém enfileira `login_check` | `grep -n '"journey"' backend/app/services/billing_collection.py` | só `"cobranca_sweep"` em **`:680`** | `:680` | ✅ |
| 14 | `tela_cega` tem escritor e não tem leitor | `select count(*) from tela_cega` + `grep -rn tela_cega backend --include=*.py` | **2 linhas**; fora dos testes só `tela_cega.py` (escritor) e `insurer_dispatch_service.py:2890/2998` (chama o escritor) | 2; zero leitores | ✅ |
| **15** | quantos itens reais trazem `cpf_cnpj` | `regexp_matches(output_full,'CPF/CNPJ[: ]*[0-9]...')` sobre as execuções de 10 e 11/09 + `grep -n cpf_cnpj journeys/*.py` | **6 de 7 itens por dia (86%)** com documento, 1 com `?`; **os 7 itens são os MESMOS nos dois dias**; 4 dos 7 têm o **mesmo CNPJ** (14 dígitos) e o mesmo vencimento; 2 sem telefone. Journeys: Allianz (`:170`) · Mapfre (`:299`) · Tokio (`:247`, da API) extraem na lista; **Yelum (`:641`) e Zurich (`:1283`) buscam no detalhe** (`cpf_do_cliente`); **HDI (`:327`) devolve `""` por desenho** ("a tela Parcela não traz documento") | NÃO MEDIDO | 📊 medido: janela por documento cobre 86% do acervo; o fallback por nome é a regra para a HDI |

### 1.1 As telas transcritas — o corpus que não existia

📊 12 prints baixados do bucket privado (`storage/v1/object/portal-evidence/{job}/00-desfecho-*.jpg`, service role, read-only) e lidos como imagem. Resultado em `backend/tests/corpus/telas_reais_de_portal/` (6 arquivos + `INDICE.md`), redigido (`<usuario>`, `<cpf>`, `<nome>`, `<codigo>`):

| tela | o que diz | consequência |
|---|---|---|
| Allianz `needs_human` | **"Acesso negado — Por favor, valide os dados introduzidos."** | é credencial recusada; a `_FAIL` de `allianz_corretor.py:659` não tem nenhuma das duas frases → P0.3 |
| Mapfre `failed` | **"Autenticação inválida!"** + **o CPF do corretor em claro** no campo | confirma o P2 (B4.3: mascarar no DOM antes da foto) |
| Zurich `needs_human` | dashboard **logado**: "Parcelas vencidas", "Minha Conta", razão social da corretora | 🔴 NÃO é credencial recusada — é o CONTROLE negativo do G3 (login = `done`; o `needs_human` é da varredura, e está certo) |
| HDI / Tokio / Yelum `done` | dashboards logados | controles positivos do G3 |

⚠️ **Não existe print real de dashboard da Allianz** (último `done` 17/08, antes de a prova de desfecho existir). O controle "Allianz logada continua `done`" usa o texto sintético já presente em `test_spec023_allianz_login.py:106`, marcado como sintético.

### 1.2 Divergências materiais entre a proposta e a árvore (registradas, não "consertadas")

| # | a proposta diz | o que a árvore tem em `de79a13` | decisão do executor (nota 0–100) |
|---|---|---|---|
| D1 | P0.3 / G3: *"`interpret_login` de cada uma das 6 journeys contra os 12 prints"* | **só Allianz (`:693`) e HDI (`:445`) têm `interpret_login(page_text, url)` puro.** Mapfre (`:585`), Tokio (`:858`), Yelum (`:454`) e Zurich (`:745`) classificam a credencial recusada **dentro do `login_check` assíncrono**, sobre `_norm(await _texto(page))` | **A · extrair, nas 4, um `interpret_login(page_text, url)` puro com EXATAMENTE os mesmos `if` de hoje, e fazer o `login_check` chamá-lo** — nota **85** (refatoração mecânica; comportamento byte-idêntico; o G3 passa a rodar o motor das 6). B · G3 só sobre Allianz+HDI e as outras 4 "documentadas" — 55 (deixa 4 journeys sem prova, e o gate ③ do P0 não fecha). C · dirigir o `login_check` com uma `page` falsa — 40 (frágil, testa o Playwright e não a classificação) |
| D2 | P0.4: *"o campo ganha rótulo humano na tela (`PainelDeRotinas.tsx`)"* | **o campo `attendant_name` NÃO existe na tela** — `grep -n attendant PainelDeRotinas.tsx` só acha os placeholders do template (`:263`, `:272`, `:287`); o config no banco não tem a chave | o P0 **cria** o campo "Quem assina a mensagem" (e a Implantação 1 passa a incluir `smith-web`, que a proposta §15.1 já previa como condicional). Sem ele o Founder não tem como preencher o nome que o blocker exige — nota 95 × "preencher por SQL" 20 |
| D3 | P0.5: *"os cards de `heartbeat.py` que filtram `kind='billing'`"* | **não existe card que filtre `kind='billing'`**: `grep -n billing heartbeat.py` acha só o comentário `:316`; o único leitor humano de `platform_sends` por `kind` é `context_note_for` (`platform_outbound.py:1659-1682`) e o card do Follow-up filtra os kinds dele | o P0.5 ajusta `context_note_for` (ignora `billing_nota`/`billing_doc`) e **não** toca o heartbeat; o gate ⑥ vira "nenhum card passou a contar componente" (prova pelo `grep`) |
| D4 | §4.2 premissa 5: `error` NULL em 100% | 124/129; os 5 são vidros de julho | conclusão intacta para a cobrança (acima) |
| D5 | §4.2 premissa 12: "12 prints" | 12 objetos, **6 telas** | o corpus tem 6 arquivos; a matriz do G3 roda 6 journeys × 6 telas |
| D6 | B1.5: o item 💭 do acervo tem `portal` | o relatório da execução **não imprime o portal por item** | o corpus anonimizado (`tests/corpus/cobranca_acervo_2026-09-11.json`) marca o portal como 💭 ilustrativo; a forma (4 parcelas do mesmo CNPJ, 1 sem documento) é 📊 |

### 1.3 Coordenadas `arquivo:linha` conferidas em `de79a13`

`billing_collection.py`: `ordenar_para_entrega` :334 · `fila_de_cobranca` :362 (return :424) · `normalize_billing_config` :449 (default `"nossa equipe"` :500; `build_customer_message` :619 tem o **segundo** default :631) · `build_customer_message` :619 · `_enqueue_job` :676 (`"journey"` :680) · `_format_test_message` :973 · `FLAG_DEDUP_TESTE` :1056 · `dedup_de_envio_ativa` :1059 · `_send_test_messages` :1067 (`ordenar_para_entrega` :1119, `send_message` :1153, `if dedup` :1191) · `_registrar_no_governador` :1253 (`record_platform_send` :1261) · `_incidente` :1333 · `_whatsapp_legivel` :1350 · `_nota_interna_para_a_equipe` :1366 · `_reservar_obrigacao` :1437 (rpc :1449) · `_entregar_cobranca_real` :1491 (laço :1544; porta :1669/:1683) · `_format_report` :1810 (clientes :1885-1891) · `_mascarar_documento` :1931 · `execute_billing_collection_routine` :2270 (laço de portais :2301) · relatório `needs_human` :2329 / `failed` :2331.
`platform_outbound.py`: `record_platform_send` :312 · `send_to_client_guarded` :1070 · `_entregar_agora` :1439 (`send_message` :1478-1479; `send_document` :1490; `record_platform_send` :1494) · `context_note_for` :1659 (`hits[:3]` :1680).
`whatsapp_service.py`: `_fatiar_documento` :92 · `send_message` :131 (`bloco_unico` :157).
`portal_worker/worker.py`: `_load_session_bundle` :240 · `_save_session_state` :271 (`health: ok` :294) · `_prova_do_desfecho` :411 · `session_reused` :812 · `_prova_do_desfecho(...)` :884 · `"error": None` :944 · `available_at` :1001 · `attempts+1` :1017.
`allianz_corretor.py`: `_norm` :24 · `_FAIL` :659 · `interpret_login` :693 · `login_check` :803 · `_diagnosticar_sessao_na_pagina` :2572 · `_relogin_fresh` :2748 · `cobranca_sweep` :3755 (`if login.status != "done"` :3758; diagnóstico :3786, relogin :3793).
`app/api/portal.py`: lista devolve `health` :141 · salvar grava `health='unknown'` :165.
Outros chamadores da porta (NÃO viram documento): `saudacao_do_religamento.py:541` · `dispatch_followup.py:282` · `platform_outbound.py:1635` (fila) · `intelligence/delivery_executor.py:283`.

### 1.4 `grep` do valor antigo (`BILLING_DEDUP_TEST_ENABLED`) antes do B1

📊 `grep -rn BILLING_DEDUP_TEST_ENABLED` (árvore, sem `node_modules`/`.git`): `billing_collection.py:1054,1056` · `PENDENCIAS.md:5958` · a proposta e o research pack desta SPEC. Depois do B1 os dois primeiros têm de sumir e o `PENDENCIAS.md:5958` recebe a nota da inversão.

---

(seções 2–14 preenchidas por bloco, abaixo)
