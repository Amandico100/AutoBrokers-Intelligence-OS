---
> **Status:** em execução · **Protocolo:** AAA v12.2 · AAA FAST · modo GERENTE (experimento C do A/B, D-PROTO-02/09)
> **SPEC:** `docs/canon/specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md` · FICHA `docs/canon/FICHA-EXTRA-001.5.md`
> **Branch:** `feat/spec-extra-001-5-planos-de-assistencia` · **Base:** `3563b0e` (= `origin/main`, 17/09/2026 22:42 UTC)
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `3563b0e`

```
OUTCOME ..............  pergunta de cobertura ("tem carro reserva? cobre granizo? limite do guincho?") → um dos
                        CINCO estados (coberto · nao_coberto · condicionado · nao_contratado · nao_sabemos_ainda),
                        com documento e página ao lado e o NÍVEL do plano, no chat core E no atendimento WhatsApp
                        (mesmo caminho: InfocapPolicyLookupTool → policy_answer_composer), para toda seguradora
RISCO ................  8 = ALCANCE 3 (segurado lê a resposta) + REVERSIBILIDADE 3 (a resposta sai pelo WhatsApp; e
                        tabelas novas + CHECK de tabela viva) + FREQUÊNCIA 2 (toda pergunta de cobertura) — recontado no BLOCO 0                                   (§3)
SUPERFÍCIE ...........  2 (peça nova: 2 tabelas + Skill; comportamentos listados na FICHA A–E) — BLOCO 0 confere se
                        há leitor do corpus fora da lista §3.1 (→ 3)                                        (§3)
PISO APLICADO ........  §3.2 em DOIS pontos: (1) a migration que ALARGA o CHECK de `doc_kind` em tabela viva e
                        SEM_ARQUIVO (§11.2: manifesto, transação única, rollback com guarda de contagem);
                        (2) todo texto que chega ao segurado (§6.2: o "não" carrega documento e página)
NÍVEL ................  🔴 a soma dá CRÍTICO (7); a marcha fixada é PADRÃO (D-PROTO-02, FICHA). Divergência
                        ESCRITA, não silenciada: mantém-se a marcha PADRÃO com o piso nos 2 pontos acima.
                        Builder Opus 5 `xhigh` (subagente fresco por fatia) · juiz Fable 5.1 (D-PROTO-09)
UNIDADES .............  5 · A chave+tabelas · B Skill `cobertura_e_assistencia` · C três ondas · D tela · E medição
                        FATIAS: 1 = A · 2 = B+E · 3 = C+D                                                   (§5.2)
COESÃO ...............  A é hub (chave + migrations; B e C consomem o contrato). B+E tocam o MESMO turno (resposta
                        + `tool_invocations`). C+D tocam a MESMA fila de curadoria (quem propõe · quem publica) (§3.4)
PARALELISMO REAL .....  nenhum — escrita de um só, um builder por vez; investigador read-only: SIM (BLOCO 0)
TIME .................  gerente Fable (este chat) · builder Opus 5 xhigh ×3 · juiz Fable fresco · escalação:
                        lente do dado SIM (outcome é DATASET + migration altera trava + SPEC afirma % do acervo) ·
                        confirmação SÓ se o juiz achar blocker em migration/texto ao segurado · red team NÃO
REFERÊNCIA ...........  interna `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` · externa: as 3 da
                        proposta §14 (PROV-O · Citations da API Anthropic · ALCE 2023)                (§7.1 · §7.3)
GATES ................  GA GB GC GD GE G-MIG G-CANÁRIO + py_compile · suíte por diff · rotas-montam + next start
O ELO ................  "responde genérico PORQUE não há plano estruturado": medir A (respostas genéricas) · medir
                        B (0 linhas de plano) · medir que B CHEGA em A (o caminho atual sobre perguntas de carro
                        reserva devolve os 3 serviços residenciais fixos de `assistance_policy.py:28`)      (§0.3)
FAIXA DE RELÓGIO .....  declarada: fatia ≤ 75 min ×3 · juiz+lente+conserto+entrega ≤ 45 min · tetos por fatia
                        160 turnos · 250 k · real: <preencher>                                      (§9.2 · §10)
```

**Produto:** AutoBrokers Intelligence OS · **Executor:** gerente Fable 5.1 + builders Opus 5 `xhigh` · **Juiz:** Fable 5.1 ·
**Preflight** 📊 17/09/2026 22:42 UTC: `HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD = `3563b0e` · árvore
com 4 arquivos soltos do Founder (prompts `.TXT`/`.md` não versionados; não tocados) · **Início:** 17/09 22:42 UTC

**Decisão do gerente (nota 0–100):** todas as 3 fatias vão a builder Opus xhigh (90) contra "o gerente constrói a
fatia 1" (50): o protocolo v12.2 §5.2 manda o gerente delegar CADA fatia, e o Founder pediu (17/09) que o gasto do
Fable fique no mínimo (91 % da cota semanal consumida). Investigador do BLOCO 0 em Opus (85) × Sonnet (65): as
medições decidem o desenho da onda 2 e o tamanho do Bloco A; erro aqui custa uma fatia inteira.

## 1. BLOCO 0 — as premissas que mudariam o desenho (investigador Opus read-only, 📊 17/09 23:20 UTC, banco só SELECT)

| # | a proposta afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | `storage_ref` em 0 de 29 | **173/206** versões com fonte (pilotos: 49/62) | `select count(*) filter (where storage_ref is not null), count(*) from normative_document_versions` | onda 1 tem fonte; docstring de `acervo_arquivo.py:5` vencido (§9.3) |
| 1b | corpus sem página | **nenhuma** coluna de página em `normative_*`; `` morre em `limpar()` (`insurance_corpus.py:367`) | `information_schema.columns` | página só pela FONTE ARQUIVADA (PDF no MinIO), como §7.1 manda |
| 2 | elo SUSEP bloqueado pelo filtro | `extrair_susep(build_document_plain_text(pages))` → **`15414.900228/2017-63`**; `build_document_plain_text` não chama `is_boilerplate_fragment`; `eq("susep_process"` → **0** | script em `backend/`; `rg` exit 1 | filtro fica intocado; falta só o CONSUMIDOR (M-C2 controla o caminho real) |
| 3 | caminho vivo único | 1 importador (`policy_answer_composer.py:24`), 1 consumidor (`infocap_tool.py:722`), tool em `graph.py:449` | `rg -n "apply_residential_assistance_policy\|compose_policy_answer_with_meta" backend/app` | a base entra no composer; nada ao lado |
| 3b | WhatsApp usa o mesmo | `capability_bindings`: `attendance` e `core` **enabled** para `operational.infocap.policy_lookup.read` | `select agent_role, enabled from capability_bindings where capability_key=…` | 🔴 pedido do Founder atendido sem código extra: a Skill serve o atendimento |
| 3c | guarda dos 3 serviços | `nodes.py:344-352` ANULA resposta sem eletricista+chaveiro+encanador (copiloto); WhatsApp (`client_facing`) **sem** guarda | `sed -n 344,352p` | o guarda muda de regra (FICHA B) — senão "carro reserva: não" é revertido |
| 4 | 6 seguradoras com CG casando | depois de `normalize_insurer_key(…,"conhecimento")`: **7** (allianz azul bradesco mapfre porto tokio yelum); `hdi` (8 docs) fora das 61 siglas; desconhecida → **primeiro token** (`seguradora_xyz`→`seguradora`, `:8262`) | script `placar_das_siglas` + SELECT + função em processo | a base aceita seguradora fora do censo; chave desconhecida é REJEITADA/UNKNOWN listado, nunca gravada como lixo |
| 5 | CHECK de `doc_kind` | 9 valores no CHECK, **3 em uso** (condicoes_gerais 184 · manual_do_segurado 5 · circular_susep 5 = 194); 4 triggers, todos FK internas | `pg_get_constraintdef` · `group by doc_kind` · `pg_trigger` | manifesto de §11.2 nasce desta saída; expand-first vale |
| 6 | `tool_invocations` guarda `tool_args` | coluna **não existe**: é `input_summary jsonb` (`gateway.py:294-306`); CPF cru → **0/289**; escritor único `invocation_recorder.py:307` | `information_schema.columns` · `~ '[0-9]{11}'` | E grava a `origem` em `input_summary`/saída do registro que existe |
| 7 | Skill nasce no `SkillRegistry` | 20 skills · 21 releases `published`; cutover lê `TOOL_GATEWAY_MODE` (default `off`, ausente do `.env`) — o chat resolve **tools LangChain**, não releases | `rg SkillRegistry` · `grep -c TOOL_GATEWAY_MODE backend/.env` → 0 | Skill nasce como MÓDULO em `services/skills/` + release no registro (escritor existente) + entra pelo caminho vivo (composer) |
| 8 | O ELO | 10 perguntas reais: "carro reserva" **nem casa** `_ASSIST_INTENT_RE` (`composer:39-41`); quando casa, responde **"Sim"** com os 3 fixos a "cobre carro reserva? vidros? táxi? borracheiro?" | script em processo, saída no transcrito | 🔴 defeito de PRODUTO §9.5: resposta afirmativa errada ao segurado. A unidade B conserta o elo |
| 9 | linha de base da suíte | **35 failed · 1114 passed · 34 xfailed · 48 errors** (35 min); os 48 erros são `test_098_builder_b_unit.py` por ordem (isolado: 80 passed) | `python -m pytest tests -q` | triagem por diff contra esta linha; `test_o_protocolo_tem_policia` JÁ vermelho na main |
| 10 | leitores do corpus | 4 arquivos; escritor único `insurance_corpus.py` | `rg -l "normative_document" backend/app` | SUPERFÍCIE fica 2 |
| 11 | procedência volta? | `_INDICES_DE_PAYLOAD:88-99` sem `doc_kind`; retorno `:891-909` com 8 chaves, nenhuma de origem | `sed -n 885,910p` | B: índice + parâmetro + chaves de retorno (aditivo) |
| 12 | tela em `frontend/` | app Next é a RAIZ: `app/dashboard/personalizacao/conhecimento/{page,KnowledgeClient}.tsx`; `test:rotas-montam` em `package.json:24` | `find`, `grep` | D usa o caminho real |
| 13 | pendências | P-PILOTO-20 **FECHADA** (`PENDENCIAS-FECHADAS.md:896`); P-PILOTO-04 aberta (`:10522`) | `rg` | — |
| F1 ❌ | "`documents` tem `doc_kind`" | **0** (controle `normative_documents` → 1) | `information_schema.columns` | refutada por comando |
| F2 ❌ | "`eq(\"susep_process\"` existe" | **zero linhas, exit 1** | `rg` | refutada por comando |

**Achados fora do escopo (§4):** `PlanoDeAssistencia`/`EstadoDoPlano` JÁ existem (`policy_data_provider.py:491-507`: contratado · nao_contratado · nao_sabemos_ainda) — a Skill **estende**, não recria · o briefing da LLM já escreve `plano_de_assistencia` (`infocap_tool.py:872-879`) e o composer não sabe dele: a Skill entra nos DOIS · `test_o_protocolo_tem_policia` vermelho na main · 48 erros de ordem em `test_098` · docstring "0 de 29" vencido.

**Recontagem:** RISCO **8** (reversibilidade 3: a mensagem sai pelo WhatsApp) · SUPERFÍCIE **2**. A conta dá CRÍTICO; a marcha fixada
(D-PROTO-02, FICHA) é PADRÃO. **Decisão (nota):** executar com o ELENCO do CRÍTICO (juiz Fable + lente do dado + confirmação por
gatilho + piso nos 2 pontos) e os tetos por fatia de PADRÃO — 88; PADRÃO puro — 60; parar para perguntar — 10.

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|---|

## 3. Migrations — APPLY · VERIFY · ROLLBACK (escritos ANTES; VERIFY contra o objeto)

## 4. O juiz fresco

## 5. O conserto único

## 6. A bateria

## 7. O que ficou fora, e o gatilho que o faz voltar

## 8. 📋 Caixa do Founder

## 9. Pendências e decisões

## 10. Telemetria (§11)

## 11. Entrega

