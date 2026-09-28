# SPEC-120 — Os dezesseis corredores atendem sozinhos

> **A regra que governa esta SPEC inteira, nas palavras do Founder:**
> *"Quanto mais tipos de atendimento conseguirmos atender sem travar, sem o agente errar e sem
> precisar de um humano, mais valiosos seremos. Se toda hora travar, mais vamos irritar as
> corretoras e menos valor teremos."*
>
> ⛔ **Chamar humano é o último recurso, nunca o primeiro.** Mas o agente **nunca** pode travar
> sem chamar ninguém.

## 0. O EXECUTION CARD

```
OUTCOME ........  os 16 corredores que TÊM conversa gravada passam a atender de ponta a ponta
                  sem humano — e o de 24 sobe para o máximo que a evidência permitir

RISCO ..........  9  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE a resposta vai à SEGURADORA 3 ·
                  FREQUÊNCIA 3 — são as rotas de maior volume da Resulta)
SUPERFÍCIE .....  2  (10 corredores com tela órfã, 4 playbooks residenciais, 3 montadores de
                  dossiê — todos nomeados e medidos)
PISO APLICADO ..  §3.2 — toda resposta nova SAI para a seguradora → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5 xhigh · juiz ‖ red team cegos · 1 conserto

O FIO ..........  §2
PARALELISMO ....  F1 ‖ F2 ‖ F4 (arquivos disjuntos) → F3 (depende de F1) → F5 (mede tudo)
UNIDADES .......  5 fatias, §5
COESÃO .........  as respostas das telas e a política da tela desconhecida são o mesmo domínio
TIME ...........  builders frescos, dono único por arquivo
REFERÊNCIA .....  interna: as 67 respostas HUMANAS achadas no banco (§1) ·
                  externa: CLAUDE.md §9.5 (a constante que decide precisa dizer por quê)
GATES ..........  §6
O ELO ..........  a afirmação-título é "as telas sem resposta já FORAM respondidas, e a resposta
                  está no banco". 📊 Medido: 67 de 86. §1 mede A, mede B e mede que B chega em A.
FAIXA DE RELÓGIO  💭 sem teto declarado pelo Founder. Tetos de contexto: 250 turnos por builder.
ORÇAMENTO ......  💭 sem chamada de modelo prevista; se houver, declarar.
```

---

## 1. O ELO — a descoberta que justifica esta SPEC

📊 **Medido em 28/09/2026** (`scripts/` + `regua_motor.eventos_observados`, casando a sessão pelo
prefixo de 8 caracteres e o carimbo de tempo):

```
telas ORFAS nos 16 corredores ............... 86
  com a RESPOSTA HUMANA gravada no banco .... 67   <- as atendentes da corretora responderam
  a conversa TERMINOU naquela tela ...........  1
  sem par no banco ........................... 18
```

🔴 **A resposta que falta não precisa ser inventada: ela foi dada por uma pessoa, na conversa
real, e está guardada.** O que esta SPEC faz é ler essa resposta, decidir com o Founder se ela é
**constante segura** ou **vem do caso**, e escrever o passo.

⚠️ **E a ressalva que impede o erro:** uma resposta humana é evidência FORTE, não prova. *"Não"*
para *"o veículo é blindado?"* estava certo porque aquele carro não era blindado. Por isso cada
resposta abaixo foi decidida pelo Founder, uma a uma, e carrega o porquê.

---

## 2. O FIO

```
A tela sem resposta faz o corredor parar.
  -> parar chama humano (ou, no residencial, chama humano SEM NEM TENTAR)
     -> a corretora recebe trabalho que o sistema deveria ter feito
        -> o sistema vale menos.
Logo: escrever a resposta certa em cada tela órfã, e fazer o residencial TENTAR,
é o que converte volume em valor.
```

---

## 3. AS DECISÕES DO FOUNDER — cada uma é lei nesta SPEC

| # | a tela | a decisão | por quê (palavras dele) |
|---|---|---|---|
| D1 | *"O veículo é blindado?"* | **constante: Não** | *"não vai mudar o guincho por causa disso. Não precisa perguntar."* |
| D2 | *"garagem subsolo ou acima do nível da rua?"* | 🔴 **PERGUNTAR ao segurado** | *"precisa perguntar onde está o carro. Esse depende do caso."* |
| D3 | *"O câmbio está travado?"* | **constante: Não** | *"sempre colocar não"* |
| D4 | *"O veículo está desatrelado?"* | **constante: Sim** | *"deve usar a probabilidade maior"* — desatrelado = não está rebocando nada, que é o caso normal |
| D5 | *"as rodas estão livres?"* | **constante: Sim** | mesma regra da D4; *"não podemos chamar humano para isso"* |
| D6 | *"Possui animal de estimação?"* | **constante: Não** | *"pode deixar não como padrão. Não precisa perguntar."* |
| D7 | datas de agendamento | **a PRIMEIRA disponível** | *"pode ser a primeira data disponível"* |
| D8 | período (manhã/tarde) | 🔴 **PERGUNTAR ao segurado** | *"horário de preferência precisa ser perguntado sim"* |
| D9 | táxi além do guincho (Porto) | 🔴 **PERGUNTAR ao segurado** | *"pode perguntar então. Mas isso precisa ser para a Porto Seguro."* |
| D10 | Azul *"posso te ligar?"* | **constante: 1 — Sim** | o telefone é o do segurado, não o da atendente |
| D11 | Bradesco *"impedido de rodar?"* | **constante: Sim** | *"senão não tinha chamado o guincho"* |
| D12 | HDI residencial: corretor ou segurado | **SEGURADO** | decisão delegada a mim; entrar como segurado é o caminho que o corredor já conhece |
| D13 | 🔴 *"quantos amperes tem a bateria?"* | **tabela por porte, e o padrão é 60 Ah** | §3.1 |
| D14 | 🔴 os 4 playbooks **residenciais** | **param de ir direto ao humano** | *"quero que tente fazer o atendimento normalmente, de ponta a ponta… Allianz residencial é o maior volume da Resulta"* |

### 3.1 🔴 A REGRA DOS AMPERES — e ela vale para QUALQUER seguradora

> *"Não podemos chamar suporte humano nessa pergunta em nenhuma seguradora. Precisamos passar
> dessa tela… ela não vai mudar muita coisa pro prestador. Não podemos perder a chance de fazer
> esse atendimento ponta a ponta por causa disso."*

📊 A distribuição que o Founder forneceu:

| amperagem | % da frota | perfil |
|---|---|---|
| **60 Ah** | ~50–55% | **o padrão do mercado** — 1.4, 1.6, 2.0 e compactos modernos |
| 45–50 Ah | ~25–30% | populares e compactos 1.0 |
| 70–75 Ah | ~15% | SUVs, sedãs médios, start-stop |
| 80+ Ah | ~5% | caminhonetes e SUVs grandes a diesel |

**A regra, em ordem:**
1. Se o veículo do caso identifica o porte com clareza → a faixa da tabela.
2. 🔴 **Em QUALQUER dúvida → 60 Ah.**
3. ⛔ **NUNCA travar. NUNCA chamar humano nesta tela.** Escrita, múltipla escolha ou número: o
   agente responde.

---

## 4. O QUE ESTA SPEC **NÃO** FAZ

- **Não** cria o corredor de `carro_reserva` (126 telas, 13 pedidos, zero passos). O Founder
  concordou em deixá-lo depois: os 16 já têm playbook e precisam de remendo; carro reserva
  precisa do playbook inteiro. **Fica registrado e organizado**, como ele pediu.
- **Não** resolve as 31 rotas sem conversa nenhuma — essas dependem de acionamento real.
- **Não** promete que os 6 "sem desfecho" fecham: eles dependem de **um acionamento que chegue ao
  protocolo**, e isso é do Founder.

---

## 5. AS FATIAS

### F1 · AS RESPOSTAS QUE FALTAM — as 14 decisões, nas 10 rotas
**Arquivos:** `backend/app/services/corridor_playbooks.py` + testes novos.
Escrever o passo de cada tela órfã, aplicando D1–D12. 🔴 Toda constante que escolhe entre
**alternativas de conteúdo** leva `constante_justificada` **nomeando o rótulo daquela tela**
(a regra que a SPEC-119 criou e que fica vermelha se a justificativa mentir).
🔴 As que são **do caso** (D2, D8, D9) viram **pergunta ao segurado ANTES de entrar na URA** —
não no meio, para não deixar a seguradora esperando.

### F2 · O RESIDENCIAL PARA DE DESISTIR
**Arquivos:** `corridor_playbooks.py` (os 4 playbooks residenciais).
`pause_and_handoff` → `adaptive_then_handoff` em allianz, hdi, porto e yelum residencial.
⚠️ **Com rede:** a tela que DECIDE (escolher serviço, aceitar custo) continua indo a uma pessoa —
essa trava é da SPEC-119 e não se afrouxa. O que muda é a tela que apenas CONDUZ.
🔴 **Linha de controle obrigatória:** uma tela de escolha de ramo continua indo ao humano.

### F3 · A TELA QUE NÃO PODE TRAVAR — amperes e os repiques
**Arquivos:** `corridor_playbooks.py`, `insurer_dispatch_service.py` + testes.
A tabela de amperes (§3.1) com o padrão 60 Ah; o repique *"informe somente números"*; o reenvio
de placa/CPF quando a seguradora não acha. 🔴 **Guarda que prove que o agente responde mesmo sem
saber** — o teste tem de falhar se ele travar.

### F4 · O DOSSIÊ E O GRUPO
**Arquivos:** `app/agents/tools/human_handoff.py`, `app/tasks/handoff_watchdog.py`,
`app/services/os_modelos_do_grupo.py`.
📊 **Medido antes de escrever:** existem **3** montadores (`_montar_dossie`,
`_dossie_de_pos_acionamento`, `build_handoff_dossier`). O do agente é o novo (SPEC-071 +
EXTRA-001.3) e **já segue** o rascunho do Founder; o do corredor **está completo** quando os
slots estão preenchidos (conferido campo a campo).
🔴 **O que de fato falha, e é o que esta fatia conserta:**
1. o **lembrete do vigia** (o que o Founder viu) sai sem seguradora, sem serviço e com
   *"motivo não registrado"* — é a mensagem mais pobre e a que ele mais vê;
2. o **momento** não aparece: o Founder quer saber se travou na **conversa inicial**, no
   **acionamento** ou no **pós-acionamento**;
3. *"Está enviando msg demais"* — o teto de lembretes precisa ser medido e declarado;
4. o **relatório das 19h** precisa levar **nome, protocolo, serviço, seguradora e WhatsApp
   clicável**, que é o que ele pediu por escrito.

### F5 · A MEDIÇÃO — e a página
**Arquivos:** os scripts de medição, `docs/canon/reports/**`, `painel-do-founder/**`.
Rodar o simulador e a régua depois de tudo, regerar a aba, e dizer **de quanto para quanto** foi.

---

## 6. OS GATES

```
G1  🔴 as 10 rotas com tela órfã ficam com ZERO órfãs funcionais
G2  🔴 os 4 residenciais TENTAM — e a tela que DECIDE continua indo a uma pessoa (controle)
G3  🔴 a tela dos amperes NUNCA trava: guarda vermelho se o agente pausar ou chamar humano nela
G4  toda constante nova tem `constante_justificada` NOMEANDO o rótulo da tela real
G5  as OITO respostas erradas de 22/08 continuam vermelhas
G6  mutação de cada guarda novo: vermelho com o defeito reintroduzido
G7  bateria completa em worktree SEPARADO, triada contra o commit base
G8  o dossiê diz o MOMENTO, e o lembrete do vigia leva seguradora + serviço
G9  📊 o simulador mede: de 24 para quanto
```

---

## 7. AS PENDÊNCIAS QUE JÁ NASCEM

| # | o que | de quem |
|---|---|---|
| P-120-01 | `carro_reserva` — corredor novo, 126 telas de material | 🤖 SPEC futura |
| P-120-02 | os 6 corredores "sem desfecho" — um acionamento real cada | 🧑 Founder |
| P-120-03 | as 31 rotas sem conversa nenhuma | 🧑 acionamento dirigido |
| P-120-04 | a pessoa da Porto que assume o atendimento no meio da URA | 🤖 |
