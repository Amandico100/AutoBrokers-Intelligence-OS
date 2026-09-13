# SPEC-EXTRA-001.2 — RESEARCH PACK
## O agente lê tudo antes de falar

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão. **Não é** relatório de execução.
**Worktree:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
**Baseline medida:** `a0bb5fef440eba394a9275671b1143f5025807ef` (= `origin/main`; 0 atrás, 0 à frente, medido em 13/09/2026).
**Método:** leitura dos arquivos do produto nesta revisão, reabertos hoje; consultas read-only ao banco de produção (só contagens e intervalos, nunca conteúdo de mensagem); documentação primária pública reaberta em 13/09/2026.
**O que NÃO foi feito nesta preparação:** nenhum código de produto alterado, nenhuma migration, nenhuma mensagem enviada, nenhum portal acessado, nenhum agente ligado.

---

## 0. Legenda e precedência

- **DECISÃO** — instrução explícita do Founder já registrada em `FOUNDER-DECISIONS.md`.
- **📊 MEDIDO** — número com data, fonte e o comando/consulta ao lado (CLAUDE.md §12.1 e AAA §0.4).
- **💭 ILUSTRATIVO** — exemplo de copy ou hipótese. **Nunca citável como fato.**
- **OBSERVADO NO CÓDIGO** — existe e foi lido nesta revisão. Existir não é funcionar (CLAUDE.md §13.7).
- **INFERÊNCIA** — consequência deduzida; precisa de comando no BLOCO 0.
- **FONTE EXTERNA** — padrão documentado fora. Nunca vira autoridade (CLAUDE.md §5).

> 🔴 **Onde este documento diverge do `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`, vence este** — as linhas foram reabertas hoje e cinco delas mudaram de arquivo, de número ou de significado. A lista das divergências está na §1.

---

## 1. 🔴 O que o diagnóstico afirmou e que a remedição de hoje CORRIGE

Esta seção existe porque o pacote do redator manda conferir cada `arquivo:linha` do diagnóstico e anotar a divergência. **Cinco correções são materiais** — mudam o que a SPEC tem de fazer.

| # | o diagnóstico §1.4 / §7.4 diz | o que se mede hoje | consequência |
|---|---|---|---|
| **C1** | `message_buffer_service.py` em `app/services/atendimento/` | **`backend/app/services/message_buffer_service.py`** — o diretório `app/services/atendimento/` **não existe** | caminho no pacote do executor |
| **C2** | `buffer_processor.py` em `app/services/atendimento/` | **`backend/app/tasks/buffer_processor.py`** | idem |
| **C3** | "**mídia não passa pelo buffer** (`webhook.py:1448-1451`)" — **um** ponto | **três** pontos: `webhook.py:1449-1452` (rota legada), `:1634-1637` (z-api com token), **`:2226-2229`** (`_handle_evolution_like_inbound`, que é o **caminho quente** de `/evolution/{token}` e `/evolution-go/{token}`) | 🔴 consertar um ponto deixa o defeito vivo. **É esta divergência que obriga a SUPERFÍCIE 3** |
| **C4** | "a ficha guarda `apolice_confirmada: bool`, **não os slots já respondidos**" | a ficha **tem** `confirmados: {}` e **tem** o bloco *"JÁ CONFIRMADO com o cliente — **não pergunte de novo**"* (`attendance_ficha.py:274`). O defeito é outro e mais preciso: **o escritor cobre 15 de 35 slots** | 🔴 o conserto não é "criar a ficha de slots" — é **fechar o buraco entre o vocabulário e o escritor** (§2.4) |
| **C5** | "a corretora escolhe o nome no card Agente (**já existe `agent_name`**)" | 📊 **`companies.agent_name` não existe** (0 linhas em `information_schema`). `conversations.agent_name` é **rótulo de quem atendeu** — 📊 `Espelho` 782 · `Smith Agent` 73 · `AutoBrokers` 4 · `Motor de Acionamento` 1. O nome configurável é **outro campo**: `agents.name` / `context_package[…].variables.attendant_name` → `display_name` | 🔴 a SPEC que mexesse em `agent_name` mexeria no campo errado. §2.6, §3.8 |
| **C6** | §1.4 mede rajadas "em `messages`" | 🔴 **`messages.created_at` é o relógio do ESPELHO**, não do segurado; infla as rajadas em **+39,2%**. O relógio real é `attendance_transcripts.wa_timestamp` | 🔴 **muda a fonte do corpus e de toda calibragem.** §3.0 |
| **C7** | "dedupe do espelho por `wa_message_id`" (implícito: falta o índice) | 📊 o índice existe desde 06/08 e é **por conversa**; 📊 **134 ids repetidos, 100% entre conversas DIFERENTES, 0 dentro da mesma**, e **104 atravessam corretoras** | 🔴 dar a chave ao pipeline **não basta**; e há candidato a **P0 cross-tenant**. §3.6 |
| **C8** | "174 conversas fantasma (P-PILOTO-13)" | 📊 **175** hoje (106 AutoFleet, 69 Resulta), **100% abertas**, **10** com pausa presa, **9** com par real, **166 sem par** | o ganho é a **176ª não nascer**, não recuperar as 166. §3.5 |
| **C9** | "ordem `pausar_ia` × exceções — P-PILOTO-15" | 🔴 **P-PILOTO-15 é outra coisa**: `resolvido_em` mata a pausa. A inversão de ordem é um defeito **medido hoje, sem pendência própria** | as **duas** entram. §2.9, §8 |
| **C10** | D-PILOTO-12: *"'Amanda' na Resulta é escolha da Saionara e fica"* | 📊 a linha `Amanda` está **desativada**; o agente **ativo** da Resulta se chama **`AutoBrokers`** | 🧑 **caixa do Founder**, não decisão do executor. §3.8 |

Correções **não materiais** (o número mudou, o fato não): `prompts.py` está em `app/core/`, não `app/agents/core/`; a instrução "SEMPRE se apresente" é a linha **359** (o bloco abre em 355); `attendance_capture.py` e `espelho_chat.py` estão em `app/services/atlas/`; `identidade_do_evento.py` está em `app/services/whatsapp/`.

Confirmações **exatas** do diagnóstico (reabertas, batem): `attendance_ficha.py:132-141` (a ficha vazia) · `prompts.py:90` ("NUNCA pergunte dado que o cliente já informou") · `message_buffer_service.py:158` (o debounce por ociosidade) · zero `lock` no webhook · `buffer_processor` com 6 em paralelo e sem trava por conversa.

---

## 2. Achados centrais no código — cada um com o comando que o produz

> ⚠️ As linhas são coordenadas de `a0bb5fe`. O BLOCO 0 reencontra os **símbolos**, não os números.

### 2.1 O buffer: onde o turno nasce, e por que ele se parte

**`backend/app/services/message_buffer_service.py` (221 linhas —** `wc -l backend/app/services/message_buffer_service.py` **)**

| ID | evidência | consequência |
|---|---|---|
| R01 | `message_buffer_service.py:158` — `if seconds_since_last >= max(settings.BUFFER_DEBOUNCE_SECONDS, 8):` | debounce **por ociosidade**. Qualquer pausa ≥ 8 s abre um segundo turno. 🔴 **E o `max(…, 8)` é um PISO: uma janela de 3 s para dado curto é IMPOSSÍVEL hoje**, mesmo mudando o ambiente |
| R02 | `message_buffer_service.py:166` — `if seconds_since_first >= max(settings.BUFFER_MAX_WAIT_SECONDS, 25):` | teto de 25 s desde a primeira. Mesma trava de piso |
| R03 | `app/core/config.py:73-75` — `BUFFER_DEBOUNCE_SECONDS: int = 8` · `BUFFER_MAX_WAIT_SECONDS: int = 25` · `BUFFER_TTL_SECONDS: int = 60` | os três nomes de campo **são** os nomes das env vars (pydantic `Settings`) |
| R04 | `backend/.env.example:40-42` — `BUFFER_DEBOUNCE_SECONDS=3`, `BUFFER_MAX_WAIT_SECONDS=30`, `BUFFER_TTL_SECONDS=300` | ⚠️ o exemplo ainda ensina os valores velhos. O `max()` neutraliza os dois primeiros; **o TTL de 300 não tem piso nem teto** |
| R05 | `message_buffer_service.py:56-57` — `return f"whatsapp_buffer:{esc}:{phone}"`, com `esc` = id da integração | 🔴 **o isolamento multi-tenant do buffer já existe e é por integração** (SPEC-063 Bloco H, docstring `:38-55`). A trava nova herda essa chave; não se inventa outro escopo |
| R06 | `message_buffer_service.py:127` — `await self.redis.setex(key, settings.BUFFER_TTL_SECONDS, …)` | o TTL é **reescrito a cada mensagem**; não é TTL desde a primeira |
| R07 | `message_buffer_service.py:116-124` — `data = {"messages": [message], …}` | 🔴 **`messages` é uma lista de STRINGS.** Mídia não cabe na estrutura sem mudar a forma. A migração de forma é in-flight: o TTL de 60 s drena o formato velho em ≤ 1 min após o deploy |
| R08 | `message_buffer_service.py:183-186` — pipeline `get`+`delete` | é **toda** a exclusão mútua que existe hoje. Quem perde a corrida recebe `None` e desiste |
| R09 | `message_buffer_service.py:109-113` — `interactive` novo não apaga o antigo | precedente vivo de "mesclar em vez de sobrescrever" na rajada. O re-planejamento da §B copia esta regra |
| R10 | grep `SET NX`/`lock` no módulo → **zero** | 🔴 **não existe trava por conversa**. Confirma o diagnóstico |

```bash
grep -n "max(settings.BUFFER" backend/app/services/message_buffer_service.py
grep -n "BUFFER_" backend/app/core/config.py backend/.env.example
grep -rn "nx=True\|SET NX" backend/app/services/message_buffer_service.py backend/app/tasks/buffer_processor.py   # → vazio
```

### 2.2 O varredor: 6 em paralelo, e um comentário que diz por quê

**`backend/app/tasks/buffer_processor.py` (160 linhas)**

| ID | evidência | consequência |
|---|---|---|
| R11 | `buffer_processor.py:60` — `_PARALELISMO_PADRAO = 6`; `:76-77` — `asyncio.Semaphore(limite)`, env `WHATSAPP_BUFFER_PARALELISMO` | o paralelismo é **entre conversas** e é desejado (SPEC do plano de 08/09) |
| R12 | `buffer_processor.py:47-51` — comentário: *"`get_and_clear_buffer` é um pipeline Redis `get`+`delete` — ATÔMICO. Duas tarefas na mesma chave: uma leva o buffer, a outra leva `None` e desiste"* | 🔴 **a proteção declarada cobre duas tarefas na MESMA varredura sobre a MESMA chave — e não cobre o caso real**: buffer limpo, turno rodando 20 s, mensagem nova cria chave nova, varredura de 1 s depois abre um SEGUNDO turno. É a fragmentação medida |
| R13 | `buffer_processor.py:63-64` — `processar_buffers_prontos(chaves, buffer_service, processar, paralelismo=0)` recebe as peças por parâmetro *"porque é assim que o teste exercita ESTE motor com dublês, em vez de reimplementar o laço"* (docstring `:69-71`) | 🔴 **o ponto de enxerto da trava já é testável pelo motor** (CLAUDE.md §9.4). Não se cria arquivo novo |
| R14 | `buffer_processor.py:79-86` — ordem hoje: `should_process` → `get_and_clear_buffer` → `processar` | a trava entra **antes** do `get_and_clear`: falhar em adquirir não pode custar o buffer |
| R15 | `buffer_processor.py:154-160` — `interval` de 1 s, `max_instances=10` | dez varreduras podem se sobrepor. O contrato da trava tem de valer entre varreduras |

### 2.3 O webhook: três desvios de mídia, e o lugar onde a resposta sai

**`backend/app/api/webhook.py`**

| ID | evidência | consequência |
|---|---|---|
| R16 | `webhook.py:2226-2229` — `if image_payload or audio_payload: background_tasks.add_task(process_whatsapp_message_background, …); return {"status": "received", "type": "media"}` | 🔴 **o desvio quente.** A foto gera turno imediato, em paralelo ao texto que está no buffer |
| R17 | `webhook.py:1634-1637` e `:1449-1452` | os outros dois desvios (rotas z-api). O conserto tem de valer nos três |
| R18 | `webhook.py:2206` — `documento_payload` **não** dispara o desvio | documento **já** cai no buffer de texto. Assimetria a uniformizar |
| R19 | `webhook.py:1593-1604` — `_buffer_or_dispatch_text(payload_dict, phone)`, **único** helper de entrada no buffer; `company_id="pending"`, `user_id="pending"`, `integration={}` | 🔴 **o `company_id` do buffer é literalmente `"pending"`.** A trava por corretora precisa resolver o tenant a partir do `_integration_id`, não do buffer |
| R20 | `webhook.py:1425-1427` e `:1496-1503` — `redis.set(f"wa_dedupe:{messageId}", "1", ex=…, nx=True)` | 🔴 **o padrão `SET NX EX` já é usado na casa, no mesmo arquivo.** A trava de turno é o mesmo comando com outra chave e um token — **não é motor novo** |
| R21 | `webhook.py:766-769` — `_calar, _motivo = await a_ia_deve_calar(...)`; `:785-786` fail-closed; parada em `:1059-1062` | o portão de silêncio **de entrada** |
| R22 | `webhook.py:1240-1290` — reconferência **depois** de gerar; `:1288-1290` descarta a resposta pronta; `:1276-1283` escreve o feed **só** se `foi_a_janela(motivo)` | 🔴 é aqui que entram (a) a re-leitura do buffer, (b) a confirmação de que ainda somos donos do turno e (c) o motivo de silêncio que hoje some |
| R23 | `webhook.py:952-963` — insert da mensagem do segurado em `messages` **sem `payload`**; `:1294-1300` — insert da resposta da IA **sem `payload`** | 🔴 **a causa do espelho em dobro.** O índice único que já existe (R27) só cobre linhas COM `wa_message_id`; o pipeline do agente não grava nenhum |
| R24 | `webhook.py:1711` `_pausar_quando_a_atendente_fala(...)`; chamadas em `:1828` e `:2016-2018` | a pausa por intervenção humana, entregue em 09/09 e **ainda não exercitada com segurado real** (diagnóstico §1.8) |
| R25 | `webhook.py:1330-1345` — `success = await asyncio.to_thread(whatsapp_service.send_message, …)` | o ponto de efeito. O canário e a allowlist se ancoram aqui |

### 2.4 🔴 A ficha: 35 rótulos, 15 escritos — o buraco que faz a pergunta repetir

**FATO, com o comando:**

```bash
cd backend && PYTHONIOENCODING=utf-8 python -c "
import re
rot=set(re.findall(r'\"([a-z0-9_]+)\":', re.search(r'ROTULOS = \{(.*?)\n\}', open('app/services/attendance_ficha.py',encoding='utf-8').read(), re.S).group(1)))
fic=set(re.findall(r'\"([a-z0-9_]+)\"', re.search(r'_SLOTS_DA_FICHA = \((.*?)\n\)', open('app/agents/nodes.py',encoding='utf-8').read(), re.S).group(1)))
print(len(rot), len(fic), sorted(rot-fic))"
```

📊 **Medido em 13/09/2026:** `ROTULOS` (o vocabulário único do atendimento, `attendance_ficha.py:74-114`) tem **35** slots. `_SLOTS_DA_FICHA` (o escritor, `nodes.py:835-846`) tem **15**. **20 slots existem no vocabulário e nunca são gravados na ficha:**

```
destino_bairro · destino_cep · destino_cidade · destino_numero · destino_rua · destino_uf
local_bairro · local_cep · local_cidade · local_numero · local_rua · local_uf
ocupantes_particularidade · pessoa_no_local · ponto_referencia · quando
rodovia · veiculo_cor · veiculo_descricao · veiculo_situacoes
```

🔴 **E o `agua_escorrendo` não está em NENHUM dos dois.** Ele é slot do corredor, declarado em três lugares e ausente do vocabulário da ficha:

```bash
grep -rn "agua_escorrendo" backend/app/
# app/agents/tools/insurer_dispatch_tool.py:320   (campo da tool)
# app/services/corridor_playbooks.py:1302, :3826  (obrigatório do encanador)
# app/services/corridor_playbooks.py:9712         ("se a água ainda está escorrendo")
```

**O ELO (§0.3), medido:** A = a pergunta repetiu 3× (diagnóstico §1.4, acervo de 10/09). B = o bloco *"não pergunte de novo"* existe (`attendance_ficha.py:253-274`) e é injetado no prompt (`graph.py:1459-1471`, guarda em `:1453` só para `attendance`/`insured_external`). **B chega em A?** Não: o bloco só lista `ficha["confirmados"]`, e `confirmados` só recebe as chaves de `_SLOTS_DA_FICHA` (`nodes.py:872-874`). `agua_escorrendo` nunca entra no dicionário, logo nunca aparece no bloco, logo o modelo não tem como saber. **O elo está medido e está partido no escritor.**

Peças relacionadas, todas lidas hoje:
- `attendance_ficha.py:119` `_tem_valor` — recusa `"não informado"` como confirmação (protege contra ficha falsamente completa).
- `attendance_ficha.py:298-347` — a ficha mora na coluna JSON **`conversations.ficha_atendimento`**; não há tabela nova a criar.
- `insurer_dispatch_service.py:1362` importa `ROTULOS` — **o vocabulário já é único**; é por isso que fechar o buraco no escritor conserta os dois lados.
- Outros escritores da coluna: `human_handoff.py:1078-1084`, `atendimento/acompanhamento.py:419-441`. **Três escritores** — o BLOCO 0 confirma quem é o dono de cada chave antes de acrescentar a nova.

### 2.5 A apresentação: a instrução, o gate e o conflito

| ID | evidência | consequência |
|---|---|---|
| R26 | `prompts.py:355-361`, sendo a linha **359**: `- SEMPRE se apresente com nome E corretora na primeira mensagem: {_exemplo}` | 🔴 "primeira mensagem" é ambíguo e o modelo lê "primeira **minha**". O bloco inteiro só entra se `role_norm in ("attendance","insured_external")` **e** `display_name` não vazio (`prompts.py:352-354`) |
| R27 | `prompts.py:87` — `- Frases CURTAS (1 a 3 por mensagem)…`; `:95-100` — bloco de até **4 itens**, `:99` "Máximo 4 itens"; `:102-108` — **exceção documental** (lista inteira numa mensagem só) | 🔴 **a hierarquia de tamanho JÁ ESTÁ ESCRITA no prompt.** O que falta não é a regra: é o número que prove se o modelo obedece. AAA §3: *"não sei se o modelo obedece → é PROVA, não mais gente"* |
| R28 | `prompts.py:91` — `- Se o cliente mandou várias mensagens seguidas, responda o conjunto…` | idem: a regra existe; o buffer é que entrega o conjunto partido |
| R29 | `prompts.py:604` — único `agent_name` do arquivo, e é de **subagente** | ver C5 |
| R30 | `graph.py:1256-1261` → `config.display_name` ou `agents.name`; `:1267-1270` nome da empresa; `:1295-1302` repasse a `build_composite_prompt` (`prompts.py:287-294`) | **este** é o caminho do nome do agente |
| R31 | `whatsapp/balloons.py:17-20` — `TARGET_LEN=300`, `HARD_LEN=500`, `MAX_BALLOONS=4`; `whatsapp_service.py:132-157` — `bloco_unico=True` desliga a humanização | 🔴 **uma resposta já vira até 4 balões.** O gate "uma resposta por rajada" é sobre **TURNO** (uma geração), nunca sobre número de balões — senão mede a coisa errada |

### 2.6 🔴 O nome do agente: dois campos com o mesmo nome, e o card mexe no outro

```bash
grep -rn "agent_name" backend/app app components lib | grep -v node_modules
```

📊 **Medido em 13/09/2026 —** `conversations.agent_name` tem **três escritores, todos constantes**:

| escritor | valor gravado |
|---|---|
| `app/services/atlas/espelho_chat.py:535` | `"Espelho"` |
| `app/services/dispatch_mirror.py:147` | `"Motor de Acionamento"` |
| `app/api/webhook.py:219` | `"AutoBrokers"` |
| default da coluna (`schema_completo.sql:675`) | `'Smith Agent'` ⚠️ nome revogado pelo GLOSSARIO |

Leitores: `app/api/dashboard/conversas/route.ts:45-49` e `app/dashboard/atendimentos/conversas/ConversasClient.tsx:39,112,115` (`=== 'espelho'` marca o que veio do WhatsApp). **É rótulo de origem, não identidade configurável.**

O nome que o agente **usa para se apresentar** vem de:
- `agents.name` e `agents.context_package[TENANT_AGENT_CONFIG_NS].variables.attendant_name`;
- escrita: `lib/admin/agent-blueprints-canonical.ts:439` (`if (!bp.brand_locked_name) columns.name = eff.display_name;`) e `:460-466`; o blueprint `even-attendance-v1` tem `display_name = '{{attendant_name}}'` (`:99`) e a variável `attendant_name` com rótulo *"Nome do atendente"*, máx. 60 (`:116`);
- tela: `app/dashboard/personalizacao/agentes/AgentConfigClient.tsx` (+ `page.tsx`, API `app/api/dashboard/agents/[agentKey]/route.ts`); `app/dashboard/agente/page.tsx:23` é só um `redirect`.

**Card Equipe** (onde mora o nome da atendente, D-PILOTO-09/12): tela `app/dashboard/personalizacao/equipe/TeamClient.tsx`, API `app/api/dashboard/team/route.ts` (papéis aceitos em `:31` — `admin_company`, `member`, `attendant`), tabela `company_members` + `users_v2` (`lib/admin/tenant-overview-store.ts:18-44`). Campos disponíveis: `name`, `first_name`, `last_name`, `email`, `phone`, `role`, `is_owner`, `status`, `last_login_at`.

🔴 **Não existe hoje nenhum conceito de "quem está de plantão".** A SPEC precisa declarar a regra determinística e o que acontece quando ela não decide — ver §5 das armadilhas.

### 2.7 O espelho em dobro: o índice único **já existe** e não alcança o pipeline

| ID | evidência | consequência |
|---|---|---|
| R32 | `backend/supabase/migrations/20260806_02_espelho_sem_duplicata.sql:41-43` — `CREATE UNIQUE INDEX … ON public.messages (conversation_id, (payload->>'wa_message_id')) WHERE payload->>'wa_message_id' IS NOT NULL;` | 🔴 **o índice existe.** O diagnóstico sugere criá-lo; a SPEC não deve criar de novo |
| R33 | `espelho_chat.py:588-614` — único insert do espelho, **com** `payload.wa_message_id`; 23505 tratado em `:571-579` | o espelho está do lado certo |
| R34 | `webhook.py:952-963` e `:1294-1300` — inserts do pipeline **sem `payload`** | 🔴 **a causa**: as linhas do pipeline ficam **fora** do índice parcial. Duas gravações da mesma mensagem não colidem porque uma delas não tem chave |
| R35 | `observer_intake.py:711-738` — `if agente_ligado and not bool(key.get("fromMe")): return`, com 📊 de 17/08/2026 no próprio comentário | a mitigação de hoje é **divisão de responsabilidade**, não dedupe. Ela cobre o inbound com agente ligado — e **não cobre** o outbound |
| R36 | `webhook.py:1955-1957` (comentário) + `:1963-1969` — `espelhar_no_chat(…, direcao="out")` **incondicional** para `fromMe`; o comentário diz *"quem deduplica é o índice único, não este `if`"* | 🔴 **e o índice não consegue**: a resposta da IA foi gravada em `:1294` **sem** `wa_message_id` e volta pelo webhook **com** ele. Sobram `e_a_nossa_propria_voz` (`webhook.py:1951-1953`) e `_eco_do_dashboard` (`espelho_chat.py:433-459`, janela de tempo em Python) |

### 2.8 LID × telefone: uma normalização boa, duas resoluções de conversa diferentes

| ID | evidência | consequência |
|---|---|---|
| R37 | `whatsapp/identidade_do_evento.py:100-115` — `@lid` → busca `remoteJidAlt`/`remoteJidPn`/`senderAlt` (`:79-81`); sem alternativo válido → **`""`** | a normalização **existe** e é pura (módulo sem imports do produto, `:23-26`) |
| R38 | `identidade_do_evento.py:64-65` — ≥13 dígitos e não começa com `55` → recusa | custo assumido e documentado (`:43-47`) |
| R39 | `espelho_chat.py:502-505` — conversa por `(company_id, user_id, channel='whatsapp', agent_id IS NULL)` vs `webhook.py:936-945` — `get_or_create_conversation(..., session_id=…, agent_id=…)` | 🔴 **duas chaves de resolução no mesmo produto.** É por onde nascem duas linhas para a mesma contraparte |
| R40 | `backend/scripts/migrar_conversas_fantasma_lid.py:24-31` (registro do próprio script) | 📊 **09/09/2026: 774 conversas · 174 fantasmas · 174 abertas · 7 com pausa a copiar · 165 sem par real** |
| R41 | `migrar_conversas_fantasma_lid.py:69` `MOTIVO = "fantasma_lid"` vs `:78-81` `MOTIVOS_ACEITOS_PELO_BANCO` → `:283-286` devolve `RECUSADO`, código 2 | 🔴 **o `--vivo` está travado pelo CHECK `ck_conversations_resolucao_motivo`.** `grep -rn "fantasma_lid" backend/supabase/migrations/` → **zero**. A migration que destrava **não existe** |
| R42 | `migrar_conversas_fantasma_lid.py:113-137` `parear_pelo_wa_id` — só pares **sem ambiguidade** (`len(reais)==1`); `:35-38` ordem obrigatória (copiar a pausa **antes** de fechar); `:308-315`, `:323-329` escritas com `.eq("company_id", …)` | o script é conservador e multi-tenant. **Reaproveitar, não reescrever** |
| R43 | `docs/canon/PENDENCIAS.md:10533` — P-PILOTO-13 diz exatamente isso e nomeia o destravamento | pendência absorvida por esta SPEC |

### 2.9 O silêncio: a ordem está invertida, e quase nenhum motivo chega ao feed

**`backend/app/services/o_fim_do_atendimento.py:1325-1377`** — ordem **real** de `a_ia_deve_calar`:

| ordem | linha | checagem | resultado |
|---|---|---|---|
| 0 | `:1341-1342` | `company_id` vazio | `True, "sem corretora: …"` |
| **1** | **`:1343-1345`** | **`telefone_e_excecao_da_janela(conversa["user_phone"])`** | **`False, ""` — sai ANTES de `pausar_ia`** |
| 2 | `:1347-1355` | `pausar_ia(conversa)` | `True` + motivo (takeover ou `HUMAN_REQUESTED`) |
| 2b | `:1356-1359` | exceção | `True` (fail-closed) |
| 3 | `:1361-1366` | `dias <= 0` | `False, ""` — nem consulta |
| 4 | `:1368-1374` | `janela_de_mensagens`: `sem_conversa` → `False`; outro erro → `True` | fail-closed |
| 5 | `:1376-1377` | `silenciar_por_palavra_humana(...)` | a janela de N dias |

🔴 **Confirma P-PILOTO-15 e agrava:** o docstring da função (`:1329-1332`) descreve **dois** passos e **omite a exceção**, que na prática é o passo zero. Consequência medida por leitura: um telefone em `JANELA_SILENCIO_EXCECOES` **também neutraliza o takeover humano (`claimed_by`) e o `HUMAN_REQUESTED`** — não só a janela de N dias. O comentário do env (`:1288-1292`) admite isso; a função que decide, não.

**O feed:** `anotar_silencio_no_feed` (`:1411-1412`) começa com `if not foi_a_janela(motivo): return False` (`:1419-1420`). **Não viram linha no feed:** silêncio por `claimed_by`/`HUMAN_REQUESTED` · por `sem corretora` · por falha de leitura (as duas frases fail-closed) · e a **não-calada** por exceção de telefone (`:1344` só faz `logger.info`). A memória de "uma vez por dia" é de processo (`_SILENCIO_JA_ANOTADO`, `:1396`, teto `:1397`) — contêiner novo repete.

Chamadores (todos chamam a decisão e o feed juntos): `webhook.py:766`+`:781` · `webhook.py:1257`+`:1281` · `chat.py:194`+`:207` · `chat.py:666`+`:676` · `atendimento/acompanhamento.py:339`+`:350`.

### 2.10 Presença "digitando…": não existe nenhuma chamada

```bash
grep -rn "sendPresence\|setPresence\|composing\|presenceSubscribe" backend/app/
```
📊 **13/09/2026 — zero chamadas de saída.** As únicas ocorrências são: `providers/evolution.py:89,157` (comentário listando `presence.update` como evento de **entrada ignorado**) e `providers/uazapi.py:127,140` (gate que **rejeita** eventos de presença). `llm_presence_penalty` é parâmetro de LLM, sem relação.

O cliente onde a chamada nova mora: `app/services/whatsapp/providers/evolution.py` — `EvolutionProvider._post(url, payload)` (`:286`) é o **único** ponto de saída HTTP; `send_text` (`:308`) monta `f"{base}/message/sendText/{instance}"` (`:314`) com payload `{"number": to, "text": text}` (`:315`) — **sem `delay`**. Fork GO: `providers/evolution_go.py` (`_post(path, payload)` `:441`, `rotas_de_envio_medidas()` `:577`).

### 2.11 Leases e locks que **já existem** (CLAUDE.md §5 — consolidar, não duplicar)

| local | padrão |
|---|---|
| `backend/portal_worker/leases.py` | o mais completo: `LEASE_DURACAO_SEGUNDOS=120` (`:93`), `HEARTBEAT_INTERVALO_SEGUNDOS=30` (`:94`), Lua CAS `_LUA_RENOVAR` (`:145-151`) e `_LUA_LIBERAR` (`:154+`), classe `LeaseDePortal` (`:363`) com `adquirir/renovar/liberar/dono_atual` (`:401/:427/:453/:480`) |
| `app/services/atlas/route_sentinel.py:103-107` | `await redis.set(key, token, nx=True, ex=ttl)` + `_release_redis_claim(redis, key, token)` — **claim com token de dono, em `app/`** |
| `app/services/atlas/observer_media.py:599-606` | `redis.set(lock_key, "1", ex=300, nx=True)` + `delete` |
| `app/api/webhook.py:1425-1427`, `:1496-1503` | `SET NX EX` de dedupe de mensagem, **no próprio arquivo do webhook** |
| `app/services/work/runs.py` + `app/workers/smith_worker.py:281-312` | lease em Postgres (`lease_owner`/`lease_token`/`lease_expires_at`) |
| `app/services/memory_service.py:248/308/330` | lock em tabela |

🔴 **Conclusão para a §5 do CLAUDE.md:** a trava de turno **não é peça nova**. É `SET NX EX` com token, o mesmo comando que o webhook já usa, liberado pelo mesmo comparador de valor que `route_sentinel` já usa, morando no módulo que já é dono das chaves Redis do buffer.

### 2.12 Os guardas que já existem e que esta SPEC NÃO pode quebrar

```bash
grep -rln "message_buffer\|buffer_processor\|processar_buffers_prontos" backend/tests/ | head
wc -l backend/tests/test_midia_e_concorrencia_do_webhook.py backend/tests/test_a_atendente_fala_e_o_robo_cala.py
```

📊 **13/09/2026:** `backend/tests/` tem **350** arquivos. Os que cercam esta superfície:

| arquivo | o que afirma hoje | efeito desta SPEC |
|---|---|---|
| `tests/test_midia_e_concorrencia_do_webhook.py` (608 linhas) — `teste_o_buffer_processa_em_paralelo` (`:519`), `teste_uma_conversa_que_explode_nao_derruba_as_outras` (`:551`), `teste_o_teto_de_paralelismo_vem_do_ambiente` (`:578`) | o varredor processa **conversas diferentes** em paralelo | 🔴 **tem de continuar verde.** A trava é **por conversa**, nunca global — este arquivo é a linha de controle (CLAUDE.md §9.2) |
| mesmo arquivo, `:177-334` | mídia de 8 MB/16 MB, vídeo, figurinha | mídia entra no buffer: estes casos mudam de caminho, não de veredito |
| `tests/test_a_atendente_fala_e_o_robo_cala.py` (732 linhas), `:675,:704` | a janela, a pausa e o `fantasma_lid` | a ordem nova de `a_ia_deve_calar` passa por aqui |
| `tests/test_a_janela_esta_ligada_nos_portoes.py`, `test_a_janela_do_travamento_e_de_verdade.py` | os portões da janela | idem |
| `tests/test_o_espelho_vira_conversa.py`, `test_o_espelho_nao_le_o_proprio_eco.py`, `test_o_espelho_nao_aprende_com_a_amandus.py` | o espelho | o `wa_message_id` no pipeline passa por aqui |
| `backend/tests/corpus/` | hoje só `retornos_de_cobranca.json` e `telas_reais/` (17 `.jsonl` de URA) | 🔴 **não existe corpus de conversa de atendimento.** O corpus de rajadas desta SPEC é novo |

---

## 3. As medições no banco — 📊 com a consulta ao lado

> ⛔ Todas read-only, só contagens e intervalos. **Nenhum conteúdo de mensagem, nenhum telefone, nenhum nome.** Conversas identificadas só por UUID.

**Como foi medido:** `psycopg` 3.3.5 direto no Postgres pela `SUPABASE_DB_URL` de `backend/.env`, sessão `read_only = True`, com um guarda em Python que **recusa** qualquer SQL com verbo de escrita. ⚠️ O repositório não tem helper de SQL cru (`app/core/database.py` só expõe o cliente PostgREST); o padrão de conexão de `scripts/migrar_conversas_fantasma_lid.py` foi lido e reproduzido. **Zero escritas.** PostgreSQL 17.6. Volumes de partida: `messages` **33.565** · `conversations` **860** · `attendance_transcripts` **166.365** · `companies` **5**.

### 3.0 🔴 O ACHADO QUE PRECEDE TODOS OS OUTROS: a régua da rajada estava no relógio errado

A primeira medição rodou sobre `messages.created_at` e devolveu **2.510 rajadas**. ⛔ **Esse número está errado e não pode ser citado.**

`messages.created_at` é `DEFAULT now()` — o instante em que **o espelho gravou a linha**, não em que o segurado mandou a mensagem. O próprio produto documenta a diferença: `app/services/atlas/espelho_chat.py:771-777` e `:921` — *"`created_at` (quando ela foi GRAVADA). São coisas diferentes"*. 📊 **32.231 das 33.565** linhas de `messages` têm `payload->>'origem' = 'espelho'`, e os dias de backfill aparecem como picos (14/08: 5.365 linhas · 15/08: 5.090 · 10/09: 4.928). Um HISTORY_SYNC de pareamento novo grava **meses** de conversa em segundos — e tudo isso vira "rajada".

**O relógio real é `attendance_transcripts.wa_timestamp`** (o acervo do Observador, 166.365 linhas desde 17/09/2024), que casa com `messages` em **97,2%** por `wa_message_id`. ⚠️ `observed_events` **não serve**: só 3,9% casam e 32.587 das 32.588 linhas têm `insurer_key` — é o acervo de **corredor com seguradora**, não de atendimento.

**A linha de controle (CLAUDE.md §9.2) — mesmas linhas, dois relógios, mesma regra de 30 s:**

| | intervalos ≤ 30 s |
|---|---|
| por `created_at` (gravação) | **9.927** |
| por `wa_timestamp` (real) | **7.249** |
| **falsos positivos do `created_at`** | **2.839 (+39,2%)** |
| perdidos pelo `created_at` | 161 |

📊 Atraso entre o evento e a gravação: **mediana 5 s, p90 2.097.447 s (24 dias)**. A mediana engana; o p90 é o backfill.

```sql
with par as (
  select m.id, m.conversation_id, m.created_at, t.wa_timestamp, t.company_id, t.counterparty, t.message_id
  from messages m join attendance_transcripts t on t.message_id = m.payload->>'wa_message_id'
  where m.role='user' and t.direction='in' and t.insurer_key is null),
r as (select extract(epoch from (created_at - lag(created_at) over w1)) gap_gravacao,
             extract(epoch from (wa_timestamp - lag(wa_timestamp) over w2)) gap_real
      from par window w1 as (partition by conversation_id order by created_at, id),
                      w2 as (partition by company_id, counterparty order by wa_timestamp, message_id))
select count(*) intervalos, count(*) filter (where gap_gravacao<=30) pelo_created_at,
       count(*) filter (where gap_real<=30) pelo_wa_timestamp,
       count(*) filter (where gap_gravacao<=30 and gap_real>30) falso_positivo,
       count(*) filter (where gap_gravacao>30 and gap_real<=30) perdidos
from r where gap_gravacao is not null and gap_real is not null;
```

🔴 **Consequência para a SPEC:** o corpus das 20 rajadas e toda calibragem da janela leem **`attendance_transcripts.wa_timestamp`**. Uma régua calibrada em `messages.created_at` é uma régua sobre o relógio do espelho — é literalmente o defeito do CLAUDE.md §9.4 ("um padrão medido com um motor e aplicado com outro é um padrão sobre outra coisa"), na versão relógio.

### 3.1 📊 As rajadas — 20.727 delas, e a janela calibrada

Definição usada em **todas** as medições de A (uma só, com ordenação idêntica em todos os CTEs — a primeira versão tinha ordenação inconsistente entre o `lag` e o `sum` acumulado e devolvia 19.118 em vez de 20.727):

```sql
with base as (select company_id, counterparty, direction, msg_type, wa_timestamp, message_id
              from attendance_transcripts where insurer_key is null),
ord as (select *, sum(case when direction='in' then 1 else 0 end) over (
          partition by company_id, counterparty
          order by wa_timestamp, (case when direction='in' then 0 else 1 end), message_id
          rows between unbounded preceding and current row) as idx_in from base),
inb as (select o.*, extract(epoch from (o.wa_timestamp - lag(o.wa_timestamp) over w)) as gap_s
        from ord o where o.direction='in'
        window w as (partition by o.company_id,o.counterparty order by o.wa_timestamp,o.message_id)),
marc as (select *, case when gap_s is null or gap_s>30 then 1 else 0 end nova from inb),
grp as (select *, sum(nova) over (partition by company_id,counterparty
          order by wa_timestamp,message_id rows between unbounded preceding and current row) g from marc),
rajadas as (select company_id, counterparty, g, count(*) n, max(idx_in) idx_fim,
              extract(epoch from (max(wa_timestamp)-min(wa_timestamp))) dur_s,
              count(*) filter (where msg_type in ('image','audio','video','document','sticker','ptt')) n_midia
            from grp group by 1,2,3 having count(*)>=2)
```

⚠️ Filtro `insurer_key is null` conferido **contra o motor real** (`canais_observados.natureza_da_contraparte`): o motor classifica 159.257 linhas como cliente contra 159.267 do filtro — divergência de **0,006%**, desprezível (CLAUDE.md §9.4: medir com a ferramenta que vai usar).

**Universo:** 📊 **84.818** mensagens de entrada de cliente, **1.874** contrapartes, 17/09/2024 → 12/09/2026.

| | |
|---|---|
| **rajadas** (≥ 2 mensagens de entrada com ≤ 30 s entre consecutivas) | **20.727** |
| mensagens envolvidas | **72.610** — **85,6% de todo o inbound** |
| média · maior | 3,50 · **84** |
| duração da rajada | mediana **7 s** · p90 **34 s** · máx **254 s** |

| tamanho | rajadas | mensagens | % |
|---|---|---|---|
| 2 | 11.058 | 22.116 | 53,4% |
| 3 | 2.403 | 7.209 | 11,6% |
| 4 | 3.585 | 14.340 | 17,3% |
| **5+** | **3.681** | **28.945** | **17,8%** |

🔴 **Os intervalos DENTRO da rajada — 51.883 medidos. É esta tabela que calibra a janela:**

| min | p25 | mediana | p75 | p90 | máx |
|---|---|---|---|---|---|
| 0 s | 0 s | **1 s** | 8 s | 17 s | 30 s |

| faixa | intervalos | % | **acumulado** |
|---|---|---|---|
| 0–3 s | 29.065 | **56,0%** | 56,0% |
| 3–8 s | 8.579 | 16,5% | **72,5%** |
| 8–18 s | 9.253 | 17,8% | **90,3%** |
| 18–25 s | 3.508 | 6,8% | 97,1% |
| > 25 s | 1.478 | 2,8% | 100% |

📊 **Uma janela de 8 s agrega 72,5% dos intervalos; 18 s agrega 90,3%.** O que se compra ao ir de 8 para 18 é 17,8 pontos; o que se paga é latência em toda resposta que espera. **É exatamente por isso que a janela precisa ser por conteúdo, e não um número só.**

⚠️ `wa_timestamp` tem granularidade de **segundo inteiro** (`messageTimestamp` do WhatsApp é em segundos). O p25 = 0 s é real, não arredondamento. **Não há resolução sub-segundo neste acervo** — o que significa que a classe "dado curto · 3 s" não pode ser validada contra intervalos menores que 1 s.

### 3.2 📊 Rajadas com mídia — 27,06%

| | rajadas | % |
|---|---|---|
| **com mídia** | **5.608** | **27,06%** |
| sem mídia | 15.119 | 72,94% |

Entrada de cliente por tipo: text 68.943 · **audio 7.302** · **image 4.652** · **document 2.744** · sticker 381 · buttons 361 · video 310 · list 97.

🔴 **Mais de uma em cada quatro rajadas tem mídia.** Enquanto a mídia pula o buffer, o buffer é furado em **27% do corpus** — e há rajadas **100% mídia** (6 de 6, 5 de 5, 4 de 4 entre as candidatas).

### 3.3 📊 Fragmentação — 81,2%, com uma ressalva material

| | acervo inteiro | desde 01/09/2026 |
|---|---|---|
| rajadas | 20.727 | 826 |
| **0** respostas | 5.281 | 211 |
| **exatamente 1** | **2.897** | **270** |
| **mais de 1** | **12.549** | **345** |
| % que fragmentou (das respondidas) | **81,2%** | **56,1%** |

Distribuição: 2 respostas → 6.369 · 3 → 1.201 · 4+ → 4.979.

🔴 **A ressalva, e ela é grande.** `attendance_transcripts.direction='out'` **não distingue o agente da atendente humana** — o Observador captura tudo que sai do número, e `messages.sender_user_id` é **NULL em 100%** do outbound. 📊 `companies.agent_enabled` é **false nas 5 empresas**, e `conversation_logs` (o rastro do agente) tem **566** linhas contra ~13.679 saídas no acervo. **INFERÊNCIA:** a esmagadora maioria desse outbound é **humano**. Portanto os 81,2% medem como a **rajada é respondida hoje**, e servem de linha de base; ⛔ **não** provam que o agente fragmenta. A prova disso continua sendo a do diagnóstico §1.4 (4 de 4, sobre os 5 atendimentos reais do agente).

### 3.4 📊 O corpus tem de onde nascer — 30 candidatas estratificadas

Estratificadas por tamanho × ritmo × corretora, a mais recente de cada célula, desde 01/08/2026. Identificador = UUID da **primeira mensagem** da rajada (`attendance_transcripts.id`); não existe UUID de rajada. Todas casam com `conversations.id`.

| uuid (1ª msg) | corretora | n | mídia | gap méd/máx | respostas | data |
|---|---|---|---|---|---|---|
| `56e1d9ae-6f08-487a-9c8e-1f3249f5c43d` | Resulta | 2 | 0 | 12/12 | 0 | 12/09 |
| `463f3a59-4016-4214-9350-ca012c1ab38b` | AutoFleet | 2 | 1 | 28/28 | 0 | 12/09 |
| `0c4157c5-837a-4cdf-bef0-ba211eac4c9c` | AutoFleet | 2 | 2 | 8/8 | 0 | 12/09 |
| `0e0dd627-5c32-48be-b9e1-89cb4a6d1e70` | Resulta | 2 | 0 | 2/2 | 1 | 11/09 |
| `a15cc871-8627-4e58-8cd5-7d692b53ee9f` | Resulta | 2 | 0 | 6/6 | 1 | 11/09 |
| `3fbe4342-ed69-431f-8d2d-90ebadedb385` | AutoFleet | 2 | 2 | 0/0 | 0 | 12/09 |
| `e431ab34-6085-4670-8f15-7da37c9f9b72` | AMANDUS | 2 | 0 | 17/17 | 1 | 14/08 |
| `5ad7a7f1-10f9-4172-ab77-fef18dd87c3a` | AMANDUS | 2 | 0 | 8/8 | 2 | 17/08 |
| `dd13fc8d-3958-44f8-8514-bf6d1476fcbb` | Resulta | 3 | 2 | 12,5/**22** | 2 | 11/09 |
| `0ba6a1e6-d80b-4f5e-a159-4f20ef1919b4` | AutoFleet | 3 | 1 | 10,5/15 | 0 | 12/09 |
| `e692a96d-657a-4418-a0c9-3aab0e65115a` | Resulta | 3 | 3 | 5,5/6 | 1 | 11/09 |
| `70244206-f202-4a9b-8495-084ed4c5c62b` | AutoFleet | 3 | 0 | 7/7 | **4** | 11/09 |
| `0445caff-5a99-4f5c-bab0-cd57bb65cc11` | Resulta | 3 | 2 | 1,5/2 | 2 | 10/09 |
| `3943c1bd-4098-4e11-93f2-bd34c7c3cde2` | AutoFleet | 3 | 3 | 0/0 | 3 | 11/09 |
| `1c7745ce-f071-4b0e-9b03-2737993e5183` | AMANDUS | 3 | 0 | 19/**28** | 0 | 12/08 |
| `4c347c50-e8bc-4428-94f7-a4ccc07af193` | Resulta | 4 | **4** | 11/19 | 1 | 11/09 |
| `f1788f54-519a-44df-bac9-50f2fac5eb67` | AutoFleet | 4 | 1 | 18,3/**28** | 0 | 11/09 |
| `8d45042b-3bfa-49e5-89bd-44099337dac0` | Resulta | 4 | 0 | 3,7/6 | 0 | 11/09 |
| `416d511b-3a5b-40d7-96e7-66f8e54c238d` | AutoFleet | 4 | 0 | 2/4 | **4** | 08/09 |
| `7da70262-a718-4126-9289-616d69f46645` | AutoFleet | 4 | **4** | 0,3/1 | 2 | 09/09 |
| `e46836f6-8023-43ca-8ea9-876f2023dedf` | Resulta | 4 | 1 | 0,7/2 | 1 | 31/08 |
| `fcd46669-844e-411a-8552-858937beed53` | AMANDUS | 4 | 2 | 13,7/**27** | 1 | 16/08 |
| `c7eef074-4347-4865-b94f-55d703c65f79` | Resulta | 5 | 0 | 9,3/20 | 3 | 11/09 |
| `609fab58-f5f5-4e01-8510-d4065660ef5b` | AutoFleet | 5 | 2 | 8,8/18 | 3 | 11/09 |
| `ff27822e-57d6-4bda-953f-7e619799ca29` | AutoFleet | 5 | 0 | 7/8 | 1 | 10/09 |
| `727bd8db-1436-4ac1-ad19-642131a9e260` | Resulta | 5 | 0 | 2,8/5 | 1 | 04/09 |
| `cbfccc8a-0b2f-411c-8082-0af429d5b41a` | AutoFleet | 5 | **5** | 0,8/2 | 1 | 09/09 |
| `955a0e64-6cd8-4d24-9ae1-f04939684cb6` | Resulta | **6** | **6** | 0,8/1 | 1 | 10/09 |

Corretoras no acervo: **Resulta** 14.509 rajadas · **AutoFleet** 6.202 · **AMANDUS** 16 (corretora de teste do Founder, `company_kind='client'`, `is_technical=false`).

### 3.5 📊 As fantasmas — **175**, não 174, e só **9** têm par

Critério idêntico a `e_fantasma()` (`migrar_conversas_fantasma_lid.py:105-110`): dígitos de `user_phone`; fantasma se **não começa com `55`** OU tem **mais de 13 dígitos**. A contagem foi feita **em SQL**, não invocando o script.

| | |
|---|---|
| conversas | 860 |
| **fantasmas** | **175** · ⚠️ era 174 em 09/09 — **nasceu mais uma** |
| **abertas** | **175 (100%)** — nenhuma foi fechada |
| status | `open` 170 · `HUMAN_REQUESTED` 5 |
| **com pausa humana presa** | **10** ⚠️ o script dizia 7 em 09/09; P-PILOTO-13 diz 10. **10 é o número de hoje** |
| **com par real inequívoco** | **9** |
| **sem par encontrável** | **166 (94,9%)** |
| mensagens presas do lado fantasma | **1.884** (todas com `wa_message_id`) |

| corretora | fantasmas | com pausa | total de conversas |
|---|---|---|---|
| **AutoFleet** | **106** | 5 | 506 |
| **Resulta** | **69** | 5 | 345 |
| AMANDUS | 0 | 0 | 9 |

🔴 **E o schema não impede a próxima.** Constraints reais de `conversations`, lidas do catálogo:

```sql
conversations_pkey                   PRIMARY KEY (id)
conversations_session_id_key         UNIQUE (session_id)
uq_conversations_id_company          UNIQUE (id, company_id)
conversations_company_id_fkey        FOREIGN KEY (company_id) REFERENCES companies(id)
conversations_agent_id_fkey          FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
ck_conversations_resolucao_coerente  CHECK ((resolvido_em IS NULL AND resolucao_motivo IS NULL)
                                         OR (resolvido_em IS NOT NULL AND resolucao_motivo IS NOT NULL))
ck_conversations_resolucao_motivo    CHECK (resolucao_motivo IS NULL OR resolucao_motivo IN
                                       ('acionamento_concluido','encaminhado','resolvido_pelo_segurado',
                                        'fechado_por_humano','expirou'))
```

📊 `idx_conversations_company_user_channel (company_id, user_id, channel)` **NÃO é UNIQUE**; `user_phone` **não tem índice nem constraint**. O único UNIQUE natural é `session_id` — e o `@lid` gera `session_id` diferente do telefone, então **a fantasma nasce legalmente**. 🔴 E o CHECK confirma no banco: **`fantasma_lid` não é aceito** — é o texto exato que a migration M1 tem de estender.

RLS: `relrowsecurity=true` em `conversations`, `messages` e `attendance_transcripts`; `relforcerowsecurity=false` nas três. **O backend usa service role: o filtro no código é a única proteção efetiva** (CLAUDE.md §7).

### 3.6 🔴 O espelho em dobro — e um candidato a P0 cross-tenant que ninguém tinha visto

**`wa_message_id` existe e está preenchido em 96,03%** (`messages.payload->>'wa_message_id'`, jsonb; não há coluna dedicada):

| | linhas | com `wa_message_id` | % |
|---|---|---|---|
| total | 33.565 | **32.231** | **96,03%** |
| `role='user'` | 17.099 | 16.410 | 95,97% |
| `role='assistant'` | 16.466 | 15.821 | 96,08% |

As 1.334 sem o campo são as linhas web/legado pré-espelho (`payload` nulo em 1.253).

**Duplicatas por conteúdo** (comparadas por `md5(content)`, ⛔ conteúdo nunca impresso; filtro `length > 20` para não contar "ok"/"sim"):

| | conteúdo > 20 chars | sem filtro |
|---|---|---|
| grupos duplicados | 594 | 1.747 |
| pares exatos | 433 | 1.112 |
| **pares com 1–60 min de diferença** | **99** | 194 |
| desses, com `wa_message_id` distinto | 54 | 132 |

⚠️ **Não confirmo os "30 pares" do diagnóstico.** O número depende inteiramente do critério (varia de 99 a 1.112); o mais próximo do enunciado é **99**. Os de > 24 h são quase certamente o segurado repetindo a frase.

🔴 **E aqui está o achado que muda o desenho:**

```sql
with w as (select payload->>'wa_message_id' wa, count(*) n, count(distinct conversation_id) nc
           from messages where payload ? 'wa_message_id' group by 1)
select count(*) filter (where n>1) repetidos, sum(n-1) filter (where n>1) excedentes,
       count(*) filter (where n>1 and nc>1) em_conversas_diferentes,
       count(*) filter (where n>1 and nc=1) na_mesma_conversa from w;
```

| | |
|---|---|
| `wa_message_id` repetidos | **134** |
| linhas envolvidas · excedentes | 273 · **139** |
| **em conversas DIFERENTES** | **134 — 100%** |
| **na mesma conversa** | **0** |

🔴 **O índice único funciona exatamente como escrito, e é por isso que ele não pega nada disto.** `messages_espelho_sem_duplicata_uidx` é único **por conversa**: duplicata dentro da conversa é impossível; **entre** conversas é livre. É a assinatura estrutural do espelho em dobro.

Cruzando com as fantasmas: **35 dos 134** são par fantasma × real (10 fantasmas, 11 reais) — o LID responde por ~26% do problema. 🔴 **Os outros 99 se repetem entre duas conversas REAIS**, e a migração das fantasmas não os toca.

🔴🔴 **E 104 dos 134 atravessam CORRETORAS** (108 linhas no acervo). O medidor investigou antes de reportar: os 110 grupos têm **texto idêntico** (0 com texto diferente → **não é colisão de id**), tocam **6 contrapartes**, **nenhuma é seguradora** (`insurer_key is null` em 100%), e os `observer_number` **não são compartilhados** (0 dos 5 observadores aparece em mais de uma empresa). Ids repetidos são curtos (22 e 32 chars) contra 41/36 dos únicos. Linhas: Resulta 88 · AutoFleet 103 · AMANDUS 25.

> **INFERÊNCIA, não fato:** a mesma mensagem de WhatsApp está gravada sob **dois `company_id`**. A causa não se determina por contagem sem ler conteúdo, e conteúdo não foi lido. 🔴 **Tratar como candidato a P0 cross-tenant e investigar ANTES de qualquer migração** — é a classe de defeito do CLAUDE.md §7 e uma das oito condições de parada do §10.

*(Bônus: `attendance_transcripts` tem **110** `message_id` repetidos em 166.365 linhas — a tabela **não** tem UNIQUE em `message_id`.)*

### 3.7 📊 O silêncio — 8.574 sem explicação, 6 motivos escritos em todo o banco

**Existe uma única coluna de motivo:** `conversations.human_handoff_reason` (texto livre).

| | conversas | com motivo escrito | sem motivo |
|---|---|---|---|
| total | 860 | **6** | **854 (99,3%)** |
| `open` | 670 | 4 | 666 |
| **`HUMAN_REQUESTED`** | **131** | **2** | **129** |
| `active` | 59 | 0 | 59 |

🔴 **129 das 131 conversas em `HUMAN_REQUESTED` não dizem por quê** — e isso confirma, com número, o que o diagnóstico §1.5 afirmou sobre `human_handoff_reason` vazio.

**Não existe nenhum registro de "o agente não respondeu porque X".** `work_events` (45.459 linhas) só tem ciclo de vida de run/step (`step.started` 11.546 · `run.succeeded` 4.453 · `step.failed` 41 · `run.failed` 4 · `espera.vencida` 3). `agent_activities` é feed de UI. 🔴 E `conversation_logs` tem **566 linhas, todas `status='success'`, zero com `error_message`**: **ele só grava o que deu certo — uma resposta que nunca saiu não deixa linha nenhuma.**

**Quanto silêncio existe de fato** (turno = rajada ou mensagem isolada; silêncio = nenhuma saída antes da próxima entrada; a coluna "no meio" exclui o último turno, que naturalmente não tem resposta):

| janela | turnos | sem resposta | **silêncios no MEIO da conversa** | % |
|---|---|---|---|---|
| acervo inteiro | 32.935 | 9.636 | **8.574** | **26,0%** |
| desde 01/08/2026 | 6.416 | 1.987 | **1.777** | **27,7%** |
| desde 01/09/2026 | 2.127 | 705 | **589** | **27,7%** |

🔴 **8.574 silêncios no meio da conversa · 6 motivos escritos no banco inteiro.** E os 6 são motivos de *handoff*, não de silêncio, e não estão ligados a um turno.

⚠️ **Achado de PII não solicitado:** `conversations.human_handoff_reason` guarda **narrativa livre em texto claro** sobre o sinistro do segurado — detalhe de acidente, terceiros envolvidos, orientação jurídica. Descoberto ao listar os 6 valores distintos; ⛔ **o conteúdo não foi reproduzido**. É uma coluna sem redação num campo que o produto trata como "motivo". **Vira pendência.**

### 3.8 🔴 O nome do agente — e o campo que o diagnóstico procurou não existe

```sql
select column_name from information_schema.columns
 where table_name='companies' and column_name='agent_name';   -- 0 linhas
```

📊 **`companies.agent_name` NÃO EXISTE.** As colunas `agent*` de `companies` são `agent_enabled`, `agent_system_prompt`, `agent_user_prompt_template`, `agent_config_updated_at`, `agent_config_updated_by`. **Não há nome de agente por empresa.**

**`agents.name` — 8 agentes, 3 ativos, um por corretora:**

| corretora | `agents.name` | ativo |
|---|---|---|
| **Resulta** | **AutoBrokers** | ✅ |
| Resulta | **Amanda** | ❌ **desativado** |
| **AutoFleet** | **AutoBrokers** | ✅ |
| AutoFleet | Maria Regina | ❌ |
| AMANDUS | AutoBrokers Sandbox | ✅ |
| AMANDUS | JOANA | ❌ |
| Blueprint Studio | AutoBrokers · **Even** | ❌ ❌ |

🔴🔴 **Divergência material com D-PILOTO-12.** A decisão diz *"'Amanda' na Resulta é escolha da Saionara e **fica**"*. 📊 Mas a linha `Amanda` está **desativada**, e o agente **ativo** da Resulta se chama **`AutoBrokers`**. **O nome que o Founder acredita estar em uso não é o que o agente ativo carrega.** Isto é caixa do Founder, não decisão do executor.
⚠️ `Even` é nomenclatura da SPEC-013, declarada **memória superada** pelo CLAUDE.md §4 — desativada, mas ainda no banco.

**`conversations.agent_name` — o rótulo, e o que ele realmente diz:**

| valor | conversas | empresas |
|---|---|---|
| **Espelho** | **782** | 3 |
| **Smith Agent** | **73** | 3 |
| AutoBrokers | **4** | 2 |
| Motor de Acionamento | 1 | 1 |

🔴 Dois nomes proibidos pelo GLOSSARIO ocupando o campo que o corretor lê: **"Smith"** (runtime técnico invisível, nunca marca) é o `DEFAULT` da coluna e aparece em 73 conversas; **"Espelho"** é nome de mecanismo interno em 782 de 860. O nome certo aparece em **4**.

**Colisão entre nome de agente e nome de membro da equipe: NÃO.** ⚠️ `company_members` **não tem coluna `name`** — o nome vem de `users_v2.first_name/last_name` via `user_id`. Comparados os **9** nomes de agente distintos contra os **10** membros: **0 coincidências** de nome completo e **0** de primeiro nome. ⛔ Nenhum nome de pessoa física foi impresso.

📊 E o contexto que enquadra tudo: **`companies.agent_enabled = false` nas 5 empresas.** O agente está desligado agora.

### 3.9 O que NÃO foi possível medir, e por quê

| pedido | por quê |
|---|---|
| fragmentação **do agente**, separada da atendente | nenhuma coluna distingue: `messages.sender_user_id` é NULL em 100% do outbound, `payload->>'origem'` é `espelho` para todos, e `conversation_logs` (566 linhas) não liga a `messages` |
| intervalos abaixo de 1 s | `wa_timestamp` vem do `messageTimestamp` do WhatsApp, com granularidade de **segundo inteiro** |
| comparar com "174 fantasmas em 12/09" | não há snapshot histórico. Medido o estado de hoje: **175**. O delta com 09/09 é verificável; com 12/09 não |
| reproduzir os "30 pares" do espelho | nenhum critério razoável devolve 30 (varia de 99 a 1.112). O critério que produziu 30 é desconhecido |
| causa raiz do `wa_message_id` cross-tenant | as contagens provam que acontece e **excluem** colisão de id e observador compartilhado; a causa exige leitura de conteúdo, que não foi feita |
| `companies.agent_name` | **a coluna não existe** |

⛔ **Escritas: zero.** Sessão `read_only`, guarda de verbo em Python, nenhum script do repositório rodado com `--vivo`. Nenhum conteúdo de mensagem, CPF, CNPJ, telefone, nome de segurado, placa, e-mail ou credencial foi impresso ou gravado.

---

## 4. Pesquisa externa — fontes primárias reabertas em 13/09/2026

### E01 — Redis · `SET … NX PX` como lock, e a liberação que compara o valor

**URL:** https://redis.io/docs/latest/commands/set/ · https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
⚠️ A URL antiga `…/use-cases/patterns/distributed-locks/` **mudou**; a página do `SET` aponta para a nova.

**O que ela faz.** Documenta `SET key value [NX] [PX milliseconds]` e, na seção *Patterns*, o lock mínimo, literal:

> *"The command `SET resource-name anystring NX EX max-lock-time` is a simple way to implement a locking system with Redis."*
> *"Instead of setting a fixed string, set a non-guessable large random string, called token."*
> *"Instead of releasing the lock with `DEL`, send a script that only removes the key if the value matches."*

Script Lua oficial, literal:
```lua
if redis.call("get",KEYS[1]) == ARGV[1]
then
    return redis.call("del",KEYS[1])
else
    return 0
end
```

Sobre renovar, literal: *"the client … may extend the lock by sending a Lua script … that extends the TTL of the key if the key exists and its value is still the random value the client assigned"* — e o teto: *"the maximum number of lock reacquisition attempts should be limited, otherwise one of the liveness properties is violated."*

E a advertência que não se pode ignorar: *"don't assume that a lock is retained as long as the process that had acquired it is alive"* · *"Redis is not using monotonic clock for TTL expiration mechanism."*

**O que MODELAMOS:** `SET NX EX` com **token aleatório por turno**, liberação por comparação de valor, renovação com teto, e — por causa da última frase — **uma reconferência de posse imediatamente antes de enviar** (o `fencing` possível sem token monotônico): quem não é mais dono **não fala**.
**O que REJEITAMOS:** Redlock multi-instância (temos um Redis, e a doc só o recomenda contra falha de nó — complexidade sem o problema); e `DEL` cego na liberação, que apagaria a trava de outro turno.
**Como o juiz inspecciona:** abre a página do `SET`, confere que o release do código é `EVAL` com comparação (ou `DELEX IFEQ` se o Redis for ≥ 8.4), e roda a mutação "liberar com `DEL`" exigindo que o guarda fique vermelho.

### E02 — Meta · WhatsApp Cloud API: o "digitando" morre sozinho em **25 segundos**

**URL:** https://developers.facebook.com/docs/whatsapp/cloud-api/typing-indicators/

**O que ela faz.** Define o typing indicator como parte da mesma chamada do read receipt (`status: "read"` + `typing_indicator`), exigindo o `message_id` de uma mensagem **recebida**. Citações literais:

> *"The typing indicator will be dismissed once you respond, or after 25 seconds, whichever comes first."*
> *"To prevent a poor user experience, only display a typing indicator if you are going to respond."*

**O que MODELAMOS:** 🔴 **o teto da janela adaptativa e a vida do indicador passam a ser o mesmo número, 25 s** — o que já é o `BUFFER_MAX_WAIT_SECONDS` de hoje. E a segunda frase vira regra de produto: **presença só depois do portão de silêncio dizer que o agente vai falar** (senão o segurado vê "digitando…" e não recebe nada).
**O que REJEITAMOS:** a chamada da Meta em si — nosso canal é Evolution, não Cloud API (D-E001-02: atendimento permanece Evolution Go). Modela-se o **limite e a regra**, não o endpoint.
**Como o juiz inspeciona:** abre a página, confere o número 25 no texto, e confere no código que o teto da janela e a renovação da presença derivam da **mesma constante**.

### E03 — Evolution API · `sendPresence`, e o `delay` que já digita

**URL (código-fonte, que é fonte primária mais forte que a doc):**
`src/api/routes/chat.router.ts` · `src/api/abstract/abstract.router.ts` · `src/validate/chat.schema.ts` · `src/api/dto/chat.dto.ts` · `src/api/integrations/channel/whatsapp/whatsapp.baileys.service.ts` — todos em https://github.com/EvolutionAPI/evolution-api
⚠️ `doc.evolution-api.com/v2/api-reference/chat-controller/send-presence` **devolveu 404** em toda tentativa de fetch em 13/09/2026 (site renderizado por JS). A autoridade usada é o repositório.

**O que ela faz.** Rota `POST {base}/chat/sendPresence/{instanceName}` (prefixo `/chat` em `index.router.ts`, `:instanceName` em `abstract.router.ts:routerPath`). Schema, literal:
```ts
properties: { number: {...}, delay: { type: 'number' },
  presence: { type: 'string', enum: ['unavailable','available','composing','recording','paused'] } },
required: ['number', 'presence', 'delay'],
```
E `delay` **no próprio `sendText`** já produz o "digitando", em `sendMessageWithTyping`:
```ts
if (options?.delay) { … await this.client.sendPresenceUpdate('composing', sender);
  await delay(20000); await this.client.sendPresenceUpdate('paused', sender); … }
```
O laço refaz `composing` a cada **20 000 ms**.

**O que MODELAMOS:** presença pelo **provider que já existe** (`EvolutionProvider._post`), `composing` renovado a cada ≤ 20 s enquanto o turno é gerado, `paused` ao terminar. E a economia: quando a resposta **já está pronta**, `delay` no `sendText` resolve sem uma segunda chamada.
**O que REJEITAMOS:** um cliente HTTP novo para presença; e tratar 20 s como número nosso — é constante **deles**, e o BLOCO 0 confere se o fork GO implantado tem a rota (`rotas_de_envio_medidas()`, `evolution_go.py:577`). **Se a rota não existir no fork, a presença fica desligada com pendência nomeada — não se simula "digitando".**
**Como o juiz inspeciona:** abre os dois arquivos do repositório, confere o enum e os três campos obrigatórios, e confere no nosso código que `delay` é enviado em milissegundos.

### E04 — Meta · webhooks reentregam, e a dedupe é do consumidor

**URL:** https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview · https://developers.facebook.com/docs/graph-api/webhooks/getting-started/

> *"Meta retries delivery with decreasing frequency until the request succeeds, for up to 7 days."* · *"These retries can result in duplicate webhook notifications."*
> (Graph API) *"Your server should handle deduplication in these cases."*

⚠️ **Lacuna registrada, e é da Meta:** em nenhuma página ela escreve *"deduplique pelo id da mensagem"*, nem documenta unicidade/estabilidade do `wamid` em texto — o campo só aparece nos exemplos JSON.

**O que MODELAMOS:** a dedupe durável é **nossa**, por `wa_message_id`, no **índice único que já existe** (R32) — o que a SPEC faz é **dar a chave ao pipeline** (R34), não criar índice.
**O que REJEITAMOS:** herdar garantia de unicidade de quem não a escreve; e confiar no TTL do Redis (`wa_dedupe:*`, R20) como histórico — TTL não é reconciliação.
**Como o juiz inspeciona:** reenvia o mesmo payload duas vezes pela rota real e conta **uma** linha em `messages` e **uma** resposta ao cliente.

### E05 — Evolution API · o webhook dela reentrega até 10 vezes, e ela não deduplica

**URL:** `src/api/integrations/event/webhook/webhook.controller.ts` e `prisma/postgresql-schema.prisma` em https://github.com/EvolutionAPI/evolution-api

Medido no código: `maxRetryAttempts = maxRetries ?? webhookConfig.RETRY?.MAX_ATTEMPTS ?? 10`, backoff exponencial com jitter (delay inicial 5 s, teto 300 s), e `nonRetryableStatusCodes ?? [400, 401, 403, 404, 422]`. E o schema:
```prisma
model Message { id String @id @default(cuid())  key Json @db.JsonB … @@index([instanceId]) }
```
**Nenhum `@unique` sobre `key`** — a chave primária é um `cuid()` da própria Evolution: reentrega grava linha nova lá dentro.

**O que MODELAMOS:** o webhook responde **200 rápido** e o trabalho fica no buffer/turno — é o que o desenho já faz para texto (`_buffer_or_dispatch_text`) e o que a mídia passará a fazer. E a trava de turno vira a segunda rede: uma reentrega que chegue durante a geração **não abre turno novo**.
**O que REJEITAMOS:** supor `key.id` estável por contrato (não há fonte); e devolver erro em caminho lento, que é o gatilho das 10 retentativas.
**Como o juiz inspeciona:** injeta a mesma entrega duas vezes com 5 s de intervalo e conta turnos gerados.

### E06 — Stripe · a frase que a Meta não escreve

**URL:** https://docs.stripe.com/webhooks

> *"Ocasionalmente, os endpoints de webhook podem receber o mesmo evento mais de uma vez. Para se proteger contra o recebimento de eventos duplicados, registre os IDs de evento que você processou e não processe eventos já registrados."*
> *"A Stripe não garante a entrega dos eventos na ordem em que foram gerados."* · *"Não use `created` para determinar o pedido dos eventos…"*

**O que MODELAMOS:** id processado é registrado e não reprocessado; **ordem de chegada não é ordem de acontecimento** — e é por isso que a rajada se ordena por `first_at`/`last_at` do buffer e não pela ordem de entrega do webhook.
**O que REJEITAMOS:** copiar headers, assinatura ou formato da Stripe. O provedor é outro.
**Como o juiz inspeciona:** reordena duas entregas da mesma rajada e confere que o texto combinado sai na ordem do relógio da mensagem, não na da entrega.

### E07 — 🔴 Janela adaptativa por conteúdo: **não há fonte primária. A invenção é nossa.**

Procurado, com filtro de domínio, em `rasa.com/docs`, `botpress.com/docs`, `twilio.com/docs` (Conversations e ConversationRelay), `learn.microsoft.com` (Bot Framework) e `developers.facebook.com`. **Nenhum fornecedor documenta agregação/debounce de mensagens do usuário com um número de segundos recomendado.** O que aparece em cada um é outra coisa (agregação de tokens de streaming do bot, timeout de espera por atendente humano, barge-in de voz).

Implementação aberta verificada arquivo a arquivo (README + `config/config.py` lidos): **`devmoreir4/whatsapp-ai-chatbot`** — https://github.com/devmoreir4/whatsapp-ai-chatbot — README literal: *"Redis-backed debounce buffer for grouped incoming messages"*, *"Debounce window: `10` seconds"*; constante `DEBOUNCE_SECONDS = 10`. **Janela fixa.** Nenhum projeto verificado faz janela adaptativa por conteúdo.

**O que MODELAMOS:** a **forma** (buffer em Redis + janela + varredor), que já é a nossa.
**O que REJEITAMOS:** 🔴 **copiar o número.** Os 10 s dele não são referência para nós. Todo segundo desta SPEC **sai do acervo** (§3) ou é declarado 💭 e calibrado no BLOCO 0.
**Como o juiz inspeciona:** procura no diff qualquer constante de janela sem 📊 ao lado; uma constante sem medição é achado.

> ⚠️ **Pistas não verificadas, registradas como pistas e não como evidência** (os arquivos não foram abertos): `openclaw/openclaw` (`debounceMs`), `NousResearch/hermes-agent` (`_text_batch_delay_seconds`), `Anmoldureha/whatsapp-bot` (5 s). **Não citar como fonte.**

---

## 5. Armadilhas que o aquecimento deve refutar

1. *"Basta aumentar o debounce de 8 s para 20 s."* — 📊 as rajadas medidas tinham 10, 12 e 22 s de intervalo (diagnóstico §1.4); e um teto maior atrasa **toda** resposta curta. A janela tem de ser por conteúdo, e o teto é 25 s por causa da E02.
2. *"Mídia é só mais um `elif` para tirar."* — são **três** pontos (C3), e a estrutura do buffer é lista de **strings** (R07): a legenda e o arquivo precisam viajar juntos.
3. *"A trava pode ser por corretora."* — trava global por corretora é exatamente o defeito da EXTRA-001.8 (uma conversa travando as outras). **É por conversa, e a prova disso é o teste de paralelismo que já existe continuar verde** (§2.12).
4. *"O `get_and_clear_buffer` atômico já resolve a corrida."* — resolve a corrida **na mesma chave**; não resolve a chave **nova** criada enquanto o turno roda (R12).
5. *"É só criar a ficha de slots respondidos."* — ela existe (C4). O buraco é o escritor cobrir 15 de 35, e `agua_escorrendo` não estar em nenhum dos dois (§2.4).
6. *"Trocar a instrução do prompt resolve a saudação."* — a regra de tamanho e a de não repetir **já estão escritas** (R27, R28, `prompts.py:90-91`). Sem número que meça obediência, trocar texto é trocar texto (AAA §3).
7. *"O índice único do espelho falta."* — ele existe desde 06/08 (R32). Falta a **chave** nas linhas do pipeline (R34).
8. *"`agent_name` é o nome do agente."* — não é (C5, §2.6).
9. *"A lista de exceções da janela é a última checagem."* — é a **primeira**, e por isso neutraliza o takeover (§2.9).
10. *"Rodar o script das fantasmas resolve as 174."* — 📊 165 das 174 **não têm par real** e o `--vivo` está travado por um CHECK (R41). Sem a migration, o script recusa e sai com código 2.
11. *"O agente responde 'digitando…' enquanto pensa, é só chamar a Evolution."* — não existe nenhuma chamada hoje (§2.10), a rota precisa ser confirmada no **fork GO implantado**, e presença antes do portão de silêncio promete resposta que não vem.
12. *"Uma resposta por rajada = uma mensagem no WhatsApp."* — não: uma resposta já vira até **4 balões** (R31). A régua é o **turno**.
13. 🔴 *"Para medir rajada, basta olhar `messages.created_at`."* — **não.** É o relógio do **espelho**, e ele infla as rajadas em **+39,2%** (§3.0). O relógio real é `attendance_transcripts.wa_timestamp`.
14. 🔴 *"Dar `wa_message_id` ao pipeline resolve o espelho em dobro."* — resolve o caso **dentro** da conversa, que 📊 é **0 de 134**. Os 134 repetidos estão **entre** conversas, e o índice único é por conversa (§3.6).
15. 🔴 *"81,2% das rajadas fragmentaram, logo o agente fragmenta."* — o acervo **não distingue** agente de atendente, e `agent_enabled` é **false nas 5 empresas** (§3.3). Esse número é linha de base de hoje, não prova sobre o agente.
16. 🔴 *"O agente da Resulta se chama Amanda."* — 📊 a linha `Amanda` está **desativada**; o agente **ativo** se chama `AutoBrokers` (§3.8). D-PILOTO-12 descreve uma intenção que o banco não reflete.
17. *"Fechar as 174 fantasmas devolve as conversas."* — 📊 são **175**, e **166 (94,9%) não têm par**. Fechá-las não devolve nada; o ganho é a **176ª não nascer**.

---

## 6. Roteiro de remedição — comandos para o BLOCO 0

```bash
git fetch origin && git rev-parse HEAD && git rev-parse origin/main
git rev-list --count HEAD..origin/main   # tem de ser 0
git rev-list --count origin/main..HEAD
git status --short

# o buffer e o varredor
grep -n "max(settings.BUFFER\|BUFFER_TTL\|def \|messages\"\]" backend/app/services/message_buffer_service.py
grep -n "_PARALELISMO_PADRAO\|Semaphore\|should_process\|get_and_clear\|max_instances" backend/app/tasks/buffer_processor.py

# os TRÊS desvios de mídia (o número tem de voltar 3)
grep -n "type\": \"media\"" backend/app/api/webhook.py

# a ficha: o buraco entre vocabulário e escritor
grep -n "_SLOTS_DA_FICHA" backend/app/agents/nodes.py
grep -n "ROTULOS = {" backend/app/services/attendance_ficha.py
grep -rn "agua_escorrendo" backend/app/

# a apresentação e o tamanho
grep -n "SEMPRE se apresente\|Frases CURTAS\|Máximo 4 itens" backend/app/core/prompts.py
grep -n "TARGET_LEN\|MAX_BALLOONS\|bloco_unico" backend/app/services/whatsapp/balloons.py backend/app/services/whatsapp_service.py

# o espelho e a chave que falta
grep -n "insert({" backend/app/api/webhook.py | head
grep -rn "wa_message_id" backend/app/ backend/supabase/migrations/

# a ordem do silêncio
sed -n '1325,1380p' backend/app/services/o_fim_do_atendimento.py

# as fantasmas
grep -rn "fantasma_lid" backend/supabase/migrations/   # tem de voltar VAZIO hoje
cd backend && PYTHONIOENCODING=utf-8 python scripts/migrar_conversas_fantasma_lid.py   # dry-run; NUNCA --vivo aqui

# presença: existe rota no fork implantado?
grep -rn "rotas_de_envio_medidas" backend/app/services/whatsapp/providers/evolution_go.py

# os guardas que não podem quebrar
cd backend && python -m pytest tests/test_midia_e_concorrencia_do_webhook.py -q
```

**Antes de qualquer SQL:** ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro. Diretório canônico: `backend/supabase/migrations/`. Formato obrigatório em §7 de lá (cabeçalho com APPLY/VERIFY/ROLLBACK/EXPAND-FIRST/DESTRUTIVA); VERIFY é **SQL executável**; ROLLBACK escrito **antes**. Modelo de forma a copiar: `backend/supabase/migrations/20260907_02_spec_extra001_reclamar_so_do_que_pode.sql`.

---

## 7. O que continua desconhecido — e como saber

| # | desconhecido | como se mede |
|---|---|---|
| D1 | Quanto tempo dura um turno de atendimento, do `get_and_clear_buffer` até o envio | ⚠️ **não medido, e `messages.created_at` NÃO serve** (§3.0). Instrumentar no BLOCO 0, ou reconstruir pelo par (entrada, saída) em `attendance_transcripts.wa_timestamp`. 🔴 **O TTL da trava sai deste número, não do palpite de 90 s** |
| D2 | Se o **fork GO implantado** tem `POST /chat/sendPresence/{instance}` | `rotas_de_envio_medidas()` (`evolution_go.py:577`) + uma chamada de teste para TESTE-A no canário |
| D3 | Qual fração das mensagens reais termina em pontuação final, termina em conectivo, ou é "dado curto" | 🔴 **não medido — exige ler texto, e esta preparação não leu.** É trabalho do BLOCO 0: script read-only aplicando **a função do motor** (`tracos_da_mensagem`) ao texto real, imprimindo **só contagens**. As faixas de intervalo (§3.1) já estão medidas e são a outra metade da calibragem |
| D4 | 🔴 **A causa do `wa_message_id` repetido entre corretoras** (104 de 134) | **o mais urgente.** Exige ler conteúdo de duas linhas pareadas, sob autorização, ou reconstruir o caminho de ingestão dos 5 observadores. **Antes de qualquer migração** (§3.6) |
| D5 | Se os **99** pares repetidos entre duas conversas REAIS somem quando a contraparte for única | rodar a contagem de §3.6 depois da M2 e comparar. Se não sumirem, há um segundo caminho de duplicação |
| D6 | Quantos turnos por dia o produto faz por corretora (base do custo da presença) | contagem em `attendance_transcripts` por dia e `company_id` |
| D7 | Se `_eco_do_dashboard` (janela de tempo) ainda é necessário depois do `wa_message_id` no pipeline | rodar os testes do espelho com a chave presente |
| D8 | Se a corretora quer mesmo o agente chamado `AutoBrokers` (o ativo) ou `Amanda` (o desativado) | 🧑 **caixa do Founder** — §3.8. Não é decisão do executor |

**Já respondido por esta preparação, e por isso saiu da lista:** as 174 fantasmas → 📊 **175**, 9 com par, 166 sem (§3.5) · colisão nome de agente × membro → 📊 **zero hoje** (§3.8) · existe corpus de rajadas? → 📊 **20.727** (§3.1).

**Nada disso bloqueia a escrita da SPEC.** Tudo isso é BLOCO 0 (AAA §5 ①: *"o executor REMEDE o que a SPEC afirma. O número dele vence"*).

---

## 8. Pendências que esta SPEC toca, por número

| pendência | estado hoje | o que esta SPEC faz |
|---|---|---|
| **P-PILOTO-13** | texto real (`PENDENCIAS.md:10532-10533`): *"174 conversas com `user_phone` de LID (106 AutoFleet, 68 Resulta), 10 com pausa humana presa; o `--vivo` está bloqueado por `ck_conversations_resolucao_motivo`… **Destrava:** migration acrescentando o valor, depois `--vivo`"*. 📊 **Hoje são 175** (106 AutoFleet, **69** Resulta), 10 com pausa, e o CHECK confirmado no banco sem `fantasma_lid` | **absorve**: migration M1 + `--vivo` com VERIFY + o índice que impede a **176ª** |
| **P-PILOTO-15** | 🔴 **texto real** (`PENDENCIAS.md:10538-10539`): *"pausa não protege conversa com `resolvido_em` preenchido; `pausar_ia` devolve False quando `resolvido_em` está preenchido e a pausa não limpa o campo"*. ⚠️ **Não é** "a ordem de `pausar_ia` × exceções" — essa é uma segunda coisa, medida hoje (§2.9) e sem pendência própria | **absorve as duas**: (a) a pausa passa a valer em conversa reaberta; (b) a exceção de teste deixa de vir antes do takeover |
| **novas, a abrir** | 🔴 `wa_message_id` repetido entre **corretoras** (§3.6) — candidato a P0 · ⚠️ PII em `conversations.human_handoff_reason` (§3.7) · `conversation_logs` só grava sucesso (§3.7) · `attendance_transcripts` sem UNIQUE em `message_id` · `conversations.agent_name` com `'Smith Agent'` como default (nome revogado, GLOSSARIO) | a primeira **pode parar a SPEC** (CLAUDE.md §10 item 4); as outras são pendência com dono e destrava |
| P-PILOTO-16, 17, 18 | citadas pelo diagnóstico §5 como "→001.2/001.1" | **reencontrar por número no BLOCO 0** e dar `FECHADA`/`CONTINUA`/`MORREU` (AAA §2). Não assumir que continuam abertas |
| P-PILOTO-01 | uma corretora trava a outra | **fora**: é a EXTRA-001.8. Esta SPEC só promete que a trava é **por conversa** e prova com o teste de paralelismo existente |
| P-264 | `tela_cega` com escritor e sem leitor | **fora**, mas é o precedente citado na §D: nenhum registro novo desta SPEC nasce sem leitor |

---

## 9. Regra de integridade deste research pack

Os números marcados 📊 nesta preparação têm data **13/09/2026** e a consulta/comando ao lado. O executor **remede** antes de usar: um número deste documento que não bata com o comando é defeito **do documento**, e a correção entra no relatório (AAA §0.4 — *"o juiz REPRODUZ por amostra: 3 números ao acaso por artefato"*).

⛔ Nenhum telefone, CPF, nome de segurado, placa, e-mail ou credencial foi impresso, gravado ou transportado nesta preparação. Os dois números de teste do Founder aparecem exclusivamente como **TESTE-A** e **TESTE-B**.
