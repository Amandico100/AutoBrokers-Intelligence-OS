# SPEC-086 — O ATENDIMENTO CONTINUA ATÉ O FIM
## Continuidade Humano ↔ IA, Durable Waits, Follow-up e Resume Pack

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline observado durante a redação:** `main` em `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Branch sugerida quando for executar:** `feat/spec086-o-atendimento-continua-ate-o-fim`  
**Autoridades preservadas:** SPEC-053, SPEC-055, SPEC-063, SPEC-083/084.x, SPEC-085 e Protocolo AutoBrokers AAA v9  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Primeiro domínio de implantação:** Atendimento / Assistência  
**Contrato projetado para reuso futuro:** Sinistro, Renovação, Cobrança, Pós-venda e outros Work Runs  
**Research Pack:** `SPEC-086-o-atendimento-continua-ate-o-fim-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Um atendimento pode passar de IA para humano, de humano para IA, esperar cliente, seguradora, documento ou decisão, atravessar horas/restart e continuar exatamente do ponto seguro — sem duas pessoas falarem ao mesmo tempo, sem mensagem de follow-up fora de contexto e sem o segurado virar problema de ninguém.**

Ao final desta SPEC, handoff deixa de significar apenas:

```text
“a IA chamou alguém”
```

e passa a significar:

```text
TRABALHO COM DONO
+
ESTADO DURÁVEL
+
CONTEXTO RECONSTRUÍVEL
+
ESPERA EXPLÍCITA
+
RETOMADA SEGURA
+
FOLLOW-UP GOVERNADO
+
FECHO VERDADEIRO
```

---

# 0.1 DECISÕES DO FOUNDER JÁ APROVADAS

Estas decisões entram como requisitos:

1. **Hard possession lock por conversa/recurso.**  
   Quando um humano assume uma conversa, a IA deixa de enviar naquela conversa até devolução explícita. Outras conversas continuam normalmente.

2. **Resume Pack é objeto canônico estruturado.**  
   A versão legível é renderização sobre dados estruturados; não é um resumo solto criado por LLM.

3. **Follow-up é decidido por policy + state machine.**  
   A LLM pode decidir COMO redigir dentro das regras. Não decide QUANDO, PARA QUEM nem POR QUÊ enviar.

4. **Política oficial AutoBrokers + override seguro por corretora.**  
   A corretora personaliza dentro de limites governados; não precisa inventar tudo do zero.

5. **Atendimento/Assistência primeiro, contrato genérico desde o início.**

6. **Humano da seguradora no meio do acionamento deve ser suportado.**  
   Preferência: funcionário da corretora consegue agir pela interface AutoBrokers quando o canal estiver homologado; fallback explícito para o WhatsApp original quando necessário.

7. **Não criar outro runtime, scheduler ou máquina universal concorrente.**

---

# 0.2 O QUE ESTA SPEC NÃO É

Esta SPEC NÃO é:

- uma reescrita da SPEC-085;
- uma nova Central de Agentes;
- um novo CRM;
- a fila/Kanban completa da SPEC-097;
- a Channel Fabric completa da SPEC-099;
- um “agente de follow-up” autônomo;
- um segundo Work OS;
- Temporal dentro do AutoBrokers;
- um novo banco de memória;
- um novo motor de acionamento;
- uma desculpa para refatorar todo Atendimento;
- uma implantação de sinistros autônomos;
- um sistema que força a IA a reassumir depois de humano responder;
- um mecanismo de bypass das regras do WhatsApp/Meta.

---

# 1. POR QUE ESTA SPEC EXISTE

## 1.1 A SPEC-085 resolveu “o travamento fica visível”

A 085 entregou uma base importante:

- travamento durável em `work_runs`;
- `work_steps.output_redacted`;
- `work_runs.unblock_state`;
- `owner_user_id`;
- timeline via `work_events`;
- tela “Precisa de você”;
- `assumir` atômico;
- `arquivar` com motivo;
- dossiê humano;
- watchdog de handoff;
- mensagens honestas ao segurado;
- distinção entre destino ausente/recusado/falha de envio;
- re-alerta de casos abandonados.

Isso deve ser REUSADO.

## 1.2 Mas “assumir” ainda não significa “continuar”

No baseline atual, a ação de um travamento possui basicamente:

```text
travado
→ assumido_por_humano
→ resolvido / abandonado
```

Isso prova posse do travamento.

Não prova:

- o que o humano recebeu;
- qual pergunta precisa responder;
- qual slot já foi coletado;
- qual side effect já aconteceu;
- como a IA recebe de volta o que o humano fez;
- qual checkpoint deve ser retomado;
- se uma mensagem chegou enquanto o humano estava com o caso;
- se a IA que estava “em voo” ainda pode enviar uma mensagem antiga;
- como o mesmo padrão funciona numa intervenção temporária.

## 1.3 A conversa já possui claim, mas `release` não é `resume`

Desde a SPEC-017, `conversations` possui:

```text
claimed_by
claimed_by_name
claimed_at
```

e o dashboard suporta:

```text
claim
release
close
send
```

O `claim` é atômico e `send` humano auto-claim.

Além disso, mensagem manual `fromMe` pode colocar aquela conversa em `HUMAN_REQUESTED`, e testes já guardam:

> uma intervenção humana pausa aquela conversa e NÃO desliga o agente nas outras.

Excelente.

Porém o `release` atual:

- solta o claim;
- volta à fila humana quando há handoff aberto;
- ou volta para `open`.

Ele NÃO significa:

> “o humano terminou sua contribuição; reconcilie o que aconteceu e retome o mesmo Work Run do checkpoint seguro”.

A SPEC-086 cria essa semântica.

---

# 2. O PROBLEMA DE PRODUTO

Em Atendimento real existem pelo menos seis tipos de espera:

```text
1. esperando o SEGURADO responder
2. esperando a SEGURADORA responder
3. esperando um DOCUMENTO
4. esperando uma CONFIRMAÇÃO
5. esperando um HUMANO DA CORRETORA
6. esperando o CANAL permitir/entregar uma mensagem
```

Hoje esses estados aparecem espalhados em:

- status de conversation;
- state do acionamento;
- Redis;
- timers/watchdogs;
- last message;
- handoff reason;
- lógica local de cada componente.

Quando a espera não é objeto de primeira classe, o sistema comete erros como:

```text
está esperando a SEGURADORA
↓
manda “ainda precisa de ajuda?” ao SEGURADO

humano assumiu
↓
timer antigo dispara
↓
IA manda mensagem

cliente respondeu
↓
timer antigo continua vivo
↓
mensagem chega depois da resposta

humano resolveu no celular
↓
IA não sabe
↓
começa do zero ou mantém caso aberto

humano devolveu
↓
release muda status
↓
mas ninguém sabe de qual passo retomar
```

A SPEC-086 existe para impedir essa classe inteira.

---

# 3. O PRINCÍPIO MAIS IMPORTANTE

> ## POSSE E ESPERA SÃO EIXOS DIFERENTES.

Não criar um enum gigantesco:

```text
HUMAN_WAITING_INSURER_AFTER_FIRST_FOLLOWUP...
```

Separar:

```text
QUEM CONTROLA?
+
QUEM/QUAL EVENTO ESTAMOS ESPERANDO?
+
QUAL É O ESTADO DO WORK RUN?
```

Exemplo:

```text
control = HUMAN
wait = INSURER
work_run = running
```

ou:

```text
control = AI_PAUSED_FOR_REVIEW
wait = BROKER_HUMAN
work_run = waiting_input
```

Essa separação evita explosão de estados.

---

# 4. AS DUAS FORMAS DE INTERVENÇÃO HUMANA

A palavra “handoff” hoje mistura duas situações diferentes.

A partir desta SPEC existem dois contratos.

## 4.1 HUMAN REVIEW — humano contribui, IA continua

```text
IA está conduzindo
↓
falta decisão / informação / ação humana
↓
IA PAUSA
↓
Resume Pack + pergunta objetiva
↓
humano responde
↓
resposta entra no mesmo Work Run
↓
IA RETOMA
```

O humano NÃO vira dono permanente da conversa.

Casos:

- “A seguradora perguntou se o carro está em local seguro; confirme.”
- “Aprovar esta exceção?”
- “Qual endereço deve ser usado?”
- “O atendente da seguradora pediu uma informação não inferível.”
- “Revise esta resposta antes de eu enviar.”

## 4.2 HUMAN TAKEOVER — humano assume, IA para

```text
IA conduz
↓
humano assume
↓
HARD LOCK
↓
só o humano pode falar naquele recurso
↓
humano resolve
ou
humano devolve explicitamente
```

Casos:

- segurado pediu pessoa;
- sinistro;
- negociação;
- insurer specialist exige conversa livre;
- situação de risco;
- humano detectou que a IA está errando;
- operador decidiu assumir.

## 4.3 Não confundir os dois

Botão/ação deve ser explícito:

```text
[Responder e deixar a IA continuar]
[Assumir este atendimento]
```

Nunca um botão ambíguo “Handoff”.

---

# 5. AUTORIDADES — NENHUMA NOVA ILHA

| Responsabilidade | Autoridade |
|---|---|
| execução durável | `work_runs` |
| checkpoint do trabalho | `work_steps` + mecanismo atual |
| timeline | `work_events` |
| efeitos externos | `work_effects` / seam canônica existente |
| conversa com segurado | `conversations` + `messages` |
| quem humano assumiu | `claimed_by` |
| estado do acionamento | motor atual + Work Run do acionamento |
| estado cognitivo Smith | LangGraph checkpointer |
| fila/transporte | Redis + Work Queue existentes |
| segredos | Vault |
| Resume Pack | DERIVADO das autoridades acima |
| wait | novo objeto subordinado ao Work Run, não novo runtime |

---

# 6. CONTROLE DE CONVERSA — HARD POSSESSION LOCK

## 6.1 Problema da implementação somente por `status`

Um `status=HUMAN_REQUESTED` impede novas decisões do agente em vários caminhos.

Mas não fecha esta corrida:

```text
T0 IA gera texto
T1 humano clica ASSUMIR
T2 IA que já tinha o texto pronto envia
```

No T2:

- o estado pode já dizer “humano”;
- mas o processo velho ainda possui trabalho local.

Isso é split-brain de comunicação.

## 6.2 Fencing / Control Epoch

Adicionar à autoridade de conversa, nomes finais decididos no warm-up:

```text
control_mode
control_epoch
control_updated_at
control_reason
```

Proposta de `control_mode`:

```text
AI
AI_REVIEW_PAUSED
HUMAN_QUEUE
HUMAN
```

`closed` continua sendo lifecycle, não control mode.

## 6.3 Control Epoch

`control_epoch` é inteiro monotônico.

Toda transição de controle incrementa:

```text
AI epoch 12
↓ humano assume
HUMAN epoch 13
↓ humano devolve
AI epoch 14
```

## 6.4 Regra do outbound

Todo side effect de mensagem gerado pela IA precisa possuir:

```text
conversation_id
expected_control_epoch
actor_type = ai
```

e revalidar IMEDIATAMENTE ANTES de chamar o provider:

```text
control_mode == AI
AND
control_epoch == expected_control_epoch
```

Falhou:

```text
STALE_CONTROL
```

Mensagem NÃO é enviada.

## 6.5 Por que não basta ler antes

Proibido:

```text
ler owner
↓
gerar mensagem por 8s
↓
enviar
```

A verificação precisa ocorrer na borda do efeito.

## 6.6 Envio humano

Humano só envia se:

```text
control_mode == HUMAN
AND
claimed_by == current_user
AND
epoch atual corresponde
```

O `send` atual que auto-claim deve migrar para esse contrato.

## 6.7 Queue

`HUMAN_QUEUE` significa:

```text
IA pediu humano
ninguém é dono ainda
IA NÃO envia conteúdo operacional
```

Mensagens de holding autorizadas pelo sistema podem existir, mas passam por política explícita e não “reativam” a IA.

---

# 7. CONTROLE DO WORK RUN

Conversa e execução são recursos relacionados, mas diferentes.

Exemplo:

- humano pode assumir a conversa com a SEGURADORA;
- o customer-facing assistant pode continuar apenas enviando updates autorizados ao segurado.

Portanto o Work Run também precisa de controle executável.

Preferência expand-only:

```text
execution_control_mode:
    AI
    AI_REVIEW_PAUSED
    HUMAN
    SYSTEM_PAUSED

execution_control_epoch bigint
```

`owner_user_id` continua identificando humano.

## 7.1 Não duplicar status

`work_runs.status` continua lifecycle:

```text
queued
running
waiting_approval
...
completed
failed
```

`execution_control_mode` responde apenas:

> **quem pode avançar a execução?**

---

# 8. TRANSIÇÃO ATÔMICA

Quando uma ação muda conversa + run:

```text
takeover
return_to_ai
submit_review
```

não fazer dois UPDATE independentes.

Implementar RPC/transaction canônica equivalente:

```text
attendance_takeover(...)
attendance_return_to_ai(...)
attendance_submit_human_input(...)
```

A implementação final pode ter nomes diferentes.

Garantias:

- tenant-scoped;
- expected epoch;
- expected current mode;
- first writer wins;
- atualiza conversa;
- atualiza run quando vinculado;
- incrementa epoch;
- grava `work_events`;
- devolve novo estado.

Duas pessoas competindo:

```text
1 vence
1 recebe 409/CONFLICT
```

---

# 9. RESUME PACK — O OBJETO CANÔNICO

## 9.1 O que ele é

Resume Pack é:

> **a representação estruturada do ponto em que o trabalho está, feita para outro ator continuar sem reler a história inteira.**

Não é uma nova fonte de verdade.

É DERIVADO.

## 9.2 Fontes

Conforme o caso:

```text
conversations
messages
work_runs
work_steps
work_events
dispatch snapshot
policy/customer/policy refs
Atlas/playbook refs
observed insurer messages
confirmed side effects
```

## 9.3 Schema conceitual

```json
{
  "version": "1.0",
  "case_ref": {
    "company_id": "...",
    "conversation_id": "...",
    "work_run_id": "...",
    "insurer_session_ref": "..."
  },
  "insurance": {
    "insurer": "allianz",
    "line": "residencial",
    "service": "maquina_de_lavar",
    "policy_ref": "...",
    "playbook_ref": "..."
  },
  "progress": {
    "workflow": "acionamento.seguradora",
    "phase": "human_phase",
    "current_step": "...",
    "last_safe_checkpoint": "..."
  },
  "control": {
    "mode": "AI_REVIEW_PAUSED",
    "epoch": 14,
    "owner_user_ref": null
  },
  "wait": {
    "kind": "BROKER_HUMAN",
    "reason_code": "INSURER_ASKED_FREEFORM",
    "started_at": "...",
    "due_at": "..."
  },
  "facts_known": [],
  "missing_facts": [],
  "customer_context": [],
  "insurer_context": [],
  "effects_completed": [],
  "open_questions": [],
  "recommended_next_actions": [],
  "resume_conditions": [],
  "source_fingerprint": "..."
}
```

## 9.4 PII

Resume Pack NÃO vira um novo cofre de PII.

Preferência:

```text
pack persistido / evento:
  valores redigidos + refs

valor sensível completo:
  continua na autoridade original
  é resolvido JIT quando uma ação autorizada realmente precisa
```

Exemplo:

```text
CPF: ***.***.***-42
source_ref: customer_profile/cpf
available: true
```

O backend autorizado pode resolver o valor real no momento de responder à seguradora.

## 9.5 Duas renderizações

```text
ResumePackRuntime
```

- refs;
- estrutura;
- campos;
- conditions;
- usado pelo executor.

```text
ResumePackOperator
```

- linguagem humana;
- redigido;
- “o que aconteceu”;
- “o que falta”;
- “o que fazer agora”.

A LLM pode ajudar a redigir a narrativa do Operator Pack.

Ela NÃO inventa fatos.

## 9.6 Fingerprint

Cada pack recebe fingerprint das fontes/estado.

Ao devolver para a IA:

- construir pack fresco;
- comparar;
- se houve nova mensagem/efeito:
  - reconciliar;
  - nunca retomar assumindo snapshot antigo.

---

# 10. O RESUME PACK NA TELA

O operador deve entender em segundos:

```text
🔧 ASSISTÊNCIA · GUINCHO

Cliente
João ... · Porto · Auto

Onde parou
Especialista da seguradora entrou na conversa.

Já sabemos
✓ placa
✓ local
✓ telefone
✓ destino
✓ situação de segurança

A seguradora perguntou
“Há alguém acompanhando o veículo no local?”

Sugestão do AutoBrokers
“Sim, o segurado está no local.”

[Responder e deixar a IA continuar]
[Assumir o acionamento]
```

Se alguma afirmação da sugestão não tiver fonte:

```text
NÃO sugerir como fato.
```

---

# 11. O HUMANO DA SEGURADORA NO MEIO DO ACIONAMENTO

O estado `human_phase` já existe no acionamento.

Esta SPEC transforma isso em experiência operacional.

## 11.1 Primeiro: automação continua quando seguro

Se o especialista humano da seguradora fizer pergunta que:

- é claramente identificada;
- tem resposta proveniente de fato estruturado;
- não envolve negociação/interpretação;
- está dentro das regras de segurança;

o motor pode continuar conforme comportamento atual.

## 11.2 Human Review

Quando faltar dado/certeza:

```text
insurer human asks
↓
AI_REVIEW_PAUSED
↓
Resume Pack
↓
humano da corretora recebe pergunta
↓
opções:
  RESPONDER E DEVOLVER
  ASSUMIR
```

## 11.3 Responder e devolver

O humano fornece input estruturado.

Exemplo:

```json
{
  "action": "submit_and_resume",
  "answer": "Sim",
  "fields": {
    "acompanhante_no_local": true
  }
}
```

A resposta:

1. é validada;
2. grava evento;
3. atualiza estado canônico;
4. passa pelo outbound gate;
5. é enviada ao especialista da seguradora quando canal homologado;
6. IA retoma.

## 11.4 Assumir acionamento

```text
execution_control_mode = HUMAN
owner_user_id = pessoa
epoch++
```

A IA:

- observa;
- grava;
- pode montar sugestões privadas;
- NÃO envia à seguradora naquele recurso.

## 11.5 Fallback: continuar no WhatsApp original

Se o envio humano via dashboard não estiver homologado:

a UI deve dizer a verdade:

```text
“Continue pelo WhatsApp conectado.”
```

E mostrar:

- pergunta atual;
- fatos relevantes;
- checklist;
- resposta sugerida;
- próximo objetivo.

O Espelho/Observador deve reconciliar as mensagens `fromMe` quando disponível.

A UI nunca mostra:

```text
“enviado”
```

se não houve confirmação.

## 11.6 Retorno

Quando humano clicar:

```text
[Devolver para o AutoBrokers]
```

ou o sistema reconhecer explicitamente uma ação equivalente permitida:

- construir pack fresco;
- reconciliar mensagens;
- validar desfecho;
- incrementar epoch;
- retornar executor do Work Run;
- nunca começar outro acionamento.

---

# 12. COMO RETOMAR — DOIS EXECUTORES, UMA INTERFACE

O Work OS já suporta múltiplos `runtime_kind`.

A SPEC não inventa um único mecanismo falso.

Criar interface de continuidade, por exemplo:

```python
ContinuationAdapter:
    pause(...)
    resume(...)
    can_resume(...)
    reconcile(...)
```

Implementações iniciais:

## 12.1 Smith / LangGraph

Usar:

```text
interrupt()
+
checkpointer durável
+
mesmo thread_id
+
Command(resume=...)
```

Regras:

- mesmo thread;
- side effect antes de `interrupt` precisa ser idempotente;
- preferir side effect após resume ou em nó separado;
- não criar novo graph/runtime.

## 12.2 `runtime_kind=acionamento`

O acionamento é movido por inbound do WhatsApp, não pelo Smith Worker.

Retomada deve:

- usar mesmo Work Run;
- usar current_step/checkpoint/snapshot existente;
- reconciliar mensagens observadas durante takeover;
- atualizar o state atual;
- voltar ao motor existente.

Não usar `Command(resume)` só para parecer uniforme.

> **Interface uniforme; executor verdadeiro.**

---

# 13. DURABLE WAIT — ESPERA VIRA OBJETO

## 13.1 Por que `retry_scheduled` não serve

Retry significa:

> **nós tentamos e falhamos; tentaremos novamente.**

Wait significa:

> **o trabalho está saudável; estamos esperando algo externo.**

Misturar os dois estraga:

- métricas;
- UX;
- alarmes;
- retry semantics;
- análise de gargalo.

## 13.2 Novo objeto subordinado

Criar `work_waits` ou nome equivalente aprovado no warm-up.

NÃO é runtime.

É estado filho do Work Run.

Schema conceitual:

```text
id uuid PK
company_id uuid NOT NULL
work_run_id uuid NOT NULL
conversation_id uuid NULL

scope_type text NOT NULL
scope_ref text NULL

wait_kind text NOT NULL
waiting_on text NOT NULL
reason_code text NOT NULL

status text NOT NULL
policy_key text NULL
policy_version text NULL

started_at timestamptz NOT NULL
next_action_at timestamptz NULL
last_action_at timestamptz NULL
attempt_count int NOT NULL DEFAULT 0
max_attempts int NULL

control_epoch_at_start bigint NULL

satisfied_at timestamptz NULL
satisfied_by_event_ref text NULL

metadata_redacted jsonb NOT NULL DEFAULT '{}'

created_at
updated_at
```

## 13.3 Status

```text
active
satisfied
timed_out
cancelled
superseded
```

## 13.4 Wait kinds iniciais

```text
CUSTOMER
INSURER
DOCUMENT
CONFIRMATION
BROKER_HUMAN
CHANNEL
EXTERNAL
```

## 13.5 Um wait ativo por scope

Criar constraint/índice que impeça dois waits ativos concorrentes no mesmo:

```text
work_run + scope
```

quando isso não fizer sentido.

Se existir caso legítimo de waits paralelos:

o executor deve prová-lo antes de relaxar.

---

# 14. SIGNAL OU TIMEOUT

Cada wait termina por:

```text
SIGNAL
ou
TIMEOUT/POLICY ACTION
```

Exemplo:

```text
WAITING CUSTOMER
   │
   ├─ mensagem do cliente
   │      ↓
   │   satisfied
   │      ↓
   │   cancela próxima ação
   │
   └─ relógio chega
          ↓
       follow-up due
```

Isso reproduz a semântica de durable workflow sem instalar Temporal.

---

# 15. QUEM SATISFAZ CADA WAIT

| Wait | Sinal típico |
|---|---|
| CUSTOMER | inbound do segurado |
| INSURER | inbound da seguradora / mudança de dispatch |
| DOCUMENT | documento recebido/ingestado |
| CONFIRMATION | resposta explícita |
| BROKER_HUMAN | review submit / takeover / resolved |
| CHANNEL | janela/capability mudou ou template disponível |
| EXTERNAL | evento específico do provider |

O matcher do sinal deve ser explícito.

“Qualquer mensagem” não satisfaz qualquer wait.

---

# 16. SCHEDULER — REUSAR O QUE EXISTE

É proibido criar outro scheduler.

Implementar scanner de waits no runtime operacional existente.

Preferência:

```text
SmithWorker
  └─ loop de waits / manutenção
```

O warm-up deve confirmar se o Worker dedicado está realmente ativo em produção.

Se não estiver:

- isso vira blocker de go-live da automação de follow-up;
- não declarar feature pronta sustentada apenas por processo local frágil.

Intervalo inicial deve ser configurável.

---

# 17. FOLLOW-UP POLICY ENGINE

## 17.1 Determinístico

Entrada:

```text
wait
case priority
channel
last inbound/outbound
business hours
tenant policy
attempt count
ownership
delivery capability
```

Saída:

```text
NO_ACTION
SEND_FOLLOWUP
SEND_STATUS_UPDATE
ESCALATE_HUMAN
CLOSE_INACTIVITY
KEEP_WAITING
REQUIRE_TEMPLATE
CREATE_MANUAL_TASK
```

A LLM não retorna uma dessas decisões.

## 17.2 Policy versionada

```text
policy_key
policy_version
```

Exemplo:

```text
attendance.assistance.default@1
```

## 17.3 AutoBrokers default

Existem defaults oficiais.

Tenant pode alterar dentro de limites:

- horários;
- intervalo;
- número de tentativas;
- tom;
- alguns destinos de escalada.

Não pode:

- desligar hard safety;
- mandar fora das regras do canal;
- remover idempotência;
- permitir IA falar durante takeover humano;
- enviar para telefone não confirmado.

---

# 18. PERFIS DE FOLLOW-UP INICIAIS

Os tempos abaixo são **CANDIDATOS para calibração no warm-up**, não fatos medidos.

## 18.1 Assistência ativa — aguardando cliente

Objetivo:

> não deixar um pedido urgente morrer.

Proposta inicial:

```text
15 min  → lembrete curto
45 min  → segundo lembrete
120 min → escalada/triagem humana; NÃO fechar automaticamente uma assistência urgente
```

## 18.2 Documento

```text
4 h               → lembrete
próximo horário útil → lembrete
48 h              → fila humana ou política de inatividade
```

## 18.3 Confirmação pós-etapa

```text
2 h  → pergunta contextual
24 h → segunda tentativa
depois → fechar somente se o tipo de caso permitir e o motivo for explícito
```

## 18.4 Aguardando seguradora

Não perguntar ao cliente:

> “ainda precisa de ajuda?”

quando ele não tem nada para fazer.

Ações possíveis:

```text
status update ao cliente
+
monitorar insurer
+
escalar operação se SLA interno estourar
```

## 18.5 Aguardando humano da corretora

- holding message verdadeira ao cliente;
- alertas para a equipe;
- stale claim volta a alertar;
- nunca IA reassumir silenciosamente só porque demorou.

---

# 19. BUSINESS HOURS / QUIET HOURS

Policy precisa considerar:

```text
tenant timezone
business hours
quiet hours
holiday policy quando configurada
urgency override
```

Não assumir que toda corretora opera em São Paulo.

`America/Sao_Paulo` pode ser fallback somente se já for regra do produto/tenant; confirmar no warm-up.

Assistência urgente pode possuir policy diferente de rotina comercial.

---

# 20. WHATSAPP / CHANNEL POLICY

## 20.1 Nunca hardcode “WhatsApp = sempre pode texto livre”

Para WhatsApp Business Platform oficial:

- dentro de 24h da última mensagem do usuário → free-form permitido;
- fora da janela → Message Template aprovado necessário;
- automação precisa ter escalada humana clara.

Mas AutoBrokers pode operar providers/conexões diferentes.

Portanto a Policy Engine consulta uma capability:

```text
FREEFORM_ALLOWED
TEMPLATE_REQUIRED
BLOCKED
UNKNOWN
```

## 20.2 Fora da janela

Se provider oficial exige template e não existe template homologado:

```text
NÃO tentar texto livre
```

Opções:

- template aprovado;
- approval/manual task;
- outro canal permitido;
- esperar inbound;
- escalar humano.

## 20.3 SPEC-099

A Channel Fabric completa fica para a 099.

A 086 implementa apenas o contrato mínimo necessário para não enviar ilegal/incorretamente.

---

# 21. FOLLOW-UP COPY

## 21.1 A decisão é determinística

A LLM recebe somente depois:

```text
SEND_FOLLOWUP foi autorizado
```

## 21.2 Input da LLM

```text
purpose
recipient role
case type
facts allowed
previous message
attempt number
tone policy
max length
forbidden claims
```

## 21.3 Output

Somente:

```text
body
```

Opcionalmente:

```text
subject / quick-reply labels
```

Nunca:

```text
recipient
send_at
channel
whether_to_send
```

## 21.4 Fallback

LLM falhou:

usar template determinístico.

Follow-up não pode ficar sem proteção porque a LLM caiu.

---

# 22. SIDE EFFECT — ÚLTIMO CHECK ANTES DE ENVIAR

Antes de CADA follow-up:

revalidar atomicamente:

```text
wait.status == active
AND
now >= next_action_at
AND
control epoch ainda é o esperado
AND
control mode permite
AND
nenhum inbound relevante chegou
AND
case não foi resolvido/fechado
AND
recipient continua o mesmo
AND
channel policy permite
AND
idempotency effect ainda não executado
```

Se qualquer um falhar:

```text
followup.skipped
```

com reason.

---

# 23. IDEMPOTÊNCIA DE FOLLOW-UP

Idempotency key conceitual:

```text
followup:{wait_id}:{attempt_no}:{action_kind}
```

Usar `work_effects` quando compatível.

Dois scanners detectam o mesmo timer:

```text
um reserva
um perde
```

Nunca duas mensagens.

---

# 24. EVENTO INBOUND CANCELA TIMER ANTES DE RESPONDER

Ordem crítica:

```text
INBOUND
↓
persistir mensagem
↓
satisfazer/cancelar wait
↓
incrementar/reconciliar state
↓
só depois processar resposta
```

Assim um timer concorrente vê o wait como encerrado.

---

# 25. HUMAN REVIEW — TIMEOUT

Review é wait durável.

Campos:

```text
review question
required response schema
reviewer/team
timeout
escalation behavior
```

Se timeout:

nunca inventar input humano.

Opções por policy:

```text
escalate to takeover queue
notify customer truthfully
keep waiting
```

---

# 26. HUMAN TAKEOVER — STALE CLAIM

O watchdog atual já descobriu:

> claim fresco deve calar alerta; claim abandonado não pode tornar caso invisível.

Preservar.

A SPEC formaliza:

```text
claimed_at
↓
stale threshold
↓
alert owner/team
```

Mas:

> stale claim NÃO devolve automaticamente o caso à IA.

Isso poderia fazer a IA falar enquanto uma pessoa ainda está trabalhando.

---

# 27. RETURN TO AI — NÃO É RELEASE

Criar ação explícita:

```text
RETURN_TO_AI
```

Ela é diferente do atual `release`.

Contrato:

1. humano informa resultado/observações obrigatórias conforme caso;
2. pack fresco é construído;
3. sistema reconcilia mensagens/efeitos;
4. adapter verifica se runtime pode retomar;
5. epoch incrementa;
6. Work Run retoma;
7. somente então AI outbound é liberado.

Falhou a reconciliação:

```text
não liberar IA
```

fica:

```text
HUMAN / NEEDS_RECONCILIATION
```

em linguagem/estado equivalente aprovado no warm-up.

---

# 28. CLOSE — ENCERRAMENTO VERDADEIRO

`close` não pode significar apenas:

```text
status = closed
```

O fecho deve carregar `resolution_reason`.

Famílias iniciais:

```text
RESOLVED_AUTONOMOUS
RESOLVED_HUMAN
RESOLVED_BY_REDIRECT
CUSTOMER_DECLINED
DUPLICATE
INACTIVITY_POLICY
CHANNEL_UNREACHABLE
ABANDONED_WITH_REASON
```

Usar campos existentes se já houver autoridade equivalente.

Não criar enum/tabela duplicada sem necessidade.

## 28.1 Inatividade

Só fechar automaticamente por inatividade quando:

- policy autoriza;
- attempts acabaram;
- não estamos esperando seguradora/humano/documento externo;
- caso não é crítico;
- nenhum inbound recente;
- nenhum takeover humano;
- channel policy não impediu envio das tentativas.

Se não conseguimos mandar porque Meta exigia template e não tínhamos:

> isso NÃO é “cliente não respondeu”.

---

# 29. O LEGADO `follow-up-whatsapp`

O Auxiliar existente é:

- draft-only;
- LLM;
- approval;
- dry-run;
- telefone manual.

Não é autoridade de follow-up operacional.

Decisão:

```text
não apagar
não expandir como segundo motor
```

Reaproveitar, se útil:

- copy generation;
- UX de draft;
- approval pattern.

Depois da 086 ele deve ser:

```text
surface/manual skill
→ chama o mesmo FollowUp Policy/Composer
```

ou ser formalmente superseded.

---

# 30. STATE MACHINE — VISÃO DE PRODUTO

```text
                     ┌───────────────┐
                     │   AI ACTIVE   │
                     └───────┬───────┘
                             │
                  precisa input humano?
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
      AI PAUSED FOR REVIEW           HUMAN QUEUE
                │                         │
        humano responde              humano claims
                │                         │
                ▼                         ▼
         AI RESUMES                  HUMAN OWNED
                                          │
                             ┌────────────┴────────────┐
                             │                         │
                         resolve                   return
                             │                         │
                             ▼                         ▼
                           CLOSE             RECONCILE + AI ACTIVE
```

WAIT roda ortogonalmente a isso.

---

# 31. UI MÍNIMA DA SPEC-086

Não construir a Operations Workspace inteira.

Na superfície atual de atendimento/conversa:

## Quando IA pede review

Mostrar card:

```text
AutoBrokers precisa de uma informação

A seguradora perguntou:
...

O que já sabemos:
...

[Responder]
[Assumir atendimento]
```

## Quando human-owned

Mostrar:

```text
Com Maria desde 14:32
AutoBrokers está pausado nesta conversa.

[Devolver para o AutoBrokers]
[Resolver]
```

## Quando wait ativo

Mostrar:

```text
Aguardando seguradora há 18 min
Próxima ação: acompanhar às 14:50
```

## Quando follow-up agendado

Mostrar:

```text
Aguardando cliente
Próximo lembrete em 12 min
```

Com opção autorizada:

```text
[Cancelar lembrete]
```

---

# 32. OUTBOUND GATE CANÔNICO

O warm-up deve mapear TODOS os seams atuais que enviam customer-facing/insurer-facing message.

Objetivo:

não reescrever providers.

Criar uma borda comum, nome conceitual:

```text
ConversationOutboundGate
```

ou equivalente.

Ela recebe:

```text
actor
resource_ref
expected_epoch
recipient_ref
channel
message
idempotency_key
```

Valida:

- ownership;
- epoch;
- tenant;
- channel capability;
- effect idempotency;
- delivery permission.

Só então chama seam atual.

---

# 33. INSURER OUTBOUND

O projeto possui histórico de outbox/gates de mensagens para seguradora.

O executor deve verificar o caminho ATUAL.

É proibido:

- reativar skeleton antigo como se fosse produção;
- criar segundo outbox;
- ignorar kill switch/approval/capability existente;
- dizer que humano enviou se adapter está bloqueado.

A 086 usa o envio real já homologado, se existir.

Se não existir:

fallback para atuação no WhatsApp original + observação/reconciliação.

---

# 34. EVENT TAXONOMY

Adicionar eventos em `work_events`, conforme aplicável:

```text
control.ai_paused
control.human_review_requested
control.human_review_submitted
control.human_takeover_requested
control.human_claimed
control.human_released_to_queue
control.return_to_ai_requested
control.return_to_ai_succeeded
control.return_to_ai_failed
control.stale_action_rejected

wait.started
wait.satisfied
wait.cancelled
wait.timed_out

followup.due
followup.composed
followup.sent
followup.skipped
followup.failed
followup.exhausted

insurer.human_phase_entered
insurer.human_reply_submitted
insurer.human_takeover

case.resolved
case.closed_inactivity
```

Payload sempre redigido.

---

# 35. MÉTRICAS

Métricas mínimas:

```text
time_ai_owned
time_human_queue
time_human_owned
time_review_wait

wait_time_customer
wait_time_insurer
wait_time_document
wait_time_human

human_review_count
human_takeover_count
return_to_ai_success_rate

control_conflict_count
stale_outbound_rejected_count

followups_due
followups_sent
followups_skipped
followups_recovered_conversation
followups_exhausted

handoff_to_resolution_time

insurer_human_phase_count
insurer_human_review_resolution
insurer_human_takeover_resolution

close_by_reason
```

Essas métricas prepararão SPEC-097/108.

---

# 36. SECURITY / TENANT ISOLATION

Hard requirements:

- toda mudança de control filtra `company_id`;
- nenhuma RPC aceita `company_id` arbitrário sem contexto autenticado;
- conversation e run precisam pertencer ao mesmo tenant quando vinculados;
- wrong-tenant claim = zero rows/404, nunca vazamento;
- `claimed_by` precisa pertencer ao tenant;
- Resume Pack não carrega segredo;
- operator pack não persiste PII duplicada;
- follow-up recipient vem da conversa/authority, nunca da LLM;
- telefone cru não entra em event payload;
- insurer/customer channel refs ficam scoped.

---

# 37. FAILURE MODES

## F1 — Humano assume enquanto IA está gerando

Control epoch rejeita side effect stale.

## F2 — Dois humanos assumem

Atomic transition; um vence.

## F3 — Cliente responde no mesmo instante do timer

Inbound satisfaz wait; final pre-send check bloqueia follow-up.

## F4 — Timer dispara duas vezes

`work_effect` idempotente bloqueia segunda.

## F5 — Worker reinicia com waits ativos

Postgres permanece; scanner encontra `next_action_at`.

## F6 — Redis cai

Wait não some; Redis não é autoridade.

## F7 — LLM de copy cai

Template determinístico.

## F8 — Meta/window bloqueia

Não envia; classifica channel policy; cria ação permitida.

## F9 — Human review expira

Escala segundo policy; não inventa resposta.

## F10 — Human takeover fica abandonado

Watchdog re-alerta; não auto-devolve à IA.

## F11 — Humano usa o celular

Espelho captura quando disponível; pack fresco reconcilia.

## F12 — Pack antigo

Fingerprint diverge; não retoma sem reconciliação.

## F13 — LangGraph resume reexecuta nó

Side effect pré-interrupt precisa ser idempotente ou movido.

## F14 — Insurer side provider indisponível

Fallback explícito; sem status falso de enviado.

---

# 38. BLOCO 0 — WARM-UP / REFUTAÇÃO

Antes de editar:

1. confirmar HEAD;
2. verificar se existe SPEC-086 canônica;
3. listar todas as referências atuais a `SPEC-086`;
4. mapear o que essas referências já assumem;
5. conferir migrations de `conversations.claimed_*`;
6. conferir `work_runs`/`work_steps` atuais;
7. conferir 085 migration/report;
8. confirmar quais estados de Work Run existem no banco;
9. localizar TODOS os writers/readers de `HUMAN_REQUESTED`;
10. localizar TODOS os send seams customer-facing;
11. localizar TODOS os send seams insurer-facing;
12. confirmar como `fromMe` pausa conversa;
13. confirmar como `human_phase` funciona hoje;
14. confirmar caminho real de envio à seguradora;
15. confirmar se old action-outbox skeleton foi superseded;
16. confirmar Smith Worker em produção;
17. medir follow-up legado;
18. procurar timers/watchdogs duplicados;
19. medir casos parados por owner/wait;
20. validar schema vivo em read-only.

## 38.1 Premissas para refutar

**A:** “`HUMAN_REQUESTED` é suficiente para garantir que a IA nunca envia depois do claim.”

Tente provar falso.

**B:** “Todo `release` pode devolver a conversa à IA.”

Falso por desenho atual; mapear casos.

**C:** “Existe apenas um envio WhatsApp por tipo de conversa.”

Tente achar seams paralelos.

**D:** “O Smith Worker está ativo e pode hospedar durable waits.”

Provar, não supor.

**E:** “Todo `human_phase` precisa de humano da corretora.”

Provavelmente falso. Separar automation-safe de review/takeover.

---

# 39. BLOCO A — CONTROL PLANE DE POSSE

Implementar:

- control mode;
- control epoch;
- transições atômicas;
- backfill compatível;
- integração com `claimed_by`;
- execution control no Work Run quando necessário;
- eventos;
- RLS/constraints.

### Gate A

Provas:

- dois humanos competindo;
- AI vs human race;
- outra conversa continua AI;
- wrong tenant não altera;
- stale epoch não envia.

Mutation crítica:

```text
remover epoch check
```

deve tornar race test vermelho.

---

# 40. BLOCO B — OUTBOUND FENCED GATE

Mapear/funilar todos os sends relevantes.

Não duplicar provider.

Implementar:

```text
pre-send ownership + epoch + effect check
```

### Gate B

Ensaio concorrente:

```text
AI prepara msg
barrier
humano claim
AI libera barrier
```

Esperado:

```text
0 mensagens AI enviadas
1 stale_action_rejected
```

Controle:

sem claim:

```text
1 mensagem enviada
```

---

# 41. BLOCO C — RESUME PACK

Implementar builder estruturado:

- run;
- conversation;
- insurer context;
- facts;
- missing;
- effects;
- next actions;
- control;
- wait;
- refs;
- fingerprint.

Renderização operator.

Sem PII duplicada.

### Gate C

- pack explica o ponto atual;
- pack muda quando fontes mudam;
- pack stale é detectado;
- texto humano nunca inventa fato;
- pack de tenant A não carrega tenant B.

---

# 42. BLOCO D — HUMAN REVIEW / HUMAN TAKEOVER

Implementar as duas operações separadas.

## Review

```text
pause
input schema
timeout
submit
resume
```

## Takeover

```text
claim
hard lock
human send
return_to_ai
resolve
```

### Gate D

E2E:

```text
AI → review → human input → AI
```

e:

```text
AI → takeover → human message → AI stays silent
```

---

# 43. BLOCO E — INSURER HUMAN BRIDGE

Implementar experiência em `human_phase`.

- resposta determinística segura continua automática;
- dúvida/negociação cria review;
- operator responde via UI quando homologado;
- fallback WhatsApp original;
- takeover explícito;
- retorno ao mesmo run.

### Gate E

Ensaio:

```text
URA → human_phase → pergunta humana → review → resposta humana → protocolo
```

mesmo Work Run.

Controle:

takeover:

```text
AI não envia à insurer session
```

---

# 44. BLOCO F — DURABLE WAITS

Implementar `work_waits`/equivalente:

- migration expand-only;
- active/satisfied/cancelled/timed_out;
- scope;
- signal matching;
- next action;
- indexes;
- service;
- timeline.

Scanner entra em scheduler existente.

### Gate F

- restart preserva wait;
- inbound satisfaz;
- stale timer não dispara;
- dois scanners não duplicam.

---

# 45. BLOCO G — FOLLOW-UP POLICY

Implementar:

- policy schema;
- defaults;
- tenant override;
- business hours;
- channel capabilities;
- copy composer;
- deterministic fallback;
- idempotent send;
- close/exhaust semantics.

### Gate G

Cenários:

```text
WAIT CUSTOMER
→ follow-up

WAIT INSURER
→ NÃO pergunta ao cliente por resposta

HUMAN OWNED
→ nenhum follow-up AI

CUSTOMER REPLIED
→ timer cancela

OUTSIDE WHATSAPP WINDOW
→ template/manual path, não freeform
```

---

# 46. BLOCO H — RETURN / RECONCILIATION

Criar ação explícita `RETURN_TO_AI`.

Implementar adapters:

- Smith/LangGraph;
- acionamento.

Reconciliar:

- messages;
- effects;
- insurer events;
- current step;
- checkpoint/fingerprint.

### Gate H

E2E:

```text
AI
→ human takeover
→ humano faz ação
→ inbound/outbound observado
→ return_to_ai
→ IA continua do próximo ponto
```

Proibido:

```text
novo Work Run
novo atendimento
repetir side effect
```

---

# 47. BLOCO I — CLOSURE / OBSERVABILITY / MIGRATION

- resolution reason;
- follow-up metrics;
- ownership durations;
- timeline;
- compat com dashboards existentes;
- legacy follow-up supersession plan;
- docs;
- feature kill switch;
- canary.

---

# 48. TEST MATRIX

| Tipo | Obrigatório | Prova |
|---|---|---|
| unit | sim | control/wait/policy |
| DB constraint | sim | tenant + transitions |
| concurrency | sim | AI vs human / human vs human |
| mutation | sim | epoch/gate/idempotency |
| restart | sim | durable waits |
| inbound race | sim | reply vs timer |
| Work Effect | sim | no duplicate follow-up |
| Smith HITL | sim | same thread resume |
| dispatch resume | sim | same run |
| insurer human | sim | review/takeover |
| channel policy | sim | freeform/template/block |
| PII | sim | Resume Pack/events |
| mobile/fromMe | sim | human takeover observation |
| cross-tenant | sim | no leak |
| E2E | sim | AI→human→AI→resolve |
| E2E | sim | AI→human→resolve |
| E2E | sim | follow-up→reply→resolve |
| E2E | sim | wait insurer no wrong nag |
| regression | sim | 085 + attendance pack |
| failure injection | sim | Redis/worker/provider |

---

# 49. CONTROLS OBRIGATÓRIOS

Cada teste de bloqueio precisa do outro lado.

Exemplo:

```text
human claim blocks AI
+
without human claim AI can send

stale timer is skipped
+
active timer sends once

wrong epoch rejected
+
current epoch accepted

wrong tenant rejected
+
correct tenant accepted

window closed blocks freeform
+
window open allows it
```

---

# 50. MUTATIONS OBRIGATÓRIAS

## M1 — remover control epoch check
race deve deixar teste vermelho.

## M2 — mudar `HUMAN` para aceitar AI outbound
teste vermelho.

## M3 — não cancelar wait em inbound
stale follow-up deve aparecer e teste cair.

## M4 — remover idempotency key
double scanner produz duplicata; teste cai.

## M5 — `UNKNOWN channel` virar `FREEFORM_ALLOWED`
teste cai.

## M6 — release legado chamar resume automático
teste de handoff aberto cai.

## M7 — pack stale ignorado
resume incorreto deve ser detectado.

## M8 — LangGraph side effect antes de interrupt sem idempotência
mutation/effect test acusa duplicação.

---

# 51. RED TEAM

Missão:

> **fazer IA e humano falarem simultaneamente ou mandar follow-up errado sem os testes perceberem.**

Ataques:

- claim entre generation/send;
- atraso de processo;
- dois tabs;
- duas pessoas;
- fromMe e dashboard no mesmo segundo;
- retry de webhook;
- customer reply e timer;
- provider timeout after accepted;
- Redis down;
- worker restart;
- stale Resume Pack;
- wrong conversation id;
- route/run de outro tenant;
- channel window stale;
- human takeover abandonado;
- “release” sem reconciliação;
- follow-up para segurado enquanto espera insurer;
- close por inactivity sem mensagem ter sido entregue.

---

# 52. ROLLOUT

## Fase 1 — shadow metrics

- criar waits/control state;
- não alterar envio;
- comparar decisões.

Curta e com exit criteria.

## Fase 2 — canary tenant

Preferência:

- corretora piloto;
- poucos operadores;
- Assistência primeiro.

Ativar:

- hard control gate;
- human review;
- durable waits;
- follow-up selecionado.

## Fase 3 — insurer human bridge

Somente canais homologados.

## Fase 4 — generalização

Depois de dados:

- outras corretoras;
- outras rotas;
- outras classes de wait.

---

# 53. KILL SWITCHES

Mínimo:

```text
ATTENDANCE_CONTINUITY_ENABLED
ATTENDANCE_FOLLOWUP_ENABLED
ATTENDANCE_HUMAN_REVIEW_ENABLED
```

Não criar dezenas de flags.

Global kill switch de outbound existente continua superior quando aplicável.

---

# 54. ROLLBACK

Rollback precisa:

- desativar follow-up;
- manter waits/dados para auditoria;
- preservar claims humanos;
- nunca reassumir IA automaticamente em massa;
- não apagar work_events;
- migrations expand-only;
- old behavior só volta onde seguro.

---

# 55. DEFINIÇÃO DE PRONTO

A SPEC-086 só fecha quando:

- [ ] SPEC-085 foi auditada e não duplicada;
- [ ] control mode explícito existe;
- [ ] control epoch/fencing existe;
- [ ] outbound AI revalida epoch imediatamente antes do effect;
- [ ] duas pessoas não conseguem possuir a mesma conversa;
- [ ] human takeover é hard lock;
- [ ] outras conversas continuam IA;
- [ ] Human Review e Human Takeover são operações distintas;
- [ ] Resume Pack estruturado existe;
- [ ] Resume Pack não vira fonte de verdade;
- [ ] Resume Pack possui fingerprint;
- [ ] Resume Pack não duplica PII;
- [ ] return_to_ai é ação explícita;
- [ ] release legado não é confundido com resume;
- [ ] Smith retoma pelo mesmo thread/checkpoint;
- [ ] dispatch retoma pelo mesmo Work Run;
- [ ] side effects pré-interrupt são idempotentes/segregados;
- [ ] insurer `human_phase` tem Review/Takeover;
- [ ] humano pode responder pelo AutoBrokers quando canal homologado;
- [ ] fallback manual é verdadeiro e reconciliável;
- [ ] durable wait existe;
- [ ] wait != retry;
- [ ] wait sobrevive restart;
- [ ] inbound satisfaz wait antes do processamento posterior;
- [ ] Follow-up Policy é determinística;
- [ ] LLM não escolhe timing/recipient;
- [ ] default AutoBrokers existe;
- [ ] override tenant possui limites;
- [ ] business hours/quiet hours entram na decisão;
- [ ] channel capability entra na decisão;
- [ ] regras oficiais de WhatsApp não são burladas;
- [ ] follow-up usa idempotência;
- [ ] stale timer não envia;
- [ ] human-owned não recebe send da IA;
- [ ] WAIT_INSURER não vira pergunta indevida ao cliente;
- [ ] stale claim re-alerta sem auto-resume;
- [ ] closure possui reason verdadeiro;
- [ ] channel-blocked não é contado como customer-inactivity;
- [ ] métricas de ownership/waits/followup existem;
- [ ] PII audit verde;
- [ ] cross-tenant verde;
- [ ] concurrency tests verdes;
- [ ] mutation critical verde;
- [ ] E2E AI→review→AI verde;
- [ ] E2E AI→takeover→human→AI verde;
- [ ] E2E AI→takeover→human resolve verde;
- [ ] E2E follow-up race verde;
- [ ] E2E insurer human bridge verde;
- [ ] regression pack da 085 continua verde;
- [ ] execution report criado;
- [ ] deploy/canary comprovado quando a execução acontecer.

---

# 56. MÉTRICAS DE SUCESSO DA SPEC

Primárias:

```text
AI message after human claim .............. 0
duplicate follow-up ....................... 0
follow-up after relevant inbound .......... 0
wrong-tenant control mutation ............. 0
resume creating second work run ........... 0
unreconciled return_to_ai .................. 0
false “sent” insurer messages .............. 0
```

Operacionais:

```text
time to human claim
time human-owned
review response time
return-to-ai rate
follow-up recovery rate
handoff resolution time
wait duration by actor
close reason distribution
stale action rejection count
```

---

# 57. PENDÊNCIAS QUE ESTA SPEC NÃO DEVE ENGOLIR

- fila/Kanban completa → SPEC-097;
- Channel Fabric completa → SPEC-099;
- Slack/Teams → SPEC-099;
- Marketplace de Auxiliares → SPEC-103;
- Claims autonomous → SPEC-093 prepara;
- MetaHarness → SPEC-108;
- Voice → SPEC-112;
- política global de SLA operacional → pode ser aprofundada na Operations Workspace;
- templates de WhatsApp completos / gestão de catálogo → Channel Fabric.

---

# 58. REFERÊNCIAS INTERNAS

Leitura sob demanda:

- SPEC-053 — Work OS/Core Harness
- SPEC-055 — Durable Work Runs
- SPEC-055 Execution Report
- SPEC-063 — Acionamento durável
- SPEC-085
- SPEC-085 Execution Report
- `backend/app/services/work/runs.py`
- `backend/app/services/work/queue.py`
- `backend/app/workers/smith_worker.py`
- `backend/app/agents/tools/human_handoff.py`
- `backend/app/tasks/handoff_watchdog.py`
- `backend/app/services/insurer_dispatch_service.py`
- `app/api/dashboard/conversas/[id]/route.ts`
- `app/api/dashboard/acionamentos-travados/route.ts`
- `backend/tests/test_quem_fala_primeiro_cala_o_outro.py`
- `backend/tests/test_o_humano_e_chamado_de_verdade.py`
- Follow-up WhatsApp auxiliary report legado
- Insurer WhatsApp Outbox/Gates report histórico
- Protocolo AutoBrokers AAA v9

---

# 59. REFERÊNCIAS EXTERNAS

Contexto completo no Research Pack.

Principais padrões absorvidos:

## LangGraph

- `interrupt()`;
- checkpointer durável;
- mesmo `thread_id`;
- `Command(resume=...)`;
- side effects antes do interrupt devem ser idempotentes;
- Human-in-the-loop sem segundo runtime.

## Intercom Fin Procedures — Human-in-the-loop

Distinção extremamente útil:

```text
Loop in teammate
→ humano contribui
→ Fin continua

Take over conversation
→ humano assume
→ Fin para
```

É a referência de produto para separar Review e Takeover.

## Temporal — design benchmark

Padrões:

```text
durable timer
signal
wait_condition
timeout
time-skipping tests
```

Não instalar.

Absorver a semântica no Work OS existente.

## WhatsApp Business Policy

- 24h customer service window para free-form na plataforma oficial;
- fora da janela → approved template;
- automação precisa oferecer escalada humana clara.

A 086 cria capability gate; Channel Fabric completa vem depois.

## Fencing token pattern

A ideia:

```text
owner velho pode acordar atrasado
↓
token/epoch antigo
↓
resource/gateway rejeita
```

Aplicação:

`control_epoch` em toda mensagem crítica.

---

# 60. AQUECIMENTO SUGERIDO AO CLAUDE CODE / CODEX

Responder antes da primeira edição:

1. Quantos writers atuais de `HUMAN_REQUESTED` existem?
2. Quais deles pausam somente conversa?
3. Quais send seams consultam esse estado?
4. Existe algum send seam que não consulta?
5. Mostre uma corrida possível claim-vs-send.
6. `release` hoje volta quando para `open` e quando para a fila?
7. Quantas cadeias de handoff ainda existem?
8. Quais referências atuais a SPEC-086 já pressupõem implementação futura?
9. O Smith Worker está ativo em produção?
10. Qual é o status enum real de Work Runs?
11. Onde o dispatch persiste seu current phase?
12. Como `human_phase` está sendo respondido hoje?
13. Existe envio real homologado insurer-side pela UI?
14. O velho 42X2 foi superseded?
15. Quais outbound providers existem hoje?
16. Quais têm service window/template semantics?
17. Onde seria o menor ponto comum para `control_epoch`?
18. `work_effects` já consegue reservar mensagem de follow-up?
19. Existe tabela/objeto de wait que eu não vi?
20. Ache um caso em que esta SPEC criaria uma segunda autoridade.
21. Ache uma forma de IA falar depois do takeover mesmo com a proposta atual.
22. Ache uma forma de timer velho mandar mensagem depois da resposta.
23. Liste o que nesta SPEC ficou vencido.
24. Liste o que você não entendeu.

---

# 61. COMANDO FINAL AO EXECUTOR

Não transforme a 086 em:

```text
mais estados
+
mais timers
+
mais ifs
```

O objetivo é criar uma única lei operacional:

> **Cada trabalho sabe quem pode avançá-lo, cada conversa sabe quem pode falar, cada espera sabe o que a encerra, e cada retomada sabe de qual verdade continuar.**

Sempre que houver conflito entre simplicidade local e essa lei:

a lei vence.

Se uma implementação proposta nesta Candidate Spec divergir do código vivo:

- medir;
- refutar;
- preservar invariantes;
- usar a menor integração compatível;
- registrar a correção.

> **Depois da SPEC-086, “precisa de humano” deixa de ser o fim da inteligência. Passa a ser apenas uma mudança governada de mãos dentro da mesma inteligência operacional.**
