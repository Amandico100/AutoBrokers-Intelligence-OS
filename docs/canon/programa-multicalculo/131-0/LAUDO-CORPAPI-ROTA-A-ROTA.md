# LAUDO — CorpAPI (InfoCap/CorpNuvem): a coleção Postman inteira, medida com o login da Resulta

> Modo INVESTIGAÇÃO (protocolo §3.3) · read-only · 11/10/2026 · só GET (+ POST /login) · em SÉRIE
> Ferramenta: `scratchpad/ic/ic.py` + `ic/probe.py` (forma do envelope) · coleção salva em `scratchpad/corpapi-postman.json` (66.660 bytes)
> Nenhum nome, CPF/CNPJ, telefone ou e-mail impresso — só contagens, nomes de CAMPOS e formas.
> Arquivo de trabalho com dado de cliente (`_renov_rows.json`) foi APAGADO ao fim.

---

## 0. A coleção

📊 FATO — `python urllib GET https://documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi` → 200, 66.660 bytes.
`info.name = CorpAPI`, `publishDate = 2025-03-14`, schema v2.0.0. **51 requisições em 13 pastas**
(Autenticação · Documentos/Produção · Cliente · Endereço · Email · Telefone · Negociações · Produtores · Ramos · Sinistro · BI · InCorp).
Só **3 requisições têm exemplo de resposta** (`/documento`, `/producao`, `/renovacoes`); nenhuma tem descrição de parâmetro.
A única descrição em texto da coleção inteira é `POST /cliente`: *"Insert de clientes. Pode ser inserido também telefones, emails e enderecos."*

### 0.1 Os quatro itens destacados pelo Founder

| id | rota | o que é |
|---|---|---|
| `43f1e9e4-0785-495d-a7ff-0e3f69cb1553` | `GET /renovacoes?dt_ini&dt_fim&qtd_pag&pag&ordem&orientacao&texto&cancelado&resgates&codcli&codram&codcia` | A carteira a renovar (filtra **FIMVIG**). Detalhe em §3. |
| `49d1b342-dde0-43f3-80e9-735fc0bc0049` | `GET /documento_anexos?codfil&nosnum` | **Os PDFs da apólice** (apólice, proposta, boleto…) como URL S3 pré-assinada. §6. |
| `864a6cd2-f97f-424f-bae8-92263e82fab9` | `GET /documento?codfil&nosnum` | A apólice inteira: 84 campos + `parcelas[]` + `prod_docs[]` + `historico[]` + `acompanhamento{}`. |
| `b192767c-c9c9-4a9a-b7f9-c1a67c4d1742` | `GET /producao?texto&dt_ini&dt_fim&ordem&orientacao&so_renovados&so_emitidos` | Lista de produção por período, com `renovacao_situacao` e `historico_imagem`. |

**`/renovacoes` (exemplo da doc)** campos: `codfil nosnum tipdoc codcli datemi fimvig nosnum_ren cancelado cliente nome_busca pessoa cic fone email seguradora ramo numapo pretot historico_imagem historico_hint renovacao_situacao sin_situacao situacao_txt dias_a_vencer produtor quant_produtores codopo situacao_multi oportunidade inivig`.
📊 Ao vivo a resposta tem **3 campos a mais** que a doc: `ramo_tipo`, `ramo_multi`, `prod_docs[]` (reduzido: `agente produtor automat ordem per_r val_r cod_age cod_pro`).

**`/documento`** (84 campos; ao vivo há também `historico[]` e `acompanhamento{}`, que a doc não mostra):
`acompanhamento = {negocio{codigo_negocio,datinc_negocio}, cotacao{codmulti,datinc_cotacao,ramo_multi,ramo_tipo}, proposta{numprop,datpro,url_proposta,importado_pelo_incorp}, emissao{numapo,datemi,url_apolice,bot_a_dthora,bot_emitido}, recebimento{…}, entrega{…}}`.
`historico[] = codfil nosnum tipdoc numapo numend inivig fimvig qtd_endossos nosnum_ren nosnum_endosso renovado`.
🔴 `emissao.url_apolice` vem preenchida com URL `corp-anexos.s3.amazonaws.com` — **o link do PDF da apólice já vem dentro de `/documento`**.

**`/producao`** campos: `codfil nosnum tipdoc seguradora ramo cliente_codigo cliente inivig fimvig numapo numend numprop datemi nosnum_ren bot_a_dthora sin_situacao cancelado historico_imagem renovacao_situacao`.
📊 Parâmetros medidos (set/2026, controle=242, controle repetido=242):
`so_emitidos=t` → 236 · `so_emitidos=f` → **6** (todos com `datemi` nulo = pendentes de emissão) · `so_emitidos=x` → 242 (todos).
`so_renovados` t/f/x/T/F → **242 sempre** (📊 sem efeito medido nesta janela).
Página padrão = **15 linhas**; aceita `qtd_pag`/`pag`. **Ignora** parâmetro desconhecido (`xyz=1` → 242) e `codfil`.

---

## 1. TODAS as rotas — status medido hoje (login Resulta, salvo indicação)

Legenda "usada": ✅ está na lista que o produto já usa · 🆕 NÃO está.
⚠️ A lista do gerente omite `/producao` e `/sinistros`, mas 📊 `backend/app/data/providers/infocap/infocap-schema-fingerprints.json` já os registra (linhas 441 e 553) — marcados ✅*.

| # | método rota | usada | status | envelope · nº | campos (nomes) |
|---|---|---|---|---|---|
| 1 | POST /login | ✅ | 200 | objeto | `codigo nome login email email_multi codfil p500..p602 p226 p212 p25 p51 p91 p282 p357 p227 p56 p9 p213 corp_mais_dashboard token chat_bot` |
| 2 | POST /logout | 🆕 | não testado (invalida sessão) | — | — |
| 3 | GET /documento | ✅ | 200 | `documento`·1 + `historico` + `acompanhamento` | ver §0.1 |
| 4 | GET /producao | ✅* | 200 | `producao`·242 (pág. 15) | ver §0.1 |
| 5 | GET /renovacoes | ✅ | 200 | `renovacoes`·99 (11/10–10/11) | ver §3 |
| 6 | GET /documentos | ✅ | 200 | `documentos`·275 (set/2026 por datinc) | `codfil nosnum tipdoc seguradora ramo cliente_codigo cliente inivig fimvig numapo numend sin_situacao cancelado historico_imagem renovacao_situacao datemi numprop` |
| 7 | GET /documento_anexos | 🆕 | 200 | `anexos`·4 | `nome tipo descricao datahora usuinc url indice_anexo` |
| 8 | GET /documento_endossos | 🆕 | 200 | `endossos`·35 (numa apólice com endosso) / `message` se não há | `codfil nosnum tipdoc inivig` |
| 9 | GET /itens | ✅ | 200 COND/RESI/EMPR · 404 RCPR, 1 VIND | `itens`·1 | (Resulta) `atividade bairro cancelado cep ci cidade clausulas cod_profissao codfil complemento cpf cpf_cnpj datnas … garantias inivig item loc nomseg nosnum numend proprietario rubrica telram tipo_imovel` · (AutoFleet AUTO) `veiculo placa chassi anofab anomod franquia bonus valmer fipe renavam … garantias[]{seguradora ramo garantia impseg taxa premio percom valcom agrucom valfran franquia}` |
| 10 | GET /cliente | ✅ | 200 | `cliente`·1 | `codfil codigo nome ativo cpf_cnpj datanas pessoa sexo email telefone cidade estado vigente observacoes profissao … dt_venchab enderecos[] emails[] telefones[] contatos` |
| 11 | GET /clientes | 🆕 | 200 | `clientes`·**15.047** (pág. 20; aceita qtd_pag/pag) | `codfil codigo nome ativo cpf_cnpj datanas pessoa sexo email telefone cidade estado vigente` |
| 12 | GET /cliente_cpf | ✅ | 200 | `cliente`·1 | igual /cliente sem `dt_venchab` |
| 13 | GET /cliente_anexos | 🆕 | 404 (cliente amostrado sem anexo) | — | — |
| 14 | GET /lista_clientes | ✅ | 200 (`message` se vazio) | `clientes` | — |
| 15 | GET /busca_cpf | 🆕 | 200 | `cliente`{} | `codfil codigo nome cpf_cnpj datanas sexo cod_estado_civil estado_civil emails telefones enderecos` |
| 16 | POST /cliente · DELETE /cliente | — | NÃO chamado (escrita) | — | corpo: `codfil nome ativo cpf_cnpj datanas pessoa sexo observacoes profissao estado_civil escolaridade usuinc enderecos[] emails[] telefones[]` |
| 17 | GET /cliente_ligacoes | ✅ | 200 | `{documentos{header,documentos}, negocios{…}, cotacoes{…}}` | docs: `… historico_imagem renovacao_situacao dat_inc nosnum_ren` |
| 18–26 | POST/PUT/DELETE /endereco /email /telefone | — | NÃO chamados (escrita) | — | — |
| 27 | GET /negocios_andamento | ✅ | 200 | `negocios`·2.465 | `codfil codigo codcli cliente status prioridade tipo tipo_neg ramo sit_multi val_premio val_c doc_codfil doc_nosnum produto_fimvig prox_aten_* codmulti inivig fimvig descricao_item situacao_multi oportunidade codram ramo_multi ramo_tipo multi_corp_mais` |
| 28 | GET /em_calculo | 🆕 | 200 (2010–2026: 23) · 404 (só 2026) | `negocios` | `… veiculo placa vigencia_ini vigencia_fim multi_corp_mais` |
| 29 | GET /negocios_finalizados | 🆕 | 200 | `negocios`·1 (2026) | `… calc_fimvig_anterior …` |
| 30 | GET /negocio_anexos | 🆕 | 404 (negócio amostrado) | — | — |
| 31 | GET /negocio | ✅ | 200 | `negocio`·1 | 56 campos, incl. **`codusu_responsavel`** (int), `usuinc usualt usuini_negociacao usufim_negociacao produto_nosnum produto_fimvig motivo_perda codcamp campanha atendimentos[]{codigo codfil codopo tipo_atendimento data hora canal datinc usuinc descricao realizado tipo}` |
| 32 | POST /negocio · DELETE /negocio | — | NÃO chamados | — | corpo inclui `codusu_responsavel`, `usuinc`, `etapa`, `status`, `tipo` |
| 33 | GET /agentes | ✅ | 200 | `agentes`·**1** (codigo 1) | `codigo nome` |
| 34 | GET /prod_docs | ✅ | 200 | `prod_docs`·3–6 | `codfil nosnum codage codpro perpart indireto ordem datrep_prot campo_base_r base_r per_r val_r forma_repasse_r *_rc *_ra *_rp cod_com_ind taxa_repasse nome_agente nome_produtor` |
| 35 | GET /produtores | ✅ | 200 | `produtores`·119 (AutoFleet 105) | `codigo nome` |
| 36–38 | POST/PATCH/DELETE /prod_docs | — | NÃO chamados | — | corpo: `codfil nosnum codage codpro indireto perpart campo_base_r per_r forma_repasse_r` (PATCH: `codpro_novo codage_novo`) |
| 39 | GET /ramos | ✅ | 200 | `ramos`·50 | `codigo nome abreviatura` |
| 40 | GET /lista_ramos | 🆕 | 200 | `ramos`·5/6/5 (telram 1/2/3) · `message` (0) | `codigo nome telram` |
| 41 | GET /sinistros | ✅* | 200/404 · **500 com `tipo_sinistro=r`** | `sinistros` | (2025–2026: sit=t tipo=t → 6) |
| 42 | GET /documentos_bi | ✅ | 200 | `documentos`·245 (set/2026) | `codfil nosnum codcli cliente seguradora ramo inivig numpar preliq pretot base_c val_c val_cp numapo numend nosnum_ren datpro fimvig datalt sit_sinistro` |
| 43 | GET /incorp_url_post | 🆕 | NÃO chamado (gera URL de UPLOAD) | — | — |
| 44 | POST s3 area-transferencia-fenix-prod | — | NÃO chamado | — | — |
| 45 | GET /incorp_url_download | 🆕 | 200 com `key=''` | `link` (string vazia) | — |
| 46–48 | POST /incorp /incorp_contexto /incorp_documento | — | NÃO chamados | — | IA de leitura de PDF da própria Corp: link → JSON → contexto (agente/produtor) → grava documento |

**Rotas FORA da coleção** que respondem: `/seguradoras` (200·61) · `/cotacoes?codfil=1` (200·7, mesmos campos de negócio) · `/atendimentos?codfil=1` (200·2.355, envelope **`tarefas`**: `codigo tipo_atendimento codfil codcli nome_cli codopo nosnum codsin item data hora descricao satisfeito usuinc datinc ativo realizado tipo sistema usuario_responsavel codigo_usuario_responsavel titulo`) · 🆕 **`/usuario?codigo=N`** (§5).

---

## 2. Comportamento do gateway (vale para todas)

- 📊 Rota inexistente → **403** `"Authorization header requires 'Credential' parameter…"` (é o API Gateway da AWS, não permissão).
- 📊 **Lista-branca estrita de parâmetros em `/renovacoes`**: QUALQUER parâmetro fora da lista → **500** — inclusive um inventado `xyz=1`. Controle intercalado (controle=99 · `codpro=1`→500 · controle=99 · `codfil=1`→500 · controle=99 · `xyz=1`→500 · controle=99). **Não é estrangulamento; é a validação.** O mesmo vale para `ordem` fora da lista (`cliente`, `xpto` → 500; `fimvig`, `dias_a_vencer`, `nosnum` → 200).
- 📊 `/produtores` exige `texto` **e** `codage` (falta qualquer um → 500); aceita extra `xyz`.
- 📊 `/documentos_bi`, `/producao`, `/documentos`, `/clientes`, `/atendimentos` **ignoram** parâmetro desconhecido.
- 📊 `/usuario` responde `400 "Unknown field."` a parâmetro desconhecido e `400 "Invalid input type."` sem `codigo`.
- ⚠️ "Vazio" nem sempre é 404: `/documento_anexos` sem anexo → **200 com `message`**; `/documento_endossos` sem endosso → 200 `message`; `/produtores codage=2` → 200 `message`; `/lista_clientes` sem achado → 200 `message`. O leitor precisa checar a chave do envelope, não só o status.
- ⚠️ `/negocios_andamento` paginado: o `header.count` da 1ª página é o total (2.465); o da última página foi 65 (o resto). Não somar `count` por página.
- Token: JWT com claims `data_expiracao exp session email`; 📊 expira em ~3 dias (exp 14/10/2026 10:34 UTC para login feito hoje).

---

## 3. RENOVAÇÕES por completo

### 3.1 Parâmetros de `/renovacoes` — a lista inteira é a da doc
📊 Resulta, janela FIMVIG 11/10/2026–10/11/2026, `qtd_pag=1` (só o `header.count`):

| parâmetro | valor | count | o que faz |
|---|---|---|---|
| controle (`cancelado=F resgates=F`) | — | **99** | apólices a vencer, não canceladas |
| `cancelado` | `T` | 108 | **INCLUI** canceladas (+9, `renovacao_situacao=6`, hint "APÓLICE CANCELADA PELO DOCUMENTO [N]") |
| `cancelado` | `X` / vazio | 99 | igual F |
| `resgates` | `T` | **404** nesta janela | só "**APÓLICE NÃO RENOVADA**" (`renovacao_situacao=3`) — o que já VENCEU sem renovar. Janela 01/01–10/10/2026: T=394 ⊂ F=1.050 (T−F = 0; F−T = 656 = "RENOVADA PELO DOCUMENTO [N]"); 2025: T=2.594 / F=3.536 |
| `codram` | COND / RESI | 14 / 34 | = contagem por ramo da base (📊 bate 14/14, 34/34) |
| `codcia` | ALLI | 52 | = 52 da base |
| `codcli` | 1 cliente | 1 | |
| `texto` | `COND` | 11 | busca textual (10 COND + 1 EMPR — casa nome, não o ramo) |
| `ordem` | nosnum · fimvig · dias_a_vencer | 200 | `cliente`/`xpto` → 500 |
| `dt_ini`/`dt_fim` | | | filtram **FIMVIG** (📊 todas as 99 têm fimvig em 10–11/2026; `dias_a_vencer` 0..30) |
| `qtd_pag`/`pag` | | | paginação (testado até 200) |

🔴 **NÃO EXISTE filtro por PRODUTOR, agente, usuário, filial ou situação.** 📊 `codpro`, `codprod`, `produtor`, `cod_pro`, `codage`, `codfil` (1/2/3), `situacao`, `renovacao_situacao`, `renovados`, `so_renovados`, `codusu`, `ramo_tipo` → **todos 500** (lista-branca). Filtrar por dono é no NOSSO lado.

### 3.2 Medição Resulta 11/10/2026–10/11/2026 (`cancelado=F resgates=F`, paginado, 99 linhas, 99 nosnum distintos)

| campo | contagem |
|---|---|
| `renovacao_situacao` | **1: 89 · 2: 10** |
| `situacao_multi` | **-1: 99** (nenhuma cotação no Multicálculo da Corp) |
| `ramo_tipo` | **'' (vazio): 99** |
| `ramo_multi` | 0: 99 |
| `oportunidade` | **None: 99** · `codopo` preenchido: **0** |
| `historico_imagem` | 11: 57 · 10: 32 · 13: 6 · 12: 4 |
| `historico_hint` (3 linhas sempre) | "APÓLICE NÃO NOVA – RENOVAÇÃO DO DOCUMENTO [N]" + "APÓLICE VIGENTE": 57 · "APÓLICE NOVA" + "VIGENTE": 31 · "NÃO NOVA" + "VIGENTE MAS JÁ RENOVADA PELO DOCUMENTO [N]": 6 · "NOVA" + "JÁ RENOVADA": 4 · "NOVA" + "APÓLICE ANTERIOR À VIGÊNCIA": 1. 3ª linha = "VIGÊNCIA: dd/mm/aaaa A dd/mm/aaaa" |
| `sin_situacao` | 0: 91 · 3: 6 · 2: 1 · 1: 1 (`situacao_txt` = "APÓLICE SEM SINISTRO" 91, resto "N SINISTRO(S) …") |
| `quant_produtores` | 2: 35 · 3: 42 · 4: 21 · 5: 1 |
| `prod_docs[]` (reduzido) | **sempre 2 itens** (99/99) |
| `ramo` | RESI 34 · EMPR 20 · COND 14 · VIND 6 · CAPI 5 · VIAG 4 · RCPR 3 · VGRP 3 · GOC 3 · NAUT 2 · outros 5 |
| `pessoa` | F 54 · J 45 |
| `cic`/`fone`/`email` preenchidos | 96 / 71 / 86 |
| `tipdoc`, `codfil`, `cancelado` | A: 99 · 1: 99 · F: 99 |

**Legenda deduzida (INFERÊNCIA, por tabulação cruzada 99/99 + janela passada 1.050):**
`renovacao_situacao` 1 = a renovar (vigente) · 2 = já renovada por outro documento · 3 = vencida e NÃO renovada · 6 = cancelada.
`historico_imagem` 10 = nova vigente · 11 = renovação vigente · 12 = nova já renovada · 13 = renovação já renovada · 16/17 = não renovada (nova/renovação) · 22/23 = cancelada (nova/renovação) · 14/15 raros (9 linhas no passado, não decodificados).
🔴 **`nosnum_ren` NÃO é "renovada por"**: é o documento ANTERIOR que esta apólice renova (📊 preenchido em 63 = exatamente as "NÃO NOVA"). Quem renovou aparece só no texto do `historico_hint` ("JÁ RENOVADA PELO DOCUMENTO [N]") e em `/documento.renovado_nosnum`.

### 3.3 Renovação como NEGÓCIO no CRM da Corp
📊 `/negocios_andamento` (todas as páginas, 2.465): `tipo_neg` PROSPECÇÃO 2.452 · **RENOVAÇÃO 8** · **RESGATE 5** (tipo 1/2/3); os 13 de renovação/resgate têm `produto_fimvig` de **2024**. `/negocios_finalizados` 2026: 1.
INFERÊNCIA: a Resulta **não usa** o funil de renovação da Corp; `oportunidade`/`codopo` vazios em 99/99 confirmam. A renovação vive só na carteira (`/renovacoes`).

---

## 4. ESCOPO / BLOQUEIO

- 📊 **Uma filial só.** `/documentos_bi` set/2026 com `codfil` 1,2,3,4,5 → **245 sempre, todos codfil=1** (parâmetro ignorado). `/documentos` codfil 1/2/3 → 275 sempre, codfil=1. `/renovacoes` com codfil → 500. `/documento codfil=2` mesmo nosnum → 404. Nada esconde dado por filial: a base inteira é a filial 1.
- 📊 `/documentos_bi` `data` aceita só `INIVIG DATINC DATALT DATPROP` (mensagem de erro 400 lista; `DATPRO` também passou: 270; `FIMVIG`/`DATEMI` → 400). `tipo_doc=A` (ou `a`) → 122; **qualquer outro valor** (E, R, END, P, X) = TODOS (245) — não existe filtro de endosso.
- 📊 **`email_multi`**: igual entre os logins da Resulta e da AutoFleet (`email_multi R==A: True`), diferente do `email` do login e de domínio diferente; o JWT carrega o `email` do login, não o `email_multi`. INFERÊNCIA: é a conta da integração Multicálculo (os campos `codmulti`, `situacao_multi`, `multi_corp_mais` existem), **não um seletor de empresa**. 📊 `/empresas`, `/empresa`, `/multi`, `/trocar_empresa`, `/troca_empresa`, `/me`, `/perfil`, `/permissoes` → 403 (não existem). Não há troca de empresa pela API; a empresa é decidida pelo login.
- 📊 Flags `p…` idênticas (todas T) nos dois logins; `codigo` 75 (Resulta) e 73 (AutoFleet).
- 📊 Rotas que o mapa antigo dava como NEGADAS, hoje: `/vendedores /usuarios /propostas /proposta /sinistro /endossos /tarefas /agenda /cias /filiais /filial /parcelas /comissao /comissoes /financeiro` → **403 = não existem** (não é negação de permissão). `/sinistros` (plural) existe (500 sem parâmetros; 200/404 com). As tarefas existem como `/atendimentos` (envelope `tarefas`); as parcelas existem dentro de `/documento.parcelas[]`; os endossos em `/documento_endossos`; as cias em `/seguradoras`.
- Outras inexistentes (403): `/oportunidades /oportunidade /renovacao /lista_produtores /produtor /agente /responsaveis /equipes /canais /canal_vendas /anexos /documento_anexo /historico /historico_imagem /apolice /apolices /repasses /extrato`.

---

## 5. PRODUTORES e o DONO

- 📊 **`codage` = código do AGENTE** (de `/agentes`). As duas bases têm **1 agente só** (codigo 1). `codage=1` → 119 produtores (AutoFleet 105); `codage=0`/`2` → 200 "Não há produtores."; sem `texto` ou sem `codage` → 500. `texto='A'` → 112 (busca por nome).
- 📊 `cod_pro` das renovações presentes em `/produtores`: **28 de 30** (2 fora — INFERÊNCIA: produtores inativos).
- 📊 **`/renovacoes.prod_docs[]` é TRUNCADO em 2 itens** e **não traz `indireto` nem `perpart`**. `/prod_docs` traz a lista inteira (3–6 por apólice: 3:35 · 4:42 · 5:21 · 6:1) com `indireto`, `perpart`, `ordem`, repasses.
- 📊 Em **99/99** apólices da janela há **exatamente 1 produtor com `indireto='F'`**, sempre com `perpart=100`; os demais são `indireto='T'`. `quant_produtores` = nº de `indireto='T'` (99/99).
  O produtor `indireto='F'` está em `ordem` 1: 37 · 2: 19 · 3: 23 · 4: 15 · 5: 3 · 6: 2 → **9 produtores distintos** (participações 40/33/11/5/4…).
  O campo `produtor` (texto) de `/renovacoes` = o de **`ordem` mínima** (9/9 na amostra), que é o direto só em 37/99.
  INFERÊNCIA: o **dono comercial** da apólice é o `indireto='F'` com 100 % (os `T` são cadeia de repasse). Precisa de `/prod_docs` por apólice (99 chamadas/mês na Resulta). ⚠️ Confirmar com o Founder o que "indireto" significa no Corp antes de construir.
- 🆕 📊 **`GET /usuario?codigo=N`** (fora da coleção) → `nome email nome_agente nome_produtor nome_grupo_prod corp_mais_dashboard`. Varredura 1..199 na Resulta: **39 usuários** (códigos 2–77); `nome_produtor` preenchido em **1**, `nome_agente` em 2, `nome_grupo_prod` em 0; e o `nome_produtor` preenchido **não casa** com nenhum nome de `/produtores` (normalizado). 🔴 **O vínculo usuário↔produtor existe no modelo mas está VAZIO na prática** (1/39).
- 📊 `codusu_responsavel` existe **só em `/negocio`** (int): amostra de 43 negócios → 30 nulos, 3 usuários distintos, 13 resolvíveis em `/usuario`. `/atendimentos`: `usuario_responsavel`/`codigo_usuario_responsavel` vazios em **100/100**. `usuinc`/`usualt` (em `/documento`, `/negocio`, anexos) são **string de login**, não código.
- 📊 Os usuários parecem **compartilhados** entre as duas bases: dos 39 códigos da Resulta, 34 existem na AutoFleet e **32 com o mesmo nome no mesmo código**.

---

## 6. ANEXOS — o PDF da apólice existe e é baixável

- 📊 `/documento_anexos` → `anexos[]{nome tipo descricao datahora usuinc url indice_anexo}`; `url` = **S3 pré-assinada** em `corp-anexos.s3.amazonaws.com` (query `AWSAccessKeyId Signature x-amz-security-token Expires`), **expira em ~1 h** (📊 3.515 s restantes).
- 📊 Prova sem gravar em disco: `GET url` com `Range: bytes=0-7` → **206, `application/pdf`, magic `%PDF-`, 340.132 bytes** no total. Nada salvo.
- 📊 Cobertura na janela de renovação (99 apólices): **93 têm anexo**; **77 têm um arquivo de APÓLICE**, 69 de PROPOSTA. Por ramo: RESI 34/34 · EMPR 20/20 · COND 14/14 · VIND 6/6 · VIAG 4/4 · **CAPI 0/5**. Extensões: .pdf 254 · .doc 2 · .jpe 1. Nomes por prefixo: PROPOSTA 69 · APÓLICE 30 + "APÓLICE <ramo>" ~38 · BOLETO ~31 · OUTRO 9.
- 📊 `/documento.acompanhamento.emissao.url_apolice` também traz a URL S3 da apólice (na amostra).
- `/cliente_anexos` e `/negocio_anexos` existem (404 nos itens amostrados). `historico_imagem` **não é imagem**: é um código de ícone (10–23).
- `/incorp_url_download?key=` → `{link: ''}`. O fluxo InCorp (`/incorp*`) é a leitura de PDF por IA da própria Corp, com escrita no fim — não foi chamado.

---

## 7. Fora do escopo (reportar ao gerente)

1. 🔴 **CPF zerado casa um cliente real.** 📊 `/busca_cpf?cpf_cnpj=00000000000` e `/cliente_cpf?codfil=1&cpf_cnpj=00000000000` → 200 com 1 cliente na Resulta. Se o produto aceitar CPF "000…" (placeholder, digitação, máscara mal limpa) ele identifica alguém. INFERÊNCIA: cadastro com CPF de preenchimento. Teste do produto: SIM (segurança/dado ao segurado) — vale um guarda "CPF inválido não consulta".
2. `/sinistros?tipo_sinistro=r` → 500 sempre (bug da API, não do produto).
3. A base da Resulta tem **AUTO** no passado: 93 das 394 "não renovadas" de 2026 são AUTO (INFERÊNCIA: carteira auto que migrou/foi perdida; coerente com "Resulta só não-auto hoje").
4. `/clientes` lista **15.047** clientes da Resulta com CPF/telefone/e-mail em lote, paginado — rota de varredura em massa; não usar sem necessidade (LGPD).
5. `/renovacoes` devolve `cic`, `fone`, `email` do segurado em cada linha (96/71/86 de 99) — qualquer log de resposta crua vaza PII.
6. O token dura ~3 dias; o `/logout` existe — não foi chamado.

---

## 8. RECOMENDAÇÕES

1. Dono da renovação: `/renovacoes` (a carteira) + `/prod_docs` por apólice, dono = `indireto='F'` (perpart 100) — **validar o significado com o Founder** antes. Não usar o campo `produtor` de `/renovacoes` como dono (certo em 37/99).
2. Não mandar parâmetro extra a `/renovacoes` (500). Filtro por produtor/ramo/situação é local.
3. Para "já renovada?": usar `renovacao_situacao` (2) ou o hint — nunca `nosnum_ren`.
4. PDF da apólice: `/documento_anexos` (ou `url_apolice`), baixar sob demanda (URL vale 1 h), para MinIO/Artifact — cobre 77/99 da janela.
5. Tratar 200+`message` como vazio em todo leitor da InfoCap.
6. Guarda de CPF zerado/ inválido antes de consultar `/busca_cpf`/`/cliente_cpf`.
