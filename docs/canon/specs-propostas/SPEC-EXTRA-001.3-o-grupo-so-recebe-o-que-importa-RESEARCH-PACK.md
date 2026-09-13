# SPEC-EXTRA-001.3 — RESEARCH PACK
## O grupo só recebe o que importa — evidências, medições e o que continua desconhecido

**Versão:** 1.0 · **Data:** 13/09/2026. **Natureza:** evidência para conversão. **Não** é relatório de execução.
**Repositório:** `Amandico100/AutoBrokers-Intelligence-OS`. **Worktree lido:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
**Baseline:** `HEAD = a0bb5fef440eba394a9275671b1143f5025807ef`, branch `docs/diagnostico-pilotos-0912`, 13/09/2026.
**Método:** leitura direta dos arquivos nesta revisão + consultas **read-only** ao banco de produção via `SUPABASE_DB_URL` + execução local do motor de balões. **Nada foi executado no produto. Nenhuma mensagem foi enviada. Nenhum portal foi acessado.** ⛔ Nenhum CPF, CNPJ, telefone, nome de segurado, placa, e-mail ou credencial aparece neste documento.

---

## 0. Legenda e precedência

- **📊 MEDIDO** — com data, fonte e o comando que produziu o número (CLAUDE.md §12.1 e AAA §0.4).
- **💭 ILUSTRATIVO** — exemplo ou hipótese. **Nunca citável como fato.**
- **FATO** — existência/comportamento visível no código ou no banco desta revisão.
- **INFERÊNCIA** — consequência derivada, com o grau de confiança dito.
- **PENDENTE DE MEDIÇÃO** — precisa de comando, consulta ou canário.
- **CORREÇÃO** — o diagnóstico de origem dizia outra coisa; aqui está o que medi.

🔴 **As coordenadas `arquivo:linha` deste pacote foram TODAS reabertas e conferidas em 13/09/2026.** Onde divergiram do diagnóstico, está escrito. Mesmo assim: elas envelhecem. O BLOCO 0 reabre e corrige.

---

## 1. Fontes canônicas lidas, e o que aproveitar

| Fonte | O que aproveitar | O que **não** transportar sem conferir |
|---|---|---|
| `CLAUDE.md` (inteiro) | §5 motor paralelo · §7 multi-tenant · §8 migrations · §9.1–9.5 os corolários de guarda · §12.1 marcação de número | O caminho de worktree de um exemplo não prova árvore em dia |
| `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` v11.2 | §0.2 card · §0.3 o ELO · §0.4 a regra do comando · §2 teste do produto · §3 as duas contas · §5 o laço · §7.3 referência externa | ⛔ Não montar painel de juízes sobre a SPEC (§5.1) |
| `docs/canon/GLOSSARIO.md` | Work Run · Approval · Artifact · Auxiliar × Rotina | "Even/SERGIO" é nomenclatura revogada |
| `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` | §1.5 (os defeitos com causa) · §3 bloco 001.3 · §7.2 (janela do grupo) · §7.5 (eficiência) · §12.1 (ordem) | ⚠️ Seis afirmações dele estão vencidas — ver §4 deste pacote |
| `docs/canon/FOUNDER-DECISIONS.md` linhas 1753, 1757, 1758 | D-PILOTO-09, D-PILOTO-13, D-PILOTO-14 | ⛔ Não reabrir nenhuma |
| `docs/canon/MIGRATIONS-AUTHORITY.md` | §7 formato obrigatório · §8 proibições · §9 sequência de segurança | ⚠️ O parágrafo do P1 já foi corrigido em 02/08; ler a nota do fim |
| `docs/canon/PENDENCIAS.md` **por número** | P-PILOTO-02, 03, 04, 10, 12, 13, 15, 20 | ⛔ Nunca ler inteiro (📊 562.580 bytes) |
| `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md` | O modelo de forma e profundidade desta proposta | A proposta histórica não prova o que foi entregue |

---

## 2. Achados no código — cada um reaberto em 13/09/2026

> **Como ler:** `arquivo:linha` é coordenada **desta baseline**, não contrato permanente. Reencontre o **símbolo**, leia a função inteira, os chamadores e os consumidores (AAA §0.3, "código morto").

### 2.1 Os onze pontos de envio ao grupo

| ID | evidência | consequência |
|---|---|---|
| **R01** | `backend/app/agents/tools/human_handoff.py:920-962` `_avisar_suporte`; o envio em **:951-956** passa `bloco_unico=True` | **É a única porta correta que existe.** Três chamadores: `:1182` (a tool), `handoff_watchdog.py:351` (re-alerta), `handoff_watchdog.py:568` (espera vencida). Pôr a guarda **dentro** dela cobre os três de uma vez |
| **R02** | `backend/app/services/dispatch_router.py:3291-3314`: `resolver_destino_de_suporte` em :3291, `send_to_client(support, texto)` em **:3304** (sem `bloco_unico`), `entregar_dossie_uma_vez(... build_handoff_dossier ...)` em :3312 | Caminho A do dossiê de acionamento. Picotado |
| **R03** | `backend/app/services/dispatch_router.py:187-201`: `_support_alert_seguro`, envio em **:201** `get_whatsapp_service().send_message(str(alvo), aviso, integ)` | "o aviso de protocolo NÃO chegou ao segurado". Chamado em :3140 e :3186. Picotado |
| **R04** | `backend/app/tasks/dispatch_watchdog.py:270-319` `_support_alert`, envio em **:315**; `build_handoff_dossier` em **:424**, marcador em **:437-438** | Caminho C. Cobre `ura_silent`, `human_silent_alert`, `never_started`, `deadline` e o dossiê do Sentinela. Picotado |
| **R05** | `backend/app/services/billing_collection.py:243-292` `avisar_suporte_humano`: lê `human_support_destinations` **direto** em :269-274; envia em :287-289 | 🔴 **Segunda implementação do resolvedor**, e ela **pula** `_destino_e_compartilhado`. Funde-se na primeira (BLOCO E) |
| **R06** | `backend/app/services/regression_sentinel.py:100` via `_support_contact` (:89) | "QUALIDADE EM QUEDA" — é sobre a corretora, não sobre conversa: passa pela guarda como tipo `vigia` |
| **R07** | `backend/app/services/whatsapp/alerts.py:60-97` `_alert_destination`, envio em **:255** | Queda de canal. 🔴 Muda de **destinatário** no BLOCO C.4 |
| **R08** | `backend/app/api/admin_spec034.py:232-241` | Alerta de TESTE. Mantém — é ferramenta de diagnóstico |
| **R09** | `backend/app/services/weekly_report.py:85-91` e `proactive_suggestions.py:85,183` | 🔴 Leem **só** o legado `acionamento_profile.suporte_humano_whatsapp` e **ignoram** `human_support_destinations`. Fora do escopo; **pendência nova** |
| **R10** | `backend/app/services/atlas/route_sentinel.py:498` via `_founder_alert_number()` (:588) | Vai ao **Founder**, não à corretora. Não muda |

### 2.2 O re-alerta de 6 h — e por que a acusação do diagnóstico é meia verdade

| ID | evidência | consequência |
|---|---|---|
| **R11** | `backend/app/tasks/handoff_watchdog.py:106-376` `varrer_handoffs_parados()`. Relógios em **:43-45**: `_ESPERA_ALERTA_MIN_PADRAO=30`, `_REALERTA_HORAS_PADRAO=6`, `_MAX_POR_PASSADA=50`. O SELECT em **:139-146** (`.eq("status","HUMAN_REQUESTED").lt("last_message_at", limite)`) | ⚠️ **CORREÇÃO:** o diagnóstico cita `handoff_watchdog.py:140` como estando em `app/services/`. **Está em `app/tasks/`.** A linha 140 é a lista de colunas do select, não a query inteira |
| **R12** | **:180-197** — o filtro "a última palavra foi do cliente?": lê `messages`, monta `vista[cid]` com o `role` mais recente, e `esperando = {c for c in ids if vista.get(c,"user")=="user"}` | 🔴 **Já existe uma checagem de humano**, posta em 21/08/2026. 📊 Ela cala **73 de 131** hoje. O que **não** existe é a janela de N dias |
| **R13** | **:271-291** — o corte por **idade do claim**, não por existência: `if _idade_claim_ms is not None and _idade_claim_ms < _janela_ms: continue` | Segunda checagem de humano. Um claim abandonado **volta** a gerar lembrete, de propósito (:235-249) |
| **R14** | **:198-203** — falha de leitura → `logger.warning` e **avisa todos** | 🔴 **FAIL-OPEN deliberado**, com a justificativa escrita: *"o defeito grave aqui sempre foi calar, nunca repetir"*. A guarda do BLOCO A **conserva** essa escolha |
| **R15** | O marcador de "já avisei" é **Redis**, não coluna: `_ja_avisado_recentemente` (**:293**) → `human_handoff.reivindicar_o_aviso` (`human_handoff.py:186-206`), chave `_CHAVE_DO_MARCADOR="handoff_realerta:{}"` (**:71**), `set(..., ex=horas*3600, nx=True)` (**:200-201**). Teto de 4 lembretes em `human_handoff.py:213,231` | A chave de dedup do BLOCO C.5 muda **a chave**, não o mecanismo. ⛔ Nada de tabela de dedup nova |
| **R16** | `_devolver_a_vez` (**:372, :376**) devolve a reserva quando o envio falha | Comportamento a **preservar**: senão um envio que falhou cala a próxima varredura por 6 h |
| **R17** | Cadência do job: `buffer_processor.py:547-554`, `HANDOFF_WATCHDOG_INTERVAL_MINUTES` default **10 min** | O marcador de 6 h é o que segura o volume, não o intervalo |

### 2.3 A espera vencida

| ID | evidência | consequência |
|---|---|---|
| **R18** | `handoff_watchdog.py:476-627` `varrer_esperas_vencidas`; agrupamento **1 alarme por conversa** em **:532-544**; envio em **:566-572** via `_avisar_suporte`; `EVENTO_ESPERA_VENCIDA="espera.vencida"` em **:407** | ⚠️ **CORREÇÃO:** o diagnóstico põe `espera.vencida` em `dispatch_watchdog.py`. **Está em `handoff_watchdog.py`** |
| **R19** | `AVISOS_ATE_EXPIRAR = 3` em `o_fim_do_atendimento.py:478`; corte em `deve_expirar_a_conversa` (**:870-876**); job a cada 10 min (`buffer_processor.py:573-579`) | 🔴 São **três avisos ao grupo**, e o terceiro é o que **expira** a conversa. Cortar o contador quebra a expiração — o BLOCO C.2 corta só quantos **chegam ao grupo** |
| **R20** | **:590-600** — a mensagem ao **segurado** sai por porta separada, uma por vencimento, com a razão escrita | O contrato de "dois destinos, duas chamadas" já existe e é o modelo a seguir |

### 2.4 O vigia do acionamento

| ID | evidência | consequência |
|---|---|---|
| **R21** | `backend/app/tasks/dispatch_watchdog.py:31-38`: `URA_UNANSWERED_S=30`, `URA_SILENT_ALERT_S=120`, `HUMAN_NUDGE_S=600`, `HUMAN_ALERT_S=1200`, `NEVER_STARTED_S=300`, `SESSION_DEADLINE_S=2700`, `MAX_SENTINELA_ATTEMPTS=2` | Os relógios que o BLOCO C.3 desliga para o grupo (menos `never_started`) |
| **R22** | `diagnose()` **:68-134**; envios **:564-608**, cada um com flag `wd_*` gravada na sessão **antes** do envio | 🔴 É **uma vez por sessão por gatilho** — não de 10 em 10 min. ⚠️ Mas a flag vive na **sessão**, e sessão reabre: é a mesma causa de R23 |
| **R23** | `session["dossier_sent"]` em **:437-438**, via `_entregar_dossie_com_marcador` | 📊 **A causa dos 3 dossiês em 21 minutos no 10/09.** O BLOCO C.5 troca a chave por `(company_id, conversation_id, tipo)` |
| **R24** | Job a cada **20 s**: `buffer_processor.py:176-179` | Confirma que o volume vem da reabertura, não do intervalo |

### 2.5 A janela de silêncio — o motor que o BLOCO A reusa

| ID | evidência | consequência |
|---|---|---|
| **R25** | `backend/app/services/o_fim_do_atendimento.py:944-951`: `JANELA_SILENCIO_HUMANO_DIAS = 7`, env `JANELA_SILENCIO_HUMANO_DIAS`, override `companies.acionamento_profile.janela_silencio_humano_dias` | **É o número único** de §7.2. ⛔ Proibido criar um segundo |
| **R26** | `janela_de_silencio_dias()` **:1012-1054**; `0` desliga a regra e é valor legítimo (**:1021-1024**); valor ilegível cai no padrão, **nunca** em zero (**:1026-1027**) | O guarda G-A3 usa o `0` como mutação: tem de devolver as 58 |
| **R27** | `ORIGENS_HUMANAS = ("espelho","dashboard")` **:963**; `e_origem_humana` **:1066-1074** (`role='assistant'` **e** `payload.origem` na lista) | 🔴 É lista **fechada e por inclusão**: origem nova não vira "humana" por acidente |
| **R28** | `ultima_palavra_humana` **:1146-1165** — exclui o segurado, o próprio agente, o **eco do agente espelhado** (`e_eco_do_agente`, :1124) e a **anotação `#nota`** (`e_anotacao`, :1077) | 🔴 **É por isso que o 58 medido em SQL pode não ser o 58 medido pelo motor.** Ver §3.3 |
| **R29** | `silenciar_por_palavra_humana` **:1194-1217** — devolve `(calar, frase_em_português)`; a frase vai para o feed e para a ficha | A guarda do BLOCO A devolve **a mesma frase**. ⛔ Não traduzir código de motivo em tela |
| **R30** | `a_ia_deve_calar` **:1325-1398** — a porta completa, **fail-closed** (:1373-1374) | ⚠️ A guarda do grupo é **fail-open** (§5.4 da SPEC). A assimetria é deliberada e está justificada |
| **R31** | `janela_de_mensagens` **:1257**, teto `_MENSAGENS_DA_JANELA = 40` (**:970**), servido por `idx_messages_by_conversation` | O custo da regra é uma consulta indexada por turno |
| **R32** | `_variantes_do_telefone` **:1296-1308** e `telefone_e_excecao_da_janela` **:1310-1323** | 🔴 **É a autoridade de casamento de telefone** (com/sem 55, com/sem nono dígito), do commit `05f46a9`. O BLOCO B **a reusa** |
| **R33** | 🔴 **Nenhum dos onze pontos de envio ao grupo chama `a_ia_deve_calar` ou `janela_de_silencio_dias`.** Confirmado por varredura | **É o elo que falta**, e é o BLOCO A inteiro |

### 2.6 O que sai picotado

| ID | evidência | consequência |
|---|---|---|
| **R34** | `backend/app/services/whatsapp/balloons.py:17-19`: `TARGET_LEN=300`, `HARD_LEN=500`, `MAX_BALLOONS=4`; `split_whatsapp_balloons` **:73-117** — devolve `[raw]` se `len ≤ 300`, senão **parte por linha em branco** (`re.split(r"\n\s*\n", raw)`) | ⚠️ **CORREÇÃO:** não é "a cada 300 caracteres". É *cabe em 300 → inteiro; não cabe → parte por parágrafo* |
| **R35** | `backend/app/services/whatsapp_service.py:157-160`: `if bloco_unico: balloons = _fatiar_documento(text)`; `_fatiar_documento` **:92-122**, teto `_TETO_DE_UMA_MENSAGEM = 3500` (**:89**) | **O desvio já existe e está pronto.** O conserto é passar a flag |
| **R36** | `build_handoff_dossier` `backend/app/services/insurer_dispatch_service.py:3657`; título "🚨 *ATENDIMENTO PRECISA DE VOCÊ*" em :3669; `link_do_caso` :3610, usado em :3673; `telefone_curto` :3597, usado em :3693 e :3783 | Os campos que o BLOCO D retira (§8.0 da SPEC) |
| **R37** | `_montar_dossie` `human_handoff.py:710-808`: seções na ordem *o que é → quem é → o que houve → o que falta → o que fazer → a conversa → o link*; histórico em **:783-794** (`_MSGS_NO_DOSSIE`); link em **:804**; `_fone_bonito` **:463-475** | 🔴 **É o dossiê BOM**, da SPEC-071. O BLOCO D **evolui** este, não cria outro |
| **R38** | `_dossie_de_pos_acionamento` `human_handoff.py:841-918` | Segunda variante; a régua de língua do BLOCO D roda nas duas |

### 2.7 A contabilidade

| ID | evidência | consequência |
|---|---|---|
| **R39** | `platform_sends` — migration `backend/supabase/migrations/20260720_02_spec045_platform_sends.sql:7-17`. 7 colunas: `id, company_id, phone, kind, summary, sent_at, created_at`. `kind` é `text not null`, **sem CHECK** | Os `kind` novos entram como **dado**. ⛔ Não criar CHECK (congelaria a lista) |
| **R40** | Escritores: `platform_outbound.py:305` (INSERT) e `:312` (`record_platform_send`), `dispatch_router.py:244`, `billing_collection.py:1261`, `dispatch_followup.py:320`, `platform_outbound.py:1494` — **todos com telefone de segurado** | Nenhum é do grupo |
| **R41** | 🔴 `backend/app/services/platform_outbound.py` `_historico_sync` faz **TRÊS** leituras de `platform_sends` por `company_id`, **nenhuma filtrando `kind`**: `recentes` (**:606-610**, 26 h) · `primeiro` (**:611-613**, data do 1º envio) · `total_res` (**:614-616**, `count="exact"` da história inteira). O comentário :632-636 explica que a fonte é durável de propósito | 🔴 **O achado que o diagnóstico não tinha.** `recentes` governa a cota imediata; **`primeiro` e `total_res` governam a MATURIDADE** (R41b) |
| **R41b** | 🔴 `maturidade_do_canal(dias_de_uso, envios_no_total)` **:424-441** — `'maduro'` exige `>= _MADURO_DIAS` (30) **E** `>= _MADURO_ENVIOS` (200); chamada em **:697** com os valores de R41; decide `teto_do_dia` **:444-445**. O docstring diz literalmente que *"só volume → 200 envios feitos numa tarde é exatamente a rajada que este arquivo existe para impedir"* | 🔴 **Com `grupo_*`/`billing_nota` contados, um canal que NUNCA falou com segurado amadurece e SOBE o teto diário.** É o contrário do que a função existe para provar |
| **R41c** | `SPEC-EXTRA-001.6:408-409, 412, 417, 430` cria `billing_nota` (nota interna à atendente) e `billing_doc`; 📊 a 001.6 mede 7 parcelas virando **17 linhas** em `platform_sends` | 🔴 **`billing_nota` não começa com `grupo_`** e, sob filtro por prefixo, consumiria a cota do segurado. Por isso o contrato é **allowlist** (ou coluna `conta_na_cota`), nunca prefixo — e a lista é **arquivo-hub** entre a 001.3 e a 001.6 |
| **R42** | `work_events` + `_anotar_no_diario` `handoff_watchdog.py:446-473`: grava `company_id`, `event_type`, `actor_type='system'`, `severity`, `message_human[:400]`, `payload_redacted`; `work_run_id` fica **nulo** de propósito (:454-456) | **É onde o `motivo` classificado mora.** ⛔ E a carga nunca leva nome, telefone ou texto de mensagem (:458-460) |
| **R43** | `EVENTO_HANDOFF_REALERTADO="handoff.realertado"` (**:429**), `EVENTO_HANDOFF_NO_TETO` (**:430**), `EVENTO_ESPERA_VENCIDA` (**:407**); o comentário **:409-425** diz que as três perguntas *"quantos alertas saíram / quantos eram de quem esperava / o teto foi atingido"* não tinham resposta | O contrato do BLOCO E já estava escrito aqui em 26/08 |
| **R44** | `agent_activities` — 6 colunas (`id, company_id, category, title, detail, created_at`); escrito por `human_handoff.py:160-183` | É a segunda trilha, e é a que permitiu reconstruir o 10/09 |

### 2.8 O resolvedor de destino e a tabela

| ID | evidência | consequência |
|---|---|---|
| **R45** | `resolver_destino_de_suporte` `backend/app/services/dispatch_router.py:2346`. Ordem: `human_support_destinations` ativo (**:2370-2374**, `.eq("company_id",…).eq("is_active",True).order("is_primary",desc).order("priority_order").limit(1)`) → `companies.acionamento_profile.suporte_humano_whatsapp` (**:2380-2386**) → `integrations.alert_target` (**:2388-2396**) | 🔴 **Três fallbacks.** A trava do canário tem de ficar no **último ponto de efeito**, não aqui |
| **R46** | `_destino_e_compartilhado` **:2259-2343**: varredura **global de propósito** (`.limit(500)` sem filtro de empresa, :2307-2309) que recusa destino usado por mais de uma corretora | 🔴 É a proteção §7 que `billing_collection` **pula** (R05). Prova histórica: P-PILOTO-10 |
| **R47** | `human_support_destinations` — migration `backend/supabase/migrations/20260613_human_support_destinations_foundation.sql:30-77`. 18 colunas | ⚠️ `silence_minutes`, `active_hours`, `escalation_rules`, `fallback_enabled` **não são lidos por nenhum código do backend** — o resolvedor lê só 4 colunas |
| **R48** | ⚠️ `20260803_01_spec063_destino_de_suporte_unico.sql:44-60` grava `destination_type='whatsapp_number'`, valor que **não existe no CHECK** da migration de 2026-06-13 | PENDENTE DE MEDIÇÃO: conferir se o CHECK foi alterado ou se o backfill falhou |

### 2.9 Os números da casa

| ID | evidência | consequência |
|---|---|---|
| **R49** | 🔴 **Não existe tabela.** Zero ocorrências de `company_internal_numbers` / `internal_numbers` / `numeros_internos` como tabela em `backend/supabase/migrations/` e no código | O BLOCO B cria a primeira |
| **R50** | O conceito vive em `integrations.alert_target` (JSONB), criado em `20260703_01_spec017_whatsapp_channel_expand.sql:15-25`. COMMENT oficial (**:32-33**): *"destino do alerta de desconexão (nunca o próprio número de atendimento)"* | 🔴 O COMMENT é a **justificativa escrita** do BLOCO C.4 |
| **R51** | 🔴 **Três formatos incompatíveis na mesma coluna**, documentados pelo próprio código em `backend/app/services/whatsapp/pairing_orchestrator.py:770-789`: `{"label","observer_scope"}` · `{"observer_scope","internal_numbers"}` · `{"number"}` | Um JSONB com três escritores de forma diferente não é uma lista |
| **R52** | Único **leitor**: `backend/app/services/atlas/attendance_capture.py:109-117`, dentro de `client_chat_allowed` (:54) — junta `observer_exclusions` + `internal_numbers` e filtra o que o **Observador captura** | 📊 O efeito de hoje é **um** dos quatro que a SPEC exige |
| **R53** | Único **escritor** das listas: `pairing_orchestrator.py:775-777`, e só por `setdefault(..., [])` — **cria vazias**. Nenhuma rota popula | 📊 O conjunto de exclusão é **sempre vazio**, salvo edição manual no banco |
| **R54** | 🔴 `backend/app/api/whatsapp_channel.py:1124` faz `update({"alert_target": target})` com `target` montado em :1096-1102 como `{"number":…}` ou `{"use_support_destination":True}` — **apaga** `observer_scope`, `observer_exclusions` e `internal_numbers`. Mesmo padrão em `app/api/admin_atlas.py:470` | **Pendência nova.** Um escritor destrutivo sobre um JSONB compartilhado |
| **R55** | `company_members` — migration `20260721_01_spec047_rls_e_company_members.sql:17-26`, **uma** que cria e **nenhuma** que altera. 7 colunas, **nenhuma de contato** | ✅ Confirma o diagnóstico |
| **R56** | O telefone da equipe vem de `users_v2.phone`, **já selecionado** por `getTeam` (`lib/admin/tenant-overview-store.ts:17-24`) e mostrado em `TeamClient.tsx:13` (campo `phone`). 📊 preenchido em **796 de 796** usuários | 🔴 **A fonte 1 do BLOCO B já existe, já está preenchida e já está na tela certa. ⛔ NENHUMA coluna nova em `company_members`** |
| **R56b** | ⚠️ **Preenchido ≠ utilizável.** Nada no schema ou no código prova o **formato** dos 796, nem que o número é WhatsApp: `users_v2.phone` é texto livre | O casamento tem de ser por `_variantes_do_telefone` (R32), e o G-B1 leva um caso com telefone de membro **mal formatado** (com `+55`, sem `55`, com máscara, com e sem nono dígito). **PENDENTE DE MEDIÇÃO:** a distribuição de formatos |
| **R57** | A tela: `app/dashboard/personalizacao/equipe/page.tsx` + `TeamClient.tsx` (259 linhas). `app/dashboard/equipe/page.tsx:16-20` é só um `redirect`. API única: `app/api/dashboard/team/route.ts` | Onde o sub-bloco entra |

### 2.10 Autorização — o BLOCO G

| ID | evidência | consequência |
|---|---|---|
| **R58** | `requireCompanyMember` mora em **`lib/admin/admin-auth.ts:68-100`** ⚠️ (**CORREÇÃO:** o diagnóstico aponta `admin-auth-policy.ts`, que só tem as decisões **puras**). Valida sessão → vínculo **ativo** em `company_members` pela `activeCompanyId` → `canWriteTenantConfig` se `write:true` → fallback por `users_v2` com consistência sessão×banco | O padrão |
| **R59** | `assertSameOrigin(req)` **`admin-auth.ts:103-108`** — lê `origin` + `host`/`x-forwarded-host`, devolve `403 cross_origin_blocked` | A origem |
| **R60** | `writeAudit` **`lib/vault/server.ts:55`** — grava em `vault_audit_log` com `actor_user_id` | A auditoria |
| **R61** | **A referência de uso correto:** `app/api/dashboard/team/route.ts:46-50` (POST), `:105-109` (PATCH), `:145-149` (DELETE), `:36` (GET com `write:false`). Idem `company-profile/route.ts:18`, `brand-identity/route.ts:111,130` | O juiz abre este arquivo |
| **R62** | `TENANT_WRITE_ROLES = ['owner','admin','admin_company','master_admin']` (`admin-auth-policy.ts:5`); `canWriteTenantConfig` (:150); `ATTENDANCE_TOGGLE_ROLES` acrescenta `attendant` e `member` (:42) | 🔴 **Aplicar `write:true` RESTRINGE quem pode mexer.** Caixa do Founder item 2 |
| **R63** | **As 6 mutações abertas**, conferidas uma a uma: `attendance/support-destinations/route.ts:72` (POST) · `…/[destinationId]/route.ts:23` (PATCH) · `…/[destinationId]/route.ts:108` (DELETE) · `dashboard/portal-credentials/route.ts:58` (POST) · `:78` (DELETE) · `dashboard/whatsapp-channel/route.ts:236` (POST). Nenhuma chama `requireCompanyMember`, `assertSameOrigin` ou `writeAudit` | O BLOCO G |
| **R64** | 🔴 A #6 despacha **6 ações** por `body.action` (`whatsapp-channel/route.ts:244`): `set-auxiliary-authorization` (:263, escreve `integrations.permite_envio_de_auxiliar`), `set-alert` (:306), `disconnect` (:318), `retry`/`cancel` (:328), `pairing` (:349) | **Desconectar o WhatsApp da corretora não exige papel administrativo hoje** |
| **R65** | A causa é **estrutural**, e são **dois** resolvedores, não um: as 3 de `portal-credentials`/`whatsapp-channel` usam `resolveSessionCompany` (`lib/auxiliaries/server.ts:31` → `{userId, companyId}`); as 3 de `support-destinations` usam **`getIronSession` cru + `companyIdDoSeletor()`** (`app/api/attendance/support-destinations/route.ts:25-27`; `lib/attendance/support-destinations.ts:48` → `string | null`) | ⚠️ **A conclusão é a mesma — nenhum dos dois devolve papel** — mas a prova é diferente, e o executor precisa das duas. O conserto é trocar o resolvedor, ⛔ não acrescentar um `if` |
| **R66** | ⚠️ `lib/attendance/support-destinations.ts:20` usa `createClient(..., SUPABASE_SERVICE_ROLE_KEY)` e **escreve direto na tabela**, sem passar pelo backend Python | 🔴 A única proteção dessas três rotas é o código delas. RLS não protege contra service role |

### 2.11 O gate de ligar o agente

| ID | evidência | consequência |
|---|---|---|
| **R67** | Leitura em runtime: `backend/app/services/atlas/attendance_capture.py:267-295` `attendance_agent_active`, **fail-closed** (:291-295) | 🔴 **Não muda.** O BLOCO F trava no ato de **ligar**, não no runtime |
| **R68** | Escrita: **não existe rota dedicada.** É o CRUD genérico `app/api/agents.py:260-261` (`PUT /{agent_id}`) → `agent_service.py:137`, UPDATE em :177-179; único guarda é validação de prompt (:160-171) | O BLOCO F |
| **R69** | A checagem que existe é **posterior e passiva**: `backend/app/main.py:876-921` conta `corretoras_ligadas_sem_destino_de_suporte`, exposto em :980-981. A docstring **:879-884** registra o incidente que a criou: agente ligado + zero destinos = **5 handoffs que não chegaram a ninguém** | 🔴 **A justificativa do BLOCO F já está escrita no repositório** |
| **R70** | `app/api/whatsapp_channel.py:795-826` `_resolve_attendant_agent_id` só **escolhe** o agente para vincular ao canal — aceita inclusive o inativo (:812-821) | Não liga nada; não confundir com o gate |

### 2.12 O agendador — onde o resumo das 19h entra

| ID | evidência | consequência |
|---|---|---|
| **R71** | `backend/app/tasks/buffer_processor.py:154-579` — **24 jobs**, todos `IntervalTrigger` (`seconds=`/`minutes=`). **Nenhum `CronTrigger`** | 🔴 O resumo das 19h **não** cria scheduler: entra como job neste, no padrão de `relatorio_semanal_check` (:243-247, intervalo de 1800 s + checagem interna de hora e de "já saiu") |
| **R72** | `fuso_da_corretora` (`platform_outbound.py:638`) e `FUSO_DA_CORRETORA` (`o_fim_do_atendimento.py`) | As 19h são **locais da corretora** |
| **R73** | ⚠️ `main.py` chama `start_buffer_scheduler()` **sem `try`** no startup — um `ImportError` ali derruba a aplicação inteira (documentado em `handoff_watchdog.py:21-31`) | 🔴 O módulo do resumo tem de ser **leve**, com o import pesado **dentro** da função |

---

## 3. As medições — comando, data, e o resultado

> Todas em **13/09/2026**, conexão `SUPABASE_DB_URL` do `backend/.env`, **somente SELECT**, nenhuma linha de conteúdo impressa.

### 3.1 O dia 10/09 reconstruído — 7 mensagens, 75,7 minutos, uma conversa

```sql
with t as (
  select created_at, title as o_que from agent_activities
   where created_at >= '2026-09-10' and created_at < '2026-09-11'
     and (title ilike 'Dossi%' or title ilike '%desconectado%')
  union all
  select created_at, event_type from work_events where event_type='espera.vencida')
select count(*), min(created_at), max(created_at),
       extract(epoch from (max(created_at)-min(created_at)))/60 from t;
```

📊 **7 · 17:14:18 · 18:29:59 · 75,68 min** (UTC).

| hora | o quê | origem |
|---|---|---|
| 17:14:18 | Dossiê — acionamento travou | R23 |
| 17:21:34 | Dossiê — acionamento travou | R23 |
| 17:35:57 | Dossiê — Allianz | R02 |
| 17:50:39 | WhatsApp de atendimento desconectado | R07 |
| 18:09:58 / 18:19:58 / 18:29:59 | ⏳ ESPERA VENCIDA 1, 2 e 3 de 3 | R18/R19 |

📊 **E as esperas eram de UMA conversa:** `select count(*), count(distinct conversation_id), count(distinct company_id) from work_waits` → **5 · 1 · 1**, todas de 10/09, `kind='esperando_humano'`, `scope='acionamento'`, `avisos ∈ {0,3}`.

📊 **A Saionara entrou às 17:18:14:** `work_events` com `travamento.assumido` (1 linha, 10/09) e `travamento.aberto` (2 linhas). **6 das 7 mensagens saíram depois disso.**

⚠️ **CORREÇÃO ao diagnóstico §1.5:** "7 mensagens em 77 min" → **75,7 min**.

### 3.2 As 58 — elegíveis ao re-alerta, todas com humano dentro

```sql
with ult as (select distinct on (m.conversation_id) m.conversation_id, m.role, m.created_at
             from messages m join conversations c on c.id=m.conversation_id
             where c.status='HUMAN_REQUESTED' order by m.conversation_id, m.created_at desc)
select count(*) filter (where role='user')  as ultima_do_segurado,
       count(*) filter (where role<>'user') as ultima_da_casa, count(*) from ult;
--  58 | 73 | 131
```

```sql
-- (a continuação, com a janela de 7 dias ancorada na última mensagem) — ver §0.2 da SPEC
--  elegiveis = 58 | humano_nos_7d_antes_do_alerta = 58
```

| medição | valor | comando |
|---|---|---|
| conversas `HUMAN_REQUESTED` | **131** | `select count(*) from conversations where status='HUMAN_REQUESTED'` |
| por corretora | AutoFleet **78** · Resulta **53** | `… join companies … group by 1` |
| elegíveis ao re-alerta | **58** | acima |
| caladas hoje pela regra de 21/08 (R12) | **73** | acima |
| com humano nos 7 dias anteriores | **58 de 58** | §0.2 da SPEC |
| `human_handoff_reason` vazio | **129 de 131** | `select (human_handoff_reason is null or human_handoff_reason='') , count(*) … group by 1` |
| origem das falas humanas | `espelho` **32.231** · sem payload **1.334** · `dashboard` **0** | `select lower(coalesce(payload->>'origem','(sem)')), count(*) from messages group by 1` |

🔴 **O NÚMERO JÁ DERIVOU NA MESMA TARDE.** Uma segunda passada em 13/09 deu **131 · 59 elegíveis · 72 caladas** (contra 58/73 da primeira). O acervo é vivo e o espelho grava enquanto se mede: **58 e 59 são o mesmo fato em dois instantes.**

⛔ **Consequência de contrato:** o `58` é 📊 **datado, na prosa, e NUNCA na asserção de um guarda**. G-A1 e G-A3 afirmam *"todas as elegíveis medidas no BLOCO 0 calam"*, com linha de controle. Um guarda que fixe `58` fica vermelho na primeira mensagem nova — e ensina a equipe a ignorar guarda, que é o defeito que a SPEC existe para consertar.

⚠️ **E o teto por passada não é 58:** `varrer_handoffs_parados` tem `.limit(_MAX_POR_PASSADA)` = **50** (`handoff_watchdog.py:45, :146`) e corte `last_message_at < agora − HANDOFF_ALERTA_MINUTOS` (30 min, :43, :108-112). O certo é **≤ 50 por passada, em ondas de 6 h**.

🔴 **FATO que muda a leitura:** `select count(*) from work_events where event_type like 'handoff%'` → **0**. O re-alerta de 6 h **nunca disparou** sobre essas conversas desde que a telemetria existe (SPEC-086 C.1, 26/08).

📊 **A razão medida:** `select company_id, destination_type, is_primary, is_active, silence_minutes from human_support_destinations` → 4 linhas, **1 ativa** (AMANDUS), Resulta e AutoFleet com `is_active=false`. E `select id, company_name, agent_enabled from companies` → **os 5 com `agent_enabled=false`**.

**INFERÊNCIA (alta confiança):** o grupo está quieto por configuração, não por desenho. Reativar destino + ligar o agente — que é o que a EXTRA-001.7 manda fazer — dispara até 58 mensagens a cada 6 horas.

### 3.3 🔴 A armadilha do motor — leia antes de confiar no 58

📊 O **58** acima foi medido em **SQL**, com `payload->>'origem' in ('espelho','dashboard')`.

A regra que vai rodar é **Python**: `ultima_palavra_humana` (R28) exclui, **além** disso, a anotação `#nota` (`e_anotacao`) e o **eco do agente espelhado** (`e_eco_do_agente` — o texto que o próprio robô mandou, que volta pelo espelho dentro de 180 s).

🔴 **CLAUDE.md §9.4:** *um padrão medido com um motor e aplicado com outro é um padrão sobre outra coisa.* O BLOCO 0 **tem** de rodar `ultima_palavra_humana` sobre as mesmas 58 e dizer o número que sair. Se der 55, é 55 — e a SPEC se corrige, não o contrário.

**PENDENTE DE MEDIÇÃO.** É a medição mais importante do BLOCO 0.

### 3.4 O dossiê picotado — medido com o motor real

```python
# 13/09/2026, execução local, sem banco, sessão SINTÉTICA sem PII
from app.services.whatsapp.balloons import split_whatsapp_balloons
from app.services.insurer_dispatch_service import build_handoff_dossier
texto = build_handoff_dossier(sessao_sintetica, reason="Travou na URA e a recuperacao automatica esgotou")
len(texto), len(split_whatsapp_balloons(texto)), [len(b) for b in split_whatsapp_balloons(texto)]
```

📊 **429 caracteres → 4 balões (136 · 16 · 69 · 201).** Constantes: `TARGET_LEN=300`, `HARD_LEN=500`, `MAX_BALLOONS=4`.

💭 **A sessão é sintética** (dicionário montado por mim); **o motor e a contagem são reais**. O BLOCO 0 refaz sobre uma sessão do acervo. ⚠️ E note: **429 caracteres já viram 4 balões** — não é preciso ser longo, basta ter parágrafos (R34).

### 3.5 🔴 O governador — o achado que o diagnóstico não tinha

📊 `backend/app/services/platform_outbound.py:606-617`, lido em 13/09:

```python
recentes = (db.client.table("platform_sends").select("sent_at")
            .eq("company_id", str(company_id)).gte("sent_at", desde)   # 26 h
            .order("sent_at", desc=True).limit(1000).execute().data or [])
```

**Sem filtro de `kind`.** Alimenta o governador de vazão da SPEC-063 Bloco C (12/h · 20 novos/dia por corretora).

📊 Estado atual de `platform_sends`: **19 linhas na base inteira** — `billing` 18 (17/08 a 11/09) e `acionamento_protocolo` 1 (19/08). Por isso ninguém percebeu.

🔴 **INFERÊNCIA de alta confiança, e são DOIS danos:**

1. **Cota imediata** (`recentes`): mensagens ao **grupo** consomem a cota do **segurado**. Num dia movimentado o produto para de falar com clientes, e o motivo é invisível.
2. **Maturidade** (`primeiro` + `total_res` → `maturidade_do_canal`, R41b): um canal que **nunca falou com segurado** amadurece com tráfego interno e **sobe o teto diário** — o oposto exato do que a função prova.

**O conserto é pré-requisito do BLOCO E, nas TRÊS leituras, e é ALLOWLIST — não prefixo** (R41c: `billing_nota` da 001.6 não tem prefixo `grupo_` e seria contado). Com linha de controle (CLAUDE.md §9.3): N linhas `grupo_*` + N `billing_nota` não mexem em cota, `dias_de_uso` nem maturidade; N linhas `billing` mexem nas quatro.

### 3.6 Schema medido — o que existe hoje

```sql
select column_name, data_type from information_schema.columns
 where table_schema='public' and table_name = '<tabela>' order by ordinal_position;
```

| tabela | colunas | nota |
|---|---|---|
| `company_members` | `id, user_id, company_id, role, is_owner, status, created_at` | **7 · nenhuma de contato** |
| `human_support_destinations` | 18, incl. `silence_minutes`, `active_hours`, `escalation_rules`, `fallback_enabled` | 4 dessas **não têm leitor** (R47) |
| `platform_sends` | `id, company_id, phone, kind, summary, sent_at, created_at` | `kind` sem CHECK |
| `work_events` | (usado) `company_id, event_type, actor_type, severity, message_human, payload_redacted, work_run_id` | `work_run_id` nulo é legítimo |
| `agent_activities` | `id, company_id, category, title, detail, created_at` | 6 |
| `conversations` | 25, incl. `status, user_phone, human_handoff_reason, claimed_by, claimed_by_name, claimed_at, ficha_atendimento, resolvido_em, resolucao_motivo` | — |
| tabela de números internos | 🔴 **não existe** (`… table_name like '%internal%' or like '%alert_target%'` → 0 linhas) | R49 |

### 3.7 🔴 O estado do produto — a pré-condição do canário

📊 Medido em 13/09/2026. **Tem de ser remedido e colado no relatório ANTES do primeiro caso do canário:**

```sql
select company_id, destination_type, is_primary, is_active from human_support_destinations;
--  4 linhas · 3 empresas · 1 ATIVA (AMANDUS) · Resulta e AutoFleet is_active=false
select id, company_name, agent_enabled from companies;          -- agent_enabled=false em 5 de 5
select count(*) from work_events where event_type like 'handoff%';   -- 0
```

⚠️ **Sem essa linha escrita, "0 mensagens ao grupo" será lido como "a guarda funcionou" — e não é: é o produto desligado.** Um canário que mede silêncio num sistema já mudo prova nada (CLAUDE.md §9.3).

🔴 **A ordem obrigatória do canário** (§14 da SPEC): criar destino no tenant de teste → ligar o agente → **medir a linha de base com a guarda DESLIGADA** → ligar a guarda e repetir. **O terceiro passo é o que dá direito à conclusão** (CLAUDE.md §9.2).

📊 Volumetria auxiliar: `agent_activities` por categoria — `atendimentos` 125 · `qualidade` 66 · `acionamentos` 41 · `auxiliares` 5. `work_events` por tipo — `step.*`/`run.*` dominam; `espera.vencida` **3** (todas 10/09); `travamento.*` **3** (todas 10/09).

---

## 4. ⚠️ O que no diagnóstico está vencido — corrija sem hesitar

| # | o diagnóstico diz | medido em 13/09 | ação |
|---|---|---|---|
| 1 | `handoff_watchdog.py` em `app/services/` | está em **`app/tasks/`** | corrigir o caminho |
| 2 | *"o re-alerta não pergunta se um humano está na conversa"* | ⚠️ **meia verdade** — já pergunta duas coisas (R12, R13); falta **só** a janela de N dias. 📊 73 de 131 já são caladas | reescrever a causa: é **a janela** que falta, não a pergunta |
| 3 | *"7 mensagens em 77 min"* | **75,7 min** | corrigir |
| 4 | *"quebra a cada 300 caracteres"* | cabe em 300 → inteiro; acima → **parte por parágrafo** (R34) | corrigir |
| 5 | `espera.vencida` em `dispatch_watchdog.py` | está em **`handoff_watchdog.py:407`** | corrigir |
| 6 | *"3 'espera vencida' de 10 em 10 min"* + *"3 dossiês por reabertura"* | ✅ **confirmado**, com hora | manter |
| 7 | *"58 de 58"* | ✅ **confirmado em SQL** — ⚠️ mas ver §3.3: falta confirmar **pelo motor** | remedir |
| 8 | `requireCompanyMember` em `admin-auth-policy.ts` | está em **`admin-auth.ts:68`** | corrigir |
| 9 | P-PILOTO-10: *"a AutoFleet segue com zero destinos"* | **vencida** — AutoFleet tem 1 destino próprio; os dois das pilotos `is_active=false` | reavaliar a pendência |
| 10 | *"`alert_target.internal_numbers` … só impedem a captura"* | ✅ e **pior**: nunca populadas, e `whatsapp_channel.py:1124` as **apaga** (R54) | pendência nova |

---

## 5. O que continua desconhecido

1. 🔴 **O número do motor** (§3.3): quantas das 58 `ultima_palavra_humana` realmente cala.
2. **Quantas conversas a guarda deixaria passar** — o outro lado do teste. Uma guarda que cala tudo reprova.
3. **Quem é `owner`/`admin` na Resulta e na AutoFleet** — decide se o BLOCO G tira acesso de quem usa as telas hoje (Caixa do Founder, item 2).
4. **Se o CHECK de `destination_type` aceita `whatsapp_number`** (R48) — ou se o backfill de 03/08 falhou em silêncio.
5. **Quantos balões o dossiê real gera** — a medição de §3.4 é sobre sessão sintética.
6. **Se existe alguma edição manual de `internal_numbers`** no banco — decide se há backfill (§13 da SPEC).
7. **Se `work_events` tem escritor para tudo que o resumo das 19h precisa contar.** 📊 `agente.cerebro|sentinela|vigia`: 0 de 0 (diagnóstico §11.2c). `handoff.realertado`: 0. **Número sem escritor vira "não medido", nunca estimativa.**
7b. 🔴 **`motivo_classe` não tem escritor NENHUM hoje.** 📊 `grep -rn "motivo_classe" backend/app` → **0**; `human_handoff_reason` vazio em **129 de 131**, e as 2 preenchidas são prosa livre. **Consequência de contrato:** se `desconhecido` caísse em `regra`, todo pedido de ajuda sairia do denominador e a eficiência daria **~100% sem medir nada**. Por isso `desconhecido` fica fora do numerador **e** do denominador, com linha própria, e o resumo **não publica** o número acima de 💭 30% de desconhecidos. **O escritor nomeado é `app/agents/tools/human_handoff.py`** (`_arun` :1182 e `_montar_dossie` :710); os gatilhos automáticos gravam `desconhecido` explicitamente. **PENDENTE DE MEDIÇÃO:** a fatia real de desconhecidos num dia de piloto, que calibra o limite.
8. **Qual é o volume real de um dia de piloto** com o agente ligado 8 h — todo o dimensionamento desta SPEC vem de 1h53 de operação em três dias.
9. **Se a Saionara e a Regina leem o grupo no celular ou no WhatsApp Web** — muda a régua de tamanho da mensagem.
10. **Se algum outro serviço lê `platform_sends` sem filtrar `kind`** além do governador (R41). Uma varredura, não uma suposição.

---

## 6. Roteiro de remedição — leitura antes de edição

Rodar **de dentro de `backend/`**, com `PYTHONIOENCODING=utf-8`.

```bash
# preflight — CLAUDE.md §2
git fetch origin
git rev-list --count HEAD..origin/main     # TEM de ser 0
git rev-list --count origin/main..HEAD
git branch --show-current && git rev-parse HEAD && git status --short

# os onze pontos de envio ao grupo
rg -n "resolver_destino_de_suporte|_support_contact|_support_alert|_avisar_suporte" backend/app
rg -n "bloco_unico" backend/app
rg -n "build_handoff_dossier|_montar_dossie|_dossie_de_pos_acionamento" backend/app

# a janela, e a prova de que ninguém a consulta
rg -n "a_ia_deve_calar|janela_de_silencio_dias|ultima_palavra_humana|_variantes_do_telefone" backend/app
rg -n "JANELA_DO_GRUPO|GRUPO_SILENCIO"        # TEM de dar ZERO (guarda G-A3)

# a contabilidade e o governador
rg -n "platform_sends|record_platform_send|_historico_sync" backend/app
rg -n "internal_numbers|observer_exclusions|alert_target" backend/app app

# autorização
rg -n "requireCompanyMember|assertSameOrigin|writeAudit|resolveSessionCompany" app lib

# o gate de ligar
rg -n "attendance_agent_active|corretoras_ligadas_sem_destino" backend/app

# pendências POR NÚMERO — ⛔ nunca o arquivo inteiro (562 KB)
rg -n "P-PILOTO-02|P-PILOTO-03|P-PILOTO-04|P-PILOTO-10|P-PILOTO-12|P-PILOTO-13|P-PILOTO-20" docs/canon/PENDENCIAS.md
```

**Antes de qualquer SQL:** ler `docs/canon/MIGRATIONS-AUTHORITY.md` **inteiro**. Medir o schema por `information_schema`, não por suposição. ⛔ Nunca consultar segredo como parte de um censo; manter telefone e conteúdo pessoal fora de qualquer saída compartilhada.

### Censo mínimo que a SPEC definitiva registra

| medição | forma de evidência | ⛔ não concluir |
|---|---|---|
| as 58 pelo motor | `ultima_palavra_humana` sobre as conversas reais | SQL = motor |
| os 11 pontos | AST/varredura + leitura da função inteira | "achei todos" sem o comando |
| balões do dossiê real | sessão do acervo pelo caminho real de envio | 4 → 1 por leitura de código |
| governador | inserção controlada + leitura da cota, **com linha de controle** | "filtrei o kind" sem provar que sem filtro ele contava |
| isolamento | duas corretoras reais, guarda e números | RLS = proteção (service role) |
| papéis na Resulta/AutoFleet | `select role, is_owner, count(*) from company_members group by 1,2` | "todo mundo é admin" |
| escritores do resumo | contagem por `event_type` do dia | número sem escritor vira estimativa |

---

## 7. Armadilhas que o aquecimento deve refutar

1. *"O re-alerta de 6 h não checa humano nenhum."* **Falso.** Checa duas coisas (R12, R13). Falta **a janela**.
2. *"Basta pôr `bloco_unico=True` e o dossiê chega inteiro."* Incompleto: são **três** caminhos, e o caminho da tool já tem a flag — quem consertar um e declarar vitória repete o erro de 18/08.
3. *"`platform_sends` é só um log; escrever nele é inócuo."* **Falso** — R41. Ele alimenta o governador em **três** leituras, e duas delas decidem a **maturidade do canal**.
3b. *"Basta excluir os `kind` que começam com `grupo_`."* **Falso** — R41c: `billing_nota` da 001.6 não tem esse prefixo e seria contado. É **allowlist**, não prefixo.
3c. *"Se `motivo_classe` vier vazio, é ajuda por regra — o agente não erra sem prova."* **Falso e perigoso** — §5 item 7b: com zero escritores hoje, isso dá **~100% de eficiência sem medir nada**.
4. *"A guarda tem de ser fail-closed, como a do atendimento."* **Não.** A assimetria é deliberada (§5.4 da SPEC): calar por falha de infraestrutura é o defeito pior.
5. *"O grupo deve calar sobre tudo quando há humano na conversa."* **Não.** Sinistro, conclusão e resumo passam sempre (§5.3). Uma guarda que cala tudo reprova no G-A1 pela linha de controle.
6. *"`company_members` tem telefone, é só ler."* **Falso** — R55. O telefone é de `users_v2`.
7. *"`alert_target.internal_numbers` já resolve os números da casa, basta popular."* **Falso** — R51/R53/R54: três formatos, nenhum escritor, e um `update` que apaga tudo.
8. *"O resumo das 19h precisa de um scheduler novo."* **Falso** — R71. Entra no APScheduler que já existe, no padrão do relatório semanal.
9. *"`requireCompanyMember` é só trocar a linha; não muda nada para ninguém."* **Falso** — R62: `write:true` exige papel administrativo, e isso pode tirar acesso de quem usa a tela hoje.
10. *"O 58 de 58 é fato consolidado."* É fato **em SQL, num instante**. Em Python pode ser outro número (§3.3), e 📊 na mesma tarde já deu **59/72**. Quem citar sem remedir viola CLAUDE.md §9.4; quem **fixar 58 numa asserção** cria um guarda que fica vermelho sozinho.
11. *"As 58 já estão gerando mensagem hoje."* **Falso** — `handoff.realertado` = 0. É risco carregado, não dano em curso. Dizer o contrário é vender inferência como incidente. ⚠️ E quando disparar, o teto é **≤ 50 por passada**, não 58.
11b. *"O canário mostrou 0 mensagens ao grupo: a guarda funcionou."* **Não prova nada** se o produto estava desligado — 📊 hoje há **1 destino ativo em 4** (nenhum das pilotos) e `agent_enabled=false` em **5 de 5**. Sem a linha de base do §3.7 (com a guarda desligada), o canário mede silêncio num sistema já mudo.
12. *"Como `espera_vencida` repete 3×, basta cortar `AVISOS_ATE_EXPIRAR` para 1."* **Quebra a expiração** (R19). Corta-se quantos **chegam ao grupo**, não o contador interno.

---

## 8. Pendências herdadas — drenar por número, com estado

| número | o que é | estado esperado ao fim |
|---|---|---|
| **P-PILOTO-02** | acionamento pelo portal não aparece na Fila nem na Ficha | ⚠️ **Tocada de raspão.** Esta SPEC muda a Fila só para **excluir** número da casa. Reavaliar: `CONTINUA`, com o que destrava |
| **P-PILOTO-03** | o PDF do segurado some da Ficha | Idem. Reavaliar; provavelmente `CONTINUA` |
| **P-PILOTO-04** | sinistro/empresarial/condomínio sem checklist | **Parcialmente absorvida**: o modelo 🚨 e o campo "pontos de atenção" nascem aqui; o **conteúdo** fica para a 001.5. `CONTINUA` com escopo reduzido escrito |
| **P-PILOTO-12** | a régua de língua humana não roda nos dossiês | **Absorvida** — §8.6 da SPEC. `FECHADA` com a prova do G-D1 |
| **P-PILOTO-10** | grupo da AutoFleet cadastrado na Resulta | ⚠️ **Vencida** (§4 item 9). `FECHADA` com ressalva |
| **P-PILOTO-13** | 174 conversas-fantasma LID | **Dependência** (§21 da SPEC). `CONTINUA` — é da 001.2 |
| **P-PILOTO-15** | pausa não protege conversa com `resolvido_em` | Vizinha da guarda. Reavaliar |
| **P-PILOTO-20** | 4 guardas de policy quebram no harness | Ruído na baseline da suíte. Não rotular como regressão |

**Pendências novas que esta SPEC deve registrar:**

- `weekly_report`/`proactive_suggestions` ignoram `human_support_destinations` (R09);
- `whatsapp_channel.py:1124` sobrescreve `alert_target` e apaga `observer_scope`/`observer_exclusions`/`internal_numbers` (R54);
- `handoff.realertado` com **0 linhas** desde 26/08 — a telemetria existe e nunca foi exercida;
- 4 colunas de `human_support_destinations` sem leitor (R47);
- `destination_type='whatsapp_number'` fora do CHECK (R48).

---

## 9. Referências externas — as cinco reabertas em 13/09/2026

Transportar para a §19 da SPEC definitiva no formato AAA §7.3. O pesquisador do Fable **reabre cada uma na conversão** e registra a data; se uma envelheceu ou houver melhor, troca e diz por quê.

| ID | fonte | o ponto que modelamos |
|---|---|---|
| **E01** | Google SRE Book, cap. 6 *Monitoring Distributed Systems* — https://sre.google/sre-book/monitoring-distributed-systems/ | *"Are other people getting paged for this issue, therefore rendering at least one of the pages unnecessary?"* → a guarda como **pré-condição**, não filtro de entrega |
| **E02** | Google SRE Book, cap. 11 *Being On-Call* — https://sre.google/sre-book/being-on-call/ | *"Noisy alerts that systematically generate more than one alert per incident should be tweaked to approach a 1:1 alert/incident ratio."* → 📊 o 10/09 foi **7:1** |
| **E03** | PagerDuty, Events API v2, *Send an Alert Event* — https://developer.pagerduty.com/docs/events-api-v2/trigger-events/ ⚠️ SPA: ler `…/index.html` | `dedup_key` do **incidente**, não da execução; e `acknowledge` = "alguém está trabalhando nisto" → o BLOCO A |
| **E04** | Prometheus Alertmanager, `inhibit_rules` — https://prometheus.io/docs/alerting/latest/configuration/ e https://prometheus.io/docs/alerting/latest/alertmanager/ | *"Both target and source alerts must have the same label values for the label names in the equal list."* → o nosso `equal` é **a conversa** |
| **E05** | Prometheus Alertmanager, `route` — https://prometheus.io/docs/alerting/latest/configuration/#route | *"Notifications are not repeated if any new alerts have fired … since the last group_interval."* → separar **"tem novidade"** de **"estou repetindo"** |

⛔ Referência externa **nunca** vira autoridade (AAA §7.3): Smith, Work OS, Tool Gateway, Skill Registry e Artifact Hub continuam únicos. Modela-se o **padrão**.

---

## 10. Regra de integridade deste pacote

Este research pack é **evidência de 13/09/2026**, não contrato permanente. Toda coordenada `arquivo:linha` foi reaberta hoje; toda contagem tem o comando ao lado; todo número sem comando **não existe**.

🔴 **Se o BLOCO 0 medir diferente, o número do executor vence** (AAA §5 ①), e a divergência vai **escrita** no relatório — não se "conserta" este documento para esconder que o mundo mudou.
