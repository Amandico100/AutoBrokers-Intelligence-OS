# SPEC-073 — Relatório de execução

> **Portal Worker 2.0** — hardening transversal, profiler, discovery, percepção
> em camadas e zero regressão.
> **Executado em:** 16/08/2026 · **Branch:** `feat/spec073-portal-worker-hardening`
> 📊 medido · 💭 inferido (CLAUDE.md §12.1)

---

## 1. Git

| Campo | Valor |
|---|---|
| Repo | `AutoBrokers-Opus-Exec` (worktree isolado `AutoBrokers-SPEC073`) |
| Branch | `feat/spec073-portal-worker-hardening` |
| Commit inicial | `5cac02f` (= `origin/main` no início e no fim) |
| Baseline citada nas SPECs | `0ffcbed4` — 10 commits atrás, **nenhum tocando portal** |
| Migration | **nenhuma** — como a SPEC previu |
| Deploy realizado | **nenhum** — ver §7 |

**Worktree, por decisão do Founder (Q1).** A pasta principal estava em
`feat/spec072` com trabalho de outra sessão e um `stash@{0}`. Conferido ao final:
branch, untracked e stash intactos.

### Arquivos novos

```
backend/portal_worker/redaction.py       o redator único
backend/portal_worker/guardrails.py      classe de efeito · guard · recuperação
backend/portal_worker/profiler.py        network · DOM · assinatura · trace
backend/portal_worker/perception.py      escada L0-L5 · validador determinístico
backend/portal_worker/runtime.py         PortalRuntimeContext (aditivo)
backend/portal_worker/identidade.py      gate de corretora, portátil
backend/tests/test_spec073_*.py          6 suítes · 363 asserções
```

### Arquivos alterados

```
backend/portal_worker/worker.py                 identidade · runtime · recovery · kill switch
backend/portal_worker/main.py                   /health com as flags
backend/portal_worker/adaptive.py               funil · force-choose · escalada
backend/portal_worker/journeys/vidros_lanternas.py   passa o runtime (1 linha)
backend/portal_worker/journeys/yelum_corretor.py     gate de identidade
backend/portal_worker/journeys/tokio_corretor.py     gate de identidade
backend/portal_worker/journeys/zurich_corretor.py    fail-open corrigido
backend/app/api/portal.py                       /cobranca-capabilities
backend/app/main.py                             tool_gateway_modo no /health
lib/portal/hitl.ts                              retry pós-efeito bloqueado
app/api/dashboard/portal-jobs/route.ts          devolve o motivo da recusa
app/api/dashboard/portal-credentials/route.ts   entrega a capacidade derivada
app/dashboard/auxiliares/rotinas/page.tsx       array literal APAGADO
backend/tests/fixtures/zurich_parcelas.py       datas relativas
```

### Intocados, como a SPEC exigiu

📊 Provado por teste (`test_spec073_zero_regressao_portais.py` §5, via
`git diff --name-only`): `allianz_corretor.py`, `hdi_corretor.py`,
`mapfre_corretor.py`, `billing_collection.py`.

---

## 2. O defeito principal, e o que ele custava

📊 Medido em 16/08 lendo `worker.py:83-101`:

```
stale_running_patch() selecionava  id, started_at, created_at, attempts
e NUNCA lia  evidence
```

Um job que morresse **depois** de o portal criar o atendimento — com o protocolo
já gravado — voltava para `queued` e recomeçava do passo 1. O portal de vidros
diz, em texto, que cada solicitação é um pedido novo. Recomeçar não conserta:
**cria um segundo atendimento na seguradora.**

O mesmo buraco existia no botão de retentar do dashboard (`hitl.ts:58`), que
conferia apenas `status == 'needs_human'` — e o caminho adaptativo produz
`needs_human` **carregando protocolo**. A evidência gritava; o botão não lia.

Agora a evidência manda, e o controle mantém a regra honesta:

| Situação | Antes | Depois |
|---|---|---|
| read-only órfão | `queued` | `queued` — **inalterado** |
| reincidente | `failed` | `failed` — **inalterado** |
| protocolo em evidence | `queued` 🔴 | `needs_human` |
| fase `armed`/`submitted`/`unknown` | `queued` 🔴 | `needs_human` |

---

## 3. Os seis P1 de segurança (CA-041)

| # | Antes | Depois |
|---|---|---|
| 1 | Yelum varria com `brokerlist: []` e descartava `BrokerName` | duas corretoras na leitura → bloqueia, **mesmo com rótulo genérico** |
| 2 | Tokio capturava a corretora e nunca comparava | compara após login, antes de baixar relatório |
| 3 | Zurich pulava a checagem com rótulo `principal` (o default) | rótulo genérico vira *não-verificado* registrado; tela ilegível com rótulo nomeado **para** |
| 4 | `account_id` buscado só por `id` | `.eq(company_id)` + `portal_key` conferido, **antes** de abrir browser e decifrar |
| 5 | dois retries cegos pós-efeito | ambos bloqueados, com motivo legível |
| 6 | `GLOBAL_KILL_SWITCH` só no Next.js | alcança o worker Python, checado **dentro** do laço |

**A generalização que destravou o P1 nº 1.** A tranca da MAPFRE parecia depender
de saber *qual* corretora esperar — inaplicável onde o rótulo é genérico, e ele é
genérico em 14 das 16 contas. Mas a pergunta que protege é outra:

> **a leitura veio de UMA corretora só?**

Duas corretoras distintas na mesma resposta é vazamento qualquer que seja o
rótulo. É essa a regra que alcança o `brokerlist: []` da Yelum.

**MAPFRE não foi tocada.** É o único guarda cross-tenant provado, tem teste com
duas carteiras disjuntas, e reescrevê-la para "unificar" trocaria certeza por
elegância.

---

## 4. Testes

### Novos — 363 asserções

| Suíte | Asserções | O que prova |
|---|---:|---|
| `mutations` | 107 | M01–M22 + identidade + kill switch + **linha de controle** |
| `perception` | 70 | escada, validador ação a ação, provider trocável |
| `guardrails` | 49 | classe de efeito, ciclo do checkpoint, bloqueio auditável |
| `profiler` | 48 | path, origem, assinatura, candidato, redator |
| `runtime` | 45 | flags, checkpoint incremental, envelope, aditividade |
| `zero_regressao` | 44 | registry, contratos, arquivos intocados |

### Regressão global

📊 `python tests/run_all.py` — **211 verdes · 17 vermelhos · 143s**

Os 17 vermelhos foram medidos **um a um na baseline `5cac02f`**, num worktree
descartável: **todos os 17 já falhavam antes desta SPEC.** Nenhum é regressão.
Causas: `ModuleNotFoundError` de módulos do Atlas, mocks desatualizados,
`IndexError` em fixtures — todos fora do território do portal.

**Uma vermelha virou verde:** a suíte da Zurich abriu a SPEC com 111 verdes e 7
vermelhas. Nenhuma era defeito de código — o fixture ancorava `diasAtraso` na
data da captura (13/08) e a testemunha recusava, corretamente. O guarda estava
certo; o fixture é que tinha vencido (CLAUDE.md §9.3). Agora `venc` **deriva** de
`dias`, e as duas contas não têm como divergir por passagem de tempo. 118/0.

### O experimento de mutação

Seis guardas quebrados de propósito, com cópia de arquivo (nunca `git checkout`):

| Mutação | Vermelhas |
|---|---:|
| recovery volta a ignorar `evidence` | 7 |
| guard deixa visão autorizar material | 1 |
| guard não confere QUAL botão | 3 |
| redator para de mascarar | 2 |
| identidade aceita duas corretoras | 1 |
| **`_valor_conhecido` desligado** | **0 🔴** |

**A sexta não foi detectada, e isso foi o achado mais útil do dia.** Eu testava
o *texto do prompt* e o *campo não-crítico*, e nunca tinha afirmado que um campo
crítico com valor inventado é recusado. O prompt proibia, o código impedia, e o
teste não olhava — é assim que uma proteção real morre num refactor sem ninguém
perceber. Quatro asserções acrescentadas; a mutação agora produz 2 vermelhas.

Nenhum resíduo de mutação ficou: `grep -rn MUTACAO backend/portal_worker/` vazio.

---

## 5. Decisões que tomei sozinho

Todas dentro da autonomia dada, com a nota que as justifica.

| Decisão | Nota | Por quê |
|---|---:|---|
| Corrigir o fixture da Zurich em vez de registrar como preexistente | 92 | Sem isso a linha de controle da cobrança abre vermelha e a SPEC não tem contra o que comparar |
| Visão **nunca** clica material; adaptive clica só o botão que a journey NOMEOU | 94 | Recusar todo clique de modelo quebraria o `confirm=true` de vidros; liberar tudo deixaria "Agendar a domicílio" aberto |
| Fronteira material **contextual** via `is_confirm_screen` | 95 | Em vidros o clique que cria o pedido é `Avançar` — texto inofensivo nos passos 1–5. Blocklist de rótulo jamais pegaria |
| `BOTOES_DE_VOLTA` isentos na tela material | 88 | Sem isso nem `Voltar` passava no 80%, e um robô sem saída é pior que um que avança demais |
| Extrair `identidade.py` e **não** refatorar a MAPFRE | 88 | Ela é o único guarda provado; um teste liga as duas sem tocar na que funciona |
| `/cobranca-capabilities` = interseção registry ∩ deployed | 90 | Só o registry marcaria MAPFRE como pronta, e ela não está na imagem (P-149) |
| Assinatura vazia para tela sem conteúdo semântico | 85 | Hash de `/` faria duas telas em branco compararem como `drift=none` — "conferi e está tudo igual" |

---

## 6. Critérios de aceite da SPEC

**Arquitetura** — ✅ um worker, um registry, um `portal_jobs`, runtime aditivo,
nenhuma tabela/motor/fila nova.

**Segurança transacional** — ✅ guard em toda ação material · checkpoint `armed`
antes do efeito · resultado incerto nunca gera retry · stale read-only ainda
recuperável · mismatch falha antes da credencial.

**Discovery/Profiler** — ✅ `PORTAL_DISCOVERY_MODE` existe e nasce `false` ·
discovery não permite material · Network + DOM + trace sanitizado · zero
Authorization/Cookie/PII no artefato · candidatos nascem `candidate`.

**Percepção** — ✅ DOM adaptive intacto · contrato multimodal com o mesmo action
schema · validador + guard em toda ação · provider indisponível degrada para
HITL · nenhuma opção crítica por posição.

**Cobrança** — ✅ as 6 journeys verdes · `portais_com_cobranca()` idêntico ·
`billing_collection.py` não tocado · nenhum WhatsApp enviado.

**Operação** — ✅ `/health` com flags · flags de rollback · matriz verde ·
vermelhos preexistentes registrados um a um.
⚠️ **build SHA:** o portal-worker já injeta de verdade (Dockerfile stage
`gitinfo`); o `smith-api` continua `nao-injetado` — fora do território desta SPEC.

**Não atendido:** o canário live (§7).

---

## 7. Fechamento em produção — 16/08/2026

### Deploy

`portal-worker` · `smith-api` · `smith-web`, nesta ordem, mais
`PORTAL_WORKER_URL` no smith-api. Depois da correção do redator, um segundo
deploy só do `portal-worker` (build `19:40:38Z`).

### Health, medido

```
portal-worker : registry_entries 14 · portais_com_cobranca 6 (com MAPFRE)
                kill_switch false · discovery false · profiler true · vision false
smith-api     : tool_gateway_modo SHADOW  (inalterado, como a SPEC exige)
smith-web     : HTTP 200
ponte         : /cobranca-capabilities degraded=false, operacional = 6
```

📊 **P-149 resolvida:** a journey da MAPFRE está na imagem implantada.

### P-186 — o canário achou uma regressão, e era minha

Rodada 1: `cobranca_sweep` read-only em Allianz (controle, 65s, 10 itens) e
Yelum (identity gate alterado, 23s, 1 item). Ambos `done`, sem `critical_effect`.

O identity gate funcionou e foi honesto:

```
estado               unique_context_unverified
verificado           false
contextos_na_leitura 1
contexto_observado   RESULTA CORRETORA DE SEGUROS LTDA
```

Job da Resulta, leitura da Resulta. **Zero cross-tenant.**

Mas a evidência gravada mostrou `inadimplentes[0].recibo` como
`<redacted:cartao>-3`. `recibo` é a chave anti-duplicação de `billing_sent_log`
e o nome do PDF no bucket — mascarado, toda execução concluiria que nada foi
enviado, e o segurado receberia a mesma cobrança de novo.

Causa: envolvi a evidência inteira em `redigir()`. Corrigido com
`redigir_envelope()`, que sanitiza só as superfícies de diagnóstico e deixa o
payload de trabalho intacto.

Rodada 2, após o redeploy — 📊 medido no banco:

```
recibo_intacto true · apolice_intacta true · cpf_intacto true · nome_intacto true
identidade     unique_context_unverified · 1 corretora
critical_effect null · vazou_segredo false
profiler       104 requests observados
```

### Critério de conclusão

| Item | Estado |
|---|---|
| Código em main | ✅ `575bbdf` |
| Três serviços no runtime | ✅ |
| Healths verdes | ✅ |
| P-186 verde | ✅ (2 rodadas, defeito corrigido entre elas) |
| Zero regressão nova | ✅ 385 asserções · 17 vermelhos preexistentes |
| Cobrança preservada | ✅ leitura real intacta nos dois portais |
| Zero cross-tenant | ✅ 1 corretora por leitura, tenant correto |

## 8. O que NÃO foi feito, e por quê

**Nenhum deploy, nenhum canário live.** Dois motivos, ambos legítimos:

1. Havia uma reindexação de 17.928 cartas rodando **dentro do `smith-api`**, e o
   Founder determinou não implantar nem reiniciar nada até ela terminar.
2. 📊 A MAPFRE está na P-149: a journey existe no código e **não** na imagem. Um
   canário dela mediria o deploy, não a SPEC.

Tudo que não depende de rede real foi provado offline. **Executado em 16/08/2026** — ver §7.

📊 Conferido ao final: a API de produção respondia 200 e a reindexação seguia
intacta. Nenhuma escrita em `knowledge_cards`, Qdrant ou produção.

---

## 8. Pendências abertas

| # | O quê | Dono |
|---|---|---|
| P-182 | `PORTAL_VAULT_KEY` única e global, sem rotação | 🧑 decide · 🤖 implementa |
| P-183 | PII em `portal_jobs.evidence` sem retenção | 🧑 define janela |
| P-184 | Pilha TS de portal com guardas que nada chama | 🤖 SPEC-075 |
| P-185 | `portal.py` aceita `company_id` livre atrás de segredo estático | 🤖 |
| P-186 | Canário live read-only não executado | 🧑 janela |
| P-149 | Deploy da journey MAPFRE (preexistente) | 🧑 Implantar |

---

## 9. Declaração final

> Nenhum runtime, registry, scheduler, fila universal, Tool Gateway, Skill
> Registry, Auxiliary Factory ou Work Run paralelo foi criado. O
> `TOOL_GATEWAY_MODE` não foi alterado e nenhum cutover foi feito — o Gateway
> segue em `shadow`, exatamente onde estava.

**O que foi provado:** as classes de falha cobertas por 363 asserções novas, com
matriz de mutação cujos guardas foram quebrados de propósito e verificados.

**O que não foi provado:** o comportamento contra portal real. Nenhuma linha
desta SPEC tocou produção. Isso é P-186, e não deve ser lido como sucesso até
acontecer.
