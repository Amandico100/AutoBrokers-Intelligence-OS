# SPEC-117 · O atendimento nunca perde a apólice que encontrou

> **STATUS: PROPOSTA — NÃO EXECUTADA** · 24/09/2026 · redigida sobre `b976aac` (branch `spec/116-onda-a-conclusao`)
> **Origem:** SPEC-116, bancada F6 — `SPEC-116-EVIDENCIAS/06-resultado-da-bancada.md` §1 ("O ELO, medido") ·
> `reports/SPEC-116-EXECUTION-REPORT.md` linha 71 (atendimento N1 68,9 %)
> **Marcha proposta:** CRÍTICO · rito do protocolo v13 · 💭 faixa 6–10 h de relógio
>
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1
> Toda afirmação sobre código abaixo traz o comando que a produziu (protocolo §0.4). O executor **reconfirma no BLOCO 0**.

---

## §0 · O resultado, o motivo, e o card

### 0.1 O resultado, em uma frase

Quando o atendimento do WhatsApp encontra a apólice do segurado no sistema de gestão, **ela fica guardada no caso até
o fim** — ramo, seguradora, vigência e número — e toda peça que decide alguma coisa (qual tecla da URA, qual portal,
qual seguradora acionar, quem recebe o caso no handoff) lê **essa** apólice, e não o que o modelo lembrou de escrever.

### 0.2 O motivo — o contexto da apólice **nunca nasce** no atendimento

**FATO 1 — a identidade chega mascarada no atendimento, e a função que monta o contexto exige identidade crua.**

```
$ grep -n "def _unmasked" -A2 backend/app/agents/tools/infocap_tool.py
425:    def _unmasked(self) -> bool:
426:        return self.agent_role in ("", "core")
$ sed -n 566,578p backend/app/api/infocap_connector.py      # _canonical_customer_identity
    if unmasked: out["client_name"] = name ; out["client_document"] = doc ...
    else:        out["client_name_masked"] = _mask_name(name) ; out["client_document_masked"] = _mask_tail(doc)
$ sed -n 423,426p backend/app/agents/nodes.py               # _safe_infocap_policy_context
    document = str(data.get("client_document") or "").strip()
    name = str(data.get("client_name") or "").strip()
    if not (document or name) or not policy_numbers:
        return None
```

No papel `attendance`, `data` só tem `client_*_masked` → `document` e `name` vazios → **`None`**. 📊 Medido na F6 da
SPEC-116 (06-resultado §1, linha 42): *"chamada direta com o `data` mascarado → `None`; com o do core → dict com
`selected_policy_ramo='auto'`"*. ⚠️ O resto do `data` **está lá**: `_sanitize_policy` (`infocap_connector.py:888-940`)
devolve `policy_number`, `insurer_key`, `product`, `valid_from/valid_to`, `active_now`, `expired`, `policy_locator_ref`
também no papel mascarado; e `client_ref` (`codigo`/`codfil`) sai **sem máscara** nos dois papéis (`:559-564`).
O que mata o contexto é só a porta de identidade.

**FATO 2 — as três peças nasceram em épocas diferentes, e a última regra nasceu morta para o atendimento.**

```
$ git log -S "client_name_masked" --format="%h %ad %s" --date=short -- backend/app | tail -1
d8da12a 2026-06-24 feat(infocap): R1B canonical policy read adapter and verified evidence contract
$ git log -S "_safe_infocap_policy_context" --format="%h %ad %s" --date=short -- backend/app | tail -1
c84da57 2026-06-25 fix(infocap): P0 enforce human policy number identity integrity
$ git log -S "def _unmasked" --format="%h %ad %s" --date=short -- backend/app/agents/tools/infocap_tool.py | tail -1
b25d1cc 2026-07-03 feat(spec017): ... role-masked policy exposure for attendance
$ git log -S "selected_policy_ramo" --format="%h %ad %s" --date=short -- backend/app | tail -1
ff74680 2026-09-17 feat(extra-001.4): fatia 2 - ... tecla do ramo vem da apolice
```

- 25/06: a função foi escrita quando a tool do agente **sempre** pedia dados completos → a identidade crua existia.
- 03/07 (SPEC-017 P3): o atendimento passou a receber a identidade mascarada — **correto** —, mas ninguém mudou a porta
  da função. Desde então o contexto da apólice **não nasce no atendimento**.
- 17/09 (EXTRA-001.4, D-PILOTO-11): a decisão do Founder *"o ramo da apólice vence o do modelo"* foi pendurada nesse
  contexto (`nodes.py:452`, `:2024`, `:1830`) — **uma regra do atendimento plugada numa fonte que o atendimento não
  alimenta**. INFERÊNCIA: ela só dispara no Chat Principal (papel core), onde não há `insurer_dispatch` real.

```
$ grep -rln "selected_policy_ramo" backend/tests --include=*.py        → (vazio)
$ grep -c "client_name_masked" backend/tests/test_spec016_*.py backend/tests/test_infocap_policy_output_guard.py → 0 0 0 0
```
📊 **Zero** testes exercitam `_safe_infocap_policy_context` com dado mascarado, e **zero** afirmam `selected_policy_ramo`.
É o CLAUDE.md §9.4 de novo: a regra foi provada com o dado do papel errado.

**FATO 3 — o que sobra para transportar a apólice é o texto do modelo, e ele é comprimido.**

```
$ sed -n 1470,1478p backend/app/agents/nodes.py
    # Comprime tools antigas
    ToolMessage(content="[🔍 RAG: Conteúdo bruto removido para otimização. As informações relevantes já constam na resposta ...
$ sed -n 1839,1844p backend/app/agents/nodes.py      # _gravar_ficha_do_turno
    for origem, destino in (("insurer_key", "seguradora"), ("line_kind", "ramo"), ...):
        if tool_args.get(origem): novidades[destino] = tool_args[origem]
```
- A ToolMessage da consulta vira placeholder no turno seguinte. 📊 F6 (06-resultado linha 42): com `POLICY_INTELLIGENCE_V2`
  desligada, *"'Allianz' some da entrada do modelo no turno 2"*; com ela ligada, a seguradora sobrevive **só porque o
  modelo a repetiu na resposta**.
- A ficha durável (`conversations.ficha_atendimento`, `attendance_ficha.gravar`) recebe `seguradora`/`ramo` dos
  **argumentos que o modelo escreveu** na tool — não da apólice. A única escrita durável da apólice é autoria do modelo.

### 0.3 O que os números dizem — e o que ainda **não** dizem (protocolo §0.3, O ELO)

| | afirmação | estado |
|---|---|---|
| 📊 FATO | atendimento N1, `claude-sonnet-5` (o de produção): **pass@1 68,9 %**, crít^k 50 % | `SPEC-116-EXECUTION-REPORT.md:71` |
| 📊 FATO | `openai:gpt-6-astra:high` nos 26 críticos do N1: **pass@1 68,4 %**, crít^k 83,3 % (21 tentativas infra) | 06-resultado, grupo `89661ceb…` |
| 📊 FATO | no atendimento o contexto de apólice por turno é `[[],[],[]]` também com a forma real das tools | 06-resultado linhas 37-42 |
| INFERÊNCIA | o teto baixo não é inteligência do modelo: um modelo muito maior erra os mesmos críticos, e o produto não entrega a ele o fato que decide | — |
| ⚠️ A CONFIRMAR | **quantos** dos casos reprovados caem por ESTE defeito. O N1 é de turno único e muitas reprovações são "não chamou a tool" (06-resultado linha 275) — elas **não** são explicadas por transporte de contexto. A SPEC mede isso no BLOCO 0 (B0.6) e **não** promete subir os 68,9 % por um número fixo |

### 0.4 A separação que esta SPEC faz — A não é B

| | **A · ADQUIRIR** os fatos corretos da apólice | **B · TRANSPORTAR** o fato já adquirido pelo atendimento |
|---|---|---|
| o que é | ler o sistema de gestão, o PDF oficial (Docling), extrair coberturas/assistências → Policy Facts | a apólice encontrada no turno 1 continuar sendo a apólice do turno 7, do dispatch, do portal e do handoff |
| onde mora | `PolicyDataProvider` (`policy_data_provider.py:1844`), `infocap_connector`, `policy_facts.extract_policy_facts` | `nodes.tool_node` → `state.infocap_policy_context` → `attendance_ficha` → consumidores |
| estado | funciona para o que esta SPEC precisa (ramo, seguradora, vigência, número já vêm) | **quebrado** — é o defeito desta SPEC |
| nesta SPEC | ⛔ **fora** — nenhuma mudança de extração, PDF, Docling ou base de planos | ✅ **todo o escopo** |

Qualquer defeito de A encontrado no caminho vai para `PENDENCIAS.md`, não para esta SPEC.

### 0.5 🔴 EXECUTION CARD (preliminar — o executor reconfirma no BLOCO 0)

```
OUTCOME ..............  a apólice que o atendimento encontrou fica no caso até o fim; ramo oficial decide a tecla,
                        a seguradora e o portal; nenhum dado pessoal cru chega ao modelo
RISCO ................  6/8 — decide QUAL seguradora é acionada e QUAL ramo é teclado (efeito material na vida do
                        segurado) + fronteira de PII (LGPD)
SUPERFÍCIE ...........  2/3 — nodes.py (tool_node, agent_node, _gravar_ficha_do_turno), 1 módulo novo puro,
                        attendance_ficha (fundir/bloco), leitores (dispatch/portal/handoff/compositor)
PISO APLICADO ........  CRÍTICO por EFEITO (§3.2): altera o que vai para insurer_dispatch/portal_action
NÍVEL ................  CRÍTICO · gerente Fable · builders Opus xhigh · juiz Fable ‖ red team Fable (PII + cross-tenant)
O FIO ................  §1 abaixo · o TESTE DO FIO (F0) é a 1ª entrega e nasce VERMELHO
PARALELISMO REAL .....  F1 (módulo novo + testes) ‖ F4a (casos do corpus) — arquivos disjuntos. F2 → F3 em SÉRIE
                        (ambas tocam nodes.py)
UNIDADES .............  5 fatias (F0–F4) + canário do Founder (§7)
COESÃO ...............  construtor + escrita durável + troca dos leitores ficam na MESMA SPEC: metade entregue
                        = duas verdades de apólice convivendo (pior que hoje)
TIME .................  2 builders · juiz ‖ red team · ESCALAÇÃO se o red team achar PII no prompt ou no rastro
REFERÊNCIA ...........  interna: a própria F6 (bancada.py --papel atendimento --nivel N2, grupo a2fb9be0…) e
                        o caminho core que JÁ funciona (mesmo data, papel core → selected_policy_ramo='auto');
                        externa: §8
GATES ................  §5 (G1–G10)
O ELO ................  título "o atendimento perde a apólice PORQUE a porta de identidade devolve None" —
                        medido (FATO 1 + F6). "68,9 % PORQUE isto" — NÃO medido: B0.6
FAIXA DE RELÓGIO .....  💭 6–10 h · teto 600 k de contexto no gerente
```

---

## §1 · O FIO — arquivo:função por elo

### 1.1 Hoje (quebrado)

```
① graph.py:473                      InfocapPolicyLookupTool(company_id, agent_role=_agent_role)   papel "attendance"
② infocap_tool.py:425  _unmasked     → False
③ infocap_connector.py:545  _canonical_customer_identity(unmasked=False)
                                      → client_name_masked / client_document_masked  (+ client_ref, sem máscara)
   infocap_connector.py:888  _sanitize_policy → policy_number, insurer_key, product, vigência, status, locator_ref ✅
④ nodes.py:2170  tool_node            infocap_policy_context = _safe_infocap_policy_context(data)
⑤ nodes.py:425   _safe_infocap_policy_context   if not (document or name) → return None      ✖ O ELO QUE QUEBRA
⑥ nodes.py:2249  _merge_infocap_policy_context(prev=None, new=None) → None → state.infocap_policy_context = None
⑦ consumidores mortos no atendimento:
     nodes.py:2024  insurer_dispatch     ramo_da_apolice do sistema NÃO sobrescreve o do modelo
     nodes.py:1830  _gravar_ficha_do_turno  qual_seguro_opcao nunca recebe origem "sistema_de_gestao"
     nodes.py:1996  infocap lookup       selected_policy_number da ficha = vazio → nova escolha/nova pergunta
     nodes.py:1342  _policy_context_tool_args   sem contexto → anáfora ("ela cobre…?") sem trava
     nodes.py:1810  tem_infocap = False
⑧ nodes.py:1839  ficha durável recebe seguradora/ramo dos tool_args do MODELO
⑨ nodes.py:1472  turno seguinte: ToolMessage comprimida → só o texto do modelo carrega a seguradora
```

### 1.2 Proposto (uma autoridade, uma escrita, todos leem o mesmo)

```
① PolicyDataProvider (policy_data_provider.py:1844, porta existente) — INALTERADO (A fica fora)
② NOVO, PURO: app/services/policy_context.py  construir_policy_context(data, *, company_id, papel) -> PolicyContext|None
     · aceita identidade crua OU mascarada OU client_ref — a porta é "há apólice e há cliente identificado",
       não "há CPF em claro"
     · devolve SÓ campos da lista branca (§2); nunca nome/CPF/telefone/e-mail
③ nodes.py tool_node:2170   _safe_infocap_policy_context passa a DELEGAR a ②  (consolidação — sem função paralela;
                              o nome antigo vira adaptador fino ou é removido; decisão do builder, registrada)
④ nodes.py:2249  _merge_infocap_policy_context  — mesma regra de hoje (SPEC-016.1 D6), trocando "mesmo cliente" por
                              cliente_ref opaco em vez de document/name
⑤ DURÁVEL (D1): attendance_ficha.fundir/gravar ganha a chave "apolice" com o PolicyContext selecionado
                              → conversations.ficha_atendimento (coluna JSONB existente — A CONFIRMAR no B0.4)
                              · state.infocap_policy_context continua sendo o espelho do checkpoint
⑥ leitura única: attendance_ficha.apolice_do_caso(ficha, state) -> PolicyContext|None
     · insurer_dispatch (nodes.py:2024)   ramo_da_apolice + insurer_key DO CONTEXTO vencem o modelo
     · portal_action / corredor de vidros  seguradora e apólice do contexto
     · request_human_agent / o_fim_do_atendimento  o handoff leva a apólice do caso
     · compositor / bloco_para_o_prompt   renderiza os campos da lista branca (já é o bloco da ficha — não é regra nova de prompt)
     · _gravar_ficha_do_turno:1839        seguradora/ramo do MODELO só entram se NÃO houver apólice do sistema;
                                          havendo, divergência vira log + a do sistema vence (origem por campo)
⑦ nodes.py:1472  a compressão da ToolMessage continua — o fato não depende mais dela
```

⛔ Nada em prompt como regra, nada em memória/RAG, nenhuma tabela nova, nenhum segundo "contexto de apólice".
As peças do CLAUDE.md §5 continuam únicas.

---

## §2 · O PolicyContext — o que carrega, e o que nunca carrega

| campo | origem | visível ao modelo? | por quê |
|---|---|---|---|
| `versao` | constante `1` | não | evoluir sem quebrar leitor (expand-first) |
| `company_id` | estado | não | amarra o contexto ao tenant; leitor recusa se diferente |
| `cliente_ref` | HMAC(`company_id`, `codfil:codigo`) — **D3** | não | identidade **opaca e estável** para "mesmo cliente"; não reversível sem a chave |
| `apolices[]` | `_sanitize_policy` | resumo | todas as candidatas do cliente, cada uma com os campos abaixo |
| `· locator_hash` | `policy_facts._locator_hash` (existe) | não | chave técnica estável; o `policy_locator_ref` cru **não** vai ao modelo (regra P0 de hoje) |
| `· numapo` | `policy_number` | **sim — D2** | P0 (25/06) decidiu número humano sempre visível; esta SPEC não reabre sem o Founder |
| `· ramo` | `familia_de_ramo(product)` | sim | categoria, não dado pessoal (decisão de 17/09) |
| `· seguradora` | `insurer_key` → nome canônico | sim | — |
| `· produto` | `product` | não (só a família) | o produto cru carrega abreviação interna da fonte (SPEC-016.1 D10) |
| `· vigencia` | `valid_from/valid_to` | sim (datas) | — |
| `· status` | `policy_status`, `active_now`, `expired`, `cancelled` | sim | **vencida/cancelada nunca é selecionável** (G5) |
| `selecionada` | `locator_hash` da escolhida | — | a escolha vale até o fim do caso ou até o segurado trocar |
| `origem_por_campo` | `sistema_de_gestao` · `cliente` · `corredor` (`attendance_ficha.ORIGEM_*`, existem) | não | quem disse o quê — o que decide empate |
| `evidencia` | `{fonte, consultado_em, request_id}` | não | auditoria e "sem consulta repetida" (G6) |

⛔ **Nunca** no PolicyContext: nome, CPF/CNPJ (nem mascarado — a máscara fica no DTO por papel, onde já está),
telefone, e-mail, endereço, placa (placa segue pela ficha do AUTO, fluxo existente, fora do escopo).
🔴 **A máscara continua.** O que muda é que a máscara deixa de apagar o contexto.

---

## §3 · Escopo

**Dentro:** construtor puro · porta de identidade · escrita durável na ficha · troca dos leitores (dispatch, portal,
handoff, compositor, bloco da ficha, trava de anáfora) · os mesmos no papel core (mesmo construtor — D5) ·
testes, corpus e bancada.

**Fora, de propósito:** extração de PDF/Docling/Policy Facts (lado A) · o laço de 7 consultas forçadas do Chat
Principal (06-resultado linha 44 — já é item 9 da SPEC-116; esta SPEC **não** o conserta, mas o G6 não pode piorá-lo)
· troca de modelo do atendimento · base de planos.

---

## §4 · BLOCO 0 — converter medindo

```
B0.1  a porta continua a mesma?     sed -n 423,426p backend/app/agents/nodes.py
B0.2  o papel do atendimento é "attendance"?   grep -n "_CLIENT_FACING_ROLES\|agent_role=" backend/app/agents/tools/infocap_tool.py backend/app/agents/graph.py
B0.3  o client_ref sai nos dois papéis?  sed -n 545,565p backend/app/api/infocap_connector.py
B0.4  a coluna durável existe e é JSONB?  MCP execute_sql (SÓ SELECT):
        select column_name, data_type from information_schema.columns
        where table_name='conversations' and column_name='ficha_atendimento';
B0.5  todo leitor de infocap_policy_context:  grep -rn "infocap_policy_context" backend/app --include=*.py
B0.6  O ELO dos 68,9 %: reler o grupo 03af4327… por caso (python scripts/bancada.py --relatorio 03af4327-…)
        e classificar cada reprovação crítica em  (a) transporte de apólice · (b) não chamou tool · (c) outro.
        Só (a) é desta SPEC. O número vai para o relatório com o comando.
B0.7  o teste do fio (F0) nasce VERMELHO no HEAD — se nascer verde, a premissa caiu: PARE e registre.
```

---

## §5 · Os GATES — medidos, com controle

| # | gate | como se mede | nível |
|---|---|---|---|
| G1 | **o contexto nasce no core E no atendimento** | unitário: o MESMO `data` nos dois papéis → PolicyContext não-nulo, `ramo` igual · **linha de controle**: o `data` de hoje pela função antiga → `None` no atendimento | unit |
| G2 | **PII não vaza** | varredura do PolicyContext, do prompt montado, das ToolMessages, do `rastro` da bancada e do log por regex de CPF/CNPJ/telefone/e-mail + os valores crus do caso de teste; **mutação**: inserir `client_name` no construtor → o guarda fica VERMELHO | unit + N2 |
| G3 | **ramo oficial vence** | modelo escreve `ramo_da_apolice=auto` num caso cuja apólice é `resi` → `insurer_dispatch` recebe `resi`; divergência logada | N1 + N2 |
| G4 | **seguradora e apólice persistem** | trajetória de 6+ turnos: `apolice_do_caso` idêntica em todo turno, no dispatch, no portal e no handoff | N2 |
| G5 | **duas vigentes desambiguadas; vencida nunca** | Auto+Residencial: serviço de casa escolhe `resi` sem perguntar; duas `resi` vigentes → UMA pergunta na conversa inteira, resposta persiste; vencida/cancelada nunca `selecionada` | N1 + N2 |
| G6 | **sem consulta repetida** | contagem de `infocap_policy_lookup` por trajetória ≤ 1 + trocas explícitas de cliente/apólice; Chat Principal **não piora** o item 9 da SPEC-116 | N2 |
| G7 | **compressão não apaga estado** | turno N com a ToolMessage já comprimida (placeholder) e o texto do modelo **sem** a seguradora → decisão igual à do turno 1 | N2 |
| G8 | **retomada** | timeout do provedor / 429 depois da tool / reinício do processo (novo `MemorySaver`) → a ficha durável devolve a apólice; nenhum efeito duplicado | N2 + injeção de falha |
| G9 | **dois tenants** | mesmo `codigo`/`codfil` em A e B → `cliente_ref` diferentes; leitor recusa contexto de outro `company_id`; teste com dois tenants reais (CLAUDE.md §7) | unit + N2 |
| G10 | **sem efeito duplicado** | `insurer_dispatch`/`portal_action` com a mesma chave de idempotência de hoje: 0 duplicados na bancada (`dup` = 0) | N2 |

🔴 Cada guarda novo prova que **consegue** ficar vermelho (CLAUDE.md §9.3/§9.5): o defeito de hoje reintroduzido
(porta que exige nome/CPF crus) tem de reprovar G1, G3, G4 e G7.

**Onde se mede:** N1 (turno único, corpus existente + novos) · **N2 multi-turno** (o nível que expõe o transporte) ·
**casos reais mascarados** (conversas do acervo, identidade trocada por sintética — nada de dado real no corpus) ·
**injeção de falha** (`falhas_injetadas` já existe no formato do corpus) · **canário** posterior (§7).

---

## §6 · Cenários obrigatórios (corpus `backend/tests/corpus/bancada/atendimento/casos.jsonl`)

📊 Hoje: `wc -l casos.jsonl` → **40** casos; 10 N2 (`atd-n2-guincho-feliz`, `-msg-duplicada`, `-429-depois-da-tool`,
`-timeout-provedor`, `-tool-erro`, `atd-n2-vidros-portal`, `-risco-faisca`, `-dois-tenants`, `-msg-atrasada`,
`-irritado-handoff`). Os N2 já carregam `client_name_masked` (forma real, v2). Novos casos — **tenant A e B**, nenhum
nome de corretora em código ou teste (CLAUDE.md §13.9):

| chave proposta | o que prova | gates |
|---|---|---|
| `atd-n2-auto-e-resi-eletricista` | cliente com Auto+Residencial pede eletricista, depois "ela cobre eletricista?" → apólice `resi`, sem nova consulta, anáfora resolvida pelo contexto | G1 G5 G6 |
| `atd-n2-guincho-ramo-oficial` | modelo infere/escreve ramo diferente → o oficial vence no dispatch | G3 |
| `atd-n2-vidros-apolice-ate-o-portal` | apólice do turno 1 é a que chega ao `portal_action` no turno 5+ | G4 G7 |
| `atd-n2-varias-mensagens-sem-reconsulta` | 6 mensagens curtas ("ok", "tá", "e agora?") → 1 consulta | G6 |
| `atd-n2-toolmessage-fora-da-janela` | janela empurra a ToolMessage; resposta do modelo sem a seguradora → contexto decide | G7 |
| `atd-n2-identidade-mascarada` | só `client_*_masked` + `client_ref` → contexto nasce | G1 G2 |
| `atd-n2-duas-vigentes-mesmo-ramo` | uma pergunta, uma vez; escolha persiste | G5 |
| `atd-n2-vencida-nunca` | uma vigente + uma vencida mais recente no número → a vencida nunca é selecionada | G5 |
| `atd-n2-timeout-e-retomada` | timeout depois da consulta + novo processo → retoma da ficha | G8 G10 |
| `atd-n2-handoff-leva-a-apolice` | handoff no turno 4 → o aviso ao humano traz a apólice certa (número humano, ramo, seguradora), sem CPF | G4 G2 |
| `atd-n2-dois-tenants-mesmo-codigo` | mesmo `codigo` em A e B → contextos isolados | G9 |

Braços: `duble:perfeito` · `duble:burro` · o modelo de produção · um modelo grande (linha de comparação). 🔴 A
**linha de controle** é a trajetória rodada no HEAD de hoje (F0): tem de reprovar onde a SPEC diz que reprova.

---

## §7 · Unidades e fatias

| fatia | entrega | arquivos | depende |
|---|---|---|---|
| **F0** | **teste do fio** — N1 unitário + 1 N2 (`atd-n2-identidade-mascarada`) chamando o **motor** (`tool_node` + `agent_node` reais, dublês só nas tools) · nasce `xfail(strict=True)` | `backend/tests/test_o_atendimento_guarda_a_apolice.py` (novo) | — |
| **F1** | `policy_context.py` puro + unitários (G1, G2, G9, mutação) | `backend/app/services/policy_context.py` (novo) + teste | F0 |
| **F2** | `tool_node`/`_merge` delegam a F1; escrita durável em `attendance_ficha` (`fundir` com a chave `apolice`, origem por campo) | `nodes.py`, `attendance_ficha.py` | F1 |
| **F3** | leitores trocados para `apolice_do_caso` (dispatch, portal, handoff, compositor/bloco, trava de anáfora, `_gravar_ficha_do_turno`) | `nodes.py`, `o_fim_do_atendimento.py`, leitores achados no B0.5 | F2 (série: mesmo arquivo) |
| **F4** | corpus (§6) + bancada N1/N2 com injeção de falha + relatório | `casos.jsonl`, `bancada_gerar_corpus.py` | F1 (F4a em paralelo), F3 (rodada final) |

**Canário (Founder, depois da entrega):** uma conversa de teste por corretora piloto (dois tenants), número de teste,
com Auto+Residencial; conferir no `ficha_atendimento` que a chave `apolice` nasceu e que o dispatch de teste levou o
ramo oficial. Comandos prontos vão no relatório final (CLAUDE.md §12.2).

**Migrations:** 💭 esperada **nenhuma** (a coluna JSONB existe — B0.4 confirma). Se B0.4 negar, a migration segue o
CLAUDE.md §8 (APPLY/VERIFY/ROLLBACK antes de rodar) e o card sobe de superfície.

---

## §8 · O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (protocolo §7.3)

⚠️ URLs listadas sem nova leitura nesta sessão (economia de franquia); o juiz as reabre na execução.

**R1 · LangGraph — Persistence**
- URL: https://langchain-ai.github.io/langgraph/concepts/persistence/
- O que faz: checkpointer salva o **estado do grafo** por thread a cada passo; retomada lê o estado, não a conversa.
- MODELAMOS: o fato que decide mora em **campo tipado do estado** (`infocap_policy_context`), não em mensagem.
- REJEITAMOS: o checkpoint como única verdade — o `MemorySaver` de fallback (`graph.py:50`) some no reinício; a verdade durável é o Supabase (`ficha_atendimento`), CLAUDE.md §6.
- COMO O JUIZ INSPECIONA: G8 com processo novo e checkpointer em memória — a apólice volta pela ficha.

**R2 · LangGraph — Memory (short-term: estado × mensagens, trim/summarize)**
- URL: https://langchain-ai.github.io/langgraph/concepts/memory/
- O que faz: separa o histórico de mensagens (que se apara ou resume) do estado que persiste.
- MODELAMOS: comprimir ToolMessage é legítimo **desde que** o fato já tenha sido promovido ao estado antes.
- REJEITAMOS: "resumir para o modelo lembrar" — resumo é texto do modelo; o fato vem do sistema de gestão.
- COMO O JUIZ INSPECIONA: G7 — placeholder no lugar da ToolMessage e decisão idêntica.

**R3 · Google ADK — Session State**
- URL: https://google.github.io/adk-docs/sessions/state/
- O que faz: `session.state` chave-valor por sessão, com escopos por prefixo e escrita via evento, não mutação solta.
- MODELAMOS: **uma** escrita (F2) e leitura por uma função (`apolice_do_caso`); escopo = caso (`company_id`+`session_id`).
- REJEITAMOS: prefixo `user:` (estado entre sessões) — a apólice é do caso; outro sinistro reconsulta.
- COMO O JUIZ INSPECIONA: `grep -n "infocap_policy_context\[\|\[\"apolice\"\] *=" backend/app` → um único escritor.

**R4 · OWASP Top 10 for LLM Applications 2025 — LLM02 Sensitive Information Disclosure**
- URL: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/
- O que faz: recomenda minimizar e sanitizar o que entra no contexto do modelo; o modelo não é fronteira de segurança.
- MODELAMOS: lista branca de campos (§2) aplicada **antes** do modelo; a máscara continua no DTO.
- REJEITAMOS: "o prompt manda não repetir o CPF" — Approval/regra não é frase de prompt (CLAUDE.md §6).
- COMO O JUIZ INSPECIONA: G2 com a mutação (campo cru injetado → guarda vermelho).

**R5 · ENISA — Pseudonymisation techniques and best practices** (+ LGPD, Lei 13.709/2018, art. 13 §4 e art. 12)
- URL: https://www.enisa.europa.eu/publications/pseudonymisation-techniques-and-best-practices · https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2018/lei/l13709.htm
- O que faz: pseudônimo por função com chave secreta (HMAC) mantida separada; hash sem chave de identificador de baixa entropia é reversível por força bruta.
- MODELAMOS: `cliente_ref` = HMAC com chave por tenant (D3), chave no Vault.
- REJEITAMOS: `sha256(codigo)` sem chave — `codigo` é sequencial e curto.
- COMO O JUIZ INSPECIONA: G9 + leitura do construtor: a chave não está em código, log nem artifact.

---

## §9 · Riscos

| risco | consequência | mitigação |
|---|---|---|
| o ramo oficial passa a **vencer** e a apólice selecionada está errada | tecla errada na URA, seguradora errada — silencioso (CLAUDE.md §9.5) | G5 (vencida nunca, desambiguação), divergência modelo×sistema vira log e métrica no relatório |
| PII escapa pelo novo campo durável | incidente LGPD; `ficha_atendimento` é lida pelo painel | lista branca + G2 com mutação + red team focado em PII |
| contexto de um caso antigo contamina caso novo do mesmo telefone | apólice de outro sinistro | escopo por caso (`assunto_id` da identidade da ficha); caso resolvido não herda `apolice` |
| duas verdades durante a transição (função antiga + nova) | leitor lê a antiga | COESÃO: F2+F3 na mesma SPEC; guarda de escritor único |
| a ficha falha de gravar (hoje engole o erro) | perde a memória do turno | leitor cai para o `state` (checkpoint); G8 mede |
| a SPEC promete subir os 68,9 % e não sobe | expectativa errada | §0.3: o número só é afirmado depois do B0.6 |

---

## §10 · Decisões abertas (nota 0–100)

| # | decisão | opções e nota | recomendação |
|---|---|---|---|
| **D1** | onde mora a apólice durável | `ficha_atendimento` (JSONB existente) + espelho no checkpoint **90** · só checkpoint **50** · tabela nova **20** (motor paralelo, §5) | 1ª — já vem decidida |
| **D2** | `numapo` visível ao modelo no atendimento | manter visível (regra P0 de 25/06) **80** · só final mascarado + `locator_hash` **60** | manter; reabrir é decisão de LGPD do Founder |
| **D3** | como se faz o `cliente_ref` | HMAC com chave por tenant no Vault **80** · HMAC com uma chave de plataforma **65** · sha256 sem chave **25** · `codigo` cru **10** | HMAC por tenant |
| **D4** | fatia de alívio antes do todo | não: F2+F3 juntas (duas verdades convivendo é pior) **75** · conserto de 1 linha na porta (aceitar `client_ref`) como hotfix imediato **70** | quase empate — **o Founder decide**; o hotfix só vale se entrar com F0 e G3 |
| **D5** | o construtor serve os dois papéis | um construtor para core e atendimento **90** · só atendimento **35** | um só |
| **D6** | quando reconsultar | só em troca explícita de cliente/apólice ou contexto de outro dia **75** · a cada N turnos **40** · nunca **20** | a 1ª |

---

## §11 · Entrega

Uma branch (`spec/117-…`), um relatório (`reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`) com FATO/INFERÊNCIA/RECOMENDAÇÃO,
saída real dos testes e da bancada, declaração de que nenhum motor paralelo foi criado, pendências em `PENDENCIAS.md`,
e **a saída do `git push` colada** — entregar é empurrar (CLAUDE.md §2).
