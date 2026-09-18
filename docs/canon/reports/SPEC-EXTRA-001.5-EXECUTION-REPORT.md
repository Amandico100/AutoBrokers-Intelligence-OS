---
> **Status:** CONCLUÍDA · **Protocolo:** AAA v12.2 · AAA FAST · modo GERENTE (experimento C do A/B, D-PROTO-02/09)
> **SPEC:** `specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md` · **FICHA:** `FICHA-EXTRA-001.5.md`
> **Branch:** `feat/spec-extra-001-5-planos-de-assistencia` · **Base:** `3563b0e` (= `origin/main`, 17/09 22:42 UTC)
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0

```
OUTCOME ........... pergunta de cobertura → um dos CINCO estados (coberto · nao_coberto · condicionado ·
                    nao_contratado · nao_sabemos_ainda) com documento e página e o NÍVEL do plano, no chat
                    core E no WhatsApp pelo mesmo caminho, para toda seguradora
RISCO ............. 8 = ALCANCE 3 (o segurado lê) + REVERSIBILIDADE 3 (a resposta sai pelo WhatsApp) +
                    FREQUÊNCIA 2 (toda pergunta de cobertura)
SUPERFÍCIE ........ 2 — o BLOCO 0 fechou a lista de leitores do corpus (4 arquivos, escritor único)
PISO APLICADO ..... §3.2 em 2 pontos: a migration que alarga o CHECK de `doc_kind` em tabela viva e
                    SEM_ARQUIVO; e todo texto ao segurado — o "não" carrega documento e página
NÍVEL ............. a soma dá CRÍTICO (8); a marcha fixada era PADRÃO (D-PROTO-02). Divergência ESCRITA
                    (D-E0015-02): elenco do CRÍTICO (juiz + lente + confirmação), tetos do PADRÃO.
                    Builder Opus 5 `xhigh` · juiz Fable 5.1
UNIDADES .......... 5 · A chave+tabelas · B a Skill · C três ondas · D a tela · E a medição
                    FATIAS: 1 = A · 2 = B+E · 3 = C+D
COESÃO ............ A é hub (B e C consomem o contrato) · B+E tocam o mesmo turno · C+D a mesma fila
PARALELISMO REAL .. nenhum — a escrita é de um só, um builder por vez; investigador read-only: SIM
TIME .............. gerente (Fable → Opus no fechamento) · 3 builders Opus 5 xhigh · juiz Fable fresco ·
                    lente do dado (gatilho: outcome é DATASET) · confirmação §6.1 DISPAROU · red team NÃO
REFERÊNCIA ........ interna `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` · externa: PROV-O ·
                    Citations da API Anthropic · ALCE 2023 (proposta §14)
GATES ............. GA GB GC GD GE G-MIG + py_compile · suíte por diff · rotas-montam + next start
O ELO ............. "responde genérico PORQUE não há plano estruturado": medi A · medi B · medi que B
                    CHEGA em A (o caminho vivo devolvia os 3 serviços fixos de `assistance_policy.py:28`)
FAIXA DE RELÓGIO .. declarada fatia ≤ 75 min · 📊 real 27 · 58 · 142 min (a 3 estourou: onda 1 sobre 49
                    PDFs) · juiz 29 · lente 14 · conserto 142 · turnos 71/151/214 dentro do teto de 160
```

**Preflight** 📊 17/09 22:42 UTC: `HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD `3563b0e` · árvore limpa.

🔴 **Troca de gerente no meio (FATO, para a auditoria do A/B):** o gerente Fable esgotou a cota semanal logo depois do
conserto único, com a confirmação §6.1 lançada e o relatório em §5. Um gerente **Opus 5** assumiu o mesmo chat, refez
a confirmação com juiz Opus fresco (divergência de D-PROTO-09, registrada em D-E0015-09), fechou o relatório e
empurrou. Nenhuma fatia foi reconstruída, nenhum builder rechamado.

## 1. BLOCO 0 — as premissas que mudariam o desenho (investigador Opus read-only, 📊 17/09, só SELECT)

| # | a proposta afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | `storage_ref` em 0 de 29 | **173/206** (pilotos 49/62) | `select count(*) filter (where storage_ref is not null), count(*) from normative_document_versions` | a onda 1 tem de onde ler a página |
| 1b | o corpus tem página | **nenhuma** coluna de página; o `\f` morre em `limpar()` (`insurance_corpus.py:367`) | `information_schema.columns` | a página vem da FONTE ARQUIVADA |
| 2 | o filtro bloqueia o elo SUSEP | `extrair_susep(build_document_plain_text(pages))` → **`15414.900228/2017-63`**; `eq("susep_process"` → **0** | script; `rg` exit 1 | 🔴 não se toca em `_BOILERPLATE_RE`; falta o CONSUMIDOR |
| 3 | caminho vivo único | 1 importador, 1 consumidor (`infocap_tool.py:722`), tool em `graph.py:449` | `rg -n` | a base entra no composer, nada ao lado |
| 3b | o WhatsApp usa o mesmo | `attendance` **e** `core` enabled na mesma capability | `select agent_role, enabled from capability_bindings …` | 🔴 o atendente responde cobertura **sem código extra** |
| 3c | o guarda dos 3 serviços | `nodes.py:344` ANULA resposta sem eletricista+chaveiro+encanador; no WhatsApp não há guarda | `sed -n 344,352p` | o guarda muda de REGRA, não morre |
| 4 | 6 seguradoras com CG casando | **7** após normalizar; `hdi` fora das 61 siglas; desconhecida → primeiro token | script + SELECT + função em processo | a base aceita fora do censo e **rejeita** chave-lixo |
| 5 | o CHECK de `doc_kind` | 9 valores, **3 em uso** (184 · 5 · 5 = 194); 4 triggers, todos FK | `pg_get_constraintdef` · `pg_trigger` | o manifesto da migration ② nasce daqui |
| 6 | `tool_invocations` tem `tool_args` | não existe: é `input_summary jsonb`; CPF cru **0/289** | `information_schema.columns` | a origem entra no registro que já existe |
| 7 | a Skill nasce no `SkillRegistry` | `TOOL_GATEWAY_MODE` default `off` e ausente do `.env` — o chat resolve **tools** | `grep -c TOOL_GATEWAY_MODE backend/.env` → 0 | Skill = módulo + release inerte (D-E0015-03) |
| 8 | 🔴 **o ELO** | "carro reserva" nem casava a intenção; quando casava, saía **"Sim"** com os 3 fixos para *vidros, táxi, borracheiro* | script em processo | **defeito de produto §9.5**: afirmação errada ao segurado |
| 9 | linha de base da suíte | **35 failed · 48 errors** (os 48 de `test_098` por ordem; isolado 80 passed) | `python -m pytest tests -q` | é contra isto que a bateria foi triada |
| F1 ❌ | "`documents` tem `doc_kind`" | **0** (controle: `normative_documents` → 1) | `information_schema.columns` | refutada por comando |
| F2 ❌ | "`eq("susep_process"` existe" | **zero linhas, exit 1** | `rg` | refutada por comando |

**Fora do escopo:** `PlanoDeAssistencia`/`EstadoDoPlano` já existem (`policy_data_provider.py:491`) — a Skill estende,
não recria · `test_o_protocolo_tem_policia` já vermelho na `main`.

## 2. As unidades entregues, por fatia (48 commits, `3563b0e`..`3d08edf`, 52 arquivos)

| fatia | o que entrou | gate · saída real 📊 |
|---|---|---|
| **1 · A** | 2 migrations · `services/knowledge/assistance_plans_base.py` (17 funções, nenhuma aceita `company_id`) · `providers/susep/servicos-de-assistencia.json` (15 serviços) · `MANIFEST.md` · M-A1..M-A4 | 20/25/15/14 asserções verdes · o **banco** recusa `documento_id NULL`, `pagina=0`, hash de 63, publicado sem revisor, limite sem unidade (controle: linha completa aceita) · 5/5 mutações vermelhas · `corridor_playbooks.py` **não tocado** (as 7 aliases já existiam) |
| **2 · B+E** | `services/skills/cobertura_e_assistencia.py` (5 estados + `fonte_indisponivel` + gancho) · `policy_answer_composer.py` (a base entra no caminho vivo, UM vencedor) · `assistance_policy.py` (fallback marcado) · `nodes.py` · `infocap_tool.py` · `qdrant_service.py` (`doc_kind` no índice e no filtro, 8 chaves de procedência) · `invocation_recorder.py` · 2 scripts · 30 perguntas reais sem PII · M-B1..M-B5 | 78 asserções verdes · **30/30** devolvem um dos 5 estados (coberto 15 · condicionado 6 · nao_coberto 6 · nao_sabemos_ainda 3); toda resposta da base traz documento e página **no campo e no texto**; controle "quantas parcelas faltam?" → **0** consultas · release `insurance.cobertura_e_assistencia 1.0.0` · PII **0** · 6/6 mutações vermelhas |
| **3 · C+D** | `assistance_plans_extractor.py` (filtro textual → modelo por página → verificador que SÓ reprova) · `assistance_plans_susep_link.py` (a condição **vigente na emissão**) · `insurance_corpus.py` · `api/assistance_plans.py` (3 endpoints, zero `company_id`) · a tela de Conhecimento (3 componentes + rota) · `fila-onda-3.json` · M-C1..M-C3, M-D1 | 23/9/8/11 asserções verdes · M-C2: apólice real casa por `15414.900666/2014-89`, processo inexistente → **None**, filtro intocado · `test:rotas-montam` **303 rotas** · `next build` exit 0 · `next start` + requisição → `HTTP/1.1 401 {"error":"no_session"}` (controle: rota vizinha 401) · 5/5 mutações vermelhas |

**Onda 1 em produção** (📊 18/09, 49 documentos, ≈ US$ 3, só `proposto`): 148 propostas → **37 planos + 75 serviços**,
**0 publicados**. **O ELO fechou**, num par medido: apólice que diz "Plano Completo" + base com Essencial/Completo →
*"Tem sim: carro reserva — 7 dias. (Condições gerais da HDI, p. 24.)"*; sem o nome do plano → `nao_sabemos_ainda`.

## 3. Migrations — APPLY · VERIFY · ROLLBACK escritos ANTES; VERIFY contra o objeto

**① aditiva** (`20260917_01_extra0015_assistance_plans.sql`) — APPLY 2× idêntico; VERIFY 📊 `pg_get_constraintdef`:
`servico_tem_fonte` · `servico_publicado_foi_revisado` · `limite_tem_unidade` (+ os dois irmãos no plano); colunas de
dono **0** (controle: a mesma consulta acha 2 em `tool_invocations`); ROLLBACK exercitado em transação desfeita. RLS
ligada sem policy, como as 4 globais irmãs (D-E0015-06).
**② altera a trava** (`…_02_extra0015_doc_kind_manual.sql`, piso §3.2) — manifesto no cabeçalho com o
`pg_get_constraintdef` real (`normative_documents_doc_kind_check`; em uso 184/5/5 = 194, **igual antes e depois**);
transação única; APPLY 2× → constraint idêntica; ROLLBACK com a guarda `count(*) where doc_kind='manual_de_assistencia'`
= 0; atomicidade provada. 📊 Nenhuma migration do repo grava em `schema_migrations`: as duas seguem o padrão.
**Nenhuma outra migration nesta SPEC.** `MANIFEST.md` traz as duas como APLICADAS e `normative_documents` como
**NÃO RASTREADA**, com o DDL real do catálogo.

## 4. O juiz fresco (Fable 5.1, sobre `3394836`, 59 chamadas, 29 min) — **FAIL** · nota **72/100**

| # | achado | teste do produto | medição | classe |
|---|---|---|---|---|
| **B1** | a fila publica só a LINHA; o plano nunca chega a `publicado`, e a base só responde por plano publicado | **SIM**: o Founder publica 10 linhas e o segurado segue ouvindo `nao_sabemos_ainda` | `grep publicar_plano` → 0 chamadores; serviço publicado + plano `proposto` → `nao_sabemos_ainda` | BLOCKER |
| **B2** | `trecho_confere` **False em 100 %** da fila: a rota hasheia a PÁGINA, o extrator grava o hash do TRECHO (dialeto §9.4) | **SIM**: a tela que colhe a assinatura do revisor mostra bandeira falsa em tudo | `fila(limite=4)` → 4/4 False | BLOCKER |
| **B3** | apólice que nomeia DOIS planos → "o mais longo vence" | **SIM**: um "não" cuja escolha de plano foi chute | ataque A10 | BLOCKER |
| **B4** | 📊 **25 de 38** planos chamam-se "Plano único"; `identificar_plano` exige o nome no texto | **SIM**: 66 % da base nunca responderia | `select count(*) filter (where plano ilike 'plano único')` → 25 | BLOCKER → D-E0015-01 |
| 5–7 | fallback residencial inalcançável · `_NEGATIVA_RE` casa qualquer `sem` (*"tem, sem custo adicional"* atravessa) · `publicar_servico` publica até `rejeitado` | SIM | ataques A8/A13 + leitura | blockers |
| 8–10 | M-B2 flaky (1 vermelho em 5) · `atendente` nunca chega · `POLICY_INTELLIGENCE_V2` não medida em produção | não / canário | — | pendências |

**Ataques que passaram:** base vazia · `result` vazio · plano None nunca vira nível 1 · pergunta sem serviço → 0
consultas · nenhuma assinatura aceita `company_id` · idempotência · `fonte_indisponivel` com texto diferente ·
"Essencial" × "Essencial Plus" · gancho sem preço e sem prometer aceite · nível máximo sem gancho · seguradora
desconhecida → `nao_sabemos_ainda` · trecho cru 0 ocorrências · 3 mutações vermelhas em cópia · **19/20 regressões
dirigidas verdes** (a 20ª falha igual na base). **Amostra §0.4:** 173/206 ✔ · 194 = 184/5/5 ✔ · "37+75" ✘ → 38+76+5
(o extrator rodou em duas ondas; recontado). **Referências §14 reabertas 17/09:** PROV-O ✔ · Citations ✔ (página 9999
e 0 → `pagina_inexistente`) · ALCE ✔.

**Lente do dado** (Opus, cega ao juiz, 14 min) — **PASS COM PENDÊNCIAS · 82/100.** As três contagens separadas:
(a) CG indexada **8** · (b) plano publicado **0**, proposto em 8 seguradoras e 17 pares seguradora×ramo · (c) carteira
61 siglas · 83,86 % do prêmio; cruzamento após normalizar: **7 · 1 · 7**. Amostra de 6 linhas lidas do PDF no MinIO:
**5/6** a afirmação é o que a página diz; 2 (`alagamento = nao`) generalizavam exclusão de risco de OUTRA cobertura.
Integridade: chave 8/8 canônica · nível duplicado 0 · limite sem unidade 0 · hash ≠ 64 = 0 · órfãos 0 · **PII 0**
(controle: o regex acha 2 numa string de teste) · a régua conta 17 pares, não 81 linhas · migration ②: 9/9 recusas
adversariais com controle verde, em transação desfeita.

## 5. O conserto único — e a confirmação (§6.1)

Mesmo builder da fatia 3, contexto quente; 10 commits `18c137c`…`3d08edf` (12 arquivos, +995/−81): **B1** publicar a
linha publica o **plano pai** (mesmo revisor, só de `proposto`), `revisado_por` validado como uuid, a fila devolve o
plano e a tela avisa · **B2** campo enganoso removido; a fila devolve a **página inteira** com os termos grifados ·
**B3** ≥ 2 nomes → `nao_sabemos_ainda` · **B4** regra do plano único com **3 travas** (D-E0015-01) · fallback
residencial volta a rodar sem plano identificado, um vencedor só · `_NEGATIVA_RE` exige negação **do serviço** ·
M-B2 sem flake (📊 5 rodadas: 17/17) · `vigencia_inicio` = vigência do documento (38 linhas corrigidas pelo módulo) ·
`produto`/`plano` normalizados · nível não contíguo recusado (D-E0015-07) · exclusão de risco ≠ `nao` · o painel cruza
pela mesma chave (7/1/7, era 6/2/8).

📊 **Gates rerodados pelo gerente sobre `3d08edf`:** `py_compile` dos 8 `.py` tocados OK · **13/13 guardas exit 0** ·
`test_spec016_policy_intelligence` + `test_spec017_attendance_unleashed` + `test_spec016_1_answer_quality` verdes ·
5/5 mutações vermelhas · `tsc --noEmit` exit 0 · rotas-montam 303.

📊 **Produção depois do conserto** (SELECT, 18/09): **33 planos + 73 serviços `proposto`** · 5 + 8 `rascunho` ·
**0 `publicado`** · **0 `revisado_por`** · **0 planos com a data da rodada** · **0 colunas de dono** · `doc_kind`
intacto. 17 pares seguradora×ramo em 8 seguradoras (bradesco 3 ramos · hdi 2 · mapfre 3 · tokio 3 · yelum 2 · porto 2
· azul · allianz).

**Confirmação §6.1** (disparou porque havia blocker no texto ao segurado) — juiz **Opus 5** fresco (o Fable
estava sem cota — D-E0015-09), 31 chamadas, 10 min, só sobre `3394836..3d08edf`: **"o conserto criou defeito? NÃO"**,
nota **88/100**. As 8 afirmações do conserto sustentaram-se por execução: as 3 travas do plano único juntas →
`contratado`, e cada uma sozinha → `nao_sabemos_ainda`; emissão anterior à vigência → `nao_sabemos_ainda`; 17/17
frases classificadas certo pelo `_NEGATIVA_RE` (*"sem custo adicional"* e *"sem franquia"* **não** negam; *"não está
incluído"* e *"fora do plano"* negam); `rejeitado`/`rascunho` e revisor não-uuid recusados; M-B2 rodado 3× seguidas,
17/17/17. 📊 Produção conferida por ela: 33+5 planos · 73+8 serviços · `vigencia_inicio = current_date` → **0**
(19 datas distintas, 2024-05-01…2026-09-17) · `publicado` → 0 · `revisado_por` → 0 · nenhuma coluna de dono · os 4
planos com nome > 60 chars **todos em `rascunho`**, fora da fila. `npx tsc --noEmit` exit 0.

**E ela expôs três divergências entre o que o código diz e o que faz — as três consertadas em seguida** (4 commits `8fca8b3`…`543b684`, mesmo builder, contexto quente; 📊
13/13 guardas rerodados pelo gerente, exit 0 — M-B5 subiu a 27 asserções, M-C1 a 39, M-B1 a 21 — e a regressão
dirigida `test_spec016_policy_intelligence` **92 passaram / 0 falharam** e `test_spec017_attendance_unleashed`
**27 / 0**, rodadas como SCRIPT):
① 🔴 o **fallback respondia antes de a base ser consultada**: sem plano identificado, uma linha **publicada** dizendo
`eletricista = nao` era ignorada e saía *"costuma estar incluído"* (`origem='regra_generica'`). Inalcançável enquanto
a base tem 0 publicados — e o passo ③ da caixa do Founder é justamente publicar. É o defeito silencioso do §9.5,
pego antes de existir. ② `publicar_servico` aceitava **re-publicar** e sobrescrevia `revisado_por` (a docstring dizia
que não): quem revisou é a prova de proveniência (PROV-O). ③ **data de emissão ilegível** (`"maio de 2023"`) degradava
em silêncio para `date.today()` e respondia com o plano de hoje.
**Pendência registrada, não consertada:** o comando de regressão `pytest tests/test_spec016… tests/test_spec017…`
**não media nada** ("no tests collected") — são guardas-script; rodados como script dão 92/0 e 27/0.

## 6. A bateria — 📊 **1 rodada inteira**, triada por DIFF contra a linha de base

Base (`3563b0e`): **35 failed · 48 errors**. HEAD: **36 failed · 1126 passed · 34 xfailed · 48 errors** em 2225 s.
**Diferença: 1** — o guarda-script do corredor da Porto; 📊 isolado dá `16 assercoes verdes - 0 vermelhas`, exit 0, e o
diff não toca corredor nem playbook ⇒ ordem/concorrência (juiz, lente e builder na mesma máquina). **Regressões da
SPEC: 0.** Os 48 erros são contaminação de ordem de `test_098`, iguais na base (P-E0015-09). Depois do conserto
rerodaram-se os 13 guardas e a regressão dirigida, não a suíte inteira (D-E0015-05).

## 7. O que ficou fora, e o gatilho que o faz voltar

Cotação/renovação do plano superior (EXTRA-003/004: quem orça é gente) · a porta `PolicyDataProvider` (001.1;
consumida, não editada) · adaptadores Quiver/Agger/Segfy · chunker com página (P-E0015-01) · `insurer_key` nas 14
tabelas (P-E0015-02) · `ficha.faltando`/`_TITULOS`/dossiê de sinistro (001.3) · o filtro `doc_kind` vivo no Qdrant
(P-E0015-07: a coleção é inalcançável da máquina de execução) · a atendente nomeada no gancho (P-E0015-05) · o canário.

## 8. 📋 Caixa do Founder — o que só ele faz (nenhum item bloqueia a entrega na `main`)

| # | o que é | o que faz | o que custa esquecer | bloqueia? |
|---|---|---|---|---|
| ① | **Implantar** `smith-api` **e** `smith-web` | põe o caminho novo no ar | a `main` não é o ar | NÃO |
| ② | 🔴 conferir/ligar **`POLICY_INTELLIGENCE_V2=true`** no `smith-api` | sem a flag a Skill não roda | o canário mede o composer antigo e conclui errado | NÃO (trava o canário) |
| ③ | 🔴 **publicar as primeiras linhas** em Personalização → Conhecimento (💭 HDI residencial, ~10 linhas) | a base passa a responder; publicar a 1ª linha publica o plano | até lá o produto responde `nao_sabemos_ainda` — honesto, sem valor | NÃO (trava os casos 1, 3, 4, 5) |
| ④ | os 8 casos do canário: 1–5 e 7 no chat `core`; 6 pelo TESTE-A; 8 é do executor | prova a resposta ponta a ponta | "funcionou" sem os controles 5, 7 e 8 não é conclusão | NÃO |
| ⑤ | `NEXT_PUBLIC_API_URL`/`BACKEND_INTERNAL_API_KEY` no `smith-web` | a tela lê a base | a tela mostra blocos vazios (degrada, não quebra) | NÃO |
| ⑥ | validação com Saionara e Regina | o único juiz que não mente | — | NÃO |
| ⑦ | destilar as seguradoras que faltam — `providers/susep/fila-onda-3.json` traz a ordem pela carteira | a base cresce sem código novo | seguradoras da carteira sem resposta | NÃO |

## 9. Pendências e decisões — numa passada, um commit

`PENDENCIAS.md`: **P-PILOTO-04 → PARCIAL** (a parte de conhecimento fecha; o resto é 001.3) · **P-PILOTO-20** já
FECHADA pela 001.1 (conferido) · novas **P-E0015-01…10**. `FOUNDER-DECISIONS.md`: **D-E0015-01…09**.
🔴 **Nenhum motor paralelo foi criado** — nominalmente: nenhum segundo pipeline de ingestão, coleção de Qdrant, fila de
curadoria, catálogo de seguradoras, normalizador de seguradora, registro de tool call ou porta de apólice.

**FATO:** tudo o que tem 📊 foi medido por comando. **INFERÊNCIA:** a falha do guarda da Porto na bateria é de
concorrência (passa isolado; o diff não o toca). **RECOMENDAÇÃO:** publicar a fila da HDI residencial antes do
canário e conferir `POLICY_INTELLIGENCE_V2` no `smith-api` antes de concluir qualquer coisa sobre produção.

## 10. Telemetria (§11)

```
SESSAO 7bb009e8 (UTC) · 17/09 22:40 -> 18/09
EXECUTOR (gerente Fable -> Opus)  327 min · turnos  85 · pico 385k · ctx  23.3M · saida 160k · US$  23.92
  BLOCO 0 (investigador Opus)      44 min · turnos 103 · pico 189k · ctx  13.1M · US$  8.82
  Builder fatia 1 (Opus xhigh)     27 min · turnos  71 · pico 225k · ctx  10.4M · US$  6.77
  Builder fatia 2 (Opus xhigh)     58 min · turnos 151 · pico 322k · ctx  31.4M · US$ 18.36
  Builder fatia 3 + conserto + acerto (Opus xhigh)
                                  180 min · turnos 231 · pico 460k · ctx  64.5M · US$ 40.66
  Juiz fresco (Fable 5.1)          29 min · turnos  65 · pico 204k · ctx   9.6M · US$  7.76
  Lente do dado (Opus)             14 min · turnos  38 · pico 135k · ctx   3.7M · US$  2.58
  Confirmacao §6.1 (Fable, morreu por cota / Opus, concluiu)
                                   14 min · turnos  37 · pico 108k · ctx   2.8M · US$  2.75
TOTAL  8 agentes alem do executor · turnos 781 · ctx 158.7M · saida 0.31M · US$ 111.63
achados por mecanismo: executor/BLOCO 0 8 (2 EXCLUSIVOS: o ELO e o caminho do WhatsApp) ·
  prova mecanica 1 · juiz 10 (4 blockers, 4 EXCLUSIVOS) · lente do dado 7 (4 EXCLUSIVOS: vigencia,
  painel sem normalizar, produto sujo, exclusao de risco) · confirmacao 3 (3 EXCLUSIVOS) · canario: do Founder
rodadas da bateria: 1 inteira (2225 s) + parciais por fatia · nota da execucao 86/100 · juiz 72 · lente 82 ·
  confirmacao 88
```

## 11. Entrega

```
$ git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   3563b0e..b24ede5  HEAD -> main
$ git rev-list --count origin/main..HEAD
0                                  <- o trabalho está no ar (CLAUDE.md §2)
```
📊 **56 commits**, de `3563b0e` (base) a `b24ede5` (na `origin/main` em 18/09). ENTREGAR NÃO É COMMITAR: é empurrar — e está empurrado.

📊 **Gate final pelo gerente sobre a árvore empurrada:** `py_compile` OK · **13/13 guardas exit 0**
(M-A1 20 · M-A2 25 · M-A3 15 · M-A4 16 · M-B1 21 · M-B2 17 · M-B3 11 · M-B4 25 · M-B5 27 · M-C1 39 · M-C2 9 ·
M-C3 8 · M-D1 12, todas 0 vermelhas) · regressão dirigida 92/0 e 27/0 e `test_spec016_1_answer_quality` exit 0 ·
`npm run test:rotas-montam` → **A TABELA DE ROTAS MONTA** · `npx tsc --noEmit` exit 0 ·
`test_o_protocolo_tem_policia` **73 ok, 0 falhas** (estava vermelho na linha de base por causa deste mesmo
relatório, então aberto).

**O roteiro do canário, escrito para o Founder:** `docs/canon/reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md`.

**Implantar, nesta ordem:** `smith-api` → `smith-web`. **Variáveis novas:** nenhuma criada por esta SPEC. **A conferir
no ambiente:** `POLICY_INTELLIGENCE_V2`, `TOOL_GATEWAY_MODE`, `NEXT_PUBLIC_API_URL`, `BACKEND_INTERNAL_API_KEY`.
**Rollback:** o código é aditivo (a Skill sai e `assistance_policy.py` volta a ser o caminho único); as migrations têm
ROLLBACK próprio — o da ① apaga linhas curadas, o da ② só é seguro com zero linha em `manual_de_assistencia`.

**NOTA DA EXECUÇÃO: 86/100** — critério: o outcome está de pé e provado por 13 guardas, 16 mutações vermelhas, duas
migrations verificadas e uma base real que não mente para cima nem tem dono; perde pontos porque o juiz achou 4
blockers que só o conserto fechou, a faixa de relógio estourou na fatia 3, e o filtro do Qdrant e o canário ficaram por
medir. **Juiz 72/100** (antes do conserto) · **lente 82/100** · **confirmação 88/100**.
