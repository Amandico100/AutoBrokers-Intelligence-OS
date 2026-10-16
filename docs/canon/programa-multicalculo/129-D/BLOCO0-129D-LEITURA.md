# BLOCO 0 da SPEC-129-D — vida (e moto?) no multicálculo · leitura do investigador

> 16/10/2026 · investigador Opus 5.5 (read-only) · árvore `AutoBrokers-FIX` @ `fbb2a80` (branch `spec/131-0-B3-um-whatsapp`)
> ZERO cálculo no Agger, nenhum login no Agger · InfoCap só GET (pelo caminho do produto `dono.abrir_fonte` →
> `InfocapAnalyticsProvider._abrir`, cache Redis DESLIGADO no script: `FI._TTL_CACHE_S = 0`) · banco só SELECT ·
> nenhum CPF/nome/telefone/placa/apólice/valor pessoal neste arquivo. Scripts: `scratchpad/129d/m1_medir.py` (+ `m2_*.py`),
> saída agregada `m1.json`/`m1.log`.

## 0. As conexões (quem é quem) — conferido pelo LOGIN, não pelo nome

Comando: `m1_medir.py` §0 — `SELECT tenant_connections(id,company_id,status,name,connector_templates(slug),encrypted_secret_ref)`,
decifrado pelo serviço do produto (`get_encryption_service().decrypt`), impresso só o prefixo genérico do login.

| conexão | company_id | status | login guardado |
|---|---|---|---|
| `05c74a9c` "InfoCap" (criada 14/10) | `04b5cdbc-…` (Resulta) | 📊 **connected** | 📊 `resulta@api…` |
| `7309380a` "InfoCap" (criada 14/10) | `6c9c55e2-…` (AutoFleet) | 📊 **connected** | 📊 `autofleet@api…` |
| `5039f90d` "InfoCap AUTOFLEET" (a da troca da 131-0-A) | `3aa75902-…` (Amandus) | archived | autofleet@ |
| `604ec9f1` | Amandus | archived | resulta@ |
| outras 5 | Resulta/AutoFleet | archived | login de pessoa ou ilegível |

→ A medição abaixo usa `05c74a9c` para a Resulta e `7309380a` para a AutoFleet — cada uma com o login DELA (a lição da 131-0-A conferida).
📊 `renovacoes` (a tabela da 131-A) no banco: **0 linhas** (`SELECT company_id,ramo_sigla,estado,motivo FROM renovacoes`) — a madrugada
ainda não gravou lista em produção; não há o que contar do lado do produto.



## M1 · Volume por ramo na InfoCap, nas duas corretoras (16/10/2026, 00:5x)

Comando (`m1_medir.py`): `fonte = await dono.abrir_fonte(db, company_id)` → `fonte.renovacoes_cruas(ini, fim)` (a função do produto,
`fonte_infocap.py:482` — `GET /renovacoes?dt_ini&dt_fim&qtd_pag=5000&pag=1&ordem=nosnum&orientacao=asc&texto=&cancelado=F&resgates=F`),
filtro do produto (`renovacao.linha_da_infocap`: `tipdoc == "A"` e não cancelada), contagem por `ramo` (a sigla). Janelas:
**últimos 90** = 18/07–15/10/2026 · **próximos 90** = 16/10/2026–14/01/2027 (por `fimvig`).

### Resulta (`04b5cdbc…`, login `resulta@`)
📊 últimos 90: **320** apólices · próximos 90: **340**.

| sigla | ramo por extenso (`/documento.ramo`) | últ. 90 | próx. 90 | seguradoras (180 d) | o produto hoje |
|---|---|---:|---:|---|---|
| **VIND** | VIDA INDIVIDUAL | **11** | **11** | PORT 8 · TMAR 4 · ALLI 4 · SULA 2 · HDI 1 · UNIV 1 · MAG 1 · LIBE 1 | `ramo_nao_cotado` |
| **VGRP** | VIDA GRUPO | **11** | **12** | PORT 9 · METL 9 · LIBE 2 · PASI 2 · ALLI 1 | `ramo_nao_cotado` |
| **API** | AP INDIVIDUAL | **9** | **4** | TMAR 12 · ALLI 1 | `ramo_desconhecido` |
| **APC** | AP COLETIVO | 0 | **1** | METL 1 | `ramo_desconhecido` |
| MOB | 📊 IMOBILIARIA (não é mobilidade) | 2 | 2 | MAPF 2 · PORT 2 (produtores = imobiliárias) | `ramo_desconhecido` |
| PREV | PREVIDENCIA | 1 | 2 | PORT · ICAT · SULA | `ramo_desconhecido` |
| MOBI | — | 0 | 0 | — | — |
| AUTO | — | 2 | 0 | LIBE 2 | cotável (2/2 categoria "Passeio") |
| moto (qualquer sigla) | — | 0 | 0 | — | — |
| (referência) RESI · COND · EMPR | | 90 · 70 · 43 | 136 · 50 · 47 | | cotáveis (129-C) |
| outras | | VIAG 16 · CAPI 15 · GOC 8 · RD E 8 · SAUD 7 · ENGE 6 · RCPR 6 · NAUT 4 · RC 2 · HABI 2 · EVEN 2 · FIAN · AERO · CONS · AM · DENT 1 | ENGE 18 · SAUD 13 · GOC 12 · CAPI 9 · RD E 5 · RCPR 4 · NAUT 3 · FIAN 2 · RC 2 · CONS 2 · DENT 2 · CIBE · VIAG · EVE 1 | | |

→ **Vida (VIND+VGRP) na Resulta = 22 + 23 = 45 apólices em 180 dias** (📊 ≈ 7,5/mês); **só VIND = 22 (≈ 3,7/mês)**; AP (API+APC) = 14.
Bate com o Agger: 📊 9 negócios de vida (91) em 90 d na Resulta (A-PROVA §10) — o comercial já cota parte da vida pelo Agger.

### AutoFleet (`6c9c55e2…`, login `autofleet@`)
📊 últimos 90: **651** · próximos 90: **705**.

| sigla | ramo por extenso | últ. 90 | próx. 90 | seguradoras (180 d) | o produto hoje |
|---|---|---:|---:|---|---|
| **AUTO** | — | **627** | **684** | ALLI 334 · TMAR 291 · LIBE 225 · PORT 134 · HDI 94 · AZUL 61 · BRAD 41 · YOUS 32 · ZURI 19 · ITAU 19 · ALFA 18 · MAPF 17 · SURA 13 · SUHA 6 · SANT 3 · MITS 2 · EZZE · DARW 1 | cotável (carro) |
| **MOBI** | 📊 **MOBILIDADE** (3/3 `/documento.ramo`) | **13** | **15** | 📊 **SURA 28/28** | `ramo_desconhecido` |
| FROT | — | 8 | 5 | TMAR 4 · LIBE 3 · HDI 2 · PORT · ALLI · AXA · SURA 1 | `ramo_nao_cotado` (frota) |
| APC | AP COLETIVO | 1 | 0 | MBMS 1 | `ramo_desconhecido` |
| VIND · VGRP · API | — | 0 | 0 | — | — |
| ONIB · 24HS · RESI | | 1 · 1 · 0 | 0 · 0 · 1 | | |

→ 🔴 **MOBI confirmado NÃO é moto:** 📊 28/28 SURA, ramo por extenso "MOBILIDADE", e `/itens` volta **vazio** para as 3 amostras (sem
veículo, sem placa — 📊 `amostra_MOBI.campos["/itens"] = {}`). É o Mobi Livre (palavra do Founder), produto de AP/RC do condutor.
→ **Vida na AutoFleet = 0.**

### Moto: há volume? onde?
**Onde:** dentro da sigla **AUTO**, só pelo item do veículo. 📊 `/itens` (o mesmo `itens_crus` do produto, `data` por `data_dos_itens`) de
**679 das 684** apólices AUTO dos próximos 90 dias da AutoFleet (33 leituras falharam — tempo; orçamento de 900 s esgotou antes dos
últimos 90): `categoria` dos itens = **Passeio 631 · Demais 43 · Moto 3 · Comercial 1**; apólices com moto pela regex do produto
(`pedido.veiculo_nao_cotado(categoria, veiculo)`) = **4** (3 com `categoria = "Moto"` + 1 "Passeio" cuja descrição do veículo diz moto).
Resulta: 2 AUTO em 180 d, ambos "Passeio" → 0 moto.
- 🔴 **O rótulo exato da InfoCap é `categoria = "Moto"`** — o comentário de `pedido.py:586` diz "⚠️ o rótulo exato da moto na InfoCap não
  foi medido": está medido agora (3 itens); e há 1 moto rotulada "Passeio" (a regex sobre `veiculo` a pega).
- **Volume:** 📊 4 em 679 = **0,6 %** do AUTO da AutoFleet nos próximos 90 dias (≈ 1,3/mês); no Agger da AutoFleet, 📊 1 link de
  Motocicleta em 51 do código 31 (A-PROVA §10). 💭 Moto NÃO tem volume que pague uma SPEC agora (D-131-38 já a trata como pendência
  visível); "Demais" (43) não foi aberto — 💭 provavelmente utilitário/caminhão, conferir antes de concluir.
- Nenhuma InfoCap traz "tipo de veículo" além de `categoria` e da descrição `veiculo` (📊 chaves do item: `anofab, anomod, bonus,
  bonusclas, cancelado, categoria, chassi, ci, cobertura, codfil, combustivel, cor, fipe, franquia, garantias, inivig, item, nosnum,
  numend, observacoes, passageiros, pervalmer, placa, renavam, telram, usualt_valmer, valmer, valmer_fipe_contr, veiculo, zerokm`).

## M2 · O que a apólice de VIDA traz para repetir na renovação (Resulta)

Comandos: `m1_medir.py` (5 VIND + 2 VGRP, todos os caminhos de campo) e `m2_vida.py` (TODAS as 22 VIND, 23 VGRP, 13 API, 1 APC, 4 MOB,
3 PREV dos 180 d), por apólice: `GET /documento?codfil&nosnum` · `GET /itens?codfil&nosnum&data=<data_dos_itens>` · `GET /prod_docs` ·
`GET /documento_anexos` · e, para VIND/API, `fonte.cliente_cru` (`GET /cliente`, sem cache). Saída = nomes de campo e "preenchido/visto".

### `/itens` — onde estariam o capital e as coberturas
| | VIND (22 apólices) | VGRP (23) | API (13) |
|---|---|---|---|
| apólices com item em `/itens` | 📊 **8 de 22** (36 %) | 📊 1 de 23 | 📊 9 de 13 |
| garantias por item | 📊 2 · 2 · 0 · 1 · 3 · 4 · 3 · 0 (15 no total) | — | 📊 0 em todos |
| garantia com `impseg` (capital) preenchido | 📊 14 de 15 | — | — |
| garantia com `premio` preenchido | 📊 11 de 15 | — | — |
| nomes das garantias (15) | ASSISTÊNCIA FUNERAL 4 · INVALIDEZ POR DOENÇA 3 · MORTE ACIDENTAL 2 · MORTE NATURAL 2 · INVALIDEZ POR ACIDENTE 2 · CONJUGÊ-MORTE 1 · INVALIDEZ FUNC PER P/DOEN 1 | — | — |

Campos do item de vida (📊 `m2.json Resulta.VIND.campos_do_item`, 8 itens): `nomseg` 7/8 · `cpf` 6/8 · `datnas` 7/8 · `cod_profissao` 4/8 ·
`observacoes` 4/8 · `perconj` 6/8 · `seguro_conjuge` 8/8 · `sexo_conj` 3/8 · `nome_conjuge`/`dt_nasc_conj` 0/8 · `num_sorteio` 0/8 ·
`inivig`, `telram`, `item` 8/8. Garantia: `seguradora, ramo, garantia, impseg, taxa (0), premio, percom (0), valcom (0), agrucom, valfran, franquia`.
🔴 **NÃO existe** sexo do segurado no item, **nem beneficiários, nem renda, nem fumante** em rota nenhuma lida.

### `/cliente` (o cadastro) — VIND, 22 clientes
📊 `cpf_cnpj` 22/22 · `nome` 22/22 · `sexo` 19/22 · `datanas` 15/22 · `estado_civil` 11/22 (`cod_estado_civil` 11/22) · `enderecos[]` 21/22 ·
`profissao` 7/22 (`cod_profissao` 7/22) · `escolaridade` 4/22 · `email` 20/22 · `telefones[]` 21/22. **Sem** renda, fumante, altura/peso.
(API, 13: sexo 13/13 · datanas 11/13 · estado_civil 10/13 · profissão 0/13.)

### `/documento` (a apólice) — 5 VIND, todos os campos
📊 preenchidos 5/5: `ramo` ("VIDA INDIVIDUAL"), `ramo_abrev`, `seguradora`, `inivig`/`fimvig`, `preliq`, `pretot`, `prepri`, `numpar`,
`forma_pag`, `per_c`/`val_c` (comissão), `parcelas[]` (58), `historico[]` (42, as anteriores ligadas por `nosnum_ren`), `sit_renovacao`,
`acompanhamento.emissao.url_apolice` 4/5. `sinistro` 0/5. **Nenhum campo de capital, cobertura ou beneficiário no `/documento`.**

### `/documento_anexos` — o PDF
📊 apólices com anexo `descricao = "A"` (o PDF da apólice, `.pdf`): **VIND 19 de 22 (86 %)** · VGRP 9 de 23 · API 10 de 13 · MOBI 20 de 25.
Rótulos de anexo VIND: `A` 27 · `B` 5 · `O` 3 · `I` 2 · `P`, `T`, `S` 1 (todos `.pdf`).

### `/prod_docs`
📊 5/5 com produtores (`codpro`, `indireto` 15/20, `per_r`/`val_r`) — o DONO sai daqui como no RE/auto (`dono.py`, regra indireto F).

### → O que a renovação de VIDA consegue repetir SEM inventar
| o que o formulário pede | fonte | cobertura medida |
|---|---|---|
| capital da Morte + adicionais (IPA, IFPD, DIH, DIT, doenças graves, funeral) | 🔴 **o PDF da apólice** (86 % têm); `/itens.garantias` só em 8/22 e incompleto (15 linhas; a Morte natural em 2) | 💭 a leitura do PDF de vida pela ficha NUNCA foi medida |
| CPF, nome, nascimento | `/itens` (quando há) ou `/cliente` | nascimento 15/22 no cadastro |
| sexo | `/cliente` | 19/22 |
| estado civil | `/cliente` (rótulo) | 11/22 · código do Agger não lido (P-129B-05) |
| CEP | `/cliente.enderecos[]` | 21/22 com endereço (o CEP dentro não foi contado) |
| profissão | `/cliente.profissao` ou `/itens.cod_profissao` | 7/22 · e é texto/código da InfoCap, não o da busca do Agger |
| fumante · renda · esporte radical | **nenhuma** | 0/22 → pergunta ao corretor (ou o pedido fica `falta_dado`) |
| beneficiários | **nenhuma rota** | não vão ao cálculo do Agger (o formulário não os pede nos 23 campos registrados) |

**A ficha única (130-B) e a vida:** 📊 `git grep -n "ficha" backend/app/services/multicalculo` → a ficha é lida em `madrugada.ficha_da_apolice`
(`madrugada.py:132-157`, `InfoCapProvider().detail(document_evidence_requested=True)` → `apolice_documental_do_pack`). O leitor do PDF
(`policy_document_evidence_service.py:1680-1863`) é GENÉRICO por ramo (linhas `coverage_row` rótulo + LMI + prêmio; `objeto_do_risco_local`
`:1072-1097` só procura placa, chassi, ano/modelo, CEP, atividade, importância segurada). **Mas a vida nunca chega lá:** `madrugada.py:482-492`
corta o item pela sigla da LISTA antes da ficha (`_ramo_do_agger` → `ramo_nao_cotado`). → 💭 a ficha "lê" vida no sentido de que o
leitor não depende do ramo, mas **nunca foi exercitada num PDF de vida** — o primeiro gate da 129-D é ler 3–5 PDFs de vida reais pela ficha
e contar se a linha da Morte e o capital saem.

**Resto das siglas (para a decisão de escopo):** 📊 `API` = "AP INDIVIDUAL" (13, TMAR 12) · `APC` = "AP COLETIVO" · `MOB` = **"IMOBILIARIA"**
(4, MAPF/PORT — incêndio/conteúdo/perda de aluguel: seguro de imóvel de imobiliária, NÃO é mobilidade) · `PREV` = "PREVIDENCIA" ·
`24HS` = "ASSISTENCIA 24H AUTO" · `MOBI` = "MOBILIDADE".

## M3 · O formulário de VIDA do Agger (a fixture)

Comando: `python -c "import json;v=json.load(open('backend/tests/fixtures/agger_formularios/formularios_por_ramo.json',encoding='utf-8'))['formularios']['vida'];print(v['n_campos'],v['n_obrigatorios'],len(v['campos']))"` → `47 12 23`.

📊 47 campos na tela · 12 obrigatórios · **só 23 registrados** na fixture (os 12 obrigatórios + 11 opcionais). Os outros 24 dos 47
NÃO estão na fixture (o mapa guardou só os campos com rótulo; o mesmo padrão nos outros ramos: condomínio 58/83, residencial 45/86,
empresarial 55/59, auto 77/139 — mesmo comando trocando a chave). 💭 provavelmente as seguradoras (checkbox), as configurações e
campos condicionais. Medido 06/10 na conta AutoFleet, login de teste, sem preencher (A-PROVA §10).

| # | campo (fc) | rótulo | tipo | obrig. | opções (fixture) | vem da apólice/InfoCap? (M2) |
|---|---|---|---|---|---|---|
| 1 | `cpf` | CPF | input | ✅ | — | ✅ `/itens.cpf` e `/cliente` |
| 2 | `nome` | Nome completo | input | ✅ | — | ✅ `/itens.nomseg` |
| 3 | `dataNasc` | Data de Nascimento | input | ✅ | — | ✅ `/itens.datnas` (e `/cliente`) |
| 4 | `sexo` | Sexo | mat-select | ✅ | Feminino · Masculino | ⚠️ o item de vida NÃO traz o sexo do segurado (só `sexo_conj`); vem do `/cliente` |
| 5 | `estadoCivil` | Estado civil | mat-select | ✅ | Solteiro(a) · Casado(a) · Separado(a) · Divorciado(a) · Viúvo(a) · União Estável | ⚠️ `/cliente` (rótulo); o código do Agger NÃO foi lido (P-129B-05) |
| 6 | `cep` | CEP Residencial | input | ✅ | — | ⚠️ `/cliente.enderecos[].cep` |
| 7 | `isFumante` | Fumante | mat-select | ✅ | Sim · Não | ❌ nenhuma rota da InfoCap — perguntar |
| 8 | `rendaMensal` | Renda Mensal | input | ✅ | — | ❌ (ver `/cliente` em M2) |
| 9 | `profissao` | Busca por profissão* | input (busca) | ✅ | lista do Agger (busca) | ⚠️ `/itens.cod_profissao` = CÓDIGO da InfoCap; casar com a busca do Agger = o problema da atividade do empresarial (D-129C-04) |
| 10 | `praticaEsporteRadical` | Pratica esportes radicais | input | ✅ | — | ❌ |
| 11 | `vigenciaIni` | Início de vigência | input | ✅ | — | ✅ o fim da vigência atual |
| 12 | `assistMorte` | Morte (capital) | input | ✅ | — | ⚠️ `/itens.garantias`: "MORTE NATURAL" em só 📊 2 linhas nas 22 VIND (só 8 têm item) → o capital da Morte, na prática, só do PDF (19/22 têm) |
| 13 | `fone` | Telefone | input | — | — | `/cliente` |
| 14 | `email` | Email | input | — | — | `/cliente` |
| 15 | `altura` | Altura (m) | input | — | — | ❌ |
| 16 | `peso` | Peso (kg) | input | — | — | ❌ |
| 17 | `isAppMorteAcidental` | Morte acidental | input | — | — | PDF |
| 18 | `isAppInvalidez` | Invalidez permanente (IPA) | input | — | — | PDF |
| 19 | `assistFuneral` | Assistência funeral | mat-select | — | Sem Assistência · Individual · Familiar | ⚠️ às vezes em `/itens.garantias` |
| 20 | `isDespesasMedicasHospitalares` | Diária de Internação Hospitalar (DIH) | input | — | — | PDF |
| 21 | `isInvalidezDoenca` | Invalidez por doença (IFPD) | input | — | — | ⚠️ às vezes em `/itens.garantias` |
| 22 | `valorDIT` | Diária de Incapacidade Temporária (DIT) | input | — | — | PDF |
| 23 | `valorDoencasGraves` | Doenças graves | input | — | — | PDF |
| 24–47 | (não registrados) | — | — | — | — | medir ao vivo (abrir a tela, sem preencher) |

**Moto:** 📊 a fixture tem 5 formulários — `condominio, empresarial, residencial, vida, auto` (`list(json.load(...)['formularios'])`);
**não há formulário de Motocicleta**. `ramos_codigo["31"] = "auto (carro, caminhão, motocicleta)"`. Nada gravado de corpo de moto.

**Vida Global e Acidentes Pessoais:** sem formulário na fixture. O que existe são as CHAVES por ramo na config de cada seguradora,
gravada dentro dos corpos de RE (📊 `grep -rhoE "percComiss[a-zA-Z]*" backend/tests/fixtures backend/portal_worker/multicalculo | sort | uniq -c`):
`percComissaoVida` 5 · `percDescontoVida` 5 · `percAgenciamentoVida` · `percComissaoVidaGlobal` 64 · `percComissaoAcidentesPessoais` 46 ·
`percComissaoViagem` 18 · `percComissaoAluguel` 16 · `percComissaoBike`/`Celular` 8; `montador.js:27` já lista `percComissaoVida`/
`percDescontoVida` em `SO_SEG`. 🔴 **Vida tem `percAgenciamento*`** (o agenciamento) — auto e RE não. 💭 o corpo de vida deve levar
comissão E agenciamento: só uma gravação de cotação de vida decide.

## M4 · O mapa do código para o ramo 91 (o molde da 129-C)

Números de linha por `grep -n` na árvore `fbb2a80`.

| # | arquivo:linha | hoje | o que muda para vida (91) |
|---|---|---|---|
| 1 | `backend/portal_worker/multicalculo/contrato.py:22-32` | `RAMO_AUTO=31`, `RAMOS_RE=(16,2,18)`, `RAMOS`, `NOME_DO_RAMO` | `RAMO_VIDA=91` (📊 `formularios_por_ramo.json` `ramos_codigo["91"]="vida"`; A-PROVA §10) + entrar em `RAMOS`/`NOME_DO_RAMO` |
| 2 | `contrato.py:266-415` (`CAMPOS_DO_PEDIDO_RE`) · `:508-514` (`campos_do_pedido` → `ValueError("ramo … não implementado")`) | catálogo só auto e RE | `CAMPOS_DO_PEDIDO_VIDA` (segurado + saúde/hábitos + vigência + coberturas); vida não tem grupo "risco" |
| 3 | `contrato.py:432-463` (`CODIGOS_VALIDOS_RE`) | códigos medidos do RE | códigos de vida (sexo, estado civil, fumante, funeral) — só a tela/bundle diz os números (§9.5) |
| 4 | `contrato.py:492-505` (`SEGURADORAS_DO_RAMO`, `CAMPO_DO_RAMO_NA_RENOVACAO`) | habilitada no ramo = `app/seguradoraStatus.<ramo>Status == 1` ∩ ativas na conta | a lista de VIDA — **não medida** (bundle + `calculo/seguradoras`: leitura ao vivo, sem cálculo) |
| 5 | `backend/portal_worker/multicalculo/presets.py:27-102` (auto) · `:151-262` (RE: `CHAVES_DE_COBERTURA_RE`, `TIPICAS_RE`, `ORDEM_RE`, `coberturas_re`) · `:264-272` (opções da renovação) | presets auto e RE | preset de vida: na RENOVAÇÃO só "anterior" (capital e coberturas da apólice, nunca inventar); cotação nova 💭 sem preset (capital é escolha do cliente) |
| 6 | `backend/portal_worker/multicalculo/montador.js:79` (`RAMO_AUTO=31`) · `:89` (`DESCONTO_DO_RAMO={16,2,18}`) · `:93` (`montarCalculosRE`) · `:187`, `:206` (`ramo !== 31` → RE) | todo ramo ≠ 31 cai no RE | despacho por ramo (vida ≠ RE); `percDescontoVida`/`percAgenciamentoVida` — forma só da gravação |
| 7 | `backend/portal_worker/multicalculo/agger_robo.py:61` (`lista_de_calculos`: ≠31 → RE) · `:296-303` (`cotacao_do_pedido`: `ramo not in RAMOS_RE` → `DisparoRecusado("ramo 91 não implementado")`) · `:310-470` (molde e montagem do RE) · `:857-858` (`disparar` → `_disparar_re`) · `:513`, `:581` (JS `ramo !== 31`) | auto e RE | `_cotacao_do_pedido_vida` com o molde da gravação; rota `/cotacao/vida/formulario` |
| 8 | `backend/portal_worker/multicalculo/leitor_agger.py:126-140` (`COBERTURAS_ECOADAS_RE_MEDIDAS`) · `:170-174` (`LISTA_BRANCA_POR_ENDPOINT`) · `:329-390` (recusas do RE, `classificar_mensagens`) · `:411-413` (`endpoint_de_calculos`: ≠31 → RE) · `:498-541` (`_oferta`/`ler_resposta`: `re_ = ramo != RAMO_AUTO`) | ≠31 lido como RE | lista branca e coberturas ecoadas de VIDA; famílias de recusa de vida (idade, profissão, capital, DPS) — só da gravação |
| 9 | `backend/app/services/multicalculo/pedido.py:34` (`RAMOS_ACEITOS`) · `:40-43` (`ramo_nao_cotado` "(vida, viagem, saúde…)") · `:567-575` (`RAMO_DO_AGGER_POR_FAMILIA` auto/resi/cond/empr) · `:770-792` (`_ramo_do_agger`; vida → `RamoIndisponivel(ramo_nao_cotado)` em `:789-791`) · `:795-842` (`de_apolice`) · `:1030-1047` (`de_ficha`) | vida = `ramo_nao_cotado` | `"vida": RAMO_VIDA` + `_de_apolice_vida` |
| 10 | `backend/app/providers/policy_data_provider.py:1283-1295` (`FAMILIAS_DE_RAMO`) | `"vida": ("vida","vind","vgrp","vida individual","vida em grupo","vidaind")`; **API, APC, MOB, MOBI, PREV ausentes** → `ramo_desconhecido` | ⚠️ **VGRP é vida EM GRUPO** (apólice de empresa, N vidas) — não é o formulário de Vida Individual: separar `vgrp` de `vind` antes de ligar o 91 (senão um VGRP vira pedido de vida individual) |
| 11 | `backend/app/services/multicalculo/porta.py:68` (`OPCOES_POR_RAMO`) · `:406-417` (`capacidades`) · `:513-516` (`RamoNaoSuportado`) · `:524-531` (`_comissao_re`) · `:557-559` (`_calcular_re`) · `:803`, `:854-858` (régua/ajuste por ramo) | auto e RE | o 91 nas opções, capacidades, comissão (+ agenciamento?) e despacho |
| 12 | `backend/app/services/multicalculo/madrugada.py:338-346` (`motivo_da_excecao`) · `:425-430` (`estado_derivado`: `veiculo_moto` → `pendente(ramo_nao_cotado)`) · `:482-492` (o ramo da LISTA decide antes da ficha) · `:599` (`ramo_agger`) | vida sai sem ler a ficha | vida passa a ler a ficha (PDF: capital e coberturas) e o perfil |
| 13 | `backend/app/services/multicalculo/perfil_da_renovacao.py:186-190` (`_ramo`) · `:235-375` (`montar`: auto = veículo/condutor; RE = endereço do risco) · `:313-321` (moto → marca) · `:68-78` (estado civil citando o formulário de vida) | sem vida | perfil de vida: `/cliente` (nascimento, sexo, estado civil, CEP) + `/itens.cod_profissao` + os que nenhuma fonte tem |
| 14 | `backend/app/services/multicalculo/renovacao.py:69-77` (`MOTIVOS_DE_PENDENCIA`, `MOTIVOS_NAO_COTAVEIS`, `FRASE_DO_MOTIVO`) | `ramo_nao_cotado` fora do denominador | vida passa a contar como cotável (muda `calculadas ÷ cotáveis`) |
| 15 | `backend/app/services/multicalculo/comparacao.py:322-323` (`REGRAS_POR_RAMO`; resto → `_classificar_generico` `:165`) · `:441-449` (`coberturas_publicas`) · `:579-733` (RE) | genérico para vida | régua de vida (mesmo capital + mesmas coberturas = comparável) |
| 16 | `backend/app/services/multicalculo/config.py:47-48` (`comissao.por_ramo {"16","2","18"}`) · `:60-61` (reajuste da básica por ramo) · `:105-109` (`preferencias_de_seguradoras {"31","16","2","18"}`) · `:404-467` (leitores por ramo) | sem "91" | `"91"` em comissão/agenciamento e preferências; reajuste do capital na renovação = 💭 decisão do Founder |
| 17 | `backend/app/services/multicalculo/proposta.py:194`, `:648`, `:874`, `:1034` · `mensagem.py:295-303` | "carro" ou RE | página/mensagem de vida (como D-129C-08: a página de RE foi para SPEC própria) |
| 18 | `backend/app/services/cotacao/pedido_da_conversa.py:27-36`, `:112-119` (Cotação Rápida: moto/frota/RCF-V → `ForaDoEscopo`) | vida fora | só se a 129-D abrir vida também na conversa |
| 19 | `backend/supabase/migrations/20261005_01_spec129b_motor.sql:300` (`multicalculo_pedidos.ramo int not null default 31`) | **sem CHECK de ramo** (📊 `grep -n -i ramo backend/supabase/migrations/*.sql \| grep -i check` → nada no multicálculo) | nenhuma migration para o código 91 |

**Quem marca `ramo_nao_cotado` hoje** (📊 `git grep -n "ramo_nao_cotado\|RamoIndisponivel" -- backend/app`):
1. `pedido._ramo_do_agger` (`pedido.py:770-792`): família `vida`/`viag`/`saud` → `ramo_nao_cotado`; FROT/"auto frota"/RCFV → `ramo_nao_cotado`;
   sigla fora de `FAMILIAS_DE_RAMO` (API, APC, MOB, MOBI, PREV, CAPI, GOC, NAUT…) → `ramo_desconhecido`.
2. `pedido.de_apolice:819-820` e `de_ficha:1046-1047`: a marca de moto (do `/itens.categoria`/`veiculo`) → `ramo_nao_cotado`.
3. `madrugada._avaliar:482-492`: a sigla da LISTA passa por `_ramo_do_agger` antes da ficha → `motivo_da_excecao:338-346` → `pendente`.
4. `madrugada.estado_derivado:427-430`: o cálculo que voltou `veiculo_moto` (a placa revelou moto, D-131-38) → `pendente(ramo_nao_cotado)`.
5. `porta.RamoNaoSuportado` → `madrugada:344-345` → `pendente(ramo_nao_cotado)`.
**O que a renovação faz:** o item fica `pendente` com "ramo que o Agger não cota (renove manualmente)" (`renovacao.py:77`), sai do
denominador das cotáveis (`renovacao.py:74`), não vai ao Agger, não lê a ficha.

**Há gravação de vida?** 📊 NÃO. `grep -rlE '"ramo": ?91\b|vidaStatus|"/cotacao/vida' --include=*.json .` → nada; `agger_ramos/` só tem
condomínio/residencial/empresarial; `agger_formularios` tem o DOM de vida (23 de 47 campos), sem corpo, sem seguradoras, sem resposta.
O A-PROVA §10 registra 📊 **32 negócios 91 na Resulta em 730 d (28 em 365 d, 9 em 90 d, 4 em 30 d)** e 1 na AutoFleet — histórico real
que a 129-D pode LER (GET `negocio/busca/v2`, `cotacao/versoes`, `cotacao/calculos`, sem calcular), como a 129-C leu 45 negócios de RE
para tirar as 9 gravações (D-129C-02).

## M5 · Mobi Livre no Agger

📊 O "Nova Cotação" tem 13 entradas (A-PROVA §10): Carro · Caminhão · Motocicleta · Residencial · Condomínio · Empresarial · Vida
Individual · Vida Global · **Acidentes Pessoais** · Viagem · Aluguel · **Bike** · Celular. Nenhuma é Mobi/mobilidade.
- O Mobi Livre (SURA: AP na mobilidade + RC do condutor) **não tem entrada própria**. 💭 a parte de AP talvez saia por "Acidentes
  Pessoais" (formulário NÃO mapeado; as chaves `percComissaoAcidentesPessoais` existem na config das seguradoras), mas a RC do condutor
  não está em nenhuma das 13 → 💭 o Mobi Livre como produto não é cotável no Agger. "Bike" é bicicleta, outro produto.
- 📊 A SURA não está entre as 14 seguradoras da Resulta e está entre as 15 da AutoFleet (A-PROVA §11) — e o MOBI mora na AutoFleet (M1).
- **Medir ao vivo (sem cálculo):** abrir `/cotacao/acidentes_pessoais/formulario`, ler campos e seguradoras habilitadas
  (`seguradoraStatus.<ap>Status`); SURA fora do AP do Agger = MOBI fora de vez.

## O que ficou por medir

**Só a cotação/sessão AO VIVO responde (Agger, conta `cotador@` da Resulta):**
1. As seguradoras de VIDA habilitadas: `app/seguradoraStatus.<vida>Status` no bundle (o nome exato da chave de vida é desconhecido) ∩
   `calculo/seguradoras` ativas da Resulta — 💭 candidatas pela carteira: Porto, Tokio, Allianz, SulAmérica, HDI, Liberty, MetLife (a
   Resulta tem Metlife/Alfa/Chubb/Axa/SulAmérica/Sompo configuradas, A-PROVA §11). ⚠️ a carteira VIND tem MAG e UNIV, que não estão
   na conta do Agger.
2. O corpo do `calcularV2` de vida (`cotacao.ramo=91`, onde vão capital/coberturas, comissão e **agenciamento**) e os 24 campos não
   registrados do formulário — 💭 sem cálculo: LER os 📊 32 negócios 91 já existentes no Agger da Resulta (`negocio/busca/v2` →
   `cotacao/versoes` → `cotacao/calculos`), como a 129-C fez com o RE (D-129C-02). Precisa de login no Agger (fora desta tarefa).
3. Os rótulos do resultado (`resultados[]` de vida, coberturas ecoadas, famílias de recusa: idade, profissão, capital, DPS).
4. Os códigos de `sexo`/`estadoCivil`/`isFumante`/`assistFuneral` e a lista de profissões da busca do Agger (o casamento com
   `cod_profissao`/`profissao` da InfoCap).
5. Acidentes Pessoais e Vida Global: formulário e seguradoras (para decidir AP — API 13 em 180 d — e se VGRP cabe em "Vida Global").
6. Mobi: se a SURA está habilitada em "Acidentes Pessoais" no Agger.

**Medível sem o Agger, que não coube aqui:**
7. A ficha (o leitor de PDF da 130-B) sobre 3–5 PDFs de VIND reais: sai a linha da Morte e o capital? (exige rodar o leitor com modelo — custo e PDF real).
8. O CEP dentro de `/cliente.enderecos[]` dos 22 VIND (contei só que a lista existe: 21/22).
9. As 627 AUTO dos últimos 90 dias da AutoFleet (o orçamento de 900 s esgotou nas 684 dos próximos 90) e as 33 leituras de `/itens` que falharam; e o que é `categoria = "Demais"` (43).
10. Se VGRP (vida em grupo, 23) é cotável em "Vida Global" — 📊 só 1 de 23 tem item em `/itens`; a apólice de grupo não é de uma pessoa.

## Notas de método
- 📊 Cada número acima saiu de `m1.log`/`m1.json`/`m2.log`/`m2.json` (rascunho), produzidos pelos scripts citados; nomes de produtor
  foram retirados do `m1.json` depois da medição (o campo `produtor` da linha de `/renovacoes` traz nome de funcionário).
- ⚠️ Os números de 30 dias do BLOCO0 da 131-0 (Resulta 99: VIND 6, VGRP 3) e os de 90 d aqui (VIND 11+11, VGRP 11+12) são janelas diferentes; não comparar como série.
- Nenhum cálculo, login ou escrita: Agger não tocado; InfoCap só GET (o `POST /login` da InfoCap é o da autenticação do próprio `FonteInfocap`);
  banco só SELECT (`tenant_connections`, `companies`, `renovacoes`); Redis não usado (`_TTL_CACHE_S = 0`).
