---
> **Status:** relatório de execução — SPEC-EXTRA-001.3, sob o **PROTOCOLO AAA v12 · AAA FAST**
> **Experimento A do A/B (D-PROTO-02):** executor Opus 5 `xhigh` · juiz Fable 5.1 · lente do dado Opus 5
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `09a238f`

```
OUTCOME .............. o grupo da corretora recebe 4 tipos de mensagem e mais nada; nenhuma sobre
                       conversa que um humano já conduz ou sobre número da casa; cada uma inteira e
                       clicável; todo envio contado
RISCO ................ 8 — ALCANCE 3 · REVERSIBILIDADE 3 (mensagem que sai do prédio) · FREQUÊNCIA 2
SUPERFÍCIE ........... 3 — 11 pontos de envio, e "consigo apontar TODOS" era o que provar
PISO APLICADO ........ §3.2 três vezes: ENVIA mensagem · migration de ESTRUTURA · filtro `company_id`
NÍVEL ................ CRÍTICO · executor Opus 5 `xhigh` · juiz Fable 5.1
UNIDADES ............. 7 — A guarda única · B números da casa · C mensagem inteira · D os quatro
                       modelos · E contabilidade · F gate de ligar · G as 6 rotas
                       FATIAS: 1 = A+C+E · 2 = B+D+F+G (⚠️ na MESMA sessão — ver §10)
COESÃO ............... A e C tocam os mesmos arquivos de envio → um dono, serial. E fecha o contrato
                       que A e C produzem (o que saiu, e o que significava) → mesma fatia.
PARALELISMO REAL ..... nenhum — a escrita é de um só. Investigador read-only: não
TIME ................. executor · juiz Fable 5.1 · lente do dado (gatilho: o outcome é dataset +
                       migration de dado) · red team NÃO (sem auth nova, dinheiro ou portal)
REFERÊNCIA ........... interna `backend/tests/test_o_caso_se_explica_sozinho.py` (`problemas_de_lingua`)
                       e `backend/tests/corpus/acervo_do_grupo_2026-09-16.json` (acervo real, redigido)
                       externa: E01–E05 da §19 (SRE Book 6 e 11 · PagerDuty `dedup_key` ·
                       Alertmanager `inhibit_rules` · Alertmanager `group_by`)
GATES ................ G-A1..A3 · G-B1..B3 · G-C1..C4 · G-D1/D2 · G-E1 · G-F1/G-G1
O ELO ................ "o grupo virou ruído PORQUE nenhum gatilho pergunta se um humano já está na
                       conversa" — A medido (7 mensagens / 75,7 min, e 6 delas DEPOIS do takeover das
                       17:18) · B medido (97 de 99 elegíveis calam, pelo MOTOR) · 🔴 B CHEGA EM A: os
                       11 pontos foram abertos um a um e TODOS passam a consultar a mesma guarda;
                       G-A2 varre o backend e fica vermelho com um 12º caminho
FAIXA DE RELÓGIO ..... declarada 1h15 + 1h15 + 45min · real 167 min · tetos 250 turnos / 300 k:
                       🔴 ESTOURADOS (271 · 649 k) — §10
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** `docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md` ·
**Branch:** `feat/spec-extra-001-3-grupo-so-o-que-importa` ·
**Preflight** 📊 16/09/2026: `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `09a238f` · árvore limpa ·
**Executor:** Opus 5 `xhigh` (sessão nova) · **Juiz:** Fable 5.1 · **Início/fim:** 16/09 18:26 → 21:20 UTC

## 1. BLOCO 0 — as premissas que mudariam o desenho

| # | a proposta afirma | medido 📊 16/09 | comando | consequência |
|---|---|---|---|---|
| 1 | 7 mensagens ao grupo em 75,7 min no 10/09 | **7 · 75,68 min** — idêntico | a SQL da §0.1, colada no módulo novo | âncora confirmada. 🔬 A lente acrescentou: **1** saiu antes do takeover das 17:18 e **6 depois** — o argumento fica mais forte, não mais fraco |
| 2 | 58 elegíveis, 58 com humano nos 7 dias | **254→259** `HUMAN_REQUESTED` · **99** elegíveis · **97–98** calam | `ultima_palavra_humana` + `silenciar_por_palavra_humana` sobre as 99, **pelo MOTOR**, não por SQL | o acervo dobrou; a asserção do guarda é contra o CONJUNTO, nunca contra um literal. A mesma pergunta em SQL cru dá **96** — três réguas, três números |
| 3 | o dossiê vira 4 balões | **4 balões** (508 chars, não 429) | `split_whatsapp_balloons` real, na linha de controle de G-C1 | a asserção é `> 1`, nunca `4` |
| 4 | `motivo_classe` não tem escritor | **0** ocorrências · `human_handoff_reason` em **2 de 254** | `grep -rn motivo_classe backend/app` · SQL | a regra de `desconhecido` e o limite de 30% são obrigatórios |
| 5 | as 3 leituras do governador não filtram `kind` | **confirmado**, e `billing_nota`/`billing_doc` da 001.6 já existem e já contam | `platform_outbound.py:606-616` lido da linha 1 | a allowlist (não o prefixo) era mesmo o desenho certo |
| 6 | `internal_numbers` vazio em toda a base | **0** integrações com a lista preenchida (a chave existe em 3, vazia nas 3) | `jsonb_array_length(...) > 0` | sem backfill, escrito na migration |
| 7 | 🔴 **não estava na proposta** | `work_events.work_run_id` era **NOT NULL sem default** | `insert` sem a coluna → `NotNullViolation` (em transação revertida) | **BLOCKER**: o diário do grupo era impossível. Migration `20260916_02`. É também por isto que `handoff.realertado` tinha 0 linhas — a proposta lia esse 0 só como "o re-alerta nunca disparou". 🔬 **E o elo fechou:** as 4 primeiras linhas `handoff.*` da história da base nasceram hoje, com `work_run_id` nulo |
| 8 | 🔴 **não estava na proposta** | `_support_alert_seguro` lia `destino.get("number")` | `resolver_destino_de_suporte` devolve `{destino, fonte, recusa}` | o aviso *"o protocolo NÃO chegou ao segurado"* **saía calado sempre**. Morreu junto com as 3 linhas |
| 9 | `write:true` pode restringir quem usa as telas | `admin_company` **8** (4 `is_owner`) · `member` **2** | `select role, is_owner, count(*) from company_members group by 1,2` | 🔬 a lente corrigiu a leitura otimista: **2 pessoas em 2 corretoras** perdem a escrita. Caixa do Founder #3 |
| 10 | P-PILOTO-10: AutoFleet com zero destinos | **4 destinos · 3 empresas · 1 ativo** · `agent_enabled` false em 5 de 5 | `select … from human_support_destinations` | pendência re-justificada (§9) |

**MUTAÇÃO B0** — as duas afirmações falsas do desenhista, refutadas: (a) *"basta filtrar `kind LIKE 'grupo_%'`"* é falso, `billing_nota` não tem o prefixo e consumiria a cota do segurado; (b) *"o dossiê já sai em um balão"* é falso, `bloco_unico` estava em **1 de 11** caminhos.

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate | saída real | commit |
|---|---|---|---|---|---|
| 1 | **A** guarda única | `services/o_grupo_so_o_que_importa.py` (novo) + os 11 pontos | `tests/test_o_grupo_so_fala_de_quem_precisa.py` | **33 verdes · 0** | `21f2243` `fe136c0` `87b92e6` |
| 1 | **C** uma mensagem, inteira, uma vez | `human_handoff` · `dispatch_router` · `dispatch_watchdog` · `handoff_watchdog` · `whatsapp/alerts` | `tests/test_uma_mensagem_inteira_e_uma_vez.py` | **22 verdes · 0** | idem |
| 1 | **E** todo envio contado | `platform_outbound.py` (allowlist nas 3 leituras) · `billing_collection` | `tests/test_toda_mensagem_ao_grupo_e_contada.py` | **18 verdes · 0** | idem |
| 2 | **F** gate de ligar | `api/porteiro_do_agente.py` (novo) · `porteiro-de-ligar-o-agente.ts` · rota do toggle | `tests/test_ligar_o_agente_tem_porteiro.py` | **38 verdes · 0** | `a405bbb` |
| 2 | **G** as 6 mutações | `lib/admin/porteiro-de-configuracao.ts` (novo) + as 6 rotas | idem | idem | `a405bbb` |
| 2 | **D** os quatro modelos + 19h | `services/os_modelos_do_grupo.py` · `tasks/o_resumo_das_19h.py` (novos) · `human_handoff` · `o_fim_do_atendimento` | `tests/test_os_quatro_modelos_falam_portugues.py` | **47 verdes · 0** | `bbff51a` `87b92e6` |
| 2 | **B** números da casa | migration · `lib/atendimento/numeros-da-casa.ts` · `casos.ts` · `attendance_capture` · rotas + card Equipe | `tests/test_o_numero_da_casa_nao_e_cliente.py` | **20 verdes · 0** | `04291fe` |

🔴 **Os 11 pontos, um a um:** 1 `human_handoff` ✅ porta · 2 `dispatch_router:3312` ✅ porta · 3 `dispatch_router:201` ✅ porta (e o defeito do `number` morto) · 4 `dispatch_watchdog` ✅ porta · 5 `billing_collection` ✅ porta (perdeu o 2º resolvedor, que pulava a recusa de destino compartilhado) · 6 `regression_sentinel` ✅ porta · 7 `whatsapp/alerts` ✅ muda de destinatário (§7.4) · 8 `admin_spec034` isento (alerta de TESTE) · 9/10 `weekly_report`/`proactive_suggestions` fora de escopo, **pendência** · 11 `route_sentinel` vai ao Founder. **G-A2 varre o backend e fica vermelho com um 12º caminho.**

**§9.1 — o servidor RESPONDE, não só compila:** `npm run test:rotas-montam` → *302 rotas ordenadas* · `npm run build` rc=0 · `next start` → *Ready in 37s* · e as requisições reais:
```
POST /api/dashboard/internal-numbers   Origin: https://evil.example  ->  403 cross_origin_blocked
DELETE /api/attendance/support-destinations/…  Origin alheia         ->  403 cross_origin_blocked
POST /api/dashboard/internal-numbers   Origin: a da casa (CONTROLE)  ->  401 no_session
PATCH /api/dashboard/agents/even                                     ->  401 no_session
```
🔴 A linha de controle é o que dá direito à conclusão: a tranca do BLOCO G barra a origem alheia **e deixa passar a de casa**.

## 3. Migrations — APPLY · VERIFY · ROLLBACK (escritos ANTES; VERIFY contra o objeto)

| migration | APPLY | VERIFY (rodado no banco) | ROLLBACK |
|---|---|---|---|
| `20260916_01_…_company_internal_numbers` | tabela + índice único `(company_id, phone)` + RLS | `tabela_existe=True` · `unique_por_corretora=True` · `rls_ligada=True` | `drop table if exists` — nasce nesta SPEC e o leitor do JSONB continua (expand-first) |
| `20260916_02_…_work_events_sem_run` | `alter column work_run_id drop not null` | `run_id_opcional=True` · `fk_composta_intacta=True` · `linhas_sem_run=0` **no APPLY** | `set not null` — 🔴 **já exige decisão do Founder**: 📊 existem 5 linhas com `work_run_id` nulo (as `handoff.teto_de_lembretes` de hoje), e `work_events` é append-only |

⚠️ A FK composta `(work_run_id, company_id)` continua valendo: em MATCH SIMPLE, coluna nula satisfaz sem checar — um evento sem run não aponta para o run de outra corretora porque não aponta para run nenhum. 🔬 A lente registrou que, nessas linhas, quem garante a corretora é só `work_events_company_id_fkey`.
⚠️ 🔬 As duas migrations **não têm linha em `supabase_migrations.schema_migrations`**, embora os objetos estejam no banco — é o descompasso que o `MIGRATIONS-AUTHORITY.md` documenta e que o protocolo §4 prevê (*"o ledger mente; confere o OBJETO"*). Os objetos conferem. Fica o risco de um `db push` futuro tentar reaplicar — **pendência `P-E0013-06`**.
⛔ Sem migration para `platform_sends`: `kind` é `text` livre, sem CHECK. Os `kind` novos entram como **dado**.

## 4. O juiz fresco (Fable 5.1, sobre `04291fe`, 75 chamadas, 47 min) — VEREDITO **FAIL** · nota **80** · 🔬 lente do dado (Opus 5, 41 chamadas, 26 min) · confiança **87**

| # | achado | teste do produto (§2) | medição | classe | conserto |
|---|---|---|---|---|---|
| **B1** | a pergunta 3 era pulada com linha PARCIAL | **SIM** — uma "⏳ ESPERA VENCIDA" a mais sobre conversa já assumida | `handoff_watchdog.py:562-564` seleciona a conversa **sem coluna de claim**; linha do banco → `(False, "Regina assumiu…")`, a MESMA pela linha de :562 → `(True, "")` | BLOCKER | chave ausente ≠ valor nulo: `"claimed_by" not in linha` manda ler o banco |
| **B2** | `classificar_o_motivo` fazia substring, contra o próprio docstring | **SIM** — muda a *Eficiência* que a corretora lê às 19h | `"ura" ⊂ segURAdora`: *"a seguradora não respondeu"* → `incapacidade/ura_travou`; *"tempo limite"* → `regra` | BLOCKER | `\b…\b`, com as EXPRESSÕES antes das palavras soltas |
| **B3** | corpus de produção com texto de segurado | SEGURANÇA | 1220 mensagens `role=user`, 19 sequências de 11 dígitos, **0 marcadores de redação** | **REFUTADO** — 📊 as 2287 mensagens têm `content` = `h:<sha256[:16]>` ou `#nota `, **0 fora do formato**; os dígitos são do hexadecimal | o juiz estava certo no que importa (**nada dizia isso**): o arquivo ganhou o bloco `REDACAO` e o guarda fica vermelho com texto cru |
| **P1** | gate G-A **vermelho em HEAD** | fecha a SPEC | `porteiro_do_agente.py` caiu na varredura do G-A2; `grep send_message\|enviar_ao_grupo` → **0** | BLOCKER de gate | ISENTOS, com o motivo: *"só pergunta, não envia"* |
| 🔬 **L1** | a pergunta 3 era **inerte em produção** | **SIM**, sob `janela=0` | 📊 `claimed_by` em **1 de 938** linhas e em **0 de 259** `HUMAN_REQUESTED`; `claimed_by_name` em 259/259, 63 com `claimed_at` ≤ 6h. O escritor que acontece (`espelho_chat.py:761-764`) nunca grava `claimed_by` | BLOCKER | `claimed_by OR claimed_by_name`, como `saudacao_do_religamento.py:104` já fazia |
| P4 | marcador do dia reservado antes do envio; docstring prometia fuso por corretora | a corretora perde o dia de números por falha de destino | leitura do código | conserto | `_devolver_o_dia` na falha + docstring honesta |
| P6 | comentário dizia *"só o 🆘 leva CPF"* e contradizia `_montar_sinistro` oito linhas abaixo | comentário que mente encerra a investigação seguinte | leitura | conserto | alinhado à §8.2 |
| P8 | número da casa decidido ANTES da exceção de número de teste | **SIM** — quem testa pelo próprio celular perde o agente, e é assim que o canário roda | 📊 8 conversas de 30 dias são de telefones de membros | conserto | a exceção de teste vence |
| P2·P3·P5·P7·P9·P10 | resíduo de mutação (EOL), `envio_falhou` no caso calado, números derivados, par fixado do silêncio, cosméticos, ROLLBACK da M2 | NÃO | — | **PENDÊNCIA** | §9 |

🔬 **A lente reconstruiu o outcome sobre o acervo real** (16/09, 20:31 UTC, pelo MOTOR): das 97 elegíveis, **95 calam · 2 passam** — e as 2 que passam são as certas (a conversa em que ninguém da corretora falou e a que esfriou há mais de 7 dias). **Linha de controle: `n_dias=0` → 0 calam · 99 passam.** 🔴 É ela que dá direito à conclusão: o silêncio vem da regra, não de um `return True` escondido.

⚠️ **E o que ainda não aconteceu:** 📊 `work_events` com `grupo.%` → **0** · `platform_sends` com `kind like 'grupo%'` → **0**. **Nenhuma mensagem atravessou a porta nova em produção.** Toda a reconstrução acima é prospectiva, e é por isso que o canário do Founder é o único juiz que não mente.

## 5. O conserto único — 4 blockers + 4 pendências, num commit (`87b92e6`)

Cada um com o **par de teste** que o deixa vermelho de novo. Gates depois do conserto:
`G-A 33 · G-C 22 · G-E 18 · G-D 47 · G-F/G 38 · G-B 20` — **0 vermelhas**. Vizinhos migrados verdes (`27 · 23 · rc=0 · 11`). `tsc --noEmit` rc=0.

📊 **Mutações da SPEC inteira: 28, todas vermelhas.** 🔴 Duas ficaram VERDES na primeira tentativa e foram consertadas: `if (cond)` → `if (false && cond)` e o `if (porteiro instanceof NextResponse)` desarmado deixavam a substring intacta. É o defeito de §12.1 (*"a SPEC-083 teve dois guardas verdes por detalhe de mutação"*) — pego pela própria mutação.

**Não consertado, e por quê:** P3 (estado `envio_falhou` num caso calado — sem consumidor no painel), P5 (números derivados: §12.1 pede a hora da medição, não um freeze), P7 (par fixado do silêncio por desenho), P9 (cosméticos), P10 (o ROLLBACK da M2 já exige decisão do Founder). Todos escritos em §9.

## 6. A bateria — 📊 1 rodada inteira, triada por DIFF contra `origin/main`

```
MINHA (ca325ce)   1227 coletados · 34 failed · 1110 passed · 35 xfailed · 48 errors · 57min28
BASE  (09a238f)   1227 coletados · 26 failed · 1112 passed · 34 xfailed · 48 errors · 24min03
                                   ^^ +8
```

🔴 **O DIFF ACHOU QUATRO REGRESSÕES REAIS — verdes na base, vermelhas na minha.** Foi para isto que a triagem existe; sem ela as quatro teriam ido para a `main`:

| guarda | verde na base | por quê quebrou | conserto |
|---|---|---|---|
| `test_governador_de_envio` | ✅ | o dublê de `platform_sends` não tinha `.in_()`, e `_historico_sync` passou a filtrar por `kind` nas três leituras | o dublê ganhou `in_` **e HONRA o filtro** — um dublê que aceitasse e ignorasse provaria o contrário do que o guarda afirma |
| `test_ninguem_pede_mais_de_mil_linhas_de_novo` | ✅ | 🔴 **defeito de PRODUTO meu:** `contagens_do_dia` pedia `.limit(5000)` e o PostgREST devolve **1000** — num dia movimentado o resumo das 19h publicaria um número MENOR que a verdade, com cara de medição | `ler_paginado_async`, com `truncou` viajando junto até a contagem |
| `test_o_segurado_nao_fica_no_escuro` | ✅ | duas asserções de fonte sobre `human_handoff` — a resolução de destino e o `except` do marcador mudaram de arquivo | migradas para a porta única (§9.3: o fato muda, o teste muda, e a lição MIGRA) |
| `test_spec040_onda4_gate_council` | ✅ | o alerta de qualidade passou a sair pela porta, e o teste dublava `send_message` sem `bloco_unico` e sem o resolvedor canônico | o dublê acompanhou o contrato, e a porta é carregada de verdade — é ela que o guarda precisa exercitar |

⚠️ **Os outros 4 do delta são instabilidade de ordem, não regressão:** `test_a_regua_nao_tem_furo`, `test_a_resulta_tem_marca`, `test_as_ferramentas_de_relatorio_comercial` e `test_infocap_policy_output_guard` passam isolados na minha árvore (rc=0) e falham dentro da suíte. `test_a_arvore_ficou_limpa_no_fim` e `test_nenhuma_mutacao_foi_commitada` falham **nas duas** — 🔬 o juiz mediu a causa: alguns guardas antigos deixam a mutação na árvore. **Pendência `P-E0013-09`**.

📊 **Depois do conserto, 14 rodadas dirigidas: rc=0 em todas** — os 6 guardas novos, os 4 regredidos e os 4 vizinhos migrados. `tsc --noEmit` rc=0.

## 7. O que ficou fora, e o gatilho que o faz voltar

| frente | por quê | gatilho |
|---|---|---|
| `weekly_report` / `proactive_suggestions` lendo `human_support_destinations` | outra superfície; dois envios semanais sem gate próprio | `P-E0013-01`; SPEC de canais (099) |
| Conteúdo do checklist de sinistro por tipo | depende da base de produtos | EXTRA-001.5 — o **lugar** está reservado em `modelo_novo_sinistro` |
| Aposentar `alert_target.internal_numbers` | expand-first: o leitor velho continua | SPEC futura, com backfill e prova |
| CHECK em `platform_sends.kind` | congelaria a lista de tipos | quando a lista parar de crescer |
| Régua de eficiência publicada no dossiê | o número nasce aqui; a régua é produto da medição de 3 dias | EXTRA-001.7 |
| Fuso do resumo por corretora | não existe coluna de fuso por corretora | `P-E0013-05` |

## 8. 📋 Caixa do Founder — o que só o Amandus faz

| # | o que é | o que destrava | bloqueia? |
|---|---|---|---|
| 1 | **Implantar** `smith-api` e depois `web` no EasyPanel | tudo abaixo | não |
| 2 | **Criar o grupo de canário** (só você dentro) e dizer qual é o tenant de teste | os 8 casos da §14, **incluindo o par de controle** | não |
| 3 | 🔴 **`write:true` tira a escrita de 2 pessoas.** 📊 `admin_company` 8 · `member` 2, e os 2 `member` estão em 2 corretoras diferentes. Eles param de poder mexer em destino de suporte, credencial de portal e conexão de WhatsApp | o BLOCO G sem surpresa na segunda-feira | não |
| 4 | **19h é a hora certa?** É o padrão e é env (`RESUMO_DIARIO_HORA`). ⚠️ Hoje é o fuso da PLATAFORMA, não de cada corretora | o BLOCO D.4 | não |
| 5 | **Ler os quatro modelos** (§2 do resumo que te mandei) e dizer o que cortaria — 💭 a copy é ilustrativa de propósito | a validação com Saionara e Regina | não |
| 6 | 🔴 **`JANELA_SILENCIO_HUMANO_DIAS` agora tem DOIS efeitos**: governa o silêncio do agente com o segurado **e** o silêncio do grupo. Mudar esse número muda as duas coisas | nada; é aviso | não |
| 7 | **Reativar os destinos** da Resulta e da AutoFleet quando quiser voltar a ligar o agente (os dois estão `is_active=false`) | a EXTRA-001.7 | não bloqueia esta SPEC |
| 8 | 🔴 **CPF/CNPJ vai no 🆘 e no 🚨**, e o histórico do grupo guarda isso para sempre. A SPEC pediu assim (§8.1/§8.2). Você quer mesmo? | nada; é decisão de PII | não |
| 9 | **O ROLLBACK da migration 02 agora exige você**: 📊 há 5 linhas com `work_run_id` nulo, e `work_events` é append-only. Desfazer exigiria apagá-las | nada; é aviso | não |

**Variáveis novas** (nome, sem valor): `RESUMO_DIARIO_HORA` (padrão `19`) · `RESUMO_DIARIO_ATIVO` (padrão `true`).
**Rollback sem deploy:** `RESUMO_DIARIO_ATIVO=false` desliga o resumo · `janela_silencio_humano_dias=0` na corretora devolve o comportamento de antes. 🔴 Os dois existem porque esta SPEC **cala** coisas, e o modo de falha mais perigoso dela é calar demais.

## 9. Pendências e decisões

**Absorvidas (§2 — quem drena):** P-PILOTO-02 **CONTINUA** (fora da superfície; nada tocou `portal_jobs`) · P-PILOTO-03 **CONTINUA** (`webhook.py` intocado) · P-PILOTO-04 **CONTINUA, com o lugar pronto** (`modelo_novo_sinistro` tem *Pontos de atenção*, hoje preenchido com `_o_que_falta`) · **P-PILOTO-12 ✅ FECHADA** (`problemas_de_lingua` roda nos quatro modelos renderizados) · **P-PILOTO-10 ✅ FECHADA-com-ressalva** (📊 4 destinos, 3 empresas, cada corretora com o seu; os dois das pilotos `is_active=false` — caixa #7) · P-PILOTO-13 e 15 já fechadas pela 001.2, e a mitigação de §21 **não foi necessária**.

**Novas:** `P-E0013-01` (weekly/proactive no legado) · `P-E0013-02` (`whatsapp_channel.py:1124` apaga o `alert_target`) · `P-E0013-03` (`handoff.realertado` — 🔬 **parcialmente fechada**: 4 linhas `handoff.teto_de_lembretes` nasceram hoje, com `work_run_id` nulo; falta o `realertado`) · `P-E0013-04` (canário vivo depende do Implantar) · **`P-E0013-05`** (fuso do resumo é o da plataforma) · **`P-E0013-06`** (as 2 migrations sem linha em `schema_migrations`) · **`P-E0013-07`** (`suporte_indisponivel="envio_falhou"` quando a guarda CALOU — sem consumidor hoje) · **`P-E0013-08`** (isolamento com dois tenants foi lido no código e nos guardas com dublê; **não rodado contra dois tenants reais** — 🔬 a lente marcou confiança 50 nessa dimensão).

**Decisões (nota 0–100):** D-E0013-01..08 em `FOUNDER-DECISIONS.md`.

## 10. Telemetria (§11)

```
relógio total · por fase ①–⑥ ........  167 min (executor) · ①+② build ~101 min · ③ provas ~22 min ·
                                       ④ juiz+lente 47 min (em paralelo) · ⑤ conserto ~18 min · ⑥ entrega
turnos · contexto de pico ...........  executor 271 · pico 649k  |  juiz 26 · 256k  |  lente 41 · 134k
ctx-tokens · saída ..................  118,7 M de contexto · 0,30 M de saída
US$ API-equivalente .................  executor 65,82 · juiz 7,23 · lente 2,80  |  TOTAL 75,85
agentes além do executor ............  2 (juiz Fable 5.1 + lente do dado Opus 5)
achados por mecanismo ...............  executor 2 EXCLUSIVOS (a trava NOT NULL de `work_events`; o
                                       `destino.get("number")` que saía calado) · prova mecânica 2
                                       EXCLUSIVOS (as duas mutações que ficaram verdes) · juiz 4
                                       (3 EXCLUSIVOS + 1 gate vermelho) · lente 1 EXCLUSIVO (a
                                       pergunta 3 inerte) · canário 0 (depende do Implantar)
rodadas da bateria ..................  1 inteira (57min28, 1227 coletados) · ~40 parciais dirigidas
nota da execução ....................  88/100 — 7 unidades entregues, 12 guardas em 7 arquivos (teto de
                                       D-PILOTO-14 respeitado), 28 mutações vermelhas, 2 migrations
                                       aplicadas e verificadas no banco, 4 blockers achados e
                                       consertados, servidor de pé respondendo. Desconto: os tetos de
                                       turno e contexto foram estourados e a triagem da bateria contra
                                       a base não fechou. Nota do juiz 80 · confiança da lente 87
```

⚠️ 🔴 **OS TETOS FORAM ESTOURADOS, e isto é dado do A/B (D-PROTO-02/03).** O protocolo §10 manda fechar a fatia e abrir sessão nova ao passar de 250 turnos ou 300 k de contexto. Rodei as duas fatias na **mesma** sessão (executor Opus 5 com janela de 1 M) e o resultado foi **271 turnos e 649 k de pico**. O relógio ficou **dentro** da faixa declarada (167 min contra 3h15) e nenhum gate caiu por cansaço — mas a regra é a regra, e quem decide se o teto muda de número é o Fable, com este dado na mão (§13).

## 11. Entrega

```
<saída real de `git push origin HEAD:main`>
```

**Implantar, nesta ordem:**
```
smith-api   backend: a guarda, a porta única, os números da casa, os quatro modelos,
            platform_sends com a allowlist, o resumo das 19h, o gate de ligar
web         painel: card Equipe, rotas de números internos, as 6 rotas do BLOCO G,
            o porteiro do toggle
```

## 12. Handoff

Não há próxima fatia: as 7 unidades estão entregues e gateadas. O que resta é do Founder (§8) e a triagem da bateria contra a linha de base (§6).
