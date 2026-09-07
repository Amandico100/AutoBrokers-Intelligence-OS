# Relatório de execução — SPEC-EXTRA-001: A operação dos pilotos

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  a corretora escolhe ENCAMINHAR PARA A EQUIPE (atendente recebe nota interna + texto limpo + PDF) ou ENVIAR AO CLIENTE
                        (segurado recebe texto limpo + PDF pelo WhatsApp já pareado); cada parcela é cobrada UMA vez, com reserva antes do
                        efeito e estado por componente; a resposta do cliente chega ao atendimento com o caso certo e fica registrada mesmo
                        com o agente desligado; toda falha vira pendência visível; observador, QR, sessões e o modo teste de 17/08 não mudam
RISCO ................  8 = ALCANCE 3 + REVERSIBILIDADE 3 + FREQUÊNCIA 2
SUPERFÍCIE ...........  3 (📊 5 arquivos-hub: billing_collection 1.799 · platform_outbound 1.209 · webhook 1.997 · PainelDeRotinas 1.057 · rotinas/route.ts)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" + migration de estrutura em billing_sent_log → CRÍTICO
NÍVEL ................  CRÍTICO · opção B (desenhista · 2 lentes + red team · juiz fresco)
UNIDADES .............  U0 medir · U1 motor+porta+migration · U2 respostas/convivência · U3 tela e rotas Next · U4 guardas · U5 canário · U6 docs/dossiê
COESÃO ...............  U1 = billing_collection + platform_outbound + migration (a porta) · U2 = billing_replies + webhook · U3 = Next (PainelDeRotinas hub)
PARALELISMO REAL .....  U1 ∥ U3 em arquivos disjuntos · U2 depois de U1 · integração serial
TIME .................  investigador+pesquisador (orquestrador) · aquecimento Opus · desenhista Opus · builders Opus (3) · verificador Sonnet ·
                        lentes verdade+regressão e produto+DADO · red team · juiz fresco
REFERÊNCIA ...........  interna: CLAUDE.md §7 · test_a_cobranca_esta_como_estava.py (34/34) · test_spec078_bloco_a_seguranca.py (39/39) ·
                        send_to_client_guarded · canario_098.py · externa: SPEC §7 (Postgres constraints · AWS outbox · Stripe webhooks · WhatsApp policy)
GATES ................  gate zero VERMELHO · G00–G23 (SPEC §8) · mutações M1–M14 por nome · canário Q1–Q6 · suíte inteira · push
O ELO ................  "o cliente não recebe PORQUE a porta exige o agente ligado e escolhe integração sem para=auxiliar" — A medido (4/4 agentes
                        desligados), B medido (platform_outbound.py:948-990 · integration_service.py:274-298), B chega em A ✅ (o ramo live nunca
                        chama a porta; chamando, cairia em agente_desligado/sem_canal)
FAIXA DE RELÓGIO .....  declarada 8–11 h · real: (preencher)
ORÇAMENTO ............  ≤ 2,5 M tokens de subagentes · gasto: (preencher)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?           (preencher)
② a AUDITORIA / juiz fresco? (preencher)
③ pendências por VALOR MARGINAL: (preencher)
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md`
**Branch:** `feat/spec-extra-001-operacao-pilotos`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 07/09/2026: HEAD = origin/main = `34424fa`, 0 atrás, 0 à frente)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (aquecimento, desenhista, builders, lentes, red team, juiz) · Sonnet 5 (mecânico)
**Início:** 07/09/2026 · **Conclusão:** (preencher)
**Commit inicial:** `34424fa576f8fdb35f687e3a3af5c66a6e07f915`
**Commit final:** (preencher)
**Estado final:** (preencher)

---

## 0. Declaração de integridade
- [ ] Nenhum motor paralelo foi criado.
- [ ] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
- [ ] Nenhum DDL monolítico foi aplicado.
- [ ] Nenhum segredo foi exposto (telefones de teste só por alias; `to_phone` do ledger é dado da própria corretora e não aparece em log/relatório).
- [ ] Nenhum escopo foi reduzido sem decisão registrada.
- [ ] Nenhum dado atravessou tenants.
- [x] `CLAUDE.md`, protocolo, glossário, decisão do ritmo, proposta e research pack lidos no início.

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | RISCO | SUP | piso? | time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| U1 motor + porta + migration | 3 | 3 | 2 | 8 | 3 | §3.2 envia + migration | desenhista · builder A · verificador · painel · juiz fresco |
| U2 respostas / convivência | 3 | 2 | 2 | 7 | 2 | §3.2 (toca o webhook do atendimento) | builder B · painel |
| U3 tela e rotas Next | 2 | 2 | 1 | 5 | 2 | herda o piso do lote | builder C · verificador · painel |
| U4 guardas · U5 canário · U6 docs | 0 | 0 | 0 | 0 | 1 | — | desenhista · orquestrador |

**Telemetria (§11):** (preencher ao fim)

**RP0 (integridade dos insumos):** research pack `3ce221c0dca9600d0bcd5b568866e0c42d50b6ef0c2695f4d202a7a106d9a911` ✅ igual ao declarado na proposta. Proposta: entrada `e62b12bd71d3c6c4…` → cópia canônica sanitizada `5d23fc3d636bd1ae…` (telefones → aliases; cabeçalho registra a transformação). Prompt: `12ff4737…` → `39b61d27…`. LEIA-ME `ac6b6dcb…` sem alteração. Manifesto SHA-256 não veio no pacote; a prova é o hash cruzado da proposta.

**Aquecimento:** (preencher)

**O laço:** (preencher)

**Blockers rebaixados a pendência:** (tabela vazia = nenhum)

**Pendências tocadas:** ver SPEC §12; estado final na §0.1 ao fechar.

---

## 1. Resumo executivo
(preencher)

## 2. Escopo executado por bloco
(preencher)

## 3. Arquivos alterados
(preencher)

## 4. Migrations
(preencher com APPLY/VERIFY/ROLLBACK)

## 5. Testes executados
(preencher com saída real)

## 6. Canário e rollout
(preencher)

## 7. Gate da SPEC
(preencher)

## 8. Mudanças além do texto da SPEC
(preencher)

## 9. Decisões registradas
(preencher)

## 10. Riscos remanescentes
(preencher)

## 11. Impacto para o corretor
(preencher)

## 12. Estado do Master Plan
(preencher)

## 13. ROLLBACK da SPEC inteira
(preencher)

## 14. A entrega (`git push`) — saída colada
(preencher)

## 📊 A BATERIA
(preencher)
