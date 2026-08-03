# Glossário — um termo, uma definição, um lugar

> **Documento canônico.** SPEC-064 Bloco J.
> **Um termo tem UMA definição.** Se dois documentos discordarem, **este vence**
> e o outro se corrige.
>
> Para a ontologia do trabalho em profundidade:
> [`ONTOLOGIA-DO-TRABALHO.md`](ONTOLOGIA-DO-TRABALHO.md).
> Para as camadas de conexão: [`CAMADAS-DE-CONEXAO.md`](CAMADAS-DE-CONEXAO.md).

---

## As quatro palavras do trabalho

| Termo | É | Não é | Onde mora |
|---|---|---|---|
| **Skill** | *como* se faz | não é RAG, não tem dono, não tem agenda | `skills` · `skill_releases` |
| **Rotina** | *quando* acontece | **não é Auxiliar** · nunca existe sozinha | `routines` (sempre com `tenant_auxiliary_id`) |
| **Auxiliar** | *quem* faz | **não é Rotina** · não é agente | `auxiliary_templates` (global) · `tenant_auxiliaries` (instalado) |
| **Artifact** | *o que* foi entregue | não é arquivo órfão | `artifacts` · `artifact_versions` |

> **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.**

---

## Quem conversa, quem executa

| Termo | É | Onde mora |
|---|---|---|
| **Agente** | quem conversa. Tem papel (`agent_role`) e público (`agent_audience`) | `agents` |
| **Agente CORE** | o copiloto **interno** do corretor. `broker_internal` | `agent_role='core'` |
| **Agente de atendimento** | quem fala com o **segurado**. `insured_external` | `agent_role='attendance'` |
| **Subagente** | especialista chamado por outro agente. **Somente leitura por construção** | `agents.is_subagent` |
| **Work Run** | toda execução durável, de qualquer origem | `work_runs` |
| **Approval** | decisão humana vinculada a um passo | `approval_requests` |

> **Nenhum subagente escreve estado durável de cliente.** É trava, não instrução
> de prompt.

---

## O que dá poder, e o que dá acesso

| Termo | É | Onde mora |
|---|---|---|
| **Capability** | o *poder* governável — pode ser negado, exige aprovação | `capabilities` · `capability_bindings` |
| **Tool** | a *implementação* técnica de um poder | `tool_definitions` · `backend/app/agents/tools/` |
| **Conector** | a *conexão* com um serviço de fora | `connector_templates` (catálogo) · `tenant_connections` (da corretora) |
| **Scope de conector** | **quem segura a credencial** | `platform` · `company` · `user` |

---

## Portais e corredores — a distinção que decide onde o trabalho acontece

| Termo | É | Fala com | Onde mora |
|---|---|---|---|
| **Portal** | o site da seguradora, com login da corretora | um **site** | tabela `portals` (17) · `portal_worker` |
| **Corredor** | o roteiro para acionar assistência | a **URA** da seguradora | `corridor_playbooks.py` |
| **Atlas** | os mapas de URA observados | — | `ura_maps` — **10 vivos** (`status='observed'`) |
| **RAG** | o conhecimento que o agente usa para falar | o **segurado** | `knowledge_cards` (8.916) |

```
RAG ......... conversa do agente com o SEGURADO
corredor .... conversa do motor com a URA DA SEGURADORA
portal ...... o motor entrando no SITE com login e senha
```

**Nenhum dos três substitui o outro.** Detalhe em
[`PORTAIS-E-CORREDORES.md`](PORTAIS-E-CORREDORES.md).

---

## Memória e conhecimento

| Termo | É | Escopo | Onde mora |
|---|---|---|---|
| **Conhecimento** | o que vale para qualquer corretora | global | `knowledge_cards` |
| **Memória da corretora** | o que só vale para aquela empresa | corretora | `company_memories` |
| **Memória do usuário** | o que só vale para aquela pessoa | usuário | `user_memories` |
| **Carta** | uma unidade de conhecimento destilada | global | `knowledge_cards` |

> **Conhecimento não é memória.** 📊 Em 02/08/2026: 8.916 cartas e **zero**
> memórias de corretora — nenhuma delas sabe que a Resulta trabalha condomínio.

---

## Inteligência

| Termo | É |
|---|---|
| **Sinal** | algo que o sistema percebeu, com evidência |
| **Finding** | um achado que separa **fato** de **inferência** |
| **Recomendação** | um achado com ação proposta |
| **Briefing** | a publicação periódica — hoje é o Auxiliar "Checklist das 6h" |
| **Detector** | a regra que produz sinal (`intelligence_rules`) |

---

## As camadas — vale para tudo

```
GLOBAL       o que a AutoBrokers oferece a TODAS as corretoras
CORRETORA    o que ESTA corretora tem, e só ela
USUÁRIO      o que ESTA pessoa tem, dentro daquela corretora
```

> **O de baixo sobrepõe o de cima. Mudar o de cima nunca apaga a sobreposição
> do de baixo. Mudar o de baixo nunca toca o de cima.**

---

## Termos que NÃO existem no produto

| Não usar | Usar |
|---|---|
| **Jarvys / Jarvis** | **AutoBrokers** — é o nome do agente central |
| **Smith** | é o runtime técnico invisível; não é marca, não vai para UI |
| **Even / SERGIO** | nomenclatura da SPEC-013, revogada (CLAUDE.md §4) |
| **Portal Browser** | removido na SPEC-064 — era simulação. Use **portal worker** |
| **Garimpo** *(como produto)* | é a voz do corretor. O achador chama-se **Descobridor** |
| **Auxiliares = Rotinas** | interpretação da SPEC-019, **revogada** pela SPEC-064 |
| **Venda casada** | prática proibida (CDC art. 39, I). O auxiliar chama-se **Proteção Completa** |

---

## Marcação obrigatória de números — CLAUDE.md §12.1

```
📊  medido        com data, fonte e a query que produziu
💭  ilustrativo   exemplo de copy — NUNCA citável como fato
```

> Um número de exemplo atravessou seis documentos como se fosse medição e virou
> "o achado que dá o tom do produto". A marcação existe por causa disso.

---

## Onde cada regra mora

| Pergunta | Documento |
|---|---|
| O que é cada peça e onde mora? | [`ONTOLOGIA-DO-TRABALHO.md`](ONTOLOGIA-DO-TRABALHO.md) |
| Quem paga, quem conecta, quem usa? | [`CAMADAS-DE-CONEXAO.md`](CAMADAS-DE-CONEXAO.md) |
| Quando o chat oferece automatizar? | [`QUANDO-OFERECER-AUTOMACAO.md`](QUANDO-OFERECER-AUTOMACAO.md) |
| Portal, corredor, Atlas — qual é qual? | [`PORTAIS-E-CORREDORES.md`](PORTAIS-E-CORREDORES.md) |
| O que ficou pendente? | [`PENDENCIAS.md`](PENDENCIAS.md) |
| Posso aplicar este SQL? | [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md) |
| O que já foi decidido? | [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md) |
