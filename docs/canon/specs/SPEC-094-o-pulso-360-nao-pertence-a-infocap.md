# SPEC-094 · O PULSO 360 NÃO PERTENCE À INFOCAP — o número executivo nasce de um modelo canônico, uma vez, com ponteiro

> **O que ela entrega:** o dono da corretora pergunta *"como estamos?"* e recebe um veredito executivo
> cujo **cada número aponta para a métrica que o produziu** — calculada UMA vez, sobre fatos canônicos
> da corretagem (apólice, produtor, comissão, renovação), lidos por um **adapter** que é a única peça que
> conhece a InfoCap. O chat e o Artifact leem o **mesmo pacote de evidência**. Dado que a fonte não expõe
> sai **INDISPONÍVEL**, nunca zero. E antes de congelar o modelo, um **censo medido** da CorpAPI diz o que
> a InfoCap realmente entrega às três corretoras — em JSON que o código lê, não em PDF morto.
>
> **v2 · 03/09/2026 · protocolo v11.1** · commit base `{HEAD da branch}` · repo `AutoBrokers-FIX`
> Proposta: `specs-propostas/8 - SPEC-094-executive-intelligence-360-provider-agnostic.md` (3.619 linhas, 25/08)
> Research-pack: `specs-propostas/8 - SPEC-094-executive-intelligence-360-RESEARCH-PACK.md` · reaberto em 03/09/2026
> Número: **094** — livre (INDICE-DE-SPECS). Evolução direta da **SPEC-081**; NÃO é um Report Engine novo.
> **v2 = v1 + aquecimento do executor (03/09, 16 perguntas medidas, nota 74 → emendas 1–15 aplicadas).**
> **v2.1 = v2 + o CENSO executado (BLOCO 0, 03/09 09:43→10:02, 86 chamadas GET, 3 conexões) — §1.11.**

---

## 0. O TESTE DO PRODUTO

> **Na segunda-feira, o dono da Resulta escreve no chat "como estamos este ano?". Em menos de um minuto
> lê: "1.680 apólices, R$ 1,86 mi de comissão apropriada [commission.broker_accrued@1 · vigência iniciada
> em 2025 · cobertura de produtor 80,6%]. Comissão RECEBIDA: indisponível na InfoCap". Clica no link e o
> Artifact mostra os MESMOS números, com a mesma cobertura, e a seção "Fontes e confiança" diz de onde
> veio cada um. Na terça, o Founder roda a mesma pergunta na AutoFleet — pela CONEXÃO dela em
> `tenant_connections`, não pelo nome da empresa — e funciona; na Amandus o sistema RECUSA, porque a conexão dela é a
> conta da Resulta (F-094-07), e a recusa é a resposta certa. Na quarta, um teste troca a InfoCap por
> um provider de referência que devolve fatos canônicos direto: TODA a métrica dá o mesmo resultado, sem
> importar um módulo InfoCap.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ **Esta SPEC LÊ.** Nenhuma escrita na InfoCap; nenhuma chamada a Quiver/Segfy; nenhum adapter de
produção para provider sem acesso medido. O que ela decide é **onde mora a semântica**.
⚠️ A tool nova aparece para **toda corretora com agente `core`** no mesmo deploy (📊 `graph.py:528` não
distingue tenant) — é intencional: o canário são as três, e o dado de cada uma vem da conexão dela.

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 03/09/2026, HEAD `8662644`, produção `dcajcvlzcjbmyapmklil`

### 1.1 · A 081 entrega duas tools de chat, sem tela, e ninguém as usou em 16 dias
📊 `backend/app/comercial/fonte_infocap.py` (567 L) · `calculos.py` (493 L, 11 funções) ·
`backend/app/agents/tools/relatorios_comerciais.py` (760 L: `RaioXComercialTool:275`,
`RadarDeRenovacoesTool:553`). Saída: string `RELATORIO_PRONTO · … [Abrir o relatório](link)` (:378-385 e a
gêmea do Radar :636-643) + Artifact via `ArtifactService` (`_publicar:172-190`, templates
`commercial.pipeline`/`renewals.radar`, definidos em `services/artifacts/templates.py:144-174`, `CATALOGO:785`).
📊 `grep -rln "commercial.pipeline|renewals.radar|Raio-X" app components lib` → **0**: não há tela.
📊 `SELECT … FROM artifacts`: Resulta **28** artifacts da 081 (14+14), **todos de 18/08/2026**; Amandus **0**;
AutoFleet **0**. **Zero execuções desde o dia da própria SPEC. O canário das três corretoras nunca foi feito.**
📊 A tool entra no chat em **um único lugar**: `backend/app/agents/graph.py:562-563`, dentro do `if` de `:528`
(`agent_role in ("core","","core(legado)")`). Sem capability, sem `tools_config`, sem linha de banco.

### 1.2 · Não existe carteira no banco: a 081 é 100% read-through
📊 175 tabelas em `public`; regex `polic|commission|comiss|renov|infocap|producao|apolice|carteira|premi|
producer|produtor|metric|snapshot|provider` casa 13 tabelas e **nenhuma guarda apólice, comissão ou
produtor**. O dado só existe na InfoCap e no cache Redis (`fonte_infocap.py:162-199`). **Consequência:**
"última ingestão" e "% comissão nula" não são mensuráveis sem chamar a API; Source Snapshot (§72 da
proposta) e histórico (§74) são construção nova; tendência custa N chamadas (`JANELA_MAXIMA_DIAS=366`, :95).

### 1.3 · A camada "pura" já fala InfoCap — mas a troca é mecânica
📊 `calculos.py`: imports só `re, unicodedata, dataclasses, datetime, typing`; uma impureza declarada
(`date.today()` em `entender_periodo:338`). `nosnum` **7 vezes** (:143,145 dedupe · :146 JOIN `mapa.get` ·
:168,170 dedupe · :173 JOIN · :213 comentário) — sempre `str` como chave de dict/set, **nunca parseado**.
Trocar por `policy_ref` opaco é renomear 6 ocorrências, desde que a MESMA função gere as duas pontas do
join. 📊 O risco real está fora: `grep -rln nosnum` → **19 arquivos**.

### 1.4 · O provider resolve pelo NOME da corretora — e o resolver por CONEXÃO já existe, em outro módulo
📊 `relatorios_comerciais.py:_slug_da_empresa:131-171` → `CORP_INFOCAP_{SLUG}_LOGIN/PASSWORD/APPLICATION/BASE_URL`
(`fonte_infocap.py:266-269`, "💭 Dívida registrada" :262).
📊 `tenant_connections` JOIN `connector_templates(slug='infocap')`: **6 linhas** — Resulta 4 (1 `connected`
healthy + 3 `archived`, uma com `invalid_credentials`), Amandus 1 (`connected`, health `unknown`), AutoFleet 1
(`connected`, healthy). **`last_used_at` NULL nas 6** e 📊 `grep -rn last_used_at --include=*.py` → **0 escritores**.
📊 O segredo mora **na tabela**, cifrado com Fernet: `encrypted_secret_ref` é o **ciphertext** (o nome mente —
CLAUDE.md §12.1), lido por `get_encryption_service().decrypt` em `backend/app/api/infocap_connector.py:966`;
`connection_config = {base_url}`. 🔴 **E o resolver por conexão já existe:** `_resolve_infocap_connection` /
`_resolve_infocap_connection_candidates` (`infocap_connector.py:725-757`), usados em 4 chamadas do conector
de atendimento. Escrever um segundo é motor paralelo (CLAUDE.md §5).
📊 **Nesta máquina não existe `CORP_INFOCAP_*`** em nenhum `.env` (17 nomes em `backend/.env`, nenhum
`CORP_*`); existem `ENCRYPTION_KEY` e as chaves do Supabase → **o caminho pela conexão funciona localmente**,
o caminho por nome não. Mais uma razão para o BLOCO B.

### 1.5 · Dado ausente vira zero, hoje, com nome e comentário
📊 `fonte_infocap.py:_num():521-530` devolve `0.0` para `None`, `""` e qualquer valor não conversível.

### 1.6 · O canon tem duas verdades sobre o 403 — e a errada bloqueia 18 endpoints
📊 `docs/canon/INFOCAP-CORPAPI-MAPA.md` (42 L): **10 endpoints acessíveis** (`/cliente_cpf`, `/lista_clientes`,
`/cliente_ligacoes`, `/documentos`, `/documento`, `/itens`, `/cotacoes`, `/atendimentos`, `/seguradoras`,
`/ramos`) e **18 marcados "403 = pedir liberação"** (`/parcelas`, `/comissao`, `/comissoes`, `/financeiro`,
`/titulos`, `/contas_receber`, `/contas_pagar`, `/fluxo_caixa`, `/faturamento`, `/vendedores`, `/usuarios`,
`/propostas`, `/sinistro`, `/endossos`, `/tarefas`, `/agenda`, `/cias`, `/filiais`). O MAPA registra ainda que
**`/login` devolve as flags de permissão do perfil** (`p500/p501/…=T`) — uma chamada classifica as 18.
📊 `fonte_infocap.py:56` e `:333-338`: *"403 com texto SigV4 → a rota não existe"*. O MAPA não menciona
`/renovacoes` nem `val_r`. Código usa 5 rotas (`/login`, `/documentos_bi`, `/renovacoes`, `/documentos`,
`/producao`); **`/cotacoes` e `/atendimentos` nunca foram chamados**. Sem Postman/OpenAPI no repo.

### 1.7 · O Intelligence Fabric já tem Finding, Evidence e Veredito — e tem LEIS
📊 `intelligence_findings` **14** · `intelligence_signals` **92** · `intelligence_signal_evidence` **810** ·
`intelligence_rules` **12** · `briefing_items` **1.324** · `briefing_publications` **134**.
📊 `schemas.py`: `domain` é `@property` derivada de `DOMINIO_POR_TIPO[signal_type]` (:259-261) — **não é
gravável**; `SignalDraft.valido()` recusa `signal_type` fora de `TIPOS_DE_SINAL` (:272-274) e **exige
evidências** (:279); dos 26 tipos só `commercial_opportunity` mapeia para `comercial`; `data_quality` tem
gate próprio (:118). `finding_engine.consolidar` filtra por `source_type` (`SOURCE_TYPES_INTERNOS`, :311) —
um sinal `executive_360` **entra** no briefing. A proposta cria Finding/Evidence Pack **sem citar o Fabric**.

### 1.8 · O número vira PROSA antes de chegar ao modelo — e leva o NOME do produtor junto
📊 `relatorios_comerciais.py:378-385`: `f"Resumo para você comentar: {cob.apolices_total} apólices,
{_reais(cob.comissao_total)} de comissão" + f", liderado por {topo.nome} com {_reais(topo.comissao)}"`.
Texto livre, sem referência, sem base temporal — e `topo.nome` é **nome de pessoa no chat**. A gêmea do
Radar em `:636-643`. **É o elo mais barato e mais valioso da SPEC** (BLOCO 0-bis).
🔴 📊 `backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py:283-294` carrega o **nome completo de um
produtor real** da Resulta, versionado, com o percentual de repasse dele ao lado. É dado de pessoa
identificada com remuneração, no git. **BLOCKER de higiene, unidade própria (BLOCO H).**

### 1.9 · Custo: o LLM é desprezível, a API é o relógio
📊 `token_usage_logs`: `chat` 5.247 chamadas, média 1.980 in / 449 out, **US$ 19,79 total**; sem
`work_run_id`, `tool_name` ou `artifact_id`. 💭 ≈ **US$ 0,008 por Raio-X**. 📊 Latência no comentário de
`fonte_infocap.py:167-168` e `:538`: **Raio-X anual frio ~53 s (6 chamadas) · Radar 90 dias ~8 s (1 chamada)**,
medidos em 18/08/2026 — o BLOCO 0 remede (a v1 desta SPEC dizia que o 8 s não tinha fonte; tinha).

### 1.11 · 📊 O QUE O CENSO MEDIU — BLOCO 0 executado em 03/09 (`docs/canon/providers/infocap/`)
📊 **As 18 rotas "403 = pedir liberação" NÃO EXISTEM**: todas devolvem 403 com assinatura SigV4 do API Gateway; e `/login`
das TRÊS corretoras devolve **17 flags de permissão, todas `T`**. Não há liberação a pedir; `financial.cashflow` é
UNAVAILABLE **medido**. 📊 Existem e o MAPA não sabia: **`/sinistros`** (plural: 200, **5.729 registros** na Resulta,
26,3 s, `numsin/situacao/datoco/datavi/datenc/valind/franquia/nosnum`) e `/usuario` (400 = existe). `/producao` → 500 ×3.
`/atendimentos` devolve a lista na chave **`tarefas`**; "2.355 atendimentos" do MAPA **não reproduzido** (15).
📊 **Golden controls 2025:** Resulta 1.680 apólices tipo A · `val_c` **R$ 1.863.830,79** · `pretot` R$ 11.910.456,05 ·
3.536 renovações · 97 produtores · 97,1% com produtor ordem=1 · BI∩renov 100 — **a 081 reproduz exatamente**.
AutoFleet 3.117 · R$ 2.099.510,43 · 2.654 · 64 · 99,1% · **BI∩renov 0** → a receita de cobertura de produtor da 081
**não é constante do provider**: remedir por corretora.
🔴 **E `BI∩renov` é um ARTEFATO DE JANELA, não a cobertura do produto** (acrescentado em 03/09/2026, pela lente do
dado). Os dois números acima — 100 na Resulta, 0 na AutoFleet — medem `2025 × 2025`, e apólice anual que **começa**
em 2025 **termina** em 2026: as duas rotas filtram pontas opostas da vigência. 📊 O produto pede `2024–2027`
(`anos_de_vencimento_para`), e nessa janela a cobertura medida é de **80,6%**. Citar `BI∩renov` como "a cobertura da
AutoFleet" é afirmar sobre a carteira o que só se sabe sobre o recorte.
📊 **Base temporal:** `/documentos_bi` filtra `inivig` (1.680/1.680; `fimvig` só 106); `/renovacoes` filtra `fimvig`
(3.536/3.536); `data=` aceita exatamente `INIVIG · DATINC · DATALT · DATPROP` (a lista sai num 400). Não há base de
apropriação de comissão: `COMMISSION_ACCRUAL_DATE` não existe na InfoCap.
📊 **F-094-02 RESOLVIDA — `val_r = val_c × per_r / 100`, PROVADO em 198/198 linhas de `prod_docs` (desvio máx. R$ 0,01).**
`val_r` é repasse APROPRIADO (não pago). 🔴 **`ordem==1` não é o maior repasse** (amostra: ordem 1 = 4%, ordem 2 = 15%):
somar só ordem 1 subestima — o repasse soma TODOS os `prod_docs`. `quant_produtores == len(prod_docs)` só em 34,1%.
`val_ra/val_rc/val_rp/taxa_repasse/cod_com_ind` vieram None/0 → 💭 não provados.
📊 **Latências:** `/renovacoes` 90 d **2,28 s** (a 081 dizia 8 s) · `/documentos_bi` 1 ano 3,3–7,5 s · `/renovacoes` 1 ano 7–15 s.
📊 **Capacidades:** SUPPORTED 9 · PARTIAL 6 · UNKNOWN 3 · UNAVAILABLE 1.
🔴 **P1 CROSS-TENANT (CLAUDE.md §10 (4)) — Amandus e Resulta descriptografam para a MESMA conta CorpAPI:** mesmo
`user_sha`, mesmo `pass_sha`, mesmo perfil, carteira **idêntica ao centavo**. Os ciphertexts diferem (IV do Fernet), a
tabela não denuncia. **Um canário na Amandus mostraria a carteira da Resulta com o nome da Amandus.** Registrado em
`FOUNDER-DECISIONS.md` e na caixa (F-094-07); o canário da Amandus **não roda** até a decisão; o resolver do BLOCO B ganha
um gate contra conta compartilhada.

### 1.10 · Linha de base de regressão (rodada hoje com `SEM_REDE=1`)
```
npm run test:calculos-comerciais      81 verdes · 0 vermelhas
npm run test:fonte-comercial          26 verdes · 0 vermelhas · 3 blocos de rede pulados (e dizem que pularam)
npm run test:ferramentas-comerciais   31 verdes · 1 vermelha ALHEIA (guarda de git-diff vendo a 093-B)
```
📊 São scripts com `check()`, não pytest (`def test_` → 0). O guarda `test_as_ferramentas_de_relatorio_comercial.py:120`
prende `ferramentas_comerciais` ao `if` de `graph.py:528` — é ele que protege o agente de ATENDIMENTO.
📊 `test_template_de_artefato_existe.py:89-106` exige que **todo template do CATALOGO fora dos 8 originais**
esteja no SQL de `backend/supabase/migrations/20260730_01_spec057_seed_templates.sql`.

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado, corretor ou seguradora. Esta SPEC só responde a quem perguntou no chat.
⛔ InfoCap SOMENTE LEITURA (GET). Censo com prudência: uma chamada por rota por conjunto de parâmetros, sem laço de
   força bruta, período ≤ 30 dias nas rotas de lista (1 ano só nos golden controls), respeitando o retry/backoff de
   fonte_infocap.py. Fora do censo, a InfoCap só é chamada pelo caminho de produto (tool) e pelo live test da 081.
⛔ Nenhuma chamada a Quiver/Segfy. Nenhum adapter de produção para provider sem acesso medido (M13).
⛔ Credencial: SÓ pelo caminho do produto — tenant_connections + get_encryption_service().decrypt, em processo.
   NUNCA em .env do repo, arquivo do censo, teste, log ou relatório. Só presença/ausência.
⛔ Banco: SELECT livre. UMA migration, de SEED (§7), idempotente, com APPLY/VERIFY/ROLLBACK antes de rodar.
   Escritas de dado: artifacts* (ArtifactService) · report_templates (upsert do ArtifactService) · intelligence_signals +
   intelligence_signal_evidence (SignalService/EvidenceService) · intelligence_findings (FindingEngine, indireto) ·
   tenant_connections.last_used_at (UPDATE de uma coluna, escritor novo e declarado).
⛔ NUNCA imprimir CPF, nome de segurado, apólice, placa, e-mail, telefone, credencial. Censo com amostras REDIGIDAS
   (dígitos → #, letras → x). Nome de PRODUTOR é dado de pessoa: vai ao Artifact do tenant, NUNCA a string de chat,
   log, censo, teste, fixture ou relatório.
⛔ NUNCA `git add -A`. Não tocar em .env de produção. Nenhum merge sem gate final.
⛔ O modelo nunca recebe registro cru de apólice: só agregados, findings, cobertura e referências.
⛔ Não apagar RaioXComercialTool/RadarDeRenovacoesTool: viram WRAPPERS sobre o registry (BLOCO F).
⛔ A tool nova fica DENTRO do `if` de graph.py:528 (agente core). Fora dele (capabilities :443, lookup :431) é regressão
   de conduta do atendimento — o guarda da 1.10 é estendido a ela.
```

## 2.1 O EXECUTION CARD da conversão — o executor confere e discorda com número

```
SPEC .................  094 · O Pulso 360 não pertence à InfoCap
RISCO ................  7  — número financeiro EXECUTIVO lido pelo dono; tool viva nas 3 corretoras; credencial de 3 tenants
                            no caminho (piso §3.2). Não sobe a 8: nada envia
SUPERFÍCIE ...........  3  — providers · comercial · agents/tools · docs/canon/providers · intelligence (escrita de sinal) ·
                            artifacts (template + seed) · tests (higiene)
NÍVEL ................  CRÍTICO — desenhista ANTES do código · painel de 4 lentes (uma é a LENTE DO DADO) · red team ·
                            auditoria externa · integrador
UNIDADES .............  10  BLOCO 0 (censo) · 0-bis (ELO) · H (higiene PII) · A · B · C · D · E · F · G
COESÃO ...............  0 e H são independentes de tudo; A→B→C→D seriais (mesmo contrato); E → F (F consome o pack) ; G paralela a E/F
                            mas relatorios_comerciais.py é arquivo-hub (F e G): quem chega segundo faz rebase
PARALELISMO REAL .....  2 escritores (0 ‖ 0-bis+H, depois E/F ‖ G); integração serial
O ELO ................  chat "como estamos?" → conexão do tenant (resolver EXISTENTE) → adapter InfoCap → CBIM (sem nosnum) →
                        registry com time_basis → UM Evidence Pack → tool devolve REFERÊNCIAS, Artifact lê o MESMO pack →
                        o mesmo caminho com o provider de referência dá o MESMO número → o sinal gravado CHEGA ao briefing
GATE ZERO ............  (i) as strings :378-385 e :636-643 devolvem prosa com número e nome — VERMELHO em HEAD
                        (ii) _num(None) == 0.0 — VERMELHO em HEAD · (iii) `nosnum` em calculos.py — VERMELHO
                        (iv) grep de nome de produtor em backend/tests — VERMELHO em HEAD (1.8)
FAIXA DE RELÓGIO .....  14–18h do primeiro despacho ao push (censo 4–6h EM PARALELO · 0-bis+H 1,5h · A–D 6–7h · E/F/G 4h ·
                        laço 3–4h). Se o censo não puder rodar (credencial), a SPEC NÃO fecha: para e registra (§10 (5)/(8))
BATERIA ..............  suíte inteira no gate do D e no fim (2×); os 3 scripts comerciais a cada bloco; live test da 081
                        (sem SEM_REDE) UMA vez no BLOCO 0 e UMA no gate final, pela conexão
```

---

## 3. 🌐 O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS — §7.3, reaberto em 03/09/2026

📊 Os 10 URLs do pack estão vivos (3 redirects). O pack sustentava o Metric Registry citando a **home** do
dbt e não trazia referência para as três teses mais originais (Evidence Pack, snapshot único chat+Artifact,
versionamento semântico). As seis abaixo dão lastro às duas primeiras; **a terceira continua sem, e fica
como decisão nossa** (metric_id@versão, BLOCO D).

### ① Anti-Corruption Layer — Microsoft
```
URL ................. https://learn.microsoft.com/azure/architecture/patterns/anti-corruption-layer
O QUE FAZ ........... fachada que traduz semântica de um sistema externo para o modelo interno; 12 "considerations"
MODELAMOS ........... BLOCO B: o adapter InfoCap é a ÚNICA peça que lê `nosnum/val_c/inivig`; valida na fronteira de
                      confiança; cada tradução carrega correlation_id gravado na provenance do pack
REJEITAMOS .......... API Management/Functions e a variante event-driven — vendor sem problema medido
COMO O JUIZ INSPECIONA `grep -rn "from app.comercial.metricas\|from app.comercial.calculos" backend/app/providers/` → 0
                      (orquestração dentro da ACL) · `grep -rn "infocap\|nosnum\|val_c" backend/app/comercial/metricas/` → 0 (M1)
```
### ② ACL — AWS Prescriptive Guidance
```
URL ................. https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html
O QUE FAZ ........... exemplo real: Int32.TryParse devolve BadRequest, não 0, quando o campo não converte
MODELAMOS ........... BLOCO C: campo ilegível ou ausente vira UNAVAILABLE no fato canônico — o adapter é a única peça
                      autorizada a falhar na tradução. `_num(None)` deixa de existir na fronteira
REJEITAMOS .......... a transitoriedade: a AWS manda descomissionar a ACL após a migração. A NOSSA É PERMANENTE — escrito
                      no docstring do port
COMO O JUIZ INSPECIONA mutação M2/M4: força None num campo de comissão da fixture e exige UNAVAILABLE no envelope, não 0.0
```
### ③ dbt Semantic Models — a definição de métrica com base temporal obrigatória
```
URL ................. https://docs.getdbt.com/docs/build/semantic-models
O QUE FAZ ........... YAML com `agg_time_dimension` OBRIGATÓRIO, entities/dimensions, métricas simple → ratio/derived
MODELAMOS ........... BLOCO D: cada métrica declara metric_id · version · time_basis (o análogo do agg_time_dimension — o campo
                      cuja ausência causou INIVIG×FIMVIG) · grain · required_capabilities · formula sobre fatos CBIM.
                      `contribution.after_repasse` é DERIVED de duas simples, nunca reescrita
REJEITAMOS .......... instalar dbt/MetricFlow como runtime (CLAUDE.md §5); join dinâmico em tempo de consulta
COMO O JUIZ INSPECIONA `grep -rn "val_c" backend/app/agents/tools/ backend/app/comercial/metricas/` → 0 (📊 em HEAD: 1 em tools —
                      régua que consegue ficar vermelha) · abre o registry ao lado do exemplo `fact_transactions`
```
### ④ dbt MetricFlow time spine — grão de tempo custom, sem densificar zeros
```
URL ................. https://docs.getdbt.com/docs/build/metricflow-time-spine
O QUE FAZ ........... calendário canônico com granularidades custom; `join_to_timespine` preenche zeros
MODELAMOS ........... BLOCO D: eixo de tempo canônico do CBIM em grão de negócio (safra de vigência), pré-requisito de
                      qualquer comparação 30/60/90
REJEITAMOS .......... materializar o spine (§73) e o join automático — "período sem renovação = 0" ≠ "provider não expõe
                      FIMVIG = UNAVAILABLE", e densificar apaga a diferença (§14)
COMO O JUIZ INSPECIONA pede renovações por trimestre com uma capability desligada na fixture e confere que o trimestre vazio
                      sai 0 e a capability ausente sai UNAVAILABLE — dois estados, nunca um
```
### ⑤ Cube — cubes (físico) × views (fachada): o consumidor nunca toca o cube
```
URL ................. https://docs.cube.dev/docs/data-modeling/overview
O QUE FAZ ........... separa o mapa físico da fachada que o consumidor lê
MODELAMOS ........... BLOCO E: CBIM é o cube; o EVIDENCE PACK é a view — única superfície que chat, Artifact e o trilho de
                      sinais consomem. É o mecanismo do §68 (chat e Artifact batem)
REJEITAMOS .......... Cube como runtime — servidor, cache e autoridade paralela ao Work Run
COMO O JUIZ INSPECIONA `grep -rn "FonteInfocap\|from app.comercial" backend/app/agents/tools/ backend/app/services/artifacts/`
                      → 📊 9 linhas em HEAD; depois do E tem de ser 0 fora do adapter (M10/M12). Régua que fica vermelha hoje
```
### ⑥ Claude Citations — o número chega como bloco citável, não como prosa
```
URL ................. https://platform.claude.com/docs/en/build-with-claude/citations
O QUE FAZ ........... `cited_text` + `document_index` extraídos do documento, não gerados; custom content desliga chunking
MODELAMOS ........... BLOCO 0-bis/F: cada métrica/finding do pack vira um bloco estruturado com título `metric_id@versão`
                      no retorno da tool; o LLM do grafo (que já narra hoje) cita — NENHUMA chamada nova de modelo
REJEITAMOS .......... mandar registro cru como documento citável (§81/§82) — só agregados; e um "narrador" separado
                      (seria a 3ª chamada do turno; a 1.9 orçou 2)
COMO O JUIZ INSPECIONA guarda determinístico: a string devolvida não contém `R$ ?\d`, `\d+ apólices` nem nome fora dos blocos
                      (roda com SEM_REDE) · UMA verificação viva no gate final: pergunta real no chat, resposta colada no relatório
```

**O que o estado da arte faz e nós não faremos AGORA** (💭 valor 0–100 para a corretora): registry consultável
pelo modelo em runtime 92 · grão custom safra/competência 88 (parcial no D) · narração com ponteiro 85
(**fazemos**) · joins em tempo de consulta 78 (não: fonte é API paginada) · view por tenant 74 (**fazemos**
por company_id) · correlation-id de tradução 70 (**fazemos**, barato) · ACL event-driven 40 (não).

---

# BLOCO 0 · REMEDIR + O CENSO DA INFOCAP — em paralelo, com a credencial da CONEXÃO

**Remedir (§5 ① do protocolo):** os 📊 da §1, pelo comando. Em especial: (a) as 3 conexões `connected`
descriptografam nesta máquina pelo caminho do produto (`get_encryption_service().decrypt`) — só
sim/não; (b) latência real de `/documentos_bi` 2025 numa chamada (o "53 s") e do `/renovacoes` 90 dias (o "8 s").

**O censo (🔒 exigência do Founder, §0.3 da proposta):** com a conexão `connected` da **Resulta**, GET, na ordem:
```
1  /login          → as flags de permissão do perfil (p500/p501/…): classifica as 18 rotas "403" ANTES de tentá-las
2  /seguradoras /ramos /lista_clientes (30 dias)   → dimensões e a chave que as rotas parametrizadas exigem
3  rotas parametrizadas (/documento, /itens, /cliente_ligacoes, /cliente_cpf…) → UMA chamada cada, com chave vinda do passo 2
4  as 18 do MAPA, uma chamada cada, só para confirmar a CLASSE de erro que o passo 1 previu
5  /documentos_bi e /renovacoes em período FECHADO (2025) → golden controls · /cotacoes e /atendimentos (30 dias)
para cada rota: classe (200 · 403-SigV4=rota inexistente · 403-permissão · 404 · 5xx · timeout) · envelope · paginação ·
limite de range · latência de UMA chamada · campos (nome · tipo · % nulo · exemplo REDIGIDO · significado com confiança ·
chave de relação · PII s/n) · base temporal MEDIDA com dois filtros · fingerprint (sha256 das chaves ordenadas)
```
Saída, machine-usable, em `docs/canon/providers/infocap/`: `INFOCAP-CORPAPI-CENSUS-v2.md` ·
`infocap-capability-manifest.json` · `infocap-field-dictionary.json` · `infocap-golden-controls.json` ·
`infocap-schema-fingerprints.json`. E `INFOCAP-CORPAPI-MAPA.md` ganha no topo *"SUPERADO pelo censo v2 em {data}"*.
**Amandus e AutoFleet:** o censo roda **só o passo 1 e os golden controls** nas duas (o resto é igual por
contrato) — é isso que prova que a conexão delas serve para o canário do BLOCO G.

**Gate 0:** manifesto com TODAS as 31 rotas e classe de erro medida (M18: censo que só documenta as rotas em
uso REPROVA); nenhum valor não redigido nos 5 arquivos (guarda grepa `\d{6,}`, `@` e a lista de nomes do
passo 2); nenhuma credencial; o live test da 081 verde UMA vez **pela conexão**. **Nenhum código de métrica
antes do manifesto existir** — mas 0-bis e H não esperam o censo.

# BLOCO 0-bis · O ELO — as DUAS strings deixam de ser prosa

UM builder, na forma mais curta, antes de qualquer outro código:
1. `RaioXComercialTool` (:378-385) **e** `RadarDeRenovacoesTool` (:636-643) devolvem ao modelo um **bloco
   estruturado** (`metricas: [{metric_id, version, value|UNAVAILABLE, unit, period, time_basis, coverage, confidence}]`,
   `link`, `aviso`) — **zero número em prosa, zero nome de produtor** (o nome fica no Artifact do tenant).
2. O Artifact recebe **o mesmo objeto** (mesmo `pack_id`) — não recalcula.
3. Guarda novo, VERMELHO em HEAD: (a) a string não contém `R\$ ?\d`, `\d+ apólices` nem `topo.nome`; (b) chat e
   Artifact carregam o mesmo `pack_id` e valores; (c) mutação M10 (Artifact consulta de novo) vermelha.

# BLOCO H · HIGIENE — o acervo comercial não carrega pessoa
`test_a_fonte_comercial_bate_com_a_infocap.py:283-294`: o nome do produtor sai; o controle passa a ser
"o produtor de maior repasse tem razão `val_r/val_c` entre X e Y" **sem nome**. Guarda: grep de `[A-Z][a-z]+ [A-Z]`
nas fixtures comerciais é uma lista fechada de rótulos de negócio. **O histórico do git não se reescreve**
(CLAUDE.md §13.5) — a pendência registra que o nome está no histórico e é ação do Founder decidir.

# BLOCO A · CBIM — os fatos canônicos que a InfoCap consegue alimentar HOJE

`backend/app/comercial/cbim.py` — dataclasses congeladas, sem import de provider:
```
PolicyFact             policy_ref · provider_key='infocap'(tipo, constante) · source_ref(opaco) · insurer · branch · valid_from ·
                       valid_to · premium: Money|UNAVAILABLE · kind: NEW|RENEWAL|ENDORSEMENT|UNKNOWN · status
ProducerAssignmentFact policy_ref · producer_ref · producer_label(só o Artifact lê) · role_source · share? · order
CommissionFact         policy_ref · broker_commission_accrued: Money|UNAVAILABLE · producer_repasse: Money|UNAVAILABLE · received: UNAVAILABLE
RenewalFact            policy_ref · valid_to · producer_ref? · status_source
QuoteFact              (SÓ se o censo provar /cotacoes) quote_ref · created_at · closed_at? · status · branch
Money                  amount: Decimal · currency='BRL'   ·   UNAVAILABLE = sentinela tipada, nunca 0/None
Provenance             connection_id · correlation_id · fetched_at · fingerprint   ← infraestrutura fica AQUI, não no fato
```
`policy_ref = sha256(company_id + provider_key + source_ref)[:16]` — **por corretora**, estável entre
conexões do mesmo tenant, e é o ÚNICO identificador que `calculos`/`metricas` conhecem. `ClaimSignalFact` tem dado
(📊 `/sinistros`, 5.729 registros) — **fica fora da v1 por tempo**, contrato documentado, pendência P-094-SINISTROS
com gatilho JÁ atingido. `Interaction` (`/atendimentos`, chave `tarefas`), `Cashflow` (UNAVAILABLE medido) e
`PolicyMovement` ficam como contrato (§6).
**Gate A:** a fixture CBIM importa e roda sem `fonte_infocap` em `sys.modules`; mutação "UNAVAILABLE → None" vermelha.

# BLOCO B · O PORT e o ADAPTER — a única peça que fala InfoCap, sobre o resolver que JÁ EXISTE

`backend/app/providers/brokerage_analytics_provider.py` (mesmo padrão de registry de `policy_data_provider.py`):
`Protocol BrokerageAnalyticsProvider` com `capabilities()`, `policies(period, time_basis)`, `producer_assignments`,
`commissions`, `renewals`, `quotes` (só se A tiver QuoteFact). Docstring: **"ACL permanente; InfoCap é o
provider piloto, nunca a semântica"** (ref ②).
`backend/app/providers/infocap_analytics_provider.py`: **envolve `FonteInfocap`** (não a reescreve): `Apolice →
PolicyFact`, `ProdutorDaApolice → ProducerAssignmentFact + CommissionFact.producer_repasse`, `Vencimento →
RenewalFact`. `_num` sai da fronteira: ilegível → `UNAVAILABLE` + warning com correlation_id.
**Resolver: REUSA `_resolve_infocap_connection` / `_resolve_infocap_connection_candidates`**
(`infocap_connector.py:725-757`), estendendo-os se preciso (são async: a tool já roda em contexto async no
grafo — o executor mede). Filtro **`status='connected'`** (a Resulta tem 3 arquivadas, uma com credencial
inválida). Legado por NOME só atrás de `feature_flags.env_ligada("COMERCIAL_RESOLVER_LEGADO")`, com log e
pendência. **Escritor novo e declarado:** `UPDATE tenant_connections SET last_used_at = now() WHERE id = …`
depois de uma leitura bem-sucedida (uma coluna, uma linha, com `company_id` no filtro).
**Gate contra conta compartilhada (P1 do censo):** o adapter calcula `account_fingerprint = sha256(login)[:12]` da
credencial descriptografada e o grava na `Provenance`; se duas corretoras ATIVAS resolvem para o mesmo fingerprint, a
leitura da segunda **recusa** com aviso "conexão compartilhada com outra corretora — decisão F-094-07" e o Artifact NÃO
é publicado. Teste com fixture de duas conexões iguais → vermelho sem o gate.
**Gate B:** `grep -rn "nosnum\|val_c\|inivig\|fimvig\|codfil" backend/app/comercial/ backend/app/agents/tools/` → 0 (M1
estático); 📊 `last_used_at` da conexão da Resulta deixa de ser NULL após um Raio-X; cache com chave por
`company_id + connection_id` (M11 vermelha); a conexão `archived` NUNCA é escolhida (teste com fixture das 4 linhas).

# BLOCO C · O MANIFESTO DE CAPACIDADE — ausente ≠ zero
`ProviderCapabilityManifest` lido do JSON do censo: `capability → SUPPORTED|PARTIAL|UNAVAILABLE|UNKNOWN|DEGRADED`
com `coverage_pct` e `source_refs`. `UNKNOWN` lê-se *"não verificado"*, não *"indisponível"*. Drift: no início
de cada leitura, o fingerprint da rota é comparado ao do censo; diferente → `DEGRADED`, a métrica dependente sai
bloqueada com aviso, as outras sobrevivem (E2E-4).
**Gate C:** M2 (`commission_received` UNAVAILABLE → 0) · M14 (drift silencioso) · M15 (cobertura omitida) vermelhas.

# BLOCO D · O METRIC REGISTRY — a fórmula não conhece provider, e carrega a base temporal que EXISTE
`backend/app/comercial/metricas/` — `registry.py` + uma definição por métrica:
```
metric_id · version · label · grain · time_basis · required_capabilities · formula(facts) → MetricResult · coverage_rule · forbidden_fallback
```
**Bases temporais medidas na InfoCap: `POLICY_VALID_FROM` (`/documentos_bi`, INIVIG) e `POLICY_VALID_TO`
(`/renovacoes`, FIMVIG). Só.** `commission.broker_accrued@1` declara `time_basis=POLICY_VALID_FROM` e o
envelope diz isso; `COMMISSION_ACCRUAL_DATE` só nasce se o censo achar rota que a exponha.
**Métricas v1** (migradas das 11 funções de `calculos.py`, que passam a receber CBIM): `production.policy_count@1`
· `production.premium_written@1` · `commission.broker_accrued@1` · `production.new_vs_renewal@1` · `mix.insurer@1`
· `mix.branch@1` · `producer.performance@1` · `producer.momentum@1` (30/60/90 via `comparar`) · `renewal.exposure@1`
· `projection.run_rate@1` (premissa no envelope) · `data.coverage@1` (a métrica agregada de cobertura de
produtor — distinta do campo `coverage` que TODO envelope carrega para a sua própria métrica).
**Provadas pelo censo (§1.11), portanto DENTRO da v1:** `repasse.producer_accrued@1` = Σ `val_r` de **todos** os
`prod_docs` (nunca só `ordem==1`), `time_basis=POLICY_VALID_TO` (vem de `/renovacoes`) — e por isso
`contribution.after_repasse@1` (DERIVED, ref ③) só é calculável sobre a **interseção** das populações INIVIG × FIMVIG,
com `coverage` = fração da comissão do período que tem repasse conhecido, escrito no envelope. **`commission.broker_received`,
estorno e imposto: UNKNOWN** (rota não existe; o Artifact escreve "não exposto pela InfoCap"). Cobertura de produtor é
remedida **por corretora** (AutoFleet: BI∩renov = 0 — ⚠️ artefato de `2025 × 2025`; o produto varre `2024–2027` e
mede 📊 **80,6%**. Ver §1.11).
**Gate D:** M1 vermelha por grep; M5 (endosso como apólice) vermelha; M6 (comparar `MetricResult` de `time_basis`
diferentes) → o registry recusa; **paridade com a 081** (golden controls do censo; 📊 `SPEC-081:113-114` e
`fonte_infocap.py:41-42`): `policy_count` 2025 = 1.680 · `new/renewal` 717/963 · `broker_accrued` ≈ R$ 1.863.831 ·
cobertura de produtor 80,6% · comissão atribuída 86,2% — tolerância 💭 0,5%, diferença explicada por escrito;
**suíte inteira** neste gate.

# BLOCO E · O EVIDENCE PACK e o FINDING — pelas leis do Intelligence Fabric
`backend/app/comercial/evidence_pack.py`: `EvidencePack(pack_id, company_id, period, compare_period, capabilities,
metrics: [MetricResult], findings: [Finding], coverage, freshness, provenance, warnings)` — **em memória e no
payload do Artifact**; nenhuma tabela nova.
**Findings determinísticos** (queda de produtor · concentração acima do limiar · exposição de renovação ·
cobertura baixa) vivem no pack e no Artifact. **Viram sinal** só os que cabem num `signal_type` EXISTENTE
com semântica honesta: 📊 `commercial_opportunity` (domain `comercial`) para exposição de renovação e
concentração; queda de produtor idem, com `severity ≤ medium`. **Cobertura baixa NÃO vira sinal** (`data_quality`
tem gate próprio) — fica no pack. Cada sinal leva **evidência** pelo `EvidenceService` (o envelope da métrica,
sem nome de pessoa) e `metadata={'metric_refs': [...], 'pack_id': ...}`; `source_type='executive_360'`.
`schemas.py` **não muda**. `finding_engine.consolidar` os inclui (não estão em `SOURCE_TYPES_INTERNOS`) — é o
que a SPEC quer: o briefing existente decide se mostra.
**Gate E:** mesmo `pack_id` na tool e no Artifact (M10); pack serializado sem `\d{11}` nem nome de produtor (M16);
`SignalDraft.valido()` aceita os 3 sinais (teste chama `valido()` de verdade); o sinal carrega `metric_refs` no metadata.

# BLOCO F · A TOOL `executive_intelligence`, os wrappers e o mapa de produtor mínimo
Uma tool de domínio: recebe um **query plan** (`period`, `compare`, `views[]`, `dimension?`) que o modelo
preenche — **o modelo escolhe O QUE; o registry calcula**. Default de "como estamos?": ano até hoje × mesmo
período do ano anterior (`entender_periodo`). Follow-up ("e só a Porto?") reusa o pack por `pack_id` e filtra
a dimensão — sem refetch (E2E-2). Retorno: blocos estruturados (ref ⑥) + uma frase determinística de
resumo **sem número solto** + link. **Sem chamada nova de LLM** — quem narra é o grafo, como hoje.
Vocabulário proibido testado no resumo determinístico e nos rótulos do Artifact: `lucro`, `recebid` para accrued,
`funcionário` sem mapa (M7/M8/M3).
**Mapa de produtor mínimo:** `actor_type ∈ {employee, partner, indicator, channel, unknown}`, default `unknown`,
lido de **arquivo versionado** `docs/canon/providers/infocap/producer-roles.{company_slug}.json` (o mesmo
mecanismo do manifesto; 📊 a única jsonb de `companies` é `acionamento_profile`, que é outra coisa). Rótulo
da InfoCap (`EXECUTIVO`, `FECHADOR`) vai para `role_source`, nunca decide `actor_type`. Artifact escreve
"papel não mapeado" quando `unknown`.
**Wrappers:** `raio_x_comercial` e `radar_renovacoes` continuam e chamam o registry. A tool nova entra na
lista de `relatorios_comerciais.py:757-760` (dentro do `if` de `graph.py:528`); o guarda
`test_as_ferramentas_de_relatorio_comercial.py:120` é estendido a ela.
**Gate F:** guarda do 0-bis verde com a tool nova; M3 vermelha; `py_compile`; os 3 scripts comerciais verdes.

# BLOCO G · O ARTIFACT `executive.pulse360`, o provider de referência e o canário
Template novo em `services/artifacts/templates.py` (`CATALOGO`), 8 seções (§62 da proposta): veredito ·
atual × anterior · pessoas e canais · economia pós-repasse **ou** "indisponível" · mix e concentração ·
exposição de renovação · projeção · **fontes e confiança**. Nenhum renderer novo. Restrições do banco (📊
`pg_get_constraintdef`): `category='executive'`, `narrative_shape='verdict_led'`, `kind='report'`.
🔴 **A migration de SEED (§7):** `test_template_de_artefato_existe.py:89-106` exige o template no SQL de seed, e
editar `20260730_01_spec057_seed_templates.sql` é proibido (CLAUDE.md §8). Então: **nova** migration
`backend/supabase/migrations/2026090X_01_spec094_seed_template_pulse360.sql` — `INSERT … ON CONFLICT DO NOTHING`,
idempotente, expand-only, APPLY/VERIFY/ROLLBACK escritos antes; e o teste passa a ler os DOIS arquivos de seed.
**Provider de referência** (`backend/app/providers/reference_analytics_provider.py`, test-only): devolve CBIM de
fixture; o guarda roda TODO o registry com ele e compara com a mesma fixture traduzida pelo adapter InfoCap
(paridade semântica). `sys.modules` sem `fonte_infocap` durante o teste (M12).
**Canário:** um "como estamos?" em **Resulta → AutoFleet**, pela conexão de cada uma; 📊 latência fria e quente,
`pack_id` igual no chat e no Artifact, cobertura visível, 0 número em prosa, e a **verificação viva** da ref ⑥ (uma
pergunta real, resposta colada no relatório). **Amandus NÃO roda** (P1 do censo, F-094-07): o gate de conta
compartilhada tem de recusá-la — e essa recusa É o teste do canário dela.
**Gate G:** 📊 `SELECT count(*) FROM artifacts WHERE template='executive.pulse360'` ≥ 1 por corretora; E2E-1..5 verdes;
`test_template_de_artefato_existe` verde; **suíte inteira**; `git push origin HEAD:main` com a saída colada.

---

## 4. Os arquivos, por caminho (o mapa da SUPERFÍCIE 3)

```
NOVOS
  docs/canon/providers/infocap/{INFOCAP-CORPAPI-CENSUS-v2.md, infocap-capability-manifest.json, infocap-field-dictionary.json,
                                infocap-golden-controls.json, infocap-schema-fingerprints.json, producer-roles.{slug}.json}
  backend/app/comercial/cbim.py · evidence_pack.py · metricas/*.py
  backend/app/providers/brokerage_analytics_provider.py · infocap_analytics_provider.py · reference_analytics_provider.py
  backend/app/agents/tools/executive_intelligence.py
  backend/supabase/migrations/2026090X_01_spec094_seed_template_pulse360.sql
  backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py   (script com check(), como os irmãos comerciais)
ALTERADOS
  backend/app/comercial/calculos.py (recebe CBIM; nosnum → policy_ref) · fonte_infocap.py (_num sai da fronteira; resto intacto)
  backend/app/agents/tools/relatorios_comerciais.py (0-bis; wrappers; lista de tools) · backend/app/core/feature_flags.py
  backend/app/api/infocap_connector.py (só se o resolver precisar de parâmetro novo) · backend/app/services/artifacts/templates.py
  backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py (H) · test_as_ferramentas_de_relatorio_comercial.py (guarda do if)
  backend/tests/test_template_de_artefato_existe.py (lê os dois seeds) · package.json (script do guarda novo)
  docs/canon/INFOCAP-CORPAPI-MAPA.md (SUPERADO) · PENDENCIAS.md · CHANGE-ADDENDA.md · INDICE-DE-SPECS.md · reports/SPEC-094-EXECUTION-REPORT.md
NÃO TOCAR  backend/app/services/intelligence/schemas.py · finding_engine.py (a 093-B acabou de mexer; a 094 só LÊ as regras)
```

## 5. O CONTRATO — congelado para os builders paralelos (depois do D)
`MetricResult`, `EvidencePack`, `ProviderCapabilityManifest`, `Provenance` e os fatos do BLOCO A são congelados
no gate D com um teste de forma. Quem precisar mudar o contrato depois do D **para e escreve** (CHANGE-ADDENDA).

## 6. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça
```
Quiver/Segfy adapters, Provider Admission Gate formal, "SPEC-101"   → sem acesso medido. Gatilho: credencial de um cliente Quiver/Segfy
Source Snapshot persistido (§72.1) e histórico analítico (§74)      → não há carteira no banco (1.2). Gatilho: 2ª pergunta de tendência
                                                                       que a API não responde em <60 s
PolicyMovement/Claim/Interaction/Cashflow Facts                     → contrato documentado; implementação só se o censo achar o dado
Momentum em quadrantes (§33), HHI (§36), risco de renovação (§38)    → v1 tem 30/60/90 e shares simples
Narrador LLM separado (§69)                                          → seria a 3ª chamada do turno; o grafo já narra sobre blocos (ref ⑥)
ACL/roles por papel (§79), self-view do produtor (§80)              → mede roles reais antes; pendência medida
Cost observability com 11 campos (§71.2)                            → `token_usage_logs` sem coluna; `tool_name`/`pack_id` em `details`
Drift monitor agendado (§94)                                        → fingerprint comparado A CADA leitura (C); cron é outra SPEC
Mapa de produtor em coluna do banco                                 → arquivo versionado (a única jsonb de companies é de acionamento)
Tela de frontend                                                    → a 081 nunca teve; o canal é chat + Artifact. Tela é a 095
"ZERO migration"                                                    → UMA migration de SEED de template (o guarda do repo exige) — §7
```

## 7. ⛔ UMA MIGRATION, DE SEED — e nenhuma estrutura
A v1 desta SPEC prometia zero migration. 📊 O aquecimento mediu que `test_template_de_artefato_existe.py`
exige todo template novo no SQL de seed, e que editar a seed da 057 é proibido. Então a 094 tem **uma**
migration: `INSERT INTO report_templates … ON CONFLICT DO NOTHING` do `executive.pulse360` — idempotente,
expand-only, sem tabela, coluna, trava ou dado alterado; ler `MIGRATIONS-AUTHORITY.md` antes. Tudo o mais
tem escritor existente (lista na §2) mais o `UPDATE` de `last_used_at` (BLOCO B). Se o BLOCO 0 provar que
outra tabela é indispensável, **para e registra** — CLAUDE.md §10 (6).

## 8. O que fica pendente (vai para PENDENCIAS.md com dono)
P-094-LEGADO resolver por nome atrás de flag · P-094-SNAPSHOT histórico · P-094-ROLES ACL medida · P-094-CUSTO
colunas de custo · P-094-MAPA-PRODUTOR curadoria por corretora · P-094-QUIVER/SEGFY acesso · P-094-CENSO-RERUN
protocolo de re-censo · P-094-GIT-PII nome de produtor no histórico do git (🧑) · P-094-SECRET-REF o nome
`encrypted_secret_ref` mente (é ciphertext) — renomear é migration, outra SPEC · **P-094-CONTA-COMPARTILHADA** (🧑, P1)
Amandus e Resulta na mesma conta CorpAPI · **P-094-SINISTROS** `/sinistros` tem 5.729 registros e nenhum leitor (gatilho
do ClaimSignalFact atingido) · **P-094-PRODUCAO-500** `/producao` devolve 500 e o conector de atendimento a usa ·
**P-094-RAG-MAPA** o MAPA errado foi ingerido no RAG global (censo §8 item 10): superar lá também.

## 9. 🧑 A CAIXA DO FOUNDER
```
F-094-01  O censo e o canário usam as CONEXÕES de tenant_connections (3 connected), descriptografadas pelo caminho do produto,
          nesta máquina. Nenhuma variável CORP_INFOCAP_* entra em .env do repositório.
F-094-02  "Contribuição pós-repasse" só aparece se o censo PROVAR o significado de val_r/per_r (ou /comissao). Senão o Artifact
          diz "indisponível na InfoCap" — decisão desta SPEC, não omissão.
F-094-03  A tool nova aparece para as TRÊS corretoras no mesmo deploy (graph.py:528 não distingue tenant). Intencional.
F-094-04  Deploy: `git push origin HEAD:main` + Implantar no smith-api + aplicar a migration de seed. Sem smith-web.
F-094-05  Nome de produtor real está no HISTÓRICO do git (test:283-294, desde a 081). Reescrever histórico é decisão sua.
F-094-06  Rotação das chaves coladas no chat de 03/09 (inclui CORP_INFOCAP_* da Resulta e AutoFleet) continua devida.
F-094-07  🔴 P1: a conexão InfoCap da AMANDUS descriptografa para a MESMA conta da RESULTA (mesmo login, mesma carteira ao centavo).
          Se a Amandus é a mesma corretora legal, diga — e a SPEC trata as duas como um tenant de dados. Se não é, a conexão da
          Amandus está ERRADA e qualquer tela dela mostraria a carteira da Resulta. Até você decidir: o resolver recusa a
          segunda corretora da mesma conta e o canário da Amandus não roda. (FOUNDER-DECISIONS, 03/09)
```

## 10. A ordem de execução
```
desenhista escreve o guarda com as mutações M1–M18 ANTES de qualquer builder
BLOCO 0 (censo, pela conexão, 4–6h) ─────────────────────────────────────────────┐
0-bis + H (1 builder, 1,5h) → A → B → C → D (serial; gate D + suíte inteira) ──┤
                                                    ├→ E → F ┐                   │
                                                    └→ G ────┼→ integrador ←──────┘ (manifesto entra em C/D quando o censo fechar)
→ painel (4 lentes: verdade/ELO · DADO · regressão+tenant · produto/guarda) + red team → conserto único → juiz de
  confirmação → auditoria externa → suíte inteira → canário nas 3 → relatório → push
```
**A LENTE DO DADO** desta SPEC: recalcula 3 métricas de 2025 direto da resposta da InfoCap (não há tabela) e
compara com o envelope do registry, item a item; abre o Artifact da Resulta e confere que mostra o que o pack diz.
