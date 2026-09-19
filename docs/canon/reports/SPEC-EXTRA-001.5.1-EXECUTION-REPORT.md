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

## 2. As unidades entregues, por fatia

| fatia | unidade | o que entrou | gate · saída real 📊 |
|---|---|---|---|
| **1** | **A** a cegueira (D1, D2, D3, D4, D9) | o vocabulário passa a viver em `backend/app/data/servicos-de-assistencia.json` (o de `docs/` vira PONTEIRO, e `vocabulario_de_servicos` recusa arquivo sem serviços — decisão ponteiro 88 × cópia com guarda 72) · o resolvedor procura primeiro dentro do pacote · `contar_fila()` conta a base · ordem estável em dois níveis · `/fila` devolve `{ok, itens, total, mostrando, limite}` e uma página que falha não derruba a resposta · `route.ts` testa `r.ok` · `KnowledgeClient` testa `ok` · a fila tem 3 estados (erro · vazio honesto · lista "mostrando N de M") e o botão morto explica · 11 commits `0e9a995`…`f1517dd` | 🔴 **guarda do contêiner** (`test_o_vocabulario_viaja_na_imagem.py`): cópia só de `backend/`, vermelho **3/5** antes → verde **14/0** depois · **O ELO**: na cópia sem `docs/`, antes `Skill de cobertura indisponível` e `COBERTURA: None`; depois `COBERTURA: {"servico":"carro_reserva",…}` · `test_a_fila_diz_a_verdade` 24/0 · `contar_fila` = 73 = SQL (controle: rascunho 8) · rotas-montam 303 · `tsc` 0 · `next build` 314 rotas · `next start` → `GET /api/dashboard/knowledge/planos` 401 `no_session` em 0,29 s · 3 mutações vermelhas em arquivo real (JSON apagado · `itens:[]` no catch · `.order()` removido) · 16 guardas vizinhos verdes · gerente rerodou 5 guardas: exit 0 |

**Fora do escopo, visto pelo builder (🔴 vira unidade A-bis):** `backend/app/providers/susep_ses_provider.py:100-109` lê
`docs/canon/providers/susep/{seguradora-coenti,ramo-cogrupo}.json` por `parents[4]` — fora da imagem, como o
vocabulário. 📊 Na cópia que reproduz o contêiner os três mapas vêm **vazios** (`[SES] mapa de seguradoras ausente`),
e `familia_de_acionamento(insurer_key)` devolve `UNKNOWN` em vez de `porto` — está no caminho vivo (`infocap_tool.py:856`).
Degrada em silêncio, sem 500. **Não consertado nesta fatia** (fora do card); entra na fatia 2 com o mesmo remédio.

## 12. Handoff — a sessão parou aqui, e por quê

🔴 **Parada legítima (CLAUDE.md §10 (8) · protocolo §10):** o hook `teto-de-agentes.py` bloqueou o 13º agente deste chat
(a 001.5 gastou 11; o builder da fatia 1 foi o 12º). A variável `AAA_FAST_TETO_DE_AGENTES=24` já está em
`.claude/settings.json`, mas só vale numa sessão nova. Não contornei o guarda. A fatia 1 está **verde e commitada** na
branch `feat/extra-001-5-1-a-base-chega-ao-cliente` (empurrada para `origin`, **não** para a `main`: sem juiz não há gate final).

**O que resta (fatias 2 e 3 + o juiz), nesta ordem, na sessão retomada:**
1. **Leitor das 81 linhas** (Opus, read-only) → `reports/SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.{md,json}` (o pacote está no transcrito deste chat; foi bloqueado pelo hook).
2. **Fatia 2 = B + A-bis**: página sob demanda (65 s → segundos) · `scripts/publicar_linhas_da_base.py` (`--dry-run`/`--aplicar`, consome o JSON do leitor, revisor = `4e6da87a-111d-4f31-b7cf-1b7d69598bc3`) · os 4 serviços presos · motivo do rascunho · **os 3 JSONs SUSEP para `backend/app/data/` + o guarda do contêiner estendido**.
3. **Fatia 3 = C + D + E**: texto por canal · gancho com atendente · lacuna em `capability_gaps` (`missing_data`) com aviso ao grupo **limitado a 1 por lacuna por corretora por dia e só no canal do segurado** (emenda E1) · tela de curadoria de administrador · guardas de isolamento e de "a resposta não faz I/O".
4. **Juiz Fable fresco** sobre `0dc113b..HEAD`, com a instrução *"prove na cópia sem `docs/`, não na árvore"* · conserto · publicação das linhas `PUBLICAR` pelo script (Founder autorizou 19/09) · suíte · relatório · push.

**Emendas do revisor à proposta (PASSO 1, 19/09):** E1 aviso ao grupo com teto e só no WhatsApp · E2 a publicação entra nesta execução, conferida linha a linha contra a página · E3 A-bis (catálogos SUSEP) · E4 `TOOL_GATEWAY_MODE` em produção é `shadow`, não `off` — nada muda · E5 o guarda do contêiner precisa de env mínimo dummy (pydantic) — feito. **Nota da proposta: 84** (sólida no diagnóstico; perdia por D sem teto de aviso e por não dizer quem publica).
