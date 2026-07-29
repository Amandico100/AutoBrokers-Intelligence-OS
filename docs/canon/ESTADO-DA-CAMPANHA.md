# ESTADO DA CAMPANHA — passagem de bastão

> **Se você é um chat novo:** leia este arquivo inteiro antes de qualquer coisa,
> depois `CLAUDE.md` e `docs/canon/CURADORIA-POR-SUBAGENTES.md`. Este arquivo diz
> **onde paramos**; os outros dizem **como se trabalha aqui**.

**Atualizado em 29/07/2026, 21h** · commit `60bcca1` + os desta sessão

---

## 1. O que estamos fazendo agora, em uma frase

A destilação do histórico de duas corretoras está sendo feita por **subagentes
Opus 5 pelo plano Max**, e não pela API — porque por API custaria ~US$ 80 e o
projeto tem US$ 6.

Isso é **temporário**. Quando Resulta e AutoFleet estiverem prontas, a Central
de Agentes volta a fazer o trabalho corrente, com Batch API a 50% de desconto.

---

## 2. Estado dos números (29/07, 21h)

```
RESULTA      7.733 sessoes · ~2.900 destiladas
AUTOFLEET      705 sessoes ·    173 destiladas
CARTAS       ~3.200 no RAG · marca `destilacao_max_29_07_2026` nas novas
ATLAS        10 mapas tecidos · 456 sessoes de seguradora · 17.488 eventos
API          US$ 0,00 gasto pelos subagentes hoje
TESTES       97 suites verdes
```

**Lotes em disco** (gitignored, reexportados limpos às 20h):
`backend/scripts/destilacao_max/lotes/` (52 lotes, Resulta) e
`lotes_autofleet/` (10 lotes). Os `.destilado.jsonl` já aplicados podem ser
reconhecidos por `aplicar.py` devolver "0 sessões".

---

## 3. O fluxo, em quatro comandos

```bash
cd backend
# 1. exportar (mascara com as funcoes de producao; custo zero)
python scripts/destilacao_max/exportar.py --lotes 60 --por-lote 100 \
       --empresa <company_id> --saida scripts/destilacao_max/lotes
# 2. destilar: um subagente Opus 5 por lote, 2 lotes por agente, 2-4 em paralelo
#    Prompt: ler BRIEFING-SUBAGENTE.md, destilar, gravar .destilado.jsonl, PARAR
# 3. gravar (nao e o subagente que grava — foi o que cortou 60% dos tokens)
python scripts/destilacao_max/aplicar.py scripts/.../lote_00X.destilado.jsonl
# 4. publicar: nao faca nada. O publicador de `distill_once` leva ao RAG.
```

`company_id`: Resulta `04b5cdbc-04cd-4ddf-8e4b-f43efb062fab` ·
AutoFleet `6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a`

---

## 4. AS PEGADINHAS — leia antes de mexer em qualquer coisa

### 4.1 Nunca reaplique `templatize` num transcript montado

`cliente` está na lista de rótulos do `_LABELED_VALUE` e a regra é ancorada em
início de linha. `CLIENTE: meu vidro trincou` casa como "rótulo: valor" e a fala
inteira do segurado vira `{VALOR}`.

**Eu fiz isso três vezes em 29/07** ao reaplicar o mascarador nos lotes
pendentes depois de cada conserto de PII. Apaguei a fala do cliente em 278
sessões. Use `mascarar.remascarar()`, que desmonta a linha primeiro — ou
simplesmente reexporte do banco. Ver `test_remascarar_nao_apaga_o_cliente.py`.

### 4.2 O teto de gasto é 0 por padrão, e isso é de propósito

`DESTILADOR_TETO_POR_RODADA=0` → nenhuma chamada de modelo em `distill_once`.
O botão "Processar aprendizado" **não** processa um lote: processa até a fila
secar ou o crédito acabar. Foi assim que US$ 6 sumiram numa rodada.

O teto **não** desliga curar e publicar — é por ali que as cartas dos
subagentes chegam ao RAG. Não use `_env_int` para lê-lo: aquele faz `max(1,...)`
e transformaria o teto travado em uma conversa + um playbook no modelo caro.

### 4.3 PostgREST corta em 1.000 linhas e não avisa

Toda consulta que possa passar de mil linhas precisa paginar com `.range()`.
Foi essa mudez que construiu o mapa da Allianz sobre 40% do material.

### 4.4 `hash()` de string em Python é aleatório por processo

Não use para `on_conflict` nem para id estável. Use `hashlib`.

### 4.5 Claude Opus 5 e Sonnet 5 PENSAM por padrão

O LangChain devolve `content` como lista de blocos. `str()` numa lista dá a
repr, e o leitor de JSON falha. Use `_texto_da_resposta()`. Isto custou US$ 15
em chamadas repetidas antes de ser achado.

### 4.6 Deploy sai da `main`

O EasyPanel constrói a `main`. Commit em feature branch não chega em produção:
`git push origin HEAD:main`.

### 4.7 Uma sessão que falha três vezes sai da fila

`summary.distill_falhas >= 3` → parada. Sem isso a mesma sessão é cobrada em
toda rodada, para sempre, em silêncio.

---

## 5. Regras do Founder que não se negociam

- **Nenhuma mensagem pode ser perdida ou apagada do WhatsApp da Resulta.**
- **Nunca analisar as 9.565 mídias por API.** Só as 20 autorizadas.
- **Áudio liberado para transcrição, desde que não seja por API** — hoje isso
  significa: não é possível. Claude não recebe áudio aqui, e Whisper é API.
  A conta honesta está na §7.
- Menu não cresce: coisa nova vai dentro de item existente.
- Se um teste com dado real revelar defeito no seu código, corrija o código.
- Nunca criar motor paralelo (CLAUDE.md §5). Consolidar antes de duplicar.
- Separe **FATO**, **INFERÊNCIA** e **RECOMENDAÇÃO** em todo relatório.
- Em 29/07 o Founder afastou o excesso de zelo com LGPD: *"estamos num projeto
  controlado só na minha máquina e sem clientes"*. O portão de PII continua
  valendo, mas **não bloqueie trabalho por causa dele** — o que não pode é
  perder conversa.

---

## 6. Pendências abertas

| # | O quê | Estado |
|---|---|---|
| 1 | ~~Telas quase-duplicadas no Atlas~~ | **investigado: hipótese errada, §9** |
| 1b | **Cobertura mentia para cima** | **corrigido; exige re-tecer** |
| 2 | Destilar o resto: ~4.800 Resulta + ~530 AutoFleet | em andamento |
| 3 | WhatsApps desconectados desde 18:49 de 29/07 | esperando repareamento |
| 4 | ~~Sessões abertas não fecham~~ | **corrigido, §15** |
| 5 | Playbooks de conduta: 3 existem, faltam os demais | precisa teto > 0 |
| 6 | Validar os 3% da AutoFleet pelo caminho automático | `TETO=20`, ~US$ 0,13 |
| 7 | `isForwarded` não é persistido → conduta trocada (CA-021) | registrado |
| 8 | 45 chaves de seguradora distintas, com sujeira antiga | limpeza pendente |
| 9 | Áudio: conhecimento falado que não fica registrado | decisão do Founder |
| 10 | Relatório consolidado de condutas de risco observadas | ~7 ocorrências |
| 11 | **SPEC-063** (P1 de segurança, CA-020) | não iniciada |
| 12 | **SPEC-064** | não iniciada |
| 13 | Cobertura pela fatia que a corretora atende | proposta |
| 14 | Curadoria de áudio — instrução pronta | aguarda o texto terminar |

---

## 7. A auditoria do Atlas de 29/07 — o que foi verificado

**FATO — a AutoFleet FOI processada.** A hipótese de que o tecelão ignorou as
conversas novas porque já existia mapa está **errada**, e a prova é o volume:

```
                telas de URA        eventos
                ontem → hoje        ontem → hoje
Allianz          221 → 326          5.330 → 6.746
Yelum            179 → 492            546 → 3.026
Porto            298 → 686          1.019 → 2.883
HDI              229 → 387            884 → 1.965
Zurich            39 → 115             94 →   379
Tokio             40 →  54            138 →   178
```

Mais: **456 sessões de seguradora no banco = 456 contadas nos mapas.** Zero
eventos sem seguradora. Zero seguradoras sem mapa. Nada foi deixado de lado.

**FATO — por que a cobertura da Allianz ficou em 63%.** Cobertura é
`opções percorridas / opções descobertas` = 435/687. A AutoFleet descobriu
opções novas (denominador subiu) e percorreu parte delas (numerador subiu), na
mesma proporção. Em número absoluto a Allianz passou de ~140 para **435 opções
percorridas**. Percentual estável com mapa maior é mais território conhecido,
não estagnação.

**INFERÊNCIA — o defeito real é inflação de telas.**

```
Porto     686 telas de URA · 1.292 opções
Yelum     492 telas
HDI       387 telas
Allianz   326 telas de URA + 924 nós de conversa humana
```

Uma URA de seguradora tem 30 a 80 telas. 686 é a mesma tela contada muitas
vezes, porque algo dentro dela varia — protocolo, nome, saudação com hora. Já
consertamos parte disso em 28/07 (mascarar `Assistência: 8923467` derrubou 18
nós da Yelum para 1), mas sobrou muito.

Três consequências concretas:
1. a cobertura parece baixa porque o denominador está inflado;
2. o Canvas fica ilegível;
3. **o agente não acha a rota certa** — é a pior das três.

**FALSO ALARME que eu mesmo levantei e descartei:** achei que `edges` apontava
para nós inexistentes (977 chaves órfãs na Porto). A chave de `edges` é
`nó|opção`, então o número maior é esperado. Não é defeito.

**A INVESTIGAR:** Tokio tem 36 sessões e só 178 eventos — 5 por sessão. Ou as
conversas são curtíssimas, ou algo corta antes do fim.

**Sobre áudio, a conta honesta:** transcrever exige API. Claude não recebe áudio
neste ambiente. Whisper custa US$ 0,006/min — se a média for 30s, são US$ 0,003
por áudio. Não é os US$ 80 que o Founder teme; é da ordem de **US$ 10 a US$ 15
por milhares de áudios**. É decisão dele, com o número na mão. Imagem é outra
conversa: descrever foto de para-choque não ensina processo.

---

## 8. A próxima auditoria recomendada

**Assinatura de tela.** Medir quantas das 686 telas da Porto são a mesma tela e
endurecer a assinatura no `cartographer`. É a auditoria que destrava a cobertura
real de todas as seguradoras de uma vez — e é a que mais importa para o
atendimento, porque cobertura inflada esconde rota que o agente precisa achar.

Método: agrupar nós por conjunto de opções normalizado, não pelo texto inteiro
da tela. Duas telas com as mesmas opções na mesma ordem são a mesma tela, ainda
que o cabeçalho traga um protocolo diferente.


---

## 9. Auditoria de assinatura de tela (29/07, 22h) — a hipótese estava errada

Eu previ que as 686 telas da Porto eram a mesma tela repetida, e que normalizar
protocolo e saudação colapsaria tudo. **Medi, e não é isso.**

```
                telas   sem numeros   sem numero+saudacao
Porto            816        806              797
Allianz        1.250      1.231            1.183
Yelum            545        544              534
```

Nove por cento de redução. Os textos são **genuinamente diferentes** — não são
variantes da mesma tela.

O que a medição mostrou de fato:

```
             telas   menus distintos   telas SEM opção
Allianz      1.250        141              1.022
Porto          816        167                545
Yelum          545         67                428
HDI            440         53                335
```

**A maioria dos nós não tem menu nenhum.** São mensagens de texto livre — a URA
informando ("aguarde, vamos transferir") ou o especialista conversando. Cada
frase distinta virou um nó. Isso infla o número de "telas" na tela do admin e
polui o Canvas, mas **não afeta a cobertura**, porque cobertura só conta opção.

### O defeito real, e ele é o oposto do que eu esperava

A cobertura **mentia PARA CIMA**, porque `compute_coverage` somava por nó e a
mesma opção era contada uma vez por cópia da tela. A tela que mais duplica é a
mais percorrida — duplicou porque apareceu em muitas sessões — então o
numerador inflava mais que o denominador.

```
            painel   real   opções distintas   percorridas
Allianz      63%     37%         451              165
Porto        29%     21%         965              207
Yelum        32%     24%         277               66
HDI          33%     23%         225               52
Zurich       31%     15%         144               22
Azul         36%     27%         133               36
Bradesco     14%     11%         100               11
Tokio        11%     10%          72                7
Mapfre       22%     18%          44                8
Alfa         53%     44%          41               18
```

**Vinte e seis pontos de otimismo na Allianz.** Cobertura baixa manda continuar
explorando; cobertura que mente para cima manda **parar** — e o que fica sem
explorar é rota que o agente vai precisar no meio de um atendimento.

**Corrigido:** a chave passou a ser (conjunto de opções da tela, rótulo da
opção). Duas telas que oferecem exatamente as mesmas escolhas são a mesma tela
para efeito de navegação. `test_cobertura_nao_mente_para_cima.py` trava as
quatro condições, incluindo a inversa: menus DIFERENTES não podem ser fundidos.

**Exige re-tecer os mapas** para o número corrigido aparecer.

---

## 10. Levantamento de áudio (29/07) — medido

```
                 áudios   do cliente   do atendente   imagens   documentos
Resulta           2.660      2.399           261       2.851      3.580
AutoFleet           993        539           454         452        169
TOTAL             3.653      2.938           715
```

Duração **não** está gravada em nenhum dos 3.653 (`media_meta.seconds` é nulo).
Estimativa por média de mensagem de voz de atendimento (30 a 40s):

```
TUDO (3.653 audios) ................. US$ 11 a US$ 15
SÓ O ÁUDIO DO ATENDENTE (715) ....... US$ 2,15 a US$ 2,90
```

### A seleção certa não é amostra aleatória, é por direção

O áudio do **cliente** é o caso: "meu carro quebrou na avenida tal". Situacional,
não ensina processo.

O áudio do **atendente** é o conhecimento: é ele explicando o procedimento — e é
exatamente o que os subagentes relataram faltar, conversa após conversa.

**715 áudios de atendente por ~US$ 2** cobre a lacuna que importa, sem amostra e
sem perder conteúdo de valor.

### Depois do texto, não junto

1. Terminar as cartas de texto (rodando, custo zero).
2. Saber **quais sessões deram zero cartas** — são as que perderam conhecimento.
3. Transcrever só o áudio do atendente dessas sessões.
4. Anexar a transcrição ao texto da sessão e re-destilar só elas.

Fazer antes gastaria transcrição em sessão que já entregou seu conhecimento por
escrito. Fazer depois é mais barato e mais preciso.

**Imagem: não recomendo.** Descrever foto de para-choque não ensina processo, e
sem o modelo enxergar de verdade a descrição não vale o custo.

---

## 11. SPEC-063 e SPEC-064 — não perder de vista

Ficaram para trás quando a campanha de destilação virou prioridade em 29/07.
**Nenhuma das duas foi iniciada.** O texto canônico está em `docs/canon/specs/`.

**SPEC-063** nasceu de CA-020, o middleware de `/api/`: uma rota do dashboard
respondia sem passar pela verificação esperada, e a causa-raiz nunca foi isolada
— foi contornada. Enquanto isso ficar aberto existe um caminho de requisição
cuja garantia de autorização é por convenção, não por código. É P1 pela regra do
CLAUDE.md §10.4, e por isso não pode ir para produção com cliente pagante.

**SPEC-064** é a etapa seguinte do plano de execução. Antes de começar, reler
`EXECUTION-MASTER-PLAN.md` e `FOUNDER-DECISIONS.md`: a campanha de destilação
**não** revogou nada, só entrou na frente.

Também abertos, do relatório da SPEC-062: prova de restore, RPO/RTO,
OpenTelemetry, e o Bloco B de billing (travado pela decisão D22).

---

## 12. Por que a cobertura da Porto é 29% depois de anos atendendo

Fui olhar as 372 lacunas distintas da Porto. Elas se dividem em quatro famílias,
e só a última vale perseguir.

**1. Nunca vai ser percorrido, por natureza**

```
"09 = bom"  "10 = ótimo"           escala 0-10 da pesquisa de satisfação
"1 - 124279107688"                 protocolo DAQUELE cliente
"2 - Porto Alegre São João         oficina próxima DAQUELE endereço
     - 5.16km - Av Benjamin..."
```

Onze notas por tela de pesquisa. Uma lista de protocolos por cliente. Uma lista
de oficinas por endereço. **Cada item é uma lacuna que nunca fecha** — mesma
família de "Voltar". Corrigido em 29/07 com `pesquisa`, `protocolo` e
`prestador` em `acao_conhecida`.

**2. Não é opção nenhuma**

```
"peço gentilmente que avalie meu atendimento"
"laudo técnico atestando a causa e extensão dos danos"
```

Frase de pesquisa e item de lista de documentos capturados como se fossem
escolha. Corrigido: sem número de opção e com mais de 32 caracteres não é opção
— o WhatsApp limita título de linha de lista a 24 caracteres, então opção
interativa de verdade nunca passa disso sem vir numerada. Ficam fora dos DOIS
lados da fração.

**3. Outro negócio da Porto, que a corretora não vende**

```
"seguro saúde"  "consultar extrato"  "segunda via do cartão"
"regulamento do programa"  "ajuda com o app da porto"
```

A Porto Seguro é conglomerado: banco, cartão, saúde, programa de pontos. O
WhatsApp é um só e oferece tudo. A corretora nunca vai percorrer isso — e não
deveria. **NÃO foi suprimido:** esconder rota real seria mentir de novo, só para
o outro lado. Ver §13.

**4. Cauda longa legítima**

```
"caçamba aberta"  "pesado 2 a 3 eixos"  "portão de aço"
"fogão, cooktop ou forno"  "micro-ondas"  "kit instalação"
```

Rota de verdade, só rara. **É a única família que vale perseguir**, e ela se
preenche com atendimento real ao longo do tempo — ou com o Cartógrafo
explorando a URA de propósito, que é para isso que ele existe.

### A conclusão que importa

29% não é mapa mal feito. É o **denominador medindo a coisa errada**: inclui o
conglomerado inteiro quando a corretora precisa de uma fatia. Depois dos
consertos a estimativa sobe pouco (Porto 29→32, Bradesco 17→37), porque as
famílias 1 e 2 são pequenas na Porto: 11 das 372.

---

## 13. Proposta: cobertura da fatia que importa

Hoje é `opções percorridas / TODAS as opções descobertas`, o que mistura "seguro
saúde" com "guincho".

A medida honesta é **por ramo alcançável**: das opções que descem do galho que a
corretora atende, quantas já foram percorridas? Esse número mede o que o agente
precisa para atender, e é o único que deveria mandar continuar ou parar de
explorar.

Não implementado. É decisão de produto, não conserto, e antes dela vale terminar
a destilação — que é o que trava o lançamento.

---

## 14. Instrução: curadoria de áudio (quando o Founder autorizar)

O levantamento está na §10. Esta é a instrução de execução.

**Pré-requisito:** as cartas de TEXTO das duas corretoras terminadas. Áudio é
complemento, não substituto — transcrever antes gastaria em sessão que já
entregou seu conhecimento por escrito.

**Passo 1 — escolher o que transcrever.** Não é amostra aleatória. São os áudios
do **ATENDENTE** (`direction='out'`) em sessões cuja destilação devolveu
`fatos_reutilizaveis` vazio. O áudio do cliente é o caso ("meu carro quebrou na
avenida tal"); o do atendente é o processo. São ~715 nas duas corretoras.

**Passo 2 — baixar a mídia.** Pelo `/message/downloadmedia` do fork GO da
Evolution, com body `{message: waE2E.Message}`. O
`/chat/getBase64FromMediaMessage` é o caminho Baileys e devolve 404 neste fork.
**Exige o WhatsApp pareado.**

**Passo 3 — transcrever.** Whisper (`whisper-1`), US$ 0,006/min. É API, e é a
única forma: Claude não recebe áudio neste ambiente. Custo estimado dos 715:
**US$ 2,15 a US$ 2,90**. Abrir orçamento explícito antes, como se faz com mídia.

**Passo 4 — anexar e re-destilar.** A transcrição entra no texto da sessão como
`ATENDENTE: <transcrição>`, a sessão volta para a fila (`summary` sem
`distilled`) e um subagente a destila de novo pelo caminho normal. **Passe o
texto por `mascarar.remascarar()`, nunca por `templatize` direto** — §4.1.

**Não fazer imagem.** Descrever foto de para-choque não ensina processo, e sem o
modelo enxergar de verdade a descrição não paga o custo.


---

## 15. Auditoria das sessões abertas (29/07, 23h) — corrigido

**FATO.** 50 sessões estavam `open`: 43 da Resulta, 7 da AutoFleet. A mais antiga
desde **21/07** — oito dias — com 423 mensagens paradas. A fila do Destilador só
olha `status='closed'`, então tudo isso era conhecimento invisível.

**FATO — nenhuma era conversa com seguradora.** O material que o Founder
considera insubstituível estava intacto. Mas nada no sistema garantia isso: foi
sorte, não projeto.

**A causa.** A sessão fechava só no caminho de ENTRADA de mensagem: quando
chegava mensagem NOVA da mesma pessoa depois do intervalo de duas horas
(`observer_intake._SESSION_GAP`). Se o segurado nunca escreve de novo — o caso
normal quando o atendimento resolveu — ninguém fechava nada, para sempre.

**O conserto.** `_fechar_sessoes_vencidas_sync()` em `distill_once`, **antes** de
ler o teto de gasto: sessão sem mensagem por mais de **seis horas** fecha. Seis é
o triplo do intervalo de sessão, de propósito — fechar cedo partiria uma conversa
em duas e ensinaria conduta pela metade, que é pior que esperar.

Roda mesmo com o teto em zero: não chama modelo, e é justamente o que destrava
material para quando houver crédito. Se estivesse depois de um `return` por teto
zero, a varredura nunca aconteceria — o material ficaria invisível exatamente
enquanto se economiza.

**Onde mora e por quê.** No Destilador, não num serviço novo com agendamento
próprio: seria motor paralelo para uma consulta de duas linhas (CLAUDE.md §5).
Ele já roda periodicamente, já é quem precisa da sessão fechada, e já tem trava
de rodada única.

**Resultado.** 38 sessões fechadas na varredura manual, 320 mensagens na fila.
Sobraram 12 abertas, a mais antiga com 6h — recentes de verdade, e a próxima
rodada as pega.

`test_conversa_que_acabou_nao_fica_aberta.py` trava as quatro condições,
incluindo a inversa (sessão viva de 30min e de 3h **não** fecham) e a de
arquitetura (nenhum serviço novo foi criado).

---

## 16. Estado do Atlas depois dos consertos de 29/07

```
allianz  73%   ·  alfa     58%  ·  azul   44%  ·  bradesco 38%
porto    37%   ·  hdi      36%  ·  yelum  34%  ·  zurich   28%
mapfre   25%   ·  tokio    12%                      média: 39%
```

Movimento em relação ao painel de antes dos consertos: Bradesco +21, Azul +9,
Porto +8, Allianz +6. São exatamente as seguradoras que mais usam lista de
oficinas próximas e pesquisa de satisfação — o que confirma que o que subiu foi
a remoção de lacuna falsa, não otimismo novo.

A Tokio continua em 12% com 36 sessões e só 178 eventos. **É a próxima
investigação** — cinco eventos por sessão está muito abaixo de todas as outras.
