# SPEC-095 · RELATÓRIOS QUE O CORRETOR ENTENDE — relatório de execução

> **v1.2 da SPEC, executada sob o protocolo v11.2 · OPÇÃO B (três marchas) · marcha PADRÃO** · 04/09/2026 · branch
> `feat/spec095-relatorios` · base `5c22590` · commit da SPEC `aa6ec76` · commit final de código `{SHA_FINAL}`
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
FAIXA DE RELÓGIO .....  declarada 5–7h · 📊 realizada: {FAIXA_REAL}
ORÇAMENTO ............  ≤ 1,3 M · 📊 gasto: conversão 225k · aquecimento 199k · desenhista {T_DES} · builder tela {T_FE} · builder motor {T_BE} ·
                        red team {T_RT} · confirmação {T_SON} · TOTAL {T_TOTAL}
BATERIA ..............  suíte inteira {N_SUITE}× · parciais {N_PARCIAIS}
```

```
o painel rodou sobre CÓDIGO?          {PAINEL}
conserto criou defeito?               {CONSERTO}
o que sobrou é MATERIAL?              {SOBROU}
```

## 0.1 A TELEMETRIA (§11)

```
começou / terminou                     04/09 ~11:00 (preflight + leitura) / {FIM}
tempo até a PRIMEIRA linha de código   {T_PRIMEIRA_LINHA} — inclui conversão medida (investigador+pesquisador 19 min) e aquecimento (23 min)
rodadas de painel e achados por lente  {PAINEL_ACHADOS}
defeitos que o painel NÃO pegou        {NAO_PEGOU}
rodadas da bateria                     {BATERIA}
nota 0–100 do orquestrador             nota provisória 0/100 — em execução; a definitiva entra no fecho, com a justificativa em uma linha
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

**Depois:** {DEPOIS}

## 2. As unidades

| bloco | commits | o que fez | gate |
|---|---|---|---|
| 0 · remedir + gate zero | | | |
| A · a lista e o nome | | | |
| B · identidade, data honesta, canário, limpeza | | | |
| C · o placar | | | |
| D · a narrativa | | | |
| E · o detalhe | | | |
| F · canário vivo + dossiê | | | |

## 3. 📊 Os números
```
{NUMEROS}
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
{LACO}

## 6. Pendências (PENDENCIAS.md)
```
{PENDENCIAS}
```

## 7. Gate da SPEC
```
GATE ZERO ......... {GZ}
GUARDAS ........... {GUARDAS}
RED TEAM .......... {RT}
CANÁRIO VIVO ...... {CANARIO}
ROTAS ............. {ROTAS}
SUÍTE INTEIRA ..... {SUITE}
ENTREGA ........... {ENTREGA}
```
**Veredito do orquestrador:** {VEREDITO}

## 8. 🧑 A caixa do Founder
```
{CAIXA}
```

## 9. Riscos remanescentes
{RISCOS}

## 10. Declaração de integridade
Nenhum motor paralelo foi criado (uma rota de lista, um publicador — `ArtifactService` —, um mapa de tipos, o placar é leitura). Nenhuma
migration. Nenhum segredo exposto. Nenhum dado atravessou tenants nas verificações (dois tenants no dublê da lista e do placar; `?versao=`
de outra corretora → 404). Escopo não reduzido: o que saiu da proposta está na §5 da SPEC com gatilho. `CLAUDE.md`, o protocolo, o glossário
e a decisão do ritmo foram lidos no início.

## 📊 A BATERIA
{BATERIA_DETALHE}
