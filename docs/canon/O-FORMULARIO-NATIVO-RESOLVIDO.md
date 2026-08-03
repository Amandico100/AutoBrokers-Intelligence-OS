# O formulário nativo do WhatsApp — resolvido, e como

> **03/08/2026.** O registro completo de como o AutoBrokers passou a **responder
> formulários nativos** dentro do WhatsApp — o que a Meta chama de *Flow* e o
> corretor chama de *"aplicativo dentro da conversa"*.
>
> Este documento existe para que **qualquer pessoa ou sessão possa retomar
> daqui**, com evidência, sem depender de quem estava presente.
>
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## 1. O problema, em uma tela

Quatro seguradoras pararam de fazer perguntas por texto e passaram a **abrir um
formulário** dentro da conversa. 📊 Porto desde 09/2025 (12 vezes) · HDI (6) ·
Azul (4) · Yelum (2).

Quando isso acontece no meio de um acionamento, o corredor **para**. Ele sabe
tudo que o formulário pede, tem os dados na ficha do atendimento — e não
consegue responder. O atendimento morre esperando um humano.

📊 **460 apólices de auto — 26,9% da carteira** estão nessas quatro seguradoras.

---

## 2. Por que era difícil

**A biblioteca sempre soube.** O `whatsmeow`, que roda por baixo do Evolution
GO, lê e escreve esse tipo de mensagem. O próprio Evolution GO **já lia** —
quando um formulário respondido chega, ele extrai `name` e `paramsJSON`.

📊 O que faltava era a porta de **saída**: das **88 rotas** do Evolution GO, 12
são de envio, e **todas as 12 ORIGINAM mensagem**. Nenhuma responde uma.

E a resposta a um formulário não é texto: é um tipo próprio de mensagem
(`interactiveResponseMessage.nativeFlowResponseMessage`), com um envelope, um
token de sessão e os campos preenchidos.

---

## 3. A única evidência que existia

📊 `observed_events`, linha `ed3f9ea3-7e79-475d-a767-627c5c0ce9ca`, 18/07/2026,
família HDI. **Uma pessoa de verdade respondendo um formulário de verdade.**

É **a única**. As outras 22 respostas de formulário do acervo foram gravadas
**vazias** por um defeito no observador — o mesmo que a Fase 0.1 consertou. Esta
sobreviveu por acaso.

O que ela ensinou:

| Campo | Valor | Por que importa |
|---|---|---|
| `name` | `galaxy_message` | é o envelope LEGADO. A Meta documenta `flow` como o atual. **A família HDI usa o legado** |
| `flow_token` | `uuid:551155020700:5547996274743` | **não é um uuid solto**: os dois telefones vão dentro dele. Nunca construir — sempre ecoar |
| chaves de 1º nível | `rb_*`, `ckb_*` | é o dado que a seguradora consome |
| `wa_flow_response_params` | title, flow_id, flow_name, response_message | a moldura |
| `version` | **ausente** | ver §7 |

Guardada, com telefones mascarados, em
[`backend/tests/fixtures/clique_humano_no_formulario_18_07.json`](../../backend/tests/fixtures/clique_humano_no_formulario_18_07.json).

> **A lição que vale além deste caso:** um acervo de **um** não permite conferir
> hipótese. Permite comparar. Foi por isso que tudo aqui teve de ser **medido no
> ar**, e não deduzido por leitura.

---

## 4. O que foi construído

### Patch 0005 — a décima terceira rota

`POST /send/interactiveResponse` no nosso fork do Evolution GO. 329 linhas.

Duas descobertas mudaram o desenho, e as duas teriam custado um ciclo de build:

1. 📊 **Não existe `{instance}` nas rotas do GO.** A instância vem do header
   `apikey`. A rota planejada não existiria.
2. 📊 **`SendMessage` tem uma lista branca de `messageType`**, com
   `default: return invalid messageType`. Sem acrescentar o caso novo nos
   **dois** `switch`, todo envio morreria ali — e o erro não falaria de
   formulário. **Esse era o defeito que passaria por revisão.**

**A camada Go é um cano burro, de propósito.** `paramsJSON` viaja como texto
opaco: validado como JSON e repassado **byte a byte**, nunca re-serializado —
re-serializar reordena chaves e reescreve acentos. O Go não sabe o que é um CEP
nem qual seguradora está do outro lado. Assim, descoberta nova muda o Python,
não a imagem.

### Patch 0006 — o embrulho vira mensurável

A primeira tentativa no ar deu **479**. 📊 O próprio whatsmeow documenta
(`client.go:303`): *"Invalid stanza sent (smax-invalid)"* — recusa do
**envelope**, não do conteúdo.

Rodada 1 mediu os fatores de payload. 📊 Cinco formas, **cinco vezes 479**:
`version`, nós `<biz>`, `body` — nenhum mudou nada.

> **Fator que não muda o resultado não é a causa.** Isso descartou o payload
> inteiro e apontou para a forma.

Sobraram as duas coisas que `/send/button` faz em **todas** as suas variantes e
nós não fazíamos: o embrulho `DocumentWithCaptionMessage` e o `MessageSecret`.
Viraram **bandeiras**, para poderem ser medidas numa única imagem.

---

## 5. 📊 A prova

**03/08/2026**, entre dois números nossos, sem tocar em seguradora nenhuma:

```
controle — como na rodada 1          479   "Invalid stanza sent"
embrulho DocumentWithCaption         200   ACEITO
```

Resposta do servidor:

```
Type:      "InteractiveResponseMessage"
ID:        3EB07C9C74F4A217DE0477
De:        554796274743
Para:      554788087463
```

**A primeira linha era CONTROLE.** Deu 479 igual à rodada anterior — por isso o
mérito é do embrulho e de mais nada. O `MessageSecret` nem chegou a ser testado:
parou antes.

> **Sem uma linha de controle, um acerto se credita ao lugar errado — e se
> constrói em cima de uma causa que não era a causa.**

### A resposta

**`DocumentWithCaptionMessage`.** O mesmo embrulho que os botões usam. Sem ele o
WhatsApp recusa a mensagem inteira: **em silêncio para o cliente, com um número
para nós.**

---

## 6. O que está ligado hoje

```
a rota      /send/interactiveResponse é o PADRÃO. A variável de ambiente
            EVOLUTION_GO_FLOW_REPLY_PATH mudou de papel: era o que LIGAVA,
            virou o que corrige ou DESLIGA ('off' funciona sem deploy)

o embrulho  sempre. Não é estilo — é a diferença entre 200 e 479

a ponte     flow_sender era SEMPRE None vindo de app/api/. Todo formulário
            virava `formulario_pronto_sem_transporte`. Agora tem transporte,
            e falha devolve False (o motor pausa) em vez de exceção (que
            derrubaria o inbound inteiro)

o botão     "Provar envio de formulário" na tela de WhatsApp da corretora.
            Diagnóstico permanente: qualquer corretora confere o próprio
            canal sem depender de quem escreveu o código
```

📊 Imagem `0.7.2-autobrokers.3` · 6 patches aplicam no commit fixado ·
6 testes Go rodam dentro do build · suíte Python **132 verdes**.

---

## 7. O que NÃO está provado — leia antes de assumir

| # | O quê | Por quê importa |
|---|---|---|
| **1** | 💭 **`version`** | A captura **não tem** o campo. Não se sabe se o remetente não mandou ou se nosso observador não leu — as duas explicações cabem. O Go **omite quando ninguém pede**. Ninguém finge saber |
| **2** | 💭 **`response_message`** | A captura tem um campo de ~6 KB com o eco das telas. Não sabemos se a seguradora **exige** ou se é só a bolha bonita. A hipótese razoável é a segunda — mas hipótese razoável já custou caro aqui |
| **3** | 🔴 **O desfecho** | Provamos que a **mensagem sai e o WhatsApp aceita**. **Não** provamos que a seguradora aceita a resposta no meio de um atendimento real. São coisas diferentes |
| **4** | 💭 **`MessageSecret`** | Nunca testado — a bateria parou antes. Pode ser necessário em algum caso que não vimos |

---

## 8. O que falta para chegar a 100%

```
🧑  1. um acionamento REAL com formulário, em modo teste
       abrir conversa com a HDI, andar o menu até o formulário chegar,
       e responder AQUELE — o único teste que fecha o item 3 acima

🤖  2. medir se `response_message` é exigido
       só dá para saber com uma seguradora do outro lado. Se a resposta
       for descartada em silêncio com tudo mais certo, é o suspeito nº 1

🤖  3. o embrulho como padrão no GO, não no Python
       hoje quem garante é o chamador. Um patch 0007 inverteria: o Go
       sempre embrulha, e desembrulhar seria o explícito. Seguro por
       construção em vez de seguro por convenção

🤖  4. `version` decidido por medição, não por omissão

🤖  5. cada família de seguradora com o próprio formulário mapeado
       HDI e Yelum compartilham flow_id 857030507196739. Porto, Azul e
       as demais têm os seus, e nenhum foi capturado ainda
```

---

## 9. Onde está cada coisa

```
infra/evolution-go-autobrokers/patches/0005-send-interactive-response.patch
infra/evolution-go-autobrokers/patches/0006-interactive-response-envelope.patch
infra/evolution-go-autobrokers/VERSION                      0.7.2-autobrokers.3

backend/app/services/whatsapp/providers/evolution_go.py     montar_nfm_reply,
                                                            rota_de_flow_reply,
                                                            send_native_flow_response
backend/app/api/webhook.py                                  a ponte (flow_sender)
backend/app/api/whatsapp_integrations.py                    a bateria de prova
backend/app/services/insurer_dispatch_service.py            quem monta a resposta
backend/app/services/corridor_playbooks.py                  native_flows por família

backend/tests/fixtures/clique_humano_no_formulario_18_07.json   a captura
backend/tests/test_o_formulario_nativo_tem_transporte.py        rota+embrulho+ponte
backend/tests/test_o_acionamento_nao_trava.py                   o motor não trava

app/dashboard/personalizacao/corretora/whatsapp/                o botão da prova
app/api/dashboard/prova-de-formulario/route.ts
```

---

## 10. O método, para a próxima vez

Cinco coisas fizeram a diferença, e nenhuma é sobre WhatsApp:

1. **Separar o que pode estar errado do que precisa de rede.** A montagem virou
   função livre e ganhou testes que rodam dentro do build, sem telefone.
2. **Provar que o guarda pode falhar.** Um dos testes Go verifica que
   `Unmarshal`+`Marshal` de fato altera o texto — senão a comparação byte a byte
   estaria passando por coincidência.
3. **Variar um fator por vez, com linha de controle.** Foi o que separou "não é
   o conteúdo" de "é a forma".
4. **Ler o erro na fonte.** `479` não foi pesquisado no Google: foi lido no
   comentário do whatsmeow que o documenta.
5. **Não pedir segredo a ninguém.** A chave da instância é cifrada e só abre
   dentro do processo. Um teste que exija alguém colar uma chave em algum lugar
   não é teste — é vazamento com hora marcada.
