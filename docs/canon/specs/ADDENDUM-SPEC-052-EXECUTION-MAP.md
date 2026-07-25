---
> **Status:** CANÔNICO — adendo executivo
> **Versão:** 1.0 · **Criado em:** 25/07/2026
> **Autoridade superior:** [`SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`](SPEC-052-cerebro-cognitivo-unificado-autobrokers.md)
> **Decisão de origem:** [`../FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) — **D1**
> **Natureza:** este adendo **não altera** a arquitetura da SPEC-052. Ele atribui **dono executor** a cada lote.
---

# Addendum — Mapa de execução da SPEC-052

## 1. Problema que este adendo resolve

A auditoria global de 25/07/2026 confirmou um vazio de responsabilidade:

- a SPEC-052 §16 define **Lotes 0 a 6** de migração da arquitetura cognitiva;
- a SPEC-053 §24 define a sequência de SPECs subordinadas 054 a 062;
- **apenas o Lote 6** (harness e ferramentas avançadas) foi absorvido por essa sequência;
- os Lotes 1 a 5 permaneceram **sem SPEC executora**;
- o índice canônico, porém, declarava o programa "documentalmente completo".

Consequência prática se nada fosse feito: ao final da SPEC-062, o Work OS estaria pronto e o cérebro da SPEC-052 continuaria com dois caminhos globais de recuperação, memória produzindo zero registros e um corpus de 9 documentos.

**Decisão D1: não criar SPEC-063.** Os lotes são execução da SPEC soberana e recebem dono nominal aqui.

---

## 2. Estado auditado dos lotes em 25/07/2026

| Lote | Estado | Evidência factual |
|---|---|---|
| **0** — Censo read-only | **CONCLUÍDO** | SPEC-052 §3 + [auditoria SPEC-054](../audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) + auditoria global de 25/07 |
| **1** — Unificação global | **ABERTO** | dois caminhos ativos em [`search_service.py:290-323`](../../../backend/app/services/search_service.py#L290-L323) |
| **2** — Publisher único | **ABERTO** | nenhum serviço de publicação governada existe no backend |
| **3** — Context Assembly 2.0 | **ABERTO** | nenhum `intent_router`, `context_planner`, `evidence_builder` ou `model_router` no código |
| **4** — Memory & Learning Fabric | **ABERTO com defeito** | `user_memories = 0`, `session_summaries = 0`, `knowledge_cards = 0` com 523 `conversation_logs` |
| **5** — Primeiro corpus | **ABERTO** | 9 documentos no sistema inteiro |
| **6** — Harness e ferramentas | **atribuído** | SPECs 054–062 |

---

## 3. Mapa de execução

| Lote | Dono executor | Etapa no Master Plan |
|---|---|---|
| **Lote 1** — Unificação global | **SPEC-054 Bloco B** | 2 |
| **Lote 2** — Global Knowledge Publisher | **SPEC-052 Cognitive Foundation Closure** | 7 |
| **Lote 3** — Context Assembly 2.0 | **SPEC-056 Bloco B** | 5 |
| **Lote 4** — Memory & Learning Fabric | **SPEC-054 Bloco C** (diagnóstico) + **SPEC-059 Bloco A** (implementação) | 2 e 9 |
| **Lote 5** — Primeiro corpus | **SPEC-052 Cognitive Foundation Closure** | 7 |
| Ponte Atendimento → Work Runs | **SPEC-055 — integração operacional** | 3 |

O pacote **SPEC-052 Cognitive Foundation Closure** roda **depois da SPEC-057 e antes da SPEC-058**. Não é SPEC nova: é execução nominada da SPEC-052, com branch, relatório e gate próprios.

---

## 4. Lote 1 — Unificação global → SPEC-054 Bloco B

### Estado atual (FATO)

[`backend/app/services/search_service.py:290-323`](../../../backend/app/services/search_service.py#L290-L323) executa **duas** recuperações globais e mescla os resultados:

1. `build_global_search_kwargs()` → coleção `autobrokers_global` ([`knowledge_scope.py:37`](../../../backend/app/services/knowledge_scope.py#L37));
2. `GLOBAL_KNOWLEDGE_COMPANY_ID` → coleção `company_<GK_ID>`, com `include_tenant_wide=True` e **sem** os filtros de curadoria.

`GLOBAL_KNOWLEDGE_COMPANY_ID` também é referenciado em `attendance_distiller.py`, `agent_council.py` e `global_knowledge_seed.py`.

### Escopo do lote

- inventariar o conteúdo de ambas as coleções antes de qualquer mudança;
- migrar o que for legítimo para `autobrokers_global`;
- **remover o segundo caminho da recuperação de runtime**;
- manter a empresa técnica `AutoBrokers Global Knowledge` apenas como sala administrativa da biblioteca — nunca como segundo RAG;
- capability governa o acesso; variável de ambiente vira **kill switch**, não autoridade;
- aplicar filtros de `valid_until`, `namespace`, `audience` e `visibility` em toda recuperação;
- provenance completa chegando ao modelo;
- corrigir health e debug para refletirem o comportamento real.

### Critério de conclusão

- **uma única** coleção global recuperável pelo runtime, comprovada por teste;
- nenhum draft aparece no runtime;
- teste de vazamento do global entre tenants verde;
- diagnóstico de RAG coerente com o comportamento observado.

### Restrição

Não apagar a coleção `company_<GK_ID>` no mesmo bloco que remove o caminho. Inventário → migração → prova → remoção do caminho → só então decisão sobre a coleção.

---

## 5. Lote 2 — Global Knowledge Publisher → Cognitive Foundation Closure

### Estado atual (FATO)

Não existe serviço de publicação governada. `global_knowledge_seed.py` escreve diretamente na coleção — exatamente o que a SPEC-052 §7.2 proíbe.

### Escopo do lote

**Autoridade única de publicação.** Nenhum uploader, seed, Destilador ou agente publica fora dela.

Ciclo de vida obrigatório (SPEC-052 §7.3):

```text
discovered → downloaded/uploaded → quarantined → extracted
→ sanitized → classified → curated → reviewed → approved
→ published → superseded/deprecated/revoked
```

Somente `published` entra em `autobrokers_global`.

Componentes:

- endpoint administrativo global;
- upload sem `agent_id` obrigatório, owner `platform`;
- quarentena e sanitização antes de qualquer indexação;
- curadoria e approval por classe de risco;
- publicação, reindexação e revogação;
- todos os metadados obrigatórios da SPEC-052 §7.4;
- seeds existentes migrados para usar o mesmo publisher.

### Critério de conclusão

- `global_knowledge_seed.py` deixa de escrever direto;
- todo documento em `autobrokers_global` tem `curation_status = published`, provenance completa e aprovador registrado;
- revogação remove do índice e mantém o registro de auditoria;
- proteção de conteúdo proprietário validada — tenant não lista chunks, não baixa corpus, não enumera fontes privadas.

---

## 6. Lote 3 — Context Assembly 2.0 → SPEC-056 Bloco B

### Estado atual (FATO)

Nenhum módulo de `intent_router`, `context_planner`, `evidence_builder` ou `model_router` existe. `model_policy.py` tem 1,4 KB. O contexto é montado de forma majoritariamente fixa em `_build_initial_state` no grafo.

### Escopo do lote

Executado **junto** com o Skill Resolver da SPEC-056, por serem irmãos arquiteturais:

- **Outcome & Intent Router** — classifica intenção e risco;
- **Context Planner** — decide **quais camadas** buscar, sem carregar tudo por padrão;
- **Evidence Builder** — monta o Evidence Pack com fonte, autoridade, escopo, versão, validade e confiança;
- **recuperação capability-aware** — a capability decide o que pode ser lido;
- **precedência** — SPEC-052 §6.4 para fatos de seguro e §6.5 para estratégia;
- deduplicação e orçamento de contexto;
- **model routing** por complexidade, risco, latência e custo;
- tracing do plano de contexto.

### Critério de conclusão

- o plano de contexto é observável e registrado por execução;
- pergunta de cobertura de apólice **nunca** é respondida só com RAG global — exige Evidence Pack específico;
- provenance chega ao modelo e aparece na resposta;
- comparação `sem RAG` × `com RAG` executada: o RAG só é aprovado se melhorar a resposta **sem** limitar a inteligência geral (SPEC-052 §15).

---

## 7. Lote 4 — Memory & Learning Fabric → SPEC-054 Bloco C + SPEC-059 Bloco A

### Estado atual (FATO — o achado mais grave desta auditoria)

[`backend/app/services/memory_service.py`](../../../backend/app/services/memory_service.py) tem 1.855 linhas com `process_summarization`, `extract_user_facts`, `generate_session_summary`, `save_user_memory`, `save_session_summary`, locks distribuídos e versões sync e async completas.

E o banco vivo mostra:

```text
conversation_logs   523        user_memories        0
conversations       143        session_summaries    0
messages          1.425        knowledge_cards      0
                               broker_insights      0
                               conduct_playbooks    0
                               playbook_overlays    0
```

> Isto **não é** funcionalidade ausente. É **defeito silencioso**: o código existe, é chamado, e não produz saída.

### Fase 1 — SPEC-054 Bloco C · diagnóstico e correção inicial

Determinar a causa raiz antes de construir qualquer coisa em cima:

- o `should_summarize` está sendo satisfeito alguma vez?
- `memory_settings` está desligando a memória por agente?
- `_acquire_lock` / `memory_processing_locks` está bloqueando permanentemente?
- há exceção engolida em `_safe_execute`?
- a escrita falha por RLS, por `company_id` ausente ou por schema?
- o `schedule_summarization_async` chega a ser agendado no fluxo do chat?

**Saída obrigatória:** causa raiz documentada com evidência **e** correção aplicada, **ou** — se a correção exceder o escopo do Bloco C — causa raiz documentada com plano explícito na SPEC-059.

### Fase 2 — SPEC-059 Bloco A · implementação completa

- session summaries em produção;
- memória pessoal (`company_id + user_id`, escopo inviolável) e memória da corretora;
- pipeline de escrita controlada: extração → classificação → deduplicação → checagem de contradição → relevância futura → escopo → retenção → gravação;
- **Knowledge Candidate** como objeto comum de todas as fontes;
- Destilador, Tecelão, Sentinela, Curador e Conselho ligados ao pipeline;
- gates por risco (SPEC-052 §10.4) — alto risco exige fonte oficial e humano responsável;
- anonimização obrigatória de qualquer candidato derivado de corretora.

### Critério de conclusão

- memória produzindo registros reais, pequenos, úteis e revisáveis;
- nenhum segredo, senha ou credencial em memória;
- nenhuma conversa bruta publicada globalmente;
- página Memórias exibindo **métricas honestas** — conversa não é chamada de "memória consolidada";
- aprendizado gera **candidatos**, nunca publicação direta.

---

## 8. Lote 5 — Primeiro corpus global → Cognitive Foundation Closure

### Estado atual (FATO)

9 documentos no sistema inteiro. O corpus global é praticamente inexistente, o que torna o RAG global decorativo.

### Escopo do lote

50 a 100 documentos de **fontes oficiais**, publicados exclusivamente pelo Publisher do Lote 2:

- legislação e normas aplicáveis;
- condições gerais e especiais de produtos;
- seguradoras prioritárias, seus produtos e procedimentos;
- fundamentos de seguros por ramo;
- vendas, gestão, marketing e administração de corretora;
- Knowledge Cards derivados;
- goldens de avaliação por documento.

### Critério de conclusão

- todo documento com metadados completos, `valid_from`/`valid_until` e aprovador;
- goldens verdes;
- perguntas reais de corretor respondidas com citação verificável;
- teste de vazamento entre tenants verde.

### Restrições

1. **Corpus real e curado.** Não preencher quantidade artificial para bater a meta numérica. 60 documentos excelentes valem mais que 100 medíocres.
2. **O material de INTAKE não pode ser fonte deste corpus** — decisão **D7**. São dados operacionais brutos de corretoras, com PII, sem autorização de uso.
3. Conhecimento derivado de corretoras só entra anonimizado, agregado e após os gates da SPEC-052 §10.5.

---

## 9. Ponte Atendimento e corredores → SPEC-055

### Contexto

A SPEC-053 §5.2 define as fronteiras do Atendimento, e a SPEC-062 §11.10 prevê datasets de eval para Atendimento e WhatsApp — mas nenhuma SPEC de 054 a 062 fazia a ponte entre `attendance_sessions`/corredores e o Work Run universal.

### Escopo

Integrar Atendimento à execução durável na SPEC-055, **preservando integralmente** as restrições da SPEC-053 §5.2.

### Restrição inegociável

O agente externo de Atendimento **não** pode receber as capacidades do Core.

Permanecem obrigatórios: corredor definido, menor privilégio, Evidence Pack, regras de cobertura, handoff humano, controle de linguagem, e proibição de ferramentas genéricas de gestão, marketing, pesquisa ou administração. O Atendimento **não** cria Auxiliares nem acessa conhecimento global irrestrito.

---

## 10. Critério de conclusão da SPEC-052 como um todo

A SPEC-052 §17 só estará atendida quando **todos** estes forem verdadeiros:

- [ ] uma única coleção global recuperável — **Lote 1**
- [ ] um único publisher global — **Lote 2**
- [ ] nenhum draft no runtime — **Lotes 1 e 2**
- [ ] capability controla o acesso — **Lotes 1 e 3**
- [ ] validade e audience aplicadas — **Lotes 1 e 3**
- [ ] provenance chega ao modelo — **Lote 3**
- [ ] global, tenant e user isolados — **Lotes 1 e 4**
- [ ] página Memórias não expõe o corpus global — **Lotes 2 e 4**
- [ ] Core combina RAG, dados vivos e ferramentas — **Lote 3 + SPEC-056**
- [ ] perguntas de cobertura usam Evidence Pack — **Lote 3**
- [ ] aprendizado gera candidates, não publicação direta — **Lote 4**
- [ ] PII nunca entra no global — **Lotes 4 e 5**
- [ ] health e debug refletem o comportamento real — **Lote 1**
- [ ] goldens e testes de vazamento verdes — **Lote 5**
- [ ] rollback documentado — todos

**Nenhuma Launch Decision pode ser emitida com qualquer item acima em aberto.**

---

## 11. Referências

- [`SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`](SPEC-052-cerebro-cognitivo-unificado-autobrokers.md) — §7, §9, §10, §16, §17
- [`SPEC-053-autobrokers-work-os-core-harness.md`](SPEC-053-autobrokers-work-os-core-harness.md) — §5.2, §24
- [`../FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) — **D1**, **D7**
- [`../EXECUTION-MASTER-PLAN.md`](../EXECUTION-MASTER-PLAN.md) — Etapas 2, 3, 5, 7, 9
