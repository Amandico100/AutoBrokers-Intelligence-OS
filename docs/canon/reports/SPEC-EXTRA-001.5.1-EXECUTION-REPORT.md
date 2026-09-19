---
> **Status:** em execução · **Protocolo:** AAA v12.2 · AAA FAST · modo GERENTE (Fable 5.1 no chat da 001.5, por decisão do Founder de 19/09)
> **SPEC:** `specs-propostas/SPEC-EXTRA-001.5.1-a-base-de-planos-chega-ao-cliente.md` · **Branch:** `feat/extra-001-5-1-a-base-chega-ao-cliente` · **Base:** `6836258`
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `6836258`

```
OUTCOME ........... a base de planos CHEGA ao cliente: a Skill roda em produção (hoje está desligada em
                    silêncio), a fila de curadoria abre e publica, o corretor recebe a fonte e o segurado
                    recebe a mesma verdade sem citação, e o que o agente não sabe vira tarefa
RISCO ............. 8 = ALCANCE 3 (o segurado lê) + REVERSIBILIDADE 3 (sai pelo WhatsApp) + FREQUÊNCIA 2
SUPERFÍCIE ........ 2 — lugares listados na proposta §2 (2 arquivos de backend, 3 de front, 2 prompts, o pacote)
PISO APLICADO ..... §3.2: todo texto ao segurado; a migration do motivo do rascunho, se houver
NÍVEL ............. CRÍTICO pela soma · marcha PADRÃO com o elenco do crítico (como a 001.5, D-E0015-02) ·
                    builder Opus 5 xhigh por fatia · juiz Fable 5.1 fresco · confirmação por gatilho
UNIDADES .......... 5 · A cegueira · B fila e lote · C resposta por canal · D lacuna vira tarefa · E isolamento
                    FATIAS: 1 = A · 2 = B · 3 = C+D+E · + publicação das linhas conferidas (Founder autorizou 19/09)
COESÃO ............ A é pré-condição de tudo (sem o vocabulário nada roda); B toca a mesma fila que a
                    publicação usa; C+D+E tocam o mesmo turno de resposta
PARALELISMO REAL .. nenhum na escrita de código; um LEITOR read-only confere as 81 linhas em paralelo à fatia 1
TIME .............. gerente Fable · 3 builders Opus xhigh · leitor Opus (read-only) · juiz Fable fresco ·
                    lente do dado NÃO (o outcome não é dataset novo) · confirmação se blocker no texto ao segurado
REFERÊNCIA ........ interna `backend/tests/test_a_resposta_traz_documento_e_pagina.py` (o par corretor × segurado
                    nasce dele) · externa: as 3 da 001.5 §14 (PROV-O · Citations · ALCE)
GATES ............. GATE A..E da proposta §5 · 🔴 todo gate de produção roda na CÓPIA que reproduz o contêiner
O ELO ............. "responde 'não sei' a tudo PORQUE a Skill nem roda": medi A (a resposta em produção) ·
                    medi B (/fila 500; Dockerfile copia só backend/) · B chega em A: o except do composer engole
FAIXA DE RELÓGIO .. fatia ≤ 60 min ×3 · juiz+conserto+entrega ≤ 45 min · tetos 160 turnos · 250 k por fatia
```

📊 **Preflight 19/09:** `HEAD..origin/main` = 0 · HEAD `6836258` · as 5 medições do prompt reproduzidas (§1).
**D-E00151-01:** o Founder decidiu executar no MESMO chat da 001.5 (11 agentes já usados); o teto do hook sobe
para 24 pelo botão documentado (`AAA_FAST_TETO_DE_AGENTES`), registrado aqui — 90 × abrir chat novo 60.

## 1. BLOCO 0 — as premissas remedidas em 19/09
| # | afirmação | medido 📊 | comando |
|---|---|---|---|
| 1 | `/fila` 500 em produção | **500** em 1,4 s · `/cobertura` **200** em 1,8 s | `curl -H X-Internal-Key …/api/assistance-plans/fila?limite=3` |
| 2 | o vocabulário está fora da imagem | `Dockerfile`: `WORKDIR /app` + `COPY . .` (de `backend/`) | `grep -n COPY backend/Dockerfile` |
| 3 | o composer engole | `except Exception` + `logger.warning` (`policy_answer_composer.py:576`) | `sed -n 576,577p` |
| 4 | o front esconde o erro | `route.ts:42` sem `r.ok`; `KnowledgeClient.tsx:108` `fila.itens \|\| []` | `grep -n` |
| 5 | o dado | planos 33 proposto/5 rascunho · serviços 73/8 · 0 publicado · `TETO_DA_FILA = 60` · `capability_gaps` = 0 | SELECT |
