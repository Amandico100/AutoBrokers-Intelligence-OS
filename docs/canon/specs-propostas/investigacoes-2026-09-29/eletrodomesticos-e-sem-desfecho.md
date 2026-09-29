# Investigação: eletrodomésticos e as 6 rotas que nunca chegaram ao protocolo

Somente leitura · main `1fb9db1` · 29/09/2026. Nenhuma mensagem enviada, nada gravado no banco, nenhuma chamada a modelo.
Os scripts estão em `scratchpad/inv-eletro/`. Todos usam `regua_motor` (motor do produto), `padroes_de_ramo`, `padroes_de_servico` e `zonas_do_acervo`, sem reimplementar nada.

```
dump.py        → M.eventos_observados()                 📊 33.628 eventos · 688 sessões (28/07/2025 → 29/09/2026)
classificar.py → PR.classificar_ramo + PSV.servico_da_sessao + G.sessao_chegou_ao_fim, sessão a sessão
cruzado.py     → replay CRUZADO: telas reais do BANCO de uma sessão irmã → match_ura_step/flow/handoff/captura
                  com o subserviço da rota-alvo (mesma ordem de scripts/replay.py)
```

## Veredito sobre a hipótese

**A hipótese está certa quanto ao menu e só em parte quanto à etiqueta. A causa maior é outra.**

- **O menu confirma a hipótese.** Nas quatro seguradoras com residencial, a máquina de lavar é um item *dentro* de eletrodoméstico:
  - Allianz: `Qual eletrodoméstico precisa de conserto? 1-Linha Branca (… Máquina de Lavar e secar roupas) 2-Ar Condicionado 3-Geladeira, Freezer e outros`. Em seguida vem a lista de 15 itens: 1 Geladeira · 2 Freezer · 3 Frigobar · 4 Adega · 5 Micro-ondas · 6 Fogão · 7 Forno · 8 Cooktop · 9 Filtro · 10 Lava-louças · 11 Coifa · 12 Exaustor · 13 Secadora · **14 Máquina de Lavar** · 15 Outros.
  - Porto: `Eletrodoméstico → Conserto ou reparo → O conserto é para o quê?`, em 3 páginas (a máquina de lavar está na 1ª).
  - HDI/Yelum: `Linha branca → Qual desses itens…`. A lista mostrada é Geladeira, Side by Side, Fogão, Cooktop, Micro-ondas, Lava-louças, Frigobar/Reversão e Outras opções. **A máquina de lavar não aparece nessa página.**
  - 📊 Fonte: `telas.py "selecione o eletrodomestico|qual eletrodomestico|linha branca|geladeira…"` sobre o banco.
- **As etiquetas erradas existem, mas são poucas.** 📊 Contagem por `classificar.py`, conferida sessão a sessão:
  - Allianz: 2 de geladeira e 1 de micro-ondas saíram com etiqueta `None`, e todas chegaram ao fim (`213af941`, `2802ddf8`, `3db870e0`).
  - HDI: 5 sessões de **fogão** saíram como `eletricista`. Uma é abertura com protocolo (`1c8d0849`); as outras 4 são acompanhamento do mesmo caso.
  - **Yelum: 5 sessões de "Recarga de bateria" saíram como `socorro_mecanico`** e todas têm protocolo.
  - Causas medidas:
    - `PADROES_DE_SERVICO_TEXTO["eletrodomestico"]` só casa `eletrodoméstic|linha branca|máquina de lavar|lavadora`. Geladeira, fogão, micro-ondas e freezer ficam de fora.
    - O resumo humano da Allianz chama o serviço de **"CONSERTO RESIDENCIAL"**, que é um rótulo desconhecido (5 sessões, a maioria de acompanhamento).
    - O resumo da Yelum diz "Socorro Mecânico" para a recarga.
  - Allianz, Porto, HDI e Yelum não têm nenhuma sessão de TV, secadora ou lava-louças pedida pela corretora. Azul, Bradesco, Mapfre e Zurich não têm nenhuma sessão residencial no banco. Tokio tem uma única menção a geladeira, num lembrete de agendamento.
  - O acervo versionado só guarda 1 sessão `eletrodomesticos` na Allianz, 1 na Yelum e nenhuma fora do cardápio na Porto.
- **🔴 A causa maior é o corte na transferência para uma pessoa.** O acervo guarda só a zona `URA`, e `zonas_do_acervo.zonas` marca como `HUMANO` tudo o que vem depois da primeira transferência, **mesmo quando o robô da seguradora recomeça depois**.
  - 📊 Na Allianz residencial, 39 sessões têm o protocolo **só** na zona humana. Em 19 delas o robô reabriu depois da transferência (`zonas_fim.py`).
  - Exemplo: a sessão `8ad1d251` fez uma máquina de lavar inteira pelo robô, com resumo, protocolo e senha, e nada disso entrou no acervo.
  - É por isso que desentupimento e eletrodomésticos da Allianz aparecem como "nunca chegou": no banco, 📊 **4 de 4 e 3 de 3 chegaram ao fim** (`rotas.py`).

## As 6 rotas

### 1. allianz/residencial/desentupimento — dá para ligar hoje? 35
- **a) Chegou ao fim?** No banco, 📊 3 aberturas reais, e **todas passaram por "Outros serviços → Outros → especialista"**:
  - `96f220ca` e `3a895d36` terminaram com protocolo aberto pelo especialista: *"A assistência foi agendada para o dia ##/##, entre ##h e ##h…"*;
  - `2540f42f` recebeu *"A apólice não contempla desentupimento de chuveiro"*.
  - O caminho do produto (`Emergenciais → De qual profissional? → 3`) 📊 **nunca foi escolhido: 0 de 16 respostas** (`apos.py "de qual profissional"`). O simulador não cobre nada disso.
- **b) Dá para deduzir da rota irmã?** Pelo encanador, a tela seguinte seria *"E para quando precisa do Desentupimento? Agora/Quero agendar"*, e o passo `quando` casa uma versão sintética dela. Nota **55**. O que vem depois não se deduz (nota **25**), e o próprio playbook proíbe copiar o encanador.
- **c) Telas pendentes:**
  - Tudo depois de `profissional=3` é desconhecido.
  - Na fase humana, o especialista perguntou:
    - *"informe todos os pontos de entupimento: dispositivo/tubulação, quantidade e cômodos"*;
    - *"qual banheiro? social/suíte"*;
    - *"algum outro local entupido?"*;
    - *"a caixa de esgoto também?"*;
    - o período (em janelas de N horas) e o ponto de referência.
  - Respostas prováveis: vêm do caso (problema_descricao), nota 70.
- **Recomendação:** **1 acionamento real** escolhendo `3 - Desentupimento`, só para registrar o que a seguradora mostra. Até lá o caso fica com a fase humana guiada pelo modelo, não com o determinístico.

### 2. allianz/residencial/eletrodomesticos — 80 depois de um conserto
- **a) Chegou ao fim?** 📊 3 sessões, as 3 no especialista:
  - `7c22675f` (geladeira): categoria **3** → especialista → protocolo;
  - `21610390` e `eb7c521e`: *"não cobrimos conserto de eletrodomésticos no seu plano ESSENCIAL"* e *"Cláusula de Assistência Não Contratada"*.
- **b) Dá para deduzir da rota irmã?** Sim. O **replay cruzado** da máquina de lavar `7ac3c101` como `eletrodomesticos` 📊 respondeu 23 telas, marcou 6 como passagem e **0 órfãs**, até `protocolo_com_sucesso` (`cruzado.py allianz/residencial/eletrodomesticos 7ac3c101`). O caminho do robô foi provado até o protocolo em 3 sessões (`7ac3c101`, `b2bf40e7`, `8ad1d251`). Nota **85** para qualquer item de 1 a 13.
- **c) Onde para:** 🔴 em `menu_aparelho`. O subserviço fixa `eletrodomestico_opcao="15"` (Outros), e a URA tem a tecla exata do aparelho. Para geladeira, o produto aperta Linha Branca → Outros.
  - Resposta certa: a tecla do aparelho (1 a 14), nota **90**.
  - "15" só quando o aparelho não está na lista, nota 40; a tela seguinte nunca foi vista.
  - Geladeira/freezer: categoria 3 leva ao especialista (📊 3 de 3 transferiram), nota **75**; Linha Branca → 1 tem nota 45, porque a própria URA põe a geladeira fora da Linha Branca.
- **Recomendação:** conserto de código: pedir o aparelho ao segurado e traduzi-lo para a tecla. Não precisa de acionamento real.

### 3. porto/residencial/eletrodomesticos — dá para ligar hoje? 40
- **a) Chegou ao fim?** 📊 Há 1 sessão (`3854b4a2`). Ela percorreu as 3 páginas de categoria e a corretora digitou "sair". Nenhuma tela depois da categoria.
- **b) Dá para deduzir da rota irmã?** O fim, sim: o replay cruzado do chaveiro `565cb39a` (protocolo e link) casa como eletrodomésticos:
  - `recado_peca_20_dias → seguir_agendamento → quando → data → período → horário → no local → celular → resumo → confirmar → protocolo + link`;
  - nota **70**.
  - O miolo entre a categoria e o recado, provavelmente marca/modelo/idade/defeito, nota **30**.
- **c) Telas pendentes:**
  - 🔴 Risco de página: `eletro_categoria` responde `{eletrodomestico_rotulo}` em todas as páginas. Uma geladeira (página 2) seria digitada na página 1, e o reparo de opção inválida só funciona para menu numerado, que a Porto não usa. Resposta certa: "Mais opções" até achar o item, nota 60.
  - Miolo: desconhecido.
- **Recomendação:** **1 acionamento real** (máquina de lavar ou geladeira).

### 4. yelum/residencial/eletrodomesticos — geladeira já está certa; o resto, 45
- **a) Chegou ao fim?** 📊 1 sessão (`bb573c0a`): Linha branca → Geladeira → *"usada para armazenar medicação? Não"* → *"por ser um item essencial, vou te transferir…"*. O gatilho `vou te transferir para` dispara, então a transferência para uma pessoa é o desenho, e está correta.
- **b) Dá para deduzir da rota irmã?** O fim da família: a Yelum eletricista `315f0681` e a HDI encanador `61b96027` vão até a *"Resumo da solicitação / Assistência: ####"*. Nota **55** para fogão, micro-ondas e os outros.
- **c) Telas pendentes:** o que vem depois do item, para o que não é geladeira. Máquina de lavar só pode estar em "Outras opções", que nunca foi aberta.
- **Recomendação:** 1 acionamento real com item que não seja geladeira. Geladeira fica como está.

### 5. hdi/residencial/chaveiro — dá para ligar hoje? 20
- **a) Chegou ao fim?** 📊 1 sessão (`0a7c24ef`), que parou em *"Em qual destas opções está localizado o problema? Porta interna / Porta principal"*. A corretora apertou Voltar e a sessão morreu por inatividade.
- 🔴 **Defeito novo:** a bolha anterior (*"Garante os custos… ou ainda em decorrência de **sinistro** devidamente coberto…"*) não casa passo nenhum e dispara o gatilho `sinistro`.
  - 📊 `detect_handoff_trigger → 'sinistro'`.
  - Chegou no mesmo segundo que a pergunta da porta, e `webhook.py:1176` manda cada bolha separada ao motor.
  - Em `handle_insurer_message` (`insurer_dispatch_service.py:4444`) isso vira `needs_human` **antes** da pergunta da porta. O simulador não vê, porque HANDOFF sai do denominador.
  - Classificação: INFERÊNCIA com nota 80. Quem prova é um teste que chame o motor com as duas bolhas.
- **b) Dá para deduzir da rota irmã?** O fim, sim (mesma família: quando_agora → data → período → resumo "Assistência: N"), nota **65**.
- **c) Respostas prováveis:**
  - Porta principal: nota **90**, porque o recado diz *"limitado a portas ou portões principais"*.
  - `chave_o_que_aconteceu`: nota 50.
  - "Agora": nota 75.
- **Recomendação:** consertar o recado (passo de passagem ou exceção ao gatilho) e depois fazer 1 acionamento real.

### 6. yelum/auto/bateria — 85 depois de um conserto de uma linha
- **a) Chegou ao fim?** 📊 A única sessão etiquetada (`69816f6b`) **não é de bateria**: o carro "travou e não anda" e a corretora recusou a recarga. Os 5 casos reais de recarga (`86769bd5`, `ba475989`, `927d8cea`, `8ac461dc`, `935c4076`) estão como `socorro_mecanico`, **todos com protocolo** (*"Finalizamos a abertura do pedido de Socorro Mecânico e o número da sua assistência é…"*).
- **b) Replay cruzado como bateria:**
  - 📊 2 de 5 sessões com 100% respondido e 0 órfãs; `o_que_aconteceu → "Recarga de bateria"` é a mesma tecla dos casos reais.
  - 🔴 3 de 5 param no formulário nativo *"precisamos entender onde o veículo está parado"* (`rb_InformacoesLocal`): **bateria não consegue responder, e socorro_mecanico e guincho conseguem.**
  - Causa: `required_slots` da bateria não tem `local_situacao`.
- **Recomendação:** acrescentar `local_situacao` e reetiquetar. Não precisa de acionamento real.

## Perguntas ao segurado antes de abrir o eletrodoméstico (tiradas das telas reais)

| pergunta | quem pergunta (📊 tela real) |
|---|---|
| **Qual aparelho**, com a palavra da lista da seguradora | Allianz (15 itens), Porto (3 páginas), HDI/Yelum |
| **Idade de fabricação: até 10 anos ou mais?** Acima de 10, recusa e a visita conta como usada | Allianz (URA e humano), HDI/Yelum (recado), humano HDI |
| **Qual o problema/defeito** | Allianz URA ("Qual problema/defeito apresentado?"), humano Allianz/HDI |
| **Marca** e **modelo completo** (pode ser aproximado) | Allianz URA (duas telas separadas), humano ("problema, marca, modelo e idade") |
| Está **fora da garantia do fabricante**? | Allianz URA, humano Allianz |
| **Geladeira: guarda medicação?** | Yelum/HDI |
| **Data e período** (Allianz: próximos 7 dias úteis, manhã/tarde) · quem estará no local · 2 telefones · horário de entrada no condomínio · referência | Allianz, HDI, Porto |
| Ar-condicionado: **BTUs, Split ou Janela**, acesso pelo lado interno, altura até 4,5 m | Allianz, HDI |
| Avisar: **as peças são do segurado** (Allianz, prazo de 10 dias) ou **peças até o limite** (HDI/Yelum) | recados |

⚠️ **Voltagem, tamanho e capacidade não são perguntados** em nenhuma tela de eletrodoméstico. A voltagem só aparece como dica ("teste em outra tomada com a mesma voltagem"); litros só aparecem como limite de cobertura (adega).

## Riscos que apareceram de passagem

- 📊 5 de 5 frases reais de recusa da Allianz não disparam gatilho nenhum: *"não cobrimos… plano ESSENCIAL"*, *"Cláusula de Assistência Não Contratada"*, *"não contempla"*. Hoje dependem do modelo na fase humana.
- `extract_capture_anchors` lança `IndexError` com texto vazio quando o playbook não tem âncora `password`/`eta` (padrão `$^`). O produto se protege com `strip()` antes de chamar; `gerar_corpus_de_telas.sessao_chegou_ao_fim` não se protege.

**Resumo por rota:**
- **Atende sozinho com um conserto, sem acionamento real:** allianz/eletrodomésticos (tecla do aparelho) e yelum/bateria (`local_situacao`).
- **Precisa de 1 acionamento real:** allianz/desentupimento, porto/eletrodomésticos, yelum/eletrodomésticos (item que não seja geladeira) e hdi/chaveiro, este depois do conserto do gatilho.
- **Vai para uma pessoa por desenho:** geladeira na Yelum e na Allianz (categoria 3).
