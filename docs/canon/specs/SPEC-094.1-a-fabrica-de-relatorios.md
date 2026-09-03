# SPEC-094.1 · A FÁBRICA DE RELATÓRIOS — o chat propõe a métrica que não existe, um humano promove, e todo relatório novo é uma definição, não um deploy

> **O que ela entrega:** (1) o **protocolo escrito** de como nasce um relatório, um cálculo, um cruzamento
> ou um conector novo no AutoBrokers — para qualquer chat executar em minutos, com guarda; (2) o chat
> principal **enxerga o que já entregou** (126 artifacts que ninguém lê) e **propõe** métrica nova quando
> o corretor pede algo que não existe — a proposta vira Work Run com Approval, nunca número na tela;
> (3) **cinco relatórios da lista obrigatória** que a InfoCap já expõe e ninguém lê: sinistros da
> carteira, funil de cotações, cancelamentos, cross-sell por cliente, pendência de emissão; (4) o
> **primeiro cruzamento com dado externo** que só o AutoBrokers faz: sinistralidade do mercado (SUSEP
> SES) × a carteira da corretora, por ramo e seguradora — o exemplo que o Founder deu.
>
> **v1 · 03/09/2026 · protocolo v11.2** · nasce da SPEC-094 executada + pedido do Founder de 03/09 +
> 3 pesquisas: `docs/canon/pesquisa/{RELATORIOS-QUE-VALEM-DINHEIRO, CORPAPI-CATALOGO-OFICIAL, COMO-NASCE-UM-RELATORIO-HOJE}.md`
> Número: **094.1** — é a continuação direta da 094 (precedente 084 · 084.1 · 084.2). Executa DEPOIS da 094 fechar.
> ⛔ Não substitui as propostas 095/096: elas continuam na fila com o próprio número.

---

## 0. O TESTE DO PRODUTO

> **Segunda-feira, o dono da Resulta pergunta "quantos sinistros abertos temos por seguradora, e a
> Porto está sinistrando mais que o mercado?". O chat responde com dois números com ponteiro
> [claims.open_count@1 · 30 dias] [claims.loss_ratio_vs_market@1 · SES 07/2026 · ramo auto], e o
> Artifact "Pulso 360" ganha a seção de sinistros. Terça, ele pergunta "qual a comissão média por
> produtor só nas apólices de frota?". Não existe. O chat diz: "não tenho essa métrica registrada;
> proponho `commission.avg_per_producer_by_segment` sobre comissão apropriada × produtor × ramo — quer
> que eu registre a proposta para revisão?" Ele diz sim; nasce um Work Run `metric.proposal` com
> Approval. Quarta, um chat com o Claude Code abre o protocolo COMO-NASCE-UM-RELATORIO.md, adiciona
> a definição em 15 minutos, o guarda fica verde, o deploy sai e a proposta vira `promovida`. Quinta,
> o dono pergunta "o que você já me entregou este mês?" e o chat lista os 6 Artifacts com link.
> Nenhum número inventado apareceu na tela em nenhum dos quatro dias.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ O chat **NUNCA** calcula uma métrica não registrada nem publica Artifact com ela. Propor é o teto.

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 03/09/2026 (as três pesquisas, com os comandos nelas)

### 1.1 · Um relatório novo hoje são 7 passos, 5 arquivos e um deploy — fora de qualquer registry
📊 `COMO-NASCE-UM-RELATORIO-HOJE.md`: cálculo em `calculos.py` → `Template` no `CATALOGO`
(`templates.py:785`) + pista léxica em `escolher():798` → seed → tool em `agents/tools/` → uma linha em
`graph.py:~562` dentro do `if` de papel `core` → guarda → `git push`. **Nada passa por Skill, Tool
Gateway ou Registry.** 📊 Skill Registry: 20 skills, 21 releases, 26 bindings, **0 turnos governados**.
Tool Gateway: `tool_gateway_shadow_diffs` **155 linhas, todas `identico=false`**, `TOOL_GATEWAY_MODE=off`.
Quem governa de verdade é a **Capability**: 38 caps, 61 bindings, 114 entitlements, 129 `tool_invocations`
gravadas por `capability_key`.

### 1.2 · O chat não cria cálculo, não propõe e não lembra
📊 `grep -rn "exec(|eval(|python_tool|code_interpreter|sandbox|text_to_sql" backend/app` → 0 ocorrências
reais. 📊 `auxiliary_requests = 0` e `capability_gaps = 0`: os dois motores de "propor o que falta" existem
em código (`factory_tool.py:45`) e **nunca escreveram uma linha**. 📊 `grep -rn 'table("artifacts")'
backend/app/agents/` → **0**: o chat publicou 126 Artifacts em 3 corretoras e não consegue listar um.
`gerar_relatorio` (`report_tool.py:196`, LLM compõe o conteúdo) **nunca produziu artifact**; só as duas
tools da 081 produziram (14 + 14).

### 1.3 · A 094 cobre 8 dos 16 relatórios obrigatórios; os que faltam já têm rota
📊 `RELATORIOS-QUE-VALEM-DINHEIRO.md` §A cruza os catálogos públicos de Quiver PRO, Agger (manual de
208 páginas) e Segfy (49 artigos): **11 relatórios aparecem nos três**. A 094 entrega A1 A2 A4 A5 A6 A7
A8 A11. Faltam, com rota 200 medida no censo ou documentada: **A15 sinistros** (`/sinistros`, 5.729
registros, 7 parâmetros na doc), **A16 funil** (`/negocios_andamento`, `/em_calculo`,
`/negocios_finalizados` — na doc, nunca medidas), **A10 cancelamentos** (`cancelado=T` não medido),
**A12 cross-sell** (`/cliente_ligacoes`), **A14 pendência de emissão** (`sit_acompanhamento_txt` já vem no
`/documento`). 🔴 **A3 comissão recebida e A9 inadimplência — as duas de maior nota (94 e 88) — NÃO vêm da
CorpAPI em lote** (só `/documento.parcelas[]`, 💭 ≈23 min para 1.680 apólices): vêm do **portal da
seguradora** (`portals`: 17 ativos, `portal_worker` baixa "boleto, apólice, comissão"). Ficam para a 094.2.

### 1.4 · A CorpAPI oficial tem 51 requests, 22 de escrita, e 3 rotas 200 que a doc não lista
📊 `CORPAPI-CATALOGO-OFICIAL.md` (export do documenter, 66.660 bytes, 14/03/2025): 36 rotas + 1 S3 ·
29 GET · 12 POST · 6 DELETE · 3 PUT · 1 PATCH · **1 descrição em 51 · 0 campos obrigatórios · 0 respostas
de escrita**. 🔴 `/producao` devolve 500 porque é chamada com `datini/datfim`; a doc exige `dt_ini/dt_fim`
(P-094-PRODUCAO-500). `/documentos` é lista paginada por `periodo=datinc` — a base temporal de apropriação
que a 094 não tinha. Escrita (F-094-09): 5 portas, nenhuma medida — **fora desta SPEC**.

### 1.5 · As fontes externas existem, medidas hoje, sem login
📊 **SUSEP SES** `BaseCompleta.zip` → 200 · 545 MB · Last-Modified 31/08/2026 · semanal · CSV
(sinistralidade por empresa + mês + ramo). 📊 **ANS** `dadosabertos.ans.gov.br/FTP/PDA/` → 200 · 53
diretórios (`valor_comercial_medio_por_municipio_NTRP-054`). 📊 **BACEN SGS** séries 433/4189 → 200.
📊 **Opin Directory** → 200 · 38 participantes · 2 corretoras · 10 das 15 seguradoras de `portals`.
❌ Senatran 403 · SINESP DNS · dados.gov.br 401 · Receita CNPJ recusa — **não entram**.
🔴 📊 `infocap.com.br` → 301 → `agger.com.br` (ONE = Quiver + Agger): o fornecedor da API é a casa dos
dois maiores concorrentes (F-094-08). A fórmula nunca conhecer provider deixou de ser elegância.

### 1.6 · O estado da arte não deixa o LLM criar métrica persistente — em nenhum dos cinco
📊 `RELATORIOS-QUE-VALEM-DINHEIRO.md` §E: dbt Semantic Layer + MCP, Cube MCP, Snowflake Cortex Analyst,
Databricks Genie, Looker — **a saída do LLM é sempre um OBJETO DE CONSULTA, nunca uma definição**. Cube
"deliberately exposes no commit tool"; Euno: propor → revisar duplicata → promover. 📊 BIRD: melhor
sistema 82,28% × humano 92,96% → **1 resposta em 5 errada**, e pelo CLAUDE.md §9.5 a errada é a silenciosa.
Nota da pesquisa: (b) propor → humano promove **92** · (c) só registradas 74 · (a) criar na hora **18**.

### 1.7 · O que já está pronto para esta SPEC usar (da 094, medido no gate dela)
Registry de métricas com `time_basis` · CBIM · adapter InfoCap sobre `_resolve_infocap_connection` ·
manifesto de capacidade · Evidence Pack único chat+Artifact · tool `executive_intelligence` com query
plan · template `executive.pulse360` · Work OS com `work_runs` + `approvals` (SPEC-055, HITL) ·
`ArtifactService` · `SignalService`/`EvidenceService`. **Esta SPEC não cria motor: cria definições,
um workflow de proposta, uma tool de leitura e um conector público.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado, corretor ou seguradora. O chat só responde a quem perguntou.
⛔ InfoCap SOMENTE LEITURA. As 5 portas de escrita (F-094-09) ficam FORA — nem em flag desligada.
⛔ Nenhuma chamada a Quiver/Segfy/Agger. Nenhum adapter sem acesso medido.
⛔ Fontes externas: só as medidas em 1.5 com 200 e sem login (SES, ANS, BACEN). Download em lote, no MinIO, por
   uma Rotina existente (tick.py), nunca no caminho quente do chat. Nenhuma fonte paga nesta SPEC.
⛔ Métrica PROPOSTA nunca aparece como número. A proposta é um Work Run `metric.proposal` com Approval; o chat só
   devolve o texto da proposta e o id. Não existe tool de "promover" para o modelo (Cube: remover a capacidade).
⛔ Sem sandbox, sem exec, sem SQL gerado. Um cálculo novo é uma DEFINIÇÃO no registry, escrita por gente, com guarda.
⛔ ZERO migration de estrutura. Escritas: work_runs/work_events/approvals (escritores existentes), artifacts,
   intelligence_signals. Uma migration de SEED só se o template mudar (como na 094).
⛔ Nenhum motor paralelo: nem segundo catálogo de templates, nem segundo caminho de publicação, nem segundo registro
   de tool, nem segundo motor de regra, nem segunda camada de cálculo, nem "fábrica" ao lado de services/skills/.
⛔ NUNCA nome de pessoa, CPF, apólice, placa em log, teste, fixture, censo, relatório. Nunca `git add -A`.
⛔ A conta compartilhada (F-094-07) continua: Amandus recusada até a decisão.
```

## 2.1 O EXECUTION CARD da conversão — o executor confere e discorda com número

```
SPEC .................  094.1 · A fábrica de relatórios
RISCO ................  6  — número executivo lido pelo dono (herdado da 094) + primeira fonte EXTERNA no dado + workflow com
                            Approval; nada envia; nada escreve na InfoCap
SUPERFÍCIE ...........  3  — comercial/metricas (definições) · providers (adapter: 5 rotas novas; conector SES) · agents/tools
                            (1 tool de leitura + proposta) · services/work (workflow) · artifacts (template) · docs/canon (protocolo)
NÍVEL ................  CRÍTICO sob v11.2 — desenhista antes · painel de 3 lentes (verdade/ELO · DADO · regressão+tenant) · red team ·
                            um juiz fresco confirma + audita · integrador
UNIDADES .............  7   BLOCO 0 (as 6 chamadas) · A (5 relatórios obrigatórios) · B (SES: conector público + 2 métricas) ·
                            C (o chat lembra: listar_entregas) · D (proposta com Approval) · E (o PROTOCOLO escrito + guarda) · F (canário)
COESÃO ...............  A e B tocam metricas/ e o adapter: seriais (A → B). C, D, E independentes entre si e de A/B. F no fim
PARALELISMO REAL .....  3 escritores (A→B ‖ C+D ‖ E)
O ELO ................  pergunta "sinistros por seguradora × mercado" → adapter lê /sinistros + SES do MinIO → duas métricas do
                        registry → mesmo Evidence Pack no chat e no Artifact → E a pergunta sem métrica devolve PROPOSTA (Work Run
                        com Approval) e ZERO número → um chat com o protocolo promove em minutos e o guarda prova
GATE ZERO ............  (i) grep 'table("artifacts")' em agents/ → 0 (VERMELHO) · (ii) pergunta sem métrica hoje devolve prosa/erro,
                        não proposta (VERMELHO) · (iii) /sinistros sem leitor (VERMELHO) · (iv) SES não existe no MinIO (VERMELHO)
FAIXA DE RELÓGIO .....  10–14h do primeiro despacho ao push
ORÇAMENTO ............  ≤ 2,5 M tokens de subagentes (v11.2)
BATERIA ..............  suíte inteira no gate do B e no fim (2×); scripts comerciais + guarda da 094 + guarda novo a cada bloco
```

---

## 3. 🌐 O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS — §7.3, reaberto em 03/09/2026

### ① Cube — MCP server sem ferramenta de commit
```
URL ................. https://cube.dev/docs/product/apis-integrations/mcp-api
O QUE FAZ ........... o modelo consulta o modelo semântico e rascunha; "deliberately exposes no commit tool" — só gente publica
MODELAMOS ........... BLOCO D: a tool `propor_metrica` cria Work Run + Approval; NÃO existe tool `promover`. Remover a capacidade,
                      não pedir contenção
REJEITAMOS .......... Cube como runtime; rascunho de SQL pelo modelo
COMO O JUIZ INSPECIONA grep de tools registradas para `core`: nenhuma escreve em comercial/metricas/ nem em templates.py;
                      mutação: acrescentar uma tool que grava definição → o guarda fica vermelho
```
### ② Euno — propor → revisar duplicata → promover
```
URL ................. https://www.euno.ai/  (doc do fluxo "shift-left proposals"; índice citado na pesquisa, página 404 em 03/09)
O QUE FAZ ........... proposta de métrica é revisada contra o catálogo ANTES de existir; duplicata é o modo de falha real
MODELAMOS ........... BLOCO D: a proposta carrega `parecida_com=[metric_ids]` calculado por similaridade de fatos+dimensões; três
                      "comissão do mês" divergentes destroem mais confiança que uma métrica faltando
REJEITAMOS .......... produto SaaS; revisão por LLM como autoridade final
COMO O JUIZ INSPECIONA propõe "comissão apropriada por ramo" (já existe como mix.branch) e confere que a proposta aponta a duplicata
```
### ③ Databricks Genie — o selo "Trusted" viaja com a resposta
```
URL ................. https://docs.databricks.com/aws/en/genie/trusted-assets
O QUE FAZ ........... resposta de asset verificado carrega badge; a não verificada, outra cara
MODELAMOS ........... o bloco <<PACK>> da 094 ganha `origem: registry|proposta`; o Artifact escreve "registrada" ou "proposta em
                      revisão" ao lado; proposta NUNCA tem `value`
REJEITAMOS .......... Genie como runtime
COMO O JUIZ INSPECIONA muta a tool para devolver `value` numa proposta → guarda vermelho (M-PROPOSTA)
```
### ④ Snowflake Cortex Analyst — Verified Query Repository e régua com regressão
```
URL ................. https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository
O QUE FAZ ........... perguntas verificadas por gente melhoram a precisão (📊 +20 p.p. em teste controlado); régua detecta regressão
MODELAMOS ........... BLOCO E: o protocolo exige, para toda métrica nova, UMA pergunta de exemplo + o número esperado numa fixture
                      (golden) — a régua de "o que respondia certo e passou a falhar"
REJEITAMOS .......... geração de SQL
COMO O JUIZ INSPECIONA remove a pergunta verificada de uma métrica e confere que o guarda do protocolo reprova a definição
```
### ⑤ SUSEP SES — a estatística oficial do mercado, semanal, sem login
```
URL ................. https://www2.susep.gov.br/download/estatisticas/BaseCompleta.zip
O QUE FAZ ........... prêmios, sinistros e sinistralidade por seguradora (coenti), mês (damesano) e ramo; 📊 545 MB, 31/08/2026
MODELAMOS ........... BLOCO B: Rotina baixa o ZIP semanal para o MinIO, extrai SÓ Ses_cias.csv + tabelas de código, grava
                      MarketFact(coenti, damesano, ramo, premio, sinistro) em Parquet/CSV no MinIO; o adapter `susep_ses` devolve
                      MarketFact ao registry; métricas claims.loss_ratio_vs_market@1 e market.loss_ratio_trend@1
REJEITAMOS .......... ler 545 MB no caminho quente; warehouse; mapear seguradora→coenti por nome sem tabela (usa a tabela de
                      códigos do próprio SES + um mapa versionado por seguradora do repo)
COMO O JUIZ INSPECIONA pega uma seguradora e um mês, recalcula sinistralidade do CSV à mão e compara com a métrica (lente do DADO)
```
### ⑥ dbt Semantic Layer + MCP — definição vive uma vez, o modelo só parametriza
```
URL ................. https://docs.getdbt.com/docs/dbt-ai/about-mcp
O QUE FAZ ........... o modelo lista métricas e dimensões e pede o cálculo por parâmetros; não escreve a fórmula
MODELAMOS ........... a tool `executive_intelligence` (094) ganha `listar_metricas` no query plan: o modelo descobre o que existe
                      ANTES de propor; é o que evita a proposta duplicada
REJEITAMOS .......... instalar dbt
COMO O JUIZ INSPECIONA pergunta ao chat "que métricas você tem?" e confere que a lista bate com registry.listar()
```

---

# BLOCO 0 · REMEDIR + as 6 chamadas que decidem o tamanho dos blocos

Remedir os 📊 da §1 pelo comando. E as **6 chamadas GET** que a pesquisa pediu (💭 < 1 min), pela conexão
da Resulta, com prudência do censo: `/producao` com `dt_ini/dt_fim` (conserta P-094-PRODUCAO-500 ou o
fecha como "500 mesmo certo") · `/documentos?periodo=datinc` (base de apropriação: existe?) · `/sinistros`
com janela de 90 dias e `tipo_data` (quantos, quais campos) · `/negocios_andamento` (funil existe?) ·
`/produtores` · `/documentos_bi?tipo_doc=TODOS` (quanto some no recorte `A`). Cada uma vira linha no
manifesto (`infocap-capability-manifest.json`) e no dicionário. **Gate 0:** manifesto atualizado; nenhuma
PII; e o SES baixado UMA vez para o MinIO com `sha256` e `Last-Modified` registrados (📊, não 💭).

# BLOCO A · Cinco relatórios obrigatórios que já têm rota — como DEFINIÇÕES, não como tools

Adapter InfoCap ganha `claims(period)` (`/sinistros` → `ClaimFact(policy_ref, claim_ref, status, occurred_at,
reported_at, closed_at, indemnity: Money|UNAVAILABLE, deductible)`), `quotes(period)` (funil → `QuoteFact`, só se
o BLOCO 0 provar), `cancellations` (`cancelado=T` → `PolicyFact.status`), `customer_links` (`/cliente_ligacoes` →
`CustomerPortfolioFact(customer_ref, policy_refs, branches)`), `issuance_status` (`sit_acompanhamento`).
Métricas novas no registry (uma definição por arquivo, com pergunta verificada + golden na fixture):
`claims.open_count@1` · `claims.indemnity_paid@1` · `claims.by_insurer@1` · `quotes.funnel@1` (condicional) ·
`quotes.lost_reasons@1` (condicional) · `portfolio.cancellation_rate@1` · `customer.single_product_share@1`
(cross-sell: clientes com 1 produto ÷ total, com os ramos ausentes mais comuns) · `issuance.pending@1`.
O Pulso 360 ganha as seções **Sinistros**, **Funil** (se houver), **Carteira por cliente**, **Pendências**.
**Gate A:** cada métrica com golden sintético + pergunta verificada; M1 (provider na fórmula) vermelho;
`customer_ref` é hash — nenhum CPF no pack (M16); paridade adapter × provider de referência (M17).

# BLOCO B · O primeiro cruzamento externo — SUSEP SES × a carteira

Conector público `backend/app/providers/susep_ses_provider.py` (mesmo port de dados analíticos, `provider_key='susep_ses'`,
sem credencial): uma Rotina existente (`tick.py`, cadência semanal) baixa `BaseCompleta.zip` para o MinIO, extrai
`Ses_cias.csv` + códigos, grava `MarketFact` particionado por ano em CSV no MinIO. Mapa versionado
`docs/canon/providers/susep/seguradora-coenti.json` (nome canônico da seguradora da InfoCap → `coenti` do SES; o que
não mapeia sai `UNKNOWN`, nunca omitido). Métricas: `market.loss_ratio@1` (por coenti × ramo × mês, do SES) ·
`claims.loss_ratio_portfolio@1` (indenizações pagas ÷ prêmio, da carteira; `coverage` = fração da carteira com
sinistro instrumentado) · `claims.loss_ratio_vs_market@1` (DERIVED, mesma seguradora e ramo, mesmo período; UNAVAILABLE
onde o mapa não casa) · `market.loss_ratio_trend@1` (3 trimestres, sinal ▲▼). Seção **Mercado** no Pulso 360:
*"a seguradora X subiu a sinistralidade de Y por 3 trimestres — negocie antes da carta de reajuste"*, com o ponteiro.
**Gate B:** lente do DADO recalcula uma célula do CSV à mão; mutação "ler o ZIP no caminho quente" vermelha (o adapter
só lê o MinIO); mapa sem uma seguradora → UNAVAILABLE, não zero (M2); **suíte inteira**.

# BLOCO C · O chat lembra o que entregou — `listar_entregas`

Tool de leitura sobre `artifacts` (filtro `company_id` obrigatório): lista, filtra por período/template, devolve
título, data, link, `pack_id`, métricas do pack. Entra na lista de tools `core` dentro do `if` de `graph.py:528`.
**Gate C:** duas corretoras → só as próprias (mutação sem `company_id` vermelha); a resposta não traz payload cru.

# BLOCO D · A proposta — Work Run `metric.proposal` com Approval, e nenhuma tool de promover

`executive_intelligence` ganha no query plan `listar_metricas` (ref ⑥) e, quando `views` pede algo que não existe,
devolve **proposta**: `{nome_sugerido, fatos, dimensoes, time_basis, parecida_com:[...], pergunta_exemplo}` — sem
`value`. Tool `propor_metrica` cria `work_runs` (`workflow_key='metric.proposal'`, `source_type='chat'`, `risk_level`
baixo) via `criar_registro_sem_fila` da 093-B + `approvals` (SPEC-055) para o dono da corretora **ou** o Founder
(configurável por corretora, default Founder no piloto); `work_events` `metric.proposta_criada`. Estados:
`proposta → aprovada → promovida (commit do humano com o metric_id) | recusada`. A promoção é **fora do produto**:
o humano segue o protocolo do BLOCO E; o guarda [D] confere que, para toda proposta `promovida`, o `metric_id`
existe em `registry.listar()`. No pack, `origem: registry|proposta` (ref ③); o Artifact escreve "proposta em
revisão", sem número.
**Gate D:** M-PROPOSTA (devolver `value` numa proposta) vermelho; duplicata apontada (ref ②); não existe tool que
escreva em `metricas/` (grep + mutação); Approval criado com `company_id`; dois tenants não veem propostas um do outro.

# BLOCO E · O PROTOCOLO — `docs/canon/COMO-NASCE-UM-RELATORIO.md` + guarda que o reprova

O documento que o Founder pediu, ≤ 12 KB, para QUALQUER chat seguir:
```
1  CLASSIFIQUE  é MÉTRICA (definição no registry) · SEÇÃO do Pulso (view) · FONTE (adapter/conector) · ENTREGA (template/canal)?
                um relatório novo quase sempre é 1 métrica + 1 seção. Não é tool, não é skill, não é auxiliar.
2  MEÇA         a fonte existe? (manifesto) · o fato canônico existe? (CBIM) · a pergunta já tem métrica parecida? (listar_metricas)
3  DEFINA       metricas/<id>.py: metric_id@versão · label · grain · time_basis · required_capabilities · formula(facts) ·
                coverage_rule · forbidden_fallback · pergunta_verificada · golden (fixture com o número esperado)
4  PROVE        guarda: golden bate · mutação M1 (provider na fórmula) vermelha · UNAVAILABLE ≠ 0 · dois tenants
5  MOSTRE       seção no template do Pulso (templates.py) — se for seção nova, seed idempotente (MIGRATIONS-AUTHORITY)
6  FECHE        proposta → promovida (se veio do chat) · PENDENCIAS se algo ficou · push com saída colada
QUANDO É MAIS QUE ISSO   fonte nova sem credencial → conector público (BLOCO B como modelo) · fonte com credencial →
                CAMADAS-DE-CONEXAO.md · canal de entrega novo → SPEC-095 · trabalho recorrente → Rotina, nunca "auxiliar novo"
```
E o **guarda do protocolo**: `test_o_relatorio_nasce_pelo_protocolo.py` reprova (a) métrica sem `pergunta_verificada`
ou sem golden; (b) métrica cujo id não aparece em nenhuma seção de template (órfã); (c) seção de template sem métrica
(caixa vazia — 📊 32 asserções já deixaram passar 7 caixas vazias); (d) tool nova fora do `if` de `graph.py:528`;
(e) qualquer arquivo em `metricas/` com `infocap|susep|nosnum` (M1). Com PARES (v11.1): uma definição correta passa,
a mesma sem golden reprova.
**Gate E:** o guarda fica VERMELHO ao introduzir uma métrica sem golden (mutação por cópia); o documento cabe em 12 KB.

# BLOCO F · Canário e o Pulso completo

"Como estamos?" na Resulta e na AutoFleet: Pulso 360 com as seções novas (sinistros, mercado, carteira por cliente,
pendências, funil se houver) e a lista de entregas; uma pergunta sem métrica → proposta criada, visível no admin
de Work Runs; 📊 latência; 0 número em prosa; verificação viva (uma pergunta real colada no relatório).

---

## 4. Os arquivos, por caminho
```
NOVOS     backend/app/comercial/metricas/{claims_*,quotes_*,portfolio_cancellation_rate,customer_single_product_share,issuance_pending,
          market_*}.py · backend/app/providers/susep_ses_provider.py · backend/app/services/susep_ses_ingest.py (a Rotina) ·
          backend/app/agents/tools/{listar_entregas,propor_metrica}.py · backend/app/services/work/metric_proposal.py ·
          docs/canon/COMO-NASCE-UM-RELATORIO.md · docs/canon/providers/susep/{seguradora-coenti.json,SES-CENSO.md} ·
          backend/tests/{test_a_fabrica_de_relatorios,test_o_relatorio_nasce_pelo_protocolo}.py
ALTERADOS backend/app/providers/infocap_analytics_provider.py (5 métodos) · backend/app/comercial/cbim.py (ClaimFact, QuoteFact,
          CustomerPortfolioFact, MarketFact) · backend/app/agents/tools/executive_intelligence.py (listar_metricas, proposta) ·
          backend/app/agents/graph.py (2 linhas no if de :528) · services/artifacts/templates.py (seções) · core/heartbeat.py
          (trabalhador "Censo SUSEP") · docs/canon/providers/infocap/*.json (BLOCO 0) · PENDENCIAS · INDICE · reports/
NÃO TOCAR services/skills/* (20 skills em sombra: decisão F-094.1-01) · services/intelligence/schemas.py · infocap_connector.py
```

## 5. 🔴 O QUE SAIU — e o gatilho
```
A3 comissão recebida · A9 inadimplência           → não vêm da CorpAPI; vêm do portal → SPEC-094.2 (portal_worker + extrato)
Escrita no InfoCap (5 portas)                      → F-094-09; exige ambiente de teste da InfoCap e Approval — outra SPEC
Sandbox / exec / SQL gerado                        → rejeitado pelo estado da arte (nota 18); propor é o teto
"Skill que cria skills"                            → não existe no estado da arte; o PROTOCOLO + guarda é o mecanismo
Tool Gateway fora da sombra (155 diffs, 0 idênticos) → decisão F-094.1-01: ligar ou desligar — nenhuma SPEC constrói em cima antes
ANS (B7), BACEN (B5), Opin (B15), FIPE (B9)        → o conector público do BLOCO B é o molde; entram como definições depois (💭 1–2h cada)
Auxiliar de relatório recorrente                   → Rotina existente agenda o Pulso; "auxiliar" não é o nome disso (GLOSSARIO)
Fontes pagas (SPC veicular, BigDataCorp…)          → decisão comercial do Founder (§10 (2))
```

## 6. O que fica pendente · 🧑 A caixa do Founder
```
F-094.1-01  Tool Gateway: 155 diffs em sombra, 0 idênticos, desde 19/08. Ligar (cutover medido) ou desligar e apagar. Ninguém deve
            construir em cima até decidir.
F-094.1-02  Quem aprova uma proposta de métrica no piloto: você, ou o dono da corretora? Default desta SPEC: você.
F-094.1-03  094.2 (comissão recebida × apropriada e inadimplência pelo PORTAL da seguradora) é a maior nota da lista (94) e não vem
            da API. Autoriza entrar na fila antes da 095?
F-094.1-04  Fontes pagas com preço público: SPC Histórico Veicular R$ 51,90 · BigDataCorp R$ 0,04–0,08 · Consultar Placa R$ 0,70–0,99.
            Decisão comercial.
F-094.1-05  01/10/2026: mensagem de serviço do WhatsApp deixa de ser grátis (F-094-10). Relatório por WhatsApp muda de conta.
```

## 7. A ordem
```
desenhista (guarda + mutações) → BLOCO 0 (6 chamadas + SES no MinIO) → A → B (serial) ‖ C + D ‖ E → integrador → painel v11.2
(3 lentes + red team) → conserto → juiz fresco (confirma + audita o dado: recalcula uma célula do SES e uma métrica de sinistro
à mão) → suíte inteira → canário → relatório → push
```
