# SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta — relatório de execução

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `083eeca`

```
OUTCOME ..............  o agente coleta ANTES o que o portal pede, abre o pedido em qualquer seguradora que o portal
                        publica, LÊ o desfecho que o portal decidiu e devolve nº + franquia + próximo passo; resposta
                        desconhecida = handoff com dossiê + fila de aprendizado
RISCO ................  8 = alcance 3 + reversibilidade 3 + frequência 2
SUPERFÍCIE ...........  3
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus 5 xhigh · juiz Fable ‖ red team Fable
O FIO ................  SPEC §2 · testes: tests/test_o_fio_do_portal_de_vidros.py + test_e00110_a_costura_do_agente_ao_desfecho.py
PARALELISMO REAL .....  2 builders com arquivos disjuntos (A = journeys/vidros_* · C = app/* + freio) + 1 fatia de costura em série
UNIDADES .............  SPEC §3 (17 unidades; 3 nasceram da captura nº 1: desfecho, reparo, contato)
COESÃO ...............  SessaoVidros ↔ vidros_estado ↔ vidros_apifirst ↔ vidros_api com um dono só
TIME .................  2 leitores Opus (captura · mapa do código) · 2 builders Opus · juiz ‖ red team Fable · confirmação · docs
REFERÊNCIA ...........  interna tests/test_spec074_a_fronteira_material_executada.py · externa: proposta §13 (6 URLs)
GATES ................  G1 · G1b · G1c · G2–G9 · G11 verdes · G10 (canário) na caixa do Founder
O ELO ................  "loja/agenda aparece PORQUE opcoes-disponiveis manda": A, B e B→A medidos (bundle + 3 desfechos)
FAIXA DE RELÓGIO .....  declarada 10–14 h 💭 · real: §10
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** `docs/canon/specs/SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md` ·
**Branch:** `feat/extra-001-10-o-portal-de-vidros-ponta-a-ponta` · **Preflight** 📊 20/09/2026: `HEAD..origin/main` = 0 ·
`origin/main..HEAD` = 0 · HEAD = `083eeca` · árvore com arquivos do Founder (`.TXT`, 3 deleções, 1 teste modificado) — não tocados.

