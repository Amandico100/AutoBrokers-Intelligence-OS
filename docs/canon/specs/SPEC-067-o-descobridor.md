---
> **Status:** canônica · depende das SPECs 064, 065 e 066
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-052 · SPEC-055 · SPEC-056 · SPEC-059
> **Origem:** a pergunta do Founder — *"como fazer um auxiliar achar ouro se ele
> não sabe onde procurar?"* · catálogo de 59 análises de 31/07 · auditoria dos
> doze detectores de 31/07 · pesquisa de memória de agente de 30/07
> **Branch:** `feat/spec067-o-descobridor`
> **Nomenclatura:** "Garimpo" continua sendo a mineração da VOZ do corretor
> (SPEC-059 §18). Isto é outra coisa e chama-se **Descobridor**.
---

# SPEC-067 — O Descobridor

> **A frase que resume:** os doze detectores de hoje vigiam o próprio sistema —
> fila parada, aprovação pendente, conexão degradada. **Nenhum olha dinheiro,
> venda, renovação ou cliente.** Não foi burrice do modelo: **ninguém nunca disse
> a ele que a corretora tem um negócio.**

---

## 1. Por que esta SPEC existe

### 1.1 A prova

Os doze detectores registrados, verificados no código:

```
automacao.lacuna_recorrente     operacao.aprovacao_parada
automacao.resultado_positivo    operacao.artifact_nao_entregue
automacao.tarefa_repetida       operacao.auxiliar_degradado
conexoes.conexao_degradada      operacao.work_run_falhando
conexoes.orcamento_no_limite    operacao.work_run_travado
qualidade.atendimento_parado    qualidade.regressao_atendimento
```

**Doze. Todos autorreferentes.** O sistema foi construído para vigiar a si mesmo.

E os oito caminhos de recomendação (`recommendation_service.py:60`) — `revisar_aprovacoes`, `investigar_falha`, `investigar_qualidade`, `reconectar`, `reduzir_fila`, `revisar_custo`, `propor_automacao`, `destravar_portal` — **nenhum leva a dinheiro.**

### 1.2 A pergunta do Founder, e por que ela é a certa

> *"Como fazer um auxiliar achar ouro se ele não sabe onde procurar? Se eu não
> tivesse falado sobre Google, você nunca teria pensado nisso sozinho."*

**Ele está certo, e o diagnóstico é preciso:**

O modelo não deixou de pensar em Google por falta de inteligência. **Deixou porque
"presença digital" não estava no mapa do que é uma corretora — e o site dela não
está no banco de dados.**

> **Um modelo solto no schema encontra apenas o que o schema contém.**

A correção não é soltar mais. **É manter um mapa curto de onde há dinheiro,
revisado por gente, e soltar o modelo dentro dele.**

### 1.3 O que esta SPEC entrega

```
o corretor recebe, toda semana, um achado que ele não pediu
   e que vale dinheiro que ele consegue contar
o sistema descobre coisas que ninguém programou — dentro de formas explicáveis
e aprende, sozinho, onde ele NÃO estava olhando
```

### 1.4 O que esta SPEC NÃO faz

| Fora do escopo | Onde vai |
|---|---|
| construir cada auxiliar do catálogo | um por vez, SPECs próprias |
| a carteira e os conectores | SPEC-065 |
| o acervo público | SPEC-066 |
| prontidão e go-live | SPEC-068 |

### 1.5 A dependência

```
SPEC-064 ..... a ontologia. Sem ela, o Descobridor vira mais uma página órfã.
SPEC-065 ..... a carteira. Sem ela, 40 das 59 análises não têm dado.
SPEC-066 ..... o acervo. Sem ele, faltam as análises de mercado.
SPEC-065 §F .. o harness que calcula. Sem ele, o Anel 2 não existe.
```

**19 das 59 análises rodam só com dado interno** — conversas, cotações,
atendimentos. **Essas podem começar antes das outras SPECs terminarem.**

---

# BLOCO 0 — A auditoria que vem antes de qualquer linha de código

**Obrigatório. E aqui ela tem uma exigência a mais.**

## 0.1 O que confirmar

```
[ ] os doze detectores continuam sendo os mesmos, e continuam autorreferentes
[ ] o contrato ContextoDeDeteccao → SignalDraft não mudou
[ ] o SignalService continua sendo o único que grava
[ ] dedupe, cooldown e quiet hours continuam funcionando
[ ] os dois detect_signals presos em `queued` desde 28 e 30/07 — o que são?
[ ] briefing_publications já sai de `pending`? (depende da 064)
```

## 0.2 A exigência a mais: validar CADA análise

**Nenhuma das 59 análises entra sem passar por isto:**

```
1. rodar a consulta contra dado real da Resulta ou da AutoFleet
2. contar quantos casos aparecem
3. conferir TRÊS casos à mão, contra o InfoCap ou o portal
4. calcular o valor com o número REAL, não com o estimado
5. perguntar ao corretor: "isso é novidade para você?"
```

**Análise que falha no passo 3 não entra. Análise que falha no passo 5 vira
segunda prioridade** — pode ser verdadeira e já sabida, e aí não é ouro.

**Por que o passo 5 importa:** o Founder já apontou o risco — *"as corretoras já
têm seus processos de renovação, verifique isso direito."* **Achar o que ela já
sabe não gera efeito nenhum.**

## 0.3 O relatório

**✅ confirmado · ⚠️ corrigido · ➕ acrescentado · ❓ em aberto · 🚫 retirado**,
mais uma seção nova:

```
📋 ANÁLISES VALIDADAS ..... quantas passaram nos 5 passos, com o número real
📋 ANÁLISES REPROVADAS .... quais falharam, em qual passo, e por quê
```

---

# BLOCO A — Os três anéis

**O coração da SPEC.** É a resposta à pergunta do Founder.

## A.1 Por que três, e não um

```
lista fechada só ........ acha só o que está na lista. Nunca surpreende.
exploração livre só ...... acha ruído, e caro. Ou não acha nada.
```

**Nenhuma das duas.** A lista fechada é de **domínios** e de **formas** — a
análise é aberta dentro delas.

---

## A.2 ANEL 1 — O catálogo

**59 análises escritas, com a frase de saída pronta e a conta do quanto valem.**
Determinísticas, testáveis, auditáveis, baratas.

**Entregam ~90% do valor.** Rodam sempre.

### A.2.1 A estrutura de uma análise

```
id ..................... estável, versionado como Skill (SPEC-056)
versão ................. muda quando a fórmula muda
domínio ................ um dos 12 do Anel 3
pergunta ............... o que ela responde, em uma linha
dados .................. quais campos, de quais fontes
gatilho ................ calendário, evento, ou contínuo
consulta ............... a pergunta ao dado — determinística
fórmula de valor ....... como o R$ é calculado
frase de saída ......... o texto, com os espaços para os números
nível de evidência ..... 0 a 5 (SPEC-059 §8)
esforço do corretor .... quanto trabalho ele terá
como validar ........... o teste que prova que funciona
status ................. rascunho · validada · publicada · aposentada
```

### A.2.2 A distribuição por domínio

| Domínio | Análises | Nota média | Dado interno? |
|---|---|---|---|
| Dinheiro parado | 10 | 91 | parcial |
| Vendas | 8 | 90 | parcial |
| Retenção | 7 | 91 | parcial |
| Negociação com seguradora | 7 | 89 | precisa da 066 |
| Risco e conformidade | 6 | 89 | **sim** |
| Produtividade | 4 | 82 | **sim** |
| Contabilidade e fiscal | 7 | 89 | precisa da 065 |
| Marketing e presença digital | 6 | 87 | fonte externa |
| Pessoas e equipe | 4 | 91 | precisa da 065 |
| **Total** | **59** | **89** | **19 rodam já** |

### A.2.3 As três ondas

```
ONDA 1 — só dado interno, dificuldade baixa
   cobertura suspensa · carteira vazando · duplicidade · cotação esfriada
   ex-cliente na janela · renovação órfã · sinistro apodrecendo
   concentração de carteira · site fora do ar · alocação de lead
   carteira sem dono · queda de produção com causa
   → 12 análises · ~R$ 300 mil/ano demonstrável

ONDA 2 — com as fontes públicas (SPEC-066)
   sinistralidade da seguradora · minha carteira vs a média dela
   cliente que abriu CNPJ · sócio sem produto pessoal · gap de ramo
   bairro que piorou · posição no Google · ficha do Google

ONDA 3 — fiscal e conciliação (precisa do extrato)
   comissão a menor · endosso não comissionado · retenção não compensada
   anexo do Simples · fator R · nota fiscal que não bate
```

### A.2.4 Três exemplos, no formato final

**Renovação com taxa efetiva** — a de maior valor do catálogo

```
domínio ......... retenção
pergunta ........ a renovação subiu mais do que o bem vale?
dados ........... prêmio de renovação · prêmio anterior · FIPE nas duas datas
                  coberturas (para detectar mudança real de escopo)
gatilho ......... 45 dias antes do vencimento
fórmula ......... taxa_efetiva = prêmio ÷ valor_do_bem
                  variação = (taxa_atual − taxa_anterior) ÷ taxa_anterior
frase ........... "A renovação do {cliente} veio {prêmio} contra {anterior}:
                   +{pct}%. Só que o carro caiu {fipe_pct}% na FIPE.
                   A taxa efetiva subiu {efetiva}%. Ele vai cotar fora e vai
                   achar mais barato. Você tem {n} renovações assim em {mês}."
valor ........... n × prêmio × comissão × probabilidade de perda evitada
como validar .... pegar 5 renovações do mês passado, calcular à mão,
                  e conferir quantas de fato saíram
```

> **Nenhum corretor calcula taxa efetiva. Todos comparam o prêmio nominal.**

**Cliente sem cobertura**

```
domínio ......... risco e conformidade
gatilho ......... diário, 07h
frase ........... "{n} clientes estão com cobertura suspensa por falta de
                   pagamento. O {cliente} tem {dias} dias de atraso numa apólice
                   de {prêmio}. Se ele bater o carro hoje, a seguradora nega —
                   e a culpa vira sua."
como validar .... confirmar a regra de suspensão em 3 seguradoras diferentes
                  ANTES de afirmar prazo. Nunca número fixo.
```

**O que ele disse × o que o sistema registra**

```
domínio ......... risco e conformidade
dados ........... conversas × perfil da apólice
frase ........... "O {cliente} escreveu em {data} que começou a rodar por
                   aplicativo. A apólice dele é uso particular. Se houver
                   sinistro, a seguradora nega — e como a informação estava no
                   seu WhatsApp, a corretora responde junto."
valor ........... exposição evitada, não receita
como validar .... 10 casos detectados, conferidos contra a apólice real
```

**Esta é a análise mais nossa do catálogo** — ninguém mais tem as conversas.

### A.2.5 O catálogo é produto, não caixa-preta

**O corretor vê a lista.** Como o Claude for Small Business faz com seus 15
workflows: **número finito, nomeado, legível em dois minutos.**

Isso importa porque:

```
ele confia mais no que consegue ler
ele pede o que falta — e o pedido vira demanda medida
e ele entende por que paga
```

---

## A.3 ANEL 2 — As formas

**Não são análises. São formas de análise**, instanciadas automaticamente sobre
pares de campo e dimensão.

### A.3.1 As seis formas

| Forma | O que procura | Exemplo do catálogo |
|---|---|---|
| **divergência** | duas fontes que deveriam bater e não batem | comissão contratada × creditada |
| **concentração** | Pareto em qualquer dimensão | 3 clientes = 21% da comissão |
| **quebra de série** | o que fugiu da própria tendência | produção que caiu 46,7% |
| **coorte** | grupo que se comporta diferente do resto | quem fez downgrade cancela 41% mais |
| **queda de funil** | perda entre duas etapas | cotação → fechamento por vendedor |
| **o que ele DISSE** | declarou X, o sistema registra Y | uso por aplicativo não declarado |

**A sexta é só nossa.** Ninguém mais tem 69.150 transcrições ligadas à carteira.

### A.3.2 Como funciona

```
1. o sistema tem um dicionário de dados com semântica de negócio
   (não só nome de coluna — o que aquilo SIGNIFICA)
2. aplica cada forma sobre cada par métrica × dimensão × janela
3. testa significância — o resultado é anômalo de verdade?
4. calcula o valor em R$
5. FILTRO DURO: sem valor calculável, descarta. Não mostra.
```

### A.3.3 Por que isso é seguro

```
produz achados que ninguém programou
   MAS dentro de formas conhecidas
      logo: explicável, barato, e sem alucinação
```

**O modelo não inventa a análise. Ele instancia uma forma conhecida sobre um
campo que existe.**

### A.3.4 O que impede a explosão combinatória

```
só campos marcados como analisáveis no dicionário
só janelas que fazem sentido para aquele campo
teto de execuções por rodada, com orçamento declarado
resultado sem significância estatística nem entra na fila de valor
```

---

## A.4 ANEL 3 — O mapa de domínios

**A peça que teria evitado o ponto cego do Google.**

### A.4.1 Os doze domínios

```
 1. dinheiro parado
 2. vendas
 3. retenção
 4. negociação com seguradora
 5. risco e conformidade
 6. produtividade
 7. contabilidade e fiscal
 8. marketing e presença digital     ← o que faltava
 9. pessoas e equipe
10. patrimônio e caixa da própria corretora
11. relacionamento institucional (SUSEP, sindicato, certificação)
12. tecnologia e dados (integração caindo, campo faltando, portal mudou)
```

### A.4.2 Por que ele é fechado e revisado por gente

**Um domínio não é uma tabela. É um lugar onde há dinheiro.**

O site da corretora **não está no banco** — e por isso nenhum modelo, por mais
capaz, iria olhar para lá. **Só olha quem foi mandado olhar.**

```
revisão ....... 1 a 2 vezes por ano, por gente
gatilho ....... quando o mecanismo do Bloco B apontar um domínio novo
efeito ........ cada domínio novo enriquece o sistema SEM UMA LINHA DE CÓDIGO
```

### A.4.3 O que cada domínio declara

```
nome
o que significa, em uma frase de negócio
onde estão os dados — inclusive fora do banco
que perguntas ele responde
quantas análises do catálogo pertencem a ele
```

**Domínio sem análise nenhuma é sinal:** ou está mal definido, ou é uma lacuna
que precisa ser preenchida.

---

## A.5 Testes do Bloco A

| # | Prova |
|---|---|
| A1 | toda análise do catálogo tem os 13 campos da estrutura |
| A2 | análise sem fórmula de valor não pode ser publicada |
| A3 | análise sem "como validar" não pode ser publicada |
| A4 | as formas do Anel 2 só instanciam sobre campo marcado como analisável |
| A5 | achado sem valor em R$ calculável é descartado antes de virar sinal |
| A6 | o mapa de domínios existe, tem 12, e cada um declara onde estão os dados |
| A7 | acrescentar domínio ao mapa não exige mudança de código |
| A8 | o teto de execuções por rodada é respeitado |

---

# BLOCO B — O que o sistema perdeu

**O mecanismo que aprende, sozinho, onde ele não está olhando.**

## B.1 A ideia

> Quando o corretor age **sem** o sistema ter sugerido — contratou alguém para
> mexer no site, cobrou a seguradora, trocou o vendedor de um cliente, mudou de
> contador — **isso é um achado que o sistema perdeu.**

## B.2 Como se detecta

```
mudança de estado que o sistema não previu:
   apólice cancelada sem recomendação prévia
   vendedor reatribuído
   campanha disparada
   fornecedor novo aparecendo em conversa
   reclamação formal contra seguradora
   contrato novo, conta nova, ferramenta nova
```

**E o gatilho mais simples e mais valioso:** o corretor menciona, na conversa,
algo que fez. *"Contratei um cara pra mexer no site."*

## B.3 A pergunta

**Uma vez. Nunca duas.**

> *"Vi que você [ação]. Só para eu aprender: **eu deveria ter te avisado disso?**"*

```
sim  → vira lacuna de domínio, entra na fila de revisão do mapa
não  → registrado, e o sistema não pergunta de novo sobre esse tipo
```

## B.4 Por que isso é o mecanismo certo

**É barato, é contínuo, e ensina exatamente o ponto cego.**

> **Se estivesse ligado, teria descoberto o Google sem o Founder falar.**

O corretor teria contratado alguém para o site, o sistema teria perguntado, ele
teria dito *"sim, deveria"*, e **"presença digital" teria entrado no mapa por
demanda medida.**

## B.5 A trava

```
no máximo 1 pergunta dessas por semana, por corretora
nunca no meio de uma conversa urgente
nunca sobre algo que ele já respondeu
```

**Perguntar demais transforma aprendizado em incômodo.**

## B.6 Testes

| # | Prova |
|---|---|
| B1 | ação não antecipada é registrada |
| B2 | a pergunta acontece no máximo uma vez por semana |
| B3 | resposta "não" impede repetição sobre o mesmo tipo |
| B4 | resposta "sim" gera item na fila de revisão do mapa |
| B5 | a pergunta nunca interrompe conversa marcada como urgente |

---

# BLOCO C — A taxonomia

## C.1 Por que a taxonomia comum não serve

`urgente / alerta / oportunidade / conselho` **mistura dois eixos.**

```
"urgente" ......... é tempo
"oportunidade" .... é natureza
"alerta" .......... não é nada
```

**"Alerta" vira lixeira.** Em três meses, tudo é alerta — e aí nada é.

## C.2 A classificação: pelo que se espera do corretor

| Classe | O que significa | O que se espera dele | Exemplo |
|---|---|---|---|
| **AGORA** | perda em curso, janela fecha em dias | **executar hoje** | cobertura suspensa · renovação em 7 dias |
| **DINHEIRO NA MESA** | valor quantificado, sem janela crítica | **autorizar** | comissão a menor · retenção não compensada |
| **OPORTUNIDADE** | receita nova possível | **decidir se vale o esforço** | cliente que abriu CNPJ · gap de ramo |
| **EXPOSIÇÃO** | não custa hoje, custa se acontecer | **decidir aceitar ou mitigar** | uso por app não declarado · RC vencido |
| **CONSELHO** | mudança estrutural, sem urgência | **pensar, talvez com terceiro** | regime tributário · alocação de leads |
| **LIMPO** | verificação feita, nada encontrado | **nada** | recibo de vigilância |

## C.3 Os três eixos, todos obrigatórios

```
classe ............ o que fazer          (as 6 acima)
severidade ........ quanto pesa          (P0..P3, já existe na SPEC-059)
valor_brl ......... quanto vale          (número, obrigatório fora de LIMPO)
```

Mais o **nível de confiança** (0 a 5), **sempre exibido**.

## C.4 Por que EXPOSIÇÃO é separado de AGORA

```
AGORA ......... a resposta é EXECUTAR
EXPOSIÇÃO ..... a resposta é DECIDIR
```

**Misturar as duas produz fadiga de alerta — a única coisa que mata este produto.**

## C.5 Testes

| # | Prova |
|---|---|
| C1 | todo achado tem classe, severidade e valor |
| C2 | achado fora de LIMPO sem valor não é emitido |
| C3 | não existe classe "alerta" |
| C4 | o nível de confiança é exibido em toda apresentação |

---

# BLOCO D — A dosagem

**Sustentada por uma lição medida, e ela vale ser lembrada:**

> Todos os cards de meta do InfoCap, em todos os períodos, mostram
> **"0% ATINGIDA — MUITO ABAIXO DA META"** — porque a meta nunca foi cadastrada.
>
> **Um alerta que está sempre vermelho não é lido por ninguém.**

## D.1 O orçamento de atenção

```
briefing diário ....... 3 itens
briefing semanal ...... 5 a 7 itens
manchete .............. 1 por semana
P0 .................... fura o orçamento. Nada mais fura.
```

## D.2 As cinco regras

**D.2.1 — Um item por domínio por briefing.** Sem isso, uma conciliação de
comissão manda 6 itens de dinheiro parado e sequestra a semana.

**D.2.2 — Ordenar por ação, não por gravidade.**

```
ranking = valor_normalizado          × 0,35
        + probabilidade_de_ser_verdade × 0,20   (deriva do nível de confiança)
        + facilidade_para_o_corretor   × 0,20   (inverso do esforço dele)
        + urgência_da_janela           × 0,20   (dias até fechar)
        + alinhamento_com_o_papel      × 0,05
        − penalidades já existentes na SPEC-059 §12.2
```

**Um achado de R$ 40 mil que exige projeto de três meses perde para R$ 3 mil
resolvíveis num clique.**

**D.2.3 — Nunca dois achados que exigem a mesma decisão.** Se dois apontam para a
mesma renovação, **é um item com duas razões** — que é dez vezes mais forte.

**D.2.4 — Backlog visível, nunca empurrado.**

> *"Mais 14 itens no seu Radar."* com link. **Nada se perde; nada é empurrado.**

**D.2.5 — Uma manchete por semana.** O maior achado, **já investigado**, com
número, evidência item a item e ação pronta. **É o que faz o corretor abrir na
segunda-feira.**

## D.3 O que a dosagem protege

```
sem ela ..... o corretor desliga tudo na terceira semana
com ela ..... ele abre todo dia porque nunca foi enganado
```

## D.4 Testes

| # | Prova |
|---|---|
| D1 | o teto diário é respeitado |
| D2 | um item por domínio por briefing |
| D3 | dois achados sobre a mesma decisão viram um |
| D4 | o excedente aparece no backlog e não some |
| D5 | a ordenação usa as cinco dimensões, não só gravidade |
| D6 | existe exatamente uma manchete por semana |

---

# BLOCO E — O recibo de vigilância

## E.1 A regra

```
IRRITA ....... "Está tudo certo!" como notificação
               genérico, não falsificável, e parece que ele pagou por nada

VALE OURO .... o recibo no rodapé do briefing, e como página consultável
```

> *"Conferi 41 verificações hoje. 38 estão limpas, 3 pedem atenção (acima).
> Ver a lista."*

## E.2 As cinco regras do recibo

```
1. NUNCA push. Nunca no topo. É rodapé e é página.
2. Sempre com contagem, o nome de cada verificação e o horário.
   "Conciliação Tokio — 210 apólices conferidas — 06:14 — limpa"
3. AUDITÁVEL: clicar em "limpa" mostra o que foi conferido.
   Sem isso é decoração.
4. Vale mais em fiscal e conformidade (onde silêncio gera ansiedade)
   do que em vendas (onde silêncio é normal).
5. Acumula. O trimestre inteiro fica consultável.
```

## E.3 O momento em que ele vale mais

**Quando o corretor perguntar "por que eu pago isso?".**

> *"Nos últimos 90 dias: 3.690 verificações, 47 achados, R$ 118 mil
> identificados, R$ 71 mil recuperados."*

**Isso liga direto no Outcome Loop da SPEC-059 e no billing da SPEC-062.**

## E.4 O que ele NÃO é

**Não é um Finding.** É derivado das execuções com resultado "limpo". **Não
polui a tabela de achados.**

## E.5 Testes

| # | Prova |
|---|---|
| E1 | o recibo nunca é enviado por push |
| E2 | cada verificação limpa é auditável — mostra o que conferiu |
| E3 | o acumulado do trimestre é consultável |
| E4 | o recibo não gera registro na tabela de achados |

---

# BLOCO F — A permissão para investigar

## F.1 Dois tempos

```
FAREJADA ......... sempre autorizada · orçamento fixo
                   produz INDÍCIO com magnitude e incerteza
                   nunca conclusão

INVESTIGAÇÃO ..... Work Run com custo, escopo e prazo declarados
                   passa por Approval (SPEC-055 — a peça já existe)
```

## F.2 O pedido precisa de quatro coisas, nesta ordem

```
1. O NÚMERO ................ "pode valer R$ 34 mil por ano"
2. A INCERTEZA HONESTA ..... "olhei 3 meses e 2 seguradoras; posso estar errado"
3. O CUSTO PARA ELE ........ "15 minutos meus, nada seu"
                             ou "preciso do extrato da Tokio"
4. O QUE SAI NO FIM ........ "a lista apólice a apólice e a carta pronta
                              para o gerente"
```

**A ordem importa.** O número prende a atenção; a incerteza compra a confiança.

## F.3 A frase-modelo

> *"Achei um buraco que pode valer R$ 34 mil por ano na sua comissão da Tokio.
> Olhei 3 meses e a diferença aparece em 47 de 210 apólices. Para ter certeza
> preciso conferir 12 meses e cruzar com os endossos — 15 minutos de
> processamento, nada seu. No fim você recebe a lista apólice a apólice e a carta
> para o gerente. **Investigo?**"*

**Botões:** `Investiga` · `Depois` · `Não é isso` *(com motivo — vira feedback)*

## F.4 As três regras duras

**F.4.1 — Só pede com número e evidência de nível 3 ou melhor.** Pedir permissão
para *"procurar algo"* é ruído puro e queima a confiança.

**F.4.2 — Uma investigação em curso por corretora.** Se já tem uma rodando, o
próximo indício entra na fila e aparece como *"tem outro fio para puxar quando
este terminar."*

**F.4.3 — Autorização permanente por domínio, opcional.**

> *"Da próxima vez que achar algo em conciliação de comissão, pode investigar sem
> perguntar."*

**Reduz atrito e é reversível a qualquer momento.**

## F.5 Testes

| # | Prova |
|---|---|
| F1 | indício sem número não gera pedido |
| F2 | o pedido tem as quatro partes, na ordem |
| F3 | só uma investigação em curso por corretora |
| F4 | "não é isso" com motivo vira feedback registrado |
| F5 | autorização permanente é reversível |

---

# BLOCO G — A copy

## G.1 A regra

```
A MANCHETE VENDE.  O ARTEFATO ENTREGA.
E no fim tem O TRABALHO JÁ FEITO — não a instrução de como fazer.
```

## G.2 A manchete

**Uma linha. Com o número. Com o link.**

```
WhatsApp / Telegram:
   "Achei ouro na sua contabilidade. R$ 98 mil que você pode não
    estar devendo. Detalhe completo: [link]"

E-mail — assunto:
   "R$ 98 mil que você pode não estar devendo"
```

**O que a manchete nunca faz:**

```
✗ prometer o que o artefato não entrega
✗ usar número redondo que não veio de conta
✗ ser genérica ("temos novidades para você")
✗ carregar o relatório inteiro pelo WhatsApp
```

## G.3 O artefato

```
1. TÍTULO         "Você paga imposto no anexo errado — e não é culpa sua"

2. O QUE DESCOBRI  em três frases, com o número na primeira

3. QUANTO VALE     a conta, aberta. Não "cerca de R$ 98 mil" — a conta.

4. POR QUE NINGUÉM VIU
                   a explicação de por que isso passa despercebido.
                   É o que faz o corretor confiar em vez de desconfiar.

5. O QUE FAZER SEGUNDA
                   passos concretos, na ordem, com quem falar

6. O TRABALHO PRONTO
                   a carta para o contador · a planilha · a lista
                   apólice a apólice · a mensagem para o cliente
```

**O item 6 é o que separa este produto de um relatório.**

## G.4 A separação que o Founder pediu

> **A tela do corretor nunca mostra instrução de agente.**
> **A instrução de agente nunca tem copy de venda.**

**São dois campos, com dois autores, no mesmo registro.** Hoje estão misturados —
e é parte da bagunça que a SPEC-064 desfaz.

```
copy_corretor ....... o que ele lê. Vende, explica, convence.
instrucao_agente .... o que o modelo lê. Precisa, seca, sem adjetivo.
```

## G.5 O tom

```
✓ direto, com número, sem adjetivo vazio
✓ o corretor é competente — a copy não explica o óbvio
✓ quando há incerteza, ela aparece
✗ nada de "revolucionário", "incrível", "transformador"
✗ nada de exclamação em cadeia
✗ nada de urgência fabricada
```

**A régua:** se um corretor experiente ler e pensar *"isso é conversa de
vendedor"*, a copy falhou.

## G.6 Testes

| # | Prova |
|---|---|
| G1 | toda manchete tem número que veio de conta |
| G2 | manchete no WhatsApp tem no máximo uma linha e um link |
| G3 | o artefato tem as seis seções |
| G4 | a seção 6 (trabalho pronto) nunca está vazia |
| G5 | copy do corretor e instrução do agente são campos separados |
| G6 | a copy não contém as palavras proibidas |

---

# BLOCO H — A memória

**O que o sistema sabe sobre ESTA corretora.**

## H.1 O defeito, medido

```
cartas no RAG .............. 8.916
conversas encerradas ....... 8.872
user_memories .............. 0
company_memories ........... 0
session_summaries .......... 1
```

**Oito mil, novecentas e dezesseis cartas de conhecimento. Zero memórias.**

Nenhuma das 8.916 sabe que a Resulta trabalha condomínio, que uma parceria foi
tentada em março, ou que o corretor odeia resposta longa.

## H.2 A distinção

```
RAG ......... o que o MUNDO sabe sobre seguros
MEMÓRIA ..... o que aconteceu AQUI
```

> **A segunda é a que torna o sistema insubstituível** — porque a primeira o
> concorrente também compra.

## H.3 Por que está zerado

`graph.py:1108` chama o gatilho de fechamento com
`last_message_at=datetime.now()`. **A inatividade é sempre zero, por construção,
dentro do turno.** A condição nunca é satisfeita.

O conserto existe (`memory_fabric.fechar_sessoes_inativas`) e roda no laço de
manutenção — **mas o piso é de 7 dias e há uma conversa nos últimos 7 dias.**
**O motor não está provado quebrado: está sem tráfego.**

## H.4 Os três tipos que importam

```
FATO ......... "a Resulta trabalha residencial e condomínio"
               "o vendedor Diego converte melhor em residencial"

EXPERIÊNCIA .. "tentamos parceria com o sindicato X em março; não fechou
                porque eles queriam exclusividade"
               "acionar vidros pela Allianz falhou 3 vezes na terça"

PREFERÊNCIA .. "ele quer o briefing às 6h, não às 8h"
               "ela não quer que a gente mande nada no sábado"
```

**A EXPERIÊNCIA é a que não existe hoje, e é a mais valiosa.**

## H.5 A forma: guardar a decisão, não a descrição

```
✗ "o cliente falou sobre parceria com sindicato"
✓ quando {parceria com entidade de classe}
  → {pedir exclusividade por ramo antes de discutir comissão}
  → porque {em março o sindicato X vendeu para a mesma base por outro canal}
  → resultado {a proposta caiu}
```

**Memória deve reter o que muda uma decisão, não um resumo do que foi dito.**
Isso a torna auditável e consumível pela camada de Skill.

## H.6 A regra que impede o apodrecimento

**A pesquisa de 30/07 nomeou dois modos de falha, e os dois são reais:**

```
brevity bias ....... resumir joga fora o detalhe de domínio que ERA o valor
context collapse ... reescrever iterativamente erode o detalhe com o tempo
```

**A regra que sai disso, e vale para playbooks também:**

> **O otimizador NUNCA reescreve uma memória ou um playbook inteiro.**
> **Emite deltas** — acrescenta, edita ou remove um item numerado, com
> proveniência por item.

Ganho medido dessa disciplina em pesquisa publicada: **+10,6% em tarefas de
agente**, sem supervisão rotulada.

## H.7 O teste de admissão

**Nenhum sistema de memória entra sem provar que ganha do baseline de "jogar tudo
no contexto".**

Uma auditoria acadêmica independente mediu que **muitos sistemas de memória
perdem para o baseline** — e ninguém percebe, porque o agente continua conversando
bem enquanto a memória apodrece.

```
[ ] medir o desempenho COM memória
[ ] medir o desempenho com contexto cheio, sem memória
[ ] a memória só entra se ganhar
```

## H.8 O que NÃO fazer

```
✗ produto de memória de terceiro como runtime
   (auditoria independente mediu 30% de operações malformadas em modelo
    pequeno — o agente conversa fluentemente enquanto a memória apodrece)
✗ grafo de conhecimento sobre as conversas
✗ segundo motor de memória ao lado dos três que já existem
   (memory_service, memory_fabric, agent_memory)
```

**Os três existentes precisam ser consolidados, não multiplicados** — e isso é
parte deste bloco.

## H.9 Testes

| # | Prova |
|---|---|
| H1 | memória é escrita fora do turno, no varredor |
| H2 | toda memória guarda decisão, não descrição |
| H3 | otimizador emite delta, nunca reescrita completa |
| H4 | escrita de memória com formato inválido é REJEITADA, não salva pela metade |
| H5 | o teste de admissão foi executado e a memória ganhou |
| H6 | existe um motor de memória, não três |
| H7 | memória de tenant A não vaza para tenant B |

---

# 2. Objetos novos

**Poucos. E nenhum é motor.**

```
analysis_definitions ..... o catálogo, versionado como Skill
analysis_runs ............ execução por tenant · resultado limpo|achado|erro
analysis_candidates ...... fila de crescimento do catálogo
probe_templates .......... as 6 formas paramétricas
value_domains ............ o mapa dos 12 domínios
vigilance_receipts ....... derivado de analysis_runs com resultado limpo
unanticipated_actions .... o Bloco B
```

**Alterações em tabela existente:** `intelligence_findings` ganha `classe`,
`valor_brl`, `esforco_do_corretor`, `janela_expira_em`, `analysis_definition_id`.

**Reusa sem tocar:** `intelligence_signals`, `intelligence_findings`,
`recommendations`, `briefing_*`, tiers de evidência, dedupe, cooldown, quiet
hours, Outcome Loop, Approval, Skills, Artifacts, Auxiliares.

---

# 3. Gate final

```
[ ] o relatório do Bloco 0, com as análises validadas
[ ] os 8 testes do Bloco A     [ ] os 5 testes do Bloco E
[ ] os 5 testes do Bloco B     [ ] os 5 testes do Bloco F
[ ] os 4 testes do Bloco C     [ ] os 6 testes do Bloco G
[ ] os 6 testes do Bloco D     [ ] os 7 testes do Bloco H
[ ] a suíte inteira verde
[ ] ao menos 12 análises validadas em dado real
```

## 3.1 A prova viva

```
1. rodar o catálogo na Resulta
   → ao menos 3 achados, com valor calculado e evidência

2. conferir o maior à mão
   → o número bate

3. mostrar ao corretor
   → ele diz "eu não sabia disso"  ← O TESTE QUE IMPORTA

4. abrir o recibo de vigilância
   → mostra o que foi conferido, e o limpo é auditável

5. pedir uma investigação
   → o pedido tem número, incerteza, custo e o que sai

6. deixar rodar uma semana
   → no máximo 3 por dia, uma manchete, backlog visível
```

**O passo 3 é o gate real.** Achado verdadeiro que o corretor já sabia **não é
ouro** — é confirmação. Vale, mas não é o produto.

---

# 4. Riscos

| Risco | Mitigação |
|---|---|
| achar coisa que o corretor já sabe | passo 5 do Bloco 0: perguntar antes de publicar |
| fadiga de alerta | dosagem do Bloco D; classe EXPOSIÇÃO separada de AGORA |
| achado falso destruir a confiança | validação à mão em 3 casos; nível de confiança sempre exibido |
| Anel 2 explodir em combinações | só campo marcado; teto por rodada; filtro de significância |
| memória apodrecer em silêncio | delta em vez de reescrita; rejeição de formato inválido |
| copy virar conversa de vendedor | palavras proibidas viram teste |
| o catálogo virar caixa-preta | o corretor vê a lista inteira |

---

# 5. O que NÃO pode acontecer

```
✗ motor de detecção novo ao lado do Intelligence Fabric
✗ tabela por auxiliar — persona é filtro, não motor
✗ achado sem valor em R$ no briefing
✗ achado sem evidência nomeada (apólice, cliente, número)
✗ mais de uma investigação por corretora ao mesmo tempo
✗ memória reescrita inteira por otimizador
✗ análise em produção sem validação à mão
✗ o nome "Garimpo" para isto — Garimpo é a voz do corretor (SPEC-059 §18)
```
