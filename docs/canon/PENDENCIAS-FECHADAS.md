# PENDÊNCIAS FECHADAS — arquivo

> ⛔ **Não entra no bootstrap do `CLAUDE.md` §2.** Existe para consulta por
> número, e para que ninguém reexecute trabalho pronto.
>
> Separado de [`PENDENCIAS.md`](PENDENCIAS.md) em 25/08/2026.


## P-05 · ✅ A AutoFleet tem agente ativo sem prompt nenhum — **NÃO É MAIS VERDADE**

### ✅ 24/08/2026 — FECHADA: o fato mudou, e a pendência ficou descrevendo o passado

📊 Medido no banco em 24/08 (`SELECT` em `agents` × `companies`): o agente `c95de02a`
tem **638 caracteres** de `agent_system_prompt`, e o `agent_role` dele é **`core`** — o do
chat interno da corretora, **não** o que fala com segurado. E os quatro agentes
`attendance` do produto (AMANDUS, Blueprint Studio, AutoFleet, Resulta) estão todos
`is_active = false`.

⚠️ **O que fica de lição, e vale para as ~328 pendências abertas:** esta não foi
consertada por ninguém que a lesse — o mundo mudou por baixo dela, e ela continuou
aberta afirmando um fato morto. **Pendência que ninguém remede envelhece para mentira.**
🔴 É a razão da regra de drenagem do `PROTOCOLO-AUTOBROKERS-AAA.md` §1: toda SPEC que
começa **fecha ou re-justifica** as pendências que ela toca.

**O registro original, preservado:**

📊 Agente `c95de02a` — `is_active = true`, `agent_enabled = true`,
**`agent_system_prompt = NULL`**. Com o defeito B1, é ele que responderia o
segurado: um agente ativo sem uma linha de instrução, sem nenhuma trava.
**Não está entre os doze bloqueios da SPEC-063.**
- **Dono:** 🤖 SPEC-063 Bloco A

> ⚠️ 🔴 **RENUMERADAS em 24/08/2026.** As quatro pendências abertas hoje nasceram como
> **P-180 a P-183** — quatro números que **já existiam** neste arquivo (linhas 5482, 5512,
> 5651 e 5673). Um auditor externo achou uma das colisões; medindo, eram **quatro**.
> 📊 O maior número em uso era **P-222**; as novas passaram a ser **P-223 a P-226**.
> **A causa é estrutural e continua aberta: não há nada que impeça a próxima colisão.**

## P-90 · ✅ RESOLVIDO em 04/08/2026 — a aprovação é o botão LIGAR AGENTE

📊 `build_portal_params` cravava `"confirm": False`, e uma busca no repositório
inteiro não achava **nenhum** caminho que ligasse `confirm=True`. O acionamento
percorria o formulário todo, chegava na tela de confirmação e parava. 📊 É o que
explica os 9 acionamentos que "chegaram na confirmação (80%)" e nunca viraram
protocolo.

Esta entrada propunha construir um passo de aprovação (tela, WhatsApp do
suporte, ou os dois). **O Founder respondeu outra coisa, e a resposta dele é
melhor**, porque tira uma trava em vez de somar uma:

> *"A questão de trava no final sempre foi por um motivo exclusivo. Eu estava
> fazendo os testes no meu próprio celular. Se não tivesse a trava, seriam
> feitos os acionamentos dos serviços de vidro de verdade."*
> *"Quero tudo pronto e funcionando, mas o agente de atendimento tem que
> continuar desligado. Só podem funcionar se clicar em LIGAR AGENTE."*

O que passou a valer: **um interruptor só, `agents.is_active` do agente de
atendimento.** `portal_tool` e `insurer_dispatch_tool` perguntam
`attendance_agent_active` antes de agir e derivam dela o `confirm` do portal e o
envio real do corredor de WhatsApp (regra única em
`insurer_dispatch_service.acionamento_liberado`). Provado nos dois sentidos em
`backend/tests/test_o_que_acontece_quando_o_agente_liga.py`.

📊 Em 04/08/2026 os quatro agentes `attendance` estão `is_active=false` — nada
sai enquanto ninguém clicar.

---

## P-98 · ✅ Os 23 documentos destravaram — mas o buraco do varredor continua

> **📊 Reconferido em 07/08/2026, e o número mudou para melhor.** Deixar o texto
> antigo mandaria o próximo leitor caçar um problema resolvido — e o pior tipo
> de pendência é a que já foi feita e ninguém apagou.

```
                     05/08/2026        07/08/2026
fetching                 23      🔴         0      ✅
ingested                  8                29   (11.409 chunks)
discovered                4                 6
                                    última mudança: 06/08
```

**O crédito voltou e a ingestão andou sozinha.** 📊 São hoje 29 documentos
indexados — 25 de condições gerais, 5 de manual do segurado, 5 de circular
SUSEP, cobrindo auto, residencial, vida, empresarial, condomínio e
responsabilidade civil, de 8 seguradoras.

### 🔴 O que NÃO se resolveu, e é o que valia a entrada

O buraco do varredor continua aberto — ele só não está machucando **agora**:

📊 `insurance_corpus.py:654-660` — a função `vencidos()`, que é a **única** que
reencontra trabalho pendente, procura documentos em `('ingested', 'discovered',
'unreachable')`. **`fetching` não está na lista.**

`ingerir()` marca `fetching` **antes** de sair para a rede. Se a chamada falha,
o documento fica nesse estado transitório **para sempre** — aprovado pela
curadoria, invisível para o varredor, e sem nenhum alarme. Da próxima vez que o
crédito acabar (e ele já acabou uma vez), acontece de novo, igual.

> É a mesma lição que este repositório já aprendeu duas vezes — na reconciliação
> de acionamento órfão e no vigia de handoff: **um estado que só é observado
> quando nasce não é observado.**

### 🟠 E uma anomalia nova, ainda não explicada

📊 Dos 6 documentos em `discovered`, **quatro nunca foram conferidos**
(`last_checked_at` nulo) e têm `next_check_at = 2026-07-25` — vencidos há 13
dias. `vencidos()` ordena por `next_check_at` crescente, então eles deveriam ser
os **primeiros** da fila, não os últimos.

💭 Duas hipóteses, nenhuma medida: ou o varredor não roda de fato em produção
(o portão `smith_worker.py:223` desiste sem `FIRECRAWL_API_KEY` **no worker**),
ou existe caminho que consome o documento sem gravar `last_checked_at`. Os
outros 2 têm erro de origem (HTTP 408 e 500 na Bradesco), que não é nosso.

**O que destrava:** 🤖 o varredor de órfãos — não precisa de saldo nem de
decisão. E 🤖 medir qual das duas hipóteses acima é a certa, antes de consertar
a errada.

### O agravante que ninguém veria

📊 `insurance_corpus.py:654-660` — a função `vencidos()`, que é a **única** que
reencontra trabalho pendente, procura documentos em `('ingested', 'discovered',
'unreachable')`. **`fetching` não está na lista.**

`ingerir()` marca `fetching` **antes** de sair para a rede. Se a chamada falha,
o documento fica nesse estado transitório **para sempre** — aprovado pela
curadoria, invisível para o varredor, e sem nenhum alarme.

> É a mesma lição que este repositório já aprendeu duas vezes — na reconciliação
> de acionamento órfão e no vigia de handoff: **um estado que só é observado
> quando nasce não é observado.**

**O que custa esquecer:** o corpus normativo é a base para responder cobertura
pelo contrato, e não pela prática. Ele agora EXISTE — 📊 11.409 trechos
indexados. O agente continuar dizendo "normalmente é coberto" deixou de ser
falta de acervo e passou a ser falta de ligar o acervo ao atendimento.

⚠️ **A lição que fica para a próxima falta de crédito:** mover documentos presos
de volta para um estado varrido faz o sistema tentar de novo — e, sem crédito,
produzir uma falha por documento por rodada. A saída correta é um estado
**visível e não retentável** até o saldo voltar. Ver
`DESENHO-ATUALIZAR-SEM-ESTRAGAR.md`, §5 item A.

---

## P-117 · ✅ RESOLVIDO — a captura da AutoFleet voltou, e está provada

📊 06/08/2026 17:42Z, `attendance_transcripts`: **124 linhas na última hora**, a
mais recente **6 segundos** antes da consulta. `source='live'`, com sessão,
entrada e saída, texto e áudio. Conversas reais de sinistro (perito, oficina,
pneu, roda) — e `attendance_sessions` com 15 sessões em 2 horas.

A mensagem de teste que o Founder mandou está gravada inteira:

```
17:29:38  in   "Boa tarde Regina. Tô só enviando uma msg de teste"
17:31:16  out  "opa"
17:31:21  out  "boa tarde"
```

**Isto encerra o P-110, o P-114 e o P-116** na parte que era acionável: o
conserto do webhook (`f81e24e`) restaurou a captura em produção, e o reconector
novo religou a Resulta sozinho, com webhook e os quatro eventos.

⚠️ O que NÃO estava quebrado, e eu quase tratei como se estivesse:

- `observed_events` parado desde 04/08 **é o comportamento correto**. Ele guarda
  o HISTORY_SYNC, que só chega no pareamento. Conversa ao vivo vai para
  `attendance_transcripts` — são dois acervos, não um com defeito.
- `conversations` vazia **é o comportamento correto**. Ela nasce no pipeline do
  agente, e `observer_tap` consome o evento enquanto o agente está desligado.
  Com os quatro agentes `is_active=false`, a tela "Atendimentos → Conversas"
  vazia é a decisão do Founder funcionando, não uma falha.

## P-120 · ✅ DECIDIDO — o "melhor jeito de atender" é GLOBAL, não por corretora

Eu sugeri que o agente aprendesse o tom de cada corretora a partir das respostas
capturadas da equipe dela. **O Founder recusou, e a razão dele é melhor que a
minha proposta:**

> *"Não sei se pode gerar confusão. Ter a melhor forma de atender todas as
> corretoras e todas terem o melhor seria mais valioso. Empatia, humanizada, se
> colocar à disposição, ser educada, agir como um humano. Essa melhor forma deve
> ser global e não só de uma corretora. Todas devem usufruir do melhor que temos
> globalmente."*

Fica registrado como decisão, não como pendência de código: o aprendizado do
Observador alimenta a conduta **global** do produto. Uma corretora que atende mal
não deve ensinar o agente a atender mal — nem para ela mesma.

Isto NÃO impede personalização de superfície (nome do atendente, tom escolhido no
painel, mensagem de abertura), que já existe em `Personalização → Agente de
Atendimento` e continua sendo da corretora.

- **Destrava:** nada. É decisão tomada.
- **Custa se esquecer:** alguém reabre a ideia daqui a três meses sem saber que
  já foi decidida, e o produto ganha uma inconsistência que ninguém pediu.

## P-121 · ✅ RESOLVIDO — a classe de erro que matou o espelho existia em mais 3 lugares

📊 06/08/2026. O espelho do chat não criava conversa nenhuma. O `/health` dizia
`espelho_no_chat: true` e o Redis contava a verdade:

```
espelho_contadores: {"erro:ImportError": 2255}
```

A ponte fazia `from app.services.integration_service import integration_service`.
**Esse nome não existe** — o módulo exporta a fábrica `get_integration_service(client)`.
2.255 tentativas mortas no import, dentro do `try/except` que protege a captura.

**Por que o teste não pegou:** eu havia DUBLADO o módulo com
`falso.integration_service = _Servico()` — a forma que eu imaginava. Todo teste
ficou verde contra uma API inexistente. *Um dublê valida a sua suposição, não a
realidade.*

A varredura que nasceu disso (`test_todo_import_aponta_para_algo_que_existe`,
311 módulos, sem importar nada) encontrou **mais três em produção**:

| onde | import | consequência |
|---|---|---|
| `dispatch_router.py:164` | `integration_service` | o aviso "o segurado NÃO recebeu o protocolo" nunca chegava ao humano |
| `dispatch_router.py:169` | `whatsapp_service` | idem — segundo import do mesmo bloco |
| `whatsapp/service.py:54` | `wa_send_retry` | o nome **não existia em lugar nenhum**; o módulo quebrava ao ser importado |

Os três estavam dentro de `try/except` ou em módulo não importado — por isso
nunca deram erro visível. O primeiro é o mais caro: toda vez que o protocolo
falhava, o alerta ao humano falhava junto, e o log dizia "alerta não saiu" como
se fosse rede.

Todos corrigidos. `wa_send_retry` passou a existir de fato em
`whatsapp_service.py`, com a política que o comentário já descrevia (3
tentativas, espera exponencial, só falha transitória, última falha sobe).

- **Destrava:** nada. Resolvido e guardado por teste.
- **Custa se esquecer:** era exatamente o que já custava — funcionalidade morta
  em silêncio, com log que parecia outra coisa.

---

## P-126 · ✅ RESOLVIDO — o Lapidador reescrevia com as regras de outra época

Registrado por completude, porque o padrão vale mais que o caso.

Duas peças escreviam o mesmo playbook: `attendance_distiller._STAGE2_SYSTEM`
(primeira vez) e `prompt_optimizer._REFLECT_SYSTEM` (reescreve o que está
ativo). O primeiro ganhou três campos e quatro proibições em 07/08/2026. O
segundo não ganhou nada, e pedia um JSON de 8 chaves — **o que ele não pede,
some do playbook que está no ar**.

📊 A janela real: só entre 3h e 10h UTC, no máximo uma vez por semana. E
`_mudancas` aparece em **0 dos 18 playbooks** — ele nunca rodou. O risco não era
iminente; era certo e sem data.

**A causa não era o texto: era existirem duas descrições da mesma coisa.** O
conserto não foi reescrever o segundo prompt com as mesmas regras — foi fazê-lo
`import`ar o primeiro (`REGRAS_DO_PLAYBOOK`). Regra nova já nasce valendo para
os dois.

**Onde mais isso pode estar acontecendo:** em qualquer par de peças onde uma
escreve e outra reescreve o mesmo objeto. Não foi varrido.

- **Guarda:** [`test_quem_lapida_obedece_quem_escreveu.py`](../../backend/tests/test_quem_lapida_obedece_quem_escreveu.py)
  — lê o import por **AST**, não por busca de texto: `REGRAS_DO_PLAYBOOK` citado
  num comentário passaria numa busca por substring e não importaria nada.

---

## P-129 · ✅ RESOLVIDO — a marca da campanha era uma constante congelada

`aplicar.py:51` tinha `MARCA = "destilacao_max_29_07_2026"`, escrita à mão e
nunca trocada. 📊 As 1.941 cartas da campanha de 04/08/2026 foram gravadas com
a marca de 29/07: pelo campo que existe justamente para separá-las, as duas
campanhas são a mesma coisa.

E `CURADORIA-POR-SUBAGENTES.md:236` manda conferir a campanha por
`pii_check->>'por' = '<marca>'` — a conferência rodava, devolvia um número, e o
número somava as duas. **Um passo de conferência que responde com confiança à
pergunta errada é pior que passo nenhum: ele encerra a dúvida.**

O conserto não é um valor novo — é tirar o valor de onde alguém precisa lembrar
dele. `marca_de_hoje()` vem do calendário e `--marca` nomeia a campanha à mão,
como `aplicar_seguradoras.py` já fazia. `aplicar_sql.py` tinha a MESMA linha
congelada e agora **importa** a resposta em vez de manter a segunda cópia dela:
duas cópias congeladas do mesmo valor errado não são um defeito com duas faces,
são o defeito duas vezes.

- **Guarda:** [`test_a_marca_da_campanha_nao_e_congelada.py`](../../backend/tests/test_a_marca_da_campanha_nao_e_congelada.py)
  — controle: duas datas produzem duas marcas. Uma função que devolvesse sempre
  a mesma string passaria em tudo o mais.
- **Continua aberto · 🤖** as 1.941 cartas de 04/08 seguem com a marca errada
  no acervo. Nada foi reescrito no banco. Separá-las exige `created_at`, não o
  marcador — e é justamente essa a informação que se perdeu.


---

## P-131 · ✅ MEDIDO — o caminho da SUSEP está vivo; o 404 tinha mudado de endereço

📊 Verificado ao vivo em 08/08/2026, sem autenticação.

### O 404 do P-22 não era morte, era endereço errado

```
www2.susep.gov.br/download/menuestatistica/SES/BaseCompleta.zip    404
www2.susep.gov.br/redarq.asp?arq=BaseCompleta%2ezip                200
   application/x-zip-compressed · 568.932.978 bytes (542,6 MB)
   last-modified: Mon, 03 Aug 2026 · ETag presente · accept-ranges: bytes
```

O tamanho bate com o da SPEC-066. `accept-ranges` e ETag confirmam que a
detecção por sentinela descrita nela funciona.

### O repositório de produtos funciona, e a armadilha é a porta

```
GET  .../REP2/Produto.aspx              200 — mas é a tela de LOGIN (a pegadinha)
GET  .../REP2/Produto.aspx/Consultar    200 — formulário PÚBLICO, um campo
POST .../REP2/Produto.aspx/Consultar    200 · 72.638 bytes · 72 versões · 1,08 s
GET  .../DownloadConsultaPublica/509527 200 application/pdf · 2.089.937 B
```

A resposta traz `Sociedade`, `RAM: 05 | AUTOMÓVEL - CASCO` e `Situação` — o
código de ramo que a SPEC-066 usa como ponte para o SES existe mesmo.

### P-22, metade resolvida

📊 Baixada a documentação oficial das tabelas do SES (734.925 B):
`sinistro_ocorrido` aparece **0 vezes**; `sinistro_retido` e `sin_dir` aparecem.
**A tese está confirmada.** A outra metade — se `retido` está zerado desde 2013 —
exige baixar os 542 MB e continua aberta.

### 404 mapeados, para ninguém retestar às cegas

`REP2/ConsultaPublica.aspx` · `REP2/Produto.aspx/ConsultarPorSociedade` ·
`menumercado/rcorretores/pesquisa.asp` · todo o CMS antigo `susep.gov.br/menu/…`
(migrou para `gov.br/susep`).

### Varredura em massa continua impossível, e não por educação

📊 O formulário público tem **um único campo** (`numeroProcesso`) e
`ConsultarPorSociedade` dá 404. **Não existe enumeração.** A ingestão dirigida da
SPEC-066 §A.2 não é uma escolha de bom comportamento: é a única via.

---

## P-142 · 🟢 `vigente` e `faceta` já têm escritor — falta o LEITOR

📊 Até 08/08/2026 os dois campos tinham **índice de payload criado no Qdrant e
nenhum escritor** (o comentário em `qdrant_service.py` dizia isso com todas as
letras). O maestro da SPEC-070 fechou essa ponta: `_ingerir_sync` agora grava
na raiz `vigente`, `faceta`, `unit_id`, `parent_id`, `doc_kind`,
`susep_process` e `effective_from`, um jogo por pedaço.

**Falta a outra ponta.** A §6 da SPEC-070 pede duas buscas com orçamento
próprio:

```
busca 1  namespace=normative  ∧ (insurer_key=X ∨ ausente) ∧ vigente
busca 2  namespace=cards      ∧ (insurer_key=X ∨ ausente)
```

⚠️ E o filtro de vigência tem de ser **de dois braços** (`vigente=true` OU
chave ausente). Sem o segundo braço ele apaga as 12.063 cartas, que não têm
essa chave e nunca terão.

- **Destrava:** nada de fora — é trabalho em `search_service`/`qdrant_service`.
- **Dono:** 🤖 execução.
- **O que custa esquecer:** hoje nada quebra, porque a versão revogada sai do
  índice na ingestão (D-Acervo-02). O custo aparece no dia em que uma remoção
  falhar: 📊 `delete_document` já respondeu "removi" com o Qdrant fora do ar, e
  aí as duas versões respondem com a mesma autoridade e nada no filtro separa.


### ✅ 15/08/2026 — FECHADA pela SPEC-072 Bloco 1

O leitor existe. `_filtro_de_faceta` em `qdrant_service.py`, com os **dois
braços** que esta pendência exigia — e o segundo braço tem número:

```
só o filtro de faceta salva  12.534 cartas de conversa + 1.139 trechos de contrato
mutação (um braço só)         os mesmos 13.673 somem, e o teste FALHA
```

⚠️ E o aviso desta pendência valeu para um campo que ela não previa: `temas`
tinha o **mesmo** defeito uma camada antes (P-177), e 22,8% das cartas não o
têm. Os dois filtros nasceram juntos, com o mesmo desenho.

Teste: `backend/tests/test_o_filtro_de_faceta_tem_dois_bracos.py` — ele
**executa** o filtro contra um acervo de mentira, em vez de afirmar que a string
`IsEmptyCondition` aparece no código.

---

## P-143 · ✅ A âncora certa não prova a afirmação certa — RESOLVIDO em 09/08/2026

📊 Achado por um auditor de ancoragem em 08/08/2026, no LOTE 1.

A auditoria da §6.5 confere **de onde a carta veio**. Ela não confere **o que a
carta acrescentou ao trecho**. São defeitos de famílias diferentes, e o segundo
passa inteiro pelo primeiro:

> `condominio_CARTAS.jsonl:185` afirma *"R$ 1.200,00 no Prata e R$ 1.800,00 no
> Ouro"* como se fossem os tetos dos planos. No contrato os dois valores estão
> nas cláusulas **34.6 e 34.7, ambas de LIVRE ESCOLHA** — a carta generalizou
> uma condição. O endereço está correto; um corretor que o abrir encontra o
> número **e a qualificação que a carta comeu**.

É a regra 7 da §10.3 (*o teste da cauda*) escapando pela porta que a auditoria
de âncora não vigia. E é exatamente o defeito que mais machuca: corpo fiel,
cauda inventada.

### 📊 O LOTE 2 mediu o alcance disto, e ele tem nome: **o adjetivo enxertado**

Dois auditores da Allianz, em lotes diferentes e sem se falarem, acharam o mesmo
caso — e nenhum dos três vereditos tinha casa para ele:

> *"Vendaval é cobertura **OPCIONAL** do Allianz Residência."* O escopo está
> literal no trecho citado, então o veredito é `ok`. Mas a palavra **opcional**
> não aparece em nenhum dos cinco trechos. **Um corretor que abrir esse endereço
> para provar "é opcional" não acha a prova.**

E é a classe de palavra mais cara de errar: `opcional` × `básica` decide se o
cliente **tem ou não** a cobertura.

📊 Medido em 09/08/2026 sobre as 1.536 cartas da Allianz, com um detector de
afirmação de contratação:

```
cartas que AFIRMAM ser básica/opcional/adicional     110
cujo trecho citado não traz nenhuma marca disso       52   (47%)
```

⚠️ **Esses 52 não são 52 defeitos confirmados.** O detector é grosseiro e erra
para os dois lados: a primeira versão dele acusou 182, e entre elas cartas em
que `Facultativa` era o **nome da cobertura** (RCF-V), não uma afirmação de
opcionalidade. O número serve para dimensionar o trabalho, não para condenar
carta. Só leitura decide.

- **Destrava:** nada de fora. É uma segunda auditoria, com outro prompt: dado o
  trecho e a carta, *a carta afirma algo que o trecho não sustenta, ou omite uma
  condição que o trecho impõe?*
- **Dono:** 🤖 execução.
- **Sugestão de escopo, na ordem:** (1) as ~110 cartas que afirmam
  básica/opcional/adicional, nas duas seguradoras — é o defeito com nome, dono e
  consequência clara; (2) as cartas de `limite` e `franquia`, onde um número
  vira afirmação e a qualificação some com mais facilidade.
- **Sugestão de veredito:** os três atuais não bastam. Dois auditores propuseram
  o mesmo quarto, com nomes diferentes (`ok_parcial`, `ok_com_enxerto`): a carta
  está ancorada, **e** carrega uma afirmação secundária sem lastro. Hoje isso
  passa como `ok` e não deixa rastro.

### ✅ RESOLVIDO — 09/08/2026

Três auditores leram as 129 cartas apontadas, uma a uma:

```
reescrever            72     a afirmação não tem prova em nenhum dos 5 trechos
provado_no_vizinho    38     a prova está a um pedaço de distância
provado               19     falso positivo do detector
remover_carta          0
```

📊 As 72 foram reescritas e aplicadas. Conferência depois: o detector aponta 57,
e **os 57 são exatamente os 57 já julgados como corretos** — zero pendentes.

**Os 38 `provado_no_vizinho` NÃO foram movidos**, e o motivo é um aviso que um
auditor deu antes de eu aplicar em lote:

> *"Em 19 deles o **escopo** está corretamente ancorado no endereço citado e é só
> a **natureza** que mora no vizinho. Trocar o endereço conserta a prova do
> rótulo e **quebra a prova do escopo**."*

Trocar teria sido um defeito por outro. Fica aberto o caso de a carta poder
citar **dois** trechos — hoje o formato só aceita um.

**A regra virou §10.3.1-C da SPEC**, com a redação literal que os três auditores
convergiram. O próximo lote nasce com ela.

**O que os auditores acharam de mais grave**, e que a auditoria de ancoragem
nunca pegaria:
- uma carta afirmava que *"a RC Condomínio exclui expressamente a
  responsabilidade do síndico"* — **fato de contrato que não está em trecho
  nenhum**. Vira argumento de venda errado.
- outra dizia que a Assistência Funeral do Porto Vida *"é cobertura básica"*,
  quando o contrato diz *"de acordo com o Plano contratado"*. É o erro na
  direção mais cara: promete um funeral que talvez não tenha sido contratado.
- duas do Allianz Corporate tinham o rótulo **provavelmente errado**, não só sem
  prova: são complementares (obrigatórias) e foram chamadas de adicionais. O
  auditor retirou o classificador em vez de trocá-lo, e 💭 marcou como inferência
  — vale conferência humana.
- **O que custa esquecer:** a carta responde com um número certo e uma condição
  errada. O corretor repassa, o cliente contratou o outro plano, e a conferência
  do endereço **confirma** a carta em vez de desmenti-la.

---

## P-154 · ✅ RESOLVIDA — o boleto da Zurich baixa pela função do portal

**Aberta em:** 13/08/2026 · **Dono:** 🤖 execução, numa tentativa em outro dia

📊 `GerarBoleto` devolveu **404 em toda tentativa da journey**, enquanto a MESMA
chamada funcionou na captura manual do founder. Medido com a lista como linha de
controle (200 antes e depois, em todas as rodadas):

```
fetch, cabecalho minimo ............ 200, mas devolve HTML
fetch, cabecalho igual ao do jQuery  404
sem o _=timestamp .................. 404
data com %2F ....................... 404
$.ajax DO PROPRIO jQuery da pagina . 404
CONTROLE: a lista, no mesmo momento  200 com 33 KB   <- sessao viva
```

**Não é** cabeçalho, cliente HTTP, sessão nem ritmo. E os parâmetros são
idênticos aos da captura — conferidos contra o código do próprio portal
(`GerarBoleto2` em `/Scripts/Corretor/ParcelaVencida/Index.js`), incluindo o
`FormatDate`, que dá a mesma data pelos dois campos.

**A hipótese que sobra é regra de negócio:** o founder emitiu a 2ª via dessa
parcela em 13/08 e o portal respondeu *"o boleto estará registrado e disponível
para pagamento no dia 14/08/2026"*. Uma segunda emissão da mesma parcela, no
mesmo dia, pode ser recusada — e 404 é como este portal diz "agora não".

**RESOLVIDA em 14/08/2026.** Não era regra de negócio nem instabilidade: era
insistir em **reconstruir a URL**. A solução é chamar `GerarBoleto2` — a função
do próprio portal, que mora no view model do Knockout — com um objeto montado a
partir da lista. 📊 Baixou **107.288 bytes, `%PDF`**.

A journey tenta, nesta ordem: chamada direta → `GerarBoleto2` → clique no botão.
Os dois últimos são o fallback de navegação visual da SPEC-033 — que eu deveria
ter usado horas antes, em vez de variar cabeçalho.

**O que custa esquecer:** nada silenciosamente — a journey **retém** o item com
o motivo escrito e ele vai para a fila humana. Mas a Zurich não fecha o ciclo
sozinha enquanto isto não resolver.

---

## P-177 · 🔴 `temas` não chega ao índice — 14.264 cartas rotuladas para nada

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução
**Achada** pelo juiz crítico do BLOCO 0 da SPEC-072.

O commit `3f6d1b4` rotulou **14.264 cartas** com tema. A migration
`20260815_02_a_carta_ganha_tema.sql:76` criou `knowledge_cards.temas text[]` com
índice **GIN**. 📊 Hoje, `temas` não aparece em nenhum ponto do caminho do RAG:

```
knowledge_extras de publish_card_sync   attendance_distiller.py:648-683   ausente
select de reindexar_acervo              _ler_publicadas                    ausente
select de publicar_lote_sync            curadoria_cartas.py                ausente
search_service.py · qdrant_service.py   grep "temas"                       ZERO
índice de payload no Qdrant             qdrant_service.py:88-98            não existe
```

**O rótulo existe no Postgres e o índice não sabe dele.** É o mesmo defeito que
a SPEC-072 diagnosticou para `faceta` — *"o rótulo é produzido e nenhum leitor o
alcança"* — só que uma camada antes: a `faceta` ao menos **chega** ao payload do
Qdrant e tem índice lá; `temas` não chega a lugar nenhum.

⚠️ **E isso torna inexecutável uma promessa da própria SPEC-072.** A §4 diz que
a entrega é *"achável por `faceta='documento'` + `insurer_key` + `temas`"*.
Como o runtime não lê o Postgres (§3.4①), **esse AND não tem como rodar hoje** —
o terceiro termo não existe do lado que a busca enxerga.

**O que destrava:** `temas` entra em `knowledge_extras` (2 linhas), nos selects
dos republicadores (uma palavra em cada) e ganha índice de payload KEYWORD ao
lado de `faceta` em `qdrant_service.py:96`. ⚠️ **E o mesmo filtro de dois braços
de P-142**: `temas` é nulo em 📊 **4.083 das 17.928 cartas publicadas (22,8%)**
— um braço só apagaria um quinto do índice.

**Por que não foi feito junto com o BLOCO 0:** o bloco existia para impedir que
a republicação **apagasse** o que já estava no índice. Levar um rótulo **novo**
para lá é outra decisão, e ela pertence ao BLOCO 1 (o leitor), onde o filtro é
desenhado. Registrado para não se perder entre os dois.

**O que custa esquecer:** 14.264 cartas rotuladas numa noite inteira de trabalho
continuam respondendo como se não tivessem rótulo, e ninguém vê — porque a busca
devolve resultado, só que o errado. É o mesmo formato de defeito das 📊 11.211
cartas de contrato que atravessavam como genéricas até 08/08.

### ✅ 15/08/2026 — CONSERTADA, por decisão do Founder

Decidido consertar dentro da SPEC-072 em vez de adiar: sem isso, o título do
commit do BLOCO 0 seria falso — "republicar não apaga o lastro" valeria para o
índice e não para o Postgres, que é o durável.

⚠️ **E a pendência subestimava o conserto.** Ela dizia "uma linha e duas chaves,
propagar `source_unit_id`". São **três** colunas: `20260808_03` criou a FK
composta `knowledge_cards_procedencia_coerente_fk (source_version_id,
source_document_id)`. Propagar só o `unit_id` daria uma carta com endereço e sem
documento.

Feito: `corrigir.py:85` pede `pii_check, source_unit_id, source_document_id,
source_version_id`; a substituta herda as três e a `faceta`; `origem` fica de
fora porque descreve a rodada de origem, e a substituta veio desta correção.
Teste: `backend/tests/test_corrigir_nao_perde_a_procedencia.py`, com linha de
controle e mutação. Registro em CHANGE-ADDENDA, addendo de CA-039.

### ✅ 15/08/2026 — FECHADA pela SPEC-072 Bloco 1, junto com a P-142

`temas` deixou de ser write-only nos quatro pontos que faltavam:

```
escritor    attendance_distiller.publish_card_sync  -> knowledge_extras
selects     reindexar_acervo + publicar_lote_sync   -> carregam `temas`
índice      qdrant_service._INDICES_DE_PAYLOAD      -> ("temas", KEYWORD)
leitor      _filtro_de_temas, dois braços           -> MatchAny + IsEmpty
```

⚠️ **A armadilha que quase passou:** a chave tem de ficar AUSENTE quando não há
tema, nunca `[]`. A regra de promoção de payload só pula `None` e `""`
(`qdrant_service.py:329`) — uma lista vazia seria GRAVADA, e aí o braço
`IsEmptyCondition` não alcançaria o ponto, que sumiria de toda busca com tema.
O escritor usa `if card.get("temas")`, que é falso para `[]`. Há teste para isso.

📊 Efeito medido do segundo braço: **4.083 cartas sem tema + 6.797 trechos de
contrato** (que nunca terão tema) continuam respondendo.

---

## P-179 · 🟢 O `COMMENT` da coluna `temas` não conhece `documentacao`

**Aberta em:** 15/08/2026 · **Dono:** 🤖 execução

`20260815_02_a_carta_ganha_tema.sql` documenta os valores da coluna e lista
**13**: reparo_oficina, vistoria, pecas, terceiro, franquia, carro_reserva,
indenizacao, reembolso, perda_total, boletim_ocorrencia, funilaria, regulacao,
endosso.

📊 `documentacao` **não está lá** — e tem **2.786 cartas publicadas**, é o tema
que a SPEC-072 inteira usa, e está em `backfill_temas.py:35`. Medi 24 temas
vivos no banco; o COMMENT conhece 13.

⚠️ **Não se conserta editando a migration:** ela já foi aplicada, e
`MIGRATIONS-AUTHORITY.md` §8.8 proíbe alterar migration aplicada — *"corrigir
sempre com migration nova"*. Vai junto com a migration do Bloco 6, que já toca
`knowledge_cards`.

**O que custa esquecer:** quem for conferir a documentação autoritativa da coluna
conclui que o único tema que a SPEC-072 filtra é ilegal. É um `COMMENT` que
mente, e §12.1 manda consertar o campo, não o texto.

### ✅ 16/08/2026 — FECHADA: o `COMMENT` foi reescrito com os 24 temas

📊 `20260816_01_a_carta_diz_que_pergunta_responde.sql:68` — uma linha, dentro de
uma migration que já ia sair, com `documentacao` entre os **24 valores medidos em
16/08/2026**. Sem juiz, sem red team, sem bloco próprio.

⚠️ **Corrigido em 24/08/2026:** até hoje este título dizia *"a cota entrou, e é cota
mesmo"*, e o bloco abaixo conta a história da **P-178** (`COTA_DE_FACETA`), colada no
lugar errado. A P-179 estava 🟢 por acidente e sem prova. Achado por um juiz que
auditava outra coisa — e é a `PENDENCIAS.md` §índice-que-mente em ação.

---

### ✅ 16/08/2026 — FECHADA (é da **P-178**): a cota entrou, e é cota mesmo

Decisão do Founder: *"a terceira linha do ORCAMENTO_GLOBAL logo depois do Bloco
2, como parte do gate dele — a carta nova tem de ser recuperável, senão o bloco
entrega arquivo e não produto."* E a correção dele sobre a ordem estava certa:
**as cartas do Bloco 2 nascem com `faceta` e `temas` corretos por construção**,
porque somos nós que as escrevemos — a discordância de 47% é do legado.

Implementado em `knowledge_scope.COTA_DE_FACETA` (6 vagas) + uma busca extra nos
**dois** caminhos globais, que **SOMA** ao que as faixas acharam:

```
o laço de ORCAMENTO_GLOBAL   NÃO recebe faceta   ← nada é escondido
a busca extra                roda só quando a pergunta pede
o resultado                  merge_rag_results   ← soma, nunca substitui
```

⚠️ Fica **fora** da tupla `ORCAMENTO_GLOBAL` de propósito: ela é desempacotada
em três (`for rotulo, faixa, cota in ...`) e um teste de outra SPEC afirma essa
forma. Quebrar o guarda de uma SPEC para caber o desta seria o oposto do que
esta pendência ensinou.

Guardado por `test_o_filtro_de_faceta_tem_dois_bracos.py`, bloco [7], que agora
afirma o par certo: **o laço não recebe faceta** E **a busca extra soma**.

---

## P-181 · 🔴 As 147 cartas do Bloco 2 são CÓPIA LITERAL — não publicar

**Aberta em:** 16/08/2026 · **Dono:** 🧑 **Founder decide** · 🤖 execução aplica
**Origem:** juiz crítico adversarial do SPEC-072 Bloco 2. **Bloqueia a publicação.**

🔴 **NÃO RODAR `publicar_cartas.py` PARA AS CARTAS NOVAS.** Elas estão gravadas
em `.jsonl` e versionadas; **nenhuma foi publicada**, e nenhuma deve ser até
esta pendência fechar.

📊 **146 das 147 cartas são substring LITERAL do texto limpo do contrato.**
Medido com acento removido e espaços colapsados. Fração copiada, por âncora:

```
1º pedaço, autojunk=True   (como o guarda rodava)   42/147 acusadas
1º pedaço, autojunk=False                           53/147
corrida inteira, autojunk=False  (a âncora honesta) 117/147
```

**Elas passariam pelo gate por acidente**, e o acidente já foi consertado —
ver abaixo.

### O conflito, e ele é entre duas coisas que estão certas

`conferir_ancoragem.py:202-219` diz, e está certo:

> *"A carta é o contrato REESCRITO. Se ela for o contrato COPIADO, o namespace
> `cards` vira uma segunda cópia do `normative` — duas entradas disputando as
> mesmas vagas na busca, dizendo a mesma coisa com as mesmas palavras. A carta
> perde a razão de existir."*

E a SPEC-072 §3.4③ diz, e também está certo:

> *"Não destile a lista. Extraia a seção inteira."* — 📊 destilar em prosa levou
> o núcleo comum de documentos de 12/16 para 5/16.

**Linha de controle que fecha o argumento:** as 5.396 cartas de acervo já
publicadas têm p50=444 e max=1.667 — são reescritas. Estas 147 têm p50=1.397 e
são verbatim. **São objetos de natureza diferente entrando no mesmo namespace.**

### As três saídas, e a minha recomendação

1. 🟢 **Reescrever preservando o item** — cada item vira o NOME do documento sem
   o juridiquês (*"a) Boletim de Ocorrência Policial nos casos de Incêndio e
   Explosão, Impacto de Veículos, Roubo de Bens..."* → *"boletim de ocorrência
   (incêndio, explosão, impacto de veículo, roubo)"*). Preserva a contagem, que
   é o gate, e quebra o bloco literal. **É o que eu recomendo** — resolve os dois
   lados sem isentar ninguém.
2. 🟡 **Isenção explícita e registrada** para `faceta='documento'`: lista
   taxativa é o único conteúdo em que reescrever é o próprio dano. Exige decisão
   do Founder e um `namespace` próprio, senão a busca passa a ter duas cópias.
3. 🔴 **Não publicar.** O Bloco 2 vira arquivo e não produto.

### O que JÁ foi consertado — e vale além desta SPEC

`conferir_ancoragem._fracao_copiada` chamava `difflib.SequenceMatcher(None, a, b)`
com `autojunk` no default `True`. Em sequência de CARACTERES com `len(b) ≥ 200`,
o autojunk marca como lixo todo elemento presente em mais de 1% de `b` — em
português, **toda letra comum**. O `find_longest_match` ficava aleijado
exatamente nas cartas longas, que são as únicas onde cópia importa.

📊 Só desligando o autojunk, a fração p50 vai de **0,04 para 0,37**.

⚠️ **É defeito do GUARDA, não da SPEC-072.** Ele vale para toda carta já
conferida por esse script desde que ele existe — e um guarda calibrado para não
ver é pior que guarda nenhum, porque emite laudo de aprovação.

### Os outros achados do juiz, para o mesmo bloco

- 🟠 **18 das 147 citam menos de 2 documentos no próprio texto** (8 citam zero).
  O portão mede o BLOCO e a publicação é por CARTA. Conserto de uma linha:
  reaplicar `nomeia_documentos(parte)` dentro do laço que monta as partes.
- 🟠 **5 corridas, 18.180 chars, 185 itens** de lista de documentos legítima
  somem **sem rastro**: `corridas_de_documento` exige ao menos um pedaço
  `faceta='documento'`, e essas são só `escopo`. Não entram nem no diagnóstico.
- 🟠 **28 cortes cegos** em `partir()`: quando nenhuma fronteira cabe, corta no
  caractere (`...formali|zado...`). O docstring promete que isso nunca acontece.
- 🟠 **O teste está VERDE com tudo isso de pé.** O guarda [5] chama-se *"nunca
  corta no meio"* e aceita até 25% das cartas começando no meio; o [3] chama-se
  *"o texto sobrevive inteiro"* e compara COMPRIMENTO, não conteúdo. **É o §9.3
  em estado puro, e no meu próprio teste.**
- 🟡 3 falsos negativos no vocabulário: o acervo escreve *"Carta Aviso"*,
  *"carteira de habilitação"*, *"Documento Pessoal"*, *"Comprovante de
  Propriedade"* — e `_VOCAB_DOC` não tem nenhum. E `declaração` foi removido
  demais: *"Declaração de únicos herdeiros"* é documento. `declaração de` (com a
  preposição) mantém o documento e derruba o verbo.
- 🟢 **PII sobrevive:** 1 recusada em 147 (uma tag `{EMAIL}`), zero CPF, zero
  CNPJ, zero placa. A fonte é condição geral, não caso concreto.

**O que custa esquecer:** publicar as 147 põe 146 cópias do contrato no
namespace `cards`, competindo com o `normative` pelas mesmas vagas e dizendo a
mesma coisa com as mesmas palavras. O agente passaria a ver tudo em dobro.

### ✅ 16/08/2026 — FECHADA: reescritas, e o guarda passou a ser o portão

Decisão tomada por nota, a pedido do Founder:

```
reescrever preservando o item ....  88   ← executada
isenção + namespace próprio .....  45   (namespace novo = motor paralelo, §5)
não publicar ....................  20   (o Bloco 2 vira arquivo)
```

**O conserto:** `reescrever_lista()` tira o marcador (`a)`, `bb)`, `1)`), tira o
juridiquês de forma (*"Cópia da"*, *"Original do"*), minúscula a inicial e junta
com `; `. O que a destilação em prosa perdia era **item**, não formatação — então
o item fica inteiro e a forma muda. 📊 O maior bloco literal em comum cai para o
tamanho de **um item**.

```
                              antes    depois
substring literal inteira ...  146/147     0
acusadas de cópia ...........   79        0
cartas publicáveis ..........  147       70
p50 .........................  1.397   1.466
```

⚠️ **De 147 para 70, e isso é qualidade, não perda.** Três portões novos, todos
com o número declarado:

- **52 blocos sem lista delimitada** (152.393 chars) — a Yelum é tabela achatada
  e reescrever exigiria inventar fronteira. A heurística de maiúscula erra
  **107%** na mediana. Registrados, não publicados. **R7: qualidade sobre volume.**
- **10 cartas barradas pelo portão de cópia** — o próprio limiar de
  `conferir_ancoragem` (>70% num bloco de 250+), agora rodando ANTES de gravar e
  contra a âncora honesta (a corrida inteira, não o primeiro pedaço).
- **97 blocos/partes** sem ≥2 nomes de documento — o portão agora é **por
  carta**, não por bloco, que era o achado do juiz.

**Os outros cinco achados, todos consertados:** os 28 cortes cegos (`partir()`
agora corta em `; `, e o teste prova **0** fora de fronteira); as 5 corridas
`escopo` invisíveis (o censo as resgata quando nomeiam ≥4 documentos); os 4
falsos negativos de vocabulário (`Carta Aviso`, `carteira de habilitação`,
`Documento Pessoal`, `Comprovante de Propriedade`, e `declaração de` com a
preposição); o cabeçalho *"para sinistro"* (usa o título da cobertura); e **as
duas asserções frouxas do meu próprio teste** — `[5]` era `<= 25%` num teste
chamado *"nunca"*, e `[3]` comparava comprimento em vez de conteúdo.

---

## P-210 · ✅ RESOLVIDAS pela SPEC-078 — registro do que saiu da lista

**Fechadas em:** 17/08/2026

| | O que era | Como ficou |
|---|---|---|
| P-207 | O freio de emergência significava coisas opostas em dois processos | A ausência ficou **visível** (`kill_switch_presente` no `/health`); e a porta que realmente faltava — `send_to_client_guarded` sem leitura do interruptor — foi fechada no Bloco A.1 |
| P-208 | Nada no banco ligava um Auxiliar ao modelo de Rotina | `routines.tenant_auxiliary_id` é **NOT NULL** com FK composta por corretora. Os quatro escritores passam a preencher |

**P-207 continua com uma parte 🧑 do Founder:** definir `GLOBAL_KILL_SWITCH=false`
**explicitamente** no serviço `portal-worker` do EasyPanel. 📊 Medido em
17/08/2026: `kill_switch_presente: false` — a variável não existe no processo.
Com ela definida, virar o padrão para fail-closed é um commit de uma linha.

---

## P-227 · ✅ A duplicação ACABOU — e sobrou uma coisa nova para saber

### ✅ 24/08/2026 — FECHADA quanto à duplicação

📊 O ambiente atual do `autobrokers-smith-api` traz **uma ocorrência de cada**:
`INSURER_DISPATCH_LIVE=false` · `DISPATCH_FINALIZE_MODE=test`. O estado deixou de
depender de qual duplicata a plataforma escolhe. **Era o defeito, e ele morreu.**

### ⚠️ CONTINUA, e é outro: o freio de emergência não está mais armado

📊 Medido rodando as funções reais contra o ambiente atual:

```
ACIONAMENTO_FREIO_DE_EMERGENCIA   ausente  →  freio DESARMADO
dispatch_live_enabled()                       False
acionamento_liberado(agente LIGADO)           True     🔴 antes era False
finalize_live_for(allianz-residencial@v1)     True
finalize_live_for(allianz-auto@v1)            False
finalize_live_for(porto-auto@v1)              False
```

🔴 **Eram três freios em série; hoje são dois.** Antes, mesmo com o agente
ligado, o freio derrubava. Agora o que segura é `INSURER_DISPATCH_LIVE=false`
**mais** os quatro `attendance` em `is_active=false`, e nada além disso.

⚠️ **E a graduação de finalização está ligada para UM corredor:**
`DISPATCH_FINALIZE_LIVE_PLAYBOOKS=allianz-residencial-whatsapp@v1`. Isso é o
mecanismo funcionando como documentado (`insurer_dispatch_service.py:349`) — e é
exatamente o corredor do `work_run e5279497`, a única travessia ponta a ponta.
**Não é defeito; é a escada de go-live.** Mas muda o que um `true` significa:

> Com o freio desarmado, escrever `INSURER_DISPATCH_LIVE=true` passa a abrir
> **envio real E finalização real** no `allianz-residencial` — de uma vez, sem
> terceira rede. Antes esse gesto ainda esbarrava no freio.

- **Destrava:** 🧑 Founder — decidir se o freio volta a ficar armado até o
  ensaio, ou se os dois freios bastam. **Não bloqueia a execução**: os quatro
  agentes estão desligados e esta SPEC não liga nenhum.
- ⚠️ **`CARTOGRAPHER_MODE=1` continua ligado** — o Cartógrafo manda WhatsApp
  real para seguradora (P-32, decisão ainda pendente).


## P-PILOTO-17 · `agents.llm_max_tokens` gravado em 1200/2000 mente para quem abre a tela
📊 10/09: o agente core da Resulta tinha 1200; 10 de 95 respostas do chat cortadas exatamente nesse teto. O piso de 8192 (`llm_factory.py`) conserta o comportamento sem tocar o banco; o número na tela continua errado. **Destrava:** atualizar `llm_max_tokens` dos 8 agentes para 8192 pela tela ou por SQL com manifesto. **Dono:** 🧑.

✅ **FECHADA em 14/09/2026 pela SPEC-EXTRA-001.1 BLOCO E:** migration `20260914_06_spec_extra0011_llm_max_tokens.sql` aplicada (📊 VERIFY: 8 de 8 em 8192; backup por `agent_id` com os 8 valores originais; APPLY 2×; ROLLBACK exercitado e reaplicado); defaults de código 2000/1200 → 8192 em 5 lugares (`agent_config.py:82/:133/:288`, `models/agent.py:19`, `app/api/admin/sandbox/bootstrap-tenant/route.ts:106`); `insured_external` no piso (`PAPEIS_QUE_CONVERSAM`). O `DEFAULT 2000` de DDL fica em `P-E0011-DEFAULT-DDL-2000`; `companies.llm_max_tokens` NÃO subiu (D-E0011-01).


## P-PILOTO-18 · o chat do painel não registra que ferramenta o agente chamou
📊 10/09: `messages.payload` só tem `turn`; sem `tool_invocations`/atividade para o chat web. Auditar "por que o agente disse que não conseguia" exigiu reproduzir a API. **Destrava:** gravar as tool calls do turno no `payload.turn` (nome, status, ms). **Dono:** 🤖.

✅ **REESCRITA E FECHADA em 14/09/2026 pela SPEC-EXTRA-001.1 BLOCO E.** O texto original estava vencido: 📊 `tool_invocations` existe (277 linhas em 14/09) e o chat grava nela desde `nodes.py:1057` (`RegistroDeInvocacao` → `ToolGateway`). O que faltava era (a) a LIGAÇÃO com o turno — feita: `trace_id = "<session_id>|<client_request_id>"` (coluna e escritor que já existiam; zero DDL) e `payload.turn.tool_calls` derivado por junção (uma escrita, dois leitores); (b) o contador observável do `_RegistroInerte`; (c) a DDL não rastreada de `tool_invocations` registrada no `MANIFEST.md` como `NÃO RASTREADA`, lida do catálogo. 📊 `input_summary` continua sem argumento cru (0 de 277 com 11 dígitos) — guarda `test_a_ferramenta_do_turno_deixa_rastro.py`. Implementar a pendência como estava escrita (gravar em `payload.turn`) teria criado um segundo registro (CLAUDE.md §5).


## P-PILOTO-20 · 4 guardas antigos de policy quebram no harness por `nodes.py` importar `honestidade_do_handoff` (desde 23/08)
`test_infocap_policy_output_guard`, `test_spec016_*`: o stub de `app.agents` com `__path__=[]` não acha o módulo. Pré-existente, não é regressão de 10/09. **Destrava:** o harness registra o módulo no stub. **Dono:** 🤖.

---

# SPEC-EXTRA-001.6 · A cobrança prova que funciona (14/09/2026)

> As pendências desta SPEC. As três que ela fecha (`P-E001-CANARIO-VIVO-NO-IMPLANTADO`, `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY`, `P-PILOTO-11`) só se movem para `PENDENCIAS-FECHADAS.md` quando o canário Q1–Q10 rodar no implantado.

✅ **FECHADA em 14/09/2026 pela SPEC-EXTRA-001.1 BLOCO E:** o harness dos 4 scripts (`test_infocap_policy_output_guard`, `test_spec016_policy_intelligence`, `test_spec016_1_answer_quality`, `test_spec016_e2e_stub`) carrega o módulo real `honestidade_do_handoff` antes de `nodes.py`; os 4 RODAM e estão verdes (📊 14 · 92 · 51 · 21). Duas verdades vencidas migradas sob CLAUDE.md §9.3 (o registry agora RECUSA adaptador incompleto; listar apólice deixou de ser ordem incondicional). Mesma classe de conserto aplicada em `test_infocap_contract_capture` e `test_spec017_attendance_unleashed` (`app.providers.__path__` real).

---

# SPEC-EXTRA-001.2 · O agente lê tudo antes de falar (14/09/2026)

## P-PILOTO-13 · 174 conversas-fantasma LID e o CHECK de `resolucao_motivo`
✅ **FECHADA em 14/09/2026:** M1 `20260914_07_spec_extra001_2_check_fantasma_lid.sql` (CHECK aceita `fantasma_lid`; VERIFY: motivo fora da lista RECUSADO 23514, `fantasma_lid` ACEITO) e `migrar_conversas_fantasma_lid.py --vivo` (📊 2 pausas copiadas · 175 fantasmas fechadas · 0 falhas · VERIFY 0). M2 `20260914_08` (`conversations.contraparte` + `uq_conversations_contraparte_aberta`) impede a fantasma nº 176 (VERIFY: 2ª aberta RECUSADA 23505; outra corretora ACEITA). Guarda: `test_uma_conversa_por_contraparte.py` (35) e `test_o_atendimento_termina_e_o_produto_sabe.py` (6 motivos).

## P-PILOTO-15 · pausa não protege conversa com `resolvido_em` preenchido
✅ **FECHADA em 14/09/2026 (opção b′, D-E0012-03):** `pausar_ia` protege quando o takeover (`claimed_at`) é DEPOIS do encerramento (`resolvido_em`); nenhum leitor de `resolvido_em` (📊 12) muda. Guarda: `test_todo_silencio_tem_motivo.py` (conversa reaberta com atendente dentro → protegida; exceção de janela NÃO fura o takeover). O pedido de humano sem timestamp ficou em P-E0012-03.
