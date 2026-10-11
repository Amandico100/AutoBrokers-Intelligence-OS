# AGREGADO POR RAMO — o histórico do Agger da corretora (Condomínio 16 · Residencial 2 · Empresarial 18)

> B0-c · SPEC-129-C · 11/10/2026, sessão de LEITURA das 01:05 às 01:25 (relógio da máquina), login de pessoa autorizado
> pelo Founder. 📊 `calcularV2 = 0`, trocas de token = 2 (teto da guarda: 6/h), ~221 GETs, logout pela tela `True`.
> Sem dado pessoal: nomes, documentos e endereços nunca saíram do processo. Para casar renovações usei o agrupamento por
> cliente que a própria busca faz e um hash do endereço; nenhum valor foi impresso.
> Fonte: `agregado.json` + `agregado2.json` (mesma pasta). Universo da busca (730 d, `negocio/busca/v2?ramos=`): 📊
> condomínio **677 negócios / 385 clientes** · residencial **121 / 94** · empresarial **186 / 105**.

## Amostra lida (por ramo)
15 negócios com status 2 (calculado), criados há mais de 3 dias: os **10 mais recentes** e **5 de 1–2 anos atrás**
(📊 condomínio 4–11 d e 367–410 d · residencial 5–18 d e 368–410 d · empresarial 3–27 d e 369–417 d). Para cada um:
todas as versões (`cotacao/versoes/{ref}`) e a resposta (`cotacao/calculos/{ref}/{versao}`). Mais os pares de renovação
(abaixo). ⚠️ Os 5 "antigos" foram **migrados** para o Aggilizador novo (📊 `dataHoraMigracao` = 03/09/2026): os itens
deles têm outra forma (26 chaves, sem a configuração da seguradora) e carregam o erro de migração — não valem como
"recusa".

## (1) Quem deu preço — com preço / presentes no cálculo
| seguradora | Condomínio recentes | Cond. antigos | Residencial recentes | Resid. antigos | Empresarial recentes | Empr. antigos |
|---|---|---|---|---|---|---|
| Porto | 9/10 | 5/5 | 7/10 | 5/5 | 7/8 | 2/5 |
| Tokio | **10/10** | 3/5 | 6/10 | 3/5 | 4/9 | 1/5 |
| HDI | 8/8 | 4/5 | 7/10 | 5/5 | **8/9** | 1/5 |
| Allianz | 7/9 | 3/5 | **8/9** | 3/5 | 6/7 | 4/5 |
| Axa | 4/8 | 4/5 | — | — | 1/8 | 3/5 |
| Bradesco | 2/9 | 2/5 | 7/10 | 3/5 | 2/7 | 2/5 |
| Chubb | 0/2 | 0/4 | — | 0/5 | 1/2 | 2/5 |
| Alfa | — | 0/4 | — | 5/5 | — | 1/5 |
| Liberty (Yelum) | — | — | 7/10 | 4/5 | 3/8 | 1/5 |
| Mapfre | — | — | 7/10 | 2/5 | 3/6 | 0/5 |
| Zurich | — | — | 3/10 | 4/5 | 1/2 | 2/5 |

⚠️ A HDI dá preço nos três ramos nos negócios recentes, embora o `cotador@` a mostre com credencial inválida (§11 da
PROVA; a credencial é compartilhada — 💭 ela foi consertada depois do teste guardado, ou o teste guardado está velho).
Prêmio do resultado (📊 só os com preço): condomínio mediana **R$ 11.161** (R$ 2.061–189.643, n=61) · residencial
**R$ 744** (R$ 227–13.049, n=86) · empresarial **R$ 2.122** (R$ 296–37.108, n=55). Menor preço ÷ mediana do mesmo negócio:
📊 condomínio 0,73 (0,60–0,85) · residencial 0,69 (0,27–0,91) · empresarial 0,67 (0,17–0,98).

### Famílias de recusa/erro (texto normalizado, contagem de seguradora×negócio)
- **Migração** (só os antigos): "essa cotação possui algum erro ou não apresenta valor, por esse motivo não foi migrada para o novo aggilizador" — 📊 cond 17 · resid 16 · empr 36.
- **Credencial**: "Login ou senha incorreta. Confira suas credenciais de acesso." (cond 4 · resid 2 · empr 6); "usuário e/ou senha incorretos… atualizar o login" (1); Tokio "é necessário fazer a adesão ao multicálculo no portal" (1).
- **Aceitação**: "risco sem aceitação para este cenário nesta seguradora" · "risco recusado. fora da atual política de aceitação" · "# - risco restrito" · "risco com divergência de experiência (#)" · "risco proibido… para o local de risco" · "o cálculo deve ser encaminhado para análise" · "cotação não será realizada - motivo técnico".
- **Limite de cobertura (LMI)** — a família mais rica de RE: "valor de IS da cobertura PERDA OU PAG DE ALUG. supera o máximo permitido (#)" · "LMR da cobertura inferior ao LMR mínimo" · "limite máximo para [roubo] é #% da cobertura básica" · "danos elétricos… fora do intervalo permitido (#% até #%) em função da cobertura" · "danos por água acima do limite máximo" · "desmoronamento supera o limite máximo" · "perda de lucro bruto limitada a #% de lucros cessantes" · "LMI de despesas fixas acima do permitido (#% da cobertura incêndio)" · RC guarda de veículos: "o número de vagas deve ser maior do que…".
- **Construção/uso** (residencial): "usuário sem autorização para cotar construção madeira" · "o tipo de construção (inferior) não está disponível" · "LMI de roubo – veraneio acima do permitido".
- **Atividade** (empresarial): "atividade deve ser especificada corretamente" · "atividade inválida" · "atividade bloqueada… sujeita a análise prévia" · "atividade declinada".
- **Comissão** (empresarial): "comissão do corretor acima do permitido" · "percentual de comissão… ultrapassa o máximo de (#%)" · "a comissão deve possuir um valor entre #% e #%".
- **Renovação/cadastro**: "não foi possível calcular como renovação interna, alterar para seguro novo" · "Verificamos que esse proponente pode ser uma Renovação AXA" · "cotação de renovação não encontrada para o segurado" · "a apólice informada (#) é inválida" · "código da seguradora anterior inválido" · "endereço não encontrado para o CEP informado" · "Nº de ocorrências: Campo Obrigatório".
- **Genérico**: "ocorreu um erro inesperado… tente novamente" · "Erro - descrição retorno vazio".

## (2) Coberturas enviadas e LMIs típicos (`cotacao.configuracoes`, valores > 0, n = negócios dos 15)
**Condomínio** — básica = `isDanosIncendioRaioExplosao` (📊 15/15): mediana **R$ 14 mi** (p25 12 mi · p75 33,6 mi · 2,5–115 mi);
conteúdo dos condôminos `isDanosIncendioRaioExplosaoCond` 11/15, mediana 1,6 mi · danos elétricos 15/15 mediana 52 mil ·
impacto de veículo 15/15 50 mil · vidros 15/15 15 mil · RC condomínio `isValorCondominio` 15/15 300 mil · RC síndico
`isValorSindico` 15/15 300 mil · vendaval 15/15 84 mil · portões 15/15 30 mil · danos morais 14/15 50 mil · tumulto 13/15
20 mil · roubo 13/15 10 mil · perda de aluguel 11/15 300 mil · vazamento 11/15 70 mil · desmoronamento 8/15 · roubo do
condômino 7/15 30 mil · RC garagista exclusiva 6/15 100 mil · RC empregador 6/15 200 mil · garagista 5/15 · despesas fixas
3/15 · alagamento 2/15. Assistência: 📊 código 3 (Completa) em 8, 1 (Básica) em 7. Valor de novo = 1 em 15/15.
**Residencial** — básica: mediana **R$ 550 mil** (p25 400 mil · p75 1 mi · 150 mil–6 mi); elétricos 13/15 25 mil · vendaval
13/15 50 mil · RC familiar 12/15 50 mil · aluguel 10/15 36 mil · roubo 10/15 37,5 mil · vazamento 9/15 20 mil · vidros 9/15
20 mil. Assistência: 2 (Intermediária) em 10, 1 em 5. Objeto 3 (Prédio+Conteúdo) em 14/15.
**Empresarial** — básica: mediana **R$ 2 mi** (p25 1,5 mi · p75 4,5 mi · 350 mil–38 mi); elétricos 15/15 30 mil · RC
`responsabilidadeCivil` e `responsabilidadeCivilOperacoes` 12/15 125 mil (sempre iguais) · vidros 11/15 10 mil · aluguel
10/15 90 mil · vendaval 10/15 100 mil · roubo 10/15 30 mil · impacto 8/15 · vazamento 8/15 · equipamentos 7/15 50 mil ·
recomposição de documentos 6/15 · tumulto 6/15 · lucros cessantes 4/15 · RC empregador 4/15. Assistência: 1 em 15/15.

### "Padrão" × "mais em conta"
O Agger não marca isso: o que existe são as **versões** que a corretora fez do mesmo negócio. Nos negócios com 2+ versões
(📊 cond 4, resid 2, empr 6), comparei a versão de maior menor-preço ("padrão") com a de menor ("mais em conta"):
- condomínio: razão 0,66–0,98; em 2 de 4 **nada mudou nas coberturas** (só o resultado das seguradoras); 1 tirou alagamento (0,84).
- residencial: básica 1 mi→500 mil + roubo 50→12 mil + vendaval 1 mi→200 mil (0,26) · assistência 2→1 (0,72).
- empresarial: tirar elétricos/roubo/vazamento/RC (0,23) · assistência 2→1 + tirar roubo/vendaval/vazamento (0,68) · em 1 nada mudou (0,88).
→ 💭 o "mais em conta" de RE é **tirar acessórias e baixar a assistência**, nunca mexer na básica sem o cliente (a única que
baixou a básica foi residencial). Amostra pequena.

## (3) A regra "+15 % na básica na renovação"
Pares = o MESMO cliente (mesmo CPF/CNPJ, pelo agrupamento da busca) com dois negócios a 300–430 dias (residencial e
empresarial ampliados a 240–520 d por falta de pares). Mesmo risco = hash do logradouro+número+CEP.
| ramo | pares | mesmo endereço | razão básica ano2/ano1 |
|---|---:|---:|---|
| Condomínio | **41** | 40 | mediana **1,133** · p25 1,10 · p75 1,167 · faixas: =1,00 → 2 · 1,00–1,09 → 1 · **≈+10 % (1,09–1,11) → 16** · 1,11–1,14 → 5 · **≈+15 % (1,14–1,16) → 6** · 1,16–1,30 → 7 · >1,30 → 4 |
| Empresarial | 7 | 4 | os 4 do mesmo endereço = **+10 %** (1,10 · 1,10 · 1,10 · 1,108); os outros 3 (endereço diferente) 0,63 · 0,66 · 1,50 |
| Residencial | 2 | 0 | inconclusivo (0,29 e 2,30, endereços diferentes) |
📊 → **o reajuste mais comum é +10 %, não +15 %** (16 de 41 condomínios; +15 % em 6). A mediana é +13 %. A renovação vem
marcada (`renovacao=true`, `seguradoraAnteriorId` e `numeroRenovacao` preenchidos) em 15/15 condomínios lidos. As outras
coberturas em geral se repetem idênticas no ano 2 (RC síndico às vezes dobra).

## (4) Empresarial — atividades
A atividade vai **por seguradora** em `calculos[].valoresAjusteSeguradora.imovelAtividadeProfissionalLocal =
{Key: código da seguradora, Value: rótulo, Description: null}` (📊 presente em Tokio 10 · HDI 10 · Axa 9 · Liberty 9 · Porto 9 ·
Bradesco 8 · Mapfre 7 · Allianz 7 · Chubb 3 · Zurich 3 itens). CNAE do segurado em `configuracoes.cnae`/`segurado.cnae`.
Mais comuns: **escritórios** (de longe — "ESCRITORIOS", "Escritório", "701.75 - Escritório de pessoa física ou jurídica",
"101 - ESCRITORIO - … superior"), **postos de combustível**, **máquinas/equipamentos (loja e depósito)**, **artigos
médicos/dentários e consultórios**, **salão de beleza/estética**. CNAE: 📊 5510801 (hotéis) 8 · 8630504 (odontologia) 3 ·
4530703 · 4781400 · 6911701 (2 cada).
