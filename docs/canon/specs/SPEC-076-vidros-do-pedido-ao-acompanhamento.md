# SPEC-076 — Vidros: do pedido do cliente ao acompanhamento

> **O atendimento inteiro, sem buraco.** Do "quebrou meu vidro" no WhatsApp até
> "o serviço foi feito?" alguns dias depois.
>
> **v1.0** · 16/08/2026 · base `e632171` (SPEC-074 concluída)
> **Dirigida por captura:** esta SPEC não começa a executar antes de os três
> acionamentos reais chegarem.

---

# 0. A frase que resume

A SPEC-074 fez o robô **abrir** o pedido. Ele para em 99% e diz ao segurado
*"falta você escolher a loja"*. A SPEC-076 fecha os 1% que faltam — e as duas
pontas que nunca existiram: **o que o segurado ouve** e **o que acontece depois**.

```
HOJE                                    DEPOIS DA 076
─────────────────────────────────       ─────────────────────────────────
cliente pede no WhatsApp        ✅      cliente pede no WhatsApp        ✅
o robô entra no portal          ✅      o robô entra no portal          ✅
preenche até o questionário     ✅      preenche até o questionário     ✅
o pedido nasce (2 fronteiras)   ✅      o pedido nasce (2 fronteiras)   ✅
escolher loja ou domicílio      ❌      escolher loja ou domicílio      ✅
agendar                         ❌      agendar                         ✅
confirmar / finalizar           ❌      confirmar / finalizar           ✅
avisar o cliente no WhatsApp    🟡      avisar o cliente no WhatsApp    ✅
acompanhar se deu certo         ❌      acompanhar se deu certo         ✅
```

🟡 = existe a frase, nunca foi exercida com um pedido real.

---

# 1. Por que esta SPEC precisa de captura, e não de código

📊 **Fato medido, 16/08/2026:** em 39 acionamentos históricos, **zero** chegaram
ao passo 7. O HAR de 58 MB que alimentou a SPEC-074 cobre o fluxo até o
questionário. Depois disso o repositório tem dois endpoints **declarados e nunca
exercidos**:

```python
EP_FINALIZAR_NAO_MEDIDO       = "/atendimentos/finalizar"
EP_VISTORIA_MOBILE_NAO_MEDIDO = "/atendimentos/vistoriamobile"
```

O sufixo `_NAO_MEDIDO` é literal e está no código. A CLAUDE.md §9.2 e a SPEC-073
§G3 dizem a mesma coisa: **candidato ≠ aprovado**. Implementar a escolha de loja
por dedução seria adivinhar num fluxo que cobra por atendimento e escreve no nome
de um segurado real.

**Portanto:** esta SPEC não tem bloco de implementação executável antes da
captura. O que ela tem, e é o que vale agora, é o **protocolo de captura** da
seção 3.

---

# 2. Onde exatamente o código para hoje

## 2.1 A máquina de estados conhece 8 estados

| Estado | Implementado? |
|---|---|
| `pre_protocolo` | ✅ |
| `protocolo_criado` (fronteira A) | ✅ |
| `atendimento_materializado` (fronteira B) | ✅ |
| `aguardando_escolha_do_segurado` | ✅ **— e é aqui que tudo para** |
| `finalizado` | ⚠️ o estado existe; **nada transita para ele** |
| `cancelado` | ⚠️ fronteira declarada, endpoint conhecido, nunca exercido |
| `abandonado` | ⚠️ idem |
| `desconhecido` (maybe_committed) | ✅ |

## 2.2 As quatro fronteiras materiais

```python
FRONTEIRA_ABRIR        = "criar_atendimento_maxpar"   # ✅ exercida
FRONTEIRA_MATERIALIZAR = "gravar_questionario"        # ✅ exercida
FRONTEIRA_CANCELAR     = "cancelar_atendimento"       # ⚠️ nunca
FRONTEIRA_ABANDONAR    = "abandonar_atendimento"      # ⚠️ nunca
```

Falta uma quinta que nem foi declarada, porque ninguém sabe qual é o endpoint:
**escolher loja / agendar**.

## 2.3 O buraco do acompanhamento é estrutural, não é preguiça

`ler_atendimento()` existe — mas só funciona **dentro da sessão que criou o
pedido**, com o `token_autorizacao` que o `POST /atendimentos` devolveu. Três dias
depois esse token não existe mais.

**Não há nenhum caminho conhecido para perguntar ao portal "e o atendimento
99999999, como está?"** Sem isso, acompanhamento é impossível — não por decisão
de projeto, por falta de informação.

## 2.4 O lado do WhatsApp

O que existe: `format_result` monta a frase e o Vigia detecta job parado. O que
**nunca aconteceu**: um pedido real chegar ao fim e a mensagem sair para um
segurado de verdade. A frase nunca foi lida por ninguém.

---

# 3. O protocolo de captura — o que os três acionamentos precisam trazer

> Esta é a seção operacional. É para ser seguida com o navegador aberto.

## 3.0 Antes de começar — três ajustes que decidem se a captura serve

🔴 **Sem os três, a captura fica inútil e o trabalho é perdido.**

1. **DevTools → Network → marque `Preserve log`.** Sem isso, cada navegação
   **apaga** o que foi capturado antes. É o erro mais comum e só se descobre
   depois.
2. **Exporte como `HAR with content`** (botão de download → *Export HAR
   (with content)*). O HAR "normal" salva só os cabeçalhos; **sem os corpos de
   resposta não dá para saber o que o portal respondeu.**
3. **Não feche a aba entre os passos.** O `token_autorizacao` vive na sessão.

## 3.1 Os três casos precisam ser DIFERENTES

Três capturas iguais valem por uma. O que separa os casos:

| # | Caso | O que ele destrava |
|---|---|---|
| **1** | **Loja** — segurado escolhe uma oficina e agenda | o caminho mais comum; a lista de lojas, o agendamento, a confirmação |
| **2** | **Domicílio** — atendimento na casa/trabalho | outro ramo do passo 7; endereço, janela de horário |
| **3** | **Algo dá errado** — sem cobertura, dado recusado, ou um cancelamento | as telas de recusa e o caminho de cancelar/abandonar |

Se o caso 3 não aparecer naturalmente, **abra um pedido e cancele** — o
cancelamento é um dos endpoints nunca medidos, e conhecê-lo vale muito.

## 3.2 O que salvar, em cada um dos três

### 📁 Rede
- [ ] **HAR completo `with content`**, do login até a última tela
- [ ] Um HAR **por caso**, com nome claro: `CASO1-LOJA.har`, etc.

### 📄 Páginas
- [ ] **HTML salvo** (Ctrl+S → "Página completa") de:
  - a tela de escolha de loja/domicílio
  - a tela de agendamento
  - **a tela final, com o número do atendimento visível**
- [ ] Só o HTML da tela final já ajudaria; as três ajudam muito mais

### 📸 Prints
- [ ] Print de **cada tela do passo 5 em diante**
- [ ] 🔴 **Print da tela final inteira, com o número do atendimento legível** —
      é a peça mais importante de todas
- [ ] Print de **qualquer mensagem, aviso, banner ou modal** que apareça no fim

### ✉️ O que o portal manda para fora
- [ ] O **e-mail** que chega no endereço do solicitante (print ou encaminhar)
- [ ] Qualquer **SMS ou WhatsApp** que o segurado receba direto da Autoglass
- [ ] Se aparecer **link de vistoria**, o link inteiro (ele já existe no código
      como `LinkVistoriaMobile`, mas nunca foi visto funcionando)

### 🕐 Tempos
- [ ] Anotar **que horas** cada acionamento começou e terminou
- [ ] Se algum passo demorar muito, anotar qual

## 3.3 A quarta captura, que não é opcional

🔴 **Volte ao portal 2 a 5 dias depois de cada acionamento** e capture como se
consulta um atendimento já aberto:

- [ ] Onde fica a lista de "meus atendimentos" / consulta
- [ ] **HAR dessa consulta** (é aqui que aparece o endpoint que hoje não existe)
- [ ] Print mostrando o **status** do atendimento (agendado? feito? cancelado?)
- [ ] Se houver histórico ou linha do tempo, print dele

**Por que isso é obrigatório:** sem esta captura, **acompanhamento é impossível**
— não difícil, impossível. Não existe hoje nenhuma forma conhecida de perguntar
ao portal sobre um atendimento depois que a sessão morreu.

## 3.4 O lado do WhatsApp — o que só você tem

O portal é metade. A outra metade é a conversa, e ela não está em HAR nenhum:

- [ ] **Print da conversa inteira** com o segurado, dos três casos
- [ ] O que ele perguntou, e **em que momento ficou ansioso ou repetiu a pergunta**
- [ ] O que **você** respondeu manualmente que o robô deveria ter respondido
- [ ] O que ele perguntou **depois** — no dia seguinte, na semana seguinte

📌 Este último item é o que ensina a desenhar o acompanhamento. A pergunta que o
segurado faz sozinho é a pergunta que o sistema deveria ter respondido antes.

---

# 4. O que cada captura destrava, item por item

| Captura | Destrava | Estado hoje |
|---|---|---|
| HAR passo 7 (loja) | o endpoint de escolha de loja; a quinta fronteira material | ❌ desconhecido |
| HAR passo 7 (domicílio) | o ramo alternativo; que campos mudam | ❌ desconhecido |
| HAR do agendamento | como se envia data/hora; que validações existem | ❌ desconhecido |
| HAR da confirmação final | `POST /atendimentos/finalizar` — hoje `_NAO_MEDIDO` | ❌ declarado, nunca visto |
| Print da tela final | **que número o segurado repete no telefone**; que texto ele lê | 🟡 inferido do HAR |
| HTML da tela final | os rótulos exatos, para o caminho DOM de recurso | ❌ |
| E-mail do portal | se o segurado já é avisado sem a gente | ❌ desconhecido |
| Link de vistoria | se `LinkVistoriaMobile` é usável | ⚠️ campo lido, nunca visto |
| **HAR da consulta dias depois** | **o acompanhamento inteiro** | ❌ **impossível hoje** |
| Caso que dá errado | telas de recusa; cancelar/abandonar | ⚠️ endpoints conhecidos, nunca exercidos |
| Conversa do WhatsApp | o texto certo, o momento certo, a pergunta que falta | 🟡 frase escrita, nunca lida |

---

# 5. Respondendo direto: os três acionamentos resolvem tudo?

**Resolvem o portal — quase 100% — se seguirem o protocolo da seção 3.**

**Não resolvem sozinhos três coisas:**

1. **O acompanhamento.** Precisa da quarta captura (§3.3), dias depois. Sem ela
   não há como consultar um atendimento antigo, e nenhuma quantidade de
   acionamentos novos resolve isso.
2. **Os caminhos de erro.** Três acionamentos que dão certo ensinam o caminho
   feliz. Se nenhum der errado, ficamos sem as telas de recusa — por isso o
   caso 3 deve **provocar** um erro ou terminar em cancelamento.
3. **O WhatsApp.** Não depende do portal. Depende da conversa (§3.4) e de
   decisão de produto: quantas mensagens, quando, e o que fazer quando o
   segurado some.

**E uma quarta que não é captura, é decisão sua:** quando o robô pode **escolher
a loja sozinho**? Se ele escolher, o segurado pode receber o carro numa oficina
que não queria. Se ele nunca escolher, o atendimento nunca fecha sozinho.
Provavelmente a resposta é *"ele oferece as 3 mais próximas e o segurado escolhe
no WhatsApp"* — mas isso é decisão, não medição, e vai para
`FOUNDER-DECISIONS.md`.

---

# 6. O que a SPEC-076 vai construir, quando a captura chegar

## Bloco 1 — A quinta fronteira: escolher loja ou domicílio
Endpoint medido, `FRONTEIRA_ESCOLHER` declarada, guard nomeado, checkpoint antes
do POST. Mesma disciplina das duas fronteiras que já existem.

## Bloco 2 — O agendamento e o fecho
`POST /atendimentos/finalizar` sai de `_NAO_MEDIDO`. O estado `finalizado` passa
a ser alcançável, e a máquina de estados fecha.

## Bloco 3 — A conversa que devolve o resultado
O segurado recebe: o número, o que foi combinado, onde e quando. Em linguagem de
gente, com o número que a **tela** mostra — não o protocolo interno de 16 dígitos.

## Bloco 4 — A escolha da loja pelo WhatsApp
As lojas viram opções na conversa. O segurado responde, e o robô continua de onde
parou. É aqui que o estado `aguardando_escolha_do_segurado` deixa de ser um beco.

## Bloco 5 — O acompanhamento
Uma rotina consulta os atendimentos abertos e avisa quando muda de status. Depende
inteiramente da captura §3.3.

## Bloco 6 — Cancelar e abandonar
As duas fronteiras declaradas e nunca exercidas. Com medição, entram com guard.

---

# 7. Riscos, ditos antes

| Risco | Mitigação |
|---|---|
| Cada acionamento de teste é **pago** | são clientes reais com pedidos reais — não gerar acionamento artificial |
| A captura contém **CPF, placa, nome, telefone** de gente real | os HAR ficam em `docs/intake/`, **nunca** em teste, fixture, RAG ou log. As fixtures são sanitizadas, como as da 074 (📊 0 CPF, 0 CNPJ) |
| Entrar muitas vezes no portal pode **bloquear** | 🔴 [P-188](../PENDENCIAS.md) segue aberta: não há teto por portal/hora. Três acionamentos manuais não preocupam; automatizar sem o teto, sim |
| Implementar por dedução o que não foi medido | proibido. `_NAO_MEDIDO` só sai do nome com HAR na mão |

---

# 8. O que NÃO entra nesta SPEC

- Outros portais — é [SPEC-075](SPEC-075-portal-capability-factory-global-agentes-auxiliares.md)
- O teto de entradas por portal/hora — é 075, e é 🔴
- Ligar `PORTAL_VIDROS_API_FIRST` — depende do canário ([P-190](../PENDENCIAS.md)),
  e o canário **é** o caso 1 desta captura
- Qualquer mudança em cobrança, Atlas ou acervo

---

# 9. Ordem sugerida

```
1. você captura os 3 acionamentos          (§3.1, §3.2)
2. você captura as 3 conversas do WhatsApp (§3.4)
3. eu leio, meço e escrevo o contrato — sem implementar nada ainda
4. blocos 1, 2, 6 (o portal fecha)
5. blocos 3, 4 (a conversa fecha)
6. você volta ao portal dias depois        (§3.3)
7. bloco 5 (o acompanhamento fecha)
```

O passo 6 é o único que **não dá para adiantar**: depende do tempo passar.

---

# 10. Gate

A SPEC-076 está concluída quando **um atendimento de vidro nasce de uma conversa
no WhatsApp, atravessa o portal até o fim, volta ao segurado com o número que a
tela mostra, e é acompanhado até alguém saber se o serviço foi feito** — sem
ninguém abrir o navegador.

E quando cada fronteira material desse caminho tiver: guard nomeado, checkpoint
antes do POST, um teste que **executa** e conta quantas vezes o POST saiu, e uma
mutação que prova que o teste reprova.
