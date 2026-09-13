# SPEC-EXTRA-001.1 — A APÓLICE CERTA, INTEIRA, EM UMA RODADA
## A porta `PolicyDataProvider` deixa de ser um cano e vira a fronteira: vigência, ramo, cobertura completa e origem escrita por linha

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medida nesta redação:** `a0bb5fe` (worktree `AutoBrokers-FIX`, 📊 `git rev-parse HEAD` em 13/09/2026; 0 atrás e 0 à frente de `origin/main`).
**Branch sugerida:** `feat/spec-extra-001-1-apolice-certa`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md`.
**Research Pack:** `SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada-RESEARCH-PACK.md`.
**Prompt de abertura:** `PROMPT-DE-ABERTURA-EXTRA-001.1.md`.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.1-EXECUTION-REPORT.md`.
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.1, §1.2, §3 (bloco 001.1), **§7.3** (a porta, D-PILOTO-11) e §12.1 (ordem).
**Protocolo:** AAA v11.2 + OPÇÃO B. Marcha **CRÍTICO**, **3 juízes** (diagnóstico §8: "muda o que o corretor lê sobre dinheiro do cliente").

---

## 0. Resultado e motivo

> O corretor pergunta pela apólice de um cliente — pelo CPF, pelo nome ou pelo número. **Na primeira rodada** ele
> recebe a apólice **vigente do ramo que a pergunta implica**, com **todas** as coberturas, limites, franquias,
> prêmio, parcelas e plano de assistência, e com a **origem escrita ao lado de cada linha**: o que veio do sistema
> de gestão da corretora e o que veio do PDF oficial da apólice. O segurado, no WhatsApp, recebe a mesma verdade
> em linguagem de conversa. Apólice vencida só aparece quando alguém pede histórico. Quando não há nenhuma vigente,
> a resposta diz qual foi a última e até quando valeu. **Perguntar qual apólice é a exceção, não a regra** — e só
> acontece quando sobram duas ou mais vigentes do mesmo ramo.

### 0.1 Por que esta SPEC existe — os números que a motivaram

📊 Medições do diagnóstico de 12/09 (fonte: laudos I1/I2 sobre `messages` e `observed_events` de 09–11/09; cada
número tem consulta no RESEARCH-PACK §2):

| o que se mediu | resultado |
|---|---|
| consultas por CPF no chat do painel que listaram apólices **vencidas** | **7 de 7** (31 linhas de opção) |
| consultas que **perguntaram** antes de responder | 5 de 7 |
| consultas resolvidas **em 1 rodada** | 2 de 7 |
| coberturas entregues na HDI residencial da Saionara (o cadastro tem 6; o PDF tem 10) | **6 de 10** — faltando **Assistências Essenciais, R$ 125,94 = 41% do prêmio** |
| declarações de "não consigo / a fonte não retornou" | 11 (10 antes do conserto de 10/09, 1 depois) |
| turnos que responderam *"ainda não recebi uma pergunta sua"* | 2 — os **dois maiores** do acervo (120 e 128 chunks de RAG) |
| nota do chat principal, dimensão "apólice certa" | **35/100**; "uma rodada" **25/100** |

E o efeito no atendimento: o agente chamou de **"ativa"** uma Allianz **vencida há 27 dias** e pediu ao cliente que
escolhesse. **O cliente corrigiu o robô.**

### 0.2 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | Decisão que governa esta execução | Onde |
|---|---|---|
| **D-PILOTO-08** | Numeração **EXTRA-001.1** dentro da família; nada renumera | `FOUNDER-DECISIONS.md:1752` |
| **D-PILOTO-11** | Fonte de verdade: **PDF** para cobertura/franquia/cláusula/plano; **sistema de gestão** para parcela/quitação/status/vigência. **A arquitetura não nasce presa à InfoCap**: porta `PolicyDataProvider`, InfoCap = primeiro adaptador, Quiver/Agger/Segfy = adaptadores. Seguradoras e ramos são **catálogo nosso** (chave SUSEP), nunca a lista do sistema de gestão. Corretora só com PDFs também é atendida | `FOUNDER-DECISIONS.md:1755` |
| **D-PILOTO-14** | Alta qualidade sem ser exorbitante: AAA opção B, **≤ 12 guardas novos**, bateria sobre o **motor** e o **acervo real** | `FOUNDER-DECISIONS.md:1758` |
| **D-PILOTO-16** | **SPEC-101 vira a porta**; EXTRA-002 Agger, EXTRA-008 Quiver e EXTRA-009 Segfy viram **adaptadores dela** e mantêm seus números | `FOUNDER-DECISIONS.md:1760` |
| **D-PILOTO-20** | Esta proposta nasce no chat do Fable com laço leve; **a execução é em chat novo, sob AAA opção B** | `FOUNDER-DECISIONS.md:1763` |

⚠️ **D-PILOTO-16 tem consequência direta no escopo desta SPEC:** a 001.1 **não constrói a SPEC-101**. Ela entrega a
porta no lugar certo, com o contrato completo e **dois** adaptadores (InfoCap e PdfOnly), e deixa escrito o que a
101 herda. Quem confundir as duas escreve uma fábrica de conectores dentro de uma SPEC de apólice.

### 0.3 🔴 A correção mais importante desta proposta: **a porta já existe**

O diagnóstico §7.3 pede criar `backend/app/services/policy_provider/`. **Isso seria motor paralelo (CLAUDE.md §5).**

📊 Medido em 13/09/2026 (`find backend -iname "*policy_data_provider*"` e
`grep -rn "PolicyDataProvider" --include=*.py .`):

```
backend/app/providers/policy_data_provider.py      149 linhas · SPEC-016 E5
  :41   class PolicyDataProvider(Protocol)       ← a porta existe
  :55   class InfocapPolicyDataProvider          ← o adaptador existe
  :137  register_policy_data_provider(provider)  ← o registry existe
  :144  get_policy_data_provider(provider_key)
  :149  register_policy_data_provider(InfocapPolicyDataProvider())

📊 e o CENSO REAL de quem já fala com ela — comando:
   grep -rn "get_policy_data_provider\|provider\.lookup\|provider\.detail\|provider\.vehicle" backend/app --include=*.py

  CINCO módulos consumidores, OITO pontos de chamada:
  app/agents/tools/infocap_tool.py          :159 resolve · :169 detail · :183 lookup · :217 lookup · :265 vehicle
  app/agents/tools/insurer_dispatch_tool.py :970 resolve · :974 vehicle
  app/agents/tools/portal_tool.py           :346 resolve · :350 vehicle
  app/agents/tools/vehicle_tool.py          :57  resolve · :64  vehicle
  app/services/billing_collection.py        :793 resolve · :797 lookup      🔴 FORA de app/agents/
```

⚠️ **Duas correções à versão anterior desta proposta, medidas em 13/09:**
1. `brokerage_analytics_provider.py:193-196` **não é chamada — é COMENTÁRIO** (*"o MESMO padrão de
   `policy_data_provider.py:134-149`"*). Citá-lo como consumidor era erro de leitura de `grep`.
2. Faltava `app/services/billing_collection.py:790-797` — **o caminho da cobrança**, que resolve o telefone do
   inadimplente pela porta. 🔴 Ele mora em `app/services/`, um diretório que a fronteira de §3.2 **não previa**,
   e é território da **EXTRA-001.6**, que corre em paralelo. **Mexer no `lookup()` sem avisar a 001.6 quebra a
   cobrança.** A ordem de migração de §5.1.1 existe por causa dele.

**FATO:** a fronteira existe. **INFERÊNCIA:** ela é hoje um **cano**, não uma porta — `lookup()` e `detail()`
devolvem `Dict[str, Any]` com a **forma da InfoCap** dentro, e por isso o resto do sistema continua sabendo o que é
`preliq`, `sit_renovacao_txt` e `tabela_itens`. Um `Protocol` cujo valor de retorno é o dicionário do fornecedor
**não isola nada** — é o problema que o padrão Anti-Corruption Layer descreve com todas as letras (§16, referência ②).

**RECOMENDAÇÃO — e é o Bloco A desta SPEC:** a 001.1 **evolui a porta que existe**, no arquivo que existe. Ela
ganha o modelo canônico de saída, as operações que faltam e a reconciliação. **Nada em
`backend/app/services/policy_provider/` é criado.** Se o executor criar esse diretório, o guarda **M-A** fica
vermelho por construção.

📊 **E o modelo canônico também está meio pronto:** `backend/app/services/policy_facts.py` (305 linhas, SPEC-016 E2)
já produz fatos tipados **com fonte e confiança**:

```python
# policy_facts.py:23
FACT_SOURCES = ("infocap_structured", "official_document", "policy_rule")
# :24-34
FACT_TYPES  = ("coverage","assistance","deductible","limit","installment",
               "exclusion","premium","validity","clause")
# :84   confidence: str = "medium"   (high|medium|low, validado em :165-167)
```

🔴 **E aqui está o vazamento que prova a tese:** o valor canônico de origem chama-se **`infocap_structured`**. O
nome do fornecedor está **dentro do modelo do domínio**. Numa corretora que use Quiver, o fato de uma cobertura
continuará dizendo que veio da InfoCap. Consertar isso é uma renomeação com backfill de leitores — pequena, e é
exatamente o tipo de defeito que, não corrigido agora, "reinfecta todo leitor seguinte" (CLAUDE.md §12.1).

📊 **E o catálogo nosso de seguradoras já existe** (SPEC-094.1 BLOCO B), versionado e revisado por gente:

```
docs/canon/providers/susep/seguradora-coenti.json   27.871 bytes · chaves: seguradoras, siglas,
                                                     criterio_de_casamento, placar_das_siglas
docs/canon/providers/susep/ramo-cogrupo.json        16.400 bytes
backend/app/providers/susep_ses_provider.py         551 linhas · lê o agregado, nunca a fonte
```

📊 A seção `siglas` foi construída **a partir das 61 entradas do censo `/seguradoras` da corretora piloto**, e a
cobertura de prêmio da carteira viva subiu de 12,35% para **83,86%**. **A 001.1 pendura nessa chave. Não cria a
segunda.** E o que não casa sai `UNKNOWN` **com o nome listado no arquivo** — nunca omitido, nunca zero.

### 0.4 EXECUTION CARD proposto — a medir no BLOCO 0, não a copiar

```text
OUTCOME .............. pergunta sobre apólice/cobertura (chat core e atendimento) → resposta na PRIMEIRA
                       rodada, da apólice VIGENTE do ramo deduzido, completa, com origem escrita por linha
RISCO ................ 7  =  ALCANCE 3 (o SEGURADO lê a resposta no WhatsApp)
                            + REVERSIBILIDADE 2 (dado/estado: facts, cache documental, llm_max_tokens no banco)
                            + FREQUÊNCIA 2 (TODO atendimento e toda pergunta de apólice do corretor)
                       ⚠️ recontar no BLOCO 0. Se o executor concluir que a resposta ao segurado "sai do prédio"
                          (REVERSIBILIDADE 3), o risco vai a 8 — e o nível não muda, já é CRÍTICO
SUPERFÍCIE ........... 2  (vários comportamentos + uma peça que muda de natureza: a porta)
                       ⚠️ vira 3 se o BLOCO 0 achar chamador do conector fora da lista medida em §3.2
PISO APLICADO ........ §3.2 — migration que ALTERA DADO (`agents.llm_max_tokens`, 8 linhas) e texto que chega
                       ao segurado. CRÍTICO independentemente da conta
NÍVEL ................ CRÍTICO — opção B
UNIDADES ............. 5  ·  A porta+modelo  ·  B vigência/ramo  ·  C briefing/guarda  ·  D PDF+reconciliação
                          ·  E contexto/tokens/rastro
COESÃO ............... A é arquivo-hub (policy_data_provider.py + policy_facts.py): UM dono, primeiro, sozinho.
                       B, C e D consomem o contrato de A → integração SERIAL. E é disjunta (graph.py, chat.py,
                       llm_factory.py, migration) e pode correr em paralelo a B/C/D
PARALELISMO REAL ..... E ∥ (A → B → C → D). Nenhum outro
TIME ................. investigador+pesquisador · desenhista da prova ANTES do código · builder por unidade ·
                       verificador mecânico · painel de 3 lentes (verdade+regressão · produto+DADO · red team) ·
                       integrador · UM juiz fresco que confirma o conserto E audita o dado (§6.1)
REFERÊNCIA ........... INTERNA: SPEC-094 BLOCO B (`brokerage_analytics_provider.py` + `infocap_analytics_provider.py`)
                       — a porta que JÁ PASSOU no gate deste repositório. O juiz abre os dois arquivos e compara.
                       + `backend/tests/test_a_apolice_responde_item_por_item.py` (326 linhas, 31 asserções)
                       EXTERNA: as 5 de §16, reabertas em 13/09/2026
GATES ................ GA, GB, GC, GD, GE, G-MIG, G-CANÁRIO da §11 + os canônicos
O ELO ................ "a resposta vem errada PORQUE a porta é um cano": medir A (respostas erradas, 7 de 7),
                       medir B (a porta devolve o dict cru do fornecedor) e 🔴 medir que B CHEGA em A —
                       rodar o MOTOR sobre o acervo e mostrar a linha de `policy_status` cru virando "ativa"
FAIXA DE RELÓGIO ..... 💭 8–12 h  ·  faixa, nunca promessa (§9.2 do protocolo)
ORÇAMENTO ............ 💭 1,2–2,0 M tokens no chat executor (faixa de CRÍTICO, diagnóstico §8). Medir, não prometer
```

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira, antes de qualquer efeito

### 1.1 Allowlist

| Alias | Uso nesta SPEC |
|---|---|
| **TESTE-A** | único número de WhatsApp autorizado a receber/enviar no canário de atendimento |
| **TESTE-B** | segundo número autorizado, quando o caso exigir dois interlocutores distintos |

Os valores reais ficam na configuração privada já existente (`ATTENDANT_INBOUND_ALLOWLIST` /
`JANELA_SILENCIO_EXCECOES`, commit `05f46a9`). **Nunca commitar, publicar em dossiê, print, log, fixture ou
relatório.** No canon só existem os aliases.

### 1.2 O que está autorizado

- Ler o banco de produção com a chave de serviço **em SELECT e contagem**. Detalhe de apólice pela **porta**,
  em memória, para montar o golden — **nunca colado em arquivo**.
- Chat `core` do painel da Resulta pela conta do Founder, com as perguntas do corpus.
- Uma conversa de atendimento com **TESTE-A**, com o agente ligado **apenas** para esse número (as exceções de
  janela do commit `05f46a9` já dão o mecanismo; não criar outro).
- Rodar a suíte, mutações em cópia e scripts de medição read-only.

### 1.3 O que permanece proibido

1. Enviar qualquer mensagem a segurado real, seguradora, atendente, grupo de suporte ou número fora da allowlist —
   inclusive por fallback, alerta, fila, retry ou job de fundo.
2. Ligar o agente de atendimento globalmente numa corretora operacional "para o teste funcionar".
3. Abrir chamado, acionar assistência, entrar em portal de seguradora ou alterar apólice. **Nada desta SPEC
   precisa disso.**
4. Gravar em arquivo, log, teste, fixture, dossiê ou relatório: CPF, CNPJ, telefone, nome de segurado, placa,
   chassi, e-mail, endereço, número de apólice completo ou credencial.
5. Copiar dado de uma corretora para outra "para montar teste".
6. Tratar a autorização de leitura como autorização de escrita: **nenhuma migration roda antes do gate de §11.2**.

### 1.4 A verificação imediatamente antes de cada efeito

Antes de **qualquer** envio: ambiente + tenant + conexão fixada + identidade real do remetente + destino
normalizado + allowlist. Identidade não confirmada → **não envia**, e não escolhe outra conexão sozinho.

🔴 **E a verificação que é específica desta SPEC:** antes de gravar **qualquer** fixture ou golden, passar o
conteúdo pelo redator de PII já existente e **conferir com uma consulta**, não com leitura. O golden da HDI é
construído **pela porta, em memória, e persistido só com os campos que o teste compara** (contagem de coberturas,
rótulos normalizados, origem, presença/ausência de franquia). Valor em R$ é permitido; identificador de pessoa
nunca é.

---

## 2. Escopo completo e exclusões deliberadas

### 2.1 Obrigatório nesta SPEC

1. **A porta com modelo canônico próprio** e cinco operações, no arquivo que já existe.
2. **Dois adaptadores:** `InfoCapProvider` (envolvendo o conector, sem reescrevê-lo) e `PdfOnlyProvider` (mínimo).
3. **Reconciliação CORP × PDF na porta**, por rótulo normalizado, com origem por linha e o **contador de prêmio**.
4. **Vigência e cancelamento filtrados na porta**, antes de qualquer `ambiguous_policy`.
5. **Inferência de ramo para todos os papéis**, lendo ficha + últimas 3 mensagens humanas.
6. **Briefing e guarda corrigidos** para que listar opções deixe de ser o padrão — **sem desfazer** a regra que
   manda listar todas as *coberturas* (§7.2: são duas regras diferentes na mesma seção do arquivo).
7. **PDF oficial lido sempre que a pergunta é de apólice**, não por palavra-chave.
8. **Campos hoje ignorados** passam a ser lidos: `itens[].observacoes`, `sit_renovacao_txt`, `sit_sinistro_txt`,
   `tabela_itens`, `forma_pag`.
9. **Teto no bloco de contexto recuperado** e **a pergunta repetida depois do bloco**.
10. **`agents.llm_max_tokens`** corrigido no banco (P-PILOTO-17) e **tool calls do chat gravadas** (P-PILOTO-18).
11. **P-PILOTO-20** fechada: os 4 guardas antigos de policy voltam a rodar no harness.

### 2.2 Fora desta SPEC, sem empobrecer o outcome

| Frente | Por que não entra | Gatilho de retorno |
|---|---|---|
| **Base de produtos e planos de assistência por seguradora** (`insurer_assistance_plans`, os três níveis, extração das condições gerais) | É a **EXTRA-001.5** inteira, 💭 10–14 h. Ela **pendura na chave nossa** que a 001.1 consolida — por isso vem depois, não junto | EXTRA-001.5, trilho paralelo, começa assim que o Bloco A fechar |
| **A fábrica de conectores** (admissão de provider, censo de capacidade, UI de conexão) | É a **SPEC-101**, que **vira a porta** por D-PILOTO-16. A 001.1 entrega o contrato e os dois adaptadores; a 101 entrega a fábrica | SPEC-101; EXTRA-002/008/009 como adaptadores |
| **Adaptadores Agger, Quiver, Segfy** | Sem credencial medida. A 001.1 prova que o contrato aceita um segundo adaptador construindo o `PdfOnlyProvider` | EXTRA-002 (Agger), 008, 009 |
| **Rajadas, debounce, uma resposta por conversa** | É a **EXTRA-001.2**. Tocar o buffer aqui cria duas SPECs escrevendo no mesmo arquivo | EXTRA-001.2 |
| **`/parcelas`, `/comissoes`, `/financeiro` da InfoCap** | 📊 respondem **403** (P-PILOTO-19): depende de a corretora liberar o perfil da API, não de código | 🧑 Founder pede o perfil à InfoCap; a porta já tem a operação `parcelas_em_aberto` esperando |
| **Ligação apólice → condições gerais pelo processo SUSEP** | O elo é real e já casa hoje (diagnóstico §1.3), mas o consumidor é a 001.5 | EXTRA-001.5 onda 2 |

🔴 **Nada da §2.1 sai em silêncio.** Se a conversão mostrar conflito material, vai para `CHANGE-ADDENDA.md`
classificado (BLOCKER · ESSENCIAL · VALIOSA · FUTURA) com problema, evidência, consequência e autorização
(CLAUDE.md §11). **Escopo não se reduz sem decisão explícita do Founder (D5).**

---

## 3. Autoridades preservadas e arquitetura — o que já existe, e por que não se refaz

### 3.1 A tabela do que se reaproveita, por caminho

| peça que a SPEC precisa | **já existe em** | o que a 001.1 faz com ela |
|---|---|---|
| a porta e o registry | `backend/app/providers/policy_data_provider.py:41,55,137,144` | **evolui** — modelo canônico, 5 operações, reconciliação |
| o adaptador InfoCap | `policy_data_provider.py:55-131` (`InfocapPolicyDataProvider`) | **envolve o conector**; nada do conector é reescrito |
| o conector | `backend/app/api/infocap_connector.py` (4.487 linhas) | **intocado como motor**; deixa de ser chamado fora de `app/providers/` |
| fatos com origem e confiança | `backend/app/services/policy_facts.py:23,84,165` | **vira o modelo canônico**; `infocap_structured` é renomeado |
| o compositor da resposta | `backend/app/services/policy_answer_composer.py:279,297,332` | `_real_vigencia`/`_compose_options` **sobem para a porta** e passam a valer para todos os papéis |
| evidência documental (PDF) | `backend/app/services/policy_document_evidence_service.py` (844 linhas) | **mantido**; muda o **gatilho**, não o motor |
| catálogo de seguradoras (chave SUSEP) | `docs/canon/providers/susep/seguradora-coenti.json` + `susep_ses_provider.py` | **pendura nele**; o adaptador mapeia o código do fornecedor para a nossa chave |
| catálogo de ramos | `docs/canon/providers/susep/ramo-cogrupo.json` | idem |
| padrão de porta que já passou no gate | `backend/app/providers/brokerage_analytics_provider.py` (216 linhas) + `infocap_analytics_provider.py` (1.604 linhas) + `reference_analytics_provider.py` (357) | **referência interna do juiz** — copia-se o PADRÃO, nunca o código |
| **como se testa uma porta neste repositório** | `backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py` | 📊 o teste da 094 faz asserção **estrutural** (`hasattr`, `callable`), **grep no texto do arquivo** (a porta não pode importar o motor; o adaptador tem de importar a fonte) e **comportamento com fixture de 4 conexões** (a escolha cai na única `connected`, nunca na `archived`). É esse o molde de M-A1 e M-A4 |
| registro de chamada de ferramenta | `tool_invocations` + `app/services/skills/gateway.py:294,323` + `app/agents/nodes.py:784,1057` + `invocation_recorder.py` | **já grava** — a SPEC **liga ao turno**, não cria segundo registro (§9.3) |
| últimas 3 mensagens humanas | `backend/app/agents/nodes.py:1011-1017` | **existe e funciona** — só não vale para `core`. Estende-se a condição |
| piso de tokens de saída | `backend/app/factories/llm_factory.py` (commit `312939f`) | **mantido**; a SPEC conserta o **dado** que a tela mostra |
| cobertura item a item | commit `bf963b0` (`/itens` + PDF + cache 180 s) | 🔴 **PROTEGIDO por guarda** — a 001.1 não pode desfazê-lo |

### 3.2 🔴 A fronteira, escrita como regra verificável

```
NINGUÉM fora de backend/app/providers/ importa app.api.infocap_connector.
NINGUÉM fora de backend/app/providers/ conhece preliq, nosnum, codfil, sit_renovacao_txt,
        tabela_itens, forma_pag, inivig, fimvig ou qualquer outro campo de fornecedor.
NENHUM prompt de produto contém a palavra "InfoCap" ou "CorpAPI".
NENHUM texto que chega ao corretor ou ao segurado nomeia o sistema de gestão —
        diz "sistema de gestão da corretora" e "documento oficial da apólice".
```

⚠️ **O BLOCO 0 mede a lista real de infratores antes de escrever a regra.** Se houver chamador legítimo que não
cabe em `app/providers/` (por exemplo uma rota administrativa de diagnóstico), ele entra numa **allowlist escrita,
com o motivo ao lado de cada linha** — nunca numa exceção silenciosa. Uma allowlist com mais de 3 linhas é sinal
de que a fronteira está no lugar errado: **pare e registre** em `FOUNDER-DECISIONS.md`.

### 3.3 Multi-tenant (CLAUDE.md §7)

Toda operação da porta recebe `company_id` **explicitamente**, como primeiro parâmetro nomeado, e o repassa ao
resolver de conexão. Nenhuma operação deduz tenant de contexto global, de sessão ou do LLM.

- O cache documental e o cache de `/itens` (180 s, `bf963b0`) têm chave **`company_id + connection_id + policy_ref`**.
  Chave sem `company_id` é **blocker**, não pendência.
- `policy_ref` segue o padrão já provado na SPEC-094: derivado por corretora, estável entre conexões do mesmo
  tenant, e **opaco** para quem o consome.
- Prova: teste com **dois tenants reais** (fixture de duas conexões distintas) em que a leitura do tenant B nunca
  devolve linha do tenant A, **e** o cache do A não serve o B. O filtro é conferido **no código**, não na RLS
  (o backend usa service role).

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código

> Este documento envelhece. As linhas abaixo foram conferidas em 13/09/2026 sobre `a0bb5fe`. **O número do
> executor vence** (protocolo §5 ①).

1. **Preflight**, nesta ordem, com a saída colada no relatório:
   `git fetch origin` · `git rev-list --count HEAD..origin/main` (🔴 tem de ser 0) ·
   `git rev-list --count origin/main..HEAD` · `git branch --show-current` · `git rev-parse HEAD` · `git status --short`.
2. **Reabrir cada `arquivo:linha` do RESEARCH-PACK §2.** Divergiu? corrigir na SPEC definitiva e **anotar a
   divergência** — não silenciosamente.
3. **Medir a fronteira:** `grep -rn "infocap_connector" backend/ --include=*.py` e
   `grep -rniE "preliq|nosnum|codfil|sit_renovacao_txt|tabela_itens|forma_pag|inivig|fimvig" backend/app --include=*.py`
   fora de `app/providers/` e `app/api/infocap_connector.py`. **Contar.** É esse número que a SUPERFÍCIE do card usa.
4. **Medir o acervo do defeito, sem PII:** quantas respostas do chat `core` de 09–11/09 contêm lista de opções;
   quantas listaram apólice com `valid_to` passado. Consulta e resultado no relatório; **conteúdo de mensagem
   nunca sai da consulta**.
5. **Reconstruir o golden pela porta:** HDI residencial (📊 esperado: 6 garantias no cadastro, 10 linhas no PDF,
   Σ prêmios do cadastro R$ 70,29 × `preliq` R$ 306,60, franquia de Danos Elétricos 550 × 600) e Allianz
   condomínio (📊 esperado: 15 coberturas). **Se o número de hoje não bater com o de 12/09, o número de hoje
   vence** — e a diferença vira linha do relatório.
6. **Ler `MIGRATIONS-AUTHORITY.md` inteiro** antes de qualquer SQL, e medir o schema real de `agents` e de
   `messages` no catálogo do Postgres. 📊 Medido em 13/09: **8 agentes**, 4 `core` + 4 `attendance`,
   `llm_max_tokens` ∈ {1200 ×4, 2000 ×4}.
7. **Medir P-PILOTO-18 com a ferramenta que vai usar:** as chaves reais de `messages.payload.turn`. 📊 Medido em
   13/09 sobre a primeira página de `messages` de 10/09: as chaves são
   `submitted_at, stages, status, attempt, ttft_ms, total_ms, artifacts, error_code, client_request_id` —
   **zero chave de ferramenta**.
8. **Rodar os 4 guardas de P-PILOTO-20** e confirmar que quebram por import, não por regra.
9. **Estabelecer a linha de base da suíte** (falhas preexistentes nomeadas, uma a uma). "Preexistente" é um
   veredito por teste, nunca um rótulo de lote.
10. **Recontar RISCO e SUPERFÍCIE** e escrever o card definitivo no §0.1 do relatório.

**GATE B0:** matriz `premissa → observação nova → comando/consulta → decisão`, com **as divergências do
documento listadas**. Nenhum achado não reproduzido entra como incidente confirmado.

**MUTAÇÃO B0:** o pacote de aquecimento carrega **duas afirmações deliberadamente falsas, assinadas**
(§ do prompt de abertura). O executor tem de refutá-las **com comando**, não com leitura.

---

## 5. BLOCO A — A PORTA: contrato, modelo canônico, dois adaptadores, reconciliação

> Arquivo-hub. **UM dono. Primeiro, sozinho, antes de B, C e D.**
> Arquivos: `backend/app/providers/policy_data_provider.py` · `backend/app/services/policy_facts.py` ·
> `backend/app/providers/infocap_policy_provider.py` (novo) · `backend/app/providers/pdf_only_policy_provider.py` (novo)
> · ⚠️ `backend/app/providers/policy_catalog.py` **só se §5.4 provar que ele precisa existir** — e, se existir,
> ele **delega** a `susep_ses_provider.coenti_de()` / `cogrupo_de()`, nunca lê o JSON.

### 5.1 As cinco operações

```python
class PolicyDataProvider(Protocol):
    provider_key: str                      # "infocap" | "pdf_only" | "quiver" | "agger" | "segfy"

    def capacidades(self) -> CapacidadeDoProvider: ...

    async def buscar_cliente(self, *, company_id: str, documento: str | None = None,
                             telefone: str | None = None, nome: str | None = None
                             ) -> ResultadoDeBusca: ...

    async def listar_apolices(self, *, company_id: str, cliente_ref: str,
                              incluir_vencidas: bool = False,
                              ramo: RamoCanonico | None = None) -> ListaDeApolices: ...

    async def detalhar_apolice(self, *, company_id: str, apolice_ref: str) -> Apolice: ...

    async def documento_oficial(self, *, company_id: str, apolice_ref: str
                                ) -> DocumentoOficial | None: ...

    async def parcelas_em_aberto(self, *, company_id: str, cliente_ref: str
                                 ) -> list[Parcela]: ...

    # ── MEMBROS DEPRECIADOS — existem porque os 8 pontos de chamada de hoje os usam.
    #    Saem quando a tabela de §5.1.1 estiver toda em "migrado". Não são opcionais:
    #    estão NO Protocol, e o verificador de tipos cobra os OITO membros.
    async def lookup(self, **kwargs: Any) -> Dict[str, Any]: ...     # DEPRECIADO
    async def detail(self, **kwargs: Any) -> Dict[str, Any]: ...     # DEPRECIADO
    async def vehicle(self, **kwargs: Any) -> Dict[str, Any]: ...    # DEPRECIADO
```

### 5.1.1 🔴 `vehicle()` nunca esteve no contrato — e é por isso que a porta falha em silêncio

📊 Conferido em 13/09: o `Protocol` atual (`policy_data_provider.py:41-52`) declara **só `lookup` e `detail`**.
`vehicle` existe **apenas** na implementação concreta (`:112`). Consequência medida:

```python
# vehicle_tool.py:57-59
provider = get_policy_data_provider("infocap")
if not provider or not hasattr(provider, "vehicle"):
    return {"content": "Fonte de veículos indisponível.", "found": False}
```

🔴 **Um `hasattr` é o contrato de verdade.** Um adaptador novo que esqueça `vehicle` não quebra: ele responde
*"Fonte de veículos indisponível"* — e o atendente **pede a placa ao cliente**, que é exatamente o que
`infocap_tool.py:256` existe para impedir. **Falha silenciosa que chega ao segurado.**

E o outro lado: `billing_collection.py:793-797` chama `provider.lookup(...)` com guarda **só** de
`provider is None` — **sem `hasattr`**. Um adaptador sem `lookup` levanta `AttributeError` **dentro da rotina de
cobrança**.

**A emenda:** os três membros antigos entram **no Protocol como depreciados**, e a migração é uma tabela, não um
corte:

| # | ponto de chamada | migra para | ordem | dono |
|---|---|---|---|---|
| 1 | `infocap_tool.py:183, :217` (`lookup`) | `buscar_cliente` + `listar_apolices` | **BLOCO B** | 001.1 |
| 2 | `infocap_tool.py:169` (`detail`) | `detalhar_apolice` | **BLOCO A** | 001.1 |
| 3 | `infocap_tool.py:265` (`vehicle`) | `detalhar_apolice().item_de_risco` | **BLOCO D** | 001.1 |
| 4 | `portal_tool.py:350` (`vehicle`) | idem | **BLOCO D** | 001.1 |
| 5 | `insurer_dispatch_tool.py:974` (`vehicle`) | idem | **BLOCO D** | 001.1 |
| 6 | `vehicle_tool.py:64` (`vehicle`) | idem, **e o `hasattr` sai** | **BLOCO D** | 001.1 |
| 7 | `billing_collection.py:797` (`lookup`) | `buscar_cliente` | 🔴 **NÃO MIGRA NESTA SPEC** — é da **EXTRA-001.6**, que corre em paralelo | 001.6 |

🔴 **O item 7 é a razão de os depreciados continuarem no contrato.** Removê-los agora quebraria a cobrança de
uma SPEC irmã em execução simultânea. A SPEC definitiva registra isso em `CHANGE-ADDENDA.md` e avisa a 001.6
**por escrito**, não por suposição.

⚠️ **E isto corrige uma contradição da versão anterior desta proposta:** §14 dizia *"a porta é aditiva; os
chamadores antigos continuam existindo"*, enquanto o GATE A1 exigia que um adaptador incompleto reprovasse. As
duas coisas só convivem se os membros antigos estiverem **no contrato**. Agora estão.

Regras duras do contrato:

- **`company_id` é sempre o primeiro parâmetro nomeado.** Operação sem ele não compila o contrato.
- **`apolice_ref` e `cliente_ref` são opacos.** Seguem o locator técnico que a porta já define
  (`policy_data_provider.py:23`, `parse_policy_locator_ref`, formato `"<provider>:<parte>:<parte>"`). **Número
  humano de apólice nunca é ref** — a regra já está escrita no arquivo e continua valendo.
- **Ausência de dado nunca é `0` nem `None` ambíguo.** Existe uma sentinela tipada `INDISPONIVEL`, no mesmo
  espírito do `UNAVAILABLE` que a SPEC-094 já usa e cuja mutação "`UNAVAILABLE → None`" já é vermelha lá
  (`SPEC-094` Gate A). Reaproveitar o padrão; **não** importar o tipo da 094 se isso acoplar analytics a apólice —
  o executor mede e decide, e escreve a decisão.
- **`capacidades()`** declara, por operação, `SUPORTADA | PARCIAL | INDISPONIVEL | DESCONHECIDA`.
  🔴 `DESCONHECIDA` lê-se *"não verificado"*, **nunca** *"não tem"*. É o que permite ao `PdfOnlyProvider` existir
  sem mentir, e ao adaptador Agger nascer amanhã sem quebrar o compositor.

### 5.2 O modelo canônico — nosso, com origem por campo

```python
Origem       = Literal["sistema_de_gestao", "documento_oficial", "catalogo", "manual"]
Confianca    = Literal["alta", "media", "baixa"]

@dataclass(frozen=True)
class CampoComOrigem[T]:
    valor: T | Indisponivel
    origem: Origem
    confianca: Confianca
    detalhe: dict          # provider_field, pagina, trecho_hash — NUNCA o trecho cru com PII

@dataclass(frozen=True)
class Cobertura:
    rotulo: str                      # humano, já normalizado; código curto ("P","A1") NUNCA vira rótulo
    rotulo_normalizado: str          # chave do casamento CORP × PDF
    limite: CampoComOrigem[Dinheiro]         # LMI
    franquia: CampoComOrigem[Dinheiro | str] # valor OU a prosa de `observacoes`
    premio: CampoComOrigem[Dinheiro]
    divergencia: Divergencia | None  # quando CORP e PDF discordam, as DUAS ficam

@dataclass(frozen=True)
class Parcela:
    numero: int
    vencimento: CampoComOrigem[date]
    valor: CampoComOrigem[Dinheiro]
    forma_de_pagamento: CampoComOrigem[str]   # 🔴 das PARCELAS, não do cabeçalho (§8.3)
    quitada_em: CampoComOrigem[date] | None

@dataclass(frozen=True)
class PlanoDeAssistencia:
    nome: CampoComOrigem[str]        # "Assistências Essenciais"
    nivel: CampoComOrigem[int] | None
    servicos: list[CampoComOrigem[str]]
    estado: Literal["contratado", "nao_contratado", "nao_sabemos_ainda"]

@dataclass(frozen=True)
class Apolice:
    apolice_ref: str
    numero_humano: str
    seguradora: SeguradoraCanonica   # chave NOSSA (§5.4)
    ramo: RamoCanonico               # chave NOSSA (§5.4)
    vigencia: Vigencia               # inicio, fim, situacao: VIGENTE|VENCIDA|CANCELADA|DESCONHECIDA
    coberturas: list[Cobertura]
    parcelas: list[Parcela]
    premio_liquido: CampoComOrigem[Dinheiro]
    plano_de_assistencia: PlanoDeAssistencia | None
    sinais: list[Sinal]              # "cadastro_incompleto", "divergencia_de_franquia", …
    documento: ReferenciaDeDocumento | None
```

🔴 **A regra que o modelo existe para impor:** **toda linha que chega ao corretor ou ao segurado carrega origem.**
Um `CampoComOrigem` sem `origem` não se constrói — é `TypeError`, não um aviso.

### 5.3 A migração de `policy_facts.FACT_SOURCES` — a renomeação que não pode ficar para depois

```
ANTES  FACT_SOURCES = ("infocap_structured", "official_document", "policy_rule")
DEPOIS FACT_SOURCES = ("sistema_de_gestao",  "documento_oficial", "regra_de_apolice")
```

Expand-first, no código como no banco:
1. os novos valores passam a ser **escritos**;
2. os leitores aceitam **os dois** por um período declarado, com o antigo registrado em log;
3. os fatos antigos já persistidos são convertidos na leitura (não há tabela de facts a migrar se o BLOCO 0
   provar que eles só vivem em memória — **medir, não presumir**);
4. o valor antigo sai do código quando o guarda **M-A3** provar que ninguém mais o escreve.

⚠️ **E o nome não muda sozinho o comportamento.** O que o guarda mede é que nenhuma string de fornecedor
atravessa a fronteira — não que a constante foi renomeada.

### 5.4 O catálogo é nosso, e já existe

🔴 **E o leitor do catálogo também já existe.** 📊 Conferido em 13/09 — `backend/app/providers/susep_ses_provider.py`:

```
:129  mapa_de_seguradoras(caminho="")     lê seguradora-coenti.json
:155  mapa_de_siglas(caminho="")          a seção `siglas`
:184  mapa_de_ramos(caminho="")           lê ramo-cogrupo.json
:221  nomes_dos_grupos(caminho="")
:233  cogrupo_de(ramo, *, mapa=None)      ramo        → grupo SUSEP
:258  coenti_de(nome, *, mapa=None, …)    seguradora  → entidade SUSEP
```

⚠️ **`backend/app/providers/policy_catalog.py`, anunciado como "novo, pequeno", é o risco de segundo catálogo.**
A emenda é dura e verificável:

```
policy_catalog.py NÃO lê JSON, NÃO abre arquivo, NÃO tem mapa.
Ele faz UMA coisa: traduz o código/sigla DO FORNECEDOR para o nome canônico,
e DELEGA a coenti_de() / cogrupo_de() a resolução da chave SUSEP.
Se, ao escrever, ele não precisar de mais que isso — ele NÃO EXISTE,
e a tradução mora no adaptador.
```

- **Seguradora:** chave canônica do AutoBrokers, com a **entidade SUSEP (`coenti`)** como identidade estável,
  resolvida por **`coenti_de()`**, nunca por leitura própria do arquivo. O que não casa sai **`UNKNOWN` com o
  nome listado no arquivo**, nunca omitido e nunca zero.
- **Ramo:** resolvido por **`cogrupo_de()`**, sobre `ramo-cogrupo.json`.
- 🔴 **Nome não é chave.** 📊 O censo da 094.1 mediu: o token `SEGUROS` devolveu **284 candidatos** e `SURA`
  devolveu **130** (casa dentro de "ASSURANCE"). **Casamento por derivação de string é proibido**; cada linha
  nova é uma decisão datada, revisada por gente, com o critério escrito ao lado.
- ⚠️ **E o diagnóstico tem uma imprecisão aqui, medida em 13/09:** ele lista `/seguradoras` e `/ramos` entre os
  "campos da API nunca lidos". 📊 `grep` no repositório: **nenhuma chamada HTTP a `/seguradoras` ou `/ramos`
  existe** — as duas menções em `susep_ses_provider.py:36,48` são **docstring** sobre um censo feito à mão.
  **Isso não é um defeito a consertar: é a arquitetura certa.** Chamar `/ramos` no caminho quente do chat seria
  deixar a lista do fornecedor decidir o que é um ramo — exatamente o que D-PILOTO-11 proíbe. O adaptador pode
  ler `/seguradoras` **uma vez, fora do caminho quente**, para propor linhas novas ao arquivo versionado; quem
  aprova é gente.
- ⚠️ **A família que a InfoCap não separa, o catálogo separa:** o briefing de hoje ensina que
  "Liberty e Yelum são a MESMA seguradora" e "Itaú = grupo Porto" (`infocap_tool.py:449`). **Isso é conhecimento
  de catálogo, não de prompt.** Ele sai do texto e vira linha do arquivo versionado, com o guarda medindo que a
  regra continua valendo — porque no prompt ela vale só enquanto o modelo obedecer.

### 5.5 `reconciliar(corp, pdf)` — mora na PORTA, nunca no adaptador

```python
def reconciliar(corp: Apolice, pdf: ApoliceDocumental | None) -> Apolice:
    """Casa cobertura por rótulo normalizado. D-PILOTO-11 governa o desempate."""
```

| campo | vence | por quê |
|---|---|---|
| cobertura, limite (LMI), franquia, cláusula, exclusão, plano/nível de assistência | **documento oficial** | 📊 o cadastro tinha 6 de 10 linhas e faltava 41% do prêmio |
| parcela, quitação, status, vigência, renovação, sinistro | **sistema de gestão** | é o que muda todo dia e o PDF congela na emissão |

Regras:
1. **Divergência não escolhe: mostra as duas.** 📊 A franquia de Danos Elétricos era 550 no cadastro e 600 no PDF.
   A resposta diz o número do PDF **e** que o cadastro diz outro — o corretor decide, e o corretor é quem liga
   para a seguradora.
2. **Casamento por rótulo normalizado** (sem acento, sem caixa, sem pontuação, sinônimos declarados num arquivo,
   não num regex escondido). Rótulo do PDF que não casa com nada **entra como cobertura nova, com origem PDF** —
   nunca é descartado.
3. 🔴 **O contador de prêmio:**
   ```
   Σ premio(cobertura) do sistema de gestão  ≠  premio_liquido  →  Sinal("cadastro_incompleto")
   ```
   com a diferença em R$ e em % ao lado. 📊 Na HDI da Saionara: 70,29 × 306,60 → **77% faltando**. Teria acendido.
   ⚠️ **A tolerância é declarada e pequena** (💭 R$ 0,05 de arredondamento), escrita no código com o motivo.
   Tolerância generosa transforma o sinal em enfeite.
4. **Reconciliar é puro:** sem I/O, sem LLM, sem rede. Entra dois objetos, sai um. É o que torna o guarda barato.

### 5.6 Os dois adaptadores

**`InfoCapProvider`** (`backend/app/providers/infocap_policy_provider.py`) — **envolve** `infocap_lookup`,
`infocap_policy_detail`, `infocap_vehicle_item` e a leitura de `/itens` que o `bf963b0` acrescentou. Nada do
conector é reescrito. É o único lugar do repositório que sabe o que é `preliq`. Reusa o resolver de conexão que
já existe e **filtra `status='connected'`** — 📊 a Resulta tem **duas conexões arquivadas**, uma com credencial
inválida (P-PILOTO-19); uma conexão `archived` **nunca** é escolhida.

**`PdfOnlyProvider`** (`backend/app/providers/pdf_only_policy_provider.py`) — o adaptador mínimo, e **ele não é
enfeite**: é ele que prova que o contrato é um contrato. `capacidades()` devolve `INDISPONIVEL` para
`parcelas_em_aberto` e `PARCIAL` para `listar_apolices`; `detalhar_apolice` monta a `Apolice` só a partir do
documento, com **todas** as origens `documento_oficial`. Uma corretora sem sistema de gestão é atendida por ele.
🔴 **E ele é quem garante que o PDF é lido sempre, não só quando a CORP falha** — no `InfoCapProvider` a leitura
documental é **um passo do caminho feliz**, não um `except`.

**GATE A:**
1. `pytest` do contrato: os dois adaptadores satisfazem o `Protocol`; `mypy`/`pyright` reprova um adaptador a que
   falte **qualquer um dos 8 membros** — as 5 novas **e as 3 depreciadas**. 🔴 E o teste prova que **nenhum
   `hasattr` sobrou** como contrato: `grep -rn 'hasattr(provider' backend/app` → 0.
2. O golden da HDI e o da Allianz condomínio montam **pela porta**, com contagem de coberturas e origem por linha.
3. `reconciliar` puro, sobre os dois pacotes reais mascarados, produz o sinal de cadastro incompleto na HDI e
   **não** produz na apólice de controle em que a soma bate.
4. Dois tenants: a leitura do B nunca devolve linha do A, e o cache do A não serve o B.

**MUTAÇÃO A:** (a) `from app.api.infocap_connector import infocap_lookup` dentro de `infocap_tool.py`;
(b) `CampoComOrigem` aceitando `origem=None`; (c) tolerância do contador de prêmio para `float('inf')`;
(d) chave de cache sem `connection_id`; (e) **adaptador sem `vehicle`** → o verificador de tipos reprova
(hoje o `hasattr` deixaria passar). **As cinco têm de ficar vermelhas.**

---

## 6. BLOCO B — VIGÊNCIA E RAMO: a escolha acontece na porta, e diz por quê

> Arquivos: `policy_data_provider.py` (a operação `listar_apolices`) · `policy_answer_composer.py:279-331`
> (as duas funções sobem) · `infocap_tool.py:26-40, 195-230` · `infocap_connector.py:~1315`.

### 6.1 O filtro, e onde ele passa a morar

📊 Conferido em 13/09 — `infocap_connector.py:1316-1331` decide por **contagem pura**, e nenhuma data participa:

```python
:1316   if documents_count > 1 and not requested_policy_number:
:1317       return _done({"ok": False, "status": "ambiguous_policy",
:1322                     "result_count": documents_count,
:1323                     "documents_count": documents_count,     ← a contagem CHEIA
:1326                     "matches": [p for p in policies[:10]],  ← 🔴 a lista TRUNCADA em 10
:1328                     "requires_human": True, "blockers": ["multiple_policies"]})
```

🔴 **E aqui está um defeito que a versão anterior desta proposta ia introduzir.** `documents_count` é a contagem
cheia; `matches` tem no máximo **10**. Filtrar vigência **na porta sobre `matches`** faria duas coisas erradas
num cliente com 11 ou mais apólices:

```
a única VIGENTE pode estar na posição 11  →  a porta conclui "nenhuma vigente"
                                             e responde a frase da §6.2 — MENTINDO
historico_oculto derivado de len(matches)  →  diz "3 ocultadas" quando são 14
```

⚠️ **Um cliente com 11+ apólices não é hipótese:** é a carteira de uma empresa, de um condomínio ou de uma
família — exatamente o perfil da Allianz condomínio que está no golden.

**A emenda, e ela é do contrato:**

1. **`listar_apolices` lê a lista inteira**, não a truncada. Se o conector não a expuser, ele passa a expor —
   ou filtra vigência **antes** de truncar. O executor mede qual das duas custa menos e escreve a escolha.
2. 🔴 **`historico_oculto` deriva de `documents_count`**, nunca de `len(matches)`. É a única fonte que conhece
   o tamanho real.
3. O truncamento em 10 continua existindo **para o texto que vai ao modelo** — é teto de prompt, e é legítimo.
   O que não pode é ele **decidir vigência**.

…embora `/cliente_ligacoes` já devolva `inivig`, `fimvig`, `ramo` e `cancelado` por documento. E o filtro certo
**existe**, em `policy_answer_composer.py:279-300` — só que roda **depois**, no compositor. A docstring de `:279`
é a prova de por que ele nasceu:

> *"Vigência REAL calculada pelas datas — a fonte marca 'ativo' até em apólice vencida há anos (bug visto no
> teste do founder 2026-07-10)."*

E `:297-299` diz, em comentário, exatamente a regra que esta SPEC promove a estrutura: *"vencidas/canceladas
NUNCA aparecem como opção quando existe apólice vigente"*. 🔴 **A regra já está escrita e já está certa. O que
está errado é o lugar: ela roda tarde demais, e só para quem chega no compositor.**

**A 001.1 move a decisão para a porta**, antes de qualquer status ambíguo:

```
listar_apolices(company_id, cliente_ref, incluir_vencidas=False, ramo=None)
  → classifica cada apólice: VIGENTE | VENCIDA | CANCELADA | DESCONHECIDA
     (por inicio/fim contra a data de hoje no fuso da CORRETORA, e por `cancelado`;
      🔴 `policy_status` do fornecedor NUNCA decide sozinho — entra como sinal, não como veredito)
  → aplica o ramo, quando houver
  → sobrou 1  →  status "found" + auto_selected_reason + historico_oculto: N
  → sobrou 0 vigente e havia N vencidas  →  status "sem_vigente" + ultima_vigente(numero, ate)
  → sobraram 2+ do MESMO ramo  →  status "ambiguous_policy" com as opções JÁ FILTRADAS
  → sobraram 2+ de ramos DIFERENTES e há ramo deduzido  →  aplica o ramo e recomeça
```

**`auto_selected_reason` é texto humano, não código** (CLAUDE.md §9.5: "a escolha diz por quê"):

> 💭 `"única apólice vigente de auto; 2 vencidas ocultadas"`
> 💭 `"única vigente; a Allianz venceu em 14/08"`

E `historico_oculto: N` é o que torna a ocultação **honesta**: o corretor vê que existe histórico e sabe pedir.

### 6.2 Quando não há nenhuma vigente

A resposta **não** é "não encontrei". É, palavra por palavra da §3 do diagnóstico:

> 💭 "A última apólice vigente foi a **[número]**, da **[seguradora]**, que valeu até **14/08/2026**. Hoje não há
> nenhuma apólice vigente deste cliente no sistema de gestão. Quer que eu liste o histórico?"

### 6.3 A inferência de ramo — para todos os papéis, e lendo mais que a última frase

📊 Conferido em 13/09: a auto-seleção inteira (`infocap_tool.py:197-215`) está trancada atrás de
`self._client_facing` — property de `:128-129` que devolve `agent_role in ("attendance","insured_external")`
(`:22`). **O chat do painel é `core`.** É por isso que o corretor recebe a lista e o segurado não.

⚠️ **E aqui o diagnóstico precisa de uma emenda.** Ele diz que "a inferência de ramo só lê a mensagem atual".
`_product_hint_from_query` (`:35-41`) de fato só lê a string que recebe — mas **quem a alimenta decide**:
`nodes.py:1009-1018` já concatena as 3 últimas humanas **para atendimento**. Ou seja, o defeito não é "a função
lê pouco": é **`core` receber uma frase onde atendimento recebe três**, e a auto-seleção nem rodar para `core`.
A distinção muda o conserto: não se reescreve a função, **estende-se a condição**.

Três correções, todas pequenas:

1. **A auto-seleção passa a valer para todos os papéis.** O que muda entre `core` e `attendance` é **a redação
   da resposta**, nunca **qual apólice é a certa**.
2. **A fonte do sinal de ramo deixa de ser uma string.** Passa a ser, em ordem de precedência:
   ```
   ① ramo explícito no pedido ("a do carro", "a residencial")
   ② ficha do atendimento, quando existir (apólice já confirmada no caso)
   ③ as 3 últimas mensagens humanas
   ④ o serviço pedido (guincho → auto; encanador → resi)
   ```
   🔴 **E o mecanismo de ③ já existe:** `nodes.py:1009-1018` monta
   `" | ".join([t for t in _recent_humans[-3:] if t])` — **só que dentro de um
   `if _role in ("attendance","insured_external")`**; fora dele, `_query_for_tool = current_user_query`, que
   `nodes.py:942-946` define como a **última** humana. A correção é estender a condição, não escrever a janela
   de novo.
3. **`chaveiro`.** 📊 Conferido em 13/09: a palavra está em `_AUTO_INTENT_RE` (`infocap_tool.py:27`) e **não**
   está em `_RESI_INTENT_RE` (`:30-32`, que tem `fechadura da porta`). Chaveiro de **casa** é residencial,
   chaveiro de **carro** é auto. Hoje, *"preciso de um chaveiro, fiquei trancado fora de casa"* devolve
   **`"auto"`**. A palavra sozinha **não decide**: ela entra nos dois regex e o desempate vem do contexto
   (`carro|veículo|porta de casa|apartamento`) ou, não havendo contexto, do **número de apólices vigentes** —
   e se houver uma de cada, **aí** se pergunta, uma vez.

⚠️ **A armadilha que o aquecimento tem de pegar:** acrescentar `chaveiro` aos dois regex **sem** o desempate não
muda nada — `_product_hint_from_query` (`:36-41`) testa AUTO **primeiro** e retorna na primeira condição que
casa. O guarda **M-B3** existe exatamente para isso: ele não mede o regex, mede o motor.

**GATE B:**
1. Sobre o acervo mascarado das 📊 31 linhas de opção de 09–11/09: `listar_apolices` devolve **zero** vencidas,
   e `historico_oculto` bate com a contagem.
2. Par de controle (CLAUDE.md §9.5): cliente com **1 vigente auto + 1 vigente resi** → **não pergunta**;
   cliente com **2 vigentes auto** → **pergunta**. Mesma superfície, veredito oposto.
3. `auto_selected_reason` presente em 100% dos `found` por auto-seleção, e legível (passa pela régua de língua
   que já existe, `problemas_de_lingua`).
4. A pergunta só de CPF, sem nenhuma palavra de ramo, resolve pela ficha ou responde com a **única** vigente.

**MUTAÇÃO B:** (a) restaurar `self._client_facing` na condição da auto-seleção; (b) desligar o filtro de vigência
em `listar_apolices`; (c) `chaveiro` só no regex de auto **sem** desempate; (d) `policy_status` voltando a decidir
vigência. **As quatro vermelhas.**

---

## 7. BLOCO C — O BRIEFING E O GUARDA: listar deixa de ser o padrão

> Arquivos: `backend/app/agents/tools/infocap_tool.py:403-414, 445-474` ·
> `backend/app/agents/nodes.py:263-274` · `backend/app/core/prompts.py`.

### 7.1 O que sai do briefing

📊 Conferido em 13/09 — a instrução que manda listar opções aparece **três vezes**, com papéis diferentes:

| linha | texto | veredito |
|---|---|---|
| `infocap_tool.py:405` | `"opcoes_de_apolice (liste TODAS, com os numeros exatos):"` | 🔴 **SAI** — vira `apolices_vigentes` já filtrado; o cabeçalho deixa de ordenar |
| `infocap_tool.py:467` | `"3. Se houver opcoes_de_apolice, liste TODAS com os numeros exatos e peca a escolha."` (bloco do **corretor**) | 🔴 **SAI**, e volta condicionada: *só quando o bloco trouxer `apolices_vigentes` com 2+ do mesmo ramo* |
| `infocap_tool.py:453` | `"4. Se houver mais de uma apolice vigente: escolha VOCE a coerente com o pedido…"` (bloco do **segurado**) | ✅ **JÁ ESTÁ CERTO** — é a regra que a 001.1 estende ao corretor |

📊 Conferido em 13/09: **`:453` está exatamente 48 linhas abaixo de `:405`** — o mesmo bloco monta a lista e, 48
linhas depois, manda escolher sozinho. Os dois textos saem do **mesmo** array `lines`, que já contém
`opcoes_de_apolice`. O modelo obedece ao que aparece primeiro.

### 7.2 🔴 A regra que NÃO pode sair junto — e que é a armadilha desta SPEC

```
infocap_tool.py:465        ← DUAS linhas acima da que sai
"1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), cada uma com
     limite, franquia e premio — de preferencia numa tabela. Nunca resuma para
     'uma cobertura' quando o bloco traz varias."
```

**Esta linha FICA.** Ela é o conserto do commit `bf963b0` (📊 prova ao vivo: HDI 6 coberturas, Allianz 15) e é
exatamente o oposto do defeito de §1.1: uma manda listar **coberturas** (certo), a outra manda listar **apólices**
(errado). As duas usam as palavras "liste TODAS" e moram a **duas linhas** de distância no mesmo array
(📊 `:465` e `:467`, conferido em 13/09).

🔴 **Um executor que aplicar "tirar 'liste TODAS' do briefing" ao pé da letra reintroduz o defeito das 6 de 10.**
O guarda **M-C2** existe para deixar isso vermelho.

### 7.3 O guarda de `nodes.py`

📊 Conferido em 13/09 — `nodes.py:263-273` (SPEC-016.1 D7) **anula** qualquer resposta que não cite todos os
números de `policy_options`:

```python
if "policy_options" in required:
    options = contract.get("policy_options") or []
    for option in options[:10]:
        number = str(option.get("policy_number") or option.get("numapo") or "").strip()
        if number and … and number not in candidate:
            return rendered          # ← anula a resposta do modelo
```

**O guarda não morre — ele passa a guardar a regra certa.** `policy_options` só é populado quando a porta devolver
`ambiguous_policy`, isto é, **2+ vigentes do mesmo ramo**. Nos demais casos a lista vem vazia e o guarda não tem
o que exigir. Assim ele continua impedindo o modelo de **esconder** uma opção quando a escolha é legítima — que é
a razão de ele existir — e para de **obrigar** a listagem quando não é.

⚠️ O ramo `if not options and (...)` de `:273` precisa ser remedido: hoje ele tem um `and`/`or` que muda o
significado conforme a precedência. **Medir o comportamento real com um teste antes de tocar**, não deduzir por
leitura (protocolo §0.4).

### 7.4 O `CORE_BASE_PROMPT` ganha a regra — em uma frase, não em cinco

📊 Diagnóstico §1.1 causa 4: o `CORE_BASE_PROMPT` **não tem uma linha** sobre vigência ou ramo.

> 💭 "Quando o bloco da apólice trouxer uma apólice vigente, responda sobre ela e diga por que é ela. Só peça ao
> corretor que escolha se o bloco trouxer duas ou mais vigentes do mesmo ramo. Apólice vencida só entra na
> resposta se ele pedir histórico."

🔴 **E a regra da fronteira (§3.2) vale aqui:** nenhuma palavra "InfoCap" ou "CorpAPI" em `core/prompts.py`.
A origem, na resposta, é **"o sistema de gestão da corretora"** e **"o documento oficial da apólice"**.

📊 **Conferido em 13/09 — inventário completo, linha a linha, com veredito.** Comandos:
`grep -ni "infocap" backend/app/core/prompts.py` (8 linhas) e `grep -o -i "infocap" … | wc -l`
(**10 ocorrências**). `CorpAPI`: **0**.

| linha | ocorrências | o que é | veredito |
|---|---:|---|---|
| **:31** | 1 | *"se confirmam na InfoCap ou no documento"* | **PROSA → sai** ("no sistema de gestão da corretora") |
| **:37** | 1 | `` `infocap_policy_lookup` `` — **o nome registrado da ferramenta** | 🔴 **FICA** (ver abaixo). ⚠️ E o resto da linha é a instrução do commit `bf963b0` — **não se apaga a linha** |
| **:40** | 1 | *"Se a ferramenta InfoCap trouxe o dado"* | **PROSA → sai** |
| **:42** | 1 | *"CHAME a ferramenta InfoCap"* | **PROSA → sai** |
| **:47** | 1 | *"quando responder sobre uma apólice (InfoCap OU documento)"* | **PROSA → sai** · 🔴 **dentro do `CORE_BASE_PROMPT` (L22-60)** |
| **:131** | **2** | *"descubra na InfoCap"* · *"a ferramenta pega da InfoCap"* | **PROSA → sai** |
| **:133** | **2** | *"busca SOZINHA na apólice (InfoCap)"* · *"Identifique o cliente na InfoCap"* | **PROSA → sai** |
| **:193** | 1 | *"consulta ao sistema da corretora (InfoCap ou outro gestor)"* | **PROSA → sai** |

**9 de prosa saem. 1 identificador fica.** ⚠️ A versão anterior desta proposta dizia "6 vezes" e omitia `:47`
e `:131` — **`:47` é a mais grave das oito, porque é a única dentro do `CORE_BASE_PROMPT`.**

### 7.4.1 🔴 Por que o identificador da ferramenta fica — e o que o guarda passa a medir

📊 `infocap_policy_lookup` é o **nome registrado** da tool, e aparece em pelo menos sete lugares fora do prompt:

```
backend/app/agents/tools/infocap_tool.py:74      name: str = "infocap_policy_lookup"
backend/app/agents/gateway_cutover.py:102        "infocap_policy_lookup": "insurance.policy_lookup"
backend/app/api/chat_eventos.py:214              "infocap_policy_lookup": _APOLICE
backend/app/services/prompt_effective_service.py:80
backend/app/agents/nodes.py:38, :576, :1004, :1146
```

**Renomear a tool é um cutover de catálogo, não uma edição de texto** — e `gateway_cutover.py:102` prova que o
projeto **já** tem o caminho para isso (`insurance.policy_lookup`), o que torna a renomeação uma entrega de
**outra** SPEC, com o seu próprio gate de compatibilidade.

🔴 **E o argumento que decide:** o identificador **nunca chega ao usuário**. 📊 `chat_eventos.py:19` documenta,
em comentário, que o rótulo exibido é *"apólice"*, **nunca `infocap_policy_lookup`**. A fronteira que D-PILOTO-11
exige é sobre **o que o corretor e o segurado leem**, não sobre um símbolo interno.

**Portanto o guarda M-A1 mede MENÇÃO EM PROSA, e não a string solta:**

```
❌  grep -i "infocap"                       → pega o identificador; obriga um cutover fora de escopo
✅  grep -nE '\bInfoCap\b' (SENSÍVEL A CAIXA) em core/prompts.py            → tem de dar 0
    + allowlist ESCRITA de um único identificador: `infocap_policy_lookup`
    + a allowlist mora no teste, com o motivo ao lado e o número da SPEC que fará o cutover
```

⚠️ **A alternativa medida e rejeitada:** escopar a renomeação da tool para dentro da 001.1, com gate próprio.
Nota 💭 40 — ela toca 7 arquivos, o catálogo de capacidades, o mapa de eventos do chat e o `prompt_effective`,
e nada disso muda um byte do que o corretor lê (protocolo §2: é **pendência**, não blocker). Fica registrada
como pendência nova, com gatilho: *"quando a segunda corretora usar um sistema de gestão diferente"*.

⚠️ E há uma armadilha de contagem: o `ATTENDANCE_BASE_PROMPT` (L83-218) **já tem** a regra certa em **L126**
(*"Mais de uma apólice vigente? ESCOLHA VOCÊ…"*) e em **L206** (*"só ofereça as com vigência ATUAL"*). 📊 O
`CORE_BASE_PROMPT` **não tem nenhuma** — as palavras "vigência" só aparecem nele como **lista de dados que a tool
devolve** (L37, L40), nunca como instrução. **A regra não precisa ser inventada: precisa ser copiada do papel que
já a tem, e depois subir para a porta, onde deixa de depender de o modelo obedecer.**

**GATE C:**
1. 📊 `grep -nE '\bInfoCap\b' backend/app/core/prompts.py` (**sensível a caixa**) → **0** (hoje: 8 linhas,
   9 menções em prosa). `grep -n "CorpAPI"` → **0** (hoje já é 0). O identificador `infocap_policy_lookup`
   (`:37`) está na allowlist escrita do teste, com o motivo e o número da SPEC do cutover.
2. O corpus das 7 perguntas reais de 10/09 (só as perguntas, PII removida), rodado **pelo motor**: 7 de 7 chegam
   a uma resposta em **1 rodada**, nenhuma lista opções.
3. Golden HDI → **10 linhas de cobertura**; Allianz condomínio → **15**. Vermelho em 6 de 10.
4. Um caso com 2 vigentes do mesmo ramo → o guarda de `nodes.py` **continua** anulando resposta que omita uma.

**MUTAÇÃO C:** (a) reintroduzir `"liste TODAS com os numeros exatos"` no bloco do corretor;
(b) **apagar a regra 1b** (as coberturas); (c) `policy_options` populado com vencidas;
(d) `"InfoCap"` numa linha do `CORE_BASE_PROMPT`. **As quatro vermelhas.**

---

## 8. BLOCO D — O PDF É LIDO SEMPRE, E OS CAMPOS QUE NINGUÉM LIA

> Arquivos: `backend/app/services/policy_document_evidence_service.py:~132` ·
> `backend/app/providers/infocap_policy_provider.py` · `policy_facts.py`.

### 8.1 O gatilho deixa de ser palavra-chave

📊 Conferido em 13/09 — `policy_document_evidence_service.py:132`:

```python
def policy_document_evidence_requested(question, explicit=False) -> bool:
    if explicit:
        return True
    normalized = _strip_accents(question or "")
    return any(term in normalized for term in _INTENT_TERMS)
```

`_INTENT_TERMS` (a partir de `:47`) traz `cobertura, cobre, garantia, assistencia, eletricista, encanador,
chaveiro, franquia, lmi, limite, importancia segurada, clausula, exclusao, condicao…`. **É uma lista de palavras
sobre a última mensagem.** *"Quero o detalhamento da apólice X"* **não casa** com nenhuma delas — e o PDF não é
lido. ⚠️ E note o parâmetro `explicit`: o caminho para ler sempre **já existe**; ninguém o usa a partir do fluxo
de apólice.

**A regra nova:**

```
a pergunta é SOBRE APÓLICE?   →  o documento oficial é lido.  Ponto.
```

"Sobre apólice" é decidido pelo **destino da chamada**, não pelo texto: se a tool de apólice foi chamada, o
documento entra no caminho feliz. O cache de 180 s por `corretora + apólice` (commit `bf963b0`) é o que faz isso
não custar — e o `PdfOnlyProvider` (§5.6) é o que faz isso ser estrutura, não `if`.

🔴 **A linha de controle obrigatória** (CLAUDE.md §9.2): uma pergunta que **não** é de apólice
(💭 "quantos clientes eu tenho?") **não** dispara leitura documental. Sem ela, o guarda que exige "7 de 7" passa
com um `return True` no topo da função.

### 8.2 Os campos que a API devolve e ninguém lê

| campo | o que carrega | onde entra no modelo |
|---|---|---|
| `itens[].observacoes` | **as franquias em prosa** ("15% dos prejuízos, mínimo R$ 600") | `Cobertura.franquia` como `CampoComOrigem[str]` — a prosa é o valor, não um comentário |
| `sit_renovacao_txt` | "APÓLICE VIGENTE…" | `Apolice.vigencia` como **sinal**, nunca como veredito |
| `sit_sinistro_txt` | situação de sinistro | `Apolice.sinais` |
| `tabela_itens` | **o nome do plano** ("PACOTE", "Benefícios") | `PlanoDeAssistencia.nome`, origem `sistema_de_gestao` |
| `forma_pag` (cabeçalho) | 🔴 **mente** | ver §8.3 |
| `/seguradoras`, `/ramos` | catálogo do fornecedor | **só** no adaptador, para mapear à nossa chave (§5.4) |

### 8.3 🔴 `forma_pag`: o campo que mente, e o que se faz com ele

📊 Diagnóstico §1.2 causa 3 e §12.1: o `forma_pag` do **cabeçalho** diz **Boleto** enquanto as **parcelas** dizem
**Cartão**. A HDI da Saionara tem **4 parcelas no cartão**.

**A forma de pagamento do modelo canônico vem das PARCELAS.** O campo do cabeçalho entra como sinal
`"cabecalho_divergente"` quando discorda — e **não** aparece na resposta.

⚠️ CLAUDE.md §12.1: *"se o nome de um campo mente sobre o que ele guarda, conserte o campo"*. Aqui o campo é do
fornecedor e não se conserta — **por isso ele não atravessa a fronteira com esse nome**. É a diferença entre um
adaptador e um alias.

**GATE D:**
1. Corpus das 7 perguntas: leitura documental disparada em **7 de 7**; e a pergunta de controle (não-apólice)
   em **0 de 1**.
2. Golden HDI: a linha de **Assistências Essenciais (R$ 125,94)** aparece, com origem `documento_oficial`.
3. Franquia de Danos Elétricos: as **duas** (550 do cadastro, 600 do documento) aparecem, com a divergência dita.
4. Forma de pagamento respondida: **cartão**, e não o boleto do cabeçalho.
5. Sinal `cadastro_incompleto` aceso na HDI; **apagado** na apólice de controle.

**MUTAÇÃO D:** (a) voltar o gatilho por palavra-chave; (b) `forma_pag` do cabeçalho vencendo;
(c) `observacoes` descartado; (d) divergência de franquia resolvida silenciosamente pelo maior valor.
**As quatro vermelhas.**

---

## 9. BLOCO E — O TURNO QUE SOME, O TETO DE TOKENS E O RASTRO

> Disjunta de A–D. Pode correr em paralelo.
> Arquivos: `backend/app/agents/graph.py:~1395-1405` · `backend/app/api/chat.py` ·
> `backend/app/factories/llm_factory.py` · migration nova.

### 9.1 A pergunta sobrevive ao bloco de contexto

📊 Duas vezes o agente respondeu *"ainda não recebi uma pergunta sua"* — nos **dois maiores turnos do acervo**
(120 e 128 chunks de RAG; 135k e 163k tokens de entrada).

📊 Conferido em 13/09: `graph.py:1377` atribui `rag_prefetch_content = rag_result.get("content") or ""`
**cru — sem `[:N]`, sem contagem de tokens** — e `:1394-1405` o concatena em `dynamic_context` entre os
marcadores `=== 📚 CONTEXTO RECUPERADO… ===`. O resultado vira `composite_prompt = static_prompt +
dynamic_context` em `:1515`. **A pergunta do usuário fica antes de tudo isso.**

Duas correções, e a segunda é a que tem fonte primária (§16, referência ⑤):

1. **Teto declarado** no bloco de contexto recuperado — em **caracteres ou chunks contados**, com o número
   escrito, o motivo ao lado e o excedente **dito** ("mostrando os N trechos mais relevantes de M"), nunca
   truncado em silêncio.
2. 🔴 **A pergunta é repetida DEPOIS do bloco.** 📊 "Lost in the Middle" (Liu et al., TACL 2023) mediu que o
   desempenho é mais alto quando a informação relevante está **no começo ou no fim** do contexto e cai
   significativamente no meio — **inclusive em modelos explicitamente de contexto longo**. Repetir a pergunta
   depois do bloco é colocá-la no fim.

⚠️ **E a prova não é o teste sintético.** O guarda roda sobre um turno do **tamanho medido** dos dois piores casos
do acervo. Um teste com 3 chunks não prova nada sobre 128.

### 9.2 P-PILOTO-17 — `llm_max_tokens` no banco

📊 Medido em 13/09/2026 (`SELECT agent_role, llm_max_tokens FROM agents`, contagem, sem PII):

```
8 agentes  ·  4 core + 4 attendance
llm_max_tokens:  1200 → 4 agentes     2000 → 4 agentes
```

O piso de 8192 do `llm_factory.py` (commit `312939f`) já conserta o **comportamento**. O que continua errado é o
**dado**: quem abre a tela lê 1200, e quem ler o banco para decidir qualquer coisa decide errado.

**Decisão, com nota (CLAUDE.md §12.1; a pontuação é a recomendação do redator, o executor confirma no BLOCO 0):**

| opção | nota | por quê |
|---|---|---|
| **migration de dado, no diretório canônico, com APPLY/VERIFY/ROLLBACK** | **88** | 8 linhas em 4 corretoras, rastro no Git, reprodutível, e o ROLLBACK guarda os valores exatos |
| pela tela, à mão | 45 | 8 telas, 4 trocas de corretora, zero rastro, e o Founder é 🧑 num item que é 🤖 |
| não mexer — o piso basta | 55 | o comportamento fica certo e o dado continua mentindo; o próximo leitor decide errado (§12.1) |

🔴 **E há um segundo defeito escondido atrás do primeiro — medido, não suposto.** 📊 Conferido em 13/09, o
default `2000` mora em **quatro lugares**, e o código diverge de todos:

```
schema_completo.sql:454   public.agents.llm_max_tokens    integer DEFAULT 2000
schema_completo.sql:581   public.companies.llm_max_tokens integer DEFAULT 2000
backend/app/api/agent_config.py:133                       = 2000
backend/app/models/agent.py:19                            default=2000, ge=100
backend/app/factories/llm_factory.py:84-85                company_config.get("llm_max_tokens", 8192)   ← 8192
```

O agente da próxima corretora **nasce com 2000**. Corrigir as 8 linhas sem corrigir os defaults é consertar o
sintoma. A SPEC conserta os defaults de **código** (`agent_config.py`, `models/agent.py`) junto com o dado; o
`DEFAULT` de **schema** é DDL e vira **segunda migration**, com manifesto completo — **ou** fica registrado como
pendência com número, se o BLOCO 0 mostrar que o código nunca deixa o banco decidir.

⚠️ E há uma decisão a tomar com nota: `companies.llm_max_tokens` é o **fallback** da corretora. Subi-lo junto
(nota 💭 80) mantém uma régua só; deixá-lo (💭 55) mantém o piso do código como única rede. O executor decide no
BLOCO 0 **medindo quem lê a coluna de `companies` hoje** — não por simetria.

### 9.2.1 🔴 O defeito novo que a conferência achou: o segurado não tem piso

📊 Conferido em 13/09, `backend/app/factories/llm_factory.py:34-35`:

```python
PAPEIS_QUE_CONVERSAM = ("", "core", "attendance")
```

**`insured_external` não está na lista.** É o papel do agente que fala com o **segurado** (GLOSSARIO: *"quem fala
com o segurado"*). Ele fica com o valor gravado no banco — 📊 hoje 1200 ou 2000 — **sem piso**.

**Teste do produto (protocolo §2):** consertar isto muda um byte do que chega **ao segurado** — a resposta dele
pode ser cortada no meio, exatamente como 10 das 95 respostas do corretor foram. **É BLOCKER, não pendência.**
A correção é uma palavra na tupla, e o guarda é a mutação que a remove.

### 9.3 P-PILOTO-18 — o rastro da ferramenta · **⚠️ a pendência está DESATUALIZADA, e o conserto é outro**

P-PILOTO-18 diz: *"o chat do painel não registra que ferramenta o agente chamou … sem `tool_invocations`"*.

📊 **Conferido em 13/09 — a tabela existe e o chat grava nela:**

```
backend/app/agents/nodes.py:784    def _abrir_registro_de_invocacao(state, *, tool_name, tool_args)
backend/app/agents/nodes.py:1057   registro = _abrir_registro_de_invocacao(...)  →  with registro:
                                   ENVOLVE TODA execução de tool no tool_node
backend/app/services/skills/gateway.py:294   db.table("tool_invocations").insert({...})
backend/app/services/skills/gateway.py:323   .update({...})   (finalizar_invocacao)
backend/app/services/skills/invocation_recorder.py           RegistroDeInvocacao
```

🔴 **Escrever a SPEC pela pendência teria criado uma segunda gravação de tool call ao lado da que existe** —
motor paralelo (CLAUDE.md §5). O que falta é **outra coisa**, e são três coisas:

| falta | prova | o que a 001.1 faz |
|---|---|---|
| **a ligação com o turno** | `messages.payload.turn` (📊 chaves medidas em 13/09: `submitted_at · stages · status · attempt · ttft_ms · total_ms · artifacts · error_code · client_request_id`) **não** referencia a invocação | o `client_request_id` do turno entra em `tool_invocations`; a resposta da API expõe `tool_calls` derivadas por junção — **uma escrita, dois leitores** |
| **o silêncio na falha** | `_RegistroInerte` (`nodes.py:814-830`) engole erro de registro para não derrubar a tool | correto como desenho; **errado sem contador**: o inerte passa a incrementar um contador observável, e o guarda mede que ele é 0 no caminho feliz |
| **a DDL não é rastreada** | 📊 `20260727_04_indices_read_models_061.sql:24` diz "JA EXISTIA"; `20260816_02_...:147` registra *"a DDL de `tool_invocations` não está rastreada no repositório"* | entra no **`MANIFEST.md`** como `NÃO RASTREADA`, com o DDL real lido do catálogo — **documental, sem DDL nova** (MIGRATIONS-AUTHORITY §3, §5) |

🔴 **E o que NÃO se grava, em nenhuma das pontas:** argumento cru. Um `tool_args` de `infocap_policy_lookup`
carrega **CPF**. Grava-se `{"documento": "presente"}`, nunca o documento. **Medir isto é obrigatório no BLOCO 0**:
se `tool_invocations` já estiver guardando argumento cru hoje, isso é um **P1 de segurança** desta SPEC, não uma
pendência — e a drenagem vem antes da funcionalidade.

⚠️ `messages.payload` é `jsonb` com escritor. **Acrescentar chave não é migration**; mudar tipo ou trava é.

**A pendência é reescrita, não fechada por engano:** P-PILOTO-18 passa a dizer o que realmente falta.

### 9.4 P-PILOTO-20 — os 4 guardas que não rodam

📊 Desde 23/08, `test_infocap_policy_output_guard` e `test_spec016_*` quebram no harness porque `nodes.py` importa
`honestidade_do_handoff` e o stub de `app.agents` tem `__path__=[]`. **Pré-existente, não é regressão.**

Conserto: o harness registra o módulo no stub. É pequeno — e **é pré-requisito**, porque são exatamente os
guardas da superfície que esta SPEC mexe. **Entregar a 001.1 com eles mudos é entregar sem rede.**

**GATE E:**
1. Turno do tamanho medido dos dois piores do acervo → a resposta **responde a pergunta** (não "não recebi").
2. `SELECT agent_role, llm_max_tokens, count(*) FROM agents GROUP BY 1,2` → **8 de 8 em 8192**; VERIFY colado.
3. `piso_de_saida("insured_external", 1200)` → **8192**. Hoje devolve 1200.
4. Um turno do chat com chamada de ferramenta → a invocação está em `tool_invocations` **ligada ao turno**, e o
   varredor de PII (`backend/scripts/auditar_pii_no_codigo.py` + o redator de saída) **não acha nada** nela.
5. Os 4 guardas de P-PILOTO-20 **rodam** — verdes ou vermelhos, mas rodam.

**MUTAÇÃO E:** (a) remover a repetição da pergunta depois do bloco (o turno grande volta a falhar);
(b) teto substituído por corte silencioso; (c) `insured_external` fora de `PAPEIS_QUE_CONVERSAM`;
(d) gravar `tool_args` cru com CPF; (e) ROLLBACK da migration aplicado → os 8 valores voltam **exatamente** ao
que eram, conferidos por `agent_id`. **As cinco vermelhas.**

---

## 10. Os guardas novos — **12, o teto de D-PILOTO-14** (+ 1 canônico), cada um com a mutação que o deixa vermelho

🔴 Todos sobre o **MOTOR** e o **ACERVO real** (CLAUDE.md §9.4/§9.5). **Proibido teste que reimplementa a regra:**
o teste chama `porta.listar_apolices(...)`, nunca um regex sobre a mesma tabela que o código lê.

| # | guarda | o que afirma | mutação que o deixa VERMELHO |
|---|---|---|---|
| **M-A1** | `test_a_porta_nao_vaza_o_fornecedor` | nenhum import de `app.api.infocap_connector` fora de `app/providers/` **e da allowlist de §3.2** (AST, não string); nenhum campo de fornecedor fora da fronteira; 🔴 **menção em PROSA** `\bInfoCap\b` (sensível a caixa) em `core/prompts.py` = **0**, com allowlist escrita do identificador `infocap_policy_lookup` | (a) import do conector dentro de `infocap_tool.py`; (b) **par de controle**: acrescentar `"a InfoCap respondeu"` a uma linha do `CORE_BASE_PROMPT` → vermelho, **e** acrescentar `infocap_policy_lookup` a outra → **continua verde** |
| **M-A2** | `test_toda_linha_tem_origem` | toda `Cobertura`/`Parcela` do golden carrega `origem ∈ {sistema_de_gestao, documento_oficial}`; construir sem origem é `TypeError` | `CampoComOrigem` aceitando `origem=None` |
| **M-A3** | `test_o_contador_de_premio_acende` | Σ prêmios ≠ prêmio líquido → `Sinal("cadastro_incompleto")` com a diferença; **linha de controle:** apólice em que a soma bate → sem sinal | tolerância para `inf` |
| **M-A4** ⚖️ | `test_a_segunda_corretora_nao_ve_a_primeira` — **canônico, não conta no teto**: CLAUDE.md §7 exige "teste automático de isolamento com dois tenants reais" de **todo** contrato novo | duas conexões, dois tenants: nenhuma linha atravessa; o cache do A não serve o B; conexão `archived` nunca é escolhida | chave de cache sem `company_id` |
| **M-B1** | `test_vencida_nunca_vira_opcao` | sobre as 📊 31 linhas mascaradas do acervo: `listar_apolices` devolve 0 vencidas e `historico_oculto` bate com `documents_count`. 🔴 **Caso de 12 apólices com a única vigente na posição 11** → ela é encontrada | (a) filtro de vigência desligado; (b) **`listar_apolices` lendo `policies[:10]`** → o caso de 12 fica vermelho |
| **M-B2** | `test_so_pergunta_com_duas_do_mesmo_ramo` | **par de controle**: 1 auto + 1 resi → não pergunta; 2 auto → pergunta | ramo diferente contado como ambíguo |
| **M-B3** | `test_o_ramo_sai_da_conversa_nao_da_ultima_frase` | frases reais do acervo: CPF puro + "meu carro quebrou" 2 mensagens antes → auto; `chaveiro` com contexto de casa → resi | `_product_hint_from_query(user_query)` restaurado |
| **M-C1** | `test_o_corretor_recebe_a_apolice_nao_a_lista` | corpus das 7 perguntas de 10/09 pelo MOTOR → 7 de 7 em 1 rodada, 0 listagens | `"liste TODAS com os numeros exatos"` de volta em `:468` |
| **M-C2** | `test_a_cobertura_continua_inteira` | golden HDI = **10** linhas; Allianz condomínio = **15**. 🔴 **vermelho em 6 de 10** | **apagar a regra 1b** de `:466` |
| **M-D1** | `test_o_documento_e_lido_sempre_que_a_pergunta_e_de_apolice` | 7 de 7 disparam leitura documental; **linha de controle:** pergunta não-apólice → 0 | gatilho por palavra-chave de volta |
| **M-D2** | `test_a_divergencia_aparece_inteira` | franquia 550 × 600 → as duas na resposta, com origem; forma de pagamento = **cartão** (das parcelas) | `forma_pag` do cabeçalho vencendo |
| **M-E1** | `test_a_pergunta_sobrevive_ao_bloco` | turno do tamanho medido dos dois piores do acervo → responde a pergunta | repetição da pergunta removida |
| **M-E2** | `test_quem_fala_com_o_segurado_tambem_tem_piso` | `piso_de_saida("insured_external", 1200) == 8192`; e o par: um papel que **não** conversa continua sem piso | `insured_external` fora de `PAPEIS_QUE_CONVERSAM` |

⚠️ **Não contam no teto de 12** (e o executor não os usa para ampliá-lo): os 4 guardas de **P-PILOTO-20** (conserto
de harness de guardas que **já existiam**), o varredor de PII sobre `tool_invocations` e o VERIFY da migration —
os dois últimos são **gates de bloco**, não guardas novos de produto. **Se o executor discordar, ele corta um da
lista acima e escreve qual.**

🔴 **A regra que fecha a porta (CLAUDE.md §9.3):** cada mutação roda em **cópia**, em subprocesso, produz **falha
nova nomeada**, e a árvore é restaurada por cópia. **Um guarda que não conseguiu ficar vermelho não é guarda.**

---

## 11. Migrations — APPLY / VERIFY / ROLLBACK escritos ANTES

🔴 **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro antes de escrever a primeira linha de SQL.** O repositório
**não** é a fonte completa do schema: 📊 9 versões aplicadas não têm arquivo e 16 arquivos não têm versão aplicada.
Diretório canônico: `backend/supabase/migrations/`. Proibido sempre: `schema_completo.sql`, `upgrade_v6.2.sql`,
`storage_buckets.sql`.

### 11.1 A única migration certa desta SPEC — dado, não estrutura

**Nome sugerido:** `20260913_01_extra0011_llm_max_tokens.sql` · **expand-first** · **idempotente**.

**MANIFESTO (§5 da autoridade):** esta é migration de **dado**, não de DDL. O manifesto exigido é o **inventário
das 8 linhas afetadas antes e depois**, capturado no APPLY e colado no relatório — não o cruzamento completo do
§5, que vale para alteração de schema. 🔴 **Se o BLOCO 0 achar que o default também precisa mudar, aí há DDL e o
manifesto completo passa a ser obrigatório** — e vira **segunda** migration, nunca um `ALTER` pendurado nesta.

```sql
-- APPLY
-- Registro do estado ANTES (vai para o relatório; nenhuma PII: só role, valor, contagem).
--   SELECT agent_role, llm_max_tokens, count(*) FROM agents GROUP BY 1,2 ORDER BY 1,2;
--   📊 esperado em 13/09/2026: (attendance,2000,3) (attendance,1200,1) (core,1200,3) (core,2000,1)
--   ⚠️ se a contagem de hoje não bater, PARE: alguém mexeu, e o ROLLBACK abaixo está desatualizado.

CREATE TABLE IF NOT EXISTS agents_llm_max_tokens_backup_extra0011 (
    agent_id        uuid PRIMARY KEY,
    company_id      uuid NOT NULL,
    valor_anterior  integer,
    capturado_em    timestamptz NOT NULL DEFAULT now()
);

INSERT INTO agents_llm_max_tokens_backup_extra0011 (agent_id, company_id, valor_anterior)
SELECT id, company_id, llm_max_tokens
FROM   agents
WHERE  agent_role IN ('core','attendance')
  AND  (llm_max_tokens IS NULL OR llm_max_tokens < 8192)
ON CONFLICT (agent_id) DO NOTHING;          -- idempotente: rodar 2× não perde o valor original

UPDATE agents
SET    llm_max_tokens = 8192
WHERE  agent_role IN ('core','attendance')
  AND  (llm_max_tokens IS NULL OR llm_max_tokens < 8192);
```

```sql
-- VERIFY  (roda depois; a saída vai COLADA no relatório)
SELECT agent_role, llm_max_tokens, count(*)
FROM   agents
GROUP  BY 1,2 ORDER BY 1,2;
-- esperado: (attendance, 8192, 4) e (core, 8192, 4). Qualquer linha < 8192 reprova.

SELECT count(*) AS linhas_guardadas FROM agents_llm_max_tokens_backup_extra0011;
-- esperado: 8. Guardadas 0 com UPDATE feito = ROLLBACK impossível → reprova o gate.
```

```sql
-- ROLLBACK  (restaura o valor EXATO de cada agente, não um valor médio)
UPDATE agents a
SET    llm_max_tokens = b.valor_anterior
FROM   agents_llm_max_tokens_backup_extra0011 b
WHERE  a.id = b.agent_id;

-- conferência do rollback:
SELECT a.agent_role, a.llm_max_tokens, count(*)
FROM   agents a JOIN agents_llm_max_tokens_backup_extra0011 b ON b.agent_id = a.id
GROUP  BY 1,2 ORDER BY 1,2;
-- a tabela de backup NÃO é apagada pelo rollback: ela é a prova.
```

⚠️ **O rollback do comportamento é outro:** reverter o código do `llm_factory.py` (piso de 8192, commit
`312939f`) **não** está nesta SPEC e não deve ser feito junto. A migration conserta o dado; o piso continua sendo
a rede.

### 11.2 GATE G-MIG

1. APPLY, VERIFY e ROLLBACK **escritos antes** de rodar qualquer um deles (CLAUDE.md §8).
2. APPLY rodado **duas vezes** → mesmo resultado, e a tabela de backup com os valores **originais**, não 8192.
3. ROLLBACK exercitado em ambiente de teste → os 8 valores voltam **um a um**, conferidos por `agent_id`.
4. `MANIFEST.md` de `backend/supabase/migrations/` atualizado.
5. Nenhuma outra migration nesta SPEC. Se aparecer, **pare e registre** — é sinal de que o escopo escorregou.

---

## 12. Canário controlado em produção

### 12.1 Antes

- Confirmar o SHA implantado de cada serviço (não o health: `CLAUDE.md` §9.1 — health não prova versão).
- Confirmar identidade real da conexão de WhatsApp; **nome de corretora, instância ou label não prova número**.
- Confirmar que as exceções de janela (`05f46a9`) contêm **só** TESTE-A/TESTE-B.
- Provar o bloqueio **com uma saída simulada** antes de liberar qualquer envio vivo.

### 12.2 Os casos (mínimo, e nenhum toca segurado real)

| # | caso | onde | o que prova |
|---|---|---|---|
| 1 | Pergunta por CPF de um cliente com histórico (📊 os que produziram as 31 linhas) | chat `core` da Resulta, conta do Founder | 1 rodada · 0 vencidas · `auto_selected_reason` legível |
| 2 | "Quais as coberturas da apólice residencial dele?" | idem | **10 linhas**, com origem, com a assistência e a divergência de franquia |
| 3 | Cliente sem nenhuma apólice vigente | idem | a frase da §6.2, com data |
| 4 | Cliente com 2 vigentes do mesmo ramo | idem | pergunta **uma vez**, com as duas opções vigentes |
| 5 | Turno grande (documento longo + RAG) | idem | não volta "ainda não recebi uma pergunta sua" |
| 6 | "Meu carro quebrou" e, 2 mensagens depois, só o CPF | WhatsApp, **TESTE-A** | ramo deduzido da conversa, não da última frase; resposta de atendimento, não relatório |
| 7 | Pergunta que **não** é de apólice | chat `core` | **linha de controle**: o documento não é lido |

🔴 **Caso 7 é o que dá direito à conclusão** (CLAUDE.md §9.2). Sem ele, "7 de 7 leram o PDF" pode ser um
`return True`.

### 12.3 Depois

Desligar apenas a habilitação temporária; conferir que não ficou envio futuro nem agente amplamente ligado;
preservar logs **sem PII**; entregar evidências **por alias**. Nenhuma evidência com número, CPF ou nome.

### 12.4 O que só o Founder faz

1. Abrir o chat do painel da Resulta e colar as perguntas dos casos 1–5, 7 (ou autorizar a conta que o faça).
2. Mandar as mensagens do caso 6 do aparelho **TESTE-A**.
3. Se o EasyPanel exigir clique: **implantar** `smith-api` (e `smith-web` se a tela de agentes mudar), na ordem
   que o contrato medido desta SPEC indicar — **não** copiada do histórico da 098.
4. 🧑 Pedir à InfoCap o perfil que libera `/parcelas`, `/comissoes`, `/financeiro` (403 hoje, P-PILOTO-19) —
   **não bloqueia esta SPEC**, destrava `parcelas_em_aberto` de verdade.

---

## 13. Validação com Saionara e Regina

O executor **prepara o roteiro e as telas**; o Founder conduz. O executor **não as contata** nem usa os números
operacionais delas.

O que se valida, em linguagem delas: a resposta veio da apólice certa? veio inteira? dá para ver de onde cada
número saiu? quando ela pergunta "qual apólice?", faz sentido? a frase do "não há vigente" é entendível?

📊 **A Saionara é a dona do caso de referência** (a HDI residencial com 10 coberturas e a Allianz condomínio com
15). O roteiro pede a ela exatamente as perguntas que ela fez nos pilotos — **as perguntas, nunca os dados**.

Registrar: **"não testado" × "aprovado no canário técnico" × "validado pela atendente"**. Não declarar aceite
antes de recebê-lo; não travar o trabalho técnico esperando a agenda delas.

---

## 14. Entrega, implantação e rollback

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR. (CLAUDE.md §2)
git rev-list --count origin/main..HEAD          # 0 = o trabalho está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` e o SHA remoto vão **colados** no relatório. Nunca `git add -A`, nunca force push, nunca
apagar `index.lock` por timeout.

**Serviços a implantar:** `smith-api` (backend: porta, tool, grafo, migration). `smith-web` **só** se a tela de
agentes mudar. **Variáveis de ambiente novas:** 💭 nenhuma prevista — se o executor precisar de uma, ela entra
com **nome e sem valor** no relatório e na caixa do Founder.

Se a SPEC tocar `app/`, `middleware.ts`, `instrumentation.ts`, `next.config.js` ou variáveis de ambiente:
`npm run test:rotas-montam` **e** `next start` + uma requisição real a `/api/…` (CLAUDE.md §9.1). Uma rota que
responde 200 vale mais que um build de 287 rotas.

| marco | evidência exigida |
|---|---|
| Implementado e gateado | commit, gates, mutações vermelhas, parecer do painel |
| Entregue na main | SHA remoto + saída do `push` |
| Implantado | serviço/imagem/SHA + `/health` + **uma requisição que executa código** |
| Validado no canário | os 7 casos, por alias, sem efeito fora do escopo |
| Validado pelas pilotos | feedback real, registrado pelo Founder |

**Rollback:** reverter o código é compatível (a porta é aditiva; os chamadores antigos continuam existindo até o
guarda M-A1 ser ligado). A migration tem ROLLBACK próprio (§11.1) e a tabela de backup **não se apaga**.

---

## 15. Documentação e acompanhamento obrigatórios — um escritor por arquivo

1. `docs/canon/reports/SPEC-EXTRA-001.1-EXECUTION-REPORT.md` pelo template canônico, **abrindo com o EXECUTION
   CARD** (protocolo §0.1: relatório sem card = SPEC aberta) e com a telemetria de 5 linhas.
2. `docs/canon/PENDENCIAS.md`, **por número, com veredito e prova** (protocolo §2):

   | pendência | veredito proposto | por quê |
   |---|---|---|
   | **P-PILOTO-17** (`llm_max_tokens` mente na tela) | **FECHADA** | migration §11.1 + defaults de código + `insured_external` no piso |
   | **P-PILOTO-18** (tool calls do chat) | 🔴 **REESCRITA, depois fechada** — ⚠️ o texto atual está **vencido** (§9.3): `tool_invocations` existe e o chat grava nela desde `nodes.py:1057`. Fechar pelo texto velho teria criado registro duplicado | falta a **ligação com o turno**, o contador do inerte e o registro no `MANIFEST.md` |
   | **P-PILOTO-20** (4 guardas mudos no harness) | **FECHADA** | são os guardas da superfície que esta SPEC mexe |
   | **P-PILOTO-19** (403 em `/parcelas`, `/comissoes`, `/financeiro`) | **CONTINUA** | é 🧑: perfil de API. A operação `parcelas_em_aberto` fica pronta esperando |
   | **P-PILOTO-16** (`attendant` × `member`) | **CONTINUA** | ⚠️ o diagnóstico §5 a encaminha para 001.2/001.1, mas esta SPEC **não a toca**. Registrar, nunca fechar em silêncio |

   Entrada nova obrigatória se o BLOCO 0 confirmar: **`tool_invocations` sem DDL rastreada** (📊 declarado em
   `20260816_02_spec075_portal_job_lineage_priority.sql:147`). O que não couber vira entrada com **o que
   destrava**, **de quem é** e **o que custa esquecer** (CLAUDE.md §11.1).
3. `docs/canon/FOUNDER-DECISIONS.md`: registrar a correção de §0.3 (a porta já existia; o diagnóstico §7.3
   indicava criar diretório novo) como decisão de arquitetura datada.
4. `docs/canon/CHANGE-ADDENDA.md`: tudo que esta SPEC fizer além do texto dela, classificado.
5. `docs/canon/ESTADO-DAS-SPECS.md` e `INDICE-DE-SPECS.md`: a família EXTRA-001.x na fila; **não renumerar**.
6. Dossiê: fonte versionada `docs/canon/reports/dossies/dossies-autobrokers.html`. 📊 As páginas existentes são
   `p-home, p-s088, p-s093b, p-s091, p-s094, p-s0941, p-s095, p-s096, p-s097, p-s0971, p-s098, p-extra001,
   p-pilotos, p-proto, p-fila` — a nova segue a convenção: **`p-extra0011`**, com item de navegação e linha na
   home. 🔴 **Ler o HTML publicado inteiro antes de republicar com `url`**
   (https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868). Sem ferramenta ou acesso: manter a
   fonte atualizada e declarar **"publicação pendente"** com o arquivo e o passo exato. Nunca fingir que atualizou.

---

## 16. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> Cinco referências, todas **fontes primárias**, reabertas em **13/09/2026** pelo redator. O pesquisador do
> executor reabre cada uma na conversão e **registra a data da reabertura** (protocolo §7.3).

### ① Ports & Adapters (Hexagonal Architecture) — Alistair Cockburn
**URL:** https://alistair.cockburn.us/hexagonal-architecture/ · reaberta 13/09/2026
**O que faz:** define a intenção — *"Allow an application to equally be driven by users, programs, automated test
or batch scripts, and to be developed and tested in isolation from its eventual run-time devices and databases."*
Uma **porta** é um canal de conversa com propósito, cujo protocolo toma a forma de uma API; um **adaptador**
converte a definição da API para os sinais de cada dispositivo externo.
**O que MODELAMOS (um ponto):** a frase que vira teste — *"The application has a semantically sound interaction
with the adapters on all sides of it, **without actually knowing the nature of the things on the other side**."*
É exatamente o guarda **M-A1**: nada fora de `app/providers/` sabe que existe InfoCap.
**O que REJEITAMOS:** o desenho canônico do hexágono com camadas e diretórios novos. 🔴 O padrão é sobre
**dependência**, não sobre pastas — e criar `backend/app/services/policy_provider/` ao lado da porta que já existe
seria motor paralelo (CLAUDE.md §5).
**Como o juiz inspeciona:** abre a página, lê a definição de porta, e **roda** `M-A1` sobre a árvore.

### ② Anti-Corruption Layer — Microsoft Azure Architecture Center (padrão de Eric Evans, DDD)
**URL:** https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer · reaberta 13/09/2026
**O que faz:** *"When you maintain access between new and legacy systems, you force the new system to adhere to at
least some of the legacy system's APIs or other semantics. When these legacy features have quality problems, this
support **corrupts** what might otherwise be a cleanly designed modern application."* A solução é uma camada que
**traduz**, e cujo lado interno usa sempre o modelo do subsistema novo.
**O que MODELAMOS (um ponto):** *"Communication between subsystem A and the anti-corruption layer always uses the
data model and architecture of subsystem A."* Traduzido para esta SPEC: **a porta devolve `Apolice`, nunca o
`Dict[str, Any]` da InfoCap** — que é precisamente o que ela devolve hoje (`policy_data_provider.py:46-52`), e por
isso `preliq` e `sit_renovacao_txt` vazaram para o resto do sistema.
**O que REJEITAMOS:** implementar a camada como **serviço** separado (API Management + Functions, no exemplo da
página). Aqui ela é um **componente dentro da aplicação** — a própria página autoriza as duas formas, e a nossa
latência é a do chat. Rejeitamos também colocar regra de negócio na camada: a página avisa —
*"focus the anti-corruption layer on translation logic. Avoid placing business rules or orchestration in the layer."*
⚠️ Por isso `reconciliar` é **política da porta**, e não do adaptador: a escolha "PDF vence em cobertura" é decisão
do Founder (D-PILOTO-11), não tradução.
**Como o juiz inspeciona:** abre a seção "Problems and considerations" e confere os dois itens que a página manda
tratar e que esta SPEC trata: **validação/sanitização na fronteira** (o redator de PII, §9.3) e **observabilidade
com correlation ID** (a `Provenance` que a SPEC-094 já grava).

### ③ PEP 544 — Protocols: Structural subtyping (static duck typing)
**URL:** https://peps.python.org/pep-0544/ · reaberta 13/09/2026
**O que faz:** *"A concrete type X is a subtype of protocol P if and only if X implements all protocol members of
P with compatible types. In other words, subtyping with respect to a protocol is always structural."* Não exige
herança explícita. `@runtime_checkable` é opt-in, e a própria PEP explica por quê: *"Protocol checks are not type
safe in case of dynamically set attributes."*
**O que MODELAMOS (um ponto):** o adaptador novo (Agger, Quiver, PdfOnly) **não herda de nada** — basta ter as
operações. É o que permite à SPEC-101 admitir provider sem tocar em quem consome.
**O que REJEITAMOS:** confiar na verificação em tempo de execução. 🔴 A PEP diz que protocolos são
**fundamentalmente estáticos** e que `@runtime_checkable` *"não é type safe no caso de atributos definidos
dinamicamente"*. ⚠️ 📊 A porta da SPEC-094 **é** `@runtime_checkable` — e por isso o teste dela **não** usa
`isinstance` como prova: usa asserção estrutural e comportamento. A 001.1 segue o mesmo: o Gate A roda o
**verificador de tipos**.
**Como o juiz inspeciona:** remove uma operação de um adaptador e confere que o verificador de tipos **reprova**,
e que um `isinstance` **não** teria reprovado.

### ④ PROV-O: The PROV Ontology — W3C Recommendation, 30/04/2013
**URL:** https://www.w3.org/TR/prov-o/ · reaberta 13/09/2026
**O que faz:** modelo de proveniência com três classes de partida — **Entity**, **Activity**, **Agent** — e as
relações `wasGeneratedBy` (*"Generation is the completion of production of a new entity by an activity"*),
`wasDerivedFrom` (*"a transformation of an entity into another"*) e `wasAttributedTo` (*"the ascribing of an
entity to an agent"*).
**O que MODELAMOS (um ponto):** proveniência é **do dado**, não do log. Cada `CampoComOrigem` carrega de onde veio
e por qual leitura — é `wasDerivedFrom` aplicado a uma linha de cobertura. É o que permite escrever
"franquia R$ 600 (documento oficial, p. 4) · o sistema de gestão diz R$ 550" sem inventar nem esconder.
**O que REJEITAMOS:** adotar RDF, OWL, a ontologia inteira ou um grafo de proveniência. Modela-se **a ideia**:
três campos (`origem`, `confianca`, `detalhe`), no dataclass, congelado.
**Como o juiz inspeciona:** pega 3 linhas ao acaso do golden e pergunta, para cada uma: de onde veio, com que
confiança, e o que diz a outra fonte. Uma sem resposta reprova a amostra (protocolo §0.4).

### ⑤ Lost in the Middle: How Language Models Use Long Contexts — Liu et al., TACL 2023
**URL:** https://arxiv.org/abs/2307.03172 · reaberta 13/09/2026
**O que faz:** mede o uso de contexto longo em QA multi-documento e recuperação chave-valor. *"Performance is
often highest when relevant information occurs at the beginning or end of the input context, and significantly
degrades when models must access relevant information in the middle of long contexts, **even for explicitly
long-context models**."*
**O que MODELAMOS (um ponto):** a pergunta do usuário é **repetida depois** do bloco de contexto recuperado
(§9.1). É a explicação medida dos dois turnos que responderam *"ainda não recebi uma pergunta sua"* — 120 e 128
chunks, com a pergunta no meio.
**O que REJEITAMOS:** concluir que "contexto grande é ruim" e cortar o RAG. O paper mede **posição**, não volume;
cortar recuperação para resolver posição trocaria um defeito por outro, e o bloco de cobertura item a item
(`bf963b0`) é justamente o que precisa caber.
**Como o juiz inspeciona:** abre o abstract, confere a afirmação sobre posição, e roda **M-E1** com a pergunta
antes e depois do bloco — o par de controle é a mesma pergunta nas duas posições.

⛔ **Referência externa nunca vira autoridade** (protocolo §7.3): Smith, Work OS, Tool Gateway, Skill Registry e
Artifact Hub continuam únicos. Modela-se o **padrão**.

---

## 17. O que sai desta SPEC e quando volta

| frente | por que sai | gatilho de retorno |
|---|---|---|
| `insurer_assistance_plans` e os três níveis de assistência | é a 001.5 inteira; pendura na chave que a 001.1 consolida | EXTRA-001.5, trilho paralelo, assim que o Bloco A fechar |
| fábrica de conectores, admissão de provider, UI de conexão | é a SPEC-101, que **vira a porta** (D-PILOTO-16) | SPEC-101 |
| adaptadores Agger / Quiver / Segfy | sem credencial medida | EXTRA-002 / 008 / 009, como adaptadores da 101 |
| rajadas, debounce, uma resposta por conversa | é a 001.2; mesmo arquivo, dois escritores | EXTRA-001.2 |
| `/parcelas`, `/comissoes`, `/financeiro` | 📊 403 hoje (P-PILOTO-19); é perfil de API, não código | 🧑 Founder pede o perfil; a operação já existe esperando |
| ligação apólice → condições gerais por processo SUSEP | o elo casa hoje, mas o consumidor é a 001.5 | EXTRA-001.5, onda 2 |
| papel `attendant` × `member` (P-PILOTO-16) | é decisão 🧑, não código desta superfície | 🧑 Founder decide; execução em 001.2 ou 001.9 |

---

## 18. A fila depois desta entrega — contexto, não autorização

Ordem canônica (diagnóstico §12.1, D-PILOTO-08):

```
001.0 retroativa  →  001.6-P0 cobrança  →  ★ 001.1 (esta)  →  001.2 lê tudo antes de falar
→  001.3 grupo ∥ 001.4 corredor  →  001.6 cobrança completa  →  001.7 piloto medido
→  001.10 vidros  ∥  001.5 base de produtos  →  001.8 isolamento  →  001.9 rotas
```

**O que a 001.1 deixa pronto para quem vem depois:**

- para a **001.5**: a chave canônica `seguradora + ramo + produto`, o `PlanoDeAssistencia` com estado
  `nao_sabemos_ainda`, e a operação `detalhar_apolice` que já traz o nome do plano de `tabela_itens`.
- para a **SPEC-101**: o `Protocol` completo, `capacidades()`, dois adaptadores provando que o contrato aceita
  fornecedores de naturezas diferentes, e a lista escrita do que falta (admissão, censo, UI).
- para a **001.2**: a resposta já vem de uma apólice só — o que torna "uma resposta por rajada" um problema de
  buffer, e não de conteúdo.
- para a **001.3**: `auto_selected_reason` e `historico_oculto` dão ao dossiê a frase de por que aquela apólice.

---

## 19. Definição final de conclusão — lista fechada, verificável

A SPEC está concluída quando **todas** as linhas abaixo forem verdadeiras, cada uma com evidência no relatório:

1. A porta `PolicyDataProvider` tem as **cinco operações** e `capacidades()`, com modelo canônico próprio, e
   **nenhum diretório novo** foi criado ao lado dela.
2. **Dois adaptadores** satisfazem o contrato pelo verificador de tipos; o `PdfOnlyProvider` monta uma `Apolice`
   completa só do documento.
3. `reconciliar` é puro, casa por rótulo normalizado, **mostra as duas** quando diverge, e o contador de prêmio
   acende na HDI e **não** acende na apólice de controle.
4. 📊 `grep` da fronteira → **0** fora de `app/providers/` e da allowlist de §3.2 (com motivo por linha);
   e `\bInfoCap\b` em prosa no `core/prompts.py` → **0**, com o identificador `infocap_policy_lookup` na
   allowlist escrita.
5. Golden **HDI = 10 coberturas** e **Allianz condomínio = 15**, montados **pela porta**, com origem por linha,
   sem uma única PII no arquivo.
6. Corpus das **7 perguntas reais de 10/09** → **7 de 7 em 1 rodada**, **0 vencidas listadas**, pelo MOTOR.
7. A **linha de controle** existe e funciona: pergunta não-apólice **não** lê documento; 1 auto + 1 resi **não**
   pergunta; 2 auto **pergunta**.
8. Os **12 guardas** existem e cada um ficou **vermelho** na sua mutação, em cópia, em subprocesso, com falha
   nova nomeada.
9. Os **4 guardas de P-PILOTO-20** voltaram a rodar.
10. Migration aplicada, VERIFY colado (**8 de 8 em 8192**), ROLLBACK exercitado, `MANIFEST.md` atualizado, e os
    **quatro defaults de 2000** (📊 `agents`, `companies`, `agent_config.py:133`, `models/agent.py:19`) tratados
    ou registrados com número.
11. `piso_de_saida("insured_external", 1200)` devolve **8192** — o segurado deixa de ter resposta cortada.
12. A chamada de ferramenta do turno é **auditável por junção**, sem segundo registro, **sem PII**, e o varredor
    não acha nada.
13. Turno do tamanho medido dos dois piores do acervo **responde a pergunta**.
14. Canário: os **7 casos** rodados, só com TESTE-A/TESTE-B e a conta do Founder, evidências por alias.
15. `git push` feito, saída colada, SHA remoto conferido, serviço implantado e **uma requisição que executa
    código** respondida.
16. Relatório com **EXECUTION CARD**, FATO/INFERÊNCIA/RECOMENDAÇÃO separados, 📊/💭 em todo número, pendências
    drenadas por número, dossiê publicado ou **publicação pendente** declarada com o passo exato.
17. **Declaração explícita de que nenhum motor paralelo foi criado** — nominalmente: nenhuma segunda porta de
    apólice, nenhum segundo catálogo de seguradoras, nenhum segundo caminho de leitura documental.

🔴 **E a pergunta que o resumo ao Founder responde em linguagem simples:** *quando eu perguntar pela apólice de um
cliente, eu recebo a apólice certa, inteira, de uma vez — e consigo ver de onde veio cada número?*
