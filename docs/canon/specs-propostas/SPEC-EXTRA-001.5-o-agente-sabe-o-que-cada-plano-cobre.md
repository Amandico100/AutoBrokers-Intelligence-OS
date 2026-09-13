# SPEC-EXTRA-001.5 — O AGENTE SABE O QUE CADA PLANO COBRE

## Três níveis de assistência por seguradora, numa base com fonte e página por linha

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medida nesta redação:** `a0bb5fe` (worktree `AutoBrokers-FIX`; 📊 `git rev-parse HEAD` em 13/09/2026, 0 atrás e 0 à frente de `origin/main`).
**Branch sugerida:** `feat/spec-extra-001-5-planos-de-assistencia`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md`.
**Research Pack:** `SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre-RESEARCH-PACK.md`.
**Prompt de abertura:** `PROMPT-DE-ABERTURA-EXTRA-001.5.md`.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md`.
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.3, §3 (bloco 001.5), **§7.3** (a chave é nossa, não do sistema de gestão) e **§7.6** (os três níveis), §12.1 (ordem). D-PILOTO-01, D-PILOTO-11.
**Protocolo:** AAA v11.2 + OPÇÃO B. Marcha **PADRÃO**, **1 lente + juiz fresco + canário** · 💭 10–14 h · **trilho paralelo**, abre assim que o BLOCO A da 001.1 fechar.
**Absorve:** P-PILOTO-04 (a parte de conhecimento). **Depende de:** EXTRA-001.1 (a porta e a chave canônica).

---

## 0. Resultado e motivo

> O corretor pergunta *"o segurado X tem carro reserva?"*, *"cobre granizo?"*, *"qual o limite do guincho?"* — e recebe
> **sim · não · não contratado · não sabemos ainda**, com a **origem escrita ao lado** (o documento e a página), para
> **qualquer** seguradora que a corretora usa. A resposta diz o **nível** do plano contratado, e só isso já resolve a
> conversa: *"o seu é o Essencial da HDI: guincho até 200 km, sem carro reserva."* Quando existe plano acima **na
> tabela**, e só então, aparece o gancho comercial. **"Não sabemos ainda" é uma resposta honesta e conta como acerto.
> "A fonte não retornou" é falha, e tem outro nome na tela.**

### 0.1 Os números que motivaram — e os de hoje, remedidos

📊 Medido em **13/09/2026** sobre o banco de produção, só SELECT e contagem (as consultas estão no RESEARCH-PACK §2):

| o que se mediu | resultado |
|---|---|
| documentos normativos na base (`normative_documents`) | **194** |
| desses, **indexados** (`status='ingested'` e `chunk_count>0`) | **97** — bate com o diagnóstico |
| **seguradoras reais** com condição geral indexada | **8** (allianz · azul · bradesco · hdi · mapfre · porto · tokio · yelum) + `susep`, que é o regulador |
| siglas da **carteira viva** da corretora piloto (`seguradora-coenti.json`) | **61**; 14 com chave canônica; 📊 cobertura de prêmio **83,86%** |
| das 14 canônicas, quantas têm CG indexada **sob a mesma chave** | **6** — `tokio` não casa com `tokio_marine` (§0.3 ③) |
| **planos/níveis de assistência estruturados** em qualquer tabela do banco | **0** — nenhuma tabela, nenhuma coluna |
| linha do corpus que é do ramo dos pilotos | auto **24** · residencial **24** · condomínio **8** · **vida 101** (a maior fatia é o ramo que os pilotos não vendem) |
| cartas de conhecimento publicadas · de assistência · com seguradora nomeada | **17.995** · **1.535** · 20 chaves distintas (**784** cartas de assistência **sem** seguradora) |
| perguntas reais no acervo (`messages`, papel humano) | "carro reserva" **81** · guincho **121** · vidro **93** · eletricista **36** · granizo **26** · chaveiro **24** · encanador **24** |

⚠️ **Três números do diagnóstico não bateram, e o de hoje vence** (protocolo §5 ①). Estão listados com a consulta no
RESEARCH-PACK §3; o BLOCO 0 os reconfere e a divergência vai escrita no relatório:

| diagnóstico | medido em 13/09 | leitura |
|---|---|---|
| §3: *"hoje 10 de 61 seguradoras com CG"* | **8 de 61** por chave própria, **6 de 61** quando se exige que a chave case com o catálogo | o §1.3 do mesmo documento já dizia **8**; o "10" é o número frouxo |
| §1.3: *"`knowledge_cards`: 857, 39 de assistência, 4 nomeiam seguradora"* | **17.995** publicadas · **1.535** de assistência · **20** chaves | o número antigo é de um recorte; o denominador de hoje é outro |
| §1.3/§3: *"a ligação apólice → CG pelo processo SUSEP **já casa hoje**"* | 🔴 **não existe código que case** — e o caminho está **bloqueado** (§0.3 ②) | é a maior correção desta proposta |

E o efeito medido no piloto, que é o motivo de tudo: o agente **misturou Allianz auto com residencial** e admitiu
*"não recuperei o detalhe fino do plano VIP"* (diagnóstico §1.3). 📊 Hoje o que ele tem para responder sobre
assistência é `backend/app/services/assistance_policy.py` — **142 linhas, três serviços residenciais fixos**
(`:28`), **nenhuma seguradora, nenhum produto, nenhum nível, e a palavra "carro reserva" não aparece no arquivo**.

### 0.2 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | Decisão que governa esta execução | Onde |
|---|---|---|
| **D-PILOTO-01** | Conhecimento de atendimento é **GLOBAL**: toda corretora conectada usa o mesmo, nunca por corretora | `FOUNDER-DECISIONS.md:1745` |
| **D-PILOTO-08** | Numeração **EXTRA-001.5** dentro da família; nada renumera | `:1752` |
| **D-PILOTO-11** | **PDF** vence em cobertura/franquia/cláusula/**plano**; sistema de gestão vence em parcela/status. **A arquitetura não nasce presa à InfoCap**: porta `PolicyDataProvider`. **Seguradoras e ramos são catálogo nosso (chave SUSEP)**, nunca a lista do sistema de gestão | `:1755` |
| **D-PILOTO-14** | Alta qualidade sem ser exorbitante: **≤ 12 guardas novos**, bateria sobre o **motor** e o **acervo real** | `:1758` |
| **D-PILOTO-16** | SPEC-101 vira a porta; EXTRA-002/008/009 viram adaptadores | `:1760` |
| **D-PILOTO-20** | Proposta nasce no chat do Fable; **execução em chat novo, sob AAA opção B** | `:1763` |

🔴 **D-PILOTO-01 é o que decide a forma da tabela:** `insurer_assistance_plans` é conhecimento **global**, **sem
`company_id`**. O que a HDI cobre no plano Essencial é o mesmo para a Resulta, para a AutoFleet e para a corretora
que entrar amanhã. §3.3 escreve a prova de que isso não é um furo de isolamento, e sim a ausência de dado de
corretora.

### 0.3 🔴 As quatro correções que mudam esta SPEC — todas medidas hoje

**① O corpus não mora onde o diagnóstico diz. Mora em `normative_documents`, e o pipeline inteiro já existe.**

O pedido original fala em `documents` / `doc_kind`. 📊 `doc_kind` **não existe** em `documents`; é coluna de
`normative_documents`, com CHECK de 9 valores. E o que existe ali já é quase tudo de que as três ondas precisam:

```
normative_documents        insurer_key · product_line · doc_kind · susep_process · content_hash
                           effective_from/until · status · approved_at/approved_by
                           qdrant_collection · check_interval_days · next_check_at
backend/app/services/knowledge/insurance_corpus.py   2.020 linhas: descobrir · classificar ·
                           aprovar/rejeitar/candidatos · baixar · extrair · limpar · partir ·
                           etiquetar · indexar no global · versionar · reconferir
```

🔴 **A fila de curadoria que a proposta pediu (`curation_status`) JÁ EXISTE** — `status` + `approved_at`/`approved_by`,
com `aprovar()` (`insurance_corpus.py:1887`), `rejeitar()` (`:1900`), `candidatos()` (`:1908`) e a trava que faz valer:
`vencidos()` exige `approved_at is not null` (`:1921-1942`). **Criar um segundo `curation_status` ao lado seria motor
paralelo** (CLAUDE.md §5). Esta SPEC **pendura na fila que existe**; o que ela acrescenta é a curadoria da **linha
extraída**, que é outra coisa e mora na tabela nova (§5.4).

**② O elo apólice → condições gerais não existe. E está ativamente bloqueado.**

📊 Conferido hoje, linha a linha:

```
backend/app/services/knowledge/insurance_corpus.py:49   _RE_SUSEP = \b(\d{5}\.\d{6}/\d{4}-\d{2})\b
backend/app/services/knowledge/insurance_corpus.py:65   def extrair_susep(texto) -> Optional[str]   ← o extrator EXISTE
📊 normative_documents.susep_process preenchido em 190 de 194 (98%)  ← o lado do corpus está pronto

grep -rn 'eq("susep_process"' backend/ --include=*.py   →  VAZIO
grep -rni "susep" backend/app/services/policy_facts.py backend/app/services/assistance_policy.py \
     backend/app/services/policy_answer_composer.py backend/app/providers/policy_data_provider.py \
     backend/app/agents/tools/infocap_tool.py                                    →  VAZIO
```

🔴 **E a única ocorrência de `susep` na camada de apólice é o contrário do que se precisa:**

```python
# backend/app/services/policy_document_evidence_service.py:204-209
_BOILERPLATE_RE = re.compile(
    r"consulte|acesse|…|intervalo cont[ií]nuo|susep|ouvidoria|sac 24|…", re.IGNORECASE)
```

**Toda linha do PDF da apólice que menciona SUSEP é descartada como entulho institucional** — inclusive a linha que
carrega o número do processo. A ponte não está faltando: ela está **demolida de propósito**, por um filtro que foi
escrito para outro fim e nunca soube que ia atrapalhar este. Onda 2 (§7.2) tira `susep` dessa lista, liga
`extrair_susep` ao caminho documental da apólice, e o guarda **M-C2** exige **ZERO** casamentos com o filtro de volta
— porque é assim que se prova que era o filtro (CLAUDE.md §9.4).

**③ Não existe chave canônica de seguradora. Existem quatro, e duas já discordam.**

📊 14 tabelas do banco têm a coluna `insurer_key`. **Zero constraints** a mencionam:
`select … from pg_constraint where pg_get_constraintdef(oid) ilike '%insurer_key%'` → **nenhuma linha**.

```
portals.insurer_key              …  tokio_marine        (15 valores)
normative_documents.insurer_key  …  tokio               (9 valores)
knowledge_cards.insurer_key      …  tokio               (20 valores, inclui axa, chubb, essor, itau, youse)
seguradora-coenti.json .canonica …  tokio_marine        (14 das 61 siglas)
```

**Consequência medida:** a Tokio tem **15 documentos indexados** e, num casamento por chave canônica, **cairia para
zero, em silêncio**. A HDI tem **8** e **não aparece entre as 61 siglas da carteira** — é a seguradora da apólice de
referência da Saionara. 🔴 **Uma base de planos pendurada numa chave que ninguém governa é uma base que emudece por
digitação.** O Bloco A resolve isso antes da primeira linha de dado (§5.1), e o guarda **M-A1** fica vermelho quando
uma chave nova entra sem decisão.

**④ A procedência já é gravada — e morre na volta. Sem consertar isso, "origem escrita" é impossível.**

📊 `insurance_corpus.py:1125-1171` grava na raiz do payload do Qdrant: `insurer_key`, `product_line`, `doc_kind`,
`susep_process`, `effective_from`, `vigente`, `unit_id`, `parent_id`, `faceta`. 📊 `qdrant_service.py:891-909` monta o
resultado da busca com **oito chaves, e nenhuma delas é essas**: `score`, `score_scale`, `content`, `document_id`,
`agent_id`, `chunk_index`, `metadata`, `namespace`.

> **A procedência entra estruturada e volta como texto.** Hoje ela sobrevive só porque a etiqueta
> (`insurance_corpus.py:758-776`) é colada **dentro** do texto do pedaço. Uma resposta que precise dizer *"condições
> gerais da HDI, processo 15414.002160/2005-11, página 12"* não tem de onde tirar isso por campo.

E há um segundo buraco no mesmo lugar: 📊 **`doc_kind` nunca filtra.** Não está em `_INDICES_DE_PAYLOAD`
(`qdrant_service.py:88-99`) e não é parâmetro de `search_similar` (`:639-668`). Perguntar *"o que dizem as **condições
gerais** — não o manual do segurado — da Allianz auto"* é hoje **impossível de filtrar**.

🔴 **E o buraco que decide como a coleta funciona: o corpus normativo não tem página.** O chunker corta por **seção**
(`partir_documento`, `insurance_corpus.py:696`), e nenhum campo do payload carrega número de página. Do outro lado, o
caminho do PDF da apólice **tem** página (`policy_document_evidence_service.py:387-407`) e o guarda
`nodes.py:297-303` **já rejeita página inventada** — mas quando o docling entra como fallback, `:539-549` devolve
**uma única página, `page_number: 1`**, com o markdown inteiro dentro. **Citar página a partir do chunk indexado é
impossível; citar a partir do docling é mentir.** §7.1 resolve extraindo da **fonte arquivada**, não do pedaço.

### 0.4 EXECUTION CARD proposto — a medir no BLOCO 0, não a copiar

```text
OUTCOME .............. "tem carro reserva? cobre granizo? qual o limite do guincho?" → sim · não ·
                       não contratado · NÃO SABEMOS AINDA, com documento e página ao lado, dizendo
                       o NÍVEL do plano contratado, para toda seguradora que a corretora usa
RISCO ................ 7  =  ALCANCE 3 (o SEGURADO lê "você tem carro reserva")
                            + REVERSIBILIDADE 2 (dado e estrutura: tabela nova, CHECK de tabela viva)
                            + FREQUÊNCIA 2 (toda pergunta de cobertura, no chat e no atendimento)
                       ⚠️ VER §0.5: a soma dá CRÍTICO e a marcha fixada é PADRÃO. A divergência é
                          registrada, não silenciada.
SUPERFÍCIE ........... 2  (peça nova — a tabela e a Skill — mais comportamentos que eu consigo listar)
                       ⚠️ vira 3 se o BLOCO 0 achar leitor do corpus normativo fora da lista de §3.1
PISO APLICADO ........ §3.2 dispara em UM ponto e só nele: a migration que ALARGA O CHECK de
                       `doc_kind` numa tabela VIVA (§11.2). A tabela nova é aditiva e não dispara.
NÍVEL ................ PADRÃO — opção B, com o reforço de §0.5
UNIDADES ............. 5  ·  A tabela+chave  ·  B a Skill  ·  C as três ondas  ·  D a tela  ·  E a medição
COESÃO ............... A é arquivo-hub (a chave canônica + a migration): UM dono, primeiro, sozinho.
                       B e C consomem o contrato de A → integração SERIAL. D e E são disjuntas
                       (painel + relatório) e correm em paralelo a B/C.
PARALELISMO REAL ..... (D ∥ E) ∥ (A → B → C). Nenhum outro
TIME ................. investigador+pesquisador (um agente, §10 do protocolo) · desenhista da prova
                       ANTES do código · builder por unidade · verificador mecânico · UMA lente
                       (produto + DADO, porque o outcome É um dataset — protocolo §5 ④) ·
                       UM JUIZ FRESCO que confirma o conserto e audita o dado
REFERÊNCIA ........... INTERNA: `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` (254 linhas) —
                       o guarda que já exige que toda afirmação de COBERTURA aponte uma tela do acervo.
                       É o mesmo formato aplicado à linha da tabela. O juiz abre e compara.
                       + `backend/app/services/knowledge/insurance_corpus.py` (o pipeline a reusar)
                       EXTERNA: as 3 de §16, reabertas em 13/09/2026
GATES ................ GA, GB, GC, GD, GE, G-MIG, G-CANÁRIO da §10/§11 + os canônicos
O ELO ................ "o agente responde genérico PORQUE não há plano estruturado": medir A (as
                       respostas genéricas do acervo), medir B (0 linhas de plano em qualquer tabela)
                       e 🔴 medir que B CHEGA em A — rodar a Skill ATUAL sobre as perguntas reais e
                       mostrar `assistance_policy.py:28` devolvendo os mesmos 3 serviços para
                       uma pergunta de carro reserva em apólice de auto
FAIXA DE RELÓGIO ..... 💭 10–14 h  ·  faixa, nunca promessa (§9.2)
ORÇAMENTO ............ 💭 0,9–1,5 M tokens no chat executor (faixa de PADRÃO). Medir, não prometer
```

### 0.5 🔴 A divergência de marcha, escrita em vez de escondida

A conta do redator dá **RISCO 7 → CRÍTICO** pela tabela do protocolo §3.1. A marcha fixada pelo Founder
(diagnóstico §8 e §12.1, D-PILOTO-14) é **PADRÃO, 2 juízes**, e a instrução desta redação a ajustou para
**1 lente + juiz fresco + canário**. O protocolo §3.1 diz *"se o rótulo e a soma discordarem, a soma vence"*, e §3.2
diz que a exceção do Founder **só sobe**.

**Isto não é uma condição de parada** (não é nenhuma das oito do CLAUDE.md §10). É uma divergência a registrar e
resolver com nota (protocolo §9):

| caminho | nota | por quê |
|---|---|---|
| **PADRÃO com o piso aplicado nos dois pontos onde ele dispara de verdade** | **86** | a lente única é "produto + DADO" — a que o protocolo §5 ④ **exige** quando o outcome é um dataset; o juiz fresco audita o dado; o canário vivo prova a resposta; e a migration do CHECK (§11.2) recebe tratamento CRÍTICO com manifesto completo |
| subir tudo para 3 lentes | 62 | +2 lentes que leriam o mesmo diff de uma tabela e uma Skill; o defeito desta SPEC não é código, é **dado errado com cara de certo** — e isso uma lente de DADO pega melhor que três de código |
| baixar e seguir sem registrar | 15 | rebaixamento silencioso de um RISCO 7 que chega ao segurado |

🔴 **O executor recalcula no BLOCO 0.** Se a soma dele também der 6+, ele escreve a divergência no card definitivo,
mantém a marcha do Founder e **aplica o piso nos dois pontos**: (a) a migration do §11.2, (b) todo texto que chega ao
segurado (§6.3). Se der 5 ou menos, ele escreve por quê.

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira, antes de qualquer efeito

### 1.1 Allowlist

| Alias | Uso nesta SPEC |
|---|---|
| **TESTE-A** | único número de WhatsApp autorizado no canário de atendimento |
| **TESTE-B** | segundo número, só se o caso exigir dois interlocutores |

Os valores reais ficam na configuração privada já existente (`ATTENDANT_INBOUND_ALLOWLIST` /
`JANELA_SILENCIO_EXCECOES`, commit `05f46a9`). **Nunca commitar, publicar em dossiê, print, log, fixture ou
relatório.** No canon só existem os aliases.

### 1.2 O que está autorizado

- Ler o banco de produção com a chave de serviço, **em SELECT e contagem**.
- Ler o corpus normativo e as fontes arquivadas no MinIO (`acervo_arquivo`) — são **documentos públicos de
  seguradora**, não dado de cliente.
- **Baixar condições gerais e manuais de assistência de sites públicos de seguradora e do registro público da
  SUSEP (REP2)**, pelo caminho que já existe (`insurance_corpus._buscar`, `:1752`). Isto é leitura de documento
  público; não é portal com login, não é acionamento.
- Chat `core` do painel da Resulta pela conta do Founder, com as perguntas do corpus.
- Uma conversa de atendimento com **TESTE-A**, com o agente habilitado **apenas** para esse número.
- Rodar a suíte, mutações em cópia, scripts de medição read-only, e as migrations de §11 **depois** do gate.

### 1.3 O que permanece proibido

1. Qualquer mensagem a segurado real, seguradora, atendente, grupo de suporte ou número fora da allowlist —
   inclusive por fallback, alerta, fila, retry ou job de fundo.
2. Ligar o agente de atendimento globalmente numa corretora operacional "para o teste funcionar".
3. **Entrar em portal de seguradora com login, acionar assistência, abrir chamado ou alterar apólice.** Nada desta
   SPEC precisa disso — as fontes desta SPEC são documentos públicos.
4. Gravar em arquivo, log, teste, fixture, dossiê, commit ou relatório: CPF, CNPJ, telefone, nome de segurado,
   placa, chassi, e-mail, endereço, número completo de apólice ou credencial.
5. Copiar dado de uma corretora para outra "para montar teste".
6. **Publicar linha da tabela sem revisão humana** (§7.1). Extração assistida por modelo é proposta, nunca publicação.
7. Rodar migration antes do gate, ou aplicar `schema_completo.sql` / `upgrade_v6.2.sql` / `storage_buckets.sql`.

### 1.4 A verificação específica desta SPEC, antes de cada efeito

🔴 **Antes de gravar qualquer linha da tabela ou qualquer fixture:** o texto citado passa pelo redator de PII que já
existe e é **conferido por consulta**, não por leitura. Uma condição geral é documento público — mas o **exemplo**
que o extrator copiar pode ter vindo de uma apólice. **Valor em R$, km e dias é permitido; identificador de pessoa,
nunca.** E o trecho citado entra **como referência (documento + página + hash do trecho)**, não como cópia integral.

---

## 2. Escopo completo e exclusões deliberadas

### 2.1 Obrigatório nesta SPEC

1. **A chave canônica de seguradora**, governada e com guarda, antes da primeira linha de dado (§5.1).
2. **`insurer_assistance_plans`** (o plano, com `nivel` 1..N) e **`insurer_assistance_services`** (a linha de
   serviço, com **documento-fonte e página obrigatórios** por CHECK), migration expand-first com
   APPLY/VERIFY/ROLLBACK (§11).
3. **A Skill única `cobertura_e_assistencia`**, com os **cinco estados** de resposta e origem escrita (§6).
4. **`assistance_policy.py` vira fallback com marca** — não é apagado, não é duplicado (§6.5).
5. **As três ondas de coleta**, com **revisão humana antes de publicar** (§7).
6. **`doc_kind` passa a filtrar** — índice de payload e parâmetro de busca (§7.1).
7. **A procedência volta da busca** como campo, não como texto (§6.6).
8. **A tela mínima no painel (Conhecimento)**: cobertura da base e fila de curadoria (§8).
9. **A medição declarada**: hoje 8 de 61 / 0 de 61; meta por onda; `origem` gravada no turno (§9).
10. **P-PILOTO-04**, a parte de conhecimento: o checklist por tipo deixa de ser linha de prompt e passa a sair da
    base (§6.4). O escritor de `ficha.faltando` e o dossiê **ficam na 001.3** — está escrito em §17.

### 2.2 Fora desta SPEC, sem empobrecer o outcome

| Frente | Por que não entra | Gatilho de retorno |
|---|---|---|
| **Cotação e renovação** (orçar o plano superior, calcular prêmio, emitir) | 🔴 **É outra SPEC inteira.** Esta SPEC **diz** que o plano superior existe e o que ele cobre; **quem orça é gente**, e o gancho é uma frase que passa o caso para a atendente. Cálculo exige capacidade de precificação que não existe aqui | EXTRA-003 (renovação) e EXTRA-004 (cotação) |
| **A porta `PolicyDataProvider` e o modelo canônico de apólice** | É a **EXTRA-001.1**. 📊 A porta existe em `backend/app/providers/policy_data_provider.py:41`, hoje devolvendo `Dict[str, Any]`; a 001.5 **consome** o que a 001.1 entregar e não a reescreve | EXTRA-001.1, que roda antes |
| **Ler a apólice certa, em uma rodada** (vigência, ramo, briefing) | É a 001.1. A 001.5 recebe a apólice já escolhida | EXTRA-001.1 |
| **Coberturas patrimoniais além da assistência** (LMI, franquia, cláusula) | A 001.1 as entrega pela reconciliação CORP × PDF. A 001.5 responde "cobre granizo?" **pela cobertura que a 001.1 já traz**, e só usa a base nova quando a pergunta é de **assistência/serviço** | já coberto pela 001.1 |
| **Adaptadores Quiver, Agger, Segfy** | Sem credencial medida. A base desta SPEC pendura na **chave nossa**, então nasce servindo qualquer um deles | EXTRA-002/008/009 |
| **Reescrever o chunker do corpus para carregar página** | Mexeria em 42.091 pedaços indexados por uma necessidade que §7.1 resolve pela fonte arquivada. **Fica registrado como pendência com número** | SPEC de RAG, ou quando a segunda consumidora aparecer |
| **Rajadas, debounce, dossiê ao grupo** | 001.2 e 001.3, mesmo arquivo, dois escritores | EXTRA-001.2 / 001.3 |

🔴 **Nada da §2.1 sai em silêncio.** Conflito material vai para `CHANGE-ADDENDA.md` classificado
(BLOCKER · ESSENCIAL · VALIOSA · FUTURA), com problema, evidência, consequência e autorização (CLAUDE.md §11).
**Escopo não se reduz sem decisão explícita do Founder (D5).**

---

## 3. Autoridades preservadas e arquitetura — o que já existe, e por que não se refaz

### 3.1 A tabela do que se reaproveita, por caminho

| peça que a SPEC precisa | **já existe em** | o que a 001.5 faz com ela |
|---|---|---|
| corpus normativo + curadoria + versão + manutenção | `backend/app/services/knowledge/insurance_corpus.py` (2.020 linhas) · `normative_documents` · `normative_document_versions` | **reusa inteiro**. Nada de segundo pipeline |
| extrator de processo SUSEP | `insurance_corpus.py:49,65` (`_RE_SUSEP`, `extrair_susep`) | **reusa** — o que falta é chamá-lo do lado da apólice (§7.2) |
| normalizador de processo malformado | `backend/app/services/knowledge/susep_rep2.py:214-216,286-292` | reusa |
| fila de curadoria humana | `insurance_corpus.py:1887` `aprovar()` · `:1900` `rejeitar()` · `:1908` `candidatos()` · rota `backend/app/api/corpus.py:90-96` | **pendura**; a curadoria da **linha** é irmã, não substituta (§5.4) |
| manutenção por `content_hash` | `insurance_corpus.py:58-62` e `:1433-1438` (hash com espaço normalizado, para PDF re-renderizado não parecer mudança) | **reusa**. `next_check_at` já está preenchido em 194 de 194 |
| arquivo da fonte (bytes originais) | `insurance_corpus._guardar_a_fonte:1608` → `backend/app/services/knowledge/acervo_arquivo.py` (MinIO) | 🔴 **é daqui que a extração lê a página** (§7.1) |
| coleção global e o escopo | `backend/app/services/knowledge_scope.py:37` (`GLOBAL_COLLECTION`) · `:384` (`build_global_search_kwargs`) | **reusa**. Nenhuma coleção nova |
| busca híbrida com filtros por seguradora/namespace/faceta | `backend/app/services/search_service.py:466-579` · `backend/app/services/qdrant_service.py:434-579,835-854` | **estende** com `doc_kind`; não cria segundo buscador |
| catálogo de seguradoras (chave SUSEP) | `docs/canon/providers/susep/seguradora-coenti.json` + `backend/app/providers/susep_ses_provider.py:129-212` | **pendura nele**; §5.1 acrescenta o que falta |
| catálogo de ramos | `docs/canon/providers/susep/ramo-cogrupo.json` (50 ramos) | idem |
| a porta da apólice | `backend/app/providers/policy_data_provider.py:41,55,137,144` | **consome o que a 001.1 entregar**; a 001.5 **não a edita** |
| plano vindo do documento | `policy_document_evidence_service.py:230-318` — `_ASSISTANCE_HEADER_RE`, `kind="assistance_plan"`, `kind="assistance_services"` | 🔴 **já extrai bloco de assistência do PDF da apólice.** É o elo entre a apólice e o `nivel`. **Reusa** |
| regra de assistência residencial | `backend/app/services/assistance_policy.py` (142 linhas) | **vira fallback com marca** (§6.5), não é apagado |
| guarda de resposta com fonte | `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` | **referência interna do juiz**; o molde de M-B2 |
| guarda de página citada | `backend/app/agents/nodes.py:297-303` — rejeita página que não está no texto determinístico | **reusa o padrão** para a página da condição geral |
| registro de ferramenta do turno | `tool_invocations` + `skills/gateway.py:294,323` + `nodes.py:784,1057` | **grava `origem` no turno pelo que existe** (§9.3); nenhum segundo registro |

### 3.2 🔴 A fronteira, escrita como regra verificável

```
A BASE É GLOBAL: nenhuma tabela desta SPEC tem company_id, e nenhuma linha dela
        carrega nome, documento, telefone, apólice ou qualquer dado de cliente.
NINGUÉM cria segunda coleção de Qdrant, segundo pipeline de ingestão, segunda fila
        de curadoria, segundo catálogo de seguradoras ou segundo caminho de leitura documental.
NENHUM texto que chega ao corretor ou ao segurado nomeia o sistema de gestão —
        diz "as condições gerais da <seguradora>" e "o documento oficial da apólice".
NENHUMA linha entra na base sem documento-fonte e página. O BANCO recusa, não o código.
```

### 3.3 Multi-tenant — e por que aqui a prova é ao contrário (CLAUDE.md §7)

CLAUDE.md §7 exige *"teste automático de isolamento com dois tenants reais"* em todo contrato novo. **Esta base não
tem tenant.** A prova, então, não é "o tenant B não vê a linha do A" — é **"não existe dado de corretora aqui"**, e
ela tem três partes, todas verificáveis por máquina (guarda **M-A4**):

1. **Estrutural:** nenhuma tabela desta SPEC tem `company_id`, `user_id` ou FK para `companies`. Um `ALTER TABLE`
   que acrescente `company_id` deixa o guarda vermelho — porque conhecimento global com coluna de dono é o começo
   de "a base da Resulta" (D-PILOTO-01).
2. **De conteúdo:** o varredor de PII que já existe (`backend/scripts/auditar_pii_no_codigo.py` + o redator de
   saída) roda **sobre as colunas de texto da tabela** e não acha nada. Zero é o número exigido.
3. **De efeito:** a leitura (§6) é feita pela `build_global_search_kwargs()` que já existe
   (`knowledge_scope.py:384`), que **não passa `company_id` algum** e isola por `scope_match=GLOBAL_SCOPES` +
   `curation_published_only=True` (`:383-389`). O teste de duas corretoras prova que **as duas recebem a mesma
   resposta** para a mesma apólice da mesma seguradora — que é o outcome, não o risco.

⚠️ **O que continua sendo tenant-scoped e não muda:** a **apólice** do segurado, que chega pela porta da 001.1 com
`company_id` explícito. A base diz *"o plano Essencial da HDI tem guincho até 200 km"*; **quem tem esse plano** é
dado da corretora e nunca entra aqui.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código

> Este documento envelhece. As linhas abaixo foram conferidas em 13/09/2026 sobre `a0bb5fe`. **O número do
> executor vence** (protocolo §5 ①).

1. **Preflight**, nesta ordem, com a saída colada no relatório: `git fetch origin` ·
   `git rev-list --count HEAD..origin/main` (🔴 tem de ser 0) · `git rev-list --count origin/main..HEAD` ·
   `git branch --show-current` · `git rev-parse HEAD` · `git status --short`.
2. **Confirmar que a 001.1 fechou o BLOCO A.** Esta SPEC consome a porta e a chave. Se a 001.1 ainda não entregou,
   o executor mede o que existe hoje (`policy_data_provider.py:41-52`, dois métodos `**kwargs`) e escreve o
   contrato mínimo de que precisa — **sem editar a porta**, para não haver dois escritores no mesmo arquivo.
3. **Reabrir cada `arquivo:linha` do RESEARCH-PACK §1.** Divergiu? corrigir na SPEC definitiva **e anotar a
   divergência**.
4. 🔴 **Remedir as sete contagens de §0.1** com as consultas do RESEARCH-PACK §2. As três divergências do
   diagnóstico entram na matriz de premissas corrigidas com o número de hoje.
5. **Medir o casamento de chave**, que é o que decide o tamanho do Bloco A:
   `normative_documents.insurer_key` × `portals.insurer_key` × `knowledge_cards.insurer_key` ×
   `seguradora-coenti.json.siglas[].canonica`. 📊 Esperado hoje: `tokio`≠`tokio_marine`, `hdi` fora das 61 siglas,
   e 20 chaves em `knowledge_cards` contra 15 em `portals`. **Contar os órfãos dos dois lados.**
6. **Ler `MIGRATIONS-AUTHORITY.md` inteiro** antes de qualquer SQL. 🔴 Medir o DDL **real** de
   `normative_documents` no catálogo do Postgres, porque 📊 a tabela é **classe SEM_ARQUIVO**: o único DDL no
   repositório é `docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`, marcado
   **PROIBIDO APLICAR**. O CHECK de `doc_kind` que vai ser alargado precisa ser lido do banco, não do arquivo.
7. **Medir o ELO com a ferramenta que vai usar** (CLAUDE.md §9.4): rodar a Skill **atual** sobre 10 perguntas reais
   de "carro reserva" do acervo e mostrar `assistance_policy.py:28` devolvendo os mesmos três serviços
   residenciais. Isso é o que prova que B chega em A.
8. **Provar a armadilha do `susep` no boilerplate com comando:** rodar o extrator documental sobre um PDF de
   apólice do acervo **com** e **sem** `susep` em `_BOILERPLATE_RE` e contar os processos SUSEP recuperados.
   📊 Esperado: **0 com o filtro, ≥1 sem**.
9. **Estabelecer a linha de base da suíte** (falhas preexistentes nomeadas, uma a uma). "Preexistente" é veredito
   por teste, nunca rótulo de lote. 🔴 Conferir se **P-PILOTO-20** (4 guardas de policy mudos no harness) já foi
   fechada pela 001.1 — se não, **eles guardam a superfície que esta SPEC também mexe**, e a SPEC não fecha com
   eles mudos.
10. **Recontar RISCO e SUPERFÍCIE** (§0.4) e escrever o card definitivo no §0.1 do relatório, com a divergência de
    marcha de §0.5 resolvida por escrito.

**GATE B0:** matriz `premissa → observação nova → comando/consulta → decisão`, com **as divergências listadas**.
Nenhum achado não reproduzido entra como incidente confirmado.

**MUTAÇÃO B0:** o pacote de aquecimento carrega **duas afirmações deliberadamente falsas, assinadas**
(§6 do prompt de abertura). O executor tem de refutá-las **com comando**, não com leitura.

---

## 5. BLOCO A — A CHAVE E A TABELA

> Arquivo-hub. **UM dono. Primeiro, sozinho, antes de B, C, D e E.**
> Arquivos: `backend/app/providers/insurer_catalog.py` (novo, pequeno) ·
> `docs/canon/providers/susep/seguradora-coenti.json` (linhas novas, revisadas) ·
> `backend/supabase/migrations/20260913_01_extra0015_assistance_plans.sql` (novo) ·
> `backend/supabase/migrations/20260913_02_extra0015_doc_kind_manual.sql` (novo).

### 5.1 A chave canônica — governada, antes do primeiro dado

📊 O catálogo já tem a governança certa escrita, e é o que se estende (`susep_ses_provider.py:165-167`):

> *"Uma sigla só entra no arquivo por igualdade de nome COMPLETO com o Noenti do SES ou por DECISÃO EXPLÍCITA de
> gente. Nunca por derivação de string em runtime."*

**O que a 001.5 acrescenta, e só isso:**

1. **Um módulo de leitura único** — `backend/app/providers/insurer_catalog.py` — com `chave_canonica(valor)` que
   resolve uma chave vinda de qualquer tabela para a canônica, por **mapa explícito**, e devolve a sentinela
   `UNKNOWN` (a string, nunca `None` — o motivo está em `susep_ses_provider.py:92-95`) quando não casa.
2. **A linha de conciliação que falta**, medida em §0.3 ③: `tokio` → `tokio_marine`, e as chaves de
   `knowledge_cards` que não existem em `portals` (`axa`, `chubb`, `essor`, `itau`, `unimed`, `youse`) entram
   **listadas** no arquivo versionado, com o critério ao lado. 🔴 **Uma por uma, revisada por gente.**
3. **`hdi` entra nas siglas** ou fica registrado por que não entra — 📊 ela tem 8 documentos indexados e é a
   seguradora da apólice de referência.
4. **A tabela nova referencia a chave canônica**, e o guarda **M-A1** fica vermelho quando aparece linha com chave
   que o catálogo não conhece.

⚠️ **O que a 001.5 NÃO faz:** normalizar `insurer_key` nas 14 tabelas que já existem. Isso é migração de dado em
superfície que esta SPEC não mede, e viraria uma SPEC própria. **Fica como pendência com número**, e o módulo de
leitura resolve o problema no ponto de uso. Nota: resolver no ponto de uso **82** × migrar 14 tabelas agora **40**.

### 5.2 As duas tabelas — e por que são duas

O diagnóstico pede uma tabela com *"seguradora · ramo · produto · plano · nivel · serviço · coberto · limites ·
carência · condições · fonte · página · vigência · confiança"*. Isso é **duas coisas**: o plano (que tem nível e
vigência) e a linha de serviço (que tem limite, carência e **fonte**).

| forma | nota | por quê |
|---|---|---|
| **`insurer_assistance_plans` (plano) + `insurer_assistance_services` (linha de serviço)** | **88** | *"existe plano acima?"* é consulta sobre planos; *"tem carro reserva?"* é consulta sobre serviços. O CHECK de fonte obrigatória pertence à **linha**, não ao plano. E a linha muda de versão sem o plano mudar |
| tabela única | 60 | repete seguradora/ramo/produto/plano/nível em cada serviço; o *"plano acima"* vira `DISTINCT` sobre dado repetido, e a primeira divergência de nível entra sem ninguém ver |

**O nome que o Founder fixou (`insurer_assistance_plans`) fica no pai.** A filha é irmã, não substituta.

```sql
-- O PLANO: o que a seguradora vende, e em que nível
insurer_assistance_plans
  id                uuid    pk
  insurer_key       text    not null   -- chave CANÔNICA (§5.1)
  ramo              text    not null   -- chave nossa (ramo-cogrupo.json)
  produto           text    not null   -- "Auto Perfil", "Residencial Mais"; 'GERAL' quando a CG não separa
  plano             text    not null   -- "Essencial", "Completo", "VIP"
  nivel             int     not null   -- 1..N DENTRO do produto. 1 = o mais básico
  vigencia_inicio   date    not null
  vigencia_fim      date    null       -- null = vigente
  susep_process     text    null       -- o elo com a condição geral (§7.2)
  documento_id      uuid    not null   -- FK -> normative_documents
  pagina            int     not null   -- a página onde o plano é nomeado
  confianca         text    not null   -- alta | media | baixa
  curadoria         text    not null   -- rascunho | proposto | publicado | rejeitado
  revisado_por      uuid    null
  revisado_em       timestamptz null
  content_hash      text    not null   -- do documento de origem, para a manutenção (§7.4)
  unique (insurer_key, ramo, produto, plano, vigencia_inicio)
  unique (insurer_key, ramo, produto, nivel, vigencia_inicio)   -- 🔴 dois planos no mesmo nível é erro

-- A LINHA DE SERVIÇO: o que aquele plano faz, com fonte obrigatória
insurer_assistance_services
  id                uuid    pk
  plano_id          uuid    not null   -- FK -> insurer_assistance_plans, on delete cascade
  servico           text    not null   -- chave nossa: guincho | carro_reserva | chaveiro | vidros |
                                       -- eletricista | encanador | granizo_vistoria | hospedagem | ...
  coberto           text    not null   -- sim | nao | condicionado
  limite_valor      numeric null       -- 200, 7, 3
  limite_unidade    text    null       -- km | dias | acionamentos_ano | reais | horas
  limite_texto      text    null       -- a prosa, quando o limite não é número
  carencia_dias     int     null
  condicao          text    null       -- "só em caso de sinistro coberto"
  documento_id      uuid    not null   -- FK -> normative_documents   🔴 NOT NULL
  pagina            int     not null   -- 🔴 NOT NULL, >= 1
  trecho_hash       text    not null   -- sha256 do trecho citado; o trecho CRU não é copiado
  confianca         text    not null
  curadoria         text    not null
  revisado_por      uuid    null
  revisado_em       timestamptz null
  unique (plano_id, servico)
```

🔴 **`servico` é chave nossa, não texto livre.** Uma tabela em que "carro reserva", "veículo reserva" e "carro
extra" são três serviços diferentes não responde a pergunta. O vocabulário nasce **das perguntas reais do acervo**
(📊 §0.1) e mora num arquivo versionado ao lado do catálogo de seguradoras, com sinônimos declarados — **nunca num
regex escondido**.

### 5.3 🔴 O CHECK que recusa linha sem fonte — no BANCO, não no código

```sql
constraint servico_tem_fonte check (
    documento_id is not null
    and pagina is not null and pagina >= 1
    and trecho_hash is not null and length(trecho_hash) = 64
),
constraint servico_publicado_foi_revisado check (
    curadoria <> 'publicado'
    or (revisado_por is not null and revisado_em is not null)
),
constraint limite_tem_unidade check (
    limite_valor is null or limite_unidade is not null
)
```

A segunda é a que impede o pior desfecho desta SPEC: **uma extração assistida por modelo publicando sozinha**. O
banco recusa `curadoria='publicado'` sem revisor. Guarda **M-C1**.

A terceira é pequena e cara: 💭 `limite_valor=200` sem unidade vira "200 dias de carro reserva" na cabeça de quem
lê. **Número sem unidade é número errado.**

### 5.4 A curadoria da linha é irmã da curadoria do documento

| o que é curado | onde já mora | o que a 001.5 acrescenta |
|---|---|---|
| **o documento** (esta condição geral é de quem, de que ramo, e vale?) | `normative_documents.status` + `approved_at`/`approved_by`; `aprovar()`/`rejeitar()`/`candidatos()` | nada. Reusa |
| **a linha extraída** (este plano tem este serviço com este limite?) | 🔴 não existe | `curadoria` + `revisado_por`/`revisado_em` nas duas tabelas novas, e a fila na tela (§8) |

**São dois julgamentos diferentes.** Aprovar o PDF da HDI não é aprovar a afirmação *"guincho até 200 km"*. Juntar
os dois num campo só faria a aprovação do documento publicar 40 linhas que ninguém leu.

### 5.5 GATE A e MUTAÇÃO A

**GATE A:**
1. As duas tabelas existem com os CHECKs; `INSERT` sem `documento_id`, sem `pagina`, com `pagina=0`, e
   `curadoria='publicado'` sem revisor são **recusados pelo banco** — a saída do erro vai colada no relatório.
2. `chave_canonica("tokio")` e `chave_canonica("tokio_marine")` devolvem **a mesma** chave; `chave_canonica("xpto")`
   devolve `UNKNOWN` **com o nome listado**, nunca omitido.
3. Nenhuma coluna `company_id` em nenhuma das duas tabelas; o varredor de PII sobre as colunas de texto acha **zero**.
4. Duas corretoras, a mesma apólice da mesma seguradora → **a mesma** linha de resposta (§3.3).

**MUTAÇÃO A:** (a) `documento_id` ou `pagina` nullable; (b) `pagina = 0`; (c) `curadoria='publicado'` com
`revisado_por IS NULL`; (d) `ALTER TABLE … ADD COLUMN company_id uuid`; (e) `limite_valor` sem `limite_unidade`.
**As cinco têm de ficar vermelhas.**

---

## 6. BLOCO B — A SKILL `cobertura_e_assistencia`

> Arquivos: `backend/app/agents/tools/cobertura_e_assistencia.py` (novo) ·
> `backend/app/services/assistance_policy.py` (vira fallback) ·
> `backend/app/services/search_service.py` / `qdrant_service.py` (o filtro e a procedência de volta) ·
> `backend/app/agents/nodes.py:307-317` (o guarda que muda de regra).

### 6.1 Skill ou tool? — a decisão, com nota

📊 O GLOSSARIO define **Skill** como procedimento versionado (`skills`/`skill_releases`, 21 releases no banco) e
**Tool** como implementação (`tool_definitions`, 32 linhas). 📊 O caminho de apólice de hoje é **tool**:
`InfocapPolicyLookupTool` registrada em `backend/app/agents/graph.py:447-449` sob capability
`operational.infocap.policy_lookup.read`, e o `SkillRegistry` só é tocado por `gateway_cutover.py:153` e
`auxiliaries/factory.py:333`.

| forma | nota | por quê |
|---|---|---|
| **tool em `app/agents/tools/`, registrada em `tool_definitions`, sob capability própria** | **88** | é o caminho que o chat e o atendimento realmente percorrem; ganha o registro em `tool_invocations` de graça (§9.3); o nome "Skill" do diagnóstico é o **conceito**, e o conceito cabe numa tool |
| skill release no `SkillRegistry` | 45 | criaria um segundo caminho de resolução ao lado do que a tool usa — motor paralelo (CLAUDE.md §5) para um ganho que o BLOCO 0 não mediu |

⚠️ **O BLOCO 0 confere** se algum agente resolve skill em runtime hoje. Se resolver, o executor reescreve esta
decisão com o número.

### 6.2 A cadeia, do pedido à resposta

```
pergunta ("ele tem carro reserva?")
 ①  apólice VIGENTE do ramo deduzido            ← pela PORTA (001.1). A 001.5 não escolhe apólice
 ②  documento oficial da apólice                 ← já no caminho feliz da 001.1
 ③  produto + plano contratado
       a) linha "Assistência" / bloco 24h do PDF  (policy_document_evidence_service.py:230-318)
       b) `tabela_itens` do sistema de gestão     (o nome do plano; hoje só vira sinal, :4015)
       c) processo SUSEP do PDF                   (§7.2 — é ele que amarra na condição geral certa)
 ④  chave canônica: seguradora + ramo + produto + plano  → `insurer_assistance_plans`
 ⑤  a linha do serviço perguntado                → `insurer_assistance_services`
 ⑥  a prosa, quando a pergunta pede "por quê"    → RAG global, FILTRADO por
                                                    insurer_key + doc_kind + vigência na data da apólice
 ⑦  existe plano de nível > o contratado, mesmo produto, mesma vigência?  → o gancho (§6.4)
```

🔴 **③ é onde a resposta pode mentir com mais confiança.** Se o plano não for identificado, o estado é
**`nao_sabemos_ainda`** — nunca "o plano padrão da seguradora". Guarda **M-B4**.

### 6.3 Os cinco estados — e a distinção que o Founder pediu

| estado | quando | 💭 como sai na conversa | conta como |
|---|---|---|---|
| `coberto` | linha publicada diz `coberto='sim'` | *"Tem sim: carro reserva por 7 dias. (Condições gerais da HDI, p. 23.)"* | acerto |
| `nao_coberto` | linha publicada diz `coberto='nao'` | *"No plano dele, não. O Essencial da HDI não tem carro reserva. (Condições gerais, p. 23.)"* | acerto |
| `condicionado` | `coberto='condicionado'` + `condicao` | *"Tem, mas só em caso de sinistro coberto — não em pane. (Condições gerais, p. 24.)"* | acerto |
| `nao_contratado` | o serviço existe no produto, **e o plano contratado é um nível que não o inclui** | *"O plano dele é o Essencial, que não inclui. O Completo inclui 7 dias."* | acerto |
| 🔴 `nao_sabemos_ainda` | não há linha publicada para essa seguradora/ramo/produto/plano, **ou o plano não foi identificado** | *"Ainda não tenho as condições da <seguradora> para esse produto na base. Posso confirmar com a seguradora — quer que eu abra?"* | **acerto** |

🔴 **E o sexto, que não é um estado da base:** `fonte_indisponivel` — a apólice não carregou, o documento não abriu,
a busca falhou. 💭 *"Não consegui abrir a apólice dele agora."* **Isto é falha**, tem outro texto, e aparece na tela
em outra coluna (§9). **Confundir os dois é o defeito que esta SPEC existe para matar:** *"não sabemos ainda"* é
honestidade sobre a base; *"a fonte não retornou"* é um incidente.

⚠️ **Regra de texto, e o piso de §0.5 se aplica aqui:** nenhuma das frases acima afirma o que a base não tem. Toda
frase que diz "não" carrega **documento e página**. Uma frase que diz "não" **sem fonte** é proibida — porque
"não cobre" sem lastro custa um acionamento que o segurado tinha direito a fazer.

### 6.4 O gancho comercial — e a trava

```
gancho aparece  ⇔  existe linha em insurer_assistance_plans com
                   mesmo insurer_key + ramo + produto,  nivel > nivel_contratado,
                   curadoria='publicado',  vigente na data da apólice
                   E a linha do serviço perguntado nesse plano superior diz coberto='sim'
```

💭 *"O plano acima (Completo) teria carro reserva por 7 dias — a Regina pode orçar a troca na renovação."*

🔴 **Três coisas que o gancho NÃO faz:** não diz preço, não diz quanto custa a troca, não promete que a seguradora
aceita. **Cotação é outra SPEC** (§2.2). O gancho **passa o caso para a atendente**, nomeando-a pelo card Equipe —
nunca pelo nome do agente (D-PILOTO-12, e a 001.2 é quem garante isso).

Guarda **M-B3**: com o plano superior removido da tabela, o gancho **some**. Mutação: gancho aparecendo com
`nivel` máximo contratado.

### 6.5 O que acontece com `assistance_policy.py`

📊 Hoje: 142 linhas, `STANDARD_SERVICES = ("eletricista", "chaveiro", "hidraulica_encanador")` (`:28`), gatilho por
substring `"resid"` (`:54`), `RULE_ID="residential_24h_standard_v1"`, e um único importador
(`policy_answer_composer.py:24`). O próprio arquivo declara a intenção, em `:4-6`: *"migração para tabela
`platform_policies` com overrides por seguradora/produto/plano/corretora está prevista para quando o primeiro
override existir"*. **O primeiro override é esta SPEC.**

**Ele vira fallback, com marca, e não é apagado:**

1. A Skill consulta a base **primeiro**. Achou linha publicada → responde pela base, com fonte.
2. Não achou, e a apólice é residencial com assistência confirmada → a regra antiga responde, **marcada**:
   `origem='regra_generica'`, `confianca='baixa'`, e a frase diz que é o padrão de mercado, não o contrato dele.
   💭 *"Pelo padrão dessas apólices, eletricista, chaveiro e encanador costumam estar inclusos — mas ainda não
   tenho as condições da <seguradora> para confirmar o plano dele."*
3. 🔴 **`policy_rule_facts` perde o vínculo com a apólice hoje** — `assistance_policy.py:123` fixa
   `locator_hash = None`. Conserta-se junto, porque um fato sem apólice não pode ser auditado depois.

⚠️ **E o guarda de saída muda de regra, não morre.** 📊 `nodes.py:307-317` hoje anula qualquer resposta final que
não contenha "eletricista" **e** "chaveiro" **e** ("hidraulica"|"hidráulica"|"encanador"), sempre que
`assistance_policy_applied` está no contrato. **Com a base no ar, isso passa a ser errado**: a resposta certa para
uma apólice de auto não tem encanador. A regra nova:

```
o contrato traz `assistencia_da_base` com N serviços?  → a resposta não pode OMITIR nenhum deles
o contrato traz `assistance_policy_applied` (o fallback)? → a regra dos 3 serviços continua valendo
```

🔴 **Um executor que apagar o guarda "porque a base substituiu a regra" reabre o defeito que ele fechou.** Guarda
**M-B5**.

### 6.6 A procedência que volta — o conserto de §0.3 ④

Duas mudanças pequenas, no caminho que já existe, e nenhum buscador novo:

1. `qdrant_service.py:891-909` passa a copiar para o item devolvido os campos que **já estão no payload**:
   `insurer_key`, `doc_kind`, `susep_process`, `effective_from`, `vigente`, `unit_id`, `parent_id`, `faceta`.
   ⚠️ **Aditivo**: nenhum leitor de hoje perde chave.
2. `doc_kind` entra em `_INDICES_DE_PAYLOAD` (`qdrant_service.py:88-99`) e vira parâmetro de filtro de
   `search_similar` — no molde de `_filtro_de_seguradora:434` (o braço "desta OU sem", que é o certo: um documento
   sem `doc_kind` não some). 🔴 **O índice é criado ANTES de qualquer ingestão nova**, porque a documentação do
   Qdrant é explícita: *"For best results, create payload indexes before ingesting data"* (§16 ③).

**GATE B:**
1. **30 perguntas reais do acervo**, extraídas por categoria (carro reserva, granizo, chaveiro, vidros, guincho,
   residência) — 🔴 **só as perguntas, PII removida**, rodadas **pelo motor** (a tool, não um regex): cada uma
   devolve um dos cinco estados, e todo estado que não seja `nao_sabemos_ainda` traz **documento e página**.
2. **Linha de controle** (CLAUDE.md §9.2): uma pergunta que **não** é de assistência (💭 "quantas parcelas faltam?")
   **não** consulta a base e **não** cita condição geral.
3. Par de controle: a **mesma** pergunta em duas apólices de níveis diferentes do mesmo produto → **vereditos
   opostos**, e o gancho só na de nível inferior.
4. `doc_kind='condicoes_gerais'` filtra: a mesma busca com e sem o filtro devolve conjuntos diferentes, e **zero**
   `manual_do_segurado` quando o filtro está ligado.

**MUTAÇÃO B:** (a) `nao_sabemos_ainda` colapsando em `nao_coberto`; (b) origem removida da resposta;
(c) plano inferido pela seguradora quando o PDF não o nomeia; (d) gancho sem plano superior na tabela;
(e) guarda de `nodes.py` apagado. **As cinco vermelhas.**

---

## 7. BLOCO C — AS TRÊS ONDAS DE COLETA

### 7.1 Onda 1 — extrair das 97 já indexadas, com revisão humana antes de publicar

📊 O alvo real, medido por seguradora × ramo (§0.1): **auto 24 · residencial 24 · condomínio 8** são os ramos dos
pilotos; **vida 101** é a maior fatia do corpus e **não é a carteira que os pilotos vendem**. 🔴 **A onda 1 começa
pelos 56 documentos de auto/residencial/condomínio, não pelos 97.** O resto fica declarado, não esquecido.

🔴 **A extração lê a FONTE ARQUIVADA, não o pedaço indexado.** O motivo é §0.3 ④: o chunk não tem página. A fonte
original está no MinIO (`insurance_corpus._guardar_a_fonte:1608` → `acervo_arquivo.py`), e o extrator de texto por
página já existe (`insurance_corpus.extrair_texto_de_pdf:177`, PyMuPDF — escolhido porque 📊 devolvia 11.064 linhas
onde o PyPDF2 devolvia 519). **Página vem daí.**

O laço, e ele tem três papéis distintos:

```
1. o extrator (modelo)   lê a fonte arquivada, página a página, e PROPÕE linhas
                         → curadoria='proposto', confianca da proposta, trecho_hash, pagina
2. o verificador (máquina)  confere o que dá para conferir sem gente:
                         · a página existe no documento?          · o trecho_hash bate com a página?
                         · o serviço está no vocabulário?         · limite tem unidade?
                         · o nível é único dentro do produto?
                         falhou → volta para 'rascunho' com o motivo, nunca para 'proposto'
3. a pessoa              abre a fila (§8), vê o trecho ao lado da linha, e publica ou rejeita
                         → curadoria='publicado' + revisado_por + revisado_em  (o CHECK exige)
```

⚠️ **O verificador não é o revisor.** Ele só reprova; ele nunca aprova. Um verificador que promove a `publicado`
seria a curadoria automática que o CHECK de §5.3 existe para impedir.

💭 **Meta da onda 1:** as **6 seguradoras** cujo `insurer_key` já casa com o catálogo, nos 3 ramos dos pilotos,
com os níveis que a condição geral nomear. O número real sai da onda, não desta proposta.

### 7.2 Onda 2 — o elo apólice → condição geral pelo processo SUSEP

**Três passos, e o primeiro é remover um bloqueio:**

1. `susep` **sai** de `_BOILERPLATE_RE` (`policy_document_evidence_service.py:208`). ⚠️ Ele está lá por um motivo
   real — linhas institucionais de rodapé. A substituição é cirúrgica: o que se descarta é `ouvidoria|sac 24`, e o
   que passa a ser **capturado** é a linha que casa `_RE_SUSEP` (`insurance_corpus.py:49`). Guarda **M-C2** exige
   **ZERO** casamentos com o filtro de volta.
2. `extrair_susep` passa a rodar sobre o texto do PDF da apólice, e o processo entra no modelo canônico da 001.1
   como campo com origem `documento_oficial`.
3. `normative_documents` é consultado por `susep_process` — 📊 **190 de 194 têm o campo preenchido**. Casou →
   a condição geral **daquele contrato** é a fonte, e não "a condição geral atual da seguradora".

🔴 **E aqui está a armadilha que o próprio código já avisa** (`insurance_corpus.py`, docstring de abertura):

> *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não pela de hoje. Um cache que
> guarda 'a condição atual' e responde sobre uma apólice antiga pode estar confiantemente errado sobre cobertura —
> e o corretor repete isso para o cliente."*

Por isso `insurer_assistance_plans` tem `vigencia_inicio`/`vigencia_fim`, e a Skill busca **pela data de emissão da
apólice**, não por `now()`. 📊 A base já sustenta isso: `normative_document_versions` tem 206 linhas para 194
documentos, com `effective_from`/`effective_until` e `superseded_at` — **as versões antigas estão lá**. Guarda
**M-C3**.

### 7.3 Onda 3 — as seguradoras ausentes, pela carteira

**O critério de ordem é a carteira, medida, não o alfabeto.** 📊 A medição existe e está no catálogo:
`placar_das_siglas` foi construído sobre **a carteira viva de 2025 da corretora piloto, 3.861 linhas, soma de
`pretot` por sigla**, e cobre **83,86%** do prêmio com 14 siglas. As **12 siglas da carteira sem `coenti`** estão
listadas no arquivo (`MAP, AXA, MAG, JUNT, AIG, ESSO, ITAU, BERK, CHUB, FATO, JNS, MITS`) — e são elas, mais as
canônicas sem CG (`alfa, seguros_unimed, sompo, suhai, sulamerica, sura, zurich`), a fila da onda 3.

⚠️ **O BLOCO 0 remede a carteira pela porta** (D-PILOTO-11: o catálogo é nosso, mas o **peso** é da corretora), e a
fila sai do número de hoje. As seguradoras que o diagnóstico nomeia (Allianz, HDI, Porto, Yelum, Azul, Tokio,
Bradesco, Mapfre, Zurich) são **8 de 9 já presentes** — 📊 só a Zurich falta, e é a que mais aparece nas ausentes.

**`doc_kind='manual_de_assistencia'` é valor novo**, e isso tem consequência de migration: 📊 o CHECK de `doc_kind`
tem 9 valores e **`manual_de_assistencia` não está entre eles**. §11.2 trata.

⚠️ E há dívida herdada a registrar, não a consertar aqui: 📊 **3 dos 9 valores do CHECK não têm escritor**
(`condicoes_particulares`, `glossario`, `regulamento`), e o classificador (`insurance_corpus.py:976-983`) produz
apenas 6. Vira pendência com número.

### 7.4 Manutenção — já existe, e só precisa alcançar a linha

📊 `content_hash` com espaço normalizado (`insurance_corpus.py:58-62`) já impede que um PDF re-renderizado pareça
alteração; `:1433-1438` não reingere quando o hash bate; `next_check_at` está preenchido em **194 de 194**, com
intervalo de 21 a 45 dias.

**O que a 001.5 acrescenta:** quando o `content_hash` do documento **muda**, as linhas que apontam para ele caem de
`publicado` para **`proposto`**, com o motivo, e voltam para a fila. 🔴 **Elas não são apagadas e não continuam
publicadas em silêncio** — porque a resposta de ontem pode ter sido certa e a de hoje já não ser.

**GATE C:**
1. Onda 1 sobre **um** documento real de auto e **um** de residencial: as linhas propostas têm página que **existe**
   no documento, `trecho_hash` que **bate** com o texto daquela página, e **nenhuma** chega a `publicado` sem
   revisor.
2. Onda 2 sobre uma apólice real do acervo: o processo SUSEP é extraído do PDF, **casa** com uma linha de
   `normative_documents`, e a condição encontrada é a **vigente na emissão** — não a mais recente.
3. **Linha de controle da onda 2:** com `susep` de volta no boilerplate, o casamento cai para **ZERO**.
4. Onda 3: `doc_kind='manual_de_assistencia'` aceito pelo banco depois da migration de §11.2, e recusado antes.
5. Mudar o `content_hash` de um documento derruba as linhas dele para `proposto` — e **não** as apaga.

**MUTAÇÃO C:** (a) verificador promovendo a `publicado`; (b) página que não existe no documento aceita;
(c) busca pela condição **atual** em vez da vigente na emissão; (d) `content_hash` novo mantendo as linhas
publicadas. **As quatro vermelhas.**

---

## 8. BLOCO D — A TELA MÍNIMA (Conhecimento)

> Disjunta de A–C. Corre em paralelo. Arquivo: a tela de Conhecimento que já existe no painel da corretora.
> ⚠️ **Rota:** a SPEC **não move** `agentes/even → corretora/…` — isso é a 001.9 (diagnóstico §3).

Duas visões, e nada além delas nesta SPEC:

**① Cobertura da base** — seguradoras × ramos × planos × fonte.

```
seguradora   ramo         produto     planos   serviços   fonte                      atualizado
HDI          residencial  Residencial  2 níveis   14      Condições gerais · p.23-26  há 3 dias
Allianz      auto         —             —          —      🔴 nenhuma linha publicada   —
Zurich       —            —             —          —      ⚪ sem condições gerais       —
```

🔴 **A régua conta seguradora × ramo com plano publicado — não conta linhas.** É o erro que
`backend/tests/test_cobertura_nao_mente_para_cima.py` documenta para a cobertura de URA (📊 Allianz: painel 63%,
real 37%), e é o mesmo erro aqui: uma seguradora com 40 linhas de um ramo só não é "a base está boa". Guarda **M-D1**.

**② A fila de curadoria** — a linha proposta, o trecho, a página, e dois botões.

Cada item mostra: seguradora · ramo · produto · plano/nível · serviço · o que o extrator propôs · **o trecho e a
página ao lado**, para a pessoa não precisar abrir o PDF. Publicar exige a leitura; rejeitar exige motivo.

⚠️ **Não exibir nome de tabela, coluna, SQL ou `insurer_key` para quem cura.** A tela fala "seguradora",
"condições gerais", "página".

**GATE D:** a tela abre com a base vazia (estado vazio honesto: *"nenhum plano publicado ainda"*), com uma
seguradora publicada, e com um item na fila; publicar pela tela grava `revisado_por`/`revisado_em`; trocar de
corretora **não muda nada** (é base global) e a tela diz isso em uma linha.

---

## 9. BLOCO E — A MEDIÇÃO

> Disjunta. Corre em paralelo.

### 9.1 A régua, declarada antes de começar

```
denominador   as 61 siglas da carteira viva (docs/canon/providers/susep/seguradora-coenti.json)
              — remedido no BLOCO 0 pela porta, e é ele que manda

HOJE (📊 13/09/2026)
  seguradoras com condição geral indexada ....................  8 de 61  (6 quando a chave tem de casar)
  seguradoras com PLANO de assistência estruturado ...........  0 de 61
  serviços com limite, carência e fonte ......................  0

💭 META POR ONDA — faixa, nunca promessa
  onda 1  (extrair das 56 CGs de auto/resi/condomínio)  ......  6 de 61, nos 3 ramos dos pilotos
  onda 2  (o elo SUSEP)  .....................................  a condição CERTA da apólice, não a atual
  onda 3  (as ausentes de maior carteira)  ...................  a fila sai da carteira remedida
```

### 9.2 O número que não pode mentir

A cobertura é contada por **seguradora × ramo com pelo menos um plano publicado e um serviço com fonte** — nunca
por linhas, nunca por documentos. 🔴 E o relatório separa **três** contagens que é tentador juntar:

```
seguradoras com CG na base        ≠  seguradoras com PLANO publicado  ≠  seguradoras que a corretora USA
```

### 9.3 `origem` no turno

Toda resposta da Skill grava, no registro que **já existe** (`tool_invocations`, via
`nodes.py:784,1057` → `skills/gateway.py:294,323`): o **estado** (§6.3), a `insurer_key` canônica, o `plano_id`
quando houve, o `documento_id` e a `pagina`. 🔴 **Nenhum segundo registro** (CLAUDE.md §5), e 🔴 **nenhum argumento
cru** — um `tool_args` desse caminho carrega CPF; grava-se `{"documento": "presente"}`.

⚠️ Se o BLOCO 0 achar que `tool_invocations` já guarda argumento cru hoje, isso é **P1 de segurança** desta SPEC e
a drenagem vem antes da funcionalidade.

**GATE E:** a consulta de cobertura roda e devolve os três números separados; um turno real do canário aparece em
`tool_invocations` com estado, seguradora, documento e página; o varredor de PII não acha nada nele.

---

## 10. Os guardas novos — **12, o teto de D-PILOTO-14** (+ 1 canônico)

🔴 Todos sobre o **MOTOR** e o **ACERVO real** (CLAUDE.md §9.4/§9.5). **Proibido teste que reimplementa a regra:**
o teste chama a tool e o banco, nunca um regex sobre a mesma tabela que o código lê.

| # | guarda | o que afirma | mutação que o deixa VERMELHO |
|---|---|---|---|
| **M-A1** | `test_a_seguradora_tem_uma_chave_so` | `chave_canonica("tokio") == chave_canonica("tokio_marine")`; chave desconhecida → `UNKNOWN` **listado**; nenhuma linha da base com chave fora do catálogo | linha com `insurer_key` novo aceita sem decisão |
| **M-A2** | `test_a_linha_sem_fonte_nao_entra` | o **banco** recusa `documento_id` nulo, `pagina` nula, `pagina=0` e `trecho_hash` de tamanho errado | CHECK `servico_tem_fonte` removido |
| **M-A3** | `test_o_nivel_e_unico_no_produto` | dois planos com o mesmo `nivel` no mesmo produto/vigência são recusados; e `limite_valor` sem `limite_unidade` é recusado | `unique` de nível removido |
| **M-A4** ⚖️ | `test_a_base_de_planos_nao_tem_dono` — **canônico, não conta no teto** (CLAUDE.md §7) | nenhum `company_id` nas tabelas novas; varredor de PII = **0** nas colunas de texto; duas corretoras → mesma resposta | `ALTER TABLE … ADD COLUMN company_id` |
| **M-B1** | `test_nao_sabemos_ainda_nao_vira_nao` | sem linha publicada → estado `nao_sabemos_ainda` com a frase própria; **e o par:** com linha → `nao_coberto` **com fonte** | estado desconhecido colapsando em "não cobre" |
| **M-B2** | `test_a_resposta_traz_documento_e_pagina` | sobre as **30 perguntas reais do acervo** (só as perguntas, sem PII), pelo motor: todo estado ≠ `nao_sabemos_ainda` cita documento e página | origem removida do contrato de resposta |
| **M-B3** | `test_o_gancho_so_aparece_com_plano_superior` | **par de controle:** nível 1 com nível 2 na tabela → gancho; nível máximo → **sem** gancho | gancho com `nivel` máximo |
| **M-B4** | `test_o_plano_vem_da_apolice_nao_do_chute` | PDF sem nome de plano → `nao_sabemos_ainda`, nunca "o padrão da seguradora" | plano inferido só pela seguradora |
| **M-B5** | `test_o_guarda_dos_servicos_mudou_de_regra_nao_morreu` | com `assistencia_da_base`, a resposta não pode omitir serviço da base; com o fallback, a regra dos 3 serviços continua valendo | guarda de `nodes.py:307` apagado |
| **M-C1** | `test_extracao_nao_publica_sem_gente` | o verificador só reprova; nenhuma linha chega a `publicado` sem `revisado_por`+`revisado_em` | verificador promovendo a `publicado` |
| **M-C2** | `test_o_susep_da_apolice_encontra_a_condicao` | sobre um PDF real do acervo: o processo é extraído e casa com `normative_documents`. 🔴 **Linha de controle:** com `susep` de volta no boilerplate → **ZERO** | `susep` de volta em `_BOILERPLATE_RE` |
| **M-C3** | `test_a_condicao_e_a_da_emissao_nao_a_de_hoje` | apólice de emissão antiga → a versão **vigente na emissão**, com par de controle de duas versões do mesmo processo | busca por `now()` |
| **M-D1** | `test_a_cobertura_da_base_nao_mente_para_cima` | a régua conta seguradora × ramo com plano publicado; 40 linhas de um ramo só **não** inflam o número | contagem por linhas |

⚠️ **Não contam no teto** (e o executor não os usa para ampliá-lo): o VERIFY das migrations e o varredor de PII —
são **gates de bloco**, não guardas novos de produto. **Se o executor discordar, ele corta um da lista e escreve
qual.**

🔴 **A regra que fecha a porta (CLAUDE.md §9.3):** cada mutação roda em **cópia**, em subprocesso, produz **falha
nova nomeada**, e a árvore é restaurada por cópia. **Um guarda que não conseguiu ficar vermelho não é guarda.**

---

## 11. Migrations — APPLY / VERIFY / ROLLBACK escritos ANTES

🔴 **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro antes da primeira linha de SQL.** 📊 O repositório **não** é a
fonte completa do schema: 9 versões aplicadas sem arquivo e 16 arquivos sem versão. Diretório canônico:
`backend/supabase/migrations/`. Proibido sempre: `schema_completo.sql`, `upgrade_v6.2.sql`, `storage_buckets.sql`.

**São duas migrations, e a segunda é de outra natureza. Elas não se juntam.**

### 11.1 `20260913_01_extra0015_assistance_plans.sql` — ADITIVA

Cria as duas tabelas de §5.2 com os CHECKs de §5.3 e os índices de leitura. **Não toca objeto existente.**

```sql
-- APPLY (expand-first · idempotente)
CREATE TABLE IF NOT EXISTS insurer_assistance_plans ( … );      -- §5.2
CREATE TABLE IF NOT EXISTS insurer_assistance_services ( … );   -- §5.2, com os 3 CHECKs de §5.3
CREATE INDEX IF NOT EXISTS ix_iap_chave
    ON insurer_assistance_plans (insurer_key, ramo, produto, nivel);
CREATE INDEX IF NOT EXISTS ix_ias_servico
    ON insurer_assistance_services (plano_id, servico);
CREATE INDEX IF NOT EXISTS ix_ias_curadoria
    ON insurer_assistance_services (curadoria) WHERE curadoria <> 'publicado';
```

```sql
-- VERIFY (a saída vai COLADA no relatório)
SELECT table_name, count(*) FROM information_schema.columns
 WHERE table_schema='public'
   AND table_name IN ('insurer_assistance_plans','insurer_assistance_services')
 GROUP BY 1;                 -- esperado: as duas tabelas, com a contagem de colunas de §5.2

SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conrelid = 'insurer_assistance_services'::regclass AND contype='c';
 -- esperado: servico_tem_fonte · servico_publicado_foi_revisado · limite_tem_unidade

SELECT count(*) FROM information_schema.columns
 WHERE table_schema='public'
   AND table_name IN ('insurer_assistance_plans','insurer_assistance_services')
   AND column_name IN ('company_id','user_id','owner_user_id');
 -- 🔴 esperado: 0. Qualquer número maior reprova o gate (D-PILOTO-01, §3.3).

-- as três inserções adversariais TÊM de falhar; a mensagem de erro vai colada:
INSERT INTO insurer_assistance_services (…, documento_id, pagina, …) VALUES (…, NULL, 1, …);   -- recusa
INSERT INTO insurer_assistance_services (…, pagina, …)              VALUES (…, 0, …);          -- recusa
INSERT INTO insurer_assistance_services (…, curadoria, revisado_por) VALUES (…,'publicado',NULL); -- recusa
```

```sql
-- ROLLBACK
DROP TABLE IF EXISTS insurer_assistance_services;   -- filha primeiro
DROP TABLE IF EXISTS insurer_assistance_plans;
-- ⚠️ o rollback APAGA as linhas curadas. Antes de rodá-lo em qualquer ambiente com curadoria feita,
--    exportar `insurer_assistance_plans` + `insurer_assistance_services` para o acervo. Trabalho
--    humano perdido não volta com `git revert`.
```

### 11.2 🔴 `20260913_02_extra0015_doc_kind_manual.sql` — ALTERA UMA TRAVA DE TABELA VIVA

**Esta é a migration onde o piso CRÍTICO do protocolo §3.2 dispara**, e por dois motivos somados:

- ela **altera um CHECK** (uma trava) de uma tabela com **194 linhas em produção**;
- 📊 `normative_documents` é **classe SEM_ARQUIVO**: o DDL só existe em
  `docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`, marcado **PROIBIDO APLICAR**. O
  CHECK real **tem de ser lido do catálogo do Postgres**, não do arquivo.

**MANIFESTO obrigatório (MIGRATIONS-AUTHORITY §5), antes de rodar:** o `pg_get_constraintdef` atual colado, a lista
de valores hoje em uso (`SELECT doc_kind, count(*) FROM normative_documents GROUP BY 1`), e a declaração de que
nenhuma linha existente perde validade.

```sql
-- APPLY (expand-first: o CHECK novo é SUPERCONJUNTO do antigo)
ALTER TABLE normative_documents DROP CONSTRAINT IF EXISTS normative_documents_doc_kind_check;
ALTER TABLE normative_documents ADD  CONSTRAINT normative_documents_doc_kind_check
  CHECK (doc_kind = ANY (ARRAY[
    'condicoes_gerais','condicoes_especiais','condicoes_particulares','manual_do_segurado',
    'nota_tecnica','circular_susep','tabela_coberturas','glossario','regulamento',
    'manual_de_assistencia'                                   -- <- o único valor novo
  ]));
```

```sql
-- VERIFY
SELECT pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conname = 'normative_documents_doc_kind_check';         -- tem de conter manual_de_assistencia
SELECT doc_kind, count(*) FROM normative_documents GROUP BY 1 ORDER BY 2 DESC;
 -- 📊 esperado em 13/09: condicoes_gerais 184 · circular_susep 5 · manual_do_segurado 5
 -- ⚠️ se a contagem de hoje não bater, PARE: alguém mexeu, e o manifesto está desatualizado.
```

```sql
-- ROLLBACK (só é seguro se NENHUMA linha usar o valor novo)
SELECT count(*) FROM normative_documents WHERE doc_kind = 'manual_de_assistencia';
 -- 🔴 > 0 → NÃO rodar o rollback: ele deixaria a tabela violando o próprio CHECK.
 --         Primeiro reclassificar essas linhas, depois reverter.
ALTER TABLE normative_documents DROP CONSTRAINT IF EXISTS normative_documents_doc_kind_check;
ALTER TABLE normative_documents ADD  CONSTRAINT normative_documents_doc_kind_check
  CHECK (doc_kind = ANY (ARRAY[ … os 9 valores lidos do catálogo no manifesto … ]));
```

### 11.3 GATE G-MIG

1. APPLY, VERIFY e ROLLBACK **escritos antes** de rodar qualquer um (CLAUDE.md §8).
2. APPLY rodado **duas vezes** → mesmo resultado.
3. ROLLBACK exercitado em ambiente de teste, **incluindo** a guarda de contagem de §11.2.
4. As **três inserções adversariais** de §11.1 falharam, com a mensagem colada.
5. `MANIFEST.md` de `backend/supabase/migrations/` atualizado, e `normative_documents` registrada como
   **NÃO RASTREADA** com o DDL real lido do catálogo.
6. **Nenhuma outra migration nesta SPEC.** Se aparecer, **pare e registre** — o escopo escorregou.

---

## 12. Canário controlado em produção

### 12.1 Antes

- Confirmar o SHA implantado de cada serviço (não o `/health`: CLAUDE.md §9.1 — health não prova versão).
- Confirmar que as exceções de janela (`05f46a9`) contêm **só** TESTE-A/TESTE-B.
- Confirmar que há **pelo menos uma** seguradora com plano publicado e revisado. **Canário com base vazia prova
  só o `nao_sabemos_ainda`** — o que é metade da prova, e a metade fácil.

### 12.2 Os casos

| # | caso | onde | o que prova |
|---|---|---|---|
| 1 | "o segurado X tem carro reserva?" numa apólice **com** plano publicado | chat `core` da Resulta, conta do Founder | estado certo **com documento e página** |
| 2 | a mesma pergunta numa seguradora **sem** plano na base | idem | `nao_sabemos_ainda`, com a frase própria — e **não** "não cobre" |
| 3 | "qual o limite do guincho dele?" | idem | limite **com unidade** e fonte |
| 4 | apólice de nível 1 num produto que tem nível 2 | idem | o **gancho** aparece, nomeando a atendente, **sem preço** |
| 5 | apólice no nível máximo | idem | o gancho **não** aparece (par de controle do caso 4) |
| 6 | "cobre granizo?" no WhatsApp | **TESTE-A** | linguagem de conversa, mesma verdade, origem dita em português |
| 7 | 🔴 pergunta que **não** é de assistência (💭 "quantas parcelas faltam?") | chat `core` | **linha de controle**: a base não é consultada |
| 8 | derrubar a busca de propósito, em ambiente controlado | — | sai `fonte_indisponivel`, com texto **diferente** do caso 2 |

🔴 **Os casos 5, 7 e 8 são os que dão direito à conclusão** (CLAUDE.md §9.2). Sem eles, "funcionou" pode ser um
`return "nao_sabemos_ainda"` no topo da função.

### 12.3 Depois

Desligar apenas a habilitação temporária; conferir que não ficou agente amplamente ligado; preservar logs **sem
PII**; entregar evidências **por alias**. Nenhuma evidência com número, CPF ou nome.

### 12.4 📋 O que só o Founder faz

1. Colar as perguntas dos casos 1–5, 7 no chat do painel da Resulta (ou autorizar a conta que o faça).
2. Mandar a mensagem do caso 6 do aparelho **TESTE-A**.
3. **Revisar e publicar as primeiras linhas da fila de curadoria** — ou indicar quem revisa. 🔴 **Isto bloqueia o
   canário completo**, e é a única dependência humana desta SPEC. 💭 Uma seguradora, um ramo, ~10 linhas já
   destravam os casos 1, 3, 4 e 5.
4. Se o EasyPanel exigir clique: implantar `smith-api` e `smith-web` (a tela de §8 muda o front).

---

## 13. Validação com Saionara e Regina

O executor **prepara o roteiro e as telas**; o Founder conduz. O executor **não as contata** nem usa os números
operacionais delas.

O que se valida, em linguagem delas: a resposta diz de onde veio, de um jeito que dá para conferir? *"ainda não
sabemos"* soa honesto ou soa como falha? o gancho de renovação soa útil ou soa como empurrar venda? a fila de
curadoria é revisável por quem não é técnico — dá para decidir olhando o trecho, sem abrir o PDF?

📊 A Saionara é a dona do caso de referência (a HDI residencial cujo cadastro escondia **R$ 125,94 de Assistências
Essenciais, 41% do prêmio**). O roteiro pede a ela exatamente as perguntas que ela fez nos pilotos — **as
perguntas, nunca os dados**.

Registrar: **"não testado" × "aprovado no canário técnico" × "validado pela atendente"**. Não declarar aceite antes
de recebê-lo; não travar o trabalho técnico esperando a agenda delas.

---

## 14. Entrega, implantação e rollback

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR. (CLAUDE.md §2)
git rev-list --count origin/main..HEAD          # 0 = o trabalho está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` e o SHA remoto vão **colados** no relatório. Nunca `git add -A`, nunca force push, nunca
apagar `index.lock` por timeout.

**Serviços a implantar:** `smith-api` (tabelas, Skill, corpus, busca) e **`smith-web`** (a tela de §8).
**Variáveis de ambiente novas:** 💭 nenhuma prevista — se o executor precisar de uma, ela entra com **nome e sem
valor** no relatório e na caixa do Founder. ⚠️ Mexeu em `app/`: `npm run test:rotas-montam` **e** `next start` +
uma requisição real a `/api/…` (CLAUDE.md §9.1).

| marco | evidência exigida |
|---|---|
| Implementado e gateado | commit, gates, mutações vermelhas, parecer da lente e do juiz fresco |
| Entregue na main | SHA remoto + saída do `push` |
| Implantado | serviço/imagem/SHA + `/health` + **uma requisição que executa código** |
| Validado no canário | os 8 casos, por alias, sem efeito fora do escopo |
| Validado pelas pilotos | feedback real, registrado pelo Founder |

**Rollback:** o código é reversível (a Skill é aditiva; `assistance_policy.py` continua inteiro e volta a ser o
caminho único). As migrations têm ROLLBACK próprio (§11), com as duas ressalvas escritas lá: **exportar a curadoria
antes** e **não reverter o CHECK com linha usando o valor novo**.

---

## 15. Documentação e acompanhamento obrigatórios — um escritor por arquivo

1. `docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md` pelo template canônico, **abrindo com o EXECUTION
   CARD** (protocolo §0.1: relatório sem card = SPEC aberta) e com a telemetria de 5 linhas.
2. `docs/canon/PENDENCIAS.md`, **por número, com veredito e prova** (protocolo §2):

   | pendência | veredito proposto | por quê |
   |---|---|---|
   | **P-PILOTO-04** | 🔴 **PARCIAL** — a parte de **conhecimento** fecha aqui | o checklist por tipo passa a sair da base; **o escritor de `ficha.faltando`, as entradas em `_TITULOS` e o dossiê de sinistro ficam na 001.3**. Fechar inteira seria fechar o que não se fez |
   | **P-PILOTO-20** | **CONTINUA ou FECHADA pela 001.1** | o BLOCO 0 confere; com eles mudos esta SPEC não fecha |

   **Entradas novas obrigatórias**, cada uma com **o que destrava · de quem é · o que custa esquecer**
   (CLAUDE.md §11.1): (a) o corpus normativo **não carrega página** no pedaço indexado; (b) `insurer_key`
   inconsistente em 14 tabelas, sem constraint; (c) 3 valores de `doc_kind` sem escritor; (d) `documents` do repo
   diverge do banco vivo (colunas `scope`/`curation_status` sem migration); (e) `normative_documents` e
   `normative_document_versions` são **classe SEM_ARQUIVO**.
3. `docs/canon/FOUNDER-DECISIONS.md`: registrar, datadas — a divergência de marcha de §0.5; a decisão "duas tabelas,
   não uma" (§5.2); a decisão "tool, não skill release" (§6.1).
4. `docs/canon/CHANGE-ADDENDA.md`: tudo além do texto desta SPEC, classificado.
5. `docs/canon/ESTADO-DAS-SPECS.md` e `INDICE-DE-SPECS.md`: a família EXTRA-001.x na fila; **não renumerar**.
6. Dossiê: fonte versionada `docs/canon/reports/dossies/dossies-autobrokers.html`, página **`p-extra0015`** na
   convenção existente (`p-home · p-extra001 · p-pilotos · …`), com item de navegação e linha na home. 🔴 **Ler o
   HTML publicado inteiro antes de republicar com `url`**
   (https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868). Sem ferramenta ou acesso: manter a fonte
   atualizada e declarar **"publicação pendente"** com o arquivo e o passo exato. **Nunca fingir que atualizou.**

---

## 16. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> Três referências, todas **fontes primárias**, reabertas em **13/09/2026** pelo redator. O pesquisador do executor
> reabre cada uma na conversão e **registra a data** (protocolo §7.3).

### ① PROV-O: The PROV Ontology — W3C Recommendation, 30/04/2013
**URL:** https://www.w3.org/TR/prov-o/ · reaberta 13/09/2026
**O que faz:** modelo de proveniência com três classes de partida — **Entity**, **Activity**, **Agent** — e as
relações `wasDerivedFrom`, `wasAttributedTo` (*"the ascribing of an entity to an agent"*) e `wasQuotedFrom`
(*"the repeat of (some or all of) an entity ... by someone who may or may not be its original author"*).
**O que MODELAMOS (um ponto):** **`wasQuotedFrom` + `wasAttributedTo` na mesma linha.** A linha de serviço carrega
de **onde** foi citada (`documento_id` + `pagina` + `trecho_hash`) **e por quem** foi afirmada
(`revisado_por` + `revisado_em`). 🔴 As duas juntas são o que distingue *"a base diz"* de *"alguém revisou e
publicou"* — e é por isso que o CHECK `servico_publicado_foi_revisado` existe.
**O que REJEITAMOS:** RDF, OWL, a ontologia inteira, um grafo de proveniência. Modela-se **a ideia**, em quatro
colunas de uma tabela relacional. Rejeitamos também guardar proveniência em **log**: proveniência é **do dado**.
**Como o juiz inspeciona:** pega 3 linhas ao acaso da base publicada e pergunta, para cada uma: de que documento e
página veio, quem publicou, e em que data. Uma sem resposta reprova a amostra (protocolo §0.4).

### ② Citations — documentação oficial da API da Anthropic
**URL:** https://platform.claude.com/docs/en/docs/build-with-claude/citations · reaberta 13/09/2026
(301 → `platform.claude.com`)
**O que faz:** *"Ground Claude's responses in your source documents. Citations return the exact passages that
support each claim."* O resultado vem em três formatos de localização, conforme o tipo de documento:
**`page_location`** com `start_page_number` (*"1-indexed"*) para PDF, **`char_location`** para texto e
**`content_block_location`** para conteúdo customizado — e cada bloco traz `cited_text`.
**O que MODELAMOS (um ponto):** a frase que vira teste — *"citations are guaranteed to contain valid pointers to
the provided documents"*. **Um ponteiro válido, não uma citação plausível.** É exatamente o guarda **M-A3**: a
`pagina` tem de **existir** no documento e o `trecho_hash` tem de **bater** com o texto daquela página. O formato
`page_location`/`start_page_number` é o que nos convence a guardar **página**, e não offset de caractere — porque
página é o que a pessoa que revisa consegue conferir.
**O que REJEITAMOS:** trocar o extrator por uma chamada de API com `citations: true` e publicar o que voltar.
🔴 A garantia é de **ponteiro válido**, não de **afirmação correta** — a página existe, o trecho é literal, e a
leitura de que aquilo significa "carro reserva por 7 dias no plano Completo" continua sendo um julgamento.
Por isso §7.1 tem três papéis e a pessoa é o terceiro. Rejeitamos também tornar o produto dependente do parâmetro:
a base tem de ficar certa também para quem lê por outro caminho.
**Como o juiz inspeciona:** abre a seção de formatos de citação, confere `start_page_number` e `cited_text`, e roda
**M-A3** contra a base — pedindo uma linha cuja página **não** exista no documento.

### ③ Enabling Large Language Models to Generate Text with Citations — Gao, Yen, Yu, Chen · EMNLP 2023
**URL:** https://arxiv.org/abs/2305.14627 · reaberta 13/09/2026
**O que faz:** propõe o ALCE, primeiro benchmark de geração com citação, com *"automatic metrics along three
dimensions — fluency, correctness, and citation quality"*. 📊 A medição que importa aqui: *"on the ELI5 dataset,
even the best models lack complete citation support 50% of the time"*.
**O que MODELAMOS (um ponto):** **qualidade de citação é uma dimensão separada de correção, e precisa ser medida
em separado.** Uma resposta pode estar certa e mal citada, ou bem citada e errada. §9 mede as duas: o estado
(certo/errado) e a origem (documento + página) são **contagens diferentes** no relatório, e **M-B2** exige as duas
nas 30 perguntas reais.
**O que REJEITAMOS:** deixar o modelo citar sozinho a partir do contexto recuperado, que é precisamente o cenário
em que o paper mede metade de falha. 🔴 Nesta SPEC **a citação não é gerada: ela é lida da tabela**, onde foi posta
por um extrator, conferida por máquina e publicada por gente. O modelo redige a frase; **a fonte não passa pela
redação dele.** Rejeitamos também usar as métricas do ALCE como gate — o gate é o acervo real, não um benchmark.
**Como o juiz inspeciona:** abre o abstract, confere as três dimensões e o número do ELI5, e pergunta ao executor
qual das duas contagens de §9 corresponde a cada dimensão.

⛔ **Referência externa nunca vira autoridade** (protocolo §7.3): Smith, Work OS, Tool Gateway, Skill Registry e
Artifact Hub continuam únicos. Modela-se o **padrão**.

---

## 17. O que sai desta SPEC e quando volta

| frente | por que sai | gatilho de retorno |
|---|---|---|
| **cotação e renovação do plano superior** | exige capacidade de precificação que não existe; o gancho **passa para gente** | EXTRA-003 (renovação) · EXTRA-004 (cotação) |
| a porta `PolicyDataProvider` e o modelo canônico de apólice | é a 001.1; dois escritores no mesmo arquivo | EXTRA-001.1, que roda antes |
| escritor de `ficha.faltando`, `_TITULOS`, dossiê de sinistro (resto de P-PILOTO-04) | é a 001.3 (o dossiê ao grupo) | EXTRA-001.3 |
| chunker do corpus carregar **página** | §7.1 resolve pela fonte arquivada; reescrever tocaria 42.091 pedaços | pendência com número; SPEC de RAG |
| normalizar `insurer_key` nas 14 tabelas | migração de dado em superfície não medida | pendência com número |
| adaptadores Quiver / Agger / Segfy | sem credencial; a base já nasce servindo qualquer um | EXTRA-002 / 008 / 009 |
| `condicoes_particulares`, `glossario`, `regulamento` sem escritor | dívida herdada, não desta superfície | pendência com número |

---

## 18. A fila depois desta entrega — contexto, não autorização

Ordem canônica (diagnóstico §12.1, D-PILOTO-08):

```
001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 ∥ 001.4 → 001.6 → 001.7 → 001.10 ∥ ★ 001.5 (esta) → 001.8 → 001.9
```

**O que a 001.5 deixa pronto para quem vem depois:**

- para a **001.3**: o dossiê ao grupo passa a dizer *o que o plano dele cobre*, com fonte — hoje ele não sabe.
- para a **001.4**: o corredor sabe, antes de discar, se o serviço pedido está no plano — e para de acionar o que
  não é coberto.
- para a **EXTRA-003/004**: o catálogo de planos por nível é metade de uma cotação de renovação.
- para a **SPEC-101**: a base pendura na chave nossa, então vale para qualquer adaptador que a fábrica admitir.

---

## 19. Definição final de conclusão — lista fechada, verificável

A SPEC está concluída quando **todas** as linhas abaixo forem verdadeiras, cada uma com evidência no relatório:

1. A **chave canônica** existe num módulo único, `tokio` e `tokio_marine` resolvem para a mesma, e o que não casa
   sai **`UNKNOWN` listado** — nunca omitido, nunca zero.
2. `insurer_assistance_plans` (com **`nivel`**) e `insurer_assistance_services` existem, com os **três CHECKs**, e
   as **três inserções adversariais** falharam com a mensagem colada.
3. 📊 **Zero** colunas `company_id`/`user_id` nas tabelas novas; varredor de PII = **0**; duas corretoras recebem a
   **mesma** resposta.
4. A Skill `cobertura_e_assistencia` existe, responde nos **cinco estados**, e **`nao_sabemos_ainda` nunca vira
   "não cobre"**.
5. `fonte_indisponivel` tem texto próprio, diferente de `nao_sabemos_ainda`, e aparece em outra coluna da tela.
6. **30 perguntas reais do acervo** (só as perguntas, sem PII) rodadas **pelo motor** → todo estado ≠
   `nao_sabemos_ainda` cita **documento e página**.
7. As **linhas de controle** existem e funcionam: pergunta não-assistência não consulta a base; nível máximo não
   mostra gancho; `susep` de volta no boilerplate → **ZERO** casamentos.
8. `assistance_policy.py` continua existindo, **como fallback marcado**, e o guarda de `nodes.py:307` **mudou de
   regra sem morrer**.
9. Onda 1 produziu linhas publicadas para ≥ 1 seguradora em ≥ 1 ramo dos pilotos, **todas revisadas por gente**.
10. Onda 2: o processo SUSEP sai do PDF da apólice e casa com a condição **vigente na emissão**.
11. Onda 3: `manual_de_assistencia` aceito depois da migration e **recusado antes**.
12. `doc_kind` **filtra** de verdade, com índice de payload criado **antes** da ingestão nova; e a procedência
    (`insurer_key`, `doc_kind`, `susep_process`, `effective_from`) **volta como campo** da busca.
13. A tela mostra cobertura por **seguradora × ramo** (não por linhas) e a fila de curadoria com trecho e página.
14. As **duas migrations** aplicadas, VERIFY colado, ROLLBACK exercitado, **manifesto** de §11.2 escrito, e
    `MANIFEST.md` atualizado com `normative_documents` registrada como **NÃO RASTREADA**.
15. Os **12 guardas** existem e cada um ficou **vermelho** na sua mutação, em cópia, em subprocesso, com falha nova
    nomeada; o canônico **M-A4** também.
16. Canário: os **8 casos** rodados, só com TESTE-A/TESTE-B e a conta do Founder, evidências por alias.
17. `git push` feito, saída colada, SHA remoto conferido, serviços implantados e **uma requisição que executa
    código** respondida.
18. Relatório com **EXECUTION CARD**, a **divergência de marcha de §0.5 resolvida por escrito**,
    FATO/INFERÊNCIA/RECOMENDAÇÃO separados, 📊/💭 em todo número, pendências drenadas **por número**, dossiê
    publicado ou **publicação pendente** declarada com o passo exato.
19. **Declaração explícita de que nenhum motor paralelo foi criado** — nominalmente: nenhum segundo pipeline de
    ingestão, nenhuma segunda coleção de Qdrant, nenhuma segunda fila de curadoria, nenhum segundo catálogo de
    seguradoras, nenhum segundo registro de chamada de ferramenta.

🔴 **E a pergunta que o resumo ao Founder responde em linguagem simples:** *quando eu perguntar se o meu cliente
tem carro reserva, eu recebo sim ou não — e consigo ver em que página de qual documento isso está escrito?*
