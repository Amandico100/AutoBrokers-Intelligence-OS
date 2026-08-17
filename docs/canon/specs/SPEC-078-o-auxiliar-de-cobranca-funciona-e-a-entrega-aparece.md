---
status: "PRONTA PARA EXECUÇÃO — solicitada pelo Founder em 17/08/2026"
spec: "SPEC-078"
titulo: "O Auxiliar de Cobrança funciona, a Rotina volta a ter dono, e a entrega aparece"
criada_em: "2026-08-17"
branch_sugerida: "feat/spec078-cobranca-funciona-e-entrega-aparece"
repo: "Amandico100/AutoBrokers-Intelligence-OS"
baseline_main_observada: "6e1d4d3bdf1f5c4f37952e8075e218e02285603d"
supabase_producao: "dcajcvlzcjbmyapmklil"
depende_de: "SPEC-064 (ontologia — 3 de 4 rotas absorvidas; esta SPEC executa a 4ª) · SPEC-063 D (proibição do observer) · SPEC-057 (Artifact) · SPEC-073/075 (portal-worker)"
deploy_esperado: "smith-web + smith-api. portal-worker só se o Bloco A tocar em algo dentro de backend/portal_worker."
migration_esperada: "3 — (1) backfill + NOT NULL/FK em routines.tenant_auxiliary_id, (2) auxiliar de plataforma tarefas-agendadas, (3) purpose auxiliary em integrations. Todas expand-first."
---

# SPEC-078 — O Auxiliar de Cobrança funciona, a Rotina volta a ter dono, e a entrega aparece

> **Resultado desta SPEC, em uma frase:** o Founder liga o Auxiliar de Cobrança em
> **qualquer** corretora, o robô entra no portal da seguradora escolhida, baixa o
> boleto do inadimplente e **a mensagem e o PDF chegam no WhatsApp de teste pelo
> número pareado da própria corretora** — e tudo o que o sistema produz passa a
> ficar clicável numa página de Entregas que funciona.
>
> **Regra de ouro:** esta SPEC não cria motor novo. Ela **liga interruptores que
> existem e não estão ligados na roda**, **dá dono a Rotinas que nascem órfãs**, e
> **abre uma porta de saída para trabalho que hoje é produzido e não pode ser
> visto**. Nenhum runtime, catálogo, scheduler ou publisher paralelo.

---

# 0. Por que esta SPEC existe agora

Em 17/08/2026 o Founder tentou usar o Auxiliar de Cobrança e encontrou uma tela
que dizia `install_failed`. O conserto imediato foi feito e está em produção
(commits `73db573` e `6e1d4d3`). Mas a investigação que veio junto — cinco
frentes de auditoria, todas read-only — mostrou que o `install_failed` era o
sintoma mais visível de **seis defeitos estruturais** que impedem o produto de
funcionar como o corretor acredita que funciona.

Nenhum deles é opinião. Todos foram medidos.

## 0.1 O achado que organiza todos os outros

📊 A SPEC-064 §B.3 mandou absorver **quatro** rotas. Três foram executadas e
viraram stubs de redirect com a mesma frase no cabeçalho —
*"O CONTEUDO FOI ABSORVIDO"*:

```text
app/dashboard/auxiliares/galeria/page.tsx      17 linhas   redirect
app/dashboard/auxiliares/meus/page.tsx         17 linhas   redirect
app/dashboard/auxiliares/execucoes/page.tsx    16 linhas   redirect
app/dashboard/auxiliares/rotinas/page.tsx     636 linhas   VIVA, com botão "Nova rotina"
```

**A quarta não foi.** E é dela que sai a confusão inteira que o Founder
descreveu: a lista solta de Rotinas, o botão que cria rotina sem dono, o modal
que mistura configuração do trabalhador com agenda, e a página que aparece
quando ele cancela.

> Esta SPEC **não propõe uma arquitetura nova**. Ela termina a única linha não
> executada de um bloco que foi executado — e coloca a trava que impede a
> regressão de acontecer uma quarta vez.

## 0.2 O que o Founder pediu, textualmente

1. *"os agentes de atendimento precisam estar 100% desligados e não podem ser
   executados… garanta que os agentes permanecem desligados, todos eles"*
2. *"preciso deixar o auxiliar de cobrança pronto… mas quero isso pronto pra
   qualquer corretora e não apenas na Resulta ou na AutoFleet"*
3. *"quero que tenha um celular pareado que possa ser usado pelo Auxiliar de
   Cobranças sem interferir no atendimento"*
4. *"as rotinas só existem nos auxiliares"* — a arquitetura
5. *"deixar tudo redondinho, organizado"* — o modal
6. *"criar um lugar onde os briefings, relatórios, entregas fiquem disponíveis
   para clicar e ver. Eu não consigo acessar as coisas que ficam prontas"*
7. *"o mais importante é o Auxiliar de Cobrança funcionar… e a msg e o boleto
   chegarem no WhatsApp de teste"*

---

# 1. Autoridade — antes de tocar em uma linha

```text
CLAUDE.md (processo)
→ SPEC-052 · SPEC-053 · SPEC-054/055/056/057
→ docs/canon/ONTOLOGIA-DO-TRABALHO.md   ← Bloco C depende desta
→ docs/canon/GLOSSARIO.md
→ docs/canon/MIGRATIONS-AUTHORITY.md    ← antes de qualquer SQL
→ SPEC-064 (a ontologia que esta SPEC termina de executar)
→ SPEC-063 Bloco D (a proibição do observer — não afrouxar)
```

**Leitura obrigatória antes do Bloco C:** `ONTOLOGIA-DO-TRABALHO.md` inteiro. O
Bloco C move telas com base nele; executar sem ler é como refazer a SPEC-064 no
escuro.

# 2. Preflight

```bash
git rev-parse --show-toplevel      # AutoBrokers-Opus-Exec
git branch --show-current
git rev-parse HEAD                 # registrar no relatório
git status --short                 # limpo ao iniciar
```

E o preflight **desta** SPEC, que é específico e não pode ser pulado:

```sql
-- 1. Nenhum agente de atendimento pode estar ligado ao iniciar.
select c.company_name, a.name, a.is_active
  from agents a join companies c on c.id = a.company_id
 where a.agent_role = 'attendance' and a.is_active = true;
-- ESPERADO: zero linhas. Se voltar linha, PARE e avise o Founder.

-- 2. Nenhuma rotina pode estar ativa ao iniciar.
select id, name, is_active from routines where is_active = true;
-- ESPERADO: zero linhas.
```

---

# 3. Estado medido que motivou a SPEC

Tudo abaixo foi medido em **17/08/2026**, projeto `dcajcvlzcjbmyapmklil`, contra
o commit `6e1d4d3`.

## 3.1 Segurança — o que está certo

📊 Os quatro agentes de atendimento estão desligados:

| Corretora | Agente | `agents.is_active` |
|---|---|---|
| AMANDUS SEGUROS | JOANA | false |
| AutoFleet | Maria Regina | false |
| Resulta Seguros | Saionara | false |
| Blueprint Studio | Even | false |

📊 O interruptor é **um só**: `agents.is_active` do papel `attendance`, lido por
`attendance_capture.attendance_agent_active()`. O caminho de resposta o consulta
em **quatro pontos independentes**, e todos falham **para o lado do silêncio**:
coluna NULL → calado; linha ausente → calado; exceção na leitura → calado.

📊 `companies.agent_enabled` e `agents.agent_enabled` **não são interruptores**.
`grep agent_enabled backend/app/agents/nodes.py` → **zero**. Nenhum caminho de
runtime as lê para decidir se responde. É por isso que estão `true` em todos os
agentes desligados sem contradição.

## 3.2 Segurança — o que está errado

| | Defeito | Evidência |
|---|---|---|
| **S1** | `check_platform_queue` roda a cada 10 min, para todas as empresas, envia a **segurado**, e **não lê o interruptor** | `platform_outbound.py:664-715`, `buffer_processor.py:339-344` |
| **S2** | `routine_engine._deliver` **não exclui o `observer`** — a correção da SPEC-063 D entrou no `billing_collection` e não aqui | `routine_engine.py:184-198` vs `integration_service.py:191-199` |
| **S3** | `routine_engine` **nunca consulta `tenant_auxiliaries.status`** — desligar o Auxiliar não desliga o robô | grep sem ocorrência; `routine_engine.py:303-312` |
| **S4** | `agent_enabled` é coluna sem leitor, e um comentário aponta para um leitor que não existe | `portao_do_prompt.py:213` → `nodes.py:438` não tem a string |

**Sobre S1**: hoje ele não morde por três acidentes — fila vazia,
📊 `platform_sends` com 0 linhas, e canal recusado por ser observer. Pelo
critério escrito no próprio repositório (`webhook.py:578`): *"não é trava: é
sorte"*.

**Sobre S2**: 📊 AutoFleet e AMANDUS têm **apenas** integração `observer` ativa.
O relatório da rotina inclui **CPF/CNPJ e telefone dos segurados em texto
claro** (`billing_collection.py:1066-1075`). Trocar "Relatório da rotina" para
WhatsApp faria esse conteúdo sair pelo número que existe para ficar calado.

## 3.3 O celular pareado não pode enviar

📊 O dashboard pareia com `purpose='observer'`
(`app/api/dashboard/whatsapp-channel/route.ts:9`), e `observer` está em
`PROPOSITOS_QUE_NUNCA_ENVIAM` (`integration_service.py:192`).

> **O número pareado da corretora literalmente não consegue enviar o boleto.**
> Esta é a causa de fundo pela qual a Cobrança nunca fechou o ciclo a partir de
> um número pareado pelo dashboard.

📊 E o conceito da solução já existe sem produtor: `routine_engine.py:196` tem
`_rank = {"auxiliary": 0, "attendance": 1}` — um canal `auxiliary` já é
**preferido** pelo código, e **nada no sistema cria esse registro**.
📊 `integrations.purpose` é texto livre, sem CHECK.

## 3.4 A Rotina nasce órfã — sempre

📊 `routines.tenant_auxiliary_id` é **nullable**, sem default, sem FK, sem
trigger. A regra canônica *"sempre com `tenant_auxiliary_id`"*
(`GLOSSARIO.md:18`) **não existe no banco**.

📊 O repositório inteiro tem 42 linhas mencionando a coluna. **Nenhuma delas a
escreve na tabela `routines`.** Os quatro escritores:

| Escritor | Preenche o dono? |
|---|---|
| `app/api/dashboard/rotinas/route.ts:162` (tela) | **não** |
| `backend/app/agents/tools/routine_tools.py:119` (chat) | **não** |
| `backend/app/services/research/monitor_service.py:226` | **não**, e nasce `is_active: True` |
| `backend/app/services/research/radar.py:144` | grava `config: {"auxiliar": SLUG}` — **o dono como string dentro de um JSONB** |

O único lugar que já preencheu a coluna foi a migration one-shot
`20260802_03_spec064_rotina_tem_dono.sql`, casando por `name ilike '%cobran%'`.

📊 **A regressão já aconteceu.** A rotina criada em 17/08 às 13:01 está com
`tenant_auxiliary_id = NULL`, na mesma corretora onde `cobranca-feita` está
instalada. Os dois lado a lado sem se conhecerem — e o card diz *"Nenhuma rotina
ainda"* com uma rotina agendada.

📊 O teste que veria isso (`test_ontologia_e_unica.py:228-233`) **nunca roda**:
as funções se chamam `teste_*` e o pytest coleta `test_*`; não há script npm que
o execute; e ele faz `return` silencioso sem `SUPABASE_URL`.

## 3.5 O modal — o que é motor e o que é enfeite

| Campo | Veredito |
|---|---|
| Seguradoras (`portal_keys`) | ✅ **motor** — mas a tela só deixa marcar **2 de 6** |
| Deduplicação entre dias | ✅ **motor** — chave `(company_id, recibo, send_mode)`, **permanente** |
| Modo `test` | ✅ **motor** — único que envia |
| Modo `approval` | ❌ **enfeite** — `send_billing_whatsapp` aparece **1 vez** no repo: no próprio insert |
| Modo `live` | ❌ **enfeite** — não existe caminho de código até um envio |
| Modo `none` | ✅ funciona (não fazer nada é o correto) |
| `approval_required` | ❌ **enfeite** nos quatro modos |
| `max_boletos_por_execucao` | ✅ **motor** — aceita 1; limita **downloads**, não envios |
| `test_number` | ✅ **motor** — só em `test`; herda de `delivery.number` se vazio |
| `message_template` | ⚠️ editável, apesar de o código afirmar que é travado; textarea abre **vazio** |
| **`instructions`** | ❌ **obrigatório e inerte** — `routine_engine.py:224` desvia antes do prompt; zero hits em `billing_collection.py` |
| **`knowledge`** | ❌ **inerte em cobrança** — não há LLM onde injetar |
| Auxiliar ligado/desligado | ❌ **enfeite para a rotina** (é o S3) |

📊 Detalhe que engana: a tela tem `PORTAIS_COM_COBRANCA = ['allianz_corretor',
'hdi_corretor']` fixo (`page.tsx:62`), enquanto
`portal_worker/journeys/__init__.py:51-80` tem **6** portais com
`cobranca_sweep`. E a rotina atual tem **6 portais salvos** — ao reabrir o modal,
quatro aparecem **desmarcados e desabilitados**, estando ativos no motor.

## 3.6 O trabalho fica pronto e não pode ser visto

Esta é a queixa nº 6 do Founder, e ela é literal.

| | Defeito | Medição |
|---|---|---|
| E1 | **Não existe rota de visualização de Artifact** no produto | `find app -type d -iname "*artifact*"` → **zero**. Os 36 artifacts têm `href: null` |
| E2 | Todo briefing em Entregas leva ao **cartão descritivo**, não ao briefing | href `/dashboard/auxiliares/checklist-6h`, capturado por `[slug]`. O endereço certo já está em `catalog.ts:96` e não é usado |
| E3 | `routine_runs` **não é lida** por Entregas | 📊 32 execuções invisíveis; `auxiliary_runs` tem 4 |
| E4 | O relatório é **cortado em 500** de até 4000 caracteres | `routine_engine.py:257` — 87% descartado, incluindo "PRECISA DE VOCÊ" |
| E5 | Não existe tela que mostre um relatório inteiro | só uma linha de 11px com `truncate` |
| E6 | `?tipo=` dos redirects é **ignorado** | `EntregasClient.tsx:91` nunca lê `searchParams` |
| E7 | Filtro "Pesquisas" com contagem que nunca sai de zero | nenhuma fonte produz esse tipo |
| E8 | A Cobrança **não gera Artifact** — descumpre a SPEC-057 | zero ocorrências de `artifact` em `billing_collection.py` |
| E9 | Boletos ficam no Storage **indefinidamente** | 📊 62 objetos, o mais antigo de 11/07, sem purga — dado financeiro de terceiro |

📊 Somando só para a AutoFleet: 10 artifacts (href null) + 26 briefings (href
errado) + 8 atividades (href null) = **44 itens**, e o filtro "Documentos" é
**100% não-navegável ou navega errado**.

---

# 4. As três decisões, e POR QUE — a pedido do Founder

O Founder pediu, textualmente: *"vc precisa deixar isso bem claro na
documentação dos motivos"*. Aqui estão as três, com a alternativa que foi
rejeitada e a razão.

## Decisão 1 — Executar os quatro blocos, não um recorte

**Nota 95.** Porque os defeitos **se sustentam entre si**. Consertar o modal sem
consertar S3 entrega uma tela bonita cujo interruptor principal não desliga
nada. Consertar a ontologia sem consertar Entregas cria um redirect que declara
*"conteúdo absorvido"* sobre 32 execuções que não foram absorvidas — e aí o
comentário passa a mentir, que é o defeito que a SPEC-064 §J.2.4 mandou
eliminar.

**Rejeitado — "só o Bloco 0 e o modal, para testar hoje" (nota 55):** entregaria
o teste funcionando sobre uma base que produz rotina órfã toda vez. Em setembro
esta análise seria escrita de novo.

## Decisão 2 — Canal `auxiliary` como segunda linha de `integrations`

**Nota 91.** O mesmo número, duas linhas, dois papéis:

```text
purpose = 'observer'    consome o inbound e CALA        ← comportamento intacto
purpose = 'auxiliary'   canal de SAÍDA dos Auxiliares   ← novo, só envia
```

O comportamento de atendimento **não muda em nada** — o `observer_tap` continua
consumindo o evento e devolvendo `{"status":"observed"}`. E o código já prefere
`auxiliary` (`routine_engine.py:196`), então não é conceito novo: é o produtor
que falta.

**Rejeitado — trocar o purpose do pareado para `attendance` (nota 54):**
funciona, mas o inbound passa a atravessar o pipeline inteiro até o portão de
silêncio. Mais superfície de risco para o mesmo ganho.

**Rejeitado — afrouxar a proibição do `observer` (nota 8):** é desfazer a
correção da SPEC-063 D, cuja causa está escrita no código:
*"Última prioridade não protege. Só a proibição protege."*

**Rejeitado — segundo QR / segundo número (nota 40):** custa uma instância
Evolution por corretora e um fluxo de pareamento novo, para um risco que a opção
de nota 91 já elimina.

## Decisão 3 — `live` fica para a rodada seguinte

**Nota 88 para adiar.** Três razões concretas:

1. **`live` não é configuração, é construção.** 📊 Não existe caminho de código
   do `live` até um `send_message`. `billing_collection.py:1206-1213` tem dois
   ramos e os dois só escrevem uma frase no relatório. Não há `else` que envie.
2. **Falar com cliente real merece o gate dele.** Um envio errado em modo teste
   incomoda o Founder. Um envio errado em `live` chega num segurado, com o nome
   da corretora, com um boleto anexado.
3. **A dedup é permanente e não tem desfazer.** 📊 Chave
   `(company_id, recibo, send_mode)`, sem janela, sem expurgo. Um erro em `live`
   queima aquele recibo para sempre naquele modo.

**O que esta SPEC deixa encaminhado** (Bloco F): o governador de vazão já existe
e funciona — espaçamento 4–8 min, teto 12/h, **20/dia** para canal novo, janela
08:00–20:00, domingo bloqueado, freio de emergência por corretora, Redis mudo =
não envia. Os 5 inadimplentes/dia da Resulta cabem com folga. O que falta é
**o fio** entre a cobrança e `send_to_client_guarded`, e ele é escrito na
SPEC-079 com o gate próprio.

**Rejeitado — construir `live` nesta SPEC (nota 62):** é tecnicamente viável e
seria a única parte da SPEC capaz de causar dano irreversível a terceiro. Juntar
isso a uma SPEC que mexe em ontologia, telas e migrations é misturar o
reversível com o irreversível no mesmo gate.

---

# 5. Definições que não podem ser misturadas

| Palavra | Significado nesta SPEC |
|---|---|
| **Auxiliar** | *quem faz*. Trabalhador instalado na corretora. `tenant_auxiliaries` |
| **Rotina** | *quando acontece*. **Nunca existe sozinha.** `routines` |
| **Agenda** | o conjunto dos "quandos". Nome canônico em `ONTOLOGIA:80`. É **relatório**, não gaveta |
| **Interruptor do agente** | `agents.is_active` do papel `attendance`. **Um só** |
| **Interruptor do Auxiliar** | `tenant_auxiliaries.status`. Depois do Bloco A, **governa a rotina** |
| **Canal de saída** | linha de `integrations` cujo `purpose` **não** está em `PROPOSITOS_QUE_NUNCA_ENVIAM` |
| **Entrega** | qualquer coisa que o sistema produziu e o corretor pode **abrir** |

> **"Auxiliares agendados" é nome proibido.** `GLOSSARIO.md:113-121` mantém a
> lista de termos que não existem no produto, e a última linha é
> `~~Auxiliares = Rotinas~~ — revogada pela SPEC-064`. Uma página que lista
> rotinas e se chama "Auxiliares agendados" afirma que cada linha é um Auxiliar.
> O nome é **Agenda**.

---

# 6. Invariantes — se uma delas quebrar, a SPEC falhou

```text
I1  Nenhum agente de atendimento é ligado por esta SPEC. Nenhum.
I2  Nenhuma mensagem chega a um cliente real. O único destino é o test_number.
I3  Toda Rotina tem dono. Verificado por constraint, não por disciplina.
I4  Desligar o Auxiliar para o robô dele. Sem exceção.
I5  O observer nunca vira canal de saída. A proibição da SPEC-063 D não afrouxa.
I6  Nenhum campo do modal existe sem ter efeito. Enfeite sai ou vira leitura.
I7  Toda entrega listada em Entregas ABRE. Nenhum href: null, nenhum destino errado.
I8  Nenhum motor paralelo é criado. Nem de rotina, nem de catálogo, nem de publisher.
```

---

# 7. BLOCO A — Segurança: fechar as portas que dependem de sorte

**Gate:** os quatro consertos aplicados, com teste de mutação provando que cada
guarda **consegue** ficar vermelho.

## A.1 — `send_to_client_guarded` lê o interruptor (S1)

No topo de `platform_outbound.send_to_client_guarded`:

```python
if not await attendance_agent_active(company_id):
    return {"ok": False, "reason": "agente_desligado"}
```

**Por que aqui e não em `check_platform_queue`:** o guarda tem de ficar na função
que **envia**, não na que drena. Qualquer chamador futuro herda a proteção.

**Prova exigida:** um teste que enfileira um envio, deixa o agente desligado, e
verifica que nada sai. **Mais a linha de CONTROLE** — o mesmo envio com o agente
ligado **sai**. Sem o controle, um guarda que bloqueia tudo passaria igual.

## A.2 — `routine_engine._deliver` exclui o `observer` (S2)

Trocar a seleção manual de integração por `IntegrationService.pode_enviar()`, que
é a autoridade única desde a SPEC-063 D.

**Prova exigida:** rotina de uma corretora que só tem `observer` ativo → o
relatório **não** é entregue, e o motivo aparece no `routine_runs.error`. Linha
de controle: a mesma corretora com um canal `auxiliary` ativo → entrega.

## A.3 — Desligar o Auxiliar desliga o robô (S3)

`routine_engine.run_due_routines` passa a consultar o estado do Auxiliar dono
antes de executar. Rotina cujo Auxiliar está `paused`, `inactive`, `disabled` ou
`archived` **não roda** — e o motivo é registrado, não engolido.

**Ordem importa:** este item **depende do Bloco C** (a rotina precisa ter dono
para que o estado do dono possa ser consultado). Executar C antes de A.3, ou
A.3 tolera dono nulo temporariamente e o gate final exige que não haja nenhum.

**Prova exigida:** Auxiliar `paused` + rotina `is_active=true` + `next_run_at` no
passado → **não executa**. Controle: Auxiliar `active`, mesma rotina → executa.

## A.4 — `agent_enabled` para de mentir (S4)

📊 A coluna não tem leitor no runtime. Duas saídas, e a SPEC escolhe a segunda:

- **(a)** fazer o runtime lê-la — nota 20: cria um segundo interruptor onde a
  SPEC-045 estabeleceu que há um só.
- **(b)** documentar que ela é legada e corrigir o comentário mentiroso de
  `portao_do_prompt.py:213`, que aponta para um leitor em `nodes.py:438` que não
  existe — **nota 90**.

Também: os três lugares que a escrevem `true` no nascimento
(`bootstrap-tenant/route.ts:107`, `blueprint-studio-store.ts`,
`AgentConfigModal.tsx:2180`) ganham comentário dizendo que o valor não liga
nada. **Não removo a coluna** — remoção de coluna viva não cabe numa SPEC de
funcionalidade.

## A.5 — O guarda dos agentes desligados

Teste novo, executável, que consulta o banco e falha se **qualquer** agente de
papel `attendance` estiver `is_active = true` sem registro de autorização.
Roda no gate final desta SPEC e fica disponível como
`npm run test:agentes-desligados`.

---

# 8. BLOCO B — O canal `auxiliary`: o WhatsApp pareado passa a poder enviar

**Gate:** o número pareado da corretora envia uma mensagem de Auxiliar sem
alterar em nada o comportamento de atendimento.

## B.1 — O produtor que falta

O pareamento pelo dashboard passa a criar **duas** linhas em `integrations` para
o mesmo número/instância:

```text
purpose = 'observer'    is_active = true    consome inbound, NUNCA envia
purpose = 'auxiliary'   is_active = true    canal de SAÍDA dos Auxiliares
```

**Migration expand-first**: nada é apagado; corretoras já pareadas ganham a linha
`auxiliary` por backfill, derivada da linha `observer` existente.

## B.2 — Quem pode usar o canal `auxiliary`

Só código de Auxiliar/Rotina. **Não** é canal de resposta de atendimento:
`webhook.py` continua exigindo o papel `attendance` e o portão de silêncio.

A ordem de preferência já existe (`routine_engine.py:196`,
`_rank = {"auxiliary": 0, "attendance": 1}`) e passa a valer também em
`billing_collection._find_whatsapp_integration` e em
`get_platform_whatsapp_integration`.

## B.3 — A tela diz o que aquele número faz

Na tela de conectores, o número pareado passa a mostrar os dois papéis em texto
de corretor:

```text
Este número observa as conversas e aprende (não responde sozinho).
Ele também é o número por onde seus Auxiliares enviam — cobrança, relatórios.
Para ele responder os segurados, ligue o Agente de Atendimento.
```

**Prova exigida:** com o agente desligado, uma mensagem inbound continua sendo
**apenas observada** (o `observer_tap` consome), e um envio de Auxiliar **sai**
pelo mesmo número. As duas coisas no mesmo teste — é o par que prova que os
papéis não se contaminam.

---

# 9. BLOCO C — Auxiliar × Rotina: a quarta linha da SPEC-064

**Gate:** impossível criar rotina sem dono. Verificado por constraint.

## C.1 — A trava (a parte que a SPEC-064 não fez)

```sql
-- 1. backfill das órfãs (ver C.2 para o dono das ad-hoc)
-- 2. alter table routines alter column tenant_auxiliary_id set not null;
-- 3. foreign key para tenant_auxiliaries(id)
```

Expand-first, idempotente, com **APPLY / VERIFY / ROLLBACK escritos antes de
rodar** (CLAUDE.md §8).

> **Por que constraint e não disciplina:** a SPEC-064 corrigiu os dados e deixou
> a porta aberta. 📊 Quinze dias depois nasceu outra órfã. A regra tem de virar
> estrutura, senão em setembro esta análise é escrita de novo.

## C.2 — O Auxiliar de plataforma `tarefas-agendadas`

Sem ele o `NOT NULL` é impossível, porque existe um caso legítimo de rotina que
não pertence a nenhum Auxiliar de catálogo: *"todo dia às 8h me manda um resumo"*
criada no chat, com `visibility: 'personal'`.

Transformar cada uma dessas em Auxiliar quebraria três regras de uma vez:
`✗ Auxiliar nascendo fora do catálogo` (`ONTOLOGIA:209`), SPEC-064 G.2.4 (*"o
chat nunca cria algo global"*), e a inexistência de "Auxiliar pessoal" no cânone.

**A saída é um Auxiliar de plataforma no catálogo global**, instalado por padrão,
dono de toda rotina ad-hoc — do chat, do Monitor e do Radar. Um Auxiliar, não um
por pedido.

## C.3 — Os quatro escritores passam a dar dono

| Escritor | O que muda |
|---|---|
| `app/api/dashboard/rotinas/route.ts` | recebe e grava o `tenant_auxiliary_id` |
| `routine_tools.py` (chat) | dono = `tarefas-agendadas` da corretora |
| `monitor_service.py` | dono = `tarefas-agendadas`; e **para de nascer `is_active: True`** |
| `radar.py` | `config.auxiliar` (string num JSONB) vira a **coluna** — CLAUDE.md §12.1 |

## C.4 — A rotina vira aba dentro do Auxiliar

`app/dashboard/auxiliares/rotinas/page.tsx` (636 linhas) segue o **mesmo padrão
das três irmãs**: o conteúdo é absorvido pela tela do Auxiliar, e a rota vira
stub de redirect de ~17 linhas.

O destino já está escrito e com o nome certo:
`AuxiliarDetalheClient.tsx:254` — **"Rotinas deste Auxiliar"**. O possessivo faz
todo o trabalho: diz que é Rotina e diz de quem é.

**O botão "Nova rotina" da lista solta morre.** Ele é literalmente a máquina que
produziu a órfã de 17/08.

## C.5 — A **Agenda**: leitura, nunca gaveta

A lista agregada continua existindo, porque *"o que vai rodar amanhã de manhã?"*
é pergunta legítima e nenhum cânone a proíbe. Mas com três regras que a impedem
de virar a segunda gaveta:

```text
1. SOMENTE LEITURA — sem botão de criar
2. Cada linha diz de QUEM é, e leva ao Auxiliar dono
3. Chama-se Agenda (ONTOLOGIA:80), nunca "Auxiliares agendados"
```

## C.6 — `routine_templates` morre

📊 As três linhas são três Auxiliares com outro nome:

```text
"Cobranca de boletos atrasados"  ≡  auxiliary_templates.cobranca-feita
"Resumo do dia do agente"        ≡  auxiliary_templates.resumo-atendimentos
"Noticias do setor"              ≈  auxiliary_templates.radar-mercado-regulacao
```

É a `✗ segunda página de catálogo` que a SPEC-064 §6 proibiu textualmente, com
CRUD admin próprio ("Rotinas Prontas"). E é ela que fabrica as órfãs: a rotina de
17/08 tem **exatamente o nome do template**.

O `config_default` migra para `auxiliary_templates`, o admin some, e
`/admin/routine-templates` vira redirect.

**Ressalva de método:** o `config_default` do template usa `portal_keys` e
`approval_required`; o `auxiliary_templates.default_config` usa `portais` e
`exige_aprovacao_para_enviar`. 📊 São nomes diferentes para os mesmos campos.
Copiar um no outro faria a seleção de seguradoras cair no default **em silêncio**.
A migração **unifica os nomes** nos que o motor lê (`billing_collection.py:385,394`).

## C.7 — Um dono só para a agenda

📊 `lib/auxiliaries/config-store.ts:35-46` aceita `horario` e `frequencia`, e
**nenhum consumidor no backend os lê** — o agendador lê `routines.schedule`.

Os dois campos **saem do whitelist**. Se a aba nova gravasse ali, o horário
mudaria na tela e a rotina rodaria no horário antigo — que é pior que não ter o
campo.

## C.8 — O teste de ontologia passa a rodar

`test_ontologia_e_unica.py` tem as funções nomeadas `teste_*` e o pytest coleta
`test_*`. Renomear, registrar como `npm run test:ontologia`, e fazer o `return`
silencioso por falta de `SUPABASE_URL` virar **falha explícita** no gate.

> Um guarda que não tem como rodar não guarda nada. CLAUDE.md §9.3.

---

# 10. BLOCO D — O modal: tirar o enfeite, consertar o que engana

**Gate:** todo campo visível tem efeito, e o que não tem virou leitura ou sumiu.

## D.1 — Nome fixo

📊 `routines.name` é rótulo em runtime (aparece no título do relatório). Nenhum
código de runtime casa por nome. Passa a ser fixo, igual ao nome do Auxiliar.

## D.2 — `instructions` vira leitura, e deixa de ser obrigatório

📊 Em rotina de cobrança o campo é **inerte**: `routine_engine.py:224` desvia
para o motor determinístico antes de chegar ao prompt; zero hits de
`instructions` em `billing_collection.py`. E é **obrigatório**, mínimo 10
caracteres (`route.ts:159`).

> É o pior tipo de campo: obrigatório, editável, e sem efeito. Ele ensina o
> corretor a acreditar que instruiu o robô.

Para Auxiliar com motor próprio: **exibido, não editável**, com uma frase
dizendo que aquilo é o que o Auxiliar faz. Deixa de ser obrigatório.
Para rotina genérica (LLM), continua editável — ali ele funciona de verdade.

## D.3 — `knowledge` some da cobrança

📊 Mesmo destino: só é lido em `render_task_prompt`, que rotina de cobrança nunca
alcança. Em cobrança **não há LLM** onde injetar conhecimento — o motor enfileira
job, faz polling e formata relatório determinístico.

O campo continua existindo para rotinas genéricas, onde tem função real.
(Corrigir de passagem: 📊 hoje um conhecimento já gravado **não pode ser
apagado**, porque string vazia não entra no patch — `route.ts:178`.)

## D.4 — As seis seguradoras

`PORTAIS_COM_COBRANCA` fixo no front (`page.tsx:62`) passa a vir de
`portais_com_cobranca()` do registro — a mesma fonte que o worker usa.
📊 São 6: allianz, hdi, mapfre, tokiomarine, yelum, zurich.

**E o checkbox passa a refletir o que está salvo.** Hoje
`checked={disponivel && billingPortalKeys.includes(p.key)}` esconde portal ativo
que a tela considera indisponível.

## D.5 — O erro aparece no modal

📊 O modal **não** fecha no erro — o `notice` é que é renderizado no corpo da
página, atrás do overlay `bg-black/60`. Ganha um lugar **dentro** do modal.

E o botão "Criar rotina" passa a exigir número de WhatsApp válido (hoje fica
clicável com o campo vazio, e a única barreira é um 400 invisível).

## D.6 — Dias da semana viram seletor

📊 A legenda "0=seg … 6=dom" está **correta** (convenção `datetime.weekday()`,
confirmada em três lugares). Mas caixa de texto CSV é ruim de usar.

Vira seletor de dias, no mesmo padrão visual das seguradoras, **com seg–sex
marcados por padrão**.

**E o defeito ao lado:** 📊 `route.ts:151-155` calcula o **primeiro**
`next_run_at` ignorando `weekdays`. Uma rotina "só segunda" criada num sábado
dispara no domingo. Passa a usar a mesma função do Python.

## D.7 — O template mostra o que vai sair

📊 O textarea abre **vazio** quando não há template salvo, em vez de mostrar o
padrão. O corretor nunca vê a mensagem que vai ser enviada.

Passa a exibir o `DEFAULT_MESSAGE_TEMPLATE` quando não houver salvo. Ganha
validação de chaves: 📊 hoje um `{` solto faz o `format_map` levantar e o sistema
manda **o template padrão sem avisar ninguém**, e uma chave desconhecida vira
**buraco vazio** na frase.

**Decisão sobre editabilidade** (nota 85): permanece **editável**, porque o
Founder quer personalizar por corretora — mas com pré-visualização preenchida e
a lista de chaves válidas ao lado. O comentário do código que afirma ser
read-only (`billing_collection.py:75-77`) é corrigido para não mentir.

## D.8 — Navegação fecha o círculo

Cancelar volta ao Auxiliar. Breadcrumb aponta para o Auxiliar, não para a lista.
Com o Bloco C isso é quase automático: o modal passa a viver dentro da tela do
Auxiliar.

## D.9 — Separação nível Auxiliar × nível Rotina

O Founder pediu isso e está certo:

| Nível **Auxiliar** (uma vez, vale para todas as rotinas dele) | Nível **Rotina** (só o *quando*) |
|---|---|
| seguradoras · modo de envio · máx. boletos · número de teste · mensagem ao cliente · destino do relatório | tipo · horário · dias · intervalo · ativa/pausada |

📊 A tabela para o lado esquerdo **já existe**: `tenant_auxiliaries.config`, com
histórico versionado (`tenant_auxiliary_revisions`) e endpoint pronto — SPEC-064
Bloco F, construído e sem nenhum chamador na UI.

> Esta SPEC **usa o Bloco F em vez de criar outro store**. E cuida do risco de
> C.6: o motor lê `routines.config`, então enquanto a leitura não migrar, a
> gravação em `tenant_auxiliaries.config` **espelha** para `routines.config` de
> forma explícita e testada — nunca duas verdades silenciosas.

---

# 11. BLOCO E — Modos de envio: o seletor para de prometer

**Gate:** todo modo listado no seletor tem motor atrás.

## E.1 — `approval` e `live` saem do seletor

📊 `approval`: a string `send_billing_whatsapp` aparece **uma vez** em todo o
repositório — no próprio insert. O endpoint de execução tem allowlist e ela não
está nela; o card nem renderiza porque a UI espera `titulo`/`mensagem` e a
cobrança grava `routine_name`/`items_count`.

📊 `live`: sem caminho de código até um envio.

Ficam **dois** modos, com nomes que dizem a verdade:

```text
Teste (envia para o número de teste)
Somente relatório (não envia nada ao cliente)
```

**Isto não apaga funcionalidade** — apaga a promessa de funcionalidade que não
existe. Os valores `approval` e `live` continuam válidos no banco; a SPEC-079 os
devolve ao seletor quando tiverem motor.

## E.2 — `approval_required` some da tela

📊 Enfeite nos quatro modos. Em `live` seu único efeito é decidir se nasce um
pedido que ninguém lê.

## E.3 — A mensagem de teste

📊 Hoje leva prefixo `[TESTE AutoBrokers - Auxiliar de Cobranca]` e duas linhas
de aviso no fim. O Founder quer conferir a mensagem que o cliente vai receber.

**Decisão (nota 90):** o prefixo **fica** — mandar em teste algo indistinguível
do real é como o produto acaba mandando o real achando que é teste. Mas o modal
ganha uma **pré-visualização da mensagem final, sem prefixo**, com dados de
exemplo. O Founder vê exatamente o que o segurado verá, sem que a mensagem de
teste minta sobre o que é.

## E.4 — Reenviar um boleto já enviado

📊 A dedup é permanente e não tem desfazer pela interface. Para testar, o Founder
precisaria apagar linhas à mão.

Ganha um botão explícito no Auxiliar: **"Liberar reenvio dos boletos de teste"**,
que limpa **apenas** as linhas com `send_mode='test'` daquela corretora, com
confirmação. **Nunca toca em `live`.**

---

# 12. BLOCO F — Entregas: onde o trabalho pronto fica visível

Esta é a parte que o Founder descreveu como *"não consigo acessar as coisas que
ficam prontas"*. Ela é a última do escopo e a mais visível.

**Gate:** **toda** linha listada em Entregas abre. Zero `href: null`, zero
destino errado. Verificado por teste que percorre a lista.

## F.1 — A rota de Artifact que não existe

📊 `find app -type d -iname "*artifact*"` → **zero**. Os 36 artifacts têm
`href: null` com o comentário *"ainda não há rota de tenant"*.

Nasce `/dashboard/entregas/[artifactId]`:

```text
título · quando · qual Auxiliar produziu · o conteúdo renderizado
botão de baixar · link de volta para o Auxiliar dono
```

Multi-tenant pelo padrão da casa: **RLS + filtro por `company_id` no
repository**, com teste de isolamento entre dois tenants reais (CLAUDE.md §7).

## F.2 — Os briefings param de levar ao lugar errado

📊 O href é `/dashboard/auxiliares/checklist-6h`, capturado por `[slug]`, que
renderiza o cartão descritivo. O endereço certo — `/checklist-6h/hoje` — já está
escrito em `catalog.ts:96` e não é usado.

A rota de Entregas passa a **usar aquele mapa**, em vez de montar o href à mão.
Fonte única, e o próximo Auxiliar com tela própria funciona de graça.

## F.3 — `routine_runs` chega em Entregas

📊 32 execuções invisíveis, contra 4 de `auxiliary_runs` que aparecem.

Vira a sexta fonte da rota. **É pré-requisito do C.4**: sem isso o redirect
declararia *"conteúdo absorvido"* sobre um histórico que não foi absorvido — e o
comentário passaria a mentir.

## F.4 — O relatório inteiro é guardado e pode ser aberto

📊 `output_preview = output[:500]` de um relatório de até 4000 caracteres. 87%
descartado no ato, incluindo "PRECISA DE VOCÊ" e a lista de clientes.

O relatório completo passa a ser guardado, e a execução ganha página própria.

⚠️ **O relatório contém CPF/CNPJ e telefone de segurados.** A página é
tenant-scoped e passa pelo redator antes de qualquer log. Não vai para RAG, não
vai para Qdrant, não aparece em artifact global.

## F.5 — A Cobrança gera Artifact (SPEC-057)

📊 Hoje o trabalho da cobrança é uma string. Zero ocorrências de `artifact` em
`billing_collection.py`, e zero `work_runs` com `source_type='routine'`.

Cada execução passa a produzir um Artifact de primeira classe — a lista de
inadimplentes, os boletos, as tarefas da equipe — usando o **Artifact Hub que já
existe**. Nenhum publisher novo.

## F.6 — Os filtros funcionam

📊 `?tipo=` é ignorado (`EntregasClient.tsx:91` nunca lê `searchParams`), e os
redirects de `/dashboard/historico` e `/dashboard/auxiliares/execucoes` chegam
sem filtro. Passa a ler. O filtro "Pesquisas", que 📊 nunca sai de zero, ou ganha
fonte ou some — decidido na execução pela regra 0–100.

## F.7 — Os boletos ganham prazo

📊 62 objetos no bucket `portal-evidence`, o mais antigo de 11/07, **sem nenhuma
rotina de purga**. É dado financeiro de terceiro sem prazo de descarte.

Esta SPEC **não apaga nada**. Ela registra a política, instrumenta a contagem por
idade, e deixa a purga pronta e **desligada** — ligar é decisão do Founder, com
prazo definido por ele. (CLAUDE.md §11.1: *"deixar pronto e desligado é
aceitável"*.)

---

# 13. O teste de aceitação — a única prova que importa

Tudo acima é meio. **Isto é o fim.** A SPEC só está verde quando esta sequência
inteira funcionar, medida e registrada com saída real:

```text
 1. Numa corretora com credencial de seguradora e WhatsApp pareado
 2. Instalar o Auxiliar de Cobrança → instala, sem install_failed
 3. Abrir o Auxiliar → a rotina dele aparece na tela DELE
 4. Configurar: 1 seguradora · máx. 2 boletos · modo Teste · número de teste
 5. Ver a pré-visualização da mensagem exata que o segurado receberia
 6. Ligar o Auxiliar e ativar a rotina
 7. O robô entra no portal, encontra o inadimplente, baixa o boleto
 8. A MENSAGEM E O PDF CHEGAM NO WHATSAPP DE TESTE
    pelo número pareado da própria corretora
 9. A execução aparece em Entregas, clicável, com o relatório inteiro
10. Desligar o Auxiliar → a próxima execução NÃO acontece
```

**O passo 10 é tão obrigatório quanto o 8.** Um sistema que só sabe ligar não
está pronto.

**E a linha de controle da SPEC inteira:** repetir o passo 7–8 com o agente de
atendimento **desligado** e verificar que **nenhuma resposta automática** saiu
para nenhum inbound naquele número. É o par que prova que os dois papéis do
mesmo telefone não se contaminam.

---

# 14. Regra de decisão autônoma durante a execução

Autorizada pelo Founder em 17/08/2026: *"se vc tiver alguma dúvida na execução,
vc use a regra de nota de 0 a 100 e decida vc mesmo para não parar a execução"*.

```text
Dúvida na execução
  → listar as opções reais
  → nota 0–100 para cada, com o porquê ESCRITO
  → executar a de maior nota
  → registrar em CHANGE-ADDENDA.md com a nota e a razão
```

**A autonomia não cobre** as paradas legítimas do CLAUDE.md §10 — perda de dados,
decisão comercial, conflito canônico, P0/P1 de segurança ou cross-tenant, ação
física do Founder, mudança material de escopo, custo extraordinário. E não cobre
**ligar agente de atendimento** nem **enviar para cliente real**: essas duas são
proibições absolutas desta SPEC (I1 e I2), não dúvidas a serem pontuadas.

---

# 15. O que NÃO entra nesta SPEC

| | Por quê |
|---|---|
| **Modo `live`** (envio a cliente real) | SPEC-079, com gate próprio. Razão completa na Decisão 3 |
| **Modo `approval` com motor** | mesma rodada do `live` — o executor de aprovação é o mesmo fio |
| **Apagar a coluna `agent_enabled`** | remoção de coluna viva não cabe numa SPEC de funcionalidade |
| **Apagar boletos antigos do Storage** | a purga fica pronta e desligada; ligar é decisão do Founder |
| **API oficial da Meta** | SPEC própria, já mencionada pelo Founder |
| **Reescrever a página de Entregas do zero** | o Bloco F conserta o que existe. Não se cria publisher paralelo (CLAUDE.md §5) |

Tudo acima vai para [`PENDENCIAS.md`](../PENDENCIAS.md) com dono e com o que
destrava.

---

# 16. Gates

| Bloco | Gate |
|---|---|
| **A** | 4 consertos aplicados; cada guarda com teste **e linha de controle** provando que consegue ficar vermelho |
| **B** | o número pareado envia por Auxiliar **e** continua mudo no atendimento — no mesmo teste |
| **C** | `NOT NULL` aplicado; zero órfãs; `npm run test:ontologia` verde e **executável** |
| **D** | nenhum campo sem efeito; `tsc` limpo; rotas montam; `next start` responde |
| **E** | seletor só com modos que têm motor |
| **F** | **toda** linha de Entregas abre; teste de isolamento entre dois tenants |
| **FINAL** | os 10 passos do §13, com saída real registrada, **incluindo o passo 10 e a linha de controle** |

**Gate de infraestrutura, em toda migration** (CLAUDE.md §8): APPLY / VERIFY /
ROLLBACK escritos **antes** de rodar. `apply_migration` via MCP 📊 **não é
transacional** — cada statement idempotente por si.

**Gate de aplicação** (CLAUDE.md §9.1): build verde não é prova de que a
aplicação sobe. `npm run test:rotas-montam` + `next start` + requisição real.

**Relatório final:** template canônico, com commit inicial e final, migrations
com saída real, o que ficou fora e por quê, canário Amandus → Resulta →
AutoFleet, riscos remanescentes, e a declaração de que nenhum motor paralelo foi
criado.

---

# 17. Ordem de execução

```text
A  Segurança            ─┐
B  Canal auxiliary      ─┤ independentes, podem ir em paralelo
                         │
C  Ontologia            ─┘ ← A.3 depende de C.1 (rotina precisa ter dono)
D  Modal                   ← depende de C.4 (o modal muda de casa)
E  Modos de envio          ← independente
F  Entregas                ← F.3 é PRÉ-REQUISITO de C.4
                             (o redirect não pode mentir sobre "absorvido")
```

**A dependência que não pode ser invertida:** `F.3` antes de `C.4`. Absorver a
página de Rotinas sem levar `routine_runs` para Entregas apaga a única prova de
que alguma coisa rodou.
