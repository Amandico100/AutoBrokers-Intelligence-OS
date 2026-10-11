# LAUDO — A leitura de apólice no produto: onde se lê, de onde vem, o que acerta, e se o PDF do CORP deve servir a TUDO

> 📋 **Cópia para o canon (11/10/2026, agente de síntese):** revisada por `grep` de CPF/CNPJ, telefone, e-mail, nº de apólice e nomes próprios de pessoa → **0 ocorrências a redigir**. Nenhuma credencial: do `/incorp_url_post` só a FORMA da resposta, nunca os valores. Os caminhos `scratchpad/…` citados são do rascunho da sessão e não estão no repositório. O resumo para o Founder está em [`MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md`](MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md).

> Modo INVESTIGAÇÃO (protocolo AAA v13 §3.3), read-only · 11/10/2026 · investigador Opus 5.5
> Árvore `AutoBrokers-FIX`, branch `spec/131-0-A-contas`, HEAD `ac0a6fd`. Nenhum arquivo do repositório alterado.
> Banco: só SELECT pelo MCP (projeto `dcajcvlzcjbmyapmklil`). CORP: só GET, em série, por `scratchpad/ic/ic.py`; os PDFs
> baixados ficaram **só em memória**. Nenhum nome, CPF, telefone ou endereço neste laudo; corretora = 6 primeiros hex de `md5(company_id)`.

## EXECUTION CARD (investigação)
```
OUTCOME ........ responder ao Founder: o PDF da apólice que o CORP guarda deve ser a fonte de TUDO? é mais estável? onde há estrutura pior?
RISCO .......... 0 (leitura) · SUPERFÍCIE 3 ("não sei apontar TODOS os leitores") → MODO INVESTIGAÇÃO
O FIO .......... /documento (url_apolice) → download → PyPDF2 (DocumentService) → regex de linhas (policy_document_evidence_service)
                 → ApoliceDocumental (infocap_policy_provider) → reconciliar(corp, pdf) (policy_data_provider) → tool → resposta
O ELO .......... "o produto JÁ lê o PDF do CORP" = medi o CÓDIGO (arquivo:linha) + o BANCO (documents) + RODEI o leitor real do produto
                 sobre 32 apólices reais da janela de renovação (não só li o regex)
FERRAMENTAS .... scratchpad/ic/medir_leitor.py · resumir_leitor.py · rotulos.py · fator_pymupdf.py (saídas _medir_leitor.out/_fator.out)
```

---

## 0. A resposta curta (para o gerente)

1. **O produto JÁ usa o PDF do CORP** — desde a R1C.1/SPEC-016 e, "sempre", desde a EXTRA-001.1 (14/09). Só pelo campo
   `acompanhamento.emissao.url_apolice`, **nunca** por `/documento_anexos`. Ele baixa, guarda no MinIO + `documents`, e lê.
   📊 21 PDFs guardados (3 corretoras, 25/06 → 26/09), 21/21 `status=completed`, 275 chunks.
2. **O defeito não é a FONTE, é o LEITOR.** O leitor de linhas de cobertura é um regex treinado em **dois layouts** (HDI e Allianz).
   📊 Rodando o leitor REAL do produto sobre 32 apólices da janela: ele fecha a apólice inteira (Σ prêmio das linhas = prêmio líquido)
   em **11/32** — **todas Allianz RESI/COND + HDI COND**. Tokio (RESI/COND/EMPR/AUTO), Allianz EMPR, Alfa, HDI AUTO: **0 linhas**.
   Sura e Yelum AUTO: o PyPDF2 **explode em todas as páginas** e o pipeline do produto cai inteiro. Porto EMPR: PDF escaneado, 0 texto.
3. **A API estruturada (`/itens`) é boa para AUTO e ruim para RE.** 📊 Σ prêmio de `/itens` fecha com o prêmio líquido (±2 %) em
   **4/8 AUTO** (e fica em 90–100 % em 6/8) — mas em **0/24 RE**, com 0–94 % (e até 209 %, Allianz empresarial) do prêmio.
4. **Há QUATRO leitores de documento de seguro no produto, e só um passa pela "ficha"** (`Apolice` + `reconciliar`). Os outros três
   (anexo do WhatsApp/chat, mídia do QCM, condição geral) não produzem ficha nenhuma; dois deles mandam o texto cru ao modelo.
5. **A "ficha da apólice" única já EXISTE no código** — `Apolice`/`ApoliceDocumental`/`reconciliar` na porta `PolicyDataProvider`,
   com o adaptador `PdfOnlyProvider` pronto para o PDF que o cliente manda. **A 130-B não deve criar leitor novo: deve trocar o
   motor de dentro do leitor que já existe** (regex → regex + modelo + visão, com o fechamento de prêmio como juiz) e ligar os
   outros três caminhos a ele. Nota **90** (detalhe na §6).

---

## 1. FATO — o mapa de TODOS os lugares que leem apólice hoje

📊 Comandos de base: `grep -rn "documento_anexos\|url_apolice\|documento_oficial\|acompanhamento" backend/app` (Grep tool);
`grep -n` dos números de linha citados abaixo, todos em HEAD `ac0a6fd`.

| # | serviço | ponto de entrada (arquivo:linha) | FONTE | o que extrai | quando | cache | falhas conhecidas |
|---|---|---|---|---|---|---|---|
| L1 | **Chat principal** (corretor) | `agents/tools/infocap_tool.py:1010` → porta `get_policy_data_provider` → `infocap_policy_provider.py` → `api/infocap_connector.py` | CORP `/cliente_cpf`·`/cliente_ligacoes`·`/documento`·`/itens` (sem `data`, `:3447`) **+ PDF por `url_apolice`** (`:3673-3678`) | cadastro + coberturas `/itens.garantias` (nome, IS, franquia, prêmio) + **texto integral do PDF** (até 24.000 chars ao modelo, `infocap_tool.py:1930-1932`) + trechos/linhas do PDF | **toda chamada da tool lê o PDF** (`_LER_SEMPRE_O_DOCUMENTO = True`, `infocap_tool.py:780`) | `/itens`: Redis 180 s (`infocap_connector.py:3459`). PDF: durável, `documents` + MinIO por corretora+conexão+locator+hash (`document_service.py:159-219`) | regex lê 2 layouts (§3); PyPDF2 sem tolerância por página (`document_service.py:397-399` relança) |
| L2 | **Atendimento WhatsApp** (segurado: assistência, sinistro) | mesma tool, papel `attendance` (`infocap_tool.py`, `client_facing`) + `policy_context.py` (PURO, lista branca da SPEC-117) + `attendance_ficha.py:901` | idem L1 | idem, **mas o texto integral NÃO vai ao modelo** (`if document_text and not client_facing`, `infocap_tool.py:1930`); vão as coberturas reconciliadas e os fatos (`policy_facts.py`) | idem | idem | idem L1; e o plano de assistência depende do PDF (abaixo) |
| L3 | **Cobertura e assistência** (Skill) | `services/policy_answer_composer.py:423-501` → `services/skills/cobertura_e_assistencia.py:790-831` | bloco de assistência do PDF (fatos) → **texto integral do PDF** → `tabela_itens` do CORP (só o NOME do plano) | qual plano publicado da base (`insurer_assistance_plans`) é o do segurado; o processo SUSEP impresso → condição geral | por pergunta de cobertura | — | 📊 19 respostas com `cobertura` no `tool_invocations`: 16 `seguradora_desconhecida`, 3 `plano_nao_identificado`, **0 identificadas** (SELECT abaixo) |
| L4 | **Fallback de assistência** | `services/assistance_policy.py` (marcado FALLBACK desde a 001.5) | fatos de assistência confirmados (`policy_facts.has_confirmed_assistance`) | 3 serviços padrão do residencial | só sem linha publicada | — | regra genérica, `confianca='baixa'` |
| L5 | **Veículo / acionamento / portal** | `vehicle_tool.py:57-70`, `insurer_dispatch_tool.py:2458-2463`, `portal_tool.py:527-532` → `provider.vehicle` → `infocap_connector.py:4344` | CORP `/documento` + `/itens` (placa, chassi, FIPE, ano) + `/cliente_cpf` | objeto do risco AUTO | no acionamento | — | ainda pelo membro DEPRECIADO `vehicle` (P-E0011-VEHICLE-VIA-DETALHAR) |
| L6 | **Cobrança** | `services/billing_collection.py:1206-1210` → `provider.lookup` | CORP `/documento` (parcelas) | parcelas | régua de cobrança | — | `/parcelas` 403 (P-PILOTO-19) |
| L7 | **Anexo no WhatsApp** (segurado manda PDF) | `api/webhook.py:3310-3325` → `services/vision_service.py:152` (`extract_document_text`) | o PDF enviado, via **docling** (se no ar) senão **PyPDF2** (40 págs) | **texto cru**, truncado em 20.000 chars (`vision_service.py:48`), **colado na mensagem do turno** | a cada documento recebido | nenhum | sem ficha, sem origem; sem redação de CPF em `vision_service.py` (📊 `grep -n -i "cpf\|redact\|redig\|mascar" app/services/vision_service.py` → 0; guarda posterior não medido); 📊 6 documentos em `messages`: 4 lidos, **2 "não foi possível ler"** |
| L8 | **Anexo no chat principal** | `api/chat.py:829-841` → `extract_document_text` | o PDF anexado | texto cru ao modelo | por anexo | nenhum | o próprio plano registra: "vai ao modelo principal sem redação" (`PLANO-MESTRE…` §SPEC-132) |
| L9 | **Quem Cobra Menos** (lead) | `services/canal/conversa.py:766-797` (`_midia_nao_e_resposta`) | foto/PDF do lead | **nada** — guarda só a REFERÊNCIA depois do "sim" | — | — | de propósito (conserto B1 da 133-A); `canal/cotacao.py:31` `SITUACAO = "novo_sem_apolice"` ("a leitura é da 130-B") |
| L10 | **Renovação / multicálculo** | `services/multicalculo/pedido.py:525` `de_apolice(Apolice, perfil)` | a `Apolice` da porta (número, seguradora, vigência, placa) + `perfil` de `/itens`/`/cliente` | pedido de RENOVAÇÃO | — | — | 📊 `de_apolice` só é chamado em TESTES (`grep -rn "\bde_apolice\b" backend/app backend/tests` → 0 chamadas em `app/` fora da definição); **só AUTO** (`pedido.py:548` recusa outro ramo). Na proposta, a apólice atual entra por **JSON digitado** (`multicalculo/comando_proposta.py:58`). 📊 `multicalculo_pedidos`: 6 linhas, todas `origem='teste'` |
| L11 | **Relatórios comerciais** | `comercial/fonte_infocap.py`, `providers/infocap_analytics_provider.py` | CORP `/documentos_bi`, `/renovacoes`, `/producao`, `/prod_docs`, `/sinistros` | contagens, prêmios, renovações | sob demanda | — | **não leem cobertura** — não precisam do PDF |
| L12 | **Condição geral (base de assistência)** | `services/knowledge/insurance_corpus.py:1681` (`_baixar_pdf_direto`) | PDF da condição geral (SUSEP/site) | cláusulas, planos | curadoria | acervo | outro documento (não é a apólice); usa **PyMuPDF** (`requirements.txt:51-56`) |
| L13 | **Portal de vidros** | `portal_worker/.../vidros_sessao.py:189` (`GET /apolices/itens-cobertos`) | API do portal da seguradora | catálogo de peças cobertas | no acionamento de vidros | — | só vidros; não é a apólice |

**FATO — o caminho L1/L2 por dentro, elo a elo:**
`infocap_connector._extract_official_document_candidates` (`:3666-3690`) só conhece `acompanhamento.emissao.url_apolice` e
`acompanhamento.proposta.url_proposta` → `_maybe_attach_official_policy_document_evidence` (`:2246-2340`) →
`PolicyDocumentEvidenceService.ensure_official_policy_evidence` (`policy_document_evidence_service.py:897`) → cache por
`find_official_policy_document` (`document_service.py:159`) → senão baixa (`_fetch_official_document_candidate_for_policy_pipeline`,
`infocap_connector.py:2209`, tenta sem auth / header / cookie) → `store_official_policy_document` (`document_service.py:233`, PyPDF2
`:378-399`) → `extract_policy_document_evidence` (`policy_document_evidence_service.py:622`, regex por linha, teto
`MAX_EVIDENCE_ITEMS = 60` `:51`) → se 0 evidência, **docling síncrono** (`:1022-1038`; o fallback devolve UMA página só, `:836`) →
ingestão no Qdrant → `apolice_documental_do_pack` (`infocap_policy_provider.py:567`) → `reconciliar(corp, pdf)`
(`policy_data_provider.py:1606`: **cobertura/limite/franquia/plano → vence o documento; parcela/status/vigência → vence o CORP**).
O próprio adaptador declara `documento_oficial: "PARCIAL"` — *"o extrator de linhas nao le os dois layouts reais de tabela"*
(`infocap_policy_provider.py:727-735`; o texto está vencido: hoje lê os dois, e só eles).

---

## 2. FATO — o que está no banco

📊 `select case when file_name like 'infocap-policy-%' … from documents group by …` (MCP, 11/10):

| origem | n | corretoras | status | chunks | 1º | último |
|---|---|---|---|---|---|---|
| PDF da apólice baixado do CORP (`infocap-policy-*`) | **21** | 3 | 21 `completed` · 0 erro | 275 (21/21 com chunk) | 25/06 | 26/09 |
| outro (`txt`, base de agente) | 1 | 1 | completed | — | 12/06 | 12/06 |

- Por corretora/mês (📊 mesmo SELECT agrupado): `660a33` 2+6+2+7 (jun–set) · `afabf5` 3 (set) · `3c8f80` 1 (set). Tamanho médio 238–693 KB.
  Nenhum com `agent_id`; 6/21 com o sufixo de conexão (o formato novo da 001.1).
- **`documents.metadata` vazio em 21/21 e `source_kind` nulo em 21/21** (📊 `count(*) filter (where metadata<>'{}')` = 0). Quem leu,
  com qual parser (`direct_text`/`docling`), quantas linhas, se fechou o prêmio — **não fica registrado em lugar nenhum consultável**.
  O `parser_used` mora só no JSON cru no MinIO (`document_service.py:266-284`).
- **Não há outra apólice guardada**: `sanitization_jobs` = 0, `canal_leads` = 0, `leads` = 0; os anexos do WhatsApp vão para o bucket
  `chat-docs` sem linha em `documents` (`webhook.py:3314`).
- Uso da tool de apólice (📊 `tool_invocations where capability_key='operational.infocap.policy_lookup.read'`): **219 chamadas**
  (15/08 → 26/09), p50 3,6 s, máx 12 s; depois de 15/09 (PDF "sempre"): **45 chamadas, 22 entradas distintas, 6 PDFs novos**.
  ⚠️ O `output_summary` só guarda `tipo/ok/campos/cobertura` — **não guarda `document_status`**, então não dá para separar
  "cache hit" de "sem URL" de "falhou a leitura". INFERÊNCIA: a taxa de sucesso do PDF em produção **não é mensurável hoje**.
- Visão (fotos): 📊 `token_usage_logs where service_type='vision'`: 29 chamadas, US$ 0,0756 no total, **US$ 0,0026 por imagem**.

---

## 3. FATO — o leitor do produto rodado sobre o PDF do CORP (o ELO)

📊 `cd scratchpad/ic && python medir_leitor.py 8 && python resumir_leitor.py` — 8 apólices por ramo da janela de renovação
(`renov.json`, seed 1311): RESI/COND/EMPR do banco Resulta, AUTO do banco AutoFleet. Para cada uma: `/documento` (prêmio
líquido, `url_apolice`), `/documento_anexos`, `/itens?data=<inivig>`, download do PDF, **PyPDF2 como o `DocumentService`**, e o
**leitor real do produto** (`extract_policy_document_evidence` → `apolice_documental_do_pack`, importados do repositório, sem cópia).
Régua de "apólice lida inteira": **Σ prêmio das linhas = prêmio líquido do CORP (±2 %)** — a mesma ideia do `_contador_de_premio` da porta.

### 3.1 Tabela por apólice
| id | prêmio líq. | `/itens`: cob · Σ prêmio (% do líq.) | PDF via | págs (c/ texto) | leitor do produto: linhas · Σ prêmio (% do líq.) |
|---|---|---|---|---|---|
| RESI-ALLI-00 | 1.146,91 | 4 · 267,08 (23 %) | url_apolice | 6 (5) | 7 · 1.146,91 (**100 %**) |
| RESI-ALLI-01 | 724,82 | 8 · 315,41 (44 %) | url_apolice | 6 (5) | 13 · 724,82 (**100 %**) |
| RESI-ALLI-02 | 153,08 | 5 · 77,50 (51 %) | url_apolice | 6 (5) | 7 · 153,08 (**100 %**) |
| RESI-ALLI-03 | 466,50 | 8 · 314,12 (67 %) | url_apolice | 6 (5) | 12 · 466,50 (**100 %**) |
| RESI-BRAD-04 | 570,73 | 4 · 570,73 (100 %) | **nenhum PDF** | — | — |
| RESI-ALLI-05 | 685,92 | 9 · 241,65 (35 %) | url_apolice | 6 (5) | 13 · 685,92 (**100 %**) |
| RESI-ALLI-06 | 337,72 | 6 · 278,32 (82 %) | url_apolice | 6 (5) | 7 · 337,72 (**100 %**) |
| RESI-TMAR-07 | 321,50 | 0 · 0 (0 %) | url_apolice | 7 (7) | **0** |
| COND-HDI-08 | 10.941,92 | 5 · 7.670,39 (70 %) | url_apolice | 4 (4) | 14 · 10.941,92 (**100 %**) |
| COND-TMAR-09 | 31.875,89 | 5 · 20.142,73 (63 %) | url_apolice | 7 (7) | **0** |
| COND-ALLI-10 | 3.656,93 | 15 · 3.018,48 (83 %) | url_apolice | 4 (4) | 18 · 3.656,93 (**100 %**) |
| COND-TMAR-11 | 5.732,11 | 5 · 4.146,42 (72 %) | url_apolice | 7 (7) | **0** |
| COND-TMAR-12 | 2.834,36 | 4 · 1.454,75 (51 %) | url_apolice | 7 (7) | **0** |
| COND-ALLI-13 | 8.618,73 | 14 · 6.886,62 (80 %) | url_apolice | 4 (4) | 17 · 8.618,73 (**100 %**) |
| COND-ALLI-14 | 8.305,48 | 16 · 7.788,77 (94 %) | url_apolice | 4 (4) | 19 · 8.305,48 (**100 %**) |
| COND-ALLI-15 | 4.790,92 | 15 · 4.021,83 (84 %) | url_apolice | 4 (4) | 18 · 4.790,92 (**100 %**) |
| EMPR-TMAR-16 | 21.280,39 | 6 · 0 (0 %) | url_apolice | **105** (105) | 6 · 1.500,00 (7 %) · **bateu o teto de 60 itens** |
| EMPR-ALLI-17 | 10.244,03 | 8 · 21.404,09 (**209 %**) | url_apolice | 4 (4) | **0** |
| EMPR-PORT-18 | 5.103,85 | 1 · 184,09 (4 %) | **só `/documento_anexos`** | 16 (**0 — escaneado**) | **0** |
| EMPR-ALLI-19 | 327,51 | 3 · 191,88 (59 %) | url_apolice | 4 (3) | **0** |
| EMPR-ALLI-20 | 6.195,72 | 8 · 9.180,09 (148 %) | url_apolice | 4 (4) | **0** |
| EMPR-ALFA-21 | 761,01 | 0 · 0 (0 %) | url_apolice | 4 (4) | **0** |
| EMPR-TMAR-22 | 9.763,69 | 9 · 0 (0 %) | **nenhum PDF** | — | — |
| EMPR-ALLI-23 | 3.291,20 | 7 · 4.464,20 (136 %) | url_apolice | 4 (4) | **0** |
| AUTO-SURA-24 | 4.591,86 | 0 · 0 (0 %) | url_apolice | 19 (**0 — PyPDF2 erro em 19/19 págs**) | **pipeline cai** |
| AUTO-TMAR-25 | 1.818,07 | 9 · 1.797,75 (99 %) | url_apolice | 8 (8) | **0** |
| AUTO-LIBE-26 | 3.449,40 | 10 · 3.449,40 (100 %) | url_apolice | 4 (**0 — erro 4/4**) | **pipeline cai** |
| AUTO-YOUS-27 | 2.578,00 | 0 · 0 | **nenhum PDF** | — | — |
| AUTO-YOUS-28 | 5.406,80 | 0 · 0 | **nenhum PDF** | — | — |
| AUTO-TMAR-29 | 1.588,14 | 8 · 1.571,34 (99 %) | url_apolice | 8 (8) | **0** |
| AUTO-HDI-30 | 2.948,64 | 11 · 2.647,56 (90 %) | url_apolice | 4 (4) | **0** |
| AUTO-TMAR-31 | 3.591,67 | 9 · 3.540,68 (99 %) | url_apolice | 8 (8) | **0** |

### 3.2 Agregados (📊 `resumir_leitor.py`)
| ramo | n | `url_apolice` | anexo "APÓLICE" | algum PDF | PDF com texto (PyPDF2) | leitor achou linhas | **leitor fecha o prêmio** | **`/itens` fecha o prêmio** | download (mediana) |
|---|---|---|---|---|---|---|---|---|---|
| RESI | 8 | 7 | 7 | 7 | 7 | 6 | **6** | 1 | 3,7 s |
| COND | 8 | 8 | 8 | 8 | 8 | 5 | **5** | 0 | 3,6 s |
| EMPR | 8 | 6 | 7 | 7 | 6 | 1 | **0** | 0 | 3,0 s |
| AUTO | 8 | 6 | 6 | 6 | 4 | 0 | **0** | **4** | 2,8 s |
| **total** | **32** | **27** | **28** | **28** | **25** | **12** | **11** | **5** | — |

- O PDF existe em **28/32** (87,5 %); `/documento_anexos` acrescenta **1** (Porto EMPR) ao que `url_apolice` já dá. Bate com o FATO NOVO
  (77/99 com arquivo de APÓLICE) na ordem de grandeza.
- PyPDF2 local levou 0,04–0,4 s por apólice típica; 18 s no PDF escaneado de 16 páginas; o download do S3 leva ~3 s (até 17 s).
- O plano de assistência (`assistance_plan`) apareceu em **23/25** PDFs com texto — inclusive nos Tokio, onde a TABELA não foi lida.
- Rótulos lidos (📊 `python rotulos.py 0 10`): Allianz condomínio → 18 linhas limpas ("Básica Simples", "RC Síndico", "Vendaval…",
  "Assistência 24h"…), cada uma com LMI e prêmio. Allianz residencial → a 1ª linha sai como "Q.Aero" (o rótulo de incêndio quebrado
  pelo PyPDF2): **o número fecha, o nome nem sempre**.
- Tokio condomínio, a linha crua que o regex NÃO lê: `Danos Elétricos 600.000,00 15.103,93` (sem "R$", dois valores) — o layout
  `lmi_premio_sem_rs` existe no código (`policy_document_evidence_service.py:385-395`) mas não casa esse texto.

### 3.3 O elo, conferido
- A afirmação "o leitor fecha 11/32" foi medida rodando **o código do produto** (`importlib` do arquivo, não cópia) sobre os **bytes reais**
  do S3, e conferida por um caminho **independente**: o prêmio líquido do `/documento` do CORP. Nas 11, o Σ bate **ao centavo**.
- ⚠️ Diferença de ambiente: o PyPDF2 do produto (`requirements.txt:50`, 3.0.1) **relança** a exceção da página (`document_service.py:397-399`);
  o meu script conta por página. Para Sura e Yelum isso significa: em produção, `store_official_policy_document` falha e o pack volta
  com `policy_document_evidence_pipeline_failed` (`infocap_connector.py:2318-2326`) — **nem o texto vai ao modelo**.

### 3.4 Um fator: o extrator de TEXTO (PyPDF2 × PyMuPDF, que o produto já tem)
📊 `python fator_pymupdf.py 10 24 26 9 17 30` — só o extrator de texto muda; o leitor de linhas é o mesmo. Controle = Allianz condomínio.

| apólice | PyPDF2 (produto): págs c/ texto · linhas · Σ | PyMuPDF (`requirements.txt:56`): págs c/ texto · chars · linhas |
|---|---|---|
| **COND-ALLI (controle)** | 4 · **18 · 3.656,93 (fecha)** | 4 · 8.695 · **0** |
| AUTO-SURA | **0 (erro 19/19)** · 0 | **19 · 44.836** · 0 |
| AUTO-LIBE (Yelum) | **0 (erro 4/4)** · 0 | **4 · 13.348** · 0 |
| COND-TMAR | 7 · 0 | 7 · 8.922 · 0 |
| EMPR-ALLI | 4 · 0 | 4 · 5.339 · 0 |
| AUTO-HDI | 4 · 0 | 4 · 9.899 · 0 |

- **O PyMuPDF recupera o TEXTO de Sura e Yelum** (onde o PyPDF2 falha inteiro) — então a falha de P3 é do extrator, não do PDF.
- **Mas a linha de controle cai de 18 para 0 linhas com o PyMuPDF**: o regex do produto foi escrito sobre o DIALETO do PyPDF2
  (CLAUDE.md §9.4, "motor de regex tem dialeto"). Trocar o extrator sem trocar o leitor **desligaria** as 11 apólices que hoje fecham.
- E nenhum dos dois extratores faz o regex ler Tokio, Allianz EMPR ou HDI AUTO. **Conclusão do fator: o gargalo é o leitor de linhas, não o
  texto.** O texto existe em 27/28 PDFs (só o escaneado da Porto não tem camada de texto).

---

## 4. Comparação das FONTES, por serviço

| fonte | completa? | estável? | custo / latência | serve para |
|---|---|---|---|---|
| **API estruturada CORP** (`/documento`, `/itens`) | RE: **não** (0/24 fecha; faltam 4–6 coberturas por apólice, laudo anterior §4.3). AUTO: **quase** (4/8 fecha, 6/8 ≥ 90 %) | formato estável; mas `/itens` sem `data` dá 404 antes do início (produto chama sem `data`, `infocap_connector.py:3447`); prêmio de `/itens` em Allianz EMPR passa de 100 % (148–209 %) — semântica não confiável | grátis, ~1–4 s, cache 180 s | parcela, quitação, status, vigência, renovação, sinistro (**vence sempre**, `reconciliar`); placa/chassi/FIPE do AUTO; endereço/atividade do RE; **esqueleto e conferência** |
| **PDF do CORP** (`url_apolice` → `/documento_anexos`) | **sim** — é o contrato (Σ fecha ao centavo onde foi lido) | o ARQUIVO é estável (congela na emissão; muda por endosso); o LINK expira em ~1 h → baixar uma vez e guardar por hash (já é assim). Existe em 28/32 | download ~3 s; texto 0,1 s; **leitura estruturada hoje: regex grátis que só cobre 2 layouts**; com modelo 💭 ~US$ 0,001–0,01 por apólice (≈9 mil chars), uma vez por hash; visão para escaneado 💭 ~US$ 0,003/página (📊 US$ 0,0026/imagem medido) | coberturas, LMI, franquia, cláusulas, exclusões, plano de assistência, processo SUSEP → condição geral. Atendimento, chat, renovação de RE |
| **PDF/foto enviado pelo cliente** | sim, se legível | depende do cliente (foto torta, só a 1ª página); não há locator nem prêmio do CORP para conferir | mesmo leitor; foto exige visão | QCM (133-B), cotação no chat (132), membro pelo WhatsApp, corretora sem sistema de gestão (`PdfOnlyProvider`) |
| **Portal da seguradora** | parcial e por produto (ex.: catálogo de peças de vidros) | frágil (token expira, layout muda — ver EXTRA-001.10.1) | robô, segundos a minutos | só o que o acionamento daquele portal precisa; **não é fonte de ficha** |

**INFERÊNCIA — "o caminho melhor é mais estável?"** Como FONTE, sim: o PDF é o contrato e não depende do cadastro do corretor (o
`/itens` é digitado/importado e incompleto). Como LEITURA, hoje não: o regex quebra a cada layout novo (2 de ~8 seguradoras), e o
PyPDF2 falha inteiro em 2 de 27 PDFs. A estabilidade vem de três coisas que já existem pela metade: **guardar o PDF por hash** (feito),
**o juiz automático do fechamento de prêmio** (existe na porta — `_contador_de_premio` —, mas só acende sobre o cadastro) e **um leitor
que não dependa de layout** (não existe).

---

## 5. FATO + INFERÊNCIA — onde o produto usa uma estrutura PIOR

| # | onde | o que é pior | evidência |
|---|---|---|---|
| P1 | **anexo no WhatsApp e no chat** (L7, L8) | PDF da apólice vira **texto cru truncado em 20 mil chars** colado na mensagem — sem ficha, sem origem por campo, sem conferência, sem redação de CPF no extrator (guarda posterior não medido); é um **segundo leitor** de apólice ao lado do L1 | `webhook.py:3317-3325`, `vision_service.py:48,152`, `chat.py:829-841`; 📊 2/6 documentos "não foi possível ler" |
| P2 | **leitor de linhas = regex de 2 layouts** | 11/32 apólices lidas inteiras; 0 em Tokio, Allianz EMPR, Alfa, HDI AUTO | §3 |
| P3 | **PyPDF2 sem tolerância por página** | Sura e Yelum: o pipeline inteiro cai, nem o texto chega | §3.1, `document_service.py:397-399` |
| P4 | **só `url_apolice`** | `/documento_anexos` (o caminho que o FATO NOVO mediu) não é consultado | `infocap_connector.py:3666-3690`; 📊 +1/32 |
| P5 | **docling síncrono dentro de `async`** e devolvendo 1 página | o fallback bloqueia o laço do servidor até `DOCLING_MAX_WAIT=600 s` (`config.py:146`) e perde o nº da página que a evidência cita | `policy_document_evidence_service.py:1022-1038, 836` (INFERÊNCIA sobre o bloqueio: lida, não medida) |
| P6 | **teto de 60 itens** | apólice empresarial de 105 páginas: 60 itens, 6 linhas, 7 % do prêmio | `:51`; EMPR-TMAR-16 |
| P7 | **nada registra a leitura** | `documents.metadata` vazio 21/21; tool não guarda `document_status` → taxa de sucesso em produção **não mensurável** | §2 |
| P8 | **renovação não usa a ficha** | `de_apolice` só AUTO e só em teste; proposta recebe a apólice atual por JSON digitado; RE (E14) sem caminho | `pedido.py:525,548`, `comando_proposta.py:58` |
| P9 | **QCM descarta a apólice** | correto HOJE (B1), mas a 133-B precisa de um leitor — e o risco é nascer um terceiro | `canal/conversa.py:766-797` |
| P10 | **`/itens` sem `data`** | 404 em apólice que ainda não começou — exatamente a renovação | `infocap_connector.py:3447`; laudo anterior §6.4 |
| P11 | **capacidade declarada vencida** | `documento_oficial: "PARCIAL"` com nota de que não lê "os dois layouts" — hoje lê os dois e só eles | `infocap_policy_provider.py:727-735` |

---

## 6. RECOMENDAÇÃO

### 6.1 A decisão
| opção | nota | por quê |
|---|---|---|
| **A. Ficha única = a `Apolice` que já existe** (porta `PolicyDataProvider` + `reconciliar`), alimentada por **UM leitor de documento** (o `policy_document_evidence_service`, com motor novo dentro), consumida por atendimento, chat, renovação, cotação e QCM | **90** | zero motor paralelo (CLAUDE.md §5); a regra de quem vence já está escrita e testada (`reconciliar`); o `PdfOnlyProvider` já é a vaga do PDF do cliente; o cache por hash já é durável |
| B. A 130-B como extrator NOVO de "documento de seguro" só para WhatsApp/QCM/chat | 35 | seria o 4º/5º leitor; duplicaria cache, origem e reconciliação; o atendimento continuaria com o regex de 2 layouts |
| C. Só a API estruturada para tudo | 30 | RE incompleto (0/24 fecha); serve ao AUTO, não ao condomínio/empresarial |
| D. Modelo/visão em TODO PDF, sem regex | 60 | resolve layout, mas paga e espera onde o regex já acerta 100 % de graça (Allianz/HDI = a maior parte do RE da Resulta: 📊 Allianz é 161/227 COND e 178/255 RESI de 2026, laudo anterior §4.1) |

**Diferença grande → A já vem decidida.**

### 6.2 O que muda na SPEC-130-B (sem motor paralelo)
1. **Escopo redefinido:** de "leitor de apólice do WhatsApp" para **"o motor do leitor de documento de seguro do produto"**, dentro de
   `policy_document_evidence_service.py` (e não ao lado dele). Saída: `ApoliceDocumental` (+ os campos do risco que faltam nela hoje:
   placa/chassi/ano do AUTO; endereço/atividade/IS do RE; tipo de documento: apólice · proposta · cotação · CRLV, como a
   `SITUACOES…` §2.1 pede).
2. **Cascata com juiz automático**, por documento e uma vez por `content_hash`:
   `texto (PyPDF2 — o dialeto do regex —, e PyMuPDF quando o PyPDF2 falhar na página: §3.4)` → `regex de layout conhecido` → **fecha o prêmio?** sim: pronto, custo zero ·
   não: `modelo barato sobre o texto` (o "Luna" do plano) → fecha? · não: `visão por página` (escaneado/foto) → não fecha: **ficha com
   aviso + humano**. O juiz é o `_contador_de_premio` que já existe na porta, estendido ao DOCUMENTO (com o CORP) ou ao total impresso
   (PDF do cliente).
3. **Fontes do mesmo leitor:** (a) CORP: `url_apolice` → **`/documento_anexos`** (P4); (b) PDF/foto do cliente: o anexo do WhatsApp
   (L7), do chat (L8) e do QCM (L9) passam a entrar por `store_official_policy_document`/`PdfOnlyProvider` e **deixam de ir crus ao
   modelo** (P1); (c) a renovação lê a mesma `Apolice` (P8).
4. **Guardar o resultado:** a ficha lida (JSON) ao lado das páginas no MinIO e o resumo em `documents.metadata` (parser, linhas,
   fecha/não fecha, custo) — P7. Coluna existe; não é migration de estrutura (só escrita).
5. **Consertos baratos que entram junto:** tolerância por página com PyMuPDF de reserva (P3 — ⚠️ nunca trocar o extrator do caminho que
   o regex lê: o controle cai de 18 para 0 linhas, §3.4); docling fora do laço `async` e com páginas (P5); teto de itens
   por TIPO, não global (P6); `/itens` com `data=<inivig>` (P10); capacidade `documento_oficial` atualizada (P11).
6. **Bancada:** as 32 apólices desta medição (sem PII, por `locator`) viram a régua: 📊 hoje 11/32 → a meta é medida por ramo e por
   seguradora, com **Σ prêmio = prêmio líquido** como acerto automático (não depende de gabarito digitado). Acrescentar as fotos e os
   PDFs de cliente (sem prêmio do CORP) com gabarito manual.
7. **Frescor:** o PDF congela na emissão; o leitor guarda a data e o `content_hash`; endosso (`/documento_endossos`) troca o hash e
   relê. Parcela/status/vigência continuam do CORP (`reconciliar`).

### 6.3 O que NÃO muda
- Os relatórios comerciais (L11) e a cobrança (L6) continuam na API — não precisam de cobertura.
- O portal (L13) continua sendo do acionamento, não fonte de ficha.
- O QCM continua sem mandar o CONTEÚDO da mídia ao modelo (B1); o que muda é que a ficha estruturada, mascarada, passa a existir.

### 6.4 Pendências que este laudo deixa (para o gerente registrar)
- **P-LEITOR-01** 🤖 — `documento_oficial` lê inteira só Allianz RESI/COND e HDI COND (📊 11/32). Destrava: 130-B no escopo da §6.2.
  Custo de esquecer: o atendimento responde cobertura de Tokio/HDI-auto/empresarial só com o `/itens` incompleto.
- **P-LEITOR-02** 🤖 — PyPDF2 relança erro de página e derruba o pipeline (Sura, Yelum: 2/27); o PyMuPDF lê os dois (§3.4). Barato;
  pode entrar antes da 130-B, como RESERVA por página (não como troca).
- **P-LEITOR-03** 🤖 — anexo do WhatsApp/chat vai cru ao modelo, sem ficha e sem redação (P1).
- **P-LEITOR-04** 🤖 — sem telemetria da leitura (P7): hoje não se sabe a taxa de sucesso em produção.

---

## 7. Reprodução
```
cd scratchpad/ic
python medir_leitor.py 8        # 32 apólices → _medir_leitor.out / _medir_leitor.json (sem PII; PDFs só em memória)
python resumir_leitor.py        # §3.1 e §3.2
python rotulos.py 0 10 9        # rótulos lidos (nomes de cobertura, sem PII)
python fator_pymupdf.py 10 24 26 9 17 30   # §3.4 — um fator (extrator de texto), controle = 10
```
SQL (MCP, SELECT): `documents` agrupado por origem/corretora/mês; `tool_invocations` da capability
`operational.infocap.policy_lookup.read` (chaves de input/output, `cobertura.motivo`); `messages` com `[FIM DO DOCUMENTO]`;
`token_usage_logs` `service_type='vision'`; `multicalculo_pedidos` por origem.
