# Relatório de execução — SPEC-059: Briefing, Proatividade & Garimpo v3

**Produto:** AutoBrokers Intelligence OS
**SPEC:** [`docs/canon/specs/SPEC-059-briefing-proatividade-garimpo-v3.md`](../specs/SPEC-059-briefing-proatividade-garimpo-v3.md)
**Branch:** `feat/spec059-briefing-proatividade`
**Worktree:** `AutoBrokers-Opus-Exec`
**Executor:** Opus 5 (1M) — sessão única
**Início:** 26/07/2026 · **Conclusão:** 26/07/2026
**Commit inicial:** `e9fedefa26d86bcc6d5f8b9e4aea8ca86f4b758b`
**Commit final:** registrado no merge desta branch
**Estado final:** **CONCLUÍDA COM RESSALVAS** — código, schema e gate verdes; a
ativação em produção depende de um deploy que é ação do Founder (§6).

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado. Execução continua no **Work OS** (SPEC-055);
      ferramenta continua no **Tool Gateway** (SPEC-056); peça continua no **Artifact
      Hub** (SPEC-057); automação continua na **Auxiliary Factory** (SPEC-058);
      memória continua no **MemoryService** existente. O agendamento entrou no laço
      de manutenção do Smith Worker que **já existia** — nenhum scheduler novo.
- [x] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo exposto em log, artifact, blueprint ou neste relatório.
- [x] Nenhum escopo reduzido. A única consolidação (9 tools → 4 no chat) está em
      CA-010 e **não remove nenhuma operação** — todas seguem disponíveis nas APIs.
- [x] Nenhum dado atravessou tenants nas verificações executadas.
- [x] `CLAUDE.md`, `EXECUTION-MASTER-PLAN.md`, `FOUNDER-DECISIONS.md`,
      `MIGRATIONS-AUTHORITY.md` e a SPEC-059 integral foram lidos no início.

---

## 1. Resumo executivo

O AutoBrokers passou a ter um pipeline proativo com procedência: evento → sinal
com evidência → diagnóstico que separa fato de inferência → recomendação com
ação real → execução pelo Work OS → medição do resultado.

Entrou o **Centro de Briefing** da corretora (Hoje, Esta semana, Oportunidades,
Histórico, Preferências), a **Central de Inteligência** no Admin (sinais,
diagnósticos, demanda agregada, regras com qualidade observada), **12 detectores
determinísticos** publicados como regras versionadas e ajustáveis sem deploy, o
**Garimpo v3** (que preserva a regex já calibrada e muda o destino), o **Demand
Radar** anonimizado e o **Memory Fabric** do Lote 4 da SPEC-052.

Quatro motores proativos antigos pararam de enviar por conta própria. Eles não
foram apagados: o algoritmo de regressão e as contagens do relatório semanal
viraram fontes do pipeline; o envio direto saiu.

**O achado mais grave desta SPEC não estava no texto dela.** A correção de
memória da SPEC-054 estava **inerte em produção** — `graph.py:1052` chama o
gatilho com `last_message_at=datetime.now()`, o que torna a inatividade sempre
zero. Dois meses depois, `session_summaries` continuava em 0 com 144 conversas.
A conclusão: o gatilho não pode viver dentro do turno. Ver CA-011.

Cinco defeitos foram encontrados pelos próprios testes e dois pelo canário com
dado de produção — todos corrigidos no código, nunca no teste (§5.4).

Ficou de fora: PDF renderizado no servidor (exige Chromium na imagem — Regra 1
do CLAUDE.md) e o painel de admin do Radar em peça própria. Detalhes em §2.

---

## 2. Escopo executado por bloco

### Bloco A — Signal Intelligence Foundation, Garimpo v3 e migração estrutural

| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|
| Migrations, RLS, FKs, índices | CONCLUÍDA | 3 migrations; 16 tabelas com RLS ligada e 0 policy |
| Envelope canônico de evento (§7) | CONCLUÍDA | `intelligence/schemas.py:EventEnvelope`; teste `[16]` |
| Signal / Evidence / Finding / Recommendation | CONCLUÍDA | `signal_service.py`, `evidence_service.py`, `finding_engine.py`, `recommendation_service.py` |
| Briefing profiles / publications / items | CONCLUÍDA | `briefing_service.py`; 3 tabelas |
| Demand clusters | CONCLUÍDA | `demand_cluster_service.py`; teste `[11]` |
| Redaction | CONCLUÍDA | `redaction_service.py` — autoridade única, a Factory delega |
| Dedupe, cooldown, escalonamento | CONCLUÍDA | `dedupe_service.py`; testes `[4]` e `[5]` |
| Scoring (§12) | CONCLUÍDA | `priority_service.py`; teste `[3]` |
| Rule engine | CONCLUÍDA | `rule_engine.py` + 12 regras publicadas |
| Garimpo v3 | CONCLUÍDA | `garimpo_v3.py` — importa a regex de `broker_insights`, não recopia |
| Adapters históricos | CONCLUÍDA | `legacy_adapter.py`; teste `[17]` |
| Skills base | CONCLUÍDA | 3 Skills publicadas, ligadas ao papel `core` |
| Testes unitários e multi-tenant | CONCLUÍDA | 19 grupos verdes |
| **Lote 4 SPEC-052 — Memory Fabric** (enxerto D1) | CONCLUÍDA | `memory_fabric.py`, `company_memories`, `knowledge_candidates`; CA-011 |

**Gate A:** schema verde · zero órfão · eventos viram Signals idempotentes ·
evidência rastreável · Garimpo produz sinais e pedidos · nenhuma publicação
direta nova · dados sensíveis redigidos. **VERDE.**

### Bloco B — Briefings, recomendações, feedback, UI e integração operacional

| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|
| Finding Engine | CONCLUÍDA | `finding_engine.py`; teste `[7]` |
| Recommendation Service | CONCLUÍDA | `recommendation_service.py`; teste `[13]` |
| Outcome Service | CONCLUÍDA | `outcome_service.py`; teste `[8]` |
| Briefing Diário | CONCLUÍDA | `briefing_service.py` + workflow `intelligence.daily_briefing` |
| Briefing Executivo Semanal | CONCLUÍDA | workflow `intelligence.weekly_executive_briefing` |
| Alertas críticos event-driven | CONCLUÍDA | `event_adapter.py` + `delivery_policy.py`; teste `[6]` |
| Artifact templates (§17.1) | CONCLUÍDA | 5 templates novos em `artifacts/templates.py` |
| Delivery | **PARCIAL** | política, canais e idempotência prontos; o **envio externo** fica desligado até o Founder autorizar (D13). Ver §10. |
| Feedback | CONCLUÍDA | `feedback_service.py` |
| Preferences | CONCLUÍDA | API + tela + tool do chat |
| Core tools | CONCLUÍDA | 4 tools; CA-010 |
| Dashboard tenant | CONCLUÍDA | `app/dashboard/briefing/page.tsx` + pilar na navegação |
| Admin mínimo | CONCLUÍDA | `app/admin/inteligencia/page.tsx` |
| Integração Auxiliary Factory | CONCLUÍDA | `execution.py:_propor_rotina` chama a Factory da SPEC-058 |
| Integração Work Runs / approvals | CONCLUÍDA | `execution.py:_abrir_work_run`, idempotente por recomendação |
| Observabilidade | CONCLUÍDA | `/api/admin/intelligence/overview` e `/quality` |

**Gate B:** briefing sob demanda funciona · briefing agendado cria Work Run ·
recomendação executável cria caminho canônico · feedback altera cooldown ·
outcome registra estado correto · nenhuma mensagem sem evidência ou validade.
**VERDE em código e teste**; a prova em produção depende do deploy (§6).

### Bloco C — Regras iniciais, cutover, canários e lançamento

| Entrega prevista na SPEC | Estado | Evidência |
|---|---|---|
| Detectores iniciais (§23.1 a §23.12) | CONCLUÍDA | 12 detectores em `detectors/` |
| Migrar Garimpo | CONCLUÍDA | `check_garimpo` desvia sob cutover |
| Migrar sugestões | CONCLUÍDA | `check_suggestions` idem |
| Migrar relatório semanal | CONCLUÍDA | `check_weekly_report` idem |
| Migrar regressão | CONCLUÍDA | algoritmo importado pelo detector; envio direto desligado |
| Remover schedulers diretos | CONCLUÍDA COM RESSALVA | os 4 jobs deixaram de agir; **as registrações continuam** para permitir rollback por variável de ambiente, sem deploy. Ver §10. |
| Substituir Admin Insights | CONCLUÍDA | Central de Inteligência é a autoridade; rota antiga vira submenu "(legado)" |
| Remover writers paralelos | CONCLUÍDA | `broker_insights` vira projeção; §10.15 |
| Canário Amandus | N/A com justificativa | Amandus é `is_technical=true` e o tick a exclui de propósito (§6) |
| Canário Resulta | CONCLUÍDA | 2 falsos positivos encontrados e corrigidos — CA-012 |
| Canário AutoFleet | CONCLUÍDA | zero sinal; comportamento honesto de ausência confirmado |
| Calibrar limiares e ruído | CONCLUÍDA | CA-012 |
| Ativar produção | **PENDENTE DE DEPLOY** | ação do Founder; §6 |
| Relatório final | CONCLUÍDA | este documento |

**Entregas da SPEC que NÃO foram executadas:**

1. **PDF renderizado no servidor** (§16.2 "Formatos: PDF"). Exige Chromium na
   imagem do contêiner. A Regra 1 do CLAUDE.md proíbe mudança de infraestrutura
   antes do preflight. O CSS de impressão da SPEC-057 já cobre o caminho pelo
   navegador, e o Artifact do briefing é gerado normalmente — o que falta é só a
   conversão server-side. Mesmo bloqueio já registrado no Master Plan.
2. **Peça `briefing.demand_radar_admin` renderizada.** O template está registrado
   e o Radar existe na tela do Admin; o que não entrou foi gerar a peça em PDF do
   radar. Mesmo bloqueio do item 1.
3. **Envio externo proativo (WhatsApp/e-mail).** A política de canal, quiet hours
   e limites está implementada e testada, mas o disparo real permanece desligado.
   Motivo em §10 — não é redução de escopo, é sequência de segurança.

---

## 3. Arquivos alterados

```text
54 arquivos: 39 criados, 15 alterados, 0 removidos
12.806 inserções, 19 remoções
```

| Área | Criados | Alterados | Removidos |
|---|---:|---:|---:|
| Backend | 28 | 12 | 0 |
| Frontend | 4 | 2 | 0 |
| Migrations | 3 | 0 | 0 |
| Testes | 1 | 1 | 0 |
| Documentação | 2 | 1 | 0 |

Backend criado: pacote `app/services/intelligence/` (21 módulos + 4 detectores),
`app/services/memory_fabric.py`, `app/api/intelligence.py`,
`app/agents/tools/intelligence_tool.py`.

Backend alterado: `graph.py` (anexa as tools sob capability; comentário do
gatilho de memória), `main.py` (rotas), `smith_worker.py` (tick + varredura de
memória no laço existente), `work/workflows.py` (carga dos workflows extras),
`artifacts/templates.py` (5 templates), `report_tool.py` (novos tipos),
`auxiliaries/factory.py` (redação delegada), e os 4 legados do cutover.

---

## 4. Migrations

### `20260726_01_spec059_intelligence_fabric.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Registro canônico de sinal, evidência, finding, recomendação, briefing, regra, demanda e evento |
| **Expand-first** | sim — só cria |
| **Destrutiva** | não |
| **APPLY** | 14 tabelas + índices + RLS + triggers de `updated_at` e append-only |
| **VERIFY** | executado — ver saída abaixo |
| **ROLLBACK** | `drop table` das 14 tabelas; escrito no arquivo antes de aplicar |
| **Aplicada em produção** | sim · 26/07/2026 · 5 versões registradas (aplicada em blocos) |
| **MANIFEST atualizado** | não — ver §10 (dívida herdada, não criada aqui) |

**Saída real do VERIFY estrutural:**

```text
16 tabelas | relrowsecurity = true | policies = 0  (todas)
```

**Saída real do VERIFY de conduta** (as garantias que o banco recusa violar):

```text
ERROR: VERIFY_RESULTADO garantias_provadas=5 de 5
```

As cinco, provadas por INSERT que o Postgres recusou:

1. Finding com inferência e sem fato → recusado.
2. Recomendação de risco alto sem `approval_required` → recusada.
3. Outcome `realized` sem `measured_at` → recusado.
4. Knowledge Candidate global carregando `company_id` → recusado.
5. `UPDATE` em `intelligence_events` → recusado (append-only).

A transação foi abortada de propósito. Confirmação de que nada persistiu:

```text
findings=0 recommendations=0 outcomes=0 knowledge_candidates=0 events=0
```

### `20260726_02_spec059_memory_fabric.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | `company_memories` (memória da corretora) e `knowledge_candidates` (objeto comum do aprendizado) |
| **Expand-first** | sim |
| **Destrutiva** | não |
| **APPLY** | 2 tabelas + índices + RLS + triggers |
| **VERIFY** | incluído no bloco de 5 garantias acima (itens 4) |
| **ROLLBACK** | `drop table` das 2 tabelas |
| **Aplicada em produção** | sim · 26/07/2026 |
| **MANIFEST atualizado** | não — ver §10 |

### `20260726_03_spec059_regras_skills_tools.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | 12 regras, 2 capabilities, 4 tools, 3 Skills, requisitos e bindings |
| **Expand-first** | sim — `ON CONFLICT DO NOTHING` em tudo |
| **Destrutiva** | não |
| **APPLY** | seeds idempotentes |
| **VERIFY** | executado — ver saída abaixo |
| **ROLLBACK** | `delete` por chave, sem tocar no que já existia |
| **Aplicada em produção** | sim · 26/07/2026 · 3 versões |
| **MANIFEST atualizado** | não — ver §10 |

**Saída real do VERIFY:**

```text
regras_ativas            12
tools_intelligence        4
tool_releases_publicadas  4
skills_publicadas         3
skill_tool_reqs           5
skill_bindings            3
capability_bindings       2
capabilities_sem_scope    0
```

`capabilities_sem_scope = 0` importa: o Gate 5 da SPEC-056 exige `scope`
preenchido em toda capability sensível.

**Advisors:** não houve alteração de função `SECURITY DEFINER`, de grant, de
view nem de policy. As 16 tabelas nascem com RLS ligada e zero policy — o mesmo
padrão das SPECs 055/057/058, que já está refletido no baseline de advisors
"ZERO ERROR / ZERO WARN" da SPEC-054. Nenhum advisor novo foi introduzido por
esta SPEC. **INFERÊNCIA**, não fato: não reexecutei o painel completo de
advisors, porque nenhuma das alterações pertence às classes que ele avalia.

---

## 5. Testes executados

### 5.1 Obrigatórios

| Teste | Comando | Resultado | Saída |
|---|---|---|---|
| Isolamento multi-tenant | pack `IDN-01` | PASS | `test_spec048_isolamento_corretoras.py` |
| Isolamento no dedupe da SPEC-059 | teste `[5]` | PASS | mesma falha em 2 corretoras → 2 chaves distintas |
| P0 de segurança / RPC / Storage | pack `SEC-01..05` | PASS | 5 casos |
| Idempotência de side effect | pack `EXE-01` | PASS | `test_spec055_work_os.py` |
| Idempotência de publicação (§28.3) | índice único | APLICADO | `ux_briefing_publications_idempotente` |
| Migration em ambiente vazio | — | **N/A** | todas são `IF NOT EXISTS`; ambiente efêmero não existe no projeto (dívida da SPEC-054, §10) |
| Migration incremental sobre estado atual | APPLY + VERIFY | PASS | saídas em §4 |
| Approval / IDOR | pack `SKL-02` | PASS | aprovação pelo mais restritivo |
| SSRF e egress | pack `EGR-01`, `SEC-01` | PASS | — |
| MCP env allowlist | pack `SEC-03` | PASS | — |

### 5.2 Proporcionais ao risco desta SPEC

`PYTHONIOENCODING=utf-8 python backend/tests/test_spec059_intelligence.py`

| # | Grupo | Resultado |
|---|---|---|
| 1 | Nenhum alerta existe sem evidência | PASS |
| 2 | Alerta crítico nunca nasce de palpite do modelo | PASS |
| 3 | A prioridade é uma conta que dá para mostrar | PASS |
| 4 | O corretor não recebe o mesmo aviso todo dia | PASS |
| 5 | A chave de dedupe nunca cruza corretoras | PASS |
| 6 | Ninguém é acordado de madrugada por item que espera | PASS |
| 7 | Inferência nunca é apresentada como fato | PASS |
| 8 | Resultado não medido é inconclusivo, nunca sucesso | PASS |
| 9 | Dado de segurado não vaza para painel nem agregado | PASS |
| 10 | Nada entra no conhecimento sem alguém olhar | PASS |
| 11 | O agregado da plataforma não identifica a corretora | PASS |
| 12 | O briefing não preenche vazio com frase bonita | PASS |
| 13 | O botão "Resolver" só aparece quando existe caminho | PASS |
| 14 | Os detectores contam o que existe, não o que parece | PASS |
| 19 | Os dois falsos positivos que o dado real revelou | PASS |
| 15 | O AutoBrokers lembra do corretor entre conversas | PASS |
| 16 | Evento avulso não entra no pipeline sem contrato | PASS |
| 17 | Nenhum motor antigo volta a enviar por conta própria | PASS |
| 18 | Cobertura e dinheiro nunca rodam sozinhos | PASS |

```text
====================================================================
TODAS AS GARANTIAS VERIFICADAS
```

`npx tsc --noEmit -p tsconfig.json` → **exit 0, zero erro.**

### 5.3 Broker Outcome Regression Pack

```text
==========================================================================
passaram=26  falhas_obrigatorias=0  avisos=0  pulados_por_ambiente=0  total=26

GATE VERDE
```

Era 24/24. Entraram **INT-01** (o briefing não inventa número nem esconde
ausência de dado) e **INT-02** (verificação estrutural: evidência obrigatória,
tier, cooldown, quiet hours, outcome e cutover presentes no código).

| Cenário | Resultado | Observação |
|---|---|---|
| Identidade e multiempresa | PASS | `IDN-01` |
| Chat e agentes | PASS | `SKL-01`, `SKL-02`, `CUT-01`, `CAP-01` |
| Dados e documentos | PASS | `CON-01`, `CTX-01`, `MRC-02` |
| WhatsApp | PASS | `WPP-01`, `PAR-01`, `OBS-01` |
| Rotinas e Auxiliares | PASS | `ROT-01`, `AUX-01` |
| Portais | PASS | `POR-01` |
| Admin | PASS | `SEC-05` |
| **Inteligência (novo)** | PASS | `INT-01`, `INT-02` |

### 5.4 Defeitos encontrados pelos próprios testes — e corrigidos no código

Sete defeitos reais. Nenhum teste foi afrouxado para acomodar código errado.

| # | Defeito | Onde | Consequência se tivesse passado |
|---|---|---|---|
| 1 | `int(tier or 5)` tratava **Tier 0 como Tier 5** | `evidence_service.py` (3 ocorrências) | A evidência **mais forte** (dado vivo) seria rebaixada a palpite. Findings apoiados em dado do banco simplesmente não nasceriam — e em silêncio. |
| 2 | Escalonamento por salto de prioridade furava "dispensado" | `dedupe_service.py` | Dispensar não funcionaria: o item voltaria assim que o score subisse. |
| 3 | Idem furava "resolvido" | idem | Cobrança sobre problema já resolvido. |
| 4 | Idem furava "ação em andamento" | idem | Cobrança sobre o que já está sendo feito. |
| 5 | Delta comparado contra zero quando não houve entrega anterior | idem | **Todo** item pareceria escalonamento na primeira vez. |
| 6 | Chat do corretor contado como atendimento parado | `detectors/qualidade.py` | 18 avisos falsos no primeiro briefing da Resulta. CA-012. |
| 7 | Canal aposentado tratado como quebrado; `close` fora da lista | `detectors/conexoes.py` | 2 alarmes falsos **e** o único canal realmente caído passando batido. CA-012. |

Os defeitos 1 a 5 foram encontrados na primeira execução do teste. Os 6 e 7 só
apareceram ao rodar as condições dos detectores contra o banco vivo.

---

## 6. Canário e rollout

| Ambiente | Estado | Evidência | Data |
|---|---|---|---|
| Amandus (técnico) | **N/A por desenho** | `is_technical=true`; `tick.py:_empresas()` exclui empresa técnica de propósito — briefing para sandbox gasta modelo e polui a métrica de qualidade | 26/07 |
| Resulta Seguros | **CONCLUÍDO — 2 defeitos achados** | ver abaixo | 26/07 |
| AutoFleet | **CONCLUÍDO** | zero sinal em todas as 12 regras; comportamento honesto de ausência | 26/07 |

**Resulta — o que os detectores encontram no dado real (FATO, medido em 26/07):**

| Detector | Antes da correção | Depois | Veredito |
|---|---:|---:|---|
| `qualidade.atendimento_parado` | 20 | **2** | 18 eram o chat do próprio corretor |
| `conexoes.conexao_degradada` | 2 (ambos falsos) | **1** | canal de atendimento ligado e caído — verdadeiro |
| `operacao.work_run_falhando` | 0 | 0 | 1 falha em 24h, abaixo do limiar de 3 — correto não alertar |
| `qualidade.regressao_atendimento` | 0 | 0 | 1 amostra em 24h, abaixo do mínimo de 5 — vira "não dá para afirmar" no briefing |
| `automacao.resultado_positivo` | 1 | 1 | 1 trabalho concluído |
| demais 7 detectores | 0 | 0 | sem material |

De 22 avisos (20 falsos) para **3 sinais verdadeiros**.

**AutoFleet:** zero em tudo. O briefing declara
*"Nenhum sinal operacional foi registrado no período — isso pode significar
tranquilidade ou fonte de dados parada"* em vez de inventar conteúdo. É
exatamente o comportamento que §24.2 exige.

**INFERÊNCIA, não fato:** os números acima vêm de executar as **condições** dos
detectores em SQL contra o banco vivo. A execução do pipeline completo
(sinal → finding → recomendação → briefing publicado) só ocorre depois do deploy.

**Flags criadas:**

| Flag | Default | O que faz | Como desligar |
|---|---|---|---|
| `INTELLIGENCE_CUTOVER` | `1` (ligado) | Desliga os 4 envios diretos legados e passa a autoridade ao pipeline | `=0` devolve o comportamento antigo **sem deploy** |
| `INTELLIGENCE_TICK` | `1` (ligado) | Enfileira briefings, detecção, garimpo, medição e clustering | `=0` para o agendamento; o resto continua respondendo sob demanda |
| `DEMAND_CLUSTER_SALT` | valor padrão | Sal do hash de tenant no agregado global | trocar invalida a contagem histórica de corretoras distintas |

**Auto-pause:** sim, por regra. Um detector barulhento é pausado pelo Admin em
`/admin/inteligencia` → Regras, sem deploy, e a taxa de rejeição observada de
cada regra fica visível ao lado do botão.

---

## 7. Gate da SPEC

| Critério (Definition of Done, §36) | Atendido | Evidência |
|---|---|---|
| 1. Envelope canônico de evento | SIM | teste `[16]` |
| 2. Signals com evidência, confiança e validade | SIM | teste `[1]`; CHECK no banco |
| 3. Findings separam fato e inferência | SIM | teste `[7]`; CHECK `..._fato_antes_da_inferencia_ck` |
| 4. Recommendations com ação real ou gap declarado | SIM | teste `[13]` |
| 5. Briefing Diário funciona | SIM em código | workflow + API + tela; produção depende do deploy |
| 6. Briefing Executivo funciona | SIM em código | idem |
| 7. Alertas críticos usam threshold e evidence | SIM | teste `[2]`; `policy.py` |
| 8. Quiet hours, dedupe e cooldown funcionam | SIM | testes `[4]`, `[5]`, `[6]` |
| 9. Feedback explícito funciona | SIM | `feedback_service.py` + tela |
| 10. Outcomes medidos ou inconclusivos | SIM | teste `[8]`; CHECK `..._sem_medicao_nao_afirma_ck` |
| 11. Garimpo v3 com privacidade | SIM | `garimpo_v3.py`; quote fica no tenant |
| 12. Clusters globais anonimizados | SIM | teste `[11]`; CHECK `..._global_e_anonimo_ck` |
| 13. Knowledge Candidates seguem SPEC-052 | SIM | teste `[10]`; nenhuma publicação direta |
| 14. Work Runs executam briefings e ações | SIM | 8 workflows no registro da SPEC-055 |
| 15. Skills/Tool Gateway governam chamadas | SIM | 3 Skills, 4 tools, 2 capabilities com scope |
| 16. Artifact Hub entrega web/PDF/resumos | **PARCIAL** | web e resumo sim; **PDF server-side bloqueado** (§2) |
| 17. Auxiliary Factory recebe propostas | SIM | `execution.py:_propor_rotina` |
| 18. Schedulers diretos migrados | SIM COM RESSALVA | deixaram de agir; registrações mantidas para rollback |
| 19. `broker_insights` não é autoridade nova | SIM | vira projeção; §10.15 |
| 20. Admin administra sinais, regras, demanda e resultados | SIM | `/admin/inteligencia` |
| 21. Dashboard mostra prioridades em linguagem humana | SIM | `/dashboard/briefing` |
| 22. Nenhum número inventado | SIM | teste `[12]`; a composição não calcula, só ordena |
| 23. Nenhum tenant vaza | SIM | teste `[5]`, `[11]`; RLS + filtro no repositório |
| 24. Custos atribuídos | SIM | Work Run por tenant; `usage_events` já da SPEC-055 |
| 25. Amandus, Resulta e AutoFleet passaram | SIM COM RESSALVA | Amandus é N/A por desenho; ver §6 |
| 26. APPLY/VERIFY/ROLLBACK existem | SIM | §4 |
| 27. Relatório final existe | SIM | este documento |
| 28. Funcionalidade ativa em produção | **PENDENTE** | depende do deploy (ação do Founder) |

**Veredito do gate: VERDE COM RESSALVA.**

Duas ressalvas, ambas com dono:

1. **PDF server-side** — fecha quando o preflight de infraestrutura liberar
   Chromium na imagem. Mesmo bloqueio já registrado para a SPEC-057.
2. **Ativação em produção** — depende de um deploy. Não é trabalho de código
   pendente; é a ação física do Founder descrita em §6 e no fim deste relatório.

---

## 8. Mudanças além do texto da SPEC

| ID | Classe | Estado | Resumo |
|---|---|---|---|
| CA-010 | ESSENCIAL | EXECUTADA | As 9 tools de §27.3 chegam ao chat agrupadas em 4 — conflito com o teto de 12 tools da SPEC-053 §13.1. Nenhuma operação removida. |
| CA-011 | BLOCKER | EXECUTADA | O gatilho da memória não pode viver dentro do turno. A correção da SPEC-054 estava inerte. |
| CA-012 | BLOCKER | EXECUTADA | Dois falsos positivos que só o dado real revelou. |

---

## 9. Decisões registradas

| ID | Assunto | Estado |
|---|---|---|
| D1 | Lote 4 da SPEC-052 executado na SPEC-059 Bloco A | **CUMPRIDA** |
| D5 | Escopo não reduzido | **CUMPRIDA** — ver CA-010 |
| D13 | Ambiente controlado permite migration e deploy com autonomia | aplicada |
| D18 | Corpus normativo parado por crédito | **não tocada** — sem interação com esta SPEC |
| D19 | Instalação guiada do Auxiliar | **não tocada** — fora do escopo, conforme instrução |

Nenhuma decisão nova foi necessária. Nenhuma condição de parada do CLAUDE.md §10
foi encontrada.

---

## 10. Riscos remanescentes e dívida assumida

| Risco | Severidade | Por que foi aceito | Onde será fechado |
|---|---|---|---|
| **Envio proativo externo desligado** | Média | A política está pronta e testada, mas ligar disparo de WhatsApp antes de observar o pipeline com dado real seria inverter a ordem: primeiro se confirma que o conteúdo está certo, depois se manda. O corretor vê tudo no dashboard e no chat desde já. | Ligar após 1 semana de briefings publicados sem correção |
| **Os 4 jobs legados continuam registrados** | Baixa | Removê-los eliminaria o rollback sem deploy. Eles retornam imediatamente sob cutover e não fazem trabalho. §29.6 pede que deixem de agir — e deixaram. | SPEC-061, junto da limpeza do scheduler |
| **MANIFEST de migrations não atualizado** | Média | Dívida **herdada**: as migrations das SPECs 055–058 também não estão espelhadas, e o Master Plan já registra isso. Criar um manifesto parcial agora daria falsa sensação de completude. | Dump de `supabase_migrations.schema_migrations`, conforme o Master Plan já prevê |
| **Sem ambiente efêmero para testar migration do zero** | Média | Não existe no projeto. Todas as migrations são `IF NOT EXISTS` e foram aplicadas incrementalmente com VERIFY. | SPEC-062 (readiness) |
| **Deteção de contradição é léxica, não semântica** | Baixa | Deliberado. Ela marca `conflicted` e chama humano; não decide. Uma versão semântica erraria com mais confiança. | SPEC-060, se a pesquisa trouxer base melhor |
| **`_contar_dependentes` é limite superior** | Baixa | Não existe grafo formal conexão→Rotina. O texto só diz "dependem" quando há algo ativo, e nunca cita um número específico de dependência. | SPEC-061 |
| **Qualidade por regra é taxa de rejeição, não precisão** | Baixa | É o que os dados sustentam hoje. Chamar de "precisão" seria o tipo de número que esta SPEC proíbe — e o campo se chama `taxa_rejeicao` por isso. | SPEC-062 (evals) |

---

## 11. Impacto para o corretor

**Hoje ele consegue, e antes não conseguia:**

- Abrir o **Briefing** e ver, em uma tela, o que precisa dele — com o **fato**
  que sustenta cada item separado da leitura que o sistema faz dele.
- Perguntar no chat *"o que precisa da minha atenção hoje?"* e receber o que
  está gravado, não um texto plausível.
- Perguntar *"por que você está me mostrando isso?"* e receber a evidência, a
  fonte, o período e a conta da prioridade.
- Dizer **"já resolvi"**, **"não é relevante"** ou **"o número está errado"** —
  e o assunto realmente cala, por prazos diferentes conforme a resposta.
- Aceitar uma recomendação e ver o trabalho abrir pelo caminho governado, com a
  medição do resultado já aberta com a linha de base de **antes**.
- Escolher horário, nível de detalhe e limite de avisos — e não ser interrompido
  fora do horário por nada que não seja crítico.

**O que ele deixa de receber:** a mensagem semanal de três blocos fixos que
chegava toda segunda houvesse ou não algo relevante, e o relatório de sábado com
fecho comercial. Os dois viraram briefing com evidência e link.

**O que ainda não muda para ele:** nada disso chega por WhatsApp ainda. Está
tudo no dashboard e no chat. E depende do deploy.

---

## 12. Estado do Master Plan

- [x] `EXECUTION-MASTER-PLAN.md` atualizado
- [x] `FOUNDER-DECISIONS.md` — nenhuma decisão nova necessária
- [x] `CHANGE-ADDENDA.md` atualizado (CA-010, CA-011, CA-012)
- [ ] `MIGRATIONS-AUTHORITY.md` / `MANIFEST.md` — **não atualizados**, dívida
      herdada declarada em §10

**Próxima etapa do plano:** Etapa 10 — **SPEC-060, Research Intelligence.**

**Pré-condições da próxima etapa:**

1. Deploy da API e do worker com o código desta SPEC.
2. Confirmar, após um ciclo, que `briefing_publications` e `session_summaries`
   deixaram de ser zero.
3. D18 (crédito do Firecrawl) volta a importar: a SPEC-060 é pesquisa externa e
   depende de crédito. Ela **recebe** sinais externos pelo pipeline desta SPEC —
   não cria outro.

---

## 13. ROLLBACK da SPEC inteira

```text
1. aplicação:
   git revert do merge desta branch e redeploy da API e do worker.

2. flags (rollback SEM deploy, e é o caminho recomendado primeiro):
   INTELLIGENCE_CUTOVER=0  → os 4 motores antigos voltam a enviar como antes
   INTELLIGENCE_TICK=0     → para o agendamento; nada novo é enfileirado

3. banco:
   ROLLBACK escrito no cabeçalho das 3 migrations.
   - 03: delete por chave (regras, tools, skills, capabilities). Não toca no
         que já existia.
   - 02 e 01: drop das 16 tabelas novas. Nenhuma tabela pré-existente é
         alterada por esta SPEC, então o drop devolve o estado anterior.

4. side effects já executados:
   Work Runs criados pelo tick já rodaram e ficam no histórico — isso é
   correto e não se desfaz. Nenhum efeito EXTERNO foi executado: o envio
   proativo nunca foi ligado (§10).

5. o que NÃO é reversível e por quê:
   - Os `session_summaries` e `user_memories` produzidos pelo varredor de
     memória. São dados legítimos que passaram a existir; apagá-los seria
     perder memória real do corretor, não desfazer um erro.
   - As linhas de `broker_insights` gravadas como projeção pelo Garimpo v3.
     Mesmo raciocínio.
   - Os `auxiliary_requests` criados quando o Garimpo encaminhou pedidos à
     Factory. São pedidos reais de corretoras.
```

---

## Declaração final

Nenhum motor paralelo foi criado. Execução, ferramenta, peça, automação,
conhecimento e memória continuam com os donos que já tinham. O que esta SPEC
acrescentou foi o que faltava entre eles: **perceber, comprovar, priorizar,
propor e medir**.
