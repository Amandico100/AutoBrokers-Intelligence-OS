# Esclarecimento do Atendimento — as respostas às 12 perguntas

> **02/08/2026** · escrito pelo líder anterior (agora consultor), a pedido do
> Founder, depois de reverificar **na fonte** cada afirmação da
> `AUDITORIA-COMPLETA-DO-ATENDIMENTO.md`.
> **Método:** nada foi aceito por estar escrito — nem o que eu mesmo escrevi.
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1) · FATO / INFERÊNCIA separados.

---

# Veredito em cinco linhas

```
a auditoria dele está CERTA nos fatos ..... reverifiquei 14 afirmações, 14 batem
a leitura arquitetural está ERRADA ........ não existem "dois corredores
                                            disputando"; existe um que MIGROU
a decisão A/B/C não precisa ser tomada .... o canon já a respondeu 3 vezes
o Atlas não quebrou ....................... você desconectou os WhatsApps
ele não está comprometido ................. está com o ESCOPO estourado
```

---

# PARTE 0 · Ele está confuso, ou eu estou?

**Nenhum dos dois, e é importante ser exato aqui.**

O `SPEC-063-BLOCO-0-AUDITORIA.md` que ele escreveu **é o melhor artefato técnico
do repositório.** Ele achou cinco defeitos que eu não achei, corrigiu quatro
erros de fato da minha SPEC, e provou que **80% da 063 é executável hoje**.

Depois disso ele escreveu a `AUDITORIA-COMPLETA-DO-ATENDIMENTO.md` — e o
diagnóstico não é confusão. É **escopo**:

```
Bloco 0 da 063 ......... "DOIS blocos · Bloco 1 não depende de nada"
                          ↓  (o Founder diz "não estrague o atendimento")
Auditoria completa ..... "TRÊS blocos · não toco em nada até você dizer A, B ou C"
```

**Ele passou de destravado a travado sem que nenhum fato novo justificasse.**
O que mudou foi o susto — e o susto é legítimo, ele tinha acabado de errar
publicamente sobre corredores. **A reação certa a um erro de contagem não é
parar; é medir. Ele mediu, e mediu bem. Só não voltou a andar.**

> **RECOMENDAÇÃO:** não abra chat novo. Ele está aquecido, mediu certo, e um
> chat novo repete a descoberta inteira e perde as cinco correções da 063.
> O que falta é **destravar**, e é o que este documento faz.

---

# PARTE 1 · A ontologia do atendimento, em uma página

Esta é a peça que faltou. Ele listou as seis peças corretamente — **mas não
disse qual delas manda em qual, e é isso que resolve todas as dúvidas dele.**

```
                         ┌──────────────────────────────┐
   O SEGURADO FALA  ───► │  ATENDIMENTO (o trabalho)    │
                         │  quem: o AGENTE               │
                         │  o que sabe: RAG + CONDUTA    │
                         │  o estado: WORK RUN (055)     │ ← não existe hoje
                         └───────────────┬──────────────┘
                                         │ precisa acionar a seguradora?
                                         ▼
                         ┌──────────────────────────────┐
                         │  ACIONAMENTO (a ação externa)│
                         │  como: o CORREDOR            │
                         │  por onde: o CANAL            │
                         │  o mapa: o ATLAS              │
                         └──────────────────────────────┘
```

## A tabela que resolve, e a pergunta que decide

| Peça | Chave | O que é | A pergunta que decide |
|---|---|---|---|
| **Carta / RAG** | por assunto | o que **dizer** ao segurado | *"isso é conteúdo de fala?"* |
| **Playbook de conduta** | (ramo, serviço) | **como se comporta** um bom atendente | *"isso vale para qualquer seguradora?"* |
| **Corredor** | (seguradora, ramo, serviço) | o **procedimento** com AQUELA seguradora | *"isso muda se a seguradora mudar?"* |
| **Atlas / `ura_maps`** | por seguradora | o **mapa observado** do menu dela | *"isso foi aprendido olhando, não escrito?"* |
| **Canal** | por seguradora | **onde** bater | *"isso é um endereço?"* |
| **Portal** | por seguradora | o **site** com login da corretora | *"isso exige senha da corretora?"* |
| **Work Run** | por execução | o **estado** do trabalho | *"isso é 'em que ponto estamos'?"* |

**A regra que fecha:**

> **Corredor é procedimento. Conduta é comportamento. Carta é conteúdo.
> Atlas é observação. Canal é endereço. Work Run é estado.**
>
> **Se você está em dúvida em qual criar, é porque está tentando guardar ESTADO
> dentro de PROCEDIMENTO. É esse o erro, e é o erro que o `corridor_templates`
> cometeu.**

---

# PARTE 2 · Os dois corredores — a resposta que não é A, nem B, nem C

## 2.1 A pergunta está mal formulada

Ele perguntou: *"qual dos dois é o corredor de verdade?"* — como se fossem dois
desenhos concorrentes esperando um juiz.

**FATO: são duas GERAÇÕES do mesmo desenho, com um mês de distância.**

```
12/06/2026   corridor_templates      SPEC-005/006    motor em TypeScript
                                                     mvp_mode: "dry_run_hitl"
                                                     ↓
             ── 297 atendimentos humanos reais foram minerados ──
                                                     ↓
   /07/2026   corridor_playbooks.py   SPEC-017 P4     motor em Python
                                                     executa de verdade
20/07/2026   d88ac70                  o motor TS órfão é removido
```

## 2.2 A prova de que não foi decisão de arquitetura — é a mensagem do commit

📊 Verifiquei `git show d88ac70`. A mensagem, literal:

> *"Prova por **fecho de órfãos** (grafo de imports `@/lib/attendance` a partir
> de `app/ components/ lib/ hooks/`): **30 módulos inalcançáveis de qualquer
> superfície viva**; contra-prova por varredura do repo inteiro só achou os
> próprios testes do MVP."*

**Aquele motor não foi desligado. Ele já estava morto, e alguém provou e
enterrou.** Não havia nenhum caminho de código que chegasse nele a partir de
qualquer tela.

**E mais:** o motor apagado era **TypeScript, dentro do Next.js** — ou seja, um
**segundo runtime de atendimento em paralelo ao backend Python.** O CLAUDE.md §5
proíbe exatamente isso. **Apagá-lo foi a consolidação que a regra manda fazer,
não uma perda.**

## 2.3 O que a tabela realmente é

📊 `corridor_templates` tem **2 linhas** e **2 leitores em todo o repositório**:
um teste e `lib/admin/tenant-corridor-store.ts`. Zero leitores em Python.

📊 Dentro dela: `mvp_mode: "dry_run_hitl"`, `requires_action_engine: true`,
`requires_dispatch_packet: true`, `status_operacional: "ready_for_dry_run"`, e
guardrails escritos **em inglês, em prosa**, do tipo *"Never confirm coverage
without policy evidence."*

> **Ela não é um motor desligado. É um DOCUMENTO DE REQUISITOS que alguém
> escreveu em formato de tabela.** Guardrail em prosa inglesa não executa; é
> especificação. Por isso `graveyard.dispatch_packets` tem 7 linhas e **zero
> enviadas**: aquele desenho **nunca teve intenção de enviar** — `dry_run_hitl`
> está escrito no próprio registro.

## 2.4 O que o playbook Python JÁ TEM — e ele disse que não tinha

**Aqui está o erro material da auditoria dele.** Ele escreveu que aposentar a
tabela *"perde os guardrails declarativos"*. 📊 Fui ao arquivo:

```python
corridor_playbooks.py:146
  "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato",
                     "problema_descricao", "periodo_preferido",
                     "risco_confirmado_sem_fumaca"]      ← o guardrail elétrico

:200  "handoff_triggers": [r"sinistro", r"n[ãa]o localizamos",
                           r"cpf.*inv[áa]lido", ...]
:201  "unknown_step_policy": "pause_and_handoff"   ← nunca responde às cegas
:170  "finalize_anchors"                           ← o freio
:803  _REGISTRY = {f"{playbook_id}@v{version}": p} ← versionado
:1198 missing_slots_for_subservice()               ← e é VERIFICADO
```

**O playbook tem slots obrigatórios, guardrails, fail-safe e versão.** Não é uma
"camada de transporte" burra — é o corredor, com governança, já executando.

**E o guardrail que ele citou como o mais impressionante da tabela** — *"se há
faísca, fumaça, cheiro de queimado, pare o fluxo"* — 📊 **existe em três lugares
no caminho vivo:**

```
corridor_playbooks.py:146      slot obrigatório risco_confirmado_sem_fumaca
insurer_dispatch_tool.py:39    o tool RECUSA acionar sem ele
prompts.py:126                 e a instrução ao modelo, com "desliga o disjuntor"
```

## 2.5 Então o que se perdeu de verdade? Três coisas — e nenhuma é "o corredor"

📊 Comparei campo a campo. A tabela tem exatamente três coisas que o caminho
vivo não tem:

| O que a tabela tem | Onde isso deve morar — e NÃO é numa tabela de corredor |
|---|---|
| **`golden_tests`** — 10 frases reais de segurado com comportamento esperado (*"Está saindo faísca da tomada"* → handoff humano) | **viram testes automáticos.** É ativo de teste, não de runtime. Hoje estão presos numa coluna que ninguém lê. **Isto é a maior perda, e é barata de recuperar.** |
| **`policy_evidence_status`** — o enum que exige provar a apólice antes de acionar | **é o Bloco A da 063 + a InfoCap.** É requisito de segurança, e é literalmente a causa do incidente de 10/07 (*"placa e telefone inventados foram parar na seguradora"*) |
| **`phases`** — a máquina de 12 estados | **é WORK RUN (SPEC-055)**, não corredor. Ver Parte 3. |

> **A conclusão que destrava:** não existe decisão A/B/C. Existe uma migração
> que já aconteceu, com **três itens de bagagem que ficaram para trás.** O
> trabalho é buscar os três e apagar a mala.

## 2.6 E o canon já disse isso três vezes

```
1. GLOSSARIO ................ aponta para corridor_playbooks.py
                              (ele mesmo registrou isso)
2. SPEC-063 §F.1 ............ "o código é a autoridade"
                              (ele mesmo citou, na PARTE B §4 do Bloco 0)
3. CLAUDE.md §5 ............. "consolidar e migrar antes de duplicar"
                              o motor TS era a duplicata
```

**Ele tinha as três informações e não as cruzou.** Não é alucinação — é uma
síntese que não fechou. **CLAUDE.md §10(3) exige parar em conflito canônico;
aqui não há conflito, há concordância em três documentos.**

---

# PARTE 3 · As fases — por que ressuscitar as 12 seria o erro

## 3.1 Ele está certo: há três respostas e elas não conversam

📊 Reverifiquei as três. Todas confirmadas:

```
12 fases em corridor_templates.phases ...... 0 leitores, em qualquer linguagem
 6 etapas em prosa no prompt ............... instrução, não estado
 7 estados de acionamento .................. REAIS, e só no Redis
```

## 3.2 Mas a conclusão certa é o contrário da dele

**A fase não pertence ao corredor.**

O corredor responde *"como se aciona a Allianz para eletricista"*. Isso é
**verdade global e estável** — vale para toda corretora, e só muda quando a
Allianz muda a URA.

A fase responde *"em que ponto está o atendimento do João"*. Isso é **estado de
uma execução**, muda a cada mensagem, e é **por definição** o que o
**Work Run** existe para guardar.

> **Guardar fase dentro de corredor é o mesmo erro que a SPEC-064 acabou de
> desfazer** — lá era "Auxiliar é Rotina". Aqui é "Corredor é Estado".
> **Auxiliar TEM Rotina. Corredor TEM fases DECLARADAS; quem GUARDA a fase é o
> Work Run.**

## 3.3 E a violação real, que ele achou e classificou errado

📊 Confirmei duas coisas:

```
dispatch_router.py:61   f"dispatch:active:{company_id}:{digits}"   Redis, TTL 6h
grep "work_run" insurer_dispatch_service.py  →  ZERO
```

**O acionamento é a única máquina de estados real do produto, e ela não passa
pelo Work Run.** Isso viola CLAUDE.md §6 (Supabase é a verdade durável) **e**
a SPEC-055 (execução universal).

**A correção não é "ressuscitar `corridor_templates`". É `dispatch` virar Work
Run.** O motor já existe, é canônico, tem lease, checkpoint e HITL. Criar uma
tabela de estado de corredor ao lado dele seria **motor paralelo — CLAUDE.md §5.**

---

# PARTE 4 · As doze respostas

### 1 · Qual dos dois corredores é o de verdade?

**`corridor_playbooks.py`.** Sem ambiguidade, e por três autoridades
concordantes (§2.6). A tabela é a geração anterior, em formato de requisito.

**Intenção para a tabela:** extrair os `golden_tests` para testes, registrar
`policy_evidence_status` como requisito do Bloco A, e **aposentar a tabela e a
tela que a lê** — depois, nunca antes, dos dois primeiros passos.

### 2 · Por que o motor da tabela foi apagado?

**Limpeza de código órfão, com prova de alcançabilidade** (mensagem do commit,
§2.2). Não foi decisão de arquitetura, e **não foi abandono de um desenho bom** —
o desenho bom migrou para Python entre 12/06 e 20/07. O que ficou para trás
foram os três itens da §2.5.

**Não estava errado. Estava em duplicidade, no lugar errado (frontend), e
inalcançável.**

### 3 · A tela que diz "o atendente já aciona por eles" é bug conhecido?

**É dívida assumida que virou mentira quando o motor saiu — e ninguém percebeu.**

FATO: até 20/07 a frase era *quase* verdadeira (havia um motor que lia a tabela;
ele nunca despachou, mas existia). Depois de 20/07 ela é **falsa sem atenuante**.

**Não é bug de código — é texto que envelheceu junto com uma remoção.** Conserto
correto: a tela para de prometer acionamento e passa a mostrar o que é verdade —
**quais corredores existem no código para aquela seguradora.**

### 4 · Por que os 4 agentes de atendimento estão desligados?

**Decisão consciente, sua, e ainda válida.** Suas palavras, nesta ordem:

```
"PRECISAMOS DEIXAR TUDO DESLIGADO AINDA ESSA PARTE DE COBRANÇA."
"NADA SERÁ COLOCADO PARA ATENDER CLIENTES/SEGURADOS ANTES QUE
 ESTIVER 100% PRONTO O RAG"
```

**É gate de go-live, e é o motivo de a SPEC-063 existir.** O que precisa
acontecer para ligar o primeiro está escrito: **o Gate do Bloco 1.**

⚠️ **E uma correção à auditoria dele:** ele escreveu que a Resulta tem
integração de atendimento **ativa**, como agravante do P0. 📊 Medi:

```
Resulta · evolution-go · attendance · is_active=TRUE
                                    · channel_status='disconnected'
                                    · last_seen_at = 22/07
```

**`is_active=true` e `channel_status='disconnected'`.** O P0 é real e tem de ser
consertado — **mas nada está fluindo por ele.** A urgência é de *antes de
religar*, não de *agora*.

### 5 · Por que o Atlas parou em 29/07?

**Não parou. Você desconectou os WhatsApps.** 📊 A prova é que **tudo** parou no
mesmo minuto:

```
observed_events .......... 29/07 18:48:58
observed_sessions ........ 29/07 18:44:22
attendance_transcripts ... 29/07 18:49:03
attendance_sessions ...... 29/07 18:44:42
```

Não é o Atlas — é **a entrada inteira de WhatsApp.** E bate com suas próprias
palavras de 30/07: *"VOU PODER RECONECTAR OS WHATSAPPS SO AMANHÃ."*

> **Mas há um defeito real embaixo, e é grave:** 📊 `channel_status` ainda diz
> **`connected`** nas duas integrações, quatro dias depois. **Nada corrige.**
> Não existe heartbeat.
>
> **É a MESMA classe do `work_run` em `queued` sem lease que ele achou na
> auditoria de entrada:** o sistema registra um estado que já não é verdade e
> nenhum vigia o desmente. **Deve virar um item só, com um teste só.**

### 6 · Os valores das variáveis em produção

**Ele já mediu uma delas e não percebeu que tinha.** Do próprio Bloco 0 dele:

```
📊 ATTENDANT_INBOUND_ALLOWLIST = 5547988087463    ← preenchida em produção
```

Os **defaults do código** — que valem se o EasyPanel não definir — 📊 medidos por
mim agora:

| Variável | Default no código | Onde |
|---|---|---|
| `INSURER_DISPATCH_LIVE` | **OFF** (dry-run) | `insurer_dispatch_service.py:8` |
| `DISPATCH_FINALIZE_MODE` | **`test`** | `:61` |
| `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` | **vazio** | `:64` |
| `CARTOGRAPHER_MODE` | **`0`** | `admin_spec034.py:200` |
| `WHATSAPP_WEBHOOK_AUTH_MODE` | **`disabled`** ⚠️ | `config.py:80` |
| `CONTEXT_ASSEMBLY_MODE` | **`shadow`** | `context_assembly.py:71` |
| `DESTILADOR_TETO_POR_RODADA` | **`0`** (destilação parada) | `attendance_distiller.py:65` |

**Os defaults são todos seguros — exceto um.** `WHATSAPP_WEBHOOK_AUTH_MODE`
nasce `disabled`, e essa é a porta legada que resolve tenant pelo corpo. **É P0
e está no Bloco H.**

> 🧑 **O que só você pode responder:** quais destas o EasyPanel sobrescreve.
> **Enquanto não souber, o Bloco 1 deve tratar todas como se estivessem
> LIGADAS** — é a suposição segura.

### 7 · Algum corredor já acionou ponta a ponta?

**Não. Nenhum, nunca.** 📊 Três provas independentes:

```
graveyard.dispatch_packets ...... 7 · ZERO enviados
conexões InfoCap com last_used_at  0
DISPATCH_FINALIZE_MODE default .. "test" (cancela antes de abrir)
```

**As cicatrizes que ele citou são de TESTE, não de produção:**
*"teste Allianz 12/07: '1' fixo pegou o carro ERRADO"*. O incidente de 10/07
(*"placa e telefone inventados foram parar na seguradora"*) foi **mensagem
enviada**, não chamado aberto. **Nenhum serviço foi acionado para nenhum
segurado real, em nenhuma seguradora.**

### 8 · As fases do atendimento: decisão ou peça faltando?

**Peça faltando — e a resposta certa está na Parte 3.** Não foi decisão de
"deixar o modelo conduzir"; foi consequência de o motor de estado ter ficado no
TypeScript que morreu, e o Python nunca ter ganhado o equivalente.

**Havia plano de persistir a ficha?** Sim: é literalmente
`phases` + `required_slots` em `corridor_templates`. **Mas o lugar certo é o
Work Run (SPEC-055), não o corredor.**

⚠️ **E o sintoma dele está certo e é sério:** a tool obriga o modelo a
re-declarar 15+ campos a cada chamada, e a memória é a janela de 60 mensagens.
**O código registra que já quebrou** (o agente repediu o CPF do mesmo cliente).
**Isso é dado real perdido, não elegância.**

### 9 · Os 16 playbooks de conduta: SPEC-063 Bloco G, ou houve motivo?

**Bloco G esperando execução. Não houve motivo para não conectar.**

📊 Reverifiquei: `grep conduct_playbook backend/app/agents/graph.py` → **zero**.
Os 5 leitores são o juiz, o otimizador, o destilador e duas telas de admin.

**Chegou a existir teste de que conectá-los melhora?** **Não.** E é por isso
que o Bloco G tem de nascer com **portão anti-regressão** — o `playbook_gate`
já existe e é o juiz certo. **Conectar sem medir seria repetir o erro de
publicar número sem marca.**

### 10 · As duas migrations que não existem no repositório

**São minhas. Eu as apliquei e não commitei os arquivos. É violação do
CLAUDE.md §8 e a responsabilidade é minha.**

📊 Confirmado: `20260728_02_redestilar_sessoes_que_foram_cortadas` e
`20260728_04_remover_observacao_de_teste_amandus` estão aplicadas; os arquivos
`_01` e `_03` estão no repositório, `_02` e `_04` não.

**O que fizeram, da minha lembrança direta:**

```
_02  marcou sessões cujo texto tinha sido cortado pela máscara antiga
     para voltarem à fila de destilação. NÃO apagou carta — mudou status
     para reprocessamento.
_04  removeu as observações de TESTE da Amandus da base de observação
     (eram minhas, de validação do Atlas — não eram dado de cliente).
```

> **INFERÊNCIA, não FATO:** não tenho o SQL literal. **RECOMENDAÇÃO ao novo
> líder:** não tente reconstruí-las. Registre as duas em
> `MIGRATIONS-AUTHORITY.md` como *"aplicadas sem arquivo, conteúdo declarado por
> memória, não reproduzir"* — que é exatamente o que aquele documento existe para
> catalogar (já há 9 versões nessa situação).

### 11 · O grupo de suporte compartilhado

**Nada mais depende dele.** 📊 O único leitor de
`companies.acionamento_profile.suporte_humano_whatsapp` é o caminho de handoff.

⚠️ **Mas atenção a uma armadilha que ele não viu:** existem **duas** tabelas de
destino, e elas não conversam:

```
human_support_destinations ..... 2 linhas, SÓ Amandus (1 inativa duplicada)
companies.acionamento_profile ... Resulta e AutoFleet, MESMO grupo
```

**Apagar o grupo sem unificar as duas deixa Resulta e AutoFleet sem destino
nenhum** — e, com o defeito do §3.2 da auditoria dele, o segurado ainda ouviria
*"um atendente foi solicitado"*. **A ordem obrigatória é: unificar primeiro,
apagar depois.**

### 12 · O que eu faria diferente, e o erro que o próximo vai cometer

**O bloco que eu faria:** o **Work Run do atendimento** — a ficha persistida.
Não é o mais urgente (o Bloco 1 é), mas é o que **desbloqueia todo o resto**:
sem estado, conduta não tem onde se apoiar, corredor não tem onde marcar fase, e
"resolvido" continua sendo um cronômetro de 48h.

**O erro que o próximo líder vai cometer — e ele já está a meio caminho dele:**

> **Confundir "entender tudo" com "consertar tudo".**
>
> A auditoria dele mapeou o atendimento inteiro, incluindo peças que a SPEC-063
> nunca prometeu tocar. Aí a lista de defeitos ficou tão grande que **parar
> pareceu mais responsável do que avançar.** Não é.
>
> **Os cinco P0 dele não dependem de nenhuma resposta desta página.** Eles
> impedem incidente e podem sair hoje. **A dúvida arquitetural sobre corredores
> não bloqueia um único deles** — e ele mesmo provou isso no Bloco 0, quando
> escreveu *"Bloco 1: nenhuma dependência externa"*.

---

# PARTE 5 · A decisão que eu tomaria, e por quê

**Não é A, B nem C. É esta, e ela cabe dentro da SPEC-063 sem SPEC nova:**

```
┌─ AGORA, sem esperar nada ──────────────────────────────────────┐
│  BLOCO 1 inteiro, como ele mesmo desenhou no Bloco 0:          │
│  A · B · H · D · P                                             │
│  + os 3 acréscimos dele (falha não mente · company_id · CPF    │
│    na tool)                                                     │
│  + o heartbeat: channel_status que mente vira alarme           │
│    (mesma correção do work_run sem lease)                       │
└────────────────────────────────────────────────────────────────┘

┌─ NA MESMA LEVA, como resgate — não como decisão ───────────────┐
│  os 10 golden_tests viram testes automáticos de verdade         │
│  policy_evidence_status entra como requisito do Bloco A         │
│  a tela para de prometer acionamento                            │
│  corridor_templates é APOSENTADA — depois dos dois acima        │
└────────────────────────────────────────────────────────────────┘

┌─ BLOCO 2, depois do gate ──────────────────────────────────────┐
│  C · governador (ESTENDE platform_outbound)                     │
│  E · cobrança conversa                                          │
│  G · conduta chega ao turno, com portão anti-regressão          │
│  F · Youse + provar os 10 em modo teste                         │
└────────────────────────────────────────────────────────────────┘

┌─ SPEC-070, futura — NÃO É DESTA ───────────────────────────────┐
│  a ficha do atendimento como WORK RUN                           │
│  o acionamento sai do Redis e vira Work Run                     │
│  "resolvido" deixa de ser cronômetro                            │
└────────────────────────────────────────────────────────────────┘
```

**Por que a ficha vai para uma SPEC futura e não para esta:** ela é a peça mais
cara e a única que exige desenho novo. **Enfiá-la na 063 transforma uma SPEC de
"parar de vazar" numa SPEC de "reconstruir o atendimento" — e adia por semanas
os cinco P0 que impedem incidente.** O CLAUDE.md §11 exige registro, não
execução silenciosa: ela vai para `PENDENCIAS.md` com destravamento escrito.

---

# PARTE 6 · Onde a auditoria dele erra — a lista completa

**Reverifiquei 14 afirmações materiais. 14 batem nos fatos.** Os erros são de
leitura, e são cinco:

| # | O que ele afirmou | O que é |
|---|---|---|
| **1** | *"aposentar a tabela perde os guardrails declarativos"* | 📊 o playbook Python **tem** slots obrigatórios, handoff triggers, fail-safe e versão — e o guardrail elétrico existe em **3** lugares vivos (§2.4) |
| **2** | *"a Resulta tem integração de atendimento **ativa**"* | 📊 `is_active=true` **e `channel_status='disconnected'`** desde 22/07. O P0 é real; a iminência não |
| **3** | *"aprovação humana no envio NÃO EXISTE"* — como defeito | 📊 é **decisão sua de 11/07**, escrita no código: o freio de finalização substituiu o HITL por corredor. **O gancho `finalize_approved` existe.** ⚠️ mas a decisão **não está em `FOUNDER-DECISIONS.md`** — e é por isso que ele leu como defeito |
| **4** | *"por que o Atlas parou?" — a pergunta mais urgente* | 📊 você desconectou os WhatsApps. **Tudo** parou no mesmo minuto (§ resposta 5). O defeito real é outro: `connected` mentindo sem heartbeat |
| **5** | a decisão **A/B/C** | não existe decisão a tomar; existe migração já feita com 3 itens de bagagem (§2.5). **Ele tinha as 3 autoridades e não as cruzou** |

**E dois números pequenos, sem consequência:** `observed_events` são 17.488 (ele
disse 17.490) e `briefing_publications` já são 26. Ambos envelheceram em dias.

---

# PARTE 7 · O que dizer a ele, em seis linhas

```
1. o corredor é o corridor_playbooks.py. Três autoridades concordam.
   Não há A/B/C. Há três itens a resgatar da tabela e depois aposentá-la.

2. a fase é do Work Run, não do corredor. Guardar estado dentro de
   procedimento é o mesmo erro que a 064 acabou de desfazer.

3. o Atlas não quebrou — o Founder desconectou. O defeito é o
   channel_status que mente. Mesma correção do work_run sem lease.

4. aprovação humana não é defeito: é decisão do Founder de 11/07.
   Registre-a em FOUNDER-DECISIONS.md, que é onde faltava.

5. o Bloco 1 não depende de nada disto. Você provou isso no seu
   próprio Bloco 0. Execute.

6. a ficha do atendimento é SPEC-070, e vai para PENDENCIAS.md hoje.
   Não é desta.
```

---

*Verificação somente leitura. Nenhum dado alterado, nenhuma migration aplicada,
nenhuma credencial exibida, nenhum motor paralelo criado.*
