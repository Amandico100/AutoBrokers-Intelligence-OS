---
> **Status:** relatório final de execução — pré-condição do gate
> **Criado em:** 23/08/2026
---

# Relatório de execução — SPEC-084.1: O ENSAIO

**Produto:** AutoBrokers Intelligence OS
**SPEC:** [`docs/canon/specs/SPEC-084.1-o-ensaio.md`](../specs/SPEC-084.1-o-ensaio.md)
**Branch:** `feat/spec084-a-fabrica-de-rotas`
**Worktree:** `AutoBrokers-FIX`
**Executor:** Claude Opus 5 (1M) — sessão de execução, com subagentes e juízes
**Início:** 22/08/2026 · **Conclusão:** 23/08/2026
**Commit inicial:** `0f54761` (a SPEC-084.1 v4, liberada pelo juiz)
**Commit final:** `15dfdd5`
**Estado final:** CONCLUÍDA COM RESSALVAS — *a liberação é do juiz, não minha*

> **O objetivo, na frase da SPEC:** *"O segurado escreve no WhatsApp e o
> acionamento sai do começo ao fim — sem travar, sem errar, sem surpresas e sem
> precisar de humano."*

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado. O corredor continua sendo **um só**
      arquivo (`corridor_playbooks.py`), a régua **uma só** (`rubrica.py`), o
      motor **um só** (`insurer_dispatch_service.py`). Nenhum passo novo foi
      escrito "ao lado" de um existente: as 73 rotas dividem os mesmos troncos.
- [x] Nenhuma migration foi criada, movida, renomeada, apagada ou reaplicada.
      **Esta SPEC não tocou em SQL.**
- [x] Nenhum DDL foi aplicado.
- [x] Nenhum segredo foi exposto. Todo diagnóstico com dado de segurado saiu com
      dígitos mascarados por `#`. Ver §7.
- [x] Nenhum escopo foi reduzido. As seis proibições do Founder foram cumpridas
      literalmente — ver §1.1.
- [x] Nenhum dado atravessou tenants. As leituras foram `SELECT` sobre o acervo
      de espelho, sempre com a Amandus excluída por variável de ambiente.
- [x] `CLAUDE.md`, `EXECUTION-MASTER-PLAN.md` e `FOUNDER-DECISIONS.md` lidos no
      início.

### 0.1 As seis proibições — e o que cada uma custou

| Proibição | Cumprida | Como se prova |
|---|---|---|
| ✗ não liga agente | **sim** | nenhuma chamada a ligar/publicar agente; o trabalho todo é replay OFFLINE contra corpus gravado |
| ✗ não envia mensagem | **sim** | nenhum envio, em canal nenhum. Nenhum teste precisou — e se precisasse, o protocolo era PARAR e perguntar |
| ✗ não escreve no banco | **sim** | só `SELECT`. Zero INSERT/UPDATE/DELETE/DDL |
| ✗ não acessa portal | **sim** | nenhum acesso, nem "para conferir uma tela" |
| ✗ não imprime segredo | **sim** | ver §7 — e um vazamento de sessão ANTERIOR foi corrigido nesta (`b4091c5`) |
| ✗ não faz merge na `main` | **sim** | a branch nunca foi mesclada. **O gate é do Founder** |

---

## 1. Resumo executivo

A SPEC-084.1 mede cada uma das **73 rotas** (`seguradora × ramo × serviço`) com
uma rubrica de 106 pontos e cinco eixos, e conserta o que a medida acusar.

📊 **Onde estava:** 1 rota AAA. 📊 **Onde chegou:** **19 rotas AAA de 43 com
corpus**, média ponderada **88,4%**, e a pior rota do acervo em 54% — com o
bloqueio dela **nomeado e atribuído**, não escondido.

O trabalho se dividiu em duas metades que se alimentaram:

1. **Vinte e um consertos na RÉGUA (C1–C21).** Metade dos achados desta SPEC não
   foi "o corredor está errado", foi **"a régua estava punindo o comportamento
   certo"** — o passo compartilhado, o escopo correto, o handoff, o desfecho por
   encaminhamento. Uma régua que pune o acerto ensina o executor a desfazer o
   acerto. Cada conserto foi declarado antes, medido depois, e commitado sozinho
   com uma mutação que fica vermelha.
2. **Sete ondas de rota (A–G).** Onda A a F consertam o que responde; a **ONDA
   G** faz o que nenhuma outra fazia: **separa `SEM_CORPUS` por coleta legítima
   de `SEM_CORPUS` por bug**, com controle medido em cada linha.

🔴 **O que mudou para o corretor**, em uma frase: as telas que a URA manda e o
produto não respondia passaram a ser respondidas — **na forma que aquela
seguradora aceita** (número na Allianz, rótulo na Porto), com o freio armado
antes de confirmar, com handoff quando a decisão é de gente, e sem chutar
resposta em pergunta que não tem padrão honesto.

**O que ficou de fora e por quê:** quase tudo que falta é **acervo**, não código.
Das 30 rotas ainda sem corpus, 15 são coleta legítima, 11 têm rótulo que a URA
nunca mostrou, 4 são seguradora onde ninguém pediu assistência — e **zero** são
suspeitas de bug. Ver §6 e o [`ROTEIRO-DE-COLETA.md`](ROTEIRO-DE-COLETA.md).

---

## 2. Escopo executado por bloco

### 2.1 Os consertos de régua (C1–C21)

> A regra que valeu para todos: **declarar o conserto ANTES**, medir o efeito
> DEPOIS, commitar sozinho, e provar com uma mutação que fica vermelha.

| # | O que estava errado | Efeito medido |
|---|---|---|
| C1–C5 | quatro bugs de LEITURA na régua; **dois subtraíam** pontos de rota correta | notas corrigidas em 12 rotas |
| C2 | o período estava na captura e era jogado fora | o furo nº 3 da Clarissa |
| C6 | o Espelho não era lido: 4 pontos vinham de TRÊS strings no código | leitor real do Espelho |
| C7 | `constante_justificada` não era lida; 55 constantes passavam | **22 notas caíram** — e as 22 estavam declaradas |
| C8 | a régua **punia o handoff correto** | 28 telas em 6 rotas deixaram de contar como buraco |
| C10 | havia item que ninguém podia ganhar | a rota de referência fecha em 106/106 |
| C11 | 🔴 **medir uma rota ESCREVIA no corredor** — duas medições simultâneas deixaram uma âncora MORTA no produto | trava de concorrência |
| C12 | 🔴 **uma mutação estava COMMITADA na régua** | guarda que pergunta ao COMMIT, não à árvore |
| C13 | o Espelho lia o PRÓPRIO ECO e chamava de palavra do cliente | vocabulário limpo |
| C14 | janela de bloco de 14,7 KB engolia vizinhos | janela fecha em linha em branco |
| C15 | o PORTAL colado no chat virava "palavra do cliente" | um cardápio creditava QUATRO rotas de uma vez |
| C16 | o item das notes dava ZERO por não ter o que conferir — e **pagava para DUPLICAR passo** | recontagem por união |
| C17 | repetia o bug do C14 na leitura dos marcadores `# ROTA` | janela fecha, marcadores separados |
| C18 | desempate de transcrição escolhia o candidato errado | critério por evidência |
| C19 | o protocolo da PORTO tem PREFIXO e a máscara só mordia o rabo dele | 5 corpora regenerados e conferidos linha a linha |
| C20 | a escolha pela placa não casava a tela REAL (número em negrito) | §9.5 — casar o teste não é responder a tela |
| **C21** | 🔴 **"suspeito de bug" acusava a mapfre de um bug que não existe** | ver §2.3 |

### 2.2 As ondas de rota

| Onda | Escopo | Estado | O achado que mais custava |
|---|---|---|---|
| A | rotas de referência (encanador, eletricista, ar-condicionado…) | CONCLUÍDA | o item impossível de ganhar (C10) |
| B | `allianz × auto` | CONCLUÍDA | a tela que **APAGA a solicitação inteira** — e o galho onde cancelar é decisão de gente |
| C | `hdi × auto` | CONCLUÍDA | 🔴 **a tecla certa na FORMA errada**: a URA responde *"Não entendi"* e manda para um analista |
| D | `yelum × auto` | CONCLUÍDA | a porta de entrada estava muda — e a apólice errada **não tem desfazer** |
| E | `porto × auto` | CONCLUÍDA | o escopo por subserviço não acompanhava o ENCADEAMENTO da URA |
| F | as 16 rotas restantes | CONCLUÍDA | a cortesia silenciava o abandono; o FREIO da porto residencial **não armava em uma tela sequer** |
| G | rotas sem corpus + roteiro de coleta | CONCLUÍDA | `DESEMPATE` declarado e **nunca lido** — 4 rotas da bradesco sumiam com o acervo cheio |

### 2.3 A ONDA G — o que ela existe para separar

🔴 `SEM_CORPUS` é uma de duas coisas, e a diferença decide **quem trabalha**:

```
coleta legítima  →  🧑 alguém pede o serviço no WhatsApp da seguradora
bug de leitura   →  🤖 alguém conserta o decodificador
```

📊 Trocar uma pela outra já custou meses: as quatro rotas de `bradesco/auto`
ficaram `SEM_CORPUS` com **159 telas** no acervo porque o `DESEMPATE` que separa
guincho de bateria estava declarado em `padroes_de_servico.py` e nunca era lido.
Corrigido: nasceram `bradesco/auto/guincho` (80%) e `bradesco/auto/bateria`
(71%), e o corpus foi de 127 → 159 telas.

🔴 **E o veredito nasceu sem controle** (C21). Ele dizia *"nenhuma ROTA deste
corredor tem telas → o decodificador é o suspeito"* — mas a tabela de rotas não é
o corpus. 📊 Em `mapfre/auto` o decodificador **funciona**: nomeia
`carro_reserva` em 14 linhas. As 6 sessões do acervo são deflexão de sinistro
(3), carro reserva (1), abandono por inatividade (1) e canal do CORRETOR (1).
**Ninguém pediu assistência à mapfre no período.** O erro tinha as duas direções:
mandaria caçar bug inexistente e faria arquivar como dívida técnica uma linha que
é **pedido de coleta**.

**Estado final dos 30 `SEM_CORPUS`:**

| veredito | rotas | de quem é |
|---|---|---|
| COLETA LEGÍTIMA — a URA oferece e ninguém pediu | **15** | 🧑 |
| ⚠️ RÓTULO NÃO VISTO — o rótulo não aparece em tela nenhuma | **11** | 🧑 conferir o rótulo, ou a URA não oferece |
| NINGUÉM PEDIU ASSISTÊNCIA — decodificador vivo, assunto outro | **4** | 🧑 (mapfre) |
| 🔴 SUSPEITO DE BUG | **0** | — |

### 2.4 Entregas da SPEC que NÃO foram executadas

| Item | Motivo |
|---|---|
| renomear `estepe_opcao`/`local_seguro_opcao` na zurich | 📊 medido: renomear trava o guincho da zurich por dois slots que ninguém coleta hoje. É mudança separada e medida — [P-084-61] |
| regra de classificação para sessão exploratória (`hdi/residencial/eletricista`) | é decisão de **corpus**, não de corredor: a sessão visita três ofícios e não abre nada — [P-084-60] |
| coleta de sessões novas | 🧑 **ação física do Founder** (§10.5 do CLAUDE.md): abrir WhatsApp de seguradora e pedir serviço. Roteiro entregue |

---

## 3. Arquivos alterados

```text
$ git diff --stat 0f54761..15dfdd5
 43 arquivos, ~9.900 inserções, ~700 remoções

 backend/app/services/corridor_playbooks.py          o corredor único (73 rotas)
 backend/app/services/insurer_dispatch_service.py    derivação de teclas e forma
 backend/app/services/atlas/templater.py             infer_ramo_servico
 backend/scripts/rubrica.py                          a régua (C1–C20)
 backend/scripts/regua_motor.py                      leitura do Espelho (C13/C15)
 backend/scripts/replay.py                           classes de replay
 backend/scripts/padroes_de_servico.py               DESEMPATE (ONDA G)
 backend/scripts/higiene_do_corpus.py                máscara com prefixo (C19)
 backend/scripts/verificar_mutacoes.py               bateria de mutações
 backend/scripts/roteiro_de_coleta.py                NOVO — a ONDA G
 backend/scripts/conferir_respostas.py               regra A e sem_chute
 backend/tests/…                                     6 guardas novos
 docs/canon/PENDENCIAS.md                            P-084-40 … P-084-65
 docs/canon/reports/ROTEIRO-DE-COLETA.md             NOVO
 docs/canon/reports/INVENTARIO-DE-ROTAS.md           regenerado
```

---

## 4. Migrations

**N/A — justificado.** Esta SPEC não criou, alterou nem aplicou migration alguma.
Todo o trabalho é de corredor, régua e corpus derivado. A proibição nº 3 do
Founder (*"PROIBIDO ESCREVER NO BANCO"*) tornaria qualquer migration uma
violação: leituras foram exclusivamente `SELECT`.

---

## 5. Testes — com saída real

### 5.1 A bateria de mutações: **12 de 12 vermelhas**

```
$ python scripts/verificar_mutacoes.py
  -> 11 de 11 mutacoes EXECUTADAS e vermelhas
$ python scripts/verificar_mutacoes.py tests/test_o_roteiro_separa_bug_de_coleta.py
  -> 1 de 1 mutacoes EXECUTADAS e vermelhas
```

> 🔴 Cada mutação é **aplicada de verdade** no produto, o teste roda, a asserção
> **nomeada** tem de cair, e o arquivo é restaurado com conferência de conteúdo —
> `git diff --quiet` não serve, ele nem vê arquivo untracked.

### 5.2 Os guardas desta SPEC

```
test_a_regua_nao_tem_furo.py                             VERDE   (49 asserções)
test_a_arvore_do_pneu_decide_o_reboque.py                VERDE   (30)
test_a_atendente_sabe_conduzir_um_acionamento.py         VERDE
test_a_base_do_e13_conta_certo.py                        VERDE
test_a_maquina_de_lavar_vai_ate_o_fim.py                 VERDE
test_as_rotas_nao_se_borram.py                           VERDE
test_o_corredor_da_hdi_responde_a_ura_dela.py            VERDE   (23)
test_o_corredor_da_porto_responde_a_ura_dela.py          VERDE   (16)
test_a_tecla_tem_a_forma_da_seguradora.py                VERDE   (12)
test_as_quatro_perguntas_nao_tem_default.py              VERDE
test_o_roteiro_separa_bug_de_coleta.py                   VERDE   (12)
test_nenhuma_mutacao_foi_commitada.py                    VERDE   (7)
```

### 5.3 A saída da régua, rota a rota

```
$ python scripts/medir_rota.py --todas --com-espelho
  43 rotas com corpus · 30 sem corpus
  AAA (>=95%): 19 de 43
  media ponderada: 88.4%
  pior rota: hdi/residencial/eletricista 57/106 = 54%
```

**As 19 AAA:** `yelum/residencial/encanador` **106/106** ·
`yelum/auto/socorro_mecanico` **88/88** · `allianz/residencial/encanador`
**106/106** · `porto/residencial/encanador` 104/106 · `hdi/auto/socorro_mecanico`
86/88 · e mais 14 em 102/106.

### 5.4 🔴 O que continua vermelho, e a prova de que é anterior

**39 arquivos da suíte geral estão vermelhos** — e cada um foi conferido no
commit ANTERIOR ao meu trabalho e já estava vermelho lá. Três oscilam
(`spec073`, `template_de_artefato`, `zurich_cobranca`): dependem de ambiente.

> ⚠️ **INFERÊNCIA, não fato:** eu não afirmo que esses 39 são inofensivos. Afirmo
> que **esta SPEC não os criou**, e isso é medido.

---

## 6. O que falta, e de quem é

📊 Estado final medido — as cinco famílias de ponto que faltam:

```
apelidos do jeito que o cliente fala .. 36 rotas   🧑 vocabulário de segurado
>=2 sessoes distintas ................. 15 rotas   🧑 +1 sessão da rota
o cliente recebe protocolo+dia+periodo  13 rotas   🧑 sessão que chegue ao fim
a mais recente tem <180 dias .......... 12 rotas   🧑 coleta nova (a URA muda)
a ROTA foi percorrida ate o fim ....... 11 rotas   🧑 idem
o freio casa >=1 tela REAL ............ 10 rotas   🧑 sessão com confirmação
o handoff casa >=1 tela REAL ..........  5 rotas   🧑 idem
zero orfas funcionais .................  1 rota    🤖 [P-084-60]
```

🔴 **`teste nomeia a rota` saiu da lista inteiramente.** Nenhuma rota perde ponto
hoje por falta de guarda.

⚠️ **E há um limite estrutural que precisa estar escrito:** o item *"apelidos do
jeito que o cliente fala"* é o maior buraco (36 rotas) e vai continuar difícil —
**o Espelho é o chat da CORRETORA com o AutoBrokers**. Quem digita é o corretor,
relatando. A palavra do segurado chega de segunda mão. Isso é *por construção*,
não por descuido — e é por isso que **não foi comprado com tautologia**: escrever
`"guincho": "guincho"` fecharia a conta em três serviços e a régua estaria
medindo strings no próprio código outra vez [P-084-63].

**Tudo o que ficou está em [`PENDENCIAS.md`](../PENDENCIAS.md), P-084-40 a
P-084-65**, cada uma com o que destrava, de quem é e o que custa esquecer.

---

## 7. Segurança e PII

### 7.1 🔴 O achado: o mascarador não alcança o CÓDIGO

O corpus é mascarado, e há guarda para isso — `test_o_corpus_nao_vaza_pii`,
📊 **20 asserções verdes**. **Comentário e fixture não passam pelo mascarador.**
Quando alguém transcreve uma tela real para explicar um passo, o dado do segurado
entra no repositório por uma porta que nenhum guarda vigiava.

📊 Medido em 23/08/2026 com `scripts/auditar_pii_no_codigo.py` (NOVO), varrendo
`git ls-files`. A conta se moveu duas vezes, e as duas merecem estar escritas:

```
166  primeira varredura, sem filtro estrutural
 85  com o filtro — 🔴 e ele engolia placa REAL
101  com o filtro corrigido: a medida honesta
 89  depois da limpeza desta SPEC — 12 identificadores saíram
```

> 🔴 **O filtro carimbava de sintético exatamente o que o script existe para
> achar.** A regra *"poucos dígitos distintos → é inventado"* valia para tudo, e
> uma placa real de forma `LLLDLDD` com dígitos `9`,`5`,`9` passava por
> fabricada. Placa tem 4 dígitos; repetir um é comum. A regra agora só vale para
> valor longo (telefone, CPF). **Um detector que se engana para menos é pior que
> nenhum: ele dá licença.**

### 7.2 O que foi limpo nesta SPEC

📊 **12 identificadores removidos, 38 arquivos reescritos**, com substituição
que **preserva a forma** para as lições não morrerem — a placa mascarada e a
placa do caso mudaram *juntas*, senão o teste que prova
`"AA#-###9" != "AAA9A59"` deixaria de provar. Todos os testes afetados foram
rodados: **14 verdes**.

🔴 **E a limpeza quebrou três guardas, que eu achei medindo, não supondo.** As
variantes `qjq0a91` (minúscula) e `QJQ-0A91` (com hífen) não estavam na primeira
substituição. Os três voltaram ao verde.

⚠️ **A prova de que os outros 7 vermelhos não são meus** foi feita num
`git worktree` em `HEAD`, **com linha de controle**: um teste que eu sabia verde
rodou verde lá, então o worktree executava de verdade. Sem esse controle, um
`cd` que falha faz *tudo* parecer "já vermelho antes" — e foi exatamente o que
aconteceu na primeira tentativa, com o worktree que nem chegou a ser criado.

### 7.3 O que fica, e por que não foi feito aqui

📊 **89 identificadores em 117 arquivos.** ⚠️ Boa parte **não é dado de pessoa**:
número publicado de seguradora (`0800`, central de atendimento) tem forma de
telefone e é endereço comercial. Um deles está anotado no corredor dizendo
exatamente isso, para o próximo leitor não "consertar" o que está certo.

🔴 A varredura completa **cruza dez SPECs e mexe em fixture que outros guardas
comparam entre si** — trocar de um lado só quebra a comparação. É mudança além
do texto desta SPEC: está no [`CHANGE-ADDENDA.md`](../CHANGE-ADDENDA.md) como
**ESSENCIAL**, aguardando autorização (§11), e em [P-084-66].

### 7.4 O resto

- 🔴 **Um vazamento de sessão anterior foi corrigido nesta** (`b4091c5`): um
  telefone real havia sido escrito num comentário. O padrão virou regra — todo
  diagnóstico com dado de segurado sai com dígitos mascarados por `#`.
- O mascarador ganhou o C19: 📊 o protocolo da PORTO tem PREFIXO e a máscara só
  mordia o rabo dele. Cinco corpora **regenerados e conferidos linha a linha**.
- ⚠️ **O auditor nunca imprime o valor** — só a forma (`LLLDLDD`) e uma sombra
  de 8 dígitos. Auditar vazamento imprimindo o vazamento é repeti-lo com mais
  leitores.
- Nenhum segredo, token ou credencial aparece em código, teste ou documento.

---

## 8. Canário Amandus → Resulta → AutoFleet

⚠️ **NÃO EXECUTADO — e é proibição do Founder, não omissão.**

O canário exige **ligar agente** e **enviar mensagem**, as duas primeiras
proibições desta SPEC:

> *"PROIBIDO LIGAR OS AGENTES DE ATENDIMENTO — só a corretora clicando 'Ligar
> Agente'"* · *"PROIBIDO ENVIAR MENSAGEM a qualquer número, em qualquer canal"*

O substituto executado, e o que ele prova e não prova:

| | prova | não prova |
|---|---|---|
| **replay offline** contra 43 corpora reais | que o corredor RESPONDE a tela real, na forma que a seguradora aceita | que a mensagem SAI pelo canal |
| **12 mutações** aplicadas no produto | que os guardas veem o que dizem ver | que a URA aceita a resposta hoje |

🔴 **RECOMENDAÇÃO:** o canário roda quando o Founder liberar `ligar agente` +
`enviar mensagem` **com a AMANDUS SEGUROS**, avisada antes. A rota sugerida é
`yelum/residencial/encanador` (106/106) — a de maior evidência no acervo.

---

## 9. Riscos remanescentes

| # | Risco | Gravidade | Mitigação |
|---|---|---|---|
| 1 | **a URA muda e o corredor não sabe** — 12 rotas têm acervo com mais de 180 dias | 🔴 alta | a régua já pune a idade; a coleta nova é 🧑 |
| 2 | `hdi/residencial/eletricista` em 54% por sessão exploratória mal classificada | ⚠️ média | [P-084-60], decisão de corpus |
| 3 | slots `*_opcao` da zurich com nome que mente | ⚠️ média | [P-084-61], mudança separada e medida |
| 4 | 39 arquivos vermelhos na suíte geral, anteriores a esta SPEC | ⚠️ média | fora do escopo; nomeados |
| 5 | 11 rotas com RÓTULO NÃO VISTO — pode ser rótulo errado no corredor | ⚠️ média | o roteiro dá o controle para descobrir na primeira tentativa |

---

## 10. Declaração final

**FATO.** 21 consertos de régua e 7 ondas de rota foram executados, medidos e
commitados. 19 rotas em AAA de 43 com corpus; média ponderada 88,4%. 12 de 12
mutações vermelhas. 30 rotas sem corpus, todas com veredito medido e nenhuma
suspeita de bug. Nenhum motor paralelo foi criado. Nenhuma das seis proibições
foi violada.

**INFERÊNCIA.** As rotas AAA *devem* levar um acionamento do começo ao fim sem
humano — mas isso é inferido de replay contra corpus gravado, **não** de um
acionamento real. A distância entre as duas coisas é exatamente o canário da §8.

**RECOMENDAÇÃO.** Liberar o canário na Amandus, com aviso prévio, na rota
`yelum/residencial/encanador`. E despachar a coleta do
[`ROTEIRO-DE-COLETA.md`](ROTEIRO-DE-COLETA.md): **é ela, não código, que move os
próximos pontos.**

> 🔴 **A LIBERAÇÃO É DO JUIZ.** Este relatório é a pré-condição do gate, não o
> gate. Nenhum merge na `main` foi feito.
