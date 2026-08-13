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

### ✅ 08/08/2026 — o item 1 está feito; 2 e 3 continuam abertos

O filtro de valor existe: `curadoria_cartas.e_sobre_seguro`, determinístico,
sem LLM, chamado em `publicar_lote_sync` — a **única** porta em que uma carta
vira `published` sem ninguém olhar. Carta recusada não some: fica em
`rejected_fora_de_escopo`, com texto e hash intactos, e o `/admin/espelho`
continua podendo aprová-la uma a uma. O nome do status é próprio de propósito:
marcá-la `rejected_pii` faria o próximo a contar vazamentos contar esta junto.

📊 Medido contra as 12.063 `published` (projeto `dcajcvlzcjbmyapmklil`),
refazendo a consulta a cada ajuste do vocabulário:

    um vocabulário só, sem nomes de companhia          184  (1,53%)
    dois níveis, sem os nomes das seguradoras          399  (3,31%)  ← PIOROU
    + nomes de seguradora no nível forte               169  (1,40%)
    + dinheiro repartido em seis entradas               64  (0,53%)  ← em uso

O passo que piorou é o que ensina: dois níveis com vocabulário estreito recusa
MAIS que um nível largo. O mérito é do que está em cada nível, não de haver
dois. E as 64 que sobram são conduta de escritório que serviria a uma pizzaria
(*"Reentrar no sistema (logout/login) pode resolver falhas de exibição"*).

- **Guarda:** [`test_a_carta_precisa_ser_sobre_seguro.py`](../../backend/tests/test_a_carta_precisa_ser_sobre_seguro.py)
  — prova as duas direções com texto REAL do acervo, e a linha de controle
  troca UMA palavra para mostrar que o limiar de duas menções é de verdade.

**Continua aberto:**
- **item 2 · 🧑** aprovação humana para carta de origem não-seguradora. Hoje o
  filtro é vocabular, não semântico: ele barra o que não fala de seguro, não o
  que fala de seguro e é falso.
- **item 3 · 🤖** as 📊 64 `published` que o filtro recusaria **continuam no
  acervo e no Qdrant**. Nada foi escrito no banco. `reindexar_acervo.py` também
  não consulta o filtro — reindexar hoje devolve as 64 ao índice.
  Destrava: rodar `e_sobre_seguro` sobre as 12.063, marcar as recusadas e tirar
  o ponto do Qdrant, com as 64 lidas à mão antes.

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

> **Escrito em 04/08/2026 (SPEC-063).** As três colunas nascem na migration
> `20260804_03_o_repareamento_nao_duplica.sql` (**ainda não aplicada** — P-91), e
> quem as preenche são `pairing_orchestrator._mark_connected` (do
> `/instance/status`) e o `connection.update` do Observador. A regra de leitura
> mora sozinha em `app/services/whatsapp/numero_pareado.py` e **não inventa**:
> sem JID do provedor, devolve `None` em vez de deduzir do nome da instância.
>
> ⚠️ **Sem backfill, e de propósito.** O telefone das linhas já pareadas não
> existe em campo nenhum deste banco — só apareceria num `/instance/status` ao
> vivo. Reconstruí-lo a partir do `identifier` seria repetir o engano que criou o
> `6955221`. As três integrações atuais ficam com o campo **vazio até reparear**.
>
> O fallback literal também morreu: `"unknown"` passou a ser
> `{company_id[:8]}:sem-digitos`, então duas corretoras sem dígito no identifier
> deixam de colidir. 📊 Os 167 eventos já gravados com `"unknown"` **continuam
> como estão** — reescrevê-los mudaria a chave de dedupe deles.

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

> **Escrito em 04/08/2026 (SPEC-063).** Os índices com `company_id` nascem na
> migration `20260804_03` (**não aplicada** — P-91), e nascem **ao lado** dos
> antigos, não no lugar deles. O motivo está medido:
>
> O código grava com `on_conflict`, que o Postgres exige que case **exatamente**
> com um índice único existente. Dropar o antigo antes de o deploy chegar faria
> `_store_history_event` levar `42P10` — e como `_ingest_conversation` engole a
> exceção, **a ingestão do histórico gravaria zero linha reportando sucesso**.
> Com os dois vivos, as duas grafias funcionam e a ordem entre migration e deploy
> deixa de importar.
>
> 📊 Medido antes de escrever: **0 linhas** colidem com a chave nova e **0** pares
> `(observer_number, message_id)` existem em duas corretoras — a construção dos
> índices não pode falhar, e nada muda de lado.
>
> ⚠️ **A fusão entre corretoras só fecha de fato com o DROP dos antigos** (P-91),
> porque enquanto existirem são eles, mais estritos, que decidem.
> `test_o_repareamento_nao_duplica.py` [3] mede as três configurações e mostra a
> transição colapsando — de propósito, para que o estado intermediário não seja
> confundido com o final.

---

## P-91 · 🧑 A migration `20260804_03` está escrita e NÃO aplicada

O arquivo `backend/supabase/migrations/20260804_03_o_repareamento_nao_duplica.sql`
existe, com APPLY/VERIFY/ROLLBACK, e **nunca foi executado** — por instrução
explícita. Ele é o que fecha P-88 e P-89.

Enquanto não for aplicado, o código já em produção continua funcionando pela
chave antiga (a reserva existe justamente para isso), mas:

- `paired_phone_e164` não existe → o telefone pareado continua sem ser gravado;
- as chaves de dedupe continuam sem `company_id`.

**O que destrava:** 🧑 Founder aplica a migration e roda o VERIFY do cabeçalho
(cinco consultas, incluindo a que prova que o guarda **consegue** falhar).
Depois: 🤖 deploy do backend — e só **então** a segunda migration, de uma linha
por índice, com os três `DROP INDEX` já escritos no cabeçalho do arquivo.
**O que custa esquecer:** parear a Regina e a Saionara antes disso significa
perder a única janela em que a separação por corretora era barata — depois dela,
os dados das duas já estarão dentro da mesma chave.

---

## P-92 · 🟠 Um parâmetro do onboarding pode duplicar o acervo inteiro

📊 `admin_atlas.py:346` — `instance = _obs_instance_name(company_id, int(body.get("seq") or 1))`.

O `seq` vem do **corpo do request**. E `observer_number` é `_digits()` do nome da
instância: `ab-obs-6c9c55e22f-1` → `6955221`; `ab-obs-6c9c55e22f-2` → `6955222`.

Chave diferente = **nada casa** = o history_sync regrava tudo. 📊 São 9.982
transcrições da AutoFleet e 59.168 da Resulta a um dígito de distância.

O caminho normal é seguro — `pairing_orchestrator._instance_name` crava `-1` e
`_prepare_and_connect` reusa o `instance_id` já gravado. O risco é só esta porta.

**O que destrava:** 🤖 execução — ignorar `seq` quando já existe integração
observer para a corretora, ou recusar `seq != 1` sem confirmação explícita.
Não foi feito aqui porque `admin_atlas.py` está fora do escopo que me foi dado.
**O que custa esquecer:** o pareamento "manual de emergência" é justamente o que
alguém usa sob pressão, que é quando ninguém confere um campo numérico.

---

## P-93 · 🟡 1.035 linhas ao vivo ainda podem ganhar cópia no repareamento

📊 04/08/2026: as duas fontes gravam `message_id` de famílias incompatíveis —
`history_sync` usa `hist-…` (100% das 85.766 linhas) e o caminho ao vivo usa o id
do WhatsApp (100% das 1.035). O índice único não tem como saber que são a mesma
mensagem.

O cruzamento por conteúdo em `history_ingest._impressoes_ao_vivo` fecha isso
**daqui para a frente** e está provado em `test_o_repareamento_nao_duplica.py` [4].
Duas ressalvas honestas:

1. Ele só compara mensagens **com texto**. Áudio, foto e documento ficam de fora
   de propósito (regra de `atlas/mensagem.py`: sem texto não há identidade
   segura, e perder áudio é irreversível). 📊 São 9.002 mídias no Espelho.
2. Ele é *fail-open*: se a leitura falhar, a ingestão segue sem o cruzamento — o
   pior desfecho vira uma cópia, que se conserta, em vez de uma mensagem
   descartada, que não.

**O que destrava:** 🤖 execução — depois do primeiro repareamento, rodar o
detector abaixo e decidir sobre o que sobrar:

```sql
SELECT company_id, counterparty, wa_timestamp, direction, msg_type, count(*)
  FROM attendance_transcripts
 WHERE wa_timestamp IS NOT NULL AND text IS NOT NULL
 GROUP BY 1,2,3,4,5 HAVING count(*) > 1;
```

**O que custa esquecer:** a duplicata de mídia não aparece em contagem de
conversa, aparece no custo de transcrever o mesmo áudio duas vezes.

---

## P-90 · ✅ RESOLVIDO em 04/08/2026 — a aprovação é o botão LIGAR AGENTE

📊 `build_portal_params` cravava `"confirm": False`, e uma busca no repositório
inteiro não achava **nenhum** caminho que ligasse `confirm=True`. O acionamento
percorria o formulário todo, chegava na tela de confirmação e parava. 📊 É o que
explica os 9 acionamentos que "chegaram na confirmação (80%)" e nunca viraram
protocolo.

Esta entrada propunha construir um passo de aprovação (tela, WhatsApp do
suporte, ou os dois). **O Founder respondeu outra coisa, e a resposta dele é
melhor**, porque tira uma trava em vez de somar uma:

> *"A questão de trava no final sempre foi por um motivo exclusivo. Eu estava
> fazendo os testes no meu próprio celular. Se não tivesse a trava, seriam
> feitos os acionamentos dos serviços de vidro de verdade."*
> *"Quero tudo pronto e funcionando, mas o agente de atendimento tem que
> continuar desligado. Só podem funcionar se clicar em LIGAR AGENTE."*

O que passou a valer: **um interruptor só, `agents.is_active` do agente de
atendimento.** `portal_tool` e `insurer_dispatch_tool` perguntam
`attendance_agent_active` antes de agir e derivam dela o `confirm` do portal e o
envio real do corredor de WhatsApp (regra única em
`insurer_dispatch_service.acionamento_liberado`). Provado nos dois sentidos em
`backend/tests/test_o_que_acontece_quando_o_agente_liga.py`.

📊 Em 04/08/2026 os quatro agentes `attendance` estão `is_active=false` — nada
sai enquanto ninguém clicar.

---

## P-91 · 🧑 Duas linhas de env que podem fazer o botão não funcionar

Herança do desenho antigo. **Se o Founder ligar o agente e nada acontecer, é
uma destas duas** — e não haverá erro nenhum para explicar por quê.

1. **`INSURER_DISPATCH_LIVE`** — o padrão do código passou a ser ABERTO, mas um
   `false` *escrito* continua fechando (de propósito: ignorar o que um operador
   escreveu é discordar dele em silêncio). O `.env.example` antigo trazia
   `INSURER_DISPATCH_LIVE=false`; se o ambiente do EasyPanel herdou essa linha,
   **apague-a**.
2. **`PORTAL_REAL_ENABLED`** (serviço `portal-worker`) — com ela desligada o
   worker sobe, responde `/health` e **não pega job nenhum**. O acionamento de
   vidros é enfileirado e fica em `queued` para sempre. 📊 Os 39 jobs de
   `abrir_atendimento` têm `started_at` preenchido (último em 10/07/2026), o que
   indica que ela já esteve ligada — mas o estado atual do ambiente não é
   legível daqui.

**O que destrava:** 🧑 Founder — conferir as duas variáveis no EasyPanel.
**O que custa esquecer:** o botão vira decoração, sem mensagem de erro.

---

## P-92 · 🤖 O chat interno também alcança o portal de vidros

📊 04/08/2026, `capability_bindings`: `tenant.portal.execute` está **ligada para
`core` e `auxiliary`** (e desligada para `attendance`). O chat interno da
corretora, portanto, também recebe `portal_action` — e ele **não** passa pelo
portão `attendance_agent_active` do webhook, porque fala com o corretor, não com
o segurado.

📊 Alcance real hoje: **uma** corretora. A capability exige conexão
(`requires_connection=true`, provider `portal_worker`) e só a Resulta
(`04b5cdbc…`) tem linha em `portal_accounts`; o `core` dela está ativo.

Não é um buraco aberto: `portal_tool` subordina o `confirm` ao mesmo
interruptor, então com o agente de atendimento desligado o job do chat interno
nasce `confirm=False` e para no 80% — exatamente o que já fazia. Mas **quando o
agente for ligado, este caminho também passa a poder abrir pedido de verdade.**

**O que destrava:** 🧑 decisão de produto — o corretor pode abrir um chamado de
vidro pelo chat interno? Se não, é um `UPDATE capability_bindings SET
enabled=false WHERE agent_role='core' AND capability_key='tenant.portal.execute'`.
**O que custa esquecer:** ninguém procura o acionamento de vidros no chat
interno, e é de lá que ele pode sair.

---

## P-93 · 🤖 Um job parado no 80% bloqueia o pedido que agora poderia ser aberto

A chave de idempotência (`idx_portal_jobs_pedido_vivo`) bloqueia todo status
menos `failed` — inclusive `needs_human`. Correto para o que ela foi feita.

Mas um job que rodou com `confirm=False` **não abriu atendimento nenhum** (é o
que `confirm=False` garante: `run_adaptive` para em `is_confirm_screen`). Se um
pedido foi tentado com o agente desligado e ficou em `needs_human`, a mesma
placa + peça + data com o agente ligado recebe *"já existe um atendimento
aberto"* — e não existe.

📊 Alcance hoje: **zero.** Os 91 jobs históricos têm `idempotency_key IS NULL`
(a migration não fez backfill de propósito) e o último `abrir_atendimento` é de
10/07/2026. A janela é só entre agora e o clique no botão.

**O que destrava:** 🤖 execução — ou marcar `failed` o job de 80% cujo
`params->>'confirm'` é `false` quando uma chamada nova está liberada, ou aceitar
o bloqueio e corrigir a frase, que hoje afirma um atendimento que não existe.
**O que custa esquecer:** um segurado ouve que o pedido dele já está aberto, e
não está.

---

## P-94 · 🟠 O mascarador chama de `{CPF}` o celular de 11 dígitos

📊 Medido em 04/08/2026 nos 10 mapas `observed`: **46 nós em 6 seguradoras**
guardam a frase *"O número de telefone {CPF} está correto?"*. Um deles é a tela
mais percorrida da HDI (20 passagens).

```sql
select count(*) from ura_maps m, jsonb_each(m.map->'nodes') k
 where m.status='observed'
   and k.value->>'text' ~* '(telefone|celular|whatsapp|contato)[^\n]{0,40}\{CPF\}';
```

A causa é ordem de regra, não sorte. Em `templater._PII_PATTERNS` o padrão de
CPF vem antes do de telefone, e `\d{3}\d{3}\d{3}\d{2}` casa exatamente os 11
dígitos de um celular com DDD. O telefone nunca chega a ser testado.

O dado continua protegido — o número sai da mesma forma. O que se perde é a
**estrutura**, que é justamente o que o Atlas existe para guardar: a tela diz
que pergunta CPF quando ela pergunta telefone. CLAUDE.md §12.1 manda consertar o
campo, não o texto — e aqui o campo é o rótulo do placeholder.

Desambiguar 11 dígitos não é trivial: `47988087463` é um celular válido e um CPF
possível. A pista boa é a palavra ao redor (`telefone`, `celular`, `contato`,
`WhatsApp`) — a mesma que `_ANSWER_HINTS` já usa para outra finalidade no mesmo
arquivo.

- **Destrava:** 🤖 uma regra em `templater.py` que, havendo `telefone|celular|
  contato|whatsapp` até ~40 caracteres antes do número, marque `{TELEFONE}`
  antes de o padrão de CPF rodar. Reprocessar os mapas depois.
- **Dono:** 🤖 execução — **não foi feito nesta passada porque `templater.py`
  estava em edição por outra frente** (04/08/2026).
- **Custa se esquecer:** o agente que ler o mapa vai responder um CPF onde a URA
  pede telefone, e a tela seguinte é de erro. E cada leitor novo do mapa herda a
  mentira.

## P-95 · 🟠 O mesmo texto vira vários nós, e isso elegeu a raiz errada da Porto

📊 Medido em 04/08/2026: nós que repetem os 80 primeiros caracteres de outro —
yelum 12,2% (72 de 590) · hdi 10,6% · porto 10,2% (86 de 841) · azul 7,2% ·
allianz 6,6% · o resto abaixo de 4%.

```sql
with n as (select m.insurer_key, left(k.value->>'text',80) p80
             from ura_maps m, jsonb_each(m.map->'nodes') k where m.status='observed')
select insurer_key, count(*)-count(distinct p80) from n group by 1;
```

A identidade do nó é o hash do texto inteiro templatizado. Quando sobra
qualquer coisa variável no meio da frase, a mesma tela vira vários nós. O caso
dominante é **nome de pessoa fora da saudação**: a regra `{NOME}` só cobre nome
COLADO em "Olá,"/"Oi,", e a Porto escreve *"Oi, sou assistente virtual da Porto
👋\n\nFulano, estou aqui pra falar sobre…"* — o nome vem depois da quebra.

**Consequência medida:** a eleição da raiz é por contagem de aberturas, e conta
por nó. 📊 Das 149 sessões da Porto, 56 começam por essa saudação e 20 por *"Eu
estou falando com Fulano?"* — mas cada nome vira um nó de 1 voto. `"Aguarde um
momento 🙂"`, que não fragmenta, juntava 10 votos num nó só **e ganhava a
eleição**. O Tecelão agora tira tela de espera da urna (04/08/2026), o que
conserta o sintoma; a fragmentação continua.

⚠️ **Não conserte fundindo por prefixo.** 📊 A Porto tem quatro grupos distintos
com os MESMOS 80 primeiros caracteres e continuações diferentes (sinistro,
vistoria, reparos) — fundi-los juntaria fluxos que não são o mesmo.

- **Destrava:** 🤖 alargar o mascaramento de nome em `templater.py` (nome depois
  de quebra de linha, e no molde "falando com Fulano?"), e só então reprocessar.
  Mexer na identidade do nó invalida `hash`, `src`, `to` e `leads_to` de todos os
  mapas gravados — é reprocessamento completo, não migração.
- **Dono:** 🤖 execução — **não feito nesta passada: o conserto mora em
  `templater.py`, em edição por outra frente**, e o risco de fundir tela errada é
  maior que o do sintoma.
- **Custa se esquecer:** cobertura e contagem de telas seguem divididas entre
  cópias, e a raiz de qualquer seguradora nova pode cair na tela errada pelo
  mesmo motivo.

---

## P-96 · 🧑 Os áudios da AutoFleet esperam um repareamento combinado

📊 Medido em 04/08/2026: **1.623 áudios recuperáveis (80 MB)**, e **zero
arquivados**. O caminho de repesca pelo banco é **impossível** — 0 têm
`fileEncSha256`/`fileSha256`, e o `/message/downloadmedia` exige a mensagem
crua inteira.

**O único caminho é reparear com o conserto de 04/08 no ar.** Aí a mídia é
enfileirada no instante da reentrega, que é o único instante em que ela existe.

📊 E o texto não duplica: **1 duplicata em 13.481 linhas** no repareamento de
hoje.

**Decisão do Founder (04/08):** *"não faz mal agora. Continuam no celular dela.
Isso fica como tarefa pendente mais pra frente, porque os áudios são na verdade
cartas pro RAG e podemos criar elas depois. Quero a destilação apenas das
conversas em texto agora."*

**O que destrava:** 🧑 combinar com a Regina um novo pareamento (5 minutos dela).
**O que custa esquecer:** nada imediato — os áudios estão no celular dela. Mas
cada mês que passa é mais chance de o WhatsApp podar a mídia antiga do servidor,
e aí nem o repareamento traz.
**Documentação completa:** [`AUDIOS-RESGATE.md`](AUDIOS-RESGATE.md) §0.

---

## P-97 · 🧑 O crédito da API Claude acabou — e o gasto tem dono

📊 Consumo total medido em 04/08 (`token_usage_logs`):

```
29/07   US$ 10,10  em 1.702 chamadas   ← a DESTILAÇÃO
28/07   US$  1,06  em 2.593 chamadas
resto   US$  0,43
                    TOTAL US$ 11,59
```

**Não foi agente de bastidor.** O destilador está desligado, o portal usa OpenAI,
os vigias não usam LLM. 📊 Foi `service_type='chat'` com `claude-sonnet-5` — a
destilação das 8.872 sessões em 9.699 cartas.

> 📊 **≈ US$ 0,0012 por carta.** A destilação é barata; o caro seria o
> raciocínio sem material.

**O que destrava:** 🧑 saldo novo na API Claude. Para a próxima leva (as ~700
sessões novas da AutoFleet), a conta proporcional é de **menos de US$ 2** — mais
uma margem para a curadoria.
**O que custa esquecer:** sem saldo, a destilação não roda, e 📊 o material cru
expira por volta de **27/10** (retenção de 90 dias).

---

## P-98 · ✅ Os 23 documentos destravaram — mas o buraco do varredor continua

> **📊 Reconferido em 07/08/2026, e o número mudou para melhor.** Deixar o texto
> antigo mandaria o próximo leitor caçar um problema resolvido — e o pior tipo
> de pendência é a que já foi feita e ninguém apagou.

```
                     05/08/2026        07/08/2026
fetching                 23      🔴         0      ✅
ingested                  8                29   (11.409 chunks)
discovered                4                 6
                                    última mudança: 06/08
```

**O crédito voltou e a ingestão andou sozinha.** 📊 São hoje 29 documentos
indexados — 25 de condições gerais, 5 de manual do segurado, 5 de circular
SUSEP, cobrindo auto, residencial, vida, empresarial, condomínio e
responsabilidade civil, de 8 seguradoras.

### 🔴 O que NÃO se resolveu, e é o que valia a entrada

O buraco do varredor continua aberto — ele só não está machucando **agora**:

📊 `insurance_corpus.py:654-660` — a função `vencidos()`, que é a **única** que
reencontra trabalho pendente, procura documentos em `('ingested', 'discovered',
'unreachable')`. **`fetching` não está na lista.**

`ingerir()` marca `fetching` **antes** de sair para a rede. Se a chamada falha,
o documento fica nesse estado transitório **para sempre** — aprovado pela
curadoria, invisível para o varredor, e sem nenhum alarme. Da próxima vez que o
crédito acabar (e ele já acabou uma vez), acontece de novo, igual.

> É a mesma lição que este repositório já aprendeu duas vezes — na reconciliação
> de acionamento órfão e no vigia de handoff: **um estado que só é observado
> quando nasce não é observado.**

### 🟠 E uma anomalia nova, ainda não explicada

📊 Dos 6 documentos em `discovered`, **quatro nunca foram conferidos**
(`last_checked_at` nulo) e têm `next_check_at = 2026-07-25` — vencidos há 13
dias. `vencidos()` ordena por `next_check_at` crescente, então eles deveriam ser
os **primeiros** da fila, não os últimos.

💭 Duas hipóteses, nenhuma medida: ou o varredor não roda de fato em produção
(o portão `smith_worker.py:223` desiste sem `FIRECRAWL_API_KEY` **no worker**),
ou existe caminho que consome o documento sem gravar `last_checked_at`. Os
outros 2 têm erro de origem (HTTP 408 e 500 na Bradesco), que não é nosso.

**O que destrava:** 🤖 o varredor de órfãos — não precisa de saldo nem de
decisão. E 🤖 medir qual das duas hipóteses acima é a certa, antes de consertar
a errada.

### O agravante que ninguém veria

📊 `insurance_corpus.py:654-660` — a função `vencidos()`, que é a **única** que
reencontra trabalho pendente, procura documentos em `('ingested', 'discovered',
'unreachable')`. **`fetching` não está na lista.**

`ingerir()` marca `fetching` **antes** de sair para a rede. Se a chamada falha,
o documento fica nesse estado transitório **para sempre** — aprovado pela
curadoria, invisível para o varredor, e sem nenhum alarme.

> É a mesma lição que este repositório já aprendeu duas vezes — na reconciliação
> de acionamento órfão e no vigia de handoff: **um estado que só é observado
> quando nasce não é observado.**

**O que custa esquecer:** o corpus normativo é a base para responder cobertura
pelo contrato, e não pela prática. Ele agora EXISTE — 📊 11.409 trechos
indexados. O agente continuar dizendo "normalmente é coberto" deixou de ser
falta de acervo e passou a ser falta de ligar o acervo ao atendimento.

⚠️ **A lição que fica para a próxima falta de crédito:** mover documentos presos
de volta para um estado varrido faz o sistema tentar de novo — e, sem crédito,
produzir uma falha por documento por rodada. A saída correta é um estado
**visível e não retentável** até o saldo voltar. Ver
`DESENHO-ATUALIZAR-SEM-ESTRAGAR.md`, §5 item A.

---

## P-99 · 🧑 Duas telas da InfoCap ainda devolvem 500 — e uma delas é a produção

**Registrado em** 05/08/2026, durante o teste de leitura da InfoCap com
credenciais reais das duas corretoras.

📊 **O que foi medido**, com sessão autenticada e navegação somente-leitura:

```
/login              200 em 1,38s     ✅
detalhe de apólice  200 · 113 campos ✅ (inclusive `datemi` e `ramo`)
/producao           500              ❌
/cliente_ligacoes   500              ❌
```

O 500 é do lado deles: a mesma sessão que abre a apólice sem erro cai nessas
duas rotas. Não é permissão — é falha de servidor.

**O que destrava:** 🧑 abrir chamado com a InfoCap citando as duas rotas. O
contato já respondeu uma vez neste ciclo (foi assim que o login voltou), então
o caminho está aberto.

**O que custa esquecer:** `/producao` é a listagem por período — é dela que sai
a conferência de carteira e o lastro de qualquer relatório de produção. Sem ela,
a leitura da InfoCap funciona **por apólice** e não **por carteira**: dá para
conferir um contrato, não dá para varrer a base. Todo trabalho que dependa de
"quantas apólices, de quais ramos, vencendo quando" fica esperando esta rota.

⚠️ **E não existe contorno bom.** Reconstruir a carteira apólice por apólice
exige saber de antemão quais apólices existem — que é exatamente o que
`/producao` responde. Tentar adivinhar a lista é como o sistema começa a mentir
sobre o tamanho da própria base.

**O que NÃO espera por eles:** 🤖 nada. O leitor de apólice já funciona e já é
útil. Esta pendência não bloqueia o atendimento; bloqueia o relatório.

---

## P-100 · 🤖 Nove dos dez normativos desceram sem crédito; o décimo é servidor deles

**Resolvido em parte em 05/08/2026.** Dez documentos normativos estavam parados
com o motivo gravado no banco: *"credito do Firecrawl esgotado — aguardando
plano"*. Estavam esperando crédito para uma tarefa que um `GET` resolve — todos
os dez já tinham no banco uma **URL de PDF direta**.

📊 Medido contra as 10 URLs reais, em 05/08/2026:

```
9 de 10 baixaram por GET direto — 3.940.679 caracteres, todos com SUSEP no texto
azul  3/3   ·   bradesco  2/2   ·   tokio  3/3   ·   hdi  1/2
```

**O que sobrou:** as **condições gerais da HDI** —
`hdiseguros.com.br/webprog/webtxt/condicoes_gerais/condicoes_gerais_000_432_01102019_09122019.pdf`
devolve **HTTP 500**. Não é a nossa ponta: o manual do segurado da HDI, no mesmo
domínio-irmão, baixou sem erro no mesmo minuto.

**O que destrava:** 🤖 achar a URL nova das condições gerais da HDI. O arquivo
tem data no nome (`01102019`), então é provável que eles tenham publicado uma
versão mais recente e derrubado esta. **Descobrir URL nova é justamente o que o
Firecrawl faz** — este é o primeiro caso do ciclo em que o crédito faria falta
de verdade (P-98).

**O que custa esquecer:** a HDI fica com manual do segurado e **sem** condições
gerais. O manual descreve a prática; as condições gerais são o contrato. Numa
pergunta de cobertura, o agente responderia pela prática sem poder citar a
cláusula — que é exatamente a distinção que o corpus normativo existe para
sustentar.

⚠️ **E a lição que fica maior que o caso:** o `fetch_error` dizia *"crédito do
Firecrawl esgotado"* em documentos que **nunca precisaram do Firecrawl**. O
motivo gravado descrevia a ferramenta que falhou, não o que o documento
precisava. Nove ficaram parados oito dias por causa dessa frase.

---

## P-101 · 🤖 O rótulo velho continua **escrito dentro do chunk** no Qdrant

Em 05/08/2026 o acervo foi reorganizado no banco: 2.582 rótulos de seguradora
rebaixados para NULL e `category` preenchida com cinco valores. **O índice não
foi refeito.**

`publish_card_sync` grava no Qdrant o texto com o rótulo **no começo da frase**:

```
(allianz / auto / cobranca) Boleto vencido nao pode ser reemitido…
```

📊 FATO (leitura de código, `attendance_distiller.publish_card_sync`): o prefixo
entra no `chunk`, e o `chunk` é o texto indexado — não é metadado.
💭 INFERÊNCIA: os 10.818 pontos publicados carregam hoje o prefixo antigo.

**Por que isto importa mais do que parecia.** O raciocínio de que "o rótulo
errado é inofensivo porque não existe filtro por seguradora" vale para o
*payload*. **Não vale para o texto.** A busca é híbrida e o BM25 casa por termo
exato: quem pergunta "boleto da Allianz" hoje casa lexicalmente com as 746
cartas genéricas cujo chunk começa por `(allianz …)`. O campo não filtra, mas a
palavra pontua.

- **Destrava:** 🤖 republicar as cartas publicadas — mesma função, mesmo
  caminho, sem código novo: `despublicar_carta_sync` + `publish_card_sync`, ou
  um passe que reescreva o ponto. Custo de embedding ≈ 650 mil tokens de
  `text-embedding-3-small` (💭 ordem de US$ 0,01).
- **Não foi feito agora porque:** outro agente está em `search_service.py`,
  `rerank_service.py` e `qdrant_service.py` neste momento. Reescrever 10.818
  pontos no meio do trabalho dele é colisão garantida.
- **Custa se esquecer:** o banco fica honesto e a busca continua respondendo
  pela bandeira errada — e o formato pior possível é esse, porque a auditoria
  no banco diz que está resolvido.

## P-102 · 🤖 `pii_check` virou caixa de marcação geral, e o nome mente

A coluna guarda hoje `deterministic`, `llm_instructed`, `qdrant_pendente`,
`superseded_por`, `motivo`, `por`, `sessao`, e agora `insurer_key_anterior`,
`rebaixado_em` e `prestadora`. Só as duas primeiras têm a ver com PII.

Isto é exatamente o defeito que o CLAUDE.md §12.1 manda consertar no CAMPO, não
no texto: *um nome que mente sobre o que guarda reinfecta todo leitor seguinte*.
Foi usada assim de propósito — é o padrão que `corrigir.py` já estabeleceu, e
`reconciliar_indice_sync` já lê `pii_check->>qdrant_pendente` em produção —
mas a dívida fica anotada em vez de silenciosa.

- **Destrava:** 🤖 migration que renomeie para `marcas` (expand-first: coluna
  nova, backfill, leitura dupla, corte) **e** dê coluna própria a `prestadora`,
  que é dado de negócio e não marca de processo.
- **Gatilho:** no dia em que alguém for FILTRAR por prestadora. Enquanto for só
  registro, jsonb basta.
- **Custa se esquecer:** a próxima pessoa lê `pii_check` e conclui que a carta
  tem problema de PII quando ela só mudou de dono.

## P-103 · 🤖 45 cartas publicadas sabem de quem são e continuam sem dono

O trabalho de 05/08 só **rebaixou**. Promover — dar rótulo a quem não tem —
é a operação inversa e não foi autorizada, com razão: errar para cima é o erro
caro. Mas o material está medido e pronto.

📊 Medido em 05/08/2026 com `curadoria_cartas.texto_nomeia_seguradora` sobre as
10.818 published:

```
30 cartas SEM rótulo cujo texto nomeia exatamente UMA seguradora
15 cartas cujo rótulo caiu e o texto nomeia OUTRA companhia — inclusive
   `sul -> sulamerica` e `bradesco auto/fleet -> bradesco`, que são a mesma
   empresa escrita errado
```

- **Destrava:** 🧑 decisão de que promover é aceitável, e depois 🤖 rodar o
  mesmo `rotular_acervo.py` com o passe de promoção ligado.
- **Custa se esquecer:** 45 fatos que TÊM dono continuam respondendo como
  genéricos — perda menor que o erro contrário, mas perda.

## P-104 · 🤖 `_fila_pendente` pagina por `started_at`, que também empata

Irmã do defeito consertado em `curar_sync` no mesmo dia. 📊 Medido no acervo:
paginar por chave que empata devolveu 11.640 linhas com 11.628 hashes distintos
— 12 repetidas e 12 nunca vistas.

`attendance_distiller._fila_pendente` faz `.order("started_at", desc=True)` com
`.range()` sobre `attendance_sessions`. O empate ali é menos provável (sessões
não nascem em lote como as cartas), e o dano é menor — a fila é um **contador**,
não uma escrita. Por isso ficou de fora do escopo em vez de entrar de carona.

- **Destrava:** 🤖 trocar por `.order("id")`, uma linha.
- **Custa se esquecer:** o número da fila no painel erra para menos, e o modo
  de recuperação (que liga por limiar) decide com um número errado.

## P-105 · 🧑 319 lotes de seguradora estão prontos e NÃO gravados

Preparado em 06/08/2026. O exportador, o prompt e um lote de prova destilado
existem; **nada foi para o banco**, porque a reindexação de 10.818 cartas estava
rodando em produção no mesmo minuto.

📊 `python backend/scripts/destilacao_max/exportar_seguradoras.py` produziu
**27 lotes · 319 conversas · 1,69 milhão de caracteres**, e o
`lote_016.destilado.jsonl` passou no `validar.py` com **12 conversas · 55 fatos**.

- **Destrava:** 🧑 terminar a reindexação; depois 🤖 destilar os 26 lotes
  restantes com o `PROMPT-DESTILADOR-SEGURADORA.md` e aplicar.
- **Custa se esquecer:** é o único acervo do projeto que ensina **o que a
  seguradora faz** em vez de o que a corretora faz, e o rótulo de seguradora
  dele é confiável por construção — o que o acervo antigo nunca teve.

### ✅ 06/08/2026 — `aplicar_seguradoras.py` existe, testado e NÃO rodado

O aplicador foi escrito, provado por mutação (12 mutações, 12 pegas) e rodado
**só em simulação**. 📊 Previsto sobre os 24 lotes destilados até então:
**288 sessões · 1.138 cartas · 1.138 inéditas**, `select` confirmando
`sessoes_marcadas = 0` e `cartas_do_acervo_observado = 0` no banco.

A decisão de rótulo foi tomada como recomendado — `insurer_key` da sessão
observada vale direto —, com um guarda estreito para o caso Porto→Azul. 📊 A
medição que sustenta: 915 de 918 fatos (99,7%) nomeiam a própria seguradora,
contra 32,3% no acervo de atendimento. Ver o cabeçalho do script.

**Falta só 🧑 mandar rodar com `--aplicar`, com a reindexação parada.**

O texto abaixo é o registro do que era o problema.

### O que faltava ANTES de aplicar: não existia `aplicar_seguradoras.py`

`aplicar.py` escreve `summary.distilled` em **`attendance_sessions`**. Este
acervo mora em `observed_sessions`. Aplicar com ele marcaria a sessão errada —
ou nenhuma.

E há uma decisão de verdade embutida: `aplicar.py` trata `seguradora` como
**candidata** e re-decide fato a fato em `curadoria_cartas.seguradora_do_fato`,
porque 📊 no acervo antigo só 32% das cartas etiquetadas citavam a própria
seguradora. **Aqui o rótulo é confiável por construção** — a conversa É com
aquela seguradora. Re-decidir por texto jogaria fora a única coisa que este
acervo tem de melhor.

- **Destrava:** 🧑 decidir se `insurer_key` da sessão observada vale como
  rótulo direto do fato (recomendação: sim, com a exceção do fato que atribui a
  regra a outra companhia); depois 🤖 escrever o aplicador.
- **Custa se esquecer:** sem isso o material fica em disco e a sessão nunca
  recebe a marca `distilled` — a próxima exportação refaz tudo do zero.

## P-106 · 🟠 O vocativo da URA só é mascarado porque a seguradora publica menus

📊 Medido em 06/08/2026 sobre as 319 sessões: **~240 ocorrências** de primeiro
nome de segurado escritas pela própria URA, na forma `"Fulano, só mais uma
informação:"`. Ela tem a MESMA forma de `"Guincho, borracheiro e chaveiro"`.

Quatro hipóteses foram medidas e **três foram refutadas** (forma · raridade ·
vocativo puro). A que funciona pergunta à seguradora o que ela oferece como
opção de menu, exige que a palavra apareça como opção em **4 sessões
distintas**, e mascara o resto.

**Ela depende de um acervo grande o bastante para conter o próprio
vocabulário.** Numa corretora nova, com 20 sessões observadas, o vocabulário de
menu fica pobre e a regra passa a mascarar palavra de menu — perda de
conhecimento, não vazamento.

- **Destrava:** 🤖 quando o acervo observado passar de ~50 sessões por
  seguradora, reconferir com `medir_vocabulario_de_menu`; ou 🧑 decidir semear o
  vocabulário a partir dos mapas do Atlas, que já são globais.
- **Custa se esquecer:** o mascarador fica silenciosamente mais guloso quanto
  menor a corretora, e o custo aparece onde ninguém olha.

## P-107 · 🟠 838 eventos observados não pertencem a sessão nenhuma

📊 Medido em 06/08/2026:

```sql
select count(*) from observed_events where session_id is null;   -- 838
```

São **4,3% dos 19.421 eventos**, espalhados por 4 seguradoras, e mais 1 evento
apontando para uma sessão que não existe. Todo exportador que parte de
`observed_sessions` é cego para eles — inclusive o novo.

- **Destrava:** 🤖 investigar se são captura anterior ao pareamento de sessão
  ou perda de correlação no `observer_intake`, e repará-los por
  (`observer_number`, `counterparty`, janela de tempo).
- **Custa se esquecer:** é conhecimento capturado, pago em risco de sessão, e
  invisível para sempre.

## P-108 · 🟡 O protocolo de 12 dígitos da Porto atravessa o mascarador

📊 17 ocorrências nos lotes exportados, na forma `1-122244434702`. A regra
`{NUMERO}` do `templatize` cobre 7 a 11 dígitos; esta tem 12 e vem colada num
prefixo `1-`. A regra `{PROTOCOLO}` exige a palavra "protocolo" ao lado, e a
Porto imprime o número na linha **seguinte**.

Não é dado de pessoa e o `validar.py` reprova qualquer carta que o contenha —
então ele não chega ao acervo. Mas ele chega ao **lote**, e ao destilador.

- **Destrava:** 🤖 estender a faixa de `{NUMERO}` ou reconhecer o padrão
  `\d-\d{10,}`. Uma linha, com controle de que "197" e "2026" sobrevivem.
- **Custa se esquecer:** um identificador de atendimento de um segurado real
  fica legível num arquivo em disco.

## P-109 · 🟠 `aplicar.py` marca a sessão ANTES de gravar as cartas

Encontrado em 06/08/2026 ao escrever o `aplicar_seguradoras.py`, que faz o
contrário de propósito.

`aplicar.py` escreve `summary.distilled` dentro do laço, conversa a conversa, e
só faz o `upsert` das cartas no **fim do arquivo**. As duas escritas não são uma
transação. Se a rodada cair entre elas — rede, chave expirada, Ctrl-C — as
sessões já marcadas ficam declaradas destiladas **sem uma carta no acervo**, e a
marca é justamente o "não volte mais": `exportar.py` e o destilador as pulam
para sempre.

A carta é idempotente (`on_conflict=card_hash, ignore_duplicates`); a marca é
irreversível na prática. Gravando as cartas primeiro, qualquer queda deixa
trabalho refazível. Gravando a marca primeiro, deixa conhecimento perdido em
silêncio — e ninguém descobre, porque o sintoma é uma sessão que parece pronta.

Não entrou de carona no trabalho de 06/08 porque `aplicar.py` está em uso e
funciona; trocar a ordem dele é uma mudança de comportamento que merece o seu
próprio controle.

- **Destrava:** 🤖 mover o `upsert` das cartas para antes do laço que marca as
  sessões — a mesma ordem que `aplicar_seguradoras._gravar` já usa e que
  `test_a_carta_da_seguradora_sabe_de_quem_e` já guarda nas duas direções.
- **Custa se esquecer:** cada queda no meio de uma rodada apaga em definitivo o
  conhecimento das conversas que estavam no arquivo naquele momento, e a perda
  não deixa rastro nenhum.

### ✅ RESOLVIDO em 08/08/2026

`aplicar.py` foi partido em `_planejar` (só lê) / `_gravar` (só escreve) — a
mesma forma de `aplicar_seguradoras.py`, e é essa separação que torna a ordem
uma escolha em vez de uma consequência: enquanto o plano era feito dentro do
laço que já escrevia, a ordem antiga era a única possível. Agora `_gravar` faz
o `upsert` de todas as cartas e só depois marca as sessões, com releitura
imediatamente antes de cada marca.

- **Guarda:** [`test_a_carta_e_gravada_antes_da_marca.py`](../../backend/tests/test_a_carta_e_gravada_antes_da_marca.py)
  — a linha de controle **reconstitui a `_gravar` antiga dentro do teste** e
  submete as duas à MESMA queda. A antiga termina com a sessão marcada e zero
  cartas; a nova, com as cartas no acervo e a sessão ainda na fila. Sem esse
  bloco o guarda não teria como falhar: exercitar só a ordem certa passaria
  igual no dia em que alguém invertesse tudo de volta.

> A marca congelada que estava no mesmo arquivo virou [P-129].

## P-110 · 🔴 A captura das duas corretoras está PARADA, e o painel diz "Conectado"

📊 Medido em 06/08/2026 (projeto `dcajcvlzcjbmyapmklil`):

```sql
select c.company_name, max(e.created_at) from observed_events e
  left join companies c on c.id = e.company_id group by 1;
--  AutoFleet         04/08 20:34Z   (42 h)
--  Resulta Seguros   03/08 20:19Z   (67 h)
```

📊 E a causa, em `GET /instance/all` do provedor no mesmo dia: **três das quatro
instâncias com `webhook=''` e `events='MESSAGE'`** — inclusive a da AutoFleet,
que estava `Connected: true, LoggedIn: true` naquele instante.

O reconector chamava `/instance/connect` com só `{"immediate": True}`, e o
`Connect` do Go grava `Webhook = data.WebhookUrl` **por cima**: religava o canal
mudo. Consertado em `f81e24e` (`corpo_do_connect` recusa URL vazia; o reconector
rotaciona a credencial antes de religar).

⚠️ **O conserto não repara o estado que já existe.** As instâncias em produção
continuam sem webhook até alguém emitir um `connect` completo. O reconector novo
só age sobre canais que a sonda vê caídos — e a AutoFleet aparece de pé.

- **Destrava:** 🤖 merge de `f81e24e` na `main` (o deploy sai da `main`) **e** um
  `connect` completo por instância para regravar webhook e eventos. 📊 É seguro
  com a instância no ar: `UpdateInstanceSettings` (`whatsmeow.go:175+`) só troca
  campos em memória — não há `Disconnect()` nem `killChannel` no caminho.
- **Custa se esquecer:** o produto segue sem matéria-prima. Nenhuma conversa
  entra no Atlas, no Espelho ou no RAG, e a tela continua dizendo que está tudo
  certo — que é a razão de isto ter durado três dias sem ninguém notar.

## P-111 · 🟠 A linha da Resulta está pareada no telefone errado

📊 `integrations` em 06/08/2026: a instância `ab-obs-04b5cdbc04-1` (Resulta) tem
`paired_phone_e164 = +554788087463` — **DDD 47**. O Founder identificou o número
como o **dele**, não o da atendente (que é DDD 48).

Isso explica o sintoma inteiro: a atendente pedia QR para uma linha que já tinha
dono, e 📊 com `jid` preenchido o whatsmeow **reconecta** em vez de emitir QR
(`whatsmeow.go:325-335`), então o QR não podia vir.

O caminho existe desde `f81e24e`: `POST /api/whatsapp-channel/pairing/liberar-numero`
recria a instância com o **mesmo nome** (preservando `observer_number`, metade da
chave de dedup de 69.150 transcrições) e com `jid` vazio, e o QR volta.

- **Destrava:** 🧑 decisão do Founder — trocar encerra a sessão do DDD 47. Depois
  🤖 deploy + clicar "trocar número" na tela da Resulta e escanear o QR.
- **Custa se esquecer:** a corretora segue capturando o WhatsApp errado, e o que
  o produto aprende não é o atendimento dela.

## P-112 · 🟡 O `/instance/status` do provedor não sabe o que o banco dele sabe

📊 `instance_service.go:391-400`: `Status` lê `clientPointer`, que é **memória do
processo**. Com `CONNECT_ON_STARTUP=false` (a config de produção), todo restart
do Evolution Go esvazia esse mapa e **toda** instância passa a responder
`LoggedIn: false` — inclusive as perfeitamente pareadas.

`f81e24e` contornou no nosso lado (`_sessao_registrada` pergunta ao
`/instance/all`, que é o estado durável). O contorno é correto e deve ficar, mas
a mentira continua na fonte, e todo consumidor novo do `/status` vai cair nela.

📊 Dois mapas divergentes agravam: `instance_service.go:366,381,647,796` apagam
`clientPointer` sem apagar `myClientPointer`. Depois de um `logout`, o `status`
diz "não está rodando" e o `connect` diz "já está rodando" — e não sobe cliente
nenhum. Foi medido: um `connect` na instância da Resulta em 06/08 às 14:54Z não
produziu **uma linha de log**.

- **Destrava:** 🤖 patch 0007 no fork — `Status` consultar o `jid` persistido, e
  os quatro `delete(clientPointer)` limparem os dois mapas. Exige rebuild da
  imagem e teste com as duas corretoras no ar.
- **Custa se esquecer:** todo diagnóstico futuro começa por uma leitura falsa, e
  a instância zumbi (`client != nil && !IsLoggedIn()`) trava a corretora até o
  contêiner reiniciar.

## P-113 · 🔴 O patch 0007 do fork NÃO foi compilado

`infra/evolution-go-autobrokers/patches/0007-status-e-runtime.patch` está escrito
e 📊 os sete patches aplicam limpo sobre o upstream `9337afc4` (`git apply
--check` verde nos sete). Mas **não houve compilação**: não há Go nem Docker na
máquina desta sessão.

Revisão manual feita: `strings` já importado, chaves balanceadas (173/173),
`ClearInstanceCache` está na interface `WhatsmeowService`, `LogWarn` já usado no
arquivo, `instance` existe nos escopos tocados.

Um erro descoberto NA revisão e evitado: a primeira versão aplicava o helper
também no `ForceReconnect`, onde o `killChannel` novo já foi criado logo acima —
`ClearInstanceCache` o fecharia antes de o `StartClient` seguinte encontrá-lo.
Ficou de fora, com o motivo escrito no próprio helper.

⚠️ **O deploy do `evolution-go-teste` derruba a AutoFleet.** `CONNECT_ON_STARTUP=false`
significa que nenhuma instância religa sozinha depois do restart do contêiner.

- **Destrava:** 🤖 `go build` (o Dockerfile já roda `go test ./pkg/instance/service`
  antes do build, então erro de compilação **reprova o build** e a imagem antiga
  continua no ar — o gate existe). Depois 🧑 disparar o deploy e, logo em seguida,
  🤖 um `POST /instance/connect` completo por instância para religar e regravar
  webhook.
- **Custa se esquecer:** o `/instance/status` segue mentindo após cada restart e
  a instância zumbi segue capaz de prender uma corretora até o contêiner cair.

## P-114 · 🟠 O webhook das instâncias precisa ser regravado depois do deploy

📊 Medido em 06/08/2026 ~16:40Z, com o `smith-api` ainda rodando o código antigo:
`integrations.webhook_token_prefix` da Resulta era `zAkKqY_b` enquanto o campo
`webhook` da mesma instância no provedor estava **vazio**. O banco tinha a
credencial; o provedor não tinha a URL. É o defeito do reconector acontecendo em
produção enquanto a correção esperava deploy.

O conserto está na `main` (`f81e24e` + `b078dcf`), mas **ele não repara o estado
que já existe**: o reconector novo só age sobre canais que a sonda vê caídos.

- **Destrava:** 🤖 depois do deploy do `smith-api`, um `connect` completo por
  instância ativa (o mesmo procedimento da Parte II §10 do relatório de
  auditoria), e então conferir `observed_events` algumas horas depois.
- **Custa se esquecer:** captura parada com o painel dizendo "Conectado" — a
  falha que já custou 42 h e 67 h sem ninguém notar.

## P-115 · 🟡 Cobrança e auxiliares: número separado, decisão pendente

O Founder (06/08/2026): *"precisam ser números separados porque são serviços
diferentes, mensagens diferentes... precisamos conversar sobre detalhes de parear
a cobrança e o agente de atendimento separadamente por causa de bloqueio"*.

O caminho já existe e está guardado por teste: `channel_identity` produz
`ab-aux-{b10}-{slug}` para `purpose="auxiliary:<slug>"`, separado do número da
corretora, e `numero_proprio()` responde quem exige QR próprio. **Nada foi
ligado** — é só o vocabulário pronto.

O que falta é decisão de produto, não código: quantos números, quem pareia, qual
o aquecimento antes do primeiro disparo, e o que acontece quando um número é
bloqueado no meio de uma régua de cobrança.

- **Destrava:** 🧑 conversa com o Founder sobre a régua de cobrança temporária
  via Evolution GO (antes da API Oficial da Meta), depois 🤖 a SPEC.
- **Custa se esquecer:** cobrança sai pelo número de atendimento da corretora, e
  um bloqueio derruba o atendimento junto — os dois serviços no mesmo risco.

## P-116 · 🟡 A captura voltou a estar CONFIGURADA — falta prova de que GRAVA

📊 06/08/2026 ~17:00Z, com o `smith-api` já rodando o código novo (os quatro
sinais do pareamento respondem `True` no `/health`; `git_commit` segue
`nao-injetado` porque o EasyPanel não passa o build-arg — e foi por prever isso
que os sinais existem).

**O que ficou provado**, conferido hash a hash entre provedor e banco:

| corretora | `webhook` no provedor | hash no banco | bate |
|---|---|---|---|
| AutoFleet | `…/e3Yd…`→ `cb369f28…` | `cb369f28…` | ✅ |
| Resulta | `9bcf4b49…` | `9bcf4b49…` | ✅ |

📊 E o socket da AutoFleet está **vivo**: `GET /user/privacy` respondeu 200 em
0,3 s com dados reais do WhatsApp dela, contra timeout de 30 s na Resulta (sem
sessão) como linha de controle.

📊 O reconector NOVO religou a Resulta sozinho, com webhook e os quatro eventos —
o conserto funcionando em produção, sem intervenção manual.

**O que NÃO ficou provado:** que uma conversa nova foi gravada. A AutoFleet segue
com `observed_events` parado em 04/08 20:34Z (44 h). Isso depende de chegar
mensagem real e **não é observável por mim**. 📊 O log da instância mostra que
em 05/08 23:23Z ela ainda RECEBIA mensagens e as despachava para o webhook vazio
— foram perdidas exatamente como a auditoria descreveu.

- **Destrava:** 🤖 rodar a query de `observed_events` daqui a algumas horas. E
  agora o produto avisa sozinho: `decidir_alarme_de_entrega` (e8ec78b) abre
  incidente na Caixa do Admin quando um canal diz "conectado" e passa 6 h sem
  gravar. 📊 A AutoFleet cai nessa condição **hoje** — o alarme dispara no
  primeiro ciclo do heartbeat depois do próximo deploy, e essa será a primeira
  prova de que ele funciona.
- **Custa se esquecer:** nada — pela primeira vez, o esquecimento é coberto. Era
  justamente a ausência disso que deixou 42 h e 67 h passarem sem ninguém notar.

> **P-114 fica RESOLVIDO por esta entrada** na parte que era acionável: os
> webhooks foram regravados e conferidos. O que resta é medição no tempo, e é o
> que esta pendência acompanha.

## P-117 · ✅ RESOLVIDO — a captura da AutoFleet voltou, e está provada

📊 06/08/2026 17:42Z, `attendance_transcripts`: **124 linhas na última hora**, a
mais recente **6 segundos** antes da consulta. `source='live'`, com sessão,
entrada e saída, texto e áudio. Conversas reais de sinistro (perito, oficina,
pneu, roda) — e `attendance_sessions` com 15 sessões em 2 horas.

A mensagem de teste que o Founder mandou está gravada inteira:

```
17:29:38  in   "Boa tarde Regina. Tô só enviando uma msg de teste"
17:31:16  out  "opa"
17:31:21  out  "boa tarde"
```

**Isto encerra o P-110, o P-114 e o P-116** na parte que era acionável: o
conserto do webhook (`f81e24e`) restaurou a captura em produção, e o reconector
novo religou a Resulta sozinho, com webhook e os quatro eventos.

⚠️ O que NÃO estava quebrado, e eu quase tratei como se estivesse:

- `observed_events` parado desde 04/08 **é o comportamento correto**. Ele guarda
  o HISTORY_SYNC, que só chega no pareamento. Conversa ao vivo vai para
  `attendance_transcripts` — são dois acervos, não um com defeito.
- `conversations` vazia **é o comportamento correto**. Ela nasce no pipeline do
  agente, e `observer_tap` consome o evento enquanto o agente está desligado.
  Com os quatro agentes `is_active=false`, a tela "Atendimentos → Conversas"
  vazia é a decisão do Founder funcionando, não uma falha.

## P-118 · 🟠 O Espelho existe, mas mora só no admin

📊 As conversas capturadas da AutoFleet estão em `/admin/espelho`
(`attendance_sessions` + `attendance_transcripts`, via
`admin_atlas.espelho_sessoes` e `replay_atendimento`). A corretora **não** as vê:
o dashboard dela mostra `conversations`, que é a central do AGENTE.

O Founder (06/08): *"as conversas precisam ir pro dashboard pra fazer o
atendimento dentro do chat de conversas, devem aparecer para o observador na
central de agentes"*.

⚠️ **Isto é mudança de produto, e tem um risco que precisa de decisão.** A tela
`Atendimentos → Conversas` tem campo de resposta. Espelhar ali as conversas
capturadas sem mais nada cria uma porta por onde alguém responde — e a mensagem
sai pelo WhatsApp da corretora. Com todos os agentes desligados de propósito,
essa porta não pode nascer aberta por acidente.

Três caminhos, e a escolha é do Founder:

1. **Espelho read-only no dashboard** (nova aba, sem campo de resposta) — mostra
   o que a equipe conversou, sem criar caminho de envio. É o menor risco.
2. **Conversas do observador na central de atendimento, com envio bloqueado** até
   o botão "Ligar agente" — mais próximo do pedido, exige um guarda explícito e
   testado no caminho de envio.
3. **Só depois de ligar o agente** — o comportamento de hoje, sem mudança.

- **Destrava:** 🧑 decisão entre os três, depois 🤖 a implementação.
- **Custa se esquecer:** a corretora não vê o próprio atendimento, e o produto
  parece vazio para ela mesmo capturando tudo.

## P-119 · 🟡 Áudio e imagem no chat da corretora aparecem, mas não tocam

Decisão do Founder, 06/08/2026: fica para depois, e a mensagem precisa aparecer
de algum jeito enquanto isso.

O Bloco 1 do espelho grava mídia como `[audio]` / `[imagem]` no chat: a mensagem
EXISTE e é visível, mas não reproduz. 📊 Não é caso raro — na primeira hora
medida da AutoFleet havia áudio de cliente no meio das conversas de sinistro.

A mídia já é baixada e guardada com o que é preciso para recuperá-la: 📊 o
`/health` prova em duas linhas (`midia_recuperavel` e `midia_chave_escondida`),
e `observer_intake.COORDENADAS_DE_MIDIA` grava `mediaKey`/`directPath`. Falta a
ponta do chat — subir para o storage e devolver uma URL que o navegador toca.

- **Destrava:** 🤖 reusar `webhook._upload_media_bytes` (que já faz isso no
  pipeline do agente) a partir da ponte do espelho, e o player no
  `ConversasClient.tsx`. Sem peça nova.
- **Custa se esquecer:** a atendente vê `[audio]` e precisa ir ao celular para
  ouvir — o que derrota o motivo de existir o chat no dashboard.

## P-120 · ✅ DECIDIDO — o "melhor jeito de atender" é GLOBAL, não por corretora

Eu sugeri que o agente aprendesse o tom de cada corretora a partir das respostas
capturadas da equipe dela. **O Founder recusou, e a razão dele é melhor que a
minha proposta:**

> *"Não sei se pode gerar confusão. Ter a melhor forma de atender todas as
> corretoras e todas terem o melhor seria mais valioso. Empatia, humanizada, se
> colocar à disposição, ser educada, agir como um humano. Essa melhor forma deve
> ser global e não só de uma corretora. Todas devem usufruir do melhor que temos
> globalmente."*

Fica registrado como decisão, não como pendência de código: o aprendizado do
Observador alimenta a conduta **global** do produto. Uma corretora que atende mal
não deve ensinar o agente a atender mal — nem para ela mesma.

Isto NÃO impede personalização de superfície (nome do atendente, tom escolhido no
painel, mensagem de abertura), que já existe em `Personalização → Agente de
Atendimento` e continua sendo da corretora.

- **Destrava:** nada. É decisão tomada.
- **Custa se esquecer:** alguém reabre a ideia daqui a três meses sem saber que
  já foi decidida, e o produto ganha uma inconsistência que ninguém pediu.

## P-121 · ✅ RESOLVIDO — a classe de erro que matou o espelho existia em mais 3 lugares

📊 06/08/2026. O espelho do chat não criava conversa nenhuma. O `/health` dizia
`espelho_no_chat: true` e o Redis contava a verdade:

```
espelho_contadores: {"erro:ImportError": 2255}
```

A ponte fazia `from app.services.integration_service import integration_service`.
**Esse nome não existe** — o módulo exporta a fábrica `get_integration_service(client)`.
2.255 tentativas mortas no import, dentro do `try/except` que protege a captura.

**Por que o teste não pegou:** eu havia DUBLADO o módulo com
`falso.integration_service = _Servico()` — a forma que eu imaginava. Todo teste
ficou verde contra uma API inexistente. *Um dublê valida a sua suposição, não a
realidade.*

A varredura que nasceu disso (`test_todo_import_aponta_para_algo_que_existe`,
311 módulos, sem importar nada) encontrou **mais três em produção**:

| onde | import | consequência |
|---|---|---|
| `dispatch_router.py:164` | `integration_service` | o aviso "o segurado NÃO recebeu o protocolo" nunca chegava ao humano |
| `dispatch_router.py:169` | `whatsapp_service` | idem — segundo import do mesmo bloco |
| `whatsapp/service.py:54` | `wa_send_retry` | o nome **não existia em lugar nenhum**; o módulo quebrava ao ser importado |

Os três estavam dentro de `try/except` ou em módulo não importado — por isso
nunca deram erro visível. O primeiro é o mais caro: toda vez que o protocolo
falhava, o alerta ao humano falhava junto, e o log dizia "alerta não saiu" como
se fosse rede.

Todos corrigidos. `wa_send_retry` passou a existir de fato em
`whatsapp_service.py`, com a política que o comentário já descrevia (3
tentativas, espera exponencial, só falha transitória, última falha sobe).

- **Destrava:** nada. Resolvido e guardado por teste.
- **Custa se esquecer:** era exatamente o que já custava — funcionalidade morta
  em silêncio, com log que parecia outra coisa.

---

## P-122 · 🟡 O teto de 1.000 linhas: o que foi consertado e o que ficou

🤖 **Execução** · aberta e parcialmente resolvida em 06/08/2026

O PostgREST tem um teto de linhas por resposta que **vence o `.limit()`
pedido**. Pedir 1.500 não dá erro: devolve 1.000 e o código segue achando que
leu tudo. Uma auditoria independente varreu o backend e achou ~28 pontos.

### ✅ Resolvido — o que dava dinheiro e o que afeta a conversa

📊 Medido em produção (`dcajcvlzcjbmyapmklil`) em 06/08/2026 23:43 UTC:

| onde | no banco | chegava | o que estragava |
|---|---|---|---|
| `api/billing.py` | 4.648 | 1.000 | **consumo que o CLIENTE vê**, com multiplicador de venda |
| `control_plane/unit_economics.py` (×2) | 4.406 + 4.787 | 1.000 | relatório de custo — **e o detector de truncagem, derrotado pelo próprio truncamento** |
| `workers/billing_tasks.py` | 5.646 | 1.000 | débito de créditos em fatias, com `processed` mentindo |
| `detectors/conexoes.py` | 4.267 | 1.000 | **alerta de orçamento que não dispara** — e se cala mais no maior cliente |
| `services/agent_memory.py` (×2) | 1.577 | 1.000 | o que o agente lembra: base da resposta, da carta e do RAG |
| `atlas/espelho_chat.py` | 1.570 | 1.000 | 19 conversas abertas e vazias na tela da corretora |
| `whatsapp/channel_state.py` | — | — | alarme de canal mudo lendo a corretora errada |

Peça única: [`backend/app/leitura_completa.py`](../../backend/app/leitura_completa.py)
(`ler_paginado` / `ler_paginado_async`). Mora em `app/` e não em `app/core/`
porque `app/core/__init__` puxa a configuração inteira — 📊 com o import lá,
quatro testes que passavam viraram `ModuleNotFoundError`.

**Escolha deliberada: paginar, não criar função SQL.** Somar dentro do Postgres
seria uma ida em vez de cinco, mas exige migration — e migration no meio de um
lançamento é onde nasce o bug que atrasa tudo. 📊 4.648 linhas são 5 idas ao
banco num relatório sob demanda. Se alguma leitura passar de ~20 mil, a conta se
inverte e aí vale a função SQL; o teto de `ler_paginado` avisa quando esse dia
chegar, em vez de truncar calado.

### 🟠 Fica pendente — 17 pedidos em 9 arquivos

Nenhum erra HOJE: 📊 `intelligence_signals` = 21 linhas, `intelligence_findings`
= 6, `research_*` praticamente vazias. Todos agregam ou contam, então passam a
errar em silêncio no dia em que a tabela crescer.

`agents/gateway_cutover.py` (1, e **ignora o parâmetro `dias` que recebe**) ·
`api/admin_atlas.py` (1) · `api/research.py` (4) ·
`intelligence/detectors/qualidade.py` (1) · `intelligence/feedback_service.py`
(2) · `intelligence/rule_engine.py` (5) · `observability/sli.py` (1, com
`.limit(50_000)` — o número é a assinatura de quem achou que estava lendo tudo)
· `regression_sentinel.py` (1) · `research/monitor_service.py` (1)

- **Destrava:** nada. Trabalho de execução, sem dependência externa.
- **Gatilho para consertar:** quando a tabela de origem passar de ~800 linhas,
  ou quando o número for usado para decidir dinheiro.
- **Como:** `ler_paginado` com `chave_unica="id"`. Nunca por data: 📊 uma
  paginação por `created_at` neste repositório perdeu 12 linhas e repetiu 12 em
  11.640, porque datas empatam.
- **Guarda:** [`test_ninguem_pede_mais_de_mil_linhas_de_novo.py`](../../backend/tests/test_ninguem_pede_mais_de_mil_linhas_de_novo.py)
  varre o backend por AST e **reprova qualquer pedido NOVO**. A lista dos 17
  está lá dentro como linha de base — e o teste também reprova se um deles for
  consertado sem sair da lista, para ela não virar ficção.

### 🔴 Achado adjacente, e não é truncamento

📊 `usage_events`: **4.406 linhas, ZERO com `work_run_id`**. `custo_do_run()`
filtra por esse campo, devolve sempre `{eventos: 0, custo: 0}`, e
`orcamento_estourado()` **sempre responde False**. O teto de orçamento por Work
Run (SPEC-055 §25) está escrito, testado e desligado na prática — porque o elo
nunca é gravado. Não foi corrigido aqui: é assunto da SPEC-055, não deste teto.

### 💭 Não medido

Se `count="exact"` sobrevive ao teto do servidor. O código usa essa técnica em
17 lugares com fallback, o que sugere que ninguém confirmou. Não afeta nada do
que foi feito acima (paginação não depende disso), mas mudaria a técnica
recomendada para os 17 pendentes: seria 1 ida em vez de N.


---

## P-123 · 🔴 O maior grupo do acervo não gera playbook — e o eixo `outro` era o outro

> **Esta entrada foi escrita errada e reescrita no mesmo dia.** A versão
> original dizia: *"`ramo='outro'` nunca é produzido — 3 playbooks ativos são
> inalcançáveis"*. **Isso é falso**, e a medição que a desmentiu está abaixo. A
> versão errada não fica arquivada porque pendência é lista de trabalho, não
> diário: quem ler amanhã precisa do fato certo. O erro fica registrado aqui,
> no cabeçalho, para não se repetir — **eu tinha olhado o eixo errado.**

📊 Medido em 07/08/2026 sobre 9.196 sessões destiladas.

`ramo='outro'` **é produzido, e muito**: 2.905 sessões, 32% de todo o material,
o segundo maior ramo. Os playbooks `outro/sinistro` (629 sessões úteis, nota
74,5) e `outro/consulta` (254, nota 69,6) não são mudos — estão entre os
maiores que existem.

**O eixo descartado é o do SERVIÇO, não o do ramo.** Duas linhas jogam fora
`servico == "outro"`:

- [`attendance_distiller.py:863`](../../backend/app/services/attendance_distiller.py#L863) — `if not ramo or servico in ("", "outro"): continue`
- [`attendance_distiller.py:1037`](../../backend/app/services/attendance_distiller.py#L1037) — `if servico in ("outro", "") or ramo in ("",): continue`

E o que elas jogam fora é o melhor material do acervo:

```
grupo                sessões ÚTEIS   nota    playbook
auto/outro                   2.219   74,4    NENHUM   ← o maior E o melhor
outro/outro                  1.468   67,2    NENHUM
residencial/outro              166   76,3    NENHUM
vida/outro                      24   72,9    NENHUM
                             -----
                             3.877 sessões — mais da metade do aproveitável
```

### A informação nunca se perdeu — ela é ignorada

O classificador grava **`tipo` E `servico`**. O playbook usa só `(ramo,
servico)`. Quando `servico='outro'`, o `tipo` tem a resposta, ao lado, e é
descartada:

```
dentro de servico='outro':
  auto        / cobranca      1.904 úteis   nota 76,2   ← melhor grupo do acervo
  outro       / cobranca        986         nota 72,7
  outro       / outro           381         nota 52,4   ← o único que é ruído
  residencial / assistencia     109         nota 78,5
  auto        / sinistro        103         nota 65,4
  auto        / apolice          64         nota 71,8
```

📊 **Cobrança é 2.890 sessões úteis com nota ~75, e 2.915 das 12.063 cartas do
RAG (24%).** É o maior bloco de atendimento humano bom da corretora, e o
produto não tem uma linha de conduta sobre ele.

### Por que `servico='outro'` foi descartado, e por que a decisão envelheceu

A regra é defensável na origem: um playbook de "outro" seria vago demais para
servir. Só que ela foi escrita quando "outro" era resto. Hoje é o maior balde —
e **`tipo` já o separa em grupos coerentes**. Descartar deixou de proteger e
passou a custar.

- **Destrava:** decisão de eixo (abaixo). Nada externo.
- **De quem é:** 🧑 Founder decide o eixo · 🤖 execução implementa.
- **O que custa esquecer:** o agente atende cobrança — 24% do trabalho — sem
  nenhuma conduta destilada, improvisando, enquanto 2.890 atendimentos humanos
  bons sobre exatamente isso estão gravados e não são lidos.

### 💭 A opção que eu recomendo (não medida, é desenho)

Deixar de tratar `outro` como valor e passar a tratá-lo como **ausência**:
quando `servico == "outro"`, usar `tipo` no lugar. Isso não inventa ramo novo,
não mexe no classificador e não migra dado nenhum — é uma linha de escolha de
chave. E faz nascer `auto/cobranca` (1.904 úteis, nota 76,2) já acima do piso.

Ver [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md) — a decisão de eixo, com as
alternativas e o que cada uma custa.

---

## P-124 · 🧑 `auto/bateria` está correto e mal lastreado

📊 Medido em 07/08/2026. O texto do playbook foi corrigido (três perguntas que
pediam placa, modelo e telefone viraram confirmação), mas o material que o
sustenta é fraco:

```
13 sessões usadas · 8 com score 0 · nota média 27,8/100
```

Score 0 não é nota baixa: é **"não houve atendimento humano"** — robô da
seguradora, central de prestadora, fragmento. Sobraram 5 atendimentos reais
para ensinar conduta de bateria.

Com o piso novo (`_MIN_SESSIONS_DEFAULT = 12` **úteis**), um playbook assim não
nasceria mais. Este nasceu antes.

- **Destrava:** a destilação das 1.767 sessões da fila (Bloco 5). Se ela trouxer
  atendimentos de bateria com humano, o grupo se re-sintetiza sozinho.
- **De quem é:** 🧑 Founder decide se ativa agora ou espera material melhor.
- **O que custa esquecer:** ativar hoje coloca no ar conduta destilada
  majoritariamente de robô. Esperar deixa o serviço sem playbook — o agente cai
  no prompt genérico, que é pior em coleta e melhor em honestidade.

---

## P-125 · 🟡 Os 7 playbooks ativos restantes não passaram por revisão de conteúdo

Nesta rodada foram corrigidas **11 frases** nos 12 playbooks ativos (10 com
espaço em branco literal, 1 com flag `ja_temos_na_apolice` errada) e os 6
rascunhos foram lapidados campo a campo.

Mas a lapidação campo a campo — objetivo, acolhimento, ordem da ficha,
sensibilidade — **só foi feita nos 6 rascunhos**. Os ativos receberam apenas as
correções que os detectores automáticos apontaram.

- **Destrava:** nada. É trabalho de leitura.
- **De quem é:** 🤖 execução.
- **O que custa esquecer:** detector pega o que sabe procurar. 📊 Dos 9 achados
  iniciais nos rascunhos, 6 eram falso positivo do próprio regex — o que mostra
  que a régua automática erra nos dois sentidos.
- **Quando:** depois da destilação. Vários desses playbooks serão reescritos
  pelo material novo, e revisar agora é revisar duas vezes.

---

## P-126 · ✅ RESOLVIDO — o Lapidador reescrevia com as regras de outra época

Registrado por completude, porque o padrão vale mais que o caso.

Duas peças escreviam o mesmo playbook: `attendance_distiller._STAGE2_SYSTEM`
(primeira vez) e `prompt_optimizer._REFLECT_SYSTEM` (reescreve o que está
ativo). O primeiro ganhou três campos e quatro proibições em 07/08/2026. O
segundo não ganhou nada, e pedia um JSON de 8 chaves — **o que ele não pede,
some do playbook que está no ar**.

📊 A janela real: só entre 3h e 10h UTC, no máximo uma vez por semana. E
`_mudancas` aparece em **0 dos 18 playbooks** — ele nunca rodou. O risco não era
iminente; era certo e sem data.

**A causa não era o texto: era existirem duas descrições da mesma coisa.** O
conserto não foi reescrever o segundo prompt com as mesmas regras — foi fazê-lo
`import`ar o primeiro (`REGRAS_DO_PLAYBOOK`). Regra nova já nasce valendo para
os dois.

**Onde mais isso pode estar acontecendo:** em qualquer par de peças onde uma
escreve e outra reescreve o mesmo objeto. Não foi varrido.

- **Guarda:** [`test_quem_lapida_obedece_quem_escreveu.py`](../../backend/tests/test_quem_lapida_obedece_quem_escreveu.py)
  — lê o import por **AST**, não por busca de texto: `REGRAS_DO_PLAYBOOK` citado
  num comentário passaria numa busca por substring e não importaria nada.

---

## P-127 · 🧑 Os ramos que existem no mercado e não existem no sistema

Decisão do Founder em 07/08/2026: **fica registrado e não se executa agora** —
a saída B de [`D-Playbook-01`](FOUNDER-DECISIONS.md).

O sistema classifica em quatro ramos: `auto`, `residencial`, `vida`, `outro`.
O mercado brasileiro tem muito mais, e o Founder perguntou por condomínio,
empresarial, responsabilidade civil, fiança e saúde.

📊 Medido em 07/08/2026 sobre as 12.063 cartas publicadas — quanto de cada tema
já existe no acervo:

| tema | cartas | % |
|---|---|---|
| condomínio | 468 | 3,9% |
| empresarial / patrimonial | 80 | 0,7% |
| frota | 74 | 0,6% |
| responsabilidade civil | 41 | 0,3% |
| fiança | 25 | 0,2% |
| saúde | 6 | 0,05% |

**Condomínio é o único com massa real.** Os demais quase não aparecem — e isso
**não prova que o ramo não importa**: prova que as duas corretoras capturadas
(Resulta e AutoFleet) trabalham auto e residencial. Uma corretora nova de
benefícios inverteria a tabela inteira.

- **Destrava:** material que justifique o ramo. O piso de evidência é 12
  atendimentos úteis; hoje só condomínio chega perto, e nem ele foi medido em
  ATENDIMENTOS (as 468 são cartas, não conversas).
- **De quem é:** 🧑 Founder decide quando · 🤖 execução implementa.
- **O momento ideal:** depois da destilação do material bruto, quando houver
  contagem de ATENDIMENTOS por tema — não de cartas. Antes disso, acrescentar
  cinco ramos cria cinco baldes abaixo do piso: playbooks que não nascem e
  telas que mostram categorias vazias.
- **O que custa esquecer:** quando entrar uma corretora de condomínio ou
  benefícios, o material dela cai em `outro` e se mistura com o resto — e a
  separação depois é mais cara que a classificação na origem.
- **Pré-requisito técnico:** antes de acrescentar ramo, ler o resultado da
  auditoria de padronização (P-128) — 📊 hoje existem **12 conjuntos distintos**
  de valores de ramo no código, e acrescentar um sexto valor a um vocabulário
  que já diverge multiplica o problema em vez de resolver.

---

## P-129 · ✅ RESOLVIDO — a marca da campanha era uma constante congelada

`aplicar.py:51` tinha `MARCA = "destilacao_max_29_07_2026"`, escrita à mão e
nunca trocada. 📊 As 1.941 cartas da campanha de 04/08/2026 foram gravadas com
a marca de 29/07: pelo campo que existe justamente para separá-las, as duas
campanhas são a mesma coisa.

E `CURADORIA-POR-SUBAGENTES.md:236` manda conferir a campanha por
`pii_check->>'por' = '<marca>'` — a conferência rodava, devolvia um número, e o
número somava as duas. **Um passo de conferência que responde com confiança à
pergunta errada é pior que passo nenhum: ele encerra a dúvida.**

O conserto não é um valor novo — é tirar o valor de onde alguém precisa lembrar
dele. `marca_de_hoje()` vem do calendário e `--marca` nomeia a campanha à mão,
como `aplicar_seguradoras.py` já fazia. `aplicar_sql.py` tinha a MESMA linha
congelada e agora **importa** a resposta em vez de manter a segunda cópia dela:
duas cópias congeladas do mesmo valor errado não são um defeito com duas faces,
são o defeito duas vezes.

- **Guarda:** [`test_a_marca_da_campanha_nao_e_congelada.py`](../../backend/tests/test_a_marca_da_campanha_nao_e_congelada.py)
  — controle: duas datas produzem duas marcas. Uma função que devolvesse sempre
  a mesma string passaria em tudo o mais.
- **Continua aberto · 🤖** as 1.941 cartas de 04/08 seguem com a marca errada
  no acervo. Nada foi reescrito no banco. Separá-las exige `created_at`, não o
  marcador — e é justamente essa a informação que se perdeu.


---

## P-130 · 🔴 O acervo oficial está VENCIDO — 14 de 15 documentos

📊 Medido em 08/08/2026 consultando o repositório público da SUSEP, produto por
produto, com os números de processo que temos no banco.

| documento | nossa versão | vigente hoje | versões existentes |
|---|---|---|---|
| **Porto Condomínio** | **01/12/2012** | **11/12/2025** | 26 |
| Bradesco Auto | 01/04/2023 | 11/07/2026 | 45 |
| Bradesco Empresarial | 04/08/2023 | **06/08/2026** | 28 |
| Porto Auto | 01/01/2026 | 01/07/2026 | **100** |
| Allianz Auto | 10/12/2025 | 22/07/2026 | 72 |
| Allianz Residencial | 01/12/2025 | 18/06/2026 | 30 |
| Allianz Vida | 16/12/2025 | 15/07/2026 | 11 |
| Porto Empresa | 11/04/2025 | 31/07/2026 | 25 |
| Azul Auto | 01/05/2025 | 30/08/2025 | 83 |
| **Porto Residência** | 05/12/2025 | 05/12/2025 | ✅ **em dia** |

**Um contrato de 2012 respondendo sobre um condomínio de 2026 é pior que não
ter documento nenhum**: ele erra com a autoridade de um documento oficial, e
quem lê não tem como desconfiar. É a mesma classe do defeito que o RAG já
conhece — *"o formato pior possível é esse, porque a auditoria diz que está
resolvido"*.

📊 O substituto do condomínio já foi baixado na auditoria: `200 application/pdf`,
1.185.165 bytes.

- **Destrava:** nada externo. O caminho está vivo e medido (P-131).
- **De quem é:** 🤖 execução.
- **O que custa esquecer:** cada resposta sobre cobertura sai de um contrato que
  não vale mais, e o sistema não tem como saber disso — não há campo de fim de
  vigência em documento nenhum.

---

## P-131 · ✅ MEDIDO — o caminho da SUSEP está vivo; o 404 tinha mudado de endereço

📊 Verificado ao vivo em 08/08/2026, sem autenticação.

### O 404 do P-22 não era morte, era endereço errado

```
www2.susep.gov.br/download/menuestatistica/SES/BaseCompleta.zip    404
www2.susep.gov.br/redarq.asp?arq=BaseCompleta%2ezip                200
   application/x-zip-compressed · 568.932.978 bytes (542,6 MB)
   last-modified: Mon, 03 Aug 2026 · ETag presente · accept-ranges: bytes
```

O tamanho bate com o da SPEC-066. `accept-ranges` e ETag confirmam que a
detecção por sentinela descrita nela funciona.

### O repositório de produtos funciona, e a armadilha é a porta

```
GET  .../REP2/Produto.aspx              200 — mas é a tela de LOGIN (a pegadinha)
GET  .../REP2/Produto.aspx/Consultar    200 — formulário PÚBLICO, um campo
POST .../REP2/Produto.aspx/Consultar    200 · 72.638 bytes · 72 versões · 1,08 s
GET  .../DownloadConsultaPublica/509527 200 application/pdf · 2.089.937 B
```

A resposta traz `Sociedade`, `RAM: 05 | AUTOMÓVEL - CASCO` e `Situação` — o
código de ramo que a SPEC-066 usa como ponte para o SES existe mesmo.

### P-22, metade resolvida

📊 Baixada a documentação oficial das tabelas do SES (734.925 B):
`sinistro_ocorrido` aparece **0 vezes**; `sinistro_retido` e `sin_dir` aparecem.
**A tese está confirmada.** A outra metade — se `retido` está zerado desde 2013 —
exige baixar os 542 MB e continua aberta.

### 404 mapeados, para ninguém retestar às cegas

`REP2/ConsultaPublica.aspx` · `REP2/Produto.aspx/ConsultarPorSociedade` ·
`menumercado/rcorretores/pesquisa.asp` · todo o CMS antigo `susep.gov.br/menu/…`
(migrou para `gov.br/susep`).

### Varredura em massa continua impossível, e não por educação

📊 O formulário público tem **um único campo** (`numeroProcesso`) e
`ConsultarPorSociedade` dá 404. **Não existe enumeração.** A ingestão dirigida da
SPEC-066 §A.2 não é uma escolha de bom comportamento: é a única via.

---

## P-132 · 🟠 39,2% das cartas com seguradora são de companhias sem contrato nenhum

📊 08/08/2026, sobre as 2.454 cartas com `insurer_key`: **961 (39,2%)** são de
seguradoras com **zero** condições gerais no acervo.

| seguradora | cartas | sinistro+assistência | site próprio | SUSEP |
|---|---:|---:|---|---|
| **yelum** | 359 | 163 | 🔒 exige CPF e nº da apólice | ✅ 54 versões, vig. 30/04/2026 |
| **hdi** | 267 | 119 | ⚠️ caminho antigo **morto (500)** | ✅ RCF 35 v. · Residencial 18 v. |
| zurich | 76 | 16 | ✅ residencial e vida | ✅ 6 versões |
| alfa | 40 | 15 | ✅ índice público com histórico | ✅ 21 versões |
| sura | 17 | 7 | ⚠️ WAF bloqueia | ✅ 20 versões |

**A Yelum é o caso que prova o método:** o site dela tem porteiro, o repositório
da SUSEP não. 📊 Duas versões baixadas na auditoria, `200 application/pdf`.

### O que NÃO vale, e é metade do valor desta entrada

- **Youse** (139 cartas) — 📊 **100 são de cobrança, 7 de sinistro/assistência**.
  Condições gerais não respondem *"por que meu boleto não chegou"*. Entra por
  ser barato, nunca por ser importante.
- **Itaú** (1 carta) e **Sompo** (8) — 📊 os dois **saíram do auto massificado**.
  A Sompo vendeu o varejo à HDI em 2023; o Itaú hoje vende Porto.
- **SES / sinistralidade** — 542 MB e responde **zero** perguntas de segurado no
  WhatsApp. É ativo de mesa de negociação (SPEC-065/067), não deste agente.
- **Ranking de reclamações** — 📊 a própria página declara os dados **congelados**
  no 4º trimestre de 2025.
- **Registro de corretores** — 📊 é uma SPA que exige JS e a API pede JWT. E este
  agente fala com **segurados**, não com corretores.

---

## P-133 · 🟠 Quatro das cinco ingestões travadas são bug nosso, não fonte morta

📊 Das 5 linhas em `discovered` com 0 chunks, **4 URLs respondem 200**:

- **Tokio** — 403 no nosso robô, **200 com User-Agent de navegador**
- **Bradesco Auto** — PDF de **5,7 MB**, estoura teto/timeout
- **Azul Residencial** — URL viva (200, 337 KB)
- **Youse** — `cdn.youse.com.br/docs/condicoes-gerais-plano-auto.pdf` (200)
- **HDI** — 🔴 a única que morreu de verdade (500 no caminho antigo)

**E um defeito de dado nosso:** 📊 os números de processo da Tokio estão gravados
**truncados** (`15414.100335/2004`, sem o `-74`). Com os dígitos: 50 versões,
vigente desde 14/04/2026. Truncado: **não encontrado, em silêncio**.

- **Destrava:** nada. Três consertos pequenos.
- **O que custa esquecer:** parece falta de fonte e é falta de cabeçalho HTTP.

---

## P-134 · 🟡 Pode ser busca, não acervo — medir antes de creditar

📊 Os limites de assistência da Porto (guincho 400 km, chave reserva 100 km) **já
estão dentro da CG140 que temos indexada**.

E o prompt do agente **não proíbe** falar de cobertura: ele exige **evidência**
(`prompts.py:201` — *"NUNCA confirme cobertura sem evidência da apólice"*).

Ou seja: para a Porto, pode não faltar documento — pode faltar **recuperação**.
Antes de creditar a documento novo uma melhora que seria de busca, medir: fazer
a pergunta ao agente hoje e ver se o trecho certo aparece entre os que chegam.

⚠️ Vale duplo porque 📊 o reranker Cohere continua **desligado** e, sem ele, os
trechos que chegam ao modelo saem de um RRF de duas buscas não comparáveis.

> **Atualizado em 08/08/2026 — o "3" desta pendência venceu.** SPEC-070 LOTE 0
> item 5: o corte final deixou de ser `rerank(top_k=3)` sobre uma lista única e
> passou a ser orçamento por namespace (3 vagas de contrato + 3 de carta + 2 do
> acervo da corretora). O trecho de contrato deixou de disputar vaga com a carta
> curta, que o BM25 favorecia por comprimento. A medição pedida acima continua
> valendo — e agora tem chance de dar outro resultado.

---

## P-135 · 🟢 O reranker Cohere: só falta a variável (e um restart)

📊 Auditado em 08/08/2026. O serviço está **completo e correto**:

| peça | estado |
|---|---|
| pacote `cohere>=5.0.0` | ✅ em `requirements.txt` |
| campo `COHERE_API_KEY` | ✅ em `config.py` (`Optional[str] = None`) |
| documentação | ✅ em `.env.example` |
| `RerankService.rerank()` | ✅ chama, injeta `rerank_score`, cai para pass-through no erro |
| cortes de relevância | ✅ 0,50/0,40/0,30 **preservados byte a byte** para a escala da Cohere |
| teste dos dois estados | ✅ `test_o_contrato_e_a_carta_nao_disputam_a_mesma_vaga.py` §6 |

**Falta a variável no ambiente.** 📊 Ela não está no repositório em lugar nenhum
(`docker-compose.yml` só sobe infra; o backend roda pelo EasyPanel) —
`pydantic-settings` a lê direto do ambiente, então basta declará-la lá.

⚠️ **E um restart.** `get_rerank_service()` é singleton e lê `settings` uma vez:
trocar a env com o processo de pé não liga o reranker.

O que muda quando entrar: `_get_score_scale` passa a devolver `rerank` e os
cortes migram de cosseno (0,28) para a escala calibrada da Cohere (0,40). O
caminho já existe e está testado nos dois estados.

- **Destrava:** uma chave da Cohere + restart do backend.
- **Dono:** 🧑 Founder (segredo).
- **O que custa esquecer:** 💭 ~US$ 2 por mil buscas. Sem ela, a ORDEM dos
  trechos dentro de cada faixa continua saindo de RRF, que mede concordância de
  posição, não relevância. A cota garante que o contrato **esteja na mesa**; o
  reranker é quem escolhe **qual** trecho de contrato.

---

## P-136 · 🔴 Quatro migrations da SPEC-067 escritas e **não aplicadas**

Escritas em 08/08/2026 pelo LOTE 0 (itens 4, 6, 7 e 8). Cada uma traz APPLY,
VERIFY executável e ROLLBACK, e nenhuma foi aplicada — por decisão: **quem
aplica é o Founder, depois de revisar.**

| ordem | arquivo | o que destrava |
|---|---|---|
| 1 | `20260808_01_spec067_a_vigencia_mora_na_versao.sql` | a vigência da SUSEP passa a ter onde morar (📊 hoje NULL em 35/35) |
| 2 | `20260808_02_spec067_o_indice_sabe_de_que_versao_veio.sql` | o backfill dos 29 endereços do esquema legado |
| 3 | `20260808_03_spec067_a_carta_sabe_de_que_contrato_saiu.sql` | achar as cartas de um contrato substituído |
| 4 | `20260808_04_spec067_o_pdf_e_o_texto_tem_endereco.sql` | os ponteiros do MinIO |

⚠️ **O código já grava nessas colunas.** `insurance_corpus.ingerir()` escreve
`vigencia_fonte`, `qdrant_doc_id`, `storage_ref`, `text_storage_ref` e
`arquivado_em` na linha da versão. **Enquanto as migrations não forem
aplicadas, o primeiro documento ingerido vai falhar no INSERT** (coluna
inexistente). Não é degradação silenciosa — é erro alto, e isso é proposital.

- **Destrava:** revisão + APPLY na ordem 01 → 02 → 03 → 04.
- **Dono:** 🧑 Founder.
- **O que custa esquecer:** o LOTE 1 (Porto) não roda. E o item 4 é o que fecha
  a janela: 📊 a URL da HDI devolve 500 e a da Allianz 403 — documento não
  guardado hoje pode não ser baixável amanhã.

---

## P-137 · 🟡 `normative_documents` e `..._versions` eram `SEM_ARQUIVO`, não órfãs

📊 08/08/2026. As duas tabelas **não têm arquivo** em
`backend/supabase/migrations/`, mas **têm versão** no banco:
`20260725215808 spec057_h1_normative_corpus`.

Um levantamento anterior afirmou que não tinham versão — e "órfã sem versão"
pede migration nova, que duplicaria o histórico. O DDL foi reconstruído do
catálogo do Postgres e registrado em
`docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`
(**proibido aplicar**), e o `MANIFEST.md` foi atualizado.

O que **não** foi feito: a reconciliação completa dos 92 versionamentos contra
os 60 arquivos. Um cruzamento por nome apontou dezenas de divergências, mas o
casamento por nome é pouco confiável — `20260803_01_spec063_destino_de_suporte_unico.sql`
corresponde à versão `spec063_01_destino_de_suporte_unico` e nenhuma regra
simples liga os dois. **Esse número não é medição.**

- **Destrava:** o baseline da SPEC-054 Bloco B, gerado do banco vivo.
- **Dono:** 🤖 execução (SPEC-054 B).
- **O que custa esquecer:** cada SPEC que passa acrescenta objeto sem dono
  documental, e o baseline fica mais caro a cada semana.

---

## P-138 · 🟡 A costura de um byte entre o item 1 e o item 4 da SPEC-067

`insurance_corpus._baixar_pdf_direto` ganhou **uma linha**:

```python
self._pdf_baixado = {"bytes": corpo, "media_type": "application/pdf"}
```

É o único ponto onde os bytes do PDF existem. `_guardar_a_fonte()` lê dali e
põe no MinIO. A função é a mesma que o item 1 reescreve (PyPDF2 → PyMuPDF).

⚠️ Se uma reescrita levar a linha embora, o arquivamento **degrada em
silêncio**: o texto continua sendo guardado e o PDF não.
`test_o_acervo_guarda_a_fonte_e_a_versao.py` §3 confere que ela existe, e a
mutação M3 provou que a conferência morde.

- **Destrava:** nada — está funcionando. É um aviso de fronteira.
- **Dono:** 🤖 quem mexer em `_baixar_pdf_direto`.
- **O que custa esquecer:** 📊 a URL da HDI já devolve 500. PDF não guardado é
  PDF perdido.

---

## P-139 · 🟡 A tabela é bloco atômico, mas não foi linearizada em frases

A SPEC-067 §4.5 pede duas coisas para tabela, e **só a primeira foi feita**:

| pedido | estado |
|---|---|
| tabela é bloco atômico, com título e notas de rodapé no mesmo pedaço | ✅ feito |
| corrigir célula girada (`odarugeS`) | ✅ não se aplica ao caminho escolhido |
| **linearizar a grade em frases** com `pdfplumber.extract_tables()` | ⬜ **não feito** |

O que existe: `regioes_de_tabela()` reconhece a corrida de linhas curtas, não
detecta título nem corta dentro dela, e estica a região até engolir `(1)`,
`(2)`, `*` e `Obs.`. A grade entra no pedaço como o PyMuPDF a entrega — uma
célula por linha, em ordem de leitura.

📊 Medido em 08/08/2026 no CG140: a tabela de carro reserva sai inteira, num
pedaço só, com `630`, `882` e as duas notas (`Limite diário R$ 90,00` e
`R$ 126,00`). A pergunta *"quantos dias de carro reserva eu tenho?"* é
respondível por esse pedaço sozinho — o limite é em reais, e a nota é que dá a
diária que converte reais em dias.

📊 E `pdfplumber` foi testado na página real (índice 102): devolve a grade de
24 linhas × 15 colunas, com as células giradas invertidas (`odarugeS`,
`ortsiniS`, `oriecreT`, `enaP`) — que o PyMuPDF, esse, lê certo. Linearizar
exigiria casar cabeçalho de dois níveis com células mescladas, e isso não cabia
no bloco sem arriscar o que já funciona.

- **Destrava:** nada urgente. Vira prioridade se aparecer uma pergunta cuja
  resposta dependa de **cruzar** linha e coluna (ex.: "quanto vale a cláusula
  26F para carro de porte médio?"), que a grade em ordem de leitura não entrega
  sem o modelo inferir o alinhamento.
- **Dono:** 🤖 execução (LOTE 1, se a conferência dos 10 pedaços reprovar).
- **O que custa esquecer:** 💭 a resposta que exige cruzamento sai plausível e
  errada — que é o pior formato de erro num contrato.

---

## P-140 · 🟡 Três produtos da Porto usam o formato de processo anterior a 2004

📊 Medido em 08/08/2026 pelo levantamento real
(`scripts/acervo/coletar_seguradora.py --seguradora porto --diagnostico`):
dos 71 produtos de varejo da Porto no catálogo oficial, **68 tiveram a versão
vigente confirmada e 3 não**:

```
auto   10.003506/01-14     05 | AUTOMÓVEL - CASCO
vida   005-00737/00        13 | VIDA (INDIVIDUAL)
vida   10.005843/99-51     13 | VIDA (INDIVIDUAL)
```

Não é truncamento nosso — é como o **próprio catálogo da SUSEP** os publica.
São processos anteriores ao formato de 17 dígitos, e o REP2 não os aceita: o
script os marca `processo_malformado` e **não indexa**, que é o comportamento
certo (§3.2.1).

⚠️ Eles **não** entram na lista `PENDENCIAS_DE_REPARO` do `susep_rep2.py`: ali
moram os que perderam dígito na nossa gravação e o catálogo recupera. Estes
três estão íntegros na fonte — o formato é que é de outra época. Inventar
dígito verificador para eles é o erro que aquela lista existe para impedir.

- **Destrava:** descobrir se o REP2 tem endereço alternativo para processo em
  formato antigo, ou confirmar que o produto está morto por outra via.
- **Dono:** 🤖 execução (LOTE 1, se algum deles for um produto que se vende).
- **O que custa esquecer:** 💭 um produto vivo fica fora do acervo para sempre,
  e a ausência é silenciosa — ninguém pergunta pelo que não está na lista.

---

## P-141 · 🟡 O ramo oficial da SUSEP não tem coluna — mora em `notes`

A SPEC-070 §5.2 é explícita: *"O REP2 devolve o ramo oficial numerado
(`05 | AUTOMÓVEL - CASCO`). **Grave o código e o nome oficiais.** Criar
vocabulário paralelo ao do regulador é divergência de graça."*

`normative_documents` não tem onde. O que existe é `product_line`, que é o
**nosso** slug (`auto`, `residencial`, `condominio`, …) e é o que a busca já
filtra na raiz do payload. O maestro grava o ramo oficial em
`normative_documents.notes` (`"ramo oficial SUSEP: 05 | AUTOMÓVEL - CASCO"`) e
o repete no `.jsonl` dos subagentes.

⚠️ Texto livre não é consultável. A pergunta *"quais documentos nossos são do
ramo 05?"* continua sem resposta em SQL.

- **Destrava:** uma migration com `susep_ramo_codigo` e `susep_ramo_nome` em
  `normative_documents` — expand-first, duas colunas nulas, nenhum leitor muda.
  Exige manifesto (CLAUDE.md §8).
- **Dono:** 🧑 Founder autoriza o manifesto · 🤖 execução escreve.
- **O que custa esquecer:** 💭 a divergência que a §5.2 quer evitar continua de
  pé, só que escondida numa coluna de observações.

---

## P-142 · 🟢 `vigente` e `faceta` já têm escritor — falta o LEITOR

📊 Até 08/08/2026 os dois campos tinham **índice de payload criado no Qdrant e
nenhum escritor** (o comentário em `qdrant_service.py` dizia isso com todas as
letras). O maestro da SPEC-070 fechou essa ponta: `_ingerir_sync` agora grava
na raiz `vigente`, `faceta`, `unit_id`, `parent_id`, `doc_kind`,
`susep_process` e `effective_from`, um jogo por pedaço.

**Falta a outra ponta.** A §6 da SPEC-070 pede duas buscas com orçamento
próprio:

```
busca 1  namespace=normative  ∧ (insurer_key=X ∨ ausente) ∧ vigente
busca 2  namespace=cards      ∧ (insurer_key=X ∨ ausente)
```

⚠️ E o filtro de vigência tem de ser **de dois braços** (`vigente=true` OU
chave ausente). Sem o segundo braço ele apaga as 12.063 cartas, que não têm
essa chave e nunca terão.

- **Destrava:** nada de fora — é trabalho em `search_service`/`qdrant_service`.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** hoje nada quebra, porque a versão revogada sai do
  índice na ingestão (D-Acervo-02). O custo aparece no dia em que uma remoção
  falhar: 📊 `delete_document` já respondeu "removi" com o Qdrant fora do ar, e
  aí as duas versões respondem com a mesma autoridade e nada no filtro separa.

---

## P-143 · ✅ A âncora certa não prova a afirmação certa — RESOLVIDO em 09/08/2026

📊 Achado por um auditor de ancoragem em 08/08/2026, no LOTE 1.

A auditoria da §6.5 confere **de onde a carta veio**. Ela não confere **o que a
carta acrescentou ao trecho**. São defeitos de famílias diferentes, e o segundo
passa inteiro pelo primeiro:

> `condominio_CARTAS.jsonl:185` afirma *"R$ 1.200,00 no Prata e R$ 1.800,00 no
> Ouro"* como se fossem os tetos dos planos. No contrato os dois valores estão
> nas cláusulas **34.6 e 34.7, ambas de LIVRE ESCOLHA** — a carta generalizou
> uma condição. O endereço está correto; um corretor que o abrir encontra o
> número **e a qualificação que a carta comeu**.

É a regra 7 da §10.3 (*o teste da cauda*) escapando pela porta que a auditoria
de âncora não vigia. E é exatamente o defeito que mais machuca: corpo fiel,
cauda inventada.

### 📊 O LOTE 2 mediu o alcance disto, e ele tem nome: **o adjetivo enxertado**

Dois auditores da Allianz, em lotes diferentes e sem se falarem, acharam o mesmo
caso — e nenhum dos três vereditos tinha casa para ele:

> *"Vendaval é cobertura **OPCIONAL** do Allianz Residência."* O escopo está
> literal no trecho citado, então o veredito é `ok`. Mas a palavra **opcional**
> não aparece em nenhum dos cinco trechos. **Um corretor que abrir esse endereço
> para provar "é opcional" não acha a prova.**

E é a classe de palavra mais cara de errar: `opcional` × `básica` decide se o
cliente **tem ou não** a cobertura.

📊 Medido em 09/08/2026 sobre as 1.536 cartas da Allianz, com um detector de
afirmação de contratação:

```
cartas que AFIRMAM ser básica/opcional/adicional     110
cujo trecho citado não traz nenhuma marca disso       52   (47%)
```

⚠️ **Esses 52 não são 52 defeitos confirmados.** O detector é grosseiro e erra
para os dois lados: a primeira versão dele acusou 182, e entre elas cartas em
que `Facultativa` era o **nome da cobertura** (RCF-V), não uma afirmação de
opcionalidade. O número serve para dimensionar o trabalho, não para condenar
carta. Só leitura decide.

- **Destrava:** nada de fora. É uma segunda auditoria, com outro prompt: dado o
  trecho e a carta, *a carta afirma algo que o trecho não sustenta, ou omite uma
  condição que o trecho impõe?*
- **Dono:** 🤖 execução.
- **Sugestão de escopo, na ordem:** (1) as ~110 cartas que afirmam
  básica/opcional/adicional, nas duas seguradoras — é o defeito com nome, dono e
  consequência clara; (2) as cartas de `limite` e `franquia`, onde um número
  vira afirmação e a qualificação some com mais facilidade.
- **Sugestão de veredito:** os três atuais não bastam. Dois auditores propuseram
  o mesmo quarto, com nomes diferentes (`ok_parcial`, `ok_com_enxerto`): a carta
  está ancorada, **e** carrega uma afirmação secundária sem lastro. Hoje isso
  passa como `ok` e não deixa rastro.

### ✅ RESOLVIDO — 09/08/2026

Três auditores leram as 129 cartas apontadas, uma a uma:

```
reescrever            72     a afirmação não tem prova em nenhum dos 5 trechos
provado_no_vizinho    38     a prova está a um pedaço de distância
provado               19     falso positivo do detector
remover_carta          0
```

📊 As 72 foram reescritas e aplicadas. Conferência depois: o detector aponta 57,
e **os 57 são exatamente os 57 já julgados como corretos** — zero pendentes.

**Os 38 `provado_no_vizinho` NÃO foram movidos**, e o motivo é um aviso que um
auditor deu antes de eu aplicar em lote:

> *"Em 19 deles o **escopo** está corretamente ancorado no endereço citado e é só
> a **natureza** que mora no vizinho. Trocar o endereço conserta a prova do
> rótulo e **quebra a prova do escopo**."*

Trocar teria sido um defeito por outro. Fica aberto o caso de a carta poder
citar **dois** trechos — hoje o formato só aceita um.

**A regra virou §10.3.1-C da SPEC**, com a redação literal que os três auditores
convergiram. O próximo lote nasce com ela.

**O que os auditores acharam de mais grave**, e que a auditoria de ancoragem
nunca pegaria:
- uma carta afirmava que *"a RC Condomínio exclui expressamente a
  responsabilidade do síndico"* — **fato de contrato que não está em trecho
  nenhum**. Vira argumento de venda errado.
- outra dizia que a Assistência Funeral do Porto Vida *"é cobertura básica"*,
  quando o contrato diz *"de acordo com o Plano contratado"*. É o erro na
  direção mais cara: promete um funeral que talvez não tenha sido contratado.
- duas do Allianz Corporate tinham o rótulo **provavelmente errado**, não só sem
  prova: são complementares (obrigatórias) e foram chamadas de adicionais. O
  auditor retirou o classificador em vez de trocá-lo, e 💭 marcou como inferência
  — vale conferência humana.
- **O que custa esquecer:** a carta responde com um número certo e uma condição
  errada. O corretor repassa, o cliente contratou o outro plano, e a conferência
  do endereço **confirma** a carta em vez de desmenti-la.

---

## P-144 · 🟡 O vizinho gêmeo — por que a reancoragem NÃO pode ser automática

📊 Achado por um auditor em 08/08/2026, antes de virar defeito.

A auditoria da §6.5 sinaliza quando um pedaço vizinho ancora melhor que o
citado. É tentador aplicar o movimento automaticamente. **Não faça.**

> No condomínio, a carta das exclusões da cobertura Básica **Ampla** (33.1.2.2)
> teve como vizinho melhor a lista da Básica **Simples** (33.1.1.1) — os textos
> são quase idênticos, e a diferença é **exatamente a alínea que some** (danos
> elétricos). Um movimento automático teria trocado a cobertura da carta por
> outra, mais barata e com escopo diferente: **erro muito mais grave que o
> original**.

A regra que sai daí: **semelhança alta entre citado e vizinho é motivo para NÃO
mover, não para mover.** Quando dois trechos são gêmeos, o diferencial mede
ruído, não evidência — e só a leitura separa.

- **Destrava:** nada. É uma trava a acrescentar ao script se algum dia alguém
  quiser automatizar, e está registrada aqui para que a ideia não volte limpa.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** trocar a apólice sobre a qual a carta fala, sem que
  nada no sistema acuse.

---

## P-145 · 🟢 O teste da faceta foi MEDIDO e recusado — não tente de novo sem dados novos

📊 08/08/2026. Um auditor sugeriu um sinal barato: *"o trecho citado contém
material da faceta que a carta declara?"* — `prazo` deveria trazer número e
unidade de tempo, `exclusao` deveria trazer verbo excludente. Ele viu dois casos
em que isso apontava o erro sozinho.

Implementei e medi contra os 19 erros que quatro auditores confirmaram:

```
              erros pegos     falso alarme
exclusao         2 de 14          1 de 27
limite           0 de  0         17 de 19
prazo            1 de  2          0 de  3
documento        0 de  0          1 de  2
TOTAL            3 de 19         19 de 64
```

**Não adotado.** `limite` é ruído quase puro — a marca textual que escrevi não
corresponde a como o contrato escreve limite. `exclusao` tem boa precisão e
pega 14% dos erros. No acervo inteiro o teste acusaria 87 cartas de 1.121, e a
maioria sem motivo.

Um sinal que grita mais do que acerta ensina o próximo a ignorar sinal.

- **Destrava:** um lote novo, com erros confirmados por auditoria, para calibrar
  as marcas por faceta com mais de 19 exemplos.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** alguém relê o relatório do auditor, acha a ideia
  boa — ela **é** boa em tese — e implementa de novo sem medir. Por isso o
  número fica aqui.

---

## P-146 · 🟡 O breadcrumb que perde o pai — investigado, MEDIDO e não aplicado

📊 09/08/2026. Um auditor do P-143 achou uma causa estrutural para o "adjetivo
enxertado" e propôs o conserto de maior alavancagem do lote:

> *"O enxerto não está distribuído por ramo nem por cobertura: está distribuído
> por **trecho de documento onde o breadcrumb do chunker quebrou**. Enquanto o
> caminho preserva `33.2. COBERTURAS ADICIONAIS > 33.2.x`, os casos são
> `provado`. A partir de `#0138` o caminho reinicia — e todo caso dali em diante
> virou reescrita. **Consertar o breadcrumb converteria ~20 das 23 reescritas em
> `provado`, sem tocar no destilador.**"*

**A causa é real e eu a reproduzi.** `_RE_NUMERADO` exige que a linha comece com
dígito, e o documento usa `►` de forma inconsistente:

```
#0135  ►33.1.3 … > 33.2. COBERTURAS ADICIONAIS > 33.2.6 PERDA DE ALUGUEL
#0138  ►33.2.7 ALAGAMENTO                        ← o pai sumiu
```

`►33.2.7` não casa o padrão numerado, cai na regra de RAIZ e **reinicia a
pilha**. As outras regras de título já toleram o marcador (`^[►▶\s]*`); esta
não. O nível deveria vir da numeração, não do símbolo.

### 📊 Por que NÃO foi aplicado

Escrevi o conserto e medi o impacto em 6 documentos reais:

```
documento              hoje   com o conserto   veredito
allianz condominio      319        319         IDÊNTICO
allianz auto            391        391         IDÊNTICO
allianz empresarial     341        341         IDÊNTICO
porto vida              155        155         IDÊNTICO
porto auto              484        487         MUDOU (+3)
porto condominio        277        276         MUDOU (−1)
```

E medi o ganho onde o corte NÃO muda — que seria ganho de graça:

```
allianz condominio: 319 de 319 pedaços com o mesmo corpo
                    0 caminhos melhorados
```

**Zero.** O conserto não alterou uma única trilha no documento onde eu conseguia
comparar sem quebrar nada. Em compensação, mudaria o corte de 2 documentos —
deslocando os `unit_id` de **530 cartas já publicadas e auditadas**.

O ganho de ~20 cartas era 💭 inferência do auditor, tirada de um lote de 43. O
custo é 📊 medido e certo. **Reverti.**

- **Destrava:** um lote em que os documentos afetados sejam re-cortados de
  qualquer jeito — ou seja, quando a Porto publicar versão nova de auto ou
  condomínio. Aí o conserto entra sem custo, junto com a re-destilação que a
  versão nova exige.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** nada hoje. O conserto está escrito neste registro e
  a causa está diagnosticada; quem retomar não precisa redescobrir.
- ⚠️ **O que NÃO fazer:** aplicar "porque é obviamente melhor". Foi o que eu ia
  fazer, e a medição do caminho — 0 de 319 — mostrou que o obviamente melhor não
  se sustentava naquele documento. Meça o caminho antes, não só o corte.

---

## P-147 · 🟡 Contaminação de seção NA FONTE — nenhum guarda automático pega

📊 09/08/2026, achado por um auditor de ancoragem no Allianz Empresa PME.

O PDF emendou duas seções. Sob o título `14.2. Riscos Excluídos` da cobertura de
**Quebra de Vidros** aparecem, no fim da lista alfabética, três alíneas que são
de **Equipamentos Eletrônicos**:

```
p) Sobrecarga… capacidade normal de operação dos equipamentos segurados
q) Negligência do segurado na utilização dos equipamentos
r) Queda, quebra, amassamento ou arranhadura
```

Uma carta usou a alínea `p` e afirmou que a cobertura de **vidros** exclui
sobrecarga *"dos equipamentos segurados"*. 📊 Corrigida — a oração saiu.

### Por que isto é uma família nova de defeito

**O endereço está CERTO.** A carta cita o pedaço que realmente contém aquele
texto. Então:

- `conferir_ancoragem.py` não acusa — não é órfã, não é cópia, o vizinho não
  ancora melhor;
- a auditoria de ancoragem devolve `ok`, e devolve com razão;
- a auditoria de fidelidade (P-143) não acusa — a afirmação **tem** lastro no
  trecho;
- só um leitor que conheça o produto percebe que "equipamentos segurados" não
  faz sentido numa cobertura de vidro.

Foi exatamente o que aconteceu: o auditor marcou os 4 casos como `ok` — o
veredito correto — e **relatou este defeito por fora**, na seção de observações.

O mesmo auditor listou outros dois pedaços do mesmo documento com cabeçalho
mentiroso: `#0238` tem título *"Riscos e Bens Cobertos Específicos"* e corpo
inteiramente de exclusões; `#0211`/`#0212` estão sob *"Reembolso de honorários
de perito Contábil"* e carregam a seção `18.3. Definições`.

- **Destrava:** nada de fora. É uma terceira auditoria, com a pergunta:
  *"o texto deste trecho pertence à cobertura que o título diz?"*
- **Dono:** 🤖 execução.
- **Escopo sugerido:** os pedaços onde o vocabulário do corpo destoa do título —
  falar de `equipamentos` sob um título de `vidros`, de `veículo` sob um título
  de `vida`. 📊 Dois destiladores já acharam isso sozinhos e não destilaram:
  o do vida em grupo achou *"vistoria prévia no veículo"* num clausulado de
  vida; o de equipamentos achou carência de *câncer e cesta básica* num produto
  de morte acidental.
- **O que custa esquecer:** a carta afirma uma exclusão que não é daquela
  cobertura, com o endereço certo apontando para o texto certo. É o formato mais
  difícil de desmentir — quem for conferir **acha exatamente o que a carta diz**.
- 💭 **Hipótese barata a testar:** os destiladores acharam esses casos sozinhos
  quando o contraste era grande (veículo × vida). O caso do PME é sutil
  (equipamentos × vidros, ambos patrimoniais) e escapou. Talvez baste pedir no
  prompt: *"antes de escrever, pergunte se este texto pertence mesmo à cobertura
  do título"*.


---

# 🟠 COBRANÇA MULTI-SEGURADORA — o que ficou aberto (10/08/2026)

## P-98 · 🔴 O `--headless=new` precisa ir para o worker em produção

📊 Medido em 10/08/2026 contra `www.hdi.com.br/hdidigital/`, um fator por vez,
com linha de CONTROLE repetida no início e no fim da bateria:

```
headless clássico ...............  BLOQUEADO   Access Denied (Akamai)
+ args anti-automação ...........  BLOQUEADO
+ script de stealth .............  BLOQUEADO
+ args E stealth ................  BLOQUEADO
navegador COM janela ............  PASSOU
--headless=new ..................  PASSOU      ← e roda sem tela
```

**Cinco variações deram o mesmo bloqueio → nenhuma delas era a causa.** O fator
é o MODO headless: o clássico é um binário separado, com fingerprint próprio, e
o Akamai o reconhece.

📊 **Linha de controle da mudança:** a Allianz, com o modo novo, baixou **4 de 4
boletos** (`via=api_chain`, 103193/117062/117223/117589 bytes). Não houve
regressão — e é isso que dá direito de creditar o ganho ao modo novo.

- **Destrava:** o código já está em `worker._launch_kwargs()`. Falta o deploy.
- **Dono:** 🧑 Founder decide o merge · 🤖 já entregou.
- **Custa se esquecer:** a HDI (e provavelmente Yelum, Porto e toda seguradora
  atrás de Akamai) **nunca** funciona no worker atual. Não é bug da journey.

## P-99 · 🟠 O Akamai da HDI também reage à FREQUÊNCIA

📊 Depois de ~14 acessos em 30 minutos, o `--headless=new` que passava começou a
receber `Access Denied` — e continuou bloqueado 12 minutos depois. **É bloqueio
por IP, temporário, disparado por volume.**

> Isso **valida** a arquitetura de duas fases: a fase COLHER entra no portal
> **uma vez por execução** e sai. Fosse um-a-um ponta a ponta, o robô entraria
> 20 vezes por rodada e seria bloqueado no meio.

- **Destrava:** nada. É desenho, não conserto.
- **Regra dura:** reusar `portal_sessions` sempre que possível, e nunca fazer
  login por item.
- **Custa se esquecer:** alguém "otimiza" o Cobrador entrando por cliente, e a
  corretora perde o acesso ao portal dela.

## P-100 · 🔴 Falta a estrutura HTML da tela de resultado da HDI

A cadeia da HDI está provada até o passo 3:

```
login ...................... ✅ provado (camada visível + camada real)
passo 1 (ponte legado) ..... ✅ HTTP 200, identidade colhida (m_cod_corretor, c_pc, l_s, n_s)
passo 2 (tela de busca) .... ✅ HTTP 200
passo 3 (a lista) .......... ⚠️  HTTP 200, mas o parser leu 0 linhas
passo 4 (o boleto) ......... ⏳ não exercitado
```

📊 O passo 3 respondeu com corpo, então **ou** o `s_tipo` pedido não traz nada,
**ou** o HTML não casa com `extrair_parcelas`. Não dá para saber sem ver o HTML,
e o Akamai cortou a sessão antes.

- **Destrava:** 🤖 uma rodada de `ver_html_parcelas.py` com o IP liberado, ou
  🧑 o founder colando o **Response** da chamada `dsp_parcelas_view_2008.htm`
  (aba Response do F12, não Headers).
- **Custa se esquecer:** é o único passo que separa a HDI de funcionar.

## P-101 · 🟠 Débito automático em atraso não tem boleto para enviar

📊 Na captura de 10/08, a **única** parcela em atraso era débito automático, e a
coluna `Gerar` dizia *"Parcela diferente de Boleto Bancário."* em vez de
*"2ª via"*. Converter para boleto está atrás de **ALTERAÇÕES FINANCEIRAS**, que
escreve no contrato do segurado — proibido.

O código já marca esses casos (`sem_boleto_motivo`) e eles entram no relatório.
**Falta a decisão de produto:** o que a corretora quer que aconteça?

```
a) só avisar o segurado que o débito não passou, sem boleto
b) abrir tarefa para a atendente humana converter no portal
c) não cobrar, só relatar
```

- **Dono:** 🧑 Founder — é decisão comercial, não técnica.

## P-102 · 🟠 Resulta e AutoFleet continuam sem destino de handoff

📊 `human_support_destinations` tem 2 linhas, **ambas da AMANDUS SEGUROS**.

O cano está construído e funciona vazio: sem destino, o problema vai para o
relatório e a rotina abre com o aviso. No dia que o grupo existir, é preencher
um campo — nada precisa ser refeito.

- **Destrava:** 🧑 criar o grupo de suporte de cada corretora.

## P-103 · 🟡 A Yelum devolve 403 a cliente automatizado

📊 `novomeuespacocorretor.yelumseguros.com.br` respondeu **403** tanto na raiz
quanto em `/home`, a um cliente HTTP simples. Provavelmente o mesmo tipo de WAF
da HDI — e provavelmente a mesma solução (`--headless=new`).

- **Custa se esquecer:** quem for fazer a Yelum vai achar que a credencial está
  errada. Não está: 📊 ela foi gravada em 10/08 e o portal recusa antes do login.



---

## ✅ P-100 RESOLVIDO em 12/08/2026 — a HDI baixa boleto

📊 Prova real, uma visita ao portal:

```
status ............ done
mensagem .......... HDI: 1 inadimplente(s), 1 boleto(s)
boleto ............ ok=True · 27.037 bytes · via=dsp_boleto · valida como %PDF
```

**Os quatro defeitos que impediam, e o que cada um ensinou:**

| # | O defeito | A lição |
|---|---|---|
| 1 | **A busca é assíncrona.** O 1º POST devolve *"aguarde, processando"* + um form que se reenvia em 5 s. Era essa sala de espera que eu lia como "tabela vazia" | HTTP 200 com corpo de 4 KB **não** é resultado. Só o reenvio traz a tabela |
| 2 | **`s_tipo=1` é "A vencer"**, não "Atrasadas" — eu pedia justamente quem não interessa | 📊 O `<select>` do portal responde em 3 segundos o que eu tentei adivinhar em 5 rodadas |
| 3 | **O boleto não é `<a href>`** — mora dentro de `onclick="window.open('dsp_boleto.htm?p=…')"` | Procurar `href` não acha nada, mesmo com a tabela lida certa |
| 4 | **Janela máxima de 30 dias** (validação do próprio botão Buscar). Meu padrão era 365 | Varredura em blocos, sem buraco entre eles |

**E duas descobertas de estrutura que valem para o parser de qualquer portal legado:**

- **Uma `<table>` por documento**, não uma tabela com N linhas. E a primeira nem
  fecha o `<tbody>` — parser que exige HTML bem formado quebra aqui.
- **Crédito também não gera boleto**, não só Débito. A marca certa é a frase
  *"Parcela diferente de Boleto Bancário"*, não a forma de pagamento.

📊 Tudo isto está preso por **102 asserções** rodando contra uma fixture com a
estrutura real do HTML e os dados trocados (`backend/tests/fixtures/hdi_parcelas.py`)
— zero acesso ao portal para testar.

- **O que falta para a HDI ser 100%:** rodar pelo worker (fila `portal_jobs`) com
  o storage ligado. Isso depende do deploy (P-98), não de mais código.

## P-104 · 🟡 A regra de ouro contra bloqueio, aprendida a duras penas

📊 Dois portais independentes (HDI e Tokio) passaram a recusar acesso depois de
~15 e ~4 visitas em menos de 30 minutos. **Eles reagem à frequência, não ao
método.**

```
FASE 0 (reconhecimento) .... no máximo 2 visitas
FASE 2 (replicar) .......... 1 visita
FASE 3 (journey) ........... teste roda de FIXTURE, zero visita
FASE 4 (ligar) ............. 1 rodada, com a Allianz junto como controle
```

> **O portal da corretora não é ambiente de teste.** Toda leitura repetida sai de
> fixture salva. Foi assim que a HDI fechou: 4 defeitos corrigidos offline, uma
> única visita para provar.



---

## ✅ P-98 e P-105 RESOLVIDOS em 12/08/2026 — a HDI fecha, e não precisou de proxy

📊 **Prova pela fila real do worker de produção:**

```
HDI ....... done · 1 inadimplente · boleto de 27.037 bytes no bucket
Allianz ... done · 4 inadimplentes · 4 boletos (LINHA DE CONTROLE)
saida_de_rede ... "direta (IP do servidor)"   ← sem proxy nenhum
```

### O Akamai eram DOIS fatores, e nenhum era o IP

| Fator | Sintoma | Correção |
|---|---|---|
| Impressão digital em **JavaScript** | headless clássico é outro binário | `--headless=new` |
| **`HeadlessChrome` no cabeçalho** | filtro derruba antes de rodar JS | `user_agent_sem_headless()` |

### A lição que quase custou uma assinatura de proxy

O primeiro diagnóstico comparou o navegador com "um cliente HTTP simples"
(`page.request`) e concluiu, com confiança, que **o fator era o IP**.

> **O teste estava furado.** `page.request` **herda o User-Agent do contexto** —
> os dois clientes mandaram o mesmo cabeçalho. Ele não isolou o que dizia
> isolar, e produziu uma conclusão confiante e errada.

O que decidiu foi variar **um fator por vez do mesmo IP**, com controle nas duas
pontas: UA limpo passa, UA padrão é bloqueado, UA limpo passa.

**Corolário para o método (SPEC-070):** um teste que não consegue separar o que
promete separar é pior que teste nenhum — ele *fecha* a investigação no lugar
errado. Antes de concluir, perguntar: *"este teste conseguiria dar o outro
resultado?"*

### O que ficou pronto e desligado

`proxy_do_portal()` — saída de rede por portal (`PORTAL_PROXY_<PORTAL>` ou
`PORTAL_PROXY_DEFAULT`). **Não é necessária hoje**, e está sem nenhuma variável
configurada. Fica para o dia em que um portal recusar o IP de verdade — e aí é
ligar uma variável, sem deploy de código.

- **Custa se esquecer:** 📊 o IP do servidor é `AS47583 Hostinger`, faixa de
  hospedagem. Um portal mais agressivo (Porto, Azul) pode barrar por ele — e a
  saída já está construída.


---

## TOKIO MARINE — fechada em 12/08/2026, e o que ela deixou

📊 Job `bc1dfaa0` pela fila de produção: `done`, 3 boletos no bucket, saída
direta (sem proxy). Detalhe em [`portais/PORTAL-tokio.md`](portais/PORTAL-tokio.md).

| # | O que ficou | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-106 | Onde exatamente fica o limite da 2ª via da Tokio — medido em 26 dias (sem) e 7 dias (com); 💭 a hipótese é o `NÃO RECEBER APÓS 15 DIAS` do próprio boleto | 🤖 | nada: o caso já vira tarefa humana com o motivo escrito. Saber o número só deixaria o aviso mais preciso |
| P-107 | Se inadimplente de **cartão de crédito** aparece em `Clientes inadimplentes` ou **só** em `Débitos Pendentes` / `Cobranças no Cartão` | 🤖 1 visita | 🔴 se for "só", um grupo inteiro de inadimplentes fica invisível — a falha que a SPEC-070 §2 proíbe |
| P-108 | Uma corretora com **2+ códigos de corretor** na Tokio (a AutoFleet tem 1) | 🧑 Founder indicar | 🔴 metade da carteira invisível, em silêncio |
| P-109 | O caso **CNPJ** na URL do detalhe (só CPF foi exercitado de ponta a ponta) | 🤖 sai sozinho | a apólice PJ não baixaria boleto — mas apareceria como retido, não como silêncio |
| P-110 | O que é o ramo **`312`** vs `0531` na mesma apólice | 🧑 atendentes | nada hoje: nenhum dos dois decide coisa alguma |

### O defeito que a Tokio revelou — e que era das TRÊS seguradoras

📊 Dos 4 downloads da primeira rodada, 3 viraram PDF e 1 não. Esse item
**continuava entrando na fila de envio**: a única porta era
`sem_boleto_por_regra`, que pega quem a *seguradora* recusa, não quem *falhou
ao baixar*. O segurado receberia "Segue o boleto abaixo" com anexo nenhum.

Corrigido em `fila_de_cobranca(boletos=…)`, e vale para Allianz, HDI e Tokio.

> **A lição:** o comentário da própria função já avisava desse desfecho. Um
> caminho estava coberto e o outro não — e só a rodada real com uma falha
> parcial mostrou a diferença. Teste com tudo dando certo não encontra isto.

## PRÓXIMA SEGURADORA — a porta das três candidatas, medida

📊 12/08/2026, carga pública das telas de login (sem tentar entrar):

| Portal | Peso | Travas detectadas | Veredito |
|---|---:|---|---|
| **Yelum** | 12 KB | **nenhuma** | ✅ **a próxima** |
| Bradesco | 1,79 MB | 🔴 captcha **+ Akamai** | deixar por último |
| Porto | 90 KB · 7 iframes | 🔴 captcha **+ Incapsula (Imperva)** | precisa de estratégia própria |

📊 Yelum: login em `/account/login`, site em **Drupal**, com um
`themes/custom/liberty_cohesion/js/portal_api.js` — indício de camada de API.
Credencial já existe para as duas corretoras; ❓ a senha precisa ser confirmada.

- **Custa se esquecer:** MAPFRE está travada esperando a Saionara (🧑). Yelum
  não depende de ninguém de fora — é a única que dá para começar hoje.

---

## YELUM — fases 1 a 4 fechadas em 12/08/2026

📊 A journey rodou contra o portal real (corretora Resulta) e trouxe um boleto
de **5.908 bytes — exatamente o tamanho do PDF que o Founder baixou à mão** no
mesmo cliente. Detalhe em [`portais/PORTAL-yelum.md`](portais/PORTAL-yelum.md).

| # | O que ficou | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-111 | **Fase 5** da Yelum — rodar pela fila de produção | 🧑 redeploy do `portal-worker` | a Yelum só varre quando o serviço tiver a imagem nova |
| P-112 | A credencial da **AutoFleet** na Yelum (a da Resulta entra; a outra dá erro mesmo parecendo certa) | 🧑 Founder / Saionara | metade das corretoras fica sem Yelum |
| P-113 | O **teto de visitas** da Yelum — não medido (Tokio ~4, HDI ~15) | 🤖 | tratamos como o mais restritivo até saber |
| P-114 | Se a API aceita janela **> 90 dias** (a tela limita) | 🤖 1 chamada | dívida antiga fica fora — mas a testemunha PEGA isso e para a varredura |
| P-115 | Se a credencial **atravessa para a HDI** (mesmo grupo, mesma API) | 🤖 1 visita | seria uma porta a menos para manter |

### 🔴 O erro que eu cometi, e o guarda que ele gera

Eu afirmei ao Founder que **a Yelum não tinha trava nenhuma** — e recomendei
começar por ela justamente por isso. Estava errado: o app logado roda **Akamai
Bot Manager** (`sensor_data` → `{"success": true}`, script de 560 KB com `bmak`,
mPulse).

O que eu medi foi a **página pública de marketing**; o que eu afirmei foi sobre
o **app logado**. São coisas diferentes, e a pública não é protegida.

> **É a terceira vez neste projeto que o mesmo erro aparece:** medir uma coisa
> **vizinha** da que se afirma. Antes foi o `page.request` que herdava o
> User-Agent e "provava" que o fator era o IP; depois foi o guarda de chegada da
> Tokio, que procurava um link que a **porta** também tinha.
>
> A pergunta que teria pego as três:
> **"a coisa que eu medi é a mesma sobre a qual eu vou afirmar?"**

A escolha continua certa (a Yelum saiu numa tarde), mas pelo motivo certo:
**a API é limpa** — não porque não tivesse trava.

---

## REGRESSÃO DAS QUATRO SEGURADORAS — 12/08/2026

📊 Sete jobs pela **fila de produção**, nas duas corretoras, todos `done`:

| Corretora | Seguradora | Inadimplentes | Boletos | Retidos |
|---|---|---:|---:|---:|
| Resulta | Allianz | 5 | **5** | 0 |
| AutoFleet | Allianz | 5 | **5** | 0 |
| Resulta | HDI | 1 | **1** | 0 |
| AutoFleet | HDI | 3 | **3** | 0 |
| Resulta | Tokio | 2 | **2** | 0 |
| AutoFleet | Tokio | 5 | **3** | 2 |
| Resulta | Yelum | 1 | **1** | 0 |
| | **total** | **22** | **20** | **2** |

📊 E a conferência que fecha: **20 de 20 arquivos existem no bucket
`portal-evidence`** e **20 de 20 começam com `%PDF`** — medido baixando os 8
primeiros bytes de cada um, não confiando no que o código disse que fez.

Os 2 retidos são os dois casos de regra, e cada um chegou com o motivo escrito:
o DÉBITO com `repique = S` e a parcela vencida há 26 dias para a qual a Tokio
não emite mais 2ª via.

### 🔴 O que AINDA falta para o ciclo completo

A **colheita** está pronta de ponta a ponta. O **envio** não foi exercitado, e
depende de duas coisas que não são código:

| # | O que falta | De quem | Custa se esquecer |
|---|---|:--:|---|
| P-116 | `human_support_destinations` só tem **AMANDUS**. Resulta e AutoFleet não têm grupo humano cadastrado | 🧑 Founder | os itens retidos (débito, sem 2ª via, sem telefone) **não têm para onde ir** — o aviso é montado e descartado |
| P-117 | **Nenhuma rotina de cobrança cadastrada** para Resulta nem AutoFleet | 🧑 Founder | nada roda sozinho; hoje as varreduras são enfileiradas à mão |
| P-118 | O **envio real de WhatsApp** nunca foi testado ponta a ponta | 🧑 Founder avisar antes | é a única peça do caminho que ainda não tem uma medição própria |

> **Sejamos exatos:** as quatro seguradoras entregam boleto no bucket, com o
> documento do segurado. O que ainda não aconteceu **nem uma vez** é o sistema
> mandar a mensagem para um cliente de verdade — e o Founder pediu para ser
> avisado antes que isso aconteça.

---

## MAPFRE — fase 1, e o risco cross-tenant que deixou de ser hipótese

📊 12/08/2026. Credenciais das duas corretoras gravadas, URL corrigida para
`negocios.mapfre.com.br/acesso`, porta pública medida.

### 🔴 P-119 — o mesmo login enxerga DUAS corretoras

📊 Depois do login, o modal `Selecione o código interno` lista
**RESULTA** e **AUTO FLEET** na mesma caixa, para o mesmo usuário.

> Se a varredura da Resulta selecionar a AutoFleet, os inadimplentes de uma
> entram no `company_id` da outra. É **dado atravessando tenant** — CLAUDE.md §7.

**Resolvido por desenho, não por sorte:** `portal_accounts.account_label` guarda
o nome exato da corretora que aquele login deve selecionar; a journey seleciona
pelo rótulo, **relê a tela para conferir**, e **para** (`needs_human`) se não
conferir. Nunca varre "o que estiver selecionado".

Isto materializa a **P-108**, anotada como hipótese desde a Tokio. Lá era "uma
corretora pode ter mais de um código"; aqui são **duas empresas** atrás do mesmo
usuário — pior, e real.

- **Custa se esquecer:** um incidente de vazamento entre clientes, que é o único
  tipo de defeito deste sistema que não dá para consertar depois.

### P-120 — a carteira MAPFRE está sem inadimplente nas duas corretoras

📊 Status `Vencida`, período padrão: `Não encontrado` nas duas. O card
`Parcelas Inadimplentes` marca `0`.

**Não bloqueia.** Zero inadimplente é um estado, não uma propriedade do portal.
📊 Na Tokio e na Yelum o boleto de parcela **A vencer** sai pelo mesmo caminho da
vencida — então dá para provar a cadeia inteira com `Status = Todos`, e o que
fica ❓ é só a coluna de juros/multa da linha vencida.

- **Custa se esquecer:** nada hoje; no dia em que aparecer o primeiro
  inadimplente, o último palmo se valida sozinho.

### P-121 — o período padrão da MAPFRE é de QUINZE DIAS

📊 `28/07/2026-12/08/2026`. É a janela mais curta das cinco seguradoras
(HDI 30 por bloco, Yelum ~90). ❓ O alcance máximo não foi medido.

- **Custa se esquecer:** dívida de dois meses não aparece — e sem uma testemunha
  independente ninguém saberia. Medir o alcance é pré-requisito do gate.

---

## P-122 · 🔴 `ESPELHO_SYNC_ENABLED` precisa ser ligado depois do canario

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (uma variavel no EasyPanel)

O recovery periodico do Espelho **nasce desligado** (commit `d9d17bb`). Foi
decisao de desenho: o primeiro boot depois do Upgrade para Pro e o instante mais
perigoso do plano — dezenas de componentes em 402 voltam ao mesmo tempo — e um
sync que sobe trabalhando nesse minuto e exatamente o que nao pode acontecer.

**Enquanto estiver OFF:** a ponte AO VIVO funciona inteira. Mensagem nova
aparece no chat normalmente. O que nao roda e a **rede de seguranca** — a
recuperacao do que a ponte perdeu durante um deploy ou uma reconexao.

**O que destrava:** `ESPELHO_SYNC_ENABLED=true` no servico `autobrokers-smith-api`,
depois do canario one-shot medido nas tres corretoras.

**O que custa esquecer:** mensagem perdida por um deploy nao seria recuperada
automaticamente. Ela continua intacta em `attendance_transcripts` e volta com um
one-shot — mas ninguem seria avisado de que faltou.

---

## P-123 · ~~A recuperacao da janela da pane~~ — **FECHADA em 13/08/2026 20:05 UTC: nao ha o que recuperar**

**Aberta e fechada no mesmo dia.** Foi aberta por deducao; a medicao a desmontou.

📊 Medido depois do deploy, antes do Upgrade:

```
transcripts elegiveis na janela de 7 dias ...... 3.426
destes, FALTANDO no chat ....................... 0
conversas afetadas ............................. 0
```

O Espelho ja tinha alcancado tudo antes da restricao. **Nao ha backfill a fazer.**

E a razao pela qual nao existe "janela da pane" no acervo e mais simples do que
eu supus: 📊 o ultimo transcript capturado e de **12/08 21:12 UTC — 22h50 antes**
desta medicao. A captura escreve via PostgREST, e PostgREST estava em 402: o
Observador nao capturou NADA durante a restricao. Nao ha material esperando no
acervo porque ele nunca chegou la.

**O que isso muda no plano:** o passo "one-shot de recuperacao por corretora"
sai da sequencia pos-Upgrade. Ele existiria para copiar acervo -> chat, e nao ha
diferenca entre os dois.

**O que assume o lugar dele:** quando o Supabase voltar e o Observador
reconectar, o WhatsApp deve reentregar por HISTORY_SYNC as ~23h que nao foram
capturadas. Elas entram pela ponte AO VIVO (que nunca foi desligada), com
`created_at` de agora — depois do cursor. Custo por mensagem depois da Alavanca
A: 2 leituras pequenas + 1 insert. Mesmo um HISTORY_SYNC do tamanho do da
Amandus (13.200 mensagens) fica na casa de poucos MB, contra os 7 GB do desenho
antigo.

**O que observar:** o contador `agora` do `/health` na primeira hora. Se
`mensagem_nova` subir muito, e o HISTORY_SYNC entrando — esperado. Se `erro:*`
subir, ai sim ha algo a investigar.

<!-- texto original preservado abaixo, append-only -->

### Registro original (13/08, antes da medicao)


**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, depois do Upgrade

O cursor foi semeado em `now()` (13/08 ~18:30 UTC) de proposito: partir do
comeco varreria as 105.275 linhas do acervo — 26x o ciclo que causou o
incidente, no minuto seguinte ao Founder pagar pelo Pro.

Consequencia: as mensagens que chegaram **durante a restricao 402** nao entram
pelo cursor. Elas estao inteiras em `attendance_transcripts`.

**O que destrava:** depois do gate 402, chamar o endpoint que ja existe, uma
corretora por vez, medindo entre uma e outra:

```
POST /api/whatsapp-channel/espelho/trazer-conversas?company_id=<id>&dias=3&limite=3000
Header: X-AutoBrokers-Internal-Key
```

📊 Volume esperado (medido em 13/08): a maior corretora tem 59.168 transcripts
no total, mas so **4.009 na janela de 7 dias**. `dias=3` cobre a pane com folga.

**O que custa esquecer:** as conversas dos dias da pane nao apareceriam na mesa
de trabalho — visiveis no acervo e no `/admin/espelho`, invisiveis para a
atendente.

---

## P-124 · 🟠 SEC-05 guarda uma tela que mudou de casa — e por isso nao guarda nada

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, bloco proprio

📊 `broker_outcome_regression_pack.py` (caso SEC-05) procura a tela de conversas
em `app/dashboard/conversas/page.tsx` e `app/admin/conversations/page.tsx`. A
primeira **nao existe** e a segunda e um redirecionamento (pulado de proposito).
Resultado: `tela de conversas nao encontrada em nenhum dos caminhos` — **gate
vermelho**, e o guarda de seguranca sem alvo.

A tela real e `app/dashboard/atendimentos/conversas/page.tsx` (SPEC-043/064).

**Nao ha exposicao:** conferido em 13/08 — a tela real nao tem `supabase.storage`
nem `createClient`, e nao renderiza midia. O que falta e o guarda saber onde ela
mora. Ele tambem exige `resolveMediaUrl`, que aquela tela nao usa porque nao
mostra midia — logo o caso precisa ser **reescrito**, nao so reapontado.

**Falha pre-existente:** o P0 do Egress nao tocou um unico arquivo em `app/`
(`git status --short -- app/` = vazio nos dois commits).

**O que custa esquecer:** o gate fica vermelho por um motivo que nao e o que ele
anuncia, e a proxima regressao de verdade se esconde atras deste vermelho
cronico — que e como um gate morre.

---

## P-125 · 🔴 O código do P0 está na `main` e NÃO está no ar — falta clicar Implantar

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (ação física no EasyPanel)

📊 `git push origin HEAD:main` às 16:18 UTC, quatro commits (`51b5c0f`,
`d9d17bb`, `05fb3ae`, `3f9e0d5`). **Vinte e um minutos depois**, o contêiner
ainda servia o código antigo.

**Prova:** o commit `3f9e0d5` acrescenta a chave `espelho_sync_ligado` ao
`/health`. Ela **não aparece** na resposta de produção. `git_commit` vem
`nao-injetado`, então o número do commit não serve para conferir — a chave nova
serve.

**Conclusão: não há auto-deploy.** Push na `main` é condição necessária e não
suficiente. É preciso clicar **Implantar** em `autobrokers-smith-api` (e no
`-worker`, que compartilha o mesmo código).

### 🔴 Por que a ORDEM importa mais do que parece

Se o Upgrade para Pro acontecer **antes** do Implantar, o código antigo volta a
funcionar com cota nova — e o sync retoma saturado, relendo 4.008 linhas por
ciclo com o laço a ~50 min por volta. **O incidente recomeça no minuto em que a
cota é restaurada**, e desta vez custando dinheiro.

```
1. Implantar  (api + worker)
2. conferir   /health → codigo.espelho_sync_ligado == false
3. só então   Upgrade to Pro
```

**O que custa esquecer:** repetir o incidente de 05–13/08 com plano pago.

---

## P-126 · 🔴 A Resulta nao observa WhatsApp ha 15 dias — e nao foi a pane

**Aberta em:** 13/08/2026 · **Dono:** 🧑 Founder (parear de novo — QR/passkey)

📊 Medido logo apos o Upgrade, com o Supabase ja respondendo 200:

| corretora | `channel_status` | ultima captura | total no acervo |
|---|---|---|---|
| AutoFleet | `connected` | **13/08 20:40** (agora) | 46.016 |
| AMANDUS SEGUROS | `connected` | **13/08 20:33** (agora) | 102 |
| **Resulta Seguros** | **`disconnected`** | **29/07 18:27** | 59.168 |

**Nao foi causado pelo incidente de Egress.** A Resulta parou em **29/07**; o
Egress comecou a subir em **07/08** e a restricao 402 chegou em **12/08**. Sao
nove dias de diferenca — a Resulta ja estava muda antes.

📊 `capturou_7d = 0` para a Resulta, contra 3.887 da AutoFleet no mesmo periodo.

O heartbeat do canal (SPEC-063 Bloco V) esta funcionando: `last_seen_at` de tres
minutos atras com `channel_status = disconnected` e exatamente o vigia
**desmentindo** a tela, que e para o que ele existe.

**O que destrava:** repareamento do WhatsApp da Resulta (QR ou passkey). E acao
fisica — ninguem pareia um WhatsApp por API.

**O que custa esquecer:** a Resulta e uma das corretoras do canario e uma das
duas contas da MAPFRE. Ha quinze dias nao ha conversa dela entrando na mesa de
trabalho, e o `/admin/espelho` dela esta parado em 29/07. Qualquer medicao de
atendimento que a inclua esta medindo silencio.

---

## P-127 · 🟠 Duas views com SECURITY DEFINER — o Advisor marca CRITICAL

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execucao, bloco proprio

📊 O Advisor do Supabase, depois do Upgrade, aponta 2 issues CRITICAL:

```
public.vw_destinos_de_suporte_em_conflito
public.vw_agentes_mudos
```

As duas sao views comuns (`relkind='v'`) de dono `postgres` e **sem**
`security_invoker=true`. Sem essa opcao, a view executa com os privilegios de
quem a CRIOU, nao de quem a CONSULTA — as policies de RLS do consumidor deixam
de valer.

**Nao e deste P0** e nao foi introduzida por ele: as duas views sao anteriores.
Nao tocadas nesta intervencao.

**O que destrava:** `ALTER VIEW ... SET (security_invoker = true)` — mas so
depois de conferir quem consulta cada uma e se alguma depende do comportamento
atual. Uma view de "agentes mudos" que passe a respeitar RLS pode devolver menos
linhas para o admin, e isso precisa ser verificado, nao presumido.

**O que custa esquecer:** e o unico CRITICAL aberto no Advisor. Cross-tenant por
view e o tipo de furo que nao aparece em teste de aplicacao (CLAUDE.md §7).

---

## P-128 · 🔴 A ANÁLISE QUE O FOUNDER PEDIU: os acionamentos com as seguradoras

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução · **Prioridade: alta, sessão própria**

Pedido do Founder, palavras dele: *"quero uma análise muito detalhada sobre o
que foi conversado com as seguradoras — acionamento na Allianz, na Porto, na
HDI... me diga se tivemos aumento dos mapas, se tivemos análise dos cliques, dos
cliques nos menus, nos apps dentro do WhatsApp da HDI, Yelum, Porto. Preciso
saber se a nossa inteligência entende tudo e se os nossos atendentes vão
conseguir fazer os acionamentos, se eles têm as informações corretas,
completas."*

### O que a análise tem de responder

1. **O que foi realmente conversado** com cada seguradora nos acionamentos
   reais — não o que o playbook diz, o que aconteceu.
2. **Os mapas cresceram?** `ura_maps` por seguradora, antes × depois. Quantas
   rotas novas, quantas mudaram, quantas morreram.
3. **Os cliques foram analisados?** Menus, botões e os *apps dentro do WhatsApp*
   (HDI, Yelum, Porto) — o formulário nativo resolvido em 03/08 é o precedente:
   ali a resposta veio de MEDIR, não de ler.
4. **A inteligência entende?** Uma coisa é ter o mapa; outra é o Atlas saber
   escolher a rota certa na hora.
5. **O atendente consegue fechar o acionamento sozinho?** Ele tem a informação
   correta e COMPLETA — placa, apólice, endereço, o que a seguradora pede em
   cada passo?

### Por que é a peça que falta

O atendimento ponta a ponta morre no acionamento. Tudo antes (captura, espelho,
chat, RAG) serve para chegar até aí. Se o atendente trava no menu da HDI, o
resto não importa.

**O que destrava:** sessão dedicada, com medição em `ura_maps`,
`attendance_transcripts` das conversas com seguradora (`insurer_key` não nulo),
`route_drift` e os `playbook_overlays`.

**O que custa esquecer:** ir a produção com o atendimento cego no último metro.

---

## P-129 · Medir o custo por sessão do destilador (teto 0 → 5, uma janela só)

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, quando o Founder pedir

📊 `attendance_sessions`: **11.347 fechadas, ZERO destiladas**, atrás de
`DESTILADOR_TETO_POR_RODADA=0`.

O objetivo **não** é destilar por API — a destilação de verdade será feita pelo
Claude Code no plano Max, com subagentes e Opus 5, sem custo marginal. O objetivo
é **saber o número**: subir o teto para `5`, deixar UMA janela da madrugada
rodar, medir o custo real por sessão, e voltar para `0`.

Serve para responder "quanto custaria se um dia quiséssemos" com medição, e não
com estimativa — e para dimensionar a SPEC-062 (billing) com dado real.

**O que custa esquecer:** decidir preço e plano em cima de número inventado.
