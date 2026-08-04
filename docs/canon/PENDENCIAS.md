# Pendências — o que ficou de fora, e o que destrava cada coisa

> **Documento vivo.** Toda SPEC que terminar deixa aqui o que não coube nela.
> **Nada sai desta lista sem estar feito ou sem uma decisão registrada.**
>
> **v1.0 · 02/08/2026** · criado durante a SPEC-064, a pedido do Founder.
> Marcação de números: 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1).

---

## Como ler

| Coluna | O que significa |
|---|---|
| **Destrava** | o que precisa acontecer para sair desta lista |
| **Dono** | 🧑 Founder (ação física, decisão, terceiro) · 🤖 execução |
| **Custa se esquecer** | por que isto não pode virar dívida silenciosa |

---

# 🔴 BLOQUEIA O OBJETIVO Nº 1 — atendimento funcionando

## P-01 · A API da InfoCap devolve 500 no pós-login

📊 **Medido em 02/08/2026, onze vezes.** Senha errada → 400 em 0,87 s. Senha
certa → **500 em 16,2–16,5 s**. Toda outra rota da API responde em menos de
0,7 s. **A autenticação passa e algo depois dela estoura num timeout fixo.**

```
NÃO é bloqueio de seguranca  → bloqueio devolve 403/429 e e instantaneo,
                                e valeria tambem para a senha errada
NÃO é credencial             → senha errada da erro diferente e especifico
NÃO é permissão (p500/p501)  → falta de permissao devolve 403
É bug do fornecedor          → na montagem de sessao/perfil pos-login
```

**Consequência que ninguém tinha mapeado:** 📊 não existe tabela de apólice no
banco, e `POLICY_DATA_PROVIDER_SOURCE` **não é lido por nenhuma linha de
código**. A InfoCap é a única fonte de apólice do sistema. **Sem ela, o agente
de atendimento não confirma uma apólice, não responde cobertura e não aciona
corredor.**

- **Destrava:** telefonema à CorpAPI com o diagnóstico acima. É uma hora de
  trabalho para o time deles, não uma investigação.
- **Dono:** 🧑 Founder
- **Custa se esquecer:** bloqueia a SPEC-065 inteira e a capacidade do
  atendimento — não só um auxiliar.

## P-02 · A AutoFleet não tem conexão InfoCap

📊 Nenhuma linha em `tenant_connections` para ela. O atendente dela seria cego
para apólice mesmo com a API no ar.
- **Destrava:** cadastrar depois que a API voltar (hoje não daria para validar).
- **Dono:** 🧑 Founder

## P-03 · Espelho local da carteira

Enquanto a única fonte de apólice for uma API de terceiro, **um fornecedor fora
do ar cega o produto inteiro.** O espelho é a tabela que a SPEC-065 Bloco B já
manda criar — muda só a alimentação.
- **Destrava:** exportação da carteira do InfoCap **web** (que funciona) para
  semear, ou a API voltar.
- **Dono:** 🧑 Founder — precisa autorizar com as corretoras.
- **Estado:** 💬 conversado em 02/08; o Founder ainda não está autorizado a
  baixar os documentos.

---

# 🟠 P0 DE SEGURANÇA E ISOLAMENTO — SPEC-063

Todos medidos na auditoria de 02/08. **Nenhum está em produção porque nada está
pareado** — mas nenhum pode ser ligado antes de resolvido.

## P-04 · Resulta e AutoFleet compartilham o grupo de suporte humano

📊 `120363427334937446@g.us` nas duas. Dossiê com nome e CPF de segurado da
AutoFleet cairia num grupo que a Resulta lê. **CLAUDE.md §7 é literal: nenhum
dado atravessa tenants.**
- A SPEC-063 classificou como **P1**; a auditoria subiu para **P0**.
- **Acréscimo:** enquanto os dois apontarem para o mesmo grupo, o correto é o
  sistema **recusar-se a acionar** — não mandar para o lugar errado com aviso.
- **Dono:** 🤖 SPEC-063 Bloco B · o Founder autorizou apagar o compartilhamento.

## P-05 · A AutoFleet tem agente ativo sem prompt nenhum

📊 Agente `c95de02a` — `is_active = true`, `agent_enabled = true`,
**`agent_system_prompt = NULL`**. Com o defeito B1, é ele que responderia o
segurado: um agente ativo sem uma linha de instrução, sem nenhuma trava.
**Não está entre os doze bloqueios da SPEC-063.**
- **Dono:** 🤖 SPEC-063 Bloco A

## P-06 · O handoff mente ao segurado em todo caminho de falha

`tools/human_handoff.py` — quando o UPDATE não acha a conversa **e** quando
estoura exceção, devolve *"Um atendente foi solicitado."* **Sucesso declarado
em cima de falha.**
- **Regra a cravar:** caminho de falha nunca afirma sucesso.
- **Dono:** 🤖 SPEC-063 Bloco B

## P-07 · O handoff escreve sem filtro de tenant

`.update({...}).eq("session_id", …)` — **sem `company_id`**. CLAUDE.md §7 exige
o filtro no service justamente para não depender de o `session_id` ser único.
- **Dono:** 🤖 SPEC-063 Bloco B

## P-08 · O vazamento de CPF tem dois caminhos

A SPEC aponta o prompt (`prompts.py`, literal). **Mas `infocap_tool.py` imprime
`CPF/CNPJ: {doc}` inclusive no ramo `client_facing`.** Quem consertar só o
prompt vai achar que resolveu.
- **Dono:** 🤖 SPEC-063 Bloco A

---

# 🟡 A MÁQUINA QUE RODA E NINGUÉM OBSERVA

## P-09 · Um Work Run pode entrar na fila e sumir para sempre

📊 Dois `intelligence.detect_signals` em `queued` desde 28 e 30/07, com
`lease_owner`, `heartbeat_at` e `next_attempt_at` **todos nulos** — nunca foram
arrendados. E a regra `operacao.work_run_travado` **rodou e não pegou nenhum
dos dois.**

> A SPEC-055 entregou fila durável. **Durável não é o mesmo que observável.**

- **Destrava:** alarme de abandono para `queued` sem lease além do prazo.
- **Dono:** 🤖 — proposto para a SPEC-068 (prontidão).

## P-10 · O observador capturou tudo e não classificou nada

📊 `attendance_sessions.insurer_key` é **NULL em 100% das 8.872 sessões**.
`ramo` e `servico` idem. A SPEC-063 F.2.1 diz que "as 69.150 transcrições dizem
quais seguradoras são" — **as cartas dizem; a tabela de sessões não.**
- **Custa se esquecer:** qualquer análise por seguradora sobre atendimento
  precisa re-analisar, não consultar.

## P-11 · 70.576 linhas de backup sem política de retenção

📊 `attendance_transcripts_copias_removidas_20260728` (58.091) e
`observed_events_copias_removidas_20260728` (12.485). Backup de uma deduplicação
de 28/07 — sem dono, sem prazo, sem registro.

## P-12 · 120 tabelas com RLS ligado e nenhuma policy

📊 Medido nos advisors de segurança. **CLAUDE.md §7:** o backend usa service
role, então RLS sem policy não protege contra erro de filtro no código — mas
também não protege contra nada mais.
- **Dono:** 🤖 — território da SPEC-054/068, não da 064.

---

# 🟢 DEIXADO PRONTO E DESLIGADO — SPEC-064

O padrão: **construir inteiro, deixar desligado, registrar o que liga.**

## P-13 · E-mail: a chave do SendGrid está vazia

📊 `SENDGRID_API_KEY=` vazia no ambiente. O canal de e-mail do Bloco E nasce
**construído e desligado**: a política decide "e-mail", o executor registra
`sem_provedor_configurado` e o `delivery_status` **não fica `pending` mudo**.
- **Destrava:** uma chave. **Mas a decisão do provedor definitivo é da
  SPEC-069** — Amazon SES, US$ 0,10/mil, com isolamento de reputação por
  corretora. **Não vale amarrar no SendGrid agora.**
- **Dono:** 🧑 Founder (quando a 069 descongelar)

## P-14 · WhatsApp para briefing depende do governador de envio

A regra é **só manchete e link**, nunca o relatório inteiro. Mas o governador de
taxa é a SPEC-063 Bloco C e **ainda não existe**: 📊 hoje não há limitação de
envio em lugar nenhum.
- **Regra dura:** o briefing **não sai por WhatsApp antes do governador
  existir**, senão repetimos a rajada de 100 mensagens da cobrança.
- **Dono:** 🤖 SPEC-063 Bloco C

## P-15 · Artifact não tem visualizador na tela da corretora

Em Entregas, o item de tipo `documento` vindo de `artifacts` fica **sem link**
(`href: null`): a rota de leitura de artifact é da SPEC-057 e só existe no lado
da plataforma.
- **Custa se esquecer:** o entregável de primeira classe do produto aparece na
  lista e não abre.

## P-16 · Duas telas de execução ainda moram fora da rota do Auxiliar

`galeria/follow-up-whatsapp` (407 linhas) e `galeria/resumo-atendimentos` (347).
**Não são duplicata de descrição — são telas de execução com API própria, e
funcionam.** São alcançadas pela ficha do Auxiliar (`tela_de_execucao`), mas o
lugar delas é sob `/dashboard/auxiliares/[slug]/`.
- **Custa se esquecer:** o teste só impede a **terceira**; estas duas
  continuam sendo o precedente.

## P-17 · A verdade sobre conexões mora em três tabelas

`tenant_connections` (o caminho novo) · `portal_accounts` (o portal worker) ·
`integrations` (o WhatsApp, anterior ao conceito de conector).
`conexoesDaCorretora()` lê as três **de propósito** — ignorar qualquer uma faria
a tela dizer *"não conectado"* para quem já fez o trabalho.
- **Destrava:** unificação, **sem apagar nenhuma antes de a nova provar que lê
  tudo.**

## P-18 · Duas tabelas de auxiliar sem escritor

📊 `auxiliary_events` = 0 (o `evento()` nunca é chamado) ·
`auxiliary_template_releases` = 0 (lido pelo código, nunca escrito). E
`tenant_auxiliaries.health` / `.current_revision` não são escritos por ninguém.
- **Recomendação registrada:** `auxiliary_events` ganha escritor — é o que
  alimenta o histórico por Auxiliar. **Regra: nenhuma tela mostra coluna
  alimentada por tabela vazia.**
- **Dono:** 🤖 SPEC-064 Bloco H

## P-19 · Os dez Auxiliares "em breve" são rascunho

O Founder foi explícito: são incógnitas até sabermos se entregam valor. Todos
já têm nome, headline, o que fazem, de onde tiram o dado e **o que falta para
existir** — e **nenhum promete número** (CLAUDE.md §12.1).
- **Destrava:** revisão um a um, quando houver dado real para medir. **Cada um
  pode ser melhorado, substituído ou retirado sem afetar os que funcionam.**
- **Dono:** 🧑 + 🤖, um por vez.

---

## P-29 · A SPEC dos portais — cobrança em todas as seguradoras

**Decidida em 02/08/2026 pelo Founder, para depois destas SPECs.**

📊 O produto tem **17 portais** cadastrados — 15 de corretor (um por
seguradora) e 2 de vidros. **Só a Allianz tem jornada de cobrança
implementada.**

```
1. o Cobrador da Allianz é o MOLDE — ele funciona ponta a ponta
2. cada seguradora nova é uma jornada no portal_worker, mesmo desenho
3. ANTES de escrever robô, conferir se ela tem API (é para isso que
   os 33 endereços de API do catálogo servem — P-26)
4. cobrança primeiro; renovação depois, se a estrutura sustentar
```

> **Regra que não muda:** cobrança de outra seguradora **não é Auxiliar novo**.
> É o mesmo "Cobrança Feita" com mais um portal na configuração da corretora.
> Um auxiliar por seguradora seria a bagunça voltando pela porta dos fundos.

**E o portal de vidros** já existe (2 portais, `cred_kind: public`) e faz parte
do atendimento de assistência. Entra na mesma revisão.

- **Destrava:** decisão do Founder de abrir a SPEC.
- **Detalhe completo:** [`PORTAIS-E-CORREDORES.md`](PORTAIS-E-CORREDORES.md)

## P-26 · O catálogo de 189 portais está mapeado e não é usado

📊 `lib/attendance/portal-global-catalog-seed.ts` — **8.696 linhas, 189 portais
de seguradora** levantados de pesquisa oficial: Allianz, Porto, HDI, Sompo,
Mapfre, Bradesco, Chubb, Azul, Junto, Liberty, Alfa e Open Insurance. Cada um
com URL de login, métodos de autenticação, perfil de desafio (captcha/MFA/OTP)
e jornadas suportadas.

**Ele sobreviveu à remoção do Portal Browser de propósito** — o simulador era
código morto; o catálogo é pesquisa. Mas hoje **nada o consome**.

> O Founder foi explícito: depois destas SPECs, repetir na Porto, HDI, Tokio e
> Yelum o que já funciona na Allianz. **Este catálogo é o mapa desse
> trabalho** — e a ordem de prioridade já está medida (P-27).

- **Destrava:** a SPEC de novos portais.
- **Custa se esquecer:** refazer o levantamento de 189 portais do zero.

## P-27 · A ordem dos corredores, medida

📊 Medido no acervo real (cartas de auto por seguradora), 02/08/2026:

```
Allianz .... 439      (+178 residencial +91 outros = 708 no total)
Yelum ...... 276
Tokio ...... 251
HDI ........ 184
Youse ...... 177      ← não estava na lista do Founder
Porto ...... 165      ← é a 6ª, não a 2ª
Bradesco ... 116
Mapfre ..... 100
```

**A lista de seguradoras do Founder estava certa; a ordem não.** E a SPEC-063
F.2.1 afirma que "as 69.150 transcrições dizem quais são" — 📊 **elas não
dizem**: `attendance_sessions.insurer_key` é NULL em 100% das 8.872 sessões
(P-10). Quem diz são as cartas.

- **Destrava:** a SPEC-063 Bloco F.
- **Dono:** 🤖

## P-28 · A capability de portal existe e ninguém a exerce

📊 Medido: `billing_collection.py` **não consulta o Capability Resolver**. As
cinco `operational.portal.*` são declaradas e nunca checadas — o Cobrador entra
no portal por fora do modelo de governança.

A SPEC-064 consertou a **declaração** (o provider agora nomeia quem trabalha, e
o resolver enxerga `portal_accounts`), então ela deixou de mentir. **Falta
ligar a checagem.**

> Enquanto ninguém checar, a capability é documentação. No dia em que alguém
> ligar sem antes conferir, o Cobrador para — e a causa vai parecer
> desconexa.

- **Destrava:** o Tool Gateway sair de `shadow` (📊 `TOOL_GATEWAY_MODE=shadow`).
- **Custa se esquecer:** é uma armadilha armada, não uma dívida passiva.

---

# 🔵 REGISTRADO PARA O MOMENTO CERTO

## P-20 · Conversas de vários WhatsApps

Quando a cobrança tiver número próprio, o mesmo cliente terá conversa em dois ou
três números. **Registrado inteiro em `SPEC-069 §A.2.1`**, com a regra que
resume: *o número é por onde a mensagem passou, não quem é o cliente.*
- **Gatilho:** o Bloco A da SPEC-069.

## P-21 · O esquema de comissionamento por produto

📊 Cinco parcelas vencidas medidas na Allianz: as duas com comissão zero são as
**últimas** (10/10 e 4/4); a 2/7 paga 4,66% e a 3/10 paga 0,03% — **150× de
diferença entre duas parcelas do meio.** 💭 A antecipação explica parte e não
explica tudo.
- **Custa se esquecer:** é o coração do Caça-Comissão. Um auxiliar que
  **descobre a regra** vale mais que um que procura "comissão zerada".

## P-22 · A coluna viva de sinistralidade do SES

A pesquisa afirma que a coluna documentada está morta desde 2013 e que a viva é
`sinistro_ocorrido`. **Não desmenti — não consegui confirmar:** a URL que testei
devolveu 404.
- **Custa se esquecer:** a SPEC-066 inteira assenta nisso.

---

# ⚫ HIGIENE

## P-23 · A `main` está 117 commits atrás

📊 **Nada deste trabalho está em produção — nem o conserto de segurança da
Fábrica.** O EasyPanel constrói a `main`.
- **Destrava:** merge com o gate final da SPEC (CLAUDE.md §13.8).
- **Dono:** 🧑 Founder decide quando · 🤖 prepara.

## P-24 · Binários soltos no repositório

📊 `exp.bin` (5,2 KB) e `mensal.xlsx` (6,1 KB) na raiz, commitados sem contexto.

## P-25 · `MIGRATIONS-AUTHORITY.md` §9 está desatualizado

Diz *"enquanto P1 estiver pendente, nenhum write em produção é autorizado"* —
mas **P1 foi resolvida por D11 em 25/07**. Quem ler o documento hoje conclui que
está proibido de aplicar migration.
- **Dono:** 🤖 SPEC-064 Bloco J (documentação).

---

## Índice rápido

| # | Pendência | Dono | Bloqueia |
|---|---|---|---|
| P-01 | InfoCap 500 | 🧑 | atendimento + SPEC-065 |
| P-02 | AutoFleet sem InfoCap | 🧑 | atendimento da AutoFleet |
| P-03 | Espelho da carteira | 🧑 | independência de terceiro |
| P-04 | Grupo de suporte compartilhado | 🤖 | ligar o atendimento |
| P-05 | Agente sem prompt | 🤖 | ligar o atendimento |
| P-06 | Handoff mente na falha | 🤖 | ligar o atendimento |
| P-07 | Handoff sem filtro de tenant | 🤖 | CLAUDE.md §7 |
| P-08 | CPF vaza pela tool | 🤖 | ligar o atendimento |
| P-09 | Work Run some sem alarme | 🤖 | confiança na fila |
| P-10 | Sessões sem classificação | 🤖 | análise por seguradora |
| P-11 | 70.576 linhas de backup | 🤖 | — |
| P-12 | RLS sem policy em 120 tabelas | 🤖 | SPEC-068 |
| P-13 | Chave de e-mail | 🧑 | canal de e-mail |
| P-14 | Governador de envio | 🤖 | briefing por WhatsApp |
| P-15 | Visualizador de artifact | 🤖 | abrir o entregável |
| P-16 | Duas telas fora do lugar | 🤖 | — |
| P-17 | Três tabelas de conexão | 🤖 | — |
| P-18 | Tabelas de auxiliar sem escritor | 🤖 | histórico por Auxiliar |
| P-19 | Dez Auxiliares em rascunho | 🧑+🤖 | valor real |
| P-20 | Conversas multicanal | 🤖 | SPEC-069 |
| P-21 | Comissionamento por produto | 🤖 | Caça-Comissão |
| P-22 | Coluna do SES | 🤖 | SPEC-066 |
| P-23 | `main` atrasada | 🧑 | **tudo em produção** |
| P-24 | Binários soltos | 🤖 | — |
| P-25 | Doc de migrations desatualizado | 🤖 | — |
| P-26 | Catálogo de 189 portais sem consumidor | 🤖 | novos portais |
| P-27 | Ordem dos corredores (medida) | 🤖 | SPEC-063 F |
| P-28 | Capability de portal não é exercida | 🤖 | Tool Gateway |

---

## SPEC-063 — o que ela deixou (03/08/2026)

### 🧑 Do Founder

| # | Pendência | O que destrava | O que custa esquecer |
|---|---|---|---|
| **P-30** | **Separar o grupo de suporte humano** — Resulta e AutoFleet dividem `120363****446@g.us` | dar um destino próprio a cada uma em Personalização → Suporte | **o handoff está RECUSADO nas duas** por segurança. É fail-closed, não bug: o dossiê leva CPF do segurado |
| **P-31** | `INSURER_DISPATCH_LIVE=true` em produção — o portão de envio **real** está aberto | decidir se fica aberto antes do go-live | o que segura hoje é `DISPATCH_FINALIZE_MODE=test` + allowlist + agentes desligados. Nenhuma trava por corretora ou por corredor |
| **P-32** | `CARTOGRAPHER_MODE=1` — o Cartógrafo **envia WhatsApp real** a seguradoras para mapear URA | decidir se continua ligado | mensagem nossa chegando em seguradora sem ninguém esperando |
| **P-33** | Credenciais **Twilio** no ambiente, sem uma linha de código que as use | decidir se telefonia entra no roadmap | é o que falta para a **Youse** ter corredor (ela não tem WhatsApp de assistência) |

### 🤖 De execução

| # | Pendência | O que destrava |
|---|---|---|
| **P-34** | Varredura periódica de acionamento órfão | hoje dispara 1× por processo, no primeiro cache-miss. Falta **uma linha** no laço de manutenção do worker |
| **P-35** | Migration `20260803_06` (índice do Work Run de acionamento) escrita e **não aplicada** | usa `CONCURRENTLY`, precisa rodar fora de transação |
| **P-36** | Três outros caminhos escrevem `agent_system_prompt` **sem o portão** de prompt vazio | `blueprint-studio-store`, `release-rollout-store`, `tenant-agent-store`. Foi por um deles que a AutoFleet zerou |
| **P-37** | `agent-health.ts` detecta agente ausente e duplicado, **não detecta agente mudo** | foi por isso que ninguém percebeu a AutoFleet |
| **P-38** | `unknown` (canal sem confirmação) não está em `ESTADOS_RUINS` | canal demovido para de mentir nas telas mas **não gera sinal** no briefing |
| **P-39** | O freio de emergência de envio **não tem botão** | `parar_envios()`/`retomar_envios()` funcionam, só por console |
| **P-40** | O grito do acionamento órfão não vai por WhatsApp | vai para `work_events` e Atividades; o resolvedor de destino já está pronto ao lado |
| **P-41** | 3 variáveis do heartbeat fora do `.env.example` | `CHANNEL_HEARTBEAT_ENABLED/_INTERVAL_MINUTES/_STALE_MINUTES` |
| **P-42** | `AGENT_OS_TENANT_TIMEZONE` não está no `.env.example` | o governador lê com padrão `America/Sao_Paulo` |
| **P-43** | **GOLD-ELEC-007 nomeia um estado que não existe** — espera `ready_for_approval`, o contrato devolve `ready_to_send` | ou renomeia o código, ou reescreve o caso. Nome que não bate é como um golden deixa de pegar o defeito que existia para pegar |
| **P-44** | 5 dos 10 golden tests só são verificáveis **com modelo** | classificar linguagem natural. Declarado no próprio teste como lacuna nomeada |
| **P-45** | Os corredores recomendados em [`CORREDORES-QUE-PODEMOS-CRIAR.md`](CORREDORES-QUE-PODEMOS-CRIAR.md) | vidros de auto (10 seguradoras) · pane seca · encanador · residencial Porto |

### SPEC-063 Bloco F — os corredores (03/08/2026)

| # | Pendência | Dono | O que destrava |
|---|---|---|---|
| **P-46** | **O motor não consome `encaminha` ainda.** `detect_referral_step()` e `subservice_referral()` existem e estão provados, mas `handle_insurer_message` não fecha a sessão como *resolvido por encaminhamento* nem entrega o link ao segurado. Hoje o passo é `noop` (correto — não responde à URA), e o caso fica aberto até o watchdog | 🤖 | ~30 linhas em `insurer_dispatch_service` |
| **P-47** | `infer_ramo_servico` devolve `"residencial"` genérico para *"encanador"* e *"eletricista"* — e `"residencial"` não é subserviço de nada, então cai em `subservico_invalido` | 🤖 | o classificador precisa nomear o subserviço. Não foi criado alias porque adivinhar qual dos cinco seria chute |
| **P-48** | `unknown_step_policy` e `coverage_guardrails` são **campos declarativos sem consumidor** | 🤖 | nascem anotados, não escondidos (CLAUDE.md §11.1) |
| **P-49** | **Nenhum dos corredores novos foi exercitado contra a URA real** | 🧑 | estão em modo teste com o freio; `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` não os inclui |
| **P-50** | **Vidros sem evidência em 7 seguradoras** — allianz, tokio, mapfre, yelum, hdi, alfa, bradesco | 🧑 | o Atlas precisa ver um atendimento de vidro nessas. Hoje elas caem em handoff, que é o certo |
| **P-51** | **Residencial sem evidência** em yelum, tokio, zurich, azul, alfa, mapfre. Bradesco só tem a entrada do menu (`*2.* Residencial`), sem subserviços | 🧑 | mesmo caminho: observação |
| **P-52** | **Cobertura de URA baixa limita o corredor**: 📊 Tokio 12%, Mapfre 25%, Zurich 28%, Yelum 34%, HDI 36%, Porto 37% | 🧑 | o pareamento da AutoFleet (auto/frota) é o que mais move esses números |
| **P-53** | **Twilio / telefonia** — credenciais no ambiente, zero código. É o que falta para a **Youse** ter corredor | 🧑 | sem prioridade agora, por decisão do Founder (03/08) |

### SPEC-063 Fase 0 — o que ficou esperando (03/08/2026)

| # | Pendência | Dono | O que destrava |
|---|---|---|---|
| **P-54** | **Re-sync do Atlas bloqueado** — os três observadores estão `disconnected`; o `history-sync` puxa da instância conectada | 🧑 | parear os WhatsApps. Runbook completo em [`RUNBOOK-RESYNC-DO-ATLAS.md`](RUNBOOK-RESYNC-DO-ATLAS.md), com a linha de base já gravada (947 cliques, 0 com id) |
| **P-55** | **20 eventos `source='live'` não são recuperáveis** por sync — nasceram do webhook | 🤖 | nada a fazer; **não apagar**. Daqui pra frente nascem certos |
| **P-56** | `evolution_inbound._text_from_message` lê `selectedButtonId` (d minúsculo) — não casa com o `selectedButtonID` real | 🤖 | mesmo defeito do observador, outro arquivo |
| **P-57** | Os 23 `flow_reply` do histórico têm `paramsJSON` com o schema do formulário — não são parseados no caminho do histórico | 🤖 | ganho real, mas tem dimensão de privacidade: avaliar antes |
| **P-58** | `rb_Ocupantes` id `4` tem **título vazio** na captura | 🧑/🤖 | uma nova captura com gestante resolve. Até lá o caso vira `missing` e exige clique humano — seguro, mas bloqueia |
| **P-59** | Os 41% de cobertura da HDI são **projeção**, não número gravado | 🤖 | sai do passo 6 do runbook (retecer) |
| **P-60** | O passo 7 do portal (escolha de loja/domicílio) **nunca foi exercitado** — em 39 acionamentos, `has_protocol` nunca foi True | 🤖 | um acionamento com `confirm=True` mostra o que há lá |
| **P-61** | Variante e lado de peça no portal (`RETROVISOR ELÉTRICO` vs `MANUAL`, porta direita/esquerda) | 🤖 | o segurado não diz; adivinhar troca a peça. Hoje para com a lista, que é o certo |

---

## P-62 · Construir a imagem `0.7.2-autobrokers.2` do Evolution GO 🤖→🧑

**O que é.** O patch `0005-send-interactive-response` abre a rota que faltava
(`POST /send/interactiveResponse`). O código está escrito, os cinco patches
aplicam limpos no commit fixado, e o teste que prova a montagem já existe.

**O que destrava.** O envio de resposta de formulário nativo — 📊 4 seguradoras
o usam (Porto 12 · HDI 6 · Azul 4 · Yelum 2) e 460 apólices de auto (26,9% da
carteira) estão nessas seguradoras.

**Por que ainda não foi feito.** Não há Go nem Docker nesta máquina: **quem
compila é o build**. Até ele rodar, o código nunca passou por um compilador.

**O que custa esquecer.** Os corredores dessas 4 seguradoras já existem e não
rendem. É trabalho pronto parado.

## P-63 · A prova de transporte precisa de UM telefone pareado 🧑

**O que é.** Mandar a resposta de um número nosso para outro número nosso e
comparar o que chega, campo a campo, com o clique humano de 18/07.

**O que destrava.** A diferença entre "escrevemos" e "funciona".

**Por que não dá para pular.** 📊 Temos **uma única** captura real de um humano
respondendo este formulário — as outras 22 foram gravadas vazias pelo defeito
que a Fase 0.1 consertou. Um acervo de um não permite conferir hipótese; permite
só comparar. O loopback é a segunda amostra, e é nossa.

**O que custa esquecer.** Ligar sem provar gasta a única janela do atendimento
real: a URA da HDI encerra em 12 minutos, e uma resposta em formato errado é
descartada **em silêncio** — sem erro, sem reenvio.

## P-64 · `version` do envelope continua HIPÓTESE 💭

**O que é.** A captura de 18/07 **não tem** o campo `version`. Não sabemos se o
remetente não o mandou ou se nosso observador não o leu — as duas explicações
cabem, e a captura não escolhe entre elas.

**Como está tratado.** O Go **omite** quando ninguém pede, e o Python passa
adiante o que lhe derem. Ninguém finge saber.

**O que destrava.** O loopback (P-63): ele mostra o que um cliente real põe ali.

---

## P-65 · 🔴 A tela de pareamento diz uma coisa e liga outra

**O que aconteceu, 03/08/2026 20:15–20:24.** O Founder abriu "Conectar WhatsApp
da corretora" no painel e escaneou. 📊 Quem conectou foram as instâncias do
**Observador** (`ab-obs-*`), não as de atendimento (`ab-*`), que seguem
`disconnected` — confirmado pelo batimento às 20:25:35.

O Observador nasce com escopo `insurers_and_clients`. Resultado: **2.556
transcrições e 745 sessões** de 630 contatos pessoais entraram em
`attendance_transcripts` — a tabela que alimenta o destilador de cartas.

**Contido e revertido.** Escopo fechado nas 3 integrações, API reiniciada para
matar o lote em voo, dados apagados. 📊 Restaurado ao número exato de antes
(69.150 transcrições · 8.872 sessões) e **nenhuma carta foi gerada**
(`knowledge_cards` parou em 30/07, zero no período).

**A causa — CORRIGIDO em 03/08 depois de ler o código.** Minha primeira leitura
dizia "a tela mente". Está errado, e ao contrário: **o texto da tela está certo
e o nome interno é que envelheceu.**

📊 `app/api/dashboard/whatsapp-channel/route.ts:9` — `const PURPOSE = 'observer'`,
usado nas 9 chamadas da rota. **Não existe nenhum caminho na UI que pareie
`attendance`.** O `/setup`, que tem esse padrão, não tem quem o chame.

E 📊 `observer_intake.py:483-523` mostra por que isso não é um bug de
comportamento: a instância chamada "observer" **vira o canal de atendimento
sozinha** quando o agente é ligado, no mesmo número, sem re-parear. O comentário
no código é literal: *"agente LIGADO → captura e o evento SEGUE para o pipeline"*.
A tela promete exatamente isso: *"ligar o agente ativa as respostas automáticas
neste mesmo número"*.

**Então o defeito real é o escopo, não o rótulo.** Aquele pareamento captura
tudo que não for grupo, e ninguém é avisado disso antes de escanear.

**O que destrava.**
1. a tela declarar o que será capturado, com as palavras certas, ANTES do QR;
2. escolher o escopo na hora do pareamento, e não depois;
3. renomear `observer` para o que a coisa é — ou aceitar o nome e documentar,
   mas não deixar os dois significados convivendo.

**O que custa esquecer.** Da próxima vez pode ser o telefone pessoal de um
corretor de verdade — e aí não é reversível com um DELETE nosso.

## P-66 · O payload cru do histórico fica 7 dias no Redis 🤖

📊 `history_ingest.py` guarda o primeiro sync inteiro em Redis, até 200 KB, TTL 7
dias. O DELETE do Postgres **não** o alcança. Vence sozinho em 10/08/2026.

**O que destrava.** Limpar a chave, ou aceitar o vencimento. Não há PII em
índice nem em RAG — é cache bruto, não consultável.

---

## P-67 · 🔴 Conversa pessoal no número da corretora não pode virar carta

**O Founder levantou, e ele está certo.** O WhatsApp de uma corretora é um
telefone de gente. No meio das conversas com segurado vão existir
*"oi amor, quando você vai no mercado?"*, o grupo do prédio, o cunhado pedindo
dinheiro. **Não é caso de exceção — é o normal de qualquer telefone de trabalho
no Brasil.**

Hoje o sistema separa por **origem**: se o número do outro lado está na lista
das 12 seguradoras, vai para o Atlas; se não está e o escopo é total, vai para
`attendance_transcripts` — e de lá o destilador faz carta. **A separação é por
QUEM falou, nunca por SOBRE O QUE se falou.**

📊 O que já existe de proteção, medido: `knowledge_cards` tem **310 cartas
`rejected_pii`** e **5 `rejected_absoluto`**. Ou seja, há um filtro e ele
reprova — mas ele mira em **dado pessoal** (CPF, telefone, endereço), não em
**assunto que não é seguro**. Uma conversa doméstica sem nenhum CPF passa nesse
filtro sem disparar nada.

**E a curadoria publica `pending_review → published` sem aprovação humana.**
Então o caminho inteiro existe: conversa doméstica → transcrição → carta →
RAG consultável pelo agente. Nada nesse caminho pergunta "isto é sobre seguro?".

**O que destrava.** Uma prova de pertinência ANTES de virar carta:
1. o destilador recusar conversa que não trate de seguro, sinistro,
   apólice, acionamento ou atendimento — e o teste ter de mostrar que ele
   recusa mesmo, com um exemplo doméstico real;
2. carta nova de origem não-seguradora nascer `pending_review` de verdade,
   com um humano aprovando, até a prova acima existir;
3. medir quantas das 9.699 cartas atuais vieram de conversa não-seguradora, e
   revisar essas.

**O que custa esquecer.** O agente de uma corretora respondendo a um segurado
com conhecimento destilado da vida particular do corretor. Não é um erro
técnico que se explica — é um constrangimento que não se desfaz.

> Relacionado a [P-65] (a tela não diz o que captura) e [P-66] (payload cru no
> Redis). Os três nasceram do mesmo pareamento de 03/08.

---

## P-68 · ⚖️ Conflito canônico: "observer nunca envia" vs. o que o código faz

📊 `SPEC-069-canais-definitivos.md:57` diz *"guarda dura: observer nunca é canal
de saída"*. 📊 `integration_service.py:192-199` implementa
`PROPOSITOS_QUE_NUNCA_ENVIAM = {"observer"}` — mas ela só é consultada em **3
lugares**, todos de envio **frio** iniciado pela plataforma (alerta do Vigia,
follow-up, cobrança).

📊 O caminho **reativo** — responder quem escreveu — não passa por ela:
`webhook.py:276-278` fixa a integração que RECEBEU e `webhook.py:710-712`
responde por ela mesma. Com o agente ligado, **a resposta ao segurado sai pelo
`ab-obs-*`**. Isso é por desenho: é a promessa da tela.

**Não é bug — é uma frase mais absoluta que o código.** E é defensável: o risco
de bloqueio do WhatsApp está no envio frio, não em responder quem falou com você.

**O que destrava.** 🧑 Decidir qual vence antes do piloto e alinhar os dois:
ou a SPEC passa a dizer "observer não INICIA conversa", ou o código passa a
proibir de verdade — e aí a promessa de "mesmo número" cai junto.

**O que custa esquecer.** Alguém lê a SPEC, conclui que aquele número é mudo
para sempre, e desenha em cima disso.

---

## P-69 · 🧑 Um clique: reteceer os mapas do Atlas

**Um clique, e a cobertura de 10 seguradoras melhora sem escrever uma linha.**

📊 Os mapas em `ura_maps` são de **29/07/2026**. O mecanismo que desconta a
NÃO-ROTA da cobertura — pesquisa de satisfação e lista gerada pelo cliente — é
de **02–03/08**. **Os mapas são anteriores ao conserto.**

📊 Verificado contra o texto literal das duas telas de pesquisa da HDI: o
detector devolve `pesquisa_de_satisfacao` e **zero opções** nas duas. Ele está
certo; os mapas é que estão velhos.

Só na família HDI+Yelum são **20 opções fantasmas** (2 pesquisas × 5 notas × 2
seguradoras) contadas como "não cobertas" sem que exista trabalho a fazer.
Elas rebaixam os 36% e 34% e escondem qual é a cobertura real.

**O que destrava.** Painel → **Atlas** → botão **"Tecer mapas"**. É idempotente
e reprocessa o histórico inteiro. **Não depende de pareamento nenhum** — lê o
acervo que já temos.

**O que custa esquecer.** Toda decisão de prioridade da Fase 3 usa a cobertura
como número. Com 20 opções fantasmas dentro dela, a prioridade sai errada — e
o esforço vai para onde não precisava.

---

## P-70 · 🟠 O Follow-up pergunta e ninguém escuta

**O Founder olhou a Central de Agentes e perguntou se o Follow-up é legado,
duplicado, quebrado, ou se vale eliminar. A auditoria respondeu: nenhum dos
quatro. É metade construída, e a metade que existe é boa.**

### O que ele faz bem

📊 `_followup_schedule` agenda 45 min **depois do ETA real do prestador** — não
depois do protocolo — com janela educada 8h30–21h. Isso é produto pensado, não
encanamento. E é o **único** componente do sistema que fala com o segurado por
iniciativa própria depois do acionamento. Nada mais faz isso.

### O que está quebrado

```
1  a resposta do cliente NÃO É LIDA por ninguém
   a chave do acionamento é o telefone da SEGURADORA; o do cliente
   nunca casa, e a resposta cai no agente comum, que não sabe do que
   se trata. 📊 zero leitores no backend inteiro

2  o timer é apagado por baixo
   `_start_next_in_queue` roda na MESMA transição que criou o timer, e
   `start_live_dispatch` trata `monitoring` como sessão velha e limpa.
   Com fila na mesma seguradora, o follow-up morre ao nascer

3  é o único envio frio a segurado que fura o governador
   não respeita a parada de emergência, não conta nos tetos, não entra
   em `platform_sends`. E plugar direto no canal governado QUEBRA:
   `client_busy` considera ocupada toda sessão em `monitoring` — que é
   exatamente o estado em que ele roda. Precisa de exceção explícita

4  o "encerramento" não encerra
   só manda texto; a sessão fica viva até o TTL de 24h

5  a mensagem não entra no transcript
   o Espelho, a timeline e o dossiê não a mostram — o Vigia faz isso, ele não

6  zero teste
   nenhum teste chama `check_dispatch_followups`
```

### 📊 E o card verde era falso — isto já foi corrigido

O critério da Central é só *"o laço rodou nos últimos 15 min"*. O pulso é dado
**mesmo quando a varredura não acha nada**. "SAUDÁVEL · 0 ações" queria dizer
apenas *"rodei e não encontrei nada"*.

A descrição no catálogo passou a dizer a verdade em 03/08. **Um card amarelo
verdadeiro vale mais que um verde falso.**

### DUPLICAÇÃO — a resposta à pergunta do Founder

**Não duplica função.** 📊 O Vigia trata `monitoring` como estado terminal e se
cala exatamente onde o Follow-up age. E os públicos são opostos:

```
VIGIA      fala com a SEGURADORA e com o suporte da corretora
FOLLOW-UP  fala com o SEGURADO
```

**Duplica mecânica.** Dois jobs (20s e 60s) varrem o mesmo keyspace, com o mesmo
parsing e as mesmas chamadas. Uma terceira varredura existe para a tela.

**E há três homônimos que confundem** e não têm relação: o auxiliar comercial
"Follow-up de WhatsApp" (proposta), o card "Follow-up de Propostas · Em breve",
e a fase `follow_up` de `corridor_templates` — 📊 esta última com **zero
leitores em qualquer linguagem**.

### A recomendação

**Manter e completar, fundindo a MECÂNICA e mantendo os NOMES separados.**

Um varredor único que percorre `dispatch:active:*` uma vez e roteia por estado:
vivo → Vigia · `monitoring` → Follow-up. Mata a varredura dupla, mantém dois
cards na Central (papéis distintos), e cria o lugar natural para o passo 5 —
quando o cliente responde *"não chegou"*, quem já sabe alertar o suporte e
montar dossiê é o Vigia.

**O que destrava:** os 6 itens acima, na ordem. O item 2 vem primeiro — sem ele
os outros não importam, porque a mensagem nunca sai.

**O que custa esquecer:** o ciclo termina em *"aqui está seu protocolo"* e a
corretora nunca sabe se o serviço foi prestado. É a diferença entre acionar e
resolver.


---

## ✅ FECHADAS EM 03/08/2026 — o dia do formulário nativo

Registro do que saiu desta lista, com o que provou cada uma.

| # | O que era | Como fechou |
|---|---|---|
| **P-68** | conflito canônico "observer nunca envia" | decisão do Founder → **D-Canal-01**: observar é função muda; atender fala e nasce desligado |
| **P-69** | mapas do Atlas anteriores ao conserto da não-rota | 🧑 o Founder clicou em **Tecer mapas**. 📊 HDI 36→41%, Yelum 34→36%, Allianz 75% |
| **P-70 (2,3,5)** | o timer do Follow-up morria ao nascer; a pergunta não deixava rastro | `monitoring` com compromisso pendente deixa de ser sessão velha; a pergunta entra em `platform_sends` e no transcript |

### E o que a auditoria de ponta a ponta fechou no mesmo dia

```
R1   protocolo sozinho já avisa o segurado (o residencial da Allianz não
     captura eta nem link — a pessoa nunca sabia que o serviço foi aberto)
R2   sem protocolo, a retomada roda; COM protocolo, não — reabrir mandaria
     um segundo prestador para o mesmo carro
R3   o flow_token atravessa: o webhook copia o `interactive` e o buffer
     não o apaga na rajada
R4   tudo que o motor diz ao cliente vira rastro; falha de aviso alerta
     o suporte em vez de sumir no log
R5   o encerramento ENCERRA: marca resolvido e libera a sessão
R5b  má notícia também passa — cancelado, sem prestador, fora da área
```

### E os achados da revisão dos 13 corredores

```
🔴 1  o freio não disparava em 28 das 33 vezes (negrito do WhatsApp no
      *para*), no PONTO DE NÃO-RETORNO. E o CI estava verde porque a
      fixture escrevia a frase sem os asteriscos
🔴 2  `pessoa_no_local` era exigido por passos e não declarado — a sessão
      nascia "pronta" e travava no meio. O PORTÃO foi consertado, não os
      três passos: fecha a classe inteira
🔴 3  apelido de subserviço não resolvia na abertura (hidráulica,
      desentupidor, eletrodoméstico)
🟠 4  vidro exigia quem acompanha no local — vidro é agendado
🟠 5/6 três noop fora de ordem sombreavam o menu re-perguntado
🟠 7  `human_phase_guidance`: 4 blocos de orientação, zero leitores
🟡 10 instruções de guincho iam para pneu, bateria e chaveiro
```

**Restam de P-70:** o item 3 (ler e classificar a resposta do cliente e agir) e
o item 6 (teste com relógio de mentira). O item 5 — passar pelo canal governado
— continua aberto **de propósito**: exige exceção explícita para `monitoring`,
senão `client_busy` adia o follow-up para sempre.

---

## P-71 · 🧑 AMANHÃ: o acionamento REAL da HDI, em modo teste

**É a última coisa não provada da cadeia inteira, e não dá para provar sem ela.**

📊 Provamos que a mensagem de resposta a formulário **sai e o WhatsApp aceita**
(`Type: "InteractiveResponseMessage"`, entre dois números nossos). **Não**
provamos que a **seguradora** aceita essa resposta no meio de um atendimento.
São coisas diferentes, e só uma seguradora de verdade responde a segunda.

### O passo a passo

```
1  🧑  parear os WhatsApps das corretoras (Amandus, Resulta, AutoFleet)
2  🤖  conferir DISPATCH_FINALIZE_MODE=test e a allowlist
3  🧑  abrir conversa com a HDI pelo número da corretora
4  🤖  andar o menu até o formulário nativo chegar
5  🤖  responder AQUELE formulário — não um fabricado
6  🤖  ler o que a HDI devolve
```

**O freio segura antes do ponto de não-retorno.** 📊 E ele foi consertado em
03/08: não disparava em 28 das 33 redações reais, por causa do negrito do
WhatsApp. Agora dispara nas quatro formas conhecidas.

### O que este teste responde, e nada mais responde

```
a resposta chega com o flow_token certo?
a HDI aceita, ou descarta em silêncio?
`response_message` é exigido? (a hipótese nº 2 do documento do formulário)
`version` precisa viajar? (a hipótese nº 1)
```

**Também destrava:** a InfoCap (P-01) — sem ela o agente pergunta a placa ao
segurado em vez de confirmar a apólice.

**O que custa esquecer:** todo o resto está pronto e desligado esperando esta
prova. Sem ela, não há como ligar `INSURER_DISPATCH_LIVE` para corretora
nenhuma — e o produto continua sabendo acionar sem nunca ter acionado.

> Ver [`O-FORMULARIO-NATIVO-RESOLVIDO.md`](O-FORMULARIO-NATIVO-RESOLVIDO.md) §7
> (o que não está provado) e §8 (o que falta para 100%).


---

## ⚠️ AVISO SOBRE O ÍNDICE RÁPIDO DESTE ARQUIVO

📊 Auditado em 03/08/2026: o índice rápido acima ainda lista **P-05, P-06, P-07,
P-08 e P-14 como abertas**. As cinco foram fechadas pelos Blocos A, B, P e C da
SPEC-063 e estão provadas por teste.

**Quem confiar no índice vai reexecutar trabalho pronto.** A tabela de fechadas
(seção "FECHADAS EM 03/08/2026") é a que vale.

| Pendência | Fechada por | Guardada por |
|---|---|---|
| P-05 AutoFleet com agente ativo sem prompt | Bloco P | `test_a_corretora_nasce_completa.py` |
| P-06 handoff mente na falha | Bloco B | `test_handoff_chega_em_alguem.py` |
| P-07 handoff sem filtro de tenant | Bloco B | idem |
| P-08 CPF vaza por dois caminhos | Bloco A | `test_quem_responde_o_segurado.py` |
| P-14 briefing sem governador | Bloco C | `test_governador_de_envio.py` |

---

## ✅ O LOTE 🤖 FECHADO EM 03/08/2026 — oito de uma vez

📊 Suíte **134 → 141 verdes** · `tsc` 0 · tabela de rotas monta (286) ·
`agent-health` 24/24. Verificado por mim, não aceito de relatório.

| # | O que era | Como fechou |
|---|---|---|
| **P-36** | 3 caminhos escreviam o prompt do agente **sem o portão** — foi por um deles que a AutoFleet ficou ativa e muda | o portão virou função única em `provision-tenant.ts`, e os três passam por ela |
| **P-56** | `selectedButtonId` × `selectedButtonID` no inbound — **o mesmo defeito dos 937 cliques**, noutro arquivo, vivo há 3 semanas depois de consertarmos o gêmeo | busca tolerante, e agora ela mora **num lugar só** |
| **P-34** | a varredura de acionamento órfão rodava 1× por processo | job periódico de 5 min |
| **P-37** | `agent-health` não via agente **mudo** | vê, e aparece na ficha |
| **P-38** | `unknown` sumia do radar | classe própria, com sinal deliberadamente mais fraco |
| **P-43** | golden test esperava `ready_for_approval` | 📊 **o caso é que estava errado**: esse estado só existe em `corridor_runs`, a tabela abandonada. Corrigido com o texto original preservado |
| **P-46** | `encaminha` declarado e sem consumidor | desfecho `encaminhado` de verdade, ensinado a 7 consumidores |
| **P-47** | `infer_ramo_servico` devolvia "residencial" genérico → `subservico_invalido` | 4 subserviços com nome próprio |

### Três achados que não estavam na lista

```
1  scripts/agent-health.test.mjs NUNCA RODOU — importava .ts e o node morria
   no import, antes da primeira asserção. Teste que não roda é pior que teste
   ausente: ele conta como cobertura. Consertado e virou `npm run test:agent-health`

2  o stub de test_audio_nao_pode_sumir.py era justificado por um fato VENCIDO
   (dizia que o módulo puxava a stack de IA; 📊 ele importa `json` e `typing`).
   Passou a carregar o módulo real — CLAUDE.md §9.3

3  test_o_clique_nao_se_perde.py C4/C5 agora guardam que a busca tolerante mora
   em UM LUGAR SÓ. Duas listas de grafias em dois arquivos foi exatamente como
   o P-56 sobreviveu três semanas ao conserto do observador
```

### E duas decisões de julgamento, registradas porque são decisões

**P-46 foi maior que as "~30 linhas" estimadas.** Encaminhar é um **desfecho**, e
desfecho sem estado é desfecho que ninguém enxerga. Por isso o estado novo.

E o corredor **não fecha na âncora**: 📊 o link do formulário da Porto vem na
mensagem *seguinte*. Fechar antes entregaria ao segurado uma frase sobre um
formulário — sem o formulário. Janela de 3 mensagens; sem link, vai para uma
pessoa. **Ninguém digita endereço de vidro de memória.** A Zurich fecha na hora,
porque 📊 a mensagem dela não traz link nenhum: esperar um transformaria o
desfecho certo em handoff.

**P-38 — a fraqueza do sinal não depende de ninguém lembrar.** `unknown` nasce
num tier que a própria SPEC-059 recusa como origem de alerta crítico. O teste
prova isso forçando `severity="critical"` e vendo o schema reprovar.

---

## P-72 · 🟠 O portão do CI não pega o defeito que aconteceu

📊 `.github/workflows/gate.yml` roda **dois passos**: um pacote de regressão
Python e `npx tsc --noEmit`. **Nenhum `.mjs`, e nem o `run_all.py`** — hoje 146
testes que ninguém executa automaticamente.

**E a consequência é precisa, não genérica.** Desde 04/08 os mapas do front são
`Record<DispatchState, …>` exaustivos por tipo. Então:

```
estado novo no TypeScript sem rótulo   → o CI PEGA (via tsc) ✅
estado novo no PYTHON que o front não conhece → o CI NÃO PEGA ❌
```

**E o segundo é exatamente o que aconteceu.** `encaminhado` e `resolvido`
nasceram no Python e ficaram órfãos em sete arquivos de tela — um caso encerrado
com sucesso aparecia ao corretor como *"conversando com a seguradora agora"*.

O guarda que cobre isso **existe** — `npm run test:atendimento-estados`, que lê o
Python e compara com a lista canônica do TS — e **não roda no CI**.

**O que destrava:** 🧑 decisão de mexer no gate. Acrescentar `run_all.py` e os
`npm run test:*` é pequeno, mas muda o que bloqueia um merge — e isso é chamada
sua, não minha.

**O que custa esquecer:** o guarda existe e a promessa que ele carrega ("o dia em
que o backend criar um estado que o front não conhece, o teste fica vermelho")
só vale se alguém digitar o comando.

## P-73 · 🟡 `npm run lint` está vermelho no repositório inteiro

📊 2.161 erros `prettier/prettier`, quase todos `Delete ␍` — quebra de linha do
Windows. **Linha de controle:** `components/patterns/StatusPill.tsx`, que
ninguém tocou nesta jornada, dá 36 erros iguais. **É pré-existente.**

Ninguém vê porque `next.config.js` traz `eslint.ignoreDuringBuilds: true` e o
gate não roda lint. Consertar é reformatar o repositório inteiro — 🧑 decisão.

## P-74 · 🟡 O `delete_agent` do backend não filtra por tenant

`backend/app/services/agent_service.py:delete_agent` arquiva o agente com
`.update({"is_active": False}).eq("id", ...)` — **sem `.eq("company_id", ...)`**.
É a mesma classe do defeito que o P-38 fechou no `update_agent`, e o backend roda
com service role: RLS sem policy não protege contra erro de filtro no código
(CLAUDE.md §7).

Não foi consertado junto porque estava fora da lista do bloco e a correção muda
o comportamento quando a resolução do tenant falha — decisão de contrato, não de
digitação.

**O que destrava:** 🤖 execução, junto com uma varredura das outras escritas de
`agents` escopadas só por `id`.
**O que custa esquecer:** um `id` errado (ou adivinhado) desliga o agente de
outra corretora, e o soft delete não deixa rastro de quem pediu.

## P-75 · 🟡 `scripts/admin-agent-blueprints-canonical.test.mjs` não roda

📊 04/08/2026: `node scripts/admin-agent-blueprints-canonical.test.mjs` morre no
import, antes da primeira asserção — ele faz
`import ... from '../lib/admin/agent-blueprints-canonical.ts'`, e o node não
resolve a extensão `.ts` em ESM. **Pré-existente**: confirmado rodando o arquivo
com `git stash` aplicado, antes de qualquer mudança desta jornada.

É exatamente o defeito que `scripts/agent-health.test.mjs` já teve e documenta —
lá foi resolvido transpilando o módulo com a API do próprio TypeScript. A
correção é copiar aquele `carregarTS()`.

**O que destrava:** 🤖 execução (o padrão já existe no repositório).
**O que custa esquecer:** `npm run test:agent-blueprints-canonical` aparece na
lista de scripts e dá a impressão de que os blueprints canônicos têm prova
executável. Não têm — e é esse arquivo que compõe o prompt de toda corretora.

## P-76 · 🟢 A varredura do portão do prompt cobre `agents` e `companies`, e só

`backend/tests/test_o_portao_do_prompt_e_um_so.py` passou a varrer o repositório
por escritas nas tabelas onde `agent_system_prompt` mora, classificando cada uma
como transparente (chaves à vista) ou opaca (variável, spread, `**`).

Ela **não** enxerga escrita por RPC do Postgres — `apply_release_rollout` e
`rollback_release_rollout` gravam a coluna dentro do banco. Os dois estão
cobertos por casos dedicados ([3]), não pela varredura.

**O que destrava:** 🤖 execução — varrer `supabase.rpc('...')` e exigir releitura
para as RPCs que tocam a coluna.
**O que custa esquecer:** uma RPC nova que escreva o prompt nasce invisível para
a varredura, que é a peça que promete "não sobrou nenhum".

---

## P-77 · 🧑 O ÚLTIMO INTERRUPTOR: o agente de atendimento nasce desligado

📊 Medido em 04/08/2026: os **quatro** agentes de atendimento do sistema estão
com `is_active = false` — Saionara (Resulta), Maria Regina (AutoFleet), JOANA
(Amandus), Even (Blueprint).

**Isso não é defeito.** É o modo observação da [D23], funcionando como desenhado:
o número segue pareado, a atendente humana responde pelo celular, o sistema
captura tudo e o agente não fala com ninguém.

Mas tem uma consequência que vale escrever: **enquanto estiver assim, todo o
portal de vidros fica inerte.** Um segurado pode mandar "quebrei o vidro" e nada
acontece — não porque falte código, e sim porque a boca está fechada.

**O que destrava:** 🧑 Founder — ligar o Agente de Atendimento no dashboard da
corretora. É um clique, e ele liga a cadeia inteira.
**O que custa esquecer:** achar que o portal "não funciona" quando ele nunca foi
chamado. É o tipo de conclusão que faz desmontar o que está certo.

---

## P-78 · 🟡 `vidro do porta-malas` é lido como vidro lateral

📊 `identidade_peca("vidro do porta-malas")` devolve `{lateral}`, porque
**"porta"** é sinônimo de lateral no vocabulário de peças. O portal ofereceria
`VIDRO DE PORTA` para um vidro que é do porta-malas.

Achado pelo executor do bloco 7.5 ao montar o catálogo de perguntas; é falha
**pré-existente** do vocabulário compartilhado, não do trabalho novo.

**O que destrava:** 🤖 execução — `_EXPRESSOES` resolve `porta-malas` /
`porta malas` / `portamalas` ANTES de separar em tokens, como já faz com
`para brisa`. É o mesmo mecanismo, e cabe em três linhas.
**O que custa esquecer:** um vidro trocado errado, e o portal proíbe corrigir —
teria de abrir OUTRO acionamento.

---

## P-79 · 🟠 O portal manda `especificos`, mas a tool não tem campo para o LADO

O bloco 7.5 abriu `especificos` no schema da `portal_action`, e as respostas do
80% (película, dianteira/traseira, lado) finalmente chegam ao portal.

Falta o outro lado da moeda: **a chave de idempotência não conhece o lado.**
📊 O portal diz, literalmente, que *"se o item possuir lateralidade será
necessário abrir uma nova solicitação para o outro lado"*. Dois vidros quebrados
são dois pedidos — e, se o agente escrever a mesma `peca` genérica nos dois, o
segundo é **barrado** pela idempotência como se fosse repetição.

A frase de "já existe" ensina a saída (*descreva a peça com o lado*), mas
depender do texto para o modelo acertar é o que esta SPEC inteira está desfazendo.

**O que destrava:** 🤖 execução — `especificos.lado_motorista_ou_carona` entra
na `chave_de_idempotencia` quando estiver presente.
**O que custa esquecer:** o segundo vidro nunca é aberto, e o segurado descobre
quando o vidraceiro chega e conserta um só.

---

## P-80 · 🟡 Telas do portal que ainda não foram medidas

Do mapa [`O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`](O-PORTAL-DE-VIDROS-TELA-POR-TELA.md) §7:

| Lacuna | O que destrava |
|---|---|
| **Consultar atendimento** — o acompanhamento oficial | 🧑 uma captura de tela |
| Perguntas específicas de retrovisor, farol, lanterna, vigia, teto | 🧑 captura ou 1ª execução real |
| Telas de **roda/pneu/suspensão** (só a Porto oferece) | 🧑 uma captura na Porto |
| Quais seguradoras da lista realmente atendem vidros | 🤖 tentativa por seguradora |

**Nenhuma impede o corredor de funcionar** — todas caem no caminho adaptativo,
que lê a tela real. Elas definem quanto o robô precisa pensar em vez de
reconhecer. A primeira é a mais valiosa: hoje prometemos "acompanho até o fim" e
a fonte oficial desse acompanhamento existe e não está ligada.

**O que custa esquecer:** o `especificas_mapeadas()` já declara em voz alta o que
não conhece — então o risco não é errar calado, é continuar pensando mais do que
o necessário.

---

## P-81 · 🟡 O cérebro do portal é OpenAI; o resto do produto poderia decidir isso

📊 `PORTAL_VISION_MODEL` passou de `gpt-4o-mini` para `gpt-4o` em 04/08, com
rede de segurança: erro de modelo cai uma vez no antigo, para que um nome
inválido nunca custe um acionamento.

📊 `app/core/config.py` só declara `OPENAI_API_KEY` — não há chave Anthropic no
backend. Trocar o cérebro do portal por um modelo Claude exigiria uma chave nova.

**O que destrava:** 🧑 Founder — decidir se vale, e fornecer a chave.
**O que custa esquecer:** nada imediato. É otimização, não trava — e o
preenchimento determinístico do bloco 7 já tirou do modelo a maior parte do
trabalho onde ele errava.

---

## P-82 · 🟡 `_expandir_caps` recebe um `set` e não expande nada

`graph.py:227` chama `capacidades_ativas(_active)` com um **set**, e a função
começa com `if not isinstance(ativas, dict): return ativas`. Ou seja: o alias
`platform.web.search` → `platform.research.search` nunca acontece naquele ponto.

Achado de passagem ao consertar o portão do portal (bloco 7.1). Não é do escopo
desta SPEC e **não** foi tocado — mexer nisso muda permissão de pesquisa, que é
outro assunto.

**O que destrava:** 🤖 execução — ou a função aceita `set`, ou a chamada passa o
dicionário resolvido. Com teste que prove a expansão acontecendo.
**O que custa esquecer:** quem tinha a capability antiga não ganha a nova no
cutover — exatamente o que o expand-first prometeu evitar.

---

## P-83 · 🧑 METADE DA SPEC-065 ESTÁ NO AR; A OUTRA METADE ESPERA UM CLIQUE

📊 Medido em 04/08/2026, depois do deploy do commit `79077f6`:

```
web           200        ✅ no ar
API           healthy    ✅ no ar
portal-worker build_time 2026-08-04T12:32:36Z   ❌ NÃO reconstruiu
```

Verifiquei por 4 minutos, de 30 em 30 segundos: o `build_time` não mudou. **O
portal-worker é um serviço próprio no EasyPanel, com gatilho de deploy próprio,
e eu só tenho os gatilhos da API e do web.**

### O que isso significa, arquivo por arquivo

| Onde | Serviço | Está no ar? |
|---|---|---|
| capability + portão do `portal_action` (`graph.py`) | API | ✅ |
| roteamento "sem corredor de vidro → portal" (`insurer_dispatch_tool.py`) | API | ✅ |
| Vigia do Portal (`vigia_do_portal.py`, `buffer_processor.py`) | API | ✅ |
| idempotência e `session_id` (`portal_tool.py`, `portal_params.py`) | API | ✅ |
| campo `especificos` + descrição da tool | API | ✅ |
| perguntar antes de abrir (`perguntas_do_portal_de_vidros.py`) | API | ✅ |
| as duas migrations | Supabase | ✅ (aplicadas e verificadas) |
| **preenchimento determinístico + modelo** (`adaptive.py`) | **worker** | ❌ |
| **vocabulário do 80% + loja crítica** (`vidros_lanternas.py`, `adaptive.py`) | **worker** | ❌ |

**A parte que decide se o portal é chamado está no ar. A parte que decide o que
ele digita, não.**

⚠️ Consequência concreta enquanto isto durar: se um acionamento rodar agora, ele
usa o `gpt-4o-mini` antigo, sem preenchimento determinístico, e `"menor que 10
cm"` ainda pode virar **"Maior (troca do vidro)"**. 📊 Na prática o risco é
teórico hoje — a [P-77] mantém os agentes de atendimento desligados, então
nenhum acionamento nasce. Mas as duas pendências têm de ser resolvidas **na
ordem certa: esta primeiro, a P-77 depois.**

**O que destrava:** 🧑 Founder — uma das duas:
1. clicar **Deploy** no serviço `portal-worker` no EasyPanel, ou
2. me passar o gatilho dele (`http://187.77.45.227:3000/api/deploy/<token>`),
   do mesmo jeito que passou o do `evolution-go-teste`.

**Como conferir que funcionou:** o `build_time` em
`https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`
tem de ser MAIOR que `2026-08-04T12:32:36Z`.

**O que custa esquecer:** ligar o atendimento (P-77) com o worker velho no ar. O
sistema passaria a acionar de verdade, com os defeitos que esta SPEC consertou
ainda em produção — e o pior deles troca um para-brisa que tinha conserto.

---

## P-84 · 🧑 DECISÃO: o que o Observador pode gravar, por corretora

📊 Medido em 04/08/2026: as **três** memórias de escopo dizem `insurers_only` —
AMANDUS, AutoFleet e Resulta. Não porque alguém tenha escolhido: foi assim que a
**contenção de 29/07** as deixou, quando o Observador capturou 630 contatos
pessoais de um celular particular.

**Uma emergência virou política sem ninguém decidir.**

E a consequência é concreta: se a Saionara e a Regina parearem amanhã sem tocar
nisso, **nenhuma conversa de segurado será capturada** — só as de seguradora. É
exatamente o oposto do que a curadoria e as cartas precisam.

### Os dois custos, para a decisão ser sua e não minha

| Escopo | O que ganha | O que arrisca |
|---|---|---|
| `insurers_only` | nenhum dado de terceiro entra | 📊 sete dias de observação rendem **zero** conversa de atendimento |
| `insurers_and_clients` | o material das cartas | se o telefone for pessoal, entra conversa particular — e o sistema **não tem como distinguir** (📊 não existe tabela de segurados com telefone neste banco) |

O erro de gravar de MENOS é reversível: 📊 o `history_sync` reentregou 133
eventos de 29/07–03/08 numa rajada de 6 minutos após um restart. O de gravar de
MAIS não é.

**O que destrava:** 🧑 Founder — dizer, por corretora: o número que vai ser
pareado é o **celular de trabalho** dela? Se sim, `insurers_and_clients`. Eu
gravo antes do QR (é uma linha), e a memória passa a preservar para sempre.
**O que custa esquecer:** parear as duas e descobrir dias depois que não há
material nenhum para destilar.

---

## P-85 · 🔴 O handoff humano está RECUSADO para AutoFleet e Resulta

📊 As duas apontam para o **mesmo** destino de suporte (o mesmo grupo de
WhatsApp), replicado em `acionamento_profile`. E `dispatch_router` recusa
destino compartilhado **de propósito** — para não entregar o CPF de um segurado
na corretora errada.

Consequência com o agente ligado: *"quero falar com uma pessoa"* **não aciona
ninguém**. E o dossiê do Vigia do Portal morre no mesmo lugar.

📊 A AMANDUS tem destino próprio e funciona — o que prova que o mecanismo está
certo e o dado é que está compartilhado.

**O que destrava:** 🧑 Founder — um grupo de WhatsApp por corretora.
**O que custa esquecer:** o handoff é a última rede. Ligar o agente sem ela é
prometer "não vou te deixar travado" sem ter para onde passar.

---

## P-86 · 🟠 A allowlist de entrada atende só um número

📊 `ATTENDANT_INBOUND_ALLOWLIST` está preenchida em produção com **um** número.
Enquanto estiver assim, ligar o agente faz ele atender só esse número e **ignorar
todo o resto em silêncio** — botão verde, tela dizendo "atendendo", nada
acontecendo para o segurado.

Isso é ótimo para o teste que o Founder quer fazer na AMANDUS. É armadilha no
dia do go-live.

**O que destrava:** 🤖+🧑 esvaziar a variável quando for atender de verdade —
**e só depois de P-85 estar fechada**, senão o agente atende e não tem para quem
passar quando travar.
**O que custa esquecer:** achar que o agente está quebrado quando ele está
obedecendo.

---

## P-87 · 🔴 O destilador está DESLIGADO, e o material expira em outubro

📊 `DESTILADOR_TETO_POR_RODADA` tem padrão **`0`** — e `0` significa "não
destile nada". Resultado medido:

```
69.150 transcrições capturadas          ✅
 8.872 sessões fechadas                 ✅
 1.460 sessões NUNCA destiladas         🔴  (AutoFleet 480 · Resulta 980)
 9.416 cartas, TODAS nascidas em 28–30/07 — a máquina rodou uma vez e parou
```

E o purge de retenção apaga o cru 90 dias depois de capturado: 📊 por volta de
**27/10/2026**. Sem religar o teto, esse material **expira sem virar carta**.

**O que destrava:** 🤖 execução — definir o teto e rodar uma leva controlada,
conferindo custo. É a peça que transforma conversa capturada em conhecimento, e
hoje ela está de pé e desligada.
**O que custa esquecer:** o acervo inteiro vira lixo com data marcada.

---

## P-88 · 🟠 O telefone pareado nunca é gravado

📊 `observed_sessions.observer_number` da AutoFleet é `6955221` — os dígitos do
**nome da instância** (`ab-obs-6c9c55e22f-1`), não um telefone. O número que
realmente pareou não é persistido em lugar nenhum.

É a causa direta da pergunta do Founder — *"já tinha um pareado e eu não sei
qual era"*. Não dava para saber: o sistema não guarda.

📊 E há fallback literal `"unknown"` (167 eventos da Resulta já estão assim) e
`"attendance-channel"` (1 transcrição).

**O que destrava:** 🤖 execução — `integrations.paired_jid` / `paired_phone_e164`
/ `paired_at`, gravados na confirmação da conexão, com backfill do provedor. Toda
tela passa a dizer `5547*****463 · pareado em 29/07`.
**O que custa esquecer:** nenhuma auditoria de "quem está conectado" é possível,
e a próxima confusão vai custar o mesmo tempo que esta.

---

## P-89 · 🟠 Os índices de deduplicação não têm `company_id`

📊 `ux_attendance_transcripts_dedupe` e `uq_observed_events_msg` são
`(observer_number, message_id)` — **sem corretora**. Somado ao `observer_number`
que cai em `"unknown"` (P-88), duas corretoras podem ter sessões **fundidas**.

Hoje é teórico. **Com duas corretoras pareando em dias, deixa de ser.**

**O que destrava:** 🤖 execução — `company_id` nos dois índices, antes do segundo
pareamento.
**O que custa esquecer:** transcrição de uma corretora descartada como duplicata
da outra — e o pior tipo de perda, a silenciosa.

---

## P-90 · 🟠 O portal para no 80% e NADA no sistema pode aprovar

📊 `build_portal_params` crava `"confirm": False`, e uma busca no repositório
inteiro não acha **nenhum** caminho que ligue `confirm=True`.

O acionamento percorre o formulário todo, chega na tela de confirmação e para —
que é o freio funcionando. Mas não existe o outro lado: nem tela, nem resposta
de WhatsApp, nem rotina que aprove. **O pedido nunca é enviado.**

📊 É o que explica os 9 acionamentos que "chegaram na confirmação (80%)" e nunca
viraram protocolo.

**O que destrava:** 🤖 execução — o passo de aprovação. A capability já existe e
já descreve o contrato (`operational.portal.assistance.request`,
`requires_approval: true`, `max_calls_per_run: 2`). Falta o mecanismo. 🧑 E uma
decisão junto: aprovar é um clique no painel, uma resposta no WhatsApp do
suporte, ou os dois?
**O que custa esquecer:** o portal está pronto para fazer 95% do trabalho e parar
na última porta. É a diferença entre "funciona" e "entrega".
