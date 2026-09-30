# As telas que faltam — rota por rota, com as respostas prováveis

> 30/09/2026 · main `84c84c7` · só leitura, nada foi mudado no produto nem no banco.
> 📊 Medido com o motor do produto sobre o acervo mascarado (`backend/tests/corpus/telas_reais/*.jsonl`):
> `python backend/scripts/simular_corredor.py --todas --formato json` (placar) e, rota a rota,
> `replay.replay(rota)` + `simular_corredor.detalhado()` (tela a tela). O placar de hoje é igual ao de
> `SIMULACAO-DOS-CORREDORES.json` (commit `4ccd063`): **31 atendem sozinhas · 4 vão a uma pessoa · 41 falta captura**.
> Única diferença: `yelum/auto/chaveiro` caiu de 3 para **2** telas órfãs depois da SPEC-122.
>
> ⚠️ **O acervo guarda só o que a SEGURADORA escreveu**, não o que a atendente digitou. Onde digo "o que a
> atendente respondeu", é dedução pela tela seguinte, e está marcado assim.
> 💭 **As notas 0–100 são julgamento meu, não medição**: dizem quão provável é que a resposta esteja certa.
> "Origem" diz de onde o dado viria: **caso** (já está no pedido) · **segurado** (perguntar a ele) ·
> **deduzir** (dá para inferir) · **pessoa** (só uma pessoa decide).

## O resumo em uma tabela

| rota | como está | telas sem resposta | o que falta |
|---|---|---:|---|
| `porto/auto/bateria` | responde e fecha em 4 conversas; trava só quando a Porto passa para uma consultora humana | 4 | respostas para a consultora |
| `yelum/auto/guincho` | responde e fecha em 4 conversas; trava só no "acompanhar assistência já aberta" | 2 | 2 passos (dado do caso) |
| `yelum/auto/chaveiro` | chave trancada: trava na pergunta do endereço de destino | 2 | 1 decisão (Sim/Não) |
| `yelum/auto/carro_reserva` | vai a uma pessoa por desenho; 4 telas órfãs depois disso | 4 | analista humano + consulta de status |
| `allianz/residencial/desentupimento` | responde tudo e **nunca chegou ao protocolo** | 0 (+1 parada) | o que o especialista da Allianz faz |
| `allianz/residencial/eletrodomesticos` | responde tudo e **nunca chegou ao protocolo** | 0 (+1 parada) | idem |
| `hdi/residencial/chaveiro` | responde tudo e **nunca chegou ao protocolo** | 0 (+1 parada) | a tela depois da cobertura |
| `porto/residencial/eletrodomesticos` | responde tudo e **nunca chegou ao protocolo** | 0 (+1 parada) | uma conversa que termine |
| `yelum/residencial/eletrodomesticos` | responde tudo; geladeira vai a analista por regra da Yelum | 0 (+1 parada) | o caminho de um item não essencial |
| `hdi/residencial/eletricista` | **sem conversa própria** (as 5 eram fogão) | — | 1 acionamento real |
| `porto/auto/vidros` · `tokio/auto/guincho` · `tokio/auto/carro_reserva` | vão a uma pessoa **por desenho** (a seguradora só dá link) | 0 | nada — é o desenho |
| `yelum/auto/bateria` | ✅ **já atende sozinho** (nota 95) desde a SPEC-121 | 0 | — |

📊 Total: **12 telas órfãs** em 4 rotas + **6 pontos onde a conversa parou antes do protocolo** + **15 telas que o robô
responde "de cabeça"** (o cérebro, sem dado no caso — seção final, em 12 linhas).

---

## 1. `porto/auto/bateria` — responde e fecha; trava quando entra a consultora humana
📊 193 telas, 99 respondidas, **4 órfãs**, protocolo em 4 conversas. As 4 órfãs são todas da mesma conversa (`4830574a`),
num ramo que só existe para **cliente de "atendimento personalizado"**: depois do menu, uma *consultora de relacionamento*
da Porto assume e conversa em texto livre.

| tela (mascarada) | opções | onde | a atendente (deduzido) | respostas prováveis · nota · origem |
|---|---|---|---|---|
| "{NOME} está por aí?" | texto livre | 13 min depois dos amperes | respondeu (a conversa seguiu) | "Sim, estou aqui" · **90** · deduzir |
| "Nós podemos abrir a solicitação; caso o prestador não tenha a bateria ele pode buscar no Centro Automotivo." | texto livre | depois de perguntar os amperes | concordou | "Pode abrir, sim" · **75** · deduzir · "Pode abrir, mas ele vai demorar mais?" · 40 · segurado |
| "Informe por gentileza o endereço" | texto livre | logo depois | deu o endereço | o endereço onde o carro está · **95** · caso |
| "Esse cliente é do Sul e está em São Paulo?" | texto livre | depois do endereço | confirmou | "Sim, a apólice é do Sul e o carro está em SP agora" · **65** · deduzir (endereço da apólice × local) · perguntar ao segurado · 60 |

**Pergunta à Regina:** *"Quando a Porto passa o cliente para a consultora de relacionamento, o que ela sempre pergunta na bateria — e por que ela quer saber se o cliente é de outro estado?"*

## 2. `yelum/auto/guincho` — responde e fecha; trava no "acompanhar"
📊 818 telas, 474 respondidas, **2 órfãs**, protocolo em 4 conversas. As 2 órfãs (`75400aad`) são de quem volta para falar
de uma assistência **já aberta** (pós-acionamento) — a conversa depois vai a um especialista por desenho.

| tela | opções | onde | a atendente (deduzido) | respostas prováveis · nota · origem |
|---|---|---|---|---|
| "Para seguir, informe o número da sua *assistência*, *placa* ou *CPF*." | texto livre | 1ª tela | respondeu (a URA achou a assistência) | o número da assistência aberta · **95** · caso · a placa · 90 · caso · o CPF · 85 · caso |
| "Identifiquei que a assistência {NÚMERO} foi aberta nas últimas 72h. Sobre qual solicitação quer falar?" | GUINCHO · MTA (meio de transporte) | 2ª tela | escolheu GUINCHO | o serviço do caso em aberto (GUINCHO) · **85** · caso · MTA só se o caso for de transporte · 10 |

Sem pergunta para a Regina: os dois dados já estão no caso; é trabalho de programação.

## 3. `yelum/auto/chaveiro` — chave trancada: a URA quer saber para onde levar o carro
📊 72 telas, 45 respondidas, **2 órfãs** (`e6a07317`). Na chave trancada a Yelum manda **chaveiro + guincho** até a
concessionária/chaveiro (até 100 km) e pergunta o destino. O passo que responde isso existe, mas só vale para guincho.

| tela | opções | onde | a atendente (deduzido) | respostas prováveis · nota · origem |
|---|---|---|---|---|
| "Você já possui o endereço para onde devemos levar o seu veículo?" | Sim · Não · Voltar | depois do formulário do local | **Não** (a tela seguinte diz "por não possuir o endereço…") | perguntar ao segurado · **85** · segurado · "Sim" + concessionária do caso · 60 · caso · "Não" · 45 · deduzir (cria a obrigação abaixo) |
| "Por não possuir o endereço de destino, o veículo será removido para o pátio do guincheiro. É necessário informar o destino em até 24 horas úteis por este canal." | nenhuma (aviso) | logo depois do "Não" | seguiu | não responder e **avisar a corretora do prazo de 24h** · **90** · deduzir |

Depois disso a Yelum achou "inconsistência sistêmica" e passou a um analista — o protocolo desta rota vem de outra conversa (`56bd78f7`).
**Pergunta à Regina:** *"Na chave trancada da Yelum, quando pergunta se já tem o endereço de destino, você diz Sim com a concessionária ou Não? E quem informa o destino depois, dentro das 24 horas?"*

## 4. `yelum/auto/carro_reserva` — vai a uma pessoa por desenho, e há 4 telas depois disso
📊 91 telas, 67 respondidas, **4 órfãs**. A rota percorre a URA até "em análise, retorno em até 3 horas úteis" e fecha como
encaminhamento. As órfãs vêm depois: um analista humano (`c0c3c694`) e a **consulta de status** do carro reserva (`f984d8f0`).

| tela | opções | onde | a atendente (deduzido) | respostas prováveis · nota · origem |
|---|---|---|---|---|
| "Para qual horário?" | texto livre | analista humano, depois do "em análise" | respondeu (veio a oferta de upgrade) | repetir o horário de retirada já informado em "Qual data e horário desejado?" · **80** · caso · perguntar ao segurado · 70 |
| "Para iniciarmos, vamos fazer uma validação. Digite seu CPF ou CNPJ." | texto livre | consulta de status | digitou | CPF do titular · **90** · caso |
| "Agora digite sua data de nascimento (dd/mm/aaaa)." | texto livre | consulta de status | digitou — a Yelum recusou ("CPF ou data não correspondem") | data de nascimento do titular · **70** se o caso tiver · caso · senão perguntar · 60 · segurado |
| "Para qual *Telefone*?" (envia código por SMS) | 1 · 2 · 3 Nenhum | consulta de status | — (terminou em "procure seu corretor") | **uma pessoa**: o código chega no celular do segurado · **80** · pessoa · "3 – Nenhum" · 20 |

Sem pergunta: é pós-acionamento (097.1); o caminho de abertura já funciona.

## 5. `allianz/residencial/desentupimento` — responde tudo e nunca chegou ao protocolo
📊 40 telas, 32 respondidas, 0 órfãs, 3 conversas — **as 3 terminam em "Vou transferir seu caso para um especialista"**.
Duas foram por *Outros serviços → lista (dedetização, limpeza, caixa d'água, telhas, veterinária, Outros)* — a lista **não tem
desentupimento**; a terceira parou logo depois do complemento do endereço.
- **Última tela conhecida:** "Vou transferir seu caso para um especialista. Ele já tem acesso a todo o histórico."
- **O que vem depois (deduzido):** um especialista humano da Allianz conversa em texto livre. Numa dessas conversas ele
  recusou: *"A apólice não contempla desentupimento de chuveiro"* (citado no playbook, sessão `2540f42f`). Prováveis:
  pede detalhes do entupimento e abre protocolo · **55**; recusa por cobertura · **35**; pede para ligar no 0800 · 10.
- **Outra hipótese:** entrar por *Serviços Emergenciais (encanador…)* em vez de *Outros serviços* chegaria a um menu com
  desentupimento · 💭 **45** — nenhuma conversa gravada prova isso.

**Pergunta à Saionara:** *"No desentupimento da Allianz, você entra por 'Serviços Emergenciais' ou por 'Outros serviços'? E quando a URA passa para o especialista, ele abre o protocolo por ali mesmo, ou costuma recusar?"*

## 6. `allianz/residencial/eletrodomesticos` — responde tudo e nunca chegou ao protocolo
📊 60 telas, 44 respondidas, 0 órfãs, 5 conversas, todas terminando em "transferir para um especialista": 2 no CPF
(apólice não encontrada / CPF inválido), 1 logo depois de "Continuar" no agendamento, 1 depois da categoria do aparelho e 1 em Outros serviços.
- **Última tela conhecida (a mais avançada):** "O serviço de *Conserto para eletrodoméstico* deverá ser agendado. 1-Continuar 2-Voltar".
- **O que vem depois — a rota irmã `maquina_de_lavar` (que atende sozinha) mostra o resto, na mesma URA:** data numa
  lista de 7 dias úteis → período (manhã 9–13 / tarde 13–18) → confirma o agendamento → aviso "fora da garantia" →
  "Selecione o eletrodoméstico" (1-Geladeira … Máquina de lavar) → defeito → marca → modelo → resumo → **protocolo**.
  💭 **80** que é o mesmo caminho. A transferência logo depois de "Continuar" provavelmente é plano sem cobertura
  (a Allianz escreveu *"não cobrimos conserto de eletrodomésticos no seu plano ESSENCIAL"* em `21610390`) · 💭 60.

A pergunta é a mesma da rota 5 (o especialista). Se ela disser "é plano sem cobertura", a rota já está pronta.

## 7. `hdi/residencial/chaveiro` — responde tudo e nunca chegou ao protocolo
📊 26 telas, 16 respondidas, 0 órfãs, **1 conversa** (`0a7c24ef`).
- **Última tela conhecida:** a cobertura do chaveiro — *"…este serviço está limitado a portas ou portões principais…"* —
  seguida, **6 minutos depois**, de "Ainda não identificamos a sua resposta! Deseja continuar?" e o fim.
  Antes dela a URA perguntou "Em qual destas opções está o problema? Porta interna · Porta principal · Voltar".
- **O que vem depois (deduzido da rota irmã `yelum/residencial/eletricista`, mesma plataforma de URA):** uma tela
  "selecione o problema" (quebra · perda · emperramento · arrombamento) · 💭 **55** → "agora ou agendar?" · **75** →
  dia → período → resumo com número da assistência · **75**.
- ⚠️ A pausa de 6 minutos sugere que a cobertura veio com um botão que o acervo não gravou (P-084-15), ou que a
  porta era **interna** e a atendente parou ali. "Porta interna" não tem cobertura — o produto já manda isso para uma pessoa.

**Pergunta à Saionara:** *"No chaveiro da HDI, depois que a URA mostra o texto de cobertura, o que ela pergunta em seguida? E quando é porta interna, tem algum caminho ou é recusa?"*

## 8. `porto/residencial/eletrodomesticos` — responde tudo e nunca chegou ao protocolo
📊 15 telas, 11 respondidas, 0 órfãs, **1 conversa** (`3854b4a2`). A atendente passou pelas 3 páginas da lista de aparelhos
(lavar, fogão, micro-ondas → geladeiras, freezer → ar condicionado / *Não encontrei o assunto*) e a Porto encerrou.
- **Última tela conhecida:** "O conserto é para o quê? Ar condicionado · Não encontrei o assunto · Voltar" → "Vou encerrar a conversa".
  💭 O aparelho do segurado **não estava na lista** · 70.
- **O que vem depois (deduzido de `porto/residencial/encanador`, que atende sozinho):** recados de cobertura →
  "Posso continuar o agendamento?" → para quando → horários → quem estará no local → nome e celular → resumo →
  **protocolo** + link de acompanhamento + garantia de 90 dias · 💭 **75**.

Pergunta só se sobrar: *"Quando o aparelho não aparece na lista da Porto, o que você faz?"* (vale pouco — basta uma conversa que termine).

## 9. `yelum/residencial/eletrodomesticos` — geladeira vai a analista, por regra da Yelum
📊 17 telas, 11 respondidas, 0 órfãs, **1 conversa** (`bb573c0a`): geladeira → "é usada para medicação?" → *"por ser um item
essencial, vou te transferir para um de nossos analistas"*. O robô já trata isso como ida a uma pessoa.
- **Última tela conhecida:** a transferência para o analista.
- **O que vem depois para um item NÃO essencial (fogão, micro-ondas, lava-louças) — deduzido de `yelum/residencial/eletricista`:**
  "agora ou agendar?" → dia → período → "sua assistência já está em andamento" + resumo · 💭 **65**.

**Pergunta à Saionara:** *"Na Yelum, geladeira sempre vai para analista. Fogão e micro-ondas seguem pela URA até o número da assistência? E o que o analista pede na geladeira?"*

## 10. `hdi/residencial/eletricista` — não tem conversa própria
📊 0 telas desta rota: as 5 conversas que a sustentavam pediam **conserto de fogão** pelo menu do eletricista e perderam a
etiqueta na SPEC-121. Numa conversa sem etiqueta (`ed46a953`) a HDI mostrou: cobertura do eletricista →
"Falta de energia · Problema elétrico · Outro" → transferência para analista (💭 escolheram "Outro").
- **O que vem depois de "Problema elétrico" (deduzido de `yelum/residencial/eletricista`, mesma plataforma):**
  lista do problema (tomadas, interruptores, lâmpadas, disjuntor, chuveiro…) → ambiente → agora/agendar → dia →
  período → resumo · 💭 **75**.

Sem pergunta: falta um acionamento real de eletricista na HDI.

## 11. As que vão a uma pessoa por desenho — nada a responder
- `porto/auto/vidros` — a Porto só aceita vidros por formulário (`porto.vc/reparovidros`). 📊 1 conversa, 0 órfãs.
- `tokio/auto/guincho` — a Tokio devolve link do autoatendimento. 📊 3 conversas, 0 órfãs.
- `tokio/auto/carro_reserva` — a Tokio devolve link da locadora ou de outro WhatsApp. 📊 2 conversas, 0 órfãs.

## 12. Conversas gravadas que não têm rota no produto
📊 contagem de sessões por etiqueta no acervo: `allianz/residencial/telhado` (2) · `mapfre/auto/carro_reserva` (1) ·
`yelum/residencial/limpeza_caixa_dagua` (1) · `allianz/auto` com táxi, encanador e eletricista (1 cada — benefício residencial
da apólice de auto). Nenhuma está entre as 76 rotas, então nenhuma aparece no placar. Na Allianz, telhado cai em
*Outros serviços → especialista*, igual ao desentupimento.

---

## As telas que o robô responde "de cabeça" (o cérebro responde, sem dado no caso)
Não travam, mas quem responde é o modelo, não o passo escrito. A maioria **já está no caso ou é pergunta simples ao segurado**.

| tela | seguradora / rotas | resposta provável · nota · origem |
|---|---|---|
| "Digite os 3 últimos dígitos do seu CPF ou CNPJ" | Porto auto e residência | tirados do CPF do titular · **95** · caso (falta só ligar o dado) |
| "Informe a PLACA do veículo" (benefício residencial da apólice de auto) | Allianz residência | placa da apólice de auto · **85** · caso · perguntar · 70 |
| "Digite o número do prédio, casa ou km" | Porto auto | número do local · **85** · caso |
| "Pode informar o CEP? · Não sei o CEP" | Porto auto | CEP do local · **80** · caso · "Não sei o CEP" · 60 |
| "E qual horário? Entre 13h00 e 13h30 …" | Porto auto (bateria, vidros) | a primeira faixa possível · **60** · deduzir · perguntar · 80 |
| "Informe para quando quer agendar" + "E qual horário?" | Porto residência | perguntar ao segurado · **85** · segurado |
| "O conserto é para o quê?" (lista de aparelhos) | Porto residência | o aparelho do pedido · **90** · caso |
| "O que você precisa?" (menu de serviço) | Porto residência | o serviço do pedido · **90** · caso |
| "Qual o motivo do reagendamento?" | Porto residência | perguntar ao segurado · **85** · segurado (pós-acionamento) |
| "Para qual data deseja o agendamento?" + "Em qual horário? Ex: 20:00" | Yelum auto | perguntar ao segurado · **85** · segurado |
| "Qual o melhor período? Manhã · Tarde" | HDI e Yelum residência | perguntar ao segurado · **80** · segurado |
| "Horário inicial / final permitido para entrada do prestador no condomínio" | HDI e Yelum residência | perguntar ao segurado · **80** · segurado · "08:00 / 18:00" · 35 · deduzir (chute comum) |
