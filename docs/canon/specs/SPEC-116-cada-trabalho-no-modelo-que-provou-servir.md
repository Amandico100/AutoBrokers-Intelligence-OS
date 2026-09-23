# SPEC-116 · Cada trabalho no modelo que provou servir — Model Router + Bancada E2E

> **SPEC convertida** em 23/09/2026 (modo CONVERSÃO) sobre `543cc82` (= `origin/main`), a partir de
> [`PROPOSTA-SPEC-MODEL-FABRIC-E2E-LLM-UPGRADE.md`](../specs-propostas/PROPOSTA-SPEC-MODEL-FABRIC-E2E-LLM-UPGRADE.md) e do
> seu research pack. **A proposta foi refutada onde a medição discordou (§2).** Evidência completa, com o comando de cada
> número: [`specs-propostas/SPEC-116-EVIDENCIAS/`](../specs-propostas/SPEC-116-EVIDENCIAS/) (01 censo · 02 banco/ledger ·
> 03 arquitetura/SDK · 04 e 05 mercado). Rito: PROTOCOLO AAA **v13 · O FIO**. 📊 medido · 💭 ilustrativo · ❓ desconhecido.
> 🔴 **Nome:** a proposta dizia "Model Fabric". O cânone já tem a peça: **Model Router** (SPEC-052 §14 — *"a escolha de
> modelos será mantida em configuração governada e avaliada por benchmarks"*) e `model_policy.profile` (SPEC-056). "Fabric"
> colidiria com o *Intelligence Fabric* (garimpo/briefings, SPEC-061 §16.5). Esta SPEC **implementa** a 052 §14; não cria motor.

## 0. EXECUTION CARD

```
OUTCOME ..............  nenhum modelo velho escondido decide o que o segurado e o corretor recebem. Cada TRABALHO
                        (papel) pede um modelo a UM resolvedor que lê UM catálogo governado no banco; o catálogo sabe
                        preço verdadeiro, ciclo de vida, capacidades e que classe de dado cada modelo pode ver. Uma
                        BANCADA E2E sobre a Eval Fabric da SPEC-062 mede cada candidato no motor REAL com dublês na
                        borda, e o mapa de modelos sai dela. Trocar e voltar = uma linha de configuração, em minutos
RISCO ................  8 = alcance 3 (o segurado lê a resposta) + reversibilidade 3 (mensagem/portal saem do prédio)
                        + frequência 2 (todo atendimento)
SUPERFÍCIE ...........  3 (34 call sites, 19 por fora da fábrica, 11 catálogos, 3 serviços)
PISO APLICADO ........  §3.2: migration que altera ESTRUTURA + caminho que ENVIA (atendimento/portal) → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus xhigh · juiz Fable ‖ red team Fable · confirmação se blocker ·
                        lente do dado (gatilho: a SPEC publica número de custo/sucesso por modelo)
O FIO ................  §4 · teste do fio: backend/tests/test_o_fio_do_modelo.py (1ª entrega da fatia F1)
PARALELISMO REAL .....  §7: F1 sozinha → F2 ‖ F4 ‖ F5a (arquivos disjuntos, listados) → F3 → F5b (costura) → F6
UNIDADES .............  §6 (U1–U14)
COESÃO ...............  catálogo+resolvedor+gate juntos (mesmo contrato ModeloResolvido) · fábrica+histórico+relógio+
                        callback juntos (mesmo arquivo-hub llm_factory) · call sites por fora numa fatia (consomem o
                        contrato, não o redefinem)
TIME .................  ≤ 6 builders (1 por fatia) · juiz ‖ red team · confirmação · lente do dado · atualizador de docs
REFERÊNCIA ...........  interna: SPEC-062 runner/evaluators (backend/app/services/evals/) · test_a_maquina_de_lavar_vai_
                        ate_o_fim.py · scripts/replay.py · externa: §12
GATES ................  §9 (G0–G14)
O ELO ................  "o modelo X decide o trabalho Y PORQUE o resolvedor devolve X": o teste do fio constrói o
                        objeto PELA FÁBRICA e lê o payload que sairia ao provedor (model, effort, sem temperature);
                        o ledger grava pedido × resolvido × real — B chegando em A medido por máquina, não por leitura
FAIXA DE RELÓGIO .....  💭 18–28 h · teto 1,5× · 24 agentes · bancada ao vivo ≤ US$ 100 (guarda no código, D-116-09)
```

## 1. BLOCO 0 — remedido em 23/09/2026 (a proposta NÃO herdou status de "medido")

| # | premissa que muda o desenho | 📊 medido | comando / fonte |
|---|---|---|---|
| B0.1 | árvore em dia | 0 atrás · 0 à frente · HEAD `543cc82` | `git rev-list --count HEAD..origin/main` |
| B0.2 | quem chama provedor | **34 call sites · 15 pela fábrica · 19 POR FORA** | EVIDENCIAS/01 §(a) |
| B0.3 | agentes vivos | 8/8 `anthropic/claude-sonnet-5`; effort gravado `low`/`medium`; 1 `vision_model=gpt-4o` (Blueprint Studio) | `select … from agents` (EVIDENCIAS/02) |
| B0.4 | effort chega ao Claude? | **NÃO** — `llm_factory.py:200` só repassa a `o1`/`o3`; Sonnet 5 roda no default `high` | leitura `llm_factory.py:198-258` + sonda (EVIDENCIAS/03 §1.8) |
| B0.5 | memória | **gpt-4o-mini de fato**: 8/8 linhas + DEFAULT da coluna `'gpt-4o-mini'`; o Haiku de `constants.py:77` só vale sem linha e aí quebra (Claude em `ChatOpenAI`) | `information_schema.columns.column_default` |
| B0.6 | ledger 45 d | Sonnet 5 chat 386 · plataforma 532 · memória gpt-4o-mini 55 · visão gpt-4o-mini 6 · Opus 5 26 · whisper 4 · **zero** gpt-4o, gemini, atlas, distiller, portal | EVIDENCIAS/02 |
| B0.7 | superfícies que RODAM sem ledger | portal (38 jobs, 0 linhas) · atlas (`company_id="atlas"` falha no uuid). ⚠️ **CORRIGIDO na execução (F3b):** o distiller NÃO sumia — 📊 as 18 execuções (29/07–05/08) têm 35 linhas `claude-opus-5`, gravadas como `chat` sob a empresa técnica Global Knowledge e FORA da janela de 45 d do censo; o defeito era o rótulo, não a ausência | EVIDENCIAS/02 "O ELO" + SELECT da F3b |
| B0.8 | preço | `llm_pricing` 50 linhas, **sem vigência nem fonte**; Sonnet 5 = 3/15 (oficial 2/10); multiplicador de cache IGUAL para todos; modelo sem preço → cobrado como gpt-4o-mini (`usage_service.py:163`) | `select * from llm_pricing` |
| B0.9 | atendimento vivo? | **parado desde 10/09** (attendance `is_active=false`) → baseline vem de REPLAY | ledger por agente |
| B0.10 | Eval Fabric (SPEC-062) | existe: 3 datasets · 8 casos · 7 avaliadores · **0 runs** | `select count(*)` nas 6 tabelas |
| B0.11 | acesso das chaves locais (`backend/.env`, gitignored) | OpenAI: `gpt-6-astra/sol/luna`, `gpt-5.6-sol/terra/luna`, `gpt-transcribe` · Anthropic: `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5`, `claude-haiku-4-5` · **sem** Google, xAI, DeepSeek, MiMo, Z.ai | `GET /v1/models` das duas APIs (só IDs) |
| B0.12 | SDKs | langchain-openai 1.0.3 (atual 1.6.4) · langchain-anthropic 1.1.0 (1.7.3) · core 1.1.0 (1.6.4) · langgraph 1.0.3 (1.2.12) · checkpoint 3.0.1 (**CVE-2026-27794/-48775**, fix 4.x) · `openai`/`anthropic`/`httpx` **sem pin** | EVIDENCIAS/03 Parte 2 |

## 2. A REFUTAÇÃO — o que a proposta acertou, errou, perdeu

**Acertou:** KPI = sucesso E2E e custo por sucesso · bench antes da troca · Responses API obrigatória para GPT-6 com tools+reasoning (📊 confirmado na doc) · preços de GPT-6, Opus 5.5 (4/20), Sonnet 5 (2/10), Grok 4.7, MiMo · pricing divergente · memória no mini · fallback silencioso da fábrica · não trocar embeddings por moda.

**Errou / desatualizou:**
| a proposta | a medição |
|---|---|
| dispatch "pode ser Sonnet 5" e atlas em Sonnet 5 | env de produção: **`claude-opus-5`** nos dois |
| Haiku 5 candidato | **não existe**; Haiku 4.5 tem retirada ≥ 15/10/2026 |
| Gemini 3.8 Flash 0,75/3,75 | só até 31/12/2026 → **1,50/7,50** em 01/01/2027; sem Live API |
| DeepSeek V4-Pro "encaminhado ao Flash" | revertido no mesmo dia; GLM-5.3-Flash saiu 26/08, não 23/09 |
| tabelas `bench_*` novas | **motor paralelo** (CLAUDE.md §5): a Eval Fabric da SPEC-062 já existe → a bancada ESTENDE |
| "ChatOpenAI com base_url" para xAI/MiMo/DeepSeek/GLM | todos exigem **reenviar o raciocínio** entre rodadas de tool (DeepSeek 400 sem ele; langchain #40219 aberta) → adaptador próprio |
| Sonnet 5 "baseline" | o baseline de hoje é Sonnet 5 **com effort ignorado e thinking descartado** — medir o modelo sem consertar o arnês credita ao modelo o nosso defeito (CLAUDE.md §9.2) |

**Perdeu (achados novos, por gravidade — EVIDENCIAS/01 §g e 03):**
1. 🔴 **Toda corretora NOVA nasce com o atendente em `openai/gpt-4o-mini`**, travado contra troca (`agent-blueprints-canonical.ts:102-103,248-249`); a promoção de `model_policy.py` é só do core.
2. 🔴 **Toda foto do segurado é lida por `gpt-4o-mini`** (`webhook.py:857,1501` chamam `describe_image` sem agente → `vision_service.py:22`).
3. 🔴 **Portal (P0 vidros) decide o clique com `gpt-4o`** (`PORTAL_VISION_MODEL` ausente) e **cai calado em `gpt-4o-mini` em qualquer erro ≥400**, por HTTP direto, fora do ledger (`adaptive.py:47,405,428`).
4. 🔴 **Retry do turno inteiro quando o erro contém "connection"** (`langchain_service.py:507-562`) — o erro de rede do SDK diz exatamente isso: tool com efeito pode rodar 2×.
5. 🟠 Auxiliares de resumo e de follow-up ao cliente **quebrados desde 07/08** (Claude em `ChatOpenAI`, `auxiliaries.py:40,479,609`).
6. 🟠 HyDE do RAG (chat e atendimento) e chunking agêntico fixos em `gpt-4o-mini` (`search_service.py:381`, `ingestion_service.py:380`).
7. 🟠 Juiz de eval **nunca rodou** (assinatura errada, `juiz_llm.py:119` → `TypeError` engolido).
8. 🟠 Fallback de visão para `claude-3-5-sonnet-20241022` — **retirado da API em 28/10/2025**; dropdown do admin oferece `-20240620` (idem).
9. 🟠 Visão com Claude 5 fica cega em 4 caminhos por fora da fábrica (mandam `temperature` → 400).
10. 🟠 Histórico reenviado descarta blocos de raciocínio (`utils.py:96`) — bloqueia Opus 5.5/GPT-6/DeepSeek/Grok corretos em loop de tools.
11. 🟡 Guardrail anti-jailbreak desligado calado (`GROQ_API_KEY` vazia) · envs `AUTOBROKERS_GEMINI_*` sem leitor neste repo (0 commits na história) · rótulo `gpt-4-turbo` mentindo no log.

## 3. A ARQUITETURA (após a refutação)

```
PAPEL (o trabalho: atendimento, chat_principal, portal_decisao, dispatch, memoria, visao, hyde, extracao_planos,
       atlas, distiller, distiller_forte, juiz, garimpo, sugestoes, brand, auxiliar, conselho, transcricao, embedding)
   │   declarado pelo CHAMADOR, nunca um model id no código de negócio
   ▼
RESOLVEDOR  backend/app/factories/model_policy.py  (reescrito; mesmo ponto de chamada)
   resolver(papel, agente?, corretora?, classe_de_dado, override_da_bancada?) → ModeloResolvido
   { provider, model, effort, api_surface, parametros, reserva, motivo, versao_da_rota }
   ordem: override da bancada (só no processo da bancada) → rota do papel (banco) → modelo do agente SÓ para
          papel sem rota (agentes custom) e só se registrado → snapshot versionado (sem banco) → ERRO EXPLÍCITO.
          ⛔ nunca "cai no mini" · D-116-17: a ROTA vence o agente (troca/volta em minutos; "modelo nunca é
          override do tenant" já era regra do blueprint)
   ⛔ recusa rota cuja classe_de_dado o modelo não pode ver (LGPD) · ⛔ recusa lifecycle BLOCKED/HISTORICAL
   ▼
CATÁLOGO (autoridade) = `llm_pricing` EXPANDIDO (não tabela nova de modelos): lifecycle · api_surface · capacidades
   (tools, reasoning_param, niveis_de_esforco, sampling_ok, vision, max_output, contexto, tool_choice_forcado_ok,
   raciocinio_ida_e_volta) · classes_de_dado · substituido_por · preços reais (input, cache read, cache write, output,
   longo) com `preco_verificado_em` + `fonte_preco_url`
ROTAS = tabela nova `llm_papeis` (papel → primário+esforço, reserva+esforço, classe_de_dado, risco, motivo) +
   `llm_papeis_historico` (cada troca, quem, por quê) → ROLLBACK = reaplicar a linha anterior, em minutos, sem deploy
SNAPSHOT = backend/app/factories/modelos_snapshot.json gerado do banco (script) → fallback offline + insumo do CI + TS
   ▼
ADAPTADORES dentro de backend/app/factories/llm_factory.py (nada paralelo): capacidades → kwargs
   OpenAI: api_surface=responses p/ GPT-6 (use_responses_api, reasoning.effort, store=False, sem temperature) ·
   Anthropic: output_config.effort nativo (langchain-anthropic ≥1.7.3), sem sampling, sem tool_choice forçado no 5.5 ·
   Google: thinking_level · OpenAI-compatível genérico (linha do catálogo com base_url + api_key_env + ida-e-volta do
   raciocínio) · provedor/modelo desconhecido → ERRO
   ▼
HISTÓRICO preserva blocos de raciocínio por provedor (sanitize só quando troca de provedor no meio da conversa)
   ▼
RESERVA (failover) declarada na rota, acionada SÓ antes da 1ª tool com efeito do turno, pelo breaker que já existe
   (relogio_do_modelo); depois da 1ª tool com efeito: reter e sinalizar, NUNCA refazer o turno em outro modelo
   ▼
LEDGER (o que já existe: cost_callback → token_usage_logs + usage_events) grava em `details`: papel · modelo_pedido ·
   modelo_resolvido · modelo_real (response_metadata) · esforço · reserva_usada + motivo · tokens de raciocínio e cache
```

## 4. O FIO (do 1º byte ao último)

```
mensagem WhatsApp/web → app/services/langchain_service.py:process_message → _get_raw_agent (agents.*)
 → app/agents/graph.py:create_agent_graph → app/factories/llm_factory.py:create_llm(papel=…)
 → app/factories/model_policy.py:resolver(papel, agente, corretora, classe_de_dado)
     lê llm_papeis + llm_pricing (cache do UsageService) | snapshot → ModeloResolvido (ou ERRO)
 → llm_factory._criar_<provider>(ModeloResolvido) → payload (model, effort, sem sampling proibido) → provedor
 → nodes.py:agent_node → tools (efeito pelo Work OS/idempotência existentes) → histórico com raciocínio preservado
 → core/callbacks/cost_callback.py:on_llm_end → usage_service.track_cost_sync → token_usage_logs.details{papel,pedido,
   resolvido,real,reserva} + usage_events
 → falha do provedor ANTES da 1ª tool com efeito: relogio_do_modelo marca → resolver devolve a RESERVA → mesma
   chamada no outro modelo, ledger com motivo · DEPOIS: retém + sinaliza
BANCADA: backend/scripts/bancada.py → app/services/evals/bancada.py → para cada BRAÇO (provider, model, effort):
   resolver(papel, override_da_bancada=braço) → o MESMO motor acima com dublês de tool/canal/portal na borda
   → avaliadores determinísticos (evaluators.py) → eval_runs(+config do braço) / eval_case_results(+custo, tokens,
   latência, rastro de tools, resultado) → relatório por papel: pass@1 · pass^k · custo por sucesso · p50/p95
```

## 5. A BANCADA E2E — o desenho (é o que decide o mapa)

**Por que ela entra ANTES da escolha e DEPOIS do conserto do arnês (D-116-05, nota 92):** hoje o Sonnet 5 roda com
effort ignorado e raciocínio descartado, e o GPT-6 nem consegue usar tool com raciocínio no nosso caminho. Bancada antes
do conserto mede o nosso defeito e o credita ao modelo. Bancada depois da troca é decreto. Ordem: **arnês → baseline →
candidatos → mapa → promoção por configuração**.

**Estende a SPEC-062 (nada de `bench_*`):** `eval_runs` ganha `braco jsonb` (provider, model, effort, api_surface,
prompt_hash, tools_hash, versao_da_rota, tentativa) e `custo_usd`; `eval_case_results` ganha `resultado`
(PASS|FAIL|PARTIAL|BLOCKED_BY_INFRA), `tokens jsonb` (in/out/cache/raciocínio), `custo_usd`, `latencia_ms`,
`rastro jsonb` (tools chamadas + args + efeitos no dublê), `tentativa`. Casos versionados em
`backend/tests/corpus/bancada/` (sem PII: mascarados do acervo real) e carregados em `eval_cases` por versão congelada.

**Três níveis, placares nunca misturados:**
| nível | o que roda | oráculo | onde |
|---|---|---|---|
| **N1 DECISÃO** | UMA volta do motor real (nó do agente com prompt real, tools reais em schema, contexto de fixture) | mecânico: tool certa · args certos · JSON válido e campos certos · fato presente/ausente · não pergunta o que já sabe | offline, barato, k=3 |
| **N2 TRAJETÓRIA** | o grafo inteiro, multi-turno, segurado roteirizado (rajadas reais), dublês de tool/canal/portal, **injeção de falha** (tool timeout, tool erro, 429/500 do provedor, mensagem duplicada, atrasada) | estado final · efeito EXATAMENTE uma vez no dublê · dois tenants sem vazamento · fatos na resposta · turnos ≤ orçamento | offline, k=3 |
| **N3 AO VIVO** | portal com credencial de teste, número de teste | recibo real | 🧑 canário — roteiro, não execução desta SPEC |

**Domínios mínimos (casos N1 / trajetórias N2 — 💭 números-alvo, o builder mede a cobertura):** chat principal
(apólice, 2 apólices, vencida × vigente, cobertura/franquia/assistência, dado conflitante, tool com erro) 30/8 ·
atendimento WhatsApp (rajadas, não repetir pergunta, serviço certo, coleta completa, retomada, handoff) 30/10 ·
corredor/URA onde o LLM decide (telas reais) 15/4 · portal `decide_next_action` (telas reais de portal) 15/4 ·
cobrança (retornos reais) 10/3 · memória (fatos ouro, não inventar, não guardar lixo) 15 · visão/documento (fotos e
PDFs mascarados → campos) 15 · extração de planos 10 · HyDE 10 · juiz (concordância com ouro) 15 · transcrição
PT-BR (áudio sintético de falas reais mascaradas) 10.

**Métricas por braço × papel:** pass@1 · **pass^k** (todas as k passam — confiabilidade, não sorte) · custo por
sucesso = custo total ÷ sucessos · p50/p95 · acerto de tool e de args · validade estrutural · **efeito duplicado
(tem de ser 0)** · recuperação após falha injetada · BLOCKED_BY_INFRA separado (falha nossa ≠ do modelo, regra de
diagnóstico do research pack §35).

**Regra de escolha (Onda A — potência primeiro):** elegível = classe de dado permitida · 0 efeito duplicado ·
pass^k = 100 % no subconjunto CRÍTICO do papel (corte da SPEC-062 §13 por risco). Entre elegíveis vence o maior
pass@1 no conjunto amplo; empate dentro de 2 pp → o de menor custo por sucesso. **Reserva** = melhor elegível de
OUTRO provedor com as mesmas capacidades exigidas pelo papel. **Teto de qualidade** (Opus 5.5 high e GPT-6 Astra)
roda no subconjunto crítico: se até o teto falha, o defeito é do arnês → vira achado, não troca de modelo.
**Onda B (baratear):** um papel por vez, desafiante mais barato promovido só se não-inferior (≥ vencedor − 1 pp amplo,
100 % crítico) **e** canário vivo — precisa de tráfego vivo; fica escrita e armada (U14).

**Braços iniciais** (vivos com as chaves de hoje): Sonnet 5 (como está = baseline · e com effort low/medium/high
consertado) · Opus 5.5 medium/high · GPT-6 Sol medium/high · GPT-6 Luna medium · GPT-6 Astra high (teto, só crítico) ·
GPT-5.6 Terra · Haiku 4.5 · gpt-4o / gpt-4o-mini (papéis onde são o atual) · gpt-transcribe × whisper-1.
**BLOCKED LIVE — chave ausente:** Gemini 3.8 Flash (chave existe em produção, falta no ambiente local) · Grok 4.7 ·
MiMo V2.6 · DeepSeek V4.1 · GLM 5.3 — adaptador + contrato com dublê prontos; entram com `--braco` quando a chave vier.

## 6. Unidades

| U | unidade | fatia | estado ao fechar |
|---|---|---|---|
| U1 | catálogo: `llm_pricing` expandido + preços verificados (fonte+data) + lifecycle de TODOS os ids do censo | F1 | no ar |
| U2 | rotas `llm_papeis` + histórico + seed = comportamento de HOJE (nada muda de modelo nesta unidade) | F1 | no ar |
| U3 | resolvedor (`model_policy.py`) + snapshot + ERRO no desconhecido + recusa por classe de dado | F1 | no ar |
| U4 | legacy gate (CI): chama o resolvedor para todo papel, lê defaults TS pelo snapshot, controle vermelho | F1 | no ar |
| U5 | adaptadores: effort Claude · Responses GPT-6 · Google thinking · OpenAI-compatível genérico com ida-e-volta do raciocínio; SDKs pinados/atualizados (§8) | F2 | no ar |
| U6 | histórico preserva raciocínio · retry por "connection" morre · reserva só antes da 1ª tool com efeito | F2 | no ar |
| U7 | ledger: papel · pedido · resolvido · real · reserva · tokens de raciocínio/cache; preço desconhecido ≠ preço do mini | F2 | no ar |
| U8 | os 19 call sites por fora passam a pedir PAPEL: visão ×4 · memória · HyDE · chunking · auxiliares · juiz (conserto) · atlas (ledger) · dispatch ×3 · distiller/extrator/brand/garimpo/sugestões/conselho · rerank/embedding/whisper registrados · docling pelo env | F3 | no ar |
| U9 | portal worker: rota `portal_decisao` lida do banco, sem rebaixamento calado, uso gravado no ledger | F3 | no ar |
| U10 | nascimento: blueprints/tenant/sandbox/auxiliares nascem SEM modelo (herdam a rota); `memory_settings` DEFAULT sai do mini; UI lista o catálogo pela API | F4 | no ar |
| U11 | bancada: extensão da Eval Fabric (migration) + runner + dublês + injeção de falha + CLI + teto de US$ | F5a | no ar |
| U12 | corpus da bancada (N1 + N2) mascarado, versionado, carregado | F5a | no ar |
| U13 | RODAR: baseline → candidatos → teto → relatório por papel → **mapa de modelos (Onda A)** aplicado nas ROTAS, com o anterior no histórico | F6 | no ar |
| U14 | Onda B armada: comando de desafiante por papel + critério de não-inferioridade + roteiro de canário | F6 | escrito, espera tráfego vivo |

**Sai (com gatilho):** Gemini/Grok/MiMo/DeepSeek/GLM ao vivo (chave + gate de privacidade) · embeddings (sem sucessor
OpenAI; troca exige reindexação + eval de retrieval) · voz Gemini (sem leitor neste repo) · guardrail Groq (pendência) ·
Onda B promovida (tráfego vivo) · upgrade `openai` 3.x/`anthropic` 1.x (httpx2 — sem necessidade concreta hoje).

## 7. Fatias e arquivos (cada arquivo tem UM dono)

```
F1 (sozinha)  backend/supabase/migrations/20260923_01_spec116_catalogo_e_papeis.sql · backend/app/factories/model_policy.py ·
              backend/app/factories/modelos_snapshot.json · backend/scripts/gerar_snapshot_de_modelos.py ·
              backend/app/services/usage_service.py · backend/scripts/seed_pricing.py ·
              backend/tests/test_o_fio_do_modelo.py · backend/tests/test_nenhum_modelo_fora_do_catalogo.py ·
              backend/tests/test_model_policy.py
F2 ‖ F4 ‖ F5a
F2            backend/app/factories/llm_factory.py · backend/app/core/utils.py · backend/app/core/relogio_do_modelo.py ·
              backend/app/core/callbacks/cost_callback.py · backend/app/services/langchain_service.py ·
              backend/app/agents/graph.py · backend/app/agents/nodes.py (só histórico/reserva) · backend/requirements.txt ·
              backend/tests/test_llm_temperature_guard.py · backend/tests/test_spec116_f2_*.py
F4            lib/admin/agent-blueprints-canonical.ts · lib/admin/agent-blueprints.ts · lib/admin/blueprint-release.ts ·
              lib/admin/provision-tenant.ts · lib/admin/agent-health.ts · app/api/admin/sandbox/bootstrap-tenant/route.ts ·
              app/admin/auxiliares/page.tsx · components/admin/AgentConfigModal.tsx · backend/app/api/agent_config.py ·
              backend/supabase/migrations/20260923_02_spec116_nascimento_sem_modelo_velho.sql · scripts/*.test.mjs tocados
F5a           backend/supabase/migrations/20260923_03_spec116_bancada_na_eval_fabric.sql ·
              backend/app/services/evals/bancada.py · backend/app/services/evals/dubles.py · backend/scripts/bancada.py ·
              backend/tests/corpus/bancada/** · backend/tests/test_spec116_bancada_*.py
F3 (depois de F2)  os call sites da U8/U9 (lista em EVIDENCIAS/01 §a, linhas 3–34) · backend/portal_worker/adaptive.py ·
              docling-service/app/config.py · backend/tests/test_spec116_f3_*.py
F5b (costura) o runner usando resolvedor+fábrica reais; ajustes em evals/ apenas
F6 (gerente)  rodar a bancada · relatório · migration de DADO das rotas (Onda A) 20260923_04_spec116_mapa_onda_a.sql
```

## 8. SDKs — só o que tem necessidade concreta (D-116-08)

| pacote | de → para | necessidade | condição |
|---|---|---|---|
| langchain-core | 1.1.0 → 1.6.x | exigido pelas integrações abaixo | junto |
| langchain-anthropic | 1.1.0 → 1.7.3 | effort nativo (B0.4) | teste do payload |
| langchain-openai | 1.0.3 → 1.6.4 | Responses API p/ GPT-6 com tools+raciocínio | issue #34660 (tool call no streaming): contrato com stream real antes de promover |
| langgraph | 1.0.3 → 1.2.x | exigido pelo checkpoint 4 | junto |
| langgraph-checkpoint | 3.0.1 → 4.x | 2 CVEs | **medir** que checkpoints existentes abrem; se não abrem → fica 3.0.1 + pendência de segurança escrita |
| openai / anthropic / httpx / checkpoint-postgres | sem pin → `==` versão resolvida hoje | build reprodutível | 3.x/1.x (httpx2) NÃO |
| langchain-google-genai | 3.1.0 → 4.x | só quando Gemini entrar na bancada | com a chave |

## 9. Gates

```
G0  censo reproduzível: o gate U4 falha com 1 literal de modelo novo fora do catálogo num call site (controle)
G1  teste do fio: pela FÁBRICA, papel=atendimento → payload com model/effort da rota, sem temperature; trocar a rota no
    banco (dublê) muda o payload sem deploy; papel/provedor desconhecido → ERRO (mutação: reintroduzir o `else → mini` ⇒ VERMELHO)
G2  classe de dado: rota pii → modelo sem 'pii' em classes_de_dado ⇒ recusa (mutação: remover a checagem ⇒ VERMELHO)
G3  legacy gate: 0 id BLOCKED/HISTORICAL/não registrado em default, reserva, blueprint, UI, env default (controle vermelho)
G4  effort: Claude recebe output_config.effort da rota; GPT-6 vai por Responses com reasoning.effort; Opus 5.5 sem tool_choice forçado
G5  histórico: 3 rodadas de tool com raciocínio preservado (dublê do provedor exige o bloco de volta — sem ele, 400)
G6  sem turno refeito por "connection" depois de tool com efeito: efeito conta 1 no dublê (mutação: restaurar o retry ⇒ 2 ⇒ VERMELHO)
G7  reserva: 429/500/timeout ANTES da 1ª tool com efeito → reserva de outro provedor, ledger com motivo; DEPOIS → retém, 0 refação
G8  ledger: toda chamada dos 34 call sites grava papel+pedido+resolvido+real (atlas, portal, distiller inclusos); preço
    desconhecido grava custo NULO + alerta, nunca o do mini
G9  nascimento: provisionar corretora (dublê) → nenhum agente/memória/auxiliar com id BLOCKED; dois tenants isolados
G10 bancada: um run registra braço, commit, custo, tokens, latência, resultado por caso; pass^k calculado; teto de US$ corta
G11 bancada rodada: baseline + ≥ 6 braços vivos por papel P0; relatório com pass@1, pass^k, custo/sucesso, p50/p95
G12 mapa Onda A aplicado por migration de DADO com rollback = linha anterior do histórico; bateria sem regressão nominal
G13 rotas montam + next start + 1 GET /api/… (tocou app/, CLAUDE.md §9.1)
G14 🧑 canário do atendimento com o mapa novo — roteiro entregue; execução depende de religar o atendimento (Founder)
```

## 10. Decisões tomadas na conversão (nota 0–100; diferença grande = já decidida)

| # | decisão | notas |
|---|---|---|
| D-116-01 | nome canônico **Model Router** (SPEC-052 §14), não "Model Fabric" | Router **95** · Fabric 40 (colide com Intelligence Fabric) |
| D-116-02 | catálogo = **`llm_pricing` expandido** + snapshot gerado | expandir **88** · catálogo em código 74 · YAML 70 · tabela nova 30 (motor paralelo) |
| D-116-03 | rotas por PAPEL no banco (`llm_papeis` + histórico); código pede papel | banco **88** · env por serviço (hoje, 12 envs) 50 · no código 45 (rollback = deploy) |
| D-116-04 | bancada **estende a Eval Fabric** SPEC-062 | estender **95** · `bench_*` 10 |
| D-116-05 | ordem **arnês → baseline → candidatos → mapa** | **92** · bancada antes do arnês 45 · trocar e medir depois 20 |
| D-116-06 | em produção agora: **OpenAI + Anthropic** (API paga, DPA, sem treino). Google após chave local + tier pago confirmado. xAI/MiMo/DeepSeek/Z.ai/Kimi: **laboratório com dado sintético**, BLOCKED para PII (EVIDENCIAS/05 §4: China/Singapura, sem cláusulas-padrão ANPD) | **90** · liberar por benchmark 25 |
| D-116-07 | reserva declarada, **só antes da 1ª tool com efeito**; depois retém | **85** · `with_fallbacks` 68 · sem reserva 70 |
| D-116-08 | SDK por necessidade (§8); checkpoint 4 condicionado à medição | **86** · subir tudo 40 · não subir nada 55 |
| D-116-09 | bancada ao vivo com **teto US$ 100** no código; teto de qualidade só no crítico | **85** · sem teto 50 · teto US$ 20 (k=1, sem variância) 45 |
| D-116-10 | classes de dado `publico · interno · pii`; rota declara a sua; modelo declara as permitidas; Fable/Mythos sem `pii` (retenção obrigatória de 30 d, sem ZDR) | **88** · sem classe 30 |
| D-116-11 | lifecycle em dois passos: legado vira **DEPRECATED** já (gate avisa) e **BLOCKED** só depois que a bancada provar o substituto do papel (F6 da proposta) | **90** · bloquear já 40 (troca cega) |
| D-116-12 | embeddings `text-embedding-3-small` **KEEP** com justificativa medida: OpenAI não tem sucessor; troca = reindexação + eval de retrieval | **85** · trocar por gemini-embedding-2 agora 35 |
| D-116-13 | transcrição: `whisper-1` desliga 26/02/2027 → bancada PT-BR `gpt-transcribe` × whisper; promove se não-inferior | **80** |
| D-116-14 | modelos do DESENVOLVIMENTO (protocolo §10 cita Fable 5.1/Opus 5/Sonnet 5): **não mexo no protocolo**; dívida registrada para o Founder | **90** |
| D-116-15 | (execução) `memory_settings.memory_llm_model` vira **legado ignorado**: a rota `memoria` manda sempre. Zerar o dado/DEFAULT antes do deploy quebraria a memória no código antigo em produção | rota manda + coluna legada **90** · migration de dado já 35 |
| D-116-17 | (execução) precedência: **rota do papel vence o modelo gravado no agente**; agente só manda em papel sem rota | rota vence **90** · agente vence 40 (8 agentes com Sonnet 5 gravado travariam toda troca) |
| D-116-16 | (execução) F5a começou em PARALELO à F1 (arquivos disjuntos; contrato `ModeloResolvido` declarado no pacote) — antecipa a fatia mais longa | **85** · esperar a F1 60 |

## 11. Pré-requisitos de API (o que só o Founder faz — nunca colar chave no chat)

| provedor | modelos | chave existe? | o que falta | onde a chave mora | recomendação |
|---|---|---|---|---|---|
| OpenAI | GPT-6 Sol/Luna/Astra, gpt-transcribe | ✅ prod + local | nada para a bancada · **ZDR/"Modified Abuse Monitoring" via vendas** para PII viva | EasyPanel `OPENAI_API_KEY` | API nativa |
| Anthropic | Opus 5.5, Sonnet 5, Haiku 4.5 | ✅ prod + local | nada · **ZDR via vendas** (não cobre Fable/Mythos) | `ANTHROPIC_API_KEY` | API nativa |
| Google | Gemini 3.8 Flash, 3.8 Live | ✅ prod · ❌ local | colar `GOOGLE_API_KEY` no `backend/.env` local · confirmar que o projeto está no **tier PAGO** (o gratuito treina com os dados) | EasyPanel + `backend/.env` | API nativa, `store=false` |
| xAI | Grok 4.7 | ❌ | conta em console.x.ai + billing · só laboratório | `XAI_API_KEY` | nativa, endpoint EUA |
| Xiaomi | MiMo V2.6 Pro/Flash | ❌ | conta + billing · só laboratório (PII bloqueada) | `MIMO_API_KEY` | via host com ZDR, se houver |
| DeepSeek | V4.1 Flash | ❌ | **não usar a API nativa** (dados na China); se quiser testar: host EUA com ZDR (Fireworks/Together) | `FIREWORKS_API_KEY` | host terceiro |
| Z.ai | GLM 5.3 / 5.3 Flash | ❌ | conta + billing · laboratório | `ZAI_API_KEY` | nativa (Singapura, ZDR disponível) |
| OpenRouter | agregador | variável vazia | opcional; só laboratório; ZDR por rota | `OPENROUTER_API_KEY` | não para caminho crítico |

## 12. O que o estado da arte faz, e o que modelamos (§7.3)

- **τ²-bench / pass^k** · https://github.com/sierra-research/tau2-bench · agente com tools diante de usuário em
  domínio com políticas; mede confiabilidade por pass^k · **modelamos:** pass^k como métrica de papel crítico ·
  **rejeitamos:** usuário simulado por LLM como oráculo (nosso segurado é roteirizado de rajadas reais) · **juiz:**
  roda `bancada.py --relatorio` e confere pass^k = todas as k passaram, caso a caso.
- **OpenAI GPT-6 Sol (Responses + reasoning)** · https://developers.openai.com/api/docs/models/gpt-6-sol · tools com
  raciocínio só na Responses API · **modelamos:** `api_surface` no catálogo e adaptador Responses com `store=False` ·
  **rejeitamos:** `previous_response_id` (estado no servidor alheio; nosso estado é o checkpointer) · **juiz:** payload
  do teste G4.
- **Anthropic effort + mudanças do Opus 5.5** · https://platform.claude.com/docs/en/build-with-claude/effort e
  https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5 · **modelamos:** effort nativo, sem sampling,
  sem `tool_choice` forçado · **rejeitamos:** desligar thinking · **juiz:** G4 com Opus 5.5.
- **Catálogo de preço+capacidade (LiteLLM)** · https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json ·
  um registro por modelo com preço e capacidades · **modelamos:** o formato de capacidades · **rejeitamos:** usá-lo como
  fonte de preço (o preço vem da página do provedor, com URL e data) · **juiz:** `select fonte_preco_url, preco_verificado_em`.
- **Idempotência Stripe** · https://docs.stripe.com/api/idempotent_requests · **modelamos:** reserva nunca refaz efeito
  (G6/G7) · **rejeitamos:** nada · **juiz:** contagem de efeitos no dublê.
