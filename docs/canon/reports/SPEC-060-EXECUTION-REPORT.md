---
> **Status:** relatório final de execução
> **SPEC:** SPEC-060 — Research Intelligence
> **Branch:** `feat/spec060-research-intelligence`
> **Commit inicial:** `92e5cc0` · **Data:** 27/07/2026
---

# SPEC-060 — Relatório de execução

## 1. O que a SPEC-060 entrega, em uma frase

O AutoBrokers passou a **olhar para fora** — buscar, ler, verificar, acompanhar
e entregar informação do mundo real — sem nunca afirmar nada que não consiga
mostrar de onde veio.

```text
Antes:  o corretor pergunta sobre o mercado e recebe o que o modelo lembra.
Agora:  ele recebe o que foi lido, com a fonte, a data e o que NÃO foi possível
        verificar.
```

Pesquisa é a única parte do sistema que traz informação de **fora**, e ela erra
de dois jeitos que custam caro à corretora:

1. **afirmando sem procedência** — o corretor repete ao cliente e a corretora
   responde pelo que disse;
2. **obedecendo a uma página da internet** — conteúdo web tratado como
   instrução vira sequestro do agente.

Toda decisão de arquitetura deste relatório existe por causa de uma dessas duas.

---

## 2. Preflight

| Item | Valor |
|---|---|
| `git rev-parse --show-toplevel` | `AutoBrokers-Opus-Exec` ✔ |
| `git branch --show-current` | `feat/spec060-research-intelligence` |
| `git rev-parse HEAD` (inicial) | `92e5cc0` |
| `git status --short` (inicial) | limpo ✔ |

---

## 3. Resultado dos gates

| Gate | Resultado |
|---|---|
| `broker_outcome_regression_pack.py` | **29/29 · GATE VERDE** (era 26/26; +3 casos) |
| `npx tsc --noEmit -p tsconfig.json` | **exit 0, sem saída** |
| `test_spec060_research.py` | 18 grupos, **todas as garantias verificadas** |
| `test_navegacao_sem_pagina_orfa.py` | **NAVEGAÇÃO ÍNTEGRA** |
| VERIFY da migration de fundação | 7/7 garantias provadas, bloco revertido |
| Canário com dado real (banco de produção) | 4 CHECKs recusaram + 2 triggers corretos, **nada persistido** |

### Casos novos no gate

| ID | O que protege |
|---|---|
| `RES-01` | Nada é afirmado sem fonte que sustente, e página não dá ordem |
| `RES-02` | Procedência, quarentena e degradação declarada continuam no código |
| `NAV-01` | Toda tela tem link no menu e nenhum rótulo é ambíguo |

---

## 4. Blocos executados

### Bloco A — Fundação

**Migration `20260727_01_spec060_research_foundation.sql`** — 13 tabelas,
todas com RLS ligada e **zero policy** (deny-all para `anon`/`authenticated`;
o backend usa service role e filtra por `company_id` na camada de repositório).

As garantias não são convenção de código — são **CHECK constraints**, porque
convenção se esquece e constraint não:

| Constraint | O que impede |
|---|---|
| `research_claims_alto_risco_exige_fonte_oficial_ck` | afirmação sobre cobertura ou norma sustentada só por imprensa |
| `research_claims_suportado_exige_citacao_ck` | claim "sustentado" com zero citação |
| `research_citations_tier5_nao_sustenta_ck` | blog anônimo sustentando fato |
| `research_snapshots_publico_e_anonimo_ck` | snapshot público carregando `company_id` |
| `research_monitors_ativo_exige_rotina_ck` | monitor "ligado" que nenhum agendador dispara |
| `research_observations_signal_exige_relevancia_ck` | mudança de banner virando aviso |
| `research_cache_publico_sem_tenant_ck` | cache público carregando pergunta de corretora |
| `research_sources_oficial_e_tier_ck` | fonte marcada oficial fora do tier oficial |

**Dois triggers** fecham o que o CHECK sozinho não fecha:

- `research_claims_recontar_citacoes()` mantém `citation_count` e
  `official_citation_count`. Sem ele, bastaria gravar um contador mentiroso
  para o CHECK de fonte oficial passar — a constraint viraria decoração.
- `research_observations_append_only()` permite alterar **apenas** `status` e
  `signal_id`. Evidência que pode ser reescrita não é evidência.

**Serviços** (`backend/app/services/research/`, 6.306 linhas):

| Arquivo | Responsabilidade |
|---|---|
| `schemas.py` | modos, tiers, risco, status e confiança de claim |
| `urls.py` | normalização, fingerprint, dedupe, diversidade por publisher |
| `source_policy.py` | catálogo de fontes: 12 oficiais/setoriais + 14 seguradoras |
| `content_sanitizer.py` | 8 padrões de injeção, score, quarentena, envelope |
| `providers.py` | Tavily, Firecrawl, leitura direta, Places |
| `provider_router.py` | hierarquia de leitura e preservação do HTML bruto |
| `source_registry.py` | fontes globais, snapshots, cache público antes do do tenant |
| `claim_service.py` | as 8 checagens de §16.4, contradições, citações |

### Bloco B — Orquestração e superfície

| Arquivo | Responsabilidade |
|---|---|
| `planner.py` | resolve o modo, decompõe e **declara a regra de parada antes de começar** |
| `orchestrator.py` | registrar → planejar → descobrir → adquirir → snapshot → claims → contradições → gravar → sintetizar |
| `monitor_service.py` | limpeza de ruído, comparação, criação de monitor **preso a uma Rotina** |
| `site_audit.py` | achados ordenados por impacto × esforço |
| `discovery.py` | fit com critérios declarados; **recusa sem API licenciada** |
| `adapters.py` | pontes para Intelligence Fabric, Knowledge e Artifact Hub |
| `radar.py` | o Auxiliar Radar (§37) |
| `workflows.py` | 5 workflows no registro da SPEC-055 |
| `legacy_adapter.py` | cutover da busca antiga, com rollback sem deploy |

**APIs:** `backend/app/api/research.py` (router de tenant + router de admin).
**Tool do Core:** `research_tool.py` — `PesquisarTool`, `MonitorarTool`,
`AuditarSiteTool`.
**Telas:** `/dashboard/pesquisas` (corretora) e `/admin/pesquisa` (plataforma),
**ambas com link no menu** e rótulo que diz o que a página responde.

### Bloco C — Catálogo, testes e gate

- 6 templates de peça novos no catálogo da SPEC-057 (CA-018).
- Auxiliar global **Radar de Mercado e Regulação**, com instalação de efeito
  real (CA-019).
- `test_spec060_research.py` (18 grupos) e `test_navegacao_sem_pagina_orfa.py`.
- 3 casos novos no gate.

---

## 5. Migrations

| Arquivo | Estado | APPLY | VERIFY | ROLLBACK |
|---|---|---|---|---|
| `20260727_01_spec060_research_foundation.sql` | **aplicada** | 13 tabelas, 8 CHECKs, 2 triggers, RLS | 7/7 garantias provadas com `raise exception` (bloco revertido) | escrito, por nome de objeto |
| `20260727_02_spec060_auxiliar_radar.sql` | **aplicada** | 1 linha em `auxiliary_templates` | executado — ver abaixo | `delete ... where slug='radar-mercado-regulacao'` |

### VERIFY da migration 02, saída real

```text
slug                     | radar-mercado-regulacao
status                   | active
execution_mode           | scheduled
workflow                 | research.radar_weekly
skill                    | research.regulatory_watch
skill_ok                 | 1
caps_ok                  | 3
duplicadas               | 0
```

Ambas são **expand-first** e **não destrutivas**: só inserem.

---

## 6. Canário com dado real

Executado no banco de produção (`dcajcvlzcjbmyapmklil`), contra a corretora
**Resulta**, dentro de um bloco `DO` encerrado por `raise exception` — **nada
foi persistido**.

### As garantias recusaram o que deviam recusar

```text
CANARIO_SPEC060 || RECUSOU: G1 G2 G3 G4 || DEIXOU PASSAR: nada
```

| | Tentativa | Resultado |
|---|---|---|
| G1 | claim regulatório `supported` com 2 citações e **nenhuma oficial** | recusado |
| G2 | claim `supported` com **zero** citações | recusado |
| G3 | monitor `is_active=true` com `routine_id` nulo | recusado |
| G4 | observação `cosmetic` carregando `signal_id` | recusado |

### Os triggers funcionaram

```text
CANARIO_TRIGGERS || OK: T1(contadores) T1b(com fonte oficial passa)
                        T2(append-only) T2b(status muda) || FALHOU: nada
```

- **T1** — inserida 1 citação oficial, `citation_count` e
  `official_citation_count` foram para `1/1` sozinhos.
- **T1b** — com a citação oficial contada, o claim crítico **passou** a poder
  ser `supported`. A regra bloqueia o que não tem fonte, não o trabalho legítimo.
- **T2** — tentativa de reescrever `summary` de uma observação: bloqueada.
- **T2b** — atualizar `status` para `promoted`: permitida.

### RLS nas 13 tabelas

```text
13 tabelas research_* · rls_ligada = true · policies = 0
```

---

## 7. Defeitos encontrados no meu próprio código, e corrigidos

A instrução era clara: se um teste com dado real revelar defeito no meu código,
corrijo o **código**. Foram quatro.

| # | Defeito | Onde | O que teria custado |
|---|---|---|---|
| 1 | `http://` e `https://` da mesma página contavam como **duas fontes** | `urls.py` | "confirmado por duas fontes independentes" sendo a mesma página duas vezes — exatamente a ilusão que §24.5 existe para impedir |
| 2 | `_avisar` do Radar montava um dicionário que o adapter **rejeitaria em silêncio** | `radar.py` | a peça semanal sairia e **ninguém seria avisado** |
| 3 | `radar.py` lia colunas inexistentes: `monitor_id`, `change_score`, `url`, `diff_excerpt`, `last_checked_at` | `radar.py` | o fechamento semanal estouraria na primeira execução real |
| 4 | `research_sources` não tem coluna `url` — o nome real é `canonical_url` | `radar.py` | nenhuma fonte apareceria no radar |

O defeito 1 foi encontrado pelo **próprio teste que escrevi**; os 2 a 4, pelo
canário contra o banco real. Nenhum teste foi ajustado para acomodar defeito.

Há ainda um quinto ajuste, no caso `RES-02` do gate: ele cobrava o símbolo
`no_credit` em `providers.py` quando o dono da garantia é `schemas.py`. A
checagem foi apontada para o arquivo correto — a garantia continua cobrada.

---

## 8. Como o D18 (crédito do Firecrawl) foi tratado

**O bloqueio não parou nada, e não foi contornado com fingimento.**

| Provider | Precisa de crédito? | Comportamento |
|---|---|---|
| `direct_fetch` | **não** | sustenta o pipeline inteiro. Egress Guard, MIME allowlist, TLS |
| `tavily` | chave | sem chave: `SEM_CHAVE`, com motivo em português |
| `firecrawl` | crédito | HTTP 402 → `SEM_CREDITO` |
| `places` | chave licenciada | sem chave: **recusa e explica**; nunca raspa o Maps |

O tratamento de 402 **reusa** o `FirecrawlClient` existente, como instruído —
não foi escrito um segundo. Ele não consome tentativa, reagenda em 6h e para o
ciclo.

Os três motivos são **distintos** no banco e na tela:

```text
SEM_CHAVE      → falta configuração
SEM_CREDITO    → falta pagamento; a fila continua e anda sozinha quando voltar
INDISPONIVEL   → o serviço não respondeu agora
```

O consumo registra `status='no_credit'`, não `'error'`: o custo não foi gasto e
a fila não foi perdida. Misturar os dois apagaria a informação de que **basta
pagar** para tudo andar.

Nenhum caminho de falha culpa o documento nem falha em silêncio.

---

## 9. As duas melhorias da SPEC-059 pedidas pelo Founder

### 9.1 "Origem interna não vira sinal" (CA-015)

`intelligence/origem.py` — um conceito só, aplicado por padrão em todo
detector. Duas decisões:

- **tipo desconhecido devolve `False`** — na dúvida o item passa. Falso
  positivo incomoda; falso negativo custa dinheiro e não tem sintoma.
- **a exceção é explícita e local** (`manter=`) — é assim que o pedido de
  atendimento humano continua aparecendo mesmo vindo do canal `web`.

Aplicado em qualidade, operação e automação. Na SPEC-060, impede que pesquisa
disparada pela plataforma vire "sinal de mercado" da corretora.

### 9.2 Feedback ajusta o cooldown, mas ninguém via o detector (CA-017)

`rule_engine.qualidade_por_regra()` passou a contar, por regra, quantas
**corretoras distintas** disseram que o número está errado, e marca
`revisar_limiar` a partir de 3. `/admin/inteligencia` mostra o alerta no topo e
a coluna "Nº errado".

**Nenhum limiar é ajustado automaticamente.** O sistema mostra; um humano
decide. Contagem de corretoras distintas, não percentual: dez reclamações de
uma corretora são um caso, uma reclamação de dez corretoras é um defeito.

---

## 10. Regra nova do Founder sobre navegação — cumprida e protegida

> "Toda página nova precisa de link no menu do papel que a usa, e nenhum rótulo
> de menu pode repetir. Rótulo deve dizer o que a página RESPONDE."

| Tela | Menu | Rótulo |
|---|---|---|
| `/dashboard/pesquisas` | menu da corretora | **Pesquisas** |
| `/admin/pesquisa` | Admin › Inteligência | **O que buscamos na internet** |

E a regra virou **teste**: `test_navegacao_sem_pagina_orfa.py`, no gate como
`NAV-01`. Ele cobra rótulo único, link não-quebrado e ausência de página órfã.

As **9 páginas órfãs herdadas** do Admin ficam listadas nominalmente em
`ORFAS_ANTERIORES_A_SPEC059` — dívida visível, não silenciada. O teste impede
que a lista **cresça** e avisa quando um item ganha link e pode sair dela.

---

## 11. Achado material: o catálogo já existia (CA-016)

Ao preparar o seed de capacidades, tools e Skills, a consulta ao banco mostrou
que o catálogo da SPEC-060 **já estava semeado** desde 26/07: 8 capabilities
ligadas ao `core`, 6 tools publicadas apontando para `research_tool`, 6 Skills
1.0.0 publicadas.

A migration que eu havia escrito criava um **segundo** conjunto. Duas
consequências: duas ferramentas de busca com o mesmo efeito e manifestos
diferentes, e o teto de 12 tools por execução consumido por duplicatas.

Pior: o ROLLBACK que eu havia escrito era
`delete from tool_definitions where tool_key like 'research.%'` — aplicado,
apagaria o catálogo **em uso em produção**.

A migration foi reescrita para conter apenas o Auxiliar do Radar, e o ROLLBACK
passou a ser por chave exata. Nenhuma mudança de código foi necessária: a
SPEC-060 depende de **capabilities**, não de `tool_key`.

> **Regra que isso confirma:** CLAUDE.md §5 vale para dados de catálogo, não só
> para motores. Rollback de seed se escreve por chave, nunca por `LIKE`.

---

## 12. Declaração: nenhum motor paralelo foi criado

| Poderia ter virado motor novo | Quem faz de fato |
|---|---|
| agendamento dos monitores | `routine_engine` (SPEC-019) |
| execução durável da pesquisa | Work Runs + Smith Worker (SPEC-055) |
| escolha e teto de ferramentas | Tool Gateway (SPEC-056) |
| composição das peças | Artifact Hub (SPEC-057) |
| aviso ao corretor | Intelligence Fabric (SPEC-059) |
| candidato a conhecimento | Knowledge Candidates (SPEC-052) |
| catálogo de Skills e tools | o que já existia no banco (CA-016) |
| tratamento de HTTP 402 | `FirecrawlClient` existente |

O `research_monitors.routine_id` é **obrigatório por CHECK** justamente para
tornar impossível criar um agendador de monitores em paralelo.

---

## 13. O que ficou fora, e por quê

| Item | Estado | Motivo |
|---|---|---|
| Leitura paga em volume | pronta, inativa | D18 — crédito do Firecrawl. `direct_fetch` cobre enquanto isso |
| PDF das peças de pesquisa | pendente | exige Chromium na imagem; a versão web sai normalmente |
| Descoberta de empresas em produção | pronta, inativa | sem chave do Places ela **recusa e explica**; raspar o Maps violaria os termos |
| PDF como fonte lida | limitação declarada | `DirectFetchProvider` declara que não extrai PDF; não finge ter lido |
| Reorganização do Admin | fora de escopo | CA-014 — é assunto da SPEC-061 |

Nada foi reduzido de escopo. §19 (descoberta de empresas) e §21 (SEO/AEO) estão
**implementados** — o CA-003 que propunha adiá-los foi rejeitado pela decisão D5.

---

## 14. FATO, INFERÊNCIA e RECOMENDAÇÃO

### FATO — verificado com saída real

- Gate 29/29 verde; `tsc` exit 0.
- 13 tabelas criadas, RLS ligada, zero policy — consultado no banco.
- 4 CHECKs recusaram dado inválido e 2 triggers se comportaram corretamente,
  contra a corretora Resulta, sem persistir nada.
- O Auxiliar do Radar existe no catálogo, com Skill e 3 capabilities presentes.
- 19 templates no catálogo de peças, com roteamento por intenção conferido.
- 4 defeitos do meu próprio código encontrados e corrigidos no código.

### INFERÊNCIA — coerente, ainda não observado em produção

- O pipeline completo de pesquisa **profunda** com provider pago não foi
  observado ponta a ponta, porque não há crédito. O que foi provado: a
  estrutura, as recusas, a degradação declarada e os caminhos com leitura
  direta.
- O fechamento semanal do Radar não foi observado em um ciclo real de 7 dias.
  Os componentes foram exercitados isoladamente.
- A qualidade da síntese e da extração de claims depende do modelo em execução
  e só pode ser avaliada com uso real.

### RECOMENDAÇÃO

1. **Deploy da API e do worker.** Sem isso, SPECs 059 e 060 são código parado.
2. Instalar o Radar em **uma** corretora primeiro. Conferir em uma semana se a
   peça saiu e se os avisos fazem sentido.
3. Quando o crédito do Firecrawl voltar, acompanhar `research_provider_usage`:
   as linhas com `status='no_credit'` mostram exatamente o que ficou represado.
4. Não ligar o envio proativo externo antes de um ciclo de briefing observado.
   Aviso errado no WhatsApp do corretor custa mais que aviso errado na tela.

---

## 15. Checklist final

- [x] Preflight registrado
- [x] Migrations com APPLY / VERIFY / ROLLBACK escritos antes de rodar
- [x] VERIFY executado com saída real
- [x] Canário com dado real (Resulta), sem persistir nada
- [x] Gate 29/29 verde
- [x] `npx tsc --noEmit` limpo
- [x] Toda tela nova com link no menu e rótulo único — e teste que cobra isso
- [x] `CHANGE-ADDENDA.md` atualizado (CA-015 a CA-019) e IDs duplicados
      renumerados (CA-013, CA-014)
- [x] `EXECUTION-MASTER-PLAN.md` atualizado: SPEC-059 concluída, SPEC-060 concluída
- [x] Nenhum motor paralelo criado
- [x] Escopo não reduzido
