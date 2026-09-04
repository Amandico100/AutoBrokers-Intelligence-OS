# INFOCAP / CorpAPI — CENSO MEDIDO v2

> 🔴 **SUPERADO/ATUALIZADO em 03/09/2026 pelo BLOCO 0 da SPEC-094.1 — a seção `v2.1`, no fim
> deste arquivo, é a autoridade onde os dois divergirem.** Ela reclassifica cinco rotas
> (`/producao`, `/produtores` e as três do funil: o 500 era parâmetro faltando), mede a base
> de apropriação (`/documentos?periodo=datinc`), prova que **`cancelado=T` INCLUI os cancelados
> em vez de filtrá-los**, e registra a sondagem segura das 5 portas de escrita.
> A fonte externa está em [`../susep/SES-CENSO.md`](../susep/SES-CENSO.md).

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

---

# v2.1 — BLOCO 0 da SPEC-094.1 · remedição de 03/09/2026 (noite)

> 🔴 **SUPERADO/ATUALIZADO em 03/09/2026 pelo BLOCO 0 da SPEC-094.1.** As seções 1–11
> acima continuam valendo, com **cinco reclassificações**: o que este documento chamou
> de "500" ou "não medido" em `/producao`, `/produtores` e nas três rotas do funil era
> **parâmetro faltando**, não rota quebrada.
>
> MÉTODO: **18 GET** pela conexão `connected` da **Resulta**, credencial lida pelo
> caminho do produto · **5 POST de SONDAGEM com corpo vazio `{}`**, autorizados pelo
> Founder, para ler a VALIDAÇÃO. ⛔ **Nenhuma escrita real. Nenhum registro criado,
> alterado ou apagado. Nenhuma escrita no Supabase.** Nenhum dado de pessoa aqui.
> 📊 Scripts: `scratchpad/bloco0_0941/{b0_gets,b0_variantes,b0_v2,b0_datas,b0_sonda_escrita}.py`

## v2.1 §A — as chamadas que a SPEC-094.1 pediu

| rota | os parâmetros que a fizeram funcionar | classe | latência | n | fingerprint |
|---|---|---|---|---|---|
| `/producao` | `dt_ini` `dt_fim` `texto` `ordem=inivig` `orientacao` `so_renovados` `so_emitidos` | **200** | 0,81 s | **15** | `55701b22…` (19 chaves) |
| `/documentos` | `periodo=datinc` `datini` `datfim` `qtd_pag` `pag` `ordem` `orientacao` `codfil` | **200** | 1,98 s | **232** (30 d) | `da67a89c…` **= v2** |
| `/sinistros` | `data_inicial` `data_final` `tipo_data=oco` `qtd_pag` `pagina` | **200** | **1,10 s** | **42** (90 d) | `15565f90…` **= v2** |
| `/negocios_andamento` | os 9 da doc, **com `status`** | **200** | 0,73 s | **1** (2025) | `78e278b0…` (30 chaves) |
| `/em_calculo` | os 8 da doc, **com `status`** | **404 = vazio** | 0,84 s | 0 (30 d) | — |
| `/negocios_finalizados` | os 8 da doc, **com `status`** | **404 = vazio** | 0,93 s | 0 (30 d) | — |
| `/produtores` | `texto=` + **`codage` real** (vindo de `/agentes`) | **200** | 0,78 s | **119** | `800cfd4b…` (2 chaves) |
| `/agentes` | `texto=` | **200** | 0,65 s | **1** | `800cfd4b…` |
| `/documentos_bi` | 2025 · `data=INIVIG` · **`tipo_doc=TODOS`** | **200** | 6,93 s | **3.272** | `3437d553…` **= v2** |
| `/renovacoes` | 2025 · **`cancelado=T`** | **200** | 15,06 s | **3.861** | `1ac6b510…` **= v2** |

📊 **Quatro fingerprints reproduzem o censo v2 com OUTRO conjunto de parâmetros.** É a
linha de CONTROLE (CLAUDE.md §9.2): o schema não mudou — mudou a pergunta.

### A1 · 🔴 P-094-PRODUCAO-500 FECHADO — e a rota não serve para lote

`/producao` com `dt_ini`/`dt_fim` (e não `datini`/`datfim`) responde **200 em 0,81 s**.
A inferência do `CORPAPI-CATALOGO-OFICIAL.md` §2.1 estava certa.

⚠️ **E o segundo achado importa mais que o primeiro:** devolveu **15 linhas** nas duas
formas medidas (`so_renovados=t` e `=x`), com `inivig` entre 04/08 e 05/08, na **mesma
janela de 30 dias** em que `/documentos` devolveu **232**. A doc não expõe `qtd_pag` nem
`pag` para esta rota. 💭 **INFERÊNCIA:** página fixa de 15. **FATO:** 15 registros, duas
formas, mesma janela, contra 232 da rota irmã.

🔴 **Consequência:** `/producao` volta a servir como **SONDA** — que é exatamente o uso
de `infocap_connector.py:3115` e `:3126` — e **não** como fonte de população. Quem somar
prêmio de `/producao` soma 15 apólices e chama de mês.

### A2 · 🔴 `/documentos?periodo=datinc` é a base de apropriação — e ela não vem no corpo

📊 232 documentos em 30 dias, 1,98 s. **E nenhuma das 17 chaves devolvidas é `datinc`.**

```
inivig dentro da janela   154/232   (66%)
fimvig dentro da janela     4/232   ( 2%)
datemi dentro da janela   128/187
```

🔴 **Nem `inivig`, nem `fimvig`, nem `datemi` explicam o recorte** — o que prova, por
eliminação, que existe uma terceira data e que **ela é invisível**. Uma métrica pode
apropriar por `datinc` **delegando ao filtro**, mas não pode auditar linha a linha nem
recalcular sem repetir a chamada. E `/documentos` **não traz `val_c`**: a comissão
continua vindo de `/documentos_bi` (que filtra `inivig`) ou de `/documento` (uma apólice
por vez). **A base de apropriação existe como JANELA, não como CAMPO.**

### A3 · `/sinistros` filtrada é 24× mais rápida, e `tipo_data=oco` prende `datoco`

📊 42 sinistros em 90 dias em **1,10 s**, contra 26,34 s do acervo inteiro no v2.
`datoco` **42/42** dentro da janela, com o mínimo exatamente no primeiro dia dela — o
filtro é a data de **ocorrência**, provado. `datavi` 42/42; `datenc` 9/42 (só encerrados).
`datvis`, `datlib`, `placa`, `oficina`, `tipo_atendimento`, `agendamento` e
`proxima_agenda` vieram **100% nulos** na amostra. `valind`, `valdes`, `valavi` e
`franquia` vêm preenchidos.
⛔ `segurado` e `responsavel` são PII — não entram no pack nem no Artifact.

### A4 · 🔴 O funil EXISTE, responde, e está VAZIO — o 500 era `status` faltando

```
sem `status`   ->  HTTP 500 {"message": "Internal Server Error."}   nas TRÊS rotas
com `status`   ->  404 {"message": "Nenhum negócio encontrado."}    = VAZIO, não erro
2025 inteiro   ->  /negocios_andamento devolve UM negócio
```

📊 30 chaves medidas: `codigo · codfil · codcli · cliente · status · prioridade · tipo ·
tipo_neg · ramo · codram · ramo_multi · ramo_tipo · sit_multi · situacao_multi · codmulti ·
multi_corp_mais · val_premio · val_c · oportunidade · inivig · fimvig · produto_fimvig ·
descricao_item · doc_codfil · doc_nosnum · prox_aten_{codigo,data,hora,descricao,qtde_atrasadas}`.

🔴 **`motivo_perda` NÃO aparece no GET medido.** Ele existe só no corpo do `POST /negocio`
da doc. **`quotes.lost_reasons@1` não tem fonte provada de LEITURA.**

⚠️ **Para a SPEC-094.1:** `commercial.quotes` fica **PARTIAL por COBERTURA, não por
rota**. `quotes.funnel@1` pode ser definida; devolveria **UNAVAILABLE por acervo vazio —
nunca zero** (M2). A corretora não usa o CRM da InfoCap.

### A5 · `/produtores` exigia um `codage` real; `/agentes` é quem o entrega

📊 `codage` vazio → **500** em duas formas medidas. Com o código do único agente de
`/agentes` → **200 com 119 produtores** (`codigo` + `nome`; `nome` é PII).
⚠️ 119 é a **dimensão**; o censo v2 mediu **97 produtores com apólice em 2025**. Os 22 de
diferença são quem existe e não vendeu — legível só agora.

### A6 · `tipo_doc=TODOS` mostra um universo 1,95× maior que o golden control

📊 2025, `data=INIVIG`: **`tipo_doc=A` = 1.680** (golden control) · **`TODOS` = 3.272** —
**+1.592 documentos** (endosso, cancelamento, proposta), com as **mesmas 20 chaves**.
🔴 O golden control continua válido: ele **é** o recorte `A`. O que faltava era saber que
existe um universo quase duas vezes maior que nenhuma métrica conta hoje.

### A7 · 🔴🔴 `cancelado=T` NÃO é "só os cancelados" — é "inclua os cancelados"

📊 `/renovacoes` 2025 com `cancelado=T`: **3.861 linhas** = **3.536 com `cancelado='F'`**
(exatamente as do golden control) **+ 325 com `cancelado='T'`**.

```
taxa de cancelamento 2025 = 325 / 3.861 = 8,4%      📊 medido, Resulta
```

⛔ **É o CLAUDE.md §9.5 em estado puro:** quem ler `cancelado=T` como recorte publica
**a carteira inteira como cancelada**, e o número **responde** — não trava.
`portfolio.cancellation_rate@1` tem de filtrar pelo **CAMPO `cancelado` de cada linha**,
nunca pelo parâmetro. Capacidade `portfolio.cancellations`: **PARTIAL → SUPPORTED**.

## v2.1 §B — 🔴 SONDAGEM SEGURA das 5 portas de escrita (corpo vazio `{}`)

⛔ **Uma requisição por rota. Corpo `{}`. Nenhum dado de pessoa, real ou fictício.
As cinco RECUSARAM: nada foi criado.**

| rota | HTTP | resposta da API | o que a validação revela |
|---|---|---|---|
| `POST /cliente` | **400** | `{"message": "O nome é obrigatório."}` | valida — e **um campo por vez** |
| `POST /endereco` | **400** | `{"message": "Padrão é obrigatória."}` | 🔴 cobra `padrao` **antes** de `codcli` |
| `POST /email` | **400** | `{"message": "Padrão é obrigatória."}` | mesma mensagem de `/endereco` |
| `POST /negocio` | **500** | `{"message": "Internal Server Error."}` | 🔴 **não valida: estoura** |
| `POST /prod_docs` | **400** | `{"message": "Valor de código inválido."}` | valida a chave composta |

🔴 **Quatro das cinco validam. A quinta explode.** `POST /negocio` com corpo vazio devolve
o **mesmo 500** que as rotas GET do funil davam sem `status` — 💭 é a assinatura de uma
API que não trata entrada ausente. Uma rota que responde 500 a corpo inválido **não diz o
que falta**, e por isso os obrigatórios de `/negocio` continuam **desconhecidos**.

⚠️ **A validação é serial:** cada rodada revela **um** obrigatório. Descobrir a lista
inteira exigiria dezenas de requisições **com dados plausíveis** — exatamente o que a
trava proíbe. 📊 **O que se sabe hoje:** `/cliente` exige `nome`; `/endereco` e `/email`
exigem `padrao`; `/prod_docs` exige código válido.

### B1 · A resposta ao Founder: *"um agente pode cadastrar clientes em massa hoje?"*

> **Tecnicamente SIM — a porta abre e reage. Operacionalmente NÃO. E a sondagem mostra
> por quê melhor do que a documentação mostrava.**

```
✅ PROVADO   as 5 rotas existem, aceitam o token da corretora e três delas VALIDAM
✅ PROVADO   não há como criar nada por acidente: corpo vazio é recusado nas 5
❌ FALTA     a LISTA de obrigatórios — a API entrega um campo por rodada, e completá-la
             custaria dezenas de escritas com dado plausível: proibido pela trava
❌ FALTA     a RESPOSTA da escrita: nenhuma foi executada e a doc não traz exemplo.
             🔴 Sem ler o `codigo` do cliente criado NÃO SE PENDURA endereço, e-mail nem
             telefone nele — o cadastro em massa quebra no segundo passo
❌ FALTA     IDEMPOTÊNCIA: nenhuma chave, nenhum header. O produto já tem retry com
             backoff — um retry de rede vira o SEGUNDO cliente
❌ FALTA     CONSERTO: `/cliente` tem POST e DELETE e não tem PUT. Errou, só apagando
❌ FALTA     GOVERNO: nenhuma dessas rotas passa por Work Run, Approval ou Capability
🔴 BLOQUEIO  F-094-07: Amandus e Resulta descriptografam para a MESMA conta CorpAPI.
             Uma escrita "da Amandus" cairia no InfoCap da Resulta. Escrita cross-tenant
             é CLAUDE.md §10 (4) — condição de PARADA, não risco a mitigar
```

**RECOMENDAÇÃO:** a escrita continua **fora** da SPEC-094.1 (§5). O que mudou é que
deixou de ser hipótese: as cinco portas foram tocadas, recusaram corpo vazio, e o que
falta é **nomeável** — ambiente que possa sujar, contrato de resposta, idempotência no
adapter, Approval por Work Run, e a conta compartilhada resolvida. **Nesta ordem.**

## v2.1 §C — o que ficou de fora desta rodada

| não medido | por quê |
|---|---|
| paginação de `/sinistros` (`pagina=2`) | 42 registros couberam em uma página |
| `tipo_data` ≠ `oco` em `/sinistros` | uma chamada por valor; `oco` provado, os demais ficam UNKNOWN |
| `/producao` em janela maior | 💭 a página fixa de 15 tornaria o teste inconclusivo |
| a lista completa de obrigatórios das 5 escritas | exigiria dezenas de POST com dado plausível — trava |
| `POST /telefone` | o pacote autorizou 5 rotas; `/negocio` entrou no lugar dela |
| `motivo_perda` no GET do funil | 📊 não está nas 30 chaves — e o acervo tem 1 negócio |
| Amandus e AutoFleet | esta rodada foi só Resulta (F-094-07 continua aberto) |

## v2.1 §D — a fonte externa

📊 O SUSEP SES foi medido e documentado em
[`../susep/SES-CENSO.md`](../susep/SES-CENSO.md): 571.756.724 bytes, `Last-Modified`
31/08/2026, `sha256 7810ea33…`, competência final **202606**, 1.801.731 linhas de
prêmio e sinistro por seguradora × mês × ramo. **14 das 15 seguradoras do repositório
casam com um `coenti`; 12 têm auto ativo; `sulamerica` fica `UNKNOWN`.**
