# SPEC-117 · O atendimento nunca perde a apólice que encontrou

> **SPEC DEFINITIVA** · 26/09/2026 · convertida da proposta de 24/09 (`specs-propostas/SPEC-117-…md`)
> sobre o HEAD `79c9e80` (`origin/main`, SPEC-116-RESERVA) · branch `spec/117-apolice-persistente`
> **Rito:** PROTOCOLO AUTOBROKERS AAA **v13.2 · O FIO** (D-PROTO-13 — gerente/juiz/red team Opus 5.5)
>
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1

---

## §0 · O EXECUTION CARD

```
OUTCOME ..............  a apólice que o atendimento encontrou fica no caso até o fim; o ramo oficial decide
                        a tecla da URA, a seguradora e o portal; nenhum dado pessoal cru chega ao modelo
RISCO ................  7/8 — ALCANCE 3 (o segurado) · REVERSIBILIDADE 2 (dado/estado durável; o efeito
                        externo já existia e não é criado aqui) · FREQUÊNCIA 2 (todo atendimento)
SUPERFÍCIE ...........  2/3 — nodes.py (tool_node, _merge, _gravar_ficha_do_turno, dispatch, portal,
                        trava de anáfora), 1 módulo novo puro, attendance_ficha, o_fim_do_atendimento
PISO APLICADO ........  CRÍTICO por EFEITO (§3.2): altera o que vai para insurer_dispatch e portal_action
NÍVEL ................  CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 xhigh · juiz Opus 5.5 ‖ red team
                        Opus 5.5 (frescos, cegos um ao outro) + confirmação curta se houver blocker
                        🔴 DESVIO REGISTRADO: o protocolo v13 previa gerente/juiz/red team Fable 5.1. O
                        Founder trocou para Opus 5.5 na abertura desta SPEC → protocolo v13.2, D-PROTO-13.
                        ⛔ Nenhum gate foi reduzido por causa da troca.
O FIO ................  §1 · o TESTE DO FIO (F0) é a 1ª entrega e NASCEU VERMELHO (§4, B0.7)
PARALELISMO REAL .....  F1 (`policy_context.py` novo + unitários) ‖ F4a (corpus `casos.jsonl`) — arquivos
                        disjuntos. F2 → F3 em SÉRIE (as duas tocam `nodes.py`; um dono por vez)
UNIDADES .............  5 fatias (F0–F4) + canário do Founder (§8)
COESÃO ...............  construtor + escrita durável + troca dos leitores na MESMA SPEC: metade entregue
                        = duas verdades de apólice convivendo, pior que hoje
TIME .................  2 builders · juiz ‖ red team · ESCALAÇÃO se o red team achar PII no prompt/rastro
REFERÊNCIA ...........  interna: o caminho `core` que JÁ funciona (mesmo `data`, papel core → contexto
                        nasce — é a LINHA DE CONTROLE de F0) · `backend/tests/test_a_maquina_de_lavar_vai_
                        ate_o_fim.py` (atendimento ponta a ponta) · externa: §9
GATES ................  §6 (G1–G10)
O ELO ................  "o atendimento perde a apólice PORQUE a porta de identidade devolve None" —
                        📊 MEDIDO (B0.1 + B0.2 + B0.7, e a F6 da SPEC-116).
                        "os 68,9 % do atendimento são POR ISTO" — 📊 **REFUTADO** em B0.6: 0 de 13 casos.
                        Esta SPEC não promete mover aquele número.
FAIXA DE RELÓGIO .....  💭 4–8 h · teto 600 k de contexto no gerente
MIGRATION ............  📊 NENHUMA — B0.4 confirmou `public.conversations.ficha_atendimento` = `jsonb`
```

---

## §1 · O FIO — arquivo:função por elo

### 1.1 Hoje (quebrado) — todo elo com o comando que o mediu

```
① graph.py:473    InfocapPolicyLookupTool(company_id, agent_role=_agent_role)        papel "attendance"
② infocap_tool.py:425-426   _unmasked → self.agent_role in ("", "core") → False
③ infocap_connector.py:541  _canonical_customer_identity(unmasked=False)
      :565-578 → client_name_masked / client_document_masked  (⚠️ NÃO client_name / client_document)
      :552-562 → client_ref = {codigo, codfil}  ✅ SEM máscara nos DOIS papéis
      :888-940 _sanitize_policy → policy_number, insurer_key, product, valid_from/to, active_now,
               expired, cancelled, policy_locator_ref  ✅ nos DOIS papéis
④ nodes.py:2170   tool_node → infocap_policy_context = _safe_infocap_policy_context(data)
⑤ nodes.py:423-425  ✖ O ELO QUE QUEBRA
      document = str(data.get("client_document") or "").strip()
      name     = str(data.get("client_name") or "").strip()
      if not (document or name) or not policy_numbers: return None
⑥ nodes.py:2249   _merge_infocap_policy_context(prev=None, new=None) → None
⑦ consumidores MORTOS no atendimento:
      nodes.py:2024-2026  insurer_dispatch — `selected_policy_ramo` do sistema não sobrescreve o modelo
      nodes.py:1810       tem_infocap = False → a ficha nunca marca ORIGEM_SISTEMA_DE_GESTAO
      nodes.py:1830       qual_seguro_opcao nunca recebe origem "sistema_de_gestao"
      nodes.py:1996       selected_policy_number vazio → nova escolha / segunda pergunta
      nodes.py:1342+377   _policy_context_tool_args — sem contexto, a anáfora ("ela cobre?") não tem trava
      portal_action (nodes.py:2032) e request_human_agent — sem apólice do caso
⑧ nodes.py:1839-1844  a ficha durável recebe seguradora/ramo dos `tool_args` do MODELO
⑨ nodes.py:1470-1478  turno seguinte: ToolMessage comprimida → só o texto do modelo carrega a seguradora
```

### 1.2 Proposto — uma autoridade, uma escrita, todos leem o mesmo

```
① PolicyDataProvider / infocap_connector — INALTERADOS (o lado A fica fora, §3)
② NOVO, PURO: app/services/policy_context.py
      construir_policy_context(data, *, company_id, papel) -> dict | None
      · a porta passa a ser "há apólice E há cliente identificado" — identidade CRUA, MASCARADA ou
        `client_ref`. ⛔ Nunca "há CPF em claro".
      · devolve SÓ a lista branca (§2) · nunca nome, CPF, telefone, e-mail, endereço
      · apolice_do_contexto(contexto) / chave_da_apolice(apolice) — leitura única
③ nodes.py:412  _safe_infocap_policy_context passa a DELEGAR a ② (consolidação, não função paralela)
④ nodes.py:456  _merge_infocap_policy_context — mesma regra (SPEC-016.1 D6) sobre `cliente_ref` opaco
⑤ DURÁVEL: attendance_ficha ganha a chave "apolice" (bloco aditivo, com origem por campo)
      → conversations.ficha_atendimento (jsonb existente) · o state continua sendo o espelho
⑥ leitura única: attendance_ficha.apolice_do_caso(ficha, state) -> dict | None
      → insurer_dispatch · portal_action · request_human_agent/o_fim_do_atendimento
      → bloco_para_o_prompt (renderiza a lista branca) · _gravar_ficha_do_turno
⑦ a compressão da ToolMessage continua — o fato não depende mais dela
```

⛔ Nada em prompt como regra, nada em memória/RAG, nenhuma tabela nova, nenhum segundo "contexto de
apólice". As peças do CLAUDE.md §5 continuam únicas.

---

## §2 · O PolicyContext — o que carrega, e o que nunca carrega

| campo | origem | vai ao modelo? | por quê |
|---|---|---|---|
| `versao` | constante `1` | não | expand-first |
| `company_id` | estado | não | amarra ao tenant; o leitor recusa `company_id` diferente |
| `cliente_ref` | HMAC-SHA256(chave, `company_id:codfil:codigo`) — **D3** | não | identidade opaca e estável, isolada por tenant |
| `apolices[]` | `_sanitize_policy` | resumo | todas as candidatas do cliente |
| `· chave` | `locator_hash` (24 hex) **ou**, sem locator, `h:` + hash do número humano | não | chave técnica estável; o locator CRU não vai ao modelo |
| `· numapo` | `policy_number` | **sim — D2** | P0 de 25/06: número humano sempre visível |
| `· ramo` | `familia_de_ramo(product)` | sim | categoria, não dado pessoal (17/09) |
| `· seguradora` | `insurer_key` | sim | — |
| `· vigencia` | `valid_from` / `valid_to` | sim | — |
| `· vigente` / `expirada` / `cancelada` | `active_now`, `expired`, `cancelled` | sim | **vencida/cancelada nunca é selecionável** (G5) |
| `selecionada` | `chave` da escolhida | — | vale até o fim do caso ou até o segurado trocar |
| `origem_por_campo` | `sistema_de_gestao` · `cliente` · `corredor` | não | quem disse o quê — decide o empate |
| `evidencia` | `{fonte, consultado_em}` | não | auditoria e "sem consulta repetida" (G6) |

⛔ **Nunca:** nome, CPF/CNPJ (nem mascarado — a máscara fica no DTO por papel, onde já está), telefone,
e-mail, endereço, placa.

### 🔴 A máscara FICA — e a decisão tem nota

O Founder autorizou remover a máscara se ela atrapalhasse. **Ela não atrapalha, e removê-la seria o
conserto errado.** Nota 0–100:

| opção | nota | por quê |
|---|---|---|
| **consertar a PORTA e manter a máscara** | **95** | o `data` mascarado já traz TODO o fato que a SPEC precisa (📊 B0.3/B0.5: número, seguradora, ramo, vigência, status, locator e `client_ref` saem nos dois papéis). O que falta é só a identidade — e para "é o mesmo cliente" o `client_ref` opaco basta e é melhor |
| dar identidade crua ao papel `attendance` | 25 | reabre LGPD/OWASP LLM02 num caminho que fala com o SEGURADO pelo WhatsApp, desfaz a SPEC-017 P3 e a SPEC-063 Bloco A, **e não é necessário** |
| um terceiro papel "semi-mascarado" | 15 | peça nova ao lado da existente (CLAUDE.md §5) |

📊 A medição que fecha a decisão: `test_a_fronteira_mascara_a_identidade_e_preserva_a_apolice` — as duas
funções reais do conector, o papel mascarado, e a apólice inteira presente.

---

## §3 · Escopo — A não é B

| | **A · ADQUIRIR** o fato correto | **B · TRANSPORTAR** o fato já adquirido |
|---|---|---|
| onde mora | `PolicyDataProvider`, `infocap_connector`, `policy_facts`, Docling | `tool_node` → `state.infocap_policy_context` → ficha → consumidores |
| estado | funciona para o que esta SPEC precisa | **quebrado** — é o defeito desta SPEC |
| nesta SPEC | ⛔ fora | ✅ todo o escopo |

**Fora, de propósito:** extração de PDF/Docling/Policy Facts · a base de planos · troca de modelo do
atendimento · o laço de consultas forçadas do Chat Principal (item 9 da SPEC-116 — esta SPEC não o
conserta, e o G6 não pode piorá-lo).

**Autorização expressa do Founder (26/09):** um defeito pequeno fora do núcleo que **mude o que o
segurado recebe** pode ser consertado aqui se couber em ≤ 30 min, ≤ 2 arquivos, sem subsistema novo,
sem migration e sem mudança ampla de contrato — com evidência, teste vermelho, conserto, teste verde.
Fora disso: `PENDENCIAS.md`, com causa, caso reproduzível, gravidade e o que destrava.

---

## §4 · BLOCO 0 — o que foi MEDIDO em 26/09/2026 (HEAD `79c9e80`)

| # | verificação | resultado 📊 | comando |
|---|---|---|---|
| **B0.0** | a árvore está em dia | `0` atrás, `0` à frente de `origin/main`; HEAD `79c9e80` | `git rev-list --count HEAD..origin/main` |
| **B0.1** | a porta continua exigindo identidade crua | **SIM** — `nodes.py:423-425`, `if not (document or name) … return None` | `grep -n "_safe_infocap_policy_context" backend/app/agents/nodes.py` |
| **B0.2** | o papel do atendimento não é `core` | **SIM** — `infocap_tool.py:425-426`; `graph.py:473` passa `agent_role` | `grep -n "_unmasked\|agent_role=" …` |
| **B0.3** | o `client_ref` sai nos dois papéis | **SIM** — `infocap_connector.py:552-562`, fora do `if unmasked` | `sed -n 541,578p …` |
| **B0.4** | a coluna durável é `jsonb` | **SIM** — `jsonb`, `is_nullable=NO` | MCP `execute_sql`, SELECT em `information_schema.columns` |
| **B0.5** | todo leitor/escritor do contexto | 12 pontos em `nodes.py`, 1 em `state.py`, 3 na bancada; **escritor único**: `tool_node:2251` | `grep -rn "infocap_policy_context" backend/app --include=*.py` |
| **B0.5b** | testes que exercitam a regra do ramo | **ZERO** — `selected_policy_ramo` não aparece em `backend/tests` | `grep -rn "selected_policy_ramo" backend/tests` |
| **B0.6** | 🔴 **quantos dos 68,9 % são deste defeito** | **NENHUM** — ver abaixo | `python` sobre `RESULTADOS/atendimento_N1_03af4327….json` |
| **B0.7** | o teste do fio nasce vermelho | **SIM** — 📊 `4 failed, 2 passed`; as 2 verdes são as linhas de controle (a fronteira mascarada e o papel `core`) | `pytest tests/test_o_atendimento_guarda_a_apolice.py` |

### 🔴 B0.6 — a medição que REFUTA metade da premissa herdada

📊 26/09/2026 · grupo `03af4327-80c5-4ec6-b21b-624299cd8542` · braço de produção
`anthropic:claude-sonnet-5` · 30 casos, 90 tentativas, pass@1 = 68,9 % · **13 casos** com ao menos uma
reprovação. Classificando cada um pelo veredito que reprovou:

| grupo | casos | quais |
|---|---|---|
| **(a) apólice encontrada e não transportada** | **0** | — |
| (b) não chamou a ferramenta esperada, ou chamou outra | **9** | `cpf-para-brisa`, `humano-cancelar`, `humano-cade-guincho`, `humano-demora-vidro`, `humano-bati-carro`, `portal-lanterna`, `portal-parabrisa-reparo`, `portal-farol`, `risco-alagamento` |
| (c) outro — não pediu o CPF no texto | **4** | `sem-id-mecanico`, `sem-id-sinistro`, `sem-id-eletricista`, `sem-id-guincho-motor` |

🔴 **Leitura honesta:** o N1 é de **turno único**. Por definição não há apólice anterior a transportar, e
por isso **esta SPEC não promete mover os 68,9 %**. Quem quiser afirmar o contrário precisa de outra
medição, no N2.

📊 **E o N2 confirma o defeito de forma direta:** `contexto_da_apolice_por_turno` = `[[], [], …]` em
**10 de 10** trajetórias N2 do atendimento, em **todos** os braços — incluindo `duble:perfeito`, que
acerta 30/30. Um modelo perfeito não salva um fato que o produto não guarda. (Grupo
`a2fb9be0-d25c-4789-9846-38d7f76ad300`.)

⚠️ **Achado da bancada, fora do escopo → pendência:** em `atd-n1-humano-bati-carro` o rastro registra
`tool_calls: ['request_human_agent']` e o avaliador diz *"não chamou `request_human_agent` — respondeu
só com texto"*. Um dos dois está errado, e é **instrumento**, não produto. Vai para `PENDENCIAS.md`.

---

## §5 · As fatias

| fatia | entrega | arquivos | depende |
|---|---|---|---|
| **F0** | **teste do fio** — `tool_node` real, dublê só na borda, `data` montado pelas funções REAIS do conector · nasce VERMELHO | `backend/tests/test_o_atendimento_guarda_a_apolice.py` (novo) | — |
| **F1** | `policy_context.py` puro + unitários (G1, G2, G5, G9 e as mutações) | `backend/app/services/policy_context.py` (novo) + teste novo | F0 |
| **F2** | `tool_node`/`_merge` delegam a F1; escrita durável da chave `apolice` na ficha | `nodes.py`, `attendance_ficha.py` | F1 |
| **F3** | leitores trocados (dispatch, portal, handoff, bloco do prompt, trava de anáfora, `_gravar_ficha_do_turno`) | `nodes.py`, `attendance_ficha.py`, `o_fim_do_atendimento.py` | F2 (série) |
| **F4** | corpus N2 novo + rodada da bancada com dublês + triagem | `casos.jsonl`, `bancada_gerar_corpus.py` | F1 (F4a ‖), F3 |

---

## §6 · Os GATES

| # | gate | como se mede |
|---|---|---|
| G1 | o contexto nasce no core **E** no atendimento | o MESMO `data` nos dois papéis pelo `tool_node` real → contexto não-nulo, `ramo` igual · **controle**: a função antiga com o `data` mascarado → `None` |
| G2 | PII não vaza | varredura recursiva do contexto, do bloco do prompt e da ficha por CPF/nome/telefone/e-mail + os valores do caso · **mutação**: injetar `client_name` no construtor → guarda VERMELHO |
| G3 | ramo oficial vence o palpite | apólice `resi`, modelo escreve `auto` → `insurer_dispatch` recebe `resi`; divergência logada |
| G4 | seguradora e apólice persistem | 6+ turnos: a apólice do caso é a mesma no dispatch, no portal e no handoff |
| G5 | duas vigentes desambiguadas; vencida nunca | Auto+Resi → serviço de casa escolhe `resi` sem perguntar · 2 `resi` vigentes → UMA pergunta, escolha persiste · vencida/cancelada nunca `selecionada`, nem sendo a mais recente |
| G6 | sem consulta repetida | contagem de `infocap_policy_lookup` por trajetória ≤ 1 + trocas explícitas; o Chat Principal não piora |
| G7 | compressão não apaga estado | `ToolMessage` comprimida e texto do modelo sem a seguradora → decisão igual à do turno 1 |
| G8 | retomada | 429/timeout depois da tool · processo novo · falha de gravação → a ficha devolve a apólice; nenhum efeito duplicado |
| G9 | dois tenants | mesmo `codfil:codigo` em A e B → `cliente_ref` diferentes; leitor recusa `company_id` alheio |
| G10 | sem efeito duplicado | mesma mensagem 2× → `dup = 0` |

🔴 Cada guarda novo prova que **consegue** ficar vermelho com o defeito de hoje reintroduzido
(CLAUDE.md §9.3/§9.5). Gate sem ambiente ou sem chamada real recebe **"NÃO PROVADO"**, nunca
"verde por inferência".

---

## §7 · Riscos

| risco | consequência | mitigação |
|---|---|---|
| o ramo oficial passa a vencer e a apólice selecionada está errada | tecla errada na URA, seguradora errada — silencioso | G5 (vencida nunca, desambiguação), divergência modelo×sistema logada |
| PII escapa pelo campo durável novo | incidente LGPD (o painel lê a ficha) | lista branca + G2 com mutação + red team focado em PII |
| caso antigo contamina caso novo do mesmo telefone | apólice de outro sinistro | escopo por `assunto_id`; assunto novo não herda `apolice` |
| duas verdades na transição | leitor lê a antiga | COESÃO: F2+F3 na mesma SPEC; guarda de escritor único |
| a gravação da ficha falha (hoje engole o erro) | perde a memória do turno | o leitor cai para o `state`; G8 mede |

---

## §8 · Canário do Founder

Depois da entrega, uma conversa de teste **por corretora** (dois tenants), em número de teste, com
Auto+Residencial: conferir no `ficha_atendimento` que a chave `apolice` nasceu e que o acionamento de
teste levou o ramo oficial. Comandos prontos no relatório (CLAUDE.md §12.2).
⛔ Nenhum teste automatizado envia mensagem a segurado, seguradora ou grupo real.

---

## §9 · O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (protocolo §7.3)

**R1 · LangGraph — Persistence**
- URL: https://langchain-ai.github.io/langgraph/concepts/persistence/
- O que faz: o checkpointer salva o **estado do grafo** por thread a cada passo; a retomada lê o estado, não a conversa.
- MODELAMOS: o fato que decide mora em **campo tipado do estado**, não em mensagem.
- REJEITAMOS: o checkpoint como única verdade — o `MemorySaver` de fallback (`graph.py:50`) some no reinício; a verdade durável é o Supabase (CLAUDE.md §6).
- COMO O JUIZ INSPECIONA: G8 com processo novo e checkpointer em memória — a apólice volta pela ficha.

**R2 · LangGraph — Memory (estado × mensagens, trim/summarize)**
- URL: https://langchain-ai.github.io/langgraph/concepts/memory/
- O que faz: separa o histórico de mensagens (que se apara ou resume) do estado que persiste.
- MODELAMOS: comprimir `ToolMessage` é legítimo **desde que** o fato já tenha sido promovido ao estado antes.
- REJEITAMOS: "resumir para o modelo lembrar" — resumo é texto do modelo; o fato vem do sistema de gestão.
- COMO O JUIZ INSPECIONA: G7 — placeholder no lugar da `ToolMessage` e decisão idêntica.

**R3 · Google ADK — Session State**
- URL: https://google.github.io/adk-docs/sessions/state/
- O que faz: `session.state` chave-valor por sessão, com escopos por prefixo e escrita por evento, não mutação solta.
- MODELAMOS: **uma** escrita e **uma** leitura (`apolice_do_caso`); escopo = caso (`company_id` + `session_id`).
- REJEITAMOS: o prefixo `user:` (estado entre sessões) — a apólice é do caso; outro sinistro reconsulta.
- COMO O JUIZ INSPECIONA: `grep -n "\[\"apolice\"\] *=" backend/app` → um único escritor.

**R4 · OWASP Top 10 for LLM Applications 2025 — LLM02 Sensitive Information Disclosure**
- URL: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/
- O que faz: recomenda minimizar e sanitizar o que entra no contexto do modelo; o modelo não é fronteira de segurança.
- MODELAMOS: lista branca de campos (§2) aplicada **antes** do modelo; a máscara continua no DTO por papel.
- REJEITAMOS: "o prompt manda não repetir o CPF" — regra não é frase de prompt (CLAUDE.md §6).
- COMO O JUIZ INSPECIONA: G2 com a mutação (campo cru injetado → guarda vermelho).

**R5 · ENISA — Pseudonymisation techniques and best practices** (+ LGPD, Lei 13.709/2018, art. 13 §4)
- URL: https://www.enisa.europa.eu/publications/pseudonymisation-techniques-and-best-practices · https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2018/lei/l13709.htm
- O que faz: pseudônimo por função com chave secreta (HMAC) mantida separada; hash **sem** chave de identificador de baixa entropia é reversível por força bruta.
- MODELAMOS: `cliente_ref` = HMAC-SHA256 com chave de plataforma + `company_id` no material (D3).
- REJEITAMOS: `sha256(codigo)` sem chave — `codigo` é sequencial e curto (📊 `"7788"` no corpus).
- COMO O JUIZ INSPECIONA: G9 + leitura do construtor: a chave não está em código, log nem artifact.

---

## §10 · As decisões (nota 0–100)

| # | decisão | opções e nota | **decidido** |
|---|---|---|---|
| **D1** | onde mora a apólice durável | `ficha_atendimento` (jsonb existente) + espelho no checkpoint **90** · só checkpoint **50** · tabela nova **20** | a 1ª |
| **D2** | `numapo` visível ao modelo | manter visível (P0 de 25/06) **80** · só final mascarado **60** | manter |
| **D3** | como se faz o `cliente_ref` | HMAC com chave de plataforma + `company_id` no material **85** · HMAC com chave por tenant no Vault **70** (exige chave nova por corretora; não há porta pronta hoje) · sha256 sem chave **25** | a 1ª — o isolamento por tenant vem do `company_id` **dentro** do material, e G9 o prova |
| **D4** | fatia de alívio antes do todo | só o conserto completo **(escolha expressa do Founder)** · hotfix de 1 linha antes **descartado** | conserto completo |
| **D5** | o construtor serve os dois papéis | um construtor para core e atendimento **90** · só atendimento **35** | um só |
| **D6** | quando reconsultar | só em troca explícita de cliente/apólice **75** · a cada N turnos **40** | a 1ª |
| **D7** | a máscara de identidade sai? | manter e consertar a porta **95** · identidade crua no atendimento **25** · papel novo **15** | manter (§2) |

---

## §11 · Entrega

Uma branch (`spec/117-apolice-persistente`), um relatório
(`docs/canon/reports/SPEC-117-EXECUTION-REPORT.md`) com EXECUTION CARD, FATO/INFERÊNCIA/RECOMENDAÇÃO,
saída real dos testes e da bancada, declaração de que nenhum motor paralelo foi criado, pendências em
`PENDENCIAS.md`, e **a saída do `git push` colada** — entregar é empurrar (CLAUDE.md §2).
