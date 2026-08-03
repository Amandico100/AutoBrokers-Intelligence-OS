# SPEC-063 — Relatório de execução

> **03/08/2026** · branch `feat/spec063-atendimento-canais` → `origin/main`
> commit inicial `c28daff` · commit final `66c2519` · **10 commits**
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## Gate final

```
suíte de testes ............... ✅  122 verdes · 0 vermelhos   (era 116)
tsc --noEmit .................. ✅  exit 0
tabela de rotas ............... ✅  285 rotas, getSortedRoutes sem exceção
migrations aplicadas .......... 4, todas com VERIFY verde
produção ...................... ✅  web 200 · API healthy
motor paralelo criado ......... nenhum
```

**Testes acrescentados: 7 arquivos.** A suíte foi de 116 para 122.

---

## O que mudou, em uma tela

| Antes | Depois |
|---|---|
| quem responde o segurado é *o agente mais antigo* — o **core**, que entrega CPF sem mascarar | **papel exigido**; sem agente de atendimento, **silêncio** |
| CPF vazava pelo prompt **e** pela tool | corte no lugar que **escreve**: o segurado vê `•••8901` |
| handoff só mudava um status, e **dizia sucesso quando falhava** | avisa de verdade, com dossiê — e a resposta diz o que **aconteceu** |
| duas corretoras no mesmo grupo de suporte | **recusa** enviar dossiê para destino compartilhado |
| buffer com chave `{telefone}` — conversas de corretoras **fundidas** | chave com tenant |
| webhook legado com auth `disabled` por padrão | **nasce fechado** |
| observer era escolhido como canal de saída quando era o único | **proibição**, não prioridade |
| AutoFleet com core **ativo e mudo** (0 caracteres) | 638 caracteres, e uma **view** que impede repetir |
| memória do atendimento = janela de 60 mensagens | **ficha persistida** — não repergunta |
| 12 playbooks destilados de 297 atendimentos, órfãos | **chegam ao turno**, com teto de 2.600 caracteres |
| 100 mensagens em rajada na cobrança | **governador**: 4–8 min, tetos, janela, domingo, freio |
| acionamento só no Redis, TTL 6h | **Work Run** — sobrevive a restart, e o órfão grita |
| a tela dizia *"o atendente já aciona por eles"* | diz a verdade |

---

## Os blocos

### 🔒 A · Quem responde o segurado

Três coisas tinham de dar errado juntas, e as três davam. `pairing_orchestrator`
gravava `"agent_id": None if purpose == "observer" else None` — um ternário que
devolve `None` nos **dois** ramos. Sem dono, o motor pegava o agente ativo mais
antigo; 📊 nas três corretoras, o **core**.

Quatro correções, em camadas independentes: o seletor **exige papel** e recusa
papel diferente mesmo com id explícito; o portão virou **positivo** (só fala quem
prova ter atendente ligado); o motor recebe `required_role="attendance"`; o
pareamento grava o dono.

**E o CPF vazava por dois caminhos.** O tool já sabia distinguir o público, mas
`_summarize` e `_summarize_detail` são `@staticmethod` e nunca receberam essa
informação. **Quem consertasse só o prompt acharia que tinha resolvido.**

### 📨 B · O handoff que chega

📊 A ferramenta só fazia `UPDATE conversations SET status='HUMAN_REQUESTED'`. E
devolvia *"Um atendente foi solicitado"* **também quando falhava** — falha
declarando sucesso apaga o rastro que levaria alguém a consertar.

Existiam **duas verdades que não se falavam**: a UI gravava em
`human_support_destinations`, o backend lia `acionamento_profile`, e 📊 a tabela
da UI não aparecia **uma vez** em `backend/app/`.

Um resolvedor canônico agora lê a tabela da UI primeiro e **recusa destino
compartilhado**. Não usei constraint `UNIQUE` de propósito: ela rejeitaria a
segunda linha e a corretora ficaria sem destino sem ninguém entender por quê.
**A view mostra, o código recusa, a pessoa decide de quem é o grupo.**

### 🧹 H · Higiene

Buffer com tenant na chave · webhook legado nasce fechado (📊 seguro: `ZAPI_*`
está vazio e o provider é `evolution-go`) · `time.sleep` fora do caminho async ·
`observer_number` deixa de colidir · **10 variáveis** que decidem envio real
documentadas com o padrão seguro escrito ao lado.

### 🔇 D · O observador nunca fala

`observer` caía no rank 2 — *"por último"*. E **por último vira o escolhido
quando é o único ativo**, que era o caso de Amandus e AutoFleet.

### 🏗️ P · A corretora nasce completa

`ensureAgentByRole` devolvia `{action:'exists'}` e **nunca atualizava**. E o
provisionamento podia gerar prompt vazio sem ninguém perceber.

O portão mede o prompt **e a personalização em separado** — a casca de ~560
caracteres de regras passaria em "não vazio" e continuaria muda. Releitura
pós-insert: se vier vazio do banco, o agente nasce **desligado**.

E a herança para quem já existe: **vazio → preenche · idêntico → nada ·
divergente → preserva · autorizado → versiona antes, confirma o hash, só então
grava.** 📊 Os 7.914 caracteres da Amandus nunca saem do índice 0 do histórico.

### 📡 V · O canal que mentia

📊 Três integrações diziam `connected` com `last_seen_at` congelado há 4 dias. A
causa não era só falta de vigia: `last_seen_at` só era escrito em
`connection.update`, um evento de **transição** que não chega em canal parado —
silêncio e saúde eram indistinguíveis.

O heartbeat **confirma antes de contestar**. E quando a sonda não responde,
grava `unknown`, não `disconnected`: não medimos queda nenhuma, só perdemos o
direito de dizer "Conectado". **Afirmar queda não medida é o mesmo pecado do
outro lado.**

### 📋 S · A ficha do atendimento

📊 `grep -niE "fase|phase|etapa|stage|slot" backend/app/agents/*.py` → **ZERO**.
A memória do que já foi perguntado **era a janela de 60 mensagens**, e o próprio
código registra que isso **já quebrou**: o agente repediu o CPF do mesmo cliente.

```
o modelo declara os slots na tool  →  a ficha GRAVA
        o turno seguinte MOSTRA de volta  →  não repergunta
```

**Merge aditivo** (turno que omite campo não apaga o que o cliente disse) e
**fase derivada, nunca declarada** (o teste prova que o modelo não consegue se
dizer "acionado" sem prova de envio). E "resolvido" deixou de ser cronômetro de
48h.

Mora em `conversations`, não em Work Run: o atendimento não é execução, é
conversa. Criar tabela de execução seria o erro do `corridor_runs` — 📊 50
execuções abandonadas, hoje no `graveyard`.

### 🎧 G · A conduta chega ao turno

📊 16 playbooks (12 ativos, ~97 KB) destilados por `claude-opus-5` de **297
atendimentos humanos reais**. Lidos por: o juiz que aprova, o otimizador, o
destilador e duas telas de admin. `grep conduct_playbook graph.py` → **zero**.

Agora entram, com **teto de 2.600 caracteres** e corte em fim de linha — conduta
cortada no meio de uma orientação é pior que conduta ausente.

### 🚦 C · O governador de envio

📊 `billing_collection` disparava 50 × 2 = **100 mensagens em rajada**. Um número
novo fazendo isso é banido, e **quem perde o canal é a corretora**.

**Estende** `platform_outbound` (fila, backoff e drenador já existiam).
Espaçamento 4–8 min com segundos nunca redondos, tetos, janela 08:00–20:00,
domingo bloqueado, freio por corretora.

**Só mensagem fria passa.** Provado com domingo + freio + teto estourado + Redis
mudo simultâneos: a quente sai.

📊 E a aritmética que a SPEC não fechava, agora escrita no código: 12/h × 12h =
144, logo **o teto de 200 do maduro é inalcançável** — o horário é sempre a
restrição ativa.

### ⚓ E · O acionamento sobrevive ao Redis

A única máquina de estados real do produto vivia só em Redis com TTL de 6h. Um
restart perdia um acionamento **em voo**, sem reconciliação.

Agora cada fase vira checkpoint em `work_runs`/`work_steps`/`work_events` —
SPEC-055, zero tabela nova. **A reconciliação restaura menos do que poderia, de
propósito:** só `monitoring` volta ao cache. `ura` e `human_phase` viram
`needs_human` com motivo — restaurá-las seria mandar mensagem real num
atendimento que andou sem nós.

`blocked_gate` removido: 📊 uma única ocorrência no repo, a própria declaração.

---

## Migrations aplicadas

| # | O que fez | VERIFY |
|---|---|---|
| `20260803_01` | destino de suporte único + view de conflito | ✅ conflito visível |
| `20260803_02` | memória, entitlements, view de agentes mudos | ✅ 0→2 e 0→38 |
| `20260803_02b` | AutoFleet deixa de ser muda | ✅ 0→638 chars |
| `20260803_04` | a ficha do atendimento | ✅ 3 colunas |

📊 **Canário:** Amandus 7.914 chars **intacto** · Resulta 650 **intacto** ·
AutoFleet 0 → 638 · agentes mudos 1 → **zero**.

---

## O que ficou fora, e por quê

```
🧑 InfoCap liberada          telefonema — bloqueia CONFIRMAR apólice
🧑 parear o WhatsApp         ação física
🧑 ativar o agente           um clique, depois do gate
🧑 separar o grupo de suporte  Resulta e AutoFleet dividem um; o código RECUSA
                             enviar até separar (é fail-closed, não bug)

🤖 varredura periódica de órfãos  hoje dispara 1x por processo, no primeiro
                                  cache-miss. Falta 1 linha no laço de manutenção
🤖 o grito do órfão não vai por WhatsApp  vai para work_events e Atividades
🤖 outros caminhos escrevem agent_system_prompt sem o portão
   (blueprint-studio-store, release-rollout-store, tenant-agent-store)
🤖 `unknown` não está em ESTADOS_RUINS — canal demovido não gera sinal
🤖 o freio de emergência não tem botão na tela
🤖 3 vars do heartbeat fora do .env.example
🤖 migration 20260803_06 (índice do Work Run) escrita e NÃO aplicada
   — usa CONCURRENTLY, precisa rodar avulso
```

---

## Riscos remanescentes

| Risco | Estado |
|---|---|
| `INSURER_DISPATCH_LIVE=true` — o portão de envio real está **aberto** | 🧑 o que segura é `DISPATCH_FINALIZE_MODE=test` + allowlist + agentes off |
| Nenhuma trava de envio **por corretora ou por corredor** | 🤖 próxima SPEC |
| Nada disto rodou contra um atendimento real | 🧑 o primeiro canário é o VERIFY que falta |
| `CARTOGRAPHER_MODE=1` — o Cartógrafo envia WhatsApp real a seguradoras | 🧑 decisão |

---

## Declaração

**Nenhum motor paralelo foi criado.** O governador estende `platform_outbound`;
o acionamento passou a morar em `work_runs`, onde a SPEC-055 já mandava; a ficha
mora em `conversations`, não numa tabela de execução nova; o heartbeat usa o
scheduler que já existia (`AsyncIOScheduler` continua aparecendo **uma vez** em
todo `backend/app`); e a fachada `outbound_governor` não tem lógica — há teste
que falha se alguém escrever um `def` nela.

📊 Todos os números foram medidos contra o banco de produção
`dcajcvlzcjbmyapmklil` em 02 e 03/08/2026.
