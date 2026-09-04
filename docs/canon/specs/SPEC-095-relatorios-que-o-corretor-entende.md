# SPEC-095 · RELATÓRIOS QUE O CORRETOR ENTENDE — a biblioteca abre pelo achado, não pelo lote

> **O que ela entrega:** (1) o menu **Entregas vira Relatórios**, e cada card diz **o que é, de quem é, de quando é e o
> que achou** — em vez de "Pulso 360 · 2026" e "4 item(ns) esperando você hoje" repetidos; (2) **nada aparece duas
> vezes**: o briefing é UM card (hoje são dois), o Pulso pedido cinco vezes é UMA peça com cinco versões (hoje são cinco
> peças), e **relatório de teste não entra na biblioteca da corretora** (hoje 📊 100% dos relatórios "do chat" da
> Resulta são canários de execução de SPEC); (3) um **placar discreto** do trabalho feito — que conta só o que a
> corretora pediu e recebeu, nunca o relógio da plataforma; (4) **o relatório abre pelo achado e diz o que fazer**:
> título = o achado principal, seção "O que importa agora" com o número, por que importa e a ação (📊 o porquê e o
> próximo passo já existem no banco e são descartados uma função antes da tela), e as seções vazias desaparecem;
> (5) o detalhe mostra as versões, de onde veio cada dado com a data honesta (📊 hoje `data_as_of` é `now()` em
> 136/136 versões e a tela afirma "Dados de…"), e o botão "Perguntar ao AutoBrokers" com a pergunta já escrita.
>
> **v1.2 · 04/09/2026 · protocolo v11.2 + opção B (três marchas) · marcha PADRÃO** · v1.1 + aquecimento (Opus, contexto
> limpo, 16 perguntas, 199 mil tokens: **nota 78 → 12 emendas E1–E12 aplicadas**; as duas afirmações falsas assinadas foram
> refutadas por leitura e por mutação; 6 blocos de números da §1 reproduzidos sem erro) · nasce da proposta
> `specs-propostas/9 - SPEC-095-artifact-delivery-hub-completion.md` (31/08; 📊 nota do investigador para ela, neste
> escopo: **41/100** — rigorosa onde há zero linhas de produção, silenciosa onde há 136 erradas) + o research pack + o
> pedido do Founder de 04/09 sobre a tela de Entregas + a medição de hoje (orquestrador + investigador/pesquisador,
> 224 mil tokens). **A proposta é ponto de partida; o que saiu dela está na §5, com o gatilho que a faz voltar.**
> Branch `feat/spec095-relatorios` · base `origin/main` = `5c22590`.

---

## 0. O TESTE DO PRODUTO

> **Segunda-feira, 08:05, o dono da Resulta abre "Relatórios" no menu. No topo, um placar discreto: hoje, 7 dias, 30
> dias, 1 ano, desde o início — quantos relatórios, conversas, execuções, pesquisas e trabalhos pedidos o AutoBrokers
> fez por ele (💭 os números são os do banco dele, e o relógio da plataforma não conta). A lista não tem dois cards
> iguais. O briefing de hoje é UM card: título "Fila acumulada", subtítulo "61 atendimentos parados há mais de 24h ·
> e mais 3 pontos" (📊 os "20 trabalhos prontos" que o briefing de 31/08 anunciava eram o relógio da plataforma — a
> frase só volta quando houver trabalho pedido), tipo "Briefing do dia · Checklist das 6h · 04/09", etiqueta "precisa de
> você". O Pulso 360 de 2026 é UM card: "Porto concentra 46,8% da comissão de 2026 · Pulso 360 · atualizado hoje
> 02:54 · 5 versões". Nenhum relatório de teste aparece. Ele abre o Pulso: a capa diz o achado; a seção "O que importa
> agora" tem um achado ou mais (💭 três no exemplo; 📊 hoje o Pulso da Resulta produz um), cada um com o número, por que importa e o que fazer; as seções sem dado não existem — o que
> não deu para medir é UMA linha; "De onde veio" lista as fontes com a hora em que a InfoCap foi lida. Ele clica
> "Perguntar ao AutoBrokers" e o chat abre com "Sobre o Pulso 360 · 2026: " já escrito. Nenhum número nasceu de um
> modelo: todos vieram do registry ou do banco.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ Nenhum LLM escreve número, título ou ação: a narrativa é **determinística por detector** (§BLOCO D).

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 04/09/2026 (SQL no projeto `dcajcvlzcjbmyapmklil`, `grep` na árvore em `5c22590`)

### 1.1 · 100% dos relatórios "do chat" da biblioteca da Resulta são execução de SPEC — e nada os distingue
📊 `select template_key, dia, count(*) … from artifacts where company_id=Resulta and origin='chat' group by 1,2` →
`commercial.pipeline` **14** e `renewals.radar` **14**, todos em **18/08 05:42–10:57** (o dia da execução da SPEC-081:
`git log` → `bb4d5ce 18/08 05:22`); `executive.pulse360` **6** em **03/09 20:03–20:37** e **04/09 02:09–02:54**. O
investigador cruzou os 7 Pulsos (6 Resulta + 1 AutoFleet) com o `git log` da 094/094.1 por menor distância: **7/7
coincidem em ±40 min com um commit** (0,4 a 34,6 min). 📊 Em TODO o banco: `requested_by` preenchido em **0/136**,
`tags` em **0/136**, `subject_ref.id` não vazio em **5/136**; `_publicar` grava `origin="chat"`, `work_run_id=None`
e `subject_ref={"kind":"chat","id":""}` como **constantes** (`relatorios_comerciais.py:326-331`). **Zero pergunta real
do dono. O Pulso sai por `origin="chat"` mesmo quando ninguém abriu o chat.**

### 1.2 · Cada briefing entra duas vezes — e as duas linhas ficam grudadas
📊 Na lista da Resulta: 46 publicações, 40 com `artifact_id`, **40 pares duplicados** (título idêntico, href idêntico,
`created_at` 3 s de diferença → ordenam juntas): **9,8% da lista inteira (40/410)** e **32,0% da lente "Documentos"
(40/125)**. 📊 33/33 publicações dos últimos 10 dias (3 corretoras) têm artifact.

### 1.3 · O título conta, não diz — e 79,7% dos títulos se repetem
📊 Manchetes da Resulta, 26/08→04/09: "2 item(ns) esperando você hoje" ×5 (5 dias diferentes, a mesma string), "1
item(ns)…" ×2, "Nada precisa de você agora" ×2, "4 item(ns)…" ×1 — e a 11ª, do semanal de 31/08: "2 ponto(s) de decisão e 20 trabalho(s) entregue(s)" (ramo
`weekly_executive` de `_narrativa`, `:318-321`, que o D.3 preserva; 📊 os 20 eram `intelligence.detect_signals`). A manchete é `_narrativa()`
(`briefing_service.py:322-330`): ela só conta. O achado principal ("Fila acumulada — 61 atendimentos parados há mais
de 24h") é o item 1 do corpo e nunca chega ao título. 📊 `artifacts` da Resulta: **79 peças, 16 títulos distintos —
79,7% repetidos** ("Radar de Renovações · próximos 90 dias" 14×, "Raio-X Comercial · 2025" 14×, "Pulso 360 · 2026"
5×). O Pulso grava `titulo="Pulso 360 · %s"` e `subtitulo="O período inteiro, com a fonte de cada número"` fixos
(`executive_intelligence.py:1539-1540`).

### 1.4 · O texto dos achados foi escrito para o chat e chega ao corretor — e o "por quê" já existe e é jogado fora
📊 `evidence_pack.py:684`: *"há carteira vencendo na janela; o detalhe por faixa de urgência está no envelope da
métrica"*; `:712`: *"um produtor apropriou menos comissão que no período anterior, abaixo do limiar declarado"* — sem
número, sem sujeito, **de propósito** (o cabeçalho do arquivo diz: o nome fica no Artifact, o pack leva referência
opaca — certo para o modelo, inútil para o dono). O achado vira `summary_redacted` do sinal `commercial_opportunity`
(`:596`); o Fabric escolhe a narrativa por tipo (`finding_engine.py:200`, `NARRATIVAS.get(tipo, NARRATIVA_PADRAO)`) e
não há entrada para esse tipo → `NARRATIVA_PADRAO` (`:151`: "Ponto de atenção" / `observacao`). 📊
`intelligence_findings` da Resulta, 4 dias: **3/3** "Ponto de atenção", 2 com o resumo idêntico do produtor.
🔴 **E o que o Founder pediu já é produzido:** 📊 `intelligence_findings`: `why_now` preenchido em **12/12**, `next_step`
em **11/12**, `fact_statement` 12/12. `ItemDeBriefing` (`briefing_service.py:85-98`) **não tem campo** para nenhum dos
dois e `como_dict` (`:100-110`) — o jsonb que vira `payload.sections[].items[]` — não os emite. O porquê e o próximo
passo morrem uma chamada antes da tela.
📊 **Dentro do mesmo briefing, 35,1% dos itens são cópia exata** (20 de 57 nos 5 últimos da Resulta). No de 04/09, 6 dos
14 itens são o MESMO Work Run repetido: "Procurar o que mudou na operação · 0 regra(s) executada(s), 0 sinal(is)
registrado(s)…" ×4 e "· 0% concluído" ×2 — é `intelligence.detect_signals`, o ciclo do próprio tick, listado como
"trabalho em andamento" e "o que ficou pronto".

### 1.5 · O Pulso 360 tem 13 seções, nenhuma diz o que fazer, e a procedência não chega ao banco
📊 `_compor` (`executive_intelligence.py`, `:1550`–`:1946`): `cover` + `verdict` + 11 seções de número + `sources` +
`footer`. O veredito (`_veredito`, `:1950`) concatena os summaries de máquina da 1.4. Métrica INDISPONÍVEL vira um
`callout` inteiro cada (seções 4, 8, 9, 10, 11, 12 têm o ramo): um Pulso sem funil, sem mercado e sem repasse imprime
**quatro caixas dizendo que não há dado**. Os blocos `actions` (`blocks.py:298`) e `callout` (`:284`) existem desde a
057; nenhum relatório usa `actions` para ação. 📊 `artifact_versions.data_sources = []` em **5/5** Pulsos (`_publicar`
desenha o bloco `sources` na composição e **não passa `data_sources=`** ao `criar`); `confidence_note` vazio em
**136/136** versões do sistema.

### 1.6 · A lista não sabe o que cada coisa é
📊 `route.ts`: 8 consultas, 6 viram linha (2 são lookups de nome), `LIMITE_POR_FONTE = 120` (`:63`), 410 geradas →
400 entregues; busca no navegador sobre título/detalhe/origem (`EntregasClient.tsx:188-190`). `origem` = `a.kind` cru
(`"report"`, em inglês) enquanto o detalhe traduz para "Relatório" (`page.tsx:67-82`). `function Linha`
(`EntregasClient.tsx:77-95`) é UM componente para os 4 tipos: a única diferença entre um Pulso e uma conversa de
WhatsApp é a cor de um ícone de 16 px. `AUXILIAR_DO_TEMPLATE` (`[artifactId]/page.tsx:56-61`) conhece 3 chaves →
📊 **35 de 136 peças (25,7%) abrem sem produtor**. `estadoDaEntrega()` (`route.ts:257`) **substitui** o resumo pelo
estado quando a entrega não foi `sent`. O sidebar diz "Entregas" (`lib/navigation.ts:50`); a URL é alvo de 4 redirects
(`test_menu_nao_cresce.py:45-55`, `ROTAS_QUE_MUDARAM` — 📊 três mandam `?tipo=`; `app/dashboard/atividades/page.tsx:17`
NÃO manda nenhum), do `_link()` do chat (`relatorios_comerciais.py:340`) e de 2 guardas. 📊 Latência
das 2 consultas mais pesadas: **1,2 ms e 1,0 ms** — o problema é de conteúdo e de descoberta, não de tempo.

### 1.7 · O que já existe e serve — nada disto se reconstrói
`ArtifactService` (`service.py`): `criar` (:61, aceita `subject_ref`, não aceita `tags` nem data de corte),
`nova_versao` (:138), `renderizar` (:170), `publicar` (:216 — supersede a anterior, sobe `current_version`), `listar`
(:355 — filtra tenant e `archived_at`). Colunas prontas e sem uso: `artifacts.tags[]`, `subject_ref`, `archived_at`,
`current_version`; `artifact_versions.data_sources`, `data_as_of`, `confidence_note`. 📊 Nunca existiu uma v2
(`max(version)=1`), um share (0), um arquivado (0). Templates entram por upsert no uso (`_garantir_template`, :96) —
**zero migration**. `listar_entregas` (094.1) já lista com link autenticado. Guardas que ficam e o que fixam:
`test_menu_nao_cresce.py:95-99` (a KEY `entregas`, o HREF e exatamente 6 pilares — o LABEL é livre);
`test_navegacao_sem_pagina_orfa.py:90,384` (o chip "Pesquisas" é o único caminho para `/dashboard/entregas/pesquisas`);
`entregas-tudo-abre.test.mjs` (5 fontes, todo href, `company_id` em toda consulta e na fonte, `?tipo=`; o dublê tem 1
briefing com artifact e 1 sem); `entregas-mostra-o-historico.test.mjs:231-238` (o título da execução nomeia o
Auxiliar dono: "Cobrança Feita rodou") e `:521` (nada de PII no detalhe). Renderizador: `cover` aceita
`title/subtitle/verdict/headline_*` (`blocks.py:82`), `actions` aceita `title/detail/owner/due/impact` (:298).

### 1.8 · A repetição que o Founder sente é a LISTA — o envio é um só, e é igual nas três corretoras
📊 `delivery_detail` dos 3 últimos briefings da Resulta: `canais: [{canal: "dashboard", motivo: "está no painel, em
Entregas"}]`, `push: true`, `sent`. Nenhum WhatsApp, nenhum e-mail. 📊 `work_runs` de 14 dias: as três corretoras
recebem o diário **no mesmo minuto** (08:00–08:08 local; alvo 08:00 com 1 h de tolerância em `deve_publicar_briefing`,
`briefing_service.py:75-105`; `tick.py:274-291`), 42/42 `completed`; o semanal na segunda. É literalmente lote.

### 1.9 · 🔴 `data_as_of` não é a data do dado: é `now()` — e a tela afirma que é (achado do investigador)
📊 `service.py:155-160`: `"data_as_of": _agora().isoformat()` em `_nova_versao`; **nenhum caller passa data de corte**
(a assinatura de `criar` nem tem o parâmetro). 📊 136/136 versões: `data_as_of` = carimbo da escrita; **30/136 no
FUTURO do próprio `created_at`** (desvio de relógio POR PROCESSO: o worker do tick grava a −0,1 s, o contêiner da API a +50…+70 s; nos 5 Pulsos, +69,9 s —
no futuro).
`[artifactId]/page.tsx:217` imprime *"Dados de 4 de setembro de 2026, 02:55"*. **É blocker pelo teste do produto (§2):
uma afirmação de frescor que o sistema não tem como sustentar chega à corretora.** A proposta (§107) daria gate verde:
ela mede presença, o defeito é de valor. CLAUDE.md §12.1: conserta-se o campo, não o texto.

### 1.10 · O placar ingênuo mentiria por 87×
📊 `work_runs` da Resulta: **1.228** na vida; `source_type='system'` **1.214 (98,86%)** — `intelligence.detect_signals`
953 vezes para produzir 32 sinais, `measure_outcomes` 160, `garimpo` 41, `daily_briefing` 40. Pedidos pela corretora:
`chat` **7** + `routine` **7**. As três corretoras têm ~1.210 cada porque o número é do relógio, não delas. Volumes
reais (Resulta, 30 d / vida): conversas 221 / 266 · atividades de agente 60 / 175 · artifacts 72 / 79 · execuções de
rotina 13 / 45 · sinais 16 / 32 · pesquisas 1 / 1 · `auxiliary_runs` 0. Colunas de data que existem: `routine_runs`
**não tem `created_at`** (`started_at`); pesquisas = `research_requests.created_at`.

### 1.11 · O que a proposta pedia e não tem chão hoje
📊 `artifact_shares` = **0** em 3 corretoras (P-094.1-LINK-PUBLICO). Renders **136/136** `html/ready/inline`;
`storage_ref` = 0. 📊 `grep -in "playwright\|chromium\|weasyprint" backend/requirements*.txt backend/Dockerfile*` →
**0**. 📊 `grep -rn "artifact_deliver" backend app` → 0. A proposta cita "36 artifacts href null" como estado atual:
hoje são 136, nenhum sem href (a 078 fechou). Blocos de share/engagement/restore/archive/PDF desenham telas para zero
linhas; a queixa do Founder toca 136.

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado, corretor ou seguradora. O briefing continua saindo só no painel (1.8).
⛔ ZERO migration. Tudo em código e nas colunas que já existem (tags, subject_ref, archived_at, current_version, data_sources, data_as_of).
⛔ Nenhum LLM escreve número, título, "por que importa" ou "o que fazer": a narrativa é determinística por detector, com guarda.
⛔ Nenhum motor paralelo: uma rota de lista (a que existe), um publicador (ArtifactService), um mapa de tipos (novo, ÚNICO,
   lido pela lista e pelo detalhe). O placar é LEITURA; não cria tabela, contador nem evento.
⛔ O placar NÃO conta o relógio da plataforma: `work_runs.source_type='system'` fora, `tool_invocations` fora (1.10). A regra de
   exclusão é escrita no código e o guarda prova que reintroduzi-la fica vermelho.
⛔ `data_as_of` só é gravado quando quem publicou SABE a data do dado; sem data → NULL, e a tela não afirma frescor (1.9).
⛔ A limpeza dos relatórios de teste é `archived_at` (reversível, com evento), nunca DELETE. E só o que o BLOCO 0 provar canário.
⛔ Todo canário vivo desta SPEC (e das próximas) roda com `AUTOBROKERS_CANARIO=1` e arquiva o que criou.
⛔ A URL /dashboard/entregas, a KEY `entregas` e os 6 pilares NÃO mudam (`test_menu_nao_cresce.py`). Muda o LABEL.
⛔ O chip "Pesquisas" fica (é o único caminho para a tela de pesquisas: `test_navegacao_sem_pagina_orfa.py:90`).
⛔ Os títulos das EXECUÇÕES ("Cobrança Feita rodou") não mudam (`entregas-mostra-o-historico.test.mjs:231`).
⛔ O chat (SPEC-096) recebe UM gancho (3 linhas + 1 prop): ler `?pergunta=` num inicializador síncrono e pré-preencher. Nunca enviar sozinho, nunca por efeito.
⛔ NUNCA nome de pessoa em título, sinal, summary ou pack (SPEC-094 §2). Nome de SEGURADORA pode. Produtor: só via `rotulos_de_produtor`
   dentro do Artifact do tenant, nunca no sinal nem no pack.
⛔ NUNCA `git add -A`. Nenhuma variável de ambiente de produção. Nada em `.env`.
```

## 2.1 O EXECUTION CARD da conversão — o executor confere e discorda com número

```
SPEC .................  095 · Relatórios que o corretor entende
OUTCOME ..............  o corretor abre Relatórios e cada card diz o que é, de quem é, de quando é e o que achou; nada repetido, nada de
                        teste; o relatório abre pelo achado e diz o que fazer; um placar honesto prova o trabalho feito; a data do dado é a do dado
RISCO ................  5 — ALCANCE 2 (a corretora: a tela e o relatório que o PRODUTO gera) · REVERSIBILIDADE 2 (versões novas em vez
                        de peças novas; `archived_at` nos canários — reversível por UPDATE com o evento como registro; título/subtítulo/
                        data_as_of gravados) · FREQUÊNCIA 1 (briefing diário; Pulso sob demanda)
SUPERFÍCIE ...........  2 — vários comportamentos em lugares que eu listo (§4): lista/rota/menu · publicação (`_publicar`,
                        `_gerar_artefato`, `service.py`) · narrativa (`evidence_pack`, `narrativa.py`, `_compor`/`_veredito`,
                        `_narrativa`/`compor`/`ItemDeBriefing`, `compor_pecas`) · detalhe · placar (rota nova) · chat (1 gancho)
PISO APLICADO ........  não atingido: nada envia (1.8), zero migration, nenhuma mudança em auth/sessão; as consultas novas NASCEM com
                        `company_id` e o gate exige dois tenants
NÍVEL ................  PADRÃO sob a opção B: desenhista ANTES (há guardas novos) · 2 builders Opus em arquivos DISJUNTOS (frontend ‖
                        backend — o mesmo custo de um builder, metade do relógio) · painel = RED TEAM (uma lente, contexto limpo) ·
                        confirmação MECÂNICA (Sonnet reroda guardas + mutações do conserto) · canário vivo pelo orquestrador
UNIDADES .............  6 — BLOCO 0 · A (a lista e o nome) · B (identidade: versões, canário marcado, data honesta, limpeza) · C (o
                        placar) · D (a narrativa: título = achado · o que importa · o que fazer · o briefing sem o relógio) · E (o detalhe:
                        versões, fontes, perguntar) · F (canário vivo + dossiê). 🔴 ORDEM: desenhista ‖ (A+C+E) ‖ (B+D) → integração → red team → conserto →
                        confirmação mecânica → F, e dentro do F: B.4 só com E no ar, e ANTES de qualquer canário publicar (E11)
COESÃO ...............  A+C+E = FRONTEND (route.ts, EntregasClient.tsx, [artifactId]/page.tsx, arquivo/route.ts, navigation.ts,
                        placar/route.ts, lib/relatorios/tipos.ts, chat: 2 linhas) — UM escritor · B+D = BACKEND (evidence_pack.py,
                        narrativa.py, executive_intelligence.py, relatorios_comerciais.py, workflows.py, briefing_service.py,
                        service.py, scripts/) — UM escritor. B e D tocam os MESMOS arquivos → juntos. O contrato entre os dois lados são
                        as COLUNAS existentes (title, subtitle, summary, tags, subject_ref, current_version, data_sources, data_as_of,
                        confidence_note) e os `props` dos blocos — fixados em §BLOCO A.3 e §BLOCO D
PARALELISMO REAL .....  2 escritores (frontend ‖ backend) depois do desenhista; integração serial; regressão depois de cada merge
TIME .................  Fable orquestra · Opus 5: aquecimento, desenhista, builder FE, builder BE, red team · Sonnet 5: confirmação mecânica
REFERÊNCIA ...........  interna: DS-001 §5 (calma, sidebar limpa, pouca competição visual) · `EntregasClient.tsx` F.6b (linha sem destino
                        PARECE sem destino) · `blocks.py` cover/actions/callout · os 2 guardas da 078 · externa: §3 (6 reabertas em 04/09)
GATES ................  GATE ZERO (7 vermelhos em HEAD provados pelo guarda ANTES do código) · guardas novos com PARES:
                        `scripts/relatorios-dizem-o-que-sao.test.mjs` e `backend/tests/test_o_relatorio_abre_pelo_achado.py` ·
                        os 2 guardas da 078 VERDES sem mudar (📊 provado por mutação no aquecimento) · a frase de trabalhos AUSENTE quando M = 0 (E2) · `textoInicial` zerado no 1º envio (E10) · `npm run test:rotas-montam` + `next start` + 1 GET
                        a `/api/dashboard/entregas` (mexe em app/) · dois tenants na lista e no placar · suíte inteira 1× no fim
O ELO ................  "o corretor entende o card PORQUE o título é o achado": medir (a) `artifacts.title` = título do achado principal
                        depois do canário (SELECT); (b) a rota devolve esse `title` (guarda executa a rota REAL com dublê, como a 078);
                        (c) a tela imprime `titulo` (guarda lê o cliente). E "o porquê chega PORQUE `como_dict` o emite": SELECT no jsonb
                        da publicação do canário → `why_now` e `next_step` presentes. E o elo que o aquecimento MEDIU e que chega
                        longe demais: "o briefing para de repetir PORQUE o `system` sai" — 📊 A = 35,1% duplicados, B = 40/41 itens
                        são `system`, e o elo apaga 70,2% do briefing e zera "trabalhos prontos" em 5/5 dias: por isso a E2 muda
                        a manchete antes de qualquer código
FAIXA DE RELÓGIO .....  5–7h do primeiro despacho ao push (o aquecimento acrescentou 1h: 12 emendas e o canário como script) (desenhista 45 min · builders 1h30–2h em paralelo · red team 30 min ·
                        conserto 45 min · canário + limpeza + dossiê + relatório 1h)
ORÇAMENTO ............  ≤ 1,3 M tokens de subagentes (opção B · PADRÃO); 📊 conversão gastou 225k (investigador+pesquisador) + 199k (aquecimento) = 424k
BATERIA ..............  suíte inteira 1× no gate final; parciais (2 scripts + 2 guardas python + canário 094) a cada bloco
```

---

## 3. 🌐 O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS — §7.3, reaberto em 04/09/2026 pelo pesquisador

**Mortas ou mudadas na reabertura:** `docs.n8n.io/workflows/executions/all-executions/` → 404 (movida) · `help.openai.com/…/deep-research-faq`
→ 403 (não inspecionável) · **Notion removeu a aba "Archived"** que o pack §41 e a proposta §28 citam como quick view.

### ① Zapier — o que NÃO conta como trabalho está escrito
```
URL ................. https://help.zapier.com/hc/en-us/articles/8496196837261-How-is-task-usage-measured-in-Zapier  (reaberta 04/09/2026)
O QUE FAZ ........... define por escrito o que não é task: "triggers never use tasks… polls never use tasks"; filtros, paths, passos
                      que erram e utilitários internos também não
MODELAMOS ........... BLOCO C: o placar conta o que a corretora PEDIU e RECEBEU; `work_runs.source_type='system'` (📊 1.214/1.228) e
                      `tool_invocations` ficam fora, e a regra de exclusão é uma constante nomeada no código
REJEITAMOS .......... a moldura de cobrança (quota, teto, "tasks restantes") — é SPEC-062
COMO O JUIZ INSPECIONA abre as duas listas da doc · `select source_type, count(*) from work_runs where company_id=… group by 1` ·
                      confere que o placar mostra 14 trabalhos pedidos, não 1.228 · mutação: reintroduzir `system` → guarda vermelho
```
### ② AWS Trusted Advisor — três campos nomeados por achado: critério · ação recomendada · itens afetados
```
URL ................. https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor.html  (reaberta 04/09/2026)
O QUE FAZ ........... cada check abre com "Alert Criteria" (o limiar), "Recommended Action" e a tabela dos itens afetados; o estado é
                      frase ("Action recommended"), não só cor
MODELAMOS ........... BLOCO D: o contrato de campos por achado — título · por que importa (o limiar cruzado) · o que fazer · a pergunta
                      pronta; 📊 `why_now` 12/12 e `next_step` 11/12 já existem em `intelligence_findings` e entram em `ItemDeBriefing`
REJEITAMOS .......... semáforo por cor como linguagem primária; "excluir & atualizar" (burocracia de ECM)
COMO O JUIZ INSPECIONA lê os 3 nomes de campo na doc · abre o jsonb de um briefing do canário e conta itens com `why_now` e `next_step`
                      não vazios · mutação: `como_dict` sem um dos dois → vermelho
```
### ③ Datadog Watchdog — dedup e prioridade por CHAVE DECLARADA, evidência dentro do card
```
URL ................. https://docs.datadoghq.com/watchdog/insights/  (reaberta 04/09/2026)
O QUE FAZ ........... ordena e colapsa insights por (Insight type, State, Status, Start time, Anomaly type); o card leva a evidência
                      e uma ação de uma tecla
MODELAMOS ........... BLOCO A.4 e D.3/D.5: a chave de colapso é escrita — lista: (artifact_id) para briefing×artifact; briefing:
                      (headline, summary) para itens e (outcome_title, status) para Work Runs, com "(+N iguais)"
REJEITAMOS .......... anomalia estatística: nossos achados são determinísticos por limiar escrito (`evidence_pack.py:553-556`)
COMO O JUIZ INSPECIONA copia as chaves da doc · confere as nossas na SPEC · roda o extrator sobre os 5 últimos briefings do canário e
                      exige `itens_duplicados = 0` (📊 hoje 35,1%)
```
### ④ Figma — uma identidade, muitas versões; cada versão com link próprio; restaurar é não destrutivo
```
URL ................. https://help.figma.com/hc/en-us/articles/360038006754-View-a-file-s-version-history  (reaberta 04/09/2026)
O QUE FAZ ........... a linha da versão tem nome, descrição, data/hora e autor; "Copy link" por versão; "non-destructive action"
MODELAMOS ........... BLOCO B.1 e E: o Pulso 360 · 2026 é UMA peça; cada pergunta é `nova_versao` + `publicar`; o detalhe lista as
                      versões (número · data · dados lidos em) e `?versao=` abre/baixa a versão exata
REJEITAMOS .......... "Restaurar" e "Comparar" — 📊 nunca existiu uma v2; entra o COLAPSO (136 linhas para arrumar)
COMO O JUIZ INSPECIONA pede o Pulso 2× no canário → `select id, current_version from artifacts where …` → 1 linha, versão 2 ·
                      `/arquivo?versao={v1}` baixa a v1 (mutação: baixar sempre a última → vermelho)
```
### ⑤ Notion — lentes como abas de UM item de menu, e "customize which details show up"
```
URL ................. https://www.notion.com/help/manage-your-library  (reaberta 04/09/2026 — as abas hoje: Teamspaces · Recents ·
                      Favorites · Shared · Private · AI Meeting Notes · Agents; "Archived" não existe mais)
O QUE FAZ ........... a biblioteca é um item de menu com visões rápidas e detalhes configuráveis por linha
MODELAMOS ........... BLOCO A: as lentes vivem DENTRO de Relatórios como chips; a "coluna que falta" vira tipo humano · produtor ·
                      período · versões no card
REJEITAMOS .......... "Arquivados" como ABA (a Notion a removeu; 📊 arquivados = 0 hoje). Fica um LINK discreto "ver arquivados (N)"
                      no fim da lista — porque a limpeza do B.3 cria 35 e o Founder precisa poder olhar e desfazer
COMO O JUIZ INSPECIONA lê a lista de abas na doc · roda `test_menu_nao_cresce.py` (6 pilares) · confere que não há aba nova
```
### ⑥ Claude Artifacts — a lista mostra a PEÇA; o seletor de versões mora dentro dela
```
URL ................. https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them  (reaberta 04/09/2026)
O QUE FAZ ........... "view all your creations in one organized location"; "switch between different versions using the version selector"
MODELAMOS ........... BLOCO A + E: um card por peça com "N versões"; as versões dentro do detalhe — resolve os 📊 40 pares e as 14
                      repetições sem tela nova
REJEITAMOS .......... "remix" e catálogo público — Artifact de corretora carrega carteira e comissão (CLAUDE.md §7)
COMO O JUIZ INSPECIONA lê a doc · compara com `/dashboard/entregas/{id}` de hoje, onde "versão N" é texto morto (`page.tsx:209`)
```

**O que o estado da arte faz e nós não (pesquisador, nota por valor para a corretora):** o achado abre com o porquê e
o que fazer **96** · dedup por chave declarada **92** · uma identidade, muitas versões **88** · contar só o trabalho
pedido **85** · título = achado **80** · a linha diz o que é **74** · frescor honesto **72** · busca que alcança o
antigo **58** (📊 latência 1,2 ms: é descoberta, não performance) · share/engagement/PDF/favoritos **20** (zero dado).

---

# BLOCO 0 · REMEDIR — o executor refaz a §1 e prova os 7 vermelhos ANTES do código

Remedir 1.1–1.11 pelos comandos (SQL e grep). Se o número for outro, o do executor vence e os dois vão para o relatório.
Fixar a lista dos **relatórios de teste** para a limpeza do BLOCO B.3 com o SQL da 1.1 e as janelas do `git log`
(18/08 05:00–11:00 · 03/09 15:00–21:00 · 03/09 21:00–04/09 04:00): 📊 esperado Resulta 34 · AutoFleet 1 · Amandus 0.
Confirmar que `finding_engine.py:235` continua `resumo = str(principal.get("summary_redacted") or narrativa.titulo)`
e que `commercial_opportunity` continua sem entrada em `NARRATIVAS` — é o encaixe do D.1. Confirmar as colunas de data
da 1.10 (`routine_runs` sem `created_at`).

**GATE ZERO — o desenhista escreve os guardas e prova que ficam VERMELHOS em `5c22590`:**
```
(i)   a rota lista o briefing de hoje DUAS vezes (ids `briefing:` e `artifact:` com o mesmo artifact_id)         VERMELHO
(ii)  `_publicar` com o MESMO (template, período) cria um segundo artifact em vez de uma versão                    VERMELHO
(iii) `_narrativa` devolve "N item(ns) esperando você hoje" quando há item acionável com manchete própria          VERMELHO
(iv)  `_compor` do Pulso não emite bloco `actions`; o título é "Pulso 360 · {rótulo}"                             VERMELHO
(v)   `_publicar` com `AUTOBROKERS_CANARIO=1` grava `tags = []`                                                     VERMELHO
(vi)  `como_dict` de um item com finding que tem `why_now`/`next_step` não os emite                                VERMELHO
(vii) `_nova_versao` grava `data_as_of = now()` sem ninguém ter passado data                                       VERMELHO
```

# BLOCO A · RELATÓRIOS — a lista que diz o que cada coisa é (frontend)

**A.1 · O nome.** `lib/navigation.ts:50` → `label: 'Relatórios'` (key, href e ícone iguais — `test_menu_nao_cresce.py`
fixa os três e conta 6 pilares). Títulos de página, breadcrumbs e "Voltar" em `entregas/page.tsx`,
`EntregasClient.tsx:200-202`, `[artifactId]/page.tsx:170`, `rotina/[runId]/page.tsx:151`; o subtítulo do
`DetailHeader` ("Tudo que o AutoBrokers fez por você — relatórios, conversas, trabalhos e pesquisas, num lugar só").
Filtro "Documentos" → "Relatórios". **Lente padrão sem `?tipo=`: Relatórios** (decisão 0–100: abrir em Relatórios 80 ·
em Tudo 55 — a queixa é a mistura). `?tipo=conversa|trabalho|tudo` continuam valendo. 📊 Dos 4 redirects (`test_menu_nao_cresce.py:45-55`), três
mandam `?tipo=`; o quarto — `app/dashboard/atividades/page.tsx:17` → `/dashboard/entregas` — não manda nenhum e
herdaria a lente `documento`, escondendo as atividades (`route.ts:339-340` dá a elas `tipo: 'trabalho'`) de quem salvou
o link: passa a `redirect('/dashboard/entregas?tipo=tudo')`. O chip "Pesquisas ↗" fica.

**A.2 · O mapa único de tipos** — `lib/relatorios/tipos.ts` (NOVO), lido pela lista E pelo detalhe (hoje o detalhe
tem `AUXILIAR_DO_TEMPLATE` só para si, com 3 chaves — 📊 25,7% das peças abrem sem produtor):
```
template_key                     tipo humano            ícone (lucide)     produtor padrão
briefing.daily_operational       Briefing do dia        sunrise            Checklist das 6h   (origin routine)
briefing.weekly_executive        Resumo da semana       calendar-days      Checklist das 6h
executive.pulse360               Pulso 360              activity           AutoBrokers (chat)
commercial.pipeline              Raio-X comercial       scan-search        AutoBrokers (chat)
renewals.radar                   Radar de renovações    radar              AutoBrokers (chat)
financial.billing_collection     Cobrança               receipt            Cobrança Feita
(default)                        Relatório              file-text          origem em português (chat → AutoBrokers · routine → Auxiliar · manual → você)
```
O produtor vem de `subject_ref.produtor` quando o publicador gravou (BLOCO B); sem ele, do mapa por `origin` +
`template_key` — **rotulado no código como `legacy_inferred`**, nunca como autoridade (proposta §51/§151). A resposta da rota carrega `produtorOrigem: 'declarado' | 'inferido'` — o
card não imprime a palavra; o Gate A [4] confere o campo.

**A.3 · A anatomia do card** (contrato com o BLOCO D — a rota devolve os campos; o cliente só desenha):
```
[ícone do tipo]   TÍTULO = artifacts.title (o achado; BLOCO D)                          [ETIQUETA]
                  SUBTÍTULO = tipo humano · produtor · período (subject_ref.label ou a data)
                  DETALHE = artifacts.subtitle (1 linha, humana; BLOCO D) — NUNCA substituído pelo estado da entrega
                  RODAPÉ = "hoje 08:05" · quando current_version > 1: "atualizado hoje 02:54 · 5 versões"
ETIQUETA (uma, a mais forte):  "crítico" (critical_count > 0) · "entrega parcial" / "não entregue" (delivery_status partial/failed — o
                                estado vira etiqueta, o resumo fica; vem ANTES de "precisa de você" porque quem não recebeu o relatório não
                                tem como agir sobre a recomendação dele — decisão do builder, confirmada) · "precisa de você"
                                (recommendation_count > 0 ou item acionável) · nenhuma quando tudo certo (etiqueta que aparece sempre é
                                etiqueta que ninguém lê)
```
Campos novos na resposta da rota: `tipoHumano`, `produtor`, `periodo`, `etiqueta`, `versoes`, `teste` (bool), sempre
presentes para `artifact:`; os demais tipos (`conversa:`, `run:`, `rotina:`, `atividade:`) ganham `tipoHumano` e
`produtor` pelo que já têm (Chat/Atendimento · nome do Auxiliar · categoria) e mantêm os títulos de hoje.
📊 `route.ts:171-172` seleciona hoje `id, title, subtitle, kind, status, created_at`: os campos novos exigem **cinco
colunas a mais** no mesmo SELECT — `template_key` (tipoHumano), `subject_ref` (produtor + periodo), `current_version`
(versoes), `tags` (teste e o filtro do A.4b), `origin` (o fallback inferido). Sem elas o A.4(b) filtra por uma coluna
que a consulta não trouxe.

**A.4 · Nada duas vezes, nada de teste.** (a) `briefing_publications` com `artifact_id` **não vira card**: a
publicação é dobrada no card do artifact (o card recebe `produtor = 'Checklist das 6h'`, `etiqueta` pelo
`critical_count/recommendation_count/delivery_status`, `href = /dashboard/entregas/{artifact_id}`); publicação SEM
artifact continua como `briefing:` com o href da tela de execução (a lição da 078 F.2 migra: o dublê do guarda já tem
UMA publicação sem artifact para esse ramo continuar exercido). (b) `artifacts` com `tags @> {canario}` **não
entram** (`.not('tags', 'cs', '{canario}')`), nem arquivados (já). (c) `?arquivados=1` lista SÓ os arquivados
(inclusive os de teste), com etiqueta "arquivado" — acessível por um link discreto "ver arquivados (N)" no fim da
lista, nunca por chip ou aba (§3 ⑤). É o que dá ao Founder o direito de desfazer a limpeza do B.4 olhando. O modo arquivados ignora a lente: lista só `artifact:` arquivados (conversas e
trabalhos não se arquivam) e esconde os chips.

**A.5 · O que não muda:** 8 consultas, `LIMITE_POR_FONTE`, busca no navegador, ordenação por data, linha-sem-destino da
078 F.6b, empty states, os títulos das execuções, o chip Pesquisas. Busca no servidor e paginação: §5, com gatilho.

**Gate A** — `scripts/relatorios-dizem-o-que-sao.test.mjs` (executa a rota REAL com o dublê da 078, mais o cliente e
o mapa por leitura), com PARES:
```
[1] publicação COM artifact → UM card, id `artifact:`, produtor "Checklist das 6h", href do artifact   (PAR: dublê antigo → 2 cards → vermelho)
[2] publicação SEM artifact → card `briefing:` com a tela de execução                                (PAR: href do cartão → vermelho)
[3] artifact com tag canario → ausente; com ?arquivados=1 → presente com etiqueta "arquivado"        (PAR: filtro removido → vermelho)
[4] todo `artifact:` tem tipoHumano, produtor, periodo não vazios; `versoes` = current_version; o detalhe do card com
    delivery_status=partial continua sendo o resumo, e a etiqueta diz "entrega parcial"                (PAR: campo vazio → vermelho)
[5] `lib/navigation.ts`: label 'Relatórios', key 'entregas', href '/dashboard/entregas'; 6 itens          (PAR: 7 itens → vermelho)
[6] toda consulta da rota com company_id (reusa guardaEscopoPorEmpresa)                                (PAR: uma sem → vermelho)
[7] `?tipo=` continua aceitando conversa/trabalho/tudo; padrão 'documento'; o chip Pesquisas existe   (PAR: cliente sem URL → vermelho)
```
E os dois guardas da 078 **continuam VERDES sem alteração** — 📊 o aquecimento provou por mutação (desligar o laço de
briefings da rota → "fonte ausente: briefing" e "nenhum briefing na lista", VERMELHOS; restaurado → verde): o dublê
deles tem 1 publicação COM e 1 SEM artifact, e a linha `briefing:` sobrevive ao A.4. A asserção nova ("a publicação COM
artifact não vira card") mora no guarda NOVO, nunca num afrouxamento dos velhos.

# BLOCO B · IDENTIDADE — uma peça, muitas versões; a data do dado é a do dado; o teste não suja a biblioteca (backend)

**B.1 · A identidade da peça** = `(company_id, template_key, subject_ref->>'id')`. `_publicar`
(`relatorios_comerciais.py:318`) ganha `identidade: dict` (`{"kind": "periodo", "id": "2026", "label": "2026",
"produtor": "autobrokers.chat"}`), `data_sources` (os MESMOS itens que `_fontes` desenha — hoje a coluna fica vazia,
1.5) e `data_as_of` (a hora em que a fonte foi lida — `agora` do pack) e passa a: procurar `artifacts` com a mesma
identidade (`.eq("company_id").eq("template_key").eq("subject_ref->>id", …).is_("archived_at","null")`, `limit(2)` — 🔴 SÓ quando `identidade["id"]` é NÃO-VAZIO: 📊 `subject_ref->>'id' = ''`
casa 6 Pulsos, 14 Raio-X e 14 Radares legados na Resulta, e `= NULL` não casa os 96 com `{}`; 2 linhas vivas = defeito,
levanta) →
**existe:** `nova_versao` + `renderizar` + `publicar` e atualiza `title/subtitle/summary` da peça (o achado muda a cada
versão) → devolve o MESMO id; **não existe:** `criar` como hoje. `ArtifactService.nova_versao` aceita
`title/subtitle/summary` opcionais e os grava em `artifacts` (evento `artifact.retitled` com `{de, para, versao}` — sem o título anterior o renome seria irreversível). As três tools
que chamam `_publicar` (Pulso, Raio-X, Radar) passam identidade, fontes e data; a Cobrança (`billing_collection.py` — 📊 já grava `subject_ref.id` em 5/5, os "5/136" da §1.7; ganha `produtor` e
`data_as_of`) e
o briefing (`workflows.py:130`) gravam `subject_ref` com `kind/id/label/produtor` (identidade = o dia; já é uma por dia
pelo tick) e `data_as_of = period_end`. Identidade que casa peça ARQUIVADA: **cria nova**, não desarquiva (nota 85 ×
45): arquivar é gesto deliberado, e ressuscitar em silêncio desfaria a limpeza do B.4 peça por peça; o `artifact.created`
anota `identidade_arquivada: id8`.

**B.2 · A data do dado é a do dado (1.9).** `criar` e `_nova_versao` ganham `data_as_of: Optional[datetime] = None` e
gravam **NULL** quando ninguém passa — nunca mais `_agora()`; `confidence_note: Optional[str]` idem. Quem sabe a data
passa: Pulso/Raio-X/Radar = a hora da leitura da InfoCap; briefing = `period_end`; Cobrança = a hora da varredura dos
portais. O detalhe (BLOCO E) só afirma frescor quando o valor existe, e com a frase certa: "dados lidos em" (chat) ·
"período" (briefing). As 136 versões antigas ficam como estão (imutáveis); a tela deixa de chamá-las de "Dados de".

**B.3 · O canário se declara.** `_publicar` e `_gerar_artefato` leem `os.getenv("AUTOBROKERS_CANARIO")`; quando
verdadeiro, `criar(..., tags=["canario"])` (`criar` ganha `tags: Optional[list[str]]`; `_nova_versao` não mexe em
tags). `ArtifactService.arquivar(company_id, artifact_id, motivo)` (NOVO: `archived_at = now()`, `status` mantido,
evento `artifact.archived` com `{motivo}`) e `desarquivar` (evento `artifact.unarchived`). 📊 `test_o_canario_do_pulso_360.py` substitui `rel._publicar` por um capturador (`:573-580`, `:813-819`, `:1089-1118`,
`:1263-1270`) e monta a tool com `SupabaseFalso()`: ele NUNCA executa o `_publicar` real — exportar a variável ali
seria decorativo. Quem a exporta é `backend/scripts/canario_095.py` (NOVO; nota 88 × 55 da instrução em pacote): roda
o caminho REAL, guarda os ids que criou, imprime os SELECTs do BLOCO F e arquiva ao fim.

**B.4 · A limpeza — uma vez, reversível, à vista.** `backend/scripts/arquivar_relatorios_de_teste_095.py`:
`--dry-run` (padrão) lista os candidatos da 1.1 (por corretora, template, dia; sem título, sem id inteiro) e
`--aplicar` chama `arquivar(motivo="canário de execução de SPEC (081/094/094.1) — SPEC-095 B.4")` e NUNCA toca peça com
`tags @> {canario}` (as do canário desta SPEC se arquivam sozinhas, F(f)). VERIFY antes/depois, com a data fixa para o
número não envelhecer (📊 `_publicar` não grava `requested_by`, então `requested_by is null` casaria todo Pulso real
para sempre): `select count(*) from artifacts where origin='chat' and requested_by is null and archived_at is null and
created_at < '2026-09-04 07:00+00'` (📊 esperado 35 → 0)
e `select count(*) from artifact_events where event_type='artifact.archived'` (0 → 35). ROLLBACK escrito no relatório:
`update artifacts set archived_at = null where id in (select artifact_id from artifact_events where event_type='artifact.archived'
and detail->>'motivo' like '%SPEC-095 B.4%')`. **Rodada pelo orquestrador no BLOCO F, com a saída colada.**

**Gate B** (no guarda `test_o_relatorio_abre_pelo_achado.py`, blocos [B]): dublê de banco em memória — (a) `_publicar`
2× com a mesma identidade → 1 insert em `artifacts`, 2 em `artifact_versions`, `current_version` 2, título atualizado,
`data_sources` não vazio (PAR: identidades diferentes → 2 inserts); (b) `_nova_versao` sem data → `data_as_of` NULL;
com data → a data passada (PAR: `now()` → vermelho); (c) sem `AUTOBROKERS_CANARIO` → `tags=[]`; com → `["canario"]`
(PAR); (d) `arquivar` grava `archived_at` + evento, `listar` deixa de devolver, `desarquivar` volta (PAR); (e) o
script em `--dry-run` não escreve (dublê conta escritas = 0) (PAR: `--aplicar` = N); (f) `listar_entregas._packs_das_versoes` (`listar_entregas.py:180`) seleciona
`payload->evidence_pack->>pack_id`, nunca `payload` (PAR: `payload` inteiro → vermelho — 📊 64.246 bytes por versão,
5.890 deles `rotulos_de_produtor`). Mutação por cópia: `_publicar`
que sempre cria → [B.a] vermelho.

# BLOCO C · O PLACAR — o trabalho feito, sem dizer "trabalhamos muito" e sem contar o relógio (frontend)

Rota NOVA `app/api/dashboard/relatorios/placar/route.ts` (`requireCompanyMember`, `force-dynamic`, `no-store`):
```
janelas   hoje (00:00 local) · 7d · 30d · 365d · tudo
contagens relatórios   artifacts.created_at              sem canario, sem arquivados
          conversas    conversations.created_at
          execuções    routine_runs.started_at + auxiliary_runs.created_at      (📊 routine_runs não tem created_at)
          pesquisas    research_requests.created_at
          sinais       intelligence_signals.created_at    (o que o produto percebeu, com evidência)
          atividades   agent_activities.created_at
          trabalhos    work_runs.created_at  🔴 SÓ source_type in CONTA_COMO_TRABALHO = ('chat','routine') — INCLUSÃO, nunca
                       exclusão (📊 o domínio inteiro hoje: system 3.626 · chat 7 · routine 7; um source_type futuro entraria
                       por omissão numa lista de exclusão). A constante mora no topo da rota, com o porquê (📊 1.214/1.228
                       da Resulta são o tick). tool_invocations: fora
```
Toda contagem: `select('id', { count: 'exact', head: true }).eq('company_id', empresa).gte(coluna, desde)` — 7 tabelas
× 5 janelas em `Promise.all` (💭 < 300 ms; 📊 as consultas da lista custam ~1 ms). Resposta `{ ok, janelas: { hoje,
"7d", "30d", "365d", tudo }, regra: "o relógio da plataforma não conta" }`. 📊 Resulta, vida (pré-limpeza): relatórios
79 → 45 · conversas 266 · execuções 45 · pesquisas 1 · sinais 32 · atividades 175 · trabalhos pedidos 14 — 💭 ≈ 580,
e é verdade. 📊 E os 14 são, eles próprios, execução de SPEC (`bridge.routine.execute` ×7 e `acionamento.seguradora` ×4
de 17–19/08 = 081; `metric.proposal` ×2 de 04/09 = 094.1): o placar não marca canário em `work_runs`, e isso fica dito
na §7. Amandus 0 · AutoFleet 0: o zero mostra "—" com a frase "ainda não houve trabalho pedido neste período", nunca
uma linha vazia.

UI `components/relatorios/Placar.tsx`: uma faixa discreta sob o cabeçalho de Relatórios — controle segmentado
[Hoje · 7 dias · 30 dias · 1 ano · Desde o início], e uma linha de números com rótulo pequeno (relatórios ·
conversas · execuções · sinais · pesquisas · trabalhos pedidos); o maior número é a **soma** ("580 coisas feitas para
a Resulta"; 💭). Sem gráfico, sem cor forte, sem frase de marketing (DS-001 §5: calma; a prova é o número). Zero vira
"—". Preferência de janela em `localStorage` (try/catch), padrão 30 dias. Fica na página principal de Relatórios
(decisão do Founder de 04/09).

**Gate C** (no `relatorios-dizem-o-que-sao.test.mjs`, bloco [8]): executa a rota do placar com o dublê que registra
consultas — toda consulta tem `company_id` E uma janela (PAR: sem `company_id` → vermelho; sem `gte` → vermelho);
🔴 a consulta de `work_runs` filtra `source_type` e o dublê com 1.000 linhas `system` + 3 `chat` devolve **3** (PAR:
reintroduzir `system` → 1.003 → vermelho); dublê com duas corretoras → a resposta de A não conta linhas de B (PAR); a
resposta tem as 5 janelas × 7 contagens (PAR: janela faltando → vermelho); o cliente lê a rota e não calcula nada
(grep: nenhum `.from(` em `Placar.tsx`).

# BLOCO D · A NARRATIVA — o relatório abre pelo achado e diz o que fazer (backend)

**D.1 · Achados humanos, determinísticos.** Módulo NOVO e PURO `backend/app/comercial/narrativa.py`: para cada
`kind` de `achar_findings` (`evidence_pack.py:640`), um **playbook** — funções que recebem o achado (com os kwargs
que ele já carrega: `valor_pct`, `limiar_pct`, `apolices`, `ja_vencidas`, `delta_pct`, `subject_id`) e devolvem
`titulo`, `por_que_importa`, `o_que_fazer`, `pergunta` (a frase que o chat abre já escrita). `finding()` grava os
quatro campos no achado; `sinais_do_pack` manda `summary_redacted = titulo + ". " + por_que_importa + " " + o_que_fazer`
e `metadata.titulo/o_que_fazer/pergunta`. **O Fabric não muda** (decisão 0–100: promover a 1ª frase do sumário
humano a manchete no briefing quando o `finding_type` é o padrão `observacao` **80** · dar narrativa própria a
`commercial_opportunity` no `finding_engine` — título estático, sem número — 60 · três `signal_type` novos na
taxonomia de `schemas.py` — certo em princípio, superfície da SPEC-059 — 55). Registrado como
P-095-NARRATIVA-DO-FABRIC. 💭 Exemplos de copy (o builder escreve a versão final; o guarda confere FORMA — número no
título, quatro campos, zero nome — não a frase):
```
CONCENTRACAO           "{seguradora} concentra {valor_pct}% da comissão de {período}"
                       por que: acima de {limiar_pct}%, um reajuste ou uma mudança de política dessa seguradora mexe em quase metade da receita
                       fazer: distribuir as próximas renovações; comparar a sinistralidade dela com o mercado
                       pergunta: "como está a {seguradora} contra o mercado?"
EXPOSICAO_DE_RENOVACAO "{apolices} apólices vencem na janela · {ja_vencidas} já vencidas"
                       por que: renovação não trabalhada é comissão que some no mês seguinte
                       fazer: começar pelas já vencidas · pergunta: "quais apólices já venceram e não renovaram?"
QUEDA_DE_PRODUTOR      "Um produtor apropriou {|delta_pct|}% menos que no período anterior"    (sem nome: sinal e pack)
                       fazer: conversar antes do fechamento · pergunta: "como está cada produtor este período?"
COBERTURA_BAIXA        (continua low, sem ação; vai para a linha "o que não deu para medir")
```
⛔ Nome de produtor só entra no Artifact do tenant, via `rotulos_de_produtor` na composição (D.2) — nunca em
`titulo`, `summary`, sinal ou pack (M16 da 094 continua verde).

**D.2 · O Pulso 360 abre pelo achado.** `_compor` (`executive_intelligence.py`): `cover.title` = `titulo` do achado
de maior severidade (sem achado: "{comissão} de comissão em {período}, nada fora do limiar" — número do registry);
`cover.subtitle` = "Pulso 360 · {período} · dados lidos em {hora}"; `verdict` = uma frase (o `por_que_importa` do
primeiro). **Seção 2, NOVA: "O que importa agora"** = bloco `actions` com um item por achado que `vira_sinal`
(`title = titulo`, `detail = por_que_importa + " → " + o_que_fazer`, `impact` = o número curto; o nome do produtor
entra aqui via `rotulos`). Depois, as seções de número como estão. **As INDISPONÍVEIS colapsam:** toda métrica
`indisponivel` sai das seções individuais e vai para UMA linha `prose` "O que não deu para medir neste período"
(uma frase por métrica, com o motivo da fonte). `sources` fica, `footer` fica. `_publicar_a_peca` grava `titulo =
cover.title`, `subtitulo = cover.subtitle`, `resumo = verdict`, a identidade do B.1, `data_sources`, `data_as_of` e
`confidence_note` = "{n} métrica(s) indisponível(is); cobertura mínima {x}%" (do pack).

**D.3 · O briefing abre pelo achado — e o porquê chega.** `ItemDeBriefing` ganha `why_now` e `next_step`
(preenchidos de `intelligence_findings` — 📊 12/12 e 11/12 — e, para os achados da 094, da 1ª/2ª frase do sumário
humano); `como_dict` os emite; `compor_pecas` (`workflows.py:160`) os desenha no `detail` do `actions`. `compor`
(`briefing_service.py:203`): quando `finding_type == "observacao"` e o sumário tem mais de uma frase, `headline` = a
1ª frase e `summary` = o resto. `_narrativa` (`:322`): com item acionável, **manchete = a headline do item de maior
prioridade** e resumo = a 1ª frase do summary dele + "e mais N ponto(s)" — N = os que FICARAM na peça
(`acionaveis[:max_itens]`; 📊 `:269` corta e `:314` conta a lista inteira: hoje a manchete promete pontos que a peça
não contém) — e, SÓ quando M > 0, "· M trabalho(s) pronto(s)"; crítico → "crítico:" na frente; o ramo
`weekly_executive` (`:318-321`) mantém a forma dele com a mesma regra do M; sem item → "Nada precisa de você hoje"
(+ "· M trabalhos prontos" só se M > 0). 🔴 Depois do D.5, M = 0 em 📊 5 de 5 dias medidos — a frase some, e o §0 não
promete mais "20 trabalhos prontos". `compor_pecas`: "Método" e
"Origem dos dados" vazios viram UMA linha no rodapé; "O que ainda não dá para afirmar" só com conteúdo (já).
`_gerar_artefato` grava `subject_ref` (`{"kind":"periodo","id": data, "label": "04/09", "produtor": "checklist-6h"}`)
e `data_as_of = period_end`.

**D.4 · Os títulos que mudam, e os guardas que mudam com eles.** 📊 `grep -rn "Pulso 360 ·\|O período inteiro\|esperando
você" backend/tests scripts lib components` → **0** (nenhum guarda fixa as strings velhas; os 8 hits são de produção,
todos em `app/` e no BLOCO A).

**D.5 · O briefing sem o relógio da plataforma.** `compor` recebe `trabalhos_em_curso` e `resultados` de `work_runs`;
passa a **excluir `source_type == 'system'`** (o tick olhando a própria operação: 📊 6 dos 14 itens de 04/09 eram
`detect_signals` repetido) e a **deduplicar** itens por `(headline, summary)` e Work Runs por `(outcome_title,
status)` com "(+N iguais)". Chave declarada (§3 ③). 📊 Medido no aquecimento (join por `item->>'work_run_id'`, presente em 57/57 itens): **40 de
41** itens `work_run`/`result` dos 5 últimos briefings vêm de Work Run `system` — 70,2% de todos os 57; depois do
filtro sobram **0** itens `result` em 5/5 dias, e `outcomes` também é 0. O filtro vive DENTRO de `compor` (é o que o
Gate [D5] testa), logo `source_type` entra no SELECT de `_trabalhos` (`briefing_service.py:566-581`, hoje `id,
outcome_title, status, progress_percent, result_summary, finished_at`). A seção "o que ficou pronto" desaparece quando
vazia (a regra das seções vazias). 📊 Esperado: itens duplicados 35,1% → 0; e o briefing encolhe de 11–14 para 3–6
itens — os que são da corretora.

**Gate D** — `backend/tests/test_o_relatorio_abre_pelo_achado.py`, com PARES e mutação por cópia:
```
[D1] todo kind de FINDINGS_QUE_VIRAM_SINAL tem playbook; achar_findings(pack golden) → todo achado com titulo/por_que_importa/o_que_fazer/
     pergunta não vazios; o título contém o NÚMERO do achado; zero nome de pessoa (regex + a fixture com nomes)   PAR: kind sem playbook → vermelho
[D2] _compor(pack golden com 3 achados) → blocos[0].title == titulo do mais severo; existe UM `actions` com 3 itens; métricas indisponíveis
     produzem ZERO callout individual e UMA prose; o pack serializado não contém `rotulos_de_produtor` nem nome (M16)  PAR: pack sem achado → título com a comissão
[D3] _narrativa(4 acionáveis) → manchete == headline do 1º; (0 acionáveis, 20 resultados) → "Nada precisa de você hoje · 20 …";
     como_dict emite why_now/next_step quando o finding os tem                                                    PAR: como_dict sem um deles → vermelho
[D5] compor com 4 work_runs `system` + 2 `chat` → só os 2 aparecem; 2 itens iguais → 1 item "(+1 iguais)"        PAR: `system` de volta → 6 → vermelho
     compor com 0 work_runs não-system → a frase "trabalho(s) pronto(s)" AUSENTE da manchete                     PAR: "0 trabalho(s)" impresso → vermelho
mutações por cópia: remover `titulo` do CONCENTRACAO → [D1] vermelho · `_compor` sem `actions` → [D2] vermelho · `_narrativa` contando → [D3] vermelho
```

# BLOCO E · O DETALHE — versões, fontes, perguntar (frontend)

`[artifactId]/page.tsx`: cabeçalho com **tipo humano · produtor · período** (do mapa único do A.2); banner "Peça
gerada por um teste do produto" quando `tags` tem `canario`; banner "Arquivado em {data}" quando `archived_at`
(a página passa a aceitar arquivado — hoje `notFound()`; só o dono da empresa, mesmo filtro). **Versões:** lista de
`artifact_versions` da peça (versão · data · "dados lidos em"/"período" quando `data_as_of` existe · atual/anterior);
`?versao={id}` abre o render HTML daquela versão (`.eq('artifact_version_id', versao).eq('company_id', empresa)`) e o
botão **Baixar** passa a apontar para `/arquivo?versao={id}` — `arquivo/route.ts` aceita `versao` e valida
`company_id` na versão (mutação: `?versao=` de outra corretora → 404). **A frase de frescor:** "Dados de {data_as_of}"
(`:217`) só quando `data_as_of` existe, e com o rótulo do tipo: "dados lidos em" (Pulso/Raio-X/Radar/Cobrança) ·
"período {label}" (briefing); as 136 versões antigas (carimbo de escrita) ganham "gerado em", nunca "dados de".
**De onde veio:** seção com `data_sources` (`label · detail · as_of`) e `confidence_note` quando houver. **Próximos
passos:** a página lê `payload->findings` da versão (só esse caminho do JSON; ⚠️ 📊 supabase-js 2.58 / postgrest-js 1.21 devolvem
a coluna pelo ÚLTIMO segmento: a linha chega como `{ id, findings }`, não `{ payload: { findings } }` —
`versao.payload?.findings` seria `undefined` e a seção ficaria vazia em silêncio; o guarda afirma a FORMA) e desenha os `o_que_fazer` com um botão
cada → `/dashboard/chat?pergunta={pergunta}`; e o botão **Perguntar ao AutoBrokers** → `/dashboard/chat?pergunta=Sobre
o relatório «{título}» ({id8}): `. No chat (SPEC-096 é dona do shell; aqui são 3 linhas + 1 prop — 📊 hoje `page.tsx:23`
lê só `session`, e `ChatShortcutCards` são dois `<Link>`): 🔴 **inicializador síncrono, nunca efeito** —
`useState(initialText ?? '')` lê a prop só na montagem, e um efeito chega tarde; `page.tsx` lê `?pergunta=` num
inicializador preguiçoso no molde do `sessionId` (`:21-27`). 🔴 **E o composer é REMONTADO:** `page.tsx:596-609`
monta `const composer` e o renderiza em duas posições da árvore (`:618` e `:645`, pelo ternário de `:614`); ao enviar a
primeira mensagem o `InputArea` desmonta, remonta e re-semearia a pergunta. Por isso o estado "já consumi" mora em
`page.tsx`, ACIMA da fronteira de remontagem: o efeito que já espelha a URL (`:31-38`) apaga `pergunta` e zera
`textoInicial`. `InputArea` (`components/InputArea/index.tsx:38`) ganha `initialText` → `useState(initialText ?? '')`.
**Nunca envia sozinho**: um Pulso custa 📊 162 s de InfoCap e uma versão nova.

**Gate E** (no `relatorios-dizem-o-que-sao.test.mjs`, blocos [9]–[11], por leitura da fonte + o padrão da 078 [4]):
toda leitura de `artifact_versions`/`artifact_renders` na página e na rota de arquivo com `company_id` (PAR); a rota
de arquivo honra `?versao=` (PAR: sempre a última → vermelho); a página não imprime "Dados de" (PAR: a string volta →
vermelho); o chat só pré-preenche: `page.tsx` não ganha efeito que chame `handleSendMessage`, e `textoInicial` é zerado
no primeiro envio (PAR: sem o zeramento → vermelho); a página lê `.findings` da linha, nunca `.payload.findings` (E5;
PAR: o caminho errado na fonte → vermelho); `payload` só é
lido pelo caminho `payload->findings` (PAR: `select('payload')` → vermelho — o payload carrega o evidence pack inteiro
e `rotulos_de_produtor`).

# BLOCO F · CANÁRIO VIVO + a limpeza + o dossiê (orquestrador)

`backend/scripts/canario_095.py` (NOVO — o builder do motor o escreve, com um modo `--simular` sobre o dublê para
provar a lógica sem rede; o orquestrador o roda ao vivo), que exporta `AUTOBROKERS_CANARIO=1` no próprio processo e
roda na Resulta o caminho REAL (`_publicar` de verdade, banco de verdade), na ORDEM (E11): **B.4 primeiro**
(`--dry-run` → `--aplicar` → VERIFY antes/depois colado — só depois de o BLOCO E estar no ar: 📊 hoje
`[artifactId]/page.tsx:121-124` faz `notFound()` em arquivado, e 35 links já entregues pelo `_link()` do chat apontam
para o DETALHE dessas peças); (a) "como estamos?" pelo caminho da tool → peça com `tags=['canario']`, título = achado,
`subject_ref.id = "2026"`, `data_sources` não vazio, `data_as_of` = hora da leitura; (b) a mesma pergunta de novo → o
MESMO `artifact_id`, `current_version = 2` (SELECT); (c) o briefing SEM gravar: `BriefingService.gerar` é idempotente
por período (`publicar` → `_publicacao_existente`) — gerar "hoje" devolve `reaproveitado` e gerar "amanhã" bloquearia o
tick real de 05/09; o script chama os leitores do serviço e `compor` + `compor_pecas` sobre os dados vivos da Resulta e
imprime: manchete = headline do item 1, itens com `why_now`/`next_step`, itens duplicados = 0, Work Runs `system` = 0,
e a frase de trabalhos ausente quando M = 0 — a primeira publicação REAL com a narrativa nova é a do tick de 05/09
08:00, e o relatório diz isso; (d) a rota da lista pelo guarda (dublê) e **ao vivo**: `next start` +
`GET /api/dashboard/entregas` (401 sem sessão: a rota executa código) + `npm run test:rotas-montam`; (e) os SELECTs de
prova colados no relatório; (f) o script arquiva o que criou (`arquivar`, pelos ids que ele mesmo guardou) — 📊 `select
count(*) from artifacts where tags @> '{canario}' and archived_at is null` → 0 ao fim.

**Dossiê:** página nova em `docs/canon/reports/dossies/dossies-autobrokers.html` — "095 · Relatórios que o corretor
entende" — que responde, em linguagem humana, o que o Founder perguntou em 04/09: o que é cada tipo de relatório
(Pulso 360 · Briefing do dia · Resumo da semana · Raio-X · Radar · Cobrança · Pesquisas), de onde vem o dado de cada
um, com que frequência aparece e por qual regra (tick, política de horário, sob demanda), por que ele via repetição
(1.1 + 1.2 + 1.4), o que mudou, e os números medidos. Republicada com `url`.

---

## 4. Os arquivos, por caminho

```
NOVOS       lib/relatorios/tipos.ts · app/api/dashboard/relatorios/placar/route.ts · components/relatorios/Placar.tsx ·
            backend/app/comercial/narrativa.py · backend/scripts/arquivar_relatorios_de_teste_095.py · backend/scripts/canario_095.py ·
            scripts/relatorios-dizem-o-que-sao.test.mjs · backend/tests/test_o_relatorio_abre_pelo_achado.py ·
            docs/canon/reports/SPEC-095-EXECUTION-REPORT.md
FRONTEND    app/api/dashboard/entregas/route.ts · app/dashboard/entregas/EntregasClient.tsx · app/dashboard/entregas/page.tsx ·
(1 escritor) app/dashboard/entregas/[artifactId]/page.tsx · app/dashboard/entregas/[artifactId]/arquivo/route.ts ·
            app/dashboard/entregas/rotina/[runId]/page.tsx (só o rótulo) · app/dashboard/atividades/page.tsx (1 linha: `?tipo=tudo`) · lib/navigation.ts (1 linha) ·
            app/dashboard/chat/page.tsx (3 linhas: inicializador + consumo no efeito da URL) · components/InputArea/index.tsx (1 prop)
BACKEND     backend/app/comercial/evidence_pack.py · backend/app/agents/tools/executive_intelligence.py ·
(1 escritor) backend/app/agents/tools/relatorios_comerciais.py · backend/app/services/artifacts/service.py ·
            backend/app/services/intelligence/workflows.py · backend/app/services/intelligence/briefing_service.py ·
            backend/app/services/routines/billing_collection.py (só produtor/data_as_of no subject_ref) · backend/app/agents/tools/listar_entregas.py (1 linha, `:180`)
DESENHISTA  os 2 guardas novos + package.json (1 script). Os 2 guardas da 078 ficam como estão e continuam verdes (📊 provado por mutação)
NÃO TOCAR   backend/app/services/intelligence/{schemas,finding_engine,signal_service}.py (o Fabric não muda: a 094 só o LÊ) ·
            backend/app/comercial/metricas/* (nenhuma métrica nova) · app/r/[token]/route.ts (link público: fora) ·
            backend/app/services/artifacts/{blocks,render,styles}.py (nenhum bloco novo) · services/skills/* (F-094.1-01) ·
            backend/tests/test_menu_nao_cresce.py · backend/tests/test_navegacao_sem_pagina_orfa.py (ficam como estão e têm de passar)
```

## 5. 🔴 O QUE SAIU da proposta — e o gatilho que faz voltar

```
Compartilhar por link (modos FROZEN/LIVE, senha, max_views, download)  → 📊 shares = 0; ninguém pediu. VOLTA quando a 1ª corretora
                                                                          pedir "manda o link para o cliente" ou o atendimento ligar (086)
Enviar por canal + delivery ledger (attempt, receipt, SENT≠DELIVERED)  → ⛔ nada envia nesta leva; o único canal é o painel (1.8).
                                                                          VOLTA com o 1º envio real (piso CRÍTICO da §3.2)
PDF / XLSX / CSV                                                        → 📊 sem renderizador no contêiner; "Abrir em nova aba" + Ctrl+P já
                                                                          gera PDF pelo CSS de impressão. VOLTA quando o Founder ou uma
                                                                          corretora pedir arquivo (Playwright entra no worker, não na API)
Busca no servidor + paginação por cursor + FTS                          → 📊 400 linhas no máximo, 130 peças/corretora, 1,2 ms por consulta.
                                                                          VOLTA com > 1.000 linhas por corretora ou uma busca que não achou (medida)
Favoritos · Recentes por usuário · "Arquivados" como aba                → preferência por usuário sem tabela; a Notion removeu a aba (§3 ⑤).
                                                                          VOLTA com > 200 peças/corretora
Restaurar / comparar versões                                            → 📊 nunca existiu uma v2. VOLTA quando a 1ª peça com 3+ versões precisar
Sensibilidade / ACL por papel (financeiro, sinistro)                     → é da SPEC-098 (cada coisa sabe de quem é)
Engajamento (raw/qualified, bot, viewer history)                        → depende de share. VOLTA com ele
Producer lineage por coluna (producer_kind/ref)                         → zero migration nesta SPEC; `subject_ref.produtor` cobre o novo,
                                                                          `legacy_inferred` rotula o velho. VOLTA na 1ª migration do Hub
Orphan output detector · observabilidade (métricas do Hub)              → o placar é a metade "quanto fez"; a metade "quanto não chegou" volta
                                                                          com o delivery ledger
Nova lente "Atividade" separada de "Resultados"                         → o Founder disse que a aba Trabalhos está boa; a lente padrão
                                                                          Relatórios já separa. Não cria
"data_as_of ou not_applicable" (§107)                                   → substituído: o campo vira NULL quando ninguém sabe a data (1.9)
```

## 6. Pendências que esta SPEC toca (regra de drenagem, §2 do protocolo)

```
P-094.1-LINK-PUBLICO      CONTINUA — shares fora (§5); o link do chat segue autenticado
P-094.1-LATENCIA          CONTINUA — 162 s por Pulso; esta SPEC não toca o adapter (e por isso "Perguntar" nunca envia sozinho)
P-094.1-CANARIO-094-RECUSA CONTINUA — o guarda ganha a variável de canário, não o isolamento do registro
NOVA  P-095-CANARIO-PROTOCOLO  🤖 o pacote do juiz/canário (docs/canon/pacotes) passa a exigir AUTOBROKERS_CANARIO=1 — 1 linha
NOVA  P-095-NARRATIVA-DO-FABRIC 🤖 `commercial_opportunity` não tem Narrativa própria no Fabric: o finding nasce "Ponto de atenção /
                                observacao" (📊 3/3 na Resulta). O briefing contorna (D.1); a Central não. Destrava: 3 signal_type + 3 Narrativas (SPEC-059)
NOVA  P-095-DATA-AS-OF-LEGADO  🤖 136 versões antigas com `data_as_of` = carimbo de escrita (imutáveis); a tela as chama de "gerado em"
NOVA  P-095-SEARCH             🤖 busca no servidor por gatilho (§5)
NOVA  P-095-PDF                🧑 renderizador de PDF por gatilho (§5)
NOVA  P-095-TICK-OLHA-953-VEZES 🤖 `intelligence.detect_signals` rodou 953× para 32 sinais na Resulta (📊 1.10) — cadência do tick para a SPEC-097
NOVA  P-095-TRABALHO-PRONTO    🤖 o briefing só conhece `work_runs` como "trabalho pronto"; execuções de rotina/auxiliar ("Cobrança Feita rodou") não
                                entram — com o relógio fora, M = 0 em 5/5 dias. Destrava: `_trabalhos` ler `routine_runs`/`auxiliary_runs` (SPEC-097)
```

## 7. 🧑 A caixa do Founder (o executor acrescenta)

```
1  A URL continua /dashboard/entregas; só o NOME vira Relatórios. Trocar a URL custaria 4 redirects + links já entregues pelo chat + 2 guardas.
2  35 relatórios de teste (34 Resulta + 1 AutoFleet) serão ARQUIVADOS pelo B.4 — visíveis em "ver arquivados", reversíveis por um UPDATE
   com o evento como registro. Se algum deles for pergunta SUA, diga: o script lista antes de aplicar.
3  O placar conta o que a corretora pediu e recebeu (📊 Resulta: ≈580 na vida). Ele NÃO conta as 1.214 voltas do relógio da plataforma:
   contar mentiria por 87× e seria exatamente a "enchição de linguiça" que você recusou.
4  "Perguntar ao AutoBrokers" toca 2 linhas do chat; a SPEC-096 (shell do chat) herda o gancho.
5  O briefing continua saindo só no painel (1.8), às 08:00, igual nas três corretoras. WhatsApp/e-mail do briefing é decisão sua e entra com o
   delivery ledger (§5). E o horário por corretora é do perfil de briefing — hoje ninguém o mudou.
6  "Dados de 4 de setembro, 02:55" era a hora da escrita, não do dado, em 136/136 peças. Some; volta só quando quem publicou souber a data.
7  Os "20 trabalhos prontos" da manchete de 31/08 eram o relógio da plataforma (📊 40 de 41 itens de trabalho dos 5 últimos briefings são
   `intelligence.detect_signals`). Com o relógio fora, a frase SOME quando não há trabalho pedido — e a Resulta terá M = 0 até uma rotina
   rodar. Se preferir ver "Cobrança Feita rodou" como trabalho pronto, é a P-095-TRABALHO-PRONTO (SPEC-097).
8  O placar de "trabalhos pedidos" mostra 14 na Resulta e 0 nas outras duas — e os 14 são execução de SPEC (081 e 094.1). É verdade e é
   pouco: o número cresce quando o chat e as rotinas forem usados de verdade. Os outros contadores (conversas, relatórios, sinais) já têm chão.
```

## 8. O gate final da SPEC

```
GATE ZERO ......... 7 vermelhos provados em 5c22590 pelo guarda, verdes no fim
GUARDAS ........... relatorios-dizem-o-que-sao (≥ 11 blocos com PAR) · test_o_relatorio_abre_pelo_achado (D1–D5 + B) · os 2 da 078 migrados verdes ·
                    canário 094 verde com a variável · menu-não-cresce e navegação verdes sem mudar · protocolo (test_o_protocolo_tem_policia) verde
RED TEAM .......... 1 lente, contexto limpo, sobre o diff: cross-tenant (lista, placar, ?versao=, payload->findings) · identidade que colide
                    (mesmo período, templates diferentes; mesmo template, corretoras diferentes) · nome de pessoa no título · canário sem variável ·
                    placar com `system` · `data_as_of` voltando a now() · efeito do chat que envia · briefing com Work Run `system`
ORDEM ............. E no ar ANTES de B.4; B.4 ANTES do canário que publica (E11)
CANÁRIO VIVO ...... `canario_095.py`: B.4 → (a)(b) → (c) sem gravar → (d) → (e) → (f); SELECTs colados; nenhuma peça `canario` viva ao fim
ROTAS ............. test:rotas-montam + next start + 1 GET a /api/dashboard/entregas
SUÍTE ............. inteira 1× com a árvore parada; contagem do conftest no relatório
ENTREGA ........... git push origin <sha>:main com a saída colada; INDICE, dossiê (republicado), memória, prompt da 096 preenchido
```
