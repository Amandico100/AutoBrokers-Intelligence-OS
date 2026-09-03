# CorpAPI / InfoCap — O CATÁLOGO OFICIAL, lido da coleção Postman pública

> **Frente de pesquisa aberta pelo Founder em 03/09/2026.** Papel: PESQUISADOR EXTERNO
> (protocolo AAA v11.2 §7.3). **Somente leitura.** ⛔ Nenhuma chamada foi feita à InfoCap
> nesta pesquisa. Nenhuma credencial foi lida. Nenhum dado de pessoa aparece aqui.
>
> **Autoridade de EXISTÊNCIA continua sendo o censo medido**
> ([`providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md`](../providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md), 03/09/2026).
> Este documento é a **DOCUMENTAÇÃO DO FORNECEDOR** — diz o que a InfoCap *declara* oferecer.
> Onde os dois discordam: **o censo vence sobre existência; a doc vence sobre parâmetros.**

---

## EXECUTION CARD

```
OUTCOME ..............  o Founder sabe, pela doc oficial, TODA a superfície da CorpAPI —
                        inclusive as 19 requisições de ESCRITA que o censo nunca tocou —
                        e sabe o que falta para um agente PREENCHER dado no InfoCap
MÉTODO ...............  download do JSON da coleção pública pelo endpoint de export do
                        Postman documenter. ZERO chamadas a api.corpnuvem.com
COMANDO ..............  curl -sS "https://documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi?segregateAuth=true&versionTag=latest"
                        -> HTTP 200 · 66.660 bytes
FONTE ................  https://documenter.getpostman.com/view/33455116/2sAYkBrLmi
                        coleção "CorpAPI" · owner 33455116 · publishedId 2sAYkBrLmi
                        publishDate 2025-03-14T13:47:07.000Z  (campo info.publishDate do JSON)
MEDIDO ...............  51 requests · 36 rotas CorpAPI distintas + 1 POST direto a bucket S3
                        29 GET · 12 POST · 6 DELETE · 3 PUT · 1 PATCH
ESCRITAS .............  nenhuma. Em lugar nenhum.
DATA .................  03/09/2026
```

---

## 0. 🔴 O QUE SE CONSEGUIU DA COLEÇÃO, E COMO

A página `documenter.getpostman.com/view/...` é renderizada por JS e devolve só o
`<title>CorpAPI</title>` a um leitor de HTML. 📊 O primeiro `WebFetch` sobre ela devolveu
**zero rotas** — a resposta foi literalmente "there's no actual Postman collection data".

**O que funcionou** foi o endpoint de export do próprio documenter, que serve o JSON no
schema v2.0.0 da coleção, sem autenticação:

```bash
curl -sS "https://documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi?segregateAuth=true&versionTag=latest"
# HTTP 200 · 66660 bytes · {"info":{"name":"CorpAPI","schema":".../v2.0.0/collection.json",...}}
```

📊 **A coleção veio COMPLETA: 12 pastas, 51 requests.** Contagem reproduzível:

```bash
python -c "import json;d=json.load(open('corpapi.json',encoding='utf-8'));n=[0]
def w(i):
  for it in i:
    if 'item' in it: w(it['item'])
    else: n[0]+=1
w(d['item']);print(n[0])"     # -> 51
```

### ⚠️ E a primeira coisa a saber é o quanto ela NÃO diz

📊 Medido sobre o JSON baixado:

| o que uma doc de API costuma ter | a CorpAPI tem |
|---|---|
| descrição por rota | **1 de 51** — só o `POST /cliente`: *"Insert de clientes. Pode ser inserido também telefones, emails e enderecos."* |
| exemplo de resposta | **3 rotas de 51** (`/documento`, `/producao`, `/renovacoes`) — 6 respostas salvas ao todo |
| descrição por parâmetro | **0** — todo `description` de query param veio vazio |
| `collection.auth` declarado | **null** |
| `collection.variable` (`base_url`) | **null** — o `{{base_url}}` não tem valor publicado |
| marcação de campo obrigatório | **nenhuma**, em nenhum corpo |
| código de erro documentado | **2**, e ambos são `404` |
| semântica de idempotência / duplicata | **nenhuma** |

🔴 **Conclusão de método, não de opinião: esta coleção é um esqueleto de requisições, não
uma especificação.** Prova que a rota existe e mostra a FORMA do corpo. **Não** diz o que é
obrigatório, o que a API faz quando o dado já existe, nem o que ela devolve quando escreve.
Toda decisão de escrita que dependa disso exige **medição própria** — e a InfoCap não
publica sandbox nesta coleção.

---

## 1. O CATÁLOGO — 51 requests, por pasta

Legenda da coluna **CENSO**:
`200` medido classe 200 · `500`/`400` medido · `403` = 403-SigV4 (não existe no Gateway) ·
`—` = **nunca tocada pelo censo**.

### 1.1 · `Autenticação` — 2

| # | método | rota | corpo / params | CENSO |
|---|---|---|---|---|
| 1 | `POST` | `/login` | `{"email","senha","aplicacao":0}` · header `Content-Type` | **200** (26 chaves, 17 flags todas `T`) |
| 2 | `POST` | `/logout` | sem corpo · headers `Content-Type`, `Authorization` | — |

⚠️ **`/logout` é a segunda escrita da API e o censo não a conhecia.** É a única rota POST
inofensiva do catálogo: encerra a sessão do token, não muda dado da corretora.

### 1.2 · `Documentos/Produção` — 7, todas GET

| # | rota | query params **da doc** | CENSO |
|---|---|---|---|
| 3 | `/documento` | `codfil`, `nosnum` | **200** |
| 4 | `/producao` | `texto`, **`dt_ini`**, **`dt_fim`**, `ordem`, `orientacao`, `so_renovados`, `so_emitidos` | **500 ×3** 🔴 §2.1 |
| 5 | `/renovacoes` | `dt_ini`, `dt_fim`, `qtd_pag`, `pag`, `ordem`, `orientacao`, `texto`, `cancelado`, `resgates`, **`codcli`**, **`codram`**, **`codcia`** | **200** |
| 6 | `/documentos` | `ordem`, `qtd_pag`, `pag`, **`periodo=datinc`**, **`datini`**, **`datfim`**, `codfil` | **200** (censo usou só `texto=`) 🔴 §2.2 |
| 7 | `/documento_anexos` | `codfil`, `nosnum` | — |
| 8 | `/documento_endossos` | `codfil`, `nosnum` | — |
| 9 | `/itens` | `codfil`, **`data`**, `nosnum` | **200** |

📊 **O exemplo 200 de `/documento` traz 79 campos de primeiro nível + `parcelas[]`.**
Comissão: `campo_base_c:3`, `base_c:3221.4`, `per_c:15`, `val_c:483.21`,
`forma_recebimento_c:1`, `val_ca:0`, mais o par de **co-corretagem**
`campo_base_cp / base_cp / per_cp / val_cp / forma_recebimento_cp`.
`parcelas[]` traz `parc · tipo · forma_pagamento · vlbasecom · vlbasecomquit · datvenc ·
vlvenc · datquit · vlquit · cod_forma_pagamento`.

🔴 **É a confirmação documental do achado #7 do censo: `datquit`/`vlquit` são a única
evidência de comissão RECEBIDA em toda a API — e ela é por apólice, uma chamada de cada vez.**

📊 Campos do exemplo que o censo não destaca e valem dinheiro:
`sit_acompanhamento` + `sit_acompanhamento_txt` (no exemplo: *"Pendente de emissão - em
atraso"*), `recusado`, `cancelado`, `codcanal`, `canal_vendas_descricao`, `codmulti`,
`importado_pelo_incorp`, `motivo_endosso`/`motivo_endosso_txt`,
`ad_receb_data`/`ad_entr_data` (entrega do documento ao cliente),
`ad_receb_doc_fisico`/`ad_receb_doc_digital`.

### 1.3 · `Cliente` — 9 (7 GET · 1 POST · 1 DELETE)

| # | método | rota | params / corpo | CENSO |
|---|---|---|---|---|
| 10 | `GET` | `/cliente` | `codfil`, `codigo` | **200** |
| 11 | `GET` | `/clientes` | **nenhum** | — |
| 12 | `GET` | `/cliente_cpf` | `codfil`, `cpf_cnpj` | **200** |
| 13 | `GET` | `/cliente_anexos` | `codfil`, `codigo` | — |
| 14 | `GET` | `/lista_clientes` | `texto` | **200** |
| 15 | `GET` | `/busca_cpf` | `cpf_cnpj` | — |
| 16 | 🔴 `POST` | `/cliente` | ver abaixo | — |
| 17 | 🔴 `DELETE` | `/cliente` | `codfil`, `codigo` | — |
| 18 | `GET` | `/cliente_ligacoes` | `codigo` | **200** |

📊 **Corpo do `POST /cliente`, verbatim da coleção:**

```json
{ "codfil": 1, "nome": "teste", "ativo": "F", "cpf_cnpj": null,
  "datanas": "04/05/1915", "pessoa": "F", "sexo": "M", "observacoes": "",
  "profissao": null, "estado_civil": null, "escolaridade": null, "usuinc": null,
  "enderecos": [ { "tipo":"", "logradouro":"", "numero":123, "complemento":"",
                   "bairro":null, "cep":00000000, "padrao":"T",
                   "cidade":"NOVO HAMBURGO", "estado":"RS" } ],
  "emails":    [ { "email":"hotmail@gmail.com", "padrao":"T" } ],
  "telefones": [ { "tipo":"C", "ddd":51, "numero":"35561006", "ramal":null,
                   "padrao":"T", "codcon":null, "codemp":null } ] }
```

🔴 **`/cliente` tem POST e DELETE e NÃO tem PUT nem PATCH.** É fato da doc, não leitura:
no JSON o path `/cliente` aparece com exatamente `['DELETE','GET','POST']`.
**Um agente pode criar um cliente e pode apagá-lo. Não pode corrigi-lo.** Consertar o nome
de um cliente criado errado exige apagar e recriar — e apagar leva junto o que estiver
pendurado nele.

### 1.4 · `Endereço` · `Email` · `Telefone` — 9 escritas, o CRUD completo dos contatos

| # | método | rota | corpo (chaves) | CENSO |
|---|---|---|---|---|
| 19 | `POST` | `/endereco` | `codcli, logradouro, numero, complemento, bairro, cep, cidade, estado, tipo, padrao` | — |
| 20 | `PUT` | `/endereco` | **`codigo`** + `codcli, tipo, logradouro, numero, complemento, bairro, cep, padrao, cidade, estado` | — |
| 21 | `DELETE` | `/endereco` | query `codigo` | — |
| 22 | `POST` | `/email` | `codcli, padrao, email` | — |
| 23 | `PUT` | `/email` | **`codigo`** + `codcli, padrao, email` | — |
| 24 | `DELETE` | `/email` | query `codigo` | — |
| 25 | `POST` | `/telefone` | `codcli, tipo, ddd, numero, padrao` | — |
| 26 | `PUT` | `/telefone` | **`codigo`** + `codcli, tipo, ddd, numero, padrao` | — |
| 27 | `DELETE` | `/telefone` | query `codigo` | — |

⚠️ **A assimetria é o achado:** contato tem CRUD inteiro; o cliente que os carrega, não.
📊 `padrao: "T"/"F"` marca o registro principal. Nada na doc diz o que acontece ao criar um
segundo `padrao:"T"` — 💭 plausível que o anterior caia para `F`, **não provado**.

### 1.5 · `Negociações` — 8 (o funil de vendas / oportunidades)

| # | método | rota | params / corpo | CENSO |
|---|---|---|---|---|
| 28 | `GET` | `/negocios_andamento` | `dtini, dtfim, texto, qtd_pag, pag, ordem, orientacao, status, calculo` | — |
| 29 | `GET` | `/em_calculo` | `dtini, dtfim, texto, qtd_pag, pag, ordem, orientacao, status` | — |
| 30 | `GET` | `/negocios_finalizados` | `texto, pag, ordem, orientacao, dtini, dtfim, qtd_pag, status` | — |
| 31 | `GET` | `/negocio` | `codfil, codigo` | — |
| 32 | `GET` | `/negocio_anexos` | `codfil, codigo` | — |
| 33 | *(dup)* | `/negocios_andamento` | request chamado "negocios", mesma URL do #28 | — |
| 34 | 🔴 `POST` | `/negocio` | 38 chaves — abaixo | — |
| 35 | 🔴 `DELETE` | `/negocio` | `codfil, codigo` | — |

📊 **Chaves do corpo do `POST /negocio`, verbatim:** `cpf_cnpj · codram · ddd_fone ·
numero_fone · email · produto_ja_possui · produto_fimvig · produto_seguradora ·
observacoes · val_premio · usuinc · datinc · usualt · datalt · produto_codfil ·
produto_nosnum · produto_numapo · prioridade · etapa · status · per_c · val_c ·
campo_base_r · per_r · val_r · codcia · codcamp · tipo · dtini_negociacao ·
usuini_negociacao · dtfim_negociacao · usufim_negociacao · codusu_responsavel ·
codopo_rep · doc_codfil · doc_nosnum · motivo_perda · codfil · codcli`

🔴 **Este é o achado comercial da PARTE 1.** O funil da corretora — etapa, prioridade,
status, responsável, **motivo de perda**, prêmio esperado, comissão esperada (`per_c/val_c`)
e repasse esperado (`per_r/val_r`) — é **legível e escrevível** pela API, e o censo nunca o
tocou, porque o MAPA antigo não sabia que estas rotas existiam.
⚠️ O JSON de exemplo é **sintaticamente inválido** (`"codram": ,`), o que confirma que
ninguém o validou: é rascunho de tela, não contrato.

### 1.6 · `Produtores` — 6 (3 leitura + 3 escrita) 🔴

| # | método | rota | params / corpo | CENSO |
|---|---|---|---|---|
| 36 | `GET` | `/agentes` | `texto` | — |
| 37 | `GET` | `/produtores` | `texto`, `codage` | — |
| 38 | `GET` | `/prod_docs` | `codfil`, `nosnum` | — *(só visto aninhado)* |
| 39 | 🔴 `POST` | `/prod_docs` | `codfil, nosnum, codage, codpro, indireto, perpart, campo_base_r, per_r, forma_repasse_r` | — |
| 40 | 🔴 `PATCH` | `/prod_docs` | `codfil, nosnum, codage, codpro, codpro_novo, codage_novo, indireto` | — |
| 41 | 🔴 `DELETE` | `/prod_docs` | `codfil, nosnum, codage, codpro` | — |

🔴 **`/prod_docs` é rota de primeira classe — e é ESCRITÁVEL.** O censo só a viu como array
aninhado dentro de `/renovacoes` e `/documento`. A doc mostra rota própria, com `GET` por
apólice e **três verbos de escrita**.

📊 **A doc confirma dois campos que o censo listou como "não provados":** `indireto`
("T"/"F") e `campo_base_r` **existem no corpo do POST** — logo são campos reais do modelo,
não lixo. E aparecem dois novos: **`perpart`** (percentual de participação, `100` no
exemplo) e **`forma_repasse_r`** (`5`, o mesmo valor de `campo_base_r`).
⚠️ Isso **não** prova o significado deles. Prova que existem e que a InfoCap espera recebê-los.

🔴 **Consequência direta para a SPEC-094:** `repasse.producer_accrued` é uma métrica sobre
uma tabela que **um agente do AutoBrokers poderia reescrever**. Trocar o produtor de uma
apólice (`PATCH /prod_docs` com `codpro_novo`) muda quanto a corretora deve a quem. **É a
escrita de maior consequência financeira de todo o catálogo, e é um PATCH sem confirmação
documentada.**

### 1.7 · `Ramos` — 2 · `Sinistro` — 1 · `BI` — 1

| # | método | rota | params **da doc** | CENSO |
|---|---|---|---|---|
| 42 | `GET` | `/ramos` | nenhum | **200** · 50 |
| 43 | `GET` | `/lista_ramos` | `telram` | — |
| 44 | `GET` | `/sinistros` | 🔴 `tipo_sinistro`, `data_inicial`, `data_final`, `tipo_data`, `situacao`, `qtd_pag`, `pagina` | **200** · 5.729 em 26,3 s |
| 45 | `GET` | `/documentos_bi` | `datini`, `datfim`, `data`, **`tipo_doc=TODOS`** | **200** · 1.680 |

🔴 **`/sinistros` tem SETE parâmetros documentados e o censo a chamou com `codfil=1`.**
Os 26,3 s e os 5.729 registros são o **acervo inteiro, sem filtro**. Com
`data_inicial`/`data_final`/`tipo_data` a rota fica utilizável em produção; com
`qtd_pag`/`pagina` ela **pagina**, o que o censo não sabia. ⚠️ `tipo_data=oco` no exemplo
sugere base temporal escolhível (ocorrência × aviso × encerramento), o que casa com os campos
`datoco/datavi/datenc/datlib/datvis` que o censo mediu. **Qual conjunto é aceito não está
provado** — a doc não enumera valores.

⚠️ **`tipo_doc`:** o censo usou `A`; a doc usa `TODOS`. 💭 `TODOS` provavelmente inclui
endosso e cancelamento além da apólice. **Se for, o golden control de 1.680 apólices é o
recorte `A` — e existe um universo maior que ninguém contou.**

### 1.8 · `InCorp` — 6 🔴 **a porta pela qual entra uma APÓLICE**

| # | método | rota | corpo / params |
|---|---|---|---|
| 46 | `GET` | `/incorp_url_post` | `nome_arquivo` → devolve URL pré-assinada de upload |
| 47 | `POST` | `https://area-transferencia-fenix-prod.s3.amazonaws.com/` | form-data: `key`, `x-amz-security-token`, `policy`, `AWSAccessKeyId`, `signature`, `file` |
| 48 | `GET` | `/incorp_url_download` | `key` |
| 49 | 🔴 `POST` | `/incorp` | `{"link": "LINK DISPONIBILIZADO PELO GET:incorp_url_download"}` |
| 50 | 🔴 `POST` | `/incorp_contexto` | *"PASSAR JSON GERADO PELO POST:/INCORP INSERINDO AGENTE E PRODUTOR"* |
| 51 | 🔴 `POST` | `/incorp_documento` | *"PASSAR JSON OBTIDO PELO POST:/INCORP_CONTEXTO"* + `"path_anexo_s3"` + *"PASSAR JSON OBTIDO PELO POST:/INCORP"* |

📊 **O fluxo, lido dos três corpos:** pede URL assinada → sobe o PDF da apólice no S3 →
`/incorp` **lê o PDF e devolve um JSON estruturado** → `/incorp_contexto` recebe esse JSON
**acrescido de agente e produtor** → `/incorp_documento` **grava a apólice** com o anexo.

🔴 **É a resposta mais forte à pergunta do Founder, e é melhor do que "cadastrar cliente":**
a InfoCap já tem caminho oficial para **um robô importar apólice a partir do PDF**, e o passo
`/incorp_contexto` é exatamente onde entra decisão humana — *qual produtor leva o repasse
desta apólice*. 📊 O campo `importado_pelo_incorp` no `/documento` confirma que a InfoCap
**marca** o que entrou por esse caminho: o rastro já existe no modelo dela.

⚠️ **E é o menos documentado dos três:** os corpos são frases em português maiúsculo, não
JSON. Nenhum exemplo de resposta. Nenhum código de erro. **Não é implementável sem uma
rodada de medição com um PDF real, num ambiente que possa sujar.**

---

## 2. 🔴 O CRUZAMENTO COM O CENSO — quatro achados

### 2.1 · 🔴 O `/producao` que dá 500 provavelmente está sendo chamado errado

📊 O censo mediu **HTTP 500 em três conjuntos de parâmetros** — `{datini,datfim}`,
`{texto}`, `{codfil,texto}` (CENSUS-v2 §4.2) — e registrou *"sem documentação da API para
tentar um quarto"*. **Agora há documentação.**

```
doc oficial:  /producao?texto=&dt_ini=22/02/2022&dt_fim=22/02/2022
                       &ordem=inivig&orientacao=asc&so_renovados=t&so_emitidos=x
censo:        /producao?datini=…&datfim=…      <- NOME ERRADO do parâmetro
              /producao?texto=…                 <- sem as datas
```

📊 E **o código de produção chama a forma que dá 500**:
```
backend/app/api/infocap_connector.py:3115  {"path": "/producao", "params": {"texto": digits}}
backend/app/api/infocap_connector.py:3126  {"path": "/producao", "params": {"texto": name}}
```
comando: `grep -n "producao" backend/app/api/infocap_connector.py` → **2 linhas, ambas só `texto`**.

💭 **INFERÊNCIA, não medição:** o 500 é a API estourando por falta de `dt_ini`/`dt_fim`.
🔴 **O que fecha isto é UMA chamada GET** com os sete parâmetros da doc. Se passar, a sonda
de CPF/nome do produto volta a funcionar e `/producao` entrega `sin_situacao`, `cancelado`,
`renovacao_situacao` e `historico_imagem` **em lista** — o que hoje só se obtém apólice a apólice.

### 2.2 · 🔴 `/documentos` é uma lista paginada por data, e foi usada como busca por texto

📊 O censo chamou `/documentos?texto=<numapo>` e leu **1 registro** (CENSUS-v2 §4.1).
📊 A doc mostra `ordem · qtd_pag · pag · periodo=datinc · datini · datfim · codfil`.

**São duas rotas diferentes escondidas no mesmo path.** Com `periodo=datinc` + janela, ela é
a **lista de tudo que foi CADASTRADO no período** — a base temporal que falta em
`/documentos_bi` (que filtra `inivig`) e em `/renovacoes` (que filtra `fimvig`).
🔴 **É a candidata direta para o buraco de `COMMISSION_ACCRUAL_DATE` da SPEC-094:** `datinc`
é quando a apólice entrou no sistema, e o próprio nome `periodo=` sugere que há outros
valores aceitos. **Não medido. Uma chamada resolve.**

### 2.3 · As 34 rotas 403-SigV4 do censo **não estão na documentação** — e isso as confirma

📊 Nenhuma das 18 rotas do MAPA antigo (`/parcelas`, `/comissao`, `/comissoes`,
`/financeiro`, `/titulos`, `/contas_receber`, `/contas_pagar`, `/fluxo_caixa`,
`/faturamento`, `/vendedores`, `/usuarios`, `/propostas`, `/sinistro`, `/endossos`,
`/tarefas`, `/agenda`, `/cias`, `/filiais`) aparece na coleção oficial. Nem as 16 variantes.

```bash
# conferência sobre o JSON baixado — todas devolvem 0
# (grep -o | wc -l, nunca grep -c: o JSON é UMA linha só — ver §6)
for r in parcelas comissao comissoes financeiro titulos contas_receber contas_pagar \
         fluxo_caixa faturamento vendedores usuarios propostas endossos tarefas agenda cias filiais; do
  printf "%-16s %s\n" "$r" "$(grep -o "base_url}}/$r" corpapi.json | wc -l)"
done
```

🔴 **É a linha de CONTROLE que faltava ao censo (CLAUDE.md §9.2).** O censo concluiu "não
existem" a partir do comportamento do Gateway. A doc oficial, publicada pelo fornecedor,
**também não as lista**. Duas fontes independentes, mesma resposta.
**`financial.cashflow` = UNAVAILABLE está agora confirmado por documentação, não só por 403.**

⚠️ **Corolário de roadmap:** comissão RECEBIDA, parcela em aberto, inadimplência e fluxo de
caixa **não têm rota em lote na CorpAPI, por desenho do fornecedor.** O único caminho medido
é `/documento.parcelas[]` — **uma chamada por apólice**.
📊 Para as 1.680 apólices da Resulta a 0,83 s cada (latência de `/documento`, CENSUS-v2 §4.1),
uma varredura serial custa **≈ 23 minutos** de relógio (`1680 × 0,83 s = 1.394 s`).
🔴 **Não é detalhe de performance: é a razão pela qual "comissão recebida" precisa ser um JOB
NOTURNO com carteira materializada, e nunca uma pergunta de chat.**

### 2.4 · Três rotas respondem 200 e a documentação oficial NÃO as lista

📊 `/seguradoras` (200, 61 registros) · `/cotacoes` (200, 7) · `/atendimentos` (200, 15, com
a lista na chave `tarefas`) — e `/usuario` (400 `Unknown field.`). Nenhuma está na coleção.

⚠️ **A doc não é exaustiva.** Isso corta dos dois lados: existem rotas não documentadas que
funcionam **e** pode existir escrita não documentada.
🔴 **A regra prática: para EXISTÊNCIA, a doc é limite INFERIOR, nunca superior. Para
PARÂMETRO, a doc é a única fonte que há.**

### 2.5 · O placar do cruzamento

```
rotas na doc                       36 CorpAPI + 1 S3     (51 requests)
rotas na doc que o censo mediu     13   (12 classe 200 + /producao 500)
rotas na doc NUNCA tocadas         23   -> 17 GET + as escritas
requisições de ESCRITA na doc      22   -> 19 de negócio + /login + /logout + o POST no S3
rotas 200 fora da doc               3   /seguradoras · /cotacoes · /atendimentos
rotas 403-SigV4 presentes na doc    0   <- confirmação por segunda fonte
```

---

## 3. 🔴 A RESPOSTA AO FOUNDER — um agente pode PREENCHER dado no InfoCap?

> ## SIM, por cinco portas distintas. Mas só UMA delas é de baixo risco, e NENHUMA foi medida.

### 3.1 · As cinco portas, por consequência crescente

| porta | rotas | o que o agente conseguiria | risco se errar |
|---|---|---|---|
| **1. contato** | `POST/PUT/DELETE` em `/endereco` `/email` `/telefone` | corrigir e-mail e telefone do segurado a partir do WhatsApp | **baixo** — tem PUT, dá para desfazer |
| **2. cliente novo** | `POST /cliente` (+ `DELETE`) | lançar lista de novos clientes; cadastrar quem chegou pelo chat, com endereço/e-mail/telefone **num único POST** | 🔴 **médio-alto** — **não tem UPDATE**; errou, só apagando |
| **3. funil** | `POST /negocio` (+ `DELETE`) | abrir oportunidade a partir de uma conversa; registrar cotação pedida, com prêmio e comissão esperados | **médio** — dado comercial, não contratual |
| **4. repasse** | `POST/PATCH/DELETE /prod_docs` | atribuir ou trocar o produtor de uma apólice | 🔴🔴 **ALTO — muda quanto a corretora paga, e a quem** |
| **5. apólice** | `/incorp_url_post` → S3 → `/incorp` → `/incorp_contexto` → `/incorp_documento` | **importar apólice do PDF da seguradora, com anexo** | 🔴🔴 **ALTO — cria o fato canônico do negócio** |

### 3.2 · Campos obrigatórios — 🔴 **a doc NÃO diz, e essa é a resposta**

📊 Zero campos marcados como obrigatórios em 51 requests. Os corpos são exemplos com valores
de teste (`"nome":"teste"`, `"cep":00000000`, `"codcli":123`). O que se pode afirmar **pela
forma** dos corpos, e só isso:

```
POST /cliente     codfil e nome são os únicos sem null no exemplo. cpf_cnpj vem NULL —
                  💭 logo a API aceita cliente SEM CPF, e é assim que nasce duplicata
POST /endereco    exige codcli   -> o cliente tem de existir ANTES
POST /email       exige codcli
POST /telefone    exige codcli
PUT  (os três)    exige codigo   -> o id do REGISTRO, que só vem de um GET anterior
POST /prod_docs   exige a chave composta codfil + nosnum + codage + codpro
POST /negocio     exige codfil + codcli; o resto é opcional pela forma
```

⚠️ 📊 `"cep": 00000000` no exemplo é **número, não string** — perde o zero à esquerda.
🔴 Um CEP `01310-100` enviado como número vira `1310100`. **A doc do fornecedor ensina o
bug.** Quem implementar copiando o exemplo escreve CEP errado em produção.

### 3.3 · Os riscos, nomeados com evidência

| risco | evidência | por que importa |
|---|---|---|
| **sem idempotência** | 📊 nenhuma rota aceita chave de idempotência; nenhum header `Idempotency-Key` em 51 requests | um retry de rede em `POST /cliente` **cria o segundo cliente** — e o produto já tem retry/backoff (`fonte_infocap.py`) |
| **sem UPDATE de cliente** | 📊 path `/cliente` = `['DELETE','GET','POST']` | não existe "corrigir". A operação de conserto é destrutiva |
| **DELETE sem escopo declarado** | 📊 `DELETE /cliente?codfil=1&codigo=` sem confirmação e sem soft-delete documentado | 💭 se apagar em cascata contatos e histórico, é perda de dado — **CLAUDE.md §10 (1), condição de PARADA** |
| **escrita sem resposta documentada** | 📊 **0 de 19** escritas tem exemplo de resposta | o agente **não sabe ler o `codigo` do que acabou de criar** — e sem ele não há como pendurar endereço no cliente novo |
| **duplicata por CPF nulo** | 📊 `cpf_cnpj: null` no exemplo oficial | a chave natural do segurado é opcional; a carteira acumula sósias |
| **`PATCH /prod_docs` move dinheiro** | 📊 `codpro_novo`/`codage_novo` no corpo | uma troca errada de produtor é repasse pago à pessoa errada |
| 🔴🔴 **conta compartilhada** | 📊 CENSUS-v2 §3: Amandus e Resulta descriptografam para a **MESMA** conta CorpAPI | **uma escrita "da Amandus" cairia no InfoCap da Resulta.** Cross-tenant de ESCRITA — **CLAUDE.md §10 (4)** |

### 3.4 · O que a governança exigiria — **só citação, sem desenho**

Escrita na InfoCap é, por definição, ação sensível sobre sistema de terceiro com efeito
financeiro. O que já existe no canon e teria de ser aplicado:

```
SPEC-055  Work Run + Approval  — toda escrita é passo durável com decisão humana VINCULADA
                                 (não frase de prompt — CLAUDE.md §6)
SPEC-054  schema/segurança     — filtro de tenant no repository, não só RLS (CLAUDE.md §7)
SPEC-056  Skills/Tools         — a escrita é TOOL com capability PRÓPRIA, separada da
                                 capability de leitura que a 094 usa
SPEC-057  Artifact             — o comprovante do que foi escrito é entregável, não log
CLAUDE.md §5                   — o adapter da 094 é a única peça que fala InfoCap; a escrita
                                 entra NELE. Um "escritor InfoCap" ao lado = motor paralelo
CLAUDE.md §10 (1) e (4)        — perda de dado e cross-tenant são condição de PARADA
```

🔴 **A trava mínima que a evidência já justifica, antes de qualquer SPEC de escrita:**

```
1. NENHUMA escrita enquanto duas corretoras apontarem para a mesma conta CorpAPI (F-094-07)
2. NENHUM POST sem uma leitura de deduplicação antes (/cliente_cpf ou /busca_cpf) —
   é a única defesa possível contra a falta de idempotência
3. NENHUM DELETE por agente, em rota nenhuma, enquanto o escopo do delete não for MEDIDO
4. escrita = Approval por padrão, e o registro guarda o corpo enviado e a resposta CRUA
```

### 3.5 · A resposta em uma linha

> 📊 **A CorpAPI expõe 19 requisições de escrita de negócio em 8 recursos.** Um agente
> **pode** cadastrar cliente com endereço, e-mail e telefone num único POST; **pode** lançar
> uma lista de novos clientes; **pode** abrir oportunidade no funil; **pode** atribuir
> produtor; e **pode** importar apólice a partir do PDF pelo fluxo InCorp.
> 🔴 **Não pode** abrir atendimento nem tarefa — `/atendimentos` responde 200 na **leitura**
> e **não tem verbo de escrita em lugar nenhum**, nem no censo nem na doc.
> ⚠️ **Zero dessas 19 foi medida.** A doc não marca campo obrigatório, não documenta resposta
> de escrita, não tem idempotência e ensina um bug de CEP. **Isto é um BLOCO 0 de MEDIÇÃO em
> ambiente que possa sujar — não é um bloco de implementação.**

---

## 4. O QUE ESTA PESQUISA **NÃO** CONSEGUIU

| não obtido | por quê |
|---|---|
| valor de `{{base_url}}` | 📊 `collection.variable` é `null` no JSON publicado. (O produto usa `https://api.corpnuvem.com` — CENSUS-v2) |
| campos obrigatórios | a coleção não os marca. Só medição resolve |
| respostas das 19 escritas | 📊 **0** exemplos salvos |
| valores aceitos em `tipo_doc`, `periodo`, `tipo_data`, `tipo_sinistro`, `situacao`, `status`, `etapa`, `prioridade` | a doc mostra **um** valor de exemplo cada, sem enumerar |
| se existe sandbox InfoCap | nada na coleção. 💭 O `filial: "BASE DE DEMONSTRAÇÃO"` no exemplo do `/documento` sugere base de demonstração interna — **não confirmado** |
| versionamento da API | 📊 sem header de versão, sem `/v1`. `publishDate` de 14/03/2025 é a única data |
| se a doc mudou desde 14/03/2025 | o documenter não expõe histórico público de versões nesta coleção |
| qualquer comportamento real de escrita | ⛔ trava desta pesquisa: **não chamar a InfoCap** |

---

## 5. O QUE UMA PRÓXIMA MEDIÇÃO DEVE FAZER — 6 chamadas GET, nenhuma escrita

Barato, seguro, e destrava quatro coisas hoje bloqueadas:

```
1. GET /producao?texto=&dt_ini=01/01/2025&dt_fim=31/01/2025&ordem=inivig
                &orientacao=asc&so_renovados=t&so_emitidos=x
   -> o 500 era parâmetro? (§2.1) — conserta uma rota do código de PRODUÇÃO

2. GET /documentos?ordem=nosnum&qtd_pag=100&pag=1&periodo=datinc
                  &datini=01/08/2026&datfim=31/08/2026&codfil=1
   -> existe base temporal por CADASTRO? (§2.2) — candidata a COMMISSION_ACCRUAL_DATE

3. GET /documentos_bi?datini=01/01/2025&datfim=31/12/2025&data=INIVIG&tipo_doc=TODOS
   -> quanto do universo o recorte "A" do golden control esconde

4. GET /sinistros?tipo_sinistro=a&data_inicial=01/01/2026&data_final=31/08/2026
                 &tipo_data=oco&situacao=p&qtd_pag=10&pagina=1
   -> tira os 26,3 s do caminho e torna claims.status usável em chat

5. GET /produtores?texto=&codage=1   e   GET /agentes?texto=
   -> o cadastro de produtor, que hoje só se conhece pelo que aparece em prod_docs

6. GET /negocios_andamento?dtini=…&dtfim=…&qtd_pag=20&pag=1&status=all&calculo=t
   -> o funil existe e tem volume? é o insumo de "cotação que não virou apólice"
```

⚠️ **Nenhuma delas escreve.** As 19 escritas ficam para uma SPEC própria, depois da decisão
do Founder sobre a conexão compartilhada.

---

## 6. REFERÊNCIA EXTERNA (§7.3) — a fonte desta pesquisa

**URL** · `https://documenter.getpostman.com/view/33455116/2sAYkBrLmi`
(JSON: `https://documenter.gw.postman.com/api/collections/33455116/2sAYkBrLmi?segregateAuth=true&versionTag=latest`)

**O QUE FAZ** · coleção Postman pública "CorpAPI" da InfoCap, publicada em 14/03/2025:
12 pastas, 51 requisições — o contrato de **forma** (não de semântica) da API que serve as
três corretoras.

**MODELAMOS** · o **catálogo de superfície**: quais recursos existem, quais verbos cada um
aceita, e a forma exata dos corpos de escrita. É o que permite dizer *"um agente pode
cadastrar cliente"* sem chutar — e é o que o censo, por ser só GET, não podia dizer.

**REJEITAMOS** · tratá-la como especificação. 📊 1 descrição em 51 requests · 3 exemplos de
resposta · 0 campos obrigatórios · 0 respostas de escrita · um exemplo que ensina CEP como
número · um corpo com JSON inválido. ⛔ E rejeitamos usá-la como prova de **existência**:
3 rotas que respondem 200 não estão nela (§2.4).

**COMO O JUIZ INSPECIONA** · roda o `curl` do EXECUTION CARD; confere
`info.publishDate == "2025-03-14T13:47:07.000Z"`; conta 51 folhas com o script do §0; e roda:

```bash
grep -o "base_url}}/comissoes" corpapi.json | wc -l   # -> 0  (a rota não existe nem na doc)
grep -o "base_url}}/prod_docs" corpapi.json | wc -l   # -> 4  (GET + POST + PATCH + DELETE)
```

⚠️ **`grep -c` NÃO serve aqui e é armadilha:** o JSON tem **uma única linha**, e `-c` conta
**linhas**, não ocorrências — devolve `1` para as quatro. 📊 Erro cometido e corrigido na
redação deste documento; fica escrito para o próximo não repetir.

---

## 7. A LINHA QUE O CENSO DEVE RECEBER

> Sugestão para o topo do `INFOCAP-CORPAPI-CENSUS-v2.md` — **não aplicada aqui**: esta
> pesquisa é somente leitura sobre o repo.

```markdown
> ⚠️ **COMPLEMENTADO em 03/09/2026 por [`../../pesquisa/CORPAPI-CATALOGO-OFICIAL.md`](../../pesquisa/CORPAPI-CATALOGO-OFICIAL.md).**
> A coleção Postman oficial da InfoCap (51 requests, publicada em 14/03/2025) confirma que as
> 34 rotas 403-SigV4 **não estão documentadas** — segunda fonte independente para "não existem" —
> e revela **19 requisições de ESCRITA** que este censo não tocou (`/cliente`, `/endereco`,
> `/email`, `/telefone`, `/negocio`, `/prod_docs`, e o fluxo InCorp de importação de apólice
> por PDF). Ela também mostra que `/producao` (500 aqui), `/documentos` e `/sinistros` foram
> chamados com parâmetros DIFERENTES dos oficiais. A EXISTÊNCIA continua sendo deste censo;
> os PARÂMETROS passam a ser da doc.
```
