# INFOCAP / CorpAPI — CENSO MEDIDO v2

> **Este documento SUPERA `docs/canon/INFOCAP-CORPAPI-MAPA.md` (42 linhas, 14/07/2026).**
> A linha exata que o MAPA deve receber no topo está na §9.
>
> BLOCO 0 da **SPEC-094** · medido em **03/09/2026** · base `https://api.corpnuvem.com`
> Credencial lida pelo caminho do produto: `tenant_connections` → `encrypted_secret_ref`
> → `get_encryption_service().decrypt`. **Nenhum valor de credencial aparece aqui.**

---

## EXECUTION CARD

```
OUTCOME ..............  o adapter da SPEC-094 sabe, por MEDIÇÃO, o que a InfoCap entrega
                        às três corretoras — e o que ela não entrega vira UNAVAILABLE
                        ou UNKNOWN, nunca zero
HEAD .................  0ae54624f44199ce25b95c00187fc211b6de7a6c
BRANCH ...............  feat/spec093b-o-sinistro-deixa-rastro
DATA .................  03/09/2026
MÉTODO ...............  SOMENTE GET (exceto /login, que é POST por contrato da API).
                        Uma chamada por rota por conjunto de parâmetros. Sem laço de força
                        bruta. Janela ≤ 30 dias nas listas; 1 ano só nos golden controls
CHAMADAS .............  Resulta 76 · Amandus 5 · AutoFleet 5  ·  TOTAL 86
ROTAS TOCADAS ........  51 (as 31 do contrato + /login + /cliente + /sinistros + 17 variantes)
CORRETORA POR PASSO ..  passo 1 (login/flags) → as 3
                        passos 2, 3, 4 (dimensões, parametrizadas, as 18) → Resulta
                        passo 5 (golden controls 2025) → as 3
DESCRIPTOGRAFOU ......  Resulta SIM · Amandus SIM · AutoFleet SIM
ESCRITAS .............  nenhuma na InfoCap · nenhuma no Supabase · nenhuma mensagem enviada
SAÍDA ................  este arquivo + 4 JSON nesta mesma pasta
```

---

## 1. 🔴 O ACHADO QUE MUDA A SPEC — as 18 rotas "negadas" NÃO EXISTEM

📊 Todas as 18 rotas que o MAPA antigo listava como *"🔒 NEGADO (403) — pedir liberação
à corretora"* devolvem **403 com a assinatura SigV4 do API Gateway da AWS**:

```
{"message":"Authorization header requires 'Credential' parameter.
 Authorization header requires 'Signature' parameter.
 Authorization header requires 'SignedHeaders' parameter.
 Authorization header requires existence of either a 'X-Amz-Date' or a 'Date' header."}
```

Esse texto é o que a AWS devolve para **um caminho que não está mapeado no Gateway** —
ele nem chega à aplicação para haver permissão a negar. É exatamente o que
`backend/app/comercial/fonte_infocap.py:56` e `:333-338` já dizia, e o MAPA contradizia.

E a prova do outro lado, que ninguém tinha feito: 📊 **o `/login` das três corretoras
devolve 17 flags de permissão e TODAS as 17 vêm `"T"`.** Não há uma única flag `F`.
Não há liberação nenhuma a pedir.

| flag | Resulta | Amandus | AutoFleet |
|---|---|---|---|
| p9 · p25 · p51 · p56 · p91 · p212 · p213 · p226 · p227 · p282 · p357 · p500 · p501 · p502 · p600 · p601 · p602 | **T** (17/17) | **T** (17/17) | **T** (17/17) |

> 📊 comando: `scratchpad/censo/p1_login.py` — as três respostas de `/login` têm as
> **mesmas 26 chaves** e o **mesmo conjunto de flags**.

**Consequência para a SPEC-094:** não existe caminho para financeiro em lote na InfoCap.
`financial.cashflow` é **UNAVAILABLE medido**, e não "pendente de liberação". Qualquer
roadmap que dependa de "a corretora libera o financeiro" está construído sobre um erro
de leitura de 14/07/2026.

---

## 2. 🔴 A SEGUNDA DESCOBERTA — `/sinistros` existe, e o MAPA testou o nome errado

📊 O MAPA listava `/sinistro` (**singular**) entre as negadas. `/sinistro` é 403-SigV4.
**`/sinistros` (plural) é classe 200 e devolveu 5.729 registros na Resulta em 26,3 s.**

```
GET /sinistros?codfil=1
{header, sinistros:[{ numsin, nosnum, numapo, numend, codfil, item, cia, ramo,
                      datoco, datavi, datenc, datlib, datvis, situacao, tipo,
                      tipo_atendimento, valind, valdes, valavi, franquia,
                      oficina, responsavel, segurado, placa, descricao,
                      observacoes, agendamento, proxima_agenda, codigo }]}
```

Isso tira `claims.status` de UNAVAILABLE e põe em **SUPPORTED**. É a capability mais
valiosa que o censo destravou, e ela custou uma letra.

📊 Uma varredura dirigida das outras 17 no número oposto (singular ↔ plural, uma chamada
cada) achou mais uma: **`/usuario` devolve `400 {"message": "Unknown field."}`** — a rota
existe e recusa o parâmetro `codfil`. `/usuarios` (plural) é 403-SigV4. As outras 15
variantes são todas 403-SigV4.

---

## 3. 🔴 O ACHADO QUE PARA O BLOCO G — Amandus e Resulta são a MESMA conexão CorpAPI

📊 As três conexões `status='connected'` descriptografam. Mas:

```
                    user_sha         pass_sha         perfil CorpAPI   documentos_bi 2025
AMANDUS SEGUROS     dab3d640…        622b9722…        codigo 75        1.680 · R$ 1.863.830,79
Resulta Seguros     dab3d640…        622b9722…        codigo 75        1.680 · R$ 1.863.830,79
AutoFleet           2926f6c8…        5d9c346e…        codigo 73        3.117 · R$ 2.099.510,43
```

**Mesmo usuário, mesma senha, mesmo perfil, carteira idêntica até o centavo.** Os
ciphertexts são diferentes (Fernet usa IV aleatório), então a tabela não denuncia isso
por comparação de coluna — só a descriptografia denuncia.

⛔ **O canário do BLOCO G, como está escrito, mostraria a carteira da RESULTA e a
chamaria de AMANDUS.** Não é defeito de código: é a linha de `tenant_connections` da
Amandus apontando para a conta InfoCap da Resulta. Um número executivo do dono da
Amandus sairia com o faturamento de outra corretora.

**FATO** medido. **RECOMENDAÇÃO:** o canário das três só vale depois que a conexão da
Amandus tiver credencial própria — ou depois que ficar registrado que ela ainda não tem
conta CorpAPI. Isto é condição de parada do CLAUDE.md §10 (4) e cabe ao Founder.

---

## 4. A TABELA DAS ROTAS — 51 medidas

Classe: `200` · `400` (existe, recusa o parâmetro) · `404` (**vazio, não erro**) ·
`500` · `403-SigV4` (**a rota não existe no Gateway**) · `timeout`.

### 4.1 As que respondem — 15 rotas classe 200 (14 GET + o `POST /login`)

| rota | params medidos | classe | latência | envelope | n |
|---|---|---|---|---|---|
| `POST /login` | email, senha, aplicacao | 200 | 1,0 s | objeto na raiz, 26 chaves | 1 |
| `/seguradoras` | — | 200 | 0,68 s | `{header, seguradoras}` | 61 |
| `/ramos` | — | 200 | 0,65 s | `{header, ramos}` | 50 |
| `/lista_clientes` | `texto=` | 200 | 0,88 s | `{header, clientes}` | 19 |
| `/cliente` | `codigo=&codfil=` | 200 | 0,71 s | `{header, cliente}` | 1 |
| `/cliente_cpf` | `cpf_cnpj=&codfil=` | 200 | 0,67 s | `{header, cliente}` | 1 |
| `/cliente_ligacoes` | `codigo=` | 200 | 0,87 s | **aninhado** `documentos.documentos` | 1 |
| `/documento` | `nosnum=&codfil=` | 200 | 0,83 s | `{header, documento, historico, acompanhamento}` | 1 |
| `/documentos` | `texto=<numapo>` | 200 | 1,13 s | `{header, documentos}` | 1 |
| `/itens` | `nosnum=&codfil=` | 200 | 0,73 s | `{header, itens}` | 1 |
| `/cotacoes` | `codfil=1` | 200 | 0,76 s | `{header, cotacoes}` | 7 |
| `/atendimentos` | `codfil=1` | 200 | 0,90 s | `{header, **tarefas**}` | 15 |
| `/sinistros` | `codfil=1` | 200 | 26,34 s | `{header, sinistros}` | 5.729 |
| `/documentos_bi` | ver §5 | 200 | 3,3–7,5 s | `{header, documentos}` | 1.680 |
| `/renovacoes` | ver §5 | 200 | 7,0–15,3 s | `{header, renovacoes}` | 3.536 |

⚠️ `/atendimentos` devolve a lista na chave **`tarefas`**, não `atendimentos`. Quem
procurar pelo nome da rota lê zero linhas com a API respondendo certo.

### 4.2 As que existem e recusam (2)

| rota | classe | mensagem da API |
|---|---|---|
| `/usuario` | 400 | `{"message": "Unknown field."}` — existe, `codfil` não serve |
| `/producao` | 500 | `Internal Server Error` em 3 conjuntos de parâmetros: `{datini,datfim}`, `{texto}`, `{codfil,texto}` |

🔴 `/producao` é uma das 5 rotas que o código de produção usa
(`infocap_connector.py:3115` e `:3126`, como sonda de CPF/nome). **Nas 3 formas medidas
hoje ela devolve 500.** Não foi possível achar um conjunto de parâmetros que funcione
dentro do orçamento de chamadas do censo.

### 4.3 As que NÃO EXISTEM — 403-SigV4 (34 rotas: as 18 do MAPA + 16 variantes)

**As 18 do MAPA:** `/parcelas` · `/comissao` · `/comissoes` · `/financeiro` · `/titulos`
· `/contas_receber` · `/contas_pagar` · `/fluxo_caixa` · `/faturamento` · `/vendedores` ·
`/usuarios` · `/propostas` · `/sinistro` · `/endossos` · `/tarefas` · `/agenda` · `/cias`
· `/filiais`.

**As 16 variantes de nome que também não existem:** `/parcela` · `/comissoes_doc` ·
`/comissao_doc` · `/financeiros` · `/titulo` · `/conta_receber` · `/conta_pagar` ·
`/fluxocaixa` · `/faturamentos` · `/vendedor` · `/proposta` · `/endosso` · `/tarefa` ·
`/agendas` · `/cia` · `/filial`.

📊 comando: `scratchpad/censo/p4_as18.py` e `p9_variantes.py`. Latência de todas entre
0,43 s e 1,74 s — o Gateway recusa antes de tocar a aplicação, e é por isso que é barato
descobrir.

---

## 5. GOLDEN CONTROLS — 2025 fechado, nas três corretoras

```
/documentos_bi?datini=01/01/2025&datfim=31/12/2025&data=INIVIG&tipo_doc=A
/renovacoes?dt_ini=01/01/2025&dt_fim=31/12/2025&qtd_pag=5000&pag=1&ordem=nosnum
           &orientacao=asc&texto=&cancelado=F&resgates=F
```
📊 comando: `scratchpad/censo/p7_final.py`

| | **Resulta** | **Amandus** ⚠️ | **AutoFleet** |
|---|---|---|---|
| apólices (tipo A) | 1.680 | 1.680 *(idêntico — §3)* | 3.117 |
| soma `pretot` | R$ 11.910.456,05 | R$ 11.910.456,05 | R$ 13.199.057,52 |
| soma `val_c` | **R$ 1.863.830,79** | R$ 1.863.830,79 | R$ 2.099.510,43 |
| soma `base_c` | R$ 11.278.819,26 | idem | R$ 12.273.965,65 |
| `val_c` nulo | 0 | 0 | 0 |
| `val_c` = 0 | 93 | 93 | 24 |
| `nosnum_ren` preenchido | 963 (57,3%) | 963 | 1.999 (64,1%) |
| seguradoras distintas | 36 | 36 | 22 |
| ramos distintos | 33 | 33 | 12 |
| renovações (fimvig 2025) | 3.536 | 3.536 | 2.654 |
| produtores distintos (ordem=1) | **97** | 97 | **64** |
| % com produtor ordem=1 | 97,1% | 97,1% | 99,1% |
| soma `val_r` (ordem=1) | R$ 440.064,21 | idem | R$ 415.336,94 |
| interseção BI∩renov por `nosnum` | 100 | 100 | **0** |
| latência `/documentos_bi` | 3,58 s | 3,31 s | 4,22 s |
| latência `/renovacoes` | 15,27 s | 8,87 s | 6,98 s |

📊 **O número da SPEC-081 reproduz exatamente:** 1.680 apólices e R$ 1.863.830,79 de
comissão em 2025. O golden control está fechado.

🔴 **A interseção da AutoFleet é ZERO.** Nenhum dos 3.117 `nosnum` da produção de 2025
aparece nas 2.654 renovações de 2025. Na Resulta são 100. Isso significa que a receita de
cobertura de produtor da 081 (varrer `fimvig` de N-1 a N+2) **precisa ser remedida por
corretora** — não é uma constante do provider.

### 5.1 A base temporal, medida com dois filtros

| rota | filtro | o que fica DENTRO da janela | o que fica fora |
|---|---|---|---|
| `/documentos_bi` | `data=INIVIG`, 2025 | `inivig` 1.680/1.680 | `fimvig` 106/1.680 |
| `/renovacoes` | `dt_ini/dt_fim`, 2025 | `fimvig` 3.536/3.536 | `inivig` 100/3.536 |
| `/renovacoes` | `dt_ini/dt_fim`, **2024** | `fimvig` 3.258/3.258 | `inivig` 118/3.258 |

📊 **`data=` aceita exatamente `('INIVIG', 'DATINC', 'DATALT', 'DATPROP')`** — a API
devolve essa lista num `400` quando recebe `DATEMI`. O `fonte_infocap.py:426` dizia que
ela devolve a lista; agora a lista está escrita.

🔴 **É esta tabela que impede o `INIVIG × FIMVIG` de voltar.** As duas rotas medem coisas
diferentes, e a interseção de 2025 com 2025 é de **100 apólices** — 6,0% da produção,
2,8% das renovações. *(O `2,8%` do docstring de `fonte_infocap.py:41` e o `6,0%` são o
mesmo 100, com denominadores diferentes. Os dois estão certos; o docstring não diz qual é
o dele.)*

### 5.2 Limite de janela e latência × a SPEC-081

| medição | a 081 diz (18/08) | medido hoje (03/09) |
|---|---|---|
| `/renovacoes` 90 dias (o "Radar") | 8 s | **2,28 s** (296 registros) |
| `/documentos_bi` 1 ano | ~4 s | **3,31–7,47 s** |
| `/renovacoes` 1 ano | ~8 s | **6,98–15,27 s** |
| `/documentos_bi` 30 dias | — | **1,33 s** (137 registros) |
| Raio-X anual frio (6 chamadas) | 53 s | ⚠️ **não remedi o caminho inteiro** — a soma das partes medidas dá ≈ 45–60 s, o que é compatível |

📊 A janela de 1 ano nunca falhou nas 8 chamadas de ano fechado desta rodada. Nenhum 502
foi observado — mas nenhuma janela plurianual foi tentada, porque a trava do censo a
proíbe. O teto de `JANELA_MAXIMA_DIAS=366` continua sem contraprova.

---

## 6. F-094-02 — o que `val_r` e `per_r` significam. **PROVADO.**

**A pergunta da SPEC:** o que são `val_r` e `per_r` dentro de `/renovacoes.prod_docs`?

**A resposta, com evidência direta e aritmética:**

```
val_r  =  val_c × per_r / 100
```

onde `val_c` é **a comissão da CORRETORA** — que **não existe em `/renovacoes`** (📊 a
chave nem aparece: `val_c` nulo/ausente em 3.536/3.536 registros) e só vem de
`/documentos_bi` ou `/documento`.

📊 **Conferido em escala:** dos 100 `nosnum` presentes nas duas rotas em 2025, todas as
**198 linhas de `prod_docs`** batem com a fórmula. **198/198 · 0 falhas · maior desvio
R$ 0,01.** O mesmo teste na Amandus (mesma conta) dá o mesmo. Na AutoFleet a interseção é
zero, então lá **não foi possível confirmar** (comando: `p7_final.py`, bloco
`f094_02_val_r_sobre_val_c`).

📊 **Três amostras à mão, para leitura humana:**

| `val_c` do documento | `per_r` | `val_r` | conferência |
|---|---|---|---|
| 7.890,37 | 4,0 % | 315,61 | 7890,37 × 0,04 = 315,61 ✓ |
| 217,87 | 3,0 % | 6,54 | 217,87 × 0,03 = 6,536 ✓ |
| 625,00 | 15,0 % | 93,75 | 625,00 × 0,15 = 93,75 ✓ |

**O que isso quer dizer para o modelo canônico:**

1. `val_r` é **repasse APROPRIADO ao produtor**, derivado da comissão apropriada da
   corretora. Não é comissão de venda sobre o prêmio, e **não é repasse pago**.
2. `contribution.after_repasse` = `val_c − Σ val_r` é uma métrica **derivada**, e as duas
   pontas têm de vir da **mesma** apólice — o join por `nosnum` não é otimização, é
   condição de correção. Sem `/documentos_bi`, `val_r` é um número sem base auditável.
3. 🔴 **`ordem == 1` não é "o maior".** 📊 Numa das amostras, `ordem=1` tinha `per_r` 4%
   e `ordem=2` tinha 15%. A 081 usa `ordem==1` como "produtor direto"; isso continua
   correto para *quem vendeu*, mas **somar só o `val_r` de `ordem=1` subestima o repasse
   total**. 📊 Média medida: 2,0 produtores por apólice.
4. 🔴 **`quant_produtores` mente**: bate com `len(prod_docs)` em 1.204 de 3.536 (34,1%).

**O que NÃO foi provado:** `val_ra`, `val_rc`, `val_rp`, `per_rc`, `per_rp`,
`taxa_repasse`, `cod_com_ind` e `datrep_prot` existem em `/documento.prod_docs` e vieram
**None ou 0.0 nas 3 amostras**. 💭 **Significado NÃO provado; só plausibilidade de razão.**
E `indireto` / `base_r` / `nome_produtor`, que a SPEC-081 original exigia, **não existem**
em `/renovacoes.prod_docs` (8 chaves) — `base_r` existe só na versão de 28 chaves de
`/documento`, e lá veio zerada.

🔴 **Achado colateral:** `/documento.prod_docs` tem **28 chaves** contra as 8 de
`/renovacoes.prod_docs`, mas 📊 nas 3 amostras **todos** os campos monetários vieram
`0.0`/`None` — enquanto o **mesmo `nosnum`** em `/renovacoes` trazia `per_r` e `val_r`
com valor. A rota rica expõe o **formato** do repasse; a rota pobre expõe o **valor**.
Quem escolher `/documento` por ter mais campos vai ler zero e não vai saber.

---

## 7. AS CAPACIDADES — 19 medidas

📊 arquivo: `infocap-capability-manifest.json`

```
SUPPORTED     9   portfolio.policies · portfolio.production · portfolio.policy_status
                  portfolio.renewals · commercial.producer_assignments
                  financial.commission_accrued · financial.producer_repasse_accrued
                  claims.status · contacts.customer
PARTIAL       6   portfolio.cancellations · commercial.producers · commercial.quotes
                  financial.commission_received · financial.receivables · crm.interactions
UNKNOWN       3   financial.commission_reversals · financial.commission_tax
                  financial.producer_repasse_paid
UNAVAILABLE   1   financial.cashflow
```

🔴 **UNKNOWN não é UNAVAILABLE.** As três UNKNOWN não foram medidas — não conclua
ausência a partir delas. O único UNAVAILABLE é o que teve rota **e** campo procurados e
não achados.

---

## 8. O QUE O MAPA ANTIGO ERROU

| # | o MAPA dizia | 📊 medido em 03/09/2026 |
|---|---|---|
| 1 | 18 rotas dão *"403 = pedir liberação à corretora"* | **as 18 não existem.** 403-SigV4 do API Gateway, e as 17 flags de permissão do perfil vêm todas `T` nas 3 corretoras |
| 2 | *"As permissões são flags do perfil (p500/p501…=T). A corretora libera no cadastro"* | as flags existem e **estão todas ligadas**. Não há o que liberar. A frase é verdadeira e a conclusão dela é falsa |
| 3 | `/sinistro` está entre as negadas | `/sinistro` não existe; **`/sinistros` responde 200 com 5.729 registros** |
| 4 | `/usuarios` está entre as negadas | `/usuarios` não existe; **`/usuario` existe** (400 `Unknown field.`) |
| 5 | *"`/atendimentos` — 2.355 registros na Resulta"* | 📊 **não reproduzido.** 15 registros com `codfil=1` e 15 com janela de 30 dias. Nenhum conjunto de parâmetros medido passou de 15 |
| 6 | lista 10 rotas acessíveis | são **13** — faltavam `/cliente`, `/sinistros`, `/documentos_bi` e `/renovacoes`; `/documentos_bi` e `/renovacoes` são as duas que o código de produção mais usa e **não estão no MAPA** |
| 7 | `/documento` — *"detalhe FINANCEIRO"* | verdade, e insuficiente: ele traz `parcelas[]` com `datquit`/`vlquit`/`vlbasecomquit`, que é **a única evidência medida de comissão recebida** em toda a API |
| 8 | não menciona `/renovacoes`, `val_r`, `per_r`, `prod_docs` | são o coração do repasse ao produtor — §6 |
| 9 | não menciona base temporal | `/documentos_bi` filtra `inivig`; `/renovacoes` filtra `fimvig`; a interseção 2025×2025 é de 100 apólices |
| 10 | *"Ingerir no RAG global"* | 🔴 **não.** O documento contém a conclusão errada do item 1, e essa conclusão já está injetada no conhecimento dos agentes (`fonte_infocap.py:60-62` registra o dano) |

---

## 9. A LINHA QUE `INFOCAP-CORPAPI-MAPA.md` DEVE RECEBER NO TOPO

> **Não edite o MAPA a partir deste censo sem o builder da SPEC-094.** A linha exata é:

```markdown
> 🔴 **SUPERADO em 03/09/2026 por [`providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md`](providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md).**
> As 18 rotas que este documento marca como "403 = pedir liberação à corretora" **não existem**
> (403-SigV4 do API Gateway), e as 17 flags de permissão do perfil vêm todas `T` nas três
> corretoras — não há liberação a pedir. `/sinistros` (plural) responde 200. Este arquivo fica
> como registro histórico; a autoridade é o censo v2 e os 4 JSON ao lado dele.
```

---

## 10. O QUE NÃO FOI MEDIDO — e por quê

| não medido | por quê |
|---|---|
| paginação real de `/renovacoes` (`pag=2`) | exigiria uma segunda chamada com o mesmo conjunto lógico de parâmetros; `qtd_pag=5000` cobriu os 3.536 numa página |
| janela plurianual (o 502 da 081) | a trava do censo proíbe janela > 1 ano |
| `/producao` funcionando | 3 conjuntos de parâmetros, 3× HTTP 500. Sem documentação da API para tentar um quarto |
| `/atendimentos` com mais de 15 registros | 2 conjuntos de parâmetros medidos; a rota não aceita `dt_ini/dt_fim` (devolve os mesmos 15) |
| `cancelado=T` em `/renovacoes` | conjunto de parâmetros novo, fora do orçamento; é o que falta para `portfolio.cancellations` sair de PARTIAL |
| estorno e imposto de comissão | nenhuma rota candidata sobreviveu ao Gateway; ficam **UNKNOWN**, não UNAVAILABLE |
| `/documento.prod_docs` com valor | as 3 amostras vieram zeradas. Não sei se é sempre assim |
| campos das rotas 403-SigV4 | não há corpo para analisar |
| o live test da 081 pela conexão | 🔴 **não rodado**: a suíte pytest do backend estava em execução e o censo não pode escrever em `backend/`. Fica como gate pendente do BLOCO 0 |

---

## 11. OS ARQUIVOS

| arquivo | o que é |
|---|---|
| `INFOCAP-CORPAPI-CENSUS-v2.md` | este documento |
| `infocap-capability-manifest.json` | 19 capabilities × estado × cobertura × rotas × evidência |
| `infocap-field-dictionary.json` | 14 rotas + 3 objetos aninhados, campo a campo |
| `infocap-golden-controls.json` | os números de 2025 das 3 corretoras, com o comando |
| `infocap-schema-fingerprints.json` | sha256 das chaves ordenadas, por rota |

**Nenhum destes arquivos contém CPF, nome de pessoa, apólice, placa, telefone, e-mail,
endereço, token, senha ou login.** Toda amostra é redigida: dígitos → `#`, letras → `x`.
Valores monetários, percentuais e contagens ficam crus — não identificam ninguém.
