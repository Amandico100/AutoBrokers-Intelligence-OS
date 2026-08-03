# SPEC-063 · Bloco 0 — a auditoria que vem antes do código

> **02/08/2026** · commit base `19d2d1f` (já em `origin/main`)
> Banco medido ao vivo · código lido linha a linha · serviços externos testados.
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)
>
> **Escopo ampliado:** além dos doze bloqueios da SPEC-063, esta auditoria
> responde a pergunta do Founder de 02/08 — *"uma corretora nova nasce
> completa?"*. As duas se tocam: o agente sem prompt da AutoFleet é P0 de
> atendimento **e** sintoma de provisionamento.

---

# Veredito em seis linhas

```
os doze bloqueios ............... 11 confirmados · 1 já resolvido (B7)
o que a SPEC erra ............... 4 correções de fato, nenhuma de direção
o que ela não previu ............ 6 acréscimos, um deles muda o Bloco C
a corretora nasce completa? ..... NÃO — e a falha é estrutural, não acidente
a InfoCap bloqueia a 063? ....... só a parte final. 80% é executável hoje
quantos blocos .................. DOIS
```

---

# PARTE A — Os doze bloqueios

## ✅ Confirmados, com prova

| # | Bloqueio | Prova medida |
|---|---|---|
| **B1** | agente errado responde o segurado | `langchain_service.py:199-210` — `.eq("is_active",True).order("created_at").limit(1)`, **sem filtro de papel**. Resulta: CORE de 21/06 **00:36** ativo; Saionara **04:45** desligada |
| **B2** | ternário morto | `pairing_orchestrator.py:493` — `None if purpose == "observer" else None`, literal |
| **B3** | `request_human_agent` não anexada | 📊 `tools_config = {}` nos 3 agentes de atendimento; `graph.py:245` só anexa se `human_handoff.enabled` |
| **B4** | ninguém é avisado | `human_handoff.py:87-99` — um `UPDATE`, zero import de envio |
| **B5** | tela e backend leem tabelas diferentes | 📊 `human_support_destinations`: só Amandus (2 linhas, 1 inativa duplicada). Resulta e AutoFleet vivem em `acionamento_profile` |
| **B6** | allowlist cala o agente | 📊 **`ATTENDANT_INBOUND_ALLOWLIST=5547988087463` ESTÁ PREENCHIDA em produção.** Só esse número é atendido; o resto é ignorado **em silêncio** |
| **B8** | buffer sem tenant | `message_buffer_service.py:36-38` — `f"whatsapp_buffer:{phone}"` |
| **B10** | duas corretoras, um grupo | 📊 `120363427334937446@g.us` em Resulta **e** AutoFleet |
| **B11** | cobrança pode sair pelo observador | `billing_collection.py:403-414` — `rank` põe `observer` em 2, mas `return rows[0]` devolve se for a única |
| **B12** | corretora sem agente responde por omissão | `webhook.py:562` e `:1044` chamam `attendance_observation_mode` (`bool(rows) and is_active is False`) → sem agente, `bool([])` = `False` → **cai no fluxo de IA** |

## ⚠️ B7 — **já resolvido.** Não é bloqueio.

📊 Testado agora contra o serviço em produção:

```
GET /server/ok → {"status":"ok","version":"0.7.2-autobrokers.1"}
```

**A imagem corrigida do fork está no ar.** O vazamento de pool que derrubaria
todas as corretoras ao parear uma **não existe hoje**. A SPEC pedia
"confirmar antes de parear" — confirmado, e o resultado é bom.

> **Vira teste, não trabalho:** o `/health` passa a exigir que a versão contenha
> `autobrokers`. Se um `latest` upstream voltar, o gate quebra.

---

# PARTE B — O que a SPEC erra

Nenhuma correção é de direção. Todas são de **fato**, e duas mudam o trabalho.

## ⚠️ 1. O caminho do `time.sleep` está errado (B9)

```
a SPEC diz .... backend/app/services/whatsapp/whatsapp_service.py:56
o arquivo é ... backend/app/services/whatsapp_service.py:56
```

📊 O defeito é real: `time.sleep(0.7)` e `time.sleep(1.2)`. **E há evidência de
que alguém já tropeçou nisso antes:** `portal_tool.py:216` traz o comentário
*"NÃO bloqueia o event loop (o `time.sleep` antigo travava o atendente
inteiro)"*. Foi corrigido lá e não aqui.

## ⚠️ 2. `send_to_client_guarded` **tem** chamador (Bloco E)

A SPEC afirma *"zero chamadores de produção"*. 📊 Medido: `platform_outbound.py:190`
o chama — é o **drenador da fila**.

**O defeito é outro, e mais específico:** `billing_collection.py:536` chama
`get_whatsapp_service().send_message` **direto**, pulando a fila. Não é que o
caminho não exista: é que a cobrança não entra nele.

## ⚠️ 3. Já existe metade de um governador (Bloco C) — **muda o trabalho**

A SPEC diz *"não existe limitação de taxa em lugar nenhum"* e manda construir do
zero. 📊 Medido em `platform_outbound.py`:

```
_QUEUE_KEY ......... fila persistente em Redis, por corretora
_BUSY_WINDOW_H = 2 . não escreve para quem está em conversa ativa
_RETRY_MIN_S ....... backoff de 2h
_MAX_ATTEMPTS = 12 . expira em ~24h e registra atividade
client_busy() ...... a guarda que impede atropelar conversa aberta
```

> **A fila existe, é persistente, tem retry e respeita conversa aberta.**
> O que falta é o **espaçamento entre destinatários**, os **tetos por
> hora/dia**, a **janela de horário** e a **parada de emergência**.

**Construir um segundo motor ao lado seria violar o CLAUDE.md §5.** O governador
**estende `platform_outbound`** — e o trabalho fica menor do que a SPEC supõe.

## ⚠️ 4. Faltam menos corredores do que a SPEC sugere (Bloco F)

📊 `corridor_playbooks.py` tem **11 playbooks**: Allianz residencial + Allianz,
Porto, HDI, Yelum, Tokio, Alfa, Azul, Bradesco, Mapfre e Zurich em auto.

Cruzando com a prioridade medida no acervo (cartas de auto):

```
Allianz 439 ✅   Yelum 276 ✅   Tokio 251 ✅   HDI 184 ✅
Youse 177 ❌     Porto 165 ✅   Bradesco 116 ✅   Mapfre 100 ✅
```

**Falta UM: a Youse.** Os outros dez existem — e nunca foram exercitados ponta a
ponta.

⚠️ **E há duas representações que discordam:** 📊 o código tem 11 corredores;
`corridor_templates` no banco tem **2**. A SPEC-063 F.1 diz que o código é a
autoridade — então a tabela é espelho parcial, e isso precisa ficar explícito.

---

# PARTE C — O que a SPEC não previu

## ➕ 1. A AutoFleet tem agente ativo sem prompt — e **não foi acidente**

📊 Medido:

```
corretora    papel        blueprint              prompt
Resulta      core         autobrokers-core-v1    650 chars
AutoFleet    core         autobrokers-core-v1        0   ← ATIVO
Amandus      core         core-v1                  7.914
```

**Mesmo blueprint. Mesmo caminho. Resultado diferente.** O template canônico tem
~714 caracteres; a Resulta ficou com 650 (bate, após substituição de variáveis);
a AutoFleet ficou com **zero**.

Com o defeito B1, é ele que responderia o segurado da AutoFleet: **um agente
ativo, sem uma linha de instrução, sem nenhuma trava.**

## ➕ 2. O handoff mente em todo caminho de falha

`human_handoff.py:109-126` — quando o `UPDATE` não acha a conversa **e** quando
estoura exceção, devolve *"Um atendente foi solicitado."*

**Sucesso declarado em cima de falha.** O Bloco B acrescenta a notificação; se
ela falhar, o segurado continua sendo informado de que alguém vem.

## ➕ 3. O handoff escreve sem filtro de tenant

`.update({...}).eq("session_id", …)` — **sem `company_id`**. CLAUDE.md §7 exige
o filtro no service justamente para não depender de o `session_id` ser único.

## ➕ 4. O CPF vaza pela TOOL, não só pelo prompt

`prompts.py` manda repassar CPF sem mascarar (é o P0 conhecido). **Mas
`infocap_tool.py:508/532/552` imprime `CPF/CNPJ: {doc}` inclusive no ramo
`client_facing`** — o do segurado. Consertar só o prompt deixa o vazamento.

## ➕ 5. Os playbooks de conduta não têm consumidor em runtime (Bloco G)

📊 `conduct_playbooks` é lido por 5 arquivos — `admin_atlas`, `agent_memory`,
`attendance_distiller`, `playbook_gate`, `prompt_optimizer`. **Nenhum deles é do
grafo do agente.** A máquina de qualidade roda e ninguém consome.

## ➕ 6. **A corretora NÃO nasce completa** — a resposta à pergunta do Founder

### O que `provisionTenant` faz

```
✓ 1 agente Core (ativo) a partir de blueprint canônico
✓ 1 agente de atendimento (INATIVO) a partir de blueprint canônico
```

### O que ele explicitamente NÃO faz

O próprio comentário do arquivo declara: *"Não instala corredores/auxiliares
(ficam globais/galeria)"*.

### E o que está medido

📊 Três corretoras, **três estados diferentes**:

| | Amandus | AutoFleet | Resulta |
|---|---:|---:|---:|
| agentes | 2 | 2 | 2 |
| **sem prompt** | 0 | **1** | 0 |
| perfis de briefing | 2 | 2 | 2 |
| **config de memória** | **0** | **0** | **0** |
| auxiliares instalados | 2 | **0** | 1 |
| conexões | 1 | **0** | 3 |
| **entitlements** | **0** | **0** | **0** |
| **corredores** | **0** | **0** | 2 |
| destino de suporte | 2 | **0** | **0** |
| memórias da corretora | 0 | 0 | 0 |

**Nada é uniforme exceto agentes e perfis de briefing.**

### As três falhas estruturais

**a) Uma vez criado, o agente nunca recebe melhoria.**
`ensureAgentByRole` faz `if (existing?.id) return { action: 'exists' }` — e
**não atualiza**. Melhorar o blueprint do AutoBrokers **não chega** a nenhuma
corretora existente.

**b) O mecanismo que faria isso existe e nunca funcionou.**
📊 `agent_blueprint_releases`: 2 publicadas. `agent_release_rollouts`: **1, com
status `rolled_back`**. O único rollout já tentado foi revertido.

**c) O provisionamento pode produzir agente vazio, e nada percebe.**
A AutoFleet prova. Não há verificação pós-provisionamento.

> **Isto responde o Founder com precisão:** hoje a corretora nasce com **duas
> peças de nove**, e o que o AutoBrokers melhora depois **não chega em ninguém**.

---

# PARTE D — A InfoCap bloqueia a SPEC-063?

**Só o final. 📊 A maior parte é executável hoje.**

```
BLOCO A  quem atende ................. NÃO depende
BLOCO B  handoff que chega ........... NÃO depende
BLOCO H  higiene (buffer, sleep) ..... NÃO depende
BLOCO D  segundo número .............. NÃO depende
BLOCO C  governador de envio ......... NÃO depende
BLOCO E  cobrança que conversa ....... NÃO depende
BLOCO G  conduta no prompt ........... NÃO depende
BLOCO F  corredores .................. escrever e testar em modo teste: NÃO
                                       ACIONAR de verdade: SIM, depende
```

O corredor precisa confirmar apólice antes de acionar, e a única fonte é a
InfoCap. **Mas `DISPATCH_FINALIZE_MODE=test` percorre o fluxo inteiro e cancela
antes de abrir** — dá para escrever, testar e provar sem ela.

---

# PARTE E — O plano: DOIS blocos

## 🔒 BLOCO 1 — Ninguém responde errado, e ninguém fica sem resposta

**Tudo que impede incidente. Nenhuma dependência externa.**

```
A · quem atende          resolver por PAPEL, não por antiguidade
                         matar o ternário · preservar vínculo ao re-parear
                         ausência de agente = SILÊNCIO (inverter B12)
                         papel errado = recusa registrada
                         + o CPF na TOOL, não só no prompt

B · handoff que chega    anexar a ferramenta aos 3 agentes
                         notificar de verdade, pelo caminho que já existe
                         backend passa a ler o que a UI escreve
                         UMA corretora, UM destino (constraint + teste)
                         + falha NUNCA afirma sucesso
                         + filtro de company_id no UPDATE
                         dossiê + prazo de volta para a IA

H · higiene              buffer com tenant na chave
                         time.sleep → await (caminho corrigido)
                         as 6 variáveis no .env.example + /health
                         Evolution Go: virar TESTE (já está verde)

D · segundo número       observer NUNCA é canal de saída — proibição, não
                         prioridade · card com três posições

P · provisionamento      a corretora nasce COMPLETA:
                         agente nunca nasce sem prompt (verificação pós-criação)
                         reaplicar blueprint em quem já existe
                         herdar o global: auxiliares, memórias, corredores,
                         config de memória, entitlements
                         + consertar a AutoFleet
```

**Por que provisionamento entra aqui:** o agente sem prompt é P0 de atendimento.
Consertar só a AutoFleet à mão deixaria a causa viva — a próxima corretora
nasceria igual.

**Gate:** o agente pode ser ligado sem risco de vazamento, sem promessa falsa, e
qualquer corretora nova nasce idêntica às outras.

## ⚙️ BLOCO 2 — O trabalho sai com segurança

```
C · governador           ESTENDE platform_outbound (não cria fila nova):
                         espaçamento aleatório · tetos · janela · domingo
                         parada de emergência · registro de cinco campos

E · cobrança conversa    cobrança passa a usar send_to_client_guarded
                         agente de cobrança próprio · skill de cobrança
                         vínculo de campanha na conversa

F · corredores           Youse (o único que falta) + provar os 10 existentes
                         em DISPATCH_FINALIZE_MODE=test
                         fechar o ciclo: avisa · acompanha · CONFIRMA
                         COMO-CRIAR-UM-CORREDOR.md

G · conduta no prompt    os 16 playbooks chegam ao turno, com teto e portão
```

**Gate:** cobrança sai espaçada pelo número certo, quem responde ao boleto sabe
que houve boleto, e o corredor percorre sem acionar.

---

# PARTE F — 🚫 Retirado

**Nada.** Nenhuma proposta da SPEC-063 se mostrou inválida. **B7 sai da lista
de trabalho** porque já está resolvido — vira teste de regressão.

---

# PARTE G — O que vai quebrar

| Mudança | Quem consome | Mitigação |
|---|---|---|
| ligar `human_handoff` nos 3 agentes | os agentes | estão desligados; vale quando forem ligados |
| inverter B12 (ausência = silêncio) | webhook | fail-closed é mais seguro que o atual |
| reaplicar blueprint em agente existente | Amandus tem prompt de 7.914 chars, editado à mão | **preservar customização**: só preenche o que está vazio, ou versiona antes |
| governador atrasa cobrança | fila existente | teto configurável + parada de emergência |
| provisionar o que faltava | 3 corretoras | idempotente; nada nasce ligado |

> ⚠️ **O risco mais real é o do blueprint.** A Amandus tem um prompt de 7.914
> caracteres — muito maior que o template. **Se o reaplicar sobrescrever, perde-se
> trabalho.** A regra tem de ser: preencher o vazio, versionar antes de tocar no
> preenchido, e nunca sobrescrever sem registro.

---

*Auditoria feita sem alterar nenhum dado. Nenhuma migration aplicada. Nenhuma
credencial exibida.*
