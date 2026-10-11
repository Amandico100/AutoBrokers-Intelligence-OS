# SPEC-130-B — A ficha única da apólice: um leitor só, que lê qualquer seguradora e diz quando não leu

> **PROPOSTA DE PLANEJAMENTO · v0.1 · 11/10/2026** · agente de síntese do gerente (Opus 5.5), branch `investigacao/2026-10-11-mapa`,
> base `ac0a6fd`. **Não executa nada agora.** O chat que a executar escreve a SPEC executável a partir desta proposta, no rito do
> protocolo v13 (CRÍTICO, §3 abaixo). **Substitui** o bloco "130-B" do [`PLANO-MESTRE-MULTICALCULO.md`](../programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md)
> (§SPEC-130, "Extrator apólice → ficha") e o item 1 do §2 de [`SITUACOES-DE-ENTRADA-DA-COTACAO.md`](../programa-multicalculo/SITUACOES-DE-ENTRADA-DA-COTACAO.md)
> onde discordar. A mudança de escopo está em `CHANGE-ADDENDA.md` (11/10/2026, ⏳ PROPOSTA).
> Fonte principal: [`LAUDO-LEITURA-DE-APOLICE.md`](../programa-multicalculo/131-0/LAUDO-LEITURA-DE-APOLICE.md) (§3 a medição, §5 os
> defeitos, §6 a recomendação). Resumo ao Founder: [`MAPA-DE-POSSIBILIDADES…`](../programa-multicalculo/131-0/MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md) §(i).
> Legenda: **FATO** (arquivo:linha em `ac0a6fd`, tabela ou comando) · **INFERÊNCIA** · **RECOMENDAÇÃO** · 📊 medido · 💭 ilustrativo.

---

## 0. Em uma página

**O que era:** "o leitor de apólice da cotação" — um extrator NOVO de foto/PDF para a 132 (chat) e a 133-B (Quem Cobra Menos).

**O que passa a ser:** **o motor do leitor de documento de seguro do produto inteiro**, trocado DENTRO da peça que já existe
(`policy_document_evidence_service` + a porta `PolicyDataProvider`), e a **ficha única da apólice** (`Apolice`/`ApoliceDocumental` +
`reconciliar`, que também já existem) passa a ser consumida por **atendimento, chat, renovação, cotação e Quem Cobra Menos**.

**Por quê (FATO, 📊 11/10, leitor REAL do produto sobre 32 apólices reais da janela de renovação):**
1. O produto **já lê o PDF do CORP** no chat e no atendimento (📊 21 PDFs guardados, 21/21 `completed`). A fonte é boa: o PDF existe
   em **28/32** e, onde foi lido, a soma das coberturas fecha com o prêmio **ao centavo**.
2. O **leitor** é que falha: regex de 2 layouts. Fecha a apólice inteira em **11/32** (só Allianz RESI/COND + HDI COND); Tokio, Allianz
   EMPR, Alfa, HDI AUTO = 0 linhas; Sura e Yelum **derrubam o pipeline** (PyPDF2 relança erro de página); Porto EMPR escaneado = 0 texto.
3. A API estruturada não substitui: `/itens` fecha o prêmio em **4/8 AUTO** e **0/24 RE**.
4. Há **quatro** leitores de documento de seguro; só **um** monta a ficha. O PDF do segurado no WhatsApp e no chat vai **cru** ao
   modelo (20 mil caracteres, sem ficha, sem conferência; 📊 2 de 6 "não foi possível ler").
5. **Nada registra a leitura** (📊 `documents.metadata` vazio em 21/21) → hoje a taxa de acerto em produção é **imensurável**.

**A decisão (LAUDO §6.1):** opção **A — ficha única no que já existe, motor novo dentro** — nota **90** × modelo em todo PDF 60 ×
leitor novo só para WhatsApp/QCM 35 × só a API 30. Abrir já, em chat novo: **92 × 40** o escopo antigo (D-1311-01).

**Pronto quando:** na bancada, a régua "**Σ prêmio das linhas = prêmio líquido do CORP (±2 %)**" sobe de 📊 **11/32** para a meta
por ramo do §4, **sem perder nenhuma das 11** (controle); toda leitura grava como leu e se fechou; e nenhum PDF de segurado vai cru
ao modelo.

---

## 1. O contrato

**Muda:**
- o MOTOR de `extract_policy_document_evidence` (`services/policy_document_evidence_service.py:622`): de "regex de 2 layouts" para
  **uma cascata com juiz automático** (§3.2);
- as FONTES que entram por ele (§3.3): `url_apolice` **+ `/documento_anexos`**, o anexo do WhatsApp e do chat, a mídia do QCM e a
  apólice da renovação;
- a `ApoliceDocumental` (`providers/policy_data_provider.py:641`) ganha o **tipo do documento** (apólice · proposta · cotação de outra
  corretora · CRLV) e os campos do risco que faltam (AUTO: placa, chassi, ano; RE: endereço, atividade, IS);
- a leitura passa a ser **registrada** (`documents.metadata`: parser, linhas, fechou/não fechou, custo, versão do leitor).

**Não pode mudar:**
- **a regra de quem vence** em `reconciliar` (`policy_data_provider.py:1606`): cobertura/limite/franquia/plano → o documento;
  parcela/status/vigência → o CORP. É testada e é o coração da ficha;
- **as 11 apólices que hoje fecham** (a linha de controle) — 🔴 trocar o extrator do caminho do regex as derruba (§2.3);
- o QCM **continua sem mandar o conteúdo da mídia ao modelo principal** (conserto B1 da 133-A); o que muda é que passa a existir a
  ficha estruturada e **mascarada**;
- relatórios comerciais (L11) e cobrança (L6) continuam na API — não precisam de cobertura;
- **nenhum motor paralelo** (CLAUDE.md §5): o modelo entra pelo **Model Router** (SPEC-116), o arquivo pelo `DocumentService`/MinIO, o
  índice pelo Qdrant que já existe; nenhum "extrator de documento" novo ao lado.

---

## 2. O que existe hoje (FATO — LAUDO §1–§5, conferido em `ac0a6fd`)

### 2.1 O fio de hoje (L1/L2)
`infocap_connector._extract_official_document_candidates` (`api/infocap_connector.py:3666`, só `url_apolice`/`url_proposta`) →
`_maybe_attach_official_policy_document_evidence` (`:2246-2340`) → `PolicyDocumentEvidenceService.ensure_official_policy_evidence`
(`policy_document_evidence_service.py:897`) → cache `find_official_policy_document` (`document_service.py:159`) → senão baixa e
`store_official_policy_document` (`document_service.py:233`, PyPDF2 `:378-399`, **relança** a exceção da página) →
`extract_policy_document_evidence` (`:622`, regex por linha, teto `MAX_EVIDENCE_ITEMS = 60` em `:51`) → se 0 evidência, docling
**síncrono** (`:1022-1038`, devolve 1 página, `:836`) → Qdrant → `apolice_documental_do_pack` (`providers/infocap_policy_provider.py:567`)
→ `reconciliar`. O juiz do prêmio já existe — `_contador_de_premio` (`policy_data_provider.py:1847`) —, mas só acende sobre o CADASTRO.
O adaptador para o PDF do cliente também já existe: `PdfOnlyProvider` (`providers/pdf_only_policy_provider.py:135`).

### 2.2 Os quatro leitores
| | onde | o que faz hoje | depois da 130-B |
|---|---|---|---|
| L1/L2 | chat e atendimento (`agents/tools/infocap_tool.py:780,1010,1930`) | PDF do CORP → regex → ficha | mesmo fio, **motor novo** |
| L7 | anexo do WhatsApp (`api/webhook.py:3310-3325` → `services/vision_service.py:152`) | texto cru, 20.000 chars, sem redação (`vision_service.py:48`) | entra pelo **mesmo leitor**; ao modelo só a ficha mascarada |
| L8 | anexo do chat (`api/chat.py:829-841`) | texto cru ao modelo | idem L7 |
| L9 | QCM (`services/canal/conversa.py:766-797`) | guarda só a referência | o mesmo leitor monta a ficha mascarada; a 133-B a consome |
| L10 | renovação (`services/multicalculo/pedido.py:525` `de_apolice`) | só AUTO e só em teste (📊 0 chamadas em `app/`) | lê a mesma `Apolice` (a 131 consome) |

### 2.3 A linha de controle que manda no desenho (📊 LAUDO §3.4)
| apólice | PyPDF2 (produto) | PyMuPDF |
|---|---|---|
| COND-ALLI (controle) | **18 linhas, fecha** | **0 linhas** |
| AUTO-SURA / AUTO-Yelum | **erro em 19/19 e 4/4 páginas** | 19 e 4 páginas com texto, 0 linhas |
| COND-TMAR · EMPR-ALLI · AUTO-HDI | 0 linhas | 0 linhas |

→ **O regex tem o dialeto do PyPDF2** (CLAUDE.md §9.4). PyMuPDF entra só como **reserva por página** onde o PyPDF2 falha; nunca como
troca. E nenhum extrator resolve Tokio/Allianz EMPR/HDI AUTO: **o gargalo é o leitor de linhas, não o texto.**

---

## 3. O desenho

### 3.1 Uma ficha, um leitor, uma vez por arquivo
Cada documento é lido **uma vez por `content_hash`** (o cache durável já existe). O resultado — a ficha em JSON, com **origem e
confiança por campo** (página, trecho, qual degrau da cascata leu) — fica ao lado das páginas no MinIO, e o resumo em
`documents.metadata`. Todo consumidor pede a ficha à porta; ninguém relê o PDF por conta própria.

### 3.2 A cascata, com o juiz automático
```
texto      PyPDF2 por página (o dialeto do regex) · PyMuPDF só na página em que o PyPDF2 falhar · página sem texto → marcada
   ↓
regex      os layouts conhecidos (Allianz, HDI…) — custo zero
   ↓
JUIZ       Σ prêmio das linhas = prêmio líquido (do CORP; ou o total impresso no PDF, quando não houver CORP), ±2 %
   ├─ fecha → pronto (custo zero)
   ↓ não fecha
modelo     o mais barato do Model Router que passar na bancada (Luna é o candidato do plano), sobre o TEXTO já MASCARADO
   ↓ JUIZ de novo
visão      só as páginas sem texto (escaneado, foto), por página (📊 US$ 0,0026 por imagem medido no produto)
   ↓ JUIZ de novo
humano     a ficha sai com o aviso "não fechou: X de Y" e a origem de cada campo; o consumidor decide (atendimento: não afirma cobertura)
```
- O juiz é o `_contador_de_premio` **estendido ao documento** — não um juiz novo.
- Documento **sem prêmio conferível** (CRLV, cotação de outra corretora sem total): o juiz vira **validação de forma** (dígitos do
  CPF, placa, datas coerentes) e a confiança cai; vale o gabarito manual da bancada (§4).
- O **docling** sai do laço `async` (thread/fila do Work OS que já existe) e passa a devolver as páginas, não uma (P5).
- O teto de 60 itens passa a ser **por tipo de documento** (P6: 📊 a apólice de 105 páginas parou em 7 % do prêmio).

### 3.3 As fontes, todas pelo mesmo leitor
| fonte | como entra | o que tem para conferir |
|---|---|---|
| CORP | `url_apolice` → **`/documento_anexos`** quando não houver (📊 +1/32: o PDF da Porto EMPR só está nos anexos) | o prêmio líquido do `/documento` |
| anexo do WhatsApp (segurado) | `webhook.py` deixa de colar o texto cru e chama o leitor (`PdfOnlyProvider`) | o total impresso; o CORP, se o CPF casar com a carteira daquela corretora |
| anexo do chat (corretor) | `chat.py` idem | idem |
| mídia do QCM | a referência guardada passa pelo leitor depois do "sim"; ao modelo da conversa, só a ficha mascarada | o total impresso |
| renovação | a 131 pede a `Apolice` da porta, com `/itens?data=<inivig>` (P10) | o CORP |

### 3.4 Frescor e endosso
O PDF congela na emissão. Endosso (`/documento_endossos`) gera documento novo → novo hash → nova leitura; a ficha da renovação usa o
**item na data** (📊 7/7 trocas de veículo mudam o item, LAUDO-CORPAPI §4.1). Parcela/status/vigência continuam vindo do CORP.

### 3.5 Dados pessoais
O texto vai ao modelo **depois** de mascarar CPF/CNPJ, telefone, e-mail e endereço (o produto já tem o mascarador do canal;
**reusar**, não escrever outro). Os campos pessoais que a ficha precisa (CPF para casar com a carteira) são extraídos pela regra local,
nunca pelo modelo. A ficha guarda CPF só mascarado onde for mostrada; inteiro só onde a SPEC-131 já guarda (cifrado).

---

## 4. A bancada — a régua que não depende de gabarito digitado

- **As 32 apólices da medição de 11/10** (8 por ramo — RESI, COND, EMPR da carteira de RE e AUTO da carteira de auto —, da janela de
  renovação, semente 1311), identificadas só por `locator` com hash, **sem PII** no repositório; os PDFs ficam no MinIO da corretora
  dona, nunca em `backend/tests`.
- **Régua automática:** Σ prêmio das linhas = prêmio líquido do CORP (±2 %), por ramo e por seguradora. 📊 Hoje: RESI 6/8 · COND 5/8 ·
  EMPR 0/8 · AUTO 0/8 = **11/32**.
- **Metas propostas** 💭 (a SPEC executável confirma no BLOCO 0): as 11 de hoje **intactas** (controle) · RESI e COND ≥ 7/8 · EMPR ≥ 5/8
  · AUTO ≥ 5/8 (o AUTO tem o `/itens` como segunda conferência) · **0** pipeline caído (Sura/Yelum) · o escaneado da Porto lido pela visão.
- **Gabarito manual (pequeno):** 5–10 PDFs/fotos de segurado, 5–10 cotações de outra corretora e 5–10 CRLVs (SITUACOES §2), com os
  campos esperados escritos à mão, autorizados pelo Founder (ele liberou até 15 apólices por ramo em 10/10).
- **Mutação obrigatória dos guardas novos:** (1) trocar o extrator do caminho do regex por PyMuPDF → a régua tem de cair de 11 para
  menos (📊 a controle cai 18 → 0 linhas); (2) desligar o juiz → uma ficha que não fecha tem de passar como "lida" e o guarda tem de
  ficar VERMELHO; (3) mandar o texto sem máscara → o guarda de PII fica vermelho.
- **Custo** 💭: 32 apólices × modelo barato ≈ US$ 0,01 cada só nas que não fecham (21) ≈ **US$ 0,25 por rodada**; visão ≈ 16 páginas
  escaneadas × US$ 0,0026 ≈ **US$ 0,05**. Livro-caixa do programa: 💭 saldo US$ 3,93. Teto proposto para a SPEC: **US$ 1,50**,
  escrito no livro-caixa antes de cada rodada.

---

## 5. Os consertos que entram junto (as pendências que esta SPEC drena)

| pendência | o que é | entra como |
|---|---|---|
| **P-LEITOR-01** | o leitor fecha só 11/32 | o coração (§3.2) |
| **P-LEITOR-02** | PyPDF2 relança erro de página e derruba o pipeline (Sura, Yelum) | reserva por página (U2) — barato, pode ir primeiro |
| **P-LEITOR-03** | anexo do WhatsApp/chat cru ao modelo, sem ficha e sem redação | U4 |
| **P-LEITOR-04** | nenhuma telemetria da leitura | U2 (`documents.metadata` + `document_status` no `output_summary` da tool) |
| P5 · P6 · P10 · P11 do laudo | docling no laço async · teto de 60 · `/itens` sem data · capacidade `documento_oficial` vencida (`infocap_policy_provider.py:727-735`) | U3 / U5 |

---

## 6. Unidades e fatias sugeridas (a SPEC executável decide)

| unidade | entrega | arquivos (para provar DISJUNÇÃO) |
|---|---|---|
| **U0 · BLOCO 0** | remedir as 32 (as 11 ainda fecham?), confirmar as metas, achar o mascarador do canal a reusar, medir o Model Router com 1 apólice | só leitura |
| **U1 · o teste do fio** | atravessa CORP → leitor → ficha → `reconciliar` → tool, com o MOTOR real e dublê só na borda (o download); nasce VERMELHO | `backend/tests/test_spec130b_o_fio.py` |
| **U2 · texto tolerante + telemetria** | PyMuPDF por página como reserva; `documents.metadata`; `document_status` na tool | `services/document_service.py` · `agents/tools/infocap_tool.py` (só o `output_summary`) |
| **U3 · a cascata** | juiz estendido, modelo via Model Router com máscara, visão por página, aviso humano; docling fora do laço; teto por tipo | `services/policy_document_evidence_service.py` · `providers/policy_data_provider.py` |
| **U4 · as fontes** | `/documento_anexos`; WhatsApp, chat e QCM pelo mesmo leitor | `api/infocap_connector.py` · `api/webhook.py` · `api/chat.py` · `services/vision_service.py` · `services/canal/conversa.py` |
| **U5 · renovação e capacidade** | `/itens?data=`; `de_apolice` lê a ficha (AUTO e RE); `documento_oficial` atualizada | `providers/infocap_policy_provider.py` · `services/multicalculo/pedido.py` |
| **U6 · a bancada** | a régua por ramo/seguradora e os gabaritos manuais | `backend/tests/corpus/bancada/…` · `backend/scripts/` (novo script de régua) |

**Paralelismo real:** U2 ‖ U4 ‖ U6 (arquivos disjuntos); U3 depois de U2 (consome o texto por página); U5 depois de U3 (consome a
ficha). **Costura:** uma fatia final em que a saída REAL de U3 alimenta U4 e U5 sobre as 32. 💭 5 fatias, 1 chat.

---

## 7. Nível e risco

RISCO = alcance **3** (o atendimento responde cobertura ao SEGURADO) + reversibilidade **3** (mensagem sai do prédio) + frequência **2**
(todo atendimento que fala de cobertura) = **8** → **CRÍTICO**. SUPERFÍCIE **2** (vários comportamentos em lugares listados). Piso
§3.2 também: dados pessoais vão a um modelo. Executor Opus 5.5 `xhigh`; juiz Opus 5.5 ‖ red team Opus 5.5; lente de PII por gatilho.

---

## 8. Decisões (para a SPEC executável confirmar; notas 0–100)

| # | decisão | nota | contra |
|---|---|---|---|
| D-130B-01 | a ficha única é a `Apolice`/`ApoliceDocumental` que já existe; o motor muda dentro do `policy_document_evidence_service` | **90** | leitor novo 35 (LAUDO §6.1) |
| D-130B-02 | o juiz é o fechamento do prêmio (o `_contador_de_premio` estendido), não um gabarito digitado | **88** 💭 | gabarito manual para tudo 50 💭 (não escala por seguradora) |
| D-130B-03 | regex primeiro, modelo só no que não fecha, visão só em página sem texto | **85** 💭 | modelo em tudo 60 (LAUDO §6.1 D) |
| D-130B-04 | PyMuPDF só como reserva por página; nunca troca o extrator do regex | **92** 💭 | trocar o extrator 20 💭 (📊 controle 18 → 0) |
| D-130B-05 | o anexo do segurado nunca mais vai cru ao modelo: só a ficha mascarada | **90** 💭 | manter o texto cru 30 💭 |
| D-130B-06 | a bancada são as 32 da medição + gabarito pequeno de cotação/CRLV/foto; a cotação de outra corretora e o CRLV entram como TIPOS (SITUACOES E5/E6) | **80** 💭 | só apólice 55 💭 |

As notas com 💭 são do gerente-síntese (não vieram de um laudo); a SPEC executável as reconfirma no BLOCO 0.

---

## 9. Riscos

| risco | o que se faz |
|---|---|
| trocar o extrator derruba as 11 que hoje fecham | a linha de controle é guarda de mutação (§4) |
| o modelo "inventa" uma cobertura e a soma fecha por acaso | o juiz confere a soma E cada linha precisa de origem (página + trecho); linha sem trecho não conta |
| CPF/endereço vão ao provedor do modelo | máscara antes do modelo (§3.5) + guarda de PII com mutação |
| custo sobe sem ninguém ver | `documents.metadata` guarda o custo; teto escrito no livro-caixa |
| a leitura demora no atendimento | lida uma vez por hash, fora da conversa (Work OS); sem ficha, o atendimento não afirma cobertura |
| PDF de outra corretora/tenant | o leitor recebe `company_id` e a conexão; o cache já é por corretora + conexão (`document_service.py:159-219`); teste de isolamento com 2 corretoras reais (CLAUDE.md §7) |

---

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

1. **https://cloud.google.com/document-ai/docs/overview** — Google Document AI: processadores que **classificam** o tipo de documento e
   depois **extraem** campos com **confiança por campo**, com revisão humana quando a confiança é baixa. · **Modelamos:** classificar
   primeiro (apólice · proposta · cotação · CRLV) e confiança por campo com o degrau "humano". · **Rejeitamos:** o serviço (dado
   pessoal sai para outro provedor, custo por página, e seria um extrator paralelo — CLAUDE.md §5). · **Juiz:** abrir a página e conferir
   "classifier" + "confidence" + "human review"; no código, procurar o tipo e a confiança na `ApoliceDocumental`.
2. **https://docs.aws.amazon.com/textract/latest/dg/queryresponse.html** — AWS Textract Queries: perguntas em linguagem natural ao
   documento ("qual o prêmio líquido?") que devolvem a resposta **com a página e a posição**. · **Modelamos:** toda linha da ficha cita
   página e trecho (origem por campo). · **Rejeitamos:** o serviço, pelo mesmo motivo do item 1. · **Juiz:** linha sem página/trecho
   tem de ser recusada pelo guarda.
3. **https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview** — Azure Document Intelligence: modelo de
   **layout** genérico (tabelas) + modelos **por formulário** treinados, compostos num só. · **Modelamos:** "layout conhecido primeiro
   (regex por seguradora), genérico depois (modelo)". · **Rejeitamos:** treinar modelo por seguradora (8+ layouts, poucas amostras;
   o juiz do prêmio dispensa o treino). · **Juiz:** a cascata tem o degrau regex antes do modelo, e a régua mostra o custo zero nas
   que o regex fecha.
4. **https://pymupdf.readthedocs.io/en/latest/recipes-text.html** — PyMuPDF: extração de texto **página a página**, robusta onde o
   PyPDF2 falha; já está no `requirements.txt` do produto (usado na condição geral). · **Modelamos:** reserva por página. ·
   **Rejeitamos:** trocar o extrator do regex (📊 controle 18 → 0 linhas). · **Juiz:** rodar a mutação "PyMuPDF no lugar do PyPDF2"
   e ver a régua cair.
5. **https://docs.claude.com/en/docs/build-with-claude/pdf-support** — o modelo lê o PDF como texto **e** imagem de cada página. ·
   **Modelamos:** o degrau "visão por página" só para página sem camada de texto. · **Rejeitamos:** mandar o PDF inteiro a cada
   pergunta (custo e PII) — a leitura é uma vez por hash, mascarada. · **Juiz:** o custo por apólice na `documents.metadata` e a
   contagem de páginas enviadas à visão (só as sem texto).

---

## 11. O QUE SAIU (fica fora, com o porquê)

- **A página dos outros ramos** (130-C, D-129C-08).
- **A cotação no chat e o QCM ampliado** (132, 133-B) — aqui só a ficha pronta e mascarada.
- **Cadastrar a proposta na InfoCap pelo INCORP** — é a SPEC "Emissão e registro" (MAPA §f), e espera a homologação da InfoCap.
- **Treinar modelo por seguradora** — o juiz do prêmio dispensa (§10 item 3).
- **A condição geral** (L12) — outro documento; não muda.

---

## 12. BLOCO 0 (o que a execução remede antes da primeira linha)
1. As 11 ainda fecham em `HEAD`? (rodar o leitor do produto sobre as 32, como o LAUDO §7 — os scripts do laudo ficaram no rascunho da
   sessão de 11/10, `…/scratchpad/ic/medir_leitor.py`; se não existirem mais, recriar pelo critério do §4.)
2. Quantos PDFs novos entraram em `documents` desde 26/09, e com qual resultado.
3. Onde está o mascarador do canal (a 133-A mascara CPF antes do modelo) — reusar.
4. O Model Router tem rota para "leitura de documento"? (SPEC-116/124: a visão já mora no Luna) — uma chamada, com o custo anotado.
5. `/itens?data=<inivig>` responde nas 32? (P10)

---

## 13. PROMPT DE ABERTURA (cole num chat NOVO do Claude Code, modelo Opus 5.5)

```
Você é o GERENTE da SPEC-130-B · A ficha única da apólice, do AutoBrokers Intelligence OS. Responda em pt-BR, em linguagem de
gente. Árvore: C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX. Python de dentro de backend/, PYTHONIOENCODING=utf-8.

0. PREFLIGHT (CLAUDE.md §2): git fetch origin · git rev-list --count HEAD..origin/main (TEM de ser 0; senão pare e pergunte) ·
   git rev-list --count origin/main..HEAD · git switch -c spec/130-B-a-ficha-unica origin/main · git rev-parse --short HEAD ·
   git status --short. Arquivos .TXT soltos em docs/canon/ são do Founder: não commite, não apague.

1. LEITURA, nesta ordem e nada mais:
   CLAUDE.md inteiro · docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md inteiro (UMA vez) · docs/canon/GLOSSARIO.md ·
   docs/canon/specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md INTEIRA (é a proposta que você converte em SPEC) ·
   docs/canon/programa-multicalculo/131-0/LAUDO-LEITURA-DE-APOLICE.md §1, §3, §5, §6 ·
   docs/canon/PENDENCIAS.md SÓ por número: P-LEITOR-01..04, P-1310-02 · FOUNDER-DECISIONS.md SÓ D-1311-01..06 e D-131-0-26 ·
   docs/canon/MIGRATIONS-AUTHORITY.md só se houver SQL (a proposta não prevê migration de estrutura).

2. O OBJETIVO: um leitor só de documento de seguro, dentro do policy_document_evidence_service, com a cascata texto → regex →
   fecha o prêmio? → modelo barato (Model Router, texto mascarado) → visão por página → humano; a ficha única (Apolice +
   reconciliar) consumida por atendimento, chat, renovação e QCM; o anexo do segurado nunca mais cru ao modelo; toda leitura
   registrada. Régua: Σ prêmio das linhas = prêmio líquido do CORP (±2 %) nas 32 apólices da bancada — hoje 11/32 — sem perder
   NENHUMA das 11 (controle). Nenhum motor paralelo (CLAUDE.md §5).

3. O RITO (protocolo v13, nível CRÍTICO — RISCO 8): EXECUTION CARD + O FIO + BLOCO 0 (§12 da proposta) → builders Opus 5.5 xhigh
   frescos, um por fatia, EM PARALELO onde os arquivos são disjuntos (U2 ‖ U4 ‖ U6), em série U3 → U5, e uma fatia de COSTURA →
   o teste do fio é a 1ª entrega e nasce vermelho → verificador mecânico com as 3 mutações da §4 → juiz Opus 5.5 ‖ red team
   Opus 5.5 (frescos, cegos, UMA vez) + lente de PII → conserto único → bateria em 2º plano contra
   docs/canon/reports/BATERIA-LINHA-DE-BASE.txt → relatório (template) → git push origin HEAD:main com a saída colada →
   agente atualizador de documentos (ESTADO-DO-PROGRAMA, PENDENCIAS, FOUNDER-DECISIONS, TAREFAS-DO-FOUNDER, painel).

4. VERBA: teto US$ 1,50 em modelo para a bancada, escrito no livro-caixa do ESTADO-DO-PROGRAMA §3 ANTES de cada rodada.

5. DADOS: as apólices da bancada são de clientes reais, autorizadas pelo Founder para teste. Nenhum CPF, nome, placa, endereço
   ou nº de apólice em código, teste, relatório ou chat — só locator com hash. Os PDFs ficam no MinIO da corretora dona.

6. Pare SÓ pelas 8 condições do CLAUDE.md §10. Decida o resto com nota 0–100 e registre. A última mensagem é o relatório
   completo ao Founder (CLAUDE.md §12.2), em linguagem de gente.
```
