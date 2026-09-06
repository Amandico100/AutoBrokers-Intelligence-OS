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
começou 05/09 ~17:00 (investigador) · primeira linha de código de produto: {A PREENCHER}
rodadas de painel: {A PREENCHER}
defeitos que o painel NÃO pegou e quem pegou: {A PREENCHER}
rodadas da bateria: {A PREENCHER}
nota 0–100 do orquestrador: {A PREENCHER}
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
24fe713 SPEC v1.0 · d11d257 v1.1 (19 emendas) · 8529008 guardas (gate zero 18 ok · 20 falhas) · c41ceef v1.2 (direção do Founder) · 22d0b57 MUTAÇÃO (polícia 52 ok) · {A PREENCHER}
```
## 4. Gate zero
📊 `python tests/test_o_caso_se_explica_sozinho.py` em `8529008`: **18 ok · 20 falhas · 0 pulados**; blocos [A][B][K][C][D][E][F][G][H][J][L][I] executando o motor real
com banco dublado e rede fechada. Hash da abertura do prompt congelado (`conhecimento_de_assistencia(sorted(_PLAYBOOKS))`). Dois PARES nasceram vermelhos ([B3p], [K2]) — achado
de produto: `abrir_espera` não substitui a anterior no mesmo escopo (no banco real a segunda seria PERDIDA). v1.2 (📊 `5517427`): **19 ok · 25 falhas** — as 5 vermelhas novas são [M1] [N1] [O1] [Q1] [Q2]; `MUTACOES` = 16 (U6 novidade enviada com agente desligado · U6B vigia
ignora o desligador · U7 filtro deixa passar pessoal · U8 handoff sem `Onde parou` conta). O desenhista fixou o contrato de UMA porta para falar com o cliente fora do turno
(`app/atendimento/acompanhamento.py`: `pode_falar_com_o_cliente`, `entregar_novidade`) — é nela que moram os 4 desligadores — e pegou o próprio carimbo ([N2b] passava com
mensagem vazia; consertado). Achados fora do contrato entregues ao builder: o vigia avisa a equipe por `_avisar_suporte` (nunca a mensagem do cliente por ali); a varredura de
`work_waits` é GLOBAL (o `company_id` vem da linha); `_marcar_fim_do_atendimento` roda antes da espera no checkpoint (`encaminhado` não gera novidade); `avisos` incrementa no fim do laço.

## 5. O builder
{A PREENCHER}
## 6. Guardas e mutações
{A PREENCHER}
## 7. O painel e o juiz
{A PREENCHER}
## 8. Canário vivo e a régua no acervo
{A PREENCHER}
## 9. O que ficou fora · pendências · a caixa do Founder
{A PREENCHER}
## 10. Declarações
- Nenhum motor paralelo: nenhum scheduler/cron/listener novo; a espera nasce no funil existente; a novidade e a mensagem honesta saem pelo caminho de resposta do agente e pelo vigia que já roda.
- Nenhuma mensagem saiu (agentes desligados; supressão provada); nenhum agente ligado; InfoCap só leitura; nenhum segredo/PII impresso; conversa pessoal descartada.
## 11. Entrega
{A PREENCHER}
