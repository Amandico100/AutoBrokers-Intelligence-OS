# BLOCO 0 · SPEC-133-A · Quem Cobra Menos no WhatsApp — laudo do INVESTIGADOR

> 07/10/2026 · read-only · árvore `AutoBrokers-FIX`, branch `spec/133-A-qcm-whatsapp`, HEAD `de66449`, `HEAD..origin/main` = **0**.
> Banco: só `SELECT` com `set transaction read only` (script `scratchpad/q.py`, psycopg). Nenhum segredo, CPF ou telefone impresso
> (telefones aparecem só como os 4 últimos dígitos, que já estão nos documentos).
> Marcas: **FATO** (arquivo:linha ou SELECT) · **INFERÊNCIA** · **RECOMENDAÇÃO**. 📊 = medido aqui, com o comando ao lado.

⚠️ **Árvore suja ao iniciar** (`git status --short`): uma F0 em curso (do gerente) mexe em `proposta_html.py`, `mensagem.py`,
`proposta.py`, `config.py`, `comando_proposta.py`, `brand/capture.py`, `api/brand.py`, a tela de identidade e `FOUNDER-DECISIONS.md`
(D-130A1-15/16). 📊 `git diff --stat` → 14 arquivos, +700/−514. **Esses arquivos têm dono agora; as fatias abaixo os evitam ou entram depois.**

---

## 1. WhatsApp de entrada e de saída

### 1.1 O caminho de um "oi" hoje (FATO)
| elo | onde | o que faz |
|---|---|---|
| ① rota | `backend/app/api/webhook.py:2867` `evolution_go_webhook_token` (e `:2857` para o Evolution v2) | `POST /api/v1/webhook/evolution-go/{token}`, 240/min |
| ② dono | `webhook.py:2508` `_resolve_webhook_integration` | **a EMPRESA vem da linha de `integrations` achada pelo HASH do token do path** (nunca do corpo); 401 uniforme |
| ③ observador | `webhook.py:2886` → `atlas/observer_intake.py:789-829` `observer_tap` | `purpose='observer'` **e** `attendance_agent_active(company)` falso → **CONSOME** o evento (`{"status":"observed"}`) e nada mais roda |
| ④ envelope | `webhook.py:2899` `go_event_to_v2_envelope` → `:2909` `_handle_evolution_like_inbound` → `evolution_inbound.py:849` `normalize_evolution_inbound` | `skip` para `from_me` e grupo (o ramo `from_me` espelha no chat e PAUSA a IA naquela conversa: `:2950-3150`) · dedup Redis · mídia baixada |
| ⑤ buffer | `webhook.py:2647` `_buffer_or_dispatch_text` → `message_buffer_service.add_message` → `tasks/buffer_processor.py:1316` `check_buffers` (job de 1 s) | a rajada vira UM turno; o `_integration_id` viaja no payload |
| ⑥ turno | `webhook.py:1045` `process_whatsapp_message_background` · `:1117-1118` `company_id = integration["company_id"]`, `agent_id = integration.get("agent_id")` | |
| ⑦ portões | `:1149` acionamento (número de seguradora) · `:1300` palavra da equipe · **`:1348-1356` `ATTENDANT_INBOUND_ALLOWLIST`** · `:1358` `get_or_create_user` · `:1440` modo humano · **`:1863-1895` portão de silêncio `attendance_agent_active`** · `:1907` porteira de billing (`BILLING_ENFORCEMENT`, padrão desligado) | |
| ⑧ agente | `:1989-2005` `LangChainService.process_message(..., required_role="attendance")` → `langchain_service.py:212-266` `_get_raw_agent` | **papel pedido é papel entregue**: sem agente ATIVO com `agent_role='attendance'` → `AGENTE_DE_PAPEL_AUSENTE` (`:345-361`) |
| ⑨ saída | `:2261` `whatsapp_service.send_message` | ver 1.4 |

### 1.2 A empresa do canal nesse caminho (FATO + INFERÊNCIA)
📊 `select id, company_name, company_kind, is_technical from companies` → `f6a92478… | AutoBrokers Canal de Cotação | platform_canal | True`.
📊 `select … from agents join companies` → **o canal NÃO tem agente nenhum** (as 4 outras empresas têm `core` e `attendance`; todos os
`attendance` estão `is_active=false`).
📊 `select … from integrations` → 7 linhas; as **3 ativas** são `evolution-go`, `purpose='observer'`, `connected` (Resulta `…2089`,
AMANDUS `…4743`, AutoFleet `…9360`). **Nenhuma integração do canal.** A z-api retirada da AMANDUS tem identifier `…7463` (`retired`).

O pareamento grava SEMPRE `purpose='observer'` para tudo que não é auxiliar: `pairing_orchestrator.py:593-598` →
`channel_identity.py:141-153` `purpose_canonico` (attendance/dispatch/qualquer coisa → `observer`). Instância:
`channel_identity.py:122-138` → `ab-obs-<10 primeiros do company_id>-1`.

**INFERÊNCIA (o que impede hoje):** se o número do canal for pareado pelo hub como está, a mensagem do convidado **morre no ③**
(observer + nenhum agente attendance ativo no canal). Se alguém "resolver" criando um agente `attendance` ativo no canal, o ⑧ roda o
grafo do ATENDIMENTO da corretora (prompt, ferramentas, handoff, RAG, papel `atendimento` = `gpt-6.1-sol high`) — errado de escopo
e caro. E ainda há o ⑦ `ATTENDANT_INBOUND_ALLOWLIST`: **variável de PROCESSO, global**, sem corretora
(`whatsapp/channel_security.py:61-98`); preenchida com 1 número, ela descarta em silêncio todo convidado do canal (P-E0017-13).
O que o canal NÃO sofre: acionamento (`try_route_insurer_inbound` só age com dispatch ativo), cartógrafo (`CARTOGRAPHER_MODE`),
billing (desligado por padrão), cota por corretora/buffer (por escopo — funciona igual).
Grupos: chegam com `skip_reason="group"` (`webhook.py:2933-2950`); as instâncias nascem com `ignoreGroups` (comentário `:2935`).

**RECOMENDAÇÃO:** um desvio ÚNICO por `company_kind` em DOIS pontos do `webhook.py` (dono: uma fatia):
(a) em `evolution_go_webhook_token`, ANTES do `observer_tap` (`:2879`): empresa `platform_canal` → não passa pelo tap (nada de acervo
de seguradora no canal); (b) em `process_whatsapp_message_background`, logo depois de `:1118`: `platform_canal` → `canal.turno(...)` e
`return` — antes do acionamento, da allowlist global, do portão de silêncio e do LangChain. Reusa token, dedup, mídia, buffer,
rajada, presença e `send_message`; não cria webhook nem fila.

### 1.3 Grupos, `fromMe` e o eco (FATO)
`fromMe` no canal (o Founder usando o próprio celular 7463) cai no ramo `:2950+`: `espelhar_no_chat` + `pausar_por_intervencao_humana`
+ `note_manual_outbound` **na empresa do canal**. A digital da própria voz (`whatsapp/voz_propria.py`, gravada em
`whatsapp_service.py:200-204`) evita que o eco do robô pause o robô.

### 1.4 A SAÍDA (FATO)
`backend/app/services/whatsapp_service.py:131-232` `send_message(to_number, text, integration, *, bloco_unico=False)`:
- divide em balões com `whatsapp/balloons.py:73` `split_whatsapp_balloons` (alvo 300 chars, duro 500, **máx. 4**, nunca quebra lista);
- **0,7 s entre balões** (`:211 _dormir(0.7)`), 1 nova tentativa com 1,2 s e, se > 400 chars, meia a meia;
- provider ≠ z-api → `whatsapp/registry.py resolve_provider(integration).send_text` (Evolution Go);
- registra a própria voz por `company_id` da integração; **síncrono** (`requests`, 30 s) → o webhook chama via `asyncio.to_thread`.
- `bloco_unico=True` desliga os balões (documento). Presença "digitando…": `send_presence` (`:234`).
⚠️ `mensagem.mensagem_para` já devolve `List[str]` (balões prontos, `mensagem.py:527-532`): mandar cada um por `send_message` pode
re-picotar um balão > 300 chars — o builder decide (`bloco_unico=True` por balão, ou conferir o tamanho).

---

## 2. O hub e o QR

### 2.1 FATO
- Tela: `app/dashboard/personalizacao/corretora/whatsapp/page.tsx` → `WhatsAppHubClient.tsx` → modal `components/vault/WhatsAppChannelModal.tsx`
  → `components/vault/WhatsAppChannelCard.tsx` (fetch **fixo** em `/api/dashboard/whatsapp-channel`: `:76`, `:105`, `:160`, `:195`)
  e `WhatsAppPairingFlow.tsx` (fixo: `:59`, `:102`, `:150`).
- Proxy Next: `app/api/dashboard/whatsapp-channel/route.ts` — `PURPOSE='observer'` (`:11`), `PROVIDER='evolution-go'`; GET por
  `resolveSessionCompany()` (`:195`), POST por `porteiroDeConfiguracao` (`:250`); a **empresa vem da SESSÃO** do dashboard. Chama o
  backend com `X-AutoBrokers-Internal-Key` (`BACKEND_INTERNAL_API_KEY` ou `ADMIN_API_KEY`).
- Backend: `backend/app/api/whatsapp_channel.py` — `POST /api/whatsapp-channel/pairing` (`:491`), `GET …/pairing/{id}` (`:513`),
  `retry`/`cancel` (`:529`/`:550`), `GET /api/whatsapp-channel/qr` (`:877`), `status`, `disconnect`, `set-alert`, diagnóstico admin
  (`:597`). **Todos recebem `company_id` no corpo/query + a chave interna** (`_require_internal_key`, `:40`). Quem cria a instância e
  o QR é `services/whatsapp/pairing_orchestrator.py` (1.618 linhas; grava a linha de `integrations` em `:775-805`, `agent_id` só para
  `attendance`, `permite_envio_de_auxiliar` nasce `false`).
- Saúde: `channel_status`/`last_seen_at` pelo `connection.update` (`webhook.py:2914-2930`) + o job `channel_heartbeat_check`
  (`tasks/buffer_processor.py:1878`); queda → `_notify_disconnect_background` → `whatsapp/alerts.py:277`.
- `app/api/vault/whatsapp/health` e `app/api/vault/connections/[connectionId]/whatsapp/{configure,test}` são o "Secret Flow" antigo
  (credencial digitada, z-api) — **não** são o caminho do QR.
- Admin: sessão `iron-session` (`adminSessionOptions`, `role === 'master_admin'`) — molde em `app/api/admin/integrations/route.ts:25-60`.
  Existe `app/admin/companies/[companyId]/{activation,agents}`; **nenhuma página de canal** (📊 `grep -rln "platform_canal" app/admin` → 0).

### 2.2 O que falta para o admin ler o QR do canal (RECOMENDAÇÃO)
1. `app/api/admin/canais/whatsapp/route.ts` (NOVO): porteiro `master_admin`; resolve a empresa do canal **pelo banco**
   (`company_kind='platform_canal'`, nunca constante — §13.9); repassa as MESMAS ações do proxy do dashboard ao MESMO backend.
2. `app/admin/canais/quem-cobra-menos/whatsapp/page.tsx` (NOVO) usando o `WhatsAppChannelCard` com uma prop `endpoint`
   (padrão = o de hoje; o dashboard não muda um byte).
3. Backend: **nada obrigatório** (os endpoints já aceitam qualquer `company_id`). Opcional: recusar `purpose` de auxiliar para o canal.
4. Mexe em `app/` → §9.1: `npm run test:rotas-montam` + `next start` + 1 requisição a `/api/…`.

### 2.3 Variáveis do Evolution (só NOMES) — 📊 `grep -rhoE` em `backend/app`
`EVOLUTION_GO_BASE_URL` · `EVOLUTION_GO_GLOBAL_KEY` · `EVOLUTION_GO_INSTANCE_TOKEN` · `EVOLUTION_GO_INSTANCE_NAME` ·
`EVOLUTION_GO_FLOW_REPLY_PATH` · `EVOLUTION_BASE_URL` · `EVOLUTION_API_KEY` · `WHATSAPP_CHANNEL_PROVIDER` · `BACKEND_PUBLIC_URL`
(URL do webhook) · `WHATSAPP_WEBHOOK_AUTH_MODE` · `WHATSAPP_WEBHOOK_SECRET` · `WHATSAPP_DEDUPE_TTL_SECONDS` ·
`WHATSAPP_BUFFER_PARALELISMO` · `WHATSAPP_COTA_POR_CORRETORA` · `WHATSAPP_TURNO_TIMEOUT_S` · `PLATFORM_ALERT_WA_{TOKEN,PROVIDER,INSTANCE_ID,BASE_URL}` ·
`PLATFORM_ALERT_FALLBACK_NUMBER` · `ATTENDANT_INBOUND_ALLOWLIST`. Nenhuma nova é necessária para parear o canal.

---

## 3. O agente

### 3.1 Como roda hoje (FATO)
- Tabela `agents` — 📊 CHECK `agents_agent_role_check`: `core · attendance · auxiliary · subagent · corridor · connector · system`.
  **Não existe papel de canal**; acrescentar um = migration de CHECK (piso CRÍTICO).
- Grafo: `app/agents/graph.py:154` `create_agent_graph` — capabilities por `agent_role` (`:254-257`), ferramentas por papel
  (`:474-486`), checkpointer Postgres por `session_id` (`:42` `get_async_postgres_checkpointer`; sessão =
  `whatsapp:{phone}:{company}:{agent}`, `webhook.py:1363-1364`).
- Model Router: `app/factories/model_policy.py:260` `resolver(papel)` — rota em `llm_papeis` → modelo do agente → erro (nunca "cai no
  mini"); produção só `APPROVED`. Chamada única com reserva e **ledger**: `app/factories/llm_factory.py:595`
  `invocar_com_reserva(papel, mensagens, company_id=, service_type=)` (molde: `app/atendimento/confirmacao.py:156-161`).
  Ledger = `token_usage_logs` (`company_id, agent_id, service_type, model_name, input/output_tokens, total_cost_usd`), via
  `core/callbacks/cost_callback.py`.
- 📊 `select … from llm_papeis` → 28 papéis; `atendimento` = `openai gpt-6.1-sol high` (reserva `claude-opus-5-5`);
  `confirmacao` = `gpt-6-luna medium` (reserva `claude-sonnet-5-5`).
- 📊 `select model_name, input/output_price_per_million from llm_pricing where lifecycle='APPROVED'` → **o mais barato de conversa é
  `gpt-6-luna` (US$ 0,10 / 0,50 por 1 M)**; `gpt-6.1-sol` e `claude-sonnet-5-5` US$ 2 / 10; `claude-opus-5-5` US$ 4 / 20.

### 3.2 Três jeitos de fazer o agente de escopo estreito (RECOMENDAÇÃO, com nota)
| opção | o quê | nota |
|---|---|---|
| **A** | **conversa guiada por ESTADO** (as perguntas, uma por vez, em ordem, com o texto humano fixo e curto) + o modelo só para ENTENDER a resposta livre e responder objeção curta, por `invocar_com_reserva` num papel novo `canal_cotacao` (linha em `llm_papeis`, `gpt-6-luna`, reserva `claude-sonnet-5-5`, classe `pii`). Estado durável no Work OS (3.3) | **86** — escopo garantido por código, barato (💭 centavos por cotação), testável sem modelo, reusa roteador + ledger + Work OS |
| B | o grafo LangGraph com um papel novo (`agents.agent_role` CHECK + capabilities + ferramenta `cotar_auto`) | 60 — o grafo carrega ramos de atendimento/core, RAG e ferramentas; escopo só por prompt; CPF passa pelo modelo a cada turno |
| C | dar ao canal um agente `attendance` ativo | 30 — herda prompt/handoff/silêncio do atendimento das corretoras; ninguém controla o escopo |

### 3.3 Onde a conversa guarda estado (FATO + RECOMENDAÇÃO)
FATO: hoje a memória do agente mora em 6 lugares (checkpoints LangGraph, `conversations`/`messages`, `user_memories`,
`session_summaries`, `conversation_logs`, Redis — P-E0017-14). Não há tabela de "slots" de conversa (📊 `information_schema.tables`
com `slot|state|sess` → só `attendance_sessions`, `observed_sessions`, `portal_sessions`, `session_summaries`, admin).
RECOMENDAÇÃO: uma tabela própria do canal (ver §6) com o estado da conversa e as respostas **cifradas** (`portal_vault.encrypt`,
o mesmo cofre do `pedido_cifrado`), por `company_id` do canal + telefone; a cotação, quando dispara, vira um **Work Run**
(`workflow_key='canal.cotacao'`, `registrar_workflow`, `services/work/workflows.py:33`) que acompanha, publica, pergunta, dorme para
os lembretes e acorda (§8). Nada em Redis como verdade (Redis é transitório, CLAUDE.md §6).

---

## 4. O pedido ao motor

### 4.1 A porta (FATO) — `backend/app/services/multicalculo/porta.py`
```python
async def calcular(self, *, company_id: str, pedido: PedidoDeCalculo,
                   corretoras: Optional[Iterable[str]] = None, opcoes: Iterable[str] = OPCOES_PADRAO,
                   coberturas=None, origem: str, quadro_s: int = 60) -> PedidoAberto      # :278
async def consultar(self, *, company_id: str, pedido_id: str, desde_evento: int = 0) -> Andamento   # :346
```
- `OPCOES_DO_CANAL = ("padrao", "economica", "minima")` (`:51`); `ORIGENS = ("auxiliar","canal","teste")`; canal: **prioridade 0,
  validade 10 min na fila** (`:58-63`).
- Autorização `:252-269`: o canal (`platform_canal`) só calcula em corretora com **adesão ativa** em `multicalculo_adesoes`.
  📊 `select … from multicalculo_adesoes` → canal→Resulta `ativa=t`, canal→AutoFleet `ativa=t`. **Quem escolhe as corretoras é o
  CHAMADOR** (passa `corretoras=`); não há função "todas as aderidas" — a 133-A lê as adesões ativas e passa a lista (o repositório já
  tem `adesoes_ativas`).
- `origem="canal"` exige o perfil PERGUNTADO (`:313-316` → `PerfilIncompleto`); `faltando()` + `sem_codigo()` → `PedidoIncompleto` (`:309-312`).
- `MULTICALCULO_HMAC_KEY` ausente → `ChaveAusente` antes de gravar (`:319`). O pedido sai cifrado com `portal_vault.encrypt` (`:330`).
- `consultar` devolve `Andamento(status, estados por cálculo com posicao_na_fila/primeira_oferta_em/quadro_pronto_em, ofertas menor
  prêmio primeiro, eventos > desde_evento)`; comissão cortada para quem não é dono (`:206-216`).

### 4.2 O que o PEDIDO precisa (FATO, sem dado pessoal)
Forma (`pedido.py:252-280` `para_dict`): `{ramo:31, segurado:{…}, veiculo:{…}, pernoite:{…}, condutor:{…}, renovacao:{…},
coberturas:{}, pacotes:{}, comissao_desconto:{…}, questionario:{km_mensal}, seguradoras:[…], assumidos:[…]}`; nomes de campo de
`backend/portal_worker/multicalculo/contrato.py:90-144`.
- **Os 16 obrigatórios** (`obrigatorio=True`): segurado `cpf_cnpj, nome, nascimento, sexo, estado_civil, cep` · veiculo `fipe,
  ano_fabricacao, combustivel` · pernoite `cep_pernoite` · condutor `cpf, nome, nascimento, sexo, estado_civil, tempo_habilitacao`.
- **O perfil do canal** (`pedido.py:37-42`): `pernoite.garagem_residencia` · `veiculo.uso` · `questionario.km_mensal` ·
  `condutor.jovem_condutor` (+ D-MC-70: "usa para aplicativo?" é a 1ª pergunta — não há campo próprio; é `veiculo.uso`).
- Códigos MEDIDOS (`contrato.py:180-186`): sexo M/F · tipo_pessoa F/J · **combustível só `flex`→6** · relação `proprio`→1. Inteiros
  sem tabela de nomes: `estado_civil`, `tempo_habilitacao`, `uso`, `km_mensal` (`:188-193`). Garagem = texto de dígito.
- O canário da 129-B usou um perfil JSON **fora do git** (`scripts/multicalculo_canario.py:50,112-124`); só a forma acima é sabida.
  ⛔ Não decifrei o `pedido_cifrado`.

🔴 **ACHADO 1 — a porta é mais exigente que o robô.** O robô completa veículo pela PLACA (`agger_robo.py:310-316` `buscaPlaca` →
`fipeModelo`; `montador.js:121-129` preenche `fabricante, anoModelo, anoFabricacao, fipe, combustivel` do `bp`) e só exige
`placa|fipe` (`agger_robo.py:178-179`). Mas `PedidoDeCalculo.faltando()` (`pedido.py:220-226`) exige `fipe`, `ano_fabricacao` e
`combustivel` → **a pessoa que só sabe a placa é recusada pela porta**. Sem mudar isso, o canal teria de perguntar o código FIPE (ninguém
sabe). RECOMENDAÇÃO: na origem `canal`, placa presente supre os 3 (viram `assumidos` "pelo Agger a partir da placa") — mudança em
`pedido.py`/`porta.py` (fora da F0).
🔴 **ACHADO 2 — `estado_civil` não tem código medido** (só "inteiro"); combustível ≠ flex é recusado. A conversa precisa do mapa
"casado/solteiro/…"→código do Agger, medido (ou buscado pelo CPF no Agger, que a E4 mediu **instável**: 4 de 5 `false`).
💭 Perguntas mínimas para fechar o pedido: app? · placa · CEP de pernoite (= CEP) · garagem · km/mês · jovem condutor · CPF · nome ·
nascimento · sexo · estado civil · tempo de habilitação (condutor = segurado é assumido) → **≈ 12 perguntas**; com consentimento e
resultado, a "8–15 mensagens nossas" fica no teto.

### 4.3 Como se espera o resultado e quem publica (FATO)
- Ninguém "aguarda" na porta: o chamador consulta aos poucos (`consultar(desde_evento=)`). A espera durável da 129-A: `runs.dormir`
  (`services/work/runs.py:469`) → `waiting_input` + `wake_at` + `wait_for`; o **despertador** roda no laço de órfãos do `smith-worker`
  a cada **60 s** (`workers/smith_worker.py:47` `WORK_ORPHAN_SCAN_INTERVAL_S`, `:160-186`). Molde do relógio:
  `workflows.py:1136-1170` `workflow_espera_de_teste`; molde de "conferir e dormir": `workflows.py:875-926` `_conferir_o_portal`.
  INFERÊNCIA: 60 s é grosso para narrar um cálculo de 1–8 min → o acompanhamento deve ser um passo que CONSULTA no próprio run
  (com heartbeat) a cada 💭 5–10 s até o quadro/teto, e o `dormir` fica para os lembretes.
- Quanto tempo: Agger isolado 📊 1ª oferta ~6 s e resultado em 36 s (E3, `A-PROVA-DO-AGGER.md:59-62`); recálculo no canário 1ª oferta
  34 s, quadro 83 s (`SPEC-129-B-EXECUTION-REPORT.md:71-72`); + login 📊 5–52 s (`motor.py:58-61`).
- **`publicar_proposta`** (`multicalculo/proposta.py:862`) — único chamador: o comando de linha `comando_proposta.py:157`. Devolve
  `{url, token, artifact_id, versao, mensagem, validade_ate}`; `mensagem = mensagem_para(modelo, url)` (`:926`). O artefato mora no
  SOLICITANTE (o canal). **Recusa sem WhatsApp de atendimento da anfitriã** (`SemCanalDeFechamento`, `:886-892`) salvo
  `permitir_sem_whatsapp=True` → depende da T-125. `modelo.origem='canal'` quando o solicitante é `platform_canal` (`proposta.py:707`).

---

## 5. Paralelo entre corretoras e a "fila de 85 s"

### 5.1 FATO — o motor JÁ é paralelo; o `concurrency: 1` é de OUTRA fila
- `concurrency` do `/health` (`portal_worker/main.py:184`) = `PORTAL_WORKER_CONCURRENCY` (`leases.py:294-305`, padrão 1), que governa o
  `run_lote` dos `portal_jobs` (cobrança/vidros, `worker.py:1658-1700`) — **não o multicálculo**.
- O motor tem laço PRÓPRIO, navegador PRÓPRIO (D-MC-42) e volta de **5 s** (`multicalculo/motor.py:62-64` `VOLTA_S=5`,
  `:1304-1338` `laco_do_motor`), não os 30 s do `PORTAL_POLL_SECONDS` (`worker.py:21`).
- `_reservar` (`motor.py:476-552`) agrupa por (pedido, corretora) e `uma_volta` cria **uma task por grupo** (`:316-336`
  `asyncio.create_task(self._executar_grupo(...))`) — docstring: *"Corretoras diferentes saem em PARALELO; a mesma conta, um grupo por
  vez (a lease)"*. As sessões: **um Chromium, um `new_context` por conta**, trava por conta (`agger_sessao.py:167-212`). A trava "conta
  da mesma corretora" = lease no banco (`robos.escolher`, `robos.py:244-280`) + `_contas_em_uso`.

### 5.2 📊 O que o canário `d0bb15ba` realmente mostra
```
select … from multicalculo_calculos where pedido_id='d0bb15ba-…'   →  dono = canario:DESKTOP-…:m2 (o PC do Founder, não o contêiner)
   4 cálculos: disparado_em IDÊNTICO (…01:01:22.238316) nas DUAS corretoras · disponivel_em = criado + 81 s · tentativas 2 (Resulta) e 3 (AutoFleet)
select tipo, min/max(criado_em) from multicalculo_eventos … group by corretora
   Resulta  : recusas 01:01:17→01:03:27 · 32 ofertas 01:03:20→01:03:29
   AutoFleet: 72 ofertas 01:06:36→01:09:24 · recusas até 01:13:58
```
- **Mesmo `disparado_em` nas duas = as duas saíram na MESMA volta** (`_reservar` grava `disparado_em=agora_iso` no CAS, `motor.py:539`;
  `_devolver_a_fila` zera, `:1201`). Logo, **não rodaram em série por desenho.**
- A rodada foi a 3ª do canário, **com morte proposital** (`--matar-depois-do-checkpoint`, `multicalculo_canario.py:191-213`: mata o m1
  depois do checkpoint, **espera a lease vencer (92 s)** e o m2 retoma só a leitura), no Windows, Chromium que levou 📊 38 s para abrir
  (`SPEC-129-B-EXECUTION-REPORT.md:71`). As 32 ofertas da Resulta em 9 s às 01:03:20 = a LEITURA da retomada; AutoFleet com 3 tentativas
  = uma retomada a mais.
- Os "85 s de fila": `disponivel_em = criado + 81 s` é o **atraso de nova tentativa** (`_devolver_a_fila(com_espera=True)`: 60 s × tentativas,
  `motor.py:81-82,1188-1206`) depois de um 1º disparo que não chegou ao POST — não um poll de 30 s.
- ⚠️ Pequeno descompasso de relógio: eventos (relógio do banco) 01:01:17 antes do `disparado_em` (relógio do PC) 01:01:22.

**INFERÊNCIA:** a P-130A1-08 / D-130A1-14 atribuíram a "série" ao `concurrency: 1` — é um **ELO não medido** (§0.3): as duas medições
estão certas (1ª corretora ~285 s, 2ª ~480 s; `/health` diz 1), mas o `concurrency` não CHEGA ao motor. O que alongou foi a morte
proposital + a espera da lease + a retomada + a máquina lenta, e a AutoFleet ter o dobro de seguradoras.
**RECOMENDAÇÃO / teste que decide:** um pedido `canal` **sem** `--matar`, no CONTÊINER, com 2 robôs `ativo`: comparar o 1º evento de cada
corretora (paralelo ⇔ diferença ≈ diferença de login). Não há variável para subir; "2+ navegadores" não é preciso (1 Chromium,
1 contexto por conta). Custo: 💭 ~100–300 MB por contexto de navegador; o limite de memória do contêiner `portal-worker` não está no
repositório (EasyPanel). ⚠️ **O motor NUNCA rodou no contêiner** (P-129B-07: `--headless=new` não abriu no Windows; o canário usou o
clássico) e T-121/T-122 estão abertas no `TAREFAS-DO-FOUNDER.md:732-742`.

### 5.3 🔴 ACHADO 3 — hoje o canal não tem robô que possa rodar
📊 `select robo_estado, tem_senha, robo_janela from portal_accounts where portal_key='agger'` → as 2 contas `pausado`, **sem senha**,
janela `seg-sex 20:00–23:59`. E `robos.conta_elegivel` (`robos.py:169-190`): conta `teste` (login de PESSOA) **só atende origem
`teste` no canário**; `origem='canal'` exige conta `ativo`, com senha e dentro da janela. → **Sem T-120 (robô próprio) ou sem o Founder
decidir pôr o login da Ellen como `ativo` numa janela, nenhuma cotação do canal sai** — e testador de dia cai fora da janela.

---

## 6. Convidados, limite, lead e consentimento (FATO)
- 📊 `invites` (10 linhas) = convite de USUÁRIO do dashboard (e-mail, `max_uses`, `role`) — **não serve** a telefone.
- 📊 `leads`: **0 linhas**; `email NOT NULL` + `UNIQUE(company_id, email)` → inútil para lead por telefone sem migration (o plano 130-A já
  avisou).
- Consentimento / "não me contate" / convidados de WhatsApp / limite por número: **não existe tabela** (📊 `information_schema` com
  `consent|opt|convid|invite|lead` → só `invites`, `leads`).
- O que a 129-B/130-A gravam: `multicalculo_pedidos` (origem, opções, corretoras, `pedido_cifrado`, `cpf_hmac`), `_calculos`, `_ofertas`,
  `_eventos`, `_seguradora_dia`; a proposta em `artifacts`/`artifact_versions`/`artifact_shares` (📊 1 `proposal.quote`, do canal, 06/10).
  📊 `multicalculo_pedidos` por origem → `teste: 3`, `canal: 0`. `multicalculo_config`: 0 linhas (vale o padrão de `config.py:98-117`,
  incl. `canal.follow_up` e o `volume.base` da F0).
- ⚠️ Texto de consentimento: com o paralelo, **o CPF vai ao Agger de TODAS as corretoras aderidas**, não só da vencedora (a PRONTIDAO §5
  diz "pelo Agger da corretora vencedora" — incompleto).
- RECOMENDAÇÃO (migration CRÍTICA, APPLY/VERIFY/ROLLBACK, MIGRATIONS-AUTHORITY antes): `canal_convidados` (company_id do canal,
  telefone normalizado com as 2 formas do 9º dígito, limite, usados, ativo, convidado_por) e `canal_conversas` (company_id, telefone,
  estado, respostas cifradas, consentimento_em + texto/versão do consentimento, pedido_id, run_id, lead) — ou estender `leads`
  (telefone, sem e-mail obrigatório). A escolha é do gerente; nota 💭 tabela própria 80 × evoluir `leads` 65 (o `UNIQUE` por e-mail e o
  consolidar com `users_v2` são outra SPEC).

## 7. A página (FATO)
- `/r/<token>` → `app/r/[token]/route.ts` → backend `ArtifactService` lê o render html pronto; para `kind='proposal'` injeta a prévia e
  devolve `csp_script_hashes=[proposta_html.HASH_DO_SCRIPT]` (`services/artifacts/service.py:744-749`; `route.ts:141-142` aceita a lista).
- O template `proposal.quote` (`artifacts/templates.py:949`) tem UM renderizador: `_renderizar_proposta` (`templates.py:932-939`) →
  `proposta_html.render_proposta(modelo)` (`proposta_html.py:811`), que já ramifica em `canal = modelo.get("origem") == "canal"`
  (`:829`, selo `:857`, textos `:943`, `:965`). Prévia PNG: `proposta_previa.py` (textos de `previa_do_modelo`, `proposta_html.py:346-399`).
  "Quero fechar": `service.py:fechar_compartilhado` → `proposta_html.destino_do_fechar`.
- RECOMENDAÇÃO: arquivo NOVO `services/artifacts/proposta_canal_html.py` (marca QCM, vencedora dentro, bloco "Corretora Nível 5",
  carrossel/lista por seguradora — D-130A1-08/D-MC-74) e UMA linha em `_renderizar_proposta`: `origem=='canal'` → o novo. A página da
  carteira não muda. **CSP:** ou o novo reusa `SCRIPT_DA_PROPOSTA` (o hash não muda, `service.py` intocado) ou `service.py:749` passa a
  devolver o hash pela origem (1 linha num hub). ⚠️ `proposta_html.py` está na F0 agora (10 linhas no diff): a fatia da página não o edita.

## 8. Lembretes (FATO + RECOMENDAÇÃO)
Agendadores existentes: APScheduler do `smith-api` (`tasks/buffer_processor.py:1456` `start_buffer_scheduler`, ~25 jobs, só o LÍDER envia
— `:1950-1960`) e o despertador do Work OS no `smith-worker` (60 s). Config pronta: `canal.follow_up = {primeiro_apos_min:15,
segundo_apos_h:24, max_sem_resposta:2, horario_comercial 9–20}` (`config.py:115-116`).
RECOMENDAÇÃO: o run `canal.cotacao` **dorme** (`runs.dormir(acordar_em_s=…, wait_for={"tipo":"relogio","ref":"lembrete_1"})`) e acorda
pelo despertador; ao acordar confere se a pessoa respondeu depois da pergunta final; senão manda o lembrete pela integração do canal e dorme
até o próximo horário comercial. Resposta da pessoa no meio → a conversa cancela/encerra o run. Nenhum scheduler novo, nenhum job novo.

## 9. Riscos
1. **7463 = cliente de teste do atendimento** (D-130A1-10). Pareado no canal: (a) se um agente de corretora ligado responder ao 7463, a
   resposta entra no CANAL como inbound → **laço robô↔robô**. Guardas: convidado-só + **anti-laço por número conhecido** (qualquer
   `integrations.paired_phone_e164`/identifier ativo, destino de suporte, WhatsApp de marca de corretora → descarta e conta); (b) o Founder
   escrevendo do 7463 para as corretoras gera `fromMe` no canal → espelho/pausa na empresa do canal (ruído, não envio); (c) a allowlist
   global com 7463 continua fazendo o atendimento das corretoras responder SÓ a um robô.
2. **Allowlist global** derruba convidados se o canal passar por ela (por isso o desvio antes de `:1348`).
3. **Paralelo não provado no contêiner** + motor nunca rodou no contêiner (P-129B-07) + robôs pausados/sem senha (Achado 3).
4. **Porta recusa quem só tem a placa** (Achado 1) e **estado civil sem código** (Achado 2).
5. **`SemCanalDeFechamento`** sem T-125 (o botão "Quero fechar" e a passagem).
6. **P-E0017-14**: o testador que repete a cotação herda memória em 6 lugares — o canal deve guardar estado POR COTAÇÃO.
7. "CPF já cotado": o Agger marca `seguradoCotadoRecentemente` (E4) — testador cotando 2× pode ver recusas; e o CPF vai às 2 corretoras.
8. Árvore suja: a F0 é dona de `proposta_html.py`, `mensagem.py`, `proposta.py`, `config.py`, `comando_proposta.py`.
9. Custo: papel `atendimento` (gpt-6.1-sol high) seria ~20× o `gpt-6-luna`; e o crédito das APIs já zerou uma vez (memória SPEC-116).

---

## 10. AS FATIAS propostas (arquivos disjuntos)
| fatia | o quê | arquivos (dono único) | paralela? |
|---|---|---|---|
| **F1 · a porta de entrada** (CRÍTICO: envia + migration) | desvio do canal no webhook; convidados + limite; anti-laço; consentimento e lead; estado da conversa cifrado; o contrato `canal.turno(integration, phone, itens)` | `backend/app/api/webhook.py` (2 pontos: antes de `:2879` e depois de `:1118`) · `backend/app/services/canal/__init__.py`, `entrada.py`, `repositorio.py` (NOVOS) · migration `backend/supabase/migrations/2026100X_0Y_spec133a_canal.sql` (NOVA) | 1ª, em série com F2 (F2 consome o contrato) |
| **F2 · a conversa e a cotação** (CRÍTICO: envia) | máquina de estados das perguntas (uma por vez, D-MC-59/70), papel `canal_cotacao` (linha em `llm_papeis`), montagem do `PedidoDeCalculo`, `porta.calcular(origem='canal', corretoras=adesões ativas, opcoes=OPCOES_DO_CANAL)`, workflow `canal.cotacao`: acompanhar/narrar → `publicar_proposta` → `mensagem_para` → pergunta final → 2 lembretes (dormir) → passagem (`billing_collection.avisar_suporte_humano` da vencedora + link) ; a placa supre FIPE/ano/combustível na origem canal | `backend/app/services/canal/conversa.py`, `cotacao.py`, `workflows.py` (NOVOS) · `backend/app/services/multicalculo/pedido.py` + `porta.py` (só a regra da placa) · migration de dado do `llm_papeis` (NOVA) · registrar o módulo em `workflows.carregar_extras` (`services/work/workflows.py:60`) | depois de F1 (costura no fim) |
| **F3 · a página do Quem Cobra Menos** | `proposta_canal_html.py` + a linha em `_renderizar_proposta` (reusando o script = hash igual) | `backend/app/services/artifacts/proposta_canal_html.py` (NOVO) · `backend/app/services/artifacts/templates.py` (1 linha) | ‖ (depois que a F0 soltar `proposta_html.py`, se precisar importar dele) |
| **F4 · o QR no admin** | rota admin + página + prop `endpoint` nos 2 componentes | `app/api/admin/canais/whatsapp/route.ts`, `app/admin/canais/quem-cobra-menos/whatsapp/page.tsx` (NOVOS) · `components/vault/WhatsAppChannelCard.tsx`, `WhatsAppPairingFlow.tsx` (prop opcional) · link no menu do admin | ‖ |
| (F5 · medição do motor) | sem código: canário `canal` sem `--matar` no contêiner com 2 robôs `ativo`; se provar série, aí sim olhar `motor.py` | — (ou `backend/portal_worker/multicalculo/*` se a medição mandar) | depois do Implantar + T-120 |

COESÃO: F1 e F2 partilham o contrato do estado → série. F3 e F4 não tocam nada de F1/F2.

## 11. O FIO (do "oi" ao último balão)
```
Evolution Go → POST /api/v1/webhook/evolution-go/{token}         webhook.py:2867 evolution_go_webhook_token
  → _resolve_webhook_integration (empresa = canal pelo hash)       webhook.py:2508
  → [NOVO] canal? pula observer_tap                                 webhook.py:~2879
  → go_event_to_v2_envelope → _handle_evolution_like_inbound        webhook.py:2899 · :2909 (fromMe/grupo = skip)
  → _buffer_or_dispatch_text → buffer → check_buffers               webhook.py:2647 · buffer_processor.py:1316
  → process_whatsapp_message_background                             webhook.py:1045 (empresa :1117)
  → [NOVO] canal.turno                                               services/canal/entrada.py
       anti-laço → convidado/limite → consentimento → estado         services/canal/repositorio.py
  → [NOVO] conversa.proxima_pergunta / entender (invocar_com_reserva papel canal_cotacao)   llm_factory.py:595
  → whatsapp_service.send_message (balões, 0,7 s)                   whatsapp_service.py:131
  … perfil completo →
  → [NOVO] cotacao.disparar → PedidoDeCalculo.de_dict → MulticalculoProvider.calcular(origem='canal')   porta.py:278
  → work run canal.cotacao (Work OS)                                 services/work/runs.py criar · workflows.registrar_workflow
  → [portal-worker] motor.uma_volta → _reservar → _executar_grupo ×2 corretoras ‖   motor.py:316 · :476
  → agger_robo.disparar/acompanhar → ofertas/eventos                multicalculo_ofertas/_eventos
  → passo acompanhar: porta.consultar(desde_evento) + narração       porta.py:346
  → publicar_proposta(company_id=canal, pedido_id, …)                proposta.py:862 → ArtifactService → /r/<token>
       → _renderizar_proposta → [NOVO] proposta_canal_html (origem canal)   templates.py:932
  → mensagem_para(modelo, url) → balões → send_message               mensagem.py:527
  → pergunta final → runs.dormir 15 min → despertador → lembrete 1 → dormir → lembrete 2   runs.py:469 · smith_worker.py:160
  → "quero fechar" → passagem: avisar_suporte_humano(vencedora) + wa.me da vencedora   billing_collection.py:244
```

## 12. O TESTE DO FIO (1ª entrega sugerida)
Um teste que chama **o motor de verdade da borda** (CLAUDE.md §9.4): `TestClient` em `POST /api/v1/webhook/evolution-go/{token}` com um
**payload real do Evolution Go** (fixture do acervo, sem PII) para uma integração de empresa `platform_canal`; Redis/banco/Evolution
dublês só na borda; buffer drenado chamando `process_whatsapp_message_background` real.
- caminho feliz: convidado manda "oi" → "sim" → respostas → afirma `porta.calcular` chamado com `origem='canal'`,
  `corretoras == adesões ativas`, `opcoes == OPCOES_DO_CANAL`, nunca `PerfilIncompleto`; porta dublê devolve um `Andamento` com ofertas →
  `publicar_proposta` (ArtifactService em memória) → os balões de `mensagem_para` saem por `send_message` para o MESMO telefone, com
  `/r/<token>`;
- **controles que têm de dar ZERO envio**: número não convidado · convidado acima do limite · número = `paired_phone_e164` de uma
  integração de corretora (anti-laço) · `fromMe` · grupo;
- **controle de não-regressão**: o mesmo payload numa integração `observer` de corretora → `observer_tap` ainda consome (o desvio não
  vaza para as corretoras);
- mutação: tirar o desvio → o "oi" do convidado morre no `observer_tap` (vermelho).

## 13. Ação física do Founder
1. **Ler o QR** do 47 98808-7463 na página admin nova (F4). ⚠️ antes: decidir se o 7463 sai da `ATTENDANT_INBOUND_ALLOWLIST`.
2. **EasyPanel:** Implantar `smith-api` → `smith-worker` → `portal-worker` → `smith-web` (a ordem que o painel usa).
   `smith-api`: `MULTICALCULO_HMAC_KEY` (T-122 — sem ela a porta recusa). `portal-worker`: `MULTICALCULO_MOTOR_LIGADO=true` +
   `PORTAL_REAL_ENABLED` (T-121/T-122). Conferir `PUBLIC_APP_URL`/`SMITH_WEB_URL` (sem host o link não sai, `proposta.py:877-879`).
3. **Robôs (T-120):** um usuário-robô do Agger por corretora, cadastrado pelo comando da 129-B, `robo_estado='ativo'`, janela que cubra
   o horário dos testadores (hoje: `pausado`, sem senha, `seg-sex 20–24h`).
4. **T-125** (WhatsApp de atendimento das corretoras) — ou aceitar `permitir_sem_whatsapp` no piloto.
5. **Verba de API** (o papel novo do canal) e a marca da AutoFleet publicada (P-130A1-09).
6. Lista dos 5 testadores (telefones) para a tabela de convidados — entra pelo admin ou por comando, nunca no código.
