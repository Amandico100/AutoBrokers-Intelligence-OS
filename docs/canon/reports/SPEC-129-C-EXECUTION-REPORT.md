# SPEC-129-C — Mais ramos do Agger: Condomínio, Residencial e Empresarial · relatório de execução

> 11/10/2026 · branch `spec/129-C-mais-ramos` · base `8d468b4` · rito AAA v13, 🔴 CRÍTICO · SPEC `specs/SPEC-129-C-mais-ramos-do-agger.md`
> BLOCO 0 e canário em `programa-multicalculo/129-C/` · laudos no rascunho do gerente (`laudos/129c-juiz.md`, `129c-red.md`, `129c-confirmacao.md`)

**Nota da execução: 88/100** (juiz 76 · red team 62 → conserto em 2 lados → confirmação 88; o canário AO VIVO passou nos 3 ramos).

## EXECUTION CARD
```
OUTCOME ..............  o MESMO motor da 129-B calcula Condomínio (16), Residencial (2) e Empresarial (18): pedido de RE pelo
                        contrato, opções de RE (básica do pedido), corpo de RE (coberturas em configuracoes, comissão no item),
                        atividade do empresarial por seguradora, leitor e comparação de RE; config por ramo; o Agger sempre ligado.
                        📊 canário real 11/10: condomínio 3/7 com preço (Allianz R$ 8.408,79), residencial 3/8 (Tokio R$ 490,25),
                        empresarial 1/1 (Allianz R$ 2.072,76), ~47 s do envio ao último preço, 0 erro de contrato do Agger
RISCO ................  7 — ALCANCE 2 · REVERSIBILIDADE 3 · FREQUÊNCIA 2
SUPERFÍCIE ...........  2 — o motor, o montador e o leitor da 129-B ganham o ramo
PISO APLICADO ........  §3.2 — robô em portal real · dado de cliente real no canário
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz ‖ red team · conserto · confirmação
O FIO ................  porta → motor → robô (RE) → montador → calcularV2 → leitor → ofertas → comparação · teste
                        `test_spec129c_o_fio.py` (as 9 gravações reais + retomada) + o canário AO VIVO
PARALELISMO REAL .....  B0-a ‖ B0-b ‖ B0-c ‖ F0 → F1 ‖ F2 → costura → canário ‖ juiz ‖ red team → conserto portal ‖ conserto app
UNIDADES .............  U1–U9 (SPEC §1)
COESÃO ...............  F1 portal · F2 app · costura+canário
TIME .................  gerente · 3 investigadores · F0 · F1 · F2 · costura · canário · juiz ‖ red team · 2 consertos · confirmação
REFERÊNCIA ...........  interna: 129-B, 128, 130-A · externa: o app do Agger (bundle de 11/10)
GATES ................  G1–G9 (SPEC §5)
O ELO ................  "o corpo de RE é o que o Agger aceita PORQUE a forma vem das gravações reais": 9 gravações no teste + 3
                        cálculos reais aceitos (HTTP 201)
FAIXA DE RELÓGIO .....  💭 8–12 h · 📊 ~11 h
```

## 1. O que mudou
- **F0 — o Agger sempre ligado:** a conta global sem janela (📊 a "seg-dom 00:00–23:59" deixava 23:59–00:00 fora); um pedido já começado
  não espera a janela; as 2 contas de produção convertidas; o horário vira regra do auxiliar (131-0 §8-A).
- **BLOCO 0:** 📊 a InfoCap da Resulta quase não tem RE (0/12/3 em 32.901); a fonte é o Agger — 45 negócios lidos (15 por ramo), 9
  gravações reais saneadas; seguradoras com preço: Tokio/Porto/HDI (condomínio), Allianz (residencial), HDI/Porto/Allianz (empresarial);
  básica típica R$ 14 mi / R$ 550 mil / R$ 2 mi; reajuste de renovação: +10 % o mais comum (16 de 41), mediana +13,3 %.
- **F1 (portal):** contrato do pedido de RE, opções de RE, montador e robô de RE, atividade do empresarial (`atividade_empresarial.py`),
  leitor de RE; o auto byte a byte (hashes `8d3160…`/`62eb12…`).
- **F2 (app):** pedido/porta/config/comparação por ramo; o canal (QCM) só auto.
- **Costura:** retomada com o ramo, evento "sem atividade compatível", a guarda barra `calcularV2` com query, a renovação de RE exige os 4
  campos da tela, o defeito de `chave_no_corpo` (extras com nome errado).
- **Conserto:** a atividade só casa com todas as palavras do pedido (📊 "estética automotiva" 8/8 errado → 0/8; "clínica de estética" 8/8
  certo); a Básica nunca muda no ajuste; a RC somada entendida (a Allianz R$ 4.870,41 volta ao 1º no condomínio_3); "não informou" ×
  "cobre menos"; a régua contra o pedido; teto de comissão; a econômica tira extras; o motivo da recusa gravado (migration `20261011_01`).

## 2. Julgamento
juiz 76 (B1 atividade, B2 Básica no ajuste) · red team 62 (B1 atividade, B2 RC somada; 8 pendências) → conserto portal ‖ app →
confirmação **88** (os 4 blockers fechados por medição; 3 ataques novos de atividade saem; auto igual).

## 3. Migration (APLICADA)
`20261011_01_spec129c_motivo_do_evento` · versão `20261011071430` · VERIFY `0·0·0` → `1·1·0` · comportamental `OK: 301 recusado, vazio
recusado, 300 e nulo aceitos` · 0 linhas sobrando.

## 4. Bateria (1 rodada inteira: 2 metades em paralelo, worktrees no commit `95b4678`)
- metade 1: `10 failed, 3204 passed, 3 skipped in 1338.57s` — 1 nova: o G8 da proposta (`.limit(50)` colidiu com o teto de comissão 50 da
  config) → consertado (`f194fe7`), `37 passed`
- metade 2: `31 failed, 2825 passed, 6 skipped, 31 xfailed, 1 xpassed in 4727.59s` — 2 novas, scripts de guarda antigos: isolados,
  `test_o_humano_da_seguradora_e_atendido` passa; `test_o_vocabulario_viaja_na_imagem` passa direto (UTF-8) e pelo runner `1 passed in
  118.13s` (o limite é 120 s — tempo, não regressão)
- **0 regressão de produto.**

## 5. Fora (com dono)
P-129C-01 o PDF não é guardado (📊 0/128 também no auto) · 02 🧑 onde está a carteira patrimonial da Resulta · 03 🧑 o reajuste 15 × 10 %
· 04 🧑 credenciais de RE da Porto/Mapfre/HDI no Agger · 05 a página de RE (130-C) · 06 a atividade medida só em 1 amostra ao vivo.

## 6. Declaração
Nenhum motor paralelo: o mesmo motor, robô, montador, leitor, porta e comparação da 129-B/130-A ganharam o ramo. Nenhum nome de corretora
em código; as fixtures sem dado pessoal (varredura 0).

## 7. Entrega
Push do código, da migration, do relatório e da bateria (11/10):
```
   8d468b4..c3a7495  HEAD -> main
```
Push do estado, da fila, das decisões D-129C-01…09 e do painel (`docs(129-C): estado, fila, decisões e painel`):
```
   c3a7495..d5691fe  HEAD -> main
   c3a7495..d5691fe  HEAD -> spec/129-C-mais-ramos
```
Painel do Founder republicado: https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0 (versão 34).
