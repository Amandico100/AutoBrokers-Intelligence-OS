# SPEC-121 — Mais rotas atendem sozinhas, e o grupo só ouve quando precisa

> Relatório de execução · 30/09/2026 · rito AAA v13 · branch `spec/121-grupo-e-rotas`
> commit inicial `0cc1bdd` · commit final: ver §2 · SPEC `specs-propostas/SPEC-121-mais-rotas-sozinhas-e-o-grupo-so-ouve-quando-precisa.md`

## 0. O EXECUTION CARD

```
OUTCOME ........  o grupo de suporte só recebe aviso de conversa que o humano NÃO conhece, com o agente LIGADO e
                  pedido PELO AGENTE; a regra dos 7 dias do Founder vale para o agente; mais rotas atendem sozinhas
                  (Porto menu novo, eletro Allianz, chaveiro, eletricista, carro reserva); Sonnet 5 sai, Sonnet 5.5 entra
RISCO ..........  9  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE mensagem enviada 3 · FREQUÊNCIA todo atendimento 3)
SUPERFÍCIE .....  3  (6 remetentes do grupo · corredores · acervo e classificador · catálogo de modelos)
PISO APLICADO ..  §3.2 — envia ao grupo, à URA e ao segurado; migration que altera dado → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto · confirmação
O FIO ..........  webhook → a_ia_deve_calar (janela de 7 dias) → coleta → antes_de_acionar → corredor → protocolo
                  → porta única do grupo (A agente ligado · B prova do agente · C nenhum humano em 7 dias)
PARALELISMO ....  F7 (modelos) ‖ F1 (grupo) ‖ F2→F4→F4b→F5 (corridor_playbooks, um dono) ‖ F3→F3b (acervo) → F6
UNIDADES .......  8 fatias + conserto em 3 partes de arquivos disjuntos (X grupo · Y corredores · Z medição)
COESÃO .........  "o agente resolve sozinho, e quando não resolve, avisa UMA vez quem não sabe"
TIME ...........  10 builders · 1 investigador · juiz ‖ red team · confirmação · atualizador de documentos
REFERÊNCIA .....  interna: os 29 avisos errados de 21/09 · externa: SRE book (alertar só quando exige ação humana),
                  SRE workbook (silenciar o que já está em tratamento), Fowler Dark Launching, doc do Sonnet 5.5
GATES ..........  G1–G10, §4
O ELO ..........  "os avisos errados vêm do vigia lendo o status do espelho" — 📊 29/29 com handoff.realertado,
                  28/29 sem motivo do agente; B chega em A: T7 reproduz as 29 formas pelo motor → 0 envios
FAIXA DE RELÓGIO  💭 1 dia; 📊 ≈ 8h20 de relógio de gerente + ~4h de bateria (duas quedas de internet)
nota da execução  89/100 (§9)
```

## 1. O QUE MUDOU

### 1.1 O grupo só ouve quem precisa (F1 + conserto X)
- 📊 BLOCO 0 (29/09, SELECT): os **29 de 29** avisos de 21/09 eram de conversas que a atendente já tinha atendido pelo
  celular, com o agente **desligado**; 28/29 sem nenhum pedido do agente. Todos saíram pelo vigia.
- Agora **toda** mensagem de conversa ao grupo passa por uma porta com três perguntas: **A** o agente de atendimento
  está ligado (na dúvida, cala) · **B** foi o agente quem pediu (o chamador leva prova explícita) · **C** nenhuma pessoa
  da corretora falou com o cliente nos últimos 7 dias (sem o antigo teto de 40 mensagens; assumir vale 7 dias).
- Sinistro e ✅ de concluído também obedecem (decisão do Founder). Todo silêncio deixa rastro `grupo.calado`.
- O vigia lia as **50 conversas mais antigas** (📊 29/09: 475 paradas; a mais nova lida era de 14/09) → agora as mais novas.
- O resumo das 19h passa a contar os silêncios por motivo (K3).
- 🔴 A corretora C3 estava armada hoje (destino ativo, agente desligado): com a SPEC no ar, ela fica calada.

### 1.2 A regra dos 7 dias vale para o agente (F1 + conserto X)
- 📊 477 conversas estavam em "pedido de humano" por causa do espelho — com o agente religado, ele ficaria calado nelas
  **para sempre**. Agora: dentro dos 7 dias, calado e sem grupo; depois, **só uma mensagem NOVA** reabre, como conversa
  nova; as mensagens antigas não voltam ao modelo como pendência; nada vai ao grupo pela reabertura.
- Pedido do agente que uma pessoa atendeu também reabre depois de 7 dias; nunca atendido → não reabre, o vigia avisa (D-121-D).

### 1.3 Rotas (F2, F4, F4b, F5 + conserto Y)
- Porto auto: o menu novo (*"Você quer falar sobre qual assunto? … Sinistro"*) passava **toda** conversa a uma pessoa;
  📊 5 telas de menu sem passo → passos novos; "sinistro" como **opção** de menu não dispara mais (relato continua).
- Porto: consultora de relacionamento → pessoa com motivo (D11); bateria nova avisa o preço antes (D8);
  "você tem um serviço aberto" → "Não" só quando o aberto é de outro tipo (D-121-G).
- Allianz eletrodomésticos: a tecla do aparelho (1–15) em vez de "15" fixo; 8 frases reais de recusa viram gatilho.
- HDI chaveiro: a bolha de cobertura não chama pessoa. Eletricista HDI/Yelum pergunta tipo, item e cômodo antes.
- Portão eletrônico não é eletricista; raio que queimou equipamento = sinistro de danos elétricos (D10).
- **Carro reserva** (decisões do Founder): Yelum pelo corredor até "em análise, até 3 horas úteis" pelo canal próprio;
  vai a pessoa sem número do sinistro, sem CNH/cartão, fora de 9h–17h, por pane; Tokio e Azul recebem o link;
  Allianz, HDI, Porto, Zurich, Bradesco, Mapfre → pessoa. 📊 5 de 6 sessões reais do canal comum chegam a "em análise"
  pelo motor; a 6ª é fora do horário (vai a pessoa, como decidido).
- O segurado deixou de receber textos escritos para a equipe (Tokio, Porto vidros, Zurich vidros — K4).

### 1.4 Acervo honesto (F3, F3b, conserto Z)
- O acervo passa a ver quando o robô da URA recomeça depois de uma pessoa; consulta de pedido já existente **não conta**
  como atendimento (derrubou uma "atende sozinho" falsa em desentupimento); etiquetas: chave → chaveiro, recarga →
  bateria, geladeira/fogão/micro-ondas → eletrodomésticos. 📊 PII no acervo regerado: **0 em 6.146 linhas** (controle pego).

### 1.5 Sonnet 5.5 (F7)
- 📊 `GET /v1/models` (29/09) lista `claude-sonnet-5-5` (28/09). Migration `20260929_01` aplicada: Sonnet 5.5 APPROVED
  (US$ 2/10), **Sonnet 5 BLOCKED**, 8 agentes e 1 corretora migrados; o adaptador troca `thinking disabled` por
  `between_tools` e tool_choice forçado por `auto`. Smoke real pelo caminho do produto: 2 chamadas, 📊 US$ 0,0027.

### 1.6 O número
📊 `python scripts/simular_corredor.py --todas --formato json`, commit `4ccd063`, 30/09:
```
                    antes (0cc1bdd)   depois (4ccd063)
ATENDE SOZINHO            31                31
VAI PARA UMA PESSOA        2                 4   (tokio e yelum carro reserva, por desenho)
FALTA CAPTURA             40                41
rotas                     73                76   (+3 carro reserva)
```
⚠️ O número de cima **não subiu**, e é honesto: duas "atende" eram falsas (desentupimento por consulta; socorro mecânico
Yelum era recarga de bateria) e saíram; entraram yelum/auto/bateria, porto/auto/guincho e azul/auto/guincho de volta.
Rota a rota com causa: `reports/SPEC-121-ROTAS-ANTES-E-DEPOIS.md`.

## 2. COMMITS
`6cb62e1` D-PROTO-16 · `dbacf5e` F7 · `c7b210c` F2+F4a · `773db2f` F3 · `823a845` F1 · `2787ff2` vigia · `62c9b87` F4b+F5 ·
`e0fa1b7` F3b · `42a491d` conserto X · `998f9da` conserto Z · `4ccd063` conserto Y · `27ebc46` F6 · `b0aff49` triagem da bateria · docs/relatório: ver o push (§8).

## 3. BATERIA
📊 Suíte inteira em worktree limpo, triada **nominalmente** contra o commit base `0cc1bdd` rodado no mesmo rito:
```
base 0cc1bdd ........ 43 failed · 2252 passed   (8.217 s)
4ccd063 ............. 49 failed · 2329 passed   → 9 NOVAS, triadas uma a uma:
                      3 de PRODUTO (18 slots sem rótulo na ficha; carro reserva cobrando "onde o carro está";
                      chaveiro sem a garagem que a Yelum pergunta) · 5 verdade vencida pela SPEC (lição migrando,
                      controle vermelho provado) · 1 ordem (dublê vazado de outro teste — P-121-28)
b0aff49 (final) ..... 40 failed · 2339 passed   (3.891 s) → 0 NOVAS; 3 sumiram (1 conserto real, 2 de ordem)
```
Lista regravada em `reports/BATERIA-LINHA-DE-BASE.txt`.

## 4. GATES
| gate | estado |
|---|---|
| G1 29 avisos de 21/09 → zero | ✅ T7 pelo motor; mutações (tirar A, claim 6 h, teto 40, sinistro isento, fail-open) vermelhas |
| G2 agente desligado → zero de conversa | ✅ controle: cobrança sai |
| G3 Porto menu novo pelo motor | ✅ 46 verdes; controle: relato de sinistro → pessoa; a irmã do gatilho guardada por 3 telas reais |
| G4 yelum guincho / porto bateria | ✅ yelum guincho 95%; ⚠️ porto bateria segue com 4 órfãs de depois da consultora (pessoa por desenho) |
| G5 desentupimento/eletro Allianz | ❌ REFUTADO pela evidência: o protocolo foi dado por pessoa (D-121-I) — acionamento real |
| G6 régua antes×depois com causa | ✅ `SPEC-121-ROTAS-ANTES-E-DEPOIS.md` |
| G7 carro reserva Yelum pelo motor | ✅ 5/6 do canal comum; controles sem nº / sem cartão / fora do horário / pane → pessoa |
| G8 constante_justificada | ✅ toda constante nova cita o rótulo da tela real |
| G9 bateria triada | ✅ 0 falhas novas contra a base (§3) |
| G10 simulador | 📊 31 de 76 (§1.6) |

## 5. JULGAMENTO
- Juiz: PASS COM PENDÊNCIAS, **87**, 5 de 5 números reproduzidos, 0 blockers.
- Red team: QUEBREI, **80** — B1: carro reserva chegava ao grupo como "🚨 NOVO SINISTRO" (a palavra "sinistro" no motivo
  era reclassificada pelo detector). **EXCLUSIVO do red team** (costura F5 × F1; nenhum teste atravessava).
- Conserto único em 3 partes (X/Y/Z, arquivos disjuntos) · confirmação: **o conserto não criou defeito**, **88**.
- Incidente de processo: a régua e `test_duas_medicoes` MUTAM `corridor_playbooks.py` na árvore compartilhada e
  reverteram 2 edições do conserto Y em silêncio — detectado pelo builder Z, reaplicado sob o lock (P-121-13).

## 6. MIGRATION
`20260929_01_spec121_sonnet_5_5.sql` — APPLY/VERIFY/ROLLBACK no cabeçalho, escritos antes; aplicada 29/09 (versão
`20260929200932`); VERIFY: "Sonnet 5 recusado, Sonnet 5.5 aceito"; o juiz rodou o VERIFY de novo e confere o ROLLBACK.

## 7. O QUE FICOU FORA
P-121-01…26 em `PENDENCIAS.md` (as principais: o número de carro reserva da Yelum, os acionamentos reais, a carta D10,
testes que mutam a árvore compartilhada, resíduos do B1). Drenadas: P-120-01, -04, -05, -10, -12, -14, -17 FECHADAS.

## 8. ENTREGA
<!-- PUSH -->

## 9. NOTA E TELEMETRIA
**Nota do gerente: 89/100** — critério: o outcome do grupo e da regra dos 7 dias está provado pelo motor com controles
e 0 blocker restante; perde por G5 refutado, pelo número de rotas não ter subido (honesto) e pelo incidente das mutações.
📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (30/09 03:5x): executor 493 min, pico 468 k,
US$ 28,53 · 15 agentes (todos opus-5-5), 1.987 turnos, US$ 297,54 no total · achados por mecanismo: investigador
(3 premissas que mudaram o desenho) · builders (vigia lendo as antigas; consulta como desfecho) · juiz 6 pendências ·
red team 1 blocker EXCLUSIVO · confirmação 0 · rodadas de bateria: 1 base + 2 finais (a 1ª achou 9, fechadas). Nenhum motor paralelo foi criado.
