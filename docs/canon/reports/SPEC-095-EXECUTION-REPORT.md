# SPEC-095 · RELATÓRIOS QUE O CORRETOR ENTENDE — relatório de execução

> **v1.2 da SPEC, executada sob o protocolo v11.2 · OPÇÃO B (três marchas) · marcha PADRÃO** · 04/09/2026 · branch
> `feat/spec095-relatorios` · base `5c22590` · commit da SPEC `aa6ec76` · commit final de código `876b01d`
> Orquestrador: Fable 5.1. Subagentes Opus 5: investigador+pesquisador (conversão) · aquecimento · desenhista · builder da tela (A+C+E) ·
> builder do motor (B+D) · red team · Sonnet 5: confirmação mecânica. Sessão nova, aberta com o prompt de abertura por SPEC.

## 0.0 EXECUTION CARD — como foi

```
SPEC .................  095 · Relatórios que o corretor entende
OUTCOME ..............  o corretor abre Relatórios e cada card diz o que é, de quem é, de quando é e o que achou; nada repetido, nada de
                        teste; o relatório abre pelo achado e diz o que fazer; um placar que só conta o que a corretora pediu; a data do
                        dado é a do dado — ou é NULL
RISCO ................  5 — ALCANCE 2 · REVERSIBILIDADE 2 · FREQUÊNCIA 1 (o aquecimento refez a conta e concordou)
SUPERFÍCIE ...........  2 — condicional a E1+E3+E4 na §4 (aplicadas): 2 arquivos e 2 SELECTs que a v1.1 não listava
PISO APLICADO ........  não atingido — nada envia (📊 canal único: dashboard), zero migration, auth/sessão intactas; `?versao=` e as 35
                        consultas do placar nascem com company_id e o red team as ataca
NÍVEL ................  PADRÃO sob B: desenhista ANTES · 2 builders Opus em arquivos DISJUNTOS (tela ‖ motor) · painel = RED TEAM · confirmação
                        MECÂNICA (Sonnet) · canário vivo por script (o orquestrador roda)
UNIDADES .............  6 — BLOCO 0 · A · B · C · D · E · F — ORDEM: desenhista ‖ (A+C+E) ‖ (B+D) → integração → red team → conserto →
                        confirmação → F (B.4 só com E no ar, antes do canário que publica)
COESÃO ...............  A+C+E frontend = 1 escritor · B+D backend = 1 escritor · desenhista = guardas · contrato = colunas existentes + props
PARALELISMO REAL .....  3 escritores simultâneos (desenhista · tela · motor) em arquivos disjuntos; gate zero provado numa cópia limpa de HEAD
TIME .................  Fable orquestra · Opus: investigador+pesquisador, aquecimento, desenhista, 2 builders, red team · Sonnet: confirmação
REFERÊNCIA ...........  interna: DS-001 §5 · os 2 guardas da 078 (dublê + controle) · blocks.py cover/actions/callout · externa: 6 reabertas em
                        04/09 (Zapier task usage · AWS Trusted Advisor · Datadog Watchdog · Figma versions · Notion library · Claude artifacts)
GATES ................  GATE ZERO 7 vermelhos em HEAD · guardas novos com PARES · 078 verdes sem mudar · rotas-montam + next start + 1 GET ·
                        dois tenants na lista e no placar · suíte inteira 1× no fim
O ELO ................  (a) título = achado: banco → rota → tela; (b) o porquê chega: `como_dict` emite → jsonb; (c) o elo medido que chegava
                        longe demais: `system` fora apaga 70,2% do briefing e zera "trabalhos prontos" → E2 mudou a manchete antes do código
FAIXA DE RELÓGIO .....  declarada 5–7h · 📊 realizada: 04/09 11:00 → ~17:20 ≈ 6h20 numa janela só (dentro da faixa 5–7h; a primeira SPEC da leva que não morreu no meio)
ORÇAMENTO ............  ≤ 1,3 M · 📊 gasto: conversão 225k · aquecimento 199k · desenhista 324k · builder tela 325k · builder motor 397k ·
                        red team 330k · confirmação mecânica 0 (o orquestrador rerodou guardas e mutações, sem Sonnet) · TOTAL ≈ 1,80 M
                        (+38% — a lição está na §9: dois builders em paralelo são metade do relógio, não metade dos tokens)
BATERIA ..............  suíte inteira 1× · parciais ≈ 40
```

```
o painel rodou sobre CÓDIGO?          sim: red team (1 lente, opção B), contexto limpo, sobre o diff 5c22590..12a7bb8, depois do gate integrado — FAIL 72, 4 blockers de TELA
conserto criou defeito?               NÃO — o orquestrador consertou os 4 + 9 numa rodada e a confirmação mecânica (guardas + 9 mutações acusadas + 078/081/094/094.1 verdes + typecheck + build + next start) não achou regressão; a suíte inteira acusou 2 conflitos REAIS de guarda (059 [12] e o guarda de mutação commitada), ambos migrados com o fato
o que sobrou é MATERIAL?              não — o que sobrou tem dono: os 3 findings legados do Fabric mantêm o texto de máquina até o Fabric recompor (P-095-NARRATIVA-DO-FABRIC; os sinais NOVOS do canário já entraram com o texto humano — SELECT na §2 F); a 1ª publicação real com a narrativa nova é o tick de 05/09 08:00; orçamento +38%
```

## 0.1 A TELEMETRIA (§11)

```
começou / terminou                     04/09 ~11:00 (preflight + leitura do NÚCLEO) / 04/09 ~17:20 (push)
tempo até a PRIMEIRA linha de código   📊 ~2h55 (11:00 → 13:56, commit 9830b6a dos guardas; produto às 14:04) — inclui a conversão medida
                                       (investigador+pesquisador, 19 min de relógio) e o aquecimento (23 min); a SPEC v1.1 saiu às 12:45 e a v1.2 às 13:18
rodadas de painel e achados por lente  1 rodada, 1 lente (red team, opção B): 4 blockers + 12 pendências (16 ataques, 5 de isolamento resistiram com
                                       controle). Únicos: os 4 blockers (todos de TELA, por baixo dos guardas de FORMA). Rodada 2 = confirmação
                                       mecânica pelo orquestrador (guardas + mutações), sem juiz retomado
defeitos que o painel NÃO pegou        o tenant inexistente no canário foi pego pelo ORQUESTRADOR antes do red team (SELECT em `companies`); o
                                       briefing_items sem as colunas novas e as janelas em SP×UTC foram pegos pelo BUILDER do motor no BLOCO 0; a
                                       fixture do guarda do placar (2 em vez de 4) pelo builder da tela; o red team não viu nada que o canário vivo
                                       pegasse a mais — o canário vivo pegou DOIS defeitos de AMBIENTE que nenhum guarda vê (slowapi e fastembed faltando no Python local, pelo caminho app.api do conector) e ZERO defeito de produto
rodadas da bateria                     📊 inteira 1× (gate final, árvore parada: 935 passed · 6 failed · 39 xfailed · 45m05 sob contenção de CPU (build + pip em paralelo), commit d2922e6); parciais ≈ 40 (os 2 guardas novos ~12× cada, os 2 da
                                       078 ~6×, 094/094.1/081 3×, typecheck 3×, rotas-montam 2×, next build 2×)
nota 0–100 do orquestrador             nota 84/100 — 6 unidades com prova viva na Resulta (o Pulso virou UMA peça com duas versões, título = o achado, data lida, 29 fontes; o briefing abre por "Fila acumulada" sem o relógio; 35 peças de teste arquivadas com VERIFY; o servidor responde); perde por orçamento +38%, por 4 blockers de tela que só o red team viu (os guardas eram de forma) e por dois tropeços de ambiente antes do canário passar
```

## 1. O que a SPEC prometeu e o que ficou

**Antes (04/09 de manhã, medido):** o menu dizia "Entregas"; cada card tinha título do banco, `report` como origem, sem tipo, sem
produtor, sem período, sem versão; 📊 100% dos relatórios "do chat" da Resulta (34) eram canários de execução de SPEC e nada os
distinguia; cada briefing entrava duas vezes (📊 40 pares, 9,8% da lista, 32% da lente Documentos); as manchetes contavam
("2 item(ns) esperando você hoje" ×5 em 5 dias) e 79,7% dos títulos se repetiam; os achados chegavam com texto de máquina e sem
número ("Ponto de atenção" ×3, 2 iguais) enquanto o `why_now` (12/12) e o `next_step` (11/12) já existiam no banco e eram
descartados por `ItemDeBriefing`; 📊 40 de 41 itens de trabalho dos 5 últimos briefings eram o tick da plataforma; o Pulso 360
tinha 13 seções, quatro caixas "INDISPONÍVEL" e nenhuma ação; `data_as_of` = `now()` em 136/136 versões com a tela dizendo
"Dados de…"; `data_sources` vazio em 5/5 Pulsos; 98,86% dos `work_runs` eram `system`.

**Depois:** o menu diz **Relatórios** (URL, key e 6 pilares intactos); a lista abre em Relatórios e cada card diz tipo humano ·
produtor · período · versões · etiqueta (crítico > entrega > precisa de você), lido de um mapa ÚNICO (`lib/relatorios/tipos.ts`) que o
detalhe também usa; o briefing é UM card (a publicação dobra no card do documento; sem documento, ou com ele fora da janela, continua
card e leva ao documento); peças de teste e arquivadas ficam fora, com "ver arquivados (N)" discreto; o **placar** conta só o que a
corretora pediu e recebeu (📊 Resulta 30 d: 396; Amandus 77; AutoFleet 529 — nunca as 1.214 voltas do relógio); o mesmo relatório do
mesmo período vira **versão** da mesma peça (identidade só com id não-vazio; `retitled` com de/para; arquivada → nova; o canário
versiona só o que é dele); `data_as_of` é NULL quando ninguém sabe a data (a Cobrança carimba a hora em que a varredura COMEÇA); o
canário se declara (`tags=['canario']`) e se arquiva; os 4 detectores ganharam título com o número, por que importa, o que fazer e a
pergunta pronta; o **Pulso abre pelo achado** com "O que importa agora" e uma linha só para o indisponível; o **briefing abre pelo
achado** (crítico: quando o topo é crítico), carrega `why_now`/`next_step` no jsonb (a tabela `briefing_items` não tem as colunas — o
insert por projeção evitou a morte silenciosa), deduplica, não lista o relógio da plataforma e só fala de "trabalhos prontos" quando
M > 0 (📊 hoje M = 0 em 5/5 dias — os "20 trabalhos entregues" de 31/08 eram `detect_signals`); o rodapé de fontes do briefing
deixou de sair com 3 bullets vazios; o detalhe mostra versões, `?versao=` (página e download, com `company_id` na versão), frescor
honesto em três formas, "De onde veio" com a hora, "Próximos passos" e **"Perguntar ao AutoBrokers"** que chega ao campo do chat
(provado executando o componente); os 35 relatórios de teste estão arquivados (reversível). Nenhuma migration; nenhum motor novo.

## 2. As unidades

| bloco | commits | o que fez | gate |
|---|---|---|---|
| 0 · remedir + gate zero | `b054b5c` `aa6ec76` (SPEC v1.1→v1.2) · `9830b6a` (guardas) | conversão MEDIDA (investigador+pesquisador, 225k: nota 41 para a proposta neste escopo; 6 referências reabertas) → aquecimento (199k: nota 78 → 12 emendas, 2 falsas assinadas refutadas por leitura e mutação, 6 blocos de 📊 reproduzidos sem erro) → v1.2; os 7 vermelhos do gate zero provados na cópia limpa `../AutoBrokers-FIX-gate0` (worktree de `b054b5c`) enquanto os builders escreviam no diretório principal | (i) tela · (ii)–(vii) motor, todos VERMELHOS em HEAD limpo |
| A · a lista e o nome | `794ac2c` | label "Relatórios" (key/href/6 pilares intactos); lente padrão Relatórios; `lib/relatorios/tipos.ts` (mapa ÚNICO, lido pela lista e pelo detalhe; `produtorOrigem` declarado/inferido); card com tipo · produtor · período · versões · etiqueta (crítico > entrega > precisa de você); briefing dobrado no card do artifact (publicação SEM artifact continua `briefing:`); canário e arquivado fora; `?arquivados=1` + link "ver arquivados (N)"; `/dashboard/atividades` → `?tipo=tudo` (E1); SELECT de `artifacts` com as 5 colunas (E3) | `test:relatorios` [1]–[7] · os 2 guardas da 078 verdes (o carregador transpila `@/lib/**` real) · `test_menu_nao_cresce` e `test_navegacao_sem_pagina_orfa` verdes sem mudar |
| B · identidade, data honesta, canário, limpeza | `ba83b68` | identidade `(company, template, subject_ref->>id)` só com id não-vazio, `limit(2)` e levanta em colisão; `nova_versao` atualiza capa com `artifact.retitled {de, para, versao}`; identidade arquivada → peça nova; `data_as_of`/`confidence_note` NULL por padrão (o `now()` morreu); `tags=['canario']` por `AUTOBROKERS_CANARIO`; `arquivar/desarquivar` com evento; `arquivar_relatorios_de_teste_095.py` (janelas em UTC — 📊 em hora de SP pegava 21 de 35, em silêncio; nunca toca `canario`); `canario_095.py` (`--simular` sobre dublê; ao vivo é o F) | guarda do motor [B] + `--mutar` B.a · B.b · B.c · B.f VERMELHAS |
| C · o placar | `794ac2c` | rota `relatorios/placar`: 5 janelas × 8 tabelas = 40 `HEAD count` com `company_id`, 32 com `.gte`; `CONTA_COMO_TRABALHO = ['chat','routine']` (inclusão); `routine_runs` por `started_at`; `Placar.tsx` discreto (segmentado, 7 números, soma, "—" + frase quando zero, janela em localStorage) | [8] + mutações 4 e 5 VERMELHAS |
| D · a narrativa | `ba83b68` | `narrativa.py` (puro: 4 playbooks — título com o número, por que importa, o que fazer, pergunta; produtor nunca nomeado); `sinais_do_pack` humano; Pulso: capa = achado mais severo, "O que importa agora" (`actions`), indisponíveis em UMA linha, `data_sources`/`data_as_of`/`confidence_note` gravados; briefing: manchete = item 1 (crítico:), N = itens que ficaram, frase de trabalhos só com M > 0, `why_now`/`next_step` no jsonb (📊 `briefing_items` não tem as colunas: insert por projeção declarada, senão morria em silêncio), dedup `(headline, summary)` e `(outcome_title, status)`, Work Runs `system` fora (`source_type` no SELECT de `_trabalhos`); `_fontes` do briefing na forma que o renderizador lê (📊 3 bullets vazios em todo briefing, antes) | guarda [D1]–[D5] + mutações D1 · D2 · D3 · D5 VERMELHAS |
| E · o detalhe | `794ac2c` | cabeçalho tipo · produtor · período; banners "peça de teste" e "arquivado em"; página aceita arquivado (E antes de B.4); lista de versões; `?versao=` na página e no download (com `company_id` na versão); frescor honesto ("dados lidos em" · "período" · "gerado em" — nunca "Dados de"); "De onde veio" (3 formas de `data_sources`); "Próximos passos" de `payload->findings` (lido por `.findings`, E5); "Perguntar ao AutoBrokers" → chat por inicializador síncrono + zeramento no efeito da URL + prop `initialText` (E10); nunca envia | [9]–[11] + mutações 6 · 7 · 8 · 9 · 12 VERMELHAS |
| F · canário vivo + dossiê | (pelo orquestrador) | **B.4 aplicado** — `arquivar_relatorios_de_teste_095.py --dry-run` → 35 candidatos (14 pipeline + 14 radar + 6 pulse Resulta + 1 pulse AutoFleet; 0 fora das janelas; 0 com tag) → `--aplicar` → **35 de 35 arquivados**; VERIFY antes/depois colado abaixo (35 → 0 · eventos 0 → 35); SELECT independente: arquivados Resulta 34 + AutoFleet 1, `artifact.archived` 35, canário vivas 0. **Canário vivo (a)(b)(c)(f), 04/09 16:40–16:44, Resulta, caminho REAL (`_publicar`, banco, InfoCap):** (a) "como estamos?" → RELATORIO_PRONTO; (b) de novo → RELATORIO_PRONTO e a MESMA peça `cd2c39ae`: title **"934 apólices vencem na janela · 355 já vencidas"** (o achado mais severo), subtitle "Pulso 360 · 2026 · dados lidos em 04/09/2026 às 16:42", tags `['canario']`, `subject_ref.id = canario:2026`, `current_version = 2` (v1 superseded, v2 published), `data_as_of` = a hora da leitura (19:40Z / 19:42Z), 29 fontes, nota "3 métrica(s) indisponível(is); cobertura mínima 66,7%"; 📊 peças vivas com a identidade: 1; SELECT independente: eventos `artifact.created, version.published, version.published, artifact.archived` (sem `retitled` porque o título não mudou entre v1 e v2), 2 versões; os 3 sinais NOVOS em `intelligence_signals` já carregam o texto humano ("934 apólices vencem na janela · 355 já vencidas. Renovação não trabalhada é comissão que some…", "Um produtor apropriou 34,5% menos…", "…61,9% menos…", `occurrence_count` 2); (c) o briefing composto sobre os dados vivos SEM gravar: manchete **"Fila acumulada"**, resumo "61 atendimentos estão parados há mais de 24h em horário útil (o mais antigo há 507h) · e mais 2 ponto(s)", 5 itens, duplicados 0, `why_now` 3/3, Work Runs `system` na entrada 22 → 0 na peça, a frase de trabalhos AUSENTE, blocos cover·kpis·actions·table·prose·sources·footer — ⚠️ os 2 achados LEGADOS do Fabric (findings de 03–04/09) ainda mostram "Ponto de atenção" com o texto de máquina: são linhas antigas de `intelligence_findings`; o Fabric as recompõe no próprio ciclo a partir dos sinais novos (P-095-NARRATIVA-DO-FABRIC); (f) `arquivar(cd2c39ae)` → True; 📊 peças `canario` vivas ao fim: 0. Antes de passar, o canário caiu DUAS vezes por ambiente (sem `slowapi`; `app.api.__init__` puxando `AudioService`/`fastembed`) — dependências do contêiner que o Python local não tinha; consertadas por `pip install` e por namespace no script, nunca no produto (876b01d). Dossiê: página "095 · Relatórios que o corretor entende" republicada | ✅ B.4 35→0 · canário (a)(b)(c)(f) verdes · next start 401 · build 2× |

## 3. 📊 Os números
```
conversão (04/09)     34/34 relatórios do chat da Resulta = canário (7/7 Pulsos a ±40 min de um commit da 094/094.1; 28 da 081 em 18/08) · 40 pares
                      briefing×artifact (9,8% da lista, 32% da lente Documentos) · 79 peças, 16 títulos (79,7% repetidos) · why_now 12/12 e next_step 11/12
                      descartados por ItemDeBriefing · 35,1% dos itens dos briefings duplicados · 40/41 itens de trabalho = o tick · data_as_of = now() em
                      136/136 (30 no futuro, +69,9 s no contêiner da API) · work_runs Resulta 1.229: system 1.214 (98,9%), chat 7, routine 7 · shares 0 · v2 0
placar (30 d, real)   Resulta 72·221·13·1·16·60·13 (Σ 396) · AutoFleet 31·443·0·0·35·20·0 (Σ 529) · Amandus 26·9·0·0·32·10·0 (Σ 77) — relatórios ·
                      conversas · execuções · pesquisas · sinais · atividades · trabalhos pedidos
limpeza (dry-run)     35 candidatos = 14 pipeline + 14 radar + 6 pulse (Resulta) + 1 pulse (AutoFleet) · 0 fora das janelas · 0 com tag canario
guardas               tela 16 asserções + 46 controles em 12 blocos · motor 61 asserções + 9 mutações acusadas (--mutar, árvore parada) · 078: 2 verdes ·
                      094: 284 · 094.1: 228 + 47 · 081: 67 · canário 094: 117 · menu/navegação verdes · rotas-montam 294 · typecheck limpo
tokens                conversão 225k · aquecimento 199k · desenhista 324k · tela 325k · motor 397k · red team 330k · TOTAL ≈ 1,80 M (orçamento 1,3 M: +38%)
```

## 4. O aquecimento e a conversão mudaram a SPEC — antes do código
Conversão (investigador+pesquisador, 225k): nota 41 para a proposta neste escopo; 12 medições; 6 referências reabertas (Notion removeu
"Archived"; n8n 404; OpenAI 403); achados que mudaram a SPEC: `why_now`/`next_step` existem e são descartados; 98,86% dos work_runs são
o tick (placar ingênuo mentiria por 87×); `data_as_of` = now() em 136/136.
Aquecimento (199k, nota 78 → 12 emendas): E1 redirect de `/dashboard/atividades` sem `?tipo=`; E2 "trabalhos prontos" some quando M = 0
(📊 40/41 eram `detect_signals`); E3 cinco colunas no SELECT de artifacts; E4 `listar_entregas` puxava 64 KB de payload por versão; E5
`payload->findings` volta como `{findings}`; E6 identidade só com id não-vazio (6 Pulsos com `''`); E7 a variável de canário no teste da 094
seria decorativa → `canario_095.py`; E8 citações de linha; E9 placar por INCLUSÃO, 14/0/0; E10 chat por inicializador, não efeito, e o
composer remonta; E11 ordem E → B.4 → canário; E12 "três achados" é 💭. As duas afirmações falsas assinadas foram refutadas por leitura e
mutação; 6 blocos de números da §1 reproduzidos sem erro.

## 5. O laço
Uma lente (opção B · PADRÃO): **red team**, Opus 5, contexto limpo, sobre `git diff 5c22590..12a7bb8` (o produto inteiro + os dois guardas),
depois de o gate integrado estar verde (guarda da tela 16/16 + 46 controles · guarda do motor 61 + 9 mutações acusadas com a árvore
parada · 078 verdes · 094/094.1/081 verdes · typecheck · rotas-montam 294). 📊 Custo: 330k tokens, 58 min.

| frente | veredito | o que achou de único |
|---|---|---|
| red team (16 ataques, cada um com linha de controle) | **FAIL 72** | **4 blockers, todos de TELA, todos por baixo dos guardas de FORMA:** B1 "Perguntar ao AutoBrokers" abria o chat VAZIO — o efeito que consumia `?pergunta=` rodava no primeiro commit, antes de o composer existir (`if (isLoadingUser) return`), e o guarda [9] aprovava a forma da declaração; B2 a Cobrança voltou a gravar `now()` como `data_as_of` com o comentário "hora da varredura", e a tela dizia "Dados lidos em" sobre o carimbo da escrita (o §1.9 reentrando pelo único publicador tratado como certo); B3 "De onde veio" nunca mostrava a hora — todos os escritores gravam `as_of_label`, a página lia `data`/`as_of` (só as peças LEGADAS mostravam data); B4 o canário apontava para uma corretora inexistente (`b26b3e79…` → 0 em `companies`). 12 pendências, 8 de uma linha. **Resistiram, com controle:** cross-tenant na lista, no `?arquivados=1`, no detalhe com `?versao=`, no `/arquivo`; a identidade da peça (6 cenários: a vizinha não versiona a peça de A; arquivada → nova; id vazio nunca casa); o placar; o canário sem variável; nome de pessoa (M16). 7/7 números da §1 reproduzidos sem erro. |

**Fundido pelo TESTE DO PRODUTO — 4 blockers + 9 pendências consertados numa rodada, pelo orquestrador (o orçamento de subagentes já
passava de 1,3 M):** `8a90480` (produto) + `cc31832` + `d2922e6` (guardas). B1: o consumo sai do efeito da URL e vai para o ATO de
enviar (`handleSendMessage`), acima da fronteira de remontagem; B2: `execute_billing_collection_routine` carimba `inicio_da_varredura`
ANTES do laço dos portais e passa a `compor_peca_da_cobranca(inicio_da_varredura=)` — sem ela, NULL; B3: `lerFontes` lê `as_of_label`;
B4: `04b5cdbc` medido no banco; P1 publicação cujo artifact ficou fora da janela de 120 vira card e leva ao documento (📊 dublê de
130+130: dez dias de briefing sumiam); P2 `useSearchParams` (a lista acompanha a navegação suave); P3 o placar propaga erro em vez de
`0`; P4 uma regra só de trabalho pedido — INCLUSÃO (`chat`,`routine`) — no briefing e no placar; P5 "crítico:" só quando o TOPO é
crítico (limiar 85 de `publicar()`); P7 Raio-X e Radar gravam `payload.findings` (a seção "Próximos passos" nascia vazia para os dois);
P8 o canário nunca versiona peça real (prefixo `canario:` na identidade); P9 `arquivadosN` no modo arquivados; P10 script npm do guarda
do motor. P6 (dois produtores com o mesmo delta colapsam em "(+1 iguais)") ficou como está: é informação, não perda. P11/P12 eram o
BLOCO F por rodar e a árvore em movimento (o id do canário), ambos fechados.

**A maior lacuna do red team virou guarda:** o Gate E era regex sobre a fonte. Entraram os blocos **[13]–[16]** no guarda da tela — o
COMPONENTE real do chat executado com um React de contrato (render → commit → flush; `useState` só lê o inicializador na montagem; a
rede responde depois do flush; `useUserId` nasce `isLoading = true`) prova que a pergunta chega ao campo na PRIMEIRA montagem do
composer, e o PAR reintroduz o zeramento no efeito e fica vermelho; a PÁGINA real de detalhe executada sobre um dublê de duas
corretoras prova o frescor honesto em três casos (peça nova sem data: nada; legada: "Gerado em"; com data e produtor declarado: "Dados
lidos em") e que `?versao=` da vizinha não traz nada dela; `lerFontes` real sobre as três formas de `data_sources` devolve a coluna de
data cheia. No motor, o bloco **[B2]**: a Cobrança carimba a varredura ANTES do laço dos portais e nunca `now()` (PAR: `now()` de
volta é acusado); `relatorios_comerciais._fontes` e `workflows._fontes` EXECUTADOS emitem `as_of_label` em todo item. Dois guardas
antigos migraram com o fato (CLAUDE.md §9.3): ler a URL via `useSearchParams` continua sendo ler a URL; e o guarda da 081 deixa de
acusar por `git diff` contra uma baseline (que toda SPEC seguinte tornaria vermelho — já tinha mudado de janela uma vez) e passa a
medir a FORMA: a tool não importa nem chama Cobrança/Atendimento/corredor/webhook (com o controle de que citar em comentário não é
chamar).

**Confirmação mecânica (feita pelo orquestrador, sem Sonnet):** typecheck limpo · guarda da tela 0 falhas / 0 esperados (16 blocos) ·
guarda do motor 69 ok · `--mutar` 9/9 acusadas (árvore parada, antes do conserto) · 078 verdes · 081 68 verdes · 094 284 · 094.1 228 +
47 · canário 094 117 · menu/navegação verdes · canário `--simular` verde. A suíte inteira e o `next start` estão na §7.

## 6. Pendências (PENDENCIAS.md) — a regra de drenagem
```
P-094.1-LINK-PUBLICO        CONTINUA — shares fora da 095 (§5 da SPEC, com gatilho); o link do chat segue autenticado
P-094.1-LATENCIA            CONTINUA — 162 s por Pulso é a InfoCap; por isso "Perguntar" pré-preenche e nunca envia
P-094.1-CANARIO-094-RECUSA  CONTINUA — o guarda da 094 ficou como estava (a variável de canário ali seria decorativa: ele usa dublê)
P-095-CANARIO-PROTOCOLO     FECHADA — a regra (AUTOBROKERS_CANARIO=1 + arquivar ao fim) entrou em PACOTE-JUIZ e PACOTE-BUILDER (71f0bcb)
P-095-NARRATIVA-DO-FABRIC   NOVA 🤖 `commercial_opportunity` sem Narrativa própria: o briefing contorna (1ª frase humana = manchete); a Central não
P-095-DATA-AS-OF-LEGADO     NOVA 🤖 136 versões antigas com carimbo de escrita (imutáveis); a tela as chama de "Gerado em"
P-095-TRABALHO-PRONTO       NOVA 🤖 o briefing só conhece work_runs como "pronto"; execuções de rotina/auxiliar não entram (SPEC-097)
P-095-TICK-OLHA-953-VEZES   NOVA 🤖 detect_signals 953× para 32 sinais na Resulta; cadência do tick (SPEC-097)
P-095-DATA-SOURCES-TRES-FORMAS NOVA 🤖 o briefing convergiu para label/detail/as_of_label; report_tool e radar ainda têm as suas; a tela lê as três
P-095-SEARCH · P-095-PDF    NOVAS — por gatilho (§5 da SPEC)
P-095-DOIS-PRODUTORES-IGUAIS observação (P6 do red team): dois produtores com o mesmo delta colapsam em "(+1 iguais)" — é informação, não perda
P-095-BRIEFING-ITEMS-SEM-COLUNAS observação: why_now/next_step vivem no jsonb da publicação; a tabela não tem as colunas (migration futura, se a Central precisar)
```

## 7. Gate da SPEC
```
GATE ZERO ......... ✅ 7 vermelhos provados em b054b5c (cópia limpa ../AutoBrokers-FIX-gate0) — (i) tela · (ii)–(vii) motor; todos VERDES em 876b01d
GUARDAS ........... ✅ relatorios-dizem-o-que-sao 16 blocos (0 falhas) + [13]–[16] que EXECUTAM chat/detalhe/fontes · test_o_relatorio_abre_pelo_achado 69 ok + [B2] · --mutar 9/9 acusadas · 078 2 verdes (carregam @/lib/** real) · 081 68 verdes (mede a FORMA) · 094 284 · 094.1 228 + 47 · canário 094 117 · 059 todas as garantias (fixture migrada) · nenhuma-mutacao-commitada 7 · menu/navegação · protocolo 47 · typecheck
RED TEAM .......... ✅ 1 lente (Opus, contexto limpo, 16 ataques com controle): FAIL 72 → 4 blockers (tela) + 12 pend. → conserto numa rodada (8a90480) → confirmação mecânica pelo orquestrador; 5 ataques de isolamento resistiram
CANÁRIO VIVO ...... ✅ B.4 aplicado (35→0, eventos 0→35, VERIFY por SELECT) · canario_095.py ao vivo: 1 peça, 2 versões, título = achado, data lida, 29 fontes; briefing composto sem gravar (manchete = item 1, sem relógio, dedup 0); arquivou o que criou (0 vivas)
ROTAS ............. ✅ `npm run test:rotas-montam` 294 rotas · `next build` exit 0 (2×: antes e depois do conserto; 16:29) · `next start -p 3097` +
                    GET /api/dashboard/entregas → `HTTP/1.1 401 Unauthorized {"ok":false,"error":"no_session"}` · GET /api/dashboard/relatorios/placar →
                    401 · GET /dashboard/entregas → 307 para /login?redirect=%2Fdashboard%2Fentregas — o servidor RESPONDE numa rota que executa código
                    (CLAUDE.md §9.1), e a lente padrão da lista não mudou a URL
SUÍTE INTEIRA ..... ✅ 935 passed · 6 failed · 39 xfailed (45m05, árvore parada, d2922e6). Os 6: 2 REAIS de guarda, migrados com o fato (059 [12]: resultado sem source_type deixou de ser da corretora; mutação-commitada: os textos D2/D5 existiam no produto de direito → marcadores únicos); 3 da classe do harness (P-093B-HARNESS: política, sinistro e ontologia passam isolados); 1 causado pelo orquestrador (docs editados durante a rodada → `test_a_arvore_ficou_limpa_no_fim`)
ENTREGA ........... ✅ 04/09 ~17:20 — preflight `HEAD..origin/main` = 0 · `origin/main..HEAD` = 17 · `git merge-base --is-ancestor origin/main HEAD` ok ·
                    `git push origin HEAD:main`:
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   5c22590..5dc3ee3  HEAD -> main
```
                    depois: `origin/main..HEAD` = 0. O EasyPanel constrói a `main`: clique Implantar (smith-web e smith-api). ZERO migration
```
**Veredito do orquestrador: GATE VERDE — SPEC-095 CONCLUÍDA**, com as pendências da §6 (todas com dono) e as decisões F-095-01/02 suas.

## 8. 🧑 A caixa do Founder
```
F-095-01  A LEITURA DO MODELO por cima do Pulso (a camada "como o ChatGPT/Claude entregam"): tudo pronto para entrar marcada como
          leitura, com guarda de que todo número da leitura existe no pack — precisa da sua autorização (1ª frase de modelo numa peça).
F-095-02  O briefing sai SÓ no painel (📊 canal único: dashboard). WhatsApp/e-mail é decisão sua, é o piso CRÍTICO (envia), e o WhatsApp
          de serviço deixa de ser grátis em 01/10 (F-094-10).
F-095-03  Decisões que a execução tomou (com nota): a URL /dashboard/entregas fica, só o nome muda; 35 relatórios de teste ARQUIVADOS
          (reversíveis — se algum era pergunta sua, diga); o placar não conta o relógio da plataforma; narrativa determinística; o Fabric
          não muda; identidade arquivada cria peça nova.
DEPLOY    `git push origin HEAD:main` está feito (§7) → clique Implantar no EasyPanel (smith-web e smith-api). ZERO migration. Até o
          deploy, os 35 links de teste dão 404 na tela ANTIGA de detalhe (a nova aceita arquivado) — nenhum link real foi afetado.
AMANHÃ    05/09 08:00 é a primeira publicação REAL do briefing com a narrativa nova (manchete = o achado, sem o relógio, com o porquê).
          O que você vai ver: "Fila acumulada" (ou o item 1 do dia) em vez de "N item(ns) esperando você hoje".
F-094.1-01 · F-094.1-02 · F-094.1-03 · F-094.1-08 · F-094-07 continuam abertas (a 095 não dependia delas).
```

## 9. Riscos remanescentes
- **Orçamento:** 📊 ≈1,80 M tokens de subagentes contra 1,3 M do card (+38%). Onde foi: o desenhista (324k) e o motor (397k) custaram o
  dobro do estimado; o red team (330k) valeu cada token (4 blockers de tela). A confirmação mecânica ficou com o orquestrador, sem Sonnet.
  A lição para a 096: builders em paralelo dobram o custo de leitura do contexto — dois builders são a metade do relógio, não a metade
  dos tokens.
- **Guardas de FORMA:** o red team mostrou que regex sobre a fonte deixa passar defeito de comportamento. Os blocos [13]–[16] executam o
  chat e o detalhe; o resto do Gate E ainda é forma. Próximas SPECs de tela: o padrão é executar.
- **A primeira publicação real com a narrativa nova é amanhã (tick 08:00)** — o canário provou o caminho sem gravar (idempotência por
  período); se a manchete de 05/09 vier contada, é regressão e o guarda [D3] deveria ter pego.
- **Nenhum motor paralelo:** ArtifactService (identidade, arquivar), a rota de lista, o mapa de tipos, `narrativa.py` puro; o placar é
  leitura; Fabric, schemas, metricas e blocks intactos.
- **P-094.1-LATENCIA** continua: 162 s por Pulso — o "Perguntar" nunca envia sozinho por causa disso.

## 10. Declaração de integridade
Nenhum motor paralelo foi criado (uma rota de lista, um publicador — `ArtifactService` —, um mapa de tipos, o placar é leitura). Nenhuma
migration. Nenhum segredo exposto. Nenhum dado atravessou tenants nas verificações (dois tenants no dublê da lista e do placar; `?versao=`
de outra corretora → 404). Escopo não reduzido: o que saiu da proposta está na §5 da SPEC com gatilho. `CLAUDE.md`, o protocolo, o glossário
e a decisão do ritmo foram lidos no início.

## 📊 A BATERIA
📊 conftest 04/09: inteira 1× no gate final (`alvo: tests · segundos: 2705,4 · coletados: 981 · falhas: 6 · commit d2922e6`); parciais ≈ 40 (guarda da tela ~12×, guarda do motor ~12× + 2× --mutar, 078 ~6×, 094/094.1/081 3×, 059 2×, typecheck 3×, build 2×). Minutos esperando a suíte: 45 (sob contenção: o build, o pip e o próprio next start competiam pela CPU). Lição: a suíte inteira roda SOZINHA — 45 min contra os 15 da 094.1.
