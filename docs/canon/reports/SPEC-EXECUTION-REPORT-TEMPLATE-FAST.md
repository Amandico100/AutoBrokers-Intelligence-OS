---
> **Status:** canônico — template do relatório sob o **PROTOCOLO AAA v12 · AAA FAST** (16/09/2026)
> **Uso:** copiar para `docs/canon/reports/SPEC-<N>-EXECUTION-REPORT.md` no passo ① e preencher ao longo da execução.
> **Teto:** 15 KB (CRÍTICO) · 12 KB (PADRÃO) · 8 KB (LEVE). O guarda `test_o_protocolo_tem_policia.py` exige o card, a faixa, a bateria com rodadas, a referência, um 📊 e a nota N/100.
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `<HEAD do preflight>`

```
OUTCOME ..............
RISCO ................  0–8   alcance + reversibilidade + frequência   (§3)
SUPERFÍCIE ...........  0–3                                            (§3)
PISO APLICADO ........  qual, e por quê                                (§3.2)
NÍVEL ................  LEVE · PADRÃO · CRÍTICO · executor Opus 5 <effort> · juiz <nenhum|Opus|Fable>
UNIDADES .............  quantas, quais, e as FATIAS                    (§5.2)
COESÃO ...............  o que ficou JUNTO e por quê                    (§3.4)
PARALELISMO REAL .....  nenhum — escrita de um só; investigador read-only: <sim/não>
TIME .................  executor · juiz · escalação com o GATILHO: lente <sim/não · motivo> · confirmação <…> · red team <…>
REFERÊNCIA ...........  interna <caminho> · externa <URL da proposta>   (§7.1 · §7.3)
GATES ................
O ELO ................  "A porque B": medi A · medi B · medi que B CHEGA em A    (§0.3)
FAIXA DE RELÓGIO .....  declarada <…> · real <…> · tetos: turnos <…> · contexto <…>  (§9.2 · §10)
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** `<caminho da proposta>` · **Branch:** `feat/<slug>` ·
**Preflight** 📊 `<data>`: `HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD = `<hash>` · árvore limpa ·
**Executor:** Opus 5 `<effort>` (sessão nova) · **Juiz:** `<modelo>` · **Início / fim:** `<dd/mm hh:mm>` UTC

## 1. BLOCO 0 — as premissas que mudariam o desenho (5–10, comando ao lado)

| # | a proposta afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|---|

## 3. Migrations — APPLY · VERIFY · ROLLBACK (escritos ANTES; VERIFY contra o objeto)

## 4. O juiz fresco (`<modelo>`, sobre `<hash>`, `<n>` turnos, `<min>` min) — VEREDITO `<…>` · nota `<…>`

| # | achado | teste do produto | medição | classe | conserto |
|---|---|---|---|---|---|

Lente do dado (se o gatilho disparou): `<…>` · Confirmação pós-conserto (se disparou): `<…>`

## 5. O conserto único — o que mudou, os gates rerodados, o que virou pendência

## 6. A bateria — 📊 `<n>` rodada(s) inteira(s) · `<contagem>` · triagem por DIFF contra a linha de base

## 7. O que ficou fora, e o gatilho que o faz voltar

## 8. 📋 Caixa do Founder — o que só ele faz (Implantar, senhas, canário, decisões)

## 9. Pendências e decisões — `P-…` com dono e custo de esquecer · `D-…` com nota 0–100 às opções

## 10. Telemetria (§11) — as 8 linhas de `python backend/scripts/medir_execucao_claude_code.py --sessao atual`

```
relógio total · por fase ①–⑥ ........
turnos · contexto de pico ...........  executor · juiz · extras
ctx-tokens · saída ..................
US$ API-equivalente .................  por agente · total
agentes além do executor ............
achados por mecanismo ...............  executor · prova mecânica · juiz · lente · canário (EXCLUSIVO marcado)
rodadas da bateria ..................  inteiras · parciais
nota da execução ....................  <N>/100 — critério: <uma linha> · nota do juiz <N>/100
```

## 11. Entrega — `git push origin HEAD:main` com a saída colada · o que Implantar, em que ordem · variáveis novas por nome

## 12. Handoff (só se houver próxima fatia) — ≤ 20 linhas: o que está verde, o que resta, onde parou
