---
> **Status:** relatório de execução — SPEC-EXTRA-001.3, sob o **PROTOCOLO AAA v12 · AAA FAST**
> **Experimento A do A/B (D-PROTO-02):** executor Opus 5 `xhigh` · juiz Fable 5.1
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `09a238f`

```
OUTCOME .............. o grupo da corretora recebe 4 tipos de mensagem e mais nada; nenhuma sobre
                       conversa que um humano já conduz ou sobre número da casa; cada uma inteira e
                       clicável; todo envio contado
RISCO ................ 8 — ALCANCE 3 (o dossiê decide o que a atendente faz pelo segurado) ·
                       REVERSIBILIDADE 3 (mensagem que sai do prédio) · FREQUÊNCIA 2 (todo atendimento)
SUPERFÍCIE ........... 3 — 11 pontos de envio ao grupo, e "consigo apontar TODOS" era o que provar
PISO APLICADO ........ §3.2 três vezes: ENVIA mensagem · migration que ALTERA ESTRUTURA · filtro
                       `company_id` nas 6 rotas do BLOCO G
NÍVEL ................ CRÍTICO · executor Opus 5 `xhigh` · juiz Fable 5.1
UNIDADES ............. 7 — A guarda única · B números da casa · C mensagem inteira · D os quatro
                       modelos · E contabilidade · F gate de ligar · G autorização das 6 rotas
                       FATIAS: 1 = A+C+E · 2 = B+D+F+G (executadas na mesma sessão, commit por fatia)
COESÃO ............... A e C tocam os MESMOS arquivos de envio → um dono, serial. E fecha o contrato
                       que A e C produzem (o que saiu, e o que significava) → mesma fatia.
PARALELISMO REAL ..... nenhum — a escrita é de um só. Investigador read-only: não
TIME ................. executor · juiz Fable 5.1 · lente do dado: SIM (o outcome é dataset + migration
                       de estrutura) · confirmação: por gatilho, se o juiz achar blocker em
                       envio/tenant/migration · red team: NÃO (sem auth nova, dinheiro ou portal)
REFERÊNCIA ........... interna `backend/tests/test_o_caso_se_explica_sozinho.py` (`problemas_de_lingua`)
                       e `backend/tests/corpus/acervo_do_grupo_2026-09-16.json` (acervo real, sem PII)
                       externa: E01–E05 da §19 da proposta (SRE Book 6 e 11 · PagerDuty `dedup_key` ·
                       Alertmanager `inhibit_rules` e `group_by`)
GATES ................ G-A1..A3 · G-B1..B3 · G-C1..C4 · G-D1/D2 · G-E1 · G-F1/G-G1
O ELO ................ "o grupo virou ruído PORQUE nenhum gatilho pergunta se um humano já está na
                       conversa" — A medido (7 mensagens em 75,7 min, §1 linha 1) · B medido (98 de 99
                       elegíveis calam, pelo MOTOR) · 🔴 B CHEGA EM A: os 11 pontos foram abertos um a
                       um e TODOS passam a consultar a mesma guarda (G-A2 varre e prova)
FAIXA DE RELÓGIO ..... declarada 1h15 + 1h15 + 45min · real: ver §10 · tetos: 250 turnos · 300 k
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** `docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md` ·
**Branch:** `feat/spec-extra-001-3-grupo-so-o-que-importa` ·
**Preflight** 📊 16/09/2026: `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `09a238f` · árvore limpa ·
**Executor:** Opus 5 `xhigh` (sessão nova) · **Juiz:** Fable 5.1

## 1. BLOCO 0 — as premissas que mudariam o desenho

| # | a proposta afirma | medido 📊 16/09 | comando | consequência |
|---|---|---|---|---|
| 1 | 7 mensagens ao grupo em 75,7 min no 10/09 | **7 · 75,68 min** — idêntico | a SQL de §0.1, colada no módulo novo | âncora confirmada |
| 2 | 58 elegíveis, 58 com humano nos 7 dias | **254** em `HUMAN_REQUESTED` · **99** elegíveis · **98** calam | `ultima_palavra_humana` + `silenciar_por_palavra_humana` sobre as 99, **pelo MOTOR Python**, não por SQL | o acervo cresceu 2×; a asserção do guarda é contra o CONJUNTO, nunca contra um literal |
| 3 | o dossiê vira 4 balões | **4 balões** (o texto do guarda tem 508 chars, não 429) | `split_whatsapp_balloons` real, na linha de controle de G-C1 | a asserção é `> 1`, nunca `4` |
| 4 | `motivo_classe` não tem escritor | **0** ocorrências · `human_handoff_reason` em **2 de 254** | `grep -rn motivo_classe backend/app` · SQL | a regra de `desconhecido` é obrigatória, e o limite de 30% também |
| 5 | as 3 leituras do governador não filtram `kind` | **confirmado**, e `billing_nota`/`billing_doc` da 001.6 **já existem** e já contam | `platform_outbound.py:606-616` lido da linha 1 | a allowlist (não o prefixo) era mesmo o desenho certo |
| 6 | `internal_numbers` está vazio em toda a base | **0 integrações** com a lista preenchida | `jsonb_array_length(...) > 0` | sem backfill, escrito na migration |
| 7 | 🔴 **não estava na proposta** | `work_events.work_run_id` era **NOT NULL sem default** | `insert` sem a coluna → `NotNullViolation` (rollback) | **BLOCKER**: o diário do grupo era impossível. Migration `20260916_02`. É também por isto que `handoff.realertado` tem **0 linhas** — a proposta lia esse 0 só como "o re-alerta nunca disparou" |
| 8 | 🔴 **não estava na proposta** | `dispatch_router._support_alert_seguro` lia `destino.get("number")` | `resolver_destino_de_suporte` devolve `{destino, fonte, recusa}` — `number` não existe | o aviso *"o protocolo NÃO chegou ao segurado"* **saía calado sempre**. Morreu junto com as 3 linhas |
| 9 | `write:true` pode restringir quem usa as telas | `admin_company` **8** (4 `is_owner`) · `member` **2** | `select role, is_owner, count(*) from company_members group by 1,2` | a trava **não tira** o acesso de quem já o usa; a linha foi para a Caixa do Founder |
| 10 | P-PILOTO-10: AutoFleet com zero destinos | **4 destinos · 3 empresas · 1 ativo** · `agent_enabled` false em 5 de 5 | `select ... from human_support_destinations` | pendência re-justificada (§9) |

**MUTAÇÃO B0** (as duas afirmações falsas do desenhista): refutadas — (a) *"basta filtrar `kind LIKE 'grupo_%'`"* é falso, `billing_nota` não tem o prefixo e consumiria a cota; (b) *"o dossiê já sai em um balão"* é falso, `bloco_unico` estava em **1 de 11** caminhos.

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|---|
| 1 | **A** guarda única | `services/o_grupo_so_o_que_importa.py` (novo) + os 11 pontos | `python tests/test_o_grupo_so_fala_de_quem_precisa.py` | **29 verdes · 0** | `21f2243` · `fe136c0` |
| 1 | **C** uma mensagem, inteira, uma vez | `human_handoff` · `dispatch_router` · `dispatch_watchdog` · `handoff_watchdog` · `whatsapp/alerts` | `python tests/test_uma_mensagem_inteira_e_uma_vez.py` | **22 verdes · 0** | idem |
| 1 | **E** todo envio contado | `platform_outbound.py` (allowlist nas 3 leituras) · `billing_collection` | `python tests/test_toda_mensagem_ao_grupo_e_contada.py` | **18 verdes · 0** | idem |
| 2 | **F** gate de ligar | `api/porteiro_do_agente.py` (novo) · `lib/admin/porteiro-de-ligar-o-agente.ts` · rota do toggle | `python tests/test_ligar_o_agente_tem_porteiro.py` | **38 verdes · 0** | `a405bbb` |
| 2 | **G** as 6 mutações | `lib/admin/porteiro-de-configuracao.ts` (novo) + as 6 rotas | idem | idem | `a405bbb` |
| 2 | **D** os quatro modelos + 19h | `services/os_modelos_do_grupo.py` · `tasks/o_resumo_das_19h.py` (novos) · `human_handoff` · `o_fim_do_atendimento` | `python tests/test_os_quatro_modelos_falam_portugues.py` | **37 verdes · 0** | `bbff51a` |
| 2 | **B** números da casa | migration · `lib/atendimento/numeros-da-casa.ts` · `casos.ts` · `attendance_capture` · rotas + card Equipe | `python tests/test_o_numero_da_casa_nao_e_cliente.py` | **20 verdes · 0** | (a seguir) |

🔴 **Os 11 pontos de envio, um a um** (§3.2 conferido): 1 `human_handoff` ✅ porta · 2 `dispatch_router:3312` ✅ porta · 3 `dispatch_router:201` ✅ porta (e o defeito do `number` morto) · 4 `dispatch_watchdog` ✅ porta · 5 `billing_collection` ✅ porta (perdeu o 2º resolvedor) · 6 `regression_sentinel` ✅ porta · 7 `whatsapp/alerts` ✅ muda de destinatário (§7.4) · 8 `admin_spec034` isento, alerta de TESTE · 9/10 `weekly_report`/`proactive_suggestions` fora de escopo, **pendência nova** · 11 `route_sentinel` vai ao Founder, não ao grupo. **G-A2 varre o backend e fica vermelho com um 12º caminho.**

## 3. Migrations — APPLY · VERIFY · ROLLBACK

| migration | APPLY | VERIFY (rodado no banco) | ROLLBACK |
|---|---|---|---|
| `20260916_01_..._company_internal_numbers` | tabela + índice único `(company_id, phone)` + RLS | `tabela_existe=True` · `unique_por_corretora=True` · `rls_ligada=True` | `drop table if exists` — nasce nesta SPEC, leitor do JSONB continua (expand-first) |
| `20260916_02_..._work_events_sem_run` | `alter column work_run_id drop not null` | `run_id_opcional=True` · `fk_composta_intacta=True` · `linhas_sem_run=0` | `set not null` — seguro **enquanto** `count(*) where work_run_id is null` = 0; havendo linhas, apagá-las é decisão do Founder |

⚠️ A FK composta `(work_run_id, company_id)` continua valendo: em MATCH SIMPLE, coluna nula satisfaz sem checar — um evento sem run não aponta para o run de outra corretora porque não aponta para run nenhum.
⛔ Sem migration para `platform_sends`: `kind` é `text` livre, sem CHECK. Os `kind` novos entram como **dado**.

## 4. O juiz fresco — **PENDENTE** (ver §12)

## 5. O conserto único — **PENDENTE**

## 6. A bateria — ver §10

## 7. O que ficou fora, e o gatilho que o faz voltar

| frente | por quê | gatilho |
|---|---|---|
| `weekly_report` / `proactive_suggestions` lendo `human_support_destinations` | outra superfície; dois envios semanais sem gate próprio | pendência nova `P-E0013-01`; SPEC de canais (099) |
| Conteúdo do checklist de sinistro por tipo | depende da base de produtos | EXTRA-001.5 — o **lugar** está reservado em `modelo_novo_sinistro` |
| Aposentar `alert_target.internal_numbers` | expand-first: o leitor velho continua | SPEC futura, com backfill e prova |
| CHECK em `platform_sends.kind` | congelaria a lista de tipos | quando a lista parar de crescer |
| Régua de eficiência publicada no dossiê | o número nasce aqui; a régua é produto da medição de 3 dias | EXTRA-001.7 |

## 8. 📋 Caixa do Founder — o que só o Amandus faz

| # | o que é | o que destrava | bloqueia? |
|---|---|---|---|
| 1 | **Implantar** `smith-api` e depois `web` no EasyPanel | tudo abaixo | não |
| 2 | **Criar o grupo de canário** (só você dentro) e dizer qual é o tenant de teste | os 8 casos de §14 da proposta | não |
| 3 | 📊 **`write:true` restringe quem configura?** Medido: `admin_company` 8 · `member` 2. Quem hoje mexe nas telas das duas pilotos é `admin_company` — **ninguém perde acesso**. Confirme se está certo assim | o BLOCO G sem surpresa na segunda | não |
| 4 | **19h é a hora certa?** É o padrão e é env (`RESUMO_DIARIO_HORA`), por corretora no fuso dela | o BLOCO D.4 | não |
| 5 | **Ler os quatro modelos** (§2 desta entrega, renderizados) e dizer o que cortaria — 💭 a copy é ilustrativa de propósito | a validação com Saionara e Regina | não |
| 6 | 🔴 **`JANELA_SILENCIO_HUMANO_DIAS` agora tem DOIS efeitos**: ela governa o silêncio do agente com o segurado **e** o silêncio do grupo. Mudar esse número muda as duas coisas | nada; é aviso | não |
| 7 | **Reativar os destinos** da Resulta e da AutoFleet quando quiser voltar a ligar o agente (os dois estão `is_active=false`) | a EXTRA-001.7 | não bloqueia esta SPEC |

**Variáveis novas** (nome, sem valor): `RESUMO_DIARIO_HORA` (padrão `19`) · `RESUMO_DIARIO_ATIVO` (padrão `true`).
**Rollback sem deploy:** `RESUMO_DIARIO_ATIVO=false` desliga o resumo · `janela_silencio_humano_dias=0` na corretora devolve o comportamento de antes. 🔴 Os dois existem porque esta SPEC **cala** coisas, e o modo de falha mais perigoso dela é calar demais.

## 9. Pendências e decisões

**Absorvidas (§2 do protocolo — quem drena):**
- **P-PILOTO-02** (acionamento pelo portal fora da Fila) · **CONTINUA** — fora da superfície desta SPEC; nada aqui tocou `portal_jobs`.
- **P-PILOTO-03** (PDF some da Ficha) · **CONTINUA** — idem, `webhook.py` não foi tocado.
- **P-PILOTO-04** (sinistro sem checklist) · **CONTINUA, com o lugar pronto**: `modelo_novo_sinistro` tem o campo *Pontos de atenção*, preenchido hoje com `_o_que_falta`. O conteúdo por tipo é da EXTRA-001.5.
- **P-PILOTO-12** (régua de língua não roda nos dossiês) · ✅ **FECHADA** — `problemas_de_lingua` roda sobre os quatro modelos renderizados em `test_os_quatro_modelos_falam_portugues.py` (4 asserções verdes).
- **P-PILOTO-10** (destino da AutoFleet na Resulta) · ✅ **FECHADA-com-ressalva** — 📊 16/09: 4 destinos, 3 empresas, 1 ativo; cada corretora tem o seu. A ressalva é que os dois das pilotos estão `is_active=false` (caixa do Founder #7).
- **P-PILOTO-13** e **P-PILOTO-15** · já **FECHADAS** pela EXTRA-001.2 em 14/09; a mitigação de §21 (conversa-irmã) **não foi necessária**.

**Novas:**
- `P-E0013-01` — `weekly_report.py:91` e `proactive_suggestions.py:183` leem só o legado `acionamento_profile.suporte_humano_whatsapp` e ignoram `human_support_destinations`. **Destrava:** apontá-los para o resolvedor único. **Dono:** 🤖. **Custo de esquecer:** a corretora que só cadastrou pela tela nova não recebe os dois envios semanais.
- `P-E0013-02` — `whatsapp_channel.py:1124` faz `update({"alert_target": target})` e **apaga** `observer_scope`, `observer_exclusions` e `internal_numbers`. **Destrava:** merge em vez de sobrescrita. **Dono:** 🤖. **Custo:** a lista velha do JSONB some sem aviso (hoje ela está vazia em toda a base, então o custo é futuro).
- `P-E0013-03` — `handoff.realertado` continua com 0 linhas até o próximo re-alerta rodar. A trava (NOT NULL) caiu; falta a **prova em produção** de que a linha passa a nascer. **Dono:** 🤖, no canário.

**Decisões tomadas pela execução (regra do Founder de 13/09 — nota 0–100, escolhe, registra, segue):**

| # | decisão | notas |
|---|---|---|
| D-E0013-01 | `work_events.work_run_id` deixa de ser obrigatório (migration extra, não prevista) | migration **88** × diário em `agent_activities` 55 × `work_run` sintético 35 |
| D-E0013-02 | A marca da captura interna vai em `source = "live_interno"` | sem migration **80** × coluna nova 70 × continuar descartando 20 |
| D-E0013-03 | O casador do BFF é uma **porta** em TS, confrontada com o motor Python caso a caso (G-B3) | porta com guarda cruzado **80** × chamar Python na Fila 30 × duplicar sem guarda 40 |
| D-E0013-04 | O gate de ligar mora no **backend** e o painel pergunta | backend **90** × duplicar a resolução no BFF 40 × só `human_support_destinations` no BFF 60 |
| D-E0013-05 | Falha de comunicação com o backend **deixa ligar** (fail-open no gate), enquanto o portão de runtime segue fail-closed | **85** × bloquear por indisponibilidade 35 |

## 10. Telemetria (§11)

```
<preencher com `python backend/scripts/medir_execucao_claude_code.py --sessao atual`>
```

## 11. Entrega

```
<saída real de `git push origin HEAD:main`>
```

**Implantar, nesta ordem:**
```
smith-api   backend: a guarda, a porta única, os números da casa, os quatro modelos,
            platform_sends, o resumo das 19h, o gate de ligar
web         painel: card Equipe, rotas de números internos, as 6 rotas do BLOCO G,
            o porteiro do toggle
```

## 12. Handoff

O juiz fresco (Fable 5.1) e a lente do dado ainda não rodaram quando esta versão do relatório foi escrita — §4, §5 e §6 são preenchidos na volta deles.
