# LAUDO — CorpAPI (InfoCap/CORP) completa: coleção, mapa por pasta, escrita, endosso, financeiro

> 📋 **Cópia para o canon (11/10/2026, agente de síntese):** revisada por `grep` de CPF/CNPJ, telefone, e-mail, nº de apólice e nomes próprios de pessoa → **0 ocorrências a redigir**. Nenhuma credencial: do `/incorp_url_post` só a FORMA da resposta, nunca os valores. Os caminhos `scratchpad/…` citados são do rascunho da sessão e não estão no repositório. O resumo para o Founder está em [`MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md`](MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md).

> Modo INVESTIGAÇÃO (protocolo §3.3) · read-only · 11/10/2026 · logins Resulta e AutoFleet
> 🔴 Na InfoCap: **só GET + POST /login**. Nenhum POST/PUT/PATCH/DELETE foi chamado, nem de teste. A escrita foi ANALISADA pela coleção.
> Ferramenta: `scratchpad/ic/ic.py` (chamadas em SÉRIE). Arquivos de trabalho: `ic/_endossos_sweep.json`, `ic/_endossos_motivos.json`, `ic/_status_sweep.txt`, `documenter-page.html`.
> Nenhum nome, CPF/CNPJ, telefone ou e-mail de cliente neste laudo: só contagens, nomes de CAMPOS e formas.
> Complementa (não repete) `laudo-postman-corpapi.md` (rota a rota) e `laudo-prints-infocap.md` (prints). O repositório já tem um catálogo lido da mesma coleção: `docs/canon/pesquisa/CORPAPI-CATALOGO-OFICIAL.md` (33 KB). Este laudo concorda com ele nas contagens e acrescenta as medições.

## EXECUTION CARD (investigação)
```
OUTCOME ........ o Founder sabe, com prova, o que a CorpAPI lê, o que ela ESCREVE, como modela endosso e o que do
                 financeiro do CORP fica fora dela
RISCO .......... 0 (só leitura) · SUPERFÍCIE 3 (território de terceiro, não mapeado) → MODO INVESTIGAÇÃO, sem juiz
O ELO .......... "a coleção baixada é a inteira" → medi A (JSON da API do documenter) e B (a página) e o ELO
                 (mesmo collectionId/versionTag/md5 em 3 variantes da URL; página sem ambiente)
                 "o endosso é documento filho" → medi o filho (codfil_end/nosnum_end) E o pai (/documento_endossos
                 contém o filho; o pai fica cancelado=T depois do X)
GATES .......... cada número com 📊 e o comando/script ao lado
```

---

## 1. A coleção é a INTEIRA — FATO

📊 `python urllib GET documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi` em **3 variantes** (sem query · `?segregateAuth=true&versionTag=latest` · `?versionTag=latest`) → todas **200, 66.660 bytes, md5 `c8bba5d4…`**, idêntico ao arquivo já baixado `scratchpad/corpapi-postman.json` (md5 igual).
📊 `info.publishDate = 2025-03-14T13:47:07Z` · `_postman_id = 94a117fa-aca4-4663-ba2f-a6f8175124d2`.
📊 Contagem por script (`walk` recursivo): **12 pastas · 51 requisições** — GET 29 · POST 12 · DELETE 6 · PUT 3 · PATCH 1 · **37 caminhos distintos** (36 da CorpAPI + 1 POST direto a um bucket S3).
⚠️ Correção ao laudo anterior: ele dizia "13 pastas" e listou 12. São **12**.

📊 A página `documenter.getpostman.com/view/33455116/2sAYkBrLmi` (HTML cru salvo em `scratchpad/documenter-page.html`, 39.997 bytes) é uma casca JS — o WebFetch não vê nenhuma rota. As meta-tags dizem:
`collectionId = 33455116-94a117fa-aca4-…` (o mesmo) · `versionTagId = latest` · **`environmentUID = "-"`** (nenhum ambiente publicado) · descrição *"Nesta documentação você conseguirá acessar os principais endpoints para utilização da API."*
📊 `GET documenter.gw.postman.com/api/environments/33455116/2sAYkBrLmi` → **404**. Não há outra versão nem outro ambiente para baixar. `{{base_url}}` não tem valor publicado; o valor real é `https://api.corpnuvem.com` (do código e do `ic.py`).

**O link `#ae7092f4-a52d-4ba6-b04c-a636cfeb94f5` é a PASTA "Documentos/Produção"**, não uma requisição. Ela tem 7 GETs: `/documento`, `/producao`, `/renovacoes`, `/documentos`, `/documento_anexos`, `/documento_endossos`, `/itens` — é o núcleo de leitura da apólice (detalhe em §2.2). É a única pasta com exemplos de resposta (3 deles).

---

## 2. O MAPA por PASTA

Legenda: **L** leitura · **E** escrita · status 📊 medido hoje nas duas bases (`ic/_status_sweep.txt`, script inline, 27 GETs × 2 logins), "R/A" = Resulta/AutoFleet.
Regra geral do gateway (laudo anterior §2, re-confirmado): rota inexistente → **403** (é o API Gateway, não permissão) · "vazio" muitas vezes é **200 com `message`** ou **404 com `message`**.

### 2.1 Autenticação (2)
| método rota | corpo / params | faz | L/E | status |
|---|---|---|---|---|
| POST /login | `{email, senha, aplicacao:0}` | devolve `token` (JWT ~3 dias) + perfil (`codigo`, `codfil`, flags `p…`, `email_multi`, `corp_mais_dashboard`) | L (autentica) | 200 R/A |
| POST /logout | só header `Authorization` | invalida a sessão | E (sessão) | não chamado |

### 2.2 Documentos/Produção (7) — o link `#ae7092f4…`
| método rota | params | faz | L/E | status R / A |
|---|---|---|---|---|
| GET /documento | `codfil, nosnum` | **a apólice inteira**: 84 campos + `parcelas[]` + `prod_docs[]` + `historico[]` + `acompanhamento{negocio,cotacao,proposta,emissao,recebimento,entrega}` | L | 200 / 200 |
| GET /producao | `texto, dt_ini, dt_fim, ordem, orientacao, so_renovados, so_emitidos` | lista de produção do período (página 15) | L | 200·242 / 200·386 (set/26) |
| GET /renovacoes | `dt_ini, dt_fim, qtd_pag, pag, ordem, orientacao, texto, cancelado, resgates, codcli, codram, codcia` (lista-branca estrita: extra → 500) | carteira por FIMVIG | L | 200·99 / 200·217 (11/10–10/11) |
| GET /documentos | `ordem, qtd_pag, pag, periodo(datinc…), datini, datfim, codfil` | lista de documentos **de todos os tipos** (A, F, C, X, M, R, I, D) | L | 200·275 / 200·406 (set/26) |
| GET /documento_anexos | `codfil, nosnum` | PDFs do documento (URL S3 pré-assinada, ~1 h) | L | 200·4 / 200·3 |
| GET /documento_endossos | `codfil, nosnum` (da apólice-mãe) | **lista os endossos filhos**: `codfil nosnum tipdoc inivig` | L | 200·1 / 200·2 |
| GET /itens | `codfil, nosnum, data` | o(s) item(ns) segurado(s) **na data informada** (reflete endosso, §4.4) | L | 200 / 200 |

### 2.3 Cliente (9)
| método rota | params / corpo | faz | L/E | status R / A |
|---|---|---|---|---|
| GET /cliente | `codfil, codigo` | ficha + `enderecos[] emails[] telefones[] contatos` | L | 200 / 200 |
| GET /clientes | `qtd_pag, pag` | **lista em massa** (CPF, fone, e-mail) | L | 200·15.047 / 200·16.290 |
| GET /cliente_cpf | `codfil, cpf_cnpj` | busca por CPF/CNPJ | L | 200 (laudo ant.) |
| GET /cliente_anexos | `codfil, codigo` | anexos do cliente | L | 404 / 404 (amostra sem anexo) |
| GET /lista_clientes | `texto` | busca por nome | L | 200 (laudo ant.) |
| GET /busca_cpf | `cpf_cnpj` | busca global por CPF | L | 200 (laudo ant.) |
| **POST /cliente** | `codfil nome ativo cpf_cnpj datanas pessoa sexo observacoes profissao estado_civil escolaridade usuinc` + `enderecos[]{tipo logradouro numero complemento bairro cep padrao cidade estado}` + `emails[]{email padrao}` + `telefones[]{tipo ddd numero ramal padrao codcon codemp}` | **cria cliente** (com contatos) | **E** | não chamado |
| **DELETE /cliente** | `codfil, codigo` (query) | **apaga cliente** | **E** | não chamado |
| GET /cliente_ligacoes | `codigo` | documentos, negócios e cotações do cliente | L | 200 / 200 |

### 2.4 Endereço (3) · Email (3) · Telefone (3) — CRUD dos contatos
| método rota | corpo | L/E |
|---|---|---|
| POST /endereco | `codcli logradouro numero complemento bairro cep cidade estado tipo padrao` | **E** cria |
| PUT /endereco | `codigo codcli tipo logradouro numero complemento bairro cep padrao cidade estado` | **E** altera |
| DELETE /endereco | `?codigo=` | **E** apaga |
| POST /email · PUT /email · DELETE /email | `codcli padrao email` · `codigo codcli padrao email` · `?codigo=` | **E** |
| POST /telefone · PUT /telefone · DELETE /telefone | `codcli tipo ddd numero padrao` · `codigo codcli tipo ddd numero padrao` · `?codigo=` | **E** |
Nenhum chamado. Não existe GET próprio destas pastas — o contato se lê dentro de `/cliente`.

### 2.5 Negociações (8)
| método rota | params / corpo | faz | L/E | status R / A |
|---|---|---|---|---|
| GET /negocios_andamento (2 requisições iguais na coleção: "/negocios_andamento" e "/negocios") | `dtini dtfim texto qtd_pag pag ordem orientacao status calculo` | funil em andamento | L | 200·2.465 / 200·2.477 |
| GET /em_calculo | `dtini dtfim texto qtd_pag pag ordem orientacao status` | negócios em cálculo (Multi) | L | 200·23 / 200·23 |
| GET /negocios_finalizados | idem + `status` | finalizados | L | 200·3 / 404 (2025–26) |
| GET /negocio_anexos | `codfil, codigo` | anexos do negócio | L | 404 / 404 (amostra) |
| GET /negocio | `codfil, codigo` | negócio inteiro (56 campos + `atendimentos[]`) | L | 200 / 200 |
| **POST /negocio** | 38 chaves: `cpf_cnpj codram ddd_fone numero_fone email produto_ja_possui produto_fimvig produto_seguradora observacoes val_premio usuinc datinc usualt datalt produto_codfil produto_nosnum produto_numapo prioridade etapa status per_c val_c campo_base_r per_r val_r codcia codcamp tipo dtini_negociacao usuini_negociacao dtfim_negociacao usufim_negociacao codusu_responsavel codopo_rep doc_codfil doc_nosnum motivo_perda codfil codcli` | **cria negócio/oportunidade**, podendo ligar a um documento (`doc_codfil/doc_nosnum`) | **E** | não chamado |
| **DELETE /negocio** | `codfil, codigo` | **apaga negócio** | **E** | não chamado |

### 2.6 Produtores (6)
| método rota | params / corpo | faz | L/E | status R / A |
|---|---|---|---|---|
| GET /agentes | `texto` | agentes (1 em cada base) | L | 200·1 / 200·1 |
| GET /prod_docs | `codfil, nosnum` | **produtores do documento com repasse** (`per_r val_r base_r campo_base_r forma_repasse_r indireto perpart ordem …`) | L | 200·5 / 200·5 |
| GET /produtores | `texto` **e** `codage` obrigatórios | cadastro de produtores | L | 200·119 / 200·105 |
| **POST /prod_docs** | `codfil nosnum codage codpro indireto perpart campo_base_r per_r forma_repasse_r` | **põe um produtor num documento** (com % de repasse) | **E** | não chamado |
| **PATCH /prod_docs** | `codfil nosnum codage codpro codpro_novo codage_novo indireto` | **troca o produtor** de um documento | **E** | não chamado |
| **DELETE /prod_docs** | `codfil nosnum codage codpro` (corpo) | **tira o produtor** do documento | **E** | não chamado |

### 2.7 Ramos (2) · Sinistro (1) · BI (1)
| método rota | params | faz | L/E | status R / A |
|---|---|---|---|---|
| GET /ramos | — | tabela de ramos | L | 200·50 / 200·54 |
| GET /lista_ramos | `telram` | ramos por tela (1/2/3) | L | 200·5 / 200·9 |
| GET /sinistros | `tipo_sinistro data_inicial data_final tipo_data situacao qtd_pag pagina` | sinistros (28 campos: `numsin datavi datoco datenc situacao valavi valind valdes franquia oficina responsavel proxima_agenda …`) | L | 200·4 / 200·552 (2025–26, sit=t) · `tipo_sinistro=r` → 500 |
| GET /documentos_bi | `datini datfim data(INIVIG/DATINC/DATALT/DATPROP) tipo_doc` | linha financeira por documento: `preliq pretot numpar base_c val_c val_cp` | L | 200·245 / 200·386 |

### 2.8 InCorp (6) — a IA de importação de PDF da própria Corp
| # | método rota | corpo / params | faz | L/E | status |
|---|---|---|---|---|---|
| 1 | GET /incorp_url_post | `nome_arquivo` | devolve um **POST pré-assinado** para o bucket `area-transferencia-fenix-prod` | L (só assina) | 📊 **200 R/A hoje** (ver abaixo) |
| 2 | POST `https://area-transferencia-fenix-prod.s3.amazonaws.com/` | form-data `key x-amz-security-token policy AWSAccessKeyId signature file` | **sobe o PDF** para a área de transferência | **E** (S3) | não chamado |
| 3 | GET /incorp_url_download | `key` | link de leitura do arquivo subido | L | 200 `{link:''}` com key vazia |
| 4 | POST /incorp | `{link}` | **a IA da Corp lê o PDF** e devolve um JSON | E? (processa; custo do lado deles) | não chamado |
| 5 | POST /incorp_contexto | "JSON do /incorp **inserindo agente e produtor**" | completa o contexto | E? | não chamado |
| 6 | POST /incorp_documento | JSON do contexto + `path_anexo_s3` (a key do passo 1) + JSON do /incorp | **GRAVA O DOCUMENTO** na base, com o PDF anexado | **E** | não chamado |

📊 **`GET /incorp_url_post` foi chamado UMA vez por base** (é GET, só gera assinatura; **nenhum arquivo foi enviado**). Forma da resposta: `{url, fields{key, AWSAccessKeyId, x-amz-security-token, policy, signature}}` · bucket `area-transferencia-fenix-prod` · **key = `files_incorp/<CÓDIGO DA BASE>/<hash>_areatransferencia_<nome>`** · `policy.expiration` ≈ 20 min depois.
🔴 📊 **O código da base apareceu:** Resulta = **`2010110006`** · AutoFleet = **`2024090009`** — o mesmo `2024090009` que o laudo dos prints viu na URL do CorpNow da AutoFleet (`#/apolice/DOCUMENTOS_2024090009_1_<nosnum>`). É o identificador inequívoco da base InfoCap (credenciais AWS temporárias da resposta NÃO estão neste laudo).

### 2.9 Rotas FORA da coleção que respondem (todas GET)
`/seguradoras` (200·61/62; só `codigo nome abreviatura` — **sem** telefones/observações da tela) · `/cotacoes?codfil=1` (200·7) · `/atendimentos?codfil=1` (200·2.355/2.362, envelope `tarefas`) · `/usuario?codigo=N` (laudo ant.) · 🆕 **`/atendimento?codigo=N`** (200, envelope `tarefa`, 30 campos incl. `entidade_tarefa atendente canal data_conclusao cliente_dados`) · 🆕 **`/dashboard`** (existe: sem parâmetro → 500; com QUALQUER um dos 14 conjuntos testados — `mes/ano`, `datini/datfim`, `dt_ini/dt_fim`, `periodo`, `codfil`… → **400 "Parâmetro inválido."**). INFERÊNCIA: é o painel "Produção" do CorpNow / `corp_mais_dashboard` do login; os parâmetros só um HAR do CorpNow revela.
📊 GET de 60 nomes financeiros candidatos (`/fluxo_caixa /contas_receber /contas_pagar /titulos /extrato /recebimentos /baixas /lancamentos /movimentos /categorias /metas /comissoes_recebidas /comissoes_pendentes /repasse* /incorp_comissoes /parcela* /ranking /grafico* /bi …`) → **todos 403 = não existem**, salvo `/dashboard`, `/usuario`, `/atendimento`.

---

## 3. ESCRITA — o que a API deixa criar/alterar, e o que NÃO existe

### 3.1 O que EXISTE (19 escritas + logout + upload S3)
| objeto | criar | alterar | apagar | corpo mínimo (da coleção) | risco |
|---|---|---|---|---|---|
| **Cliente** | POST /cliente | ❌ **não há PUT/PATCH** (nome, CPF, nascimento não se corrigem pela API) | DELETE /cliente | `codfil nome ativo pessoa` (+ contatos aninhados) | duplicar cliente (não há upsert medido; o CPF `000…` já casa 1 cliente real — laudo ant. §7) · DELETE de cliente com documentos = destruição |
| Endereço / Email / Telefone | POST | **PUT** | DELETE | `codcli` + campos | baixo-médio; troca de contato que a corretora usa para cobrança |
| **Negócio / oportunidade** | POST /negocio | ❌ não há PUT | DELETE /negocio | `codfil codcli tipo etapa status prioridade` … | o funil da Corp **está parado** (§6.3): criar negócio não afeta ninguém hoje, mas apagar é irreversível |
| **Produtor do documento** (`prod_docs`) | POST | **PATCH** (troca produtor/agente) | DELETE | `codfil nosnum codage codpro indireto perpart campo_base_r per_r forma_repasse_r` | 🔴 **ALTO: mexe em dinheiro** — o `val_r` = `per_r` % × comissão (📊 52/53 R, 57/57 A) é o repasse que a corretora paga ao produtor |
| **Documento (proposta/apólice) via INCORP** | POST /incorp_documento (depois de S3 + /incorp + /incorp_contexto) | ❌ | ❌ | JSON gerado pela IA da Corp + agente/produtor + `path_anexo_s3` | 🔴 **ALTO**: cria documento na produção; **não existe DELETE de documento na API** — erro só se desfaz à mão no CORP |
| Sessão | — | — | POST /logout | — | derruba o token em uso |

### 3.2 "Cadastrar na InfoCap a proposta do seguro fechado" — dá?
**FATO:** não existe `POST /documento`, `POST /proposta` nem `PUT /documento`. 📊 `/propostas /proposta /endossos /parcelas /comissao` → 403 (laudo ant. §4).
**FATO:** existe **um único caminho** que grava documento: o **INCORP** (§2.8). Ele recebe o **PDF** (proposta ou apólice), a IA da Corp extrai, o chamador acrescenta **agente e produtor**, e `/incorp_documento` grava com o PDF anexado.
📊 **E é o caminho que as corretoras já usam:** numa amostra aleatória de 60 apólices (tipdoc A) de 2026 por base, `importado_pelo_incorp = T` em **34/60 na Resulta** e **54/60 na AutoFleet** (script inline, `/documento` × 60).
**INFERÊNCIA (nota 75):** sim, o AutoBrokers poderia cadastrar a proposta do seguro fechado **mandando o PDF da proposta da seguradora pelo INCORP**, com o produtor certo no `/incorp_contexto` — o mesmo passo que hoje o corretor faz à mão no CORP. **O que falta saber, e só a InfoCap ou um teste autorizado responde:** (1) o formato do JSON do `/incorp` (a coleção não tem exemplo nem descrição); (2) se ele aceita endosso além de proposta/apólice (a tela INCORP tem coluna "Apo./End.", print `image 15`); (3) o que acontece com documento duplicado; (4) se há custo por chamada.
🔴 **Não há ambiente de teste:** a coleção não publica ambiente (`environmentUID "-"`), e os dois logins são as bases de PRODUÇÃO. Qualquer teste de escrita grava de verdade e — sem DELETE de documento — fica.
**RECOMENDAÇÃO:** antes de qualquer escrita, pedir à InfoCap (a) uma base de homologação e (b) o contrato do JSON do `/incorp`. Sem isso, a escrita do INCORP é aposta.

### 3.3 O que NÃO existe na API (escrita)
- criar/alterar **documento** diretamente (número da apólice depois da emissão, vigência, prêmio, forma de pagamento) — só via INCORP;
- **endosso**: nenhuma rota própria (só, talvez, pelo INCORP — não provado);
- **anexo** em documento/cliente/negócio já existente: só GET; o único upload é a área de transferência do INCORP;
- **tarefa/atendimento**, **sinistro**, **parcela/baixa**, **comissão recebida**, **repasse pago**, **fluxo de caixa**, **cotação/Multicálculo**, **usuário**: nenhuma escrita;
- **alterar cliente** (só contatos) e **alterar negócio**: não há PUT;
- **apagar documento**: não há.

---

## 4. ENDOSSO — como o CORP modela

### 4.1 O endosso é um DOCUMENTO FILHO, com nosso número próprio — FATO
📊 Em 3 de 3 endossos inspecionados a fundo (X e C da Resulta, M da AutoFleet):
- o endosso tem **`nosnum` próprio, maior que o da mãe**; aponta para a mãe por **`codfil_end` / `nosnum_end`**;
- **`numapo` do endosso = `numapo` da mãe** (o número da apólice da seguradora se repete); a mãe tem `numend = '0'`, o endosso `numend` ≥ 1;
- `GET /documento_endossos?nosnum=<mãe>` **contém o endosso** (`codfil nosnum tipdoc inivig`); `/documento(mãe).historico[]` lista a linha do endosso;
- **o endosso não sobrepõe a apólice**: a mãe mantém o próprio prêmio (📊 `preliq` da mãe inalterado; o X tem `preliq` **negativo**, −1.111,00, e `val_c` negativo). Prêmio e comissão do contrato = **mãe + soma dos filhos**;
- o **X (cancelamento)** marca a MÃE: `cancelado = 'T'` e `sit_renovacao_txt` = "APÓLICE CANCELADA PELO DOCUMENTO [N]";
- 📊 `/itens?nosnum=<mãe>&data=` devolve o item **na data**: em **7/7** endossos C "SUBSTITUIÇÃO DE ITENS" da AutoFleet, o item da mãe 2 dias antes ≠ 2 dias depois do início do endosso, e o item do próprio endosso = o da mãe depois. É o "ITEM ATUALIZADO" do CorpNow.

### 4.2 Os tipos (`tipdoc` / `tipdoc_txt`, lidos da API)
| tipdoc | texto da API | o que é |
|---|---|---|
| A | A - APÓLICE | documento-mãe (nova ou renovação) |
| C | C - ENDOSSO DE COBRANÇA | endosso com prêmio a cobrar |
| R | R - ENDOSSO DE RESTITUIÇÃO | endosso com devolução (prêmio negativo) |
| M | M - ENDOSSO SEM PRÊMIO | alteração cadastral sem valor |
| X | X - ENDOSSO CANCELAMENTO DE APÓLICE | cancela a mãe |
| I | I - ENDOSSO CANCELAMENTO DE ITEM | tira um item |
| F | F - FATURA | fatura mensal de apólice-mãe faturável (filha, `nosnum_end`) |
| D | D - DEVOLUÇÃO DE DOCUMENTO | proposta devolvida/recusada (sem mãe, sem emissão) |

`motivo_endosso` (código) + `motivo_endosso_txt`: vistos "ALTERAÇÃO DE ITENS", "INCLUSÃO DE ITENS", "SUBSTITUIÇÃO DE ITENS", "CANCELAMENTO DE ITENS", "ALTERAÇÃO APÓLICE", "PRORROGAÇÃO DE APÓLICE", "ALTERAÇÃO DO LOCAL DO RISCO/CEP DE PERNOITE", "CANCELAMENTO POR SOLICITAÇÃO DO SEGURADO / DA SEGURADORA", "CANCELAMENTO POR FALTA DE PAGAMENTO", "CANCELAMENTO POR PERDA TOTAL", "CANCELAMENTO DE APÓLICE"; nulo em ~10 %.
⚠️ **`numend` é texto livre digitado**: 📊 valores vistos "1", "000001", "01-077", "1 ok", número longo da seguradora, vazio. Não serve de chave; a chave do endosso é o `nosnum`.
⚠️ `nosnum_ren` é outro conceito (a apólice ANTERIOR que esta renova — laudo ant. §3.2); `codfil_ren/nosnum_ren` ≠ `codfil_end/nosnum_end`.

### 4.3 Quantos, por base e ano — 📊 MEDIDO
Comando: `/documentos?periodo=datinc&datini=01/MM/AAAA&datfim=<fim>&qtd_pag=1000&codfil=1`, mês a mês, jan/2025 → 11/10/2026, 44 chamadas (`ic/_endossos_sweep.json`). "Ano" = ano em que o documento foi **cadastrado** no CORP (`datinc`).

| base · ano | A apólices | **C** | **X** | **M** | **R** | **I** | **endossos (C+X+M+R+I)** | F faturas | D devoluções |
|---|---|---|---|---|---|---|---|---|---|
| Resulta 2025 | 1.699 | 215 | 274 | 57 | 11 | 4 | **561** | 1.043 | 18 |
| Resulta 2026 (até 11/10) | 1.232 | 101 | 80 | 35 | 4 | 2 | **222** | 896 | 30 |
| AutoFleet 2025 | 3.198 | 371 | 284 | 71 | 23 | 11 | **760** | 0 | 68 |
| AutoFleet 2026 (até 11/10) | 2.772 | 304 | 243 | 62 | 14 | 13 | **636** | 1 | 41 |

📊 Motivos numa amostra (todos os C/X/M/R de ago–set/2026 + todos os I do período; 57 R / 180 A, `/documento` um a um, `ic/_endossos_motivos.json`):
- **Resulta**: C → ALTERAÇÃO DE ITENS 9 · INCLUSÃO 3 · ALTERAÇÃO APÓLICE 2 · outros 5 · X → SOLICITAÇÃO DO SEGURADO 9 · FALTA DE PAGAMENTO 7 · nulo 4 · M → ALTERAÇÃO DE ITENS 5 · INCLUSÃO 3 · I → CANCELAMENTO DE ITENS 6.
- **AutoFleet**: C → **SUBSTITUIÇÃO DE ITENS 49** (troca de veículo) · INCLUSÃO 10 · ALTERAÇÃO DE ITENS 7 · X → SOLICITAÇÃO DO SEGURADO 34 · FALTA DE PAGAMENTO 10 · CANCELAMENTO DE APÓLICE 8 · PERDA TOTAL 4 · I → CANCELAMENTO DE ITENS 19 · PERDA TOTAL 4.
- Filhos com mãe (`nosnum_end`): **57/57** e **180/180**. Com parcelas: 33/57 e 124/180.

**INFERÊNCIA:** na Resulta, a **F (fatura)** é volume grande (1.043 em 2025) — apólices faturáveis (vida em grupo, transporte, etc.) geram uma filha por mês; não é endosso de alteração. Para "endossos de verdade", contar C+X+M+R+I.
**FATO:** **não existe criação de endosso pela API** (§3.3). 📊 `/documentos_bi tipo_doc=` só filtra `A`; qualquer outro valor devolve tudo (laudo ant. §4); `/documentos` traz o `tipdoc` e é o filtro que funciona.

---

## 5. FINANCEIRO / COMISSÕES / CONTABILIDADE

### 5.1 O que a API ENTREGA — FATO
| dado | onde | 📊 medido |
|---|---|---|
| **Prêmio** líquido/total/IOF/adicional/desconto | `/documento` (`preliq pretot preiof preadi predes precus prepri`), `/documentos_bi` (`preliq pretot`) | sempre |
| **Comissão da corretora** no documento | `/documento` (`campo_base_c base_c per_c val_c forma_recebimento_c val_ca`), `/documentos_bi` (`base_c val_c val_cp`) | `val_c` negativo nos endossos X/R (6 R, 13 A em set/26) · `val_cp` = **0 em 245/245 e 386/386** · `val_ca` = 0 em 60/60 e 60/60 |
| **Parcelas** do prêmio | `/documento.parcelas[]` = `parc tipo forma_pagamento cod_forma_pagamento vlbasecom vlbasecomquit datvenc vlvenc datquit vlquit` | 322 (R) / 495 (A) parcelas em 60+60 apólices de 2026 · `tipo` = **P em 100 %** |
| **Repasse ao produtor** | **`/prod_docs`** (rota própria): `per_r val_r base_r campo_base_r forma_repasse_r cod_com_ind indireto perpart` | `val_r = per_r % × val_c` em **52/53 (R)** e **57/57 (A)** · `base_r = val_c` 52/52, 57/57. ⚠️ Os MESMOS campos dentro de `/documento.prod_docs[]` vêm **nulos** (58/58, 60/60) — o repasse só vem de `/prod_docs` |
| Produção por período | `/producao`, `/documentos`, `/documentos_bi` | com `val_c` dá para somar prêmio e comissão por mês, ramo, seguradora, produtor |
| Situação do documento | `/documento.sit_acompanhamento_txt` + `acompanhamento{…}` | "Emitido e não recebido" 30/14 · "Recebido e não entregue ao cliente" 30/45 (R/A, amostra 60) |

⚠️ **A "quitação" da parcela NÃO prova pagamento do segurado.** 📊 `datquit = datvenc` em **208/212 (R)** e **395/403 (A)** parcelas quitadas; e há **quitação registrada em parcela que ainda vai vencer**: 30/126 (R) e **171/241 (A)**. INFERÊNCIA (nota 70): é baixa automática/por previsão (cartão/débito ou importação de comissão), não o dinheiro entrando. `vlbasecomquit` (base de comissão da parcela quitada) aparece em 127/322 e 206/495. Não usar `datquit` como "cliente pagou" sem validar com o financeiro da corretora.
⚠️ `/documentos_bi` **omite documentos**: 📊 set/26 por DATINC, R: BI 201 × `/documentos` 275 — faltam 74 (**60 F**, 13 A, 1 C); A: 381 × 406 — faltam 25 (21 A…). Para financeiro completo, `/documentos` + `/documento`, não só o BI.

### 5.2 O que os prints mostram e a API NÃO entrega
| módulo do CORP (print) | por quê não | 📊 |
|---|---|---|
| **Comissões Recebidas / Pendentes / Diferenças / Fechamento** (Gerenciador de Relatórios, `image 5`) | nenhuma rota de comissão recebida da seguradora | `/comissoes*` → 403 |
| **INCORP › Comissões / Histórico de Comissões** (extrato importado da seguradora: Vl. Recebido, Dt. Receb., 26.228 registros, `image 15`) | a API só tem o INCORP de **propostas** | `/incorp_comissoes` → 403 |
| **Repasse ao Produtor** pago (fechamento) | `/prod_docs` dá o **devido**, não o **pago** (`datrep_prot` vazio em 100 %) | — |
| **Fluxo de Caixa** (Extrato Diário, Mapa de Categorias, Mapa de Saldos, contas a pagar/receber) | nenhuma rota | `/fluxo_caixa /contas_* /lancamentos /categorias` → 403 |
| **Metas** ("0 % ATINGIDA") e rankings prontos | nenhuma rota; `/dashboard` existe mas recusa todo parâmetro testado | `/metas` → 403 · `/dashboard` → 400 |
| Telefones/observações das **Seguradoras** (CorpNow `image 47–49`) | `/seguradoras` só tem `codigo nome abreviatura` | 📊 campos |

### 5.3 Dá para chegar por HAR/F12?
**FATO (prints):** o **CorpNow** (`corpnow.com.br/#/…`) é SPA web com **só 4 módulos — Produção, Busca, Renovações, Seguradoras**; **não tem financeiro, comissões, fluxo de caixa nem metas**. O **CORP clássico** (`…ddns.net/software/html5.html`) tem tudo isso, mas é **programa de desktop transmitido ao navegador** (janelas MDI, menus Windows): um HAR dele mostra **pintura de tela por WebSocket, não JSON** (INFERÊNCIA 80, laudo dos prints §7).

| caminho | o que traria | nota "vale capturar" |
|---|---|---|
| HAR do **CORP clássico** para o financeiro | pixels, não dados | **10/100** |
| HAR do **CorpNow** (Produção + Seguradoras + abrir uma apólice) | os **parâmetros do `/dashboard`** (já sabemos que existe), o host do backend do CorpNow e se ele tem rotas além da CorpAPI; contatos das seguradoras | **65/100** — barato (10 min do Founder), mas **não alcança o financeiro** |
| **Exportar relatórios do CORP clássico** (Gerenciador de Relatórios já exporta **Excel/PDF/e-mail**): Comissões Recebidas, Pendentes, Repasse ao Produtor, Fluxo de Caixa Extrato Diário, Vencimento de Parcelas | o financeiro inteiro, em planilha, sem engenharia reversa | **85/100** — é o caminho real para comissões/caixa; dá para virar rotina (o Founder exporta, o AutoBrokers importa por arquivo) |
| **Pedir à InfoCap** rotas de comissão recebida/extrato e o contrato do `/incorp` + base de homologação | API oficial | **75/100** — depende de terceiro; pedir em paralelo |

---

## 6. ACHADOS FORA DO ESCOPO, IMPORTANTES

### 6.1 🔴 As duas bases são uma CÓPIA uma da outra até ago/2024 — FATO + INFERÊNCIA forte
📊 `/atendimentos` (13 páginas × 2 logins, comparação campo a campo): **2.353 de 2.355** registros da Resulta são **idênticos** aos da AutoFleet (mesmo código, mesmo conteúdo); o último idêntico foi cadastrado em **29/08/2024**; depois disso só 2 (R) e 9 (A) exclusivos.
📊 `/cotacoes` 7/7 iguais · `/em_calculo` 23/23 iguais · `/negocios_andamento` 1ª página: 35/50 iguais (os mais novos divergem).
📊 Clientes: 36/36 clientes **sorteados da Resulta** existem na AutoFleet **com o mesmo nome no mesmo código**; já clientes de documentos **novos** da AutoFleet (códigos 26–28 mil) batem só 3/8.
📊 Documentos NÃO são compartilhados: 17 de 20 `nosnum` da Resulta (set/26) existem na AutoFleet, **0 com o mesmo cliente/ramo**.
📊 O código de base da AutoFleet é `2024090009` (set/2024) e o da Resulta `2010110006`.
**INFERÊNCIA (85):** a base da AutoFleet nasceu em **setembro de 2024 como cópia da base da Resulta** (ou da base comum do grupo). Clientes, negócios, cotações e tarefas **anteriores a set/2024 aparecem nas duas**; documentos, a partir daí, seguem sequências separadas que se sobrepõem.
**Consequências para o produto (CLAUDE.md §7, §13.9):** (a) `codcli` e `nosnum` sozinhos **não identificam** pessoa nem apólice — a chave é sempre (corretora/conexão, codfil, código); (b) os "15.047 clientes da Resulta" incluem a carteira antiga da AutoFleet e vice-versa (16.290) — contagem de "clientes da corretora" pela API é inflada; (c) ler o CRM da InfoCap (negócios/tarefas) por uma conexão devolve registros históricos que são da outra corretora. Teste do produto: muda o que chega à CORRETORA (tela/contagem) → registrar como pendência de leitura, não como vazamento ao vivo.

### 6.2 O CRM da Corp está parado
📊 `/atendimentos`: último cadastro **dez/2024 (R)** e **out/2024 (A)**; das 155 mais recentes, 100 % `tipo_atendimento = O` (oportunidade). `acompanhamento.negocio` vazio em **60/60** apólices 2026 nas duas bases; `acompanhamento.cotacao` (Multi) vazio em 60/60. INFERÊNCIA: as corretoras não usam o funil/Multicálculo da Corp — o documento entra direto (INCORP).

### 6.3 Outras
- `/incorp_url_post` devolve credencial AWS temporária (token de sessão) a qualquer login da API — não logar a resposta.
- `/clientes` lista a base inteira com CPF/fone/e-mail (LGPD): não usar sem necessidade.
- O produto hoje só faz `POST /login` na InfoCap (📊 `grep -n "\.post(" backend/app/api/infocap_connector.py` → só o `auth_path` de login e rotas internas do próprio AutoBrokers). Nenhuma escrita na InfoCap existe no código.

---

## 7. TABELA FINAL — módulo do CORP × API × o que o AutoBrokers faz com ele

| módulo (print) | rota | cobertura | o que o AutoBrokers pode fazer |
|---|---|---|---|
| Cadastro de Clientes (grade, abas) | /cliente, /clientes, /cliente_cpf, /busca_cpf, /lista_clientes, /cliente_ligacoes | **tem** (sem "Dados Bancários"/"Perfil") | identificar o segurado no atendimento; ficha 360 com documentos |
| Cliente — criar / contatos | POST /cliente; POST/PUT/DELETE endereco·email·telefone | **tem (escrita)** | cadastrar cliente novo e atualizar contato depois do fechamento — **só com autorização** |
| Busca de Documentos | /documentos, /producao, /documento | **tem** | carteira, busca, "minha apólice" para o segurado |
| Apólice › Documento / Acompanhamento | /documento (+`acompanhamento`, `sit_acompanhamento_txt`) | **tem** | alertar "emitido e não recebido", "pendente de emissão em atraso" |
| Apólice › Parcelas | /documento.parcelas[] | **parcial** (quitação não é prova de pagamento) | lembrete de vencimento; cobrança só depois de validar a quitação |
| Apólice › Produtores / repasse | /prod_docs (GET + POST/PATCH/DELETE) | **tem** (devido, não o pago) | dono comercial da apólice; previsão de repasse; corrigir produtor (escrita, risco alto) |
| Apólice › Itens / garantias / "Atualizados" | /itens?data= | **tem** (📊 reflete endosso 7/7) | responder cobertura/franquia na data do sinistro |
| Apólice › Anexos (PDF) | /documento_anexos, `url_apolice` | **tem** (leitura) | mandar a 2ª via do PDF ao segurado |
| Endosso (tela roxa) | /documento_endossos + /documento do filho | **tem (leitura)**; criação **não tem** | histórico de alterações; "apólice cancelada"; contar endossos |
| Renovações (CorpNow) / relatórios Renovações, Não Renovados, Análise de Renovações | /renovacoes (`renovacao_situacao`, `resgates`) | **tem** | fila de renovação, não-renovadas, resgate |
| Consulta de Sinistro | /sinistros | **parcial** (lista; sem terceiros/atendimentos; `tipo_sinistro=r` quebra) | acompanhar sinistro aberto; sinistralidade na renovação |
| Central de Negócios (oportunidades, funil) | /negocios_andamento, /negocio, /em_calculo, /negocios_finalizados, /cotacoes, POST/DELETE /negocio | **tem, mas sem uso** (CRM parado desde 2024 e clonado) | não usar como fonte; opcional: registrar a venda fechada como negócio (escrita) |
| Tarefas / atendimentos | /atendimentos, /atendimento | **leitura só**, sem escrita, parado | nenhum valor hoje |
| Multicálculo (Segurado/Automóvel/Perfil/Seguro) | — (`codmulti`, `situacao_multi` só como campos) | **não tem** | o Multicálculo é nosso (SPEC-129/131) |
| **INCORP › Propostas** | /incorp_url_post → S3 → /incorp → /incorp_contexto → /incorp_documento | **tem (escrita, sem exemplo)** | **cadastrar a proposta/apólice fechada na InfoCap a partir do PDF** — o passo manual de hoje (📊 34/60 R e 54/60 A já entram assim) — exige homologação |
| INCORP › Comissões / Histórico | — | **não tem** | via exportação Excel do CORP clássico |
| Gráficos e métricas (prêmio, comissão, qtde, novos × renovações × faturas × endossos, rankings) | /documentos_bi + /documentos + /documento | **parcial** (dado bruto sim; painel pronto não; `/dashboard` sem parâmetros conhecidos) | painel de produção do AutoBrokers calculado por nós |
| Metas | — | **não tem** | metas no próprio AutoBrokers |
| Comissões Recebidas / Pendentes / Diferenças / Fechamento / Repasse pago | — | **não tem** | exportação Excel (nota 85) ou pedido à InfoCap |
| Fluxo de Caixa / contas a pagar e receber | — | **não tem** | exportação Excel; nada pela API |
| Seguradoras (telefones, assistência 24h, observações) | /seguradoras | **parcial** (só nome/abrev.) | contatos de assistência ficam no NOSSO cadastro de seguradoras |
| Usuários / permissões / filiais / empresa | /usuario?codigo= (só leitura) | **parcial** | vínculo usuário↔produtor vazio (1/39, laudo ant.) — de-para no nosso banco |

---

## 8. RECOMENDAÇÕES
1. **Não escrever nada na InfoCap** até haver (a) base de homologação e (b) o contrato do JSON do `/incorp` — pedir os dois à InfoCap. Sem DELETE de documento, um teste em produção é permanente.
2. Se o Founder autorizar escrita, a ordem de valor é: **INCORP da proposta fechada** (o passo manual que mais se repete) → **contato do cliente** (PUT de telefone/e-mail, reversível) → **produtor do documento** (só com dupla checagem: mexe em repasse). Negócio/tarefa da Corp: não vale (CRM parado).
3. Financeiro: pedir ao Founder **um export Excel** de "Comissões Recebidas", "Comissões Pendentes", "Repasse ao Produtor" e "Fluxo de Caixa – Extrato Diário" do CORP clássico — é o único caminho para comissão recebida e caixa. HAR do clássico não vale; HAR do CorpNow só para descobrir o `/dashboard`.
4. Endosso: ler por `/documentos` (filtro por `tipdoc`) + `/documento_endossos`; contar C+X+M+R+I; tratar F como fatura; nunca usar `numend` como chave.
5. Toda chave InfoCap no produto = (conexão/company_id, codfil, nosnum|codcli). As bases compartilham histórico até ago/2024 (§6.1).
