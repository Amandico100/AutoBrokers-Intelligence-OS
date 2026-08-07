# PLANO — Lapidar a Central de Agentes

> Decidido com o Founder em 07/08/2026, depois de uma auditoria com quatro
> auditores independentes e medição direta no banco de produção.
> **Commit base:** `1303648` · branch `feat/spec063-atendimento-canais`

---

## 1. O que este plano resolve, em uma frase

A esteira que transforma conversa de WhatsApp em inteligência está construída
inteira e bem construída — e **para em três lugares**: o RAG não sabe de qual
seguradora está falando na hora de responder, ninguém aposenta conhecimento
vencido, e o miolo está desligado por um freio de custo que vaza pelo cano mais
caro.

---

## 2. As decisões do Founder que este plano obedece

| # | Decisão | Consequência no plano |
|---|---|---|
| D1 | **O destilador automático fica DESLIGADO.** A destilação é feita pelo Plano Max, com subagentes Opus 5 orquestrados pelo Claude Code | Nenhum bloco liga `DESTILADOR_TETO_POR_RODADA`. O Bloco 5 é campanha manual |
| D2 | **Opus 5 na destilação**, não Sonnet. Inteligência importa mais que custo quando o custo é zero | Os subagentes do Bloco 5 são Opus 5 |
| D3 | **Todo conhecimento destilado é GLOBAL.** Regra de seguradora vale para qualquer corretora do Brasil | `knowledge_cards` continua sem `company_id`. Nenhuma carta pode citar corretora |
| D4 | **Três camadas de memória**: global (conversas destiladas) · corretora (InfoCap, dados dela) · usuário (conversas e conectores dele) | Bloco 4.3 liga a camada da corretora, que está vazia |
| D5 | **Conhecimento da Amandus não entra.** É corretora de teste; conversa de teste polui | Bloco 0.1 apaga só o que é dela |
| D6 | **Playbooks continuam em rascunho** até provarem 100/100 algumas vezes seguidas | Bloco 4.2 analisa e não ativa sem prova |
| D7 | **O corretor não tem filtro no chat principal.** Os dados são dele | Bloco 3.4 conserta o *fail-open*, mantendo o corretor sem filtro |

---

## 3. O que foi medido (📊 07/08/2026, produção `dcajcvlzcjbmyapmklil`)

```
CAPTURA          135.910 mensagens · 12.996 sessões · 3 corretoras · viva hoje
CARTAS            12.933 total · 12.071 publicadas · 0 esperando índice
                  186 chars de mediana · source_count = 1 em 100%
                  9.727 (80,6%) sem seguradora · 2.344 com seguradora
CLASSIFICAÇÃO     ramo e category: ZERO nulos — a etiquetagem é boa
BUSCA             insurer_key/ramo/category NÃO vão para o índice
                  o filtro por seguradora é aceito e descartado
CONTRADIÇÃO       5 cartas afirmam × 3 negam o boleto da Porto — todas publicadas
DESTILAÇÃO        parada desde 29/07 13:58 UTC · fila de 3.772 sessões
                  (1.855 depois de tirar a Amandus)
FREIO             teto de gasto = 0, e o Opus 5 escapa dele (linha 659)
SENTINELA         0 mapas ativos → route_drift = 0 · playbook_overlays = 0
MEMÓRIAS          global 12.071 · corretora 0 (vazia) · usuário 34
SUSEP             a máquina existe · research_monitors = 0 (ninguém ligou)
RERANKER          desligado (sem COHERE_API_KEY) — top-3 sai de RRF puro
AMANDUS           34.094 mensagens · 1.919 sessões · 0 destiladas · 0 cartas
```

---

## 4. Os blocos, na ordem de execução

Ordem escolhida pelo Founder: **estrutura → destilação → checkup**. Dentro
disso, a ordem é por dano evitado, e cada bloco deixa o seguinte possível.

---

### BLOCO 0 · Limpar o terreno

**0.1 — Apagar a corretora de teste (D5)**

📊 A Amandus tem 34.094 mensagens, 1.919 sessões, 107 conversas no chat e
**zero sessões destiladas**. Nenhuma carta do RAG veio dela — então o
apagamento **não toca em `knowledge_cards` nem no Qdrant**, e não há risco de
destruir conhecimento.

Regras de segurança da manobra:
- filtro por `company_id` exato, nunca por nome
- contagem antes e depois de cada tabela, registrada no relatório
- as outras duas corretoras contadas antes e depois: **os números têm de ser
  idênticos**. É a linha de controle (CLAUDE.md §9.2)
- ordem: filhos antes dos pais (transcripts → sessions), para não deixar órfão

**0.2 — Fechar o furo do freio de gasto**

`attendance_distiller.py:622` põe o teto de gasto em `teto`;
`attendance_distiller.py:659` **sobrescreve a mesma variável** com a
concorrência (6). Em `:682`, `min(teto, 3)` = 3, não 0.

📊 Prova com linha de controle: em 05/08, mesma rodada — **0 sessões
destiladas** (Sonnet, barato, bloqueado) e **2 playbooks gerados** (Opus 5, o
mais caro, passou).

Conserto: renomear a segunda para `concorrencia`. Teste com controle: com teto
0, `_call_llm(strong=True)` não pode ser chamado; com teto 1, **tem** de poder.

---

### BLOCO 1 · O RAG passa a saber de qual seguradora está falando

**É o bloco de maior ganho do plano inteiro.** Afeta as 12.071 cartas.

📊 O sistema classifica bem (`ramo` e `category` com zero nulos) e **descarta a
classificação na busca**:

- `attendance_distiller.py:477` grava só `scope`, `curation_status`, `namespace`
- `qdrant_service.search_similar` não tem parâmetro de seguradora
- `knowledge_scope.build_global_search_kwargs` **aceita `carrier_slug` e o joga
  fora** — o docstring assume: *"reservados para filtragem fina"*

Consequência: pergunta sobre a Porto pode ser respondida com a regra da
Allianz, e nada no sistema registra a troca.

**1.1** Gravar `insurer_key`, `ramo` e `category` no payload do Qdrant.
**1.2** Aceitar os três como filtro em `search_similar`.
**1.3** Ligar o filtro na busca global, com a regra:

> **"desta seguradora **OU** sem seguradora"** — nunca "só desta".

Essa regra é o coração do bloco. As 9.727 cartas genéricas (80,6%) são fato de
mercado e **devem** continuar respondendo qualquer pergunta. O que não pode é a
carta da Allianz aparecer numa pergunta sobre a Porto.

**1.4** Reindexar as 12.071 cartas. 💭 Custo estimado do embedding: ~US$ 0,01
(600 mil tokens a US$ 0,02/M). Ordem de grandeza de centavos.

**Teste com controle:** uma busca sobre a Porto não pode devolver carta com
`insurer_key='allianz'`; e a mesma busca **tem** de continuar devolvendo carta
genérica — senão o filtro virou censura.

---

### BLOCO 2 · O Curador ganha o segundo olho (o "agente de limpeza")

O Founder pediu um agente de limpeza. **Não criamos um.** Já existe o Curador
(`curadoria_cartas.py`), que faz exatamente esse trabalho com um olho fechado:
compara a carta nova só com as outras do mesmo lote, nunca com o acervo
publicado. Criar um segundo motor é o que a regra §5 do CLAUDE.md proíbe — é
assim que dois limpadores passam a se contradizer.

**O que o Curador passa a fazer:**

**2.1 — Enxergar o acervo.** Ao curar um lote, carregar também as cartas
`published` da mesma `insurer_key` + `category` e compará-las junto.

**2.2 — Detectar contradição.** Quando a carta nova nega a antiga, a antiga vira
`superseded`, **sai do índice** e guarda o link para quem a substituiu. Nada é
apagado: o histórico fica auditável.

Já existe um detector de contradição (`memory_fabric.contradiz`) com a lista de
negações certa — inclusive `"deixou de "`. Ele nunca foi ligado às cartas, e o
limiar de 0,60 de sobreposição é conservador demais para o caso da Porto (dá
0,40). **Reaproveitar o detector, calibrar o limiar contra os casos reais
medidos** — não escrever um terceiro.

**2.3 — Consolidar quase-cópias.** 📊 15 grupos já publicados, o maior com 6
cartas. A melhor vira a representante; as outras viram `superseded` apontando
para ela.

**2.4 — A validade das cartas.** Decisão do Founder, com a recomendação aceita:
**validade por evento, não por calendário.**

| mecanismo | efeito |
|---|---|
| **contradição** | carta negada sai do índice, fica no banco com o link |
| **reconfirmação** | fato visto de novo ganha data nova e **peso maior** |
| **rebaixamento** | carta velha sem contradição **não é apagada** — só desce no ranking |

Motivo: uma carta de 2026 pode valer em 2028, e uma de ontem pode morrer amanhã.
Data fixa erra dos dois lados. E só "regra operacional de seguradora" envelhece
— "vistoria complementar antes de liberar o complemento" é conhecimento do setor
e não tem prazo.

**Frequência:** por **evento**, ao fim de cada lote de cartas novas — que é o
único momento em que contradição nasce. Sem carta nova, custo zero. Semanal
deixaria a contradição da Porto viver sete dias.

**2.5 — Limpar o que já está errado hoje:**
- as cartas contraditórias da Porto sobre boleto atualizado
- a carta *"A casa opera com duas marcas, Resulta e Autofleet…"* — expõe
  estrutura comercial do cliente, viola D3
- ⚠️ **NÃO apagar** as outras três que citam "Autofleet": *"Autofleet" é também
  o nome de um sistema do Bradesco*. Elas são conhecimento legítimo e só
  precisam ganhar `insurer_key='bradesco'`. Apagá-las seria destruir
  conhecimento real — o erro que este item existe para evitar

---

### BLOCO 3 · Correções de qualidade e custo

**3.1** Tirar a hora do bloco cacheado do prompt. 📊 Só 2,3% de 4.509 chamadas
aproveitaram cache, porque a hora com minuto muda o bloco a cada 60 s e o TTL é
de 5 min. Paga-se para gravar e não se colhe.

**3.2** Modelos: sair do `gpt-4o-mini` onde ele degrada julgamento. A **memória**
é a prioridade (é ela que decide quais fatos sobrevivem; 📊 custa US$ 0,016/mês).
Autorização do Founder: trocar sem perguntar, informar depois, escolhendo por
custo × benefício da tarefa.

**3.3** Modelo de visão de reserva: `claude-3-5-sonnet-20241022` foi retirado
(404). O agente fica cego exatamente no caso que a linha promete cobrir. Limpar
também os 3 modelos retirados oferecidos na tela de configuração.

**3.4** O *fail-open* do papel: hoje papel desconhecido cai no prompt que entrega
CPF sem máscara. **O corretor continua sem filtro nenhum (D7)** — o que muda é
que papel vazio/errado passa a cair no prompt restrito, não no permissivo.

**3.5** O prompt diz *"destilado de atendimentos desta corretora"* — é falso
(D3: o acervo é global). Corrigir o texto.

**3.6** As 📊 342 sessões travadas com 3 falhas, todas de 28/07 — o dia do
pareamento, quando havia um bug já corrigido. Abrir 5, achar a causa, e criar o
caminho de reabilitação. Hoje elas saíram da fila para sempre.

---

### BLOCO 4 · Ligar o que está construído e desarmado

**4.1 — Os 10 mapas de URA.** 📊 Zero ativos → a sentinela sai na terceira linha,
`route_drift` = 0 e `playbook_overlays` = 0. Três subsistemas mortos.

**A auditoria de qualidade foi feita. O resultado é bom e tem um bloqueio.**

📊 **Os mapas NÃO inventam.** 2.620 de 2.621 nós (**99,96%**) e 3.515 de 3.621
opções (97,1%) aparecem **literalmente** numa mensagem real da seguradora. As 106
restantes foram investigadas uma a uma: são truncamento e mascaramento, nenhuma
é invenção. O Tecelão é determinístico — não há LLM no caminho padrão, cada nó é
o texto literal recebido. **Alucinação é impossível por construção.**

📊 **As 10 raízes estão certas** e 📊 **a cobertura sobe monotonicamente em 9 de
10** seguradoras — o agente aprendeu, não chutou. (A "queda" da tokio é a métrica
ficando honesta em 29/07, não o mapa piorando.)

🔴 **O bloqueio é higiene, não conteúdo:**

| | medido por mim | efeito |
|---|---|---|
| **115 nós com nome próprio não mascarado** (95 só na Porto) | são nomes de SEGURADOS e de atendentes | PII no conhecimento global |
| **24 nós com marca de corretora** (hdi 10, yelum 8, tokio 6) | a URA da Tokio é white-label; a raiz do mapa estampa "Autofleet Seguros" | viola D3 e CLAUDE.md §7 |

Causa: o mascarador só cobre nome **colado** na saudação; aqui ele está na
terceira linha e sobrevive.

**Ação:** remascarar `map.nodes[*].text` com padrão para nome fora da saudação
e para `<Nome> - <Corretora> Seguros`.

⚠️ **Linha de controle obrigatória (§9.2):** o conserto **não pode** mascarar
*"Marina, assistente virtual da Tokio Marine"* nem *"Maitê, assistente virtual da
MAPFRE"* — são personagens da URA, não pessoas. Sem esse controle, o conserto
apaga a identidade da tela.

Depois disso: promover **alfa, azul, allianz, zurich, bradesco, mapfre** (notas
75-88) e os 4 corrigidos. ⚠️ Todos com aviso: 📊 44-83% das telas estão `stale`.
E `insurer_key='technical__hdi'` é lixo de parsing — não promover.

**4.2 — Os 6 playbooks em rascunho.**

📊 **Estão limpos:** zero PII, zero CPF, zero telefone, zero placa, zero nome de
corretora nos 18. 📊 **São específicos:** 90-100% dos campos trazem a frase
pronta. E 📊 **os drafts de 05/08 não são piores que os ativos de 29/07** — a
diferença é quanto material havia no dia, não qualidade de escrita.

Notas: `auto/pneu` 88 · `auto/bateria` 88 · `auto/chaveiro` 86 ·
`residencial/chaveiro` 86 · `residencial/vidros` 85 · **`outro/vidros` 66**.

🔴 `outro/vidros` afirma *"a seguradora cobre a diferença"* em duas seções,
**contradiz o próprio campo de sensibilidade** (que manda nunca prometer valor) e
carrega `"valor X"` — um placeholder literal numa frase feita para ser enviada ao
segurado.

**Todos ficam em rascunho (D6).** O que este bloco faz é **consertar o agente que
os escreve**, não ativar os playbooks.

**4.2.1 — A causa da perda de qualidade, achada no prompt**

O prompt do Estágio 2 (`attendance_distiller.py:485`) pede *"o MELHOR playbook —
o padrão-ouro que um atendente deve seguir"*. Isso convida o modelo a preencher
lacuna com conhecimento de mundo em vez de extrair o observado. E não tem:

- nenhuma proibição de afirmar cobertura (o sistema **não tem** as condições
  gerais das apólices)
- nenhuma separação FATO / INFERÊNCIA
- nenhuma menção ao `score` do atendimento humano de origem — 📊 `auto/bateria`
  foi destilado de material com nota média **28/100** e o modelo não sabia
- nenhum piso de evidência: 📊 4 dos 6 drafts vêm de 3 a 6 conversas e afirmam
  "padrão-ouro do Brasil"
- proibição de placeholder em frase que vai ao segurado

**A casa já tem o prompt certo** — o de Estágio 1
(`scripts/destilacao_max/PROMPT-DESTILADOR.md`) tem todas essas regras. 📊
**Nenhuma das 11 chegou ao Estágio 2.** O conserto é copiar a régua que já
funciona, não inventar uma nova.

**4.2.2 — O congelamento: o agente escreveu uma vez e nunca mais**

`attendance_distiller.py:541` monta os pares que já têm playbook **sem filtrar
status**:

```python
existentes = {(r["ramo"], r["servico"]) for r in
              db.client.table("conduct_playbooks").select("ramo, servico").execute()...}
```

Qualquer playbook — inclusive um rascunho rejeitado — bloqueia aquele par
**para sempre**. 📊 `auto/sinistro` está fixado em 30 conversas enquanto **1.405**
foram destiladas e nunca serão lidas: **2,1% do material**.

Conserto: só playbook `active` bloqueia. Assim a versão 2 pode nascer quando
houver material novo — que é a condição para o "melhorar sempre" do plano.

**4.3 — A memória DA CORRETORA (D4).** 📊 `company_memories` = 0 registros,
**sem escritor e sem leitor no runtime**. A tabela existe, com CHECK, dedupe e
API. Falta gravar no fechamento de sessão e injetar no prompt ao lado da memória
do usuário. É a única das três camadas que não existe de fato.

**4.4 — O monitor da SUSEP.** 📊 A máquina existe (reconhece SUSEP, CNSP,
circular, resolução; prioriza `susep.gov.br` e `gov.br`) e `research_monitors` =
0: ninguém cadastrou. Cadastrar o monitor e ligá-lo ao Curador — mudança
regulatória tem de disparar a revisão das cartas afetadas.

---

### BLOCO 5 · A grande destilação pelo Plano Max (D1, D2)

O bloco mais demorado, e por isso o último antes do checkup.

📊 Fila depois do Bloco 0.1: **~1.855 sessões** (Resulta 980 + AutoFleet 875),
mais o que a Resulta trouxer ao parear.

1. Exportar em lotes (script já existe, mascara com as funções de produção)
2. **Subagentes Opus 5** destilam — um por lote, em paralelo
3. Aplicar ao banco (o script carrega; o modelo pensa)
4. O Curador com o segundo olho (Bloco 2) cura, consolida e publica
5. Conferência: contradição zero, quase-cópia consolidada, nenhuma carta
   citando corretora

**Custo de API: zero.** É o ponto inteiro do bloco.

---

### BLOCO 6 · Checkup geral

Bateria completa, `tsc`, rotas montam, e uma medição final do funil ponta a
ponta: conversa entra → vira carta → é indexada → é recuperada **com a
seguradora certa**.

---

## 5. Quando parear a Resulta

**Depois dos Blocos 1 e 2, antes do Bloco 5.**

O motivo é preciso: parear antes do Bloco 2 faria as conversas dela nascerem no
mesmo acervo sem detecção de contradição — 📊 e cada corretora nova multiplica
as contradições silenciosas. Parear depois do Bloco 5 deixaria o acervo dela
fora da grande destilação, e seria preciso repetir a campanha.

---

## 6. O que precisa do Founder

| # | O quê | Por quê |
|---|---|---|
| 1 | **Deploy** de `smith-api`, `smith-worker`, `smith-web` ao fim dos blocos de código | é da `main` que o EasyPanel constrói |
| 2 | **`COHERE_API_KEY`** (opcional, recomendado) | sem reranker, as 3 cartas que chegam ao modelo saem de RRF puro, que mede concordância de posição e não relevância. É a maior melhoria de qualidade por menor esforço |
| 3 | **Parear a Resulta** quando avisado | ver §5 |

---

## 7. O que este plano NÃO faz, e por quê

- **Não liga o destilador automático** (D1)
- **Não ativa playbook sem prova de 100/100** (D6)
- **Não apaga carta antiga sem contradição** — rebaixa no ranking
- **Não cria agente de limpeza novo** — estende o Curador (CLAUDE.md §5)
- **Não mexe** nos tetos de token que protegem custo (12 no dossiê, 80 no
  auxiliar, 400 no destilador): são freio de gasto, não descuido
- **Não conserta** Benchmark Global nem Sanitizar Documentos (📊 zero uso). São
  capacidade ociosa, não defeito. ⚠️ Fica registrado que **"Sanitizar" não
  remove PII** — preserva 100% da informação por desenho. O nome promete o
  contrário do que faz (CLAUDE.md §12.1)
