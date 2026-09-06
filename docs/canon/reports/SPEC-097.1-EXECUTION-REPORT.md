# SPEC-097.1 · EXECUTION REPORT — O caso se explica sozinho (pós-acionamento)

> Branch `feat/spec097-casa` (continua a 097) · base `origin/main` = `7f3f3eb`; a 097 já na main em `d758b81` · protocolo v11.2 + opção B · marcha **PADRÃO
> (compactada)** · 05/09/2026 (mesma sessão da 097, por ordem do Founder: "pode emendar direto para a 097.1") · orquestrador Fable 5.1 · SPEC
> `docs/canon/specs/SPEC-097.1-o-caso-se-explica-sozinho.md` v1.2.

## 0. EXECUTION CARD (protocolo §0.2)
```
OUTCOME ..............  o pós-acionamento vira uma FASE do atendimento com estado ESCRITO (de quem se espera, desde quando), o agente responde com regra (6 cartas) e com
                        estado, acompanha sozinho (novidade quando o corredor muda; mensagem honesta quando a espera vence), e o que sobra vai para humano com um
                        dossiê que diz PÓS — e a parte do agente termina ali (🧑 Founder). Duas réguas em turnos de intenção: resolvido pelo agente · sem humano.
RISCO ................  6  (alcance: a corretora 2 · reversibilidade: escreve work_waits/ficha_atendimento/human_handoff_reason 2 · frequência: todo acionamento 2 · sem migration
                        estrutural: −0; a data migration é opcional e não aplicada)
SUPERFÍCIE ...........  2  (FastAPI: corredor, handoff, vigia, prompt, draft; + 1 regra no read model TS; sem tela nova)
PISO APLICADO ........  §3.2: escrita no ciclo de vida em produção sem alterar estrutura → PADRÃO; compactada (1 desenhista, 1 builder, red team + 1 lente DADO+verdade, juiz fresco)
NÍVEL ................  PADRÃO
UNIDADES .............  0 (BLOCO 0 remedir) · U1 estado · U2 handoff PÓS (+U2.3 agente_concluiu) · U3 cartas/prompt/draft · U4 réguas · U5 acompanhamento (3 gatilhos existentes) · E canário · G guardas
COESÃO ...............  U3.1 (o módulo de dados) antes de tudo; U1 e U5 no mesmo funil (registrar_checkpoint); U2 lê U1; U4 importa U3.1 — um escritor (backend) e a régua
PARALELISMO REAL .....  desenhista (guarda) ‖ builder (produto); painel red team ‖ lente
TIME .................  investigador (Opus, 146k) · aquecimento (Opus, 160k) · desenhista (Opus, 213k + v1.2) · builder (Opus) · red team · lente DADO+verdade · juiz fresco
REFERÊNCIA ...........  interna: os guardas da 097 (--mutar por cópia, schema vivo, canário com controle) · `handoff_watchdog.varrer_esperas_vencidas` (o vigia que já roda)
                        externa: SPEC §3 — Intercom (SLA escrito), Zendesk (trigger por atualização), Front ("sem resposta em X"), Salesforce (case timeline), Google Agent Assist (resumo de handoff)
GATES ................  gate zero (20 vermelhos em 8529008) · guarda G verde com PARES · 16 mutações por nome · regressão zero (086/090/097) · test:casa 16/16 · régua no acervo ·
                        canário vivo com supressão provada · suíte inteira · painel + juiz · push
O ELO ................  "o pós-acionamento não tem NADA hoje" → lido (prompts, auxiliar, vigia) e medido (work_waits 0, handoff_reason 725/729 NULL, dispatch_phase 12, captured 0).
                        "95 % é impossível por desenho" → contado na taxonomia (283 com intenção, 27 humanos) → o Founder decidiu: handoff com dossiê completo = resolvido pelo agente.
                        "não precisa de Rotina" → o vigia das esperas já roda a cada 10 min em produção (buffer_processor:506) — a fase engata nele.
FAIXA DE RELÓGIO .....  4–6h   ORÇAMENTO ≤ 1,3 M (📊 a 097 gastou ≈2,9 M em CRÍTICO)
```

## 0.1 Telemetria (protocolo §11)
```
começou 05/09 ~17:00 (investigador) · primeira linha de código de produto: 05/09 ~22:00 (builder, depois do gate zero vermelho e da v1.2)
rodadas de painel: 1 (red team ‖ lente DADO+verdade) + juiz fresco em 2 rodadas (73 → 93)
defeitos que o painel NÃO pegou e quem pegou: o juiz pegou 5 (a âncora U2 na prosa do conserto [8]; a régua em traceback; `caso` nunca carregado; o `O que fazer` PRÉ no dossiê PÓS; a limpeza do canário contra o append-only) e a ausência de R11 no distiller; o desenhista pegou o próprio carimbo ([N2b] vazio) e o builder pegou dois seus (âncoras em comentário)
rodadas da bateria: suíte inteira 1× no fim (árvore parada) + guardas node 12/12 + tsc
nota 0–100 do orquestrador: 92 — o juiz deu 93; desconto meu pela régua REAL só poder medir 91,0 % até o corredor capturar protocolos de verdade (o 96,4 % é projetado, e está escrito como tal)
```

## 1. O que a conversão mediu (e o que mudou o desenho)
- 🔴 📊 O corpus do pedido (Resulta · DDD 48, 84 conversas) é uma linha ADMINISTRATIVA (cobrança 60 · apólice 50 · cancelamento 22; acionamento em 4). A linha de
  sinistro/assistência é a da AutoFleet (Regina): 448 conversas, 448 telefones, protocolo em 52, vidro 44, guincho 26 — 🧑 confirmado (AutoFleet = Regina, Resulta = Saionara).
  Corpus: 531 conversas / 21.260 mensagens → **36 com acionamento**, 1.088 mensagens do cliente depois do `t0`, **542 turnos** (2,01 msgs/turno), **283 com intenção**.
- 📊 62 % do tráfego pós-acionamento é de parceiro/oficina, não do segurado (673/1.088) → o estado responde a quem perguntar.
- 📊 O humano é excelente: mediana 0,8 min, p90 57,5 min, 1,8 % sem resposta → é o piso; a 097.1 tira o repasse de status, não vende velocidade.
- 📊 Hoje o produto tem ZERO no pós-acionamento: 4 agentes `attendance` desligados, prompts só de abertura; Follow-up não instalado, manual, `dry_run` hardcoded, não lê
  `work_waits`; `work_waits` 0 linhas (por falta de tráfego: `captured` nunca ocorreu desde a migration de 26/08); `human_handoff_reason` NULL 725/729; dossiê sem PÓS.
- 📊 A meta de 95 % é aritmeticamente inalcançável contando só carta+estado (27 de 283 são humanos por desenho: teto 94,7 %/90,5 %) → 🧑 decisão: handoff com dossiê
  completo encerra a parte do agente e conta; a linha "sem humano" fica publicada ao lado.
- 📊 O vigia das esperas JÁ RODA (`buffer_processor.py:506`, APScheduler, 10 min) → o acompanhamento é fase com 3 gatilhos existentes; nenhuma Rotina, nenhum motor.
- Aquecimento (Opus, 160k): nota 78 → 19 emendas (12 obrigatórias); as duas falsas plantadas achadas (85 msgs; `vence_em` no helper) + duas herdadas
  (`source_document_id` NULL 70,3 % não 100 %; não existe trilho `documents → knowledge_cards`).

## 2. Decisões da execução (protocolo §9: nota, escolha, siga)
- meta: handoff com dossiê completo = resolvido pelo agente, com a linha "sem humano" ao lado **90** × só carta+estado (teto < 95 %) 55 × manter 95 % e aceitar vermelho 30 — 🧑 o Founder confirmou a primeira.
- acompanhamento: fase com 3 gatilhos existentes (cliente escreve · checkpoint muda · vigia vence) **88** × Rotina/cron novo 30 (motor paralelo) × Auxiliar instalado 45.
- cartas: em CÓDIGO como dados que GERAM o prompt + publicador pelo trilho `documents` **88** × só documentos no RAG 60 (depende de Qdrant; não testável aqui) × `knowledge_cards` 50 (global).
- escopo da espera: `pos_acionamento` distinto de `acionamento` **92** × mesmo escopo 20 (o ramo `else` do helper satisfaria no mesmo turno).
- conversa pessoal: portão `e_atendimento_de_seguro` no distiller e na régua **85** × ignorar 0 (🧑 "tudo que for pessoal deve ser descartado").
- toggle: `companies.acionamento_profile.acompanhamento` (jsonb existente, ausente = ligado) **85** × coluna nova 50 (migration a mais) × por agente 40.

## 3. Commits
```
24fe713 SPEC v1.0 · d11d257 v1.1 (19 emendas) · 8529008 guardas (gate zero 18 ok · 20 falhas) · c41ceef v1.2 (direção do Founder) · 22d0b57 MUTAÇÃO (polícia 52 ok) ·
5517427 guardas v1.2 · e157d5b [E] por execução · 0fa413a BUILDER (produto) · 84641ed relatório · c0dd53b sessão REAL na fixture · f7eacbd lente no guarda · 74af224 consertos red team+lente ·
7745c62/3f0c15f [7][8][9] · 2fed44e BLOCO 0 · 18f0544 MANIFEST+pendências · 2826d43 U2 · 5f94c20 juiz r1 · 4f9d4cb relatório final + dossiê + índice + prompt 098 (empurrado à main)
```
## 4. Gate zero
📊 `python tests/test_o_caso_se_explica_sozinho.py` em `8529008`: **18 ok · 20 falhas · 0 pulados**; blocos [A][B][K][C][D][E][F][G][H][J][L][I] executando o motor real
com banco dublado e rede fechada. Hash da abertura do prompt congelado (`conhecimento_de_assistencia(sorted(_PLAYBOOKS))`). Dois PARES nasceram vermelhos ([B3p], [K2]) — achado
de produto: `abrir_espera` não substitui a anterior no mesmo escopo (no banco real a segunda seria PERDIDA). v1.2 (📊 `5517427`): **19 ok · 25 falhas** — as 5 vermelhas novas são [M1] [N1] [O1] [Q1] [Q2]; `MUTACOES` = 16 (U6 novidade enviada com agente desligado · U6B vigia
ignora o desligador · U7 filtro deixa passar pessoal · U8 handoff sem `Onde parou` conta). O desenhista fixou o contrato de UMA porta para falar com o cliente fora do turno
(`app/atendimento/acompanhamento.py`: `pode_falar_com_o_cliente`, `entregar_novidade`) — é nela que moram os 4 desligadores — e pegou o próprio carimbo ([N2b] passava com
mensagem vazia; consertado). Achados fora do contrato entregues ao builder: o vigia avisa a equipe por `_avisar_suporte` (nunca a mensagem do cliente por ali); a varredura de
`work_waits` é GLOBAL (o `company_id` vem da linha); `_marcar_fim_do_atendimento` roda antes da espera no checkpoint (`encaminhado` não gera novidade); `avisos` incrementa no fim do laço.

## 5. O builder (Opus, 424k, ≈1h40 — commit `0fa413a`)
| peça | o que nasceu |
|---|---|
| `backend/app/atendimento/pos_acionamento.py` | as 6 cartas como DADOS; `SITUACOES_PARA_HUMANO` (R9, fonte única); `classificar_turno` (cascata de regex sobre o TURNO, normalização = a do SQL, §9.4); `mapa_de_cartas`; `bloco_do_prompt` GERADO; `texto_da_espera`; `e_atendimento_de_seguro` (R11) |
| `backend/app/atendimento/acompanhamento.py` | a PORTA ÚNICA para falar com o cliente fora do turno: `pode_falar_com_o_cliente` (4 desligadores: `pausar_ia`, `companies.agent_enabled`, `agents.is_active`, `acionamento_profile.acompanhamento`) e `entregar_novidade` (entrega ou SUPRIME com `suprimida_por` em `work_events`). Nenhum job novo |
| corredor (`dispatch_router`) | `_pos_acionamento_do_checkpoint`: `captured`/`monitoring` com protocolo/previsão → espera `pos_acionamento` (`vence_em` = previsão ou +24 h); previsão MUDOU → novidade pela porta única; `encaminhado` fora; escopo `acionamento` intocado |
| `o_fim_do_atendimento` | `abrir_espera` substitui a anterior do mesmo escopo ANTES de inserir (📊 hoje a 2ª seria perdida no UNIQUE); `marcar_fim` satisfaz as ativas com `desfecho` |
| `human_handoff` | título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>`, `Quem fala` (honesto), `O que ele quer`, `Onde parou`, `Falta`, `O que fazer` por situação; `human_handoff_reason` default; `ficha_atendimento.agente_concluiu={em,motivo}` sem tocar `resolvido_em` |
| `graph.py` · `auxiliaries.py` · `handoff_watchdog.py` | bloco PÓS sob o gate `attendance` (abertura byte a byte igual, hash `ae32a67…`); o draft do Follow-up lê a espera ("ESTADO DO CASO") e expõe `dry_run` no corpo; o vigia ganha o ramo `pos_acionamento` (mensagem honesta por aviso, pela porta única) |
| `regua_0971.py` · `canario_0971.py` · `publicar_cartas_0971.py` · migration `20260905_02` | a régua com as duas linhas; canário e publicador em dry-run; a data migration escrita e NÃO aplicada |
| `casos.ts` + arnês mjs | `melhorEspera` (menor `vence_em`; empate → `pos_acionamento`); dublê com duas esperas; `--fila-json` expõe `work_waits` |
Lições do builder: duas mutações (U2, U6B) nasciam verdes porque a âncora aparecia primeiro num COMENTÁRIO — âncora mora na 1ª ocorrência em CÓDIGO; o fiscal
`honestidade_do_handoff` acusou uma docstring (reescrita, o fiscal ficou largo de propósito); `_KINDS_CITAVEIS` duplica `KINDS` → P-097.1-KINDS-DUPLICADOS.
## 6. Guardas e mutações (📊 05/09, HEAD 0fa413a)
```
python tests/test_o_caso_se_explica_sozinho.py        87 ok · 0 falhas · 0 pulados · VERDE (blocos A B K C D E F G H J L I M N O Q, todos executando o motor real)
  --mutar (cópia + subprocesso)                        16 rodadas · 16 VERMELHAS por nome novo · 0 verdes
regressão (7 guardas de atendimento)                   143 passed (sabe_como_terminou --mutar 3/3 · quem_fala_primeiro · termina_e_o_produto_sabe (migrado §9.3) ·
                                                       handoff_chega_em_alguem · chave_de_juncao · saudacao_do_religamento · chat_fala_como_corretor)
npm run test:casa                                      0 falhas (dublê com duas esperas; --fila-json com work_waits) · npx tsc --noEmit rc=0
suíte inteira (árvore parada, HEAD 5f94c20)             944 passed · 7 failed · 38 xfailed · 1 xpassed em 18m02 — triagem isolada: policia = 1 doc (este relatorio sem a nota → preenchida); test_r11_no_destilador 5 passed; sinistro_deixa_rastro 1 passed; 3 guardas-script rc=0; arvore_limpa = harness (P-093B-HARNESS). Nenhuma regressao de produto.
--mutar final (orquestrador, árvore parada)            PLACAR DAS MUTACOES: 16 rodadas · 16 vermelhas · 0 verdes (rc=0; arvore identica)
```
**A régua no acervo real** (📊 `python scripts/regua_0971.py`, SELECT nos dois tenants, zero PII):
```
turnos reconstruídos 464 · denominador (com intenção) 112 · descartados por R11 5
resolvido_por_carta 102 · estado_REAL 0 (📊 zero `captured` no banco) · estado_SIMULADO 25 (💭)
handoff_pos 0 (o histórico não tem dossiê) · para_humano_sem_dossie 6 · para_humano (por desenho) 10
resolvido_pelo_agente 102 = 91,1 %  ·  resolvido_sem_humano 102 = 91,1 %  ·  teto de desenho 94,7 % / 90,5 %
CONTROLE (mapa vazio): 0 = 0,0 %  ← o controle derruba
```
⚠️ Leitura honesta: no ACERVO HISTÓRICO o agente resolveria 91,1 % dos turnos com intenção por carta; os 10 restantes são humanos por desenho (R9) e, no produto novo,
recebem o dossiê PÓS no instante do handoff — o que a régua só pode SIMULAR (o juiz mede isso em §7). Ver §8: o juiz mediu a projeção com o motor real e o controle inverte.
## 7. O painel e o juiz
**Rodada 1 (05/09 ~22:30, red team ‖ lente DADO+verdade sobre `0fa413a`):**
- 🔴 **Red team — P0: a espera NUNCA nascia.** `_pos_acionamento_do_checkpoint` lia `session['protocolo'/'previsao'/'documentos_pendentes']` — chaves que ninguém escreve;
  o corredor grava `session['captured'] = {protocol, schedule: {day, at}, eta_minutes}` (`insurer_dispatch_service.py:2323` ← `corridor_playbooks.py:1852`). Provado com o
  motor real e a sessão real: 0 esperas; controle com as chaves inventadas: 1. E o guarda [A][K][M] e o canário FABRICAVAM a sessão imaginada — verdes sobre um formato que
  a produção não monta (§9.4, de novo: o dublê concorda com o código por construção). **Conserto:** o produto lê `captured` (com `schedule.day` dd/mm/aaaa, nunca MDY);
  a fixture do guarda passa a VIR DO MOTOR (`extract_capture_anchors` com os corredores reais sobre um texto de tela — `c0dd53b`); o canário monta a sessão pelo caminho real.
  P1: (a) o vigia ENCERRAVA o atendimento do segurado 30 min depois do prazo (regra do escopo `acionamento` vazando para `pos_acionamento`; prazo +24 h × caso de 6,9 dias);
  (b) a mesma frase ao segurado 3× em 30 min; (c) duas esperas = 6 avisos ao grupo; (d) `vence_em` cru — `'12/09/2026'` virava 9 de dezembro (MDY) e o INSERT falho era
  engolido depois de a anterior já ter sido substituída. P2: 5 classificações erradas; a régua não executava o motor do dossiê (`handoff_pos` = 0 por construção).
  Resistiu: supressão em 12 combinações dos desligadores (0 envios; controle 1); conversa assumida cala; `bloco_do_prompt()` sem termo técnico; §5 zero hits; publicador idempotente.
- 🔴 **Lente DADO+verdade** (worktree isolado): P1-1 a supressão NUNCA seria gravada — `work_events.work_run_id` é NOT NULL e o INSERT mandava `None` (📊 4/729 conversas têm
  `work_run`) → a supressão vai para `ficha_atendimento.acompanhamento`, e o dublê passa a impor NOT NULL; P1-2 a mutação U6 ficava vermelha pelo motivo errado (a âncora quebrava o
  `async def`); P1-3 `[C2b]` presa a "29/08" = `created_at` da fixture (uma `texto_da_espera` que inventa a data passaria) ; P1-4 **os 📊 do BLOCO 0 não reproduzem**: a régua dá
  464 turnos (o relatório mediu 542) porque o `t0` era regex Python sobre `_norm` e o investigador mediu em Postgres (§9.4 — a terceira vez que a lição aparece nesta leva), e o rótulo
  "283 turnos" mentia a unidade (são msgs). P2: `[B3p]` cego (`len<=1`); migration fora do MANIFEST; três listas dos mesmos 3 `kind`. Sólido: D3 CHECK/UNIQUE, D4 `agente_concluiu`
  aditivo, D5 migration idempotente, V4 hash da abertura byte a byte; 108 asserções E · 2 F legítimas · 1 F→E; declaradas 16/16, das suas 6 uma verde (L2 = P1-3).
- **Consertos (`74af224`, `7745c62`, `3f0c15f`):** o produto lê `captured` (`schedule.day` em dd/mm/aaaa pelo `instante_br`, nunca MDY; `eta_minutes`); prazo do perfil
  (`acionamento_profile.prazo_pos_acionamento_horas`, padrão 48 h); espera já aberta sem promessa nova não reabre; o vigia agrupa por conversa, `pos_acionamento` vai a `vencido`
  SEM `marcar_fim`, UMA mensagem ao cliente por vencimento (avisos 0→1), UM aviso à equipe por conversa; `abrir_espera` valida antes de substituir e devolve a anterior se o
  INSERT falhar; a supressão vai para `ficha_atendimento.acompanhamento` (work_events só com run); cascata do classificador ajustada com os exemplos reais; a régua executa
  `_montar_dossie` real, decide por `SITUACOES_PARA_HUMANO` (`I` → `volta_ao_corredor`) e publica corpus e teto ao vivo; `encaminhado` fora do PÓS; transcrição só com a
  corretora conferida; roteiro do publicador 12/12. `esperando_cliente` ficou FORA por falta de escritor real de "documento pedido" (P-097.1-DOC). Guarda 109 ok · 16/16 · arnês do
  red team 30 ok.
**Juiz fresco — rodada 1** (Opus, 211k, HEAD 3f0c15f): **NOTA 73, gate VERMELHO** — os 15 achados do painel CONFIRMADOS CONSERTADOS com controles que invertem, mas 5 defeitos
NOVOS: (1) P0 `--mutar` 15/16 — a prosa do conserto [8] virou a 1ª ocorrência de "PÓS-ACIONAMENTO" e a U2 mutava o comentário (a segunda vez nesta SPEC: âncora mora na 1ª
ocorrência em CÓDIGO); (2) a régua terminava em traceback (`medir(com_estado=)`); (3) `handoff_pos` zero por construção (`_ler_acervo` não carregava o `caso`) — a mesma forma do
P0 do red team; (4) PRODUTO: o `O que fazer` do dossiê PÓS era a recomendação PRÉ-acionamento (R9 inerte; com a lista vazia os 6 continuavam "completos"); (5) o canário vivo não tinha
volta (`work_events` append-only; run cascateia) e deixou 1 conversa + 1 run + 4 events; J6: R11 não estava no distiller. Canário Q1–Q4 OK e **zero mensagens provado**.
**Consertos da rodada 1 do juiz (`2826d43`, `5f94c20`):** prosa sem o literal (U2 volta a derrubar [C1]); `medir(turnos, mapa, com_estado)`; `_ler_acervo` carrega a conversa
real como `caso` e a espera ativa real; `_o_que_fazer` no PÓS vem da situação (R9) + espera e o controle INVERTE (0/6 com a lista vazia); o canário chama
`_pos_acionamento_do_checkpoint` sem criar run/events e limpa 0/0/0 (o lixo da 1ª corrida purgado por `set_config('app.work_events_purge','on',true)`); o portão R11 entra em
`attendance_distiller._destilar_sessao` antes da LLM (`test_r11_no_destilador.py`, pessoal → 0 cartas; atendimento → 2).
**Juiz fresco — rodada 2** (mesmo juiz, HEAD 5f94c20, 238k acumulados): **NOTA FINAL 93/100.** Os 5 defeitos + J6 → CONFIRMADO CONSERTADO por comando: U2 com
ocorrência única do literal (l.750, o título); régua rc=0 com REAL 91,0 % × PROJETADO 96,4 % × controles; `caso` em 464/464 turnos (a conversa real + a rajada real);
R9 no dossiê PÓS com ações específicas por situação e o controle com a lista vazia INVERTENDO (0/6); canário sem run/events, limpeza 0/0/0, `messages 25072 → 25072`,
`platform_sends 5 → 5`, zero órfãos após a purga governada; R11 no distiller antes da LLM. Aberto sem P0/P1: a espera de escopo `acionamento` (086) segue chamando
`marcar_fim(EXPIROU)` no teto de avisos (legado, não desta SPEC); "pode mandar o guincho" → `N` (não responde errado; não responde); `[E3]` listado como FORMA na docstring;
`_KINDS_CITAVEIS` (pendência). O `--mutar` do gate final é do orquestrador (§6).
## 8. Canário vivo e a régua no acervo
**Canário vivo** (📊 06/09 ~04:30, Resulta, `AUTOBROKERS_CANARIO=1 python scripts/canario_0971.py --vivo`, HEAD 5f94c20; a 1ª corrida do juiz em 3f0c15f fez Q1–Q4 e
crashou na LIMPEZA — `work_events` é append-only e o run cascateava; o lixo foi purgado por `set_config('app.work_events_purge','on',true)` e o canário deixou de criar run/events):
```
CONTROLE ANTES — esperas na conversa canário: 0 → OK
Q1 âncoras REAIS do corredor `alfa-auto-whatsapp@v1` → captured={protocol: '2026-00000971', schedule: {day: '09/09/2026', at: '14:00'}}
Q1 checkpoint `captured` → linhas=1 ativas=1 scope=pos_acionamento kind=esperando_seguradora · prazo = a previsão → OK
Q2 previsão mudou → linhas=2 ativas=1 substituídas=1 → OK
Q2b novidade: na ficha suprimidas=1 motivo='agente_desligado_na_corretora' · work_events da corretora antes=12984 depois=12984 → OK (zero tentados)
Q3 dossiê: título PÓS=True · 'Onde parou'=True · 'conclua'=False → OK · CONTROLE: conversa sem acionamento → título antigo → OK
Q4 marcar_fim → ativas=0 por_desfecho=1 → OK
LIMPEZA — work_waits=0 · episódios=0 · conversas=0 (esperado 0/0/0)
```
📊 Zero mensagens (juiz, SELECT antes/depois): `messages 25072 → 25072` · `platform_sends 5 → 5` · `max(messages.created_at)` inalterado (05/09 14:41). Amandus → Resulta →
AutoFleet: o canário grava só na Resulta (linhas próprias, removidas); Amandus é WhatsApp pessoal; AutoFleet coberto pela régua (o acervo dela) e pelos guardas com dois tenants.

**A régua no acervo real** (📊 06/09, `python scripts/regua_0971.py`, SELECT nos dois tenants, zero PII, rc=0):
```
corpus: 531 conversas varridas · 32 com t0 · 932 msgs do cliente · 464 turnos   (relatório em Postgres: 36 · 1.088 · 542 — §9.4; as duas publicadas)
denominador (com intenção) 111 · descartados R11 5 · resolvido_por_carta 101 · estado_REAL 0 (📊 esperas ativas no banco: 0) · estado_SIMULADO 25 (💭)
handoff_pos REAL 0 (o histórico não tem espera escrita) · volta_ao_corredor 1 (rótulo I) · para_humano_sem_dossie 6
resolvido_pelo_agente 101 = 91,0 %  ·  resolvido_sem_humano 101 = 91,0 %  ·  CONTROLE (mapa vazio) 0 = 0,0 %
💭 PROJETADO com a espera ESCRITA (o que a U1 faz nascer): carta 101 + handoff_pos 6 → 107 = 96,4 %   (≥ 95 %)
controles do handoff: SEM estado → 0 completos · com SITUACOES_PARA_HUMANO VAZIA → 0 completos   (o critério inverte — não é carimbo)
teto de desenho ao vivo em TURNOS: 95,5 % (com J) / 94,6 % (sem J)   ·   teto do relatório em MENSAGENS: 94,7 % / 90,5 %
```
**Leitura honesta para o Founder:** hoje, sobre o acervo histórico (que não tem estado escrito), o agente resolveria 91,0 % dos turnos com intenção por carta; os 10 restantes são
humanos por desenho (R9). Com o estado que esta SPEC faz nascer, o dossiê PÓS fica completo nesses turnos e a régua projeta **96,4 %** — contando o handoff com dossiê
completo como "a parte do agente terminou" (🧑 decisão de 05/09). As duas linhas ficam publicadas; a de controle derruba.
## 9. O que ficou fora · pendências · a caixa do Founder
**Fora (com gatilho):** Rotina/cron para o acompanhamento (nunca — os 3 gatilhos existem) · Follow-up como Auxiliar instalado (fica o rascunho manual lendo o estado) ·
`esperando_cliente` (sem escritor real de "documento pedido" no corredor → P-097.1-DOC) · classificar mídia (P-097.1-MIDIA-SEM-TEXTO) · markdown no WhatsApp
(P-097.1-MARKDOWN-NO-CANAL) · procedência das 13.154 cartas (P-097.1-CARTAS-SEM-PROCEDENCIA) · interlocutor por cadastro (P-097.1-INTERLOCUTOR-POR-CADASTRO) · toggle na
Central (P-097.1-ACOMPANHAMENTO-NA-CENTRAL) · `_KINDS_CITAVEIS` (P-097.1-KINDS-DUPLICADOS) · publicar as cartas no RAG (P-097.1-CARTAS-NO-RAG) · RAG da AutoFleet vazio
(P-097.1-RAG-AUTOFLEET-VAZIO). Total: **9 P-097.1-***. O resíduo do red team [2] no escopo `acionamento` (a espera do travamento ainda chama `marcar_fim` no teto de avisos)
é comportamento da 086, não desta SPEC — registrado, não tocado.

**A caixa do Founder (097.1):**
1. **Implantar** (a `main` leva 097 + 097.1). Nada muda para o segurado enquanto os agentes de atendimento estiverem desligados: a espera nasce, a novidade e a mensagem honesta
   são GERADAS e SUPRIMIDAS (fica escrito na ficha), o dossiê PÓS chega à equipe pelo caminho de handoff que já existe.
2. **Quando religar o WhatsApp e ligar os agentes:** o acompanhamento nasce LIGADO por corretora. Para desligar numa corretora: `companies.acionamento_profile.acompanhamento = false`
   (a tela na Central é P-097.1-ACOMPANHAMENTO-NA-CENTRAL). O prazo padrão da espera é 48 h (`acionamento_profile.prazo_pos_acionamento_horas`).
3. **Publicar as 6 cartas no RAG das duas corretoras — passo a passo (não urgente):**
   ```
   EasyPanel → projeto AutoBrokers → serviço smith-api → aba "Console" (o terminal do contêiner)
   1) python scripts/publicar_cartas_0971.py            ← mostra o plano: "2 tenants · 6 cartas = 12 documentos"; nada grava
   2) python scripts/publicar_cartas_0971.py --vivo     ← cria os 12 documentos pelo trilho documents → ingestion_service → Qdrant
      a última linha tem de ser:  VERIFY: 12/12 documentos nos 2 tenants
   Se o console abrir fora da pasta do app:  cd /app  (e repita). Rodar duas vezes NÃO duplica (idempotente por corretora + hash).
   Se aparecer erro com "Qdrant" ou "MinIO": copie a linha do erro e me mande.
   ```
4. **A meta:** decidida por você — handoff com dossiê completo conta para o agente. 📊 Hoje 91,0 % por carta no acervo (sem estado escrito); 💭 96,4 % projetado com o estado que
   esta SPEC faz nascer. O número REAL só aparece quando os agentes estiverem ligados e o corredor capturar protocolos de verdade — a régua está pronta para medir isso.
5. **A linha da atendente:** pessoal/colegas é descartado antes de virar carta (no distiller) e antes da régua. Nada a decidir; só saber que existe.
## 10. Declarações
- Nenhum motor paralelo: nenhum scheduler/cron/listener novo; a espera nasce no funil existente; a novidade e a mensagem honesta saem pelo caminho de resposta do agente e pelo vigia que já roda.
- Nenhuma mensagem saiu (agentes desligados; supressão provada); nenhum agente ligado; InfoCap só leitura; nenhum segredo/PII impresso; conversa pessoal descartada.
## 11. Entrega
```
$ git rev-list --count HEAD..origin/main   → 0
$ git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   d758b81..4f9d4cb  HEAD -> main
$ git rev-list --count origin/main..HEAD → 0        (📊 06/09/2026 ~05:15)
(este commit de docs, com a saída colada, empurrado em seguida)
```

