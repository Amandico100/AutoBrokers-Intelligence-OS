# SPEC-EXTRA-001 — A operação dos pilotos: a cobrança chega a quem deve, e o atendimento continua inteiro

> **SPEC definitiva** convertida MEDINDO pelo orquestrador (Fable 5.1) em 07/09/2026, sob o
> **Protocolo AAA v11.2 + opção B** (`DECISAO-DO-RITMO-03-09-2026.md`). Proposta de origem:
> `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md` (v1.0, 07/09, hash de entrada
> `e62b12bd…`; cópia canônica sanitizada `5d23fc3d…`). Research pack `3ce221c0…` — conferido byte a byte.
> **v1.1** · emendada pelo aquecimento (§0.5).
>
> **Branch:** `feat/spec-extra-001-operacao-pilotos` a partir de `34424fa` (= `origin/main` em 07/09/2026, 0 atrás / 0 à frente).
> **Relatório:** `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md`.
> **Numeração:** família EXTRA. 099→114 continuam existindo, pausadas, sem renumerar (D-E001-08).

---

## 0. O EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  a corretora escolhe, na tela do Auxiliar de Cobrança, entre ENCAMINHAR PARA A EQUIPE (a atendente recebe
                        o pacote final: texto limpo + PDF, mais uma nota interna separada) e ENVIAR AO CLIENTE (o segurado recebe
                        texto limpo + PDF pelo WhatsApp já pareado); cada parcela é cobrada UMA vez, com reserva antes do efeito e
                        estado verdadeiro por componente; a resposta do cliente chega ao atendimento com o caso certo; toda falha
                        vira pendência visível; observador, QR, sessões e o modo teste de 17/08 ficam como estão
RISCO ................  8 = ALCANCE 3 (o SEGURADO recebe cobrança) + REVERSIBILIDADE 3 (mensagem sai do prédio) + FREQUÊNCIA 2
SUPERFÍCIE ...........  3 — o efeito atravessa rotina → portal → documento → porta de saída → webhook → agente → painel; 📊 5 arquivos-hub
                        (billing_collection 1.799 linhas · platform_outbound 1.209 · webhook 1.997 · PainelDeRotinas 1.057 · rotinas/route.ts)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" + "migration que altera estrutura" (billing_sent_log) → CRÍTICO
NÍVEL ................  CRÍTICO · opção B: desenhista antes do código · 2 lentes (verdade+regressão · produto+DADO) + red team · juiz fresco
UNIDADES .............  U0 medir · U1 motor (modos, pacote, ledger com reserva, porta de saída com documento e conexão fixada, migration) ·
                        U2 respostas e convivência (contexto do caso no atendimento, retorno do cliente registrado, takeover preservado) ·
                        U3 tela e rotas Next (modalidades, pendências, encaminhado/liberar) · U4 guardas (gate zero, mutações, EXTRA na polícia) ·
                        U5 canário autorizado · U6 documentação e dossiê
COESÃO ...............  U1 = billing_collection.py + platform_outbound.py + migration (mesmo contrato: a porta de saída) — UM builder ·
                        U2 = billing_replies.py (novo) + webhook.py — UM builder, depende do contrato de U1 (função e colunas fixadas aqui) ·
                        U3 = Next (PainelDeRotinas.tsx é hub, UM dono) — disjunto de U1/U2 · U4 desenhista, antes de U1–U3
PARALELISMO REAL .....  U1 ∥ U3 (arquivos disjuntos) · U2 depois de U1 · integração SERIAL pelo orquestrador
TIME .................  investigador+pesquisador (o orquestrador, medido nesta conversão) · aquecimento Opus · desenhista Opus · 3 builders Opus ·
                        verificador Sonnet · lente verdade+regressão · lente produto+DADO · red team · juiz fresco (§6.1)
REFERÊNCIA ...........  interna: CLAUDE.md §7 (dois tenants) · `backend/tests/test_a_cobranca_esta_como_estava.py` (34/34, o modo teste não muda) ·
                        `test_spec078_bloco_a_seguranca.py` (39/39) · `platform_outbound.send_to_client_guarded` (a porta única) · `canario_098.py`
                        (forma do canário) · externa: §7 desta SPEC (Postgres constraints · AWS outbox · Stripe webhooks · WhatsApp Business Policy)
GATES ................  G00–G23 da proposta, mapeados em §8 para comandos; gate zero VERMELHO em cópia limpa; mutações M1–M14 por nome; canário Q1–Q6
O ELO ................  "o cliente não recebe PORQUE a porta exige o agente ligado e escolhe integração sem `para=auxiliar`" — A (0 agentes ligados,
                        📊 SELECT em `agents`), B (`platform_outbound.py:948-990` + `integration_service.py:274-298`), B chega em A ✅ (ramo `live` de
                        `billing_collection.py:1736` nunca chama a porta; se chamasse, cairia em `agente_desligado`/`sem_canal`)
FAIXA DE RELÓGIO .....  8–11 h de trabalho · em 2 janelas prováveis
ORÇAMENTO ............  ≤ 2,5 M tokens de subagentes (CRÍTICO). Estourou → menos lentes, nunca menos mutação
```

### 0.1 O que NÃO muda (a fronteira que o guarda de regressão mede)

- O **modo teste** de 17/08 (`send_mode='test'`): destino `test_number`, prefixo `[TESTE AutoBrokers…]`, dedup desligada por padrão, `liberar-reenvio` apaga só `test`. 📊 `test_a_cobranca_esta_como_estava.py` 34/34 antes e depois.
- O **observador não desliga**, o **QR não é refeito**, nenhuma linha de `integrations` é criada, renomeada ou desativada. Nome de instância continua vindo de `channel_identity.nome_da_instancia`.
- O interruptor do atendimento (`agents.is_active`) continua governando **quem responde**. Esta SPEC não o liga em corretora nenhuma.
- O corredor/dispatch com seguradora não é tocado; `INSURER_DISPATCH_LIVE=false` e `DISPATCH_FINALIZE_MODE=test` (📊 env de produção lido em 07/09) continuam sendo o freio.

### 0.2 As decisões do Founder que governam (registradas em FOUNDER-DECISIONS como D-E001-01…10)

D-E001-01 prioridade = fechar cobrança e preservar atendimento · 02 Evolution Go fica · 03 cobrança e atendimento no MESMO número da corretora, sem segundo QR · 04 dois modos reais: equipe e cliente · 05 no modo equipe o texto e o PDF vão prontos, sem marca de teste · 06 respostas, anti-repetição e avisos são parte do produto · 07 testes vivos só entre TESTE-A e TESTE-B · 08 família EXTRA · 09 Agger depois · 10 dossiê atualizado por bloco.

### 0.3 A autorização de teste (fronteira de todo pacote)

- Allowlist privada de canário: **TESTE-A** e **TESTE-B** (valores reais só no env `BILLING_CANARIO_ALLOWLIST` e no `ATTENDANT_INBOUND_ALLOWLIST` de produção, nunca no repositório).
- 📊 Medido em 07/09/2026 (`SELECT … FROM integrations`): a conexão **ativa e conectada da Resulta** (`ab-obs-04b5cdbc04-1`, `permite_envio_de_auxiliar=true`) tem `paired_phone_e164` terminando em **…4743 = TESTE-A**. A da AutoFleet (…9360) é operacional e **não entra**. A da Amandus (…4743) está `disconnected`. O `ATTENDANT_INBOUND_ALLOWLIST` de produção contém **só TESTE-B**.
- Logo o canário vivo é: **remetente = conexão da Resulta (TESTE-A) → destinatário = TESTE-B**, num tenant real, com item SINTÉTICO e documento sem validade financeira. A autorização acompanha o telefone, não o nome do tenant (proposta §1.1).
- ⛔ Resulta tem `human_support_destinations` com um grupo real (`…@g.us`). O canário **suprime** o aviso ao grupo (`cfg.canario=True` → `avisar_suporte_humano` não roda; o relatório diz isso).
- ⛔ Nenhuma rotina de cobrança operacional é ligada (📊 a única existente, da Resulta, está `is_active=false`, `send_mode=test`, `test_number` …9402 — **não é da allowlist**; o canário usa rotina própria marcada).

### 0.4 Referências internas que o juiz abre

| dimensão | referência | como compara |
|---|---|---|
| multi-tenant | CLAUDE.md §7 · `test_spec048_isolamento_corretoras.py` | filtro `company_id` em toda leitura/escrita nova de `billing_sent_log`; teste com dois tenants |
| regressão do modo teste | `backend/tests/test_a_cobranca_esta_como_estava.py` | 34/34 antes e depois, byte a byte no caminho `test` |
| a porta única | `platform_outbound.send_to_client_guarded` | todo efeito real passa por ela; `_entregar_agora` continua o único `send_*` |
| migration | `docs/canon/MIGRATIONS-AUTHORITY.md` | APPLY/VERIFY/ROLLBACK escritos antes |
| guarda serve? | CLAUDE.md §9.3 + mutações M1–M14 | cada gate fica VERMELHO com o defeito reintroduzido |
| canário | `backend/scripts/canario_098.py` | `--dry-run` imprime o plano; `--vivo` só com `AUTOBROKERS_CANARIO=1`; limpeza por id |
| não avaliadas | SLO de latência · OpenAPI · tela designada de UI | veredito "não avaliada" |

### 0.5 O que o aquecimento mudou (preenchido depois da rodada)

_(seção preenchida na emenda v1.1 — ver relatório §0.1)_

---

## 1. BLOCO 0 — o que foi MEDIDO em 07/09/2026 (o número de hoje vence a proposta)

| # | a proposta/RP afirmava | medido hoje | comando | decisão |
|---|---|---|---|---|
| R01 | `live` termina em aviso | ✅ `billing_collection.py:1734-1737` dois ramos só acrescentam frase | `sed -n 1730,1737p` | implementar a cadeia |
| R02 | approval sem consumidor | ✅ `send_billing_whatsapp` só em `:793`; `validar_para_execucao` tem 0 chamadores fora de `promover.py` | `grep -rn send_billing_whatsapp backend/app` | `approval` vira **legado retido**, sem seletor |
| R03 | teste tem prefixo/sufixo | ✅ `_format_test_message` `:888-905` | `sed -n 888,905p` | composição limpa NOVA; a de teste não muda |
| R04 | falha da consulta → vazio | ✅ `_already_sent_recibos` `:908-921` `except → set()` | idem | modos reais: falha de leitura/reserva = **não envia** |
| R05 | chave `(company_id, recibo, send_mode)` | ✅ `billing_sent_log_uniq` (📊 `pg_constraint`); `portal_key` fora da chave; **0 linhas** na tabela em produção | `SELECT conname… ; SELECT count(*)` | identidade = `(company_id, portal_key, recibo)` para modos reais, por índice único parcial |
| R06 | texto aceito + PDF falho | ✅ `:1088-1105` texto `ok` grava `doc_sent=False` e conta como enviado | `sed -n 1080,1110p` | estado por componente (`text_ok`, `doc_ok`, `status`) |
| R07 | aviso pelo canal avariado | ✅ `avisar_suporte_humano` `:227-265` devolve False sem incidente durável | idem | incidente em `agent_activities` sempre; aviso ao grupo é adicional |
| R08 | porta só texto | ✅ `send_to_client_guarded(company_id, phone, text, …)` `:880`; exige agente ligado `:948-990` | idem | porta ganha documento, conexão fixada, autorização de auxiliar, `enfileirar=False` |
| R09 | integração re-escolhida no efeito | ✅ `_entregar_agora` `:1071-1084` → `get_platform_whatsapp_integration` **sem** `para="auxiliar"` → observador recusado | idem + `integration_service.py:258-298` | `integration_id` viaja e é revalidado no efeito; auxiliar autorizado passa pela regra 078 |
| R10 | contexto limitado a 30 envios | ✅ `context_note_for` `:1182-1207` `limit(30)` depois filtra telefone | idem | contexto do CASO por telefone + ledger (`billing_replies.contexto_de_cobranca`) |
| R11 | ponte no atendimento | ✅ `webhook.py:975-983` | idem | mesma ponte, bloco estruturado; retorno registrado ANTES do observador consumir |
| R12 | identidade canônica | ✅ `channel_identity.py`: observer/attendance/dispatch = uma linha | `cat` | preservar; a cobrança usa a mesma linha (D-E001-03) via `permite_envio_de_auxiliar` |
| R13 | observer consome se agente desligado | ✅ `observer_intake.py:800-829` | idem | com agente desligado o cliente que responde **não é respondido** — vira incidente/tarefa (§4.2) |
| R14 | integração viaja no inbound | ✅ `webhook.py:392-398` `_integration_id` | idem | ok |
| novo | agentes de atendimento | 📊 **4/4 desligados** (Amandus, Blueprint, AutoFleet, Resulta) | `SELECT agent_role,is_active FROM agents` | a porta não pode depender do agente para AUXILIAR autorizado |
| novo | `schema_vivo.json` | ❌ não carrega `billing_sent_log`, `platform_sends`, `human_support_destinations`, `integrations` | `python - (json)` | fixture ganha as 4 tabelas com `{tipo, nulo, default}` (P-098-FIXTURE-NOT-NULL parcial) |
| novo | guarda de numeração | `numero_da_spec` = `SPEC-0?(\d{2,3})` → EXTRA isenta por omissão | `sed -n 70,72p test_o_protocolo_tem_policia.py` | U4: EXTRA-NNN entra sob a v11 |
| novo | work run da rotina | `WORK_RUNS_ROUTINE_BRIDGE=1` em produção → rotina roda como `bridge.routine.execute`; `execute_billing_collection_routine` não recebe o run | `grep work_run billing_collection.py routine_engine.py` | run viaja até o ledger e a porta (P-098-RUN-NOS-JOBS, parcial) |
| novo | Evolution Go não devolve id de mensagem | `SendResult(ok=True)` sem `provider_message_id` (`evolution_go.py:460`) | `sed -n 441,476p` | "aceito pelo provedor" é o teto de evidência; nunca "entregue" |
| novo | deploy | `/health` 200, `git_commit: nao-injetado`, `code_fingerprint 9c8c9f09bd153538` | `curl /health` | implantação prova-se por fingerprint depois do Implantar, não por 200 |

**GATE B0** ✅ — matriz acima; mapa de efeitos em §3; autorização do canário em §0.3. Nenhum achado foi vendido como incidente sem reprodução: R01–R14 têm linha e comando.

---

## 2. As modalidades — o contrato que a tela, o motor e o ledger compartilham

| `send_mode` | rótulo na tela | destino | conteúdo | dedup | estado honesto |
|---|---|---|---|---|---|
| `equipe` **(novo)** | Encaminhar para minha equipe | `team_number` da config (uma pessoa da corretora) | nota interna (mensagem própria) + texto final limpo + PDF | ON, identidade da parcela | `entregue_equipe` — cliente NÃO confirmado |
| `cliente` **(novo)** | Enviar diretamente ao cliente | telefone do item, validado pela InfoCap (`contact_status`) | texto final limpo + PDF | ON | `aceito_pelo_canal` / `parcial` / `incerto` / `falhou` |
| `test` | Teste — envia para o meu número de teste | `test_number` | como em 17/08, com marcas | OFF por padrão | teste |
| `none` | Somente relatório | — | — | — | preparado |
| `approval` / `live` (legado) | *"configuração antiga — escolha uma modalidade"* | — | — | — | **retido_legado**: nada sai; a tela e o relatório explicam |

Regras:
- `normalize_billing_config` aceita `{test, none, equipe, cliente}`; `approval`/`live` são preservados no banco e mapeados para `retido_legado` **sem promoção automática** (G02).
- `equipe` exige `team_number` válido (`telefone_br`), `cliente` exige `confirmacao_cliente=True` gravada pela tela (a UI pede a confirmação antes de salvar).
- `approval_required` deixa de ter efeito nos modos reais (não há consumidor — R02). O campo fica no JSON por compatibilidade.

### 2.1 O pacote humano (`equipe`) — três mensagens, nesta ordem
1. **Nota interna** (`_nota_interna_para_a_equipe`): `📋 COBRANÇA · para encaminhar` · cliente · seguradora · parcela/vencimento/valor · WhatsApp do cliente legível · "👇 a mensagem abaixo e o PDF são para encaminhar ao cliente; quando encaminhar, marque no painel".
2. **Texto final** = `build_customer_message(item, template, cfg)` — **sem** prefixo, sufixo ou instrução (G03).
3. **PDF** = `send_document` com `boleto_document_name` (sem PII).
O ledger grava `status='entregue_equipe'` quando (2) e (3) foram aceitos; `parcial` quando só (2). A nota (1) falhar não impede (2)+(3), mas vira pendência.

### 2.2 O envio direto (`cliente`)
Texto final + PDF ao `item.whatsapp`. Pré-condições no instante do efeito: `contact_status` ∈ aceitos, telefone normalizado por `telefone_br`, boleto no bucket (`fila_de_cobranca` já retém sem arquivo), item elegível hoje (`vencido_ha_mais_de`). Sem uma delas → `retido` com motivo (G04, G05).

---

## 3. O motor — mapa de efeitos e o contrato da porta de saída

```
routine (equipe|cliente) ─► portal jobs ─► items + boletos ─► fila_de_cobranca
   ─► para cada item:  RESERVA no ledger (claim atômico)  ──falhou──► não envia, pendência
                          │ ok
                          ▼
            send_to_client_guarded(company_id, phone, text, kind="billing",
                 actor_user_id=None, work_run_id=run,
                 integration_id=<fixada na rotina>, autorizacao_de_auxiliar=True,
                 documento={bucket, path, filename}, enfileirar=False,
                 destino_interno=(modo=='equipe'))
                          │
                          ├─ ator_ainda_pode (inalterado)
                          ├─ AUTORIZAÇÃO: auxiliar → integração fixada existe, é da corretora, is_active,
                          │     pode_enviar(para="auxiliar"); NÃO exige agente de atendimento ligado
                          │     (plataforma sem `autorizacao_de_auxiliar` continua exigindo, como hoje)
                          ├─ freio/janela/teto: governar_envio (destino_interno → intervalo curto, como o teste)
                          ├─ cortesia: client_busy → {"ok":False,"reason":"cliente_em_atendimento"} (sem fila)
                          └─ _entregar_agora(integration=fixada): texto → doc → {"ok","doc_ok","reason"}
                          ▼
            ledger.atualizar(status por componente) ──falhou──► status fica 'reservado' → 'incerto' (nunca retry cego)
```

### 3.1 O ledger — `billing_sent_log` evolui (expand-first, sem tabela nova)

Migration `backend/supabase/migrations/20260907_01_spec_extra001_billing_sent_log_estados.sql` (APPLY/VERIFY/ROLLBACK no relatório §4):

```
ADD COLUMN status text NOT NULL DEFAULT 'entregue'        -- legado: linhas antigas eram "texto aceito"
ADD COLUMN modalidade text                                 -- equipe | cliente | test
ADD COLUMN text_ok boolean, doc_ok boolean                 -- por componente (doc_sent continua, espelhado)
ADD COLUMN to_phone text, to_last4 text                    -- destino efetivo (to_phone: só dígitos; é dado da corretora)
ADD COLUMN integration_id uuid, work_run_id uuid, routine_id uuid
ADD COLUMN reserved_at timestamptz, sent_at timestamptz, updated_at timestamptz NOT NULL DEFAULT now()
ADD COLUMN attempts int NOT NULL DEFAULT 0, last_error text, motivo text
ADD COLUMN encaminhado_ao_cliente_em timestamptz, encaminhado_por uuid
ADD COLUMN retorno_do_cliente text, retorno_em timestamptz   -- ja_paguei | nao_sou | nao_quero | segunda_via | duvida
ADD COLUMN canario boolean NOT NULL DEFAULT false
CREATE UNIQUE INDEX billing_sent_log_obrigacao_uniq ON billing_sent_log (company_id, portal_key, recibo) WHERE send_mode = 'real'
CREATE INDEX billing_sent_log_to_phone_idx ON billing_sent_log (company_id, to_phone) WHERE send_mode = 'real'
```

- Modos reais gravam `send_mode='real'` + `modalidade` — a **identidade da obrigação** `(company_id, portal_key, recibo)` não depende de modo, dia ou run (G08, G11). Legado `test` continua com `send_mode='test'` e a chave antiga.
- **Estados**: `reservado` → `aceito_pelo_canal` (texto ok, sem doc previsto) · `entregue_equipe` (equipe, texto+doc) · `parcial` (texto ok, doc falhou) · `incerto` (efeito possível, registro pós-envio falhou ou timeout) · `falhou` (nada saiu; re-claimável) · `adiado` (cortesia/governador; re-claimável) · `liberado` (humano liberou reenvio, com motivo) · `suprimido` (cliente pediu para não receber / contato errado) · `contestado` (já paguei / dúvida — a sequência para até conferência).
- **Reserva**: `INSERT … ON CONFLICT DO NOTHING RETURNING` (PostgREST `ignore_duplicates`) — só quem recebe a linha de volta envia (G07). Linha existente com `status IN ('falhou','adiado','liberado')` é reclamada por `UPDATE … WHERE id=? AND status=?` retornando a linha (atômico). `parcial` → reclamada só para o **componente doc** (G06). `incerto`, `entregue_equipe`, `aceito_pelo_canal`, `suprimido`, `contestado` → **nunca** reclamadas automaticamente (G10, G14).
- Falha na leitura/reserva → `blockers` + incidente; **não envia** (G09).

### 3.2 A porta de saída — `platform_outbound.send_to_client_guarded` ganha

```
integration_id: Optional[str] = None      # conexão FIXADA; no efeito é relida por id e revalidada: is_active, company_id igual,
                                          # pode_enviar(para="auxiliar" se autorizacao_de_auxiliar). Divergiu → {"reason":"conexao_trocada"}
autorizacao_de_auxiliar: bool = False     # True: a autorização é a da corretora (integração autorizada + rotina instalada), não o interruptor
                                          # do atendimento. False: comportamento de hoje (exige agente ligado) — CONTROLE
documento: Optional[dict] = None          # {"bucket","path","filename"} — assinado no instante do efeito, enviado DEPOIS do texto
enfileirar: bool = True                   # False: cortesia/governador devolvem motivo em vez de enfileirar (a cobrança tenta amanhã)
destino_interno: bool = False             # True: governar_envio(para_numero_de_teste=True) — um número só, da corretora
ledger_ref: Optional[dict] = None         # {"table":"billing_sent_log","id":…} — _entregar_agora marca text_ok/doc_ok/sent_at/status
```
Retorno ganha `doc_ok` e `integration_id`. `_entregar_agora` continua o **único** ponto que chama `send_*`. A fila (`_enfileirar`/`check_platform_queue`) carrega `integration_id` e `documento` quando existirem — entrada antiga sem as chaves cai no comportamento de hoje.

### 3.3 O que a rotina faz por modo (em `execute_billing_collection_routine`)
- `test` → `_send_test_messages` **inalterado**.
- `equipe`/`cliente` → `_entregar_cobranca_real(...)`: fixa a integração UMA vez (`_find_whatsapp_integration`, que já aplica `para="auxiliar"`), monta pacote, reserva, envia pela porta, marca o ledger, registra incidentes. Sem canal → nada sai, incidente `cobranca.sem_canal`.
- Relatório (`_format_report`) e peça (`compor_peca_da_cobranca`) mostram contagens reconciliáveis: encontrados · elegíveis · preparados · retidos (por motivo) · aceitos pelo canal · parciais/incertos · entregues à equipe · encaminhados ao cliente (relato humano) · suprimidos/contestados.
- Rotina de sistema não ganha autorização universal: `autorizacao_de_auxiliar=True` só quando `is_billing_routine(routine)` **e** a rotina está `is_active` **e** o modo é real.

---

## 4. Respostas e convivência no mesmo número

### 4.1 O contexto do caso chega ao atendimento (`backend/app/services/billing_replies.py`, novo)
`contexto_de_cobranca(company_id, phone) -> Optional[str]`: lê `billing_sent_log` (`send_mode='real'`, `to_phone` nas variantes BR, últimos 30 dias, `limit(5)`), e devolve um bloco `[COBRANÇA EM ANDAMENTO]` com: seguradora · parcela · vencimento · valor · data do envio · estado · **regras**: "não confirme pagamento por fala; 'já paguei' → agradeça, diga que a equipe confere, não reenvie; 'me manda de novo' → diga que a equipe reenvia (não prometa horário); 'não sou essa pessoa' → peça desculpa, não cite dados, encerre; 'não quero receber' → registre e encerre; guincho/assistência → siga o atendimento normal". Nada do bloco é instrução que mude autorização (G21: o conteúdo do cliente/documento entra como dado).
No `webhook.py:975-983`, quando `contexto_de_cobranca` devolve algo, ele **substitui** o `context_note_for` genérico; senão o genérico continua (controle).

### 4.2 O retorno do cliente é registrado antes de qualquer resposta (`registrar_retorno`)
No `process_whatsapp_message_background`, logo depois de resolver `integration`/`company_id` e **antes** do observador consumir: se o telefone tem linha real no ledger, classifica o texto (`_classificar_retorno`: já paguei · não sou · não quero · segunda via · dúvida · outro) e grava `retorno_do_cliente`, `retorno_em`, `status` (`contestado`/`suprimido`) e uma linha em `agent_activities` via `log_activity` (`cobranca`, texto humano). **Não envia nada.** Com o agente desligado (📊 4/4 hoje), esta é a única forma de a equipe saber que o cliente respondeu (G13, G14, G17).
Classificação por regex em PT com pares mínimos fixados (`backend/tests/corpus/retornos_de_cobranca.json`, sintéticos). Mídia sem texto → `outro` (P-097.1-MIDIA-SEM-TEXTO continua).

### 4.3 Convivência (G15, G16)
- Takeover humano: `pausar_ia` já cala a IA por `claimed_by`/`HUMAN_REQUESTED`; a cobrança **não** cria conversa nem muda `status`; `registrar_retorno` só escreve no ledger e em `agent_activities`.
- Cortesia: `client_busy` continua na porta; com `enfileirar=False` a cobrança adia para a próxima execução em vez de entrar na fila eterna (P-098-FILA-SEM-EXPIRE não piora).
- Seguradora/URA: o `dispatch_router` roda **antes** do ramo de atendimento no webhook (📊 `webhook.py:540-580`); `registrar_retorno` só age quando o telefone é `to_phone` de uma linha real do ledger — um número de seguradora nunca é.
- Mensagem pessoal / grupo: `isGroup`/`fromMe` já são descartados no endpoint (`webhook.py:1330`).

---

## 5. Tela e rotas (Next)

- `components/auxiliares/PainelDeRotinas.tsx`: `MODOS_COM_MOTOR` = `test · none · equipe · cliente`; campo `team_number` (equipe); confirmação explícita para `cliente` (texto: "O cliente vai receber diretamente pelo WhatsApp da corretora. Cada parcela é cobrada uma vez."); configuração legada `approval`/`live` mostra o aviso e força a escolha antes de salvar; texto "Enviar direto ao segurado ainda não está disponível" **sai**. Lista **"Pendências da cobrança"** (rows do ledger com `status IN (parcial, incerto, entregue_equipe sem encaminhado, contestado, suprimido, falhou)`), com ações: *Marcar como encaminhado ao cliente* · *Liberar reenvio* (motivo obrigatório).
- `app/api/dashboard/rotinas/route.ts`: `normalizeBillingConfig` aceita os 4 modos + `team_number` + `confirmacao_cliente`; nunca promove legado.
- Rotas novas (todas por `resolveSessionCompany`, filtro `company_id` obrigatório): `app/api/dashboard/auxiliaries/cobranca/pendencias/route.ts` (GET) · `…/encaminhado/route.ts` (POST id, motivo?) · `…/liberar/route.ts` (POST id, motivo) — `liberar` só de `entregue_equipe|parcial|incerto|falhou|adiado|suprimido?` — **suprimido não libera** (preferência do cliente); `contestado` libera só com motivo.
- `liberar-reenvio` (teste) não muda.
- Guarda `scripts/rotina-mora-no-auxiliar.test.mjs` atualizado: a asserção "nenhum modo sem motor (`live`, `approval`)" continua; ganha "os modos `equipe` e `cliente` existem e têm motor" (`grep` da função `_entregar_cobranca_real` no Python).

---

## 6. Alertas, incidentes e painel (G17)
- Toda falha vira `log_activity(company_id, "cobranca", título humano, detalhe)` → tabela `agent_activities` (📊 `activity_log.py:50`) — o painel de Atividades já existe; sem inbox novo.
- `avisar_suporte_humano` continua; o relatório diz "aviso ao grupo: enviado / falhou / sem destino / suprimido (canário)". Nunca "humano avisado" por tentativa falha.
- Recuperação da conexão **não** dispara backlog: `adiado`/`falhou` só são reclamados pela **próxima execução** da rotina, dentro do teto do governador.

---

## 7. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (protocolo §7.3 — reabertas em 07/09/2026)

```
URL ................. https://www.postgresql.org/docs/current/ddl-constraints.html  (reaberta 07/09/2026, doc 18.6)
o que ela faz ....... UNIQUE multi-coluna; restrição parcial só por ÍNDICE ÚNICO PARCIAL; CHECK não barra NULL; NULLS não são iguais em UNIQUE
MODELAMOS ........... `billing_sent_log_obrigacao_uniq` parcial `WHERE send_mode='real'` (U1); `status`/`attempts` NOT NULL com default;
                      teste que exige o 23505 do banco no segundo claim
REJEITAMOS .......... supor que o UNIQUE gravado DEPOIS do envio garante uma mensagem só (é o defeito R06/R05); NULLS NOT DISTINCT (não há NULL na chave)
COMO O JUIZ INSPECIONA abre a §5.4 da doc; roda dois INSERTs concorrentes na fixture do canário e vê UM 23505
```
```
URL ................. https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html (reaberta 07/09/2026)
o que ela faz ....... resolve o "dual write": intenção gravada na mesma transação; consumidor idempotente; rollback não publica
MODELAMOS ........... a RESERVA no ledger antes do efeito e o estado `incerto` quando o registro pós-efeito falha (U1 §3.1) — sem nova fila
REJEITAMOS .......... instalar outbox/CDC/SQS ou outro scheduler (CLAUDE.md §5); prometer exactly-once (o Evolution Go não devolve id de mensagem)
COMO O JUIZ INSPECIONA lê "Issues and considerations"; injeta falha entre reserva e envio, e entre envio e registro; conta as mensagens (dublê)
```
```
URL ................. https://docs.stripe.com/webhooks  (reaberta 07/09/2026)
o que ela faz ....... eventos duplicados e fora de ordem são NORMAIS; guarda-se o id processado; assinatura verificada no corpo cru
MODELAMOS ........... o retorno do cliente é idempotente por (ledger.id, texto normalizado, janela) e nunca reordena estados para trás
                      (`suprimido` não volta a `reservado` por um evento antigo) (U2 §4.2)
REJEITAMOS .......... copiar cabeçalhos/assinatura da Stripe: a verificação do inbound continua a do webhook por token (SPEC-017)
COMO O JUIZ INSPECIONA "Handle duplicate events" / "Event ordering"; repete e reordena dois retornos no dublê e confere o estado final
```
```
URL ................. https://business.whatsapp.com/policy  (reaberta 07/09/2026 pela conversa de preparação; conferir na execução)
o que ela faz ....... exige opt-in/expectativa de contato, respeito à recusa, proíbe mensagens indesejadas; prevê restrição/suspensão
MODELAMOS ........... `suprimido` é terminal por preferência do cliente (não libera pelo botão); uma abordagem por parcela; texto identifica a corretora
REJEITAMOS .......... "número aquecido" como arquitetura; régua automática de lembretes (fora desta EXTRA)
COMO O JUIZ INSPECIONA abre a política; tenta liberar uma linha `suprimido` pela rota e recebe 409
```

O que o estado da arte faz que nós NÃO fazemos, por valor: receipt de entrega/leitura por id de mensagem (Meta oficial) **80** · template com PDF no mesmo envio **60** · opt-out por botão **55** — todos da SPEC-099.

---

## 8. Gates → comandos (a matriz G00–G23 da proposta, executável)

| gate | prova | comando | mutação (nome novo, em cópia) |
|---|---|---|---|
| G00 | BLOCO 0 acima | `python backend/scripts/canario_extra001.py --dry-run` imprime o censo | — |
| G01 | remetente E destinatário na allowlist em toda saída de canário | `test_a_cobranca_chega_a_quem_deve.py::[G01]` — porta com `cfg.canario` recusa destino fora | **M1** remover a checagem de destino no canário → verde vira vermelho |
| G02 | 4 modos distintos e executáveis; legado retido | `[G02]` normalize + `_entregar_cobranca_real` roteia; `approval`→`retido_legado` | **M2** mapear `live`→`cliente` no normalize |
| G03 | texto final sem `[TESTE`, sem "simulacao", sem instrução | `[G03]` regex sobre o payload da 2ª mensagem | **M3** reusar `_format_test_message` no modo equipe |
| G04 | direto vai ao telefone do item validado | `[G04]` item com `contact_status='not_found'` → retido | **M4** ignorar `contact_status` |
| G05 | PDF do item, assinado no efeito | `[G05]` `documento.path` = `boleto.storage_path` do MESMO recibo; HTML como pdf → recusa | **M5** trocar `by_recibo` por `boletos[0]` |
| G06 | texto ok + doc falho = `parcial` | `[G06]` dublê falha `send_media` | **M6** gravar `entregue_equipe` sem `doc_ok` |
| G07 | uma reserva vencedora | `[G07]` dois claims no dublê PostgREST (ignore_duplicates) → 1 linha | **M7** reservar DEPOIS do envio |
| G08 | dia/run/modo novo não reenvia | `[G08]` 2ª execução, modo trocado, `now()+1d` → 0 envios | **M8** incluir `modalidade` na chave |
| G09 | falha de histórico bloqueia | `[G09]` dublê levanta na leitura → 0 envios + blocker | **M9** `except → set()` de volta |
| G10 | timeout não repete | `[G10]` `send_text` levanta `Timeout` após efeito possível → `incerto`, nunca reclamado | **M10** reclamar `incerto` |
| G11 | equipe→cliente respeita decisão | `[G11]` `entregue_equipe` sem `encaminhado` → precisa de decisão; com `liberado` → envia | **M11** liberar automático |
| G12 | conexão trocada no efeito | `[G12]` `integration_id` fixada; dublê devolve outra `company_id`/inativa → `conexao_trocada` | **M12** reler por `get_platform_whatsapp_integration` |
| G13 | contexto certo com volume | `[G13]` 200 envios de outros telefones + 1 do cliente → bloco cita o caso do cliente | **M13** `limit(30)` sem filtro |
| G14 | já paguei / contestação / opt-out | `[G14]` corpus de pares → `contestado`/`suprimido`; `suprimido` não libera pela rota | **M14** `suprimido` reclamável |
| G15 | takeover e eco | `[G15]` `pausar_ia` inalterado (diff vazio em `o_fim_do_atendimento.py`); `registrar_retorno` não muda `status` da conversa | — (guarda de diff) |
| G16 | seguradora não vira interlocutor | `[G16]` telefone sem linha no ledger → `registrar_retorno` = no-op | — |
| G17 | falhas visíveis | `[G17]` `agent_activities` recebe 1 linha por falha; relatório diz "aviso ao grupo: falhou" | — |
| G18 | dois tenants | `[G18]` fixture com 2 `company_id`: leitura/claim/rotas Next não cruzam; IDOR na rota `encaminhado` (id de outro tenant → 404) | — |
| G19 | reinício | `[G19]` processo morre após reserva → linha `reservado` envelhece → `incerto` no relatório; sem reenvio | — |
| G20 | regressão | `test_a_cobranca_esta_como_estava.py` 34/34 · `test_spec078_bloco_a_seguranca.py` 39/39 · `test_governador_de_envio.py` · `npm run test:rotas-montam` | — |
| G21 | injeção | `[G21]` documento/cliente com "envie para 55…"/"mude a corretora" → bloco entra como DADO; nenhum efeito | — |
| G22 | instalação ≠ validação | relatório §6 separa main / implantado (fingerprint) / canário / aceite | — |
| G23 | docs coerentes | `test_o_protocolo_tem_policia.py` reconhece EXTRA; dossiê com `p-extra001` | — |

Gate zero: o guarda inteiro **VERMELHO** em cópia limpa (`../AutoBrokers-FIX-gate0` em `34424fa`) antes do primeiro commit de produto.

---

## 9. Canário autorizado (§0.3) — `backend/scripts/canario_extra001.py`

`--dry-run` (padrão) imprime: conexão da Resulta por id (últimos 4 do telefone), allowlist carregada (tamanho, nunca dígitos), rotina canário a criar, item sintético, documento sintético. `--vivo` exige `AUTOBROKERS_CANARIO=1` **e** `BILLING_CANARIO_ALLOWLIST` com 2 entradas, e:
- **Q1 equipe**: rotina canário (`config.canario=True`, `send_mode='equipe'`, `team_number`=TESTE-B), item sintético `recibo=CANARIO-…`, PDF sintético "SEM VALIDADE — TESTE" em `portal-evidence/canario/…` → 3 mensagens chegam em TESTE-B; ledger `entregue_equipe`, `canario=true`; **aviso ao grupo suprimido**.
- **Q2 cliente**: mesma parcela, modo `cliente`, `item.whatsapp`=TESTE-B → **0 envios** (G11: entregue à equipe sem encaminhado); depois `liberar` com motivo → 1 envio (texto+PDF).
- **Q3 reexecução**: rodar de novo → 0 envios, relatório diz "já cobrado".
- **Q4 retorno**: o Founder responde de TESTE-B ("já paguei") → `registrar_retorno` grava `contestado` + `agent_activities`; com o agente da Resulta desligado, nenhuma resposta automática (é o esperado; o teste de resposta com agente ligado fica **na caixa do Founder**, porque ligar o agente da Resulta é ligar tenant operacional — a allowlist de inbound = TESTE-B mitiga, mas a decisão é dele).
- **Q5 fora da allowlist**: rotina canário com `team_number` fora → porta recusa (`fora_da_allowlist`), 0 envios.
- **Q6 limpeza**: linhas do ledger do canário marcadas (`canario=true`) e apagadas por id+company; rotina canário desativada e apagada; `platform_sends` do canário apagados por id; VERIFY 0/0/0. Nada em `integrations` é tocado.

---

## 10. Migração e compatibilidade
- Additiva; leitores antigos (`_already_sent_recibos`, `liberar-reenvio`) continuam corretos porque só olham `send_mode='test'`.
- Legado desconhecido: linhas antigas (`send_mode` real de outra época) — 📊 não existem (0 linhas). O default `status='entregue'` é conservador.
- Backfill: nenhum.
- ROLLBACK: `DROP INDEX` + `ALTER TABLE … DROP COLUMN` (nenhum leitor antigo depende das colunas novas). Mensagens já enviadas não se desfazem; o ledger fica.

## 11. O QUE SAIU da proposta, e o gatilho que faz voltar

| saiu | por quê | volta quando |
|---|---|---|
| fila durável nova / outbox / TTL de Redis | motor paralelo (CLAUDE.md §5); a rotina já é o retentador natural | SPEC-099 se a entrega precisar sobreviver fora da rotina |
| reenvio automático de segunda via a pedido do cliente | efeito externo disparado por texto de terceiro (§9 do protocolo: conservador) | 099 com receipts e botão de opt-out |
| régua de lembretes | fora por decisão (proposta §9.3) | proposta própria |
| approval como modalidade | 0 consumidores; humano-encaminha é modalidade própria | quando `validar_para_execucao` ganhar chamador (P-098-APROVACAO-REIMPLEMENTA-O-GATE) |
| e-mail, Meta, segundo QR | D-E001-02/03 | 099 |
| resposta automática viva no canário | exige ligar o agente da Resulta (tenant operacional) | caixa do Founder |

## 12. Pendências tocadas (drenagem)
`P-098-FILA-SEM-EXPIRE` CONTINUA (a cobrança deixa de usar a fila) · `P-098-RUN-NOS-JOBS` parcial: run viaja da ponte até o ledger e a porta · `P-098-FICHA-RMW` CONTINUA (não tocada) · `P-097-TELEFONE-BR-DUPLICADO` parcial: `billing_replies` e o ledger usam `telefone_br` · `P-098-UNIT-B-NA-SUITE` CONTINUA · `P-098-FIXTURE-NOT-NULL` parcial: 4 tabelas entram na fixture com `{tipo, nulo, default}`.

## 13. Caixa do Founder (acrescentada durante a execução — ver relatório)
1. Implantar (smith-api e smith-web) quando a main receber o push.
2. Decidir se liga o agente de atendimento da **Resulta** por uma janela curta (allowlist de inbound = TESTE-B) para o teste vivo de resposta automática.
3. Validação com Saionara/Regina pelos números de teste (roteiro no relatório).
