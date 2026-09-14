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
| 7 | a sessão nunca vence | `select portal_key,health,verified_at,left(company_id::text,8) from portal_sessions order by verified_at` | **8 linhas, 8 `ok`**. Resulta (`04b5cdbc`): Allianz `verified_at` **17/08** (27 dias), HDI/Tokio/Yelum 11/09 — **sem linha de Zurich nem de Mapfre**. A outra empresa (`6c9c55e2`, a técnica): Allianz/HDI/Tokio 12/08 e **Zurich 14/08**. ⚠️ A primeira versão desta linha atribuiu a Zurich de 14/08 à Resulta; a lente do dado (§5, A-3) corrigiu | 8 `ok`, Allianz 17/08, Zurich 14/08 | ✅ com a correção da dona da sessão |
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

---

## 2. BLOCO P0 — a mensagem chega inteira e a falha fala português (implantável no 1º dia)

> É o "BLOCO 0" da D-PILOTO-18: a condição de reativar a rotina. Não depende das senhas novas.

### 2.1 O que entrou, por contrato da proposta §5

| contrato | estado | onde | evidência |
|---|---|---|---|
| P0.1 `bloco_unico` decidido por `kind` | CONCLUÍDA | `platform_outbound.py`: `MENSAGENS_QUE_SAO_DOCUMENTO`, `e_documento`, `_entregar_agora` passa `bloco_unico=True` **só** quando é documento (a chamada de conversa continua `send_message(destino, texto, integration)`, letra por letra — é o que os guardas 078 e governador medem); `billing_collection.py` `_send_test_messages` passa `bloco_unico=True` | G1: 17 asserções; M1 vermelha |
| P0.2 o motivo do portal aparece | CONCLUÍDA | `billing_collection.py`: nova função pura `_blocker_do_job(job)` (evidence.message → error → "sem motivo registrado"), chamada no laço do relatório | G2: 6 asserções sobre a linha REAL da Mapfre; M2 vermelha |
| P0.3 a Allianz para de mentir | CONCLUÍDA | `allianz_corretor.py:_FAIL` + `"acesso negado"`, `"valide os dados"` (dialeto do `_norm`); `test_spec023_allianz_login.py` lê o corpus real e mantém a frase inventada como controle | G3: 32 asserções, 6 journeys × 6 telas reais; M3 vermelha |
| P0.3 (divergência D1) `interpret_login` puro nas 4 journeys que não tinham | CONCLUÍDA | `mapfre_corretor.py`, `tokio_corretor.py`, `yelum_corretor.py`, `zurich_corretor.py`: os MESMOS `if` movidos para `interpret_login(page_text, url) -> JourneyResult | None`; `login_check` os chama | testes das 4 journeys continuam verdes (93 · 78 · 68 · Zurich pré-existente, ver §2.3) |
| P0.4 sem o nome de quem assina, a rotina não sai | CONCLUÍDA | `normalize_billing_config`: `elif send_mode in MODOS_REAIS and not attendant_name → MODO_RETIDO` com motivo em português; default "nossa equipe" continua só em `test`/`none`; **campo novo** "Quem assina a mensagem" em `PainelDeRotinas.tsx` (divergência D2: não existia) | G4: 9 asserções; M4 vermelha; `tsc --noEmit` (§2.2) |
| P0.5 o governador conta o que o canal recebeu | CONCLUÍDA | `platform_outbound.py`: `KIND_DE_CONTAGEM` (`billing_equipe`/`billing_cliente` → `billing`; `billing_equipe_nota` → `billing_nota`), `KIND_DO_DOCUMENTO_DA_COBRANCA = "billing_doc"` gravado depois do `send_document` aceito, nos DOIS caminhos (`_registrar_documento_no_governador` no modo teste); `context_note_for` ignora `KINDS_DE_COMPONENTE` | G5: 7 asserções; M5 vermelha |
| §12.3 o guarda de controle migra | CONCLUÍDA | `test_a_cobranca_esta_como_estava.py`: a constante de 292 ch e o helper `caminho_de_hoje` saíram; o texto vem de `build_customer_message`, a decisão de `e_documento`, os balões contados por dublê no seam real de `send_message`; 34 → **36** asserções (o G20 da EXTRA-001 recebeu o novo número com a lição escrita) | 36/36 |

### 2.2 Testes rodados (saída real, 13/09/2026)

```
$ PYTHONIOENCODING=utf-8 python tests/test_a_cobranca_prova_que_funciona.py
  [G1] 17 ok · [G2] 6 ok · [G3] 32 ok · [G4] 9 ok · [G5] 7 ok
  69 assercoes verdes - 0 vermelhas

$ python tests/test_a_cobranca_prova_que_funciona.py --mutar
  [ok] M1 deixa G1 VERMELHO: [FALHOU] `e_documento('billing_cliente')`
  [ok] M2 deixa G2 VERMELHO: [FALHOU] a linha do relatorio traz o motivo REAL da Mapfre  portal mapfre_corretor: failed — sem motivo registrado
  [ok] M3 deixa G3 VERMELHO: [FALHOU] allianz_corretor-needs_human-20260911.txt -> a propria journey diz `failed` ...  tela pos-login Allianz nao re
  [ok] M4 deixa G4 VERMELHO: [FALHOU] `equipe` sem nome -> `retido_legado` (nada sai)  equipe
  [ok] M5 deixa G5 VERMELHO: [FALHOU] nota -> `billing_nota`; texto -> `billing`; PDF -> `billing_doc`  ['billing_nota', 'billing', 'billing']
  PLACAR DAS MUTACOES: 5 vermelhas · 0 verdes          (árvore restaurada por cópia: `git status` só com os arquivos do P0)

$ python tests/test_a_cobranca_esta_como_estava.py        36 assercoes verdes - 0 vermelhas   (era 34)
$ python tests/test_a_cobranca_chega_a_quem_deve.py       verde (G02 migrado: o config `equipe` do gate carrega `attendant_name`; G20 espera 36)
$ python tests/test_spec023_allianz_login.py              20 ok / 0 fail   (era 19: +1 sobre a tela REAL)
$ python tests/test_spec078_bloco_a_seguranca.py          39 verdes · 0 vermelhas
$ python tests/test_governador_de_envio.py                verde
$ python tests/test_mapfre_cobranca.py                    93 verdes · python tests/test_tokio_cobranca.py 78 · test_yelum_cobranca.py 68
$ python tests/test_spec031_allianz_fixes.py              13 passaram
$ npx tsc --noEmit                                        rc=0 (13/09/2026)
```

⚠️ **M3 remove as DUAS frases**, não só `"acesso negado"` como a proposta §11 escreveu: tirar só uma deixaria a outra casar e o guarda continuaria verde — mutação que não muda comportamento não mede.

### 2.3 Triagem nominal contra a base (`de79a13`, worktree limpo `../AutoBrokers-FIX-base-0016`)

| falha | na base? | veredito |
|---|---|---|
| `test_zurich_cobranca.py:123` `IndexError: list index out of range` (`atrasados[0]`) | **SIM, igual** | pré-existente, não é desta SPEC (provavelmente dependente da data do fixture); vai para PENDENCIAS |
| `test_spec078` 3 vermelhas · `test_governador_de_envio` `TypeError` | não | **minha**, corrigida: os dublês de `send_message` desses testes não aceitam `bloco_unico`; o kwarg agora só viaja quando é documento |
| `chega_a_quem_deve` `[CTL] platform_outbound chama o canal em no maximo 2 lugares — achou 3` | não | **minha**, corrigida: uma chamada única com kwargs condicionais |

### 2.4 O que o P0 NÃO fecha (e fica para os blocos seguintes ou para o Implantar)

- gate P0 ⑤ da proposta (rotina da Resulta em `test` no IMPLANTADO → 1 balão por texto, `platform_sends` por componente): só depois do Implantar; entra no canário (B5).
- dedup em `test` continua desligada por padrão (é o B1.1); por isso `test_a_cobranca_esta_como_estava.py:212` ainda afirma o padrão antigo — migra no B1.

---

## 3. LOTE 1 — BLOCO 1 (B1) ∥ BLOCOS 2+3 (B2, B3) · commit `6f1249f`

Dois builders Opus 5 em paralelo, arquivos disjuntos (A: `billing_collection` + migration + Painel; B: `portal_worker` + `app/api/portal` + Central + telas). Integração pelo orquestrador: o vocabulário de `health` passou a ser importado do worker (`SAUDE_*`) em `billing_collection`, com fallback literal só quando o pacote do worker não está no PYTHONPATH.

### 3.1 B1 — ninguém é cobrado duas vezes (Builder A · 📊 414k tokens · 53 min)

| contrato | estado | evidência |
|---|---|---|
| B1.1 dedup SEMPRE, flag invertida (`BILLING_DEDUP_TEST_DISABLED` desliga, só em `test`) | CONCLUÍDA | G6 · M6 vermelha · `grep -rn BILLING_DEDUP_TEST_ENABLED backend/` → **0** (era 2) |
| B1.2 `segurado_chave` (doc/nome/recibo, SEM portal) · `chave_do_grupo` (empresa\|segurado\|portal) · `agrupar_por_segurado` nos DOIS caminhos · 1 nota + 1 texto + N PDFs · N reservas por parcela | CONCLUÍDA | G7 sobre o acervo anonimizado: 4 parcelas do mesmo CNPJ = 1 grupo; tenants nunca se fundem; portais nunca na mesma mensagem · M7 vermelha |
| B1.3 janela de N dias por `segurado_chave` (N=7, tela, clamp 1–30); retenção com motivo, DATA e ORIGEM da identidade; falha de leitura LEVANTA no modo real | CONCLUÍDA | G8: cobrado há 3 dias → retido; há 8 → cobra; sem documento → retido por NOME; outra seguradora → retido · M8 vermelha |
| B1.4 migration `20260914_01` | **APLICADA** (§4) | VERIFY V0–V6 no Postgres real |
| B1.5 copy do plural (💭 até o Founder emendar) | CONCLUÍDA | N=1 byte a byte igual ao template; N>1 plural nas frases fixas; template personalizado → singular com a lista |
| B3.1 prólogo: `login_check` por portal ANTES de qualquer `cobranca_sweep`; breaker lido de `portal_accounts.health`+`updated_at` | CONCLUÍDA | G10: `credencial_recusada` não gera job nenhum; `login_check` ≠ `done` não abre varredura · M10 vermelha |
| tela: "Dias entre cobranças do mesmo segurado" | CONCLUÍDA | `PainelDeRotinas.tsx` + clamp na rota; `tsc` rc=0 |

**Divergências decididas pelo builder (registradas, com nota):** D1 uma passagem pelo governador POR GRUPO exigiria tocar `platform_outbound` (fora da lista) → N+1 passagens por grupo (85 × 60 × 0) — vira `P-E0016-GOVERNADOR-POR-APROXIMACAO` · D2 `chave_do_grupo` com TRÊS segmentos (empresa|segurado|portal) para o G7 poder ficar vermelho com dois tenants (88 × 45) · D3 em `test`, janela ilegível NÃO para a simulação (88 × 60; o guarda de 19/08 afirma "banco fora do ar: a entrega acontece") · D3b a flag de demonstração também desliga a janela em `test` (88 × 55) · D6 parcelas do mesmo segurado com telefones divergentes → retidas com motivo · D5c **defeito do P0 achado pelo builder**: o dublê de `test_a_sessao_caida_volta_e_o_aviso_diz_a_verdade.py` não aceitava `bloco_unico` (vermelho desde `94862ea`; a lista de vizinhos do P0 não o incluía) — consertado e migrado (58/58).

### 3.2 B2 + B3 — a sessão morre, alguém sabe, o portal é vigiado (Builder B · 📊 296k tokens · 33 min)

| contrato | estado | evidência |
|---|---|---|
| B2.1 TTL sobre `verified_at` (`PORTAL_SESSION_TTL_HORAS` 12, clamp 1–72); sessão vencida não é injetada, `evidence["sessao_vencida"]` | CONCLUÍDA | G9 · M9 vermelha |
| B2.2 `health` com ESCRITOR nas duas tabelas (`_escrever_saude`, `updated_at` explícito, `company_id` no update); classificador PURO `veredito_de_saude` sobre as 6 mensagens reais do acervo | CONCLUÍDA | B2.2: Zurich logada com varredura vazia → `ok` (não é senha); Mapfre → `credencial_recusada`; Allianz depois do P0 → `credencial_recusada` · M13 vermelha |
| B2.3 `session_injetada` (o fato) × `session_reused` (só quando valeu: `done`, `logged_in`, sem relogin) | CONCLUÍDA | controle: o job real de 11/09 replayado → `session_injetada=True`, `session_reused` ausente |
| B2.4 Allianz: diagnóstico de sessão morta ANTES do `return`; uma retentativa; nunca com `failed` | CONCLUÍDA | B2.4 no guarda; diff de 17 linhas, zero seletor tocado. **Divergência D1 do builder:** o bloco "morto" de `:3786` não era morto — vive no ramo "logado mas sem tela de parcelas" (`_ensure_inadimplentes_page`); os dois ficam (92 × 25) |
| B3.2 `available_at` + full jitter (`proximo_available_at`, base 60 s, teto 900, máx 3 tentativas); requeue só transitória e sem efeito material; credencial recusada NUNCA | CONCLUÍDA | G11 · M11 vermelha · M14 (defeito que o próprio builder criou e fechou: a 2ª tentativa herdava `excecao_transitoria` e escondia a senha recusada) |
| B3.3 breaker nos três estados dentro de `portal_accounts.health`; `fora_do_ar` só depois de N transitórias seguidas; reabre pelo prólogo via `updated_at` | CONCLUÍDA | G10-② |
| B3.4 `saude_do_portal.py` (rótulo humano ÚNICO) → `GET /portal/credentials` (`health_rotulo`, `health_acao`, `verificado_em`) e a tela de Conectores; grupo "Portais das seguradoras" na Central (pior `health` entre contas, última verificação, sucesso 7d, motivo da última falha) | CONCLUÍDA | B3.4-④; `test_a_central_diz_a_verdade` 530 ok; `tsc` rc=0; `test:rotas-montam` 301 rotas. **D3:** `unknown` pinta NÃO MEDIDO (cinza), não amarelo (88 × 55) |

### 3.3 Verificação mecânica do lote (14/09/2026, árvore parada, HEAD `6f1249f`)

```
test_a_cobranca_prova_que_funciona.py ......... 161 assercoes verdes - 0 vermelhas   (--mutar: M1–M8, M10 = 9 vermelhas · 0 verdes)
test_o_portal_diz_por_que_nao_entrou.py ....... 110 assercoes verdes - 0 vermelhas   (--mutar: M9, M11, M13, M14 = 4 vermelhas · 0 verdes)
test_a_cobranca_esta_como_estava.py ........... 38 verdes (34 → 36 no P0 → 38 no B1: a dedup migrada e invertida em 3 linhas)
test_a_cobranca_chega_a_quem_deve.py .......... 169 ok · 0 falha(s) · 3 pulado(s)
test_spec078_bloco_a_seguranca.py ............. 39 verdes
test_a_cobranca_alcanca_todas_as_seguradoras .. PASS=171 FAIL=0
test_a_sessao_caida_volta_e_o_aviso_diz_a_verdade 58 verdes (estava VERMELHO desde o P0 — D5c)
test_spec023_allianz_login.py ................. 20 ok / 0 fail
test_a_central_diz_a_verdade.py ............... 530 ok, 0 falhas
test_governador_de_envio.py ................... rc=0 · test_o_relatorio_abre_pelo_achado rc=0 · mapfre 93 · tokio 78 · yelum 68
npx tsc --noEmit rc=0 · npm run test:rotas-montam OK (301 rotas)
pré-existentes na base (não são desta SPEC): test_zurich_cobranca.py:123 IndexError
```

---

## 4. Migrations

### `20260914_01_spec_extra0016_cobranca_por_segurado.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | o ledger passa a saber DE QUEM é a parcela (`segurado_chave`), para a regra "1 cobrança por segurado a cada N dias" |
| **Expand-first** | sim: coluna nula, índice parcial novo, SOBRECARGA de 13 args sem DEFAULT (a de 12 fica; `P-E0016-RESERVA-12-ARGS`) |
| **Destrutiva** | não |
| **APPLY** | `alter table … add column if not exists segurado_chave text` + COMMENT · `create index if not exists billing_sent_log_segurado_idx (company_id, segurado_chave, sent_at desc) where send_mode='real'` · `create or replace function billing_reservar_obrigacao(… 13 args)` com o corpo gerado de `pg_get_functiondef` do objeto vivo + a coluna/valor no INSERT |
| **VERIFY (saída real, 14/09/2026 01:35 UTC)** | V0 `true uv · true colisao · true onconflict · true segurado` (13 args; 114 chars a mais que a de 12) · V1 `segurado_chave text nullable=YES` · V2 `… (company_id, segurado_chave, sent_at DESC) WHERE (send_mode = 'real'::text)` · V3 2 linhas: 12 args e 13 args · V4a `ganhou=true status=reservado` id `f43749af…` · V4b `segurado_chave='doc:00000000000'` · V4c `ganhou=false` **mesmo id** `f43749af…` · V5a 12 args `ganhou=true` (sem 42725) · V5b `segurado_chave is null = true` · V6 `send_mode='test'` = 0 · limpeza: 2 linhas VERIFY apagadas por recibo, `send_mode='real'` = 0 |
| **ROLLBACK** | escrito no arquivo; só seguro com 0 linhas `real` (📊 0); ordem: código antes do schema |
| **Aplicada em produção** | sim · 14/09/2026 · versão `spec_extra0016_cobranca_por_segurado` (MCP `apply_migration`) |
| **MANIFEST atualizado** | sim (e a linha da `20260907_01`, que dizia "pendente" para uma função VIVA, corrigida para "aplicada 07/09") |

**Advisors antes:** segurança 133 (122 `rls_enabled_no_policy` · 2 `security_definer_view` · 3 `function_search_path_mutable` · 3+3 SECURITY DEFINER executáveis) · desempenho 314
**Advisors depois:** segurança **133** (iguais) · desempenho **315**
**Diferença:** +1 em `unused_index` (180 → 181 achados no total; nenhum nome novo entre os que a primeira leitura listou — a diferença está na contagem agregada do próprio linter, e o índice novo numa tabela com 0 linhas é o candidato esperado; MIGRATIONS-AUTHORITY §8.7 proíbe remover por isso). Nenhum achado de segurança novo: a função nova tem `set search_path`.

### 3.4 B4 — a prova tem leitor (Builder C · 📊 265k tokens · 36 min) · lote 2

| contrato | estado | evidência |
|---|---|---|
| B4.1 `evidence["tela"]` (texto redigido ≤2000, `hash` sha256 do texto normalizado, `url` sem query, `prova`) em TODO desfecho não-`done` — nas três chamadas de `_prova_do_desfecho` (timeout, exceção, status) | CONCLUÍDA | B4.①: `page` dublê com o texto REAL da Mapfre + CPF sintético → o CPF NÃO está no texto gravado; hash estável · M-B4.1 vermelha. **D-B4-1:** `redaction.redigir_texto` JÁ cobria texto livre (9 padrões) — reaproveitado, nenhum redator novo (95 × 55 × 0) |
| B4.2 fila de telas desconhecidas = CONSULTA sobre `portal_jobs` agrupada por `evidence.tela.hash`, com DOIS leitores: o card do portal na Central (`telas_desconhecidas` + frase "N telas que eu não reconheço — a mais frequente vista K×") e UMA linha por tela nova do dia no relatório da rotina | CONCLUÍDA | B4.② com dois tenants · M-B4.2 vermelha · **O ELO** (M-B4.4): as telas de LOGIN só chegam à fila porque o `_canario_de_login` passou a devolver os jobs vistos — sem isso a fila nunca veria a tela da Allianz/Mapfre (o `cobranca_sweep` nem é enfileirado) |
| B4.3 máscara no DOM antes da foto (`input` password/text/email/tel → `••••••••`) em desfecho não-`done` | CONCLUÍDA | B4.③: o dublê registra a ORDEM (evaluate ANTES de screenshot) · M-B4.3 vermelha |
| B4.4 `_format_report` sem CPF/CNPJ nem telefone inteiros (`...0272`, `...0002`); a nota interna continua com `_whatsapp_legivel` | CONCLUÍDA | G12 + M12 vermelha; CONTROLE: a nota CONTÉM o telefone |
| migration `20260914_03` (redação do legado) | **APLICADA** (§4) | V0–V4 no Postgres real |
| URL assinada da evidência com TTL curto | JÁ ERA | 📊 `_TTL_DOCUMENTO_S = 15*60` (`platform_outbound.py:1011`); o print nunca é assinado nem anexado |

**Defeitos que o builder achou e fechou no caminho:** (1) `telas_novas_do_dia` receberia o WRAPPER do Supabase em vez do cliente postgrest (`AttributeError` em toda execução, silencioso) — corrigido; (2) o ELO da fila estava quebrado (acima). **Divergências:** D-B4-2 `prova` nasce `""` e é preenchida com o `onde` REAL depois do upload (90 × 40 × 10); D-B4-3 `tela` NÃO entra em `CHAVES_DE_DIAGNOSTICO` de propósito — uma segunda rede deixaria M-B4.1 verde (CLAUDE.md §9.3).

### 3.5 Verificação mecânica do lote 2 (14/09/2026, árvore parada)

```
test_a_cobranca_prova_que_funciona.py ......... 177 assercoes verdes - 0 vermelhas   (--mutar: M1–M8, M10, M12 = 10 vermelhas · 0 verdes)
test_o_portal_diz_por_que_nao_entrou.py ....... 172 assercoes verdes - 0 vermelhas   (--mutar: M9, M11, M13, M14, M-B4.1..4 = 8 vermelhas · 0 verdes)
test_a_central_diz_a_verdade.py ............... 530 ok · test_a_cobranca_esta_como_estava 38 · test_a_cobranca_chega_a_quem_deve 169 ok
test_spec073_portal_worker_mutations .......... 134 verdes · test_o_relatorio_abre_pelo_achado rc=0
canário Q7–Q10 (orquestrador): py_compile ok; nenhum guarda cita o canário
```

### `20260914_03_spec_extra0016_redigir_output_full.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | apagar CPF/CNPJ e telefone de segurado dos relatórios de execução da cobrança JÁ gravados em `routine_runs.output_full` |
| **Expand-first** | não se aplica (sem estrutura nova) |
| **Destrutiva** | **sim** — altera dado gravado; decisão na proposta §9 B4.4 (irreversível e correto: o dado é PII que nunca deveria estar ali; continua na InfoCap e em `billing_sent_log.to_phone`) |
| **APPLY** | `update routine_runs set output_full = regexp_replace(regexp_replace(output_full,'(CPF/CNPJ[: ]*)[0-9][0-9./-]{9,17}','\1•••','g'),'(WhatsApp: )[0-9]{8,15}','\1•••','g') where id in (<6 ids fixados>)` |
| **A lista fixada (SELECT rodado ANTES, 14/09/2026)** | 6 linhas (não 7: o 7º relatório com "CPF/CNPJ" só tem `?`): `c0580f6c…` md5 `da2d39a3…` 1189 ch (17/08) · `b8742b94…` md5 `27af98f1…` 1005 (17/08) · `e8a2b731…` md5 `27af98f1…` 1005 (17/08) · `89e1c389…` md5 `c9545b90…` 729 (17/08) · `34722df5…` md5 `2a572730…` 1625 (10/09) · `37c77d7d…` md5 `bff62fc9…` 1625 (11/09). ⚠️ `routine_runs` não tem `created_at` (42703): o SELECT do arquivo usa `started_at` |
| **VERIFY (saída real)** | V0 `ainda_com_pii` = **0** · V1 `com_documento` = **0** · V2 `com_telefone` = **0** · V3 CONTROLE `explicacoes_intactas` ("WhatsApp: sem telefone") = **7** · V4 CONTROLE `relatorios_inteiros` ("Clientes encontrados:" + "CPF/CNPJ") = **7** · V5 `CPF/CNPJ •••` = **6** · tamanhos depois: `c0580f6c` 1189 → 1140 · `34722df5` 1625 → 1519 |
| **ROLLBACK** | não existe, por construção (escrito antes do APPLY); o que o substitui é o `md5`/`length` de antes, colado acima |
| **Aplicada em produção** | sim · 14/09/2026 · versão `spec_extra0016_redigir_output_full` |
| **MANIFEST atualizado** | sim |

---

## 5. O PAINEL DO LAÇO CURTO — juiz fresco + lente do dado (14/09/2026, sobre `61073ff`)

Dois agentes Opus 5 em contexto limpo, cegos entre si, read-only: o **juiz fresco** (proposta + diff + guardas rodados + `--mutar` + as três perguntas adversariais fixas do Founder) e a **lente do dado** (reconstrução das 15 premissas, das duas migrations e do número central do B1 sobre o acervo real, por SELECT).

### 5.1 Juiz fresco — **FAIL · 79/100** (📊 309k tokens · 15 min)

Amostra §0.4 reproduzida 3/3 (177 · 172 · `--mutar` 10+8 vermelhas; ledger 0, assinaturas 12+13, índice parcial, `pii_restante=0`). Vizinhos rerodados com os números do relatório.

| # | [B/P] | achado (arquivo:linha) | TESTE DO PRODUTO | conserto (rodada 1) |
|---|---|---|---|---|
| 1 | **B** | `_canario_de_login`: teto de 120 s × fila real do worker de **144 s em média, 511 s máx.** (📊 `avg(started_at-created_at)` em `portal_jobs`); worker serial por padrão (`PORTAL_WORKER_CONCURRENCY` 1, poll 30 s) → o `login_check` estoura o teto, `contas.pop(portal)` e **5 de 6 portais deixam de ser varridos** | SIM — a atendente deixa de receber a cobrança de 5 portais | teto 600 s (clamp 60–900) **e** no timeout o portal é varrido assim mesmo com blocker (ausência de veredito ≠ veredito ruim); descarte só com `failed`/credencial |
| 2 | **B** | canário: Q1, Q2a/b, Q3 e Q5 compartilham `segurado_chave` (`nome:cliente canario`) → a janela de 7 dias retém o Q5 ANTES da porta: a prova da allowlist ficaria vermelha por motivo falso; Q2a/Q3 verdes pelo motivo errado (§9.3) | SIM (segurança: Q5 é a única prova viva da allowlist) | identidade própria por Q (nome distinto; Q2/Q3 mantêm o recibo do Q1 para medirem a RESERVA) |
| 3 | P | Q10 verde em qualquer cenário (`all([])` é True; 0 portais aprovados passa) | não (instrumento) | exigir ≥1 portal `ok` e aprovados+blockers = 4 |
| 4 | P | `BILLING_LOGIN_CHECK_TETO_S` não declarada em documento nenhum | não | §15.2 abaixo + docstring |
| 5 | P | Allianz: `_FAIL` avaliado ANTES dos `_DASHBOARD_SIGNALS`; um dashboard logado com "acesso negado" num toast viraria `credencial_recusada` (breaker aberto, Founder mandado trocar senha certa); não há print real de dashboard da Allianz para controle | não (não medido que ocorra) | `failed` só com `hits < 2` |
| 6 | P | `segurado_chave` aceita documento de qualquer comprimento ("000.000/0" → `doc:0000000`; placeholder funde segurados) | não (acervo só tem 14 dígitos) | 11 ou 14 dígitos, não todos iguais; senão cai no nome |
| 7 | P | a proteção multi-tenant de `chave_do_grupo` é vazia no caminho real (os itens de `_extract_items` não carregam `company_id`; o G7 injeta à mão) | não (a execução é de uma corretora) | `agrupar_por_segurado(items, company_id=...)` |
| 8 | P | o prólogo dobra os jobs por execução e duas execuções no mesmo minuto enfileiram 2 `login_check` por portal (bater duas vezes é o que bloqueia conta) | não hoje | dedup na fila: reusar `login_check` `queued`/`running` dos últimos 30 min |
| 9 | P | a limpeza do canário não apaga os `portal_jobs` do Q10 | não | apagar por `params->>routine_id` da rotina sintética |
| 10 | P | a fila de telas da Central agrega sem `company_id` e a amostra pode trazer a razão social (rota `require_master_admin`: não é travessia) | não | `P-E0016-AMOSTRA-PODE-TRAZER-RAZAO-SOCIAL` (🧑) |

**As três perguntas adversariais (respostas do juiz, com prova):** (1) **dado vazio/nulo** — `attendant_name="   "` retém; `evidence`/`error` NULL → "sem motivo registrado"; `verified_at` NULL → não injeta; `updated_at` NULL com `fora_do_ar` → tenta uma vez; `portal_keys []` → os 6 default; itens `[]` → `[]`; `evidence` sem `tela` → `([], "")`; o que quebra: dois itens sem doc, sem nome e sem recibo viram um grupo `recibo:` — no caminho real caem nas pré-condições. (2) **duas corretoras** — `_segurados_cobrados_recentemente` e `_escrever_saude` filtram `company_id` no CÓDIGO; `portal_sessions` UNIQUE `(company_id, portal_key, account_label)`; `telas_novas_do_dia` filtra; só a Central agrega (master-admin). (3) **a mesma mensagem duas vezes** — reserva por parcela intacta (RPC com `ON CONFLICT … WHERE send_mode='real'`); perder a reserva tira só a parcela; o requeue do worker limpa as chaves de tentativa e retorna antes de `_escrever_saude`; o que fica em aberto é o achado 8.

### 5.2 Lente do dado — **PASS COM PENDÊNCIAS · 76/100** (📊 229k tokens · 20 min)

15 premissas + 2 migrations reconstruídas por SELECT: **14 batem**; a premissa 7 tinha a dona da sessão errada (A-3, corrigida acima). A migration 01: diff 12 × 13 args com **exatamente 3 diferenças** (parâmetro, coluna, valor), 2245 → 2359 chars (+114), `unique_violation`/`colisao_recibo`/`ON CONFLICT`/`search_path` nas duas. A migration 03: 1189→1140, 1625→1519, 1005→956, 729→680; 6 mascaradas; 0 com dígito; 7 com rótulo; 7 "sem telefone". O classificador de saúde sobre os 12 jobs reais: 12/12 como o esperado. As 6 telas: 6 hashes distintos, zero PII sobrevivente.

| # | [B/P] | achado | TESTE DO PRODUTO | conserto (rodada 1) |
|---|---|---|---|---|
| A-1 | **B** | 📊 **`routine_runs.output_preview`** (= `output[:500]`, `routine_engine.py:348`) ainda tem `CPF/CNPJ <dígitos>`/telefone em **5 execuções**; em 4 delas `output_full` é NULL e a tela (`entregas/rotina/[runId]/page.tsx:140`: `completo || output_preview`) mostra o preview → PII em claro na tela HOJE. A migration 03 filtrou por `output_full` e nunca olhou a coluna irmã. Varredura de 1.202 colunas texto/jsonb: nenhuma outra tabela de relatório/peça tem o texto | SIM (quem pode LER) | migration `20260914_04` sobre `output_preview`, ids fixados (5) |
| A-2 | **B** | 📊 as "4 parcelas do mesmo CNPJ" da Tokio são **4 linhas com o MESMO recibo, mesma apólice, parcela "1", mesmo vencimento e UM boleto consolidado** (`valor_original` = soma). `_boletos_by_recibo` devolve 1 chave; o laço por grupos reserva 1 e produz **3 bloqueios falsos** ("reservadas e sem desfecho") por execução para a atendente ler; o corpus anonimizado inventou 4 recibos e o dublê `BancoLeve.rpc` não modela o índice único | SIM (o que a atendente lê, toda semana) | `consolidar_por_recibo` dentro do grupo antes de reservar; corpus com a forma real 📊 + um caso 💭 de N recibos; dublê fiel ao índice; G7 refeito |
| A-3 | P | premissa 7 com a dona da sessão errada | não | corrigida no §1 |
| A-4 | P | `veredito_de_saude`: `'invalid'` em `_MARCAS_DE_CREDENCIAL` captura "sessao invalida" → `credencial_recusada` (breaker aberto até gesto humano) | não (nenhuma journey escreve a frase hoje) | sessão caída avaliada antes da credencial; "ausente" → `pede_humano` |
| A-5 | P | o plural decide por `len(parcelas)`, não por números distintos ("as parcelas 1") | não hoje (A-2 derruba antes) | plural por recibos distintos depois da consolidação; números iguais ganham o sufixo da apólice |
| A-6 | P | docstring de `telas_desconhecidas` afirma "nenhum identificador de corretora na saída" — a amostra traz razão social em 4 de 6 telas reais | não (texto) | docstring corrigida |
| A-7 | P | **"do seguro do 180"**: `_insured_item_name` cai no código de ramo da Tokio (📊 5 itens reais); e o default rende "do seguro do seguro" — pré-existente, mas a premissa 4 mediu o texto sobre um item 💭 e não o viu | não (pré-existente, caminho intocado) | candidato numérico não serve; sem nome de item, o template padrão rende "do seguro" |
| "não vi" 1 | P | `_segurados_cobrados_recentemente` lê o ledger sem corte de data no SQL (teto de linhas do PostgREST deixaria de ver as recentes em silêncio) | não hoje (0 linhas) | `.gte("updated_at", corte)` |
| "não vi" 2 | risco | **`login_check` nunca rodou em produção** (📊 129 jobs, 100% `cobranca_sweep`) — o prólogo é o maior risco do Implantar | — | canário Q10 depois da Implantação 2 |

**A conta que a lente fez para a 1ª execução real em `equipe`** (com o nome e o `team_number` preenchidos; ledger vazio): 4 grupos (Tokio ×2, Yelum, HDI por NOME) → 4 notas + 4 textos + 4 PDFs + 4 reservas = 12 linhas em `platform_sends`; **2ª execução no dia seguinte: 4 grupos retidos pela janela, 0 mensagens** — três retenções "por CPF/CNPJ", uma "por NOME … libere pela tela". Com o config de hoje (sem `team_number`): **zero**, retido com motivo.

### 5.3 O conserto — rodada 1 (Builder D, Opus 5)
Os 4 blockers (juiz 1–2, lente A-1–A-2) + as 13 pendências baratas acima, numa rodada. Resultado em §5.4.
