# SPEC-EXTRA-001.0 — RESEARCH PACK
## As cinco entregas de 08–10/09 que entraram sem SPEC — as evidências

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão; **não** é relatório de execução.
**Árvore medida:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`, branch `docs/diagnostico-pilotos-0912`, HEAD `a0bb5fe`.
**Método:** `git` local, leitura de arquivo com `arquivo:linha` reaberto hoje, execução de guardas existentes e um script read-only de impressão digital. **Nenhuma alteração de produto, nenhum SQL, nenhum envio, nenhum portal.**

---

## 0. Legenda e precedência

- **📊 MEDIDO** — tem data, comando e saída. Citável.
- **💭 ILUSTRATIVO** — estimativa ou exemplo. **Nunca citável como fato.**
- **OBSERVADO NO REPO** — existe no código nesta revisão; não prova comportamento em produção.
- **PENDENTE DE MEDIÇÃO** — precisa de comando que não rodei.
- **FONTE EXTERNA** — padrão documentado; não determina a arquitetura interna.

🔴 **As coordenadas `arquivo:linha` abaixo foram reabertas em 13/09/2026.** Elas envelhecem a cada commit. O BLOCO 0 as reconfere; divergiu, corrige e anota.

---

## 1. O preflight, medido

📊 13/09/2026:

```
$ git branch --show-current      -> docs/diagnostico-pilotos-0912
$ git rev-parse HEAD             -> a0bb5fef440eba394a9275671b1143f5025807ef
$ git rev-list --count HEAD..origin/main   -> 0
$ git rev-list --count origin/main..HEAD   -> 0
$ git status --short             -> 4 arquivos não rastreados (propostas 097/098), nada mais
```

📊 **O que entrou depois do intervalo:** `git log --oneline 05f46a9..a0bb5fe` → **2 commits**, `b1e18f8` e `a0bb5fe`, ambos `docs(pilotos)`; `git diff --stat 05f46a9 a0bb5fe` → **2 arquivos** (o diagnóstico e o dossiê), **1.017 inserções**. 🔴 **Consequência:** nenhum arquivo de produto dos cinco pacotes foi tocado depois de `05f46a9`. A descrição dos cinco vale até HEAD.

---

## 2. O intervalo, commit a commit

📊 `git log --format='%h %ad %s' --date=format:'%d/%m %H:%M' cffaa0e..05f46a9` · **22 commits** · 13/09/2026.

| # | SHA | quando | pacote | assunto (abreviado) |
|---:|---|---|---:|---|
| 1 | `e77f1c2` | 08/09 20:43 | **1** | docs(pilotos): plano de ajustes da véspera, 12 P-PILOTO-*, 7 D-PILOTO-* |
| 2 | `936d9dd` | 08/09 20:57 | **1** | feat(portal): Conectores > Portais mostra todos os acionamentos |
| 3 | `4454599` | 08/09 21:03 | **1** | feat(portal-worker): prova em todo desfecho, url/tela/ts por passo |
| 4 | `46743ca` | 08/09 21:05 | **1** | test(portal-worker): M24 procura a CHAMADA do freio depois do laço |
| 5 | `21c5ed9` | 08/09 21:10 | **1** | fix(acionamento): dossiê em português · trava de laço do formulário (P-092-10) |
| 6 | `b433a9f` | 08/09 21:32 | **1** | feat(pós-acionamento): follow-up 8h–19h (D-PILOTO-04) · cartas GLOBAIS (D-PILOTO-01) |
| 7 | `f3f9031` | 08/09 21:35 | **1** | fix(acionamento): `formulario_envio_falhou` colado ao `needs_human` |
| 8 | `fce1098` | 08/09 21:40 | **1** | feat(atendimento): foto até 16 MB · `to_thread` · buffer em paralelo |
| 9 | `e149b66` | 08/09 21:42 | **1** | docs(pilotos): resultado da execução de 08/09 no plano |
| 10 | `9e75d9f` | 09/09 20:14 | **2** | docs(pilotos): plano do handoff e da pausa (3 causas raiz, N=7) |
| 11 | `b1f6f57` | 09/09 20:40 | **2** | fix(suporte-humano): destino resolve pelo SELETOR; outro tenant = 404 |
| 12 | `c36e9a3` | 09/09 20:43 | **2** | feat(agente): membros ligam/desligam o agente da própria corretora |
| 13 | `1b64d81` | 09/09 20:47 | **2** | fix(handoff): falha deixa rastro em `agent_activities`; `/health` lista |
| 14 | `ba9688e` | 09/09 20:51 | **2** | feat(atendimento): motor da janela de silêncio (N=7) + bloco de reencontro |
| 15 | `8dae4d4` | 09/09 20:58 | **2** | fix(atendimento): identidade única do evento (`@lid`), pausa por `conversation_id` |
| 16 | `0fa6e62` | 09/09 20:58 | **2** | docs(pendências): P-PILOTO-13..16 |
| 17 | `07ad723` | 09/09 21:25 | **2** | feat(atendimento): a janela LIGADA nos portões (entrada, saída, follow-up, widget) |
| 18 | `6618faf` | 09/09 21:30 | **2** | docs(pilotos): resultado da execução do plano handoff+pausa |
| 19 | `312939f` | 10/09 10:46 | **4** | fix(chat): piso de 8192 · continuação no servidor · `finish_reason` gravado |
| 20 | `bf963b0` | 10/09 11:03 | **3** | fix(infocap): a apólice responde item a item (`/itens` + PDF + cache 180 s) |
| 21 | `2701fc3` | 10/09 11:06 | **3 e 4** | docs(pendências): P-PILOTO-17..20 |
| 22 | `05f46a9` | 10/09 13:56 | **5** | feat(atendimento): `JANELA_SILENCIO_EXCECOES` |

⚠️ **A janela de cada onda é curta:** 📊 pacote 1 em **59 minutos** (20:43→21:42), pacote 2 em **76 minutos**, a onda de 10/09 em **3h10**. Isso é FATO. A INFERÊNCIA — que o tempo curto explica a ausência de painel — é consequência direta de D-PILOTO-06 e está escrita no próprio plano; não precisa ser inferida.

---

## 3. Os arquivos, por pacote, medidos

### 3.1 Pacote 1 — plano de ajustes dos pilotos

📊 `git diff --stat e77f1c2^ e149b66` → **27 arquivos · 4.151 inserções · 122 remoções**.

**Produto (11):**
```
app/api/dashboard/portal-jobs/route.ts                            +92
app/dashboard/personalizacao/conectores/portais/page.tsx          +175
backend/app/api/webhook.py                                        +196
backend/app/atendimento/acompanhamento.py                         +202
backend/app/services/dispatch_router.py                           +165
backend/app/services/insurer_dispatch_service.py                  +515
backend/app/services/whatsapp/evolution_inbound.py                 +29
backend/app/tasks/buffer_processor.py                             +115
backend/portal_worker/adaptive.py                                  +84
backend/portal_worker/worker.py                                   +182
backend/scripts/publicar_cartas_0971.py                           +185
```

**Testes (13):** `test_midia_e_concorrencia_do_webhook.py` (**+608, novo**) · `test_o_dossie_fala_portugues_e_o_formulario_nao_repete.py` (**+444, novo**) · `test_o_follow_up_respeita_o_horario_e_as_cartas_sao_de_todas.py` (**+532, novo**) · `test_o_portal_deixa_prova_do_sucesso.py` (**+428, novo**) · e 9 tocados: `test_a_anotacao_da_atendente.py`, `test_a_confirmacao_confere_antes_de_abrir.py`, `test_a_retomada_cobre_as_dezesseis.py`, `test_ninguem_fala_com_o_segurado_sem_o_agente_ligado.py`, `test_o_acionamento_nao_trava.py`, `test_o_caso_se_explica_sozinho.py`, `test_o_travamento_vira_linha.py`, `test_spec031_ops_hardening.py`, `test_spec073_portal_worker_mutations.py`.

**Documentação (3):** `docs/canon/FOUNDER-DECISIONS.md` (+12) · `docs/canon/PENDENCIAS.md` (+36) · `docs/canon/PLANO-PILOTOS-AJUSTES-2026-09-08.md` (+120, novo).

### 3.2 Pacote 2 — handoff + pausa

📊 `git diff --stat 9e75d9f^ 6618faf` → **40 arquivos · 5.723 inserções · 112 remoções**. É o maior dos cinco.

**Produto backend (11):**
```
backend/app/agents/graph.py                                        +27
backend/app/agents/tools/human_handoff.py                         +158
backend/app/api/chat.py                                            +55
backend/app/api/webhook.py                                        +222
backend/app/atendimento/acompanhamento.py                          +46
backend/app/main.py                                                +70
backend/app/services/atlas/attendance_capture.py                   +33
backend/app/services/atlas/espelho_chat.py                         +53
backend/app/services/o_fim_do_atendimento.py                      +646   ← o arquivo-hub
backend/app/services/whatsapp/evolution_inbound.py                 +44
backend/app/services/whatsapp/identidade_do_evento.py             +119   ← PEÇA NOVA
backend/scripts/migrar_conversas_fantasma_lid.py                  +359   ← SCRIPT NOVO
```

**Produto front (9):** `app/api/admin/connectors/infocap/diagnostics/route.ts` · `app/api/attendance/support-destinations/route.ts` e `[destinationId]/route.ts` · `app/api/dashboard/agents/[agentKey]/route.ts` · `app/dashboard/…/suporte-humano/HumanSupportSettingsClient.tsx` · `app/dashboard/personalizacao/equipe/TeamClient.tsx` · `lib/admin/admin-auth-policy.ts` · `lib/admin/historico-do-botao.ts` (**+108, novo**) · `lib/admin/tenant-agent-store.ts` · `lib/admin/tenant-overview-store.ts` · `lib/attendance/support-destinations.ts`.

**Testes (12):** novos — `test_a_atendente_fala_e_o_robo_cala.py` (**+732**) · `test_a_ultima_palavra_humana_manda.py` (**+573**) · `test_o_handoff_que_falha_deixa_rastro.py` (**+476**) · `test_a_janela_esta_ligada_nos_portoes.py` (**+426**) · `scripts/o-destino-de-suporte-e-da-corretora-selecionada.test.mjs` (**+438**) · `scripts/o-membro-liga-o-agente.test.mjs` (**+407**); tocados — `test_a_atendente_aperta_o_botao_e_so_o_botao.py` (+73) · `test_handoff_chega_em_alguem.py` (+235) · `test_a_cobranca_chega_a_quem_deve.py` (+100) · `test_o_atendimento_sabe_como_terminou.py` · `test_o_follow_up_respeita…py` · `test_quem_fala_primeiro_cala_o_outro.py` · `test_spec017_channel.py` · `scripts/admin-auth-policy.test.mjs` · `scripts/spec093-a-rota-do-botao.test.mjs`.

**Documentação (2):** `PENDENCIAS.md` (+12) · `PLANO-HANDOFF-E-PAUSA-2026-09-09.md` (+125, novo).

### 3.3 Pacote 3 — a apólice responde item a item

📊 `git show --stat bf963b0` → **9 arquivos · 950 inserções · 16 remoções**.

```
backend/app/api/infocap_connector.py                              +242
backend/app/agents/tools/infocap_tool.py                           +74
backend/app/services/policy_document_evidence_service.py           +48
backend/app/services/policy_facts.py                               +22
backend/app/services/policy_answer_composer.py                     +13
backend/app/core/prompts.py                                         +2
lib/attendance/connectors/infocap-policy-lookup.ts                 +14
backend/tests/test_a_apolice_responde_item_por_item.py            +326   ← NOVO
backend/tests/fixtures/infocap_itens_garantias_masked.json         +225   ← fixture MASCARADA
```

🔴 **A fixture chama-se `masked`** — é o acervo real com PII removida. Quem mexer nela tem de conferir que continua mascarada.

### 3.4 Pacote 4 — a resposta chega inteira

📊 `git show --stat 312939f` → **4 arquivos · 915 inserções · 96 remoções**.

```
backend/app/agents/graph.py                                       +372/-96   ← o maior delta relativo
backend/app/factories/llm_factory.py                               +43
backend/app/api/chat.py                                            +19
backend/tests/test_a_resposta_chega_inteira.py                    +577      ← NOVO
```

### 3.5 Pacote 5 — as exceções da janela

📊 `git show --stat 05f46a9` → **2 arquivos · 73 inserções · 0 remoções**. É o menor, e é o que tem menos contexto escrito.

```
backend/app/services/o_fim_do_atendimento.py                       +43
backend/tests/test_o_numero_de_teste_e_conversa_nova.py            +30      ← NOVO
```

### 3.6 A união

📊 `git diff --stat cffaa0e 05f46a9` → **74 arquivos · 11.822 inserções · 344 remoções**.
📊 `git diff --name-status --diff-filter=A cffaa0e 05f46a9` → **11 arquivos de teste `.py` novos + 2 `.mjs` novos + 1 fixture + 1 script**.

⚠️ **Arquivos tocados por mais de um pacote** (a razão de a soma não fechar): `backend/app/api/webhook.py` (1 e 2) · `backend/app/atendimento/acompanhamento.py` (1 e 2) · `backend/app/services/whatsapp/evolution_inbound.py` (1 e 2) · `backend/app/agents/graph.py` (2 e 4) · `backend/app/api/chat.py` (2 e 4) · `backend/app/services/o_fim_do_atendimento.py` (2 e 5) · `docs/canon/PENDENCIAS.md` (1, 2, 3/4) · `backend/tests/test_o_follow_up_respeita…py` (1 e 2).

---

## 4. Achados no código — coordenadas reabertas em 13/09/2026

| ID | Evidência (`arquivo:linha`, reaberta hoje) | Consequência para a conversão |
|---|---|---|
| **R01** | `backend/app/services/o_fim_do_atendimento.py:945` — `JANELA_SILENCIO_HUMANO_DIAS = 7`; `:948` `_ENV_DA_JANELA`; `:1016-1029` documenta a cadeia padrão → env → override por corretora | contrato do pacote 2. A ficha diz NOME e PADRÃO, nunca valor de produção |
| **R02** | mesmo arquivo, `:1288-1293` — comentário e `_ENV_EXCECOES_DA_JANELA = "JANELA_SILENCIO_EXCECOES"` | contrato do pacote 5. 🔴 **guarda telefones** — só `TESTE-A`/`TESTE-B` no relatório |
| **R03** | `backend/app/factories/llm_factory.py:32` — `PISO_DE_SAIDA_DA_CONVERSA = int(os.getenv(..., "8192"))`; `:85` default `llm_max_tokens` 8192 | contrato do pacote 4, e a causa de P-PILOTO-17 (o banco continua com 1200) |
| **R04** | `backend/app/api/infocap_connector.py:995` — `itens_path = config.get("infocap_itens_path") or "/itens"`; `:3216` bloco "COBERTURAS ITEM A ITEM"; `:3358` "Lê `/itens` … com cache curto no Redis"; `:4008` `coverage_source` | contrato do pacote 3, incluindo o campo que diz a **origem** da cobertura |
| **R05** | `backend/app/tasks/buffer_processor.py:76` — `_env_int("WHATSAPP_BUFFER_PARALELISMO", _PARALELISMO_PADRAO)` | contrato do pacote 1; é o "alívio, não solução" de P-PILOTO-01 |
| **R06** | `backend/app/api/webhook.py:291-295` — comentário "5 MB não é limite de lugar nenhum… `_LIMITE_DO_WHATSAPP_BYTES = 16 * 1024 * 1024`"; `:326`, `:378` | contrato do pacote 1 (mídia 16 MB) |
| **R07** | `backend/app/api/webhook.py:538-542` — ⚠️ comentário "**ESTES TRÊS NÃO GANHARAM `to_thread`, E É DE PROPÓSITO**" | 🔴 a ficha do pacote 1 tem de registrar a exceção deliberada, senão a próxima SPEC "consertará" o que é intencional |
| **R08** | `backend/app/services/whatsapp/identidade_do_evento.py:18` (docstring: o telefone vem em `key.remoteJidAlt`), `:69` `jid_alternativo`, `:88` `telefone_do_evento` | peça nova do pacote 2 — é o motor que mata as conversas-fantasma |
| **R09** | `backend/app/agents/graph.py:1784-1816` (normalização de `finish_reason`/`stop_reason` por provedor), `:2234-2235` (`_ev("final", finish_reason=…, usage=…, continuations=…, truncated=…)`) | contrato do pacote 4 gravado no turno |
| **R10** | `backend/tests/test_o_protocolo_tem_policia.py:80` — `re.search(r"SPEC-EXTRA-(\d{1,3})", base)`; `:262` glob `SPEC-*-EXECUTION-REPORT.md`; `:284-290` controles da família EXTRA | 🔴 **o relatório desta SPEC SERÁ julgado**. Não é isento |
| **R11** | mesmo arquivo, `:202-224` `conferir_relatorio` — exige card, todas as linhas, `FAIXA DE RELÓGIO`, `bateria`+`rodadas`, `REFERÊNCIA`, `📊`, `nota NN/100` | o contrato literal do relatório (§6.2 da proposta) |
| **R12** | mesmo arquivo, `:226-243` `conferir_spec` — exige `O QUE O ESTADO DA ARTE FAZ`, **3 URLs externas**, `BLOCO 0`, `O QUE SAIU`, `📊`, `mutação`; só julga SPEC que declara `protocolo … v11` (`:308`) | a SPEC definitiva precisa declarar v11 **e** cumprir os seis |
| **R13** | `docs/canon/ESTADO-DAS-SPECS.md` — tabela "🔵 EXECUTADAS SEM SPEC" com SPEC-079 e SPEC-082, e a frase "Trabalho sem SPEC é trabalho sem gate" | 🔴 **o lugar já existe.** Não criar índice novo |
| **R14** | `docs/canon/EXECUTION-MASTER-PLAN.md` — 📊 `grep -n '^## '` mostra que o corpo para na "Etapa 13 — Launch Decision" (SPEC-062) e continua por blocos `# ESTADO EM DD/MM/AAAA` | acrescentar bloco datado; **não** reescrever |
| **R15** | `backend/scripts/conferir_o_que_esta_no_ar.py:29-41` — `SERVICOS` cobre só `portal-worker` (`backend/portal_worker`) e `smith-api` (`backend/app`) | 🔴 **`smith-web` não é conferível por este script.** A lacuna é obrigatória no relatório |
| **R16** | `docs/canon/reports/dossies/dossies-autobrokers.html` — 📊 `grep -o 'id="p-[a-z0-9-]*"'` devolve `p-home, p-s088, p-s093b, p-s091, p-s094, p-s0941, p-s095, p-s096, p-s097, p-s0971, p-s098, p-extra001, p-pilotos, p-proto, p-fila` | a página `p-pilotos` já existe: é onde a EXTRA-001.0 encaixa |

---

## 5. Os guardas — rodados hoje, com saída real

📊 13/09/2026, de dentro de `backend/`, `PYTHONIOENCODING=utf-8`. Saída **real**, abreviada na última linha útil:

| guarda | comando | saída |
|---|---|---|
| `tests/test_o_numero_de_teste_e_conversa_nova.py` | `python tests/…` | `VERDE` · **EXIT=0** |
| `tests/test_a_resposta_chega_inteira.py` | `python tests/…` | `PLACAR: 26 OK · 0 FALHA` · **EXIT=0** |
| `tests/test_a_apolice_responde_item_por_item.py` | `python tests/…` | `PASS=31  FAIL=0` · **EXIT=0** |
| `tests/test_o_portal_deixa_prova_do_sucesso.py` | `python tests/…` | `== 48 ok / 0 fail ==` · **EXIT=0** |
| `tests/test_a_atendente_fala_e_o_robo_cala.py` | `python tests/…` | `TUDO VERDE — a pausa cai na conversa certa, com o agente ligado ou não.` · **EXIT=0** |
| `tests/test_a_janela_esta_ligada_nos_portoes.py` | `python tests/…` | `TUDO VERDE — a regra tem chamador, e o veredito dele manda.` · **EXIT=0** |
| `tests/test_o_handoff_que_falha_deixa_rastro.py` | `python tests/…` | `PLACAR: 27 verde(s) . 0 vermelho(s)` · **EXIT=0** |
| `tests/test_a_ultima_palavra_humana_manda.py` | `python -m pytest tests/… -q` | `23 passed, 12 warnings in 13.66s` · **EXIT=0** |
| `tests/test_midia_e_concorrencia_do_webhook.py` | `python -m pytest tests/… -q` | `10 passed, 12 warnings in 19.95s` · **EXIT=0** |
| `tests/test_o_dossie_fala_portugues_e_o_formulario_nao_repete.py` | `python -m pytest tests/… -q` | `16 passed, 12 warnings in 11.45s` · **EXIT=0** |
| `tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py` | `python -m pytest tests/… -q` | ⚠️ **`1 failed, 8 passed`** na 1ª rodada · `9 passed in 5.17s` na 2ª · ver §5.1 |

**PENDENTE DE MEDIÇÃO** (não rodados nesta redação; o executor roda e cola): `test_o_follow_up_respeita_o_horario_e_as_cartas_sao_de_todas.py` · `scripts/o-destino-de-suporte-e-da-corretora-selecionada.test.mjs` e `scripts/o-membro-liga-o-agente.test.mjs` (node) · `test_handoff_chega_em_alguem.py` · `test_spec073_portal_worker_mutations.py` · `test_o_travamento_vira_linha.py`.

### 5.1 🔴 O guarda que ficou vermelho uma vez — e por quê

📊 13/09/2026. `tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py::test_a_politica_de_autorizacao_passa` **falhou** numa rodada e **passou** nas duas seguintes:

```
1ª rodada (com OUTROS processos Python escrevendo na mesma árvore)
   FAILED tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py::test_a_politica_de_autorizacao_passa
   1 failed, 8 passed in 17.74s
2ª rodada (só o nó, isolado)      1 passed in 3.42s
3ª rodada (arquivo inteiro, sozinho)  9 passed in 5.17s
```

**FATO:** a falha aconteceu; não foi imaginada.
**A causa, lida na fonte** (`backend/tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py:67-90`): `test_a_politica_de_autorizacao_passa` executa `node` sobre um `.mjs`, e o teste de CONTROLE vizinho **escreve um arquivo na árvore real** — `RAIZ/"scripts"/"_controle_politica_falha.test.mjs"` — em vez de numa cópia.
**INFERÊNCIA:** é exatamente o cenário que o protocolo §10 proíbe (*"mutação roda em WORKTREE PRÓPRIO ou com lock exclusivo · restaura por CÓPIA"*) e que o `PLANO-PILOTOS-AJUSTES-2026-09-08.md:102-106` já tinha medido noutra forma (poluição de `sys.modules`). 📊 `git status --short` confirmou, no momento da falha, **outros agentes escrevendo nesta árvore**.
**RECOMENDAÇÃO:** vira **pendência nova** (§7.1, item 15) — "guarda que muta a árvore real e não tolera escritor concorrente". **Não** se conserta nesta SPEC.
⚠️ E vira **instrução operacional para o executor**: rodar a bateria com a **árvore parada**. Um vermelho obtido com outro agente escrevendo não é prova de regressão — nem de saúde.

🔴 **A armadilha que custa caro:** 📊 `tail -3` de cada arquivo mostra três formas de entrada diferentes — `sys.exit(main())`, `pytest.main([__file__])` e asserts de módulo. **Rodar `python` num arquivo pytest imprime um aviso e sai 0 sem executar nada.** Foi assim que o primeiro `tail` desta redação devolveu só um `UserWarning`. Todo guarda do relatório vai com a **forma de invocação escrita ao lado da saída**.

⚠️ Observação de higiene, **medida nos planos, não por mim**: `PLANO-PILOTOS-AJUSTES-2026-09-08.md:102-106` registra que `pytest tests/` em lote deu **15 failed / 48 errors** por poluição de `sys.modules["app"]` deixada por `test_o_sinistro_deixa_rastro` — e que os 48 passam isolados. Isso continua **sem número de pendência**.

---

## 6. A prova do implantado

📊 13/09/2026 · `python backend/scripts/conferir_o_que_esta_no_ar.py` · saída real:

```
portal-worker
  repositorio : a006a0494024bbb4  (27 arquivos .py em backend/portal_worker)
  no ar       : a006a0494024bbb4  (27 arquivos)  2026-09-09T01:19:23Z
  VEREDITO    : BATE.

smith-api
  repositorio : 89787936aa9abe73  (383 arquivos .py em backend/app)
  no ar       : 89787936aa9abe73  (383 arquivos)  2026-09-13T10:16:36.529302
  VEREDITO    : BATE.

TODOS BATEM      (exit 0)
```

**FATO:** o código de `backend/app` e de `backend/portal_worker` que está na árvore **é** o que está no ar, hoje.
**INFERÊNCIA:** como nenhum arquivo de produto mudou entre `05f46a9` e HEAD (§1), os pacotes 1–5 estão implantados nesses dois serviços.
🔴 **NÃO SE CONCLUI:** nada sobre o `smith-web`. 📊 Os pacotes 1 e 2 mudaram **11 arquivos** de front (`app/`, `lib/`) e o script não os cobre (R15). A linha do `smith-web` fica **"declarado nos planos, não conferido"**.
⚠️ O `build_time` do portal-worker é de **09/09 01:19** — anterior aos pacotes 3, 4 e 5, o que é coerente (nenhum deles tocou `backend/portal_worker`).

---

## 7. As pendências, por número

📊 `grep -n "P-PILOTO-" docs/canon/PENDENCIAS.md` → **20 entradas**, de `:10496` a `:10553`. Ler **por número**; o arquivo tem 562 KB.

| origem | números | leitura de hoje (a confirmar no BLOCO 0) |
|---|---|---|
| pacote 1 (plano de 08/09) | **01 … 12** | 01 CONTINUA (alívio, não solução — a própria entrada diz) · 10 forte candidata a **FECHADA** (corrigida em 09/09 com VERIFY pelo motor, `PLANO-HANDOFF…:8-16`) · 11 CONTINUA (canário Q1–Q6 nunca rodado) · 09 dono 🧑 |
| pacote 2 (plano de 09/09) | **13 … 16** | 13 CONTINUA — 📊 174 conversas-fantasma; o `--vivo` bloqueado pelo CHECK `ck_conversations_resolucao_motivo`, e o guarda `test_a_atendente_fala_e_o_robo_cala` **afirma isso explicitamente** (saída de hoje: *"o script SABE que o CHECK do banco ainda recusa `fantasma_lid`"*) |
| pacotes 3 e 4 (`2701fc3`) | **17 … 20** | 17 dono 🧑 (`llm_max_tokens` 1200 no banco) · 18, 20 dono 🤖 · 19 dono 🧑 |

### 7.1 Os achados que **nunca viraram número** — o acréscimo desta SPEC

📊 `PLANO-PILOTOS-AJUSTES-2026-09-08.md:115-120`, seção "Achados dos builders que viraram pendência (**acrescentar em PENDENCIAS na próxima sessão**)" — a próxima sessão não os acrescentou:

1. supressão do follow-up fora da janela é **perdida**, não adiada (só `avisos == 0` fala)
2. `_dia_e_mes` compara em **UTC**
3. `webhook._responder_formulario_nativo` devolve `bool` e **descarta o status do provedor**
4. `dispatch_router:1210/:1973` grava `Motivo: {reason}` **cru** em `work_runs.result_summary`
5. `vidros_lanternas` **não existe** em `portals`
6. bucket `portal-evidence` **sem retenção**
7. `test_o_sinistro_deixa_rastro` deixa `sys.modules` sintético (a causa dos 48 errors da §5)

📊 `PLANO-HANDOFF-E-PAUSA-2026-09-09.md:94-99` ("Fora do escopo, anotado para a fila") e `:123-125` ("Ficou:") — além de P-PILOTO-13..16:

8. `normalize_evolution_inbound` erra o **telefone de entrada** vindo de `@lid` (mesma bomba, outra direção)
9. duas linhas duplicadas na Amandus
10. rota `admin/integrations` fora do helper canônico
11. CPF/placa em texto puro no corpo de `messages.content`
12. o ramo `fromMe` do webhook com 230 linhas e **um teste que mede bytes de código**
13. `#nota` pelo WhatsApp ainda chega ao segurado (atribuído à SPEC-090)
14. botão "Devolver ao agente" na tela **não foi conferido**

E um achado desta redação, que não está em plano nenhum:

15. 📊 `test_a_atendente_aperta_o_botao_e_so_o_botao.py` **escreve `scripts/_controle_politica_falha.test.mjs` na árvore real** e fica vermelho quando outro processo escreve junto (§5.1). O controle é legítimo e necessário (§9.3 do CLAUDE.md); o lugar onde ele escreve, não.

🔴 **Antes de numerar qualquer um destes, `grep` o símbolo em `PENDENCIAS.md`.** Vários podem já existir com outro número (o item 12, por exemplo, é parente de CLAUDE.md §9.4). Duplicata é pior que ausência.

---

## 8. O que continua desconhecido

1. **Se o `smith-web` no ar tem os pacotes 1 e 2.** Não há impressão digital para Next.js (R15). Só um endpoint que devolva o SHA resolveria — e isso é trabalho de outra SPEC.
2. **Se a suíte inteira passa com a árvore parada.** 📊 os dois planos declaram que ela **não** foi rodada. Ninguém a rodou desde então, até onde medi.
3. **Se as 4 mutações de higiene que o pacote 1 declarou continuam válidas** (`M24`, `[M2p]` da 097.1, `test_o_travamento_vira_linha`).
4. **Quantas das 174 conversas-fantasma ainda existem** — exigiria SELECT no banco; não rodei.
5. **Se algum dos 22 SHAs já é citado em algum lugar do canon.** 💭 Minha leitura diz que não, mas só o `grep` dos 22 decide (comando na §9).
6. **Se `test_o_follow_up_respeita_o_horario_e_as_cartas_sao_de_todas.py` é pytest ou script** — o `tail -3` não foi conclusivo.

---

## 9. Roteiro de remedição — comandos para o executor

> Instruções para o futuro executor, **não** saídas já obtidas. Rodar na árvore correta, de dentro de `backend/` onde for Python.

```bash
# 1. Preflight (CLAUDE.md §2)
git fetch origin
git rev-parse HEAD; git rev-parse origin/main
git rev-list --count HEAD..origin/main; git rev-list --count origin/main..HEAD
git branch --show-current; git status --short

# 2. O intervalo continua o mesmo?
git rev-list --count cffaa0e..05f46a9                 # esperado: 22
git log --format='%h %ad %s' --date=format:'%d/%m %H:%M' cffaa0e..05f46a9
git log --oneline 05f46a9..origin/main
git diff --stat 05f46a9 origin/main                    # nenhum arquivo de produto?

# 3. Os arquivos por pacote
git diff --stat e77f1c2^ e149b66                       # pacote 1
git diff --stat 9e75d9f^ 6618faf                       # pacote 2
git show --stat bf963b0 312939f 05f46a9 2701fc3        # pacotes 3, 4, 5
git diff --stat cffaa0e 05f46a9                        # a união
git diff --name-status --diff-filter=A cffaa0e 05f46a9 # o que NASCEU

# 4. O ELO: o canon cita algum dos 22?
for s in $(git log --format=%H cffaa0e..05f46a9); do
  n=$(grep -rl "${s:0:7}" docs/canon/ 2>/dev/null | wc -l); echo "${s:0:7} $n";
done

# 5. Os contratos novos, por NOME
rg -n 'JANELA_SILENCIO_HUMANO_DIAS|JANELA_SILENCIO_EXCECOES|PISO_DE_SAIDA_DA_CONVERSA' backend/app
rg -n 'WHATSAPP_BUFFER_PARALELISMO|POS_ACIONAMENTO_ESPERA_MINUTOS' backend
rg -n 'itens_path|coverage_source|remoteJidAlt|continuations' backend/app

# 6. Os guardas — a forma importa
for t in <os da §5.7 da proposta>; do tail -3 backend/tests/$t; done   # script ou pytest?
python backend/tests/test_o_protocolo_tem_policia.py                  # ANTES de escrever o relatório

# 7. O que está no ar (read-only, sem credencial)
python backend/scripts/conferir_o_que_esta_no_ar.py

# 8. As pendências, POR NÚMERO
grep -n "P-PILOTO-" docs/canon/PENDENCIAS.md
grep -n "D-PILOTO-" docs/canon/FOUNDER-DECISIONS.md

# 9. Antes de criar pendência nova: já existe?
grep -n "_dia_e_mes\|result_summary\|vidros_lanternas\|portal-evidence" docs/canon/PENDENCIAS.md
```

⛔ **Nenhum comando acima escreve.** Se o executor precisar de SQL, ele saiu do escopo desta SPEC.

---

## 10. Armadilhas que o aquecimento deve refutar

1. **"Os cinco pacotes violaram o protocolo AAA."** Não violaram: **D-PILOTO-06** os autorizou expressamente. O relatório registra o custo, não a culpa.
2. **"Se os testes estão verdes, os pacotes estão validados."** 📊 O diagnóstico mediu **1h53** de agente ligado em três dias e **5 segurados reais**. Verde de guarda não é validação de produto.
3. **"O relatório da EXTRA-001.0 é documento, logo a polícia não o julga."** 📊 `test_o_protocolo_tem_policia.py:80,284` reconhece `SPEC-EXTRA-NNN` e a coloca **sob a v11**. Será julgado.
4. **"Basta seguir o template para passar."** O casador cobra **linhas ancoradas no início** (`:63`) e ainda `bateria`+`rodadas`, `REFERÊNCIA`, `📊` e `nota NN/100`. Template sem esses campos reprova.
5. **"Como é retroativa, o card pode ficar vazio ou dizer N/A."** Campo em branco é exatamente o que o guarda existe para pegar. O card é da SPEC-001.0; os cinco ganham cards **rotulados como reconstrução**.
6. **"`git log` já é o registro; o relatório é redundante."** Keep a Changelog, reaberta hoje: *"Using commit log diffs as changelogs is a bad idea: they're full of noise"*.
7. **"`conferir_o_que_esta_no_ar.py` bate ⇒ tudo está no ar."** Ele cobre **dois** serviços `.py`. 📊 11 arquivos de front mudaram e não são conferidos.
8. **"Se achei um defeito, conserto — é pequeno."** Proibido (§1.2). Vira pendência. O escopo é documentação.
9. **"`ESTADO-DAS-SPECS.md` precisa de uma tabela nova para os cinco."** A tabela **já existe** ("🔵 EXECUTADAS SEM SPEC"). Criar outra é motor paralelo documental.
10. **"Somar as linhas dos cinco pacotes dá a união."** 📊 4.151+5.723+950+915+73 = 11.812 ≠ **11.822** medidos, e a diferença não é o que parece: **oito arquivos** aparecem em mais de um pacote. Somar esconde o fato.
11. **"O `EXECUTION-MASTER-PLAN.md` está desatualizado, então atualizo."** Ele é append-only por data e para na SPEC-062 por desenho; o próprio `ESTADO-DAS-SPECS.md` diz isso. Acrescente um bloco datado.
12. **"Os 22 commits são cinco pacotes, então 22 ÷ 5."** 📊 A distribuição é **9 / 9 / 1 / 1 / 1**, mais `2701fc3` atendendo a dois. O guarda cobra atribuição, não simetria.

---

## 11. Pesquisa externa — fontes primárias, reabertas em 13/09/2026

Quatro fontes, todas abertas nesta redação. O pesquisador do executor as reabre e registra a data dele (protocolo §7.3). A proposta §15 traz as quatro linhas de cada uma no formato exigido.

| ID | fonte | o núcleo do que ela dá |
|---|---|---|
| **E01** | Google SRE Book, *Postmortem Culture* — https://sre.google/sre-book/postmortem-culture/ | gatilhos objetivos; conteúdo mínimo (incidente · impacto · mitigação · causa raiz · ações de acompanhamento); *"Blameless postmortems are a tenet of SRE culture"*. 🔴 **medido: ela NÃO prescreve postmortem para mudança bem-sucedida** — a lacuna que D-PILOTO-15 preenche |
| **E02** | RFC 7942, *Implementation Status Section* — https://www.rfc-editor.org/rfc/rfc7942.html | campos obrigatórios de status de implementação: responsável · nome/link · descrição · **maturidade** · **cobertura** · versão · licença · experiência · contato · **data da última atualização**. E manda **remover** a seção antes da publicação — o que **rejeitamos**, porque aqui a seção é o produto |
| **E03** | Keep a Changelog 1.1.0 — https://keepachangelog.com/en/1.1.0/ | *"Changelogs are for humans, not machines"*; entrada por versão, agrupada, com data; e a justificativa direta desta SPEC: *"Using commit log diffs as changelogs is a bad idea: they're full of noise"* — o commit documenta a evolução do código, a entrada comunica *"the noteworthy difference… to end users"* |
| **E04** | MADR — https://adr.github.io/madr/ | formato mínimo de registro de decisão (título · contexto e problema · opções consideradas · resultado), metadados `status`/`date`/`decision-makers`, **Consequences** com sinal (*"Good, because" / "Bad, because" / "Neutral, because"*), e supersessão por `superseded by ADR-0123` — **apontamento, nunca edição do antigo** |

⛔ **Nenhuma delas vira autoridade.** `FOUNDER-DECISIONS.md`, `PENDENCIAS.md`, `ESTADO-DAS-SPECS.md` e o template de relatório continuam únicos (CLAUDE.md §5). Modela-se o **padrão**, não o meio: **não** se cria `adr/`, **não** se cria `CHANGELOG.md`, **não** se cria um "índice de entregas sem SPEC".

---

## 12. Dependências e limites deste research pack

- **Depende de:** nada. Todos os comandos são locais e read-only.
- **Não cobre:** o mérito técnico dos cinco pacotes (isso é o `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`), o estado do banco de produção, e o conteúdo do `smith-web` no ar.
- **Envelhece em:** cada commit novo na `main`. As coordenadas `arquivo:linha` da §4 são as mais frágeis; o §9 é o que não envelhece, porque é comando.
- **Regra de integridade:** se o executor medir um número diferente dos daqui, **o número dele vence** e a divergência vai para a matriz do GATE B0 — não se "conserta" este documento para esconder a mudança.
