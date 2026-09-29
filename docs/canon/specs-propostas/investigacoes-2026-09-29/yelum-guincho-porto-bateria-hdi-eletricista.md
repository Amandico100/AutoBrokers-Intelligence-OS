# Investigação: três rotas fora do "atende sozinho" (29/09/2026)

**Card (modo investigação, §3.3):** só leitura · main `c310e77` · nenhuma mensagem enviada · nada gravado no banco · nenhum modelo chamado · base = cópia do `observed_events` (📊 687 sessões classificadas com os motores do produto, `inv-tres-rotas/classif.py`). Todas as telas abaixo estão sem dados pessoais.

Comandos (em `backend/`, `PYTHONIOENCODING=utf-8`):
`simular_corredor.py --seguradora S --ramo R --servico V --detalhado` · `medir_rota.py --seguradora S --ramo R --servico V` · e, no rascunho, `whatif.py` (o simulador sem uma sessão), `whatif_poshandoff.py` (corta a sessão na primeira tela em que o robô passaria o caso a uma pessoa), `motor2.py` (roda `match_ura_step` e `detect_handoff_trigger` sobre a tela real) e `rota.py` (desfecho de cada sessão).

📊 Quantas conversas existem (a cópia é de hoje e o arquivo versionado é de 28/09): yelum guincho **27** (eram 26), porto bateria **6** (eram 5), hdi eletricista **5**.

---

## 1. yelum/auto/guincho: 68%, "FALTA CAPTURA"

**Por quê.** 📊 A régua dá **52/76**. Os pontos perdidos:
- **Zero telas órfãs: 4/20 (−16).** Uma tela órfã é uma tela que pede alguma coisa e para a qual o robô não tem resposta escrita.
- **100% determinístico: 4/8 (−4).** Foram 479 de 481 telas respondidas pelo corredor, sem precisar do modelo.
- **Apelidos: 0/4.** Esse item só é medido com `--com-espelho`.

Os outros guinchos ficam em 95% porque só perdem o item dos apelidos. 📊 O controle foi `medir_rota.py … hdi auto guincho`, que deu **72/76** com órfãs 20/20 e determinismo 8/8. A diferença entre 68% e 95% vem **inteira** de duas telas de uma única sessão (`56bd78f7`).

**As duas telas.** Na sessão, a atendente respondeu "Problema com a chave" na tela "Pode me dizer o que aconteceu?".

| tela | a atendente respondeu | respostas possíveis (nota) |
|---|---|---|
| "O que aconteceu com a chave? Dentro do veículo / Perda / Quebrou / Outros / Voltar / Sair" | Perda | a resposta do segurado (**90**) · uma constante (**0**) |
| "O veículo está trancado? Sim / Não / Voltar" | Não | a resposta do segurado (**90**) · uma constante (**0**) |

Logo depois a URA respondeu: *"Neste caso enviaremos o serviço de **Guincho**"*. A conversa terminou com o número da assistência.

**A etiqueta não está errada.** O classificador etiqueta pelo que a seguradora assinou ("Serviço: Guincho"), e ela entregou um guincho. O que está diferente é o **pedido**: o segurado **perdeu a chave**, e a Yelum converteu esse pedido em guincho. No banco há mais duas conversas de chave na mesma família de URA:
- `e6a07317` (Yelum): chave trancada no carro → "CHAVEIRO + GUINCHO".
- `697abd09` (HDI): terminou em chaveiro.

📊 A rota `yelum/auto/chaveiro` tem **0** conversas no acervo. Fonte: `grep.py "o que aconteceu com a chave"`.

**No produto, essas duas telas não aparecem num guincho de pane.** 📊 `motor2.py`: o passo `o_que_aconteceu` responde `{servico_opcao}`, que num guincho é "Pane ou Defeito". Elas só aparecem quando o pedido é de chave.

**E se a sessão for etiquetada como chaveiro?** 📊 `whatif.py yelum/auto/guincho 56bd78f7` deu **ATENDE SOZINHO**: 0 órfãs, 449/449 telas respondidas, protocolo em 15 conversas. A régua sobe para cerca de **72/76 (95%)**, o mesmo patamar dos outros guinchos.

**Conserto mínimo e seguro (nota 85).** No desempate do classificador (`padroes_de_servico.servico_da_sessao`), a regra seria: quando a sessão tem a tela "o que aconteceu com a chave", a rota é **chaveiro**, mesmo que a URA termine num guincho. A rota é o que o segurado pede. Isso dá à `yelum/auto/chaveiro` a primeira conversa completa. Também mostra o buraco real: o corredor de chaveiro **não responde as telas de destino do guincho**, porque `destino_ja_tem`, `destino_cep` e `destino_digitado` são `only_subservices: ["guincho"]`. E ele não pergunta ao segurado nem `chave_problema` nem `veiculo_trancado`, que hoje não têm origem. Depois do conserto, é preciso gerar o acervo de novo.
- ❌ Descartado, **nota 40**: acrescentar "guincho" ao `only_subservices` dos dois passos de chave. 📊 Também chega a "ATENDE SOZINHO" (481/481), mas é um carimbo: ensina ao guincho uma tela que ele nunca vê e deixa o chaveiro quebrado.

**Chega ao fim sozinho?** 📊 De 27 conversas, **19** têm número de assistência (`rota.py`). As 8 sem número:
- 4 são **pós-acionamento** ("A solicitação de GUINCHO está concluída… questionar atraso/entrega").
- 2 são endereço não localizado, e a Yelum passou a um especialista.
- 1 é a própria URA desistindo.
- 1 é CPF inválido.

⚠️ Essas 19 incluem dois grupos que, **por desenho**, vão para uma pessoa (`handoffs.py`):
- **6 colisões**: "Houve vítimas?" e "A polícia foi acionada?" levam a sinistro.
- **4 caminhões**: eixos, altura, carroceria.

Os casos de **pane de carro de passeio** vão de ponta a ponta. 📊 Na amostra, `0a1a616e`, `ba9f1970`, `8a0d25a4`, `c54f4a98` e `e97943bd` chegam ao número da assistência sem nenhuma tela que peça uma pessoa.

---

## 2. porto/auto/bateria: 63%, "FALTA CAPTURA"

**Por quê.** 📊 A régua dá **48/76**:
- Órfãs: **0/20 (−20)**.
- Determinismo: 4/8, com 80 de 85 telas.
- Apelidos: 0/4.

As 5 telas órfãs são todas da sessão `4830574a`, em que uma **consultora humana** da Porto assume a conversa.

**Sim, há acionamento de bateria de ponta a ponta sem a consultora.** 📊 **4 de 6**, com protocolo:
- `67296ad9`: recarga.
- `c470d13d`: recarga.
- `f4838bb3`: bateria nova, com visita técnica.
- `9e043112`: recarga, **hoje**. Ainda não está no acervo.

A sexta, `e3b1561f`, foi cancelada por quem digitava, na confirmação. Sem a sessão da consultora, 📊 `whatif.py porto/auto/bateria 4830574a` dá **ATENDE SOZINHO**: 74/74 telas, protocolo em 3 conversas.

**Quando a consultora entra.** Horário e tipo de bateria não explicam; o que explica é o **perfil do cliente**. A tela é *"Identifiquei aqui no sistema que você faz parte do nosso grupo de clientes com atendimento personalizado"*. O mesmo CPF aparece em duas sessões:

| sessão | dia/hora (Brasília) | menu que veio | resultado |
|---|---|---|---|
| `4830574a` | sex 16h25 | "Escolha sobre o que você quer falar: Cartão / Seguro Auto / Saúde…" → "O que você precisa sobre *Seguro Auto*? Assistência / Sinistro" | **consultora** |
| `f4838bb3` | qua 13h44 | "…porém seu consultor atende de seg a sex, 8h às 20h. Mas seguiremos de forma prioritária" → menu comum | **URA até o protocolo** |

As duas foram dentro do horário. Então quem decide se a consultora entra é **a Porto**, provavelmente pela disponibilidade do consultor. Nós não prevemos isso, mas **vemos** na tela. 📊 Em todo o banco só essas duas sessões têm "atendimento personalizado".

**No produto, o robô já para uma tela antes da consultora.** 📊 `motor2.py`: "O que você precisa sobre *Seguro Auto*? Assistência / Sinistro / Voltar" não casa nenhum passo, e o gatilho `sinistro` passa o caso a uma pessoa. As 5 órfãs ficam depois dessa tela, então o robô nunca chegaria nelas. 📊 `whatif_poshandoff.py` (a régua sem as telas que vêm depois da passagem para uma pessoa) dá **ATENDE SOZINHO**. ⚠️ Mas o robô para ali por acaso: a palavra "Sinistro" aparece no menu.

**O que a consultora perguntou, e o que a atendente respondeu:**
1. "Como posso te ajudar?" → um texto livre explicando que era troca de bateria.
2. Placa e modelo.
3. Quantos amperes → "70 a 80". A atendente teve de perguntar ao segurado, e isso levou cerca de 20 minutos.
4. "Está por aí?"
5. "Caso o prestador não tenha a bateria, ele pode buscar no Centro Automotivo" → "pode ser".
6. Endereço completo.
7. "Como está em São Paulo temos a bateria Premium" (só um aviso).
8. "Esse cliente é do Sul e está em São Paulo?" → sim.
9. Nome e telefone de quem está no local.
10. "O próprio segurado?"
11. Imediato ou agendado → imediato.

No fim veio o número da ordem de serviço.

**As respostas prováveis para as 5 telas órfãs:**

| tela | resposta (nota) |
|---|---|
| apresentação da consultora + "Como posso te ajudar?" | passar à pessoa com o dossiê (**90**) · texto livre do robô (**35**) |
| "{NOME} está por aí?" | passar à pessoa (**85**) · "Sim" (**40**) |
| "…ele pode buscar no Centro Automotivo" | o consentimento do segurado, colhido antes (**75**) · "Pode ser" fixo (**20**) |
| "Informe por gentileza o endereço" | o endereço já colhido (**80**) |
| "Esse cliente é do Sul e está em SP?" | a comparação entre a cidade da apólice e a cidade de agora, colhida antes (**70**) |

**Dá para perguntar tudo antes?** Os **dados**, sim, **nota 85**:
- recarga ou bateria nova;
- amperes, se o segurado souber;
- endereço completo com complemento;
- quem está no local, nome e celular;
- agora ou agendado;
- aceita a bateria premium ou que o prestador vá buscá-la;
- está fora da cidade da apólice?

Todos são curtos. O caminho pela URA nem pergunta amperes. Já **conversar sozinho com a consultora** tem nota **30**: é uma pessoa, não um menu, e hoje o produto não reconhece que a URA acabou (P-120-04).

⚠️ **Um achado maior, que atinge TODA a Porto auto.** As duas sessões mais recentes com o menu novo da Porto (`910b6295` em 14/09 e `9e043112` hoje) mostram depois de "Seguro Auto" a tela *"Você quer falar sobre qual assunto? Assistência / Consultar apólice / Informações e cobertura / **Sinistro** / Avisar…"*. 📊 `motor2.py`: **nenhum passo** casa essa tela e o gatilho `sinistro` dispara. O robô **passaria o caso a uma pessoa antes de chegar ao serviço**, e isso vale para guincho, bateria e todas as outras. O simulador tira passagem-para-pessoa do denominador, e por isso nada disso aparece nele. A tela seguinte, *"Por favor, selecione o veículo. Veículo 1…"*, também não tem passo: `escolher_veiculo` exige `^qual o veículo\?`. 📊 Nos últimos 30 dias (3 conversas): 2 vieram com o menu novo e 1 com o antigo.

---

## 3. hdi/residencial/eletricista: 30%, "FALTA CAPTURA"

**Por quê.** 📊 A régua dá **23/76**. Os pontos perdidos:
- órfãs 0/20;
- **a rota nunca chegou ao fim: 0/12**;
- a trava (freio) não casou nenhuma tela real: 0/8;
- protocolo, dia e período: 0/5;
- determinismo 4/8, com 65 de 68 telas;
- apelidos 0/4.

**As 3 telas órfãs não são de outro ramo: são de outro SERVIÇO**, dentro do residencial. Vêm da sessão `13379965`. Nela, quem digitava escolheu Eletricista, voltou na pergunta "Falta de energia / Problema elétrico", abriu Encanador ("Mais opções" e depois "Voltar"), abriu Linha branca ("Voltar") e digitou **SAIR**.

| tela | a atendente respondeu | resposta certa numa rota de eletricista (nota) |
|---|---|---|
| "Qual desses itens está com vazamento? Torneira… Mais opções" | Mais opções | nunca chega aqui: o motor responde "Eletricista" no menu de serviço (**95**) |
| "…Vasos sanitários / Boia… Voltar" | Voltar | idem |
| "Qual desses itens precisa de reparo? Geladeira… Voltar" | Voltar | idem |

A URA **não** pergunta o ramo nessa altura, e o motor não errou nenhuma resposta, porque nessa sessão ele nunca respondeu nada. Quem respondeu foi a atendente. Sem essa sessão, 📊 `whatif.py … 13379965` dá órfãs 0 e 100% determinístico, mas continua em **FALTA CAPTURA (sem desfecho)**. Pelas contas dos itens, a nota iria para cerca de 47/76.

**O problema real é outro: nenhuma das 5 conversas chegou ao fim.**
- `834cc238`: o pedido era **conserto de fogão**, e a atendente escolheu Eletricista por engano. Etiqueta errada.
- `b638adcd`: "Outro" → analista.
- `ed46a953`: botão sem texto gravado → analista.
- `1c8d0849`: endereço fora do cadastro → analista.
- `13379965`: a exploração descrita acima.

**Ninguém nunca escolheu "Falta de energia" ou "Problema elétrico" na HDI.** A URA irmã, a da Yelum, é do mesmo fornecedor e fecha: 📊 `yelum/residencial/eletricista` está em **ATENDE SOZINHO**. Na sessão `315f0681`, o caminho foi "Problema elétrico" → item (Tomadas / Interruptores / Lâmpadas / Reatores / Disjuntores / Chuveiro / Torneira elétrica) → cômodo → agora ou agendar → data → período → número da assistência.

---

## 4. O que fazer em cada rota

| rota | conserto que já destrava | perguntar ao segurado antes | precisa de acionamento real | vai para uma pessoa |
|---|---|---|---|---|
| **yelum guincho** | etiquetar pelo pedido ("chave" é chaveiro) e gerar o acervo de novo → **68 → ~95%**, ATENDE SOZINHO. **Nota 85** | nada novo para pane. Para chave: o que houve com a chave, se o carro está trancado e se já tem destino. **Nota 80** | chaveiro Yelum/HDI que vira guincho: destino no corredor de chaveiro. **Nota 70** | colisão (sinistro) e caminhão, por desenho |
| **porto bateria** | (a) um passo explícito para "O que você precisa sobre *Seguro Auto*? Assistência / Sinistro" que passa o caso a uma pessoa **com o motivo** "cliente com consultora", sem depender da palavra "sinistro" (**nota 80**); (b) na régua, telas depois de uma passagem para pessoa não contam como órfãs (**nota 75**) → **63 → ~95%** | recarga ou nova, amperes se souber, endereço completo, quem está no local, agora ou agendado. **Nota 85** | 🔴 o **menu novo da Porto**: um passo "qual assunto → Assistência" (com a mesma justificativa do `menu_como_ajudar`) e outro para "selecione o veículo". A prova só vem com acionamento real. **Nota 90 de prioridade** | a consultora de relacionamento (P-120-04: reconhecer a fronteira e mandar o dossiê) |
| **hdi eletricista** | tirar `13379965` e `834cc238` da rota: uma é exploração, a outra é fogão. Sobe para **~47/76**, sem desfecho | falta de energia (casa inteira ou só a rua; a rua é da concessionária) ou problema elétrico; o item; o cômodo; agora ou agendar, data e período; se é condomínio, os horários de entrada. **Nota 85**. Hoje `data_agendamento`, `periodo_preferido` e os horários do condomínio **não têm origem**, e quem responde é o modelo | **um acionamento real** que passe de "Falta de energia / Problema elétrico". É o único jeito de chegar a 95%. **Nota 90** | "Outro" (a URA passa a um analista) e endereço fora do cadastro |

**Em resumo:** o guincho da Yelum e a bateria da Porto **já funcionam de ponta a ponta** nos casos comuns. 📊 São 19/27 e 4/6 conversas que chegaram ao número. O que as segura na régua são as sessões atípicas: uma de chave e uma com a consultora. O **risco real** é outro: o menu novo da Porto, que hoje faria o robô passar a uma pessoa **toda** conversa que o encontrar. O eletricista da HDI não tem nenhuma conversa que chegue ao fim, e só um acionamento real resolve isso. As perguntas para o segurado já estão listadas acima.
