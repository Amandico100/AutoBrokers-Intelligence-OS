# SPEC-116 · Cada trabalho no modelo que provou servir — relatório de execução

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — o da SPEC §0, com o que mudou na execução

```
OUTCOME ..............  cada TRABALHO (papel) pede modelo a UM resolvedor que lê UM catálogo governado; nenhum modelo
                        velho escondido decide; a BANCADA E2E (Eval Fabric) mede no motor real e o mapa sai dela
RISCO ................  8 = alcance 3 + reversibilidade 3 + frequência 2
SUPERFÍCIE ...........  3 (📊 34 call sites, 19 por fora da fábrica, 11 catálogos, 3 serviços)
PISO APLICADO ........  §3.2: migration de ESTRUTURA + caminho que ENVIA (atendimento/portal) → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus xhigh · juiz Fable ‖ red team Fable · confirmação (houve blocker)
O FIO ................  SPEC §4 · backend/tests/test_o_fio_do_modelo.py (1ª entrega da F1)
PARALELISMO REAL .....  F1 ‖ F5a (D-116-16) → F2 ‖ F4 → F3a ‖ F3b → F5b (costura) → F6 → conserto único
UNIDADES .............  U1–U14 (SPEC §6); U13 PARCIAL (crédito), U14 escrita e armada
COESÃO ...............  catálogo+resolvedor+gate (contrato ModeloResolvido) · fábrica+histórico+relógio+callback (hub
                        llm_factory) · call sites em F3a/F3b (consomem o contrato)
TIME .................  4 investigadores · 8 builders · F6 · juiz ‖ red team · conserto · confirmação · docs = 17 agentes
REFERÊNCIA ...........  interna: Eval Fabric SPEC-062 (backend/app/services/evals/) · externa: SPEC §12 (5 URLs)
GATES ................  G0–G12 verdes após o conserto (G11/G12 PARCIAIS: crédito) · G13 rotas montam · G14 🧑
O ELO ................  "X decide Y PORQUE o resolvedor devolve X": o fio lê o payload construído PELA FÁBRICA; o ledger
                        grava pedido × resolvido × real; a bancada monta o braço pela mesma fábrica
FAIXA DE RELÓGIO .....  declarada 💭 18–28 h · real 📊 ≈ 9 h (§12)
```

**SPEC** `specs/SPEC-116-cada-trabalho-no-modelo-que-provou-servir.md` · **Branch** `spec/116-model-router-e2e-bench` ·
**Preflight** 📊 23/09: `HEAD..origin/main` 0 · `origin/main..HEAD` 0 · base `543cc82` · **último commit de código**
`be8b033` · 📊 `git diff --shortstat 543cc82 be8b033` → **146 arquivos · +336.058 · −2.145 · 13 commits** (≈ 317 mil linhas
são os JSONs de resultado da bancada). **Estado:** CONCLUÍDA COM MEDIÇÃO PARCIAL — Onda A parcial.

## 1. O que mudou, em uma tela
Antes: 📊 19 de 34 chamadas a modelo iam **por fora** da fábrica; a corretora nova nascia com o atendente em
`gpt-4o-mini` travado; a foto do segurado era lida por `gpt-4o-mini` **duas vezes** por turno; o portal decidia em `gpt-4o`
e **caía calado** no mini em qualquer erro, fora do ledger; o esforço gravado nunca chegava ao Claude; os auxiliares de
resumo/follow-up estavam **quebrados desde 07/08**; o turno inteiro era refeito por "connection" (tool com efeito 2×);
o juiz de eval nunca rodou; fallback de visão para modelo retirado; `attendance_media` sem filtro `company_id`; preço do
Sonnet 5 errado (3/15 × real 2/10); 11 catálogos. **Todos consertados.** Agora: 25 papéis, 1 catálogo (74 modelos com
preço, fonte e ciclo de vida), 1 resolvedor que **erra em vez de cair no mini**, troca e volta de modelo = 1 linha no banco.
⚠️ Correção honesta do BLOCO 0: o destilador **aparecia** no ledger (como `chat`, sob a empresa técnica, fora da janela de
45 d) — o defeito era o rótulo; agora grava como `plataforma` (SPEC B0.7).

## 2. As fatias
| fatia | o que entregou | commit |
|---|---|---|
| F1 | `llm_pricing` expandido + `llm_papeis`/histórico + resolvedor + snapshot + legacy gate + teste do fio | `3b25f2f` |
| F5a ‖ F1 | bancada sobre a Eval Fabric: runner, dublês, injeção de falha, teto de US$, pass^k; corpus v1 (156 casos, 11 papéis) | `f7ae730` |
| F4 ‖ F2 | agentes/sandbox/auxiliares/releases nascem **sem modelo**; admin lista o catálogo pela API e mostra o modelo efetivo | `c383c09` |
| F2 | adaptadores (effort nativo no Claude; GPT-6 pela Responses, `store=False`; Opus 5.5 sem `tool_choice` forçado), histórico com raciocínio, fim do retry de turno com tool, reserva só antes da 1ª tool, ledger pedido/resolvido/real, SDKs | `9eb0b0e` |
| F3a ‖ F3b | segurado: visão 1 chamada/foto, memória, HyDE, chunking, embedding, transcrição, rerank pela rota; auxiliares consertados; `attendance_media` com `company_id` · plataforma: dispatch, atlas, destilador, lapidador, juízes, extrator, marca, garimpo, sugestões, conselho pela rota; portal sem rebaixamento calado e no ledger | `168e401` · `5c34a77` |
| F5b | costura: bancada com resolvedor e fábrica **reais**; ledger `bancada` sem empresa, disjuntor intocado | `8518613` |
| F6 | bancada ao vivo (corpus v2/v3), resultados, EVIDENCIAS/06 | `b2de585` |
| mapa | Onda A parcial (migration `_04`) · D-116-18 registrada | `820b5d1` · `8909de2` |
| conserto | C1–C9 (§5) + migration `_05` | `be8b033` |

📊 Arquivos por área (`git diff --name-status 543cc82 be8b033`): backend 7 novos/44 alterados · testes py 15/11 · testes js
1/2 · frontend 0/10 · migrations 4/0 · corpus 44/0 · docs 7/0 · docling 0/1.

## 3. Migrations — as quatro APLICADAS em produção (📊 `supabase_migrations.schema_migrations`)
| arquivo | versão | APPLY | VERIFY (conferido) | ROLLBACK |
|---|---|---|---|---|
| `20260923_01_spec116_catalogo_e_papeis` | 20260923141248 | +15 colunas anuláveis e 4 CHECKs em `llm_pricing`; multiplicadores 5,2→9,6; catálogo; `llm_papeis` + histórico + trigger; RLS só leitura; seed = runtime de 23/09 | 📊 74 linhas: APPROVED 7 · BLOCKED 3 · CANDIDATE 14 · DEPRECATED 14 · HISTORICAL 36; 25 rotas v1, 0 proibidas (reproduzido pelo juiz) | drop das tabelas/colunas, delete das 24 linhas novas por nome, preços antigos. ⚠️ o resolvedor cai no snapshot — voltar de verdade = imagem anterior |
| `_03_spec116_bancada_na_eval_fabric` | 20260923143330 | só ADD COLUMN em `eval_runs`/`eval_case_results` + 3 CHECKs + 1 índice | bloco DO aborta se faltar algo: "VERIFY OK — 14 colunas…" | drop por nome exato (apaga a série medida) |
| `_04_spec116_mapa_onda_a` | 20260923200120 | 3 UPDATEs em `llm_papeis` + `gpt-5.6-terra` → `responses` | 📊 histórico 3 linhas v2 (memoria/visao/portal), `alterado_por 'migration 20260923_04'` | UPDATE para a linha anterior (o trigger registra a volta) |
| `_05_spec116_rota_so_aceita_modelo_governado` | 20260923214100 | trigger BEFORE INSERT/UPDATE: modelo no catálogo, provedor igual, ciclo usável, classe de dado, esforço | 📊 25 rotas passam · 0 recusadas; UPDATE para `claude-3-5-sonnet-20241022` **recusado** dentro de SAVEPOINT | drop do trigger e da função |

`_02` **não existe** (D-116-15). Nenhuma é destrutiva; nenhuma toca dado de corretora.

## 4. O MAPA DE MODELOS FINAL (📊 23/09, `modelos_snapshot.json` origem banco · bancada k=3, EVIDENCIAS/06)
| Função (papel) | Primary | Effort | Fallback | Por quê | E2E | Custo/sucesso US$ |
|---|---|---|---|---|---|---|
| Chat principal (`chat_principal`) | claude-sonnet-5 | padrão | nenhum | mantido — N2 sem medição válida (crédito) | N1 97,8 % · N2 90 % (14 infra) | 0,0049 |
| Atendimento WhatsApp (`atendimento`) | claude-sonnet-5 | padrão | nenhum | mantido — N2 sem medição; Luna 80,9 % no N1 com crít^k sobre só 2 casos | N1 68,9 % crít^k 50 % | 0,0132 |
| Cobrança (agente de atendimento) | claude-sonnet-5 | padrão | nenhum | mantido — **nenhum** braço elegível (crít^k 100 %) | 50 % crít^k 40 % | 0,0246 |
| Portal de vidros (`portal_decisao`) | **gpt-6-sol** | **medium** | nenhum | **trocado** (era gpt-4o); D-116-18: P0 empatado → maior margem; Luna medium 45/45 = desafiante Onda B | 43/43 × 38/41 | 0,0014 |
| WhatsApp seguradora (`dispatch`) | claude-opus-5 | padrão | nenhum | mantido — medição inválida (o motor engolia o erro do provedor; consertado, não remedido) | inválido | — |
| Memória (`memoria`) | **gpt-6-luna** | **low** | nenhum | **trocado** (era gpt-4o-mini) pela régua de custo (P1, volume) | 39/45 × 32/45 | 0,0001 |
| Visão da foto (`visao`) | **gpt-6-sol** | **low** | nenhum | **trocado** (era gpt-4o-mini); imagens SINTÉTICAS | 30/30 × 28/30 | 0,0016 |
| Documento (`visao_documento`) · docling | gpt-4o-mini · env `VISION_MODEL` | — | — | mantido — não medido (sem corpus de PDF); docling lê env | — | — |
| Research | — | — | — | não chama modelo próprio (📊 `grep LLMFactory app/services/research` → 0) | — | — |
| Juiz de eval (`juiz_eval`) | claude-sonnet-5 | — | — | mantido — não medido (sem ouro); **consertado** (nunca rodava) | — | — |
| Atlas (`atlas_parser`) | claude-opus-5 | — | — | mantido — não medido; agora no ledger | — | — |
| Destilador · forte | claude-sonnet-5 · claude-opus-5 | — | — | mantido — não medido | — | — |
| Lapidador (`prompt_optimizer`) · juiz de playbook | claude-opus-5 · claude-opus-5 | — | — | mantido — não medido | — | — |
| Extrator de planos · marca · garimpo | claude-sonnet-5 (os três) | — | — | mantido — não medido (sem ouro) | — | — |
| Sugestões · conselho (líder) | claude-opus-5 · claude-opus-5 | — | — | mantido — não medido | — | — |
| Auxiliar | claude-haiku-4-5-20251001 | — | — | mantido — retirada ≥ 15/10/2026 (P-S116-07) | — | — |
| Subagente | claude-sonnet-5 | — | — | mantido — não medido | — | — |
| HyDE · chunking agêntico | gpt-4o-mini (DEPRECATED) | — | — | mantido — sem ouro; agora pela fábrica e no ledger | — | — |
| Embedding | text-embedding-3-small | — | — | KEEP (D-116-12: sem sucessor; troca = reindexar) | — | — |
| Rerank | cohere rerank-multilingual-v3.0 | — | — | mantido — não medido | — | — |
| Transcrição | whisper-1 (DEPRECATED) | — | — | mantido — sem áudio-ouro e sem adaptador STT; desliga 26/02/2027 | — | — |

🔴 **Reserva vazia em todas as 25 rotas:** os braços Anthropic não foram medidos depois de 19:18Z (P-S116-02).

## 5. O julgamento — 1 rodada paralela, cegos, e um conserto único
⚖️ **Juiz Fable 74/100** "aprovada com ressalvas" · 🗡️ **Red team Fable 78/100** "QUEBREI". Laudos inteiros fora do repo.

| # | quem | achado | conserto (`be8b033`) |
|---|---|---|---|
| 1 | 🗡️ **EXCLUSIVO** | 🔴 cache de prompt decidido pelo provedor **gravado**: agente novo (F4, `llm_provider` NULL) + rota Anthropic ⇒ **sem cache**, input cheio a cada turno | C1 cache pelo provedor da ROTA; log grava provedor/modelo reais |
| 2 | ⚖️ + 🗡️ | bateria da SPEC vermelha no HEAD: 12 testes afirmavam a constante do seed depois da `_04` | C2 testes leem a rota |
| 3 | ⚖️ **EXCLUSIVO** | D-116-18 aplicada e não registrada | `8909de2` |
| 4 | ⚖️ + 🗡️ | 31 linhas `portal` de teste no ledger de produção | C4 portal não grava sem job/empresa nem em pytest; DELETE = 🧑 (P-S116-11) |
| 5 | 🗡️ | G1 carimbo (sobrevivia sem `COHERE_API_KEY`) | C3 fio sem carimbo + gate de literais conhecidos |
| 6 | 🗡️ | rota com modelo BLOCKED gravada direto cala todas as corretoras | C5 trigger (`_05`), provado em produção |
| 7 | ⚖️ + 🗡️ | "testar conexão" por fora da fábrica; POST de agente sem validar modelo | C6 · C7 |
| 8 | bancada (F6) | oráculo reprovava negação ("Não é golpe") | C8 |
| 9 | bancada (F6) | 🔴 laço de **7 consultas forçadas** de apólice no Chat Principal (`POLICY_INTELLIGENCE_V2` ligada em prod) | C9: ≤ turnos + 1 |

📊 Depois do conserto: **241 testes verdes em 3 ordens · 8/8 mutações vermelhas**. 📊 Exclusivos: juiz 1 · red team 4 · bancada 2.

### 5.1 CONFIRMAÇÃO (§6.1)
📊 juiz novo (Fable, 21 turnos, só o diff `8909de2..be8b033`): **o conserto NÃO criou defeito · 0 blockers · nota 90/100** · 146 testes verdes nos 9 arquivos tocados · trigger aceitou 6/6 trocas legítimas e recusou a inválida (DO-bloco revertido) · C9 não impede consulta legítima numa 2ª pergunta · C4: job real (job_id+empresa) continua gravando. Pendências (nenhuma muda byte): `para_teste_de_conexao` usa 8192 tokens de saída (custo) · OpenRouter sempre "não governado" no testar conexão (0 modelos/agentes openrouter) · trigger não cobre `llm_pricing` · heurística de negação olha 2 palavras.

## 6. SDKs (D-116-08)
langchain-core 1.6.4 · langchain-anthropic 1.7.3 · langchain-openai 1.6.4 · langgraph 1.2.12 · langgraph-checkpoint **4.2.0**
(fecha CVE-2026-27794 e -48775; 📊 40/40 checkpoints reais abriram) · pins exatos openai 2.54.0 · anthropic 0.125.0 · httpx 0.27.2 ·
checkpoint-postgres 3.1.2. 📊 `uv pip compile` para Python 3.11 → 196 pins, todos com wheel. O build real da imagem é no deploy.

## 7. A bancada — o que custou e por que parou
📊 corpus v3 · 156 casos · 11 papéis · gasto ao vivo **≈ US$ 11,97** (ledger `service_type='bancada'`, sem empresa, não
faturado) · parou por **crédito zerado**: Anthropic 19:18Z, OpenAI 19:41Z. 🔴 As chaves locais são as **mesmas** de produção.
Fumaça dos builders ≈ US$ 0,10. Rate limit por 4 processos em paralelo = falha de método da F6, não do modelo.

## 8. INCIDENTE (resolvido) — o pooler que ficou só-leitura
📊 Uma conexão do pooler Supabase (porta 6543, modo transação) ficou com `default_transaction_read_only=on`, vazado de um
script de medição desta execução; o pooler a entregava a quem conectava (12/12 sondas). Encerrada por
`pg_terminate_backend` ≈ 20:00Z; depois, 20/20 sondas limpas. Impacto medido: 0 checkpoints de agente nas 10 h (não
havia turnos); o espelho grava por REST (não afetado). **Lição:** script de medição nunca usa `SET` de sessão pelo
pooler — só `SET TRANSACTION`/`SET LOCAL`.

## 9. AS LLMs ANTIGAS QUE SAÍRAM
| modelo legado | onde estava | por que saiu | substituto | prova |
|---|---|---|---|---|
| gpt-4o-mini | memória (DEFAULT da coluna, 8/8) | 📊 32/45 | gpt-6-luna low | 39/45 |
| gpt-4o-mini | foto do segurado (`describe_image` sem agente), 2×/turno | 📊 28/30 | gpt-6-sol low | 30/30 · 1 chamada/foto |
| gpt-4o | portal decide o clique | 📊 38/41 | gpt-6-sol medium | 43/43 |
| gpt-4o-mini | reserva calada do portal em erro ≥ 400, fora do ledger | 📊 39/45 | nenhum: erro ⇒ `ask_human` | 4 testes (429/500/503/404) |
| openai/gpt-4o-mini | atendente de toda corretora NOVA, travado | modelo velho decidindo | rota `atendimento` | 📊 `spec116-f4-nascimento.test.mjs` 32/0 |
| `else → gpt-4o-mini` · `or "gpt-4o"` | fábrica, agente sem modelo | fallback silencioso | `ModeloNaoResolvido` | `test_o_fio_do_modelo.py` |
| claude-3-5-sonnet-2024xxxx | fallback de visão, dropdown do admin | retirado da API 28/10/2025 | BLOCKED + trigger | UPDATE recusado em prod |
| Claude num `ChatOpenAI` | auxiliares resumo/follow-up | quebrados desde 07/08 | rota `auxiliar` no cliente certo | testes F3a |
| gpt-4o (default de código) | sugestões | modelo velho no default | rota `sugestoes` | legacy gate |
| gpt-5.1 | tabela de preço própria do Atlas | fora do catálogo | rota `atlas_parser` | legacy gate |

## 10. LISTA RESIDUAL — literais que ficaram (📊 `rg -n "gpt-4o-mini|gpt-4o\"|claude-3-5" … -g '!**/tests/**'` + `LITERAIS_CONHECIDOS`)
| arquivo:linha | literal | categoria | motivo |
|---|---|---|---|
| `docling-service/app/config.py:28` · `.env.example:30` | gpt-4o-mini | default de env de outro serviço | trocar = `VISION_MODEL` no EasyPanel (P-S116-09) |
| `backend/app/core/constants.py:77` | claude-haiku-4-5-20251001 | coluna legada ignorada | D-116-15 |
| `backend/app/services/benchmark_service.py:88,96` | gpt-4o · gpt-4o-mini | benchmark de RAG do admin | ALLOWLIST do guarda, fixo por desenho |
| `attendance_distiller.py:637` · `global_knowledge_seed.py:59` · `insurance_corpus.py:1119` | text-embedding-3-small | embedding direto | = rota `embedding`, KEEP (D-116-12) |
| `llama_guard_service.py:71` | meta-llama/llama-prompt-guard-2-86m | guardrail Groq | desligado sem chave (P-S116-13) |
| `app/admin/finops/plans/page.tsx:9,427` | gpt-4o-mini | texto de estimativa na tela | não escolhe modelo; copy vencida (P-S116-23) |
| `modelos_snapshot.json` | catálogo + rotas `hyde`, `chunking_agentico`, `visao_documento` | dado governado | DEPRECATED, sem ouro para trocar |
| 19 comentários/docstrings (vision, search, memory, ingestion, portal ×4, factory ×2, cost_callback, council, webhook, `lib/admin` ×4, bootstrap) | vários | história do conserto | não executam |

## 11. FATO · INFERÊNCIA · RECOMENDAÇÃO
**FATO** 📊: 4 migrations aplicadas; 3 rotas trocadas com histórico; 241 testes verdes; bancada US$ 11,97; crédito zerado nos
dois provedores às 19:18Z/19:41Z; canário não rodou. **INFERÊNCIA:** se a chave de produção é a mesma, **o produto está sem
provedor** até o crédito voltar (memória, visão, portal, chat); no atendimento N1 até o teto (Astra high) erra casos
críticos ⇒ parte da falha é de prompt/arnês. **RECOMENDAÇÃO:** recarregar o crédito antes do Implantar; rodar a bancada N2 e o
dispatch **um processo por provedor**; só então decidir chat/atendimento/cobrança e preencher as reservas.

## 12. Canário, riscos e o que ficou fora
**Canário** Amandus → Resulta → AutoFleet: **NÃO RODOU** — crédito zerado + atendimento desligado desde 10/09 (G14 🧑).
**Riscos:** produto sem provedor até recarregar · reserva vazia em todas as rotas · rota Anthropic ativa sem cache se o C1
regredir · Python 3.11 provado só por `uv pip compile` · janela de deploy (backend antes do admin). **Fora:** P-S116-01…27 em
`PENDENCIAS.md`. **Pendências tocadas:** P-E0018-17 (juiz de eval) **FECHADA** — `juiz_llm.julgar_com_llm(llm=)` consertado na F3b ·
P-E0015-06 **CONTINUA** — o laço com a flag ligada foi consertado (C9); o valor em prod segue não medido · P-E00110-A17
**CONTINUA** — o portal não grava em pytest (C4), a trava geral de "teste não alcança o banco real" falta (P-S116-11).
**Nenhum motor paralelo:** catálogo = `llm_pricing` expandido · rotas = Model Router da SPEC-052 §14 · bancada = Eval Fabric
da SPEC-062 · portal = cliente fino governado pelo mesmo catálogo · reserva = o disjuntor que já existia (`relogio_do_modelo`).

## 13. 📋 Caixa do Founder (detalhe em `TAREFAS-DO-FOUNDER.md`, seção SPEC-116)
1. 🔴 recarregar crédito Anthropic e OpenAI + recarga automática · **bloqueia o produto**.
2. Implantar `smith-api` → `smith-worker` → `portal-worker` (Dockerfile mudou) → `smith-web`.
3. Trocar as chaves coladas no chat · 4. ZDR (opcional) · 5. Gemini local (opcional) · 6. docling `VISION_MODEL` ·
7. apagar envs ignorados · 8. decidir o DELETE das 31 linhas · 9. religar o atendimento para o canário.

## 14. BATERIA
rodadas: **1** (depois do conserto, 2º plano, `backend/.venv` com as libs NOVAS) · 📊 **36 failed · 1454 passed · 1 skipped · 34 xfailed · 1 xpassed** em 3.137 s. Triagem nominal contra a base de 21/09 (35):
- **3 novas:** `test_o_guarda_script_passa[test_o_vocabulario_viaja_na_imagem]` — **DA SPEC** (`evals/bancada.py` com `parents[3]`), consertada (raiz sai do pacote `app`) e reconferida isolada: 40 verdes / 0 vermelhas · `test_o_fio_inteiro_do_isolamento` e `test_so_um_agendador_manda` — passam **isoladas** (📊 1 passed cada); falham só na bateria longa (ordem/tempo) → ficam na base, marcadas.
- **2 sumiram:** `test_o_protocolo_tem_policia` · `test_a_arvore_ficou_limpa_no_fim`.
- `BATERIA-LINHA-DE-BASE.txt` regravado: 35 nomes.
- ⚠️ G13 (app/): a F4 rodou `npm run test:rotas-montam` (303 rotas montam) · `npm run build` exit 0 · `next start` Ready · `GET /api/admin/proxy/agent/providers` → 401 JSON (código roda, sem 500).

## 15. Entrega (saída do `git push origin HEAD:main`, 23/09 ~22:50Z)
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   543cc82..03efadb  HEAD -> main
atras=0 · afrente_depois=0
```
Depois deste relatório, 1 commit a mais (esta seção) empurrado do mesmo jeito. 🧑 Falta o Implantar (TAREFAS S116.2).

## 16. Telemetria (§11) — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`
```
relógio ......................... 📊 executor 12:47Z → (aberto) 536 min na leitura das ~21:45Z · faixa 💭 18–28 h
por agente (min · turnos · pico) . censo 24·120·271k · arquitetura 27·93·309k · mercado 11·45·229k e 20·88·264k ·
                                  F1 26·53·320k · F5a 46·105·490k · F2 133·177·486k · F4 89·133·350k · F3a 89·179·451k ·
                                  F3b 93·151·400k · F5b 33·95·305k · F6 75·160·430k · juiz 44·30·324k · red team 32·21·284k ·
                                  conserto 49·148·334k · confirmação (em curso) · docs (em curso)
executor ........................ 152 turnos · pico 600 k (teto CRÍTICO 300 k ESTOURADO) · modelo opus-5-5
ctx-tokens · saída .............. 453,8 M · 0,35 M
US$ API-equivalente ............. executor 45,67 · F2 33,14 · F3a 29,26 · F6 24,52 · F3b 22,53 · F4 18,45 · F5a 18,20 ·
                                  conserto 18,03 · F5b 12,01 · investigação 34,12 · F1 7,98 · juiz 5,95 · red team 4,46 →
                                  total ≈ US$ 277,96 (+ bancada US$ 11,97 em API real)
agentes além do executor ........ 17 de 24
achados por mecanismo ........... BLOCO 0: 11 de produto · bancada 2 (laço de consulta, oráculo) · juiz 1 EXCLUSIVO ·
                                  red team 4 EXCLUSIVOS · 3 pelos dois · canário: NÃO RODOU
rodadas da bateria .............. 1 (36 failed · 3 novas triadas: 1 da SPEC consertada, 2 de ordem)
notas ........................... juiz 74/100 · red team 78/100 · confirmação 90/100 · nota da execução 84/100 (critério: o fio inteiro está no ar e provado por máquina; o mapa ficou PARCIAL porque a bancada parou por crédito)
```
⚠️ Quebras declaradas: contexto do executor em 600 k (teto CRÍTICO 300 k; autorização permanente nº 3 do Founder) · o
gerente rodou em Opus 5.5, não Fable 5.1 (protocolo §10) · a F6 rodou 4 processos em paralelo e perdeu medição por rate
limit.
📊 **Releitura no fecho (script, 23/09 22:43Z):** executor 596 min · 168 turnos · pico 622 k · US$ 50,93 (opus-5-5) · 17 agentes · 1.848 turnos · ctx 474,2 M · saída 0,37 M · **total US$ 289,51** API-equivalente (juiz 5,95 · red team 4,46 · confirmação 1,45 · atualizador 8,48) + bancada US$ 11,97 em API real.
