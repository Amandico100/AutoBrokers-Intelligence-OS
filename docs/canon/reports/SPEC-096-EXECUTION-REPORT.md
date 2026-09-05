# SPEC-096 · EXECUTION REPORT — O chat responde, mostra o trabalho e continua

> Branch `feat/spec096-chat` · base `origin/main` = `e1494ab` · protocolo v11.2 + opção B · marcha **CRÍTICO** ·
> 04/09/2026 (mesmo chat da 095, por escolha do Founder; duas interrupções por limite de tokens) · orquestrador Fable 5.1
> (📊 um trecho da conversão rodou como Opus 4.8 — ver §0.1) · SPEC `docs/canon/specs/SPEC-096-o-chat-responde-e-continua.md` v1.1.

## 0. EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  o browser deixa de escolher a corretora (P0 provado ao vivo); o chat fala tipado (protocolo v1: conteúdo ≠ estágio ≠
                        aviso ≠ erro); a pergunta é do servidor e é uma só (idempotência por client_request_id); a geração sobrevive ao
                        disconnect e o parcial ao Stop/falha; uma linha de atividade verdadeira (das tool_calls, nunca de relógio); card do
                        relatório na conversa; histórico por cursor (60 + "carregar anteriores")
RISCO ................  7  (alcance: a corretora 2 · reversibilidade: dado/estado 2 · frequência: TODO atendimento 2 · +1 pelo P0 vivo)
SUPERFÍCIE ...........  3  (Web + BFF + FastAPI + grafo + DB + UX principal)
PISO APLICADO ........  §3.2: autenticação/sessão/filtro company_id + migration com índice → CRÍTICO
NÍVEL ................  CRÍTICO
UNIDADES .............  0 (gate zero + medição viva) · S (segurança) · A (turno) · B (protocolo) · C (shell) · D (histórico) · E (canário) · G (guardas)
COESÃO ...............  S+A+B juntas no backend (mesmo endpoint); S.1/S.3/S.4+A.2+C+D juntas na tela/BFF; contrato = o protocolo v1
PARALELISMO REAL .....  2 escritores: builder backend (backend/**) ‖ builder tela+BFF (app/**, lib/**, components/**) — arquivos disjuntos
TIME .................  investigador+pesquisador (Opus, 126k) · aquecimento (Opus, 141k) · desenhista (Opus, morreu no 429 com os 2 guardas
                        escritos) · 2 builders (Opus, 229k + 261k) · 2 Sonnet (arnês dos guardas) · red team · lente DADO · lente verdade ·
                        juiz fresco
REFERÊNCIA ...........  interna: guardas [13]–[16] da 095 (executam page.tsx); `work/queue.py` (Redis transporte, Postgres verdade);
                        externa: SPEC §3 — Claude.ai (nº 1, régua do Founder), OpenAI Responses (tipo+id+seq), LangGraph event streaming,
                        LangGraph stream_mode, AI SDK parts/resume, MDN SSE, NN/g — reabertas em 04/09
GATES ................  gate zero (10 vermelhos em cópia limpa) · guardas G verdes · mutações · rotas montam · tsc · next build · suíte inteira ·
                        canário vivo E.1 · linha de controle E.2 · TTFT não piorou · nenhum nome técnico na UI · painel + juiz · push
O ELO ................  "o corretor não vê estágio PORQUE tudo é token" → medido A (tela muda entre 1º token e fim da tool), medido B
                        (`{"token"}` é o único tipo), medido que B chega em A (SPEC-081 P-227/P-228 escolheu o contorno por causa disso).
                        "o parcial some PORQUE a persistência é depois do laço" → provado com Starlette 1.3.1 (cancel no disconnect).
FAIXA DE RELÓGIO .....  6–8h   ORÇAMENTO ≤ 2,5 M tokens de subagentes
```

## 0.1 Telemetria (protocolo §11)
```
começou 04/09 ~18:10 (preflight) · primeira linha de código de produto: ~22:30 (builders) — 4h20 de conversão+aquecimento+guardas,
   com 2 interrupções por limite (19:20 desenhista morto no 429; ~22:10 janela)
rodadas de painel: {A PREENCHER} · achados por lente: {A PREENCHER}
defeitos que o painel NÃO pegou e quem pegou: {A PREENCHER}
rodadas da bateria: inteiras {N} · parciais {N} · minutos esperando {N}
nota 0–100 do orquestrador: {A PREENCHER}
```
📊 Um trecho da conversão (as decisões delegadas, a SPEC v1.0, a aplicação das emendas) rodou com o orquestrador como **Opus 4.8** (troca de
atribuição pelo harness na virada da janela; voltou a Fable 5.1 por `/model`). O que esse trecho produziu passou pelo aquecimento (Opus 5,
nota 82), que achou ~9 números de linha deslocados (E7) além das 2 falsas plantadas — corrigidos. Nada desse trecho ficou sem régua.

## 1. O que a conversão mediu (e o que mudou o desenho)
- 🔴 **P0 provado ao vivo, custo zero** (BLOCO 0.2, 22:35): `POST {smith-api}/chat/stream` sem sessão, `companyId` Resulta + `agentId` inexistente
  → **200** SSE "⚠️ Agente não encontrado" (TTFB 3,44 s: a Resulta foi carregada); controle com `companyId` inexistente → **404** "Company not found".
- 📊 `on_tool_start` **nunca é emitido** (nó `tools` chama `tool._arun` direto, `nodes.py:1089`; `astream_events(version="v1")` não passa `custom`)
  → o estágio sai das `tool_calls` (chunk ou AIMessage) e do `on_chain_end` do nó `tools`; o motor não muda (P-096-MOTOR-DE-EVENTOS).
- 📊 Starlette 1.3.1 cancela o gerador no disconnect (`StreamingResponse.__call__`, os dois ramos) → `asyncio.create_task` + fila é obrigatório.
- 📊 Baseline Q1 (BLOCO 0.3, backend implantado, legado): **TTFT 1,13 s · `[DONE]` 8,71 s** — 7,5 s de summarization de memória segurando o
  fechamento e o composer. Conserto: memória em task própria; `turn.completed` logo depois da persistência.
- 📊 `/api/chat/stream` tem **1 chamador** (o painel); o widget usa `/api/chat` → o BFF pode ignorar o corpo sem quebrar o widget.
- 📊 `resolveSessionCompany` (`lib/auxiliaries/server.ts:31`) é o único helper que valida a filiação — nenhuma rota de chat o usava.
- 📊 `artifacts` não tem coluna de conversa e nenhuma tool sabe a conversa → `artifact.ready` via ContextVar registrado em `ArtifactService.publicar`.
- Aquecimento: **nota 82**, 16 emendas (E1–E16) aplicadas; as 2 falsas assinadas (p50 = 23 → 11; `version="v2"` → `"v1"`) refutadas por comando.

## 2. Decisões delegadas pelo Founder — executadas (F-096-00 em FOUNDER-DECISIONS.md)
F-094-07 → conexão InfoCap da Amandus arquivada (VERIFY) · F-094.1-02/08 → proposta de teste recusada (VERIFY) · F-094.1-01 → Gateway fica
desligado · F-094.1-03 → 094.2 depois da 098 · F-095-01 → P-095-LEITURA-DO-MODELO · F-095-02 → P-095-BRIEFING-POR-CANAL.

## 3. Commits
```
5a883c2 decisões delegadas · 9ed8cc8 SPEC v1.0 · 07a7ba7 aquecimento/emendas · 7b47531 guardas (gate zero) · 7c9e21f P0 fato + dossiê ·
f31643a baseline 0.3 · befd44a backend · 14c8434 tela+BFF · {N} arnês do guarda py · {A PREENCHER: consertos do painel, migration, relatório}
```

## 4. Gate zero (📊 cópia limpa `../AutoBrokers-FIX-gate0` em e1494ab)
```
node scripts/o-chat-responde-e-continua.test.mjs → 0 falha(s) de verdade · 21 VERMELHO ESPERADO · 0 já podem virar
python tests/test_o_chat_fala_tipado.py          → 14 ok · 18 falhas (13 VERMELHO ESPERADO + 5 do BLOCO 0.1: iii, iv, v, ix, x)
```

## 5. Migrations
`backend/supabase/migrations/20260904_01_spec096_turno_idempotente.sql` — índice único parcial `(conversation_id, role, payload->>'client_request_id')
WHERE … IS NOT NULL` (o `role` entrou porque a PERGUNTA do BFF também carrega `client_request_id`). APPLY/VERIFY/ROLLBACK no cabeçalho.
📊 **APLICADA em 05/09/2026 00:24 UTC** pelo orquestrador (MCP `apply_migration`, versão `20260905032441 spec096_turno_idempotente`), depois
de a lente do DADO conferir o formato e a ausência de colisão. Sequência da §9 de MIGRATIONS-AUTHORITY: commit inicial registrado (`5a883c2`);
advisors de performance ANTES = 267 INFO · 49 WARN (`unused_index` 182, `unindexed_foreign_keys` 81, `auth_rls_initplan` 47); DEPOIS = **267 · 49,
idênticos** — o índice novo não aparece em advisor nenhum. VERIFY: `select indexdef from pg_indexes where indexname='messages_turno_sem_duplicata_uidx'`
→ `CREATE UNIQUE INDEX messages_turno_sem_duplicata_uidx ON public.messages USING btree (conversation_id, role, ((payload ->> 'client_request_id'::text)))
WHERE ((payload ->> 'client_request_id'::text) IS NOT NULL)`; 📊 0 linhas com `client_request_id` no momento da aplicação (nenhum escritor gravava o campo).
ROLLBACK escrito: `drop index if exists public.messages_turno_sem_duplicata_uidx`. Canário Amandus → Resulta: o canário E.1 roda na Resulta (a
Amandus não tem agente de chat; a AutoFleet entra como controle de isolamento no E.2).

## 6. Guardas e mutações (📊 05/09/2026, árvore em `c39d780`+)
```
npm run test:chat-shell        [1]–[24] · 0 falha(s) de verdade · 0 VERMELHO ESPERADO · 0 ja podem virar · 24+ linhas de CONTROLE OK
                               (INTEGRADO=true: o que era "devendo" passou a ser exigido — commit 2002d31)
  mutações mjs (por cópia)     15 do cabeçalho original: 13 vermelhas + 2 buracos do arnês ([12] não executava o reducer; [16] não media o limiar)
                               → arnês consertado (b4a2459): E14 (120→∞) VERMELHA; [3] executa o 23505; [12] executa o reducer
                               + 8 novas ([17]–[24], c39d780): todas vermelhas, restauração byte-idêntica conferida por diff
python tests/test_o_chat_fala_tipado.py     40 ok · 0 falhas (com o grafo REAL importado: langgraph, fastembed, cohere, tavily instalados
                               nesta máquina; import do grafo 📊 231 s) — antes disso os blocos B3–B13 diziam "ainda não existe" por
                               causa de uma casca em `app.core` (o guarda escondia o erro de import: consertado, sempre mostra a causa)
  --mutar                      7/7 acusaram, por NOME novo de asserção (o arnês original contava vermelhos esperados e "acusava" sempre;
                               3 literais eram substring — X-Internal-Key, WHERE, interrupted — consertados com regex e âncora no código)
npm run test:rotas-montam      A TABELA DE ROTAS MONTA (295 rotas)
npx tsc --noEmit               EXIT=0 (builder da tela, depois da 2ª leva)
next build                     ✓ Compiled successfully in 17.6 min (sob contenção) · 134 páginas · /dashboard/chat, /api/chat/stream, /api/chat/stop presentes
guardas antigos                npm run test:relatorios VERDE ([13]–[16] executam page.tsx: ?pergunta= intacto) · entregas-tudo-abre · entregas-mostra-o-historico VERDES
```

## 7. O painel (red team · lente DADO · lente verdade/regressão) e o juiz fresco
**Rodada 1 (em paralelo, sobre `befd44a`+`14c8434`):**
- **Red team** (Opus, 198k): **16 quebras** — 1 P0 (sem chave, o modo widget usava o `companyId` do CORPO; 📊 0 de 3 agentes ativos com
  `allowedDomains`), 2 P1 (migration não aplicada → o 23505 do BFF era código morto; **Enter duplo = 2 turnos**, o `client_request_id` nascia
  dentro do handler e `!disabled` é estado assíncrono), 9 P2 (`notice` mudo na tela; `?session=` alheia → 500 para sempre; `completed{content}`
  × tela lendo `text`; `_gerar` sem `finally`; `correlation_id` fora do log; cursor empata; `users_v2` cru em vez de `resolveSessionCompany`;
  SELECT de retentativa sem `role`), 4 P3. Resistiu: o BFF do stream, `_chaves_internas`, `/api/messages`, o catálogo 38/38, a limpeza do canário.
- **Lente do DADO** (Opus, 157k): 5/5 números da §1 reproduzidos; **3 P1** — o canário usava `db.table("users")` (é `users_v2`); a retentativa
  reusava id+chave e a persistência fazia INSERT (a resposta boa nunca substituía o parcial); o P0 do modo widget (o mesmo do red team) e a
  linha de controle do canário que media algo sempre verdadeiro; 6 P2 (os mesmos seams do red team + `status 'active'×'open'`, UNIQUE de
  `session_id` como oráculo). Limpo: migration, `payload.turn`, ContextVar, redação, `_modo_de_confianca`.
- **Consertos** (mesmos builders, uma rodada cada, arquivos disjuntos): tela/BFF `c97b93d` (13 itens) · backend `fbb2a60` (10 itens) — o
  modo widget passou a derivar a corretora do AGENTE (o corpo não escolhe em porta nenhuma), `conv_check` confere o dono, UPSERT por id na
  retentativa (`attempt`++), `notice`/`failed`, `try/finally` + tetos (fila 5.000, 200 turnos → 429), `correlation_id` no log; trava síncrona
  por ref no envio, `resolveSessionCompany` nas duas rotas, `role` no reaproveitamento, 404 em sessão alheia + conversa nova, `content`
  substitui, cursor `(created_at,id)`, `before` validado, Stop confere o dono, `seq` repetido descartado.
- **Guardas para o que nasceu** (Sonnet, 227k): [17]–[24] executando o produto (Enter duplo, notice sem retry, agente nulo resolvido, sessão
  alheia → 404 + conversa nova, `content` substitui, `before` → 400, Stop de outro dono → 404, desempate do cursor) + 8 mutações vermelhas.
- **Defeitos que o painel NÃO pegou e quem pegou:** os 3 buracos do arnês dos guardas (mutação que "acusava" sempre; [12]/[16] de forma; [3]
  literal) — os próprios BUILDERS, ao medir as mutações isoladas; a casca em `app.core` que fazia B3–B13 mentirem "ainda não existe" — o
  builder do backend; a migration por aplicar — o red team (era do orquestrador).
**Rodada 2:** lente verdade/regressão (worktree próprio `../AutoBrokers-FIX-mut` em `c39d780`) e juiz fresco — abaixo.
- **Lente verdade/regressão** (Opus, 210k, worktree próprio `../AutoBrokers-FIX-mut` em `c39d780`, 29 ciclos mutar/restaurar, árvore devolvida
  limpa): produto VERDE em tudo (chat-shell 24 blocos + 37 controles; py 40 ok; tsc 0; build 134 páginas; rotas montam; guardas antigos verdes
  exceto UM vermelho PRÉ-EXISTENTE em arquivo intocado — P-096-GUARDA-MEMORIAS-VERMELHO). Os achados são do ARNÊS: 🔴 P0 — no ramo em que o
  grafo real importa, o guarda python deixava de emitir [B4][B5][B10][B13] (a lista de "vermelho esperado" esvaziou por DESAPARECIMENTO) e
  [B12] não existia; P1 — o BLOCO [A] (inclusive o cross-tenant) era FORMA (nomes na fonte), o wrapper `stream_agent` só tinha guarda de
  forma, e o [12] do mjs era vácuo (M12 não reprovava); 9 P2. 📊 Das 7 mutações próprias da lente, 6 ficaram VERDES — o número que mede o
  buraco. **Conserto:** Sonnet reescreveu essas asserções por EXECUÇÃO do `/chat/stream` dublado (molde do builder), com dois tenants e o
  wrapper executado; M12 e [25] (`seq` repetido) acrescentados — ver §6.
{A PREENCHER: juiz}

## 8. Canário vivo (E.1/E.2) — `backend/scripts/canario_096.py --vivo`, Resulta, `AUTOBROKERS_CANARIO=1`
**Rodada 1 (05/09 05:13, nesta máquina, app in-process com o lifespan de produção, chave interna do `.env.local` do Next só no processo):**
```
conversa canário criada · modo=painel company=04b5cdbc turno=4bb3385b
Q1 ORDEM: turn.accepted → heartbeat → heartbeat → assistant.content.delta → assistant.content.delta → assistant.content.completed → turn.completed → [DONE]
Q1 TTFSE=TTFT=T_COMPLETE=607 s   ← 📊 NÃO É PRODUTO: o log mostra o download dos modelos spacy (pt_core_news_md, en_core_web_lg) DENTRO
                                   do 1º turno e retentativas de Redis/Qdrant que não existem nesta máquina; a régua de tempo vale no ambiente
                                   implantado (BLOCO 0.3 mediu lá: 1,13 s / 8,71 s) e será refeita por curl depois do Implantar
Q2 (mesmo client_request_id): HTTP 200 — mas o backend logou `POST /rest/v1/messages?on_conflict=id → 409` e `falha ao gravar a resposta`
                                   ← 🔴 DEFEITO REAL que só o canário viu: o script mandava um `assistantMessageId` NOVO na retentativa; o índice
                                   (conversation_id, role, client_request_id) recusou e o UPSERT por id não resolve conflito no ÍNDICE. Conserto:
                                   `_persistir` cai para UPDATE da linha existente por (conversa, role, crid); e o canário reusa o id como a tela faz
Q3 (consumidor abandona no 5º evento): a task terminou e gravou `complete`
CONTROLE (a) companyId inexistente + agentId da Resulta, sem chave → 200, servido para a corretora DO AGENTE (`trust=widget_company_ignored`) ✔
CONTROLE (b) userId qualquer sem chave → modo widget, userId descartado, resposta legada `{token}` ✔  (e `widget_sem_dominio` logado: P-096-WIDGET-SEM-DOMINIO)
VERIFY/LIMPEZA: 0/0 — ⚠️ mas 4 respostas ficaram noutra conversa: o orquestrador apagou a conversa canário DURANTE a rodada (confundiu com a
                                   sobra da rodada anterior, que morrera sem lifespan), o `_persistir` recriou uma pelo session_id e gravou lá.
                                   Apagadas pelo orquestrador (📊 SQL: 0 mensagens com client_request_id, 0 órfãs). Lição para o script: VERIFY e
                                   LIMPEZA por client_request_id em qualquer conversa da company, não só na conversa que ele criou.
```
**Rodada 2 (05/09 ~06:20, depois dos consertos `4162155`) — 📊 saída colada de `canario-096-vivo-2.txt`:**
```
conversa canário criada: 2d80073f (sessao 8e6256ef…)
⚠️  AMBIENTE INCOMPLETO: Redis (localhost:6379) e Qdrant (localhost:6333) nao respondem nesta maquina.
Q1 status HTTP: 200
Q1 ORDEM: turn.accepted → heartbeat → assistant.content.delta → assistant.content.delta → assistant.content.completed → turn.completed → [DONE]
Q1 turn.completed.persisted = True
Q1 TTFSE=150.30s  TTFT=150.30s  T_COMPLETE=150.30s
Q1 régua: INFORMATIVA — este ambiente nao tem Redis nem Qdrant; o tempo medido aqui nao reprova nada.
Q2 status HTTP: 200 (mesmo client_request_id E mesmo assistantMessageId)
Q2 turn.completed.persisted = True
Q3 abandonado no 5º evento; esperando a task terminar…
CONTROLE (a): companyId inexistente + agentId da Resulta → status=200 · OK — o turno rodou na corretora DO AGENTE (o corpo foi ignorado)
CONTROLE (b): userId estranho sem chave → status=200 · OK — modo widget (nenhum envelope tipado; userId descartado)
VERIFY — respostas do canario (por client_request_id, em qualquer conversa): 4
VERIFY Q2 — respostas com o MESMO client_request_id: 1 (attempt=2) — UMA linha, com a resposta da 2a tentativa (A.1 + upsert)
VERIFY Q3 — o turno abandonado: gravado, status=complete (A.4: a task nao morreu com a conexao)
LIMPEZA — por client_request_id restantes=0 · mensagens da conversa=0 · conversas da sessao=0
log: [STREAM] resposta gravada em 2d80073f (complete, tentativa 1) · (complete, tentativa 2) · …
```
O que a rodada 2 PROVA: o protocolo tipado no ar (ordem certa, heartbeat antes do 1º delta); a idempotência (2 POSTs, 1 pergunta, 1 resposta
com `attempt=2`); a persistência que sobrevive ao disconnect (Q3); o corpo não escolhe a corretora em porta nenhuma (controles a/b); e o script
limpa o que criou (0/0/0). O que ela NÃO prova: o tempo — 📊 150 s aqui são retentativas de Redis/Qdrant locais; a régua (TTFT ≤ 1,47 s,
`[DONE]` bem antes de 8,7 s) é medida depois do Implantar, por curl no smith-api, como o BLOCO 0.3 fez. **Isso vai para a caixa do Founder.**

## 9. O que ficou fora e por quê · pendências
{A PREENCHER — P-096-*}

## 10. Declarações
- Nenhum motor paralelo: o turno mora em `messages.payload`; sem tabela de turno, sem fila nova, sem publisher novo; Redis não entrou; o grafo
  continua em `astream_events(version="v1")`; `stream_agent` continua existindo como wrapper.
- Nenhuma mensagem saiu para segurado/seguradora; nenhum agente de atendimento foi ligado; InfoCap só leitura; nenhum segredo impresso.
- FATO/INFERÊNCIA/RECOMENDAÇÃO separados no texto; números 📊 com comando; 💭 marcados.

## 11. Entrega
{A PREENCHER: saída do `git push origin HEAD:main`}
