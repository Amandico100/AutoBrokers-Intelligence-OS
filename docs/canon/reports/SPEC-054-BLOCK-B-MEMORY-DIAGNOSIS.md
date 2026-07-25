---
> **Status:** diagnóstico canônico — SPEC-054 Bloco B
> **Origem:** decisão **D1** — Lote 4 da SPEC-052, diagnóstico e correção inicial
> **Data:** 25/07/2026 · **Commit base:** `fa7e080`
---

# Diagnóstico — memória zerada (`user_memories = 0`, `session_summaries = 0`)

## 1. O sintoma

| Tabela | Linhas |
|---|---:|
| `conversation_logs` | 523 |
| `conversations` | 143 |
| `messages` | 1.425 |
| **`user_memories`** | **0** |
| **`session_summaries`** | **0** |

`MemoryService` tem 1.855 linhas, com `process_summarization`, `extract_user_facts`, `generate_session_summary`, `save_user_memory`, `save_session_summary`, locks distribuídos e versões sync e async completas. O código **é chamado**. E não produz nada.

> Não é funcionalidade ausente. É **defeito silencioso**.

---

## 2. Causa raiz — canal WEB · **condição logicamente inalcançável**

**FATO 1** — todas as 6 linhas de `memory_settings` têm:

```text
web_summarization_mode = 'session_end'
```

**FATO 2** — [`memory_service.py:423-424`](../../../backend/app/services/memory_service.py#L423-L424):

```python
if mode == "session_end" and session_ended:
    return True
```

**FATO 3** — [`graph.py:971-977`](../../../backend/app/agents/graph.py#L971-L977) chama sempre com:

```python
session_ended=False,
```

O mesmo acontece no segundo ponto de chamada, [`graph.py:1186`](../../../backend/app/agents/graph.py#L1186).

### Conclusão

```text
modo configurado = session_end
+ session_ended sempre False no único caminho que dispara
= should_summarize() NUNCA retorna True para web
```

**Nenhum outro ramo é avaliado**, porque `mode` é `session_end` e os ramos `message_count` e `inactivity` estão dentro do mesmo `if channel == "web"`, testados por igualdade de modo.

Não existe, em nenhum lugar do backend, um emissor de fim de sessão web que chame o trigger com `session_ended=True`.

---

## 3. Causa raiz — canal WHATSAPP · **limiar praticamente inatingível**

**FATO 4** — `whatsapp_summarization_mode = 'sliding_window'` em todas as linhas, com `whatsapp_message_threshold = 30`.

**FATO 5** — [`memory_service.py:455-465`](../../../backend/app/services/memory_service.py#L455-L465): o modo `sliding_window` só dispara com `messages_count >= threshold`.

**FATO 6** — distribuição real das conversas:

| Métrica | Valor |
|---|---:|
| Máximo de mensagens de usuário numa conversa | 190 |
| **Média** | **5,0** |
| Conversas com 50+ mensagens de usuário | 1 |

**FATO 7** — o `messages_count` passado por `graph.py:961-963` conta apenas `HumanMessage` **do estado atual do grafo**, não o histórico completo da conversa. O `CHAT_HISTORY_WINDOW` limita a janela carregada.

### Conclusão

Para WhatsApp a condição é *alcançável em teoria* mas *praticamente nunca satisfeita*: com média de 5 mensagens por conversa e janela truncada, o limiar de 30 quase nunca é atingido dentro de um único estado de grafo.

---

## 4. Por que isso não apareceu antes

O código faz `logger.info` de cada avaliação e **não** registra erro quando não dispara. Um `should_trigger = False` é indistinguível, no log, de um sistema saudável que ainda não atingiu o gatilho. Nunca houve um alerta.

Nenhum teste cobre o caminho ponta a ponta: os testes existentes exercitam `MemoryService` isoladamente, com `session_ended=True` passado explicitamente — condição que a produção nunca produz.

---

## 5. Correção inicial aplicada nesta SPEC (escopo do Bloco B/C)

Conforme **D1**, aqui entra apenas o diagnóstico e a **correção inicial**. A Memory/Learning Fabric completa é da **SPEC-059 Bloco A**.

A correção inicial deve:

1. **Tornar a condição alcançável sem inventar comportamento de produto.**
   O modo `session_end` passa a ter um fallback de inatividade: se a sessão não emite fim explícito, a inatividade configurada (`web_inactivity_timeout_min`) encerra logicamente a sessão. Isso preserva a semântica declarada — "resumir quando a sessão termina" — em vez de trocar o modo por baixo do Founder.

2. **Alinhar o limiar de WhatsApp à realidade observada**, sem alterar a semântica do modo.

3. **Registrar métrica de não disparo**, para que "memória não produzida" volte a ser visível.

> **Não** faz parte desta SPEC: pipeline de dedupe, checagem de contradição, Knowledge Candidate, Destilador, Tecelão, Sentinela, Curador e Conselho. Tudo isso é **SPEC-059 Bloco A**.

---

## 6. Riscos da correção

| Risco | Mitigação |
|---|---|
| Passar a gerar memória em volume inesperado | ambiente controlado (D13); volume atual é baixo (143 conversas) |
| Memória de baixa qualidade poluindo o contexto | a curadoria e os gates são da SPEC-059; aqui o objetivo é **provar que o caminho funciona** |
| Custo de LLM por sumarização | `memory_llm_model` já é configurável por agente; `debounce_seconds` já existe |

---

## 7. Critério de conclusão

- [ ] `session_summaries` e `user_memories` deixam de ser zero em ambiente canário;
- [ ] existe métrica/log explícito quando o gatilho **não** dispara;
- [ ] teste ponta a ponta que reproduz o caminho real da produção — não com `session_ended=True` forçado;
- [ ] nenhuma memória contém segredo, senha ou credencial;
- [ ] escopo `company_id + user_id` respeitado.

---

## 8. Referências

- [`SPEC-052`](../specs/SPEC-052-cerebro-cognitivo-unificado-autobrokers.md) §9 (Memory Fabric) e §16 (Lote 4)
- [`ADDENDUM-SPEC-052-EXECUTION-MAP.md`](../specs/ADDENDUM-SPEC-052-EXECUTION-MAP.md) §7
- [`FOUNDER-DECISIONS.md`](../FOUNDER-DECISIONS.md) — **D1**
