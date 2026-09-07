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

**Aquecimento (Opus 5, contexto limpo, 07/09/2026, 📊 138.341 tokens · 34 tool uses · 6m52s):** nota **86**; as duas afirmações falsas assinadas foram refutadas pelo comando (`test_send_number` devolve `""` fora de `test` → `_send_test_messages` retorna `[]`; o entrelaçamento leitura `:1027` → envio `:1067` → gravação `:1105`); 11 emendas, todas aplicadas na SPEC v1.1 §0.5. **Dois defeitos materiais que a minha SPEC não via:** (1) `registrar_retorno` estava proposto dentro do background, mas `webhook.py:1366-1372` faz `observer_tap` **no endpoint** e retorna antes — com observador + agente desligado (= a Resulta hoje) o hook nunca rodaria; migrou para o endpoint, G24/M15 nascem; (2) a reserva por `ignore_duplicates` do PostgREST não infere índice único parcial (42P10 / 23505 estourado) — virou função no banco (`billing_reservar_obrigacao`), G25/M16 nascem. Também: `avisar_suporte_humano` não recebia `cfg` (3 chamadas; 📊 2 grupos `…@g.us` ativos) → parâmetro `suprimir` + G26; atendente excluída do contexto (G27); `incerto` não liberável; `portal_key` vazio retido; um telefone de teste real como placeholder em `PainelDeRotinas.tsx:861` (PII no repo) → máscara. O card do aquecimento pediu SUPERFÍCIE 4 (não existe na escala; mantido 3 com o 6º hub `observer_intake.py` anotado) e faixa 10–13 h (aceita: faixa passa a **8–13 h**).

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

### `20260907_01_spec_extra001_billing_sent_log_estados.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | `billing_sent_log` ganha estado por componente, identidade da obrigação `(company_id, portal_key, recibo)` para os modos reais e as funções de reserva/reclamação atômicas |
| **Expand-first** | sim — 20 `ADD COLUMN IF NOT EXISTS` (todas nulas ou com default), 2 índices parciais `IF NOT EXISTS`, 2 `CREATE OR REPLACE FUNCTION`; nenhum DROP, nenhum backfill |
| **Destrutiva** | não |
| **APPLY** | aplicada em produção em 07/09/2026 via MCP `apply_migration` (`spec_extra001_billing_sent_log_estados`) → `{"success":true}`; o texto aplicado é o do arquivo canônico (com o ajuste `colisao_recibo` já dentro) |
| **VERIFY** | 📊 07/09/2026 · V1 `count(*)` das 20 colunas = **20** · V2 `pg_indexes` = **2** linhas, ambas `WHERE (send_mode = 'real'::text)` · V3 `pg_proc` = **2** funções com a assinatura do contrato · V4 contra o **Postgres real**, tenant Resulta, `canario=true`: 1ª reserva `ganhou=true, status=reservado`; 2ª (mesma obrigação, modalidade diferente) `ganhou=false`, **mesmo id**; 3ª (outro `portal_key`, mesmo recibo) `ganhou=false, status=colisao_recibo`; `billing_reclamar_obrigacao` a partir de `reservado` → **false**; com `company_id` de outro tenant → **false**; a linha do VERIFY apagada por `id + company_id + canario + recibo` (1 linha) · V5 controle `count(*) where send_mode='test'` = **0** antes e depois |
| **ROLLBACK** | escrito no cabeçalho do arquivo: `DROP FUNCTION ×2` → `DROP INDEX ×2` → `DROP COLUMN ×20`; seguro enquanto não houver linha `send_mode='real'` (📊 0 hoje); mensagens já enviadas não se desfazem |
| **Aplicada em produção** | sim · 07/09/2026 · versão registrada pelo MCP |
| **MANIFEST atualizado** | sim (linha da U1; classe passa de ⏳ para APLICADA neste relatório) |

**Advisors antes:** 📊 security 133 (2 ERROR · 9 WARN · 122 INFO)
**Advisors depois:** 📊 security 133 (2 ERROR · 9 WARN · 122 INFO)
**Diferença:** nenhuma. As duas funções novas declaram `SET search_path = public, pg_temp` — não entram no `function_search_path_mutable` (que continua listando só os 3 triggers antigos).

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
