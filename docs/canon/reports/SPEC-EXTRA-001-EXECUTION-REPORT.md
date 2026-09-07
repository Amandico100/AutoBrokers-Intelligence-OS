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

A corretora passa a escolher, na tela do Auxiliar de Cobrança, entre **Encaminhar para minha equipe** (a atendente recebe uma nota interna, o texto final limpo e o PDF, e repassa ao cliente) e **Enviar diretamente ao cliente** (o segurado recebe texto limpo + PDF pelo WhatsApp já pareado da corretora). Antes desta SPEC, "enviar ao cliente" era uma frase no relatório (📊 `billing_collection.py:1734-1737` em `34424fa`) e o modo de aprovação criava um pedido que ninguém consumia.

Cada parcela é cobrada **uma vez**: a obrigação `(corretora, seguradora, recibo)` é **reservada no banco antes do efeito** por uma função Postgres (o índice único parcial não é inferido pelo PostgREST — achado do aquecimento), o estado é registrado por componente (texto/PDF), "incerto" nunca é repetido às cegas, trocar de modo ou de dia não reabre a cobrança, e um recibo igual ao de outra seguradora é **retido** com incidente em vez de virar "já cobrado". A porta única do WhatsApp ganhou conexão fixada e revalidada no instante do efeito, autorização de Auxiliar independente do interruptor do atendimento, documento, e uma allowlist de canário que exige remetente **e** destinatário autorizados.

O cliente que responde é ouvido **mesmo com o agente de atendimento desligado** (📊 4/4 hoje): o retorno é registrado no endpoint do webhook, antes de o observador consumir, e vira pendência na tela; o atendimento (quando ligado) recebe o bloco do caso em vez de uma nota genérica. A atendente **não** é interlocutor — nem para ler o caso, nem para encerrá-lo (o blocker que as duas lentes acharam e o conserto fechou com par de guarda). Observador, QR, sessões e o modo teste de 17/08 não mudaram (34/34 byte a byte).

**Ficou de fora, com gatilho:** e-mail/Meta/segundo QR (099), reenvio automático de 2ª via a pedido do cliente (tarefa da equipe), régua de lembretes, resposta automática viva no canário (caixa do Founder). **Não comprovado ao vivo ainda:** Q1–Q6 do canário e o 23505 concorrente no Postgres — só rodam dentro do smith-api implantado (sem Redis o governador recusa mensagem fria, e isso está certo).

## 2. Escopo executado por bloco

### U1 — motor, porta e migration
| Entrega prevista | Estado | Evidência |
|---|---|---|
| modos `equipe`/`cliente` com motor; `approval`/`live` retidos | CONCLUÍDA | `normalize_billing_config`, `_entregar_cobranca_real`; [G02] + M2 |
| pacote humano limpo (nota interna + texto final + PDF) | CONCLUÍDA | `_pacote_humano`; [G03] + M3 |
| ledger com estados por componente e reserva antes do efeito | CONCLUÍDA | migration `20260907_01` aplicada, `billing_reservar_obrigacao`; [G06]–[G11], [G19]; VERIFY §4 |
| porta com conexão fixada, autorização de auxiliar, documento, `enfileirar=False`, allowlist | CONCLUÍDA | `send_to_client_guarded`; [G01], [G12] + M1, M12 |
| aviso ao grupo suprimido no canário; incidentes em Atividades | CONCLUÍDA | [G17], [G26] + M18 |
| `work_run_id` da ponte até o ledger | PARCIAL (P-098-RUN-NOS-JOBS) | `routine_engine`, `workflows.bridge_rotina` |

### U2 — respostas e convivência
| Entrega prevista | Estado | Evidência |
|---|---|---|
| bloco do caso no atendimento, atendente excluída | CONCLUÍDA | `contexto_de_cobranca`; [G13], [G27] + M13, M19 |
| retorno registrado no ENDPOINT antes do observador | CONCLUÍDA | `registrar_retorno` + hook; [G24] + M15; corpus 43/43 [G14] |
| a atendente não encerra o caso (conserto do painel) | CONCLUÍDA | [G28] em par + M21 |
| takeover/URA intactos | CONCLUÍDA | [G15] diff vazio em `o_fim_do_atendimento.py`; [G16] |

### U3 — tela e rotas Next
| Entrega prevista | Estado | Evidência |
|---|---|---|
| 4 modalidades, `team_number`, confirmação, legado retido, placeholders mascarados | CONCLUÍDA | `PainelDeRotinas.tsx`; mjs verde; `tsc` |
| rotas `pendencias`/`encaminhado`/`liberar` com 401/404/409/400 | CONCLUÍDA | mjs [G18]; `next start` + requisição real (§5) |

### U4 — guardas · U5 — canário · U6 — docs
| Entrega prevista | Estado | Evidência |
|---|---|---|
| gate zero vermelho em cópia limpa; mutações por nome | CONCLUÍDA | 32 vermelhos em `50d2b4e`; `--mutar` (§5) |
| canário Q1–Q6 | ESCRITO, NÃO RODADO AO VIVO | `canario_extra001.py`; censo `--dry-run` verde; rota admin; depende do Implantar (§6) |
| EXTRA reconhecida pela polícia do protocolo | CONCLUÍDA | `test_o_protocolo_tem_policia.py` com controle |
| SPEC, relatório, INDICE, ESTADO, FOUNDER-DECISIONS, CHANGE-ADDENDA, PENDENCIAS, dossiê | CONCLUÍDA | commits §3 |

**Entregas da SPEC que NÃO foram executadas:** nenhuma da §2 obrigatória. A prova viva (canário) ficou dependente do Implantar, com o motivo medido (Redis) e o mecanismo pronto.

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

### 6.1 Estado separado (proposta §18)

| marco | evidência exigida | estado |
|---|---|---|
| Implementado e gateado | commits `50d2b4e…` · guarda 155/155 · mutações · painel · juiz fresco | (preencher ao fechar) |
| Entregue na main | SHA remoto + saída do `git push` | (preencher §14) |
| Implantado | `code_fingerprint` do `/health` diferente de `9c8c9f09bd153538` (📊 07/09 antes do deploy) + `POST /api/admin/canario/extra001/plano` com chave respondendo 200 | **pendente do clique Implantar** (🧑) |
| Validado no canário autorizado | Q1–Q6 pela rota admin, com aliases | **pendente**: só roda no implantado (P-E001-CANARIO-VIVO-NO-IMPLANTADO). Censo local (`--dry-run`, 📊 07/09): conexão da Resulta = observer `connected`, remetente …4743 = TESTE-A, destino …7463 = TESTE-B, os dois na allowlist |
| Validado pelas pilotos | feedback de Saionara/Regina registrado pelo Founder | não iniciado — roteiro em `docs/canon/ROTEIRO-VALIDACAO-EXTRA-001-ATENDENTES.md` |
| Ativado em linhas operacionais | fora da autorização | **não realizado, não presumido** |

### 6.2 Ordem de implantação — medida, não copiada da 098

📊 `app/api/dashboard/rotinas/route.ts` novo grava `send_mode ∈ {equipe, cliente}`; o `normalize_billing_config` **antigo** (`billing_collection.py:403-405` em `34424fa`) devolve `test` para qualquer valor fora de `{test, approval, live, none}`. Web nova + API antiga = uma rotina salva como "Enviar ao cliente" executaria como **teste** (para o `test_number`, que pode estar vazio → nada sai, mas a tela mentiria). API nova + web antiga = a web só oferece `test/none`, a API entende os dois → inócuo.

**Ordem: smith-api PRIMEIRO, smith-web DEPOIS.** Sem migration pendente (já aplicada). Variáveis novas no smith-api (🧑): `BILLING_CANARIO_ALLOWLIST` (os dois números de teste, só dígitos com 55, separados por vírgula) e `CANARIO_TESTE_B` (o número que recebe). Nenhuma variável nova para a operação normal.

### 6.3 Canário (Q1–Q6) — preencher depois do Implantar

| Q | o que prova | resultado |
|---|---|---|
| Q1 | equipe: 3 mensagens em TESTE-B; ledger `entregue_equipe`, `canario=true` | pendente |
| Q2a/Q2b | cliente: 0 envios até liberar; depois texto + PDF | pendente |
| Q3 | reexecução: 0 envios | pendente |
| Q4 / Q4-vivo | retorno "já paguei" → `contestado` + atividade; a resposta REAL de TESTE-B pelo webhook | pendente |
| Q5 | destino fora da allowlist → `fora_da_allowlist`, 0 envios | pendente |
| Q6 | limpeza por id: ledger 0 · platform_sends 0 · atividades 0 · PDF removido | pendente |

**Flags criadas ou alteradas:** nenhuma flag de produto. `canario` é campo de config gravado só pelo script/rota do canário; a tela nunca o expõe.
**Auto-pause configurado:** o freio existente (`parar_envios`) continua valendo para a cobrança real (a porta consulta `envios_parados`).

## 7. Gate da SPEC
(preencher)

## 8. Mudanças além do texto da SPEC

| ID em `CHANGE-ADDENDA.md` | Classe | Estado | Resumo |
|---|---|---|---|
| 07/09 · peça da Cobrança nunca publicada | ESSENCIAL | feita | `NameError` engolido desde a 095; consertado em U1 |
| 07/09 · rota admin do canário | ESSENCIAL | feita | o canário vivo roda onde há Redis, atrás da chave interna |
| 07/09 · EXTRA na polícia do protocolo | ESSENCIAL | feita | `SPEC-EXTRA-NNN` → sob a v11 |
| 07/09 · colisão de recibo | ESSENCIAL | feita | `colisao_recibo` retido com incidente; migration 02 devolve id NULL |
| 07/09 · telefones reais como placeholder | ESSENCIAL | feita | máscara na tela; guarda mjs |
| 07/09 · guardas vizinhos migraram o fato | VALIOSA | feita | `rotina-mora-no-auxiliar`, `test_spec023` |

## 9. Decisões registradas

| ID em `FOUNDER-DECISIONS.md` | Assunto | Estado |
|---|---|---|
| D-E001-01…10 | as decisões do Founder que governam a EXTRA-001 | registradas 07/09 |
| (caixa) | ligar o agente da Resulta por uma janela para a resposta viva | não decidido |

## 10. Riscos remanescentes e dívida assumida

| Risco | Severidade | Por que foi aceito | Onde será fechado |
|---|---|---|---|
| Q1–Q6 e o 23505 concorrente ainda não provados ao vivo | alta (é a prova do produto) | só rodam no implantado; mecanismo pronto (rota admin) | depois do Implantar, nesta mesma SPEC (caixa do Founder) |
| `incerto` depende de uma 2ª escrita que pode falhar pelo mesmo motivo | média | `reservado` também nunca é reclamado e aparece no relatório | P-E001-INCERTO-ESCRITA-DUPLA |
| hook do retorno no caminho quente de todo inbound (teto 2 s) | média | 1 SELECT por mensagem; falha nunca derruba o atendimento | P-E001-ROUTINES-POR-INBOUND (cache) |
| a constraint antiga `(company_id, recibo, send_mode)` continua não-parcial | baixa | colisão vira retenção com incidente, nunca silêncio | migration futura que a torne parcial (099) |
| `status='entregue'` legado não vira `contestado` | baixa | 📊 0 linhas legadas | P-E001-LEGADO-ENTREGUE-NAO-CONTESTA |
| ledger sem vencimento/valor | baixa | o bloco diz que não tem | P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR |

## 11. Impacto para o corretor

Hoje a corretora consegue: escolher se o boleto atrasado vai para a **equipe** (pacote pronto para repassar, com uma nota dizendo de quem é) ou **direto para o cliente**; saber que **nenhum cliente recebe a mesma parcela duas vezes** (nem trocando de modo, nem no dia seguinte, nem com duas execuções ao mesmo tempo); ver na tela **o que ficou pendente e por quê** em português (texto foi e PDF não; não sei se saiu; cliente respondeu "já paguei"; cliente pediu para não receber); marcar "encaminhado ao cliente" e "liberar reenvio" com motivo; e ser avisada quando um cliente responde à cobrança, mesmo com o agente de atendimento desligado. O grupo de suporte deixa de ler "enviado" quando o boleto foi para a própria equipe.

O que ainda **não** vê: a prova viva de ponta a ponta (depende do Implantar + duas variáveis + o clique na rota do canário) e a resposta automática ao cliente (depende de ligar o agente).

## 12. Estado do Master Plan

- [x] `INDICE-DE-SPECS.md` e `ESTADO-DAS-SPECS.md`: EXTRA-001 em execução; 099→114 pausadas sem renumerar.
- [x] `FOUNDER-DECISIONS.md`: D-E001-01…10.
- [x] `CHANGE-ADDENDA.md`: 6 adendas.
- [x] `MANIFEST.md`: migrations 20260907_01 e 20260907_02 (aplicadas).
- [x] `PENDENCIAS.md`: 12 P-E001-*.

**Próxima etapa do plano:** EXTRA-002 · investigação Agger (proposta a escrever em chat novo). Depois 099 (canais, após os pilotos).
**Pré-condições:** Implantar esta SPEC; canário Q1–Q6 verde no implantado; roteiro com Saionara/Regina conduzido pelo Founder.

## 13. ROLLBACK da SPEC inteira

```text
1. aplicação: reverter os commits da branch (git revert em ordem inversa); a API antiga normaliza equipe/cliente para 'test' —
   uma rotina configurada em modo real passaria a rodar como TESTE (para o test_number), então antes de reverter, pôr as rotinas
   de cobrança em 'none'.
2. flags: nenhuma. Retirar BILLING_CANARIO_ALLOWLIST e CANARIO_TESTE_B do smith-api.
3. banco: ROLLBACK das migrations 20260907_02 (reaplicar os corpos da 01) e 20260907_01 (DROP FUNCTION ×2, DROP INDEX ×2,
   DROP COLUMN ×20) — só seguro sem linhas send_mode='real' (📊 0 hoje).
4. side effects já executados: mensagens enviadas não se desfazem; o ledger fica (é a prova de que saíram).
5. o que NÃO é reversível: as mensagens do canário (TESTE-A → TESTE-B) e as linhas de agent_activities do período.
```

## 14. A entrega (`git push`) — saída colada
(preencher)

## 📊 A BATERIA
(preencher)
