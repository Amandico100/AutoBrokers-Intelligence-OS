# SPEC-130-A.1 — Quem Cobra Menos: a mensagem, o mínimo do mínimo e a margem corrigida · relatório de execução

> 06–07/10/2026 · branch `spec/130-A1-quem-cobra-menos` · base `705b67f` (main) · rito AAA v13, 🟠 ALTO · SPEC
> `specs/SPEC-130-A1-quem-cobra-menos-a-mensagem-e-a-margem.md` · laudos no rascunho do gerente (`laudos/130a1-juiz.md`,
> `laudos/130a1-red.md`, `laudos/130a1-confirmacao.md`)

## EXECUTION CARD
```
OUTCOME ..............  o pedido do CANAL sai com a mensagem de comparador ao consumidor (vencedor, volume REAL, economia com a
                        origem da conta, 2 cartões, 6 por seguradora, a corretora em lista, a pergunta final) e com o 4º cálculo
                        `minima`; a margem desce até o piso sem aprovação humana, passo a passo, com a alavanca de fechamento em
                        R$; a carteira continua a da 130-A. 📊 ensaio REAL 07/10 (pedido d0bb15ba): 82 cotações · Youse
                        R$ 3.730,56 · economia até R$ 5.484 · "Tempo" escondido (495 s > teto)
RISCO ................  6 — ALCANCE 3 · REVERSIBILIDADE 2 (migration de constraint) · FREQUÊNCIA 1
SUPERFÍCIE ...........  1 — peças da 130-A e da 129-B
PISO APLICADO ........  §3.2 — migration · texto ao consumidor com número (CDC)
NÍVEL ................  🟠 ALTO · gerente Opus 5.5 · 3 builders Opus 5.5 em PARALELO · juiz ‖ red team · conserto · confirmação
O FIO ................  porta (OPCOES_DO_CANAL) → motor (4º cálculo) → comparacao (papel minima, incluir_minima) →
                        proposta.montar (resumo_do_volume, economia, selo) → mensagem.mensagem_para → comando_proposta ·
                        teste do fio + teste de COSTURA (proposta → mensagem com a mínima), que faltou e o red team pegou
PARALELISMO REAL .....  F1 (margem) ‖ F2 (mensagem) ‖ F3 (mínima) — porta.py com edições cirúrgicas em funções diferentes
UNIDADES .............  U1 margem · U2 manual por contexto · U3 mensagem do canal · U4 resumo real · U5 preset + constraint ·
                        U6 papel minima · U7 sem remuneração CNSP
COESÃO ...............  U1+U2 · U3+U4+U7 · U5+U6
TIME .................  gerente · F1 · F2 · F3 · juiz ‖ red team · conserto único · confirmação · builder da trava do tempo
REFERÊNCIA ...........  SPEC-130-A · o print do Founder (06/10) · o logo do Quem Cobra Menos (para a página futura)
GATES ................  G1–G9 (SPEC §4)
O ELO ................  "o número de cotações é o número de preços que voltaram nas OPÇÕES": medido contra o banco real (82) e
                        guardado com linha de controle (o recálculo de volta → 104 → vermelho)
FAIXA DE RELÓGIO .....  💭 3–4 h · 📊 ~6 h (23:15 → ~05:30), incluindo a bateria inteira (2 metades em paralelo, ~50 min)
```

## 1. O que mudou
- **A margem (D-MC-68 corrigida):** `negociacao.py` desce de `passo_pp` em `passo_pp` (15→14→13→12); 12→10 só com `fechamento=True` (o
  cliente sinalizou que fecha) — sem `precisa_aprovacao`, sem `aprovado_pelo_corretor`, sem `concorrencia_declarada` (saíram: quem
  chamar a regra velha quebra alto). A alavanca vem antes dos cortes de cobertura. `texto_da_alavanca` dá a frase em R$ ("Falei com a
  seguradora e consegui R$ 312,40 a menos no ano… Vale se você fechar comigo"), nunca "%". Trava de produto: piso nunca abaixo de 10 %,
  passo entre 0,5 e entrada − autônomo (D-130A1-12).
- **O manual por contexto (D-130A1-07):** `montar(config, contexto="carteira"|"canal")` com roteiro, objeções e FAQ na voz certa, a
  alavanca de fechamento e o follow-up (até 2 lembretes) como dado para a 133-A.
- **A mensagem do canal (D-130A1-01/02/03/06/14):** `mensagem_do_canal` (≤ 3 balões) e `mensagem_para` (escolhe pela origem). Volume =
  ofertas das OPÇÕES (nunca o recálculo); economia com a origem da conta; vencedor com o parcelado (12x em destaque quando existe) e o
  sem juros; 2 cartões; 6 por seguradora; a corretora em lista (linha sem dado some); selo do CANAL; pergunta final; "Tempo" só até 90 s.
- **O mínimo do mínimo (D-130A1-05):** preset `minima` = econômica + `carroReserva 0` (📊 0 ↔ "Não contratar" em 90/90 ofertas, 13
  seguradoras); `OPCOES_DO_CANAL`; a carteira não gasta o 4º cálculo; a mínima nunca é a 1ª nem entra no ranking da completa; diz "sem
  carro reserva" na página e no WhatsApp. 📊 efeito medido do carro reserva sozinho: −0,3 % a −6,9 % em 10 de 13 seguradoras.
- **Sem remuneração CNSP (D-130A-08 revogada):** a chave saiu da config e o campo do modelo; T-127 cancelada; P-130A-16 fechada.

## 2. Julgamento
| papel | nota | o que pegou |
|---|---|---|
| juiz | 82 | B1: "cotações realizadas" e "Tempo" contavam o RECÁLCULO (📊 22 de 104 preços; 82 reais; 495 s, não 648 s) |
| red team | 70 QUEBREI | B1: a mínima chegava ao WhatsApp dizendo "menos dias de carro reserva" (nenhum teste atravessava proposta → mensagem); B2 = o B1 do juiz; P1: a corretora vencedora podia RENOMEAR o selo ("Número 1 do Brasil"); P2: piso 3 aceito |
| conserto único | — | os 6 itens, cada um com guarda vermelho/verde; 21 testes novos; teste de COSTURA; 287 verdes |
| confirmação | **88** | 6/6 CONFIRMADOS por medição própria (15 mutantes vermelhos, controle 66 verdes); sobrou P-130A1-07 |

## 3. Testes (saída real)
- conserto: `287 passed in 131.78s` (14 arquivos do pacote + `test_spec130a1_conserto.py`)
- confirmação: `179 passed, 1 failed` (corrida com o commit do MANIFEST no meio da rodada) → `test_spec130a1_minima.py` de novo:
  `15 passed`; regressão extra `107 passed`
- a trava do tempo (D-130A1-14): ver §12

## 4. Bateria (2 metades em paralelo, worktrees `C:\wt130a1a`/`C:\wt130a1b` no commit `55f21f8`)
Ver §12 (preenchido na entrega com a saída real e a comparação com a linha de base da 130-A: 15 + 21 falhas pré-existentes).

## 5. Migration (APLICADA em produção)
`20261006_04_spec130a1_minima.sql` · versão `20261007040359` · psycopg numa transação, `lock_timeout 5s`, 0,86 s · VERIFY estrutural
ANTES `0·0·2·1` → DEPOIS `1·1·2·1` · comportamental `OK: pedido_com_minima=aceito, pedido_tres=aceito, pedido_desconhecida=recusado,
pedido_vazio=recusado, calculo_padrao=aceito, calculo_minima=aceito, calculo_desconhecida=recusado, minima_com_origem=recusado,
calculo_completa_mais=aceito, ajuste=aceito` · sobra 0 linhas · ROLLBACK no arquivo (recusa se houver linha da mínima).

## 6. O ensaio REAL (07/10, produção, nada gravado)
`python -m app.services.multicalculo.comando_proposta --pedido d0bb15ba-365b-483d-bcfe-ec363040f59f --nome Mariana` → "a mensagem do
CANAL": Vencedor em 82 comparações entre 2 corretoras e 14 seguradoras · Cotações realizadas 82 · (antes da trava: Tempo 8 min 15 s) ·
economiza até R$ 5.484 · Corretora AutoFleet com Youse, 4x de R$ 932,64 sem juros, total R$ 3.730,56 · Recomendada nota 87 · Mais em
conta R$ 2.975,96 nota 78 com o que cobre menos · 6 por seguradora · balão 3 só com nome + selo (a marca da AutoFleet NÃO está publicada →
sem SUSEP, sem anos: P-130A1-09) · "Quer fechar esse preço com a AutoFleet?". 📊 o tempo: fila 85 s, 1ª corretora 285 s, 2ª 480 s,
último 495 s — o `portal-worker` está com `concurrency: 1` (P-130A1-08).

## 7. O que ficou fora (com dono, em `PENDENCIAS.md`)
P-130A1-01 captura de marca presa/site modelo · 02 🧑 lista do Nível 5 · 03 franquia majorada não medida · 04 Reclame Aqui sem fonte ·
05 ninguém pede a mínima ainda (133-A) · 06 Ezze +100 % sem carro reserva · 07 passo fora do trecho reseta a seção · 08 🔴 o tempo não é
"em segundos" (fila + corretoras em série) · 09 🧑 a marca da AutoFleet não publicada. Riscos para o Founder: a "economia até" é a conta
mais agressiva possível (D-130A1-03, honesta mas forte) e a frase da alavanca atribui o desconto à seguradora (D-130A1-13).

## 8. Planejado (não construído)
`programa-multicalculo/PLANO-COMERCIAIS-E-CONTAS.md` (comerciais com Agger e WhatsApp próprios, o dono pelo InfoCap) ·
`programa-multicalculo/PRONTIDAO-DA-133-A.md` (travas, testadores, apólice/fotos, nível da conversa, Nível 5, o QR no admin).

## 9. Canário Amandus → Resulta → AutoFleet
Sem envio (a 130-A.1 não envia nada; quem envia é a 133-A). O ensaio real do canal foi feito sobre o pedido de teste `d0bb15ba` (Resulta
e AutoFleet comparadas; a AutoFleet venceu). Dois tenants reais nos testes da costura e do selo.

## 10. Declaração
Nenhum motor paralelo foi criado: a mensagem é uma função a mais no módulo da mensagem; a mínima é um preset do mesmo motor e uma opção
da mesma porta; a margem é a mesma `negociacao.py`; o manual é o mesmo módulo com contexto. Nenhum nome de corretora em código; os testes
que tinham "AutoFleet" passaram a um nome fictício.

## 11. Telemetria
Ver §12.

## 12. Entrega
(preenchido no fecho: bateria, trava do tempo, push com a saída colada)
