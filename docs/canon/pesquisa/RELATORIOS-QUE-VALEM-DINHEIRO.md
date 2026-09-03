# OS RELATÓRIOS E CRUZAMENTOS QUE COLOCAM DINHEIRO NO BOLSO DA CORRETORA

> **Frente aberta pelo Founder em 03/09/2026.** Papel: PESQUISADOR EXTERNO (protocolo AAA
> v11.2 §7.3). **Somente leitura no repo.** ⛔ Nenhuma chamada à InfoCap. Nenhuma credencial.
> Nenhum dado de pessoa. Só leitura pública na web.
>
> Companheiro deste documento: [`CORPAPI-CATALOGO-OFICIAL.md`](CORPAPI-CATALOGO-OFICIAL.md)
> (a superfície da API). Este aqui responde à outra metade: **o que vale a pena calcular.**

---

## EXECUTION CARD

```
OUTCOME ..............  o Founder sabe, com fonte e URL, QUAIS relatórios toda corretora
                        exige, QUAIS cruzamentos ninguém no mercado faz, QUAIS fontes
                        externas existem de verdade — e o que o estado da arte diz sobre
                        deixar o chat inventar um cálculo novo
MÉTODO ...............  4 frentes de pesquisa web em paralelo + 11 verificações que EU
                        rodei com curl, para não repassar número de terceiro sem controle
NÃO MEDIDO ...........  nada no InfoCap. Nenhum portal de seguradora foi acessado
BASE INTERNA .........  INFOCAP-CORPAPI-CENSUS-v2.md (03/09) · SPEC-094 §0 e §1.11 ·
                        PORTAIS-E-CORREDORES.md · GLOSSARIO.md
DATA .................  03/09/2026
```

### 🔴 O achado que não estava na pergunta, e muda o tabuleiro

📊 **A InfoCap foi absorvida pela Agger, e a Agger se fundiu com a Quiver.**

```bash
curl -sSI "https://www.infocap.com.br/"
# HTTP/1.1 301 Moved Permanently
# Location: https://www.agger.com.br
# medido em 03/09/2026 16:33 UTC
```

📊 E a Agger publica o produto conjunto: `https://www.agger.com.br/produtos/one/` (HTTP 200),
descrito na própria página como *"a primeira solução de seguros nascida da união entre
Quiver e Agger"*.

🔴 **Consequência direta:** o fornecedor da API de que o produto depende e os dois maiores
concorrentes de gestão do mercado são **a mesma casa**. Isso não muda nenhuma medição deste
documento, mas muda o cálculo de dependência: `INFOCAP-CORPAPI-CENSUS-v2.md` e
`CORPAPI-CATALOGO-OFICIAL.md` descrevem a superfície de um fornecedor que agora é
concorrente. **Registrar em `FOUNDER-DECISIONS.md` é decisão do Founder, não minha.**

---

# A. A LISTA OBRIGATÓRIA — o que toda corretora exige ver

**Como esta lista foi construída, e por que ela é confiável:** não é opinião. 📊 Ela cruza
**três catálogos verbatim** de concorrentes, obtidos de fonte pública própria de cada um:

| fonte | como foi obtida | URL |
|---|---|---|
| **Quiver PRO** | árvore de ajuda RoboHelp, com o índice em arquivos JS | `http://helponline.quiverpro.net.br/whxdata/toc.js` ⚠️ certificado TLS vencido, só HTTP |
| **Agger** | manual público de **208 páginas**, sem autenticação | `https://aggerinstala.blob.core.windows.net/novogestor/MANUAL.pdf` (14 MB) |
| **Segfy** | central de ajuda, seção Relatórios, 49 artigos | `https://ajuda.segfy.com/knowledge/relatórios` |

📊 **Onze relatórios aparecem nos TRÊS, com nomes quase idênticos.** É a mesa posta: quem
não tem, está visivelmente incompleto.

Colunas: **InfoCap hoje** = o que o censo mediu · **grão/base temporal** = o recorte correto ·
**SPEC-094** = já entregue (`✅`), parcial (`◐`) ou fora (`—`).

| # | relatório | a pergunta que responde | fatos canônicos | InfoCap hoje (rota) | grão · base temporal | Quiver / Agger / Segfy | SPEC-094 |
|---|---|---|---|---|---|---|---|
| **A1** | **Produção** | *quanto vendemos e de quê?* | apólice · prêmio · seguradora · ramo · data | ✅ `/documentos_bi` (`data=INIVIG`) | apólice · **POLICY_VALID_FROM** | `Análise de produção` / `RELATÓRIO DE PRODUÇÃO` / `Relatório de produção` (14 variantes) | ✅ `production.policy_count@1` · `production.premium_written@1` |
| **A2** | **Comissão apropriada** | *quanto ganhamos no papel?* | comissão da corretora (`val_c`, `per_c`, `base_c`) | ✅ `/documentos_bi` · `/documento` | apólice · POLICY_VALID_FROM | `Saldos de comissões` / — / `Comissões da Corretora` | ✅ `commission.broker_accrued@1` |
| **A3** | 🔴 **Comissão RECEBIDA × apropriada** | *a seguradora nos pagou o que devia?* | parcela · `datquit` · `vlquit` · `vlbasecomquit` | ⚠️ **só `/documento.parcelas[]`, uma apólice por vez** — 📊 ≈23 min para 1.680 apólices (§2.3 do catálogo) | parcela · **data de quitação** | `Comissões pendentes/recebidas`, `Ocorrências das baixas` / `RELATÓRIO DE COMISSÃO RECEBIDA` / `Recebimento de Comissão` | — **UNKNOWN** na 094 |
| **A4** | **Repasse ao produtor** | *quanto devemos a quem vendeu?* | `prod_docs` · `val_r` · `per_r` · `ordem` | ✅ `/renovacoes.prod_docs` — 📊 `val_r = val_c × per_r/100`, 198/198 | apólice × produtor · **POLICY_VALID_TO** | `Repasses pendentes/liberados/pagos`, `Resumo de impostos retidos` / `RELATÓRIO DE PAGAMENTO DE VENDEDOR` / `Pagamento de Comissão` | ✅ `repasse.producer_accrued@1` |
| **A5** | **Contribuição líquida** | *o que sobra depois do repasse?* | A2 − A4, mesma apólice | ◐ só na interseção BI∩renov — 📊 **100 na Resulta, ZERO na AutoFleet** | apólice · interseção | `Demonstração de resultados`, `Resultado de apólices` / — / `Análise Financeira` | ✅ `contribution.after_repasse@1` (DERIVED) |
| **A6** | **Renovações a 30/60/90** | *o que vence e vamos perder?* | `fimvig` · `dias_a_vencer` · `renovacao_situacao` | ✅ `/renovacoes` — 📊 **2,28 s** para 90 dias | apólice · **POLICY_VALID_TO** | `Apólices a renovar / renovadas / não renovadas`, `Dashboard de renovações` / `RELATÓRIO DE RENOVAÇÕES` / `Relatório de renovação` | ✅ `renewal.exposure@1` |
| **A7** | **Mix por seguradora e ramo** | *dependemos demais de quem?* | seguradora · ramo · prêmio · comissão | ✅ 📊 36 seguradoras · 33 ramos (Resulta) | apólice · POLICY_VALID_FROM | `Demonstração de resultados por Seguradora/Ramo` / `PAINEL B.I.` / `Mix de Carteira` | ✅ `mix.insurer@1` · `mix.branch@1` |
| **A8** | **Ranking e momentum de produtor** | *quem cresce, quem murcha?* | produtor · prêmio · comissão · período | ◐ 📊 97 produtores (Resulta), 64 (AutoFleet); **cobertura remedida por corretora** | produtor · período móvel 30/60/90 | `Metas de produção` / `RELATÓRIO DE METAS` / produção `agrupado por produtor` | ✅ `producer.performance@1` · `producer.momentum@1` |
| **A9** | 🔴 **Inadimplência / parcelas** | *quem não pagou, e o que vou perder?* | parcela · `datvenc` · `datquit` · `vlvenc` | ⚠️ **só `/documento.parcelas[]`** — não há rota em lote | parcela · vencimento | `Prêmios pagos / não pagos` / `RELATÓRIO DE VENCIMENTO DE PARCELA` / `parcelas não recebidas` | — |
| **A10** | **Cancelamentos** | *quanto de carteira evaporou?* | `cancelado` · `sit_renovacao` | ◐ PARTIAL — 📊 `cancelado=T` **não medido** (CENSUS §10) | apólice · período | `Índices de Cancelamento` (Quiver BI) / — / `desconsiderar canceladas` | ◐ |
| **A11** | **Ticket médio** | *estamos vendendo maior ou menor?* | prêmio ÷ apólices | ✅ derivado de A1 | apólice · período | `Ticket Médio` (Quiver BI) / `PAINEL B.I.` / — | ✅ derivado |
| **A12** | **Carteira por cliente / mix cruzado** | *quem tem 1 produto e podia ter 3?* | cliente · apólices · ramos | ✅ `/cliente_ligacoes` (documentos por cliente) | cliente · foto atual | `Aproveitamento de carteira` / `RELATÓRIO DE CLIENTE` / 🔴 **`Mix de Carteira`, vendido como cross-sell** | — |
| **A13** | **Aniversário de apólice / de cliente** | *quando ligar?* | `inivig` · `datanas` | ✅ `inivig` em `/documentos_bi`; `datanas` em `/cliente` | data | `Aniversariantes` (dashboard) / `RELATÓRIO DE ANIVERSARIANTE` / — | — |
| **A14** | **Pendência de emissão** | *o que vendemos e não saiu?* | `sit_acompanhamento` · `numapo` vazio | ✅ 📊 `/documento.sit_acompanhamento_txt` — ex. *"Pendente de emissão - em atraso"* | apólice · dias em atraso | `Estrutura de produção incompleta` / `RELATÓRIO DE APÓLICES PENDENTES` / `Pendência de Emissão` | — |
| **A15** | **Sinistros da carteira** | *quem está sinistrando, e quanto?* | sinistro · `situacao` · `valind` · `datoco` | ✅ `/sinistros` — 📊 **5.729 na Resulta**, com 7 params na doc | sinistro · **`tipo_data` escolhível** | `Sinistros avisados/pendentes/pagos/liquidados` (12 relatórios) / `RELATÓRIO DE SINISTRO` / `Controle de Sinistros` | — (censo destravou) |
| **A16** | **Funil / orçamentos** | *quanto cotamos e quanto virou?* | negócio · etapa · `motivo_perda` · prêmio esperado | 🔴 `/negocios_andamento` · `/em_calculo` · `/negocios_finalizados` — **existem na doc, NUNCA medidos** | oportunidade · etapa | `Análise de orçamentos`, `Orçamento por situação` / `Funil de vendas` / `Orçamentos` | — |

### 🔴 As duas conclusões que a tabela A entrega

**1. A SPEC-094 já cobre 8 dos 16 — e os 8 que faltam concentram TODO o dinheiro que sai.**
📊 A 094 entrega A1, A2, A4, A5, A6, A7, A8, A11. Não entrega A3 (comissão recebida),
A9 (inadimplência), A12 (cross-sell), A13 (aniversário), A14 (pendência de emissão),
A15 (sinistro), A16 (funil), e A10 fica parcial.

**2. 🔴 Os dois relatórios que os TRÊS concorrentes têm e a CorpAPI não entrega em lote são
exatamente os dois do dinheiro: A3 e A9.** Quiver tem cinco relatórios só de comissão e
`Ocorrências das baixas`; Agger tem `RELATÓRIO DE COMISSÃO RECEBIDA` e
`PREVISÃO DE PAGAMENTO DE COMISSÃO`; Segfy tem uma família inteira de `Recebimento de
Comissão` com `Grades de Recebimento e Parcelas`.
**Eles têm porque leem o banco por dentro. Nós lemos por API — e a API não expõe.**

⚠️ **E há uma saída que já existe no repo, e não é a API.** 📊 `PORTAIS-E-CORREDORES.md`
registra a tabela `portals` com **17 registros ativos, 15 deles portais de corretor** com
login e senha da corretora (Allianz, Alfa, Azul, Bradesco, HDI, Mapfre, Porto, SulAmérica,
Sompo, SURA, Suhai, Seguros Unimed, Tokio Marine, Yelum, Zurich), e o `portal_worker` que
entra neles para *"boleto, apólice, **comissão**"*.
🔴 **O extrato de comissão da seguradora é a fonte que fecha A3 e A9 — e ela não passa pela
InfoCap.** Isso é FATO sobre o que existe no repo; **INFERÊNCIA** minha é que essa é a
melhor rota; não medi nenhum portal.

---

# B. A LISTA EXTRAORDINÁRIA — os cruzamentos que ninguém no mercado faz

**O critério:** cada item precisa de (1) um dado que a corretora tem, (2) uma fonte externa
**que eu verifiquei existir**, e (3) um **mecanismo de dinheiro** explícito.

## B.0 · Primeiro, as fontes externas — verificadas, uma a uma

📊 **Onze verificações que EU rodei hoje, 03/09/2026.** Não são repasse de terceiro:

| fonte | comando | resultado medido |
|---|---|---|
| **SUSEP SES** | `curl -sSI "https://www2.susep.gov.br/download/estatisticas/BaseCompleta.zip"` | **200** · `Content-Length: 571756724` (**545 MB**) · `Last-Modified: Mon, 31 Aug 2026 03:47:22 GMT` |
| SUSEP lista de empresas | `curl` em `.../ses/download/LISTAEMPRESAS.csv` | **200** · 13.142 b |
| SUSEP painéis | `curl` na central-de-paineis | **200** · 370.137 b |
| SUSEP bases anonimizadas | `curl` na página | **200** · 314.965 b |
| **BACEN SGS 433 (IPCA)** | `curl "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/2?formato=json"` | `[{"data":"01/06/2026","valor":"0.16"},{"data":"01/07/2026","valor":"0.07"}]` — **sem chave, sem login** |
| **Opin Directory** | `curl "https://data.directory.opinbrasil.com.br/participants"` | **200** · 2.376.684 b · **38 participantes**, sem autenticação |
| Opin — corretoras | script sobre o JSON | 🔴 **2 corretoras ATIVAS**: `CA2C CORRETORA DE SEGUROS S.A.` (roles `DADOS`+`ICS`) e `OPEN POWER CORRETORA DE SEGUROS S.A.` |
| Opin × portais do repo | script | 🔴 **10 das 15 seguradoras** da tabela `portals` são participantes Opin. Fora: Alfa, Azul, SURA, Suhai, Unimed |
| **ANS dados abertos** | `curl "https://dadosabertos.ans.gov.br/FTP/PDA/"` | **200** · **53 diretórios**, HTTP direto, sem login |
| **FIPE (comunitária)** | `curl "https://fipe.parallelum.com.br/api/v2/references"` | **200** · referência **`setembro/2026`** já publicada · sem autenticação |
| **SINESP** | `curl "https://dados.mj.gov.br/api/3/action/package_show?..."` | 🔴 **`Could not resolve host`** — DNS falhou daqui, em duas tentativas independentes |
| InfoCap → Agger | `curl -sSI "https://www.infocap.com.br/"` | **301 → `https://www.agger.com.br`** |

**E o que eu NÃO consegui, dito com o motivo:**

| fonte | o que aconteceu |
|---|---|
| **Senatran frota** | 📊 `https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026` → **HTTP 403** ao curl. A página existe (a pesquisa a leu por outro caminho); **recusa cliente automatizado** |
| **SINESP / dados.mj.gov.br** | DNS não resolve deste ambiente. **Tem de ser reconferido da produção antes de virar dependência** |
| **SSP-SP** | reportado `ECONNRESET` a cliente automatizado |
| **dados.gov.br API** | **HTTP 401** — exige chave de cadastro |
| **CNPJ / Receita** | `dadosabertos.rfb.gov.br` → `ECONNREFUSED`; caminho alternativo → 404. **Os hosts mudam** |

### 🔴 As sete coisas que NÃO EXISTEM — ditas com todas as letras

Isto vale tanto quanto a lista do que existe, porque cada uma já apareceu como premissa em
alguma conversa de produto:

```
1. ❌ REGISTRO PÚBLICO NACIONAL DE SINISTROS POR SEGURADO — não existe.
      O SRO recebe isso e é FECHADO (SUSEP + registradoras). O "Sistema de Consulta de
      Seguros" (13/11/2023) é self-service pelo CPF do PRÓPRIO titular, sem lote, sem API.
2. ❌ API OFICIAL DA FIPE — não existe. Só formulário web, modelo a modelo.
      Tudo que é REST (parallelum, BrasilAPI) é COMUNITÁRIO, sem SLA e sem vínculo.
3. ❌ FEED MACHINE-READABLE DE NORMATIVOS SUSEP COM VIGÊNCIA — não existe.
      Só o BNPortal (busca HTML) e um CGI legado `bnmapi.exe`. Vigência = scraping.
4. ❌ ROUBO/FURTO DE VEÍCULO NACIONAL POR MUNICÍPIO — não existe.
      O SINESP para em UF/mês. Município só em portal estadual (SSP-SP é o melhor).
5. ❌ ROUBO DE VEÍCULO NO ATLAS DA VIOLÊNCIA — não existe.
      🔴 O Atlas é SIM/SINAN: MORTALIDADE. É crime contra a pessoa, não patrimonial.
      Tem município, do indicador errado. DESCARTAR para esta finalidade.
6. ❌ PRÊMIO/SINISTRO POR UF BAIXÁVEL NA SUSEP — não existe.
      O corte por UF só vive no painel PIMS, que é DASHBOARD-ONLY.
7. ❌ AUTOSEG ATUALIZADO — congelado no 2º semestre de 2020, há ~6 anos.
      Era a melhor base (modelo, ano, região, sexo, faixa etária, prêmio médio).
      O substituto são as "bases anonimizadas" de 10/06/2024, sem periodicidade declarada.
```

## B.1 · Os cruzamentos, com o mecanismo do dinheiro

Colunas: **💰 mecanismo** = vende mais / retém / economiza / negocia melhor.

| # | cruzamento | dado da corretora × fonte externa | 💰 mecanismo | exemplo de valor |
|---|---|---|---|---|
| **B1** 🔴 | **Sinistralidade do ramo × minha condição comercial** *(o exemplo do Founder)* | mix por ramo/seguradora (`/documentos_bi`) × **SES `Ses_cias.csv`**, sinistralidade por `coenti`+`damesano`+ramo | **negocia melhor** | 💭 a seguradora X sobe a sinistralidade de RC Profissional 3 trimestres seguidos → a corretora sabe **antes da carta de reajuste** e renegocia condição, ou migra a carteira. Sobre R$ 11,9 mi de prêmio (📊 Resulta 2025), 1 p.p. de reajuste evitado = **R$ 119 mil** |
| **B2** 🔴 | **Minha sinistralidade × a do mercado, mesmo ramo** | `/sinistros` (📊 5.729 na Resulta) × SES | **negocia melhor** | 💭 "minha carteira de Auto sinistra 11 p.p. abaixo do mercado" é **argumento de comissão**, não conversa de bar. Hoje nenhum concorrente descritivo produz isso |
| **B3** | **Concentração da carteira × ranking de mercado da seguradora** | `mix.insurer@1` × SES + painel **SUSEPCON** (reclamações) | **retém** | 💭 39% da carteira numa seguradora que lidera reclamação = risco de churn em massa. Diversificar antes do estouro |
| **B4** 🔴 | **Praça da corretora × Painel de Corretores da SUSEP** | UF/município dos clientes × `central-de-paineis` → **Painel de Corretores** (município · UF · situação) | **vende mais** | 💭 "há 214 corretores ativos no meu município e eu tenho 0,8% dos clientes" — é a **única fonte pública de tamanho de mercado local por corretagem** que achei |
| **B5** | **Custo de parcelamento × Selic/IPCA** | `forma_pag` + `numpar` + `parcelas[]` × **BACEN SGS 433/4189** (📊 verificado) | **economiza** | 💭 com Selic alta, prêmio à vista com desconto bate 12× no cartão; o sistema diz **quando** o desconto passa a valer a pena |
| **B6** | **Reajuste de saúde × os percentuais da ANS** | carteira saúde × **`percentuais_de_reajuste_de_agrupamento-055`** (ANS, 📊 53 diretórios) | **retém** | 💭 chegar antes da carta de reajuste ao cliente PME é a diferença entre renovar e perder |
| **B7** 🔴 | **Preço da apólice de saúde × valor comercial médio POR MUNICÍPIO** | prêmio × **ANS `valor_comercial_medio_por_municipio_NTRP-054`** + `nota_tecnica_ntrp_vcm_faixa_etaria` | **vende mais / retém** | 💭 "seu plano está 22% acima do médio do seu município na sua faixa etária" — 🔴 **é a fonte mais acionável de todo o acervo ANS**, e nenhum concorrente a usa |
| **B8** | **Frota do cliente PJ × frota do município** | itens de Auto (`/itens`) × **Senatran XLSX mensal** (⚠️ 403 a curl; raspar listagem) | **vende mais** | 💭 dimensiona o mercado de frota da praça, por modelo e combustível |
| **B9** | **Valor segurado × FIPE do mês** | `/itens` (placa/modelo) × **FIPE comunitária** (📊 `setembro/2026` disponível) | **retém** | 💭 apólice com IS defasada em relação à FIPE é sinistro mal pago e cliente perdido. ⚠️ dependência de terceiro sem SLA |
| **B10** | **Exposição a roubo × SINESP UF/mês** | UF dos itens × **SINESP** (⚠️ 📊 DNS falhou aqui) | **negocia melhor** | 💭 subida de roubo na UF antecipa endurecimento de aceitação; avisar o cliente antes vale renovação |
| **B11** | **Carteira PJ × porte/CNAE da Receita** | `cpf_cnpj` PJ (`/cliente`) × dumps CNPJ (⚠️ hosts instáveis) | **vende mais** | 💭 cliente que virou EPP precisa de RC e frota que não tem |
| **B12** 🔴 | **Cliente com 1 produto × mix típico do perfil** | `/cliente_ligacoes` × a própria carteira como referência | **vende mais** | 🔴 é o `Mix de Carteira` da Segfy, **vendido explicitamente como cross-sell** — mesa posta, não diferencial. Mas é o de maior retorno por hora de trabalho |
| **B13** | **Renovação × sinistro aberto na mesma apólice** | `/renovacoes` × `/sinistros` por `nosnum` | **retém** | 💭 renovar quem tem sinistro aberto sem falar do sinistro é como se perde cliente. Ninguém cruza as duas listas hoje |
| **B14** | **Produtor × cobertura de atribuição** | `prod_docs` × `data.coverage@1` | **economiza** | 📊 apólice sem produtor `ordem=1` é 2,9% na Resulta e 0,9% na AutoFleet — repasse que **ninguém reclamou** |
| **B15** 🔴 | **Quem no meu município já é participante Opin** | praça × **Opin Directory** (📊 38 participantes, 2 corretoras) | **vende mais** | 🔴 📊 **10 das 15 seguradoras do `portals` do repo já são participantes Opin.** Quando a Fase 2 abrir, é o mapa de quem entrega dado de cliente por API — e prova que **corretora é elegível como participante** |
| **B16** | **Vigência de norma × produtos da carteira** | ramo × BNPortal/Fenacor (⚠️ sem feed, exige scraping) | **retém** | 💭 mudança de norma em ramo específico é motivo de contato — e de venda |
| **B17** | **Renda/população do município × penetração** | clientes por município × **IBGE SIDRA** (sem chave) | **vende mais** | 💭 `apisidra.ibge.gov.br/values/t/6579/n6/all/v/all/p/last` devolve os ~5.570 municípios. ⚠️ renda municipal só existe no Censo (decenal) |
| **B18** | **Cotação perdida × preço praticado depois** | `/negocios_finalizados` + `motivo_perda` × SES prêmio médio | **vende mais** | 💭 o funil da InfoCap grava `motivo_perda` e ninguém lê. **É dado que a corretora já tem e joga fora** |

---

# C. CONECTORES E FONTES PAGAS — o que vale comprar

## C.0 · 🔴 A conclusão que inverte a pergunta

> ## O dado que diferencia é quase todo GRÁTIS. O fosso é a INGESTÃO, não a licença.

📊 SUSEP SES (545 MB semanais), SUSEP AUTOSEG (CEP → região tarifária **junto com contagem de
sinistro**), as bases anonimizadas de apólice-e-sinistro, e os 53 diretórios da ANS cobrem
quase tudo que "o concorrente não entrega". **Nenhum tem API REST — e é exatamente por isso
que ninguém construiu em cima deles.** O custo é um buscador agendado sobre caminhos de
arquivo previsíveis, não uma assinatura.

**O que vale comprar são três coisas, e todas são baratas.**

## C.1 · As três compras que dariam salto

| # | o que | preço PÚBLICO | o que destrava | nota |
|---|---|---|---|---|
| **C1** 🔴 | **SPC Histórico Veicular** — `https://loja.spcbrasil.com.br/spc-historico-veicular` (📊 HTTP 200 verificado hoje) | **R$ 51,90** (varejo) | 🔴 contém *"Sinistros — Acidentes com indenização registrada por seguradoras"*, avarias, roubo/furto, leilão. **Histórico de sinistro registrado POR SEGURADORA, por placa** — a única fonte que vi com isso. É o dado que nenhum concorrente reproduz a partir de fonte aberta | **90** |
| **C2** 🔴 | **BigDataCorp — API de Endereços** · tabela pública sem login: `https://docs.bigdatacorp.com.br/plataforma/docs/tabela-de-preços` (📊 HTTP 200, 918.418 b, verificado hoje) | **R$ 0,08** "Endereços em Área de Risco" · **R$ 0,06** "Estatísticas Criminais" · **R$ 0,04** "Municípios" · **500 consultas grátis** por dataset | 🔴 **os únicos preços por consulta de risco de endereço publicados no Brasil.** Passa CEP, volta bandeira de área de risco + estatística criminal regional. Também `API de Empresas`: dados básicos **R$ 0,03**, 🔴 **"Relacionamentos do Grupo Econômico" R$ 0,06** — diz ao corretor que três CNPJ da carteira são **um cliente só** com exposição somada | **88** |
| **C3** | **Consultar Placa** — docs públicas: `https://docs.consultarplaca.com.br/api-consultar-placa/preco.md` (📊 verificado hoje, valores VERBATIM abaixo) | ver tabela | modelo de custo **por campo**, o que permite decidir o que enriquecer em massa e o que checar sob demanda | **82** |

📊 **A tabela do C3, copiada do próprio arquivo que eu baixei** (coluna 2 = preço cheio;
coluna 3 = com o desconto de 20% do pacote de créditos):

```
Dados básicos placa/chassi   R$ 0,31 → R$ 0,15  (1–1.000 → 10.001–20.000)
Preço FIPE por placa         R$ 0,99 → R$ 0,70  (1–1.000 → acima de 100.000)
Ocorrência de PERDA TOTAL    R$ 4,50 → R$ 3,80
Histórico de roubo e furto   R$ 6,90 → R$ 6,10
RENAVAM                      R$ 5,20 → R$ 4,40
Débitos RENAINF              R$ 4,50 → R$ 3,80
Proprietário atual           R$ 6,90 → R$ 6,10
Registro de leilão           R$ 16,90 → R$ 15,90
```

💭 **O que isso significa em conta:** FIPE a R$ 0,70–0,99 torna *"valor de mercado atualizado
em toda a carteira de Auto, todo mês"* praticamente de graça. Leilão a R$ 15,90 continua
sendo checagem dirigida. **A decisão de arquitetura sai do preço, não do gosto.**

## C.2 · Enriquecimento em volume — o mais barato de cada categoria

| categoria | melhor opção pública | preço PÚBLICO | por que essa |
|---|---|---|---|
| **consulta a órgão público em lote** | **Infosimples** `https://infosimples.com/consultas/precos/` (📊 HTTP 200 verificado) | **R$ 0,20** (1–500) escalando até **R$ 0,05** (100.001+); pré-pago, franquia mínima **R$ 100/mês** | 🔴 é a rota **legítima** para Sinesp Veículo (não existe API oficial) e a mais ampla em DETRAN estadual. ⭐ **tem APIs de SUSEP/Corretores** — verifica se o registro do corretor está ativo |
| **CNPJ oficial** | **Serpro Consulta CNPJ** — docs públicas `https://apicenter.estaleiro.serpro.gov.br/documentacao/consulta-cnpj/` | ⚠️ **loja.serpro.gov.br devolveu 403** ao robô — o preço existe atrás de filtro. Único preço confirmado é de **Consulta CPF**: faixa 2 = **0,5649**, faixa 3 = **0,3557** | única fonte **oficial** da Receita em tempo real. Exige e-CNPJ e contrato: semanas, não horas |
| **CNPJ barato** | **Casa dos Dados** `https://docs.casadosdados.com.br/` | **R$ 0,01 por CNPJ**; reconsulta do mesmo CNPJ em 30 dias é grátis | ⭐ o diferencial é **prospecção em massa** por CNAE + município + porte. É produto de VENDA, não de enriquecimento |
| **score de crédito** | ⚠️ **nenhum bureau tem doc pública com preço** | Serasa varejo PME: **R$ 120,00 / até 9 consultas** = **R$ 13,33/consulta**. Revendedor SOA: Básica PF/PJ *"a partir de R$ 5,40"* | 🔴 **os quatro bureaus (Serasa, Boa Vista/Equifax, SPC, Quod) são todos gated por contrato.** Nenhum é self-serve |

## C.3 · ⛔ O que NÃO se pode comprar, a nenhum preço

```
1. ⛔ CNseg — Estudos Técnicos e a Ferramenta de Riscos Climáticos (score de inundação
      POR ENDEREÇO, lançada na COP30, https://cnseg.org.br/conteudos/risco-climatico)
      🔴 CNseg é a confederação das SEGURADORAS. Corretora NÃO é elegível.
      A rota, se houver, é por uma seguradora parceira — não por compra.

2. ⛔ SINCO / Sincor — https://sincor.org.br/estatisticas/
      gated por associação de corretor, e a licença é de uso INTERNO do associado.
      Redistribuir num SaaS multi-tenant fura a licença.

3. ⛔ API de carteira da Quiver / Segfy / Agger — 🔴 NÃO EXISTE PROGRAMA.
      📊 zero developer portal, zero OpenAPI, zero referência de endpoint, em TODO o
      mercado (Quiver, Segfy, Agger, TEx, Moshe, SGCOR, BIBlue).
      A camada de API neste mercado está na SEGURADORA, não no sistema de gestão:
      Junto Seguros https://www.juntoseguros.com/desenvolvedor-api/
      Tokio Marine  https://integracao.tokiomarine.com.br/

4. ⛔ Ituran "Mapa de Risco de Roubo e Furto" (https://ituran.com.br/mapa-de-risco/)
      a melhor geografia PROPRIETÁRIA de roubo de auto do Brasil, 700k+ veículos
      monitorados. Ferramenta pública, SEM API e SEM programa de licenciamento.
      Raspar fura os termos. Só abordagem comercial direta.
```

🔴 **E o corolário que decide o desenho de A3/A9:** já que não há API de carteira nem padrão
de troca, **📊 a Quiver importa extrato de comissão em XLS deixando o USUÁRIO definir a ordem
das colunas, e a Segfy tem template proprietário próprio, limitado a 1.000 linhas**
(`https://ajuda.segfy.com/knowledge/segurados-formas-de-importação-no-sistema`).
**Dois templates concorrentes e leitura de PDF É o estado da arte do mercado.** A ingestão de
extrato com mapeamento por seguradora não é atalho — é o caminho que todo mundo percorre.

## C.4 · 🔴 As duas datas e o campo minado jurídico

### ⏰ 01/10/2026 — a janela grátis do WhatsApp fecha em ~1 mês

📊 Verbatim da Meta (`https://developers.facebook.com/docs/whatsapp/pricing/updates-to-pricing/`):
> *"Effective October 1, 2026, Meta will charge for service messages, which have not been
> charged since November 2024."*
> *"By market, rates for service messages are the same as the rates for utility and
> authentication messages."*

📊 Rate card BRL vigente desde 01/07/2026 — ⚠️ **os CSV oficiais da Meta são renderizados por
JS e não foram lidos diretamente**; os números vêm de duas fontes independentes:

| categoria | BRL/msg | USD/msg | desconto por volume |
|---|---|---|---|
| **Marketing** | **R$ 0,3217** | $0,0625 | **nenhum** |
| **Utility** | **R$ 0,0350** | $0,0068 | sim, até −25% |
| **Authentication** | R$ 0,0350 | $0,0068 | sim |
| **Service** | grátis **até 30/09/2026** | — | nenhum depois |

📊 **A conferência interna que dá direito à conclusão:** os dois conjuntos são consistentes
num único câmbio implícito — `0,3217 / 0,0625 = 5,147` **e** `0,0350 / 0,0068 = 5,147`.
Duas fontes independentes batendo em quatro algarismos por um só câmbio é evidência forte de
que ambas derivam do mesmo card real. ⛔ E **rejeita** os cards que ainda falam em *"1.000
service conversations grátis por mês"* — é conceito do modelo de conversa, revogado em 2025.

🔴 **O risco de custo é a CATEGORIZAÇÃO, e ele é de 9,2×.** A Meta revisa cada template e
**atribui a categoria ela mesma**. Um relatório que soe promocional — qualquer empurrão para
renovação ou upsell — é reclassificado **Marketing**: **R$ 0,3217 contra R$ 0,0350 no mesmo
envio.** ⚠️ Template de relatório se escreve estritamente transacional, preso a um evento de
apólice existente, com zero linguagem de venda.
⚠️ E a migração de faturamento para BRL é **obrigatória até 30/06/2027**.

### ⛔ O campo minado: dado de agência de rating

🔴 **É o único item desta pesquisa que não deve ser ingerido sem licença de redistribuição.**
Os sites gratuitos de S&P Brasil (`https://brazil.ratings.spglobal.com/pt`), AM Best e
Moody's Local existem para cumprir **divulgação regulatória da CVM** — os termos permitem
**consulta**, não extração sistemática nem redistribuição. Um SaaS que raspe rating e sirva
aos tenants precisa de acordo **antes da primeira linha de scraper**.
📊 O único preço público de todo o bloco de mercado: **US$ 185** por um relatório avulso da
AM Best (`https://www3.ambest.com/ambv/sales/bwpurchase.aspx?record_code=366033`).

### ⚠️ E a linha LGPD que atravessa tudo

```
o arquivo aberto da ANS é aberto. O JOIN dele com o seu segurado NÃO é.
🔴 carteira de saúde + linha da ANS = dado pessoal SENSÍVEL de saúde (LGPD Art. 11).
   A licença aberta cobre redistribuir o arquivo da ANS. Não cobre o que você constrói
   ao cruzá-lo com nome de gente.

"Proprietário atual" (R$ 6,90) devolve pessoa nomeada, sem consentimento dela.
🔴 só onde a corretora tiver autorização do próprio segurado. Nunca para prospecção.

o tenant é o CONTROLADOR; a plataforma é OPERADORA. O opt-in de WhatsApp e a base
legal de consulta a bureau são da CORRETORA, e isso vai em contrato — não em código.
```

## C.5 · O que EU não consegui verificar, e por quê

| item | o que aconteceu |
|---|---|
| tabela de preço do **Serpro CNPJ** | 📊 `loja.serpro.gov.br` → **HTTP 403** em toda tentativa. O preço quase certamente existe, atrás de filtro anti-robô. **Conferir num navegador** |
| planos do **CNPJá** | 📊 **HTTP 429** em toda tentativa; os valores citados são de segunda mão |
| preços do **API Placas** | 📊 **HTTP 403** |
| CSV oficiais de tarifa da **Meta** | renderizados por JS; conferidos por consistência de câmbio, não por leitura |
| se **BrasilAPI CEP v2** devolve lat/long | não confirmado |

---

# D. PRIORIDADE — dinheiro × viabilidade com o que existe HOJE

**Como a nota é formada** (0–100, e a conta está escrita para poder ser contestada):

```
NOTA = 0,55 × DINHEIRO   (quanto entra ou deixa de sair no bolso da corretora)
     + 0,45 × VIABILIDADE (a fonte existe HOJE, medida, e o dado da corretora já é lido)
```

⚠️ **Os pesos são escolha minha, 💭 não medição.** Estão escritos para que o Founder possa
mudá-los e reordenar a lista sem refazer a pesquisa.

## D.1 · TOP da lista OBRIGATÓRIA

| nota | item | por quê, em uma linha |
|---|---|---|
| **94** | **A3 · Comissão recebida × apropriada** | é dinheiro que **já é da corretora e não chegou**; os três concorrentes têm e a InfoCap não entrega em lote — o caminho é o portal, não a API |
| **91** | **A6 · Renovações 30/60/90** | 📊 2,28 s e já pronto na 094; cada apólice não renovada é receita recorrente perdida |
| **88** | **A9 · Inadimplência / parcelas** | parcela vencida cancela apólice e leva a comissão junto; mesmo caminho de A3 |
| **86** | **A16 · Funil / cotação que não virou** | 🔴 três rotas **existem na doc e nunca foram medidas**; `motivo_perda` é dado já capturado e ignorado |
| **84** | **A15 · Sinistros da carteira** | o censo destravou 5.729 registros e a doc revelou 7 parâmetros — sai de "acervo de 26 s" para relatório usável |
| **82** | **A12 · Cross-sell por cliente** | maior retorno por hora do vendedor; ⚠️ a Segfy já vende exatamente isso |
| 78 | A14 · Pendência de emissão | 📊 `sit_acompanhamento_txt` já vem pronto no `/documento` |
| 74 | A5 · Contribuição líquida | ✅ na 094, mas 🔴 **só existe onde há interseção** — e na AutoFleet ela é ZERO |
| 70 | A10 · Cancelamentos | 📊 uma chamada com `cancelado=T` tira de PARTIAL |

## D.2 · TOP da lista EXTRAORDINÁRIA

| nota | item | por quê, em uma linha |
|---|---|---|
| **92** | **B1 · Sinistralidade SUSEP × condição comercial** | 📊 fonte medida hoje (545 MB, semanal); é **a** conversa que muda o resultado da corretora, e nenhum concorrente descritivo a tem |
| **88** | **B7 · Preço de saúde × valor comercial médio POR MUNICÍPIO (ANS)** | 📊 CSV limpo, HTTP direto, sem login; granularidade município + faixa etária é ouro e ninguém usa |
| **85** | **B2 · Minha sinistralidade × a do mercado** | mesma fonte de B1, e o dado interno (`/sinistros`) já está medido |
| **83** | **B12 · Cross-sell** | viabilidade máxima (só dado interno) — a nota cai porque a Segfy já entrega |
| **80** | **B13 · Renovação × sinistro aberto** | duas rotas 200 já medidas; join por `nosnum`; retenção pura |
| 78 | B15 · Mapa Opin | 📊 verificado por mim hoje; é inteligência de posicionamento, não receita direta |
| 76 | B6 · Reajuste ANS | mesma fonte de B7, com um passo a menos de valor |
| 72 | B4 · Painel de Corretores SUSEP | ⚠️ **dashboard-only**: não é baixável, então entra como leitura humana |
| 70 | B18 · Cotação perdida × preço de mercado | depende de A16 existir primeiro |
| 68 | B5 · Custo de parcelamento × Selic | 📊 API impecável, mas o ganho por cliente é pequeno |
| 62 | B9 · IS × FIPE | valor alto, ⚠️ **dependência comunitária sem SLA** derruba a viabilidade |
| 45 | B10 · Roubo × SINESP | 🔴 DNS falhou aqui **e** a granularidade é UF, não município |
| 40 | B8 · Frota Senatran | 📊 403 ao curl + nomes de arquivo instáveis mês a mês |
| 35 | B16 · Vigência de norma | ❌ não há feed; scraping de CGI legado |

## D.3 · O que a SPEC-094 já entrega, e o que é a PRÓXIMA SPEC

📊 **Métricas v1 da SPEC-094** (lidas de `SPEC-094:390-397`):
`production.policy_count@1` · `production.premium_written@1` · `commission.broker_accrued@1` ·
`production.new_vs_renewal@1` · `mix.insurer@1` · `mix.branch@1` · `producer.performance@1` ·
`producer.momentum@1` · `renewal.exposure@1` · `projection.run_rate@1` · `data.coverage@1` ·
`repasse.producer_accrued@1` · `contribution.after_repasse@1` — **13 métricas**.

```
✅ COBERTO PELA 094       A1 A2 A4 A5 A6 A7 A8 A11   (8 de 16)
◐ PARCIAL                 A10  (cancelado=T não medido)
🔴 A PRÓXIMA SPEC         A3 A9  — comissão recebida e inadimplência.
                          Não vêm da CorpAPI (§2.3 do catálogo). Vêm do PORTAL.
                          É a maior nota da lista A e a maior lacuna do produto
🔴 A SPEC DEPOIS DELA     A15 A16 — sinistro e funil. Ambos com rota 200 ou documentada,
                          nenhum medido, custo baixo
⚠️ FORA DE SPEC HOJE      A12 A13 A14 — baratos, alto giro, sem dono
```

🔴 **E a recomendação de sequência que a evidência sustenta:** antes de qualquer SPEC nova,
**as 6 chamadas GET do §5 do catálogo** (`/producao` com os params certos, `/documentos` com
`periodo=datinc`, `/sinistros` com janela, `/negocios_andamento`, `/produtores`,
`tipo_doc=TODOS`). 💭 Custo estimado abaixo de 1 minuto de relógio. Elas decidem se A15,
A16 e a base temporal de apropriação são SPEC de uma semana ou de um dia.

## D.4 · A prioridade dos CONECTORES (lista C)

| nota | conector | por quê |
|---|---|---|
| **90** | **SPC Histórico Veicular** (R$ 51,90) | sinistro registrado por seguradora, por placa — 🔴 **inimitável a partir de fonte aberta** |
| **88** | **BigDataCorp** (R$ 0,04–0,08) | 🔴 único preço público de risco de endereço no Brasil; e `Grupo Econômico` a R$ 0,06 revela que 3 CNPJ da carteira são 1 cliente |
| 82 | **Consultar Placa** (FIPE R$ 0,70–0,99) | torna "IS × FIPE em toda a carteira, todo mês" quase de graça — habilita **B9** |
| 76 | **Infosimples** (R$ 0,05–0,20) | rota **legítima** para Sinesp; ⭐ tem API de **SUSEP/Corretores** |
| 70 | **Casa dos Dados** (R$ 0,01/CNPJ) | prospecção por CNAE + município — produto de VENDA, não de relatório |
| 55 | **Serpro CNPJ** | única fonte oficial em tempo real; ⚠️ e-CNPJ + contrato = semanas |
| 40 | **bureaus de crédito** | 🔴 todos gated; e a base legal LGPD para score de segurado é frágil |

⏰ **A única coisa desta pesquisa com PRAZO:** 📊 **01/10/2026** — a mensagem de serviço do
WhatsApp deixa de ser grátis. É daqui a **28 dias**. Qualquer plano de entregar relatório por
WhatsApp muda de conta nessa data (§C.4), e o risco de categorização é de **9,2×**.

---

# E. O ESTADO DA ARTE (§7.3) — o chat pode auto-criar um cálculo novo?

> **A pergunta do Founder:** o chat principal deve poder **auto-criar um cálculo novo** que o
> corretor pediu e ainda não existe — sem inventar número?

## E.0 · A resposta curta, e o número que decide

> ## 🔴 NÃO auto-criar. **PROPOR** — e um humano promove.
> 📊 **Nenhum dos cinco líderes de mercado deixa o LLM criar uma métrica persistente.**
> Em quatro deles é **impossível por construção**; no quinto (Cube) é possível **rascunhar**
> e **impossível publicar**.

📊 **O número que encerra o debate**, do benchmark BIRD (`https://bird-bench.github.io/`):
a melhor sistema de text-to-SQL do mundo faz **82,28%** de acurácia de execução contra uma
**linha de base humana de 92,96%** — em benchmark onde o schema é **conhecido**.

```
🔴 UMA RESPOSTA EM CINCO ESTÁ ERRADA quando o modelo escreve a consulta sozinho.
```

⚠️ **E é exatamente o defeito do CLAUDE.md §9.5:** *"um passo que trava é barulhento; um
passo que responde errado é silencioso e chega ao cliente"*. Uma query que **falha** é
inofensiva. Uma query que devolve **R$ 1.7 mi em vez de R$ 1,86 mi** é lida, acreditada e
usada numa negociação com a seguradora.

📊 **E a queda em schema real é maior ainda** — Spider 2.0 (`https://spider2-sql.github.io/`),
com bases de mais de 1.000 colunas: **o1-preview resolve 17,1%** e **GPT-4o 10,1%**, contra
**86,6%** do Spider 1.0. 💭 A diferença entre os 10–17% do modelo cru e os 76–96% dos agentes
de topo do leaderboard **é andaime e recuperação, não capacidade de modelo** — que é
precisamente a alavanca que uma camada semântica puxa.

📊 **A única comparação CONTROLADA que encontrei** (mesmo modelo, mesmo benchmark, a camada
semântica como único fator variado) é da Snowflake
(`https://www.snowflake.com/en/blog/engineering/agentic-semantic-model-text-to-sql/`):

| dataset BIRD | LLM cru | + modelo semântico |
|---|---|---|
| debit_card_specializing | 52% | **83%** |
| california_schools | 63% | **80%** |
| thrombosis_prediction | 45% | **70%** |
| toxicology | 69% | **79%** |

> *"we observed an approximately **20% increase in accuracy** over the version lacking a
> proper semantic model"*

🔴 **É a linha de controle do CLAUDE.md §9.2 aplicada a este problema** — e a conclusão dela
é dupla: a camada semântica é a correção mais barata que existe, **e ainda assim não chega
à paridade humana.**

## E.1 · As referências, no formato do §7.3

### ① dbt Semantic Layer + MCP server

**URL** · `https://docs.getdbt.com/docs/dbt-ai/mcp-available-tools` ·
`https://docs.getdbt.com/blog/introducing-dbt-mcp-server` — reaberta em **03/09/2026**
**O QUE FAZ** · expõe a camada semântica como superfície fixa de ferramentas: `list_metrics`
→ `get_dimensions` / `get_entities` → `query_metrics`. O MetricFlow compila o SQL; o modelo
nunca o escreve.
**MODELAMOS** · 🔴 **a descoberta obrigatória antes da pergunta.** O modelo tem de *listar* o
vocabulário legal antes de poder perguntar — então uma métrica alucinada falha **na chamada
da ferramenta**, não na resposta. É o mesmo princípio do `registry` da SPEC-094.
**REJEITAMOS** · ⚠️ **entregar `text_to_sql` e `execute_sql` no MESMO servidor**, ao lado das
ferramentas governadas e sem porteiro. Um agente que ouve "não existe essa métrica" vai
**contornar** pela porta livre. **A porta governada só vale o que vale a ausência da outra.**
📊 Não há campo publicado: dbt afirma *"a higher baseline of accuracy than LLM generated SQL
queries"* **sem número**.
**COMO O JUIZ INSPECIONA** · abre a lista de ferramentas e confere que a categoria Semantic
Layer tem **sete** ferramentas e **nenhuma** cria métrica; depois acha `text_to_sql` na
categoria SQL, na mesma página.

### ② Cube — MCP server

**URL** · `https://docs.cube.dev/docs/integrations/mcp-server` — reaberta em **03/09/2026**
**O QUE FAZ** · 23 ferramentas: `searchDataModel` para descobrir, `runQuery` para executar. O
agente pede **conceitos de negócio pelo nome**; o Cube compila o SQL de forma determinística.
Verbatim: *"it does not generate raw SQL"*.
**MODELAMOS** · 🔴 **a forma inteira, e é a melhor resposta à pergunta do Founder.** O agente
**pode** escrever arquivo de modelo — mas só com papel de editor, **só em branch de
desenvolvimento**, com `getBranchDiff` para revisão, e:

> *"**Promotion is manual and human.** … The MCP server deliberately exposes **no commit
> tool** — an AI client can prepare changes, but only a person can ship them."*

🔴 **A garantia é a AUSÊNCIA da ferramenta, não uma instrução de prompt.** Remover a
capacidade é infinitamente mais forte que pedir ao modelo que se contenha — e é a diferença
entre governança e boa intenção.
**REJEITAMOS** · ⚠️ o `chat` ser ele próprio uma ferramenta MCP: um agente externo delega e
recebe **prosa** de volta. Isso **lava** um resultado governado em narrativa não auditada —
o número está certo, a frase em volta dele não passou por régua nenhuma. Na fronteira, o
resultado atravessa **estruturado**, nunca como texto.
**COMO O JUIZ INSPECIONA** · procura na doc um verbo de commit entre as 23 ferramentas e não
acha; confere que `writeDataModelFile` recusa branch que não seja de desenvolvimento.

### ③ Snowflake Cortex Analyst — Verified Query Repository

**URL** · `https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository`
· avaliações: `https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst-evaluations` — reaberta em **03/09/2026**
**O QUE FAZ** · um modelo semântico YAML define tabelas/colunas/métricas **lógicas**; o
Analyst gera SQL **sobre os nomes lógicos**, e o VQR guarda pares pergunta→SQL verificados.
**MODELAMOS** · 🔴 **o desenho da AVALIAÇÃO, que é o mais rigoroso de toda a pesquisa:**
*"Cortex Analyst creates a temporary copy of your semantic view with those selected queries
removed"* — **held-out**, então o sistema não pode acertar por recordação; juiz por LLM; e
métricas de **regressão** que rastreiam *"verified queries that were previously answered
correctly but are now failing"*. **É régua com linha de controle, no sentido do §9.2 —
exatamente o que o CLAUDE.md exige e quase ninguém faz.**
**REJEITAMOS** · 🔴 `verified_by` e `verified_at` serem **OPCIONAIS** no YAML. **Um selo de
confiança que PODE faltar é um selo que VAI faltar** — e a jusante tudo trata a entrada como
verificada de qualquer jeito. É o defeito do §9.3: um guarda que não tem como falhar não
guarda nada.
**COMO O JUIZ INSPECIONA** · abre o YAML do VQR e confere que `verified_by`/`verified_at`
estão marcados como opcionais; abre a página de avaliações e acha a cópia temporária com as
queries removidas.

### ④ Databricks AI/BI Genie — trusted assets

**URL** · `https://docs.databricks.com/aws/en/genie-agents/tune-quality` — reaberta em
**03/09/2026** ⚠️ as URLs antigas `/genie/trusted-assets` **redirecionam** para cá; o espelho
Azure devolveu **404** hoje.
**O QUE FAZ** · *"Trusted assets are example SQL queries and SQL functions that provide
verified answers to questions you anticipate from users."* Quando um ativo casa, o modelo
**não gera** — ele preenche parâmetros de SQL escrito por gente. Autoria é humana:
*"Users with at least CAN EDIT permission … can add or remove trusted assets."*
**MODELAMOS** · 🔴 **o selo "Trusted" NA PRÓPRIA RESPOSTA.** O leitor vê, sem sair da
mensagem, se aquele número veio de SQL certificado ou de geração. **É a coisa mais barata e
de maior valor de toda esta pesquisa** — governança visível no ponto de consumo, não
enterrada num console de administrador. Casa exatamente com o `[metric@version · time_basis ·
coverage]` que a SPEC-094 já põe ao lado de cada número.
**REJEITAMOS** · ⚠️ o casamento por **texto exato**. Um ativo confiável que só dispara na
redação idêntica quase nunca dispara em conversa real, e a degradação silenciosa para
"apenas um exemplo" faz o operador **acreditar que tem guarda-corpo onde tem uma dica**.
**COMO O JUIZ INSPECIONA** · abre a página e confere as duas famílias (parameterized queries
e UC functions) e a frase de permissão `CAN EDIT`; confirma que a doc **não diz** o que Genie
faz quando nenhum ativo casa.

### ⑤ Looker / LookML + Gemini Conversational Analytics

**URL** · `https://docs.cloud.google.com/looker/docs/conversational-analytics-overview` —
reaberta em **03/09/2026**
**O QUE FAZ** · a formulação mais limpa do padrão inteiro:
*"Conversational Analytics determines which fields, filters, sorts, and limits should be
used in the query. **Looker then composes and executes the query by using the underlying
LookML model.**"* — o modelo escolhe **quais campos registrados**; o Looker monta a consulta.
**MODELAMOS** · 🔴 **publicar a lista das formas de pergunta que o sistema responde e das que
NÃO responde.** A doc declara suportado *"metric trends over time, breakdown of a metric by
dimension, top dimension values by metric"* e **não suportado** *"prediction and forecasting,
advanced statistical analysis, including correlation and anomaly detection"*.
**Recusar uma categoria em voz alta bate tentar mal** — e é o que impede o chat da corretora
de "prever a sinistralidade do ano que vem" com três pontos de série.
**REJEITAMOS** · 🔴 a alegação de acurácia. *"reduces data errors … by **as much as two
thirds**"* aparece em dois blogs do Google atribuída a *"our own internal testing"*, **sem
tamanho de amostra, sem linha de base, sem método, sem link para resultado**.
⚠️ **É o defeito do CLAUDE.md §12.1 acontecendo à vista:** um número ilustrativo virou "fato
do produto" e já atravessou dezenas de documentos. **Marcar 💭 e nunca citar como medição.**
**COMO O JUIZ INSPECIONA** · abre os dois blogs, procura metodologia, não acha; abre a doc de
overview e acha as duas listas (suportado / não suportado).

### ⑥ Euno — "shift-left proposals" (o fluxo propor → revisar → promover)

**URL** · `https://euno.ai/use-cases/dbt-looker` (⚠️ `https://docs.euno.ai/automations/shift-left-proposals`
está indexado mas **devolveu 404 à busca direta** em 03/09/2026 — as citações vieram do
índice de busca, **não de leitura direta**; tratar como INFERÊNCIA até reabrir)
**O QUE FAZ** · detecta uma medida que nasceu no lugar errado — *"a measure in a LookML View
or a custom measure in a Tile or Look"* — e **gera um diff** de modelo, não uma sugestão.
Promoção é botão humano ("Create change draft") e daí segue o ciclo normal de PR.
**MODELAMOS** · 🔴 **a verificação de DUPLICATA no momento da proposta:** *"performs
comprehensive consistency checks … flagging duplicates, conflicts, and breaches of modeling
principles."*
**Este é o ponto que ninguém adivinharia e todo mundo implementa.** O modo de falha real de
métrica auto-criada **não é fórmula errada** — é **três "comissão do mês" sutilmente
diferentes**, cada uma defensável sozinha, que fazem dois relatórios discordarem e destroem
a confiança no sistema inteiro. Um fluxo de proposta que não pergunta *"isto já existe com
outro nome?"* **fabrica** esse problema.
**REJEITAMOS** · 💭 tratar como referência forte enquanto a doc não abrir — e o AtScale, que
tem discurso de governança de IA (`https://www.atscale.com/use-cases/generative-ai/`) mas
**nenhuma máquina de estados de proposta→aprovação documentada**, não deve ser citado como
se tivesse.
**COMO O JUIZ INSPECIONA** · tenta a URL da doc; se ainda 404, marca a referência como
**não reaberta** e não a deixa sustentar decisão sozinha.

## E.2 · O padrão único, e a recomendação

🔴 **Quatro empresas, quatro pilhas, uma só forma:**

```
A SAÍDA DO LLM É UM OBJETO DE CONSULTA. NUNCA UMA DEFINIÇÃO.

dbt      -> parâmetros do MetricFlow
Cube     -> uma query semântica ("it does not generate raw SQL")
Looker   -> fields + filters + sorts + limits
Genie    -> só os PARÂMETROS de um SQL escrito por gente
Cortex   -> SQL, sim — mas sobre nomes LÓGICOS que não existem no warehouse
```

### 🔴 A recomendação, com nota

| opção | nota | por quê |
|---|---|---|
| **(b) PROPOR → revisar duplicata → humano promove → registrado** | **92** | é o que Cube e Euno fazem; preserva a promessa de "o chat resolve" sem pôr número inventado na frente do dono da corretora |
| (c) impossível — só métricas registradas | 74 | seguro e o mais comum (4 de 5); mas o corretor pede recorte novo toda semana, e "não sei fazer" é atrito real |
| **(a) criar e responder na hora** | **18** | 📊 BIRD diz **uma em cinco errada**; §9.5 diz que a errada é a **silenciosa**; e o número vai para uma negociação com seguradora |

**Os quatro mecanismos a copiar, na ordem em que fecham a porta:**

```
1. 🔴 REMOVER A CAPACIDADE, não pedir contenção.
      Cube: "deliberately exposes NO COMMIT TOOL". Um prompt que pede para o modelo
      não publicar é uma promessa; uma ferramenta ausente é uma garantia.

2. 🔴 CHECAR DUPLICATA ANTES DE PROPOR.
      Euno: "flagging duplicates". Três "comissão do mês" divergentes destroem mais
      confiança que uma métrica faltando.

3. 🔴 O SELO VIAJA COM A RESPOSTA.
      Genie: badge "Trusted" na própria mensagem. A SPEC-094 já faz isso —
      [metric@version · time_basis · coverage] ao lado de cada número.
      Estender: dizer se veio do REGISTRY ou de uma PROPOSTA.

4. 🔴 A RÉGUA TEM LINHA DE CONTROLE E DETECTA REGRESSÃO.
      Cortex: cópia temporária com as queries REMOVIDAS + métrica de regressão sobre
      "o que respondia certo e passou a falhar". É o §9.2 e o §9.3 do CLAUDE.md,
      escritos por outra empresa.
```

⚠️ **E a trava que a evidência exige, específica deste produto:** uma métrica **proposta**
nunca pode aparecer como número no chat com a mesma cara de uma **registrada**. Se aparecer,
o item 3 vira decoração — e o §12.1 já custou seis documentos ao projeto uma vez.

---

## F. O QUE ESTA PESQUISA NÃO CONSEGUIU

| não obtido | por quê |
|---|---|
| Senatran frota (XLSX) | 📊 **HTTP 403** a cliente automatizado; a página existe |
| SINESP / `dados.mj.gov.br` | 📊 **DNS não resolve** deste ambiente, em duas tentativas independentes. **Reconferir da produção** |
| SSP-SP (roubo por município) | `ECONNRESET` a cliente automatizado |
| dados.gov.br API | **HTTP 401** — exige chave de cadastro |
| dumps CNPJ da Receita | `ECONNREFUSED` + 404; os caminhos mudam de mês |
| doc do Euno | **404** à busca direta; citações vieram do índice, marcadas como tal |
| SES: confirmar sinistralidade por ramo **sem baixar 545 MB** | o ZIP é a única forma; não baixei |
| qualquer preço de Quiver PRO / TEx / Moshe | **não publicado** por nenhum deles |
| nome de qualquer relatório do SGCOR | 📊 anuncia *"mais de 90 relatórios"* e **não nomeia nenhum** |
| medição em portal de seguradora | ⛔ fora do escopo desta pesquisa |
