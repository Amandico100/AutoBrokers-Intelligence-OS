# SPEC-086 — RESEARCH PACK
## O Atendimento Continua Até o Fim

**Data:** 25/08/2026  
**Baseline do repositório:** `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Uso:** investigação e justificativa. Não carregar inteiro no bootstrap do executor.  
**SPEC associada:** `SPEC-086-o-atendimento-continua-ate-o-fim.md`

---

# 1. PERGUNTA CENTRAL

Como fazer Atendimento/Assistência do AutoBrokers sobreviver a:

- IA não saber continuar;
- especialista humano da seguradora;
- funcionário da corretora assumir;
- funcionário devolver para IA;
- cliente demorar;
- seguradora demorar;
- documento demorar;
- restart;
- corrida entre timer, inbound e outbound;

sem:

- duas vozes na mesma conversa;
- duplicar side effect;
- perder estado;
- abrir outro atendimento;
- mandar follow-up sem sentido;
- inventar que um humano foi avisado;
- criar segundo runtime?

---

# 2. CONCLUSÃO

A solução correta não é “melhorar o agente de follow-up”.

É adicionar três contratos ao Work OS:

```text
CONTROL
quem pode falar/avançar

WAIT
quem/evento estamos esperando

CONTINUATION
como outro ator continua e devolve
```

Resume Pack conecta os três.

---

# 3. ESTADO REAL — O QUE A SPEC-085 JÁ FEZ

A 085 não deve ser reimplementada.

Ela já criou:

```text
work_runs.unblock_state
work_steps.output_redacted
owner_user_id
work_events
```

e estados:

```text
travado
retomado_pelo_robo
assumido_por_humano
resolvido
abandonado
```

A tela de travados já possui claim atômico e arquivo/abandono com motivo.

Portanto a 086 parte de:

> **visibilidade + posse inicial já existem.**

O que falta é continuidade.

---

# 4. CONVERSATION CLAIM JÁ EXISTE

Migration SPEC-017:

```text
claimed_by
claimed_by_name
claimed_at
```

Current dashboard API:

```text
claim
release
close
send
```

### Claim

- atomic;
- `HUMAN_REQUESTED`;
- 409 se outro humano possui.

### Send humano

- auto-claim;
- persiste;
- envia WhatsApp;
- dedup do eco.

### Release

Importante:

se existe handoff aberto:

```text
claimed_by = null
status = HUMAN_REQUESTED
```

Ou seja:

> volta para a fila humana.

Isso NÃO é retorno à IA.

Esse detalhe justifica uma operação nova explícita.

---

# 5. “QUEM FALA PRIMEIRO CALA O OUTRO” JÁ É REGRA

`test_quem_fala_primeiro_cala_o_outro.py` guarda uma decisão do Founder:

- humano responde pelo celular;
- aquela conversa pausa;
- outras continuam com IA.

O webhook vê `fromMe` mesmo com agente ligado.

Essa é uma base excelente.

O problema restante é a janela:

```text
IA já gerou
↓
humano claim
↓
IA antiga ainda envia
```

Status/claim sem fencing pode não fechar a corrida.

---

# 6. POR QUE CONTROL EPOCH

Padrão de distributed systems:

um holder antigo pode continuar executando depois de perder posse.

Um fencing token/epoch monotônico permite ao recurso rejeitar operação stale.

Adaptação:

```text
conversation epoch 7
AI começa trabalho com epoch 7

human claim
conversation epoch 8

AI tenta enviar com 7
gateway rejeita
```

Não depende de relógio.

Não usa TTL para correctness.

## Observação

O provider WhatsApp não conhece `control_epoch`.

Portanto a checagem é feita no último gateway AutoBrokers antes do provider.

---

# 7. WORK RUN JÁ TEM DURABILIDADE

SPEC-055 entregou:

- Work Run universal;
- leases;
- heartbeat;
- recovery;
- work_events;
- idempotent effects;
- approvals;
- Smith Worker.

`WorkRunService` já declara a intenção:

> retomada parte do último ponto seguro.

Portanto um novo “human workflow engine” seria regressão.

---

# 8. ACIONAMENTO JÁ É WORK RUN

SPEC-063 transformou acionamento da seguradora em Work Run.

State machine documentada:

```text
preparing
→ ready_to_send
→ ura
→ human_phase
→ captured
→ monitoring

needs_human
```

Importante:

`runtime_kind=acionamento` NÃO é movido pelo Smith Worker.

Ele progride pelos inbounds do WhatsApp.

Isso significa:

> Resume precisa ser uma interface com adapters por executor.

Não dá para fingir que todo mundo usa LangGraph Command.

---

# 9. HUMAN PHASE JÁ EXISTE

Frontend canônico atual possui:

```text
human_phase
label = “Especialista da seguradora”
```

e a explicação:

> falando com o especialista da assistência para abrir o serviço.

Ou seja:

o produto já sabe que “humano da seguradora” é uma fase legítima.

A 086 adiciona governança de quem responde.

---

# 10. HANDOFF WATCHDOG JÁ TEM LIÇÕES IMPORTANTES

O watchdog documenta um caso de conversa em `HUMAN_REQUESTED` por ~730 horas.

Também descobriu:

- `HUMAN_REQUESTED` pode significar “IA pediu humano” ou “humano já assumiu”;
- `claimed_by` distingue;
- não alertar equipe se última palavra foi da corretora;
- claim fresco cala alerta;
- claim abandonado precisa voltar a alertar;
- Redis failure deve preferir aviso extra a silêncio.

Essas lições entram na 086.

---

# 11. FOLLOW-UP LEGADO

O relatório do Auxiliar Follow-up WhatsApp mostra:

- LLM draft;
- telefone manual;
- aprovação;
- `whatsapp_send_message_dry_run`;
- zero envio real.

Isso é útil como UX/copy prototype.

Não é um scheduler nem state machine.

Portanto:

```text
usar como referência
não como autoridade
```

---

# 12. OUTBOX INSURER HISTÓRICO

O 42X2 criou:

- ExternalActionOutbox;
- 14 permission gates;
- HITL;
- kill switch;
- rate limit;
- adapter skeleton;
- canSendReal=false;
- sem envio real.

O baseline search não encontrou `canSendReal=true` naquele caminho.

Mas o acionamento atual obviamente possui outro caminho operacional de WhatsApp.

Conclusão:

> warm-up precisa descobrir o seam atual. Não assumir que 42X2 é a autoridade viva.

A 086 nunca deve reativar código histórico só para permitir UI human send.

---

# 13. LANGGRAPH — INTERRUPTS

Documentação atual do LangGraph:

`interrupt()`:

- pausa execução;
- persiste estado via checkpointer;
- pode esperar indefinidamente;
- `thread_id` identifica o estado;
- `Command(resume=...)` entrega input humano.

Detalhe crítico:

> o node reinicia desde o começo quando retomado.

Consequência:

- side effects antes do interrupt devem ser idempotentes;
- preferir side effect depois;
- ou separar node.

Isso encaixa perfeitamente no Smith, que já usa LangGraph/checkpointer.

Não instalar nada.

---

# 14. INTERCOM — A REFERÊNCIA DE PRODUTO MAIS PRÓXIMA

Intercom Fin Procedures, atualizado em 2026, diferencia duas operações.

## Loop in teammate / agent

```text
Fin permanece dono
↓
pausa
↓
humano fornece resposta
↓
Fin continua
```

## Take over conversation

```text
humano assume
↓
Fin para
```

Isso é exatamente a distinção necessária para o AutoBrokers.

Verticalização:

```text
HUMAN REVIEW
vs
HUMAN TAKEOVER
```

O produto deles também inclui:

- structured fields to collect;
- timeout;
- escalation owner;
- office-hours pause;
- first response wins;
- retorno ao owner anterior.

Padrões úteis.

Não copiar UI.

---

# 15. TEMPORAL — REFERÊNCIA, NÃO DEPENDÊNCIA

Temporal modela:

```text
durable timer
signal
wait_condition
timeout
```

e consegue testar timeouts com time skipping.

A ideia mais útil:

> “esperar” é estado saudável e durável; um signal satisfaz ou um timer expira.

AutoBrokers já tem:

- Postgres;
- Work Runs;
- worker;
- queue;
- events.

Instalar Temporal criaria duas autoridades.

Nota:

```text
Temporal como runtime: 20/100
Temporal como referência de durable wait: 96/100
```

---

# 16. WHATSAPP BUSINESS POLICY

Política oficial atual:

- iniciar conversa via Business Platform exige approved Message Template;
- dentro de 24h da última mensagem do usuário, pode responder sem template;
- fora da customer service window, somente approved templates;
- automação durante a janela é permitida, mas precisa de escalada humana clara/direta.

Aplicação:

Follow-up engine precisa perguntar ao channel/provider:

```text
posso freeform?
preciso template?
estou bloqueado?
```

E não tentar burlar.

---

# 17. POR QUE NÃO HARDCODE META

AutoBrokers possui histórico com Evolution e pode ter outros providers.

Um provider não-oficial pode tecnicamente permitir algo que a Cloud API oficial não permite.

Mas “o SDK deixou” não significa “política homologada”.

Portanto o contrato é por:

```text
ChannelDeliveryCapability
```

e não:

```text
if whatsapp: ...
```

A Channel Fabric completa fica na SPEC-099.

---

# 18. POR QUE WAIT ≠ RETRY

Retry:

```text
nós falhamos
→ repetimos
```

Wait:

```text
estamos aguardando um ator/evento
→ trabalho está normal
```

Se misturarmos:

- dashboard diz “erro” onde existe espera;
- métricas de failure aumentam;
- retries podem repetir side effects;
- scheduler trata cliente como falha de sistema.

Durable Wait deve existir separado.

---

# 19. POR QUE `work_waits` É ACEITÁVEL

Uma tabela filha de `work_runs` não vira runtime.

Ela não executa.

Só responde:

```text
o que estamos esperando?
até quando?
qual policy?
qual signal encerra?
```

A execução continua sendo Work Run/Smith/dispatch.

Analogia:

`work_events` não é runtime.

`work_waits` também não.

---

# 20. POR QUE UM SCANNER NO SMITH WORKER

Smith Worker já possui loops:

- outbox;
- consumo;
- órfãos;
- manutenção.

Já existe regra no próprio código:

> novas manutenções entram no loop existente; criar scheduler próprio seria motor paralelo.

Portanto durable waits devem entrar ali.

Se o Worker não estiver ativo:

não esconder.

Go-live depende da autoridade operacional estar rodando.

---

# 21. FOLLOW-UP É POLICY, NÃO AGENTE

LLM não é confiável para decidir relógio e recipient.

Exemplo de bug:

```text
“parece que faz tempo”
```

não é condição.

Policy recebe números/estados.

A LLM só cria linguagem depois de:

```text
SEND autorizado.
```

Isso reduz:

- spam;
- wrong recipient;
- drift;
- custo;
- dificuldade de teste.

---

# 22. FOLLOW-UP E O WAITING_ON

Uma das maiores melhorias é saber **quem precisa fazer algo**.

```text
waiting_on = customer
→ customer reminder pode fazer sentido

waiting_on = insurer
→ customer reminder pedindo resposta é absurdo

waiting_on = human
→ alert team; customer gets holding status

waiting_on = document
→ reminder sobre documento
```

Isso deve aparecer em métrica e UI.

---

# 23. FOLLOW-UP DEFAULTS

Tempos iniciais da Candidate Spec são propostas, não medições.

Por quê?

O repo possui poucas métricas históricas estruturadas de follow-up.

Escolher 17, 43 ou 120 minutos como “verdade científica” seria fingimento.

A SPEC fornece:

- profiles;
- limits;
- calibration step;
- safe defaults candidatos.

O warm-up/execução pode ajustar com evidência.

---

# 24. INSURER HUMAN BRIDGE

Quando a seguradora traz especialista humano:

há três opções:

```text
1. AI responde fato seguro
2. AI pausa e pede Human Review
3. humano toma o insurer-side interaction
```

A opção 2 evita entregar tudo para humano por qualquer pergunta fora da URA.

É ganho de automação.

---

# 25. POR QUE DIRECT HUMAN REPLY NO DASHBOARD É VALIOSO

Se seguro/homologado:

- não muda de ferramenta;
- Resume Pack ao lado;
- auditoria;
- identity;
- claim;
- timeline;
- Work Run continua.

Mas o canal atual precisa permitir.

Se não:

fallback no WhatsApp original é melhor do que construir um envio novo inseguro dentro da 086.

---

# 26. POR QUE RETURN_TO_AI PRECISA SER EXPLÍCITO

Um humano mandar uma mensagem não significa:

> “terminei, pode continuar”.

Ele pode estar:

- negociando;
- esperando resposta;
- escrevendo outra mensagem.

Auto-resume criaria dual voice.

Então:

```text
human sends
→ HUMAN continua

human clicks RETURN
→ reconcile
→ AI
```

---

# 27. RESUME PACK NÃO É MEMÓRIA

Não mandar Resume Pack para Memory Fabric automaticamente.

Ele é:

```text
operational checkpoint representation
```

Learning/memory é outra camada.

Eventos da 086 poderão alimentar Trajectory/Dreams depois.

---

# 28. PII — POR QUE REFERENCIAR

Assistência exige dados sensíveis.

Duplicar CPF/endereço no:

- Work Run;
- event;
- Resume Pack;
- notification;

multiplica superfície.

Melhor:

```text
field available + redacted display + source_ref
```

e JIT resolve valor real quando permissionado.

---

# 29. CONTROL EPOCH — ALTERNATIVAS

## A. somente `status`
Nota: 55/100

Não fecha stale process.

## B. `claimed_at` timestamp
Nota: 65/100

Relógio e comparação; menos explícito.

## C. UUID claim token
Nota: 88/100

Consegue equality fencing, mas não ordena eras.

## D. monotonic control epoch
Nota: 97/100

Simples no Postgres, fácil CAS, auditável.

Escolhido.

---

# 30. `work_waits` — ALTERNATIVAS

## A. `next_attempt_at`
Nota: 35/100

Semântica de retry errada.

## B. Redis TTL
Nota: 10/100

Perde verdade em restart/expiry.

## C. fields únicos no Work Run
Nota: 82/100

Mais simples; ruim para histórico/scopes múltiplos.

## D. child `work_waits`
Nota: 96/100

Histórico, indexável, signal, policy e reuso sem virar runtime.

Escolhido como preferência; warm-up pode refutar se schema atual já possui equivalente melhor.

---

# 31. LANGGRAPH REVIEW VS TAKEOVER

LangGraph `interrupt()` é perfeito para Review:

```text
pause
→ human input
→ resume
```

Takeover é diferente.

Não mantenha graph “esperando” enquanto humano conduz uma conversa indefinidamente se o executor não precisa.

O Work Run/control state é a verdade operacional.

Quando voltar:

adapter decide como reentrar.

---

# 32. TESTES DE TEMPO

Temporal mostra uma prática boa: time skipping.

Não precisamos instalar Temporal.

Nos nossos testes:

- injetar clock;
- policy recebe `now`;
- avançar tempo deterministically.

Evitar `sleep(3600)`.

---

# 33. FECHO / INACTIVITY

Intercom e outras plataformas distinguem resolution/handoff/inactivity.

Para seguro:

inatividade não pode ser usada cegamente.

Exemplo:

```text
segurado parou de responder
```

pode ser encerrável.

Mas:

```text
seguradora está procurando prestador
```

não é inatividade do cliente.

A wait reason precisa governar closure.

---

# 34. REFERÊNCIAS INTERNAS INSPECIONADAS

- SPEC-055
- SPEC-055 Execution Report
- SPEC-063 migration
- SPEC-085
- SPEC-085 Execution Report
- 085 migration
- `app/api/dashboard/acionamentos-travados/route.ts`
- `app/api/dashboard/conversas/[id]/route.ts`
- conversation claim migration
- `test_quem_fala_primeiro_cala_o_outro.py`
- `human_handoff.py`
- `handoff_watchdog.py`
- `test_o_humano_e_chamado_de_verdade.py`
- `dispatch-states.ts`
- `WorkRunService`
- `WorkQueue`
- `SmithWorker`
- follow-up auxiliary design report
- insurer WhatsApp outbox/gates report

---

# 35. REFERÊNCIAS EXTERNAS

## LangGraph — Interrupts
https://langchain-ai.github.io/langgraphjs/how-tos/edit-graph-state/

Usado para:
- pause/resume;
- same thread;
- idempotent side effects.

## LangGraph — Persistence
https://langchain-ai.github.io/langgraph/cloud/concepts/threads/

Usado para:
- checkpointer;
- thread-scoped continuity.

## Intercom — Human-in-the-loop approvals for Fin Procedures
https://www.intercom.com/help/en/articles/14468561-human-in-the-loop-approvals-for-fin-procedures

Usado para:
- review vs takeover;
- structured response;
- timeout;
- office hours;
- first response wins.

## Intercom — Escalation guidance
https://www.intercom.com/help/en/articles/12396892-manage-fin-ai-agent-s-escalation-guidance-and-rules

Usado para:
- ask for input vs escalation.

## WhatsApp Business Policy
https://whatsappbusiness.com/policy/

Usado para:
- 24h;
- templates;
- escalation paths.

## Temporal Python SDK
https://github.com/temporalio/sdk-python

Usado como referência:
- signal;
- durable timer;
- wait condition;
- timeout testing.

Não é dependência.

## Fencing token references

Padrão clássico de distributed systems:
- monotonically increasing era/token;
- stale holder rejected at resource/gateway.

Aplicação direta:
`control_epoch`.

---

# 36. O QUE NÃO USAR

| ideia | veredito |
|---|---|
| novo workflow engine | NÃO |
| Temporal runtime | NÃO |
| Redis como wait truth | NÃO |
| LLM decide timer | NÃO |
| auto-resume depois de human send | NÃO |
| follow-up Auxiliar como scheduler | NÃO |
| new Case Engine | NÃO |
| customer status sozinho como lock | NÃO |
| “release” atual = resume | NÃO |
| PII copiada no Resume Pack | NÃO |
| insurer skeleton antigo ativado sem homologação | NÃO |

---

# 37. GANHO ESPERADO

## Continuidade operacional
100/100

## Human takeover confiável
100/100

## Follow-up
99/100

## Experiência do operador
98/100

## Fundamento para Central/Operations
99/100

## Reutilização futura
99/100

## Complexidade adicionada
Alta, mas concentrada.

Veredito geral da SPEC:

# **100/100**

porque fecha uma lacuna entre:

```text
agente inteligente
```

e:

```text
operação que realmente termina trabalho.
```

---

# 38. O QUE O WARM-UP AINDA PRECISA RESPONDER

1. O Smith Worker dedicado está ativo?
2. Qual status model real de Work Runs?
3. Quantos send seams existem?
4. Qual seam insurer-side está em produção?
5. Como `human_phase` é respondido hoje?
6. Há equivalente atual a work_wait?
7. Quais tables/status já guardam resolution reason?
8. Qual timezone/business hours authority já existe?
9. Quais providers WhatsApp estão ativos?
10. Como cada um reporta delivery?
11. O observer captura todos os `fromMe` relevantes?
12. Existe caso de wait paralelo legítimo?
13. Follow-up atual já dispara em algum lugar além do Auxiliar?
14. Quais referências a “SPEC-086” precisam ser reconciliadas?

---

# 39. VEREDITO

A SPEC-085 fez:

> **falha não fica silenciosa.**

A SPEC-086 precisa fazer:

> **mudança de mãos não quebra a continuidade.**

A arquitetura final é:

```text
WORK RUN
  │
  ├── CONTROL
  │     quem pode avançar
  │
  ├── WAIT
  │     o que esperamos
  │
  ├── RESUME PACK
  │     como continuar
  │
  └── EVENTS / EFFECTS
        prova do que ocorreu
```

Esse é o passo que transforma handoff de “fallback” em parte normal de uma operação híbrida IA + pessoas.
