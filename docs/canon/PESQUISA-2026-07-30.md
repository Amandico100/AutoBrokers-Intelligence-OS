# Pesquisa de fundação — 30/07/2026

> Nove frentes de pesquisa em paralelo, Opus 5. Este documento é o insumo para
> as SPECs. **Não é SPEC.** Separa FATO (verificado) de INFERÊNCIA (deduzido).
> Commit base `4f827d2`.

---

## 1. O achado que vale mais que todos os outros

### As Condições Gerais de TODOS os produtos de seguro do Brasil são públicas

**FATO — verificado à mão em 30/07/2026:**

```
POST https://www2.susep.gov.br/safe/menumercado/REP2/Produto.aspx/Consultar
     multipart/form-data · campo: numeroProcesso
```

Sem autenticação. Sem CAPTCHA. Sem `__VIEWSTATE`.

Testado com o processo `15414.002216/2004-57` (Allianz, Auto-Casco):
**HTTP 200 · 72.638 bytes · 72 versões, cada uma com link de download.**

O download devolve `application/pdf` de verdade — um dos testados tem **138
páginas**.

### Por que isto muda a categoria do produto

**Cada produto tem N versões com vigência datada.** A Allianz mudou as
condições daquele produto **72 vezes**.

> Para responder *"esse sinistro tem cobertura?"*, o sistema precisa da versão
> **vigente na data da apólice** — não da mais recente.
>
> **Um RAG que indexa só a versão atual dá resposta errada para apólice em
> vigor, e não percebe.**

**É por isso que o fosso é a dimensão temporal, não o acervo.** Qualquer
concorrente consegue baixar PDF. Poucos vão modelar vigência — e quem não
modelar vai errar sem saber.

### E há uma chave de junção

O REP devolve `RAM: 05`, que casa com `ses_gruposramos.GRACODIGO` do SES.
**É a ponte entre o texto do contrato e a estatística de mercado.**

### O que NÃO fazer

**FATO:** o acervo é enumerável por ID sequencial — ~510 mil documentos,
~230 GB, sem autenticação, sem limite de taxa observado.

**Varrer tudo seria agressivo contra servidor de órgão público.** O desenho
certo é **ingestão dirigida**: os processos que a corretora comercializa, mais
backfill dos produtos líderes por prêmio. Isso são milhares, não centenas de
milhares.

---

## 2. A armadilha que zera o número mais importante

### Sinistralidade por seguradora existe — e a coluna documentada está morta

**FATO.** No `Ses_seguros.csv` (1.796.041 linhas, série desde 1995):

```
201306:  sinistro_retido = 2.481.933.031    sinistro_ocorrido = 0
201312:  sinistro_retido = 0                sinistro_ocorrido = 3.417.756.304
```

**A coluna viva é `sinistro_ocorrido` — e ela não consta na documentação
oficial.** Quem seguir o manual calcula **0,0% de sinistralidade em silêncio.**

Fórmula correta para dado moderno: `sinistro_ocorrido / premio_ganho`.
Em `SES_UF2` é o inverso — lá `sin_dir` é preenchido.

### O que o dado real diz (Auto-Casco, 12 meses até mai/26)

| Seguradora | Prêmio ganho | Sinistralidade | Desp. comercial |
|---|---:|---:|---:|
| Porto Seguro | 9,71 bi | **57,7%** | 22,8% |
| Tokio Marine | 5,81 bi | 57,8% | 20,1% |
| Bradesco Auto/RE | 5,00 bi | 56,1% | 18,9% |
| Allianz | 4,42 bi | **69,3%** | 21,7% |
| Yelum | 3,05 bi | **71,7%** | 22,4% |
| **Mercado** | **37,07 bi** | **61,3%** | 22,2% |

Por UF, mesmo ramo: **AP 95,1% · SP 67,8% · AM 56,6%.**

**É isto que transforma a conversa do corretor de opinião em evidência:** com
quem colocar risco, onde há margem, quem está fugindo do ramo.

### Outras armadilhas verificadas

- `SES_UF2.UF` tem **40 valores** — 27 UFs mais 13 duplicatas em minúscula.
  `GROUP BY UF` sem `UPPER()` racha estado em silêncio.
- `Ses_rmovram.csv` (294 MB) é **descontinuado desde 2014** — não ingerir.
- `ses_contatos.csv` e `Ses_Administradores.csv` são **nome de pessoa: PII.**

### Detecção de mudança sem baixar 542 MB

**FATO, medido:** `HEAD` para o ETag, e se mudou, ler **só** o sentinela
`Data_Final` de dentro do zip por range request.

```
6 requisições · 3.398 bytes · 0,0006% do arquivo
```

O arquivo muda toda semana; o dado avança uma vez por mês. **Isso elimina 3 de
cada 4 ingestões completas.**

---

## 3. A regra de ingestão que organiza tudo

A pergunta certa não é *"muda todo mês?"*. É **"quem é a autoridade sobre o
número?"**.

```
número ............... vai para TABELA, consultado por SQL determinístico
cláusula ............. vai para RAG, particionado por versão de vigência
identidade/situação .. consulta AO VIVO
```

**Sinistralidade não vai para o RAG.** Embutir `R$ 37.068.728.112` num chunk de
texto é convidar o modelo a errar aritmética e citar número velho sem saber.

E não adianta consultar "ao vivo": **o dado nasce com dois meses de defasagem.**
Não existe sinistralidade de hoje.

---

## 4. As fontes, em ordem de valor

| # | Fonte | Método | O que destrava |
|---|---|---|---|
| 1 | **REP — Condições Gerais** | RAG versionado por vigência | responder sobre o CONTRATO do cliente, não sobre o mercado |
| 2 | **SES** (`Ses_seguros` + `SES_UF2`) | tabela | sinistralidade e comissão por seguradora × ramo × UF, 27 anos |
| 3 | **ANS PDA** — reajuste real por contrato | tabela + RAG | o reajuste que a operadora REALMENTE aplicou; poder de negociação em saúde PME |
| 4 | **CNPJ Receita** (WebDAV, 39 snapshots) | tabela | prospecção com CNAE, porte, praça e contato |
| 5 | **API de corretores SUSEP** | ao vivo | 166.231 corretores; proxy da Receita por CNPJ, sem chave |
| — | ISP-RJ / SSP-SP | tabela | risco por município e **taxa por 100 mil veículos** |
| — | CNseg `Relatorios/List` | dimensão | mapeia código SUSEP ↔ razão social (o `LISTAEMPRESAS.csv` parou em 2019) |
| ✗ | **SUSEPCON** | — | congelado no 4T2025, Power BI não extraível |
| ✗ | **PIMS** | — | é só visualização do mesmo SES |

**A ANS surpreendeu.** O dataset de reajuste de planos coletivos responde uma
pergunta que **não tem equivalente no lado de seguros**: *"a operadora me
oferece 17% — quanto ela aplicou em contratos do mesmo porte, mesma UF, mesmo
ciclo?"*.

---

## 5. O concorrente, e onde ele não pode ir

**FATO.** Segura — R$ 45M de a16z e Kaszek, assistente "Helena" no WhatsApp,
**de graça para o corretor**, monetiza **take rate pago pelas seguradoras**.
Alvo: corretoras de até 7 funcionários. De 100 para 4.000 corretores em 15 meses.

### Onde não dá para competir

Em "assistente que responde no WhatsApp", **nada justifica cobrar**. Assistente
grátis vence assistente pago, sempre. Isso é table stakes.

### Onde está o fosso, e é estrutural

> **O cliente da Segura é a seguradora.**
>
> Um produto pago por seguradora **nunca poderá dizer** *"a Allianz está com
> 69,3% de sinistralidade contra 57,7% da Porto"*, ou *"a Porto te pagou
> R$ 1.847 a menos no mês passado"*.

**Todo entregável adversarial está permanentemente fora do roadmap deles.**
É fosso de modelo de negócio — o único tipo que sobrevive a R$ 45 milhões.

E a frase de venda que sai disso: **um produto de take rate tem incentivo para
colocar o negócio na seguradora que paga melhor o take rate. Um produto pago
pelo corretor tem incentivo para colocar na que atende melhor o cliente dele.**

### A honestidade

Vamos perder quem só quer um assistente. **Esses nunca pagariam nem R$ 52.**
O cliente certo é quem tem carteira onde 2% da comissão supera o preço — a
partir de ~700–900 apólices.

---

## 6. As dores medidas em campo

**FATO, de fontes reais:**

```
FIPE errado na apólice ............ R$ 8.000, descoberto no sinistro
estado civil errado ............... R$ 2.030 glosados na indenização
conciliação de comissão ........... "um ou mais dias por mês"
turnover do analista técnico ...... 49,3% ao ano
índice de solução das seguradoras . 73,1% (1 em 4 reclamações não resolvida)
```

### Dois mecanismos que ninguém ataca

**A comissão é liberada por parcela paga.** Se o segurado atrasa, a comissão não
é gerada — e a corretora descobre quando a apólice já foi cancelada.
**A receita do corretor depende de um evento que ele não monitora.**

**Pedir documento em fatias SUSPENDE o prazo de 30 dias do sinistro.** Não é
desorganização — é alavanca que a regra permite. **Quem entrega o dossiê
completo e datado de uma vez tira essa alavanca da seguradora.**

### O CBO oficial do Auxiliar de Seguros (R$ 1.986/mês)

*"transmitindo propostas, realizando cálculos, conferindo documentos,
cadastrando a apólice, preenchendo propostas de endosso e de renovação,
registrando cancelamento."*

**Sete verbos. Todos de transcrição.** É a definição estatal do trabalho.

---

## 7. O estado real do nosso sistema

### O que está no ar e nunca foi exercitado

```
research_requests ..... 0        tool_invocations ...... 0
admin_audit_events .... 0        eval_runs ............. 0
user_memories ......... 0        artifacts ............. 0 (corrigido em 30/07)
```

O Tool Gateway está `off`. O Context Assembly está em `shadow` — planeja e é
ignorado. A regra soberana da SPEC-052 (*"o RAG global nunca confirma sozinho
que uma apólice tem cobertura"*) **existe como constante que nenhuma rota de
produção chama.** No runtime, quem segura é a frase *"não invente cobertura"*
dentro do prompt.

### Corrigido nesta sessão

**Onze dos 19 templates existiam em código e não no banco**, e
`artifacts.template_key` é chave estrangeira. Entre os ausentes: os dois que o
briefing diário usa. **Toda criação de artefato morria em silêncio** — por isso
`artifacts = 0` com 17 briefings parados em `pending`: não havia o que entregar.
Migration + `_garantir_template` no serviço. 102 suítes verdes.

### O que ainda não entrega

`delivery_policy.decidir()` **não é chamada por ninguém.** Os 17 briefings
continuam `pending` — agora por falta da chamada, não por falta do artefato.

### A comissão que já raspamos e jogamos fora

O robô da Allianz lê `comissao` e `dt_prev_cancelamento` por parcela atrasada.
`_safe_items_for_payload` **descarta o campo `comissao`.**

**Mandamos o boleto ao cliente e nunca contamos ao corretor quanto do dinheiro
dele está preso.**

---

## 8. InfoCap — o que já dá e o que depende de um telefonema

**Acessíveis hoje, nunca chamados:**

```
/cotacoes?codfil=1 ....... pipeline comercial — O ÚNICO AGREGADO REAL, 1 chamada
/atendimentos?codfil=1 ... 2.355 registros na Resulta
/seguradoras ............. 61 companhias (decodifica ALLI → Allianz)
/ramos ................... 50 ramos
```

**Bloqueados (403), e a liberação é cadastro, não código:**
`/comissao` `/comissoes` `/financeiro` `/titulos` `/sinistro` `/propostas`
`/endossos` `/vendedores`

> As permissões são flags do perfil de API (`p500/p501=T`), **liberadas pela
> corretora dentro do próprio InfoCap.**

**Sem isso, comissão e sinistralidade da carteira são matematicamente
impossíveis.** É o desbloqueio de maior valor por menor esforço do projeto.

**E as flags chegam de graça na resposta do `/login` — o código lê o token e
descarta o resto.** Poderíamos saber sozinhos o que cada corretora liberou.

**Hipótese não testada:** `/producao` deu erro 500, mas foi chamado com
`texto=<cpf>`. "Produção" em corretagem é relatório de negócio emitido — deve
esperar `codfil` + período. **Se responder, a leitura agregada colapsa numa
chamada.**

---

## 9. Arquitetura — o que adotar, o que estudar, o que ignorar

### Adotar

| O quê | Por quê |
|---|---|
| **miniCOIL** no lugar do BM25 | *franquia*, *prêmio*, *sinistro* são polissêmicos; BM25 estatístico não distingue. Já está dentro do Qdrant que rodamos |
| **Contextual Retrieval** na ingestão | 35–49% de redução na falha de recuperação, ~US$ 13 uma vez |
| **bge-reranker-v2-m3** self-hosted | Apache-2.0; hoje pagamos Cohere **por consulta** e mandamos texto do cliente para fora |
| **Langfuse** self-hosted | MIT, sem trava no self-host, OTLP nativo; LGPD |
| **OTel `gen_ai.*`** via OpenLLMetry | instrumentar sem lock-in torna o backend trocável |
| **Tool Search** (GA, não medido) | 85% menos contexto; a degradação começa em 30–50 ferramentas |
| **hash da definição de tool + reaprovação** | classe P0: servidor muda a descrição depois de aprovado e nunca repergunta |
| **aprovação mostra a chamada REAL** | resumo amigável torna a aprovação teatro |

### A regra de multi-agente

> **Paralelize leitura. Serialize escrita. Verifique com contexto limpo.**

Duas empresas sérias publicaram conselhos opostos. **Não discordam** — cada uma
escreveu sobre o domínio onde a outra concede. A variável é conflito de escrita.

**Consequência arquitetural:** nenhum subagente escreve estado durável do
cliente. Ferramenta de subagente é **somente-leitura por construção**, não por
instrução de prompt.

### Autocrítica: o veredito é duro

**FATO** (Huang et al., ICLR 2024): CommonSenseQA cai de **75,8% para 38,1%**
quando o modelo é mandado revisar sem sinal externo.

Todos os números do Reflexion usam **verificador externo** — testes que rodam,
recompensa de ambiente, ground truth.

```
forma, tom, clareza ........ o modelo julga bem
correção factual ........... julgar equivale a resolver — não funciona
```

**Mas verificação adversarial com contexto limpo funciona, e há dado de
produção:** revisor separado pega **~2 bugs por revisão, 58% severos** — e
funciona melhor **quando o revisor não vê nada do que o gerador viu**.

**A peça a construir:** verificador que recebe só o achado, nunca o raciocínio,
e tenta refutá-lo consultando o RAG sozinho.

### Memória: temos conhecimento, não temos memória

```
cartas no RAG ......... 8.916      user_memories ......... 0
```

Nenhuma das 8.916 sabe que a Resulta trabalha condomínio, ou que uma parceria
foi tentada em março e como terminou.

**A regra a cravar:** o otimizador **nunca reescreve** um playbook — emite
deltas contra item numerado, com proveniência. Reescrever inteiro sofre
*brevity bias* e *context collapse*, ambos nomeados e medidos.

**E o teste de admissão:** um sistema de memória só se justifica se ganhar do
baseline de jogar tudo no contexto. Muitos não ganham, e ninguém percebe.

### Ignorar

**GraphRAG sobre as cartas** (existe para pergunta temática; a nossa é busca
local) · **produtos de memória de terceiro** (auditoria independente mediu 30%
de operações malformadas em modelo pequeno — o agente conversa bem enquanto a
memória apodrece) · **swarm de agentes negociando**.

### Armadilhas de licença

```
jina-reranker-v3 ..... CC BY-NC — PROIBIDO em produto pago,
                       e é o mais recomendado em todo blog
Marker (OCR) ......... pesos disparam cobrança acima de US$ 5M
AutoGen .............. CC-BY-4.0, licença de CONTEÚDO num framework
```

---

## 10. Robô em portal: o número que decide

**FATO:** melhor agente de navegador em tarefas de **escrita: 46,6%**. Leitura
passa de 70%.

**E a maioria das falhas não é de inteligência — é login, CAPTCHA e proxy.**

> Ler a comissão é a parte fácil. **Entrar é a parte difícil.**

A documentação da Anthropic diz *"não dê ao modelo acesso a credencial"* e três
seções depois ensina a passar usuário e senha. **Não é contradição — é dizer que
o caminho suportado é o caminho arriscado.**

### A estrada regulada existe

**Open Insurance Brasil** (Circular SUSEP 635/2021) — apólices, sinistros,
cotações e endossos por API certificada, com consentimento.

> **Corretoras habilitadas na SUSEP podem atuar como SPOC.**

```
apólice do cliente ....... OPIN. Regulado, consentido, auditável.
comissão da corretora .... sem API. Aqui robô é a única opção — e o risco é
                           outro: credencial DELA sobre o dado DELA.
```

---

## 11. Paradas canônicas — decisões do Founder (§10)

1. **FIPE** — a API interna funciona, mas a FIPE declara publicamente que não
   oferece API nem download. Conflito canônico + decisão comercial.
2. **Varredura do REP** — enumerar 510 mil PDFs de órgão público é trivial e
   agressivo. Ingestão dirigida é a recomendação; varredura exige decisão.
3. **PII nas bases públicas** — `ses_contatos`, `Ses_Administradores`,
   microdado de beneficiário da ANS, e-mail/CPF na base CNPJ.
4. **Benchmark entre corretoras** — a política de conhecimento global de 14/07
   diz que o global "nunca é acessível por corretora". Agregado derivado não
   está claramente permitido nem proibido.
5. **OPIN / habilitação como SPOC** — regulatório e comercial.

---

## 12. Lacunas declaradas — o que NÃO foi verificado

- Endpoint funcional de **normativos da SUSEP** — todos os caminhos deram 404
- Custo de licenciamento oficial da **FIPE** — não publicado
- **Endpoints reais do OPIN em 2026** — portal do desenvolvedor excedeu o limite
- **Termos de uso de portal de seguradora** — nenhum foi lido. Segfy usa "robô"
  abertamente, o que prova prática tolerada, **não permissão contratual**
- Medição de **N verificadores independentes com N>2**
- Distribuição publicada de **tamanho de corretora** — não existe; a inferência
  vem de Agger (≈3,9 usuários por firma) e do ICP declarado da Segura
