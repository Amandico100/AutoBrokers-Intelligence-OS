---
> **Status:** relatório final — SPEC-056 Skill Registry & Tool Gateway
> **Branch:** `feat/spec056-skill-tool-gateway` · **main:** `dddc3ca`
> **Data:** 25/07/2026
---

# Relatório de execução — SPEC-056

## 0. Declaração de integridade

- [x] Nenhum Registry ou Tool Gateway **paralelo** criado.
- [x] `capabilities` e `capability_bindings` preservados como **autoridade de poder**.
- [x] Smith segue sendo o runtime único.
- [x] Nenhuma tool existente removida do runtime — a biblioteca **registra** o que já existe.
- [x] Nenhum segredo em manifesto, release ou invocação.

---

## 1. O problema que isto resolve

O Core recebia **~13 ferramentas fixas** em toda invocação, decoradas no grafo. Três consequências:

1. custo de token em toda conversa, mesmo nas que não usam ferramenta alguma;
2. queda na chance de escolher a ferramenta certa conforme o catálogo cresce;
3. deploy obrigatório para publicar qualquer capacidade nova.

E havia algo pior: **quatro autoridades paralelas** respondendo *"este agente pode usar isto?"* — `tools_config`, o cadastro de MCP do Agent, o HTTP router entrando por conta própria, e o Capability Registry, que só valia com `AUTHORITY_STRICT_MODE` ligado. E estava desligado.

A partir daqui existe **uma** resposta, e ela é composta:

```text
Skill escolhida
  → Capability Pack declarado
    → capability ATIVA no Registry, com scope
      → tool release publicada
        → limites da Skill
          → aprovação quando o efeito exigir
            → ferramenta liberada
```

Qualquer negativa em qualquer elo **nega**. Nunca o contrário.

---

## 2. O que ficou ativo

### 15 Tool Definitions · 15 releases publicadas

| Categoria | Tools | Efeito |
|---|---|---|
| Conhecimento | `knowledge.search`, `knowledge.global.search` | leitura |
| Pesquisa | `research.web_search` | leitura |
| Documentos | `documents.extract` | leitura |
| Analytics | `analytics.csv`, `operations.control_plane_read` | leitura |
| Seguros | `insurance.policy_lookup`, `insurance.policy_evidence` | leitura |
| Portais | `portal.billing_read`, `portal.policy_read` | leitura |
| Suporte | `support.human_handoff` | preparação |
| Delegação | `delegation.subagent` | preparação |
| **Comunicação** | `communication.whatsapp_send` | **comunicação — aprovação obrigatória** |
| **Compromisso** | `insurance.insurer_dispatch`, `portal.execute` | **compromisso externo — aprovação obrigatória** |

**Zero** tools de efeito grave sem `requires_approval` — garantido por `CHECK` no banco, não por convenção.

### 8 Skills · 8 releases publicadas

`core.answer_with_evidence` · `documents.analyze_insurance_document` · `research.web_brief` · `operations.csv_analysis` · `operations.control_plane_overview` · `insurance.policy_lookup` · `operations.human_handoff` · `portals.read_business_document`

### 7 Capability Packs · 14 membros

`pack.core.knowledge` · `pack.documents.analysis` · `pack.research.readonly` · `pack.operations.analytics` · `pack.insurance.policy_lookup` · `pack.portal.readonly` · `pack.communication.approved`

### 14 bindings por papel

| Papel | Skills |
|---|---:|
| `core` | 8 |
| `auxiliary` | 3 |
| **`attendance`** | **3** |

O Atendimento recebe apenas *responder com evidência*, *consultar apólice* e *transferir para humano* — menor privilégio da SPEC-053 §5.2, coerente com a correção que a SPEC-054 já havia feito ao remover HTTP genérico e execução livre de portal daquele papel.

---

## 3. Garantias provadas

### No banco — 5/5

| Tentativa | Resultado |
|---|---|
| Alterar manifesto de release **publicada** | **REJEITADO** — publicar é compromisso, não rascunho |
| Tool com efeito `financial` sem aprovação | **REJEITADO** pelo `CHECK` |
| Tool de `communication` externa sem aprovação | **REJEITADO** |
| Binding de `tenant` sem `company_id` | **REJEITADO** — vazaria a Skill para todas as corretoras |
| Tool apontando capability inexistente | **REJEITADO** pela FK |

### No código — 16/16

| Garantia |
|---|
| Tool sem capability ativa é **negada mesmo a Skill pedindo** |
| Negativa é registrada com motivo **e mensagem humana** |
| `needs_connection`, `disabled` e `scope_missing` negam com explicação diferente |
| `scope` da capability pode **exigir** aprovação numa tool que não exigia |
| Override da Skill pode **exigir** aprovação — nunca remover |
| Limite de chamadas é o **menor** entre Skill e escopo |
| `forbidden` não é sequer considerado |
| Com teto atingido, **leitura vence ação de efeito externo** |
| Gatilho correto vence na shortlist |
| Conversa sem intenção de procedimento **não força Skill** |
| Manifesto diferente gera hash diferente — obriga nova versão |

### Regression Pack

**19/19 · GATE VERDE**, com dois casos novos:
`SKL-01` — *"O agente só usa a ferramenta que o poder dele permite"*
`SKL-02` — *"Ação de efeito externo nunca roda sem aprovação"*

---

## 4. Decisões de engenharia

### 4.1 Shortlist determinística, não embedding

O ranqueamento por gatilho e nome é barato, explicável e auditável. Reduz o espaço **antes** de gastar token com seleção por LLM. Um ranqueamento que se pode ler e conferir vale mais, nesta fase, do que um que só se pode confiar.

### 4.2 Sem intenção clara, `None`

Nem toda pergunta é um procedimento. Forçar uma Skill onde não cabe piora a resposta — o resolver devolve `None` e o caminho conversacional normal segue.

### 4.3 Negativa é dado de produto

Registrar a negativa com motivo é o que permite o Admin descobrir que um corretor está esbarrando numa conexão faltando — em vez de só ver "o agente não conseguiu".

### 4.4 Teto prioriza menor risco

Quando o limite de ferramentas é atingido, leitura entra antes de ação com efeito externo. Um agente sem a ferramenta de leitura responde pior; um agente sem a ferramenta de escrita apenas não age — e não agir é o modo seguro de falhar.

---

## 5. Estado do Authority Strict

`AUTHORITY_STRICT_MODE` **continua OFF**, e isso é intencional.

O Tool Gateway já é a autoridade composta para o caminho novo (Skill → Pack → capability). Ligar o modo estrito global agora afetaria também o caminho legado do grafo, que ainda anexa tools por `tools_config`, **antes** de existir o diff em shadow mode que a SPEC-054 §9.4 exige.

A pré-condição está cumprida — os 46 `scope` foram preenchidos na SPEC-054. O que falta é o **cutover do grafo** para consumir o Gateway, com comparação antes/depois das ferramentas carregadas. Isso pertence ao Bloco de integração com o runtime, junto da SPEC-057.

---

## 6. O que ficou fora, conscientemente

| Item | Onde fecha |
|---|---|
| Cutover do `graph.py` para consumir o Gateway | integração com o runtime |
| Context Assembly 2.0 (Lote 3 da SPEC-052) | mesma etapa do cutover |
| UI de Admin para Skills e Tools | SPEC-061 |
| Evals por Skill | SPEC-062 |
| Homologação formal de MCPs | quando houver MCP cadastrado — hoje há zero |

O registro está completo e populado; o runtime ainda usa o caminho antigo. Essa é a ordem correta: **expand antes de contract**. Trocar o grafo no mesmo passo em que se cria o registro seria mudar duas variáveis ao mesmo tempo.

---

## 7. Impacto para o corretor

Ainda não visível — e é honesto dizer isso. O que mudou é que agora existe uma resposta única e auditável para *"o que este agente pode fazer, e por quê"*, com aprovação humana garantida pelo banco em toda ação que envia mensagem, aciona seguradora ou mexe em dinheiro.

É o que permite publicar uma capacidade nova sem deploy — e é a fundação direta do Relatório Executivo e do Briefing Diário.
